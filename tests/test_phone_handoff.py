import io
import hashlib
from pathlib import Path
import tarfile
import tempfile
import unittest
from types import SimpleNamespace
from tools.phone_handoff import validated_tar_manifest,research_package_exists,collect_pc_private_state


class FakePcFiles:
    def __init__(self, corrupt=False, manifest_error=False, pull_failures=0):
        self.contents={'files/SAVE_DATA':b'synthetic-save',
                       'files/kneekura-local-signing-v1.pk8':b'synthetic-key',
                       'files/.cache/'+('x'*140)+'/'+('y'*140)+'+#':b'synthetic-cache'}
        self.corrupt=corrupt
        self.manifest_error=manifest_error
        self.pull_failures=pull_failures
        self.pulls=[]

    def adb(self,*args,**kwargs):
        if args[0]=='shell':
            return SimpleNamespace(stdout=''.join(hashlib.sha256(raw).hexdigest()+'  '+name+'\n'
                for name,raw in self.contents.items()),returncode=0,
                stderr='sha256sum: omitted-file: read error' if self.manifest_error else '')
        assert args[:2]==('pull','-Z')
        self.pulls.append(args)
        if len(self.pulls)<=self.pull_failures:
            return SimpleNamespace(stdout='',stderr='synthetic transport failure',returncode=1)
        name=args[2].split('/jp.kn.local.battlecats/',1)[1]
        Path(args[3]).write_bytes(b'corrupt' if self.corrupt else self.contents[name])
        return SimpleNamespace(stdout='',stderr='1 file pulled',returncode=0)


class PhoneArchiveTests(unittest.TestCase):
    def test_pc_export_rejects_partial_manifest_with_sha_error_before_pulls(self):
        with tempfile.TemporaryDirectory() as folder:
            lab=FakePcFiles(manifest_error=True)
            with self.assertRaisesRegex(ValueError,'MANIFEST_FAILED'):
                collect_pc_private_state(lab,Path(folder))
            self.assertEqual(lab.pulls,[])

    def test_pc_export_retries_transport_error_but_requires_verified_content(self):
        with tempfile.TemporaryDirectory() as folder:
            lab=FakePcFiles(pull_failures=1)
            archive,files,manifest=collect_pc_private_state(lab,Path(folder))
            self.assertEqual(validated_tar_manifest(archive),manifest)
            self.assertEqual(len(lab.pulls),4)

    def test_pc_export_stops_after_three_transport_failures(self):
        with tempfile.TemporaryDirectory() as folder:
            lab=FakePcFiles(pull_failures=3)
            with self.assertRaisesRegex(ValueError,'PULL_FAILED'):
                collect_pc_private_state(lab,Path(folder))
            self.assertEqual(len(lab.pulls),3)
            self.assertFalse((Path(folder)/'pc-app-state.tar').exists())

    def test_pc_export_uses_verified_flat_objects_for_long_cache_names(self):
        with tempfile.TemporaryDirectory() as folder:
            lab=FakePcFiles()
            archive,files,manifest=collect_pc_private_state(lab,Path(folder))
            self.assertEqual(validated_tar_manifest(archive),manifest)
            self.assertEqual(set(files),set(lab.contents))
            self.assertTrue(all(len(path.name)==68 for path in files.values()))
            self.assertEqual(len(lab.pulls),3)

    def test_pc_export_refuses_corrupt_file_before_phone_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'FILE_SHA_MISMATCH'):
                collect_pc_private_state(FakePcFiles(corrupt=True),Path(folder))

    def test_pc_export_rejects_traversal_before_any_pull(self):
        with tempfile.TemporaryDirectory() as folder:
            lab=FakePcFiles();lab.contents['files/../../foreign']=b'unsafe'
            with self.assertRaisesRegex(ValueError,'UNSAFE_ENTRY'):
                collect_pc_private_state(lab,Path(folder))
            self.assertEqual(lab.pulls,[])

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
