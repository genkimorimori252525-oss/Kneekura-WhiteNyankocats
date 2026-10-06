from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.battlecats_pack import PackReader
from tools.base_mod.battlecats_pack_writer import (
    _encrypt_entry,
    encrypt_manifest_bytes,
)
from tools.base_mod.patch_installpack_data import (
    DATALOCAL_LIST,
    DATALOCAL_PACK,
    patch_installpack_apk,
)


def make_pack(entries: list[tuple[str, bytes]]):
    chunks = []
    rows = []
    offset = 0
    for name, payload in entries:
        encrypted, _ = _encrypt_entry("DataLocal", payload, region="jp")
        chunks.append(encrypted)
        rows.append(f"{name},{offset},{len(encrypted)}")
        offset += len(encrypted)
    plain = (
        str(len(entries)) + "\n" + "\n".join(rows) + "\n"
    ).encode("utf-8")
    return encrypt_manifest_bytes(plain), b"".join(chunks)


class InstallPackDataPatchTests(unittest.TestCase):
    def test_only_datalocal_container_entries_are_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "source.apk"
            target = root / "target.apk"
            manifest, pack = make_pack([
                ("a.csv", b"alpha\n"),
                ("b.csv", b"beta\n"),
            ])
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("AndroidManifest.xml", b"manifest")
                archive.writestr(DATALOCAL_LIST, manifest)
                archive.writestr(DATALOCAL_PACK, pack)
                archive.writestr("assets/Other.bin", b"untouched")

            ledger = patch_installpack_apk(
                source,
                target,
                {"b.csv": b"beta changed\n"},
            )
            self.assertEqual(
                ledger["changed_apk_entries"],
                [DATALOCAL_LIST, DATALOCAL_PACK],
            )
            self.assertEqual(
                ledger["changed_datalocal_entries"],
                ["b.csv"],
            )

            with zipfile.ZipFile(target, "r") as archive:
                self.assertEqual(
                    archive.read("assets/Other.bin"),
                    b"untouched",
                )
                reader = PackReader(
                    "DataLocal",
                    archive.read(DATALOCAL_LIST),
                    archive.read(DATALOCAL_PACK),
                    region="jp",
                )
                self.assertEqual(reader.read("a.csv")[0], b"alpha\n")
                self.assertEqual(reader.read("b.csv")[0], b"beta changed\n")

    def test_missing_datalocal_entries_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "source.apk"
            target = root / "target.apk"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("AndroidManifest.xml", b"manifest")
            with self.assertRaisesRegex(ValueError, "DataLocal.list"):
                patch_installpack_apk(
                    source,
                    target,
                    {"b.csv": b"beta"},
                )


if __name__ == "__main__":
    unittest.main()
