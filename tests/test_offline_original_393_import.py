"""Synthetic tests; no original APK, keys, phone, SAVE or network."""
from __future__ import annotations
from hashlib import md5
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from tools.base_mod import offline_server_import_manifest as manifest

ROOT=Path(__file__).resolve().parents[1]

class OriginalOffline393Tests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="kneekura-393-synthetic-")
        self.addCleanup(tmp.cleanup)
        self.apk=Path(tmp.name)/"synthetic-installpack.apk"
        with ZipFile(self.apk,"w") as z:
            for i in range(35):
                z.writestr(f"assets/download_{i}.tsv",b"\t1\t"+b"0"*32+b"\n")

    def original(self, source):
        self.assertEqual(source,self.apk)
        return {f"S{i:03d}Server.list":(3,md5(b"foo").hexdigest())
                for i in range(358)}

    def test_source_index_contains_358_original_members_and_35_tsv(self):
        with patch.object(manifest,"owner_manifest",side_effect=self.original):
            rows=manifest.original_offline_asset_manifest(self.apk)
            rendered=manifest.compiled_java_metadata(self.apk)
        self.assertEqual(len(rows),393)
        self.assertEqual(len(set(x[0] for x in rows)),393)
        self.assertEqual(len([r for r in rows if r[0].endswith(".tsv")]),35)
        self.assertTrue(rendered.startswith('"') and rendered.endswith('"'))
        self.assertIn("download_34.tsv",rendered)
        self.assertIn("S357Server.list",rendered)
        self.assertNotIn("SAVE_DATA",rendered)
        self.assertNotIn("../",rendered)

    def test_source_index_missing_member_rejected(self):
        incomplete={f"S{i:03d}Server.list":(3,md5(b"foo").hexdigest())
                    for i in range(357)}
        with patch.object(manifest,"owner_manifest",return_value=incomplete):
            with self.assertRaisesRegex(ValueError,"358\\+35"):
                manifest.original_offline_asset_manifest(self.apk)

    def test_feature_off_by_default_and_requires_research(self):
        bridge=(ROOT/"tools/base_mod/inject_java_http_bridge.py").read_text()
        self.assertIn("offline_import_installpack: Path | None = None",bridge)
        self.assertIn("original 393-asset import requires strict",bridge)
        self.assertIn("KneekuraOfflineAssetImporter.java.in",bridge)
        builder=(ROOT/"tools/base_mod/build_owned_static_http_bridge.py").read_text()
        self.assertIn("research_offline_393_asset_import: bool = False",builder)
        self.assertIn("--research-offline-393-asset-import",builder)
        self.assertIn('original / "split_InstallPack.apk"',builder)

    def test_java_checks_all_393_before_copy_and_never_references_save(self):
        java=(ROOT/"bridge/java/KneekuraOfflineAssetImporter.java.in").read_text()
        for item in ("if (!ENABLED)","ORIGINAL_INDEX","rows.length != 393",
                     'MessageDigest.getInstance("MD5")',
                     "original-local-import-v1 completed-393",
                     "external.getCanonicalPath()","File.createTempFile",
                     "output.getFD().sync()"):
            self.assertIn(item,java)
        self.assertLess(java.index("393-source-md5-pass"),
                        java.index("for (OriginalFile entry : sources) {\n            copyOne"))
        self.assertNotIn('new File(root, "SAVE_DATA")',java)
        self.assertNotIn("HttpURLConnection",java)

    def test_offline_request_probe_logs_fixed_kinds_only(self):
        """The next on-device diagnostic must never log a URL or credential.

        Instrument only the explicit 393-import profile; leave network
        disabled and the original no-import profile unchanged.
        """
        code = (ROOT / "bridge/java/MyActivity.java.in").read_text(
            encoding="utf-8")
        self.assertIn("classifyDeniedOriginalHttp(String requestUrl)", code)
        self.assertIn('return "asset-cdn";', code)
        self.assertIn('return "backup";', code)
        self.assertIn('return "publisher-other";', code)
        self.assertIn('return "external-other";', code)
        self.assertIn('return "malformed";', code)
        self.assertIn('if (LOCAL_RESEARCH_IMPORT_OWNER_ASSETS)', code)
        self.assertIn('debugResearch("original-local-http-kind-v1 "', code)
        self.assertIn('throw new IllegalStateException("original local research HTTP disabled")', code)
        self.assertNotIn('debugResearch(requestUrl)', code)
        self.assertNotIn('debugResearch(method)', code)
        self.assertLess(
            code.index('debugResearch("original-local-http-kind-v1 "'),
            code.index('throw new IllegalStateException("original local research HTTP disabled")'),
        )

    def test_strict_local_exact_backup_original_network_failure_callback(self):
        """A previously observed backup request may complete locally using
        the exact ORIGINAL Java fallback, not pretend a publisher success.
        All unknown requests must still be denied with no super fallthrough.
        """
        source=(ROOT/"bridge/java/MyActivity.java.in").read_text(encoding="utf-8")
        self.assertIn('final boolean originalBackupFailureShape = isExactBackupRequest(',source)
        self.assertIn(
            '!(LOCAL_RESEARCH_DENY_HTTP && LOCAL_RESEARCH_IMPORT_OWNER_ASSETS)',
            source)
        self.assertIn(
            'if (LOCAL_RESEARCH_DENY_HTTP && !originalBackupFailureShape)',source)
        self.assertIn('if (!originalBackupFailureShape)',source)
        self.assertIn('original-local-backup-failure-fallback-v1 completed',source)
        self.assertIn('original-local-backup-failure-fallback-v1 unavailable',source)
        self.assertIn('throw new IllegalStateException("original local backup fallback unavailable")',source)
        self.assertIn('jp.co.ponos.battlecats.MyActivity.newResponse(',source)
        self.assertIn('                            "{}",',source)
        self.assertIn('                            true);',source)
        self.assertIn('view.queueEvent(new Runnable()',source)
        self.assertLess(
            source.index('if (LOCAL_RESEARCH_DENY_HTTP && !originalBackupFailureShape)'),
            source.index('if (!originalBackupFailureShape)'))
        self.assertLess(
            source.index('throw new IllegalStateException("original local backup fallback unavailable")'),
            source.rindex('return super.newHttpRequest('))
        self.assertNotIn('super.newHttpRequest(',source[
            source.index('if (LOCAL_RESEARCH_DENY_HTTP && !originalBackupFailureShape)'):
            source.index('if (!originalBackupFailureShape)')])

    def test_owner_signing_opt_in_separate_from_android_installer(self):
        owner=(ROOT/"tools/base_mod/OWNER-READY-TO-SIGN.ps1").read_text(encoding="utf-8-sig")
        signer=(ROOT/"tools/base_mod/BUILD-OWNER-RESEARCH-PAIR.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("[switch]$EnableOfflineServerImport",owner)
        self.assertIn("-EnableOfflineServerImport:$EnableOfflineServerImport",owner)
        self.assertIn("'--research-offline-393-asset-import'",signer)
        self.assertNotIn("install-multiple",signer)

if __name__=="__main__":unittest.main()
