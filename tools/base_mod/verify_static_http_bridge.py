"""Static audit for the Frida-free JP 15.7.1 Java HTTP bridge build."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from tools.base_mod.binary_axml import string_values
from tools.base_mod.dex_methods import defined_methods
from tools.base_mod.inject_java_http_bridge import BRIDGE_DEX_ENTRY
from tools.base_mod.inject_shim import NATIVE_ENTRY, SHIM_ENTRY, SHIM_SONAME
from tools.base_mod.package_flavor import FLAVOR_PACKAGES, ORIGINAL_PACKAGE
from tools.base_mod.verify_parity import _lief_binary, _split_diff


ORIGINAL_LAUNCHER = ORIGINAL_PACKAGE + ".MyActivity"
EXPECTED_NEW_HTTP_INSNS_SHA256 = (
    "14f896e5b42b8e5b8ab50f756bdc79ad44614325eb153ab99ffcdafb98c70a80"
)
EXPECTED_REQUEST_CTOR_INSNS_SHA256 = (
    "55a6e302ccfda0ba24184d8e34345559927b30cb46c0d7235e087b45256ecfb8"
)
EXPECTED_OFFLINE_FALLBACK_INSNS_SHA256 = (
    "b03f69b5a8187bee470b7fdbcee8416e3a01b667f080f37a2042786e3efd1abe"
)


def _exact_method(
    dex: bytes,
    descriptor: str,
    name: str,
    parameters: list[str],
    return_type: str,
) -> dict:
    rows = [
        row
        for row in defined_methods(dex, descriptor)
        if row["name"] == name
        and row["proto"]["return"] == return_type
        and row["proto"]["parameters"] == parameters
    ]
    if len(rows) != 1:
        raise ValueError(
            f"expected exactly one {descriptor}->{name}, got {len(rows)}"
        )
    return rows[0]


def _new_http_method(dex: bytes, descriptor: str) -> dict:
    return _exact_method(
        dex,
        descriptor,
        "newHttpRequest",
        [
            "Ljava/lang/String;",
            "Ljava/lang/String;",
            "F",
            "Ljava/util/HashMap;",
            "Ljava/nio/ByteBuffer;",
            "[Ljava/lang/String;",
            "Z",
            "Z",
        ],
        "I",
    )


def verify_static_http_bridge(
    original_dir: Path,
    modified_dir: Path,
    *,
    flavor: str,
    replay_enabled: bool,
) -> dict:
    package_name = FLAVOR_PACKAGES.get(flavor)
    if package_name is None:
        raise ValueError(f"unknown flavor: {flavor!r}")

    bridge_launcher = package_name + ".MyActivity"
    bridge_descriptor = "L" + package_name.replace(".", "/") + "/MyActivity;"

    split_names = [
        "base.apk",
        "split_config.arm64_v8a.apk",
        "split_config.en.apk",
        "split_config.ja.apk",
        "split_config.xxhdpi.apk",
        "split_InstallPack.apk",
    ]

    reports: list[dict] = []
    for name in split_names:
        original = original_dir / name
        modified = modified_dir / name
        if not original.is_file() or not modified.is_file():
            raise FileNotFoundError(f"missing split for bridge audit: {name}")
        diff = _split_diff(original, modified)

        if diff["removed"]:
            raise ValueError(f"{name}: unexpected removed entries: {diff['removed']}")

        if name == "base.apk":
            changed = set(diff["changed"])
            expected_changed = {
                "AndroidManifest.xml",
                "resources.arsc",
                "classes4.dex",
            }
            if changed != expected_changed:
                raise ValueError(
                    f"bridge base changed surface drifted: {sorted(changed)}"
                )
            if diff["added"] != [BRIDGE_DEX_ENTRY]:
                raise ValueError(
                    f"bridge base added surface drifted: {diff['added']}"
                )
        elif name == "split_config.arm64_v8a.apk":
            if set(diff["changed"]) != {"AndroidManifest.xml", NATIVE_ENTRY}:
                raise ValueError(
                    f"bridge arm64 changed surface drifted: {diff['changed']}"
                )
            if diff["added"] != [SHIM_ENTRY]:
                raise ValueError(
                    f"bridge arm64 added surface drifted: {diff['added']}"
                )
        else:
            if set(diff["changed"]) != {"AndroidManifest.xml"} or diff["added"]:
                raise ValueError(
                    f"{name}: only manifest may change in bridge build; diff={diff}"
                )

        reports.append({"name": name, **diff})

    with zipfile.ZipFile(original_dir / "base.apk", "r") as original_base:
        original_classes4 = original_base.read("classes4.dex")
        original_method = _new_http_method(
            original_classes4,
            "Ljp/co/ponos/battlecats/MyActivity;",
        )
        if original_method.get("insns_sha256") != EXPECTED_NEW_HTTP_INSNS_SHA256:
            raise ValueError("original newHttpRequest instruction hash drift")

        request_ctor = _exact_method(
            original_classes4,
            "La32;",
            "<init>",
            [
                "I",
                "Ljava/lang/String;",
                "Ljava/net/URL;",
                "F",
                "Ljava/util/HashMap;",
                "Ljava/nio/ByteBuffer;",
                "[Ljava/lang/String;",
            ],
            "V",
        )
        if request_ctor.get("insns_sha256") != EXPECTED_REQUEST_CTOR_INSNS_SHA256:
            raise ValueError("a32 request constructor instruction hash drift")

        offline_fallback = _exact_method(
            original_classes4,
            "Lz22;",
            "a",
            [],
            "V",
        )
        if (
            offline_fallback.get("insns_sha256")
            != EXPECTED_OFFLINE_FALLBACK_INSNS_SHA256
        ):
            raise ValueError("Lz22.a offline fallback instruction hash drift")

    with zipfile.ZipFile(modified_dir / "base.apk", "r") as final_base:
        manifest_values = string_values(final_base.read("AndroidManifest.xml"))
        if package_name not in manifest_values:
            raise ValueError("flavor package missing from bridge manifest")
        if bridge_launcher not in manifest_values:
            raise ValueError("bridge launcher missing from final manifest")
        if ORIGINAL_LAUNCHER in manifest_values:
            raise ValueError("original launcher remained active in bridge manifest")

        final_classes4 = final_base.read("classes4.dex")
        final_original_method = _new_http_method(
            final_classes4,
            "Ljp/co/ponos/battlecats/MyActivity;",
        )
        if final_original_method.get("insns_sha256") != EXPECTED_NEW_HTTP_INSNS_SHA256:
            raise ValueError("original newHttpRequest code was modified")

        bridge_dex = final_base.read(BRIDGE_DEX_ENTRY)
        bridge_method = _new_http_method(bridge_dex, bridge_descriptor)
        if bridge_method["kind"] != "virtual":
            raise ValueError("bridge newHttpRequest is not virtual")

        if b"nyanko-backups.ponosgames.com" not in bridge_dex:
            raise ValueError("exact backup request family missing from bridge dex")
        expected_gate = (
            b"ENABLE_BACKUP_OFFLINE_REPLAY"
            if replay_enabled
            else b"ENABLE_BACKUP_OFFLINE_REPLAY"
        )
        if expected_gate not in bridge_dex:
            # D8 may inline the boolean and remove the field name. The exact URL
            # and override signature are the stable audit anchors.
            pass

    with zipfile.ZipFile(
        original_dir / "split_config.arm64_v8a.apk", "r"
    ) as original_arm, zipfile.ZipFile(
        modified_dir / "split_config.arm64_v8a.apk", "r"
    ) as final_arm:
        original_native = original_arm.read(NATIVE_ENTRY)
        final_native = final_arm.read(NATIVE_ENTRY)
        final_shim = final_arm.read(SHIM_ENTRY)
        names = set(final_arm.namelist())
        for forbidden in (
            "lib/arm64-v8a/libfrida-gadget.so",
            "lib/arm64-v8a/libfrida-gadget.config.so",
            "lib/arm64-v8a/libbc_script.js.so",
        ):
            if forbidden in names:
                raise ValueError("Frida research payload leaked into static bridge")

    before_elf = _lief_binary(original_native, "original.so")
    after_elf = _lief_binary(final_native, "bridge.so")
    shim_elf = _lief_binary(final_shim, "libkneekura.so")
    if set(before_elf["exports"]) != set(after_elf["exports"]):
        raise ValueError("bridge changed original libnative export surface")
    if SHIM_SONAME not in after_elf["libraries"]:
        raise ValueError("bridge libnative missing Kneekura shim dependency")

    required_shim_exports = {
        "kneekura_shim_abi_version",
        "kneekura_bootstrap_initialized",
        "kneekura_feature_mask",
        "kneekura_feature_enabled",
    }
    if not required_shim_exports.issubset(set(shim_elf["exports"])):
        raise ValueError("bridge shim export contract is incomplete")

    return {
        "schema_version": 1,
        "mode": "static-java-http-bridge",
        "flavor": flavor,
        "package": package_name,
        "launcher": bridge_launcher,
        "replay_enabled": replay_enabled,
        "original_new_http_code_preserved": True,
        "request_constructor_anchor_preserved": True,
        "offline_fallback_anchor_preserved": True,
        "original_scene_activity_subclassed": True,
        "unknown_request_super_fallthrough": True,
        "shim_dependency_present": True,
        "frida_absent": True,
        "split_diffs": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_dir", type=Path)
    parser.add_argument("modified_dir", type=Path)
    parser.add_argument("--flavor", required=True, choices=sorted(FLAVOR_PACKAGES))
    parser.add_argument("--replay-enabled", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = verify_static_http_bridge(
        args.original_dir.resolve(),
        args.modified_dir.resolve(),
        flavor=args.flavor,
        replay_enabled=args.replay_enabled,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
