"""Optional, private arm64 native scene-witness dependency packaging.

Research-only: enable ONLY after the original JP15.7.1 shim is separately
built with KNEEKURA_RESEARCH_SCENE_WITNESS=ON, using the owner's own signing
keys and exactly isolated 'jp.kn.local.battlecats' no-INTERNET package.

The third-party libshadowhook.so is NEVER downloaded, distributed or
committed by this project. Its owner-supplied SHA-256 must be pinned, and
only a validated ARM64 ELF shared library is accepted. Running this
function never changes any original owner APK/SAVE/phone.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shutil
from zipfile import ZipFile, ZipInfo, ZIP_STORED

from tools.base_mod.elf_anchor import EM_AARCH64, elf_machine
from tools.base_mod.package_flavor import _clone_info, _is_signature_entry
from tools.base_mod.repack import JP_15_7_1_SPLITS

EXTRA_NATIVE_ENTRY = "lib/arm64-v8a/libshadowhook.so"
RESEARCH_PACKAGE = "jp.kn.local.battlecats"
SCENE_WITNESS_COMPILED_MARKER = b"original-native-scene-v1 id=%u"
SCENE_WITNESS_PACKAGE_MARKER = RESEARCH_PACKAGE.encode("ascii")
APPROVED_FLAVOR = "local-research"
MAX_EXTERNAL_LIBRARY_BYTES = 24 * 1024 * 1024


class OriginalSceneWitnessPackageError(ValueError):
    """Reject any source that cannot be proven research-only and local."""


def _safe_native_so(source: Path, expected_sha256: str) -> bytes:
    if not isinstance(source, Path) or source.is_symlink() or not source.is_file():
        raise OriginalSceneWitnessPackageError("research libshadowhook must be an owned regular file")
    if not re.fullmatch("[a-f0-9]{64}", expected_sha256 or ""):
        raise OriginalSceneWitnessPackageError("research libshadowhook requires full lowercase SHA256")
    if source.stat().st_size <= 0 or source.stat().st_size > MAX_EXTERNAL_LIBRARY_BYTES:
        raise OriginalSceneWitnessPackageError("research libshadowhook exceeds native size guard")
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise OriginalSceneWitnessPackageError("reviewed native hook dependency hash mismatched")
    if (len(data) < 64 or data[:4] != b"\x7fELF"
        or data[4] != 2 or data[5] != 1
        or int.from_bytes(data[16:18], "little") != 3
        or elf_machine(data) != EM_AARCH64):
        raise OriginalSceneWitnessPackageError(
            "research native hook must be ELF64 AArch64 ET_DYN"
        )
    if (b"shadowhook_init\x00" not in data
        or b"shadowhook_hook_sym_name\x00" not in data):
        raise OriginalSceneWitnessPackageError(
            "research native hook exported-function identifier anchors absent"
        )
    return data


def check_original_scene_witness_build_contract(
    *, flavor: str, no_internet: bool, shim: Path,
    shadowhook: Path | None, shadowhook_sha256: str | None,
) -> dict:
    """Reject a witness-enabled shim unless flavor/policy/dependency match.

    Must run BEFORE creating any output dirs or touching original split data.
    """
    if not isinstance(shim, Path) or shim.is_symlink() or not shim.is_file():
        raise OriginalSceneWitnessPackageError("native Kneekura shim path missing or unsafe")
    if shim.stat().st_size > MAX_EXTERNAL_LIBRARY_BYTES:
        raise OriginalSceneWitnessPackageError("native Kneekura shim size unacceptable")
    source = shim.read_bytes()
    witness_present = SCENE_WITNESS_COMPILED_MARKER in source
    paired_dependency = shadowhook is not None or shadowhook_sha256 is not None

    if witness_present and (
        flavor != APPROVED_FLAVOR or not no_internet
        or SCENE_WITNESS_PACKAGE_MARKER not in source
    ):
        raise OriginalSceneWitnessPackageError(
            "research scene witness shim MUST be isolated local-research no-INTERNET"
        )
    if witness_present != paired_dependency:
        raise OriginalSceneWitnessPackageError(
            "native scene witness requires BOTH compiled shim and exact reviewed dependency"
        )
    if paired_dependency:
        if flavor != APPROVED_FLAVOR or not no_internet:
            raise OriginalSceneWitnessPackageError(
                "reviewed native hook dependency ONLY allowed in local no-INTERNET research"
            )
        if shadowhook is None or shadowhook_sha256 is None:
            raise OriginalSceneWitnessPackageError(
                "both native hook library and exact SHA256 must be explicit"
            )
        _safe_native_so(shadowhook, shadowhook_sha256)
    return {
        "research_scene_witness_build_enabled": witness_present,
        "research_original_native_scene_hook_runtime_supplied": paired_dependency,
        "research_scene_witness_package_constraint": RESEARCH_PACKAGE,
        "research_scene_witness_default_shipping": False,
        "native_scene101_102_runtime_observed": False,
        "original_native_gameplay_or_save_verified": False,
        "original_APK_SAVE_modified": False,
    }


def include_reviewed_shadowhook_in_private_split_set(
    source_dir: Path, target_dir: Path, *, shadowhook: Path,
    expected_sha256: str,
) -> dict:
    """Clone six unsigned split APKs, adding ONLY one reviewed library.

    It is used inside the already-private research staging directory prior
    to normal package flavor, zipalign, signer and final integrity gates.
    """
    if (source_dir.is_symlink() or not source_dir.is_dir()
        or target_dir.is_symlink() or target_dir.exists()
        or source_dir.resolve() == target_dir.resolve()):
        raise OriginalSceneWitnessPackageError("unsafe or nonempty original witness staging")
    raw = _safe_native_so(shadowhook, expected_sha256)
    for name in JP_15_7_1_SPLITS:
        if not (source_dir / name).is_file() or (source_dir / name).is_symlink():
            raise OriginalSceneWitnessPackageError("missing or unsafe original JP split set")
    target_dir.mkdir(parents=True)
    changed = 0
    for name in JP_15_7_1_SPLITS:
        source = source_dir / name
        target = target_dir / name
        if name != "split_config.arm64_v8a.apk":
            shutil.copyfile(source, target)
            continue
        with ZipFile(source, "r") as src, ZipFile(target, "w", allowZip64=True) as dst:
            if EXTRA_NATIVE_ENTRY in src.namelist():
                raise OriginalSceneWitnessPackageError(
                    "preexisting libshadowhook.so forbidden in exact research source"
                )
            for info in src.infolist():
                if info.is_dir() or _is_signature_entry(info.filename):
                    continue
                out = _clone_info(info)
                with src.open(info, "r") as reader, dst.open(
                    out, "w", force_zip64=True
                ) as writer:
                    shutil.copyfileobj(reader, writer, 1024 * 1024)
            new = ZipInfo(EXTRA_NATIVE_ENTRY)
            new.compress_type = ZIP_STORED
            new.create_system = 3
            new.external_attr = 0o100644 << 16
            dst.writestr(new, raw)
            changed += 1
    if changed != 1:
        raise OriginalSceneWitnessPackageError(
            "exactly one reviewed library entry must be included"
        )
    return {
        "status": "EXACT_LOCAL_RESEARCH_ONLY_OPTIONAL_NATIVE_HOOK_SOURCE_STAGING",
        "original_split_count": len(JP_15_7_1_SPLITS),
        "only_extra_entry": EXTRA_NATIVE_ENTRY,
        "reviewed_native_dependency_sha256": expected_sha256,
        "scene_observer_runtime_or_original_gameplay_verified": False,
        "source_original_splits_or_owner_player_SAVE_unchanged": True,
    }
