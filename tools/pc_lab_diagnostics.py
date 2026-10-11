"""Fixed, privacy-safe PC evidence. Caller must scope and bound log PIDs first."""
import re
import hashlib
from datetime import datetime
from pathlib import Path


def verify_artifacts(folder: Path, manifest: dict) -> int:
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError('PC_CAPTURE_ARTIFACT_MANIFEST_MISSING')
    if {p.name for p in folder.iterdir() if p.name != 'CAPTURE.json'} != set(manifest):
        raise ValueError('PC_CAPTURE_ARTIFACT_SET_DIFFERS')
    for name, digest in manifest.items():
        if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', name)
                or name in ('.', '..', 'CAPTURE.json')
                or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)):
            raise ValueError('PC_CAPTURE_ARTIFACT_MANIFEST_UNSAFE')
        path = folder / name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('PC_CAPTURE_ARTIFACT_MISSING_OR_CHANGED')
    return len(manifest)


def anr_trace_paths(exit_info: str, pids: set[int], start: str, end: str,
                    device_offset: str = '+0000') -> list[str]:
    if not re.fullmatch(r'[+-]\d{4}', device_offset):
        raise ValueError('PC_CAPTURE_DEVICE_TIMEZONE_UNAVAILABLE')
    begin, finish = datetime.fromisoformat(start), datetime.fromisoformat(end)
    paths = []
    for entry in re.split(r'ApplicationExitInfo #\d+:', exit_info):
        stamp = re.search(r'timestamp=(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3}) pid=(\d+)\b', entry)
        trace = re.search(r'\btrace=(/data/system/procexitstore/anr_\d{4}-\d\d-\d\d-\d\d-\d\d-\d\d-\d{3}\.gz)(?:\s|$)', entry)
        if (not stamp or not trace or int(stamp[2]) not in pids
                or not re.search(r'\bprocess=jp\.kn\.local\.battlecats reason=6 \(ANR\)', entry)):
            continue
        occurred = datetime.strptime(stamp[1] + device_offset, '%Y-%m-%d %H:%M:%S.%f%z')
        if begin <= occurred <= finish and trace[1] not in paths:
            paths.append(trace[1])
    return paths


def observer_summary(scoped: str) -> dict:
    attached = set()
    returned = set()
    hook = 0
    failures = set()
    init_statuses = set()
    for line in scoped.splitlines():
        match = re.fullmatch(r'\d\d-\d\d\s+\S+\s+(\d+)\s+(\d+)\s+[VDIWEF]\s+'
                             r'KNEEKURA_STATIC_HTTP:\s*(.{1,160})', line)
        if not match:
            continue
        pair = (int(match[1]), int(match[2]))
        message = match[3]
        if message == 'original-native-pc-jni-scene-v1 attached':
            attached.add(pair)
        elif message == 'original-native-pc-jni-scene-v1 original-returned-same-gl-thread':
            if pair in attached:
                returned.add(pair)
        elif message == 'original-native-scene-hook-v1 installed':
            hook += 1
        elif message.startswith('original-native-pc-jni-scene-v1 '):
            reason = message.removeprefix('original-native-pc-jni-scene-v1 ')
            if reason in ('thread-mismatch', 'source-unavailable', 'registration-failed', 'unavailable'):
                failures.add(reason)
        elif (status := re.fullmatch(r'original-native-scene-hook-v1 hook-init-status=(-?\d{1,3})', message)):
            init_statuses.add(int(status[1]))
    good = bool(returned) and not failures
    return dict(schema='pc-original-observer-evidence-v1',
                backend='pc-jni-scene-only' if good else ('shadowhook-five-witnesses' if hook else 'unavailable'),
                pc_jni_attachment_observed=bool(attached),
                original_draw_returned_on_install_gl_thread=good,
                level_save_hooks_installed=bool(hook),
                shadowhook_init_statuses=sorted(init_statuses),
                pc_observer_failure_categories=sorted(failures),
                scene_observation_is_not_gameplay_acceptance=True)
