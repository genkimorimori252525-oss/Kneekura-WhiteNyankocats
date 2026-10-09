"""Build and inject the exact-version static MyActivity HTTP bridge.

The bridge is compiled as an additional classes5.dex and the base manifest
launcher is changed, with an equal-length binary-AXML string replacement, from
original jp.co.ponos.battlecats.MyActivity to the selected Kneekura flavor
MyActivity subclass.

No original Battle Cats DEX method body is rewritten. The subclass overrides
only newHttpRequest and calls super for feature-OFF or unrecognized requests.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

from tools.base_mod.binary_axml import (
    patch_equal_length_strings, remove_exact_uses_permission, string_values,
)
from tools.base_mod.audit_offline_egress import manifest_components
from tools.base_mod.package_flavor import (
    FLAVOR_PACKAGES,
    ORIGINAL_PACKAGE,
    _clone_info,
    _is_signature_entry,
)
from tools.base_mod.repack import JP_15_7_1_SPLITS, payload_fingerprint, sha256_file


ORIGINAL_LAUNCHER = ORIGINAL_PACKAGE + ".MyActivity"
BRIDGE_TEMPLATE = Path("bridge/java/MyActivity.java.in")
STUB_SOURCE = Path("bridge/java/stub/jp/co/ponos/battlecats/MyActivity.java")
BRIDGE_DEX_ENTRY = "classes5.dex"


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _find_executable(name: str, explicit: str | None = None) -> str:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(path)
        return str(path)

    found = shutil.which(name)
    if found:
        return found

    if os.name == "nt":
        found = shutil.which(name + ".bat") or shutil.which(name + ".exe")
        if found:
            return found

    raise FileNotFoundError(f"{name!r} not found in PATH")


def _find_d8(explicit: str | None = None) -> str:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(path)
        return str(path)

    for candidate in ("d8", "d8.bat"):
        found = shutil.which(candidate)
        if found:
            return found

    roots = [
        os.environ.get("ANDROID_HOME"),
        os.environ.get("ANDROID_SDK_ROOT"),
    ]
    candidates: list[Path] = []
    for root in roots:
        if not root:
            continue
        build_tools = Path(root) / "build-tools"
        if not build_tools.is_dir():
            continue
        for version in build_tools.iterdir():
            for leaf in ("d8", "d8.bat"):
                path = version / leaf
                if path.is_file():
                    candidates.append(path)
    if not candidates:
        raise FileNotFoundError("d8 not found in PATH or Android SDK build-tools")

    def version_key(path: Path) -> tuple[int, ...]:
        parts = []
        for token in path.parent.name.split("."):
            try:
                parts.append(int(token))
            except ValueError:
                parts.append(0)
        return tuple(parts)

    return str(max(candidates, key=version_key))


def _find_android_jar(explicit: str | None = None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(path)
        return path.resolve()

    roots = [
        os.environ.get("ANDROID_HOME"),
        os.environ.get("ANDROID_SDK_ROOT"),
    ]
    candidates: list[Path] = []
    for root in roots:
        if not root:
            continue
        platforms = Path(root) / "platforms"
        if not platforms.is_dir():
            continue
        for platform in platforms.iterdir():
            jar = platform / "android.jar"
            if jar.is_file():
                candidates.append(jar)
    if not candidates:
        raise FileNotFoundError("android.jar not found in Android SDK platforms")

    def api_key(path: Path) -> int:
        name = path.parent.name
        if name.startswith("android-"):
            try:
                return int(name.split("-", 1)[1])
            except ValueError:
                return -1
        return -1

    return max(candidates, key=api_key).resolve()


def render_bridge_source(
    template: str,
    *,
    flavor: str,
    enabled: bool,
    use_external_files_dir: bool = False,
    isolate_original_native_files_dir: bool = False,
) -> str:
    """Render the ORIGINAL MyActivity subclass, rejecting unsafe file modes.

    This function performs no Java compilation, APK modification, networking
    or player-save I/O. A separate research flavor is mandatory for this
    original-engine file-root experiment. All shipping callers default OFF.
    """
    package_name = FLAVOR_PACKAGES.get(flavor)
    if package_name is None:
        raise ValueError(f"unknown flavor: {flavor!r}")
    if isolate_original_native_files_dir and flavor != "research":
        raise ValueError("original-game native file isolation requires research flavor")
    if isolate_original_native_files_dir and use_external_files_dir:
        raise ValueError("original-game native file isolation conflicts with external files")
    launcher = package_name + ".MyActivity"
    if len(launcher.encode("utf-8")) != len(ORIGINAL_LAUNCHER.encode("utf-8")):
        raise ValueError("bridge launcher must preserve original encoded length")
    rendered = (
        template.replace("__KNEEKURA_PACKAGE__", package_name)
        .replace(
            "__KNEEKURA_ENABLE_BACKUP_REPLAY__",
            "true" if enabled else "false",
        )
        .replace(
            "__KNEEKURA_DEBUG_LOG__",
            "true" if flavor == "research" else "false",
        )
        .replace(
            "__KNEEKURA_USE_EXTERNAL_FILES_DIR__",
            "true" if use_external_files_dir else "false",
        )
        .replace(
            "__KNEEKURA_ISOLATE_ORIGINAL_NATIVE_FILES_DIR__",
            "true" if isolate_original_native_files_dir else "false",
        )
    )
    if "__KNEEKURA_" in rendered:
        raise ValueError("bridge template contains unresolved placeholders")
    return rendered


def build_bridge_dex(
    *,
    flavor: str,
    enabled: bool,
    output: Path,
    javac: str | None = None,
    d8: str | None = None,
    android_jar: str | None = None,
    root: Path = Path("."),
    use_external_files_dir: bool = False,
    isolate_original_native_files_dir: bool = False,
) -> dict:
    package_name = FLAVOR_PACKAGES.get(flavor)
    if package_name is None:
        raise ValueError(f"unknown flavor: {flavor!r}")
    launcher = package_name + ".MyActivity"
    root = root.resolve()
    template = (root / BRIDGE_TEMPLATE).read_text(encoding="utf-8")
    rendered = render_bridge_source(
        template,
        flavor=flavor,
        enabled=enabled,
        use_external_files_dir=use_external_files_dir,
        isolate_original_native_files_dir=isolate_original_native_files_dir,
    )

    javac_bin = _find_executable("javac", javac)
    d8_bin = _find_d8(d8)
    android_jar_path = _find_android_jar(android_jar)

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="kneekura-java-bridge-") as temp_name:
        temp = Path(temp_name)
        stub_classes = temp / "stub-classes"
        bridge_classes = temp / "bridge-classes"
        dex_out = temp / "dex"
        source_root = temp / "src"
        source_path = source_root / Path(*package_name.split(".")) / "MyActivity.java"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(rendered, encoding="utf-8")

        stub_source = root / STUB_SOURCE
        stub_classes.mkdir()
        bridge_classes.mkdir()
        dex_out.mkdir()

        _run([
            javac_bin,
            "-source", "8",
            "-target", "8",
            "-classpath", str(android_jar_path),
            "-d", str(stub_classes),
            str(stub_source),
        ])

        classpath = os.pathsep.join([str(android_jar_path), str(stub_classes)])
        _run([
            javac_bin,
            "-source", "8",
            "-target", "8",
            "-classpath", classpath,
            "-d", str(bridge_classes),
            str(source_path),
        ])

        class_files = sorted(str(path) for path in bridge_classes.rglob("*.class"))
        if not class_files:
            raise RuntimeError("javac produced no bridge classes")

        stub_jar = temp / "battlecats-compile-stub.jar"
        with zipfile.ZipFile(stub_jar, "w", zipfile.ZIP_DEFLATED) as archive:
            for class_file in sorted(stub_classes.rglob("*.class")):
                archive.write(
                    class_file,
                    class_file.relative_to(stub_classes).as_posix(),
                )

        _run([
            d8_bin,
            "--min-api", "24",
            "--lib", str(android_jar_path),
            "--lib", str(stub_jar),
            "--output", str(dex_out),
            *class_files,
        ])

        produced = dex_out / "classes.dex"
        if not produced.is_file() or produced.stat().st_size == 0:
            raise RuntimeError("d8 did not produce classes.dex")
        shutil.copy2(produced, output)

    return {
        "flavor": flavor,
        "package": package_name,
        "launcher": launcher,
        "enabled": enabled,
        "dex_sha256": sha256_file(output),
        "dex_size": output.stat().st_size,
        "use_external_files_dir": use_external_files_dir,
        "isolated_original_native_files_dir": isolate_original_native_files_dir,
        "isolated_original_native_files_leaf": (
            "kneekura-native-jp15-7-1" if isolate_original_native_files_dir else None
        ),
        "original_native_gameplay_persistence_verified": False,
        "network_egress_guarantee": "NOT_VERIFIED",
    }


def _rewrite_base(
    source: Path,
    target: Path,
    *,
    launcher: str,
    bridge_dex: bytes,
    research_deny_internet: bool = False,
) -> dict:
    with zipfile.ZipFile(source, "r") as src:
        if BRIDGE_DEX_ENTRY in src.namelist():
            raise ValueError(f"{source.name} already contains {BRIDGE_DEX_ENTRY}")
        manifest = src.read("AndroidManifest.xml")
        patched_manifest, counts = patch_equal_length_strings(
            manifest,
            {ORIGINAL_LAUNCHER: launcher},
        )
        if counts.get(ORIGINAL_LAUNCHER) != 1:
            raise ValueError(
                f"expected one original launcher string, got "
                f"{counts.get(ORIGINAL_LAUNCHER)}"
            )
        offline_permission_receipt = None
        if research_deny_internet:
            original_perms = manifest_components(manifest)["declared_permissions"]
            if "android.permission.INTERNET" not in original_perms:
                raise ValueError("original pinned APK lost expected INTERNET declaration")
            patched_manifest, offline_permission_receipt = remove_exact_uses_permission(
                patched_manifest, "android.permission.INTERNET"
            )
            remaining = manifest_components(patched_manifest)["declared_permissions"]
            if "android.permission.INTERNET" in remaining:
                raise ValueError("original research manifest still grants INTERNET")
            if sorted(x for x in original_perms if x != "android.permission.INTERNET") != sorted(remaining):
                raise ValueError("research original APK removed an unrelated permission")

        values = string_values(patched_manifest)
        if launcher not in values:
            raise ValueError("bridge launcher missing from patched manifest")
        if ORIGINAL_LAUNCHER in values:
            raise ValueError("original launcher string remains in patched manifest")

        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", allowZip64=True) as dst:
            manifest_info = None
            for info in src.infolist():
                if info.is_dir() or _is_signature_entry(info.filename):
                    continue
                out_info = _clone_info(info)
                if info.filename == "AndroidManifest.xml":
                    manifest_info = out_info
                    dst.writestr(out_info, patched_manifest)
                    continue
                with src.open(info, "r") as reader, dst.open(
                    out_info, "w", force_zip64=True
                ) as writer:
                    shutil.copyfileobj(reader, writer, 1024 * 1024)

            if manifest_info is None:
                raise RuntimeError("base manifest disappeared during bridge rewrite")

            bridge_info = zipfile.ZipInfo(
                BRIDGE_DEX_ENTRY,
                manifest_info.date_time,
            )
            bridge_info.compress_type = zipfile.ZIP_DEFLATED
            bridge_info.external_attr = manifest_info.external_attr
            bridge_info.create_system = manifest_info.create_system
            dst.writestr(bridge_info, bridge_dex)

    return {
        "changed_entries": ["AndroidManifest.xml"],
        "added_entries": [BRIDGE_DEX_ENTRY],
        "research_no_internet_manifest": research_deny_internet,
        "exact_permission_removal": offline_permission_receipt,
        "zero_egress_device_verified": False,
    }


def inject_bridge_split_set(
    split_dir: Path,
    output_dir: Path,
    *,
    flavor: str,
    bridge_dex_path: Path,
    research_deny_internet: bool = False,
) -> dict:
    package_name = FLAVOR_PACKAGES.get(flavor)
    if package_name is None:
        raise ValueError(f"unknown flavor: {flavor!r}")
    if research_deny_internet and flavor != "research":
        raise ValueError("original INTERNET quarantine is research flavor only")
    launcher = package_name + ".MyActivity"

    missing = [
        name for name in JP_15_7_1_SPLITS if not (split_dir / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "incomplete JP 15.7.1 split set; missing: " + ", ".join(missing)
        )

    bridge_dex = bridge_dex_path.read_bytes()
    if not bridge_dex.startswith(b"dex\n"):
        raise ValueError("bridge dex has invalid magic")

    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for split_name in JP_15_7_1_SPLITS:
        source = split_dir / split_name
        target = output_dir / split_name
        before = payload_fingerprint(source)
        if split_name == "base.apk":
            mutation = _rewrite_base(
                source,
                target,
                launcher=launcher,
                bridge_dex=bridge_dex,
                research_deny_internet=research_deny_internet,
            )
        else:
            shutil.copy2(source, target)
            mutation = {"changed_entries": [], "added_entries": []}
        after = payload_fingerprint(target)
        rows.append({
            "name": split_name,
            "input_sha256": sha256_file(source),
            "output_sha256_unsigned": sha256_file(target),
            "payload_sha256_before": before,
            "payload_sha256_after_unsigned": after,
            **mutation,
        })

    ledger = {
        "schema_version": 1,
        "anchor": "jp-15.7.1",
        "mode": "static-java-http-bridge",
        "flavor": flavor,
        "package": package_name,
        "original_launcher": ORIGINAL_LAUNCHER,
        "launcher": launcher,
        "bridge_dex_entry": BRIDGE_DEX_ENTRY,
        "bridge_dex_sha256": sha256_file(bridge_dex_path),
        "research_no_internet_manifest": research_deny_internet,
        "network_egress_certified": False,
        "original_game_first_boot_offline_verified": False,
        "splits": rows,
    }
    (output_dir / "http-bridge-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--flavor", required=True, choices=sorted(FLAVOR_PACKAGES))
    parser.add_argument("--bridge-dex", type=Path)
    parser.add_argument("--enable-backup-offline-replay", action="store_true")
    parser.add_argument("--javac")
    parser.add_argument("--d8")
    parser.add_argument("--android-jar")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--use-external-files-dir", action="store_true")
    parser.add_argument(
        "--research-no-internet-permission",
        action="store_true",
        help="Research original host only; removes manifest INTERNET, NOT a zero-egress certificate",
    )
    parser.add_argument(
        "--research-isolate-original-native-files-dir",
        action="store_true",
        help="Research ONLY; original native getFilesDir path isolation, NOT a gameplay save",
    )
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    bridge_dex = args.bridge_dex
    build_ledger = None
    if bridge_dex is None:
        bridge_dex = output / "kneekura-http-bridge.dex"
        build_ledger = build_bridge_dex(
            flavor=args.flavor,
            enabled=args.enable_backup_offline_replay,
            output=bridge_dex,
            javac=args.javac,
            d8=args.d8,
            android_jar=args.android_jar,
            root=args.root,
            use_external_files_dir=args.use_external_files_dir,
            isolate_original_native_files_dir=args.research_isolate_original_native_files_dir,
        )

    ledger = inject_bridge_split_set(
        args.split_dir.resolve(),
        output,
        flavor=args.flavor,
        bridge_dex_path=bridge_dex.resolve(),
        research_deny_internet=args.research_no_internet_permission,
    )
    if build_ledger is not None:
        ledger["bridge_build"] = build_ledger
    print(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
