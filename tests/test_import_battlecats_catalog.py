from __future__ import annotations

import hashlib
import io
import pathlib
import tempfile
import unittest
import zipfile

from Crypto.Cipher import AES

from tools.battlecats_pack import BLOCK_SIZE
from tools.import_battlecats_catalog import build_catalog


JP_KEY = bytes.fromhex("d754868de89d717fa9e7b06da45ae9e3")
JP_IV = bytes.fromhex("40b2131a9f388ad4e5002a98118f6128")


def pad(data: bytes) -> bytes:
    amount = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + bytes([amount]) * amount


def list_key() -> bytes:
    return hashlib.md5(b"pack").digest()[:8].hex().encode("ascii")


def encrypt_manifest(text: str) -> bytes:
    return AES.new(list_key(), AES.MODE_ECB).encrypt(pad(text.encode("utf-8")))


def build_pack(files: dict[str, bytes]) -> tuple[bytes, bytes]:
    offset = 0
    pack = bytearray()
    rows = []
    for name, payload in files.items():
        encrypted = AES.new(JP_KEY, AES.MODE_CBC, JP_IV).encrypt(pad(payload))
        rows.append(f"{name},{offset},{len(encrypted)}")
        pack.extend(encrypted)
        offset += len(encrypted)

    manifest = "\n".join([str(len(rows)), *rows, ""])
    return encrypt_manifest(manifest), bytes(pack)


def make_export(path: pathlib.Path) -> None:
    data_list, data_pack = build_pack(
        {
            "unit001.csv": (
                b"100,3,10,8,15,140,50,75,0,320, // cat\n"
                b"200,3,10,16,15,140,50,75,0,320,\n"
            ),
            "unit002.csv": b"400,1,8,2,30,110,100,120,0,320,\n",
        }
    )
    res_list, res_pack = build_pack(
        {
            "Unit_Explanation1_ja.csv": (
                "ネコ,基本キャラ\nネコビルダー,進化\n".encode("utf-8")
            ),
            # Deliberate mismatch: 2 text rows, 1 stat row.
            "Unit_Explanation2_ja.csv": (
                "タンクネコ,基本キャラ\nネコカベ,進化\n".encode("utf-8")
            ),
        }
    )

    install_buffer = io.BytesIO()
    with zipfile.ZipFile(install_buffer, "w", compression=zipfile.ZIP_DEFLATED) as install:
        install.writestr("assets/DataLocal.list", data_list)
        install.writestr("assets/DataLocal.pack", data_pack)
        install.writestr("assets/resLocal.list", res_list)
        install.writestr("assets/resLocal.pack", res_pack)

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as outer:
        outer.writestr("README.md", "# export\n- バージョン: `15.test`\n")
        outer.writestr("apk/split_InstallPack.apk", install_buffer.getvalue())


class BattleCatsCatalogTests(unittest.TestCase):
    def test_catalog_join_and_mismatch_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            path = pathlib.Path(temp_name) / "export.zip"
            make_export(path)
            before = hashlib.sha256(path.read_bytes()).hexdigest()

            catalog = build_catalog(path, expected_sha256=before)

            after = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(before, after)
            self.assertEqual(catalog["source"]["version"], "15.test")
            self.assertEqual(catalog["summary"]["unit_count"], 2)
            self.assertEqual(catalog["summary"]["anomaly_count"], 1)
            self.assertEqual(
                catalog["summary"]["anomalies"][0]["unit_id"],
                2,
            )

            unit1 = catalog["units"][0]
            self.assertEqual(unit1["key"], "bc:unit:001")
            self.assertEqual(unit1["forms"][0]["name"], "ネコ")
            self.assertEqual(unit1["forms"][0]["stats_raw"][0], 100)

            unit2 = catalog["units"][1]
            self.assertEqual(len(unit2["forms"]), 2)
            self.assertEqual(unit2["forms"][1]["name"], "ネコカベ")
            self.assertIsNone(unit2["forms"][1]["stats_raw"])


if __name__ == "__main__":
    unittest.main()
