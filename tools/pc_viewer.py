"""Pinned official viewer for ONLY the dedicated local Android emulator."""
from pathlib import Path, PurePosixPath
import hashlib
import subprocess
from zipfile import ZipFile

VERSION='5.0.1'
ARCHIVE='scrcpy-win64-v5.0.1.zip'
ARCHIVE_SHA256='b12a2c4ee8be317422451fc7dcf8ee20a71b5ea7ef9ad73ddd825a25316227a5'
SOURCE_URL='https://github.com/Genymobile/scrcpy/releases/tag/v5.0.1'


def verified_viewer_root(state: Path) -> Path:
    parent=state/'runtime/scrcpy'
    root=parent/'scrcpy-win64-v5.0.1'
    if parent.is_symlink() or parent.is_junction() or not parent.resolve().is_relative_to(state.resolve()):
        raise ValueError('PC_VIEWER_INSTALLED_PATH_UNSAFE')
    archive=parent/ARCHIVE
    if archive.is_symlink() or not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest()!=ARCHIVE_SHA256:
        raise ValueError('PC_VIEWER_OFFICIAL_ARCHIVE_SHA_MISMATCH')
    expected=set()
    with ZipFile(archive) as source:
        if len(source.infolist())>100 or sum(i.file_size for i in source.infolist())>128*1024*1024:
            raise ValueError('PC_VIEWER_ARCHIVE_SIZE_UNSAFE')
        for member in source.infolist():
            name=PurePosixPath(member.filename)
            if name.is_absolute() or '..' in name.parts or ':' in member.filename or '\\' in member.filename:
                raise ValueError('PC_VIEWER_ARCHIVE_PATH_UNSAFE')
            target=parent.joinpath(*name.parts)
            if not target.resolve().is_relative_to(root.resolve()) or target.is_symlink() or target.is_junction():
                raise ValueError('PC_VIEWER_INSTALLED_PATH_UNSAFE')
            if member.is_dir(): continue
            expected.add(target.relative_to(root).as_posix())
            if not target.is_file() or target.read_bytes()!=source.read(member):
                raise ValueError('PC_VIEWER_INSTALLED_FILE_SHA_MISMATCH')
    actual=set()
    for target in [root,*root.rglob('*')]:
        if target.is_symlink() or target.is_junction() or not target.resolve().is_relative_to(root.resolve()):
            raise ValueError('PC_VIEWER_INSTALLED_PATH_UNSAFE')
        if target.is_file(): actual.add(target.relative_to(root).as_posix())
    if actual!=expected:
        raise ValueError('PC_VIEWER_UNAPPROVED_INSTALLED_FILES')
    if not (root/'scrcpy.exe').is_file(): raise ValueError('PC_VIEWER_EXECUTABLE_MISSING')
    return root


def start_viewer(lab):
    from tools.pc_lab import SERIAL
    lab.identity()
    lab.verify_build()
    root=verified_viewer_root(lab.state)
    env=lab.env.copy()
    env['ADB']=str(lab.adb_bin)
    with (lab.state/'runtime/viewer.log').open('ab') as output:
        viewer=subprocess.Popen([str(root/'scrcpy.exe'),'-s',SERIAL,'--no-audio',
                                  '--no-clipboard-autosync','--window-title=Kneekura PC local test'],
                                 cwd=root,env=env,stdout=output,stderr=output,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
    return viewer
