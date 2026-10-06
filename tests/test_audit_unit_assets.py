from __future__ import annotations

import hashlib
import io
import json
import pathlib
import tempfile
import unittest
import zipfile

from Crypto.Cipher import AES

from tools.audit_unit_assets import UnitBuyRow, build_audit, required_form_count
from tools.battlecats_pack import BLOCK_SIZE


JP_KEY = bytes.fromhex("d754868de89d717fa9e7b06da45ae9e3")
JP_IV = bytes.fromhex("40b2131a9f388ad4e5002a98118f6128")


def pad(data: bytes) -> bytes:
    amount = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + bytes([amount]) * amount


def list_key() -> bytes:
    return hashlib.md5(b"pack").digest()[:8].hex().encode("ascii")


def encrypt_manifest(text: str) -> bytes:
    return AES.new(list_key(), AES.MODE_ECB).encrypt(pad(text.encode("utf-8")))


def build_encrypted_pack(files: dict[str, bytes]) -> tuple[bytes, bytes]:
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


def build_name_only_pack(names: list[str]) -> tuple[bytes, bytes]:
    rows = []
    pack = bytearray()
    for name in names:
        rows.append(f"{name},{len(pack)},1")
        pack.append(0)
    manifest = "\n".join([str(len(rows)), *rows, ""])
    return encrypt_manifest(manifest), bytes(pack)


def unitbuy_row(*, guide: int, egg_normal: int = -1, egg_evolved: int = -1) -> str:
    cols = ["0"] * 63
    cols[14] = str(guide)
    cols[20] = "-1"
    cols[25] = "-1"
    cols[26] = "-1"
    cols[49] = "30"
    cols[57] = "1"
    cols[61] = str(egg_normal)
    cols[62] = str(egg_evolved)
    return ",".join(cols)


def make_export(path: pathlib.Path) -> None:
    data_list, data_pack = build_encrypted_pack(
        {
            "unit001.csv": b"100,1,1\n",
            "unit002.csv": b"100,1,1\n",
            "unit003.csv": b"100,1,1\n200,1,1\n",
            "unitbuy.csv": (
                unitbuy_row(guide=100)
                + "\n"
                + unitbuy_row(guide=-1)
                + "\n"
                + unitbuy_row(guide=200, egg_normal=0, egg_evolved=1)
                + "\n"
            ).encode(),
        }
    )
    res_list, res_pack = build_encrypted_pack(
        {
            "Unit_Explanation1_ja.csv": "Player One,desc\n".encode(),
            "Unit_Explanation2_ja.csv": "Spirit,desc\n".encode(),
            "Unit_Explanation3_ja.csv": "Egg,desc\nEgg Evolved,desc\n".encode(),
        }
    )

    image_data_names = [
        "000_f.imgcut", "000_f.mamodel", "000_f00.maanim", "000_f01.maanim", "000_f02.maanim",
        # 000_f03 is deliberately supplied by the server index.
        "001_f.imgcut", "001_f.mamodel", "001_f02.maanim",
        "000_m.imgcut", "000_m.mamodel", "000_m00.maanim", "000_m01.maanim", "000_m02.maanim", "000_m03.maanim",
        "001_m.imgcut", "001_m.mamodel", "001_m00.maanim", "001_m01.maanim", "001_m02.maanim", "001_m03.maanim",
    ]
    number_names = ["000_f.png", "001_f.png", "000_m.png", "001_m.png"]
    unit_names = ["uni000_f00.png", "uni000_m00.png", "uni001_m01.png"]

    id_list, id_pack = build_name_only_pack(image_data_names)
    number_list, number_pack = build_name_only_pack(number_names)
    unit_list, unit_pack = build_name_only_pack(unit_names)
    image_list, image_pack = build_name_only_pack([])

    install_buffer = io.BytesIO()
    with zipfile.ZipFile(install_buffer, "w", compression=zipfile.ZIP_DEFLATED) as install:
        for family, list_bytes, pack_bytes in [
            ("DataLocal", data_list, data_pack),
            ("resLocal", res_list, res_pack),
            ("ImageDataLocal", id_list, id_pack),
            ("NumberLocal", number_list, number_pack),
            ("UnitLocal", unit_list, unit_pack),
            ("ImageLocal", image_list, image_pack),
        ]:
            install.writestr(f"assets/{family}.list", list_bytes)
            install.writestr(f"assets/{family}.pack", pack_bytes)

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as outer:
        outer.writestr("README.md", "# export\nversion=15.test\n")
        outer.writestr("apk/split_InstallPack.apk", install_buffer.getvalue())


class UnitAssetAuditTests(unittest.TestCase):
    def test_required_form_count_ignores_placeholder_stat_rows(self) -> None:
        ordinary = UnitBuyRow(
            position_order=100,
            tf_id=0,
            uf_id=0,
            egg_val=-1,
            egg_id=-1,
        )
        true_form = UnitBuyRow(
            position_order=100,
            tf_id=15001,
            uf_id=0,
            egg_val=-1,
            egg_id=-1,
        )
        ultra_form = UnitBuyRow(
            position_order=100,
            tf_id=15001,
            uf_id=16001,
            egg_val=-1,
            egg_id=-1,
        )
        internal = UnitBuyRow(
            position_order=-1,
            tf_id=0,
            uf_id=0,
            egg_val=-1,
            egg_id=-1,
        )

        self.assertEqual(required_form_count(1, ordinary), 1)
        self.assertEqual(required_form_count(3, ordinary), 2)
        self.assertEqual(required_form_count(3, true_form), 3)
        self.assertEqual(required_form_count(4, ultra_form), 4)
        self.assertEqual(required_form_count(3, internal), 3)

    def test_off_by_one_server_merge_and_internal_motion_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp = pathlib.Path(temp_name)
            export = temp / "export.zip"
            make_export(export)
            server_index = temp / "server.json"
            server_index.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "entries": [
                            {
                                "source": "historical",
                                "family": "AImageDataServer",
                                "name": "000_f03.maanim",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            audit = build_audit(export, server_indexes=[server_index])

            self.assertEqual(audit["summary"]["unit_count"], 3)
            self.assertEqual(audit["summary"]["complete_unit_count"], 3)
            self.assertTrue(audit["summary"]["strict_gate_passed"])

            first = audit["units"][0]
            self.assertEqual(first["unit_no"], 1)
            self.assertEqual(first["asset_id"], 0)
            self.assertEqual(first["forms"][0]["animation_base"], "000_f")
            self.assertEqual(first["forms"][0]["motion_policy"], "standard-00-03")
            self.assertIn("03", first["forms"][0]["motions"]["found_suffixes"])

            internal = audit["units"][1]
            self.assertFalse(internal["playable"])
            self.assertEqual(internal["forms"][0]["motion_policy"], "internal-at-least-one")
            self.assertFalse(internal["forms"][0]["deploy_icon"]["required"])
            self.assertTrue(internal["complete"])

            egg = audit["units"][2]
            self.assertEqual(egg["forms"][0]["animation_base"], "000_m")
            self.assertEqual(egg["forms"][1]["animation_base"], "001_m")
            self.assertEqual(egg["forms"][0]["deploy_icon"]["name"], "uni000_m00.png")
            self.assertEqual(egg["forms"][1]["deploy_icon"]["name"], "uni001_m01.png")

    def test_missing_standard_motion_fails_playable_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp = pathlib.Path(temp_name)
            export = temp / "export.zip"
            make_export(export)
            audit = build_audit(export)

            self.assertFalse(audit["summary"]["strict_gate_passed"])
            self.assertFalse(audit["summary"]["playable_gate_passed"])
            self.assertIn("000_f03.maanim", audit["units"][0]["forms"][0]["missing_required"])


if __name__ == "__main__":
    unittest.main()
