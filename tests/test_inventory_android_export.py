from __future__ import annotations

import hashlib
import io
import json
import pathlib
import tempfile
import unittest
import zipfile

from tools import inventory_android_export as inv


def make_apk(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


class InventoryAndroidExportTests(unittest.TestCase):
    def test_nested_apk_and_shared_storage_are_classified_read_only(self) -> None:
        base_apk = make_apk(
            {
                "AndroidManifest.xml": b"manifest",
                "classes.dex": b"dex",
                "assets/DataLocal.pack": b"pack-data",
                "assets/DataLocal.list": b"list-data",
                "assets/units/unit001.maanim": b"anim",
                "assets/units/unit001.mamodel": b"model",
                "assets/ui/title_button.png": b"png",
                "assets/audio/bgm001.ogg": b"ogg",
                "lib/arm64-v8a/libgame.so": b"native",
                "res/drawable/icon.png": b"icon",
            }
        )
        split_apk = make_apk(
            {
                "AndroidManifest.xml": b"manifest-2",
                "res/drawable-ja/text.png": b"localized",
            }
        )

        with tempfile.TemporaryDirectory() as temp_name:
            temp = pathlib.Path(temp_name)
            export_zip = temp / "export.zip"
            with zipfile.ZipFile(export_zip, "w", compression=zipfile.ZIP_DEFLATED) as outer:
                outer.writestr("apks/base.apk", base_apk)
                outer.writestr("apks/split_config.ja.apk", split_apk)
                outer.writestr(
                    "shared_storage/jp.co.ponos.battlecats/files/download/event.pack",
                    b"event-pack",
                )
                outer.writestr(
                    "shared_storage/jp.co.ponos.battlecats/files/ui/local_icon.png",
                    b"image",
                )

            before = hashlib.sha256(export_zip.read_bytes()).hexdigest()
            result = inv.inventory_path(export_zip)
            after = hashlib.sha256(export_zip.read_bytes()).hexdigest()

            self.assertEqual(before, after)
            self.assertEqual(result["source"]["sha256"], before)
            self.assertEqual(result["inventory"]["kind"], "export_zip")
            self.assertEqual(len(result["inventory"]["apks"]), 2)

            base = next(
                apk
                for apk in result["inventory"]["apks"]
                if apk["logical_name"] == "apks/base.apk"
            )
            categories = base["categories"]
            self.assertEqual(categories["manifest"]["count"], 1)
            self.assertEqual(categories["code"]["count"], 1)
            self.assertEqual(categories["native"]["count"], 1)
            self.assertEqual(categories["pack_list"]["count"], 2)
            self.assertGreaterEqual(categories["animation"]["count"], 2)
            self.assertGreaterEqual(categories["ui_candidate"]["count"], 1)

            shared = result["inventory"]["shared_storage"]["categories"]
            self.assertEqual(shared["pack_list"]["count"], 1)
            self.assertEqual(shared["ui_candidate"]["count"], 1)

            output = temp / "report"
            json_path, md_path = inv.write_reports(result, output)
            self.assertTrue(json_path.is_file())
            self.assertTrue(md_path.is_file())
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["source"]["sha256"], before)
            self.assertIn("apks/base.apk", md_path.read_text(encoding="utf-8"))

    def test_direct_apk_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp = pathlib.Path(temp_name)
            apk_path = temp / "base.apk"
            apk_path.write_bytes(
                make_apk(
                    {
                        "AndroidManifest.xml": b"m",
                        "classes2.dex": b"d",
                        "assets/a.pack": b"p",
                    }
                )
            )

            result = inv.inventory_path(apk_path)
            self.assertEqual(result["inventory"]["kind"], "apk")
            self.assertEqual(len(result["inventory"]["apks"]), 1)
            categories = result["inventory"]["apks"][0]["categories"]
            self.assertEqual(categories["pack_list"]["count"], 1)
            self.assertEqual(categories["code"]["count"], 1)

    def test_expected_sha256_rejects_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp = pathlib.Path(temp_name)
            apk_path = temp / "base.apk"
            apk_path.write_bytes(make_apk({"AndroidManifest.xml": b"x"}))

            result = inv.inventory_path(apk_path)
            with self.assertRaises(ValueError):
                inv.verify_expected_sha256(result, "0" * 64)

    def test_directory_input_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = pathlib.Path(temp_name)
            (root / "shared").mkdir()
            (root / "shared" / "sample.list").write_bytes(b"x")
            (root / "base.apk").write_bytes(
                make_apk({"AndroidManifest.xml": b"x", "assets/ui/menu.png": b"y"})
            )

            result = inv.inventory_path(root)
            self.assertEqual(result["inventory"]["kind"], "directory")
            self.assertEqual(len(result["inventory"]["apks"]), 1)
            shared = result["inventory"]["shared_storage"]["categories"]
            self.assertEqual(shared["pack_list"]["count"], 1)


if __name__ == "__main__":
    unittest.main()
