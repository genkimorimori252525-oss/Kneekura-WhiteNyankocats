"""Audit the repository-side Phase-C research preflight.

This command never touches an APK. It verifies that the exact-version evidence,
research-only package identity, trace harness, and data-first prototype gates all
agree before an owner-local device trace is attempted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


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
EXPECTED_RESEARCH_PACKAGE = "jp.kn.trace.battlecats"
EXPECTED_COMEBACK_TEMPLATE = 949
EXPECTED_COMEBACK_CYCLE = 7
EXPECTED_R1_SEED_COUNT = 495


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
    gacha = _read_json(
        root / "docs/evidence/super-kneekura-gacha-foundation-jp15.7.1.json"
    )

    failures: list[str] = []

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
        "status": "ready_for_owner_device_observation",
        "anchor": {
            "native_sha256": EXPECTED_NATIVE_SHA256,
            "native_build_id": EXPECTED_NATIVE_BUILD_ID,
            "base_apk_sha256": EXPECTED_BASE_APK_SHA256,
            "new_http_request_insns_sha256": EXPECTED_HTTP_METHOD_HASH,
        },
        "research_package": EXPECTED_RESEARCH_PACKAGE,
        "preferred_http_seam": "MyActivity.newHttpRequest",
        "comeback_template_id": EXPECTED_COMEBACK_TEMPLATE,
        "comeback_cycle_length": EXPECTED_COMEBACK_CYCLE,
        "local_r1_seed_count": EXPECTED_R1_SEED_COUNT,
        "rarity_rate_vector": "unresolved-by-design",
        "trace_mode": "call-through-observation-only",
        "shipping_frida_allowed": False,
        "next_gate": (
            "owner-device normal/airplane-mode trace of one original request "
            "lifecycle before any selective local HTTP patch is enabled"
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
