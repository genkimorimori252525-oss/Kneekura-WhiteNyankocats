"""Offline network audit guards do not claim that manifest findings prove traffic."""
from __future__ import annotations

import io
import json
from pathlib import Path
import struct
import unittest
import zipfile

from tools.base_mod.binary_axml import remove_exact_uses_permission
from tools.base_mod.audit_offline_egress import (
    audit, inspect_bridge, manifest_components,
)


def fixture_axml(permissions: tuple[str, ...] = (),
                 providers: tuple[str, ...] = ()) -> bytes:
    strings = ["manifest", "uses-permission", "provider", "name",
               *permissions, *providers]
    offsets = []
    data = bytearray()
    for string in strings:
        value = string.encode("ascii")
        if len(value) > 127:
            raise ValueError("fixture strings require short ASCII")
        offsets.append(len(data))
        data.extend(bytes([len(value), len(value)]))
        data.extend(value + b"\x00")
    pool_size = 28 + 4 * len(strings) + len(data)
    pool = (
        struct.pack("<HHI", 1, 28, pool_size)
        + struct.pack("<IIIII", len(strings), 0, 0x100,
                      28 + len(strings) * 4, 0)
        + b"".join(struct.pack("<I", offset) for offset in offsets)
        + data
    )

    def start_element(tag: str, value: str) -> bytes:
        chunk_size = 56  # 16-byte node, 20-byte attr header, one 20-byte attr
        return (
            struct.pack("<HHI", 0x102, 16, chunk_size)
            + struct.pack("<II", 1, 0xFFFFFFFF)
            + struct.pack("<II", 0xFFFFFFFF, strings.index(tag))
            + struct.pack("<HHHHHH", 20, 20, 1, 0, 0, 0)
            + struct.pack("<III", 0xFFFFFFFF, strings.index("name"),
                          strings.index(value))
            + struct.pack("<HBBI", 8, 0, 3, strings.index(value))
        )
    nodes = [start_element("uses-permission", p) for p in permissions]
    nodes.extend(start_element("provider", p) for p in providers)
    chunks = pool + b"".join(nodes)
    return struct.pack("<HHI", 3, 8, 8 + len(chunks)) + chunks


def fixture_apk(manifest: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as apk:
        apk.writestr("AndroidManifest.xml", manifest)
    return output.getvalue()




def with_empty_element_closing_tags(payload: bytes) -> bytes:
    """Upgrade test fixture's uses-permission start tags to real AXML pairs."""
    source = payload
    output = bytearray(source[:8])
    cursor = 8
    while cursor < len(source):
        kind, _, size = struct.unpack_from("<HHI", source, cursor)
        chunk = source[cursor:cursor + size]
        if len(chunk) != size or size < 8:
            raise AssertionError("synthetic fixture is malformed")
        output.extend(chunk)
        if kind == 0x0102:
            tag_id = struct.unpack_from("<I", source, cursor + 20)[0]
            if tag_id == 1:  # fixture_axml always indexes uses-permission = 1
                output.extend(
                    struct.pack("<HHI", 0x0103, 16, 24)
                    + struct.pack("<II", 1, 0xFFFFFFFF)
                    + struct.pack("<II", 0xFFFFFFFF, tag_id)
                )
        cursor += size
    struct.pack_into("<I", output, 4, len(output))
    return bytes(output)

class OfflineEgressAuditTests(unittest.TestCase):
    def test_remove_exact_original_internet_permission_without_other_manifest_changes(self):
        source = with_empty_element_closing_tags(fixture_axml(
            permissions=("android.permission.INTERNET",
                         "android.permission.ACCESS_NETWORK_STATE"),
            providers=("com.google.firebase.provider.FirebaseInitProvider",),
        ))
        before = manifest_components(source)
        patched, details = remove_exact_uses_permission(
            source, "android.permission.INTERNET"
        )
        after = manifest_components(patched)
        self.assertIn("android.permission.INTERNET", before["declared_permissions"])
        self.assertNotIn("android.permission.INTERNET", after["declared_permissions"])
        self.assertIn("android.permission.ACCESS_NETWORK_STATE",
                      after["declared_permissions"])
        self.assertEqual(before["sdk_components"], after["sdk_components"])
        self.assertEqual(details["removed_elements"], 1)
        self.assertEqual(details["removed_byte_count"], 80)
        self.assertEqual(len(source) - len(patched), 80)
        self.assertEqual(
            struct.unpack_from("<I", patched, 4)[0], len(patched)
        )

    def test_research_permission_removal_refuses_invalid_or_ambiguous_axml(self):
        from tools.base_mod.binary_axml import remove_exact_uses_permission
        good = with_empty_element_closing_tags(fixture_axml(
            permissions=("android.permission.INTERNET",),
        ))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            remove_exact_uses_permission(good, "android.permission.FAKE")
        source = with_empty_element_closing_tags(fixture_axml(
            permissions=("android.permission.INTERNET", "android.permission.INTERNET")
        ))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            remove_exact_uses_permission(source, "android.permission.INTERNET")
        malformed = fixture_axml(permissions=("android.permission.INTERNET",))
        with self.assertRaisesRegex(ValueError, "immediate paired end"):
            remove_exact_uses_permission(malformed, "android.permission.INTERNET")
        broken_len = bytearray(good)
        struct.pack_into("<I", broken_len, 4, len(good) + 1)
        with self.assertRaisesRegex(ValueError, "declared size mismatch"):
            remove_exact_uses_permission(bytes(broken_len), "android.permission.INTERNET")

    def test_actual_manifest_elements_not_unused_strings(self):
        xml = fixture_axml(
            permissions=("android.permission.INTERNET", "android.permission.ACCESS_NETWORK_STATE"),
            providers=("com.google.firebase.provider.FirebaseInitProvider",),
        )
        info = manifest_components(xml)
        self.assertIn("android.permission.INTERNET", info["declared_permissions"])
        self.assertEqual(info["sdk_components"][0]["kind"], "provider")
        self.assertIn("FirebaseInitProvider", info["sdk_components"][0]["class_name"])

    def test_original_fallthrough_and_internet_make_release_unproven(self):
        apk = fixture_apk(fixture_axml(
            permissions=("android.permission.INTERNET",),
            providers=("com.adjust.sdk.SystemLifecycleContentProvider",),
        ))
        bridge = ("public class MyActivity "
                  "extends jp.co.ponos.battlecats.MyActivity { "
                  "return super.newHttpRequest(a,b,c,d,e,f,g,h); }")
        result = audit(apk, bridge)
        self.assertEqual(result["result"], "OFFLINE_NOT_PROVEN")
        self.assertIn("ANDROID_INTERNET_PERMISSION_PRESENT", result["gaps"])
        self.assertIn("UNKNOWN_HTTP_REQUESTS_FALL_THROUGH_TO_ORIGINAL", result["gaps"])
        self.assertIn("THIRD_PARTY_SDK_COMPONENTS_REQUIRE_SEPARATE_NETWORK_AUDIT", result["gaps"])
        self.assertIsNone(result["network_transfer_observed"])
        self.assertIsNone(result["save_restriction_cause_confirmed"])
        self.assertFalse(result["no_network_release_certified"])

    def test_clean_static_manifest_does_not_claim_offline_runtime(self):
        apk = fixture_apk(fixture_axml())
        result = audit(apk, "class CleanGame {}")
        self.assertEqual(result["result"], "STATIC_GAPS_NOT_FOUND_RUNTIME_PROOF_REQUIRED")
        self.assertEqual(result["gaps"], [])
        self.assertFalse(result["no_network_release_certified"])

    def test_invalid_source_manifest_rejected(self):
        with self.assertRaises(ValueError):
            manifest_components(b"abc")
        with self.assertRaises((KeyError, ValueError)):
            audit(fixture_apk(b"not-axml"), "")
        bridge = inspect_bridge("extends jp.co.ponos.battlecats.MyActivity {}")
        self.assertFalse(bridge["original_http_fallthrough_possible"])


if __name__ == "__main__":
    unittest.main()
