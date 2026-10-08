"""Generate a local Kneekura APK signing key without committing it."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess


def generate_keystore(
    output: Path,
    *,
    alias: str,
    storepass: str,
    keypass: str | None = None,
    dname: str = "CN=Kneekura Local, OU=Personal Mod, O=Kneekura, C=JP",
) -> None:
    keytool = shutil.which("keytool")
    if not keytool:
        raise FileNotFoundError("keytool not found in PATH")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)

    command = [
        keytool,
        "-genkeypair",
        "-keystore",
        str(output),
        "-storetype",
        "PKCS12",
        "-alias",
        alias,
        "-keyalg",
        "RSA",
        "-keysize",
        "3072",
        "-validity",
        "10000",
        "-dname",
        dname,
        "-storepass",
        storepass,
        "-keypass",
        keypass or storepass,
    ]
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--alias", default="kneekura")
    parser.add_argument("--storepass", required=True)
    parser.add_argument("--keypass")
    parser.add_argument("--dname", default="CN=Kneekura Local, OU=Personal Mod, O=Kneekura, C=JP")
    args = parser.parse_args()
    generate_keystore(
        args.output,
        alias=args.alias,
        storepass=args.storepass,
        keypass=args.keypass,
        dname=args.dname,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())