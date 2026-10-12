"""Explicit owner USB handoff to a NEW isolated app on a physical ARM64 phone.

No adb root, publisher data, uninstall, clear, or existing-app overwrite.
Private app state travels only in app-own run-as stdin; never public staging.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import shlex
import subprocess
import tarfile
from uuid import uuid4
from zipfile import ZipFile

from tools.pc_lab import Lab, PACKAGE, write_json
from tools.base_mod.phone_manifest import add_phone_debuggable
from tools.base_mod.repack import JP_15_7_1_SPLITS, baseline_resign, sha256_file, _is_signature_entry

LABEL='にーくらホワイトにゃんこ'


def research_package_exists(user_listing,global_dump):
    return bool(user_listing.strip() or re.search(r'^\s*Package \['+re.escape(PACKAGE)+r'\]',global_dump,re.M))


def prepare(lab):
    source=lab.verify_build()
    if not source['presign'].get('pc_independent_boot_trust'):
        raise ValueError('PHONE_HANDOFF_REQUIRES_INDEPENDENT_PC_BUILD')
    root=lab.state/'phone-builds'/('phone-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:8])
    root.mkdir(parents=True)
    unsigned=root/'unsigned'; unsigned.mkdir()
    for name in JP_15_7_1_SPLITS:
        shutil.copyfile(Path(source['directory'])/name,unsigned/name)
    base=unsigned/'base.apk'; pending=unsigned/'base-phone.apk'
    with ZipFile(base) as original,ZipFile(pending,'w') as target:
        original_manifest=original.read('AndroidManifest.xml')
        changed=add_phone_debuggable(original_manifest,app_label=LABEL)
        for info in original.infolist():
            if _is_signature_entry(info.filename): continue
            target.writestr(info,changed if info.filename=='AndroidManifest.xml' else original.read(info))
    # Exact entry-by-entry change gate, before signing.
    with ZipFile(base) as original,ZipFile(pending) as target:
        names={n for n in original.namelist() if not _is_signature_entry(n)}
        if names!=set(target.namelist()): raise ValueError('PHONE_PAYLOAD_ENTRY_SET_CHANGED')
        for name in names:
            expected=changed if name=='AndroidManifest.xml' else original.read(name)
            if target.read(name)!=expected: raise ValueError('PHONE_UNRELATED_PAYLOAD_CHANGE')
    pending.replace(base)
    store,password=lab.key(); os.environ['JAVA_HOME']=str(lab.java)
    tools=lab.sdk/'build-tools/35.0.0'
    destination=root/'signed'
    signed=baseline_resign(unsigned,destination,keystore=store,alias='pc-lab',storepass=password,
                           zipalign=str(tools/'zipalign.exe'),apksigner=str(tools/'apksigner.bat'))
    password=None
    if signed['signer_certificate_sha256']!=source['signing']['signer_certificate_sha256']:
        raise ValueError('PHONE_DEVELOPMENT_SIGNER_CHANGED')
    proof=dict(schema='kneekura-owner-phone-build-v1',directory=str(destination),
               source_build=Path(source['directory']).name,package=PACKAGE,label=LABEL,
               debug_app_own_provisioning=True,no_internet_permission=True,
               game_payload_unchanged_except_manifest=True,
               manifest_source_sha256=hashlib.sha256(original_manifest).hexdigest(),
               manifest_output_sha256=hashlib.sha256(changed).hexdigest(),signing=signed)
    write_json(root/'PHONE-BUILD.json',proof)
    write_json(lab.state/'latest-phone-build.json',proof)
    return proof


def validated_tar_manifest(path):
    result={}; total=0
    with tarfile.open(path,'r:') as archive:
        for member in archive:
            name=PurePosixPath(member.name)
            if (name.is_absolute() or '..' in name.parts or not name.parts
                    or name.parts[0] not in ('files','shared_prefs') or '\\' in member.name
                    or any(c in member.name for c in '\r\n') or not (member.isfile() or member.isdir())):
                raise ValueError('PHONE_PRIVATE_ARCHIVE_UNSAFE_ENTRY')
            if member.isfile():
                normalized=name.as_posix()
                total+=member.size
                if len(result)>=10000 or total>2*1024**3: raise ValueError('PHONE_PRIVATE_ARCHIVE_SIZE_UNSAFE')
                if normalized in result: raise ValueError('PHONE_PRIVATE_ARCHIVE_DUPLICATE')
                stream=archive.extractfile(member); digest=hashlib.sha256()
                for block in iter(lambda:stream.read(1024*1024),b''): digest.update(block)
                result[normalized]=digest.hexdigest()
    if 'files/SAVE_DATA' not in result or 'files/kneekura-local-signing-v1.pk8' not in result:
        raise ValueError('PHONE_PRIVATE_ARCHIVE_REQUIRED_LOCAL_STATE_MISSING')
    return result


def deploy_new(lab,serial,*,resume_empty=False):
    if not re.fullmatch(r'[A-Za-z0-9_-]{4,80}',serial) or serial.startswith('emulator-'):
        raise ValueError('PHONE_PHYSICAL_USB_SERIAL_REQUIRED')
    def adb(*args,check=True,timeout=120,input=None):
        return lab.command([lab.adb_bin,'-s',serial,*args],check=check,timeout=timeout,
                           binary=input is not None,input=input)
    if adb('get-state').stdout.strip()!='device': raise ValueError('PHONE_NOT_AUTHORIZED')
    if adb('shell','getprop','ro.kernel.qemu').stdout.strip()=='1': raise ValueError('PHONE_EMULATOR_REFUSED')
    if 'arm64-v8a' not in adb('shell','getprop','ro.product.cpu.abilist').stdout.split(','):
        raise ValueError('PHONE_ARM64_REQUIRED')
    exists=research_package_exists(adb('shell','pm','list','packages','-u',PACKAGE).stdout,
                                  adb('shell','dumpsys','package',PACKAGE).stdout)
    if exists and not resume_empty:
        raise ValueError('PHONE_EXISTING_RESEARCH_PACKAGE_REFUSED_NO_OVERWRITE')
    if resume_empty and not exists: raise ValueError('PHONE_RESUME_REQUIRES_INSTALLED_CANDIDATE')
    official_before=adb('shell','pm','path','jp.co.ponos.battlecats',check=False).stdout
    build=json.loads((lab.state/'latest-phone-build.json').read_text(encoding='utf-8'))
    folder=Path(build['directory']).resolve()
    if not folder.is_relative_to((lab.state/'phone-builds').resolve()): raise ValueError('PHONE_BUILD_OUTSIDE_PRIVATE')
    expected={p['name']:p['output_sha256'] for p in build['signing']['splits']}
    if set(expected)!=set(JP_15_7_1_SPLITS) or any(sha256_file(folder/n)!=expected[n] for n in expected):
        raise ValueError('PHONE_CANDIDATE_HASH_MISMATCH')
    if not resume_empty:
        adb('install-multiple','--no-streaming',*[folder/n for n in JP_15_7_1_SPLITS],timeout=300)
    paths=adb('shell','pm','path',PACKAGE).stdout.splitlines()
    if len(paths)!=6: raise ValueError('PHONE_SIX_INSTALLED_SPLITS_REQUIRED')
    installed={p.rsplit('/',1)[-1]:adb('shell','sha256sum',p.removeprefix('package:')).stdout.split()[0] for p in paths}
    if installed!=expected: raise ValueError('PHONE_INSTALLED_SPLIT_SHA_MISMATCH')
    adb('shell','run-as',PACKAGE,'id')  # refuses a non-debuggable app; no root.
    adb('shell','am','force-stop',PACKAGE)
    if adb('shell',f"run-as {PACKAGE} sh -c 'test ! -e files/SAVE_DATA'").returncode:
        raise ValueError('PHONE_EXISTING_SAVE_REFUSED')
    # adb on Windows does not reliably support long paths. Firebase filenames
    # already exceed100chars; keep this owner-only private workspace short.
    private=lab.state/('phone-transfer-'+uuid4().hex[:8]); private.mkdir()
    sid=re.search(r'S-1-5(?:-\d+)+',lab.command(['whoami','/user','/fo','csv','/nh']).stdout)[0]
    lab.command(['icacls',private,'/inheritance:r','/grant:r','*'+sid+':(OI)(CI)F'])
    archive=private/'pc-app-state.tar'
    with lab.app_operation_lock():
        lab.identity(); lab.adb('shell','am','force-stop',PACKAGE)
        if lab.adb('shell','pidof',PACKAGE,check=False).stdout.strip(): raise ValueError('PC_APP_NOT_STOPPED')
        tree=private/'tree'; tree.mkdir()
        for leaf in ('files','shared_prefs'):
            lab.adb('pull','-Z','/data/user/0/'+PACKAGE+'/'+leaf,tree,timeout=600)
        with tarfile.open(archive,'w') as output:
            for leaf in ('files','shared_prefs'): output.add(tree/leaf,arcname=leaf)
        manifest=validated_tar_manifest(archive)
        checks=''.join(digest+'  '+name+'\n' for name,digest in sorted(manifest.items())).encode('utf-8')
        lab.adb('shell','-T',f"cd /data/user/0/{PACKAGE}; sha256sum -c - >/dev/null",binary=True,input=checks,timeout=120)
    stage='.kneekura-phone-stage-'+uuid4().hex
    adb('shell',f"run-as {PACKAGE} sh -c 'umask 077; mkdir {stage}; mkdir {stage}/files {stage}/shared_prefs'")
    for index,(name,digest) in enumerate(sorted(manifest.items())):
        target=stage+'/'+name
        command='umask 077; mkdir -p '+shlex.quote(str(PurePosixPath(target).parent))+'; base64 -d > '+shlex.quote(target)
        adb('shell','-T',f'run-as {PACKAGE} sh -c '+shlex.quote(command),
            input=base64.b64encode((tree/name).read_bytes())+b'\n',timeout=180)
        if (index+1)%100==0: print('PHONE_PRIVATE_FILES_TRANSFERRED '+str(index+1),flush=True)
    checks=''.join(digest+'  '+name+'\n' for name,digest in sorted(manifest.items())).encode('utf-8')
    adb('shell','-T',f"run-as {PACKAGE} sh -c 'cd {stage}; sha256sum -c - >/dev/null'",input=checks,timeout=120)
    if adb('shell','pidof',PACKAGE,check=False).stdout.strip(): raise ValueError('PHONE_APP_LAUNCHED_DURING_PROVISION')
    publish=(f'test ! -e files/SAVE_DATA && '
             f'(test ! -d files || test -z "$(ls -A files)") && '
             f'(test ! -d shared_prefs || test -z "$(ls -A shared_prefs)") && '
             f'mv -T {stage}/files files && mv -T {stage}/shared_prefs shared_prefs')
    adb('shell',f'run-as {PACKAGE} sh -c '+shlex.quote(publish))
    adb('shell','-T',f"run-as {PACKAGE} sh -c 'sha256sum -c - >/dev/null'",input=checks,timeout=120)
    if adb('shell','pm','path','jp.co.ponos.battlecats',check=False).stdout!=official_before:
        raise ValueError('PHONE_OFFICIAL_INSTALLATION_CHANGED')
    proof=dict(schema='kneekura-owner-phone-deploy-v1',package=PACKAGE,label=LABEL,
               installed_splits_sha256=installed,private_state_files_verified=len(manifest),
               private_state_tar_sha256=sha256_file(archive),root_used=False,
               official_package_paths_unchanged=True,source_pc_save_sha256=manifest['files/SAVE_DATA'],
               fresh_install_only=True,phone_gameplay_acceptance=False)
    write_json(folder.parent/'PHONE-DEPLOY.json',proof)
    write_json(lab.state/'latest-phone-deploy.json',proof)
    return proof


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('action',choices=('prepare','deploy-new','resume-empty'))
    parser.add_argument('--serial')
    args=parser.parse_args()
    lab=Lab(args.state,Path(os.environ['LOCALAPPDATA'])/'Android/Sdk',Path(os.environ['PROGRAMFILES'])/'Java/jdk-17')
    if args.action=='prepare':
        result=prepare(lab); print('PHONE_CANDIDATE_VERIFIED '+Path(result['directory']).parent.name)
    else:
        result=deploy_new(lab,args.serial or '',resume_empty=args.action=='resume-empty')
        print('PHONE_NEW_ISOLATED_APP_AND_PRIVATE_STATE_VERIFIED files='+str(result['private_state_files_verified']))


if __name__=='__main__': main()
