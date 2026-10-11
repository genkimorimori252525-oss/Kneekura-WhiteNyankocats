"""JP15.7.1 owner-owned 35-lane vs historical-mirror coverage auditor.

The source of truth is the user's exact owned six-split ZIP and its ORIGINAL
35 plain download_N.tsv tables. The public GitHub *tree index* supplies
filename+size candidate metadata ONLY: an equal size is NEVER called MD5
verified or suitable for a production/offline game.

Read-only by default. Optional local-file inspection validates exact historical
MD5, without reading file payload into JSON, copying copyrighted assets,
fetching the publisher's services, or modifying the original APK/SAVE.
A special empty XImageDataServer pair can be deterministically recreated
privately ONLY when its bytes match the owner's original manifest MD5.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from urllib import request, error
import zipfile

from tools.base_mod.battlecats_pack_writer import encrypt_manifest_bytes

OWNED_ZIP_SHA256 = (
    "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
)
INSTALLPACK_MEMBER = "apk/split_InstallPack.apk"
LANE_COUNT = 35
FILE_COUNT = 358
SERVER_FILE_COUNT = 186
AUDIO_FILE_COUNT = 172
MIRROR_TREE_URL = (
    "https://api.github.com/repos/fieryhenry/BCData/git/trees/main?recursive=1"
)
MIRROR_INDEX_MAX_BYTES = 16 * 1024 * 1024
OWNER_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_ROOT = OWNER_ROOT / "private"
ALLOWED_NAME = re.compile(
    r"(?:[A-Za-z][A-Za-z0-9]*Server\.(?:list|pack)|[0-9]{3}\.(?:ogg|caf))"
)
MD5 = re.compile(r"[a-f0-9]{32}")
EMPTY_NAMES = ("XImageDataServer.list", "XImageDataServer.pack")


class OriginalServerMirrorAuditError(ValueError):
    """A source file or metadata claim is not safely version-confirmed."""


@dataclass(frozen=True)
class OwnerRow:
    size: int
    md5: str
    download_lane: int


def _stream_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_owner_download_tables(payloads: dict[int, bytes], *,
                                exact_owner: bool = True) -> dict[str, OwnerRow]:
    if set(payloads) != set(range(LANE_COUNT)):
        raise OriginalServerMirrorAuditError("all 35 original download lanes required")
    rows: dict[str, OwnerRow] = {}
    for lane in range(LANE_COUNT):
        try:
            content = payloads[lane].decode("utf-8-sig")
        except UnicodeError as exc:
            raise OriginalServerMirrorAuditError("owner lane is not UTF-8") from exc
        lines = [line for line in content.splitlines() if line.strip()]
        if not lines or not lines[0].startswith("\t"):
            raise OriginalServerMirrorAuditError("original download lane header missing")
        for raw in lines[1:]:
            cols = raw.split("\t")
            if len(cols) != 3:
                raise OriginalServerMirrorAuditError("unexpected original lane columns")
            name, decimal, md5 = cols
            if (not ALLOWED_NAME.fullmatch(name)
                or not decimal.isascii() or not decimal.isdecimal()
                or not MD5.fullmatch(md5)):
                raise OriginalServerMirrorAuditError(
                    "original lane filename/size/checksum malformed"
                )
            if name in rows:
                raise OriginalServerMirrorAuditError(
                    "duplicated original source filename across download lanes"
                )
            size = int(decimal)
            if size > 256 * 1024 * 1024:
                raise OriginalServerMirrorAuditError("one original source exceeds bound")
            rows[name] = OwnerRow(size, md5, lane)
    if exact_owner:
        server = [x for x in rows if x.endswith((".list", ".pack"))]
        audio = [x for x in rows if x.endswith((".ogg", ".caf"))]
        if (len(rows), len(server), len(audio)) != (
            FILE_COUNT, SERVER_FILE_COUNT, AUDIO_FILE_COUNT
        ):
            raise OriginalServerMirrorAuditError(
                "owner extra-data 358/186/172 inventory is not exact JP15.7.1"
            )
        families = {}
        for name in server:
            family, extension = name.rsplit(".", 1)
            families.setdefault(family, set()).add(extension)
        if len(families) != 93 or any(s != {"list", "pack"} for s in families.values()):
            raise OriginalServerMirrorAuditError("expected exactly 93 complete original Server pairs")
    return rows


def read_exact_owner_export_tables(owned_zip: Path) -> dict[str, OwnerRow]:
    if (not isinstance(owned_zip, Path) or owned_zip.is_symlink()
        or not owned_zip.is_file()
        or _stream_hash(owned_zip, "sha256") != OWNED_ZIP_SHA256):
        raise OriginalServerMirrorAuditError(
            "original JP15.7.1 owner export SHA256 mismatch or missing"
        )
    try:
        with zipfile.ZipFile(owned_zip, "r") as outer:
            info = outer.getinfo(INSTALLPACK_MEMBER)
            if info.file_size > 200 * 1024 * 1024:
                raise OriginalServerMirrorAuditError("original InstallPack exceeds bound")
            inner_bytes = outer.read(info)
        with zipfile.ZipFile(io.BytesIO(inner_bytes), "r") as install:
            payloads = {
                lane: install.read(f"assets/download_{lane}.tsv")
                for lane in range(LANE_COUNT)
            }
    except (zipfile.BadZipFile, KeyError, OSError) as exc:
        raise OriginalServerMirrorAuditError(
            "owned original install-pack 35-lane metadata missing/invalid"
        ) from exc
    return parse_owner_download_tables(payloads)


def parse_historical_mirror_index(obj: dict) -> dict[str, int]:
    """Take filename/byte-size metadata only, NOT source bytes/checksums."""
    if not isinstance(obj, dict) or obj.get("truncated") is not False:
        raise OriginalServerMirrorAuditError("public tree metadata incomplete or truncated")
    nodes = obj.get("tree")
    if not isinstance(nodes, list) or len(nodes) > 80000:
        raise OriginalServerMirrorAuditError("public tree metadata unexpectedly shaped")
    result: dict[str, int] = {}
    for node in nodes:
        if not isinstance(node, dict) or node.get("type") != "blob":
            continue
        path = node.get("path")
        if not isinstance(path, str) or not path.startswith("jp_server/"):
            continue
        name = path[len("jp_server/"):]
        if not ALLOWED_NAME.fullmatch(name):
            continue
        size = node.get("size")
        if type(size) is not int or not 0 <= size <= 256 * 1024 * 1024:
            raise OriginalServerMirrorAuditError("invalid public mirror source size")
        if name in result:
            raise OriginalServerMirrorAuditError("duplicated mirror filename")
        result[name] = size
    return result


def compare_mirror_size_metadata(rows: dict[str, OwnerRow],
                                 mirror: dict[str, int]) -> dict:
    same = sorted(name for name, row in rows.items()
                  if mirror.get(name) == row.size)
    mismatched = {
        name: {"owner_bytes": row.size, "mirror_bytes": mirror[name]}
        for name, row in sorted(rows.items())
        if name in mirror and row.size != mirror[name]
    }
    missing = sorted(name for name in rows if name not in mirror)
    server = [name for name in same if name.endswith((".list", ".pack"))]
    audio = [name for name in same if name.endswith((".ogg", ".caf"))]
    return {
        "status": "PUBLIC_MIRROR_NAME_AND_SIZE_CANDIDATES_ONLY",
        "original_manifest_entries": len(rows),
        "mirror_candidate_entries": len(mirror),
        "matching_filename_and_size": len(same),
        "matching_server_list_pack_files": len(server),
        "matching_audio_files": len(audio),
        "matching_candidate_bytes": sum(rows[name].size for name in same),
        "mismatching_sizes": mismatched,
        "missing_filenames": missing,
        "missing_original_family_names": sorted({
            name.rsplit(".", 1)[0] for name in missing
            if name.endswith((".list", ".pack"))
        }),
        "MD5_for_any_mirror_candidate_proven_by_tree": False,
        "downloaded_or_decoded_proprietary_asset_bytes": False,
        "full_original_offline_gameplay_or_SAVE_verified": False,
    }


def check_local_exact_md5(rows: dict[str, OwnerRow],
                          directory: Path) -> dict:
    if directory.is_symlink() or not directory.is_dir():
        raise OriginalServerMirrorAuditError("owner-private input is missing or a symlink")
    verified = []
    for name, row in sorted(rows.items()):
        path = directory / name
        if path.is_symlink():
            raise OriginalServerMirrorAuditError("symlink in owner-local source candidates")
        if not path.exists():
            continue
        if not path.is_file() or path.stat().st_size != row.size:
            raise OriginalServerMirrorAuditError(
                f"invalid owner-local file size: {name}"
            )
        if _stream_hash(path, "md5") != row.md5:
            raise OriginalServerMirrorAuditError(
                f"original JP15.7.1 MD5 mismatch: {name}"
            )
        verified.append({
            "name": name, "size": row.size, "md5": row.md5,
            "sha256": _stream_hash(path, "sha256"),
        })
    return {
        "status": "EXACT_ORIGINAL_MD5_ON_OWNER_LOCAL_FILES_ONLY",
        "verified_count": len(verified),
        "verified_files": verified,
        "all_358_original_files_MD5_verified": len(verified) == len(rows),
        "original_APK_SAVE_or_account_touched": False,
    }


def make_exact_original_empty_ximagedata(rows: dict[str, OwnerRow]) -> dict[str, bytes]:
    """Reconstruct only the source-proven zero-file family; no other synthetic pack."""
    candidates = {
        EMPTY_NAMES[0]: encrypt_manifest_bytes(b"0\n"),
        EMPTY_NAMES[1]: b"",
    }
    for name, payload in candidates.items():
        row = rows.get(name)
        if (row is None or row.size != len(payload)
            or hashlib.md5(payload).hexdigest() != row.md5):
            raise OriginalServerMirrorAuditError(
                f"original empty Server source does not hash-match: {name}"
            )
    return candidates


def write_exact_empty_pair_privately(rows: dict[str, OwnerRow],
                                     destination: Path) -> dict:
    """Explicit, private, exclusive write after MD5 matches both original names."""
    payloads = make_exact_original_empty_ximagedata(rows)
    private = PRIVATE_ROOT.resolve()
    if PRIVATE_ROOT.is_symlink():
        raise OriginalServerMirrorAuditError("private/ cannot be symlinked")
    output = (destination if destination.is_absolute() else OWNER_ROOT / destination)
    output = output.resolve()
    if (not output.is_relative_to(private) or output == private
        or output.exists()):
        raise OriginalServerMirrorAuditError(
            "empty Server pair destination must be a new directory under private/"
        )
    # A symlinked parent cannot escape private through Path.resolve above.
    output.mkdir(parents=True, exist_ok=False)
    for name, content in payloads.items():
        with (output / name).open("xb") as f:
            f.write(content)
    return {
        "status": "EXACT_JP1571_EMPTY_XIMAGEDATA_PAIR_PRIVATE_ONLY",
        "private_files": [
            {"name": name, "size": len(b), "md5": hashlib.md5(b).hexdigest(),
             "sha256": hashlib.sha256(b).hexdigest()}
            for name, b in sorted(payloads.items())
        ],
        "original_game_loaded_empty_pair": False,
        "other_missing_X_Server_families_recovered": False,
        "APK_or_SAVE_modified": False,
    }


def fetch_metadata_only_tree(opener=request.urlopen) -> dict:
    req = request.Request(
        MIRROR_TREE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Kneekura-ReadOnly-Metadata-Audit/1.0",
        },
    )
    with opener(req, timeout=35) as response:
        b = response.read(MIRROR_INDEX_MAX_BYTES + 1)
    if len(b) > MIRROR_INDEX_MAX_BYTES:
        raise OriginalServerMirrorAuditError("mirror index exceeds metadata size cap")
    try:
        return json.loads(b.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OriginalServerMirrorAuditError("mirror GitHub tree JSON invalid") from exc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owned-zip", type=Path, required=True,
                   help="User-owned original JP15.7.1 zip, read-only")
    source = p.add_mutually_exclusive_group()
    source.add_argument("--mirror-index", type=Path,
                        help="Previously saved, complete GitHub git-tree JSON metadata")
    source.add_argument("--public-github-tree", action="store_true",
                        help="Read public GitHub TREE metadata only; no game files downloaded")
    p.add_argument("--local-files", type=Path,
                   help="Optional already-recovered owner-private file directory")
    p.add_argument("--write-empty-ximagedata", type=Path,
                   help="Opt-in: write exact hash-verified 16+0 byte pair under private/")
    args = p.parse_args(argv)
    try:
        rows = read_exact_owner_export_tables(args.owned_zip)
        receipt = {
            "owner_export_sha256": OWNED_ZIP_SHA256,
            "original_lane_count": LANE_COUNT,
            "original_file_count": len(rows),
            "owner_data_only_read": True,
            "licensed_game_assets_committed": False,
        }
        if args.mirror_index or args.public_github_tree:
            index = (json.loads(args.mirror_index.read_text(encoding="utf-8"))
                     if args.mirror_index else fetch_metadata_only_tree())
            receipt["mirror"] = compare_mirror_size_metadata(
                rows, parse_historical_mirror_index(index)
            )
        if args.local_files:
            receipt["actual_local_MD5"] = check_local_exact_md5(rows, args.local_files)
        if args.write_empty_ximagedata:
            receipt["deterministic_empty_source_pair"] = (
                write_exact_empty_pair_privately(rows, args.write_empty_ximagedata)
            )
        print(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, zipfile.BadZipFile,
            error.URLError, error.HTTPError) as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
