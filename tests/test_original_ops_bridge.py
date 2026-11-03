"""Batch wiring gates: original callbacks, local scope, immutable bundle trust."""
from pathlib import Path
import unittest
from tools.base_mod.inject_java_http_bridge import render_bridge_source

ROOT=Path(__file__).resolve().parents[1]


class OriginalOpsBridgeTests(unittest.TestCase):
    def setUp(self):
        self.template=(ROOT/'bridge/java/MyActivity.java.in').read_text(encoding='utf-8')
        self.options=dict(flavor='local-research',enabled=False,pc_boot_authority=True,
                          pc_jni_scene_observer=True,offline_393_import_enabled=True)

    def test_original_operations_are_default_off(self):
        source=render_bridge_source(self.template,**self.options)
        self.assertNotIn('KneekuraOriginalOps',source)
        self.assertIn('return false;',source[source.index('public boolean isNetworkAvailable'):])

    def test_local_operations_use_original_request_registry_and_gl_callback(self):
        source=render_bridge_source(self.template,pc_original_ops_sha256='a'*64,**self.options)
        self.assertIn('KneekuraOriginalOps',source)
        self.assertIn('a'*64,source)
        self.assertIn('originalOps().available()',source)
        self.assertIn('originalOps().response(method, requestUrl',source)
        self.assertIn('requestMap.put(Integer.valueOf(requestId), request)',source)
        self.assertIn('view.queueEvent',source)
        self.assertIn('jp.co.ponos.battlecats.MyActivity.newResponse',source)
        self.assertIn('original-local-ops-response-v1 returned',source)
        self.assertIn('original-local-ops-enqueued-v1',source)
        self.assertIn('kneekuraOriginalLoginProgressSafe',source)
        self.assertIn('if (flag1)',source)
        ordered=[source.index('jp.co.ponos.battlecats.MyActivity.'+name+'(')
                 for name in ('onResponseCodeHeaders','onResponseData','onResponseFinish')]
        self.assertEqual(ordered,sorted(ordered))
        self.assertNotIn('__KNEEKURA_',source)

    def test_event_final_clock_response_also_preserves_original_stream_callbacks(self):
        source=render_bridge_source(self.template,**self.options)
        self.assertNotIn('KneekuraOriginalOps',source)
        self.assertIn('if (flag1)',source)
        for method in ('onResponseCodeHeaders','onResponseData','onResponseFinish'):
            self.assertIn('jp.co.ponos.battlecats.MyActivity.'+method+'(',source)
        self.assertIn('original-local-pc-http-stream-v1',source)
        self.assertIn('isExactLocalClockStreamRequest',source)
        self.assertIn('"time".equals(KneekuraPcBootAuthority.operation',source)

    def test_operations_cannot_enable_original_or_nonlocal_shipping_flavors(self):
        for flavor in ('research','personal','practice'):
            with self.subTest(flavor=flavor),self.assertRaises(ValueError):
                render_bridge_source(self.template,flavor=flavor,enabled=False,
                                     pc_original_ops_sha256='a'*64)
        for digest in ('','x'*64,'a'*63):
            with self.subTest(digest=digest),self.assertRaises(ValueError):
                render_bridge_source(self.template,pc_original_ops_sha256=digest,**self.options)

    def test_bundle_without_original_boot_boundary_is_rejected(self):
        with self.assertRaises(ValueError):
            render_bridge_source(self.template,flavor='local-research',enabled=False,
                                 pc_original_ops_sha256='a'*64)


if __name__=='__main__':unittest.main()
