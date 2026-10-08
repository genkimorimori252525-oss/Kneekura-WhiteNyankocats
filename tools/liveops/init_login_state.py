"""Initialize the five-slot login scheduler from a generated pool."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.liveops.login_scheduler import Campaign, dumps, initialize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pool", type=Path)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--local-day", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        pool = json.loads(args.pool.read_text(encoding="utf-8"))
        campaigns = [
            Campaign(
                event_id=int(entry["event_id"]),
                day_count=int(entry["day_count"]),
            )
            for entry in pool["eligible"]
        ]
        state = initialize(
            campaigns,
            seed=args.seed,
            local_day=args.local_day,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"login-state initialization failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dumps(state), encoding="utf-8")
    print(
        "initialized login scheduler: "
        + ",".join(str(slot.event_id) for slot in state.active)
        + f" -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
