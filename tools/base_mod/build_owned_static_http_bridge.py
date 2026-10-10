"""Build an owned JP 15.7.1 Frida-free static HTTP bridge split set.

Pipeline:
  exact owner export
  -> inert Kneekura shim bootstrap
  -> package flavor separation
  -> flavor MyActivity subclass + classes5.dex
  -> re-align/re-sign
  -> static bridge parity audit

The optional backup replay is build-time gated. Feature-OFF still uses the
subclass, but every request calls the exact original super.newHttpRequest.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from tools.base_mod.extract_owned_splits import (
    EXPECTED_EXPORT_SHA256,
    extract_owned_splits,
)
from tools.base_mod.inject_shim import patch_split_set as inject_kneekura_shim
from tools.base_mod.package_flavor import (
    FLAVOR_PACKAGES,
    patch_split_set as apply_package_flavor,
)
from tools.base_mod.inject_java_http_bridge import (
    build_bridge_dex,
    inject_bridge_split_set,
)
from tools.base_mod.repack import baseline_resign
from tools.base_mod.original_scene_native_image_gate import (
    verify_staged_original_scene_before_signing,
)
from tools.base_mod.prepare_original_scene_witness import (
    check_original_scene_witness_build_contract,
    include_reviewed_shadowhook_in_private_split_set,
)
from tools.base_mod.verify_static_http_bridge import verify_static_http_bridge


def build_owned_static_http_bridge(
    export_zip: Path,
    *,
    flavor: str,
    shim: Path,
    keystore: Path,
    alias: str,
    storepass: str,
    output_dir: Path,
    enable_backup_offline_replay: bool = False,
    research_isolate_original_native_files_dir: bool = False,
    research_deny_internet: bool = False,
    research_shadowhook_so: Path | None = None,
    research_shadowhook_sha256: str | None = None,
    keypass: str | None = None,
    zipalign: str | None = None,
    apksigner: str | None = None,
    javac: str | None = None,
    d8: str | None = None,
    android_jar: str | None = None,
    root: Path = Path("."),
) -> dict:
    if flavor not in FLAVOR_PACKAGES:
        raise ValueError(f"unknown flavor: {flavor}")
    if flavor == "local-research":
        if (not research_deny_internet or research_isolate_original_native_files_dir
                or enable_backup_offline_replay):
            raise ValueError(
                "local research requires no-INTERNET, original app root and no online backup replay"
            )
    else:
        if research_deny_internet and (
            flavor != "research" or not research_isolate_original_native_files_dir
        ):
            raise ValueError(
                "original no-INTERNET research requires research flavor AND private file root"
            )
        if research_isolate_original_native_files_dir and flavor != "research":
            raise ValueError("original native files research isolation requires research flavor")

    # Validate the optional native observer and exact package BEFORE staging.
    witness_contract = check_original_scene_witness_build_contract(
        flavor=flavor, no_internet=research_deny_internet,
        shim=shim, shadowhook=research_shadowhook_so,
        shadowhook_sha256=research_shadowhook_sha256,
    )
    export_zip = export_zip.resolve()
    shim = shim.resolve()
    keystore = keystore.resolve()
    output_dir = output_dir.resolve()
    root = root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    work = output_dir / ".static-http-work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    original = work / "original-splits"
    bootstrap = work / "bootstrap-splits"
    flavored = work / "flavored-splits"
    scene_paired = work / "reviewed-native-scene-dependency-splits"
    bridged = work / "bridged-splits"
    bridge_dex = work / "kneekura-http-bridge.dex"
    signed = output_dir / f"{flavor}-static-http-signed-splits"
    if signed.exists():
        shutil.rmtree(signed)

    source_ledger = extract_owned_splits(export_zip, original)
    bootstrap_ledger = inject_kneekura_shim(
        original,
        bootstrap,
        shim,
    )
    source_for_flavor = bootstrap
    native_witness_ledger = None
    if research_shadowhook_so is not None:
        native_witness_ledger = include_reviewed_shadowhook_in_private_split_set(
            bootstrap, scene_paired,
            shadowhook=research_shadowhook_so,
            expected_sha256=research_shadowhook_sha256,
        )
        source_for_flavor = scene_paired
    flavor_ledger = apply_package_flavor(
        source_for_flavor,
        flavored,
        flavor=flavor,
        research_native_extraction=False,
    )
    bridge_build = build_bridge_dex(
        flavor=flavor,
        enabled=enable_backup_offline_replay,
        isolate_original_native_files_dir=research_isolate_original_native_files_dir,
        output=bridge_dex,
        javac=javac,
        d8=d8,
        android_jar=android_jar,
        root=root,
    )
    bridge_ledger = inject_bridge_split_set(
        flavored,
        bridged,
        flavor=flavor,
        bridge_dex_path=bridge_dex,
        research_deny_internet=research_deny_internet,
    )

    # Reject a changed JNI VMA / executable mapping in the unsigned
    # ORIGINAL ARM64 binary before accessing private signing credentials.
    # Post-sign parity checks the same invariant independently.
    pre_signature_scene_receipt = verify_staged_original_scene_before_signing(
        bridged,
        research_scene_witness=witness_contract[
            "research_scene_witness_build_enabled"
        ],
    )

    signing_ledger = baseline_resign(
        bridged,
        signed,
        keystore=keystore,
        alias=alias,
        storepass=storepass,
        keypass=keypass,
        zipalign=zipalign,
        apksigner=apksigner,
        source_export_sha256=EXPECTED_EXPORT_SHA256,
    )

    parity = verify_static_http_bridge(
        original,
        signed,
        flavor=flavor,
        replay_enabled=enable_backup_offline_replay,
        research_deny_internet=research_deny_internet,
        research_scene_witness=witness_contract["research_scene_witness_build_enabled"],
        research_shadowhook_sha256=research_shadowhook_sha256,
    )

    ledgers = {
        "source-split-ledger.json": source_ledger,
        "bootstrap-patch-ledger.json": bootstrap_ledger,
        "package-patch-ledger.json": flavor_ledger,
        "http-bridge-build-ledger.json": bridge_build,
        "http-bridge-ledger.json": bridge_ledger,
        "parity-report.json": parity,
    }
    if native_witness_ledger is not None:
        ledgers["original-scene-witness-optional-dependency.json"] = native_witness_ledger
    if pre_signature_scene_receipt is not None:
        ledgers["original-scene-pre-signature-proof.json"] = pre_signature_scene_receipt
    for name, payload in ledgers.items():
        (signed / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    package_name = FLAVOR_PACKAGES[flavor]
    launcher = package_name + ".MyActivity"
    instructions = f"""Kneekura JP 15.7.1 Frida-free static HTTP bridge

Flavor: {flavor}
Package: {package_name}
Launcher: {launcher}
Backup offline replay enabled: {str(enable_backup_offline_replay).lower()}
Original native file root isolation (RESEARCH ONLY): {str(research_isolate_original_native_files_dir).lower()}
Fresh original game local package (NO independent SAVE schema): {str(flavor == "local-research").lower()}
Original scene hook compiled/bundled (research only): {str(witness_contract["research_scene_witness_build_enabled"]).lower()}
Actual native scene run/restart proof: FALSE; no Android scene acceptance established
INTERNET permission removal (RESEARCH ONLY): {str(research_deny_internet).lower()}

This build contains NO Frida Gadget.
The original HTTP fallback, native code and SDK initializers remain.
This file-root/no-INTERNET permission experiment DOES NOT certify an independent
SAVE, original game boot, all IPC/SDK egress, or full zero-network gameplay.

Install every APK together:
  adb install-multiple --no-streaming -r *.apk

Launch:
  adb shell am start -n {package_name}/{launcher}

Behavior contract:
- exact observed backup GET family is locally replayed only when enabled;
- unrecognized requests call super.newHttpRequest unchanged;
- build-time feature OFF calls super.newHttpRequest for every request;
- original MyActivity remains the superclass and original UI/lifecycle host.

Final device smoke should be performed only after repository parity is green.
"""
    (signed / "INSTALL-STATIC-HTTP.txt").write_text(
        instructions,
        encoding="utf-8",
    )

    shutil.rmtree(work)
    return {
        "schema_version": 1,
        "mode": "owned-static-http-bridge",
        "flavor": flavor,
        "package": package_name,
        "launcher": launcher,
        "backup_offline_replay_enabled": enable_backup_offline_replay,
        "research_original_native_files_dir_isolation": research_isolate_original_native_files_dir,
        "research_no_internet_manifest": research_deny_internet,
        "original_native_scene_witness_build_contract": witness_contract,
        "original_research_scene_pre_signature_source_receipt": (
            pre_signature_scene_receipt
        ),
        "original_native_scene_witness_device_runtime_verified": False,
        "original_independent_local_save_verified": False,
        "fresh_local_original_package": flavor == "local-research",
        "original_native_file_root_is_super": flavor == "local-research",
        "local_origin_marker_is_gameplay_save": False,
        "original_zero_network_verified": False,
        "source_export_sha256": EXPECTED_EXPORT_SHA256,
        "signed_split_dir": str(signed),
        "signer_certificate_sha256": signing_ledger[
            "signer_certificate_sha256"
        ],
        "static_parity": parity,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_zip", type=Path)
    parser.add_argument("--flavor", choices=sorted(FLAVOR_PACKAGES), required=True)
    parser.add_argument("--shim", required=True, type=Path)
    parser.add_argument("--keystore", required=True, type=Path)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--storepass", required=True)
    parser.add_argument("--keypass")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--research-shadowhook-so", type=Path,
                        help="Opt-in owned arm64 hook library, ONLY local-research")
    parser.add_argument("--research-shadowhook-sha256",
                        help="Explicit SHA256 of reviewed owner-private libshadowhook.so")
    parser.add_argument("--enable-backup-offline-replay", action="store_true")
    parser.add_argument(
        "--research-isolate-original-native-files-dir",
        action="store_true",
        help="Research only: original Activity.getFilesDir private root; not offline gameplay",
    )
    parser.add_argument(
        "--research-no-internet-permission",
        action="store_true",
        help="Original research host only; requires original native files isolation, NOT product zero-egress",
    )
    parser.add_argument("--zipalign")
    parser.add_argument("--apksigner")
    parser.add_argument("--javac")
    parser.add_argument("--d8")
    parser.add_argument("--android-jar")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    result = build_owned_static_http_bridge(
        args.export_zip,
        flavor=args.flavor,
        shim=args.shim,
        keystore=args.keystore,
        alias=args.alias,
        storepass=args.storepass,
        keypass=args.keypass,
        output_dir=args.output,
        enable_backup_offline_replay=args.enable_backup_offline_replay,
        research_isolate_original_native_files_dir=args.research_isolate_original_native_files_dir,
        research_deny_internet=args.research_no_internet_permission,
        research_shadowhook_so=args.research_shadowhook_so,
        research_shadowhook_sha256=args.research_shadowhook_sha256,
        zipalign=args.zipalign,
        apksigner=args.apksigner,
        javac=args.javac,
        d8=args.d8,
        android_jar=args.android_jar,
        root=args.root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
