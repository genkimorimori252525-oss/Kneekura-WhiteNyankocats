from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.battlecats_pack import PackReader
from tools.base_mod.battlecats_pack_writer import (
    _encrypt_entry,
    encrypt_manifest_bytes,
)
from tools.base_mod.patch_installpack_downloadlocal import (
    DATALOCAL_LIST,
    DATALOCAL_PACK,
    DOWNLOADLOCAL_LIST,
    DOWNLOADLOCAL_PACK,
    patch_installpack_apk,
)


def make_pack(entries: list[tuple[str, bytes]], family: str):
    chunks = []
    rows = []
    offset = 0
    for name, payload in entries:
        encrypted, _ = _encrypt_entry(family, payload, region="jp")
        chunks.append(encrypted)
        rows.append(f"{name},{offset},{len(encrypted)}")
        offset += len(encrypted)
    plain = (
        str(len(entries)) + "\n" + "\n".join(rows) + "\n"
    ).encode("utf-8")
    return encrypt_manifest_bytes(plain), b"".join(chunks)


class InstallPackDownloadLocalOverlayTests(unittest.TestCase):
    def test_overlay_preserves_datalocal_and_appends_downloadlocal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "source.apk"
            target = root / "target.apk"

            data_manifest, data_pack = make_pack(
                [("GatyaDataSetR1.csv", b"original r1\n")],
                "DataLocal",
            )
            download_manifest, download_pack = make_pack(
                [
                    ("download.png", b"png"),
                    ("download.imgcut", b"imgcut"),
                ],
                "DownloadLocal",
            )

            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("AndroidManifest.xml", b"manifest")
                archive.writestr(DATALOCAL_LIST, data_manifest)
                archive.writestr(DATALOCAL_PACK, data_pack)
                archive.writestr(DOWNLOADLOCAL_LIST, download_manifest)
                archive.writestr(DOWNLOADLOCAL_PACK, download_pack)
                archive.writestr("assets/Other.bin", b"untouched")

            ledger = patch_installpack_apk(
                source,
                target,
                {
                    "GatyaDataSetR1.csv": b"override r1\n",
                    "GatyaDataSetR2.csv": b"-1\n",
                },
            )

            self.assertTrue(ledger["datalocal_preserved_byte_identical"])
            self.assertEqual(
                ledger["changed_apk_entries"],
                [DOWNLOADLOCAL_LIST, DOWNLOADLOCAL_PACK],
            )

            with zipfile.ZipFile(source, "r") as before, zipfile.ZipFile(
                target, "r"
            ) as after:
                self.assertEqual(
                    after.read(DATALOCAL_LIST),
                    before.read(DATALOCAL_LIST),
                )
                self.assertEqual(
                    after.read(DATALOCAL_PACK),
                    before.read(DATALOCAL_PACK),
                )
                self.assertEqual(
                    after.read("assets/Other.bin"),
                    b"untouched",
                )

                original_download = PackReader(
                    "DownloadLocal",
                    before.read(DOWNLOADLOCAL_LIST),
                    before.read(DOWNLOADLOCAL_PACK),
                    region="jp",
                )
                patched_download = PackReader(
                    "DownloadLocal",
                    after.read(DOWNLOADLOCAL_LIST),
                    after.read(DOWNLOADLOCAL_PACK),
                    region="jp",
                )

                self.assertEqual(
                    patched_download.read("download.png")[0],
                    original_download.read("download.png")[0],
                )
                self.assertEqual(
                    patched_download.read("download.imgcut")[0],
                    original_download.read("download.imgcut")[0],
                )
                self.assertEqual(
                    patched_download.read("GatyaDataSetR1.csv")[0],
                    b"override r1\n",
                )
                self.assertEqual(
                    patched_download.read("GatyaDataSetR2.csv")[0],
                    b"-1\n",
                )


if __name__ == "__main__":
    unittest.main()
