"""Read-only offline-egress gap audit for the exact owner JP15.7.1 APK.

IMPORTANT: reports *capability* to send data, not proof that a particular
request was sent or the reason an account/save was restricted. It never
changes APK, save, device, network or signing state.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys
import zipfile

from tools.base_mod.binary_axml import manifest_string_slots

PINNED_EXPORT_SHA256 = (
    "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
)
NO_INDEX = 0xFFFFFFFF
START_ELEMENT = 0x0102
VENDOR_INITIALIZERS = (
    "firebase", "adjust", "applovin", "ironsource", "facebook.ads",
    "google.android.gms.ads", "unity3d.ads", "vungle",
)


def _lookup(index: int, strings: dict[int, str]) -> str | None:
    return strings.get(index)


def manifest_components(payload: bytes) -> dict[str, object]:
    """Decode actual AXML element attributes, not unused string-pool literals."""
    if len(payload) < 36 or struct.unpack_from("<HH", payload, 0) != (3, 8):
        raise ValueError("not a valid Android binary manifest header")
    strings = {item.index: item.value for item in manifest_string_slots(payload)}
    cursor = 8
    permissions: list[str] = []
    sdk_components: list[dict[str, str]] = []
    total_components = 0
    while cursor < len(payload):
        if cursor + 8 > len(payload):
            raise ValueError("truncated Android XML chunk header")
        typ, header_size, chunk_size = struct.unpack_from("<HHI", payload, cursor)
        if chunk_size < 8 or cursor + chunk_size > len(payload):
            raise ValueError("corrupted Android XML chunk size")
        if typ == START_ELEMENT:
            if header_size < 16 or chunk_size < 36:
                raise ValueError("invalid XML start-element chunk")
            name_idx = struct.unpack_from("<I", payload, cursor + 20)[0]
            tag = _lookup(name_idx, strings)
            attr_start, attr_size, attr_count = struct.unpack_from(
                "<HHH", payload, cursor + 24
            )
            if attr_size < 20 or attr_count > 4096:
                raise ValueError("invalid Android XML attributes")
            attrs: dict[str, str] = {}
            for number in range(attr_count):
                loc = cursor + 16 + attr_start + number * attr_size
                if loc < cursor + 16 or loc + 20 > cursor + chunk_size:
                    raise ValueError("attribute outside XML chunk")
                _, field_idx, raw_idx = struct.unpack_from("<III", payload, loc)
                _, _, data_type, data_value = struct.unpack_from(
                    "<HBBI", payload, loc + 12
                )
                field = _lookup(field_idx, strings)
                if field is None:
                    continue
                if raw_idx != NO_INDEX:
                    text = _lookup(raw_idx, strings)
                elif data_type == 3:
                    text = _lookup(data_value, strings)
                else:
                    text = None
                if text is not None:
                    attrs[field] = text
            if tag is not None and tag.startswith("uses-permission"):
                declared = attrs.get("name")
                if declared:
                    permissions.append(declared)
            if tag in {"provider", "service", "receiver", "activity"}:
                total_components += 1
                class_name = attrs.get("name", "")
                if any(v in class_name.casefold() for v in VENDOR_INITIALIZERS):
                    sdk_components.append({"kind": tag, "class_name": class_name})
        cursor += chunk_size
    return {
        "declared_permissions": sorted(set(permissions)),
        "sdk_components": sorted(sdk_components, key=lambda x: (
            x["kind"], x["class_name"]
        )),
        "android_component_count": total_components,
    }


def inspect_bridge(source: str) -> dict[str, object]:
    """An unknown-call fallback to super is NOT an offline guarantee."""
    raw_super_count = len(re.findall(r"\bsuper\.newHttpRequest\s*\(", source))
    uses_original_subclass = (
        "extends jp.co.ponos.battlecats.MyActivity" in source
    )
    return {
        "inherits_original_http_transport": uses_original_subclass,
        "original_http_super_call_sites": raw_super_count,
        "original_http_fallthrough_possible": (
            uses_original_subclass and raw_super_count > 0
        ),
    }


def audit(apk_blob: bytes, bridge_source: str) -> dict[str, object]:
    with zipfile.ZipFile(io.BytesIO(apk_blob)) as apk:
        info = apk.getinfo("AndroidManifest.xml")
        if info.file_size > 5 * 1024 * 1024:
            raise ValueError("abnormally large AndroidManifest.xml")
        manifest = manifest_components(apk.read(info))
    bridge = inspect_bridge(bridge_source)
    permissions = manifest["declared_permissions"]
    sdk = manifest["sdk_components"]
    evidence = {
        "internet_permission_declared": "android.permission.INTERNET" in permissions,
        "network_state_permission_declared":
            "android.permission.ACCESS_NETWORK_STATE" in permissions,
        "original_http_transport_reachable": bridge["original_http_fallthrough_possible"],
        "bundled_third_party_component_count": len(sdk),
    }
    reasons = []
    if evidence["internet_permission_declared"]:
        reasons.append("ANDROID_INTERNET_PERMISSION_PRESENT")
    if evidence["original_http_transport_reachable"]:
        reasons.append("UNKNOWN_HTTP_REQUESTS_FALL_THROUGH_TO_ORIGINAL")
    if sdk:
        reasons.append("THIRD_PARTY_SDK_COMPONENTS_REQUIRE_SEPARATE_NETWORK_AUDIT")
    return {
        "schema_version": 1,
        "mode": "offline-egress-capability-audit",
        "result": "OFFLINE_NOT_PROVEN" if reasons else "STATIC_GAPS_NOT_FOUND_RUNTIME_PROOF_REQUIRED",
        "capability_findings": evidence,
        "manifest": manifest,
        "http_bridge": bridge,
        "gaps": reasons,
        "network_transfer_observed": None,
        "save_restriction_cause_confirmed": None,
        "no_network_release_certified": False,
        "limitations": [
            "Manifest or SDK presence is not evidence of actual traffic.",
            "Absence of this static evidence does not establish zero network egress.",
            "Original native code, Android IPC and other library transports need auditing.",
            "Zero actual network egress must be proven on an offline/isolated device.",
            "A blocked save may result from local validation or remote enforcement.",
        ],
    }


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--owner-export", type=Path)
    group.add_argument("--base-apk", type=Path)
    p.add_argument("--bridge", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--report-only", action="store_true",
                   help="Save findings and return 0 even with an offline gap")
    args = p.parse_args(argv)
    try:
        if args.owner_export is not None:
            if _sha_file(args.owner_export) != PINNED_EXPORT_SHA256:
                raise ValueError("not the pinned owner JP15.7.1 source archive")
            with zipfile.ZipFile(args.owner_export) as outer:
                data = outer.read("apk/base.apk")
        else:
            data = args.base_apk.read_bytes()
        result = audit(data, args.bridge.read_text(encoding="utf-8"))
        result["examined_base_apk_sha256"] = hashlib.sha256(data).hexdigest()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        p.error(str(exc))
    print(json.dumps({
        "status": result["result"],
        "gaps": result["gaps"],
        "report": str(args.output),
    }, ensure_ascii=False))
    # Fail safe as a release check; use report-only only for research.
    return 0 if args.report_only else 2


if __name__ == "__main__":
    sys.exit(main())
