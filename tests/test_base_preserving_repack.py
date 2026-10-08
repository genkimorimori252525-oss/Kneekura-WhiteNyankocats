from __future__ import annotations

import json
from pathlib import Path
import stat
import tempfile
import textwrap
import unittest
import zipfile

from tools.base_mod.repack import (
    JP_15_7_1_SPLITS,
    baseline_resign,
    payload_fingerprint,
)


def _write_apk(path: Path, marker: str) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", b"synthetic-manifest-" + marker.encode())
        archive.writestr("assets/payload.txt", f"payload:{marker}".encode())
        archive.writestr("META-INF/OLD.SF", b"old signature metadata")


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class BasePreservingRepackTests(unittest.TestCase):
    def test_payload_fingerprint_ignores_signature_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            a = root / "a.apk"
            b = root / "b.apk"
            _write_apk(a, "same")
            with zipfile.ZipFile(a, "a") as archive:
                archive.writestr("stamp-cert-sha256", b"old-source-stamp")
                archive.writestr("pinlist.meta", b"old-pin-layout")
            with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("assets/payload.txt", b"payload:same")
                archive.writestr("AndroidManifest.xml", b"synthetic-manifest-same")
                archive.writestr("META-INF/NEW.RSA", b"different signer bytes")
            self.assertEqual(payload_fingerprint(a), payload_fingerprint(b))

    def test_baseline_requires_complete_exact_split_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            (root / "base.apk").write_bytes(b"not enough")
            with self.assertRaisesRegex(FileNotFoundError, "split_InstallPack"):
                baseline_resign(
                    root,
                    root / "out",
                    keystore=root / "missing.p12",
                    alias="kneekura",
                    storepass="test",
                    zipalign="/does/not/matter",
                    apksigner="/does/not/matter",
                )

    def test_fake_tool_pipeline_emits_invariant_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "splits"
            output = root / "output"
            tools = root / "tools"
            source.mkdir()
            tools.mkdir()
            for index, name in enumerate(JP_15_7_1_SPLITS):
                _write_apk(source / name, str(index))

            keystore = root / "kneekura.p12"
            keystore.write_bytes(b"synthetic-key")

            zipalign = tools / "zipalign"
            _write_executable(
                zipalign,
                textwrap.dedent(
                    """                    #!/usr/bin/env python3
                    import shutil, sys
                    shutil.copyfile(sys.argv[-2], sys.argv[-1])
                    """
                ),
            )

            apksigner = tools / "apksigner"
            _write_executable(
                apksigner,
                textwrap.dedent(
                    """                    #!/usr/bin/env python3
                    import shutil, sys
                    args = sys.argv[1:]
                    if args[0] == "sign":
                        out = args[args.index("--out") + 1]
                        shutil.copyfile(args[-1], out)
                    elif args[0] == "verify" and "--print-certs" in args:
                        print("Signer #1 certificate SHA-256 digest: "
                              "0123456789abcdef0123456789abcdef"
                              "0123456789abcdef0123456789abcdef")
                    """
                ),
            )

            ledger = baseline_resign(
                source,
                output,
                keystore=keystore,
                alias="kneekura",
                storepass="test",
                zipalign=str(zipalign),
                apksigner=str(apksigner),
                source_export_sha256="a" * 64,
            )

            self.assertTrue(ledger["content_invariant"])
            self.assertEqual(len(ledger["splits"]), len(JP_15_7_1_SPLITS))
            self.assertEqual(
                ledger["signer_certificate_sha256"],
                "0123456789abcdef" * 4,
            )
            persisted = json.loads((output / "patch-ledger.json").read_text())
            self.assertTrue(all(row["content_invariant"] for row in persisted["splits"]))


if __name__ == "__main__":
    unittest.main()