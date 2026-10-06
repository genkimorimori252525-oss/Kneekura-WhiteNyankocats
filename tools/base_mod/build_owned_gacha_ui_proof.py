"""Build the first original-UI Super Kneekura gacha data proof.

Pipeline:
  exact owner JP 15.7.1 export
  -> append deterministic tiny Rare Gacha set 1089 in original DataLocal format
  -> preserve every other DataLocal payload byte-for-byte
  -> inert Kneekura shim bootstrap
  -> isolated research package
  -> Frida-free MyActivity static HTTP bridge
  -> re-align/re-sign
  -> static/data preservation audit

This is still a proof build. It deliberately does not invent a rarity
probability vector or replace any original gacha/capsule/result scene code.
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
from tools.base_mod.patch_installpack_data import patch_split_set as patch_datalocal
from tools.base_mod.repack import baseline_resign
from tools.base_mod.super_gacha_data_prototype import (
    OPTION,
    R1,
    R2,
    R3,
    build_from_export,
)
from tools.base_mod.verify_static_http_bridge import verify_static_http_bridge
from tools.base_mod.verify_gacha_ui_data_proof import verify_gacha_ui_data_proof


EXPECTED_NEW_SET_ID = 1089
EXPECTED_PROOF_UNITS = [37, 30, 34]
EXPECTED_CLONE_OPTION_SET = 49
PROOF_POOL_SIZE = 3


def build_owned_gacha_ui_proof(
    export_zip: Path,
    *,
    shim: Path,
    keystore: Path,
    alias: str,
    storepass: str,
    output_dir: Path,
    flavor: str = "research",
    enable_backup_offline_replay: bool = True,
    keypass: str | None = None,
    zipalign: str | None = None,
    apksigner: str | None = None,
    javac: str | None = None,
    d8: str | None = None,
    android_jar: str | None = None,
    root: Path = Path("."),
) -> dict:
    if flavor not in FLAVOR_PACKAGES:
        raise ValueError(f"unknown flavor: {flavor!r}")

    export_zip = export_zip.resolve()
    shim = shim.resolve()
    keystore = keystore.resolve()
    output_dir = output_dir.resolve()
    root = root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    work = output_dir / ".gacha-ui-proof-work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    original = work / "original-splits"
    prototype_plain = work / "prototype-plain"
    datalocal = work / "datalocal-splits"
    bootstrap = work / "bootstrap-splits"
    flavored = work / "flavored-splits"
    bridged = work / "bridged-splits"
    bridge_dex = work / "kneekura-http-bridge.dex"
    signed = output_dir / f"{flavor}-gacha-ui-proof-signed-splits"
    if signed.exists():
        shutil.rmtree(signed)

    source_ledger = extract_owned_splits(export_zip, original)

    prototype_ledger = build_from_export(
        export_zip,
        prototype_plain,
        clone_option_set=None,
        unit_ids=None,
        banner_on=1,
        auto_pool_size=PROOF_POOL_SIZE,
    )
    if prototype_ledger.get("new_set_id") != EXPECTED_NEW_SET_ID:
        raise ValueError(
            "exact JP 15.7.1 gacha row-count drift: "
            f"expected appended set {EXPECTED_NEW_SET_ID}, got "
            f"{prototype_ledger.get('new_set_id')}"
        )
    if prototype_ledger.get("prototype_pool_size") != PROOF_POOL_SIZE:
        raise ValueError("tiny proof pool size drift")
    if prototype_ledger.get("prototype_unit_ids") != EXPECTED_PROOF_UNITS:
        raise ValueError(
            "exact JP 15.7.1 deterministic proof-unit selection drift: "
            f"{prototype_ledger.get('prototype_unit_ids')}"
        )
    if prototype_ledger.get("clone_option_set") != EXPECTED_CLONE_OPTION_SET:
        raise ValueError(
            "exact JP 15.7.1 visible option clone drift: "
            f"{prototype_ledger.get('clone_option_set')}"
        )
    if prototype_ledger.get("original_rows_replaced") is not False:
        raise ValueError("prototype is no longer append-only")
    if prototype_ledger.get("rarity_probability_vector_defined") is not False:
        raise ValueError("prototype invented a rarity probability vector")
    if prototype_ledger.get("banner_on_override") != 1:
        raise ValueError("proof banner is not marked on")

    replacements = {
        name: (prototype_plain / name).read_bytes()
        for name in (R1, R2, R3, OPTION)
    }
    datalocal_ledger = patch_datalocal(
        original,
        datalocal,
        replacements,
    )
    if datalocal_ledger.get("changed_datalocal_entries") != sorted(replacements):
        raise ValueError("DataLocal proof mutation surface drift")

    bootstrap_ledger = inject_kneekura_shim(
        datalocal,
        bootstrap,
        shim,
    )
    flavor_ledger = apply_package_flavor(
        bootstrap,
        flavored,
        flavor=flavor,
        research_native_extraction=False,
    )

    research_external_files_dir = flavor == "research"
    bridge_build = build_bridge_dex(
        flavor=flavor,
        enabled=enable_backup_offline_replay,
        output=bridge_dex,
        javac=javac,
        d8=d8,
        android_jar=android_jar,
        root=root,
        use_external_files_dir=research_external_files_dir,
    )
    bridge_ledger = inject_bridge_split_set(
        flavored,
        bridged,
        flavor=flavor,
        bridge_dex_path=bridge_dex,
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

    static_parity = verify_static_http_bridge(
        original,
        signed,
        flavor=flavor,
        replay_enabled=enable_backup_offline_replay,
        allow_datalocal_patch=True,
    )
    data_proof = verify_gacha_ui_data_proof(
        original,
        signed,
        expected_units=prototype_ledger["prototype_unit_ids"],
        clone_option_set=prototype_ledger["clone_option_set"],
        expected_set_id=EXPECTED_NEW_SET_ID,
    )

    proof = {
        "schema_version": 1,
        "mode": "original-ui-super-kneekura-gacha-proof",
        "anchor": "jp-15.7.1",
        "flavor": flavor,
        "package": FLAVOR_PACKAGES[flavor],
        "new_set_id": EXPECTED_NEW_SET_ID,
        "prototype_unit_ids": prototype_ledger["prototype_unit_ids"],
        "prototype_pool_size": PROOF_POOL_SIZE,
        "clone_option_set": prototype_ledger["clone_option_set"],
        "banner_on": True,
        "original_rows_replaced": False,
        "rarity_probability_vector_defined": False,
        "visibility_schedule_defined": False,
        "original_gacha_scene_code_modified": False,
        "original_capsule_result_code_modified": False,
        "changed_datalocal_entries": sorted(replacements),
        "data_rows_verified_append_only": data_proof["original_rows_preserved"],
        "option_metadata_cloned": data_proof["option_metadata_cloned"],
        "frida_absent": static_parity["frida_absent"],
        "unknown_request_super_fallthrough": static_parity[
            "unknown_request_super_fallthrough"
        ],
        "research_external_files_dir": research_external_files_dir,
        "warning": (
            "Set 1089 is structurally loadable and BannerON in the original "
            "Rare Gacha dataset format. A live/server-style visibility schedule "
            "is deliberately not invented here; original-scene visibility and "
            "draw/acquisition behavior remain the next runtime proof."
        ),
    }

    ledgers = {
        "source-split-ledger.json": source_ledger,
        "super-kneekura-prototype-ledger.json": prototype_ledger,
        "datalocal-patch-ledger.json": datalocal_ledger,
        "bootstrap-patch-ledger.json": bootstrap_ledger,
        "package-patch-ledger.json": flavor_ledger,
        "http-bridge-build-ledger.json": bridge_build,
        "http-bridge-ledger.json": bridge_ledger,
        "parity-report.json": static_parity,
        "gacha-data-proof-report.json": data_proof,
        "gacha-ui-proof-ledger.json": proof,
    }
    for name, payload in ledgers.items():
        (signed / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    launcher = FLAVOR_PACKAGES[flavor] + ".MyActivity"
    (signed / "INSTALL-GACHA-UI-PROOF.txt").write_text(
        f"""Kneekura JP 15.7.1 original-UI gacha proof

Package: {FLAVOR_PACKAGES[flavor]}
Launcher: {launcher}
Appended Rare Gacha set: {EXPECTED_NEW_SET_ID}
Tiny pool: {prototype_ledger["prototype_unit_ids"]}
Cloned visible option set: {prototype_ledger["clone_option_set"]}

Preservation contract:
- original gacha/capsule/result scene code is not replaced;
- only four original-format Rare Gacha DataLocal entries are changed;
- all existing rows remain intact and set 1089 is appended;
- BannerON is 1 by cloning an existing BannerON row;
- no rarity-rate vector or server visibility schedule is invented;
- Frida is absent;
- unknown HTTP requests still call the exact original transport;
- research flavor only redirects getFilesDir() to its app-specific external
  files directory so verified owner-local server assets can be preseeded over
  ADB without root. Personal/Practice shipping builds do not use this override.

This build proves the version-pinned data/scene boundary. Runtime visibility of
set 1089 remains a separate proof because the live event schedule contract has
not been fabricated.
""",
        encoding="utf-8",
    )

    shutil.rmtree(work)
    return {
        **proof,
        "signed_split_dir": str(signed),
        "signer_certificate_sha256": signing_ledger[
            "signer_certificate_sha256"
        ],
        "static_parity": static_parity,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_zip", type=Path)
    parser.add_argument("--shim", required=True, type=Path)
    parser.add_argument("--keystore", required=True, type=Path)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--storepass", required=True)
    parser.add_argument("--keypass")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--flavor",
        choices=sorted(FLAVOR_PACKAGES),
        default="research",
    )
    parser.add_argument(
        "--disable-backup-offline-replay",
        action="store_true",
    )
    parser.add_argument("--zipalign")
    parser.add_argument("--apksigner")
    parser.add_argument("--javac")
    parser.add_argument("--d8")
    parser.add_argument("--android-jar")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    result = build_owned_gacha_ui_proof(
        args.export_zip,
        shim=args.shim,
        keystore=args.keystore,
        alias=args.alias,
        storepass=args.storepass,
        keypass=args.keypass,
        output_dir=args.output,
        flavor=args.flavor,
        enable_backup_offline_replay=not args.disable_backup_offline_replay,
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
