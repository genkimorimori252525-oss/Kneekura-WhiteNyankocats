#!/usr/bin/env python3
"""Read-only inventory for Battle Cats Android exports.

The tool only reads input bytes and writes metadata reports to a separate
output directory. It does not decrypt, patch, re-sign, or write back to APKs
or app-owned data.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile
import zipfile
from typing import Iterable

SCHEMA_VERSION = 1
BUFFER_SIZE = 1024 * 1024

CATEGORY_EXTENSIONS = {
    "pack_list": {".pack", ".list"},
    "animation": {".maanim", ".mamodel", ".model", ".anim", ".imgcut"},
    "image": {".png", ".jpg", ".jpeg", ".webp", ".img"},
    "audio": {".ogg", ".wav", ".mp3", ".aac", ".caf", ".m4a"},
    "text_data": {".json", ".csv", ".tsv", ".txt", ".xml"},
    "code": {".dex"},
    "native": {".so"},
}

UI_KEYWORDS = (
    "ui",
    "menu",
    "button",
    "btn",
    "title",
    "screen",
    "dialog",
    "window",
    "icon",
    "sprite",
    "texture",
    "background",
    "bg",
)

ANIMATION_KEYWORDS = (
    "anim",
    "motion",
    "model",
    "skeleton",
    "sprite",
)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(BUFFER_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extension(path_text: str) -> str:
    name = path_text.rsplit("/", 1)[-1]
    if "." not in name:
        return "<none>"
    return "." + name.rsplit(".", 1)[-1].lower()


def normalize_path(path_text: str) -> str:
    return path_text.replace("\\", "/")


def classify_path(path_text: str) -> set[str]:
    normalized = normalize_path(path_text)
    lowered = normalized.lower()
    suffix = extension(normalized)
    categories: set[str] = set()

    for category, suffixes in CATEGORY_EXTENSIONS.items():
        if suffix in suffixes:
            categories.add(category)

    if lowered.endswith("androidmanifest.xml"):
        categories.add("manifest")

    if lowered.startswith("assets/") or "/assets/" in lowered:
        categories.add("assets")

    if lowered.startswith("res/") or "/res/" in lowered:
        categories.add("resources")

    if suffix in CATEGORY_EXTENSIONS["image"] and any(keyword in lowered for keyword in UI_KEYWORDS):
        categories.add("ui_candidate")

    if any(keyword in lowered for keyword in ANIMATION_KEYWORDS):
        if suffix in CATEGORY_EXTENSIONS["animation"] or suffix in CATEGORY_EXTENSIONS["image"]:
            categories.add("animation_candidate")

    return categories


def entry_record(name: str, size: int, compressed_size: int | None = None) -> dict:
    record = {
        "path": normalize_path(name),
        "size": int(size),
        "extension": extension(name),
    }
    if compressed_size is not None:
        record["compressed_size"] = int(compressed_size)
    return record


def _bucketize(records: Iterable[dict], max_paths: int) -> dict:
    counts: collections.Counter[str] = collections.Counter()
    samples: dict[str, list[dict]] = collections.defaultdict(list)

    for record in records:
        for category in classify_path(record["path"]):
            counts[category] += 1
            if len(samples[category]) < max_paths:
                samples[category].append(record)

    result = {}
    for category in sorted(set(counts) | set(samples)):
        result[category] = {
            "count": counts[category],
            "paths": samples.get(category, []),
        }
    return result


def _extension_counts(records: Iterable[dict]) -> dict[str, int]:
    counts = collections.Counter(record["extension"] for record in records)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def inspect_apk(path: pathlib.Path, logical_name: str, max_paths: int) -> dict:
    with zipfile.ZipFile(path) as apk:
        records = [
            entry_record(info.filename, info.file_size, info.compress_size)
            for info in apk.infolist()
            if not info.is_dir()
        ]

    top_level = sorted({record["path"].split("/", 1)[0] for record in records if record["path"]})

    return {
        "logical_name": normalize_path(logical_name),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
        "entry_count": len(records),
        "top_level": top_level,
        "extension_counts": _extension_counts(records),
        "categories": _bucketize(records, max_paths=max_paths),
    }


def inspect_outer_zip(path: pathlib.Path, max_paths: int) -> dict:
    result = {
        "kind": "export_zip",
        "entry_count": 0,
        "top_level": [],
        "extension_counts": {},
        "apks": [],
        "shared_storage": {},
    }

    with tempfile.TemporaryDirectory(prefix="kneekura-inventory-") as temp_dir_name:
        temp_dir = pathlib.Path(temp_dir_name)

        with zipfile.ZipFile(path) as outer:
            outer_records = [
                entry_record(info.filename, info.file_size, info.compress_size)
                for info in outer.infolist()
                if not info.is_dir()
            ]
            result["entry_count"] = len(outer_records)
            result["top_level"] = sorted({
                record["path"].split("/", 1)[0]
                for record in outer_records
                if record["path"]
            })
            result["extension_counts"] = _extension_counts(outer_records)

            apk_infos = [
                info for info in outer.infolist()
                if not info.is_dir() and info.filename.lower().endswith(".apk")
            ]
            non_apk_records = [
                record for record in outer_records
                if not record["path"].lower().endswith(".apk")
            ]
            result["shared_storage"] = {
                "entry_count": len(non_apk_records),
                "extension_counts": _extension_counts(non_apk_records),
                "categories": _bucketize(non_apk_records, max_paths=max_paths),
            }

            for index, info in enumerate(apk_infos):
                temp_apk = temp_dir / f"{index:03d}-{pathlib.Path(info.filename).name}"
                with outer.open(info) as source, temp_apk.open("wb") as target:
                    shutil.copyfileobj(source, target, length=BUFFER_SIZE)
                result["apks"].append(
                    inspect_apk(temp_apk, logical_name=info.filename, max_paths=max_paths)
                )

    return result


def inspect_directory(path: pathlib.Path, max_paths: int) -> dict:
    files = [item for item in path.rglob("*") if item.is_file()]
    records = [
        entry_record(item.relative_to(path).as_posix(), item.stat().st_size)
        for item in files
    ]

    apks = []
    for item in files:
        if item.suffix.lower() == ".apk":
            apks.append(
                inspect_apk(
                    item,
                    logical_name=item.relative_to(path).as_posix(),
                    max_paths=max_paths,
                )
            )

    non_apk_records = [
        record for record in records
        if not record["path"].lower().endswith(".apk")
    ]

    return {
        "kind": "directory",
        "entry_count": len(records),
        "top_level": sorted({
            record["path"].split("/", 1)[0]
            for record in records
            if record["path"]
        }),
        "extension_counts": _extension_counts(records),
        "apks": apks,
        "shared_storage": {
            "entry_count": len(non_apk_records),
            "extension_counts": _extension_counts(non_apk_records),
            "categories": _bucketize(non_apk_records, max_paths=max_paths),
        },
    }


def inventory_path(path: pathlib.Path, max_paths: int = 5000) -> dict:
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    if path.is_dir():
        source = {
            "name": path.name,
            "kind": "directory",
            "size": None,
            "sha256": None,
        }
        payload = inspect_directory(path, max_paths=max_paths)
    else:
        source = {
            "name": path.name,
            "kind": "file",
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }

        if path.suffix.lower() == ".apk":
            payload = {
                "kind": "apk",
                "entry_count": None,
                "top_level": [],
                "extension_counts": {},
                "apks": [inspect_apk(path, logical_name=path.name, max_paths=max_paths)],
                "shared_storage": {
                    "entry_count": 0,
                    "extension_counts": {},
                    "categories": {},
                },
            }
        elif zipfile.is_zipfile(path):
            payload = inspect_outer_zip(path, max_paths=max_paths)
        else:
            raise ValueError(f"Unsupported input: {path}")

    return {
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "inventory": payload,
    }


def verify_expected_sha256(result: dict, expected_sha256: str | None) -> None:
    if not expected_sha256:
        return
    actual = result["source"].get("sha256")
    if actual is None:
        raise ValueError("--expect-sha256 requires a file input")
    expected = expected_sha256.lower().strip()
    if actual.lower() != expected:
        raise ValueError(
            f"SHA-256 mismatch: expected {expected}, got {actual}"
        )


def _category_count(categories: dict, name: str) -> int:
    return int(categories.get(name, {}).get("count", 0))


def render_markdown(result: dict) -> str:
    source = result["source"]
    inventory = result["inventory"]
    lines = [
        "# Android export inventory",
        "",
        f"- Schema: {result['schema_version']}",
        f"- Source: `{source['name']}`",
        f"- Source kind: `{source['kind']}`",
    ]

    if source["size"] is not None:
        lines.append(f"- Size: {source['size']} bytes")
    if source["sha256"] is not None:
        lines.append(f"- SHA-256: `{source['sha256']}`")

    lines.extend([
        f"- Inventory kind: `{inventory['kind']}`",
        f"- APK count: {len(inventory['apks'])}",
        "",
        "## Top-level paths",
    ])

    for item in inventory.get("top_level", []):
        lines.append(f"- `{item}`")
    if not inventory.get("top_level"):
        lines.append("- (none)")

    lines.extend(["", "## APKs"])
    if not inventory["apks"]:
        lines.append("- No APKs detected.")

    for apk in inventory["apks"]:
        categories = apk["categories"]
        lines.extend([
            "",
            f"### {apk['logical_name']}",
            f"- Size: {apk['size']} bytes",
            f"- SHA-256: `{apk['sha256']}`",
            f"- Entries: {apk['entry_count']}",
            f"- manifests: {_category_count(categories, 'manifest')}",
            f"- DEX: {_category_count(categories, 'code')}",
            f"- native libraries: {_category_count(categories, 'native')}",
            f"- assets/: {_category_count(categories, 'assets')}",
            f"- res/: {_category_count(categories, 'resources')}",
            f"- .pack/.list candidates: {_category_count(categories, 'pack_list')}",
            f"- animation candidates: {_category_count(categories, 'animation')}",
            f"- UI image candidates: {_category_count(categories, 'ui_candidate')}",
            f"- audio candidates: {_category_count(categories, 'audio')}",
        ])

        for category_name in (
            "pack_list",
            "animation",
            "ui_candidate",
            "code",
            "native",
        ):
            bucket = categories.get(category_name)
            if not bucket or not bucket["paths"]:
                continue
            lines.append(f"- {category_name} sample paths:")
            for record in bucket["paths"][:50]:
                lines.append(
                    f"  - `{record['path']}` ({record['size']} bytes)"
                )

    shared = inventory["shared_storage"]
    shared_categories = shared.get("categories", {})
    lines.extend([
        "",
        "## Non-APK / shared-storage candidates",
        f"- Entries: {shared.get('entry_count', 0)}",
        f"- .pack/.list candidates: {_category_count(shared_categories, 'pack_list')}",
        f"- image candidates: {_category_count(shared_categories, 'image')}",
        f"- animation candidates: {_category_count(shared_categories, 'animation')}",
        f"- audio candidates: {_category_count(shared_categories, 'audio')}",
    ])

    for category_name in ("pack_list", "animation", "ui_candidate", "audio"):
        bucket = shared_categories.get(category_name)
        if not bucket or not bucket["paths"]:
            continue
        lines.append(f"- {category_name} sample paths:")
        for record in bucket["paths"][:100]:
            lines.append(
                f"  - `{record['path']}` ({record['size']} bytes)"
            )

    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "This report records file metadata and candidate classifications only.",
        "A filename or extension is not treated as proof of a file's semantic role.",
        "No game asset bytes are copied into the report.",
        "",
    ])
    return "\n".join(lines)


def write_reports(result: dict, output_dir: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "inventory.json"
    markdown_path = output_dir / "summary.md"

    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(result), encoding="utf-8")
    return json_path, markdown_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only metadata inventory for a Battle Cats Android export ZIP/APK/directory."
    )
    parser.add_argument("input", type=pathlib.Path)
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("reports/inventory"),
        help="Directory for inventory.json and summary.md",
    )
    parser.add_argument(
        "--expect-sha256",
        default=None,
        help="Optional exact SHA-256 required for a file input",
    )
    parser.add_argument(
        "--max-paths-per-category",
        type=int,
        default=5000,
        help="Maximum sample paths retained per category; counts remain complete",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_paths_per_category < 1:
        parser.error("--max-paths-per-category must be >= 1")

    try:
        result = inventory_path(args.input, max_paths=args.max_paths_per_category)
        verify_expected_sha256(result, args.expect_sha256)
        json_path, markdown_path = write_reports(result, args.output)
    except (FileNotFoundError, ValueError, zipfile.BadZipFile) as exc:
        print(f"inventory failed: {exc}", file=sys.stderr)
        return 2

    print(json_path)
    print(markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
