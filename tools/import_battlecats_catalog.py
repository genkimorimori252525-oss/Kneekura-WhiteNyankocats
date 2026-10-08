"""Build a local-only unit catalog from a Battle Cats Android export.

Output is metadata/text/stat data intended for the Kneekura importer pipeline.
No image/audio/animation payload bytes are written by this command.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys
from typing import Any

from tools.battlecats_source import BattleCatsExport


UNIT_RE = re.compile(r"^unit(\d+)\.csv$", re.IGNORECASE)
EXPLANATION_RE = re.compile(r"^Unit_Explanation(\d+)_ja\.csv$")


def _to_scalar(value: str) -> int | str | None:
    value = value.strip()
    if value == "":
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_stat_rows(payload: bytes) -> list[list[int | str | None]]:
    text = payload.decode("utf-8-sig", "replace")
    rows: list[list[int | str | None]] = []
    for raw_line in text.splitlines():
        # The observed data sometimes appends a human-readable // comment.
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        columns = [column.strip() for column in line.split(",")]
        while columns and columns[-1] == "":
            columns.pop()
        if columns:
            rows.append([_to_scalar(column) for column in columns])
    return rows


def parse_explanation_rows(payload: bytes) -> list[list[str]]:
    text = payload.decode("utf-8-sig", "replace")
    rows: list[list[str]] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        rows.append([column.strip() for column in raw_line.split(",")])
    return rows


def _provenance_dict(provenance) -> dict[str, Any]:
    return {
        "family": provenance.family,
        "entry": provenance.entry,
        "offset": provenance.offset,
        "encrypted_size": provenance.encrypted_size,
        "mode": provenance.mode,
        "payload_sha256": provenance.payload_sha256,
    }


def build_catalog(
    export_path: pathlib.Path,
    *,
    expected_sha256: str | None = None,
    region: str = "jp",
) -> dict[str, Any]:
    with BattleCatsExport(
        export_path,
        region=region,
        expected_sha256=expected_sha256,
    ) as source:
        data = source.pack("DataLocal")
        res = source.pack("resLocal")

        unit_ids = sorted(
            int(match.group(1))
            for entry in data.entries
            if (match := UNIT_RE.fullmatch(entry.name))
        )
        explanation_ids = sorted(
            int(match.group(1))
            for entry in res.entries
            if (match := EXPLANATION_RE.fullmatch(entry.name))
        )

        if not unit_ids:
            raise ValueError("DataLocal contains no unitNNN.csv entries")
        if unit_ids != explanation_ids:
            raise ValueError(
                "unit definition IDs and Japanese explanation IDs do not match"
            )

        expected_ids = list(range(unit_ids[0], unit_ids[-1] + 1))
        if unit_ids != expected_ids:
            raise ValueError("unit IDs are not consecutive")

        units: list[dict[str, Any]] = []
        form_shape_counts: collections.Counter[str] = collections.Counter()
        anomalies: list[dict[str, Any]] = []

        for unit_id in unit_ids:
            stats_name = f"unit{unit_id:03d}.csv"
            explanation_name = f"Unit_Explanation{unit_id}_ja.csv"

            stats_payload, stats_provenance = data.read(stats_name)
            explanation_payload, explanation_provenance = res.read(explanation_name)

            stat_rows = parse_stat_rows(stats_payload)
            explanation_rows = parse_explanation_rows(explanation_payload)
            form_count = max(len(stat_rows), len(explanation_rows))
            shape_key = f"{len(stat_rows)}stats/{len(explanation_rows)}text"
            form_shape_counts[shape_key] += 1

            forms: list[dict[str, Any]] = []
            for form_index in range(form_count):
                text_fields = (
                    explanation_rows[form_index]
                    if form_index < len(explanation_rows)
                    else None
                )
                raw_stats = (
                    stat_rows[form_index] if form_index < len(stat_rows) else None
                )
                forms.append(
                    {
                        "index": form_index,
                        "name": text_fields[0] if text_fields else None,
                        "text_fields": text_fields,
                        "stats_raw": raw_stats,
                        "stats_field_count": len(raw_stats) if raw_stats else 0,
                    }
                )

            if len(stat_rows) != len(explanation_rows):
                anomalies.append(
                    {
                        "unit_id": unit_id,
                        "kind": "form_count_mismatch",
                        "stat_rows": len(stat_rows),
                        "text_rows": len(explanation_rows),
                    }
                )

            units.append(
                {
                    "id": unit_id,
                    "key": f"bc:unit:{unit_id:03d}",
                    "forms": forms,
                    "provenance": {
                        "stats": _provenance_dict(stats_provenance),
                        "text": _provenance_dict(explanation_provenance),
                    },
                }
            )

        assert source.source_info is not None
        info = source.source_info
        return {
            "schema_version": 1,
            "source": {
                "export_name": info.export_name,
                "export_size": info.export_size,
                "export_sha256": info.export_sha256,
                "version": info.version,
                "region": region,
                "install_apk_path": info.install_apk_path,
                "install_apk_size": info.install_apk_size,
                "install_apk_sha256": info.install_apk_sha256,
            },
            "summary": {
                "unit_count": len(units),
                "unit_id_min": unit_ids[0],
                "unit_id_max": unit_ids[-1],
                "unit_ids_consecutive": True,
                "form_shape_counts": dict(sorted(form_shape_counts.items())),
                "anomaly_count": len(anomalies),
                "anomalies": anomalies,
            },
            "units": units,
        }


def write_catalog(catalog: dict[str, Any], output: pathlib.Path) -> pathlib.Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a read-only local unit catalog from a Battle Cats export ZIP."
    )
    parser.add_argument("export", type=pathlib.Path)
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("reports/private/unit-catalog.json"),
    )
    parser.add_argument("--expect-sha256", default=None)
    parser.add_argument("--region", default="jp", choices=["jp"])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        catalog = build_catalog(
            args.export,
            expected_sha256=args.expect_sha256,
            region=args.region,
        )
        path = write_catalog(catalog, args.output)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"catalog import failed: {exc}", file=sys.stderr)
        return 2

    print(
        f"wrote {catalog['summary']['unit_count']} units "
        f"to {path} (anomalies={catalog['summary']['anomaly_count']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
