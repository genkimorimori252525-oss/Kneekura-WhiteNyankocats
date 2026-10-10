"""Owner-only JP15.7.1 pre-update backup. Does not install or alter game data.

Snapshots exact SAVE_DATA and the six *installed* APK splits, validates the
Japanese salted-MD5 save trailer and APK signer. Optional already-signed
candidate APKs must have exactly the same package/version/certificate.
No uninstall, no clear-data, no force-stop and no implicit APK install.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile

APK_NAMES = ("base.apk", "split_config.arm64_v8a.apk",
             "split_config.en.apk", "split_config.ja.apk",
             "split_config.xxhdpi.apk", "split_InstallPack.apk")
PACKAGES = {"jp.kn.white.battlecats", "jp.kn.clean.battlecats",
            "jp.kn.trace.battlecats"}
CERT = re.compile(r"Signer #\d+ certificate SHA-256 digest:\s*([A-Fa-f0-9:]+)", re.I)
APP = re.compile(r"package:\s+name='([^']+)'\s+versionCode='(\d+)'")
VERSION_CODE = 1507010
SAVE_VERSION = 150700


class Refused(ValueError):
    pass


def call(args, *, timeout=40, can_fail=False):
    p = subprocess.run(args, shell=False, capture_output=True, text=True,
                       errors="replace", timeout=timeout)
    if p.returncode and not can_fail:
        raise Refused("tool failed: " + str(args[0]) + ": " + p.stderr[-200:])
    return p


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_integrity(raw):
    if len(raw) < 64 or struct.unpack_from("<i", raw, 0)[0] != SAVE_VERSION:
        raise Refused("incorrect JP15.7.1 SAVE_DATA version")
    try:
        trailer = raw[-32:].decode("ascii").lower()
    except UnicodeDecodeError as e:
        raise Refused("invalid SAVE_DATA hash characters") from e
    if hashlib.md5(b"battlecats" + raw[:-32]).hexdigest() != trailer:
        raise Refused("SAVE_DATA salted-MD5 check failed")
    return {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "jp_md5_valid": True, "version": SAVE_VERSION}


def installed_paths(lines):
    out = {}
    for row in lines.splitlines():
        if not row.strip():
            continue
        row = row.strip()
        if not row.startswith("package:/data/app/") or ".." in row:
            raise Refused("unexpected installed APK path")
        name = row.rsplit("/", 1)[-1]
        if name not in APK_NAMES or name in out:
            raise Refused("unexpected duplicate or additional split APK")
        out[name] = row[len("package:"):]
    if set(out) != set(APK_NAMES):
        raise Refused("expected exactly six existing APK splits")
    return out


def signer(apksigner, file):
    result = call([apksigner, "verify", "--verbose", "--print-certs",
                   str(file)], timeout=100).stdout
    ids = [x.replace(":", "").lower() for x in CERT.findall(result)]
    if len(ids) != 1 or len(ids[0]) != 64:
        raise Refused("cannot uniquely verify Android signer")
    return ids[0]


def package_version(aapt, base):
    report = call([aapt, "dump", "badging", str(base)], timeout=60).stdout
    m = APP.search(report)
    if not m:
        raise Refused("aapt could not prove application ID and version")
    return m.group(1), int(m.group(2))


def one_device(adb, selected=None):
    if selected:
        if not selected.isascii() or any(x.isspace() for x in selected):
            raise Refused("invalid ADB device serial")
        if call([adb, "-s", selected, "get-state"]).stdout.strip() != "device":
            raise Refused("requested device is not authorized")
        return selected
    lines = call([adb, "devices"]).stdout.splitlines()[1:]
    names = [l.split()[0] for l in lines
             if len(l.split()) == 2 and l.split()[1] == "device"]
    if len(names) != 1:
        raise Refused("connect exactly one authorized Android device")
    return names[0]


def optional_signed(signed_dir, pkg, aapt, apksigner, original_cert):
    if signed_dir is None:
        return None
    signed_dir = Path(signed_dir)
    files = sorted(p.name for p in signed_dir.glob("*.apk") if p.is_file())
    if files != sorted(APK_NAMES):
        raise Refused("update candidate does not have exactly six signed APKs")
    if package_version(aapt, signed_dir / "base.apk") != (pkg, VERSION_CODE):
        raise Refused("APK application ID or version differs from installed app")
    hashes = {}
    for name in APK_NAMES:
        src = signed_dir / name
        with zipfile.ZipFile(src) as apk:
            if apk.testzip():
                raise Refused("invalid signed APK CRC: " + name)
        if signer(apksigner, src) != original_cert:
            raise Refused("SIGNATURE MISMATCH -- REFUSING APK UPDATE")
        hashes[name] = fingerprint(src)
    return {"package": pkg, "same_signer": True, "sha256": hashes}


def snapshot(pkg, backup_dir, *, adb, aapt, apksigner,
             device=None, signed_dir=None):
    backup_dir = Path(backup_dir)
    if pkg not in PACKAGES:
        raise Refused("only an existing Kneekura app may be backed up")
    if backup_dir.exists():
        raise Refused("backup already exists; never overwrite original backup")
    device = one_device(adb, device)
    running = call([adb, "-s", device, "shell", "pidof", pkg], can_fail=True)
    if running.returncode == 0 and running.stdout.strip():
        raise Refused("save and close the game before update preflight")
    paths = installed_paths(call([adb, "-s", device, "shell", "pm", "path", pkg]).stdout)
    temp = Path(tempfile.mkdtemp(prefix="kneekura101-ascii-", dir=tempfile.gettempdir()))
    try:
        if not str(temp).isascii():
            raise Refused("use an ASCII-only Windows TEMP directory for ADB")
        apks = temp / "installed-original-apks"
        apks.mkdir()
        sha_original = {}
        cert = None
        for name in APK_NAMES:
            local = apks / name
            call([adb, "-s", device, "pull", paths[name], str(local)], timeout=500)
            if not local.is_file() or not local.stat().st_size:
                raise Refused("original APK backup could not be read: " + name)
            check = signer(apksigner, local)
            if cert is not None and cert != check:
                raise Refused("installed split APK signers disagree")
            cert = check
            sha_original[name] = fingerprint(local)
        if package_version(aapt, apks / "base.apk") != (pkg, VERSION_CODE):
            raise Refused("existing installed APK is not JP15.7.1 Kneekura build")
        save = temp / "SAVE_DATA"
        remote = f"/sdcard/Android/data/{pkg}/files/SAVE_DATA"
        call([adb, "-s", device, "pull", remote, str(save)], timeout=500)
        if not save.is_file():
            raise Refused("SAVE_DATA is inaccessible; no update permitted")
        saved = save_integrity(save.read_bytes())
        candidate = optional_signed(signed_dir, pkg, aapt, apksigner, cert)
        receipt = {
            "status": "BACKUP_VERIFIED_NO_UPDATE_PERFORMED",
            "package": pkg, "device": device, "save": saved,
            "installed_apks_sha256": sha_original,
            "installed_certificate_sha256": cert,
            "signed_candidate": candidate,
            "device_write_occurred": False,
            "app_was_uninstalled": False,
            "save_data_mutated": False,
        }
        (temp / "snapshot-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )
        backup_dir.parent.mkdir(parents=True, exist_ok=True)
        temp.rename(backup_dir)
        return receipt
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def locate_sdk(name):
    ext = ".exe" if os.name == "nt" else ""
    for candidate in (name + ext, name, name + ".bat"):
        got = shutil.which(candidate)
        if got:
            return got
    for root in (os.environ.get("ANDROID_HOME"),
                 os.environ.get("ANDROID_SDK_ROOT"),
                 str(Path(os.environ.get("LOCALAPPDATA", "")) / "Android/Sdk")):
        if not root:
            continue
        base = Path(root) / "build-tools"
        if base.is_dir():
            for version in sorted(base.iterdir(), reverse=True):
                for ext in (".exe", ".bat", ""):
                    candidate = version / (name + ext)
                    if candidate.is_file():
                        return str(candidate)
    raise Refused("Android SDK build-tools missing: " + name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", choices=sorted(PACKAGES), required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--signed-splits", type=Path)
    parser.add_argument("--device")
    parser.add_argument("--adb")
    parser.add_argument("--aapt")
    parser.add_argument("--apksigner")
    args = parser.parse_args(argv)
    adb = args.adb or shutil.which("adb") or str(
        Path(os.environ.get("LOCALAPPDATA", "")) / "Android/Sdk/platform-tools/adb.exe")
    try:
        report = snapshot(args.package, args.backup_dir,
                          adb=adb, aapt=args.aapt or locate_sdk("aapt"),
                          apksigner=args.apksigner or locate_sdk("apksigner"),
                          device=args.device, signed_dir=args.signed_splits)
    except (Refused, OSError, subprocess.TimeoutExpired, zipfile.BadZipFile) as e:
        parser.error(str(e))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())