import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from tools.pc_viewer import verified_viewer_root,ARCHIVE


class ViewerIntegrityTests(unittest.TestCase):
    def test_installed_viewer_must_match_the_verified_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder); parent=state/'runtime/scrcpy'; parent.mkdir(parents=True)
            root=parent/'scrcpy-win64-v5.0.1'; root.mkdir()
            exe=root/'scrcpy.exe'; exe.write_bytes(b'local synthetic test only')
            archive=parent/ARCHIVE
            with ZipFile(archive,'w') as z: z.write(exe,'scrcpy-win64-v5.0.1/scrcpy.exe')
            with patch('tools.pc_viewer.ARCHIVE_SHA256',hashlib.sha256(archive.read_bytes()).hexdigest()):
                self.assertEqual(verified_viewer_root(state),root)
                (root/'winmm.dll').write_bytes(b'unapproved DLL must never load')
                with self.assertRaisesRegex(ValueError,'UNAPPROVED_INSTALLED_FILES'): verified_viewer_root(state)
                (root/'winmm.dll').unlink()
                exe.write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError,'INSTALLED_FILE_SHA_MISMATCH'): verified_viewer_root(state)

    def test_archive_paths_cannot_escape_even_with_a_trusted_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder); parent=state/'runtime/scrcpy'; parent.mkdir(parents=True)
            archive=parent/ARCHIVE
            with ZipFile(archive,'w') as z: z.writestr('../escape.exe',b'never extract or execute')
            with patch('tools.pc_viewer.ARCHIVE_SHA256',hashlib.sha256(archive.read_bytes()).hexdigest()):
                with self.assertRaisesRegex(ValueError,'ARCHIVE_PATH_UNSAFE'): verified_viewer_root(state)
