"""Only a dedicated local authority key may replace the isolated trust asset."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import hashlib
import unittest

from tools.base_mod.pc_boot_trust import replace_local_boot_public_key, validate_public_key


class PcBootTrustTests(unittest.TestCase):
    def test_public_only_exact_replacement_and_no_extra_asset_changes(self):
        try:
            from Crypto.PublicKey import RSA
        except ImportError:
            self.skipTest('existing RSA tooling unavailable')
        key = RSA.generate(4096)
        public = key.public_key().export_key('PEM')
        fingerprint = validate_public_key(public)
        self.assertEqual(fingerprint, hashlib.sha256(key.public_key().export_key('DER')).hexdigest())
        with TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'split_InstallPack.apk'
            with ZipFile(archive, 'w') as out:
                out.writestr('assets/nyanko-service-prd.pem', b'synthetic old public key')
                out.writestr('assets/unchanged.pack', b'synthetic data')
            with self.assertRaises(ValueError):
                replace_local_boot_public_key(archive, public, dedicated_pc=False)
            proof = replace_local_boot_public_key(archive, public, dedicated_pc=True)
            self.assertEqual(proof['public_key_sha256'], fingerprint)
            with ZipFile(archive) as result:
                self.assertEqual(result.read('assets/unchanged.pack'), b'synthetic data')
                self.assertEqual(result.read('assets/nyanko-service-prd.pem'), public)
                self.assertEqual(len(result.namelist()), 2)
        for invalid in (key.export_key('PEM'), b'invalid', RSA.generate(2048).public_key().export_key('PEM')):
            with self.subTest(kind=len(invalid)), self.assertRaises(ValueError):
                validate_public_key(invalid)


if __name__ == '__main__':
    unittest.main()
