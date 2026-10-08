import unittest

from tools.battlecats_pack import PackReader
from tools.base_mod.battlecats_pack_writer import (
    _encrypt_entry,
    encrypt_manifest_bytes,
    rebuild_pack,
    append_pack_entries,
)


def make_pack(entries: list[tuple[str, bytes]], family: str = "DataLocal"):
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


class BattleCatsPackWriterTests(unittest.TestCase):
    def test_no_replacement_is_byte_identical(self) -> None:
        manifest, pack = make_pack([
            ("a.csv", b"alpha\n"),
            ("b.csv", b"beta\n"),
            ("c.tsv", b"gamma\n"),
        ])
        new_manifest, new_pack, ledger = rebuild_pack(
            "DataLocal",
            manifest,
            pack,
            {},
            region="jp",
        )
        self.assertEqual(new_manifest, manifest)
        self.assertEqual(new_pack, pack)
        self.assertEqual(ledger["changed_entries"], [])

    def test_one_replacement_preserves_all_other_payloads(self) -> None:
        manifest, pack = make_pack([
            ("a.csv", b"alpha\n"),
            ("b.csv", b"beta\n"),
            ("c.tsv", b"gamma\n"),
        ])
        new_manifest, new_pack, ledger = rebuild_pack(
            "DataLocal",
            manifest,
            pack,
            {"b.csv": b"beta changed and longer\n"},
            region="jp",
        )

        before = PackReader("DataLocal", manifest, pack, region="jp")
        after = PackReader("DataLocal", new_manifest, new_pack, region="jp")

        self.assertEqual(after.read("a.csv")[0], before.read("a.csv")[0])
        self.assertEqual(after.read("c.tsv")[0], before.read("c.tsv")[0])
        self.assertEqual(after.read("b.csv")[0], b"beta changed and longer\n")
        self.assertEqual(ledger["changed_entries"], ["b.csv"])
        changed = [row for row in ledger["entries"] if row["changed"]]
        self.assertEqual([row["name"] for row in changed], ["b.csv"])

    def test_append_pack_entries_preserves_source_and_adds_new_files(self) -> None:
        manifest, pack = make_pack(
            [
                ("download.png", b"png bytes"),
                ("download.imgcut", b"imgcut bytes"),
            ],
            family="DownloadLocal",
        )
        new_manifest, new_pack, ledger = append_pack_entries(
            "DownloadLocal",
            manifest,
            pack,
            {
                "GatyaDataSetR1.csv": b"30,40,-1\n",
                "GatyaDataSetR2.csv": b"-1\n",
            },
            region="jp",
        )

        before = PackReader("DownloadLocal", manifest, pack, region="jp")
        after = PackReader("DownloadLocal", new_manifest, new_pack, region="jp")

        self.assertEqual(
            after.read("download.png")[0],
            before.read("download.png")[0],
        )
        self.assertEqual(
            after.read("download.imgcut")[0],
            before.read("download.imgcut")[0],
        )
        self.assertEqual(
            after.read("GatyaDataSetR1.csv")[0],
            b"30,40,-1\n",
        )
        self.assertEqual(
            after.read("GatyaDataSetR2.csv")[0],
            b"-1\n",
        )
        self.assertTrue(ledger["original_entries_preserved"])
        self.assertEqual(
            ledger["added_entries"],
            ["GatyaDataSetR1.csv", "GatyaDataSetR2.csv"],
        )

    def test_append_pack_entries_rejects_existing_name(self) -> None:
        manifest, pack = make_pack(
            [("download.png", b"png bytes")],
            family="DownloadLocal",
        )
        with self.assertRaisesRegex(ValueError, "already exists"):
            append_pack_entries(
                "DownloadLocal",
                manifest,
                pack,
                {"download.png": b"replacement"},
                region="jp",
            )

    def test_unknown_replacement_fails_closed(self) -> None:
        manifest, pack = make_pack([("a.csv", b"alpha")])
        with self.assertRaisesRegex(KeyError, "missing.csv"):
            rebuild_pack(
                "DataLocal",
                manifest,
                pack,
                {"missing.csv": b"nope"},
                region="jp",
            )


if __name__ == "__main__":
    unittest.main()
