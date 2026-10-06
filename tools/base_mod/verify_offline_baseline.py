"""Read-only verifier for the JP 15.7.1 pre-MAX SAVE_DATA baseline family."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.base_mod.build_offline_max_save import validate_baseline_family


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("save_data", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        result = validate_baseline_family(args.save_data.read_bytes())
    except (OSError, ValueError, KeyError) as exc:
        print(f"clean baseline verification failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
