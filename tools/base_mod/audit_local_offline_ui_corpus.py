"""Read-only JP15.7.1 evidence for locally bundled UI/schedules and restriction text.

Reports only structural metadata and exact localizable keys (not account data,
original save, downloaded proprietary assets, live server schedule or packet log).
A local message string does NOT establish where its triggering decision occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.battlecats_source import BattleCatsExport
from tools.base_mod.extract_owned_splits import EXPECTED_EXPORT_SHA256

UI_KEYS = (
    "gamestop", "gamestop_device", "gamestop_base",
    "calendar_error", "receive_energy", "receive_energy_full",
)
DATALOCAL_NAMES = (
    "eventDisplayData.json", "GatyaData_Option_SetR.tsv",
    "Map_option.csv", "Stage_option.csv", "DailyLoginEventData.csv",
    "DailyLoginEventGrade.json", "event.json", "gatya.tsv",
)


def summarize_corpus(localizable: bytes, event_display: bytes,
                     gacha_options: bytes, present: dict[str, bool]) -> dict:
    translations = {}
    for line in localizable.decode("utf-8-sig").splitlines():
        key, sep, value = line.partition("\t")
        if not sep:
            continue
        if key in UI_KEYS:
            if key in translations:
                raise ValueError("duplicate exact localizable key: " + key)
            translations[key] = value

    event = json.loads(event_display.decode("utf-8-sig"))
    maps = event.get("MapSet")
    if not isinstance(maps, dict):
        raise ValueError("not the expected original event display catalog")
    rows = gacha_options.decode("utf-8-sig").splitlines()
    if not rows or "GatyaSetID" not in rows[0]:
        raise ValueError("gacha data options header changed")
    if not all(present.get(name) is True for name in DATALOCAL_NAMES[:6]):
        raise ValueError("expected source-APK local definitions missing")
    return {
        "schema_version": 1,
        "status": "ORIGINAL_APK_LOCAL_DATA_CONFIRMED_DECISION_SOURCE_UNKNOWN",
        "ui_localized_keys_present": {key: key in translations for key in UI_KEYS},
        "ui_original_key_count": len(translations),
        "ui_text_corpus_sha256": hashlib.sha256(localizable).hexdigest(),
        "ui_categories_are_distinct": all(key in translations for key in UI_KEYS[:3]),
        "local_event_display_mapset_count": len(maps),
        "local_gacha_option_rows_excluding_header": len(rows) - 1,
        "data_local_file_present": dict(sorted(present.items())),
        "schedule_requires_more_than_display_definition": True,
        "original_native_decision_origin": "NOT_TRACED",
        "specific_user_save_restriction_cause": "NOT_DETERMINED",
        "network_packets_observed": False,
        "no_original_client_bypass": True,
    }


def audit_export(owner_export: Path) -> dict:
    with BattleCatsExport(
        owner_export, region="jp", expected_sha256=EXPECTED_EXPORT_SHA256
    ) as original:
        res = original.pack("resLocal")
        data = original.pack("DataLocal")
        localizable = res.read("localizable.tsv")[0]
        event = data.read("eventDisplayData.json")[0]
        gacha = data.read("GatyaData_Option_SetR.tsv")[0]
        result = summarize_corpus(
            localizable, event, gacha,
            {name: data.has(name) for name in DATALOCAL_NAMES},
        )
        result["source_export_sha256"] = EXPECTED_EXPORT_SHA256
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owned-export", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = audit_export(args.owned_export)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(
            result, ensure_ascii=False, indent=2, sort_keys=True
        ) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
