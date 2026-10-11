"""One-file offline LiveOps update bundles: signed, atomic, rollbackable.

A trusted owner-operated PC builds a signed .kneekura.zip. The future Android
game imports it with ACTION_OPEN_DOCUMENT from Downloads/USB; the game NEVER
contacts GitHub/PONOS or needs INTERNET permission.

THIS IS A PYTHON REFERENCE/OPERATOR LAYER, NOT YET CONNECTED TO ANDROID.
It updates ONLY the independent local operations catalog, NEVER SAVE_DATA,
original APKs, paid currency, gameplay stats or player achievement history.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS

from tools.localcore.ops_calendar import CHANNEL, LiveOpsError, validate_pack

BUNDLE_KIND = "kneekura.localops.bundle.v1"
SIGN_ALGO = "ECDSA-P256-SHA256-DER"
ENTRIES = ("manifest.json", "ops.json", "signature.der")
ZIP_LIMIT = 2 * 1024 * 1024
JSON_LIMIT = 1024 * 1024
CURRENT = "current.json"
PREVIOUS = "previous.json"
REVFILE = re.compile(r"^rev-[0-9]+-[0-9a-f]{64}\.json$")
SHA = re.compile(r"^[0-9a-f]{64}$")


class BundleError(ValueError):
    pass


def _serialized(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_key(location: Path, *, private: bool) -> ECC.EccKey:
    key = ECC.import_key(location.read_text(encoding="ascii"))
    if key.curve != "NIST P-256" or (private and not key.has_private()):
        raise BundleError("expected owner-controlled P-256 key")
    return key


def _public_fingerprint(key: ECC.EccKey) -> str:
    return _fingerprint(key.public_key().export_key(format="DER"))


def keygen(directory: Path) -> dict:
    """Generate the operator key ONCE, locally; private key never in any pack."""
    private = directory / "jolly-ops-private.pem"
    public = directory / "jolly-ops-public.pem"
    directory.mkdir(parents=True, exist_ok=True)
    if private.exists() or public.exists():
        raise BundleError("refusing to overwrite signing keys")
    key = ECC.generate(curve="P-256")
    private_bytes = key.export_key(format="PEM").encode("ascii")
    public_bytes = key.public_key().export_key(format="PEM").encode("ascii")
    fd = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(private_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        with public.open("xb") as stream:
            stream.write(public_bytes)
    except BaseException:
        private.unlink(missing_ok=True)
        public.unlink(missing_ok=True)
        raise
    return {"private_key": str(private), "public_key": str(public),
            "public_key_sha256": _public_fingerprint(key)}


def _prev_pointer(revision: int | None, digest: str | None) -> dict | None:
    if revision is None and digest is None:
        return None
    if (type(revision) is not int or revision < 1 or
        not isinstance(digest, str) or not SHA.fullmatch(digest)):
        raise BundleError("previous revision and previous SHA256 required together")
    return {"revision": revision, "content_sha256": digest}


def build_bundle(pack: dict, private_key: Path, target: Path, *,
                 previous_revision: int | None = None,
                 previous_sha256: str | None = None) -> dict:
    validate_pack(pack)
    if pack["status"] != "published":
        raise BundleError("only reviewed published operator packs may be imported")
    if target.exists():
        raise BundleError("refusing to overwrite an existing bundle")
    previous = _prev_pointer(previous_revision, previous_sha256)
    if previous is not None and previous["revision"] >= pack["revision"]:
        raise BundleError("the previous revision must be older")
    payload = _serialized(pack)
    if len(payload) > JSON_LIMIT:
        raise BundleError("operator pack is too large")
    key = _load_key(private_key, private=True)
    manifest = {
        "bundle_kind": BUNDLE_KIND,
        "schema_version": 1,
        "channel": CHANNEL,
        "revision": pack["revision"],
        "content_sha256": _fingerprint(payload),
        "content_bytes": len(payload),
        "previous": previous,
        "algorithm": SIGN_ALGO,
        "operator_key_sha256": _public_fingerprint(key),
        "contains_player_state": False,
        "requires_network": False,
    }
    manifest_bytes = _serialized(manifest)
    signature = DSS.new(key, "deterministic-rfc6979", encoding="der").sign(
        SHA256.new(manifest_bytes)
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_STORED) as archive:
        for name, content in (
            ("manifest.json", manifest_bytes),
            ("ops.json", payload),
            ("signature.der", signature),
        ):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100600 << 16
            archive.writestr(info, content)
    return {**manifest, "bundle_sha256": _fingerprint(target.read_bytes()),
            "publish_status": "SIGNED_OPERATOR_CONTENT_NOT_ANDROID_VERIFIED"}


def _limited_file(archive: zipfile.ZipFile, name: str, limit: int) -> bytes:
    info = archive.getinfo(name)
    if info.flag_bits & 1 or info.file_size > limit or info.file_size < 1:
        raise BundleError("unsupported encrypted, empty, or oversized entry")
    if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
        raise BundleError("unsupported bundle compression method")
    if (info.external_attr >> 16) & 0o170000 == 0o120000:
        raise BundleError("symbolic links are not accepted")
    with archive.open(info, "r") as entry:
        payload = entry.read(limit + 1)
    if len(payload) != info.file_size or len(payload) > limit:
        raise BundleError("bundle entry size mismatch")
    return payload


def verify_bundle(bundle: Path, trusted_public_key: Path) -> tuple[dict, dict]:
    """Verify against EXTERNAL pinned public key, never a key supplied in ZIP."""
    if bundle.stat().st_size > ZIP_LIMIT:
        raise BundleError("oversized update bundle")
    with zipfile.ZipFile(bundle) as archive:
        files = [x.filename for x in archive.infolist()]
        if len(files) != len(ENTRIES) or set(files) != set(ENTRIES):
            raise BundleError("bundle must contain exactly three whitelisted files")
        manifest_bytes = _limited_file(archive, "manifest.json", 8192)
        ops_bytes = _limited_file(archive, "ops.json", JSON_LIMIT)
        signature = _limited_file(archive, "signature.der", 256)
    if len(manifest_bytes) > 8192:
        raise BundleError("oversized manifest")
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if not isinstance(manifest, dict) or set(manifest) != {
        "bundle_kind", "schema_version", "channel", "revision",
        "content_sha256", "content_bytes", "previous", "algorithm",
        "operator_key_sha256", "contains_player_state", "requires_network",
    }:
        raise BundleError("invalid or ambiguous manifest fields")
    if manifest_bytes != _serialized(manifest):
        raise BundleError("noncanonical manifest not accepted")
    if (manifest["bundle_kind"] != BUNDLE_KIND or
        type(manifest["schema_version"]) is not int or
        manifest["schema_version"] != 1 or
        manifest["channel"] != CHANNEL or
        manifest["algorithm"] != SIGN_ALGO or
        manifest["contains_player_state"] is not False or
        manifest["requires_network"] is not False or
        type(manifest["revision"]) is not int or manifest["revision"] < 1 or
        type(manifest["content_bytes"]) is not int or
        manifest["content_bytes"] != len(ops_bytes) or
        manifest["content_sha256"] != _fingerprint(ops_bytes)):
        raise BundleError("bundle fields, identity or payload digest invalid")
    previous = manifest["previous"]
    if previous is not None and (
        not isinstance(previous, dict) or
        set(previous) != {"revision", "content_sha256"} or
        type(previous["revision"]) is not int or previous["revision"] < 1 or
        previous["revision"] >= manifest["revision"] or
        not isinstance(previous["content_sha256"], str) or
        not SHA.fullmatch(previous["content_sha256"])
    ):
        raise BundleError("invalid predecessor chain")
    key = _load_key(trusted_public_key, private=False)
    if manifest["operator_key_sha256"] != _public_fingerprint(key):
        raise BundleError("bundle was not signed by the pinned local operator key")
    try:
        DSS.new(key.public_key(), "fips-186-3", encoding="der").verify(
            SHA256.new(manifest_bytes), signature
        )
    except ValueError as exc:
        raise BundleError("invalid digital signature") from exc
    pack = json.loads(ops_bytes.decode("utf-8"))
    validate_pack(pack)
    if pack["status"] != "published" or pack["revision"] != manifest["revision"]:
        raise BundleError("draft or mismatched content cannot be imported")
    if ops_bytes != _serialized(pack):
        raise BundleError("noncanonical pack JSON")
    return manifest, pack


def _safe_pointer(root: Path, name: str) -> dict | None:
    path = root / name
    if not path.exists():
        return None
    pointer = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(pointer, dict) or set(pointer) != {
        "revision", "content_sha256", "file", "operator_key_sha256"
    } or not isinstance(pointer["file"], str) or not REVFILE.fullmatch(pointer["file"]):
        raise BundleError("invalid local active revision pointer")
    raw = (root / "revisions" / pointer["file"]).read_bytes()
    if _fingerprint(raw) != pointer["content_sha256"]:
        raise BundleError("current/backup content digest mismatch")
    pack = json.loads(raw.decode("utf-8"))
    validate_pack(pack)
    if pack["status"] != "published" or pack["revision"] != pointer["revision"]:
        raise BundleError("stored local content revision mismatch")
    return pointer


def _atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".kneekura-content-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def import_bundle(bundle: Path, trusted_public_key: Path, store: Path) -> dict:
    """Only the LOCAL CONTENT store changes. NEVER user progress/save or APK."""
    manifest, pack = verify_bundle(bundle, trusted_public_key)
    # No mutation until the entire bundle, signature and predecessor match.
    current = _safe_pointer(store, CURRENT) if store.exists() else None
    digest = manifest["content_sha256"]
    if current is not None:
        if current["operator_key_sha256"] != manifest["operator_key_sha256"]:
            raise BundleError("operator identity mismatch; key rotation not approved")
        if current["revision"] == manifest["revision"] and current["content_sha256"] == digest:
            return {"status": "ALREADY_INSTALLED_NO_WRITE", "revision": manifest["revision"]}
        if manifest["revision"] <= current["revision"] or manifest["previous"] != {
            "revision": current["revision"], "content_sha256": current["content_sha256"]
        }:
            raise BundleError("stale or non-chain update refused")
    elif manifest["previous"] is not None:
        raise BundleError("a predecessor must be installed before this delta")
    name = f"rev-{manifest['revision']}-{digest}.json"
    content = _serialized(pack)
    location = store / "revisions" / name
    if location.exists() and _fingerprint(location.read_bytes()) != digest:
        raise BundleError("existing local revision cache is corrupt")
    if not location.exists():
        _atomic(location, content)
    pointer = {
        "revision": manifest["revision"],
        "content_sha256": digest, "file": name,
        "operator_key_sha256": manifest["operator_key_sha256"],
    }
    # Keep a valid rollback pointer separately. Crash before CURRENT move
    # leaves the old installed revision selected.
    if current is not None:
        _atomic(store / PREVIOUS, _serialized(current))
    _atomic(store / CURRENT, _serialized(pointer))
    return {"status": "CONTENT_IMPORTED_ONLY_NOT_ANDROID_ENGINE",
            "revision": manifest["revision"], "content_sha256": digest,
            "player_save_changed": False, "network_requests": 0}


def rollback_content(store: Path) -> dict:
    current = _safe_pointer(store, CURRENT)
    prior = _safe_pointer(store, PREVIOUS)
    if current is None or prior is None:
        raise BundleError("no verified previous local content revision")
    if prior["operator_key_sha256"] != current["operator_key_sha256"]:
        raise BundleError("rollback operator key mismatch")
    _atomic(store / CURRENT, _serialized(prior))
    (store / PREVIOUS).unlink(missing_ok=True)
    return {"status": "LOCAL_CONTENT_ROLLED_BACK",
            "revision": prior["revision"], "player_save_changed": False}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("keygen", help="one-time owner-only local signing key")
    gen.add_argument("--directory", type=Path, required=True)
    build = sub.add_parser("build", help="operator PC signs one published JSON")
    build.add_argument("--pack", type=Path, required=True)
    build.add_argument("--private-key", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--previous-revision", type=int)
    build.add_argument("--previous-sha256")
    verify = sub.add_parser("verify", help="verify user-provided update, no writes")
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--public-key", type=Path, required=True)
    apply = sub.add_parser("import", help="import into a local reference store")
    apply.add_argument("--bundle", type=Path, required=True)
    apply.add_argument("--public-key", type=Path, required=True)
    apply.add_argument("--store", type=Path, required=True)
    roll = sub.add_parser("rollback", help="rollback only local content")
    roll.add_argument("--store", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.command == "keygen":
            result = keygen(args.directory)
        elif args.command == "build":
            pack = json.loads(args.pack.read_text(encoding="utf-8"))
            result = build_bundle(
                pack, args.private_key, args.output,
                previous_revision=args.previous_revision,
                previous_sha256=args.previous_sha256,
            )
        elif args.command == "verify":
            manifest, pack = verify_bundle(args.bundle, args.public_key)
            result = {"status": "SIGNED_CONTENT_VALIDATED_NO_INSTALL",
                      "revision": manifest["revision"],
                      "content_sha256": manifest["content_sha256"],
                      "catalog_kind_count": len(pack["catalog"])}
        elif args.command == "import":
            result = import_bundle(args.bundle, args.public_key, args.store)
        else:
            result = rollback_content(args.store)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile,
            json.JSONDecodeError) as exc:
        p.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
