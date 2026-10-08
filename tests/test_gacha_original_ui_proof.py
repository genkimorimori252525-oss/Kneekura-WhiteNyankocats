from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.base_mod.battlecats_pack_writer import (
    _encrypt_entry,
    encrypt_manifest_bytes,
)
from tools.base_mod.patch_installpack_downloadlocal import (
    DATALOCAL_LIST,
    DATALOCAL_PACK,
    DOWNLOADLOCAL_LIST,
    DOWNLOADLOCAL_PACK,
    INSTALLPACK_SPLIT,
)
from tools.base_mod.verify_gacha_ui_data_proof import verify_gacha_ui_data_proof


ROOT = Path(__file__).resolve().parents[1]


def make_pack(entries: list[tuple[str, bytes]], family: str):
    chunks = []
    rows = []
    offset = 0
    for name, payload in entries:
        encrypted, _ = _encrypt_entry(family, payload, region="jp")
        chunks.append(encrypted)
        rows.append(f"{name},{offset},{len(encrypted)}")
        offset += len(encrypted)
    plain = (str(len(entries)) + "\n" + "\n".join(rows) + "\n").encode()
    return encrypt_manifest_bytes(plain), b"".join(chunks)


def write_installpack(
    root: Path,
    *,
    datalocal_entries: list[tuple[str, bytes]],
    downloadlocal_entries: list[tuple[str, bytes]],
) -> None:
    data_manifest, data_pack = make_pack(datalocal_entries, "DataLocal")
    download_manifest, download_pack = make_pack(
        downloadlocal_entries,
        "DownloadLocal",
    )
    with zipfile.ZipFile(root / INSTALLPACK_SPLIT, "w") as archive:
        archive.writestr(DATALOCAL_LIST, data_manifest)
        archive.writestr(DATALOCAL_PACK, data_pack)
        archive.writestr(DOWNLOADLOCAL_LIST, download_manifest)
        archive.writestr(DOWNLOADLOCAL_PACK, download_pack)



class GachaOriginalUiProofTests(unittest.TestCase):
    def test_verifier_accepts_exactly_one_appended_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            original = root / "original"
            modified = root / "modified"
            original.mkdir()
            modified.mkdir()

            r1 = b"30,31,-1\n40,41,-1\n"
            r2 = b"-1\n-1\n"
            r3 = b"-1\n-1\n"
            option = (
                b"GatyaSetID\tBannerON_OFF\tItemID_Ticket\n"
                b"0\t0\t21\n"
                b"1\t1\t21\n"
            )
            base_data = [
                ("GatyaDataSetR1.csv", r1),
                ("GatyaDataSetR2.csv", r2),
                ("GatyaDataSetR3.csv", r3),
                ("GatyaData_Option_SetR.tsv", option),
            ]
            base_download = [("download.png", b"png")]

            write_installpack(
                original,
                datalocal_entries=base_data,
                downloadlocal_entries=base_download,
            )
            write_installpack(
                modified,
                datalocal_entries=base_data,
                downloadlocal_entries=base_download + [
                    ("GatyaDataSetR1.csv", r1 + b"30,40,-1\n"),
                    ("GatyaDataSetR2.csv", r2 + b"-1\n"),
                    ("GatyaDataSetR3.csv", r3 + b"-1\n"),
                    (
                        "GatyaData_Option_SetR.tsv",
                        option + b"2\t1\t21\n",
                    ),
                ],
            )

            report = verify_gacha_ui_data_proof(
                original,
                modified,
                expected_units=[30, 40],
                clone_option_set=1,
                expected_set_id=2,
            )
            self.assertTrue(report["original_rows_preserved"])
            self.assertTrue(report["banner_on"])
            self.assertTrue(report["option_metadata_cloned"])
            self.assertEqual(report["appended_rows_per_table"], 1)
            self.assertTrue(report["datalocal_byte_identical"])
            self.assertTrue(report["downloadlocal_original_payloads_preserved"])

    def test_builder_keeps_original_scene_code_out_of_scope(self) -> None:
        source = (
            ROOT / "tools/base_mod/build_owned_gacha_ui_proof.py"
        ).read_text(encoding="utf-8")
        self.assertIn("EXPECTED_NEW_SET_ID = 1089", source)
        self.assertIn("EXPECTED_PROOF_UNITS = [37, 30, 34]", source)
        self.assertIn("EXPECTED_CLONE_OPTION_SET = 49", source)
        self.assertIn('"original_gacha_scene_code_modified": False', source)
        self.assertIn('"original_capsule_result_code_modified": False', source)
        self.assertIn('"visibility_schedule_defined": False', source)
        self.assertIn("patch_installpack_downloadlocal", source)
        self.assertIn("allow_downloadlocal_patch=True", source)
        self.assertNotIn("patch_installpack_data", source)
        self.assertIn("verify_gacha_ui_data_proof(", source)
        self.assertIn("research_external_files_dir = flavor == \"research\"", source)
        self.assertIn("use_external_files_dir=research_external_files_dir", source)
        self.assertIn('"research_external_files_dir": research_external_files_dir', source)


if __name__ == "__main__":
    unittest.main()
