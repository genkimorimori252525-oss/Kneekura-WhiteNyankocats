"""Exact immutable JP15.7.1 APK source manifest for local offline bootstrap.

358 external original extracted members + 35 ORIGINAL InstallPack download TSV
bytes = 393 deterministic files. Compiled metadata contains only file names,
lengths and MD5, never proprietary asset bodies. The signed research APK uses
it only when the new opt-in offline-import flag is explicitly enabled.
"""
from __future__ import annotations
from hashlib import md5
from pathlib import Path
from zipfile import ZipFile
from tools.base_mod.recover_offline_original_server_cache import owner_manifest


def original_offline_asset_manifest(source_installpack: Path) -> list[tuple[str,int,str]]:
    files = owner_manifest(source_installpack)
    expected = [(name,size,checksum) for name,(size,checksum) in sorted(files.items())]
    with ZipFile(source_installpack) as z:
        for i in range(35):
            name = f"download_{i}.tsv"
            raw = z.read("assets/"+name)
            if len(raw)>65536 or not raw:
                raise ValueError("original offline download TSV size invalid")
            expected.append((name,len(raw),md5(raw).hexdigest()))
    if len(expected)!=393 or len(set(x[0] for x in expected))!=393:
        raise ValueError("original 358+35 owner source manifest changed")
    return expected


def compiled_java_metadata(source_installpack: Path) -> str:
    rows = original_offline_asset_manifest(source_installpack)
    for name,length,checksum in rows:
        if not (name.isascii() and name.replace("_","").replace(".","").replace("-","").isalnum()
                and 0<=length<=100_000_000 and len(checksum)==32):
            raise ValueError("unsafe original local offline metadata")
    # Java source will contain one escaped literal, not live game data.
    return '"'+''.join(
        name+"\\t"+str(length)+"\\t"+checksum+"\\n"
        for name,length,checksum in rows
    )+'"'
