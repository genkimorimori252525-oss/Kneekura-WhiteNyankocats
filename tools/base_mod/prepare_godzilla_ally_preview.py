"""Owner-private ENEMY Godzilla 550_e -> ALLIED No703 FIRST-form 702_f preview.

The real JP15.7.1 enemy rig comes from the owner's MD5-matched original
MNumberServer/WImageDataServer encrypted packs. This is strictly a validated,
byte-preserving candidate for original-game renderer research, NOT a patched
APK, a playable unit or proof of correct left/right animation.

Original animation grammar was corroborated against JP15.7.1 InstallPack
ImageDataLocal sample enemy 730_e and ally 799_f; those samples are never
committed, copied, or distributed by this tool.

Changes only:
  - filenames 550_e.* -> 702_f.* / 550_eNN.maanim -> 702_fNN.maanim;
  - .imgcut's PNG name (its third header line);
  - .mamodel's numeric atlas ID in model rows (550 -> 702);
  - if the single base/root row has a negative horizontal scale, normalize
    its sign to positive (original enemy vs allied facing example).
All animation keyframes and every nonessential model/image field remain intact.
The original source/receipt is never written, and second-form 702_c is untouched.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import struct
import tempfile
from typing import Any

from tools.base_mod.extract_godzilla_owner_rig import PNG_FILE, ANIM_FILES

SOURCE_STEM = "550_e"
TARGET_STEM = "702_f"
TARGET_IMAGE_ID = 702
SOURCE_IMAGE_ID = 550
SOURCE_FILES = (PNG_FILE, *ANIM_FILES)  # extractor defines six non-PNG: cut, model, four .maanim
ALLOWED_SOURCE_SET = frozenset(SOURCE_FILES)
MAX_SINGLE_ASSET = 64 * 1024 * 1024
MAX_RESEARCH_IMAGE_DIMENSION = 32768
_TARGET_FILE_RE = re.compile(r"^550_e(?:(0[0-3])\.maanim|(\.png|\.imgcut|\.mamodel))$")


class OriginalGodzillaRigPreviewError(ValueError):
    """Do not guess and write a partly converted or invalid original rig."""


def _target_name(filename: str) -> str:
    match = _TARGET_FILE_RE.fullmatch(filename)
    if not match or filename not in ALLOWED_SOURCE_SET:
        raise OriginalGodzillaRigPreviewError("unexpected original 550_e file")
    return TARGET_STEM + (match.group(1) + ".maanim" if match.group(1) else match.group(2))


def _hash(blob: bytes) -> str:
    return sha256(blob).hexdigest()


def _native_lines(raw: bytes, *, label: str) -> list[bytes]:
    if not raw or len(raw) > MAX_SINGLE_ASSET or b"\x00" in raw:
        raise OriginalGodzillaRigPreviewError(label + ": not bounded original text")
    # Strict UTF-8 with optional BOM; preserve original newline style.
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise OriginalGodzillaRigPreviewError(
            label + ": undecodable original UTF-8"
        ) from exc
    if not text or "\ufffd" in text:
        raise OriginalGodzillaRigPreviewError(label + ": undecodable original format")
    lines = raw.splitlines(keepends=True)
    if not lines or len(lines) > 150_000:
        raise OriginalGodzillaRigPreviewError(label + ": invalid line count")
    return lines


def _text_at(lines: list[bytes], index: int, *, label: str) -> str:
    try:
        return lines[index].decode("utf-8-sig").rstrip("\r\n")
    except (IndexError, UnicodeError) as exc:
        raise OriginalGodzillaRigPreviewError(label + ": truncated or invalid text") from exc


def _positive_int(
    token: str, *, label: str, max_value: int, minimum: int = 1,
) -> int:
    if not token.isascii() or not token.isdecimal():
        raise OriginalGodzillaRigPreviewError(label + ": count is not a positive decimal")
    count = int(token)
    if not minimum <= count <= max_value:
        raise OriginalGodzillaRigPreviewError(label + ": count outside original research limit")
    return count


def _newline_of(line: bytes) -> bytes:
    if line.endswith(b"\r\n"):
        return b"\r\n"
    if line.endswith(b"\n"):
        return b"\n"
    return b""


def _check_png_header(raw: bytes) -> dict[str, int]:
    if (len(raw) < 33 or raw[:8] != b"\x89PNG\r\n\x1a\n"
        or raw[12:16] != b"IHDR"):
        raise OriginalGodzillaRigPreviewError("550_e.png invalid source PNG/IHDR")
    width, height = struct.unpack(">II", raw[16:24])
    if (not 1 <= width <= MAX_RESEARCH_IMAGE_DIMENSION
        or not 1 <= height <= MAX_RESEARCH_IMAGE_DIMENSION):
        raise OriginalGodzillaRigPreviewError("550_e.png invalid atlas dimensions")
    return {"width": width, "height": height}


def _rewrite_cut(raw: bytes, *, width: int, height: int) -> tuple[bytes, dict[str, Any]]:
    lines = _native_lines(raw, label="550_e.imgcut")
    if (len(lines) < 5 or _text_at(lines, 0, label="imgcut") != "[imgcut]"
        or _text_at(lines, 1, label="imgcut") != "0"
        or _text_at(lines, 2, label="imgcut") != SOURCE_STEM + ".png"):
        raise OriginalGodzillaRigPreviewError("unexpected original 550_e.imgcut header")
    count = _positive_int(_text_at(lines, 3, label="imgcut"),
                          label="imgcut pieces", max_value=10000)
    if len(lines) - 4 != count:
        raise OriginalGodzillaRigPreviewError("imgcut declared sprite count differs from rows")
    for idx in range(4, len(lines)):
        data = _text_at(lines, idx, label="imgcut item").split(",", 4)
        if len(data) < 4:
            raise OriginalGodzillaRigPreviewError("imgcut rectangle too short")
        try:
            x, y, w, h = [int(item) for item in data[:4]]
        except ValueError as exc:
            raise OriginalGodzillaRigPreviewError("imgcut rectangle not numeric") from exc
        if (x < 0 or y < 0 or w <= 0 or h <= 0
            or x + w > width or y + h > height):
            raise OriginalGodzillaRigPreviewError("imgcut sprite outside original PNG bounds")
    eol = _newline_of(lines[2])
    lines[2] = (TARGET_STEM + ".png").encode() + eol
    return b"".join(lines), {
        "sprite_part_count": count,
        "reference_changed_from": SOURCE_STEM + ".png",
        "reference_changed_to": TARGET_STEM + ".png",
        "all_cut_rectangles_within_PNG": True,
    }


def _rewrite_model(raw: bytes, *, sprite_part_count: int) -> tuple[bytes, dict[str, Any]]:
    lines = _native_lines(raw, label="550_e.mamodel")
    header = _text_at(lines, 0, label="mamodel")
    if header not in ("[modelanim:model]", "[modelanim:model2]"):
        raise OriginalGodzillaRigPreviewError("unsupported original enemy mamodel version")
    edition = _text_at(lines, 1, label="mamodel")
    if edition not in ("3", "4"):
        raise OriginalGodzillaRigPreviewError("unsupported original mamodel revision")
    count = _positive_int(_text_at(lines, 2, label="mamodel"),
                          label="mamodel nodes", max_value=30000)
    if len(lines) < 3 + count:
        raise OriginalGodzillaRigPreviewError("truncated original mamodel nodes")
    source_models = 0
    converted_models = 0
    mirrored_root = False
    for index in range(3, count + 3):
        line = _text_at(lines, index, label="model node")
        values = line.split(",", 13)
        if len(values) != 14:
            raise OriginalGodzillaRigPreviewError("original mamodel row structure drift")
        try:
            numeric = [int(v) for v in values[:13]]
        except ValueError as exc:
            raise OriginalGodzillaRigPreviewError("invalid original mamodel numeric field") from exc
        if index == 3 and numeric[:2] != [-1, -1]:
            raise OriginalGodzillaRigPreviewError("first original model row is not base root")
        image_id = numeric[1]
        if image_id not in (-1, SOURCE_IMAGE_ID):
            raise OriginalGodzillaRigPreviewError(
                "mamodel uses another atlas image ID; not safe to auto-convert"
            )
        if not 0 <= numeric[2] < sprite_part_count:
            raise OriginalGodzillaRigPreviewError(
                "mamodel references sprite index outside original imgcut"
            )
        # Only the changed fields are serialized anew; preserve every
        # other source column's original textual representation and labels.
        replaced = list(values)
        if image_id == SOURCE_IMAGE_ID:
            replaced[1] = str(TARGET_IMAGE_ID)
            source_models += 1
        # The true root row is the only row whose scale is changed, and
        # only if its horizontal scale is negative. Never modify attack
        # keyframes, bone rotations, collision sections or offsets.
        if index == 3 and numeric[8] < 0:
            replaced[8] = str(-numeric[8])
            mirrored_root = True
        if index == 3 and numeric[8] == 0:
            raise OriginalGodzillaRigPreviewError("mamodel root has zero horizontal scale")
        # Original comments/labels, geometry, orientation-independent
        # fields and spacing are untouched at the byte-value level.
        target = ",".join(replaced)
        if target != line:
            lines[index] = target.encode("utf-8") + _newline_of(lines[index])
            converted_models += 1
    if not source_models:
        raise OriginalGodzillaRigPreviewError(
            "mamodel contains no original enemy 550 image atlas references"
        )
    return b"".join(lines), {
        "model_format": header,
        "declared_model_nodes": count,
        "atlas_ref_source_id": SOURCE_IMAGE_ID,
        "atlas_ref_target_id": TARGET_IMAGE_ID,
        "atlas_rows_rebased": source_models,
        "rows_changed": converted_models,
        "root_was_reoriented": mirrored_root,
        "extra_collision_and_model_footer_bytes_preserved": True,
        "renderer_orientation_correct_on_real_android": False,
    }


def _inspect_animation(
    raw: bytes, *, name: str, model_node_count: int,
) -> dict[str, Any]:
    """Original tracks are tied to model node indices, not free-standing CSV.

    The owned JP15.7.1 ImageDataLocal corpus has genuine .maanim files
    with zero tracks, zero-keyframe tracks, signed/negative frame indices,
    and a special -2 node reference. Keep all source bytes unchanged.
    """
    lines = _native_lines(raw, label=name)
    header = _text_at(lines, 0, label=name)
    if header not in ("[modelanim:animation]", "[modelanim:animation2]"):
        raise OriginalGodzillaRigPreviewError(name + ": unknown model animation format")
    if _text_at(lines, 1, label=name) not in ("1", "2"):
        raise OriginalGodzillaRigPreviewError(name + ": unsupported animation revision")
    count = _positive_int(_text_at(lines, 2, label=name),
                          label=name, max_value=30000, minimum=0)
    current = 3
    keyframes = 0
    negative_frame_keys = 0
    special_node_tracks = 0
    zero_frame_tracks = 0
    max_frame = None
    for _ in range(count):
        track = _text_at(lines, current, label=name)
        columns = track.split(",", 5)
        if len(columns) < 5:
            raise OriginalGodzillaRigPreviewError(name + ": malformed track header")
        try:
            track_fields = [int(item) for item in columns[:5]]
        except ValueError as exc:
            raise OriginalGodzillaRigPreviewError(
                name + ": nonnumeric original track field"
            ) from exc
        node_index = track_fields[0]
        if node_index == -2:
            special_node_tracks += 1
        elif not 0 <= node_index < model_node_count:
            raise OriginalGodzillaRigPreviewError(
                name + ": animation refers to nonexistent model node"
            )
        # Eight zero-track .maanim files and six zero-keyframe tracks were
        # found across 1,814 original local animation assets.
        frames = _positive_int(_text_at(lines, current + 1, label=name),
                               label=name + " keyframes",
                               max_value=50000, minimum=0)
        if frames == 0:
            zero_frame_tracks += 1
        end = current + 2 + frames
        if end > len(lines):
            raise OriginalGodzillaRigPreviewError(name + ": truncated keyframes")
        for at in range(current + 2, end):
            fields = _text_at(lines, at, label=name).split(",")
            if len(fields) != 4:
                raise OriginalGodzillaRigPreviewError(
                    name + ": original keyframe must contain four integers"
                )
            try:
                values = [int(item) for item in fields]
            except ValueError as exc:
                raise OriginalGodzillaRigPreviewError(
                    name + ": original keyframe includes nonnumeric values"
                ) from exc
            frame = values[0]
            if not -1000000 <= frame <= 1000000:
                raise OriginalGodzillaRigPreviewError(
                    name + ": original keyframe time outside bound"
                )
            if frame < 0:
                negative_frame_keys += 1
            if max_frame is None or frame > max_frame:
                max_frame = frame
        current = end
        keyframes += frames
    if current != len(lines):
        raise OriginalGodzillaRigPreviewError(name + ": trailing/unparsed frame data")
    return {
        "native_animation_format": header,
        "track_count": count,
        "keyframe_count": keyframes,
        "empty_animation_tracks_accepted": count == 0,
        "zero_keyframe_track_count": zero_frame_tracks,
        "negative_frame_key_count": negative_frame_keys,
        "special_minus_two_node_track_count": special_node_tracks,
        "largest_frame_number": max_frame,
        "model_node_references_validated": True,
        "keyframe_bytes_preserved_identical": True,
    }


def preview_converted_ally_rig(
    source: dict[str, bytes], *, source_receipt: dict | None = None,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Pure function: validated owner rig in, isolated preview and receipt out."""
    if set(source) != ALLOWED_SOURCE_SET:
        raise OriginalGodzillaRigPreviewError(
            "requires exactly seven original 550_e source filenames"
        )
    if source_receipt is not None:
        if (source_receipt.get("status")
                != "EXTRACTED_OWNER_ONLY_NOT_MIRRORED_OR_INSTALLED"
            or source_receipt.get("source_stem") != SOURCE_STEM
            or source_receipt.get("target_stem") != TARGET_STEM
            or set(source_receipt.get("art", {})) != ALLOWED_SOURCE_SET):
            raise OriginalGodzillaRigPreviewError("original owner rig receipt mismatch")
        for name, body in source.items():
            actual = source_receipt["art"][name]
            if actual.get("sha256") != _hash(body) or actual.get("size") != len(body):
                raise OriginalGodzillaRigPreviewError(
                    "owner rig art changed after original extraction"
                )
    geometry = _check_png_header(source[PNG_FILE])
    cut, cut_receipt = _rewrite_cut(
        source[SOURCE_STEM + ".imgcut"], **geometry
    )
    model, model_receipt = _rewrite_model(
        source[SOURCE_STEM + ".mamodel"],
        sprite_part_count=cut_receipt["sprite_part_count"],
    )
    generated = {
        TARGET_STEM + ".png": source[PNG_FILE],
        TARGET_STEM + ".imgcut": cut,
        TARGET_STEM + ".mamodel": model,
    }
    animations = {}
    for name in ANIM_FILES:
        if not name.endswith(".maanim"):
            continue  # .imgcut and .mamodel were validated and converted above
        details = _inspect_animation(
            source[name], name=name,
            model_node_count=model_receipt["declared_model_nodes"],
        )
        generated[_target_name(name)] = source[name]  # bytes unchanged
        animations[name] = details
    receipts = {
        "schema_version": 1,
        "status": "GODZILLA_FIRST_FORM_RIG_PREVIEW_ONLY_NOT_INSTALLABLE",
        "enemy_no": 552, "source_stem": SOURCE_STEM,
        "cat_no": 703, "cat_form_index": 0, "target_stem": TARGET_STEM,
        "source_art": {
            n: {"bytes": len(v), "sha256": _hash(v)}
            for n, v in sorted(source.items())
        },
        "candidate_ally_art": {
            n: {"bytes": len(v), "sha256": _hash(v)}
            for n, v in sorted(generated.items())
        },
        "atlas_geometry": geometry,
        "imgcut_conversion": cut_receipt,
        "mamodel_conversion": model_receipt,
        "animations_untouched": animations,
        "preserved_second_form": "702_c",
        "second_form_bytes_changed": False,
        "source_art_bytes_modified": False,
        "original_apk_or_pack_or_SAVE_modified": False,
        "animation_renderer_frame_sync_verified": False,
        "actual_gameplay_castle_one_damage_verified": False,
        "original_game_Android_device_verified": False,
        "ready_to_install": False,
    }
    return generated, receipts


def prepare_from_private_source(source_dir: Path, output_dir: Path) -> dict[str, Any]:
    if (not source_dir.is_dir() or source_dir.is_symlink()
        or output_dir.exists() or output_dir.is_symlink()
        or source_dir.resolve() == output_dir.resolve()):
        raise OriginalGodzillaRigPreviewError(
            "owner preview input must be a directory; output must not exist"
        )
    archive: dict[str, bytes] = {}
    for name in SOURCE_FILES:
        path = source_dir / name
        if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= MAX_SINGLE_ASSET):
            raise OriginalGodzillaRigPreviewError(
                "missing or unsafe owner original 550_e source: " + name
            )
        archive[name] = path.read_bytes()
    old_receipt = source_dir / "rig-receipt.json"
    signed_metadata = None
    if old_receipt.exists():
        if old_receipt.is_symlink() or old_receipt.stat().st_size > 1024 * 1024:
            raise OriginalGodzillaRigPreviewError("unsafe original rig metadata")
        signed_metadata = json.loads(old_receipt.read_text(encoding="utf-8"))
    generated, report = preview_converted_ally_rig(
        archive, source_receipt=signed_metadata
    )
    if output_dir.parent.is_symlink():
        raise OriginalGodzillaRigPreviewError("unsafe owner preview parent path")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".kneekura-ally-rig-preview-", dir=output_dir.parent
    ) as temporary:
        stage = Path(temporary) / "ally-preview"
        stage.mkdir()
        for filename, body in generated.items():
            (stage / filename).write_bytes(body)
        (stage / "rig-conversion-preview-receipt.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        # Commit all files only after full conversion passes, and never
        # overwrite an existing private owner art directory.
        if output_dir.exists():
            raise OriginalGodzillaRigPreviewError("owner preview appeared during staging")
        stage.rename(output_dir)
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True,
                   help="Owner-private seven 550_e files extracted by extract_godzilla_owner_rig")
    p.add_argument("--output", type=Path, required=True,
                   help="NEW owner-private 702_f preview directory; must not exist")
    args = p.parse_args(argv)
    # CLI restricts output to the Git-ignored private directory. The pure
    # conversion and unit fixtures do not require a physical user workspace.
    private = (Path(__file__).resolve().parents[2] / "private").resolve()
    target = args.output.resolve()
    if not target.is_relative_to(private):
        p.error("refusing Godzilla art preview outside repository private/")
    try:
        proof = prepare_from_private_source(args.source, args.output)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        p.error(str(error))
    print(proof["status"], len(proof["candidate_ally_art"]), "private assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
