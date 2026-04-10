#!/usr/bin/env python3
"""
Always-on launcher for OMX Switchboard.

Use this wrapper when you want task-aware routing without typing `$omx-switchboard`
inside every prompt.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()


def dispatch_script() -> Path:
    return codex_home() / "skills" / "omx-switchboard" / "scripts" / "dispatch_omx.py"


def python_cmd() -> str:
    if os.environ.get("PYTHON"):
        return os.environ["PYTHON"]
    for candidate in ("python3", "python"):
        if shutil.which(candidate):
            return candidate
    return "python3"


def run_dispatch(args: list[str]) -> int:
    script = dispatch_script()
    if not script.exists():
        print(f"omx-switchboard is not installed at {script}", file=sys.stderr)
        print("Run the project install script first.", file=sys.stderr)
        return 1
    completed = subprocess.run([python_cmd(), str(script), *args], check=False)
    return completed.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use OMX Switchboard as the default prompt entrypoint."
    )
    subparsers = parser.add_subparsers(dest="command")

    exec_parser = subparsers.add_parser("exec", help="Auto-route and execute a task.")
    exec_parser.add_argument("task", nargs="+", help="Task text.")

    route_parser = subparsers.add_parser("route", help="Auto-route and explain a task without executing.")
    route_parser.add_argument("task", nargs="+", help="Task text.")

    print_parser = subparsers.add_parser("print", help="Auto-route and print the exact command.")
    print_parser.add_argument("task", nargs="+", help="Task text.")

    parser.add_argument("default_task", nargs="*", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.command == "route":
        return run_dispatch(["--route", "auto", "--task", " ".join(args.task), "--format", "explain"])
    if args.command == "print":
        return run_dispatch(["--route", "auto", "--task", " ".join(args.task), "--format", "shell"])
    if args.command == "exec":
        return run_dispatch(["--route", "auto", "--task", " ".join(args.task), "--execute"])
    if args.default_task:
        return run_dispatch(["--route", "auto", "--task", " ".join(args.default_task), "--execute"])

    print("Usage:", file=sys.stderr)
    print("  omxr exec <task>", file=sys.stderr)
    print("  omxr route <task>", file=sys.stderr)
    print("  omxr print <task>", file=sys.stderr)
    print("  omxr <task>", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
