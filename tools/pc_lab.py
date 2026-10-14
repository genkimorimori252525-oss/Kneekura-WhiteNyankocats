"""Windows-only, unattended PC research lab. Raw evidence and keys stay private.

This operates ONLY kneekura-pc-api35 on emulator-5580; never a physical device.
Run with ``py -3.12 -B -m tools.pc_lab --state <private/pc-lab> <command>``.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import time
import uuid
from zipfile import ZipFile

from tools.base_mod.repack import JP_15_7_1_SPLITS, baseline_resign, sha256_file
from tools.base_mod.prepare_original_research_presign import prepare_unsigned_research
from tools.base_mod.audit_original_offline_boot_events import summarize_runtime_events
from tools.base_mod.summarize_original_crash_capture import summarize as summarize_crash
from tools.base_mod.offline_server_import_manifest import original_offline_asset_manifest
from tools.pc_lab_diagnostics import observer_summary, anr_trace_paths, verify_artifacts, scene97_task_summary
from tools.pc_lab_diagnostics import pc_balance_summary

AVD = 'kneekura-pc-api35'
SERIAL = 'emulator-5580'
PACKAGE = 'jp.kn.local.battlecats'
NDK = '27.2.12479018'
REPO = Path(__file__).resolve().parents[1]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def validate_identity(serial: str, avd_name: str) -> None:
    if serial != SERIAL or avd_name.splitlines()[0].strip() != AVD:
        raise ValueError('PC_LAB_IDENTITY_MISMATCH_NO_DEVICE_MUTATION')


def scope_research_log(source: str, observed_pids: set[int], *, version: int = 2) -> str:
    """Corroborate log PIDs with package starts; don't trust public tags alone."""
    verified = set(observed_pids)
    verified.update(int(p) for p in re.findall(
        r'Start proc (\d+):jp\.kn\.local\.battlecats/', source))
    if version not in (1, 2):
        raise ValueError('PC_CAPTURE_UNKNOWN_LOG_SCOPE_VERSION')
    normalized = [re.sub(r'^(\d\d-\d\d\s+\S+)\s+[+-]\d{4}\s+', r'\1 ', line)
                  for line in source.splitlines()]
    tag_pattern = (r'^\d\d-\d\d\s+\S+\s+(\d+)\s+\d+\s+[VDIWEF]\s+(\S+):'
                   if version == 1 else
                   r'^\d\d-\d\d\s+\S+\s+(\d+)\s+\d+\s+[VDIWEF]\s+(\S+)\s*:')
    verified_dumps = set()
    if version == 2:
        for line in normalized:
            match = re.match(tag_pattern, line)
            inner = re.search(r'\bpid[: ]+\s*(\d+)\b', line)
            if match and match[2] == 'DEBUG' and inner and int(inner[1]) in verified:
                verified_dumps.add(int(match[1]))
    kept = []
    for line in normalized:
        match = re.match(tag_pattern, line)
        if not match:
            continue
        pid, tag = int(match[1]), match[2]
        if version == 2:
            # Downstream aggregate parsers require tag immediately followed by ':'.
            # Keep historical v1 bytes unchanged for existing capture verification.
            line = line[:match.end(2)] + line[match.end(2):].lstrip()
        if tag == 'KNEEKURA_STATIC_HTTP' and pid in verified:
            kept.append(line)
        elif tag == 'ActivityManager' and PACKAGE in line:
            kept.append(line)
        elif tag in ('libc', 'DEBUG', 'AndroidRuntime'):
            inner = re.search(r'\bpid (\d+)\b', line)
            if pid in verified or (inner and int(inner[1]) in verified) or (
                    tag == 'DEBUG' and pid in verified_dumps):
                kept.append(line)
    return '\n'.join(kept)


def bound_to_barriers(source: str, run_id: str) -> str:
    lines = source.splitlines()
    stamp = re.compile(r'^(\d\d-\d\d\s+\d\d:\d\d:\d\d\.\d{6})\s+\+0000\s+')
    bounds = {}
    for line in lines:
        match = stamp.match(line)
        for label in ('START', 'END'):
            if match and line.endswith('KNEEKURA_PC_CAPTURE: ' + run_id + ':' + label):
                bounds[label] = match[1]
    if set(bounds) != {'START', 'END'}:
        return ''
    begin, end = bounds['START'], bounds['END']
    return '\n'.join(line for line in lines if (match := stamp.match(line)) and (
        begin <= match[1] <= end if begin <= end else match[1] >= begin or match[1] <= end))


def has_log_loss(source: str, stderr: str) -> bool:
    # "will be dropped" in an IPC diagnostic does not describe the log stream.
    return bool(re.search(r'\b[VDIWEF]\s+chatty\s*:', source)
                or re.search(r'\b[VDIWEF]\s+logd\s*:.*\b(?:dropped|lost)\b', source, re.I)
                or re.search(r'unexpected EOF|failed to read|dropped \d+ (?:lines|messages)',
                             stderr, re.I))


def summarize_java_crash(scoped: str) -> dict:
    classes = Counter()
    fatal = 0
    zero_id = False
    receiver = False
    for line in scoped.splitlines():
        if 'AndroidRuntime:' not in line:
            continue
        msg = line.split('AndroidRuntime:', 1)[1].strip()
        fatal += int(msg.startswith('FATAL EXCEPTION:'))
        match = re.match(r'^(?:Caused by: )?([A-Za-z_$][A-Za-z0-9_.$]{1,160}(?:Exception|Error)):', msg)
        if match:
            classes[match[1]] += 1
        zero_id |= 'String resource ID #0x0' in msg
        receiver |= 'jp.co.ponos.battlecats.ReceiverInitAlarm' in msg
    return dict(fatal_exception_events=fatal, exception_classes=dict(classes),
                string_resource_id_zero_observed=zero_id,
                original_receiver_init_alarm_mentioned=receiver,
                exception_messages_or_stack_paths_retained=False)


def capture_quality(evidence: dict) -> str:
    if (evidence['start_barrier'] and evidence['end_barrier']
            and evidence['launch_ok'] and evidence['collector_exit'] == 0
            and evidence['screenshots'] >= 2 and not evidence['errors']
            and not evidence['log_loss']):
        return 'COMPLETE_BOUNDED_CAPTURE'
    return 'INCOMPLETE_CAPTURE'


def verify_installed_hashes(expected: dict[str, str], actual: dict[str, str]) -> None:
    if expected != actual:
        raise ValueError('PC_LAB_INSTALLED_SPLIT_BYTES_DIFFER_NO_LAUNCH')


def parse_installed_paths(entries: list[str]) -> list[str]:
    paths = [entry.strip().removeprefix('package:') for entry in entries]
    if any(not re.fullmatch(r'/data/app/[A-Za-z0-9_.+=/~-]+\.apk', path) for path in paths):
        raise ValueError('PC_LAB_UNEXPECTED_INSTALLED_APK_PATH')
    return paths


def dpapi(data: bytes, *, decrypt: bool = False) -> bytes:
    """Current Windows user's DPAPI, no password on disk or command line."""
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_char))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    target = Blob()
    api = ctypes.windll.crypt32
    if decrypt:
        ok = api.CryptUnprotectData(ctypes.byref(source), None, None, None, None,
                                   1, ctypes.byref(target))
    else:
        ok = api.CryptProtectData(ctypes.byref(source), 'Kneekura PC development key',
                                 None, None, None, 1, ctypes.byref(target))
    if not ok:
        raise RuntimeError('PC_LAB_DPAPI_FAILED')
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        ctypes.windll.kernel32.LocalFree(ctypes.cast(target.data, ctypes.c_void_p))


def confirm_log_barrier(path: Path, token: str, emit, alive, *,
                        timeout: float = 10, retry_interval: float = 1,
                        poll_interval: float = .1) -> bool:
    """Confirm the collector saw a marker, including slow ADB subscription.

    A marker emitted before logcat attaches may be excluded by its -T tail.
    Retransmit within the bounded wait; absence remains an explicit failure.
    """
    deadline=time.monotonic()+timeout
    next_emit=0.0
    while alive() and time.monotonic()<deadline:
        if token in path.read_text(encoding='utf-8',errors='replace'):
            return True
        now=time.monotonic()
        if now>=next_emit:
            emit();next_emit=now+retry_interval
        time.sleep(poll_interval)
    return False


class Lab:
    def __init__(self, state: Path, sdk: Path, java: Path):
        self.state = state.resolve()
        if 'private' not in self.state.parts or state.is_symlink():
            raise ValueError('PC_LAB_STATE_MUST_BE_PRIVATE')
        self.sdk, self.java = sdk.resolve(), java.resolve()
        self.state.mkdir(parents=True, exist_ok=True)
        self.env = dict(os.environ, JAVA_HOME=str(self.java),
                        ANDROID_AVD_HOME=str(self.state / 'avd'),
                        ANDROID_SDK_ROOT=str(self.sdk))
        self.adb_bin = self.sdk / 'platform-tools/adb.exe'

    def command(self, argv: list, *, check: bool = True, timeout: int = 120,
                binary: bool = False, env: dict | None = None, input: bytes | None = None):
        result = subprocess.run([str(a) for a in argv], capture_output=True,
                                timeout=timeout, env=env or self.env,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                text=not binary, encoding=None if binary else 'utf-8',
                                errors=None if binary else 'replace', input=input)
        if check and result.returncode:
            # Tool output remains private, and command/env secrets never propagate.
            raise RuntimeError(f'PC_LAB_TOOL_FAILED_{Path(str(argv[0])).name}')
        return result

    def adb(self, *argv, **kwargs):
        return self.command([self.adb_bin, '-s', SERIAL, *argv], **kwargs)

    def identity(self) -> None:
        result = self.adb('emu', 'avd', 'name')
        validate_identity(SERIAL, result.stdout)
        if self.adb('shell', 'getprop', 'sys.boot_completed').stdout.strip() != '1':
            raise RuntimeError('PC_LAB_NOT_BOOTED')

    @contextmanager
    def app_operation_lock(self):
        """Serialize guest install/provision/launch/capture and profile mutation."""
        import msvcrt
        path = self.state / '.app-operation-v1.lock'
        if path.is_symlink():
            raise ValueError('PC_LAB_APP_OPERATION_LOCK_LINK_REFUSED')
        with path.open('a+b') as guard:
            if guard.seek(0, 2) == 0:
                guard.write(b'\0')
                guard.flush()
            guard.seek(0)
            try:
                msvcrt.locking(guard.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise RuntimeError('PC_LAB_APP_OPERATION_BUSY_NO_MUTATION') from None
            try:
                yield
            finally:
                guard.seek(0)
                msvcrt.locking(guard.fileno(), msvcrt.LK_UNLCK, 1)

    def setup(self) -> dict:
        for name in ('avd', 'runtime', 'keys', 'builds', 'captures'):
            (self.state / name).mkdir(exist_ok=True)
        required = [self.sdk / f'ndk/{NDK}/build/cmake/android.toolchain.cmake',
                    self.sdk / 'cmake/3.22.1/bin/cmake.exe']
        if not all(p.is_file() for p in required):
            raise RuntimeError('PC_LAB_INSTALL_NDK_27_2_AND_CMAKE_3_22_FIRST')
        avd_path = self.state / f'avd/{AVD}.avd'
        if not avd_path.is_dir():
            result = subprocess.run([
                str(self.sdk / 'cmdline-tools/latest/bin/avdmanager.bat'),
                'create', 'avd', '-n', AVD, '-k',
                'system-images;android-35;google_apis;x86_64', '-p', str(avd_path),
                '-d', 'pixel_7'], input='no\n', text=True, capture_output=True,
                env=self.env, creationflags=subprocess.CREATE_NO_WINDOW, timeout=120)
            if result.returncode:
                raise RuntimeError('PC_LAB_AVD_CREATE_FAILED')
        if self.adb('emu', 'avd', 'name', check=False, timeout=10).returncode:
            with (self.state / 'runtime/emulator-stdout.log').open('ab') as out, \
                    (self.state / 'runtime/emulator-stderr.log').open('ab') as err:
                process = subprocess.Popen([
                    str(self.sdk / 'emulator/emulator.exe'), '-avd', AVD, '-port', '5580',
                    '-no-window', '-no-audio', '-no-snapshot', '-gpu', 'software',
                    '-no-boot-anim'], env=self.env, stdout=out, stderr=err,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                write_json(self.state / 'runtime/emulator-process.json',
                           {'pid': process.pid, 'started_utc': utc()})
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                check = self.adb('shell', 'getprop', 'sys.boot_completed',
                                 check=False, timeout=10)
                if check.returncode == 0 and check.stdout.strip() == '1':
                    break
                time.sleep(2)
        self.identity()
        for service in ('wifi', 'data'):
            self.adb('shell', 'svc', service, 'disable')
        info = {key: self.adb('shell', 'getprop', key).stdout.strip() for key in (
            'ro.build.fingerprint', 'ro.product.cpu.abilist', 'ro.dalvik.vm.native.bridge',
            'ro.build.version.sdk', 'ro.ndk_translation.version')}
        info.update(schema='kneekura-pc-lab-environment-v1', avd=AVD, serial=SERIAL,
                    sdk=str(self.sdk), ndk=NDK, observed_utc=utc())
        write_json(self.state / 'environment.json', info)
        return info

    def key(self) -> tuple[Path, str]:
        folder = self.state / 'keys'
        folder.mkdir(exist_ok=True)
        store, secret = folder / 'pc-development.p12', folder / 'password.dpapi'
        if store.exists() != secret.exists():
            raise RuntimeError('PC_LAB_INCOMPLETE_KEY_PAIR_NO_REPLACEMENT')
        if not store.exists():
            user = os.environ['USERDOMAIN'] + '\\' + os.environ['USERNAME']
            self.command(['icacls.exe', folder, '/inheritance:r', '/grant:r',
                          user + ':(OI)(CI)F'])
            password = secrets.token_urlsafe(40)
            child_env = dict(self.env, KNEEKURA_PC_NEW_KEY_PASSWORD=password)
            self.command([self.java / 'bin/keytool.exe', '-genkeypair', '-noprompt',
                          '-keystore', store, '-storetype', 'PKCS12', '-alias', 'pc-lab',
                          '-keyalg', 'RSA', '-keysize', '3072', '-validity', '36500',
                          '-dname', 'CN=Kneekura PC Local Development',
                          '-storepass:env', 'KNEEKURA_PC_NEW_KEY_PASSWORD'], env=child_env)
            secret.write_bytes(dpapi(password.encode()))
        return store, dpapi(secret.read_bytes(), decrypt=True).decode()

    def build(self, owner_zip: Path, official_aar: Path, *, local_boot: bool = False,
              balance: bool = False, original_ops_bundle: bytes | None = None) -> dict:
        if balance and not local_boot:
            raise ValueError('PC_BALANCE_REQUIRES_LOCAL_BOOT')
        if original_ops_bundle is not None:
            if not local_boot:
                raise ValueError('ORIGINAL_OPS_REQUIRE_LOCAL_BOOT')
            from tools.liveops.original_ops_bundle import validate_bundle
            validate_bundle(original_ops_bundle)
        write_json(self.state / 'inputs.json', {'owner_zip': str(owner_zip.resolve()),
                                               'official_aar': str(official_aar.resolve())})
        private = REPO / 'private'
        private.mkdir(exist_ok=True)
        build_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
        scratch = private / ('pc-native-' + build_id)
        scratch.mkdir()
        balance_inputs = None
        if balance:
            from tools.base_mod.pc_balance_assets import prepare_assets, load_pinned_assets
            cached = prepare_assets(owner_zip, self.state.parent / 'original-jp1571-verified-server-cache',
                                    self.state / 'balance-cache')
            balance_inputs = scratch / 'approved-balance'
            balance_inputs.mkdir()
            for name, payload in load_pinned_assets(cached).items():
                (balance_inputs / name).write_bytes(payload)
        # Archive the exact inputs, including uncommitted/new source, before
        # compiling. Refuse publication if any source changes during the build.
        source_files = [p for base in ('native/kneekura-shim', 'bridge/java', 'tools/base_mod',
                                     'tools/liveops', 'tools/localcore')
                        for p in (REPO / base).rglob('*')
                        if p.is_file() and p.suffix in ('.c', '.h', '.txt', '.in', '.java', '.py', '.ps1')]
        source_files += [REPO / p for p in ('tools/pc_lab.py', 'tools/pc_lab_diagnostics.py',
                                           'tools/pc_profile_install.py', 'tools/pc_viewer.py', 'tools/PC-LAB.ps1')]
        source_files += sorted((REPO / 'ops/seasons').glob('*.json'))
        source_hashes = {p.relative_to(REPO).as_posix(): sha256_file(p) for p in source_files}
        source_archive = scratch / 'BUILD-SOURCE.zip'
        with ZipFile(source_archive, 'w') as archive:
            for path in sorted(source_files):
                archive.write(path, path.relative_to(REPO).as_posix())
        native_build = scratch / 'cmake'
        cmake = self.sdk / 'cmake/3.22.1/bin/cmake.exe'
        native_root = REPO / 'native/kneekura-shim'
        arguments = [cmake, '-S', native_root, '-B', native_build, '-G', 'Ninja',
                     '-DCMAKE_MAKE_PROGRAM=' + str(self.sdk / 'cmake/3.22.1/bin/ninja.exe'),
                     '-DCMAKE_TOOLCHAIN_FILE=' + str(self.sdk / f'ndk/{NDK}/build/cmake/android.toolchain.cmake'),
                     '-DANDROID_ABI=arm64-v8a', '-DANDROID_PLATFORM=android-29',
                     '-DKNEEKURA_RESEARCH_SCENE_WITNESS=ON',
                     '-DKNEEKURA_RESEARCH_PC_JNI_SCENE_OBSERVER=ON',
                     '-DKNEEKURA_RESEARCH_PC_BALANCE=' + ('ON' if balance else 'OFF'),
                     '-DKNEEKURA_RESEARCH_VIRGIN_SAVE_TRIAL=OFF', '-DCMAKE_BUILD_TYPE=Release']
        config = self.command(arguments, check=False)
        compiler_log = scratch / 'compiler.log'
        compiler_log.write_text(config.stdout + config.stderr, encoding='utf-8')
        if config.returncode:
            raise RuntimeError('PC_LAB_CMAKE_CONFIG_FAILED_PRIVATE_COMPILER_LOG_SAVED')
        compile_result = self.command([cmake, '--build', native_build], check=False)
        with compiler_log.open('a', encoding='utf-8') as stream:
            stream.write(compile_result.stdout + compile_result.stderr)
        if compile_result.returncode:
            raise RuntimeError('PC_LAB_CMAKE_BUILD_FAILED_PRIVATE_COMPILER_LOG_SAVED')
        shim = native_build / 'libkneekura.so'
        data = shim.read_bytes()
        if (data[:5] != b'\x7fELF\x02' or int.from_bytes(data[18:20], 'little') != 183
                or b'original-native-scene97-resolver-v1' not in data
                or b'kneekura-original-virgin-save-trial-v1' in data):
            raise RuntimeError('PC_LAB_PASSIVE_ARM64_CONTRACT_FAILED')
        tree = hashlib.sha256()
        for path in sorted(p for p in native_root.rglob('*') if p.is_file()):
            tree.update(path.relative_to(native_root).as_posix().encode())
            tree.update(path.read_bytes())
        commit = self.command(['git', '-C', REPO, 'rev-parse', 'HEAD']).stdout.strip()
        proof = dict(schema='local-pc-research-passive-shim-v1', elf_abi='arm64-v8a',
                     pc_jni_scene_observer_enabled=True,
                     original_save_writer_enabled=False, fixed_error_markers_compiled=True,
                     git_commit=commit, source_tree_sha256=tree.hexdigest(),
                     sha256=sha256_file(shim), ndk_version=NDK)
        readelf = self.sdk / f'ndk/{NDK}/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-readelf.exe'
        notes = self.command([readelf, '--notes', shim]).stdout
        found = re.search(r'Build ID: ([0-9a-f]+)', notes)
        if not found:
            raise RuntimeError('PC_LAB_NATIVE_BUILD_ID_MISSING')
        proof['elf_build_id'] = found[1]
        receipt = scratch / 'LOCAL_PC_PASSIVE_SHIM_RECEIPT.json'
        write_json(receipt, proof)
        aar = private / 'pc-official-shadowhook-2.0.1.aar'
        if not aar.exists():
            shutil.copyfile(official_aar, aar)
        tools = self.sdk / 'build-tools/35.0.0'
        unsigned_proof, unsigned_dir = prepare_unsigned_research(
            repo=REPO, owner_export=owner_zip, passive_shim=shim,
            passive_receipt=receipt, official_aar=aar, javac=str(self.java / 'bin/javac.exe'),
            d8=str(tools / 'd8.bat'), android_jar=str(self.sdk / 'platforms/android-35/android.jar'),
            offline_393_import=True, allow_local_pc=True, pc_jni_scene_observer=True,
            pc_boot_authority=local_boot,
            pc_boot_public_key=self.local_boot_key().public_key().export_key('PEM') if local_boot else None,
            pc_balance_assets=balance_inputs, pc_original_ops_bundle=original_ops_bundle)
        store, password = self.key()
        destination = self.state / 'builds' / build_id
        destination.mkdir(parents=True)
        previous_java = os.environ.get('JAVA_HOME')
        os.environ['JAVA_HOME'] = str(self.java)
        try:
            signed = baseline_resign(unsigned_dir / 'original-JP1571-unsigned-six',
                                     destination, keystore=store, alias='pc-lab',
                                     storepass=password, zipalign=str(tools / 'zipalign.exe'),
                                     apksigner=str(tools / 'apksigner.bat'),
                                     source_export_sha256=sha256_file(owner_zip))
        finally:
            password = None
            if previous_java is None:
                os.environ.pop('JAVA_HOME', None)
            else:
                os.environ['JAVA_HOME'] = previous_java
        metadata = dict(schema='kneekura-pc-research-build-v1', directory=str(destination),
                        package=PACKAGE, native=proof, presign=unsigned_proof, signing=signed,
                        source_commit=commit, created_utc=utc())
        if any(sha256_file(REPO / name) != digest for name, digest in source_hashes.items()):
            raise RuntimeError('PC_LAB_SOURCE_CHANGED_DURING_BUILD_NO_PUBLICATION')
        shutil.copyfile(source_archive, destination / 'BUILD-SOURCE.zip')
        metadata['source_archive_sha256'] = sha256_file(destination / 'BUILD-SOURCE.zip')
        metadata['build_source_file_sha256'] = source_hashes
        if original_ops_bundle is not None:
            (destination / 'original-ops-bundle.json').write_bytes(original_ops_bundle)
        shutil.copyfile(shim, destination / 'libkneekura.so')
        write_json(destination / 'PC-BUILD.json', metadata)
        write_json(self.state / 'latest-build.json', metadata)
        return metadata

    def verify_build(self) -> dict:
        meta = json.loads((self.state / 'latest-build.json').read_text(encoding='utf-8'))
        folder = Path(meta['directory']).resolve()
        if not folder.is_relative_to(self.state / 'builds') or meta['package'] != PACKAGE:
            raise ValueError('PC_LAB_BUILD_OUTSIDE_PRIVATE_STATE')
        expected = {p['name']: p['output_sha256'] for p in meta['signing']['splits']}
        if set(expected) != set(JP_15_7_1_SPLITS) or any(
                sha256_file(folder / name) != expected[name] for name in JP_15_7_1_SPLITS):
            raise ValueError('PC_LAB_SIGNED_SPLIT_HASH_MISMATCH')
        if 'source_archive_sha256' in meta and sha256_file(folder / 'BUILD-SOURCE.zip') != meta['source_archive_sha256']:
            raise ValueError('PC_LAB_BUILD_SOURCE_ARCHIVE_HASH_MISMATCH')
        return meta

    def local_boot_key(self):
        from Crypto.PublicKey import RSA
        import msvcrt
        protected = self.state / 'keys/local-boot-rsa4096.dpapi'
        # The PC signing folder already has owner-only ACLs. Serialize host
        # generation across processes; never replace a published/corrupt key.
        self.key()
        with protected.with_suffix('.lock').open('a+b') as guard:
            if guard.tell() == 0:
                guard.write(b'\0')
                guard.flush()
            guard.seek(0)
            msvcrt.locking(guard.fileno(), msvcrt.LK_LOCK, 1)
            try:
                if not protected.exists():
                    key = RSA.generate(4096)
                    temporary = protected.with_name(protected.name + '.' + uuid.uuid4().hex + '.pending')
                    with temporary.open('xb') as output:
                        output.write(dpapi(key.export_key('DER', pkcs=8)))
                        output.flush()
                        os.fsync(output.fileno())
                    temporary.replace(protected)
            finally:
                guard.seek(0)
                msvcrt.locking(guard.fileno(), msvcrt.LK_UNLCK, 1)
        key = RSA.import_key(dpapi(protected.read_bytes(), decrypt=True))
        if not key.has_private() or key.size_in_bits() != 4096:
            raise ValueError('PC_LAB_LOCAL_BOOT_KEY_INVALID_NO_REPLACEMENT')
        return key

    def provision_local_boot_key(self, build: dict) -> None:
        trust = build['presign'].get('pc_independent_boot_trust')
        if trust is None:
            return
        self.identity()
        key = self.local_boot_key()
        if hashlib.sha256(key.public_key().export_key('DER')).hexdigest() != trust['public_key_sha256']:
            raise ValueError('PC_LAB_LOCAL_BOOT_KEY_DIFFERS_NO_LAUNCH')
        if self.adb('shell', 'id', '-u').stdout.strip() != '0':
            self.adb('root')
            self.adb('wait-for-device', timeout=30)
            self.identity()
        if self.adb('shell', 'id', '-u').stdout.strip() != '0':
            raise ValueError('PC_LAB_LOCAL_BOOT_KEY_REQUIRES_DEDICATED_USERDEBUG_AVD')
        uid = re.fullmatch(r'package:' + re.escape(PACKAGE) + r' uid:(1[0-9]{4})',
                          self.adb('shell', 'cmd', 'package', 'list', 'packages', '-U', PACKAGE).stdout.strip())
        if uid is None:
            raise ValueError('PC_LAB_LOCAL_BOOT_PACKAGE_UID_UNAVAILABLE')
        directory = f'/data/user/0/{PACKAGE}/files'
        self.adb('shell', 'mkdir', '-p', directory)
        self.adb('shell', 'chown', f'{uid[1]}:{uid[1]}', directory)
        self.adb('shell', 'chmod', '700', directory)
        remote = directory + '/kneekura-local-signing-v1.pk8'
        # Private bytes pass through stdin only, never argv, logcat, or a source ZIP.
        encoded = key.export_key('DER', pkcs=8)
        self.adb('shell', f'umask 077; touch {remote}; chmod 600 {remote}')
        # Windows adb shell binary stdin truncates at Ctrl-Z even with -T;
        # raw exec-in may close before all bytes reach the guest. ASCII stdin
        # with the framed shell protocol avoids both, then SHA proves delivery.
        self.adb('shell', '-T', f'base64 -d > {remote}', binary=True,
                 input=base64.b64encode(encoded) + b'\n')
        self.adb('shell', 'chown', f'{uid[1]}:{uid[1]}', remote)
        self.adb('shell', 'chmod', '600', remote)
        self.adb('shell', 'restorecon', '-F', directory, remote)
        observed = self.adb('shell', 'sha256sum', remote).stdout.split()[0]
        if observed != hashlib.sha256(encoded).hexdigest():
            raise ValueError('PC_LAB_LOCAL_BOOT_KEY_DELIVERY_BYTES_DIFFER_NO_LAUNCH')

    def provision_local_age_assets(self, build: dict) -> None:
        """Host caches public, pinned static bytes; the offline guest never fetches them."""
        if build['presign'].get('pc_independent_boot_trust') is None:
            return
        import urllib.request
        with ZipFile(Path(build['directory']) / 'BUILD-SOURCE.zip') as archive:
            source = archive.read('bridge/java/KneekuraPcAgeAssets.java.in').decode('utf-8')
        paths_match = re.search(r'PATHS = \{(.*?)\};', source, re.S)
        hashes_match = re.search(r'SHA256 = \{(.*?)\};', source, re.S)
        if not paths_match or not hashes_match:
            raise ValueError('PC_LAB_AGE_BUILD_INDEX_MISSING')
        paths = re.findall(r'"([^"\n]+)"', paths_match[1])
        hashes = re.findall(r'"([0-9a-f]{64})"', hashes_match[1])
        if len(paths) != 6 or len(hashes) != 6 or any(
                not re.fullmatch(r'(?:index\.html|css/(?:reset\.css|age\.css\?01)|'
                                 r'js/age\.js\?01|img/btn_ok_(?:on|off)\.png)', p) for p in paths):
            raise ValueError('PC_LAB_AGE_BUILD_INDEX_INVALID')
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, request, response, code, message, headers, newurl):
                raise ValueError('PC_LAB_AGE_SOURCE_REDIRECT_REFUSED')
        opener = urllib.request.build_opener(NoRedirect())
        cache = self.state / 'original-age-private-cache/kneekura-local-age-v1'
        cache.parent.mkdir(parents=True, exist_ok=True)
        import msvcrt
        guard = (cache.parent / '.age-cache.lock').open('a+b')
        if guard.tell() == 0:
            guard.write(b'\0')
            guard.flush()
        guard.seek(0)
        msvcrt.locking(guard.fileno(), msvcrt.LK_LOCK, 1)
        try:
            self._cache_local_age_assets(cache, paths, hashes, opener)
        finally:
            guard.seek(0)
            msvcrt.locking(guard.fileno(), msvcrt.LK_UNLCK, 1)
            guard.close()
        self.identity()
        uid = re.fullmatch(r'package:' + re.escape(PACKAGE) + r' uid:(1[0-9]{4})',
                          self.adb('shell', 'cmd', 'package', 'list', 'packages', '-U', PACKAGE).stdout.strip())
        if uid is None or self.adb('shell', 'id', '-u').stdout.strip() != '0':
            raise ValueError('PC_LAB_AGE_DEDICATED_GUEST_UID_REQUIRED')
        remote = f'/data/user/0/{PACKAGE}/files/kneekura-local-age-v1'
        self.adb('push', cache, f'/data/user/0/{PACKAGE}/files/', timeout=60)
        self.adb('shell', 'chown', '-R', f'{uid[1]}:{uid[1]}', remote)
        self.adb('shell', 'chmod', '-R', 'u=rwX,go=', remote)
        self.adb('shell', 'restorecon', '-RF', remote)
        for path, digest in zip(paths, hashes):
            if self.adb('shell', 'sha256sum', remote + '/' + path.split('?')[0]).stdout.split()[0] != digest:
                raise ValueError('PC_LAB_AGE_DELIVERY_HASH_MISMATCH_NO_LAUNCH')

    @staticmethod
    def _cache_local_age_assets(cache: Path, paths: list[str], hashes: list[str], opener) -> None:
        # Caller holds the cross-process cache lock. Never publish partial bytes.
        for path, digest in zip(paths, hashes):
            target = cache / path.split('?')[0]
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.is_file():
                with opener.open('https://ponosgames.com/information/appli/battlecats/age/' + path,
                                 timeout=20) as response:
                    raw = response.read(32769)
                if len(raw) > 32768 or hashlib.sha256(raw).hexdigest() != digest:
                    raise ValueError('PC_LAB_AGE_PUBLIC_SOURCE_CHANGED_NO_LAUNCH')
                temporary = target.with_name('.' + target.name + '.' + uuid.uuid4().hex + '.pending')
                with temporary.open('xb') as output:
                    output.write(raw)
                    output.flush()
                    os.fsync(output.fileno())
                if target.exists():
                    raise ValueError('PC_LAB_AGE_CACHE_CHANGED_BEFORE_PUBLICATION')
                temporary.replace(target)
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError('PC_LAB_AGE_PRIVATE_CACHE_CORRUPT_NO_REPLACEMENT')

    def stage_assets(self, build: dict) -> dict:
        """Reuse the pinned source index, push only to the dedicated guest's research app."""
        self.identity()
        # API35 scoped storage hides shell-owned files from the target app.
        # Only this userdebug disposable AVD may use root to assign ownership.
        if self.adb('shell', 'id', '-u').stdout.strip() != '0':
            self.adb('root')
            self.adb('wait-for-device', timeout=30)
            self.identity()
        if self.adb('shell', 'id', '-u').stdout.strip() != '0':
            raise RuntimeError('PC_LAB_DEDICATED_USERDEBUG_GUEST_ROOT_REQUIRED')
        uid_result = self.adb('shell', 'cmd', 'package', 'list', 'packages', '-U', PACKAGE)
        uid_match = re.fullmatch(r'package:' + re.escape(PACKAGE) + r' uid:(1[0-9]{4})',
                                 uid_result.stdout.strip())
        if uid_match is None:
            raise RuntimeError('PC_LAB_TARGET_APP_UID_NOT_EXACT')
        app_uid = uid_match[1]
        installpack = Path(build['directory']) / 'split_InstallPack.apk'
        entries = original_offline_asset_manifest(installpack)
        if len(entries) != 393:
            raise ValueError('PC_LAB_393_SOURCE_INDEX_MISMATCH')
        cache = self.state.parent / 'original-jp1571-verified-server-cache'
        staging = self.state / 'original-source-stage/kneekura-original-jp1571-stage'
        staging.mkdir(parents=True, exist_ok=True)
        expected = {}
        with ZipFile(installpack) as archive:
            for name, size, digest in entries:
                if not re.fullmatch(r'[A-Za-z0-9_.-]+', name):
                    raise ValueError('PC_LAB_UNSAFE_SOURCE_ASSET_NAME')
                if name.endswith('.tsv'):
                    raw = archive.read('assets/' + name)
                else:
                    raw = (cache / name).read_bytes()
                if len(raw) != size or hashlib.md5(raw).hexdigest() != digest:
                    raise ValueError('PC_LAB_ORIGINAL_ASSET_SIZE_OR_MD5_MISMATCH')
                target = staging / name
                if not target.exists() or hashlib.md5(target.read_bytes()).hexdigest() != digest:
                    target.write_bytes(raw)
                expected[name] = digest
        remote_parent = '/sdcard/Android/data/' + PACKAGE + '/files/'
        self.adb('shell', 'mkdir', '-p', remote_parent)
        self.adb('push', staging, remote_parent, timeout=300)
        owned_stage = '/data/media/0/Android/data/' + PACKAGE + '/files/' + staging.name
        self.adb('shell', 'chown', '-R', app_uid + ':1078', owned_stage)
        owners = self.adb('shell', 'stat', '-c', '%u', owned_stage + '/*').stdout.splitlines()
        if len(owners) != 393 or set(owners) != {app_uid}:
            raise RuntimeError('PC_LAB_STAGE_APP_OWNERSHIP_NOT_VERIFIED')
        result = self.adb('shell', 'md5sum', remote_parent + staging.name + '/*', timeout=120)
        actual = {line.split()[-1].rsplit('/', 1)[-1]: line.split()[0]
                  for line in result.stdout.splitlines() if len(line.split()) == 2}
        if actual != expected:
            raise ValueError('PC_LAB_REMOTE_393_MD5_MISMATCH')
        proof = dict(status='PC_LAB_EXTERNAL_393_MD5_VERIFIED', count=len(entries),
                     target_app_stage_ownership_verified=True,
                     installed_build=Path(build['directory']).name, observed_utc=utc())
        write_json(self.state / 'stage-assets.json', proof)
        return proof

    def capture(self, seconds: int, *, install: bool = False) -> dict:
        with self.app_operation_lock():
            return self._capture_locked(seconds, install=install)

    def _capture_locked(self, seconds: int, *, install: bool = False) -> dict:
        if not 10 <= seconds <= 1800:
            raise ValueError('PC_LAB_CAPTURE_DURATION_10_TO_1800_SECONDS')
        self.identity()
        build = self.verify_build()
        if ('pc_original_ops_bundle' in build.get('native',{}) and
                self.adb('shell','getprop','persist.sys.timezone').stdout.strip()!='Asia/Tokyo'):
            raise ValueError('PC_LAB_OPERATIONS_REQUIRE_ASIA_TOKYO')
        if install:
            self.adb('install-multiple', '-r', *[
                Path(build['directory']) / n for n in JP_15_7_1_SPLITS], timeout=180)
            self.stage_assets(build)
        installed = self.adb('shell', 'pm', 'path', PACKAGE).stdout.splitlines()
        if len(installed) != 6:
            raise RuntimeError('PC_LAB_EXPECTED_SIX_INSTALLED_SPLITS')
        actual = {}
        for remote in parse_installed_paths(installed):
            digest = self.adb('shell', 'sha256sum', remote).stdout.split()[0]
            actual[remote.rsplit('/', 1)[-1]] = digest
        verify_installed_hashes({p['name']: p['output_sha256']
                                 for p in build['signing']['splits']}, actual)
        self.adb('shell', 'am', 'force-stop', PACKAGE)
        self.provision_local_boot_key(build)
        self.provision_local_age_assets(build)
        run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
        folder = self.state / 'captures' / run_id
        folder.mkdir(parents=True)
        log = folder / 'logcat-threadtime.log'
        evidence = dict(schema='kneekura-pc-capture-v1', run_id=run_id, package=PACKAGE,
                        log_scope_version=2,
                        avd=AVD, serial=SERIAL, started_utc=utc(), build=build,
                        start_barrier=False, end_barrier=False, launch_ok=False,
                        collector_exit=None, screenshots=0, errors=[], log_loss=False,
                        pid_observations=[], device_metadata={}, screenshot_times=[],
                        installed_splits_sha256=actual)
        for name, command in {
                'device-clock-before': ['shell', 'date', '+%s.%N'],
                'device-timezone': ['shell', 'date', '+%z'],
                'properties': ['shell', 'getprop'],
                'package': ['shell', 'dumpsys', 'package', PACKAGE],
                'buffers-before': ['logcat', '-b', 'all', '-g'],
                'permissions': ['shell', 'ls', '-ld', '/data/tombstones'],
        }.items():
            result = self.adb(*command, check=False)
            (folder / (name + '.txt')).write_text(result.stdout + result.stderr, encoding='utf-8')
            evidence['device_metadata'][name] = result.returncode
            if result.returncode and name not in ('permissions',):
                evidence['errors'].append(name)
        diff = self.command(['git', '-C', REPO, 'diff', '--binary', 'HEAD']).stdout
        (folder / 'source.diff').write_text(diff, encoding='utf-8')
        untracked = self.command(['git', '-C', REPO, 'ls-files', '--others', '--exclude-standard']).stdout.splitlines()
        evidence['source_untracked_sha256'] = {p: sha256_file(REPO / p) for p in untracked if (REPO / p).is_file()}
        # Keep the new runner's exact bytes as well as hashes; it may still be untracked.
        with ZipFile(folder / 'source-snapshot.zip', 'w') as archive:
            for relative in ('tools/pc_lab.py', 'tools/pc_lab_diagnostics.py', 'tools/pc_profile_install.py', 'tools/pc_viewer.py', 'tools/PC-LAB.ps1',
                             'tools/base_mod/prepare_original_research_presign.py'):
                archive.write(REPO / relative, relative)
        if 'source_archive_sha256' in build:
            shutil.copyfile(Path(build['directory']) / 'BUILD-SOURCE.zip', folder / 'BUILD-SOURCE.zip')
        observed = set()

        def snapshot(label: str) -> None:
            started = utc()
            picture = self.adb('exec-out', 'screencap', '-p', binary=True, check=False)
            if picture.returncode == 0 and picture.stdout.startswith(b'\x89PNG\r\n\x1a\n'):
                (folder / (label + '.png')).write_bytes(picture.stdout)
                evidence['screenshots'] += 1
                evidence['screenshot_times'].append({'file': label + '.png',
                                                      'started_utc': started,
                                                      'finished_utc': utc()})
            else:
                evidence['errors'].append('screencap-' + label)

        def barrier(label: str, process) -> bool:
            token = run_id + ':' + label
            return confirm_log_barrier(log,token,
                lambda:self.adb('shell','log','-p','i','-t','KNEEKURA_PC_CAPTURE',token),
                lambda:process.poll() is None)

        with log.open('wb') as output, (folder / 'logcat-stderr.log').open('wb') as errors:
            collector = subprocess.Popen([str(self.adb_bin), '-s', SERIAL, 'logcat',
                                          '-b', 'all', '-v', 'threadtime', '-v', 'usec',
                                          '-v', 'UTC', '-T', '1'], stdout=output, stderr=errors,
                                         env=self.env, creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                evidence['start_barrier'] = barrier('START', collector)
                if not evidence['start_barrier']:
                    raise RuntimeError('PC_LAB_LOGCAT_START_BARRIER_MISSING')
                launch = self.adb('shell', 'am', 'start', '-W', '-n',
                                  PACKAGE + '/' + PACKAGE + '.MyActivity', check=False)
                (folder / 'launch.txt').write_text(launch.stdout + launch.stderr, encoding='utf-8')
                evidence['launch_ok'] = launch.returncode == 0 and 'Status: ok' in launch.stdout
                snapshot('launch')
                deadline = time.monotonic() + seconds
                screen_interval = 10 if seconds <= 300 else 60
                evidence['screenshot_interval_seconds'] = screen_interval
                next_screen = time.monotonic() + screen_interval
                while time.monotonic() < deadline:
                    pids = self.adb('shell', 'pidof', PACKAGE, check=False)
                    values = [int(v) for v in pids.stdout.split() if v.isdigit()]
                    observed.update(values)
                    evidence['pid_observations'].append({'utc': utc(), 'pids': values})
                    if pids.returncode not in (0, 1) or collector.poll() is not None:
                        evidence['errors'].append('device-or-collector-unavailable')
                        break
                    if time.monotonic() >= next_screen:
                        snapshot('screen-' + str(evidence['screenshots']))
                        next_screen = time.monotonic() + screen_interval
                    time.sleep(1)
                snapshot('final')
                evidence['end_barrier'] = barrier('END', collector)
            except Exception as exc:
                evidence['errors'].append(type(exc).__name__ + ':' + str(exc))
            finally:
                # Close only this collector through its PC ADB process, never clear buffers.
                collector.terminate()
                try:
                    collector.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    collector.kill()
                    collector.wait(timeout=10)
                # A Windows TerminateProcess code describes our expected stop, not logcat health.
                evidence['collector_exit'] = 0 if evidence['end_barrier'] else collector.returncode
        source = log.read_text(encoding='utf-8', errors='replace')
        # Bound analysis to this run; old buffered logs must not supply a missing witness.
        source = bound_to_barriers(source, run_id)
        # am start -W / screenshot may outlive a short-lived app process.
        # Package-start events inside these barriers also identify its PID.
        observed.update(int(pid) for pid in re.findall(
            r'Start proc (\d+):jp\.kn\.local\.battlecats/', source))
        stderr = (folder / 'logcat-stderr.log').read_text(encoding='utf-8', errors='replace')
        evidence['log_loss'] = has_log_loss(source, stderr)
        if stderr.strip():
            evidence['errors'].append('collector-stderr-nonempty')
        scoped = scope_research_log(source, observed, version=evidence['log_scope_version'])
        evidence['runtime_summary'] = summarize_runtime_events(scoped)
        evidence['observer_summary'] = observer_summary(scoped)
        evidence['scene97_task_summary'] = scene97_task_summary(scoped)
        evidence['pc_balance_summary'] = pc_balance_summary(scoped)
        evidence['crash_summary'] = summarize_crash(scoped)
        evidence['java_crash_summary'] = summarize_java_crash(scoped)
        for name, command in {
                'exit-info': ['shell', 'dumpsys', 'activity', 'exit-info', PACKAGE],
                'buffers-after': ['logcat', '-b', 'all', '-g'],
                'device-clock-after': ['shell', 'date', '+%s.%N'],
        }.items():
            result = self.adb(*command, check=False)
            (folder / (name + '.txt')).write_text(result.stdout + result.stderr, encoding='utf-8')
            evidence['device_metadata'][name] = result.returncode
            if result.returncode:
                evidence['errors'].append(name)
        evidence['finished_utc'] = utc()
        evidence['anr_trace_collection'] = []
        paths = []
        try:
            # Exit-info uses guest wall time; do not assume host/guest clocks agree.
            device_bounds = [datetime.fromtimestamp(float((folder / f'device-clock-{label}.txt').read_text(
                encoding='utf-8').strip()), timezone.utc).isoformat() for label in ('before', 'after')]
            paths = anr_trace_paths((folder / 'exit-info.txt').read_text(encoding='utf-8'), observed,
                                   *device_bounds,
                                   (folder / 'device-timezone.txt').read_text(encoding='utf-8').strip())
        except ValueError:
            evidence['errors'].append('own-anr-time-window-unavailable')
        for index, remote in enumerate(paths):
            self.identity()
            size = self.adb('shell', 'stat', '-c', '%s', remote, check=False)
            result = None
            if size.returncode == 0 and size.stdout.strip().isdigit() and 0 < int(size.stdout) <= 8 * 1024 * 1024:
                result = self.adb('pull', remote, folder / f'anr-{index + 1}.gz', check=False)
            available = result is not None and result.returncode == 0
            evidence['anr_trace_collection'].append({'file': f'anr-{index + 1}.gz', 'available': available})
            if not available:
                evidence['errors'].append('own-current-anr-trace-unavailable')
        evidence['status'] = capture_quality(evidence)
        evidence['artifacts_sha256'] = {p.name: sha256_file(p) for p in folder.iterdir() if p.is_file()}
        write_json(folder / 'CAPTURE.json', evidence)
        write_json(self.state / 'latest-capture.json', {'directory': str(folder), 'status': evidence['status']})
        return evidence

    def verify_capture(self, directory: Path | None = None) -> dict:
        """Offline evidence verification. Never launch, install, or contact ADB."""
        if directory is None:
            directory = Path(json.loads((self.state / 'latest-capture.json').read_text(encoding='utf-8'))['directory'])
        folder = directory.resolve(strict=True)
        if not folder.is_relative_to((self.state / 'captures').resolve()) or directory.is_symlink():
            raise ValueError('PC_CAPTURE_OUTSIDE_PRIVATE_STATE')
        proof = json.loads((folder / 'CAPTURE.json').read_text(encoding='utf-8'))
        if proof.get('schema') != 'kneekura-pc-capture-v1' or proof.get('run_id') != folder.name:
            raise ValueError('PC_CAPTURE_IDENTITY_MISMATCH')
        if (proof.get('package'), proof.get('avd'), proof.get('serial')) != (PACKAGE, AVD, SERIAL):
            raise ValueError('PC_CAPTURE_TARGET_IDENTITY_DIFFERS')
        count = verify_artifacts(folder, proof.get('artifacts_sha256'))
        required = {'logcat-threadtime.log', 'logcat-stderr.log', 'launch.txt', 'final.png',
                    'source.diff', 'source-snapshot.zip', 'device-clock-before.txt', 'device-clock-after.txt',
                    'package.txt', 'properties.txt', 'buffers-before.txt', 'buffers-after.txt', 'exit-info.txt'}
        if not required.issubset(proof['artifacts_sha256']):
            raise ValueError('PC_CAPTURE_REQUIRED_ARTIFACT_MISSING')
        pictures = {name for name in proof['artifacts_sha256'] if name.endswith('.png')}
        if (pictures != {item['file'] for item in proof['screenshot_times']}
                or len(pictures) != proof['screenshots']
                or any(not (folder / name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n') for name in pictures)):
            raise ValueError('PC_CAPTURE_SCREENSHOT_EVIDENCE_DIFFERS')
        raw = (folder / 'logcat-threadtime.log').read_text(encoding='utf-8')
        source = bound_to_barriers(raw, proof['run_id'])
        if not source:
            raise ValueError('PC_CAPTURE_ACTUAL_BARRIERS_MISSING')
        stderr = (folder / 'logcat-stderr.log').read_text(encoding='utf-8')
        if (has_log_loss(source, stderr) != proof['log_loss']
                or bool(stderr.strip()) != ('collector-stderr-nonempty' in proof['errors'])
                or ('Status: ok' in (folder / 'launch.txt').read_text(encoding='utf-8')) != proof['launch_ok']):
            raise ValueError('PC_CAPTURE_COLLECTION_EVIDENCE_DIFFERS')
        observed = {p for sample in proof['pid_observations'] for p in sample['pids']}
        scoped = scope_research_log(source, observed, version=proof.get('log_scope_version', 1))
        if summarize_runtime_events(scoped) != proof['runtime_summary'] or capture_quality(proof) != proof['status']:
            raise ValueError('PC_CAPTURE_DERIVED_EVIDENCE_DIFFERS')
        if (summarize_java_crash(scoped) != proof['java_crash_summary']
                or summarize_crash(scoped) != proof['crash_summary']):
            raise ValueError('PC_CAPTURE_CRASH_EVIDENCE_DIFFERS')
        if 'observer_summary' in proof and observer_summary(scoped) != proof['observer_summary']:
            raise ValueError('PC_CAPTURE_OBSERVER_EVIDENCE_DIFFERS')
        if 'scene97_task_summary' in proof:
            expected = proof['scene97_task_summary']
            schemas = {'pc-scene97-task-evidence-v1': 1, 'pc-scene97-task-evidence-v2': 2}
            version = schemas.get(expected.get('schema')) if isinstance(expected, dict) else None
            if version is None or scene97_task_summary(scoped, version=version) != expected:
                raise ValueError('PC_CAPTURE_SCENE97_TASK_EVIDENCE_DIFFERS')
        if 'pc_balance_summary' in proof and pc_balance_summary(scoped) != proof['pc_balance_summary']:
            raise ValueError('PC_CAPTURE_BALANCE_COUNTER_EVIDENCE_DIFFERS')
        return dict(status='PC_CAPTURE_ARTIFACTS_AND_SUMMARIES_VERIFIED', run_id=folder.name,
                    artifacts=count, capture_status=proof['status'], observer=proof.get('observer_summary'))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, default=Path(os.environ.get('LOCALAPPDATA', '.')) / 'Android/Sdk')
    parser.add_argument('--java', type=Path, default=Path(os.environ.get('PROGRAMFILES', '.')) / 'Java/jdk-17')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('setup')
    build = sub.add_parser('build')
    build.add_argument('--owner-zip', type=Path, required=True)
    build.add_argument('--official-aar', type=Path, required=True)
    build.add_argument('--local-boot', action='store_true')
    build.add_argument('--balance', action='store_true')
    build.add_argument('--original-ops-bundle', type=Path)
    run = sub.add_parser('run')
    run.add_argument('--seconds', type=int, default=30)
    run.add_argument('--install', action='store_true')
    play = sub.add_parser('play')
    play.add_argument('--seconds', type=int, default=1800)
    sub.add_parser('check')
    sub.add_parser('initialize-profile')
    verify = sub.add_parser('verify-capture')
    verify.add_argument('--directory', type=Path)
    args = parser.parse_args()
    if args.command in ('run','play') and not 10 <= args.seconds <= 1800:
        parser.error('PC capture duration must be 10..1800 seconds')
    if os.name != 'nt':
        parser.error('Windows PC lab only; pure evidence gates remain portable')
    lab = Lab(args.state, args.sdk, args.java)
    if args.command == 'setup':
        lab.setup()
        print('PC_LAB_READY')
    elif args.command == 'build':
        bundle_bytes = args.original_ops_bundle.read_bytes() if args.original_ops_bundle else None
        result = lab.build(args.owner_zip, args.official_aar, local_boot=args.local_boot,
                           balance=args.balance, original_ops_bundle=bundle_bytes)
        print('PC_BUILD_VERIFIED_SIX_SPLITS ' + Path(result['directory']).name)
    elif args.command == 'run':
        lab.setup()
        result = lab.capture(args.seconds, install=args.install)
        print(result['status'] + ' ' + result['run_id'])
        return 0 if result['status'] == 'COMPLETE_BOUNDED_CAPTURE' else 1
    elif args.command == 'play':
        from tools.pc_viewer import start_viewer
        lab.setup()
        start_viewer(lab)
        result = lab.capture(args.seconds)
        print(result['status'] + ' ' + result['run_id'])
        return 0 if result['status'] == 'COMPLETE_BOUNDED_CAPTURE' else 1
    elif args.command == 'verify-capture':
        result = lab.verify_capture(args.directory)
        print(result['status'] + ' ' + result['run_id'])
    elif args.command == 'initialize-profile':
        from tools.pc_profile_install import install_once
        lab.setup()
        result = install_once(lab)
        print(result['status'])
    else:
        lab.identity()
        lab.verify_build()
        print('PC_LAB_IDENTITY_AND_BUILD_HASHES_VERIFIED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
