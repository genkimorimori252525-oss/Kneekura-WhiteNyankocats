"""Read-only device inventory and optional owner-local collection of Godzilla rig packs.

The exact research build may hold the 615 MiB original in-app download in its
external files directory. Only four original Server pack/list files are needed
to privately extract seven 550_e animation assets. Never uploads anything.
No APK install, root, Frida, new-game, SAVE_DATA write or shell script injection.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile

PACKS = ("MNumberServer.list", "MNumberServer.pack",
         "WImageDataServer.list", "WImageDataServer.pack")
ALLOWED_PACKAGES = frozenset({
    "jp.kn.trace.battlecats", "jp.kn.white.battlecats",
    "jp.kn.clean.battlecats", "jp.co.ponos.battlecats",
})


def run_checked(args: list[str], *, timeout: int = 45) -> str:
    result = subprocess.run(args, shell=False, text=True, capture_output=True,
                            timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError("ADB command failed (no game state was changed): " +
                           result.stderr[-500:])
    return result.stdout


def get_device(adb: str, requested: str | None) -> str:
    if requested:
        if not requested.isascii() or any(ch.isspace() for ch in requested):
            raise ValueError("invalid ADB serial")
        state = run_checked([adb, "-s", requested, "get-state"])
        if state.strip() != "device":
            raise ValueError("requested device not in authorized device state")
        return requested
    lines = run_checked([adb, "devices"]).splitlines()[1:]
    devices = [row.split()[0] for row in lines
               if len(row.split()) == 2 and row.split()[1] == "device"]
    if len(devices) != 1:
        raise ValueError("exactly one ADB authorized device required; pass --device")
    return devices[0]


def remote_root(package: str) -> str:
    if package not in ALLOWED_PACKAGES:
        raise ValueError("unrecognized Battle Cats package, refused")
    return "/sdcard/Android/data/" + package + "/files"


def parse_remote_paths(output: str, *, root: str, filename: str) -> list[str]:
    if filename not in PACKS:
        raise ValueError("not a required Godzilla Server pack")
    found = []
    for line in output.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("find:"):
            continue
        path = PurePosixPath(candidate)
        if path.name != filename or not (candidate.startswith(root + "/")) or ".." in path.parts:
            raise ValueError("out-of-sandbox ADB path returned")
        if candidate not in found:
            found.append(candidate)
    return found


def inventory(adb: str, device: str, package: str) -> dict[str, str | None]:
    root = remote_root(package)
    report: dict[str, str | None] = {}
    for name in PACKS:
        listing = run_checked([adb, "-s", device, "shell", "find", root,
                               "-type", "f", "-name", name], timeout=60)
        paths = parse_remote_paths(listing, root=root, filename=name)
        if len(paths) > 1:
            raise ValueError("multiple conflicting cache copies of " + name)
        report[name] = paths[0] if paths else None
    return report


def collect(adb: str, device: str, package: str, target: Path,
            *, pull: bool = False) -> dict:
    selected = inventory(adb, device, package)
    missing = [name for name, path in selected.items() if path is None]
    result = {
        "schema_version": 1,
        "mode": "owner-private-1.01-server-pack-inventory",
        "package": package,
        "remote_paths": selected,
        "missing": missing,
        "downloaded_locally": False,
        "private": True,
        "device_save_mutated": False,
        "game_apk_mutated": False,
    }
    if not pull:
        return result
    if missing:
        raise ValueError("missing original Server packs; complete original in-app download first: " +
                         ", ".join(missing))
    if target.exists():
        raise ValueError("output directory must not exist; refusing overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".kneekura-101-owned-",dir=target.parent) as td:
        stage = Path(td) / "original-server-packs"
        stage.mkdir()
        artifacts = {}
        for name, remote in selected.items():
            assert remote is not None
            local = stage / name
            run_checked([adb, "-s", device, "pull", remote, str(local)], timeout=360)
            if not local.is_file() or local.stat().st_size == 0:
                raise RuntimeError("ADB pull did not return required Server file: " + name)
            digest = hashlib.sha256()
            with local.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    digest.update(chunk)
            artifacts[name] = {"size": local.stat().st_size, "sha256": digest.hexdigest()}
        result["downloaded_locally"] = True
        result["sha256_receipts"] = artifacts
        (stage/"owner-private-pack-receipt.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",encoding="utf-8")
        stage.rename(target)
    return result


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adb", default="adb")
    p.add_argument("--device")
    p.add_argument("--package", choices=sorted(ALLOWED_PACKAGES),
                   default="jp.kn.trace.battlecats")
    p.add_argument("--output",type=Path,default=Path("private/kneekura-101-godzilla-packs"))
    p.add_argument("--pull",action="store_true",help="Explicitly collect only the 4 files")
    args=p.parse_args(argv)
    device=get_device(args.adb,args.device)
    result=collect(args.adb,device,args.package,args.output,pull=args.pull)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if not result["missing"] else 2


if __name__=="__main__":
    raise SystemExit(main())