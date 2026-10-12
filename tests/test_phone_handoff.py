import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from tools.phone_handoff import validated_tar_manifest,research_package_exists


class PhoneArchiveTests(unittest.TestCase):
    def test_other_android_users_also_block_new_install(self):
        self.assertTrue(research_package_exists('', '  Package [jp.kn.local.battlecats] (abc):\n User 0: installed=false\n User 10: installed=true'))
        self.assertFalse(research_package_exists('', 'Unable to find package: jp.kn.local.battlecats'))
        self.assertFalse(research_package_exists('', 'Package [jp.co.ponos.battlecats] (abc):'))

    def test_private_state_hashes_and_unsafe_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.tar'
            def make(extra=None):
                with tarfile.open(path,'w') as archive:
                    for name in ('files/SAVE_DATA','files/kneekura-local-signing-v1.pk8'):
                        entry=tarfile.TarInfo(name); entry.size=9
                        archive.addfile(entry,io.BytesIO(b'synthetic'))
                    if extra: archive.addfile(extra,io.BytesIO(b'') if extra.isfile() else None)
            make()
            self.assertEqual(len(validated_tar_manifest(path)),2)
            for name in ('../escape','/files/absolute','files/a/../../escape','cache/foreign'):
                make(tarfile.TarInfo(name))
                with self.assertRaisesRegex(ValueError,'UNSAFE_ENTRY'): validated_tar_manifest(path)
            link=tarfile.TarInfo('files/link'); link.type=tarfile.SYMTYPE; link.linkname='/data/system'
            make(link)
            with self.assertRaisesRegex(ValueError,'UNSAFE_ENTRY'): validated_tar_manifest(path)
            make(tarfile.TarInfo('./files/SAVE_DATA'))
            with self.assertRaisesRegex(ValueError,'DUPLICATE'): validated_tar_manifest(path)
