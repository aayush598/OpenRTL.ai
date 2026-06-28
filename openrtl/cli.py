"""Command-line interface for OpenRTL.

Usage:
  openrtl run "8-bit counter"       # Run the full pipeline
  openrtl list                       # List saved projects
  openrtl get <name>                 # Get project details
  openrtl step <name> <step>         # Run a single pipeline step
"""

import argparse
import sys
from pathlib import Path

from openrtl.config import config
from openrtl.exceptions import ConfigError
from openrtl.logging import get_logger, setup_logging
from openrtl.pipeline import FPGAPipeline
from openrtl.services.database import DatabaseService

log = get_logger("cli")


def _bootstrap() -> None:
    setup_logging(level=config.log_level, log_file=config.log_file)
    try:
        config.validate()
    except ConfigError as e:
        log.error(str(e))
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_run(args: argparse.Namespace) -> None:
    pipeline = FPGAPipeline()
    result = pipeline.run_all(args.prompt)
    if result.errors:
        sys.exit(1)


def cmd_list(_args: argparse.Namespace) -> None:
    db = DatabaseService()
    projects = db.list_projects()
    if projects:
        print("Saved projects:")
        for p in projects:
            print(f"  - {p}")
    else:
        print("No projects found.")


def cmd_get(args: argparse.Namespace) -> None:
    db = DatabaseService()
    data = db.get_project(args.name)
    if data:
        import json
        print(json.dumps(data, indent=2))
    else:
        print(f"Project '{args.name}' not found.")
        sys.exit(1)


def cmd_step(args: argparse.Namespace) -> None:
    pipeline = FPGAPipeline()
    project_name = args.name

    steps = {
        "structure": pipeline.step_project_structure,
        "rtl": pipeline.step_rtl_code,
        "tb": pipeline.step_testbench,
        "lint": pipeline.step_lint,
        "sdc": pipeline.step_sdc,
        "synthesis": pipeline.step_synthesis,
        "metrics": pipeline.step_metrics,
    }

    if args.step not in steps:
        print(f"Unknown step '{args.step}'. Choose from: {', '.join(steps)}")
        sys.exit(1)

    fn = steps[args.step]
    result = fn(project_name)
    print(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openrtl",
        description="OpenRTL.ai — FPGA development pipeline from natural-language descriptions",
    )
    parser.add_argument(
        "--version", action="version", version="OpenRTL 3.0.0"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Run the full FPGA development pipeline")
    p_run.add_argument("prompt", help="Natural-language project description (e.g. '8-bit counter')")
    p_run.set_defaults(func=cmd_run)

    # list
    p_list = sub.add_parser("list", help="List saved projects")
    p_list.set_defaults(func=cmd_list)

    # get
    p_get = sub.add_parser("get", help="Show project details")
    p_get.add_argument("name", help="Project name")
    p_get.set_defaults(func=cmd_get)

    # step
    p_step = sub.add_parser("step", help="Run a single pipeline step")
    p_step.add_argument("name", help="Project name")
    p_step.add_argument(
        "step",
        choices=["structure", "rtl", "tb", "lint", "sdc", "synthesis", "metrics"],
        help="Pipeline step to run",
    )
    p_step.set_defaults(func=cmd_step)

    return parser


def main(argv: list[str] | None = None) -> None:
    _bootstrap()
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
