"""Apply the initial profile once, only to the dedicated rooted PC AVD.

SAVE bytes, credentials, backups and transaction journals remain private.
An interrupted rename is recovered from hashes; consumed items are never reset.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from tools.pc_lab import PACKAGE, parse_installed_paths, verify_installed_hashes
from tools.base_mod.pc_initial_profile import build_profile, load_reference


def journal_action(journal, identity_digest, live_digest):
    if journal.get('schema') != 'kneekura-pc-profile-transaction-v1':
        raise ValueError('PC_PROFILE_TRANSACTION_SCHEMA_CHANGED')
    if journal.get('boot_identity_sha256') != identity_digest:
        raise ValueError('PC_PROFILE_IDENTITY_CHANGED')
    if journal.get('status') == 'APPLIED':
        return 'NO_REFILL'
    if journal.get('status') == 'PREPARED':
        if live_digest == journal.get('output_sha256'): return 'COMMIT_ONLY'
        if live_digest == journal.get('source_sha256'): return 'APPLY'
    raise ValueError('PC_PROFILE_TRANSACTION_CHANGED')


def atomic_json(path, value):
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                                     prefix='.profile-',suffix='.pending',delete=False) as stream:
        temporary=Path(stream.name)
        json.dump(value,stream,ensure_ascii=False,indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary,path)


def install_once(lab):
    with lab.app_operation_lock():
        return _install_once_locked(lab)


def _install_once_locked(lab):
    import msvcrt
    lab.identity()
    build=lab.verify_build()
    if build['presign'].get('pc_independent_boot_trust') is None:
        raise ValueError('PC_PROFILE_REQUIRES_INDEPENDENT_LOCAL_BOOT')
    if lab.adb('shell','id','-u').stdout.strip() != '0':
        raise ValueError('PC_PROFILE_REQUIRES_DEDICATED_ROOTED_AVD')
    paths=parse_installed_paths(lab.adb('shell','pm','path',PACKAGE).stdout.splitlines())
    actual={p.rsplit('/',1)[-1]:lab.adb('shell','sha256sum',p).stdout.split()[0] for p in paths}
    verify_installed_hashes({p['name']:p['output_sha256'] for p in build['signing']['splits']},actual)
    root=lab.state/'profiles'
    root.mkdir(exist_ok=True)
    if root.is_symlink(): raise ValueError('PC_PROFILE_PRIVATE_PATH_LINK_REFUSED')
    with (root/'.initial-v1.lock').open('a+b') as guard:
        guard.seek(0)
        msvcrt.locking(guard.fileno(),msvcrt.LK_LOCK,1)
        try:
            return _install_locked(lab,root,build)
        finally:
            guard.seek(0)
            msvcrt.locking(guard.fileno(),msvcrt.LK_UNLCK,1)


def _install_locked(lab,root,build):
    directory=f'/data/user/0/{PACKAGE}/files'
    save_path=directory+'/SAVE_DATA'
    identity_path=directory+'/kneekura-local-boot-v1.record'
    for path in (save_path,identity_path):
        if lab.adb('shell',f'test -f {path} && ! test -L {path}',check=False).returncode:
            raise ValueError('PC_PROFILE_APP_FILE_LINK_OR_MISSING')
    identity_digest=lab.adb('shell','sha256sum',identity_path).stdout.split()[0]
    live_digest=lab.adb('shell','sha256sum',save_path).stdout.split()[0]
    journal_path=root/'initial-v1.json'
    if journal_path.is_symlink(): raise ValueError('PC_PROFILE_JOURNAL_LINK_REFUSED')
    if journal_path.exists():
        journal=json.loads(journal_path.read_text(encoding='utf-8'))
        action=journal_action(journal,identity_digest,live_digest)
        if action=='NO_REFILL':
            return dict(status='PC_PROFILE_ALREADY_APPLIED_NO_REFILL',progress_preserved=True)
    else:
        journal=None
        action='PREPARE'
    lab.adb('shell','am','force-stop',PACKAGE)
    if lab.adb('shell','pidof',PACKAGE,check=False).stdout.strip():
        raise ValueError('PC_PROFILE_APP_STILL_RUNNING')
    # Re-read after stopping: the app may have saved while the first SHA ran.
    live_digest=lab.adb('shell','sha256sum',save_path).stdout.split()[0]
    if journal is not None:
        action=journal_action(journal,identity_digest,live_digest)
        tx=root/journal['transaction_directory']
        if not tx.resolve().is_relative_to(root.resolve()) or tx.is_symlink():
            raise ValueError('PC_PROFILE_TRANSACTION_PATH_OUTSIDE_PRIVATE')
        candidate=tx/'initial-SAVE_DATA'
        if hashlib.sha256(candidate.read_bytes()).hexdigest()!=journal['output_sha256']:
            raise ValueError('PC_PROFILE_PREPARED_BYTES_CHANGED')
        backup=tx/'original-SAVE_DATA'
        if (backup.is_symlink() or not backup.is_file()
                or hashlib.sha256(backup.read_bytes()).hexdigest()!=journal['source_sha256']):
            raise ValueError('PC_PROFILE_PREPARED_BACKUP_MISSING_OR_CHANGED')
    else:
        tx=root/('initial-v1-'+uuid.uuid4().hex)
        tx.mkdir()
        source=lab.adb('exec-out','cat',save_path,binary=True).stdout
        if hashlib.sha256(source).hexdigest()!=live_digest:
            raise ValueError('PC_PROFILE_SOURCE_CHANGED_AFTER_STOP')
        with (tx/'original-SAVE_DATA').open('xb') as backup:
            backup.write(source)
            backup.flush()
            os.fsync(backup.fileno())
        if hashlib.sha256((tx/'original-SAVE_DATA').read_bytes()).hexdigest()!=live_digest:
            raise ValueError('PC_PROFILE_BACKUP_BYTES_DIFFER')
        inputs=json.loads((lab.state/'inputs.json').read_text(encoding='utf-8'))
        references=lab.state/'source-references'
        core=load_reference(references/'bcsfe-pinned/src',references/'parser-dependencies',
                            references/'parser-state')
        output,receipt=build_profile(source,Path(inputs['owner_zip']),core)
        candidate=tx/'initial-SAVE_DATA'
        with candidate.open('xb') as pending_output:
            pending_output.write(output)
            pending_output.flush()
            os.fsync(pending_output.fileno())
        atomic_json(tx/'PROFILE.json',receipt)
        journal=dict(schema='kneekura-pc-profile-transaction-v1',status='PREPARED',
                     boot_identity_sha256=identity_digest,source_sha256=live_digest,
                     output_sha256=receipt['output_sha256'],transaction_directory=tx.name,
                     installed_build=Path(build['directory']).name,automatic_refill=False)
        atomic_json(journal_path,journal)
        action='APPLY'
    if action=='APPLY':
        match=re.fullmatch(r'package:'+re.escape(PACKAGE)+r' uid:(1[0-9]{4})',
            lab.adb('shell','cmd','package','list','packages','-U',PACKAGE).stdout.strip())
        if not match: raise ValueError('PC_PROFILE_PACKAGE_UID_UNAVAILABLE')
        pending=directory+'/.kneekura-profile-v1.pending'
        if lab.adb('shell',f'test -L {pending}',check=False).returncode==0:
            raise ValueError('PC_PROFILE_PENDING_PATH_LINK_REFUSED')
        lab.adb('shell','-T',f'umask 077; base64 -d > {pending}',binary=True,
                input=base64.b64encode(candidate.read_bytes())+b'\n')
        lab.adb('shell','chown',f'{match[1]}:{match[1]}',pending)
        lab.adb('shell','chmod','600',pending)
        lab.adb('shell','restorecon','-F',pending)
        if lab.adb('shell','sha256sum',pending).stdout.split()[0]!=journal['output_sha256']:
            raise ValueError('PC_PROFILE_PENDING_BYTES_DIFFER_NO_RENAME')
        # Also stop a manual launch that is outside the host's cooperative lock.
        lab.adb('shell','am','force-stop',PACKAGE)
        if lab.adb('shell','pidof',PACKAGE,check=False).stdout.strip():
            raise ValueError('PC_PROFILE_APP_STILL_RUNNING_NO_RENAME')
        if lab.adb('shell','sha256sum',save_path).stdout.split()[0]!=journal['source_sha256']:
            raise ValueError('PC_PROFILE_TARGET_CHANGED_NO_RENAME')
        # Same-directory rename; root/AVD/package checks precede this authorized update.
        lab.adb('shell','mv','-T',pending,save_path)
        lab.adb('shell','sync')
    if lab.adb('shell','sha256sum',save_path).stdout.split()[0]!=journal['output_sha256']:
        raise ValueError('PC_PROFILE_APPLIED_BYTES_DIFFER')
    journal['status']='APPLIED'
    atomic_json(journal_path,journal)
    return dict(status='PC_PROFILE_INITIALIZED_ONCE',private_backup_verified=True,
                categories=20,owned=677,excluded_stage_rewards=158,story_stages=192,
                automatic_refill=False)
