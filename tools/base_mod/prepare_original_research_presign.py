"""Private, UNSIGNED, read-only owner JP15.7.1 original game reconstruction.

This stops BEFORE owner keystore/password/Android device access. Verifies
the precise user-owned source ZIP, CI-built passive ARM64 shim (no virgin
writer), ByteDance official ShadowHook 2.0.1 *two* ARM64 libraries, package
isolation, no-INTERNET manifest, original JNI mapped VMA and unchanged
native game executable text. Outputs only unsigned staged six-split APKs
under gitignored private/. NOT playable and NOT ready for installation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4

from tools.base_mod.extract_owned_splits import extract_owned_splits
from tools.base_mod.inject_shim import patch_split_set as inject_kneekura_shim
from tools.base_mod.package_flavor import patch_split_set as apply_package_flavor
from tools.base_mod.inject_java_http_bridge import build_bridge_dex, inject_bridge_split_set
from tools.base_mod.prepare_original_scene_witness import (
    check_original_scene_witness_build_contract,
    include_reviewed_shadowhook_in_private_split_set,
    APPROVED_OFFICIAL_SHADOWHOOK_V201_ARM64_SHA256,
    APPROVED_OFFICIAL_SHADOWHOOK_V201_COMPANION_SHA256,
)
from tools.base_mod.original_scene_native_image_gate import (
    verify_staged_original_scene_before_signing,
)
from tools.base_mod.verify_static_http_bridge import verify_static_http_bridge
from tools.base_mod.repack import JP_15_7_1_SPLITS

ISOLATED_PACKAGE = "jp.kn.local.battlecats"
RECEIPT_SCHEMA = "kneekura-private-unsigned-original-JP1571-paired-native-v1"


class UnsignedOriginalBuildBlocked(ValueError):
    pass


def _inside_private(repo: Path, source: Path, *, folder: bool = False) -> Path:
    base = (repo / "private").resolve(strict=True)
    if not base.is_dir() or (repo / "private").is_symlink():
        raise UnsignedOriginalBuildBlocked("isolated private working root missing or unsafe")
    resolved = source.resolve(strict=True)
    if source.is_symlink() or not resolved.is_relative_to(base):
        raise UnsignedOriginalBuildBlocked("research inputs must be owner-private regular files")
    if folder != resolved.is_dir():
        raise UnsignedOriginalBuildBlocked("unexpected research private input type")
    return resolved


def _source_receipt(shim: Path, receipt: Path, *, allow_local_pc: bool = False) -> dict:
    native = shim.read_bytes()
    if not 128 <= len(native) <= 24 * 1024 * 1024:
        raise UnsignedOriginalBuildBlocked("native private source library size invalid")
    if receipt.stat().st_size > 16_384:
        raise UnsignedOriginalBuildBlocked("public passive ARM64 receipt oversized")
    try:
        proof = json.loads(receipt.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise UnsignedOriginalBuildBlocked("passive ARM64 receipt unreadable") from exc
    local_pc = (allow_local_pc and isinstance(proof, dict)
                and proof.get("schema") == "local-pc-research-passive-shim-v1"
                and proof.get("ndk_version") == "27.2.12479018"
                and isinstance(proof.get("source_tree_sha256"), str)
                and len(proof["source_tree_sha256"]) == 64
                and all(c in "0123456789abcdef" for c in proof["source_tree_sha256"]))
    if not (
        isinstance(proof, dict)
        and (proof.get("schema") == "public-original-research-passive-shim-v1" or local_pc)
        and proof.get("elf_abi") == "arm64-v8a"
        and proof.get("original_save_writer_enabled") is False
        and proof.get("fixed_error_markers_compiled") is True
        and isinstance(proof.get("git_commit"), str)
        and len(proof["git_commit"]) == 40
        and all(ch in "0123456789abcdef" for ch in proof["git_commit"])
        and isinstance(proof.get("sha256"), str)
        and len(proof["sha256"]) == 64
        and hashlib.sha256(native).hexdigest() == proof["sha256"]
        and b"kneekura-original-virgin-save-trial-v1" not in native
    ):
        raise UnsignedOriginalBuildBlocked("passive original research native bytes/receipt differ")
    return proof


def prepare_unsigned_research(
    *, repo: Path, owner_export: Path, passive_shim: Path,
    passive_receipt: Path, official_aar: Path,
    javac: str | None, d8: str | None, android_jar: str | None,
    offline_393_import: bool = False,
    allow_local_pc: bool = False,
) -> tuple[dict, Path]:
    repo = repo.resolve(strict=True)
    private = repo / "private"
    if not private.is_dir() or private.is_symlink():
        raise UnsignedOriginalBuildBlocked("research private working root unavailable")
    if owner_export.is_symlink():
        raise UnsignedOriginalBuildBlocked("owner original export ZIP must not be symlink")
    owner_export = owner_export.resolve(strict=True)
    if not owner_export.is_file():
        raise UnsignedOriginalBuildBlocked("owner original export ZIP missing or symlink")
    passive_shim = _inside_private(repo, passive_shim)
    passive_receipt = _inside_private(repo, passive_receipt)
    official_aar = _inside_private(repo, official_aar)
    native_proof = _source_receipt(passive_shim, passive_receipt, allow_local_pc=allow_local_pc)

    check_original_scene_witness_build_contract(
        flavor="local-research", no_internet=True, shim=passive_shim,
        shadowhook=None, shadowhook_sha256=None, virgin_save_trial=False,
        shadowhook_aar=official_aar,
    )
    with tempfile.TemporaryDirectory(
        dir=private, prefix="unsigned-original-jp1571-working-",
    ) as temp:
        scratch = Path(temp)
        original = scratch / "original-six"
        bootstrapped = scratch / "native-bootstrap"
        paired = scratch / "official-two-native"
        flavored = scratch / "isolated-flavor"
        final = scratch / "unsigned-final"
        bridge = scratch / "classes5.dex"

        source_ledger = extract_owned_splits(owner_export, original)
        bootstrap_ledger = inject_kneekura_shim(
            original, bootstrapped, passive_shim,
        )
        native_ledger = include_reviewed_shadowhook_in_private_split_set(
            bootstrapped, paired, official_aar=official_aar,
        )
        flavor_ledger = apply_package_flavor(
            paired, flavored, flavor="local-research",
            research_native_extraction=False,
        )
        bridge_build = build_bridge_dex(
            flavor="local-research", enabled=False,
            isolate_original_native_files_dir=False,
            virgin_save_trial=False, output=bridge,
            javac=javac, d8=d8, android_jar=android_jar, root=repo,
            offline_import_installpack=(
                original / "split_InstallPack.apk" if offline_393_import else None),
        )
        bridge_ledger = inject_bridge_split_set(
            flavored, final, flavor="local-research",
            bridge_dex_path=bridge, research_deny_internet=True,
        )
        native_gate = verify_staged_original_scene_before_signing(
            final, research_scene_witness=True,
            expected_research_native_package=ISOLATED_PACKAGE,
        )
        static_parity = verify_static_http_bridge(
            original, final, flavor="local-research",
            replay_enabled=False, research_deny_internet=True,
            research_scene_witness=True,
            research_shadowhook_sha256=APPROVED_OFFICIAL_SHADOWHOOK_V201_ARM64_SHA256,
            research_shadowhook_nothing_sha256=APPROVED_OFFICIAL_SHADOWHOOK_V201_COMPANION_SHA256,
        )
        unique = "unsigned-original-native-pair-" + uuid4().hex
        destination = private / unique
        if destination.exists() or destination.is_symlink():
            raise UnsignedOriginalBuildBlocked("owner private unsigned output occupied")
        destination.mkdir(parents=False)
        splits = destination / "original-JP1571-unsigned-six"
        splits.mkdir()
        signed_bytes = {}
        for name in JP_15_7_1_SPLITS:
            staged = splits / name
            shutil.copy2(final / name, staged)
            signed_bytes[name] = hashlib.sha256(staged.read_bytes()).hexdigest()
        # These are NOT signatures: each value is the SHA of one unsigned
        # private original research APK candidate. A later signer must reject
        # mismatches instead of signing stale/mutated intermediate data.
        # Only the exact public compiler receipt and privacy-safe static
        # metadata are copied, no source encrypted APK/SAVE to GitHub.
        local_pc = native_proof["schema"] == "local-pc-research-passive-shim-v1"
        shutil.copy2(passive_receipt, destination / (
            "LOCAL_PC_PASSIVE_SHIM_RECEIPT.json" if local_pc
            else "PUBLIC_PASSIVE_SHIM_RECEIPT.json"))
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "status": "PASS_PRIVATE_UNSIGNED_ORIGINAL_SIX_SPLITS_NOT_INSTALLABLE",
            "original_input_source_verified": bool(source_ledger),
            "original_private_JP_splits": len(JP_15_7_1_SPLITS),
            "original_game_source_executable_text_static_checked": True,
            "official_shadowhook_main_and_companion_verified": bool(native_ledger),
            "original_research_no_INTERNET_manifest_static_checked": True,
            "private_passive_native_shim_sha256": native_proof["sha256"],
            "source_compiler_commit": native_proof["git_commit"],
            "native_source_provenance": "local-pc" if local_pc else "public-ci",
            "unsigned_original_splits_sha256": signed_bytes,
            "exact_original_native_presign_status": native_gate["status"],
            "compiled_original_virgin_SAVE_writer_enabled": False,
            "owner_original_393_file_import_feature_opt_in": offline_393_import,
            "original_native_scene97_accepted": False,
            "original_user_SAVE_read_or_written": False,
            "original_user_APK_source_mutated": False,
            "Android_APK_signed": False,
            "Android_game_installed_or_launched": False,
            "original_gameplay_Lv60_MAX_or_zero_egress_verified": False,
        }
        for name, item in (
            ("original-split-source.json", source_ledger),
            ("native-bootstrap.json", bootstrap_ledger),
            ("native-official-pair.json", native_ledger),
            ("package-flavor.json", flavor_ledger),
            ("bridge-compile.json", bridge_build),
            ("bridge-injection.json", bridge_ledger),
            ("native-presign-proof.json", native_gate),
            ("original-static-parity.json", static_parity),
            ("UNSIGNED-RESEARCH-RECEIPT.json", receipt),
        ):
            (destination / name).write_text(
                json.dumps(item, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
    return receipt, destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--owner-export", required=True, type=Path)
    parser.add_argument("--passive-shim", required=True, type=Path)
    parser.add_argument("--passive-receipt", required=True, type=Path)
    parser.add_argument("--official-aar", required=True, type=Path)
    parser.add_argument("--javac")
    parser.add_argument("--d8")
    parser.add_argument("--android-jar")
    parser.add_argument("--offline-393-import", action="store_true",
                        help="Explicit research-only source import code (UNSIGNED proof only)")
    args = parser.parse_args()
    try:
        receipt, _ = prepare_unsigned_research(
            repo=args.repo, owner_export=args.owner_export,
            passive_shim=args.passive_shim,
            passive_receipt=args.passive_receipt,
            official_aar=args.official_aar,
            javac=args.javac, d8=args.d8, android_jar=args.android_jar,
            offline_393_import=args.offline_393_import,
        )
    except (UnsignedOriginalBuildBlocked, OSError, ValueError) as exc:
        parser.error(str(exc))
    print(receipt["status"])
    print("Private-only unsigned output; do not install or sign without owner approval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
