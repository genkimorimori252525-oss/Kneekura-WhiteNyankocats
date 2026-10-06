"""Audit the repository-side Phase-C research preflight.

This command never touches an APK. It verifies that the exact-version evidence,
research-only package identity, trace harness, promoted static HTTP bridge,
original login/gacha anchors, and data-first prototype gates all agree before
the first original-UI data proof is attempted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.base_mod.super_gacha_data_prototype import (
    R1,
    R2,
    R3,
    OPTION,
    build_replacements,
)


EXPECTED_NATIVE_SHA256 = (
    "333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2"
)
EXPECTED_NATIVE_BUILD_ID = "8cb3815648eb9642da10bfb039d71bff7a3519bd"
EXPECTED_BASE_APK_SHA256 = (
    "60e5e9df891b7be487abc4590fb3ca2e98218225efedbe4ba26b39dc10ce5c9a"
)
EXPECTED_HTTP_METHOD_HASH = (
    "14f896e5b42b8e5b8ab50f756bdc79ad44614325eb153ab99ffcdafb98c70a80"
)
EXPECTED_LA32_RUN_HASH = (
    "b1a8679be3ccf9deadf5a5ef6eca2730220c4414ef08064e12b3f1220ef547e7"
)
EXPECTED_LZ22_RUN_HASH = (
    "ad74dcde42dcfa2533de3f57b1b86a04d46326ce5c2c90ac46b4db3c9a669d7a"
)
EXPECTED_LZ22_FALLBACK_HASH = (
    "b03f69b5a8187bee470b7fdbcee8416e3a01b667f080f37a2042786e3efd1abe"
)
EXPECTED_RESEARCH_PACKAGE = "jp.kn.trace.battlecats"
EXPECTED_COMEBACK_TEMPLATE = 949
EXPECTED_COMEBACK_CYCLE = 7
EXPECTED_R1_SEED_COUNT = 495


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))



def _audit_tiny_gacha_prototype() -> dict:
    r1 = b"30,31,-1\n40,41,42,-1\n"
    r2 = b"-1\n-1\n"
    r3 = b"-1\n-1\n"
    option = (
        b"GatyaSetID\tBannerON_OFF\tItemID_Ticket\tanimeID\tbtnCutID\t"
        b"seriesID\tmenuCutID\tCharaID\twaitmaanimON_OFF\timgID\n"
        b"0\t0\t21\t0\t0\t0\t1\t-1\t0\t-1\n"
        b"1\t1\t21\t0\t0\t1\t1\t-1\t0\t-1\n"
    )
    replacements, ledger = build_replacements(
        r1,
        r2,
        r3,
        option,
        clone_option_set=1,
        unit_ids=[30, 42],
        banner_on=1,
    )
    if ledger.get("new_set_id") != 2:
        raise ValueError("tiny gacha prototype set-id drift")
    if ledger.get("original_rows_replaced") is not False:
        raise ValueError("tiny gacha prototype is no longer append-only")
    if ledger.get("rarity_probability_vector_defined") is not False:
        raise ValueError("tiny gacha prototype invented a rate vector")
    if not replacements[R1].startswith(r1):
        raise ValueError("tiny gacha prototype replaced original R1 rows")
    if not replacements[R2].startswith(r2) or not replacements[R3].startswith(r3):
        raise ValueError("tiny gacha prototype replaced original R2/R3 rows")
    if not replacements[OPTION].startswith(option):
        raise ValueError("tiny gacha prototype replaced original option rows")
    return ledger


def audit(root: Path) -> dict:
    root = root.resolve()

    native_map = _read_json(
        root / "docs/references/native-service-map-jp15.7.1.json"
    )
    http = _read_json(
        root / "docs/evidence/myactivity-http-transport-jp15.7.1.json"
    )
    login = _read_json(
        root / "docs/evidence/login-bonus-foundation-jp15.7.1.json"
    )
    runtime_anchors = _read_json(
        root / "docs/evidence/original-login-gacha-runtime-anchors-jp15.7.1.json"
    )
    gacha = _read_json(
        root / "docs/evidence/super-kneekura-gacha-foundation-jp15.7.1.json"
    )

    failures: list[str] = []

    try:
        prototype_runtime = _audit_tiny_gacha_prototype()
    except ValueError as exc:
        failures.append(str(exc))
        prototype_runtime = {}

    anchor = native_map.get("anchor", {})
    if anchor.get("native_sha256") != EXPECTED_NATIVE_SHA256:
        failures.append("native SHA drift")
    if anchor.get("native_build_id") != EXPECTED_NATIVE_BUILD_ID:
        failures.append("native build-id drift")

    http_anchor = http.get("anchor", {})
    if http_anchor.get("base_apk_sha256") != EXPECTED_BASE_APK_SHA256:
        failures.append("base.apk SHA drift")
    new_http = http.get("methods", {}).get("MyActivity.newHttpRequest", {})
    if new_http.get("insns_sha256") != EXPECTED_HTTP_METHOD_HASH:
        failures.append("newHttpRequest instruction hash drift")
    if http.get("methods", {}).get("La32.run", {}).get(
        "insns_sha256"
    ) != EXPECTED_LA32_RUN_HASH:
        failures.append("La32.run instruction hash drift")
    if http.get("methods", {}).get("Lz22.run", {}).get(
        "insns_sha256"
    ) != EXPECTED_LZ22_RUN_HASH:
        failures.append("Lz22.run instruction hash drift")
    if http.get("methods", {}).get("Lz22.a", {}).get(
        "insns_sha256"
    ) != EXPECTED_LZ22_FALLBACK_HASH:
        failures.append("Lz22.a instruction hash drift")
    if http.get("conclusion", {}).get("preferred_hook_boundary") != (
        "MyActivity.newHttpRequest"
    ):
        failures.append("preferred HTTP seam drift")

    comeback = login.get("comeback_template", {})
    if comeback.get("event_id") != EXPECTED_COMEBACK_TEMPLATE:
        failures.append("comeback template drift")
    if comeback.get("day_count") != EXPECTED_COMEBACK_CYCLE:
        failures.append("comeback cycle drift")

    rare = gacha.get("rare_dataset", {})
    if rare.get("r1_unique_unit_count") != EXPECTED_R1_SEED_COUNT:
        failures.append("local R1 seed count drift")
    if gacha.get("rate_status", {}).get(
        "exact_standard_rare_capsule_rate_vector"
    ) != "not yet proven":
        failures.append("rarity-rate evidence gate was bypassed")

    if not runtime_anchors.get("login_update_rtti"):
        failures.append("login runtime RTTI anchors missing")
    gacha_loader = runtime_anchors.get("gacha_dataset_loader_region", {})
    if gacha_loader.get("observed_prologue") != "0x5ed65c":
        failures.append("gacha dataset loader anchor drift")

    package_flavor = (
        root / "tools/base_mod/package_flavor.py"
    ).read_text(encoding="utf-8")
    if EXPECTED_RESEARCH_PACKAGE not in package_flavor:
        failures.append("research package id missing")

    trace = (
        root / "research/frida/trace_service_bridge.js"
    ).read_text(encoding="utf-8")
    if "KNEEKURA_TRACE " not in trace:
        failures.append("sanitized trace marker missing")
    if "overload.call(receiver, ...originalArgs)" not in trace:
        failures.append("trace no longer calls original implementation")

    summarizer = (
        root / "tools/base_mod/summarize_service_trace.py"
    ).read_text(encoding="utf-8")
    for token in (
        "request_observations",
        "network_results",
        "response_details",
        "response_lifecycles",
    ):
        if token not in summarizer:
            failures.append(f"trace summarizer missing {token}")

    static_bridge = (
        root / "bridge/java/MyActivity.java.in"
    ).read_text(encoding="utf-8")
    for token in (
        "extends jp.co.ponos.battlecats.MyActivity",
        "super.newHttpRequest(",
        "nyanko-backups.ponosgames.com",
        "MyActivity.newResponse(",
    ):
        if token not in static_bridge:
            failures.append(f"static bridge contract missing {token}")

    prototype = (
        root / "tools/base_mod/super_gacha_data_prototype.py"
    ).read_text(encoding="utf-8")
    for token in (
        "new_set_id = len(r1_lines)",
        "EXPLICIT_EXCLUDED_UNIT_IDS = {673}",
        "all_units_present_in_exact_local_r1_union",
        "original_rows_replaced",
        "rarity_probability_vector_defined",
    ):
        if token not in prototype:
            failures.append(f"tiny gacha prototype gate missing {token}")

    required_tools = [
        "tools/base_mod/build_owned_research_trace.py",
        "tools/base_mod/inject_research_gadget.py",
        "tools/base_mod/verify_research_trace.py",
        "tools/base_mod/summarize_service_trace.py",
        "tools/base_mod/dex_methods.py",
        "tools/base_mod/dex_code_refs.py",
        "tools/base_mod/arm64_string_xrefs.py",
        "tools/base_mod/battlecats_pack_writer.py",
        "tools/base_mod/patch_installpack_data.py",
        "tools/base_mod/super_gacha_data_prototype.py",
        "tools/base_mod/build_owned_static_http_bridge.py",
        "tools/base_mod/verify_static_http_bridge.py",
        "tools/base_mod/run_static_http_smoke.ps1",
        "tools/base_mod/build_owned_gacha_ui_proof.py",
        "tools/base_mod/verify_gacha_ui_data_proof.py",
        "bridge/java/MyActivity.java.in",
        "docs/architecture/phase-c-static-http-bridge.md",
        "docs/architecture/phase-c-research-preflight.md",
        "docs/architecture/phase-c-gacha-original-ui-proof.md",
    ]
    missing_tools = [
        relative for relative in required_tools if not (root / relative).is_file()
    ]
    if missing_tools:
        failures.append("missing tools: " + ", ".join(missing_tools))

    if failures:
        raise ValueError("Phase-C preflight failed: " + "; ".join(failures))

    return {
        "schema_version": 1,
        "status": "ready_for_original_ui_data_proof",
        "anchor": {
            "native_sha256": EXPECTED_NATIVE_SHA256,
            "native_build_id": EXPECTED_NATIVE_BUILD_ID,
            "base_apk_sha256": EXPECTED_BASE_APK_SHA256,
            "new_http_request_insns_sha256": EXPECTED_HTTP_METHOD_HASH,
            "la32_run_insns_sha256": EXPECTED_LA32_RUN_HASH,
            "lz22_run_insns_sha256": EXPECTED_LZ22_RUN_HASH,
            "lz22_fallback_insns_sha256": EXPECTED_LZ22_FALLBACK_HASH,
        },
        "research_package": EXPECTED_RESEARCH_PACKAGE,
        "preferred_http_seam": "MyActivity.newHttpRequest",
        "comeback_template_id": EXPECTED_COMEBACK_TEMPLATE,
        "comeback_cycle_length": EXPECTED_COMEBACK_CYCLE,
        "local_r1_seed_count": EXPECTED_R1_SEED_COUNT,
        "rarity_rate_vector": "unresolved-by-design",
        "trace_mode": "call-through-observation-only",
        "shipping_frida_allowed": False,
        "static_http_bridge": {
            "implemented": True,
            "frida_free": True,
            "unknown_request_fallthrough": "super.newHttpRequest",
            "first_local_family": "https://nyanko-backups.ponosgames.com/",
        },
        "runtime_anchor_sets": {
            "login": True,
            "gacha_dataset_loader": "0x5ed65c",
        },
        "tiny_gacha_prototype": {
            "append_only": prototype_runtime.get("original_rows_replaced") is False,
            "synthetic_new_set_id": prototype_runtime.get("new_set_id"),
            "synthetic_pool_size": prototype_runtime.get("prototype_pool_size"),
            "local_r1_membership_required": True,
            "explicit_excluded_unit_ids": [673],
            "rarity_probability_vector_defined": prototype_runtime.get(
                "rarity_probability_vector_defined"
            ),
        },
        "original_ui_gacha_proof": {
            "target_set_id": 1089,
            "changed_datalocal_entries": [
                "GatyaDataSetR1.csv",
                "GatyaDataSetR2.csv",
                "GatyaDataSetR3.csv",
                "GatyaData_Option_SetR.tsv",
            ],
            "original_scene_code_modified": False,
            "visibility_schedule_defined": False,
        },
        "next_gate": (
            "build the exact owner-data set-1089 proof and ask the unchanged "
            "original Rare Gacha scene whether an additional local visibility "
            "schedule provider is required"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = audit(args.root)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
