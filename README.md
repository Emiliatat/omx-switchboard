# omx-switchboard

> Autonomous workflow routing for Codex. Let AI decide when to stay native, when to plan, and when to escalate.

## Languages

- [English](./README.md)
- [简体中文](./docs/i18n/README.zh-CN.md)
- [日本語](./docs/i18n/README.ja.md)

`omx-switchboard` is a Codex plugin project that lets AI choose the right operating mode for the task instead of making the user micro-manage workflow selection:

- keep small, concrete tasks on native Codex
- route ambiguous tasks to `deep-interview`
- route design-heavy tasks to `ralplan`
- route execution-ready sequential work to `ralph`
- route truly parallel durable work to `team`
- route findings-first work to `code-review` or `security-review`

It ships in two layers:

1. `$omx-switchboard` skill for in-Codex routing
2. `omxr` launcher for always-on automatic routing without typing `$omx-switchboard` in every prompt

## Why this exists

Native Codex, `deep-interview`, `ralplan`, `ralph`, and `team` are all useful, but they fit different task shapes.

The problem this project tries to solve is not "OMX costs too much." The real goal is to let AI decide when it should stay lightweight, when it should plan first, and when it should escalate into a stronger workflow without the user having to specify the mode every time.

In practice that means:

- small concrete tasks stay in native Codex
- vague or underspecified tasks move to discovery-oriented modes
- design-heavy work moves to planning-oriented modes
- execution-ready work moves to implementation-oriented modes
- parallelizable work moves to `team` only when parallelism is actually justified

This project adds a stable routing policy so mode selection becomes part of the system behavior, not something the user has to keep steering manually.

## What this repo installs

This repository currently ships a practical install flow, not a marketplace-managed plugin install flow.

What gets installed:

- the `omx-switchboard` skill under `~/.codex/skills/omx-switchboard`
- the `omxr` and `omx-switchboard` launchers under `~/.local/bin`

What it does not currently do:

- register itself in a Codex marketplace
- auto-appear through a separate plugin catalog install step

So the simplest mental model is:

- this is a GitHub-installable skill and launcher package
- it also includes a valid plugin manifest for future plugin-oriented distribution

## How "default auto" works

There are two different meanings of "automatic":

### 1. Implicit skill invocation

The shipped `openai.yaml` allows implicit invocation, so Codex can pull in `$omx-switchboard` automatically when the request matches the routing problem.

### 2. Deterministic default entrypoint

For users who want guaranteed task-aware routing on every prompt, this project installs `omxr` and `omx-switchboard` launchers.

Those launchers:

- classify the task first
- print or execute the chosen route
- downgrade safely if `team` or `ralph` runtime preconditions are missing

This is the reliable "always-on" path.

## Project layout

```text
.codex-plugin/plugin.json
skills/omx-switchboard/SKILL.md
skills/omx-switchboard/agents/openai.yaml
skills/omx-switchboard/references/routing-matrix.md
skills/omx-switchboard/scripts/dispatch_omx.py
scripts/install.sh
scripts/install.ps1
scripts/uninstall.sh
scripts/omxr.py
scripts/omxr
scripts/omxr.cmd
LICENSE
```

## Routing rules

The router evaluates the task on three axes:

1. `ambiguity_score`
2. `scope_score`
3. `parallelism_score`

### Ambiguity score

Add 1 point for each:

- desired end state is unclear
- acceptance criteria are missing
- boundaries or non-goals are missing
- the task uses broad verbs like `improve`, `optimize`, or `make better` without a bounded target
- the request is still product-shaped instead of implementation-shaped

Interpretation:

- `0-1`: low ambiguity
- `2-3`: medium ambiguity
- `4-5`: high ambiguity

### Scope score

Add 1 point for each:

- multiple modules or subsystems are likely involved
- at least three meaningful implementation steps are implied
- verification or testing needs real work
- migration or compatibility risk exists
- the task will likely outlast one tight execution burst

Interpretation:

- `0-1`: small
- `2-3`: medium
- `4-5`: large

### Parallelism score

Add 1 point for each:

- at least two independent work lanes can be named
- implementation and verification can run in parallel
- docs, migration, or rollout can move independently
- durable tmux or worktree coordination would actually help

Interpretation:

- `0-1`: do not use `team`
- `2`: maybe
- `3-4`: strong `team` candidate

## Decision tree

Apply in order:

1. Explicit override such as `route:team` or `route:native`
2. Findings-first request -> `review`
3. Security-centered request -> `security`
4. `ambiguity_score >= 3` -> `deep`
5. `scope_score >= 3` and not execution-ready -> `plan`
6. `scope_score >= 3`, `parallelism_score >= 3`, and tmux-ready -> `team`
7. `scope_score >= 2` and execution-ready -> `ralph`
8. Otherwise -> `native`

Execution-ready means the target, expected outcome, and verification path are concrete enough to implement without another discovery pass.

## Downgrade policy

If a stronger route is unavailable:

- `team -> ralph -> plan -> native`
- `ralph -> plan -> native`
- `plan -> native`

The launcher includes downgrade reasons in its explanation output.

## Install

### Prerequisites

Before installation, make sure you have:

- `git`
- `python3` on Unix-like systems
- `python` or `py -3` on Windows
- Codex already installed and configured

Recommended:

- add `~/.local/bin` to your `PATH` so `omxr` and `omx-switchboard` run directly after install

If `~/.local/bin` is not on your `PATH`, you can still run the launchers with full paths:

- Unix-like: `~/.local/bin/omxr`
- Windows: `$HOME\.local\bin\omxr.cmd`

### Unix-like

```bash
git clone https://github.com/Emiliatat/omx-switchboard.git
cd omx-switchboard
bash ./scripts/install.sh
```

### Windows PowerShell

```powershell
git clone https://github.com/Emiliatat/omx-switchboard.git
cd omx-switchboard
.\scripts\install.ps1
```

By default installation does two things:

- copies the skill to `~/.codex/skills/omx-switchboard`
- installs launchers in `~/.local/bin`

Installed launchers:

- `omxr`
- `omx-switchboard`

If the launcher command is not found after install, add `~/.local/bin` to your shell `PATH` or run the launcher by full path.

## Usage

### Use the skill directly

```text
$omx-switchboard
Fix the login timeout and choose the safest workflow automatically.
```

```text
$omx-switchboard route:plan
Design the safest migration path first. Do not execute yet.
```

```text
$omx-switchboard route:team
Split implementation, verification, and docs into parallel lanes.
```

### Use the always-on launcher

Explain the chosen route:

```bash
omxr route "Design the safest auth migration"
```

Print the exact command:

```bash
omxr print "Fix the login timeout with verification"
```

Auto-route and execute:

```bash
omxr "Fix the login timeout with verification"
```

Equivalent explicit form:

```bash
omxr exec "Fix the login timeout with verification"
```

## Dispatch helper

The core helper can be used standalone:

```bash
python3 skills/omx-switchboard/scripts/dispatch_omx.py \
  --route auto \
  --task "Split implementation, tests, and docs in parallel" \
  --format json
```

It can also render explicit routes:

```bash
python3 skills/omx-switchboard/scripts/dispatch_omx.py \
  --route plan \
  --task "Design the safest auth migration" \
  --format explain
```

## Repository metadata

This repo is already structured as a publishable plugin project:

- plugin manifest at `.codex-plugin/plugin.json`
- MIT license
- install and uninstall scripts
- deterministic launcher
- installable skill directory

Users should think of the GitHub install path as:

- clone this repo
- run the install script
- use the installed skill or launcher

The current public metadata points to:

- repository: `https://github.com/Emiliatat/omx-switchboard`
- publisher: `Emiliatat`

If you fork this project, update the public metadata in:

- `.codex-plugin/plugin.json`
- `LICENSE`
- `README.md`

## Release checklist

1. Push this directory as the repo root
2. Verify the install scripts on one Unix host and one Windows host
3. Tag `v0.1.0`

## Attribution

This project is influenced by and interoperates with `oh-my-codex`.

If your published version includes copied or adapted code from upstream projects such as `oh-my-codex` or `cli-in-wechat`, keep the upstream MIT notice and attribution with your distribution. See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
