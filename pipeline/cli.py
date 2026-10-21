"""Single entry point.

    python -m pipeline run --stage all
    python -m pipeline run --stage pull_odds
    python -m pipeline auto            # what GitHub Actions runs every 30 min (gated by ET time)
    python -m pipeline backfill --seasons 2023 2024 2025 2026   # ESPN season years, local only
    python -m pipeline fit             # fit hyperparameters on the fit season (local only)
"""

from __future__ import annotations

import argparse
import importlib
import sys

# Order matters for --stage all.
STAGES = [
    "pull_schedule",
    "pull_results",
    "pull_injuries",
    "build_ratings",
    "project_games",
    "pull_odds",
    "lock",
    "grade",
]


def run_stage(name: str) -> None:
    if name not in STAGES:
        raise SystemExit(f"unknown stage {name!r}; choose from {', '.join(STAGES)} or all")
    mod = importlib.import_module(f"pipeline.stages.{name}")
    print(f"== {name}", flush=True)
    mod.run()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--stage", required=True, help="stage name, comma list, or 'all'")
    sub.add_parser("auto")
    sub.add_parser("gate")
    sub.add_parser("busy", help="exit 0 if there is pipeline work in the next few hours, else 1")
    b = sub.add_parser("backfill")
    b.add_argument("--seasons", nargs="+", type=int, required=True, help="ESPN season years, e.g. 2026 = 2025-26")
    sub.add_parser("fit")
    args = ap.parse_args(argv)

    if args.cmd == "run":
        names = STAGES if args.stage == "all" else [s.strip() for s in args.stage.split(",") if s.strip()]
        for n in names:
            run_stage(n)
    elif args.cmd == "auto":
        from .gate import auto
        auto()
    elif args.cmd == "gate":
        from .gate import due
        print(" ".join(due()) or "(nothing due)")
    elif args.cmd == "busy":
        from .gate import busy
        b = busy()
        print("busy" if b else "idle")
        sys.exit(0 if b else 1)
    elif args.cmd == "backfill":
        from .stages.backfill import run as backfill
        backfill(args.seasons)
    elif args.cmd == "fit":
        from .stages.fit import run as fit
        fit()
    sys.stdout.flush()
