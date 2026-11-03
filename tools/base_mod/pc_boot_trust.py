"""Explicit PC-only trust resource; preserve the native RSA verifier."""
import hashlib
from pathlib import Path
from zipfile import ZipFile

ENTRY = 'assets/nyanko-service-prd.pem'


def validate_public_key(public: bytes) -> str:
    from Crypto.PublicKey import RSA
    try:
        key = RSA.import_key(public)
    except (ValueError, IndexError, TypeError) as error:
        raise ValueError('PC_BOOT_PUBLIC_KEY_INVALID') from error
    if key.has_private() or key.size_in_bits() != 4096 or key.e != 65537:
        raise ValueError('PC_BOOT_PUBLIC_ONLY_RSA4096_REQUIRED')
    return hashlib.sha256(key.export_key('DER')).hexdigest()


def replace_local_boot_public_key(archive: Path, public: bytes, *, dedicated_pc: bool) -> dict:
    if not dedicated_pc:
        raise ValueError('PC_BOOT_TRUST_REQUIRES_DEDICATED_PC_PROFILE')
    fingerprint = validate_public_key(public)
    temporary = archive.with_name(archive.name + '.local-trust.pending')
    if temporary.exists() or archive.is_symlink():
        raise ValueError('PC_BOOT_TRUST_UNSAFE_STAGING')
    with ZipFile(archive) as original:
        entries = original.infolist()
        if len({entry.filename for entry in entries}) != len(entries) or ENTRY not in original.namelist():
            raise ValueError('PC_BOOT_TRUST_RESOURCE_MISSING_OR_DUPLICATED')
        with ZipFile(temporary, 'w') as output:
            for entry in entries:
                output.writestr(entry, public if entry.filename == ENTRY else original.read(entry.filename))
    temporary.replace(archive)
    return dict(schema='kneekura-pc-local-boot-trust-v1', changed_entry=ENTRY,
                public_key_sha256=fingerprint, native_verifier_preserved=True,
                publisher_private_key_used=False)
