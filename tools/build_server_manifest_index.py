"""Build a metadata-only filename index from encrypted Battle Cats server .list files."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any

from tools.battlecats_pack import parse_manifest


def parse_source(value: str) -> tuple[str, pathlib.Path]:
    source_id, separator, raw_path = value.partition("=")
    if not separator or not source_id or not raw_path:
        raise argparse.ArgumentTypeError("source must be ID=PATH")
    return source_id, pathlib.Path(raw_path)


def build_index(sources: list[tuple[str, pathlib.Path]]) -> dict[str, Any]:
    manifests: list[dict[str, Any]] = []
    entries: list[dict[str, str]] = []

    for source_id, root in sources:
        if not root.is_dir():
            raise FileNotFoundError(root)
        for path in sorted(root.rglob("*.list")):
            raw = path.read_bytes()
            count, decoded = parse_manifest(raw)
            family = path.stem
            manifests.append(
                {
                    "source": source_id,
                    "family": family,
                    "path": str(path.relative_to(root)).replace("\\", "/"),
                    "entry_count": count,
                    "manifest_sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
            for item in decoded:
                entries.append(
                    {
                        "source": source_id,
                        "family": family,
                        "name": item.name,
                    }
                )

    entries.sort(key=lambda item: (item["name"], item["source"], item["family"]))
    return {
        "schema_version": 1,
        "sources": [
            {"id": source_id, "root": str(root)}
            for source_id, root in sources
        ],
        "manifest_count": len(manifests),
        "entry_count": len(entries),
        "manifests": manifests,
        "entries": entries,
    }


def write_index(document: dict[str, Any], output: pathlib.Path) -> pathlib.Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        action="append",
        type=parse_source,
        required=True,
        help="Source directory as ID=PATH (repeatable).",
    )
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        document = build_index(args.source)
        output = write_index(document, args.output)
    except (FileNotFoundError, ValueError) as exc:
        print(f"server manifest index failed: {exc}", file=sys.stderr)
        return 2

    print(
        f"indexed {document['entry_count']} entries from "
        f"{document['manifest_count']} manifests -> {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
