"""Stage EXACT original 393 offline assets to ONLY isolated research external files.

Only owner-private exact-MD5 358 extracted members and 35 APK source TSVs.
No PONOS publisher app, no online traffic, no ADB uninstall, no SAVE reads
or writes, no internal files root access. Explicit --stage is required.
Never overwrite an existing remote file; stop on a wrong MD5.
"""
from __future__ import annotations

import argparse
from hashlib import md5
from pathlib import Path
import re
import subprocess
import tempfile
from zipfile import ZipFile

from tools.base_mod.offline_server_import_manifest import original_offline_asset_manifest
from tools.base_mod.fetch_godzilla_server_assets import verify
from tools.base_mod.audit_scene97_offline_readiness import audit_scene97, _private_path

PACKAGE = "jp.kn.local.battlecats"
STAGE = f"/sdcard/Android/data/{PACKAGE}/files/kneekura-original-jp1571-stage"
EXPECTED_COUNT = 393

class OwnerStageBlocked(ValueError):
    pass

def _call(cmd: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              errors="replace", timeout=timeout, check=False)
    except (subprocess.TimeoutExpired, OSError):
        raise OwnerStageBlocked("ANDROID_STAGE_COMMAND_FAILED_OR_TIMED_OUT") from None

def _md5_of(data: bytes) -> str:
    return md5(data).hexdigest()

def stage_owner_original(*, repo: Path, candidate: Path, cache: Path, adb: Path,
                         stage: bool = False, repair_incomplete: bool = False,
                         announce=lambda text: None) -> dict:
    repo = repo.resolve(strict=True)
    candidate = _private_path(repo, candidate, exists=True)
    cache = _private_path(repo, cache, exists=True)
    if not adb.is_file() or adb.is_symlink():
        raise OwnerStageBlocked("ANDROID_ADB_TOOL_INVALID")
    local = audit_scene97(repo=repo, candidate=candidate, cache=cache)
    if not local["all_original_extracted_members_verified"]:
        raise OwnerStageBlocked("LOCAL_SOURCE_358_ORIGINAL_MD5_INCOMPLETE")
    entries = original_offline_asset_manifest(candidate / "split_InstallPack.apk")
    if len(entries) != EXPECTED_COUNT:
        raise OwnerStageBlocked("393_SOURCE_INDEX_COUNT_DRIFT")
    if not stage:
        return {"status":"PLAN_ONLY_NO_ANDROID_WRITES", "source_count":len(entries),
                "device_changed":False}

    devices = _call([str(adb), "devices"], timeout=15)
    lines = [x.strip().split()[0] for x in devices.stdout.splitlines()
             if re.fullmatch(r"\S+\s+device", x.strip())]
    if devices.returncode or len(lines) != 1:
        raise OwnerStageBlocked("SINGLE_AUTHORIZED_DEVICE_REQUIRED")
    serial = lines[0]
    paths = _call([str(adb), "-s", serial, "shell", "pm", "path", PACKAGE], timeout=20)
    if paths.returncode or len([x for x in paths.stdout.splitlines()
                               if x.startswith("package:/")]) != 6:
        raise OwnerStageBlocked("ISOLATED_RESEARCH_SIX_SPLIT_MISSING")
    created = _call([str(adb), "-s", serial, "shell", "mkdir", "-p", STAGE], timeout=20)
    if created.returncode:
        raise OwnerStageBlocked("RESEARCH_EXTERNAL_STAGE_CREATE_BLOCKED")
    completed = 0
    already = 0
    # Only original APK TSV extraction uses a temporary private directory.
    with tempfile.TemporaryDirectory(dir=repo/"private",
                                     prefix="owner-393-tsv-stage-") as temp:
        temp_path=Path(temp)
        for name,size,expected_md5 in entries:
            if name.endswith(".tsv"):
                idx=int(name[len("download_"):-len(".tsv")])
                with ZipFile(candidate/"split_InstallPack.apk") as source:
                    raw=source.read(f"assets/download_{idx}.tsv")
                if len(raw)!=size or _md5_of(raw)!=expected_md5:
                    raise OwnerStageBlocked("ORIGINAL_APK_TSV_MD5_DRIFT")
                local_source=temp_path/name
                local_source.write_bytes(raw)
            else:
                local_source=cache/name
                try:
                    verify(local_source,(size,expected_md5))
                except (OSError,ValueError):
                    raise OwnerStageBlocked("EXISTING_ORIGINAL_MEMBER_MD5_DRIFT") from None
            remote=STAGE+"/"+name
            old=_call([str(adb), "-s", serial, "shell", "md5sum", remote],timeout=40)
            if old.returncode==0:
                tokens=old.stdout.strip().split()
                if len(tokens)<2 or tokens[0].lower()!=expected_md5:
                    if not repair_incomplete:
                        raise OwnerStageBlocked("EXISTING_RESEARCH_STAGE_MD5_MISMATCH_STOP")
                    # This is OUR fixed isolated research EXTERNAL staging leaf,
                    # with a source-pinned safe name. Never delete files from
                    # app internal, publisher, or any other folder.
                    cleanup = _call([str(adb), "-s", serial, "shell",
                                     "rm", "-f", remote], timeout=30)
                    if cleanup.returncode:
                        raise OwnerStageBlocked("PARTIAL_RESEARCH_STAGE_CLEANUP_REFUSED")
                    old = _call([str(adb), "-s", serial, "shell",
                                 "md5sum", remote], timeout=30)
                    if old.returncode == 0:
                        raise OwnerStageBlocked("PARTIAL_RESEARCH_STAGE_STILL_PRESENT")
                    sent = _call([str(adb), "-s", serial, "push",
                                  str(local_source), remote], timeout=240)
                    if sent.returncode:
                        raise OwnerStageBlocked("RESEARCH_EXTERNAL_ASSET_REPAIR_PUSH_FAILED")
                    post = _call([str(adb), "-s", serial, "shell",
                                  "md5sum", remote], timeout=40)
                    if post.returncode or not post.stdout.strip().lower().startswith(expected_md5+" "):
                        raise OwnerStageBlocked("REPAIRED_RESEARCH_ASSET_MD5_MISMATCH")
                    completed+=1
                else:
                    already+=1
            else:
                sent=_call([str(adb), "-s", serial, "push",
                            str(local_source),remote],timeout=240)
                if sent.returncode:
                    retry_devices=_call([str(adb),"devices"],timeout=15)
                    if not any(re.fullmatch(r"\S+\s+device",x.strip())
                               for x in retry_devices.stdout.splitlines()):
                        raise OwnerStageBlocked("ADB_DISCONNECTED_DURING_RESEARCH_EXTERNAL_STAGE")
                    raise OwnerStageBlocked("ADB_PUSH_ORIGINAL_MEMBER_FAILED_STOP")
                post=_call([str(adb), "-s", serial, "shell", "md5sum", remote],timeout=40)
                if post.returncode or not post.stdout.strip().lower().startswith(expected_md5+" "):
                    raise OwnerStageBlocked("ADB_STAGE_MEMBER_MD5_MISMATCH_STOP")
                completed+=1
            if (completed+already)%39==0:
                announce("RESEARCH_EXTERNAL_ORIGINAL_ASSETS_VERIFIED="+str(completed+already))
    return {
        "status":"EXACT_393_SOURCE_FILES_IN_RESEARCH_EXTERNAL_STAGE_NO_NATIVE_IMPORT",
        "source_count":len(entries),
        "newly_staged":completed,
        "previously_matching":already,
        "all_original_stage_md5_verified":completed+already==EXPECTED_COUNT,
        "research_private_internal_files_or_SAVE_touched":False,
        "publisher_app_touched":False,
        "research_game_restarted":False,
    }

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--adb", type=Path, required=True)
    p.add_argument("--stage", action="store_true", help="Explicit owner-device external-only staging")
    p.add_argument("--repair-incomplete", action="store_true",
                   help="Repair ONLY wrong-MD5 files in our dedicated external 393 stage leaf")
    a=p.parse_args()
    try:
        result=stage_owner_original(repo=a.repo,candidate=a.candidate,
                                    cache=a.cache,adb=a.adb,stage=a.stage,
                                    repair_incomplete=a.repair_incomplete,
                                    announce=print)
    except (OSError,ValueError) as exc:
        p.error(str(exc))
    import json
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
