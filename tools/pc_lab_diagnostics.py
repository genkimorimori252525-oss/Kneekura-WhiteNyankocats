"""Fixed, privacy-safe PC evidence. Caller must scope and bound log PIDs first."""
import re
import hashlib
from datetime import datetime
from pathlib import Path


def pc_balance_summary(scoped: str) -> dict:
    pattern=(r'KNEEKURA_STATIC_HTTP:\s*pc-native-balance-v1 calls='
             + ','.join([r'(\d{1,20})']*8)
             + r' castle_credit=(\d{1,20}) castle_zero=(\d{1,20})'
             + r' delayed_rejected=(\d{1,20}) query_capacity=(\d{1,20})$')
    latest=None
    observations=0
    resets=0
    for line in scoped.splitlines():
        match=re.search(pattern,line)
        if not match: continue
        values=list(map(int,match.groups()))
        if any(v >= 1<<64 for v in values): raise ValueError('PC_BALANCE_COUNTER_OUT_OF_RANGE')
        if latest and any(a<b for a,b in zip(values,latest)): resets+=1
        latest=values
        observations+=1
    return dict(schema='pc-native-balance-counters-v1',observations=observations,
                counter_resets_observed=resets,adapter_calls=latest[:8] if latest else None,
                castle_credited_hits=latest[8] if latest else None,
                castle_zero_hits=latest[9] if latest else None,
                delayed_generator_rejections=latest[10] if latest else None,
                query_capacity_rejections=latest[11] if latest else None,
                counts_are_not_gameplay_acceptance=True)


def scene97_task_summary(scoped: str, *, version: int = 2) -> dict:
    if type(version) is not int or version not in (1, 2):
        raise ValueError('PC_SCENE97_TASK_SCHEMA_UNSUPPORTED')
    observations = []
    queue_observations = []
    unavailable = set()
    pattern = (r'original-native-scene97-task-v1 active=(\d{1,2}) disabled=(\d{1,2}) '
               r'present=(\d) failed=(\d) needed=(\d) pending=(\d{1,2}) completed=(\d)')
    for line in scoped.splitlines():
        missing = re.search(r'KNEEKURA_STATIC_HTTP:\s*original-native-scene97-'
                            r'(task|queue)-unavailable-v1 (context-read|task-read|task-identity|'
                            r'task-flags|header-read|header-range)$', line)
        if missing:
            unavailable.add(missing[1] + ':' + missing[2])
        queue = re.search(r'KNEEKURA_STATIC_HTTP:\s*original-native-scene97-queue-v1 '
                          r'head=([0-4]) completed=([01]) phase=(\d{1,2}) waiting=(\d)$', line)
        if queue:
            head, complete, phase, waiting = map(int, queue.groups())
            if phase > 65 or waiting > 9:
                raise ValueError('PC_SCENE97_QUEUE_OBSERVATION_INVALID')
            item = dict(head=('none', 'download', 'create-account', 'public-config', 'other')[head],
                        completed=bool(complete) if head in (2, 3) else None,
                        phase=phase if phase < 65 else None,
                        waiting=waiting if waiting < 9 else None)
            if not queue_observations or item != queue_observations[-1]:
                queue_observations.append(item)
            if len(queue_observations) > 4:
                raise ValueError('PC_SCENE97_QUEUE_OBSERVATION_LIMIT')
        match = re.search(r'KNEEKURA_STATIC_HTTP:\s*' + pattern + r'$', line)
        if not match:
            continue
        active, disabled, present, failed, needed, pending, completed = map(int, match.groups())
        if (active + disabled != 35 or max(active, disabled, pending) > 35
                or max(present, failed, needed, completed) > 1
                or (not present and (failed or needed or pending))):
            raise ValueError('PC_SCENE97_TASK_OBSERVATION_INVALID')
        item = dict(active=active, disabled=disabled, present=bool(present),
                    failed=bool(failed) if present else None,
                    needed=bool(needed) if present else None, pending=pending if present else None,
                    completed=bool(completed))
        if ((version == 1 and item not in observations)
                or (version == 2 and (not observations or item != observations[-1]))):
            observations.append(item)
        if len(observations) > 4:
            raise ValueError('PC_SCENE97_TASK_OBSERVATION_LIMIT')
    if version == 1:
        for item in observations:
            if not item['present']:
                item.update(failed=False, needed=False, pending=0)
        return dict(schema='pc-scene97-task-evidence-v1', observations=observations,
                    resource_acceptance_proven=False)
    return dict(schema='pc-scene97-task-evidence-v2', observations=observations,
                queue_observations=queue_observations,
                unavailable_categories=sorted(unavailable),
                resource_acceptance_proven=False)


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
