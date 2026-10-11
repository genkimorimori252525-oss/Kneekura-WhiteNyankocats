import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from tools.base_mod.collect_update_101_server_assets import (
    PACKS, parse_remote_paths, remote_root, collect,
)


class Update101AssetDiscoveryTests(TestCase):
    def test_refuses_path_escapes_or_unapproved_source_package(self):
        with self.assertRaises(ValueError):
            remote_root("jp.kn.trace.battlecats; rm -rf /")
        root=remote_root("jp.kn.trace.battlecats")
        good=root+"/subdir/MNumberServer.list"
        self.assertEqual(parse_remote_paths(good,root=root,filename=PACKS[0]),[good])
        for bad in ("/sdcard/Other/MNumberServer.list",
                    root+"/../elsewhere/MNumberServer.list",
                    root+"/MNumberServer.pack"):
            with self.assertRaises(ValueError):
                parse_remote_paths(bad,root=root,filename=PACKS[0])

    def test_inventory_no_device_write_and_missing_refuses_pull(self):
        root=remote_root("jp.kn.trace.battlecats")
        def runner(argv, *, timeout=45):
            self.assertEqual(argv[:4],["adb","-s","test-device","shell"])
            self.assertEqual(argv[4], "find")
            name=argv[-1]
            if name=="WImageDataServer.pack":
                return ""
            return root+"/"+name+"\n"
        with patch("tools.base_mod.collect_update_101_server_assets.run_checked",runner):
            with tempfile.TemporaryDirectory() as d:
                target=Path(d)/"pack-copy"
                result=collect("adb","test-device","jp.kn.trace.battlecats",target)
                self.assertFalse(result["downloaded_locally"])
                self.assertEqual(result["missing"],["WImageDataServer.pack"])
                self.assertFalse(target.exists())
                with self.assertRaisesRegex(ValueError,"missing original Server packs"):
                    collect("adb","test-device","jp.kn.trace.battlecats",target,pull=True)
                self.assertFalse(target.exists())


if __name__=="__main__":
    import unittest
    unittest.main()