#!/usr/bin/env python3
"""
Render or execute the command for a route chosen by the OMX Switchboard skill.

This script supports two modes:
1. Explicit mode: translate a chosen route into a concrete invocation.
2. Auto mode: classify the task with OMX Switchboard heuristics, then render or execute it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Invocation:
    route: str
    task: str
    argv: list[str]
    prompt: str | None
    warnings: list[str]
    reason: str
    ambiguity_score: int
    scope_score: int
    parallelism_score: int
    execution_ready: bool
    explicit_override: str | None
    downgraded_from: str | None


def prompt_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def shell_join(argv: list[str]) -> str:
    return shlex.join(argv)


def normalize_route(route: str) -> str:
    aliases = {
        "auto": "auto",
        "native": "native",
        "deep": "deep",
        "deep-interview": "deep",
        "plan": "plan",
        "ralplan": "plan",
        "ralph": "ralph",
        "team": "team",
        "review": "review",
        "code-review": "review",
        "security": "security",
        "security-review": "security",
    }
    try:
        return aliases[route.lower()]
    except KeyError as exc:
        raise SystemExit(f"unsupported route: {route}") from exc


def build_prompt_skill(name: str, task: str, extra_flag: str | None = None) -> str:
    parts = [f"${name}"]
    if extra_flag:
        parts.append(extra_flag)
    parts.append(f'"{prompt_quote(task)}"')
    return " ".join(parts)


def detect_warnings(route: str, cwd: Path) -> list[str]:
    warnings: list[str] = []
    if route in {"ralph", "team"} and shutil.which("omx") is None:
        warnings.append("`omx` not found on PATH.")
    if route == "team":
        if shutil.which("tmux") is None:
            warnings.append("`tmux` not found on PATH.")
        if not os.environ.get("TMUX"):
            warnings.append("`TMUX` is not set; `omx team` usually expects a tmux leader session.")
    if route in {"review", "security"} and not (cwd / ".git").exists():
        warnings.append("No `.git` directory detected in cwd; review routes usually make the most sense in a repo.")
    if route in {"native", "deep", "plan", "review", "security"} and shutil.which("codex") is None:
        warnings.append("`codex` not found on PATH.")
    return warnings


def find_explicit_override(task: str) -> str | None:
    match = re.search(
        r"\broute:(auto|native|deep|plan|ralph|team|review|security)\b",
        task,
        re.IGNORECASE,
    )
    if match:
        return normalize_route(match.group(1))

    plain_language = [
        (r"\buse native codex\b", "native"),
        (r"\binterview me first\b", "deep"),
        (r"\bplan first\b", "plan"),
        (r"\buse ralph\b", "ralph"),
        (r"\bparallel(?:ize|ise) this\b", "team"),
        (r"\breview only\b", "review"),
        (r"\bsecurity review first\b", "security"),
    ]
    lowered = task.lower()
    for pattern, route in plain_language:
        if re.search(pattern, lowered):
            return route
    return None


def compute_ambiguity_score(task: str) -> int:
    lowered = task.lower()
    score = 0
    if not re.search(r"\b(so that|to achieve|in order to|expected|result|goal)\b", lowered):
        score += 1
    if not re.search(r"\b(test|verify|acceptance|done when|success|pass|regression)\b", lowered):
        score += 1
    if not re.search(r"\b(do not|don't|without|out of scope|non-goal|keep)\b", lowered):
        score += 1
    if re.search(r"\b(improve|optimize|refactor|make better|enhance|clean up)\b", lowered) and not re.search(
        r"\b(file|module|function|endpoint|query|test|login|auth|bridge|docker|readme|api)\b",
        lowered,
    ):
        score += 1
    if re.search(r"\b(onboarding|experience|ux|flow|architecture|system|product)\b", lowered) and not re.search(
        r"\b(src/|\.ts\b|\.js\b|\.py\b|function|class|module|endpoint|schema|table)\b",
        lowered,
    ):
        score += 1
    return score


def compute_scope_score(task: str) -> int:
    lowered = task.lower()
    score = 0
    if re.search(
        r"\b(cross[- ]module|cross[- ]repo|multi[- ]step|multiple modules|multiple services|repo[- ]wide|subsystem)\b",
        lowered,
    ):
        score += 1
    if len(re.findall(r"\b(add|implement|fix|update|write|verify|document|migrate|refactor)\b", lowered)) >= 3:
        score += 1
    if re.search(r"\b(test|verify|regression|e2e|integration|coverage)\b", lowered):
        score += 1
    if re.search(r"\b(migration|migrate|rollout|compatibility|backward|breaking|schema|data)\b", lowered):
        score += 1
    if re.search(r"\b(persist|durable|long[- ]running|end[- ]to[- ]end|full workflow|complete it)\b", lowered):
        score += 1
    return score


def compute_parallelism_score(task: str) -> int:
    lowered = task.lower()
    score = 0
    if re.search(r"\b(parallel|parallelize|split|fan[- ]out|multiple lanes|multi[- ]agent|workers?)\b", lowered):
        score += 1
    if re.search(r"\b(implement|code)\b", lowered) and re.search(r"\b(test|verify|validation|review)\b", lowered):
        score += 1
    if re.search(r"\b(docs?|documentation|rollout|migration|release)\b", lowered):
        score += 1
    if re.search(r"\b(tmux|worktree|durable coordination|shared state|survive)\b", lowered):
        score += 1
    return score


def detect_review_route(task: str) -> bool:
    lowered = task.lower()
    return bool(
        re.search(r"\b(review|audit|find issues|look for bugs|regressions?|pr review|code review)\b", lowered)
        and not re.search(r"\b(implement|fix it|apply the fix|go ahead and change)\b", lowered)
    )


def detect_plan_route(task: str) -> bool:
    lowered = task.lower()
    return bool(
        re.search(
            r"\b(plan|design|strategy|approach|safest plan|migration path|migration strategy|rollout plan|tradeoff|trade-off|architecture options?)\b",
            lowered,
        )
    )


def detect_security_route(task: str) -> bool:
    lowered = task.lower()
    direct_security = re.search(
        r"\b(security|secret|token|credential|pii|ssrf|injection|sandbox|traversal|deseriali[sz]ation|attack surface|threat model|vulnerability)\b",
        lowered,
    )
    auth_boundary = re.search(
        r"\b(auth|authentication|authorization|permissions?)\b",
        lowered,
    ) and re.search(
        r"\b(review|audit|harden|secure|exposure|boundary|risk|threat)\b",
        lowered,
    )
    return bool(direct_security or auth_boundary)


def is_execution_ready(task: str) -> bool:
    lowered = task.lower()
    signals = 0
    if re.search(r"(src/|app/|lib/|server/|client/|\.ts\b|\.tsx\b|\.js\b|\.py\b|\.go\b|\.rs\b|[A-Za-z0-9_./-]+:\d+)", task):
        signals += 1
    if re.search(r"\b(fix|implement|add|update|remove|rename|change|write|repair|debug)\b", lowered):
        signals += 1
    if re.search(r"\b(test|verify|expected|should|must|so that|pass)\b", lowered):
        signals += 1
    if re.search(r"\b(function|class|module|endpoint|query|schema|login|auth|bridge|docker|readme|api|timeout)\b", lowered):
        signals += 1
    return signals >= 2


def team_preconditions_met() -> bool:
    return shutil.which("omx") is not None and shutil.which("tmux") is not None and bool(os.environ.get("TMUX"))


def choose_auto_route(task: str) -> tuple[str, str, int, int, int, bool, str | None]:
    explicit_override = find_explicit_override(task)
    ambiguity = compute_ambiguity_score(task)
    scope = compute_scope_score(task)
    parallelism = compute_parallelism_score(task)
    execution_ready = is_execution_ready(task)
    if execution_ready:
        ambiguity = max(0, ambiguity - 1)

    if explicit_override and explicit_override != "auto":
        return (
            explicit_override,
            f"explicit override via `{explicit_override}`",
            ambiguity,
            scope,
            parallelism,
            execution_ready,
            explicit_override,
        )

    if detect_review_route(task):
        return ("review", "findings-first request", ambiguity, scope, parallelism, execution_ready, explicit_override)
    if detect_security_route(task):
        return ("security", "security-centered request", ambiguity, scope, parallelism, execution_ready, explicit_override)
    if detect_plan_route(task):
        return ("plan", "user is explicitly asking for a plan or strategy first", ambiguity, scope, parallelism, execution_ready, explicit_override)
    if ambiguity >= 3:
        return ("deep", f"ambiguity score {ambiguity} >= 3", ambiguity, scope, parallelism, execution_ready, explicit_override)
    if scope >= 3 and not execution_ready:
        return ("plan", f"scope score {scope} >= 3 and task is not execution-ready", ambiguity, scope, parallelism, execution_ready, explicit_override)
    if scope >= 3 and parallelism >= 3 and team_preconditions_met():
        return ("team", f"scope score {scope} and parallelism score {parallelism} justify durable parallel work", ambiguity, scope, parallelism, execution_ready, explicit_override)
    if scope >= 2 and execution_ready:
        return ("ralph", f"scope score {scope} with execution-ready task favors sequential persistent execution", ambiguity, scope, parallelism, execution_ready, explicit_override)
    return ("native", "no stronger route is justified", ambiguity, scope, parallelism, execution_ready, explicit_override)


def downgrade_route(route: str, execution_ready: bool) -> tuple[str, str | None, str | None]:
    downgraded_from: str | None = None
    reason: str | None = None

    if route == "team" and not team_preconditions_met():
        downgraded_from = "team"
        if shutil.which("omx") is not None and execution_ready:
            route = "ralph"
            reason = "downgraded from `team` because tmux preconditions are missing"
        else:
            route = "plan" if not execution_ready else "native"
            reason = "downgraded from `team` because runtime preconditions are missing"

    if route == "ralph" and shutil.which("omx") is None:
        downgraded_from = downgraded_from or "ralph"
        route = "plan" if not execution_ready else "native"
        reason = "downgraded from `ralph` because `omx` is not available"

    if route == "plan" and shutil.which("codex") is None:
        downgraded_from = downgraded_from or "plan"
        route = "native"
        reason = "downgraded from `plan` because `codex` is not available"

    return route, downgraded_from, reason


def build_invocation(args: argparse.Namespace) -> Invocation:
    task = args.task
    cwd = Path(args.cwd).resolve()
    requested_route = normalize_route(args.route)
    prompt: str | None = None

    chosen_reason = "explicit route selection"
    ambiguity_score = 0
    scope_score = 0
    parallelism_score = 0
    execution_ready = is_execution_ready(task)
    explicit_override: str | None = None

    if requested_route == "auto":
        (
            route,
            chosen_reason,
            ambiguity_score,
            scope_score,
            parallelism_score,
            execution_ready,
            explicit_override,
        ) = choose_auto_route(task)
    else:
        route = requested_route

    route, downgraded_from, downgrade_reason = downgrade_route(route, execution_ready)
    if downgrade_reason:
        chosen_reason = f"{chosen_reason}; {downgrade_reason}"

    warnings = detect_warnings(route, cwd)

    if route == "native":
        argv = ["codex", "exec", task]
    elif route == "deep":
        prompt = build_prompt_skill("deep-interview", task, f"--{args.depth}")
        argv = ["codex", "exec", prompt]
    elif route == "plan":
        flag = "--interactive" if args.interactive else None
        prompt = build_prompt_skill("ralplan", task, flag)
        argv = ["codex", "exec", prompt]
    elif route == "ralph":
        argv = ["omx", "ralph", task]
    elif route == "team":
        argv = ["omx", "team"]
        if args.team_spec:
            argv.append(args.team_spec)
        argv.append(task)
    elif route == "review":
        prompt = build_prompt_skill("code-review", task)
        argv = ["codex", "exec", prompt]
    elif route == "security":
        prompt = build_prompt_skill("security-review", task)
        argv = ["codex", "exec", prompt]
    else:
        raise AssertionError(f"unhandled route: {route}")

    return Invocation(
        route=route,
        task=task,
        argv=argv,
        prompt=prompt,
        warnings=warnings,
        reason=chosen_reason,
        ambiguity_score=ambiguity_score,
        scope_score=scope_score,
        parallelism_score=parallelism_score,
        execution_ready=execution_ready,
        explicit_override=explicit_override,
        downgraded_from=downgraded_from,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate an OMX Switchboard decision into a concrete Codex or OMX command."
    )
    parser.add_argument(
        "--route",
        required=True,
        choices=[
            "auto",
            "native",
            "deep",
            "deep-interview",
            "plan",
            "ralplan",
            "ralph",
            "team",
            "review",
            "code-review",
            "security",
            "security-review",
        ],
        help="Chosen route from the OMX Switchboard skill.",
    )
    parser.add_argument("--task", required=True, help="Task body for the selected route.")
    parser.add_argument(
        "--depth",
        default="standard",
        choices=["quick", "standard", "deep"],
        help="Interview depth when deep route is used.",
    )
    parser.add_argument(
        "--team-spec",
        default="3:executor",
        help="Team worker shape for team route. Use an empty string to omit it.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Add --interactive when rendering the plan route.",
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Working directory used for warnings and optional execution.",
    )
    parser.add_argument(
        "--format",
        default="shell",
        choices=["shell", "argv", "json", "prompt", "explain"],
        help="How to print the rendered result.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the rendered command instead of only printing it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    invocation = build_invocation(args)
    cwd = str(Path(args.cwd).resolve())

    if args.execute:
        completed = subprocess.run(invocation.argv, cwd=cwd, check=False)
        return completed.returncode

    if args.format == "shell":
        print(shell_join(invocation.argv))
    elif args.format == "argv":
        print(json.dumps(invocation.argv, ensure_ascii=False, indent=2))
    elif args.format == "json":
        payload = {
            "route": invocation.route,
            "task": invocation.task,
            "prompt": invocation.prompt,
            "argv": invocation.argv,
            "shell_command": shell_join(invocation.argv),
            "reason": invocation.reason,
            "ambiguity_score": invocation.ambiguity_score,
            "scope_score": invocation.scope_score,
            "parallelism_score": invocation.parallelism_score,
            "execution_ready": invocation.execution_ready,
            "explicit_override": invocation.explicit_override,
            "downgraded_from": invocation.downgraded_from,
            "warnings": invocation.warnings,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.format == "prompt":
        if invocation.prompt is None:
            raise SystemExit(f"route `{invocation.route}` does not produce an inline prompt form")
        print(invocation.prompt)
    elif args.format == "explain":
        print(f"Route: {invocation.route}")
        print(f"Why: {invocation.reason}")
        print(
            "Scores: "
            f"ambiguity={invocation.ambiguity_score}, "
            f"scope={invocation.scope_score}, "
            f"parallelism={invocation.parallelism_score}, "
            f"execution_ready={str(invocation.execution_ready).lower()}"
        )
        print(f"Command: {shell_join(invocation.argv)}")
    else:
        raise AssertionError(f"unhandled format: {args.format}")

    if invocation.warnings and args.format != "json":
        for warning in invocation.warnings:
            print(f"warning: {warning}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
