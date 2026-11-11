"""LiveOps Operator CLI: compile verified owner source into immutable ops bundle.

No character grants, stage clear forging, official communication or SAVE writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from tools.liveops.original_catalogue import owned_catalogue, bind_catalogue
from tools.liveops.original_calendar import compile_calendar
from tools.liveops.original_ops_bundle import build_login_rotation, validate_bundle
from tools.localcore.ops_calendar import ORIGINAL_OWNER_SAVE, JST, validate_pack


def compile_operator_bundle(
    export_zip: Path,
    server_cache: Path,
    pack_path: Path,
    out_bundle: Path,
    *,
    start_date: str,
    days: int,
    login_cycles: int = 32,
    login_seed: str = 'kneekura-ops-batch1',
) -> dict:
    receipt_path=out_bundle.with_suffix('.receipt.json')
    if any(path.exists() or path.is_symlink() for path in (out_bundle,receipt_path)):
        raise ValueError('ORIGINAL_OPS_OUTPUT_ALREADY_EXISTS')
    pack_bytes=pack_path.read_bytes()
    pack=json.loads(pack_bytes)
    validate_pack(pack)
    if pack.get('status')!='published' or pack['policy']['owner_save']!=ORIGINAL_OWNER_SAVE:
        raise ValueError('ORIGINAL_OPS_REQUIRE_APPROVED_ORIGINAL_PACK')
    print(f"[1/5] Verifying owner source export and server cache...")
    catalogue = owned_catalogue(export_zip, server_cache)
    print(f"      Verified {len(catalogue['asset_names']):,} assets, {len(catalogue['maps']):,} maps, "
          f"{len(catalogue['gacha'])} gacha rosters, {len(catalogue['login_pool'])} login templates.")

    print(f"[2/5] Reading and verifying season pack: {pack_path.name}...")

    print(f"[3/5] Binding pack items to source catalogue...")
    bindings = bind_catalogue(pack, catalogue)
    print(f"      Bound {len(bindings)} catalogue items (gacha/stage/event/mission).")

    print(f"[4/5] Building login rotation from source pool ({len(catalogue['login_pool'])} templates)...")
    login_rotation = build_login_rotation(catalogue['login_pool'], seed=login_seed, cycles=login_cycles)

    print(f"[5/5] Compiling calendar projection ({start_date} + {days} days)...")
    bundle_bytes, receipt = compile_calendar(
        pack,
        bindings,
        start_date=start_date,
        days=days,
        login_rotation=login_rotation,
    )
    validated = validate_bundle(bundle_bytes)

    digest = hashlib.sha256(bundle_bytes).hexdigest()
    out_bundle.parent.mkdir(parents=True, exist_ok=True)
    with out_bundle.open('xb') as output:output.write(bundle_bytes)

    receipt_record = {
        'schema': 'kneekura-original-ops-operator-receipt-v1',
        'source_export_sha256': catalogue['source_export_sha256'],
        'login_source_sha256': catalogue['login_source_sha256'],
        'pack_sha256': hashlib.sha256(pack_bytes).hexdigest(),
        'original_ui_accepted': False,
        'original_save_mutated': False,
        'bundle_file': str(out_bundle),
        'bundle_sha256': digest,
        'revision': validated['revision'],
        'start_epoch_ms': validated['start_epoch_ms'],
        'end_epoch_ms': validated['end_epoch_ms'],
        'streams': list(validated['server_files'].keys()),
        'notice_count': len(validated.get('notices', [])),
        'login_rotation_id': validated.get('login_rotation', {}).get('rotation_id'),
        'calendar_report': receipt,
    }
    with receipt_path.open('x',encoding='utf-8') as output:
        output.write(json.dumps(receipt_record, indent=2, ensure_ascii=False) + '\n')

    print(f"SUCCESS: Immutable ops bundle written to {out_bundle}")
    print(f"SHA-256: {digest}")
    return receipt_record


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile verified Kneekura LiveOps bundle.")
    parser.add_argument('--export-zip', type=Path, required=True, help="Verified owner JP15.7.1 export ZIP")
    parser.add_argument('--server-cache', type=Path, required=True, help="Verified original server cache directory")
    parser.add_argument('--pack', type=Path, required=True, help="Authoritative season pack JSON")
    parser.add_argument('--out-bundle', type=Path, required=True, help="Destination bundle JSON path")
    parser.add_argument('--start-date', type=str, default=datetime.now(JST).date().isoformat(), help="Start date (YYYY-MM-DD, default today JST)")
    parser.add_argument('--days', type=int, default=30, help="Window duration in days")
    parser.add_argument('--login-seed', type=str, default='kneekura-ops-batch1', help="Login rotation shuffle seed")
    parser.add_argument('--login-cycles', type=int, default=32, help="Number of 5-slot rotation cycles")
    args = parser.parse_args()

    compile_operator_bundle(
        args.export_zip,
        args.server_cache,
        args.pack,
        args.out_bundle,
        start_date=args.start_date,
        days=args.days,
        login_cycles=args.login_cycles,
        login_seed=args.login_seed,
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
