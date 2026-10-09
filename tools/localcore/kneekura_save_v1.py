"""KNEEKURA_SAVE_V1 and offline timers — research-only pure Python foundation.

No original JP SAVE_DATA, account identifiers, server time, network calls,
APK modifications or original game engine integration. NOT a playable Android
host. Own checksum detects accidental corruption but never bans the player.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

SCHEMA = "KNEEKURA_SAVE_V1"
SAVE_NAME = "kneekura-local-v1.json"
BACKUP_NAME = "kneekura-local-v1.bak.json"


class LocalSaveError(ValueError):
    pass


def fresh_profile(now_ms: int, *, cap: int = 100, seconds_per_point: int = 60,
                  energy_mode: str = "timed") -> dict:
    if (type(now_ms) is not int or now_ms < 0 or type(cap) is not int
            or not 1 <= cap <= 1000000 or type(seconds_per_point) is not int
            or not 1 <= seconds_per_point <= 86400
            or energy_mode not in ("timed", "unlimited")):
        raise LocalSaveError("invalid local profile initialization")
    initial = {
        "schema": SCHEMA, "revision": 1,
        "energy": {"amount": cap, "cap": cap, "mode": energy_mode,
                   "seconds_per_point": seconds_per_point,
                   "last_seen_ms": now_ms, "remainder_ms": 0},
        "currency": {"xp": 0, "catfood": 0},
        "unlocked_units": [], "cleared_stages": [],
        "local_events": {}, "local_gacha": {},
    }
    # The story ledger is local and separate from stage reward/drop history.
    # It never imports the rejected PONOS SAVE_DATA.
    from tools.localcore.story_checkpoint import apply_story_checkpoint
    return apply_story_checkpoint(initial)


def validate(profile: dict) -> None:
    if not isinstance(profile, dict) or profile.get("schema") != SCHEMA:
        raise LocalSaveError("not a Kneekura independent save")
    if any(k in profile for k in
           ("inquiry_code", "ponos_account", "original_SAVE_DATA", "account_token")):
        raise LocalSaveError("cannot import official account identity")
    e = profile.get("energy")
    if not isinstance(e, dict) or e.get("mode") not in ("timed", "unlimited"):
        raise LocalSaveError("invalid energy mode")
    for k in ("amount", "cap", "seconds_per_point", "last_seen_ms", "remainder_ms"):
        if type(e.get(k)) is not int:
            raise LocalSaveError("invalid energy numeric type")
    if not (1 <= e["cap"] <= 1000000 and 0 <= e["amount"] <= e["cap"]
            and 1 <= e["seconds_per_point"] <= 86400 and e["last_seen_ms"] >= 0
            and 0 <= e["remainder_ms"] < 1000 * e["seconds_per_point"]):
        raise LocalSaveError("invalid energy interval")
    if not isinstance(profile.get("currency"), dict) or not isinstance(
            profile.get("unlocked_units"), list):
        raise LocalSaveError("missing owned gameplay fields")


def advance_energy(profile: dict, now_ms: int) -> tuple[dict, str]:
    """Deterministic local time only; rollback never imposes a restriction."""
    validate(profile)
    if type(now_ms) is not int or now_ms < 0:
        raise LocalSaveError("invalid supplied wall clock")
    result = deepcopy(profile)
    e = result["energy"]
    if e["mode"] == "unlimited":
        e["amount"] = e["cap"]
        e["remainder_ms"] = 0
        e["last_seen_ms"] = max(e["last_seen_ms"], now_ms)
        return result, "LOCAL_UNLIMITED"
    if now_ms < e["last_seen_ms"]:
        return result, "CLOCK_WENT_BACK_IGNORED_NO_BAN"
    elapsed_ms = now_ms - e["last_seen_ms"]
    e["last_seen_ms"] = now_ms
    if e["amount"] == e["cap"]:
        e["remainder_ms"] = 0
        return result, "LOCAL_FULL"
    earned, rem = divmod(elapsed_ms + e["remainder_ms"],
                         1000 * e["seconds_per_point"])
    e["amount"] = min(e["cap"], e["amount"] + earned)
    e["remainder_ms"] = 0 if e["amount"] == e["cap"] else rem
    return result, "LOCAL_REGENERATED"


def weekly_event_active(*, utc_ms: int, weekday: int,
                        from_hour: int, to_hour: int) -> bool:
    """Simple JST local recurrence prototype; not PONOS live event data."""
    if (type(utc_ms) is not int or utc_ms < 0 or
        type(weekday) is not int or not 0 <= weekday <= 6 or
        type(from_hour) is not int or type(to_hour) is not int or
        not 0 <= from_hour < to_hour <= 24):
        raise LocalSaveError("invalid local calendar rule")
    jst = timezone(timedelta(hours=9))
    now = datetime.fromtimestamp(utc_ms / 1000, tz=jst)
    return now.weekday() == weekday and from_hour <= now.hour < to_hour


def _canonical(state: dict) -> bytes:
    return json.dumps(state, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _wrap(state: dict) -> bytes:
    validate(state)
    wrapped = {"state": state, "sha256": hashlib.sha256(_canonical(state)).hexdigest()}
    return (json.dumps(wrapped, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n").encode("utf-8")


def _read(path: Path) -> dict:
    try:
        wrapped = json.loads(path.read_text(encoding="utf-8"))
        state = wrapped["state"]
        validate(state)
        if hashlib.sha256(_canonical(state)).hexdigest() != wrapped["sha256"]:
            raise LocalSaveError("local checksum mismatch")
        return state
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise LocalSaveError("local save corrupted, restore its backup; not a ban") from exc


def load_local(folder: Path) -> tuple[dict, str]:
    primary, backup = folder / SAVE_NAME, folder / BACKUP_NAME
    if primary.exists():
        try:
            return _read(primary), "PRIMARY"
        except LocalSaveError:
            pass
    if backup.exists():
        return _read(backup), "BACKUP_RECOVERABLE"
    raise LocalSaveError("no intact Kneekura-local save; no official-server lockout")


def _atomic_write(path: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent,
                                     prefix=".kneekura-", delete=False) as stream:
        tmp = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def write_local(folder: Path, state: dict) -> None:
    """Keep last good independent save; don't silently replace a bad primary."""
    content = _wrap(state)
    folder.mkdir(parents=True, exist_ok=True)
    primary, backup = folder / SAVE_NAME, folder / BACKUP_NAME
    if primary.exists():
        old = _read(primary)
        _atomic_write(backup, _wrap(old))
    _atomic_write(primary, content)
