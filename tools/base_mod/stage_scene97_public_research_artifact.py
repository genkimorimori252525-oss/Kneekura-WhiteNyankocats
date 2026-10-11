"""Stage ONLY the pinned public NDK scene97 research witness from its CI ZIP.

No network requests, no signing secrets, APKs, Android device, SAVE or publisher
app; strict immutable source-artifact hash. Default is read-only preflight.
The user supplies their own downloaded Github Actions ZIP from build run
38154116390 / artifact 11707712363. No release/boot claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import struct
import tempfile
from zipfile import ZipFile, BadZipFile

ARTIFACT_COMMIT = "82b810fc4d437d79fc77a2f00484b1aee576565c"
ARTIFACT_BINARY_SHA256 = "d420fada2073b67388af7a9cafd603809033ab66d5d0532ae4333e385034225a"
ARTIFACT_SUBFOLDER = "scene97-native-public-82b810fc"
BINARY = "libkneekura.so"
RECEIPT = "PUBLIC_PASSIVE_SHIM_RECEIPT.json"
MARKER = b"original-native-scene97-resolver-v1 missing=%u zero=%u one=%u other=%u"
REQUIRED_FILES = frozenset((BINARY, RECEIPT))
EXPECTED_LAYOUTS = (
    frozenset((BINARY, RECEIPT)),
    frozenset(("build/kneekura-scene-research/" + BINARY,
               "build/kneekura-scene-research/" + RECEIPT)),
)


class Scene97PublicArtifactBlocked(ValueError):
    pass


def inspect_artifact(source: Path, *, binary_sha256: str = ARTIFACT_BINARY_SHA256,
                     commit: str = ARTIFACT_COMMIT) -> dict[str, bytes]:
    """Read maximum 400 KiB public source-only artifact; NEVER derive trust from JSON."""
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 400_000:
        raise Scene97PublicArtifactBlocked("missing/unsafe/oversized public CI archive")
    try:
        with ZipFile(source) as archive:
            entries = archive.infolist()
            names = frozenset(info.filename for info in entries)
            if len(entries) != 2 or names not in EXPECTED_LAYOUTS:
                raise Scene97PublicArtifactBlocked("unapproved CI archive member layout")
            payload = {}
            for info in entries:
                name = info.filename.rsplit("/", 1)[-1]
                mode = (info.external_attr >> 16) & 0o170000
                if (mode == stat.S_IFLNK or info.is_dir() or
                    info.file_size > 250_000 or info.compress_size > 350_000 or
                    info.file_size < 16 or info.flag_bits & 1):
                    raise Scene97PublicArtifactBlocked("unsafe research artifact ZIP member")
                with archive.open(info) as stream:
                    # Never decompress beyond the stated, strictly capped
                    # member length even if a malicious ZIP has inconsistent
                    # length fields or excessive compression ratios.
                    data = stream.read(info.file_size + 1)
                    if len(data) != info.file_size or stream.read(1):
                        raise Scene97PublicArtifactBlocked(
                            "corrupt or expanded research artifact member")
                payload[name] = data
    except (BadZipFile, OSError, RuntimeError) as exc:
        raise Scene97PublicArtifactBlocked("unable to read strict public CI archive") from exc
    if set(payload) != REQUIRED_FILES:
        raise Scene97PublicArtifactBlocked("expected EXACTLY two public CI files")
    binary = payload[BINARY]
    if hashlib.sha256(binary).hexdigest() != binary_sha256:
        raise Scene97PublicArtifactBlocked("public source-only ARM64 SHA256 mismatch")
    if binary[:4] != b"\x7fELF" or binary[4:6] != b"\x02\x01" or len(binary) < 64:
        raise Scene97PublicArtifactBlocked("not ELF64 little endian")
    if struct.unpack_from("<H", binary, 18)[0] != 183:
        raise Scene97PublicArtifactBlocked("not AArch64 native")
    if MARKER not in binary or b"kneekura-original-virgin-save-trial-v1" in binary:
        raise Scene97PublicArtifactBlocked("not passive scene97 observer")
    try:
        metadata = json.loads(payload[RECEIPT].decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise Scene97PublicArtifactBlocked("unreadable public CI receipt") from exc
    if (not isinstance(metadata, dict)
        or metadata.get("schema") != "public-original-research-passive-shim-v1"
        or metadata.get("git_commit") != commit
        or metadata.get("sha256") != binary_sha256
        or metadata.get("elf_abi") != "arm64-v8a"
        or metadata.get("fixed_error_markers_compiled") is not True
        or metadata.get("scene97_resolver_histogram_compiled") is not True
        or metadata.get("original_game_or_save_bundled") is not False
        or metadata.get("original_save_writer_enabled") is not False):
        raise Scene97PublicArtifactBlocked("public CI receipt content not pinned")
    return payload


def stage_artifact(repo: Path, payload: dict[str, bytes]) -> tuple[str, Path]:
    """Create-only private source staging, no overwrite; repeatable when identical."""
    root = repo.resolve(strict=True)
    private = root / "private"
    if (not private.is_dir() or private.is_symlink()
        or private.resolve(strict=True) != private.absolute()):
        raise Scene97PublicArtifactBlocked("unsafe or absent owner private root")
    target = private / ARTIFACT_SUBFOLDER
    if target.is_symlink():
        raise Scene97PublicArtifactBlocked("refuse private source symlink")
    if target.exists():
        if not target.is_dir() or set(child.name for child in target.iterdir()) != REQUIRED_FILES:
            raise Scene97PublicArtifactBlocked("existing private research folder differs")
        for key in REQUIRED_FILES:
            item = target / key
            if not item.is_file() or item.is_symlink() or item.read_bytes() != payload[key]:
                raise Scene97PublicArtifactBlocked("existing private research file mismatches")
        return "ALREADY_STAGED_IDENTICAL", target
    temp = Path(tempfile.mkdtemp(prefix=".scene97-source-verified-", dir=private))
    try:
        for key in (BINARY, RECEIPT):
            with (temp / key).open("xb") as writer:
                writer.write(payload[key])
                writer.flush()
        for key in REQUIRED_FILES:
            if (temp / key).read_bytes() != payload[key]:
                raise Scene97PublicArtifactBlocked("staged CI bytes drifted")
        if target.exists() or target.is_symlink():
            raise Scene97PublicArtifactBlocked("private destination raced")
        temp.rename(target)
        return "STAGED_PUBLIC_RESEARCH_ONLY", target
    finally:
        if temp.exists() and temp != target:
            shutil.rmtree(temp)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--artifact-zip", type=Path, required=True)
    parser.add_argument("--stage", action="store_true",
                        help="Explicitly stage two verified public files under private/")
    args = parser.parse_args()
    try:
        payload = inspect_artifact(args.artifact_zip)
        repo = args.repo.resolve(strict=True)
        if args.stage:
            status, target = stage_artifact(repo, payload)
        else:
            status, target = "PASS_READ_ONLY_PUBLIC_CI_ARTIFACT_PINNED", (
                repo / "private" / ARTIFACT_SUBFOLDER)
        print(json.dumps({
            "status": status,
            "source_public_ci_run": 38154116390,
            "source_public_commit": ARTIFACT_COMMIT[:12],
            "original_game_or_SAVE_read": False,
            "device_or_signing_key_used": False,
            "new_private_folder": str(target) if args.stage else None,
        }, ensure_ascii=True, sort_keys=True))
        return 0
    except (OSError, Scene97PublicArtifactBlocked) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
