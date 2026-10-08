from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.base_mod.inject_shim import add_needed_dependency


@unittest.skipUnless(
    importlib.util.find_spec("lief") is not None,
    "LIEF is installed only in the native-patching workflow",
)
class NativeDependencyInjectionTests(unittest.TestCase):
    def test_lief_add_needed_preserves_exports(self) -> None:
        cc = shutil.which("cc")
        if cc is None:
            self.skipTest("host C compiler unavailable")

        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "anchor.c"
            library = root / "libanchor.so"
            source.write_text(
                "__attribute__((visibility(\"default\"))) "
                "int anchor_export(void) { return 7; }\n",
                encoding="utf-8",
            )
            subprocess.run(
                [cc, "-shared", "-fPIC", str(source), "-o", str(library)],
                check=True,
            )

            patched, report = add_needed_dependency(
                library.read_bytes(),
                needed="libkneekura-test.so",
            )
            self.assertGreater(len(patched), 0)
            self.assertIn(
                "libkneekura-test.so",
                report["libraries_after"],
            )
            self.assertTrue(report["export_surface_preserved"])


if __name__ == "__main__":
    unittest.main()