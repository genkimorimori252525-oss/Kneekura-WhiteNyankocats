"""Encrypted owner-only Server input tests. Test fixtures contain no game art."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from tools.base_mod.battlecats_pack_writer import _encrypt_entry, encrypt_manifest_bytes
from tools.base_mod.extract_godzilla_owner_rig import PNG_FILE, ANIM_FILES

ROOT = Path(__file__).resolve().parents[1]

def write_pair(root: Path, family: str, entries: dict[str, bytes]) -> tuple[Path, Path]:
    chunks = []
    records = []
    offset = 0
    for name, payload in sorted(entries.items()):
        ciphertext, mode = _encrypt_entry(family, payload, region="jp")
        assert mode == "aes-128-ecb-server"
        chunks.append(ciphertext)
        records.append(f"{name},{offset},{len(ciphertext)}")
        offset += len(ciphertext)
    text = (str(len(records)) + "\n" + "\n".join(records) + "\n").encode()
    list_path, pack_path = root / f"{family}.list", root / f"{family}.pack"
    list_path.write_bytes(encrypt_manifest_bytes(text))
    pack_path.write_bytes(b"".join(chunks))
    return list_path, pack_path

class EncryptedOriginalServerExtractionTests(unittest.TestCase):
    def _run(self, root: Path, missing: str | None = None):
        png = b"\x89PNG\r\n\x1a\n" + b"mock-private-source"
        mlist, mpack = write_pair(root, "MNumberServer", {
            PNG_FILE: png, "unrelated.png": png})
        motions = {n: ("mock-"+n).encode() for n in ANIM_FILES if n != missing}
        motions["unrelated.mamodel"] = b"unrelated"
        wlist, wpack = write_pair(root, "WImageDataServer", motions)
        hashes = {
            x.name: hashlib.sha256(x.read_bytes()).hexdigest()
            for x in (mlist, mpack, wlist, wpack)
        }
        output = root / "owner-output"
        args = [sys.executable, "-m", "tools.base_mod.extract_godzilla_owner_rig",
                "--m-number-list", str(mlist), "--m-number-pack", str(mpack),
                "--w-imagedata-list", str(wlist), "--w-imagedata-pack", str(wpack),
                "--output", str(output)]
        proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True,
                              check=False, timeout=30)
        for x in (mlist, mpack, wlist, wpack):
            self.assertEqual(hashlib.sha256(x.read_bytes()).hexdigest(), hashes[x.name])
        return proc, output, hashes, png, motions

    def test_real_encrypted_server_pair_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            proc, output, hashes, png, motions = self._run(Path(temp))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual({x.name for x in output.iterdir()},
                             {PNG_FILE, *ANIM_FILES, "rig-receipt.json"})
            receipt = json.loads((output / "rig-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["cat_form_index"], 0)
            self.assertEqual(receipt["target_stem"], "702_f")
            self.assertFalse(receipt["ready_to_install"])
            self.assertFalse(receipt["original_apk_modified"])
            self.assertFalse(receipt["save_data_modified"])
            self.assertEqual(receipt["sources"], hashes)
            self.assertEqual((output / PNG_FILE).read_bytes(), png)
            for name in ANIM_FILES:
                self.assertEqual((output / name).read_bytes(), motions[name])

    def test_missing_animation_never_writes_output(self):
        with tempfile.TemporaryDirectory() as temp:
            proc, output, _, _, _ = self._run(Path(temp), "550_e03.maanim")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("missing required original owner Server asset", proc.stderr)
            self.assertFalse(output.exists())

if __name__ == "__main__":
    unittest.main()