"""Read-only access to the installed Battle Cats InstallPack split."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
import hashlib
import io
import pathlib
import re
import zipfile

from tools.battlecats_pack import PackReader


_VERSION_RE = re.compile(r"バージョン:\s*`?([^\s`]+)")


@dataclass(frozen=True)
class ExportSourceInfo:
    export_name: str
    export_size: int
    export_sha256: str
    version: str | None
    install_apk_path: str
    install_apk_size: int
    install_apk_sha256: str


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class BattleCatsExport(AbstractContextManager["BattleCatsExport"]):
    """Open a device export ZIP without extracting or mutating it."""

    def __init__(
        self,
        path: pathlib.Path,
        *,
        region: str = "jp",
        expected_sha256: str | None = None,
    ) -> None:
        self.path = path.expanduser().resolve()
        self.region = region.lower()
        self.expected_sha256 = expected_sha256.lower() if expected_sha256 else None
        self._outer: zipfile.ZipFile | None = None
        self._install_zip: zipfile.ZipFile | None = None
        self._install_bytes: bytes | None = None
        self.source_info: ExportSourceInfo | None = None

    def __enter__(self) -> "BattleCatsExport":
        if not self.path.is_file():
            raise FileNotFoundError(self.path)

        export_sha = sha256_file(self.path)
        if self.expected_sha256 and export_sha != self.expected_sha256:
            raise ValueError(
                f"export SHA-256 mismatch: expected {self.expected_sha256}, got {export_sha}"
            )

        self._outer = zipfile.ZipFile(self.path)
        install_candidates = [
            name
            for name in self._outer.namelist()
            if name.lower().endswith("/split_installpack.apk")
            or name.lower() == "split_installpack.apk"
        ]
        if len(install_candidates) != 1:
            raise ValueError(
                "expected exactly one split_InstallPack.apk, found "
                f"{len(install_candidates)}"
            )

        install_path = install_candidates[0]
        self._install_bytes = self._outer.read(install_path)
        self._install_zip = zipfile.ZipFile(io.BytesIO(self._install_bytes))

        version = None
        if "README.md" in self._outer.namelist():
            readme = self._outer.read("README.md").decode("utf-8-sig", "replace")
            match = _VERSION_RE.search(readme)
            if match:
                version = match.group(1)

        self.source_info = ExportSourceInfo(
            export_name=self.path.name,
            export_size=self.path.stat().st_size,
            export_sha256=export_sha,
            version=version,
            install_apk_path=install_path,
            install_apk_size=len(self._install_bytes),
            install_apk_sha256=hashlib.sha256(self._install_bytes).hexdigest(),
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._install_zip is not None:
            self._install_zip.close()
        if self._outer is not None:
            self._outer.close()
        self._install_zip = None
        self._outer = None
        self._install_bytes = None
        return None

    def _require_open(self) -> zipfile.ZipFile:
        if self._install_zip is None:
            raise RuntimeError("BattleCatsExport must be used as a context manager")
        return self._install_zip

    def pack(self, family: str) -> PackReader:
        install = self._require_open()
        list_path = f"assets/{family}.list"
        pack_path = f"assets/{family}.pack"
        try:
            list_bytes = install.read(list_path)
            pack_bytes = install.read(pack_path)
        except KeyError as exc:
            raise KeyError(f"missing InstallPack family {family!r}") from exc
        return PackReader(
            family=family,
            manifest_bytes=list_bytes,
            pack_bytes=pack_bytes,
            region=self.region,
        )
