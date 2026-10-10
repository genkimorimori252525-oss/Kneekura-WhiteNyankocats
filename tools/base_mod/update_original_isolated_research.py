"""Explicitly approved, same-signer update of ONLY the isolated research APK.

This is NOT run by builds or CI. Default is REFUSE; the human must explicitly
request the one supported local package update. Before the only permitted
write operation, run the proven read-only six-split/source/signer gate. Never
uninstall, clear/recreate SAVE, touch publisher app, launch the game, downgrade,
force-stop or read research SAVE contents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4
from typing import Any

from tools.base_mod.preflight_original_device_update import (
    _call,
    _candidate,
    _device,
    _owned_file,
    _paths,
    PACKAGE,
    SPLITS,
    PreflightBlocked,
    preflight,
)

_APPROVAL = "YES_UPDATE_ONLY_jp.kn.local.battlecats"


class ResearchUpdateBlocked(PreflightBlocked):
    """Suppress all raw ADB output, device identifiers and private APK paths."""


def _one_device(adb: Path, runner) -> str:
    return _device(_call(adb, ["devices"], "ADB state", 15, runner))


def _installed_paths(adb: Path, serial: str, runner) -> dict[str, str]:
    return _paths(_call(
        adb, ["-s", serial, "shell", "pm", "path", PACKAGE],
        "original isolated package paths", 20, runner,
    ))


def _not_running(adb: Path, serial: str, runner) -> bool:
    # pidof exit code 1 is a normal "not running" result on Android.
    # Any other failure/device-offline, stderr, multiple PID or unexpected
    # response rejects update without attempting package installation.
    try:
        result = runner(
            [str(adb), "-s", serial, "shell", "pidof", PACKAGE],
            capture_output=True, text=True, errors="replace",
            check=False, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ResearchUpdateBlocked("isolated research process state unavailable") from exc
    stdout = result.stdout.strip()
    if result.returncode == 1 and not stdout and not result.stderr.strip():
        return True
    if result.returncode == 0 and stdout.isascii() and stdout.isdigit():
        raise ResearchUpdateBlocked(
            "isolated research app currently running; close normally before update"
        )
    raise ResearchUpdateBlocked("cannot safely establish research app stopped")


def _checksums(candidate: Path) -> dict[str, str]:
    return {
        name: hashlib.sha256((candidate / name).read_bytes()).hexdigest()
        for name in SPLITS
    }


def run_user_approved_update(
    *, repo: Path, candidate: Path, adb: Path, apksigner: Path,
    explicit_approval: str, runner=subprocess.run,
) -> tuple[dict[str, Any], Path]:
    """Only writable device command: adb -s SERIAL install-multiple --no-streaming -r SIX_APKS.

    Everything else reads public installation/signer metadata. No upgrade
    is attempted on lost USB, an app already running, mutated bytes or a
    newly mismatched actual installed package. Postflight never relaunches.
    """
    if explicit_approval != _APPROVAL:
        raise ResearchUpdateBlocked("isolated update requires explicit owner approval")
    repo = repo.resolve(strict=True)
    candidate = _candidate(repo, candidate)
    adb = _owned_file(adb, "ADB executable")
    apksigner = _owned_file(apksigner, "Android APK signer")
    hashes_before = _checksums(candidate)
    serial_before = _one_device(adb, runner)
    paths_before = _installed_paths(adb, serial_before, runner)
    if not _not_running(adb, serial_before, runner):
        raise ResearchUpdateBlocked("original research app must not be running")
    if _one_device(adb, runner) != serial_before:
        raise ResearchUpdateBlocked("Android USB device identity changed before update")

    with tempfile.TemporaryDirectory(
        dir=repo / "private", prefix="approved-original-update-proofs-",
    ) as scratch:
        scratch_dir = Path(scratch)
        # The preflight deliberately pulls ONLY the installed research base.apk
        # to an auto-cleaned owner-private location for certificate comparison.
        before, _ = preflight(
            repo=repo, candidate=candidate, adb=adb, apksigner=apksigner,
            output=scratch_dir / "read-only-before.json", runner=runner,
        )
        if not before["candidate_signer_matches_installed_research_base"]:
            raise ResearchUpdateBlocked("read-only installed signer gate failed")
        if _one_device(adb, runner) != serial_before:
            raise ResearchUpdateBlocked("Android device identity changed")
        if _installed_paths(adb, serial_before, runner) != paths_before:
            raise ResearchUpdateBlocked("installed research package changed during preflight")
        if not _not_running(adb, serial_before, runner):
            raise ResearchUpdateBlocked("research game started while checking update")
        if _checksums(candidate) != hashes_before:
            raise ResearchUpdateBlocked("signed APK content changed during preflight")

        # One intentionally permitted Android write. Do NOT retry after a
        # timeout: the original package installer might still have committed.
        command = ([str(adb), "-s", serial_before, "install-multiple",
                    "--no-streaming", "-r"] +
                   [str(candidate / name) for name in SPLITS])
        try:
            result = runner(
                command, capture_output=True, text=True,
                errors="replace", check=False, timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ResearchUpdateBlocked(
                "isolated six-split install outcome unknown; do not retry automatically"
            ) from exc
        # Some ADB versions prefix benign install-progress lines. The LAST
        # line must still be exact Success and the exit status must be zero.
        # Never accept a substring, a trailing Failure, or ambiguous output.
        stdout_lines = [line.strip() for line in result.stdout.splitlines()
                        if line.strip()]
        if (result.returncode != 0 or not stdout_lines
            or stdout_lines[-1] != "Success"):
            raise ResearchUpdateBlocked(
                "isolated six-split installer did not finish with exact Success; do not clear data"
            )

        # Re-read installed research package; neither launching nor
        # touching its SAVE, checking publisher package or clearing logs.
        if _one_device(adb, runner) != serial_before:
            raise ResearchUpdateBlocked("update returned Success but device disconnected; no boot claim")
        _installed_paths(adb, serial_before, runner)
        try:
            after, _ = preflight(
                repo=repo, candidate=candidate, adb=adb, apksigner=apksigner,
                output=scratch_dir / "read-only-after.json", runner=runner,
                require_installed_bytes_match=True,
            )
        except PreflightBlocked as exc:
            # A successful ADB install followed by failed device attestation
            # must NEVER be described as safe completion or auto-retried.
            # No raw device stderr, serial or candidate paths in this error.
            raise ResearchUpdateBlocked(
                "post-update installed research signature mismatch or attestation failure; no automatic retry"
            ) from exc
        if not after["candidate_signer_matches_installed_research_base"]:
            raise ResearchUpdateBlocked("post-update installed research signature mismatch")
        if (after["installed_base_bytes_match_candidate"] is not True
            or after["installed_arm64_bytes_match_candidate"] is not True):
            raise ResearchUpdateBlocked(
                "post-update actual base/native split byte equality unavailable"
            )
    receipt = {
        "schema": "owner-explicit-original-isolated-sixsplit-update-v1",
        "status": "SIX_SPLIT_UPDATE_CONFIRMED_BASE_ARM64_BYTES_NOT_GAMEPLAY",
        "package": PACKAGE,
        "updated_splits": len(SPLITS),
        "prior_actual_research_signature_match": True,
        "post_install_actual_research_signature_match": True,
        "post_install_research_base_apk_byte_equal_candidate": True,
        "post_install_research_arm64_apk_byte_equal_candidate": True,
        "remaining_four_installed_split_bytes_not_compared": True,
        "official_shadowhook_two_arm64_libs_verified": True,
        "passive_shim_CI_byte_identity_verified": True,
        "owner_approval_present": True,
        "original_player_SAVE_was_not_read_by_tool": True,
        "android_data_preservation_not_dynamically_verified": True,
        "original_gameplay_black_screen_fix_unverified": True,
        "sdk_ipc_zero_egress_unverified": True,
        "no_uninstall_clear_reset_downgrade_or_publisher_package": True,
        "raw_android_device_ID_signer_APK_paths_not_retained": True,
    }
    path = repo / "private" / ("isolated-sixsplit-update-" + uuid4().hex[:12] + ".json")
    if path.exists() or path.is_symlink():
        raise ResearchUpdateBlocked("private update receipt destination occupied")
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt, path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--adb", required=True, type=Path)
    parser.add_argument("--apksigner", required=True, type=Path)
    parser.add_argument(
        "--approve-isolated-research-update",
        help="Only exact YES_UPDATE_ONLY_jp.kn.local.battlecats enables one install",
    )
    args = parser.parse_args()
    try:
        receipt, _ = run_user_approved_update(
            repo=args.repo, candidate=args.candidate, adb=args.adb,
            apksigner=args.apksigner,
            explicit_approval=args.approve_isolated_research_update or "",
        )
    except (PreflightBlocked, OSError) as exc:
        parser.error(str(exc))
    print(receipt["status"])
    print("No app was launched; run separate one-shot diagnostic after owner confirms.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
