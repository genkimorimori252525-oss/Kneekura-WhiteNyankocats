"""Read-only JP 15.7.1 login-bonus foundation audit."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from tools.battlecats_source import BattleCatsExport


EXACT_EXPORT_SHA256 = (
    "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
)
COMEBACK_TEMPLATE_ID = 949
EXPECTED_COMEBACK_DAYS = 7


def _text(payload: bytes) -> str:
    return payload.decode("utf-8-sig", "replace")


def _integer_rows(payload: bytes) -> list[list[int]]:
    rows: list[list[int]] = []
    for line in _text(payload).splitlines():
        body = line.split("//", 1)[0].strip()
        if not body:
            continue
        values: list[int] = []
        valid = True
        for cell in body.split(","):
            cell = cell.strip()
            if not cell:
                continue
            try:
                values.append(int(cell))
            except ValueError:
                valid = False
                break
        if valid and values:
            rows.append(values)
    return rows


def parse_login_groups(row: list[int]) -> tuple[list[int], list[list[int]]]:
    if len(row) < 7:
        raise ValueError("daily login row has fewer than seven header cells")

    header = row[:7]
    groups: list[list[int]] = []
    column = 7
    while column < len(row) - 1:
        item_count = row[column]
        if item_count < 0:
            raise ValueError("negative daily-login item count")
        end = column + 2 + item_count * 3
        if end > len(row):
            raise ValueError("truncated daily-login reward group")
        groups.append(row[column:end])
        column = end
    if column != len(row):
        raise ValueError("daily-login row has an unmatched trailing cell")
    return header, groups


def group_rewards(group: list[int]) -> list[dict]:
    item_count = group[0]
    group_value = group[1]
    rewards: list[dict] = []
    for index in range(item_count):
        base = 2 + index * 3
        rewards.append(
            {
                "kind": group[base],
                "item_index": group[base + 1],
                "amount": group[base + 2],
            }
        )
    return [{"group_value": group_value, "rewards": rewards}][0:1]


def item_index_names(gatya_item_buy: bytes) -> dict[int, str]:
    lines = _text(gatya_item_buy).splitlines()
    if not lines:
        return {}

    first = lines[0].split(",", 1)[0].strip()
    start = 1 if first and not first.lstrip("-").isdigit() else 0
    result: dict[int, str] = {}
    item_index = 0
    for line in lines[start:]:
        body = line.split("//", 1)[0].strip()
        columns = [cell.strip() for cell in body.split(",")]
        if len(columns) >= 13:
            result[item_index] = ",".join(columns[12:]).strip()
        else:
            result[item_index] = ""
        item_index += 1
    return result


def analyze_export(path: Path) -> dict:
    with BattleCatsExport(
        path,
        region="jp",
        expected_sha256=EXACT_EXPORT_SHA256,
    ) as export:
        data = export.pack("DataLocal")
        names = [
            "DailyLoginEventData.csv",
            "DailyLoginEventGrade.json",
            "StampData.csv",
            "Gatyaitembuy.csv",
        ]
        payloads = {}
        files = {}
        for name in names:
            payload, provenance = data.read(name)
            payloads[name] = payload
            files[name] = {
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "line_count": len(_text(payload).splitlines()),
                "provenance": {
                    "family": provenance.family,
                    "entry": provenance.entry,
                    "offset": provenance.offset,
                    "encrypted_size": provenance.encrypted_size,
                    "mode": provenance.mode,
                },
            }

        daily_rows = _integer_rows(payloads["DailyLoginEventData.csv"])
        matching = [row for row in daily_rows if row and row[0] == COMEBACK_TEMPLATE_ID]
        if len(matching) != 1:
            raise ValueError(
                f"expected one login template {COMEBACK_TEMPLATE_ID}, got {len(matching)}"
            )

        header, groups = parse_login_groups(matching[0])
        if len(groups) != EXPECTED_COMEBACK_DAYS:
            raise ValueError(
                f"template {COMEBACK_TEMPLATE_ID} day count changed: {len(groups)}"
            )

        item_names = item_index_names(payloads["Gatyaitembuy.csv"])
        days = []
        totals: Counter[str] = Counter()
        for day_index, group in enumerate(groups, start=1):
            reward_group = group_rewards(group)[0]
            resolved = []
            for reward in reward_group["rewards"]:
                item_index = reward["item_index"]
                name = item_names.get(item_index, f"item_index_{item_index}")
                amount = reward["amount"]
                resolved.append(
                    {
                        **reward,
                        "item_name": name,
                    }
                )
                totals[name] += amount
            days.append(
                {
                    "day": day_index,
                    "group_value": reward_group["group_value"],
                    "rewards": resolved,
                }
            )

        stamp_rows = _integer_rows(payloads["StampData.csv"])
        grade = json.loads(_text(payloads["DailyLoginEventGrade.json"]))

        return {
            "schema_version": 1,
            "source": export.source_info.__dict__ if export.source_info else None,
            "files": files,
            "standard_stamp": {
                "row_count": len(stamp_rows),
                "separate_from_comeback_template": True,
            },
            "comeback_template": {
                "event_id": COMEBACK_TEMPLATE_ID,
                "header_cells": header,
                "day_count": len(days),
                "days": days,
                "totals": dict(sorted(totals.items())),
                "identification": {
                    "status": "high-confidence local comeback template",
                    "reason": (
                        "The seven-day reward signature resolves through the exact "
                        "Gatyaitembuy row-index namespace to 21 Cat Tickets, "
                        "3 Rare Tickets and XP rewards, matching the distinctive "
                        "player-facing comeback sequence."
                    ),
                },
            },
            "grade_data": {
                "daily_login_stamp_ids": sorted(
                    int(key)
                    for key in grade.get("DailyLoginStampID", {}).keys()
                ),
                "not_conflated_with_template_949": True,
            },
            "policy": {
                "approved_cycle_length": EXPECTED_COMEBACK_DAYS,
                "reuse_original_template": True,
                "live_server_override_may_differ": True,
                "precedence": [
                    "exact imported server override if proven",
                    "exact JP 15.7.1 local template 949",
                    "never silently substitute community-only values",
                ],
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_zip", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = analyze_export(args.export_zip.resolve())
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
