"""Read-only owner-device signer preflight for an original-game research update.

Checks only installed jp.kn.local.battlecats. Never installs, starts, stops,
uninstalls, clears SAVE/logs or queries the publisher app. Pulls ONLY the
installed research base.apk to a private temporary directory and deletes it.
Only a metadata receipt with no device IDs, APKs, or certificate digests remains.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from uuid import uuid4
from zipfile import ZipFile, BadZipFile

PACKAGE = "jp.kn.local.battlecats"
SPLITS = (
    "base.apk", "split_InstallPack.apk", "split_config.arm64_v8a.apk",
    "split_config.en.apk", "split_config.ja.apk", "split_config.xxhdpi.apk",
)
MAIN = "lib/arm64-v8a/libshadowhook.so"
COMPANION = "lib/arm64-v8a/libshadowhook_nothing.so"
SHIM = "lib/arm64-v8a/libkneekura.so"
MAIN_SHA = "fc84287eac46e3bade2f7e07e3c9efdca005822e21191d6db5b8cb222d53e8a0"
COMPANION_SHA = "f2cc6a6f94d7361be915daafff1d25b7b3af34972e7308ac540982cfd608bd32"
MARKERS = (
    b"original-native-scene-hook-v1 hook-api-missing",
    b"original-native-scene-hook-v1 hook-runtime-init-failed",
    b"original-native-scene-hook-v1 hook-init-status=%d",
)
CERT = re.compile(r"Signer #1 certificate SHA-256 digest:\s*([0-9a-fA-F:]{64,95})")
RESEARCH_DIRECTORY = re.compile(r"^jp\.kn\.local\.battlecats-[A-Za-z0-9._+=~\-]+$")


class PreflightBlocked(ValueError):
    """Fail without embedding any private stdout/stderr/path/device identifiers."""


def _owned_file(path: Path, label: str) -> Path:
    if not path.is_file() or path.is_symlink():
        raise PreflightBlocked("required file missing or unsafe: " + label)
    return path.resolve(strict=True)


def _private(repo: Path, path: Path, *, must_exist: bool) -> Path:
    root = repo / "private"
    if not root.is_dir() or root.is_symlink():
        raise PreflightBlocked("repository private folder missing/unsafe")
    root = root.resolve(strict=True)
    current = path.absolute()
    while current != repo and current != current.parent:
        if current.is_symlink():
            raise PreflightBlocked("private path contains a symlink")
        current = current.parent
    p = path.resolve(strict=must_exist)
    if p == root or not p.is_relative_to(root):
        raise PreflightBlocked("research path must stay under private/")
    return p


def _candidate(repo: Path, candidate: Path) -> Path:
    p = _private(repo, candidate, must_exist=True)
    if not p.is_dir() or p.name != "local-research-static-http-signed-splits":
        raise PreflightBlocked("not a signed original six-split research directory")
    for split in SPLITS:
        f = _owned_file(p / split, "research split")
        if not 512 <= f.stat().st_size <= 250_000_000:
            raise PreflightBlocked("research split has implausible size")
    parity_file = _owned_file(p / "parity-report.json", "research static parity")
    if parity_file.stat().st_size > 2_000_000:
        raise PreflightBlocked("research parity JSON too large")
    try:
        parity = json.loads(parity_file.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise PreflightBlocked("cannot validate original static parity report") from exc
    if not (
        isinstance(parity, dict)
        and parity.get("mode") == "static-java-http-bridge"
        and parity.get("package") == PACKAGE
        and parity.get("flavor") == "local-research"
        and parity.get("native_scene_hook_research_only") is True
        and parity.get("final_INTERNET_permission") is False
        and parity.get("research_no_internet_manifest") is True
        and parity.get("reviewed_external_hook_binary_hash_pinned") == MAIN_SHA
        and parity.get("reviewed_official_shadowhook_companion_hash_pinned") == COMPANION_SHA
        and isinstance(parity.get("repackaged_original_native_scene_layout"), dict)
        and parity["repackaged_original_native_scene_layout"].get(
            "all_original_executable_text_bytes_unchanged_static") is True
    ):
        raise PreflightBlocked("no proof of exact original offline research parity/pair")
    try:
        with ZipFile(p / "split_config.arm64_v8a.apk") as archive:
            names = archive.namelist()
            if any(names.count(n) != 1 for n in (MAIN, COMPANION, SHIM)):
                raise PreflightBlocked("ARM64 research main/companion/shim missing or duplicated")
            main, companion, shim = (archive.read(x) for x in (MAIN, COMPANION, SHIM))
    except (BadZipFile, OSError, KeyError, RuntimeError) as exc:
        raise PreflightBlocked("cannot read original research signed ARM64 split") from exc
    if (hashlib.sha256(main).hexdigest() != MAIN_SHA or
            hashlib.sha256(companion).hexdigest() != COMPANION_SHA):
        raise PreflightBlocked("official ShadowHook main/companion SHA drift")
    if (b"kneekura-original-virgin-save-trial-v1" in shim
            or not all(marker in shim for marker in MARKERS)):
        raise PreflightBlocked("unsafe/missing passive original scene observer")
    return p


def _call(exe: Path, argv: list[str], stage: str, timeout: int, runner) -> str:
    try:
        result = runner(
            [str(exe), *argv], capture_output=True, text=True,
            errors="replace", check=False, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise PreflightBlocked("read-only " + stage + " timed out") from exc
    except OSError as exc:
        raise PreflightBlocked("read-only " + stage + " could not start") from exc
    if result.returncode != 0 or len(result.stdout) > 250_000:
        raise PreflightBlocked("read-only " + stage + " failed; raw ADB output suppressed")
    return result.stdout


def _device(text: str) -> str:
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices attached"):
            continue
        cols = line.split()
        if len(cols) != 2 or cols[1] != "device":
            raise PreflightBlocked("offline/unauthorized or ambiguous ADB device")
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", cols[0]):
            raise PreflightBlocked("unsafe ADB device ID format")
        entries.append(cols[0])
    if len(entries) != 1:
        raise PreflightBlocked("exactly one authorized device is required")
    return entries[0]


def _paths(text: str) -> dict[str, str]:
    rows = [x.strip() for x in text.splitlines() if x.strip()]
    if len(rows) != len(SPLITS):
        raise PreflightBlocked("installed research must have exactly six APK splits")
    result: dict[str, str] = {}
    for row in rows:
        if not row.startswith("package:"):
            raise PreflightBlocked("untrusted installed research package reply")
        remote = row[len("package:"):]
        if (".." in remote or "\\" in remote
                or not re.fullmatch(r"/data/app/[A-Za-z0-9._+=~/\-]+\.apk", remote)):
            raise PreflightBlocked("unsafe installed research APK location")
        parts = PurePosixPath(remote).parts
        if not any(RESEARCH_DIRECTORY.fullmatch(segment) for segment in parts):
            raise PreflightBlocked("installed APK is not an isolated research package")
        name = parts[-1]
        if name not in SPLITS or name in result:
            raise PreflightBlocked("duplicate or unexpected original research APK split")
        result[name] = remote
    if set(result) != set(SPLITS):
        raise PreflightBlocked("original research split set mismatch")
    return result


def _cert(text: str) -> str:
    if re.search(r"Signer #(?!1\b)\d+ certificate SHA-256 digest:", text):
        raise PreflightBlocked("multiple signing certificates not supported")
    rows = CERT.findall(text)
    if len(rows) != 1:
        raise PreflightBlocked("unavailable or ambiguous APK signing certificate")
    digest = rows[0].replace(":", "").lower()
    if not re.fullmatch("[a-f0-9]{64}", digest):
        raise PreflightBlocked("invalid signing certificate digest")
    return digest


def preflight(*, repo: Path, candidate: Path, adb: Path, apksigner: Path,
              output: Path | None = None, runner=subprocess.run) -> tuple[dict, Path]:
    repo = repo.resolve(strict=True)
    candidate = _candidate(repo, candidate)
    adb = _owned_file(adb, "adb tool")
    apksigner = _owned_file(apksigner, "apksigner tool")
    if output is None:
        output = repo / "private" / ("device-research-signer-" + uuid4().hex[:12] + ".json")
    output = _private(repo, output, must_exist=False)
    if output.exists() or output.is_symlink():
        raise PreflightBlocked("private research receipt already exists; no overwrite")

    serial = _device(_call(adb, ["devices"], "ADB state", 15, runner))
    installed = _paths(_call(
        adb, ["-s", serial, "shell", "pm", "path", PACKAGE],
        "isolated research APK paths", 20, runner,
    ))
    candidate_certs = [
        _cert(_call(apksigner, ["verify", "--print-certs", str(candidate / name)],
                    "signed candidate APK", 25, runner))
        for name in SPLITS
    ]
    if len(set(candidate_certs)) != 1:
        raise PreflightBlocked("candidate split signer mismatch; do not install")
    with tempfile.TemporaryDirectory(
        dir=(repo / "private"), prefix="read-only-installed-research-"
    ) as tmp:
        saved_base = Path(tmp) / "installed-base.apk"
        _call(
            adb, ["-s", serial, "pull", installed["base.apk"], str(saved_base)],
            "read installed research base.apk", 60, runner,
        )
        if not saved_base.is_file() or saved_base.stat().st_size < 512:
            raise PreflightBlocked("installed research base.apk inaccessible via unprivileged ADB")
        installed_cert = _cert(_call(
            apksigner, ["verify", "--print-certs", str(saved_base)],
            "read installed research APK signature", 25, runner,
        ))
    if installed_cert != candidate_certs[0]:
        raise PreflightBlocked(
            "candidate signer DOES NOT match actually installed isolated research app; never uninstall or clear data"
        )

    receipt = {
        "schema": "original-isolated-device-signer-preflight-v1",
        "status": "ACTUAL_INSTALLED_RESEARCH_SIGNER_MATCHED_BUILD_ONLY",
        "research_package": PACKAGE,
        "installed_research_splits": len(installed),
        "candidate_research_splits": len(SPLITS),
        "both_official_shadowhook_arm64_libraries_verified": True,
        "candidate_signer_matches_all_six_splits": True,
        "candidate_signer_matches_installed_research_base": True,
        "temporary_copy_of_installed_APK_removed": True,
        "original_game_or_player_SAVE_read_or_modified": False,
        "adb_calls_read_only": True,
        "device_install_launch_stop_or_clear_executed": False,
        "actual_game_boot_or_Level60_passed": False,
        "zero_external_network_proven": False,
        "user_approved_device_update_still_required": True,
        "device_serial_cert_digest_remote_path_saved": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return receipt, output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--adb", required=True, type=Path)
    parser.add_argument("--apksigner", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report, _ = preflight(
            repo=args.repo, candidate=args.candidate, adb=args.adb,
            apksigner=args.apksigner, output=args.output,
        )
    except (PreflightBlocked, OSError) as exc:
        parser.error(str(exc))
    print(report["status"])
    print("Saved only PRIVATE metadata; no device ID/signing digest/raw APK.")
    print("NO DEVICE INSTALL: owner approval and independent install gate remain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
