"""Obtain/verify JP15.7.1 Godzilla source pairs for owner-private research only.

The game's original archives, images and model bytes must NOT be committed to Git.
Default: print a plan; no network, device access, APK/SAVE edits or writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from urllib import error, request

SOURCE = "https://raw.githubusercontent.com/fieryhenry/BCData/main/jp_server/"
EXPORT_SHA256 = "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
# Pinned to the owner's JP15.7.1 InstallPack download_*.tsv manifest.
FILES = {
    "MNumberServer.list": (2832, "34219ad4ddebe715ddaa3af4244697b1"),
    "MNumberServer.pack": (10637344, "0c23c4defa077d2e97fbbb1b28a0de4d"),
    "WImageDataServer.list": (451888, "1ddee28c515a52ebd0a09d655745945c"),
    "WImageDataServer.pack": (79788272, "cebd0898a2c9d68fa3c7631afa9dd0d2"),
}
DEFAULT_OUTPUT = Path("private/server-jp1571/godzilla")
CHUNK = 1024 * 1024


def verify(path: Path, expected: tuple[int, str]) -> dict:
    if not path.is_file():
        raise ValueError(f"missing file: {path}")
    digest = hashlib.md5()  # Equality with historical publisher metadata, not a security signature.
    sha256 = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            size += len(chunk)
            if size > expected[0]:
                raise ValueError(f"oversized source: {path.name}")
            digest.update(chunk)
            sha256.update(chunk)
    if (size, digest.hexdigest()) != expected:
        raise ValueError(f"JP15.7.1 size/MD5 mismatch: {path.name}")
    return {"name": path.name, "size": size, "md5": digest.hexdigest(), "sha256": sha256.hexdigest()}


def stage_verified(destination: Path, expected: tuple[int, str], *, source: Path | None = None,
                   opener=request.urlopen) -> dict:
    """Copy or download into a temp file; promote only after exact verification."""
    spec = expected
    if destination.exists():
        return verify(destination, spec)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".kneekura-", suffix=".part", delete=False) as out:
            temp_path = Path(out.name)
            if source is not None:
                with source.open("rb") as inp:
                    shutil.copyfileobj(inp, out, CHUNK)
            else:
                req = request.Request(SOURCE + destination.name, headers={"User-Agent": "Kneekura-Private-Research/1.0"})
                with opener(req, timeout=90) as response:
                    if getattr(response, "status", 200) != 200:
                        raise ValueError(f"mirror returned HTTP {response.status}")
                    copied = 0
                    while True:
                        chunk = response.read(CHUNK)
                        if not chunk:
                            break
                        copied += len(chunk)
                        if copied > spec[0]:
                            raise ValueError("mirror returned more bytes than original manifest")
                        out.write(chunk)
        proof = verify(temp_path, spec)
        if destination.exists():
            return verify(destination, spec)
        temp_path.rename(destination)
        temp_path = None
        return {**proof, "name": destination.name}
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def acquire(mode: str, output: Path, source: Path | None = None, *, opener=request.urlopen) -> dict:
    if mode == "import":
        if source is None:
            raise ValueError("--from-dir is required for import")
        # Fail closed before writing anything if one owner-held input is absent/wrong.
        for name, spec in FILES.items():
            verify(source / name, spec)
    elif mode not in ("download", "verify"):
        raise ValueError("unknown operation")
    receipts = []
    for name, spec in FILES.items():
        target = output / name
        proof = (verify(target, spec) if mode == "verify"
                 else stage_verified(target, spec,
                                     source=(source / name if mode == "import" else None),
                                     opener=opener))
        proof["name"] = name
        receipts.append(proof)
    result = {
        "status": "VERIFIED_FOUR_JP15_7_1_SOURCE_FILES",
        "source_manifest_sha256": EXPORT_SHA256,
        "origin": "owner-local import" if mode == "import" else "fieryhenry/BCData historical mirror" if mode == "download" else "local verify",
        "files": receipts,
        "owner_assets_committed_to_git": False,
    }
    # Metadata-only receipt. Never copy .pack/.list into tracked directories.
    output.mkdir(parents=True, exist_ok=True)
    (output / "godzilla-server-source-receipt.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--from-dir", type=Path, help="Import four already-verified files from the owner's local cache")
    mode.add_argument("--download", action="store_true", help="Download from the public historical mirror, then verify")
    mode.add_argument("--verify-only", action="store_true", help="Verify locally, without network")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if not (args.from_dir or args.download or args.verify_only):
        print("JP15.7.1 Godzilla source archive plan (no files downloaded):")
        for name, (size, md5) in FILES.items():
            print(f"  {name}: {size:,} bytes / MD5 {md5}")
        print("Run with --from-dir PATH, --download, or --verify-only.")
        return 0
    chosen = "import" if args.from_dir else "download" if args.download else "verify"
    try:
        result = acquire(chosen, args.output, args.from_dir)
    except (OSError, ValueError, error.HTTPError, error.URLError) as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for receipt in result["files"]:
        print(f"[PASS] {receipt['name']} size={receipt['size']} MD5={receipt['md5']}")
    print(f"[SUCCESS] Four exact JP15.7.1 files available privately at {args.output.resolve()}")
    print("Next: use tools.base_mod.extract_godzilla_owner_rig with these two Server pairs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
