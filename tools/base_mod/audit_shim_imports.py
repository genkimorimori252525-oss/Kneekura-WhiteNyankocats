"""Fail closed if the Kneekura shim gains network/dynamic-hook imports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FORBIDDEN_IMPORT_PREFIXES = (
    "socket",
    "connect",
    "getaddrinfo",
    "freeaddrinfo",
    "send",
    "sendto",
    "recv",
    "recvfrom",
    "SSL_",
    "BIO_",
    "curl_",
    "dlopen",
    "dlsym",
    "android_dlopen_ext",
)

FORBIDDEN_EXACT_EXPORTS = {
    "JNI_OnLoad",
}

FORBIDDEN_NEEDED_SUBSTRINGS = (
    "ssl",
    "crypto",
    "curl",
    "cronet",
)


def _import_lief():
    try:
        import lief  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "LIEF is required; install requirements-patching.txt"
        ) from exc
    return lief


def audit_shim(path: Path) -> dict:
    lief = _import_lief()
    binary = lief.parse(str(path))
    if binary is None:
        raise ValueError(f"LIEF could not parse {path}")

    imports = sorted(
        {
            getattr(function, "name", "")
            for function in binary.imported_functions
            if getattr(function, "name", "")
        }
    )
    exports = sorted(
        {
            getattr(function, "name", "")
            for function in binary.exported_functions
            if getattr(function, "name", "")
        }
    )
    needed = sorted(str(name) for name in binary.libraries)

    forbidden_imports = [
        name
        for name in imports
        if any(name.startswith(prefix) for prefix in FORBIDDEN_IMPORT_PREFIXES)
    ]
    forbidden_exports = sorted(FORBIDDEN_EXACT_EXPORTS.intersection(exports))
    forbidden_libraries = [
        name
        for name in needed
        if any(token in name.lower() for token in FORBIDDEN_NEEDED_SUBSTRINGS)
    ]

    if forbidden_imports or forbidden_exports or forbidden_libraries:
        raise ValueError(
            "shim preservation audit failed: "
            f"imports={forbidden_imports} "
            f"exports={forbidden_exports} "
            f"needed={forbidden_libraries}"
        )

    return {
        "schema_version": 1,
        "path": str(path),
        "network_or_dynamic_hook_imports_absent": True,
        "jni_onload_absent": True,
        "forbidden_network_libraries_absent": True,
        "needed_libraries": needed,
        "import_count": len(imports),
        "export_count": len(exports),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shim", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = audit_shim(args.shim.resolve())
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
