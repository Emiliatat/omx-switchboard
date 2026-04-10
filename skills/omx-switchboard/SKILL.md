---
name: omx-switchboard
description: Decide whether a Codex task should stay native or be handed to the right oh-my-codex workflow such as deep-interview, ralplan, ralph, team, code-review, or security-review. Use for general engineering work whenever workflow choice is non-obvious, not only when the user explicitly asks for routing, so Codex can prefer the lowest-overhead path that still protects correctness.
metadata:
  short-description: Automatic OMX route selection
---

# OMX Switchboard

Use this skill when the user wants Codex to choose the right workflow instead of manually picking between native Codex and oh-my-codex modes.

## What this skill does

This skill is a policy layer, not a runtime by itself.

It should:

1. Read the task and choose the lowest-overhead route that is still safe.
2. Prefer native Codex for small, concrete work.
3. Escalate to an OMX workflow only when the task meaningfully benefits from it.
4. Honor explicit user overrides.
5. Degrade safely when OMX preconditions are missing.

For deterministic shell launch strings, use `scripts/dispatch_omx.py` after choosing the route.

## Decision procedure

Evaluate the task in this order:

1. Check for an explicit route override.
2. Check for critique-first intents such as review or security review.
3. Check whether the task is too ambiguous to execute safely.
4. Check whether the task is large or risky enough to require planning.
5. Check whether the task is execution-ready and parallelizable enough for `team`.
6. Check whether the task is execution-ready but mostly sequential, which favors `ralph`.
7. Otherwise stay on native Codex.

Do not skip earlier gates just because later execution modes are available.

## Use when

- The user asks for "auto OMX", "automatic routing", "choose the right mode", or a default Codex working style
- The task could reasonably go either to native Codex or to an OMX workflow
- The user wants one stable policy for when to use `deep-interview`, `ralplan`, `ralph`, `team`, `code-review`, or `security-review`

## Do not use when

- The user explicitly chose a mode and there is no safety reason to override it
- OMX is unavailable and the user only wants immediate native Codex work
- The task is trivial and route selection would add more overhead than value

## Core routing principles

1. Explicit user direction wins.
2. Ambiguity should be resolved before heavy execution.
3. Planning should happen before destructive or high-cost implementation.
4. Parallel orchestration is for genuinely parallel work, not for ordinary tasks.
5. Review workflows are for critique-first requests.
6. Security-sensitive work should route to security review before implementation unless the user clearly wants direct execution.
7. If a stronger route is blocked, downgrade one step at a time and explain the downgrade.

## Concrete scoring model

Use these three axes to make the route decision less subjective.

### A. Ambiguity score

Add 1 point for each true statement:

- The user did not clearly state the desired end state.
- Acceptance criteria are missing.
- Non-goals or boundaries are missing.
- The request uses broad verbs such as "improve", "optimize", "refactor", or "make better" without a target.
- The request implies product or UX intent that is not yet translated into engineering scope.

Interpretation:

- `0-1`: low ambiguity
- `2-3`: medium ambiguity
- `4-5`: high ambiguity

### B. Execution scope score

Add 1 point for each true statement:

- More than one subsystem or directory is likely involved.
- The work has at least three meaningful implementation steps.
- Tests or verification will need dedicated effort.
- There is migration, rollout, or compatibility risk.
- The task is expected to take longer than one tight coding burst.

Interpretation:

- `0-1`: small
- `2-3`: medium
- `4-5`: large

### C. Parallelism score

Add 1 point for each true statement:

- You can name at least two independent lanes of work.
- One lane can implement while another validates or writes tests.
- Docs, migration, or verification can proceed without blocking core implementation.
- Durable coordination across panes or worktrees would reduce risk or waiting.

Interpretation:

- `0-1`: not worth `team`
- `2`: maybe
- `3-4`: strong `team` candidate

## Route thresholds

Apply these thresholds after handling explicit `review` and `security` cases.

- If ambiguity score is `>= 3`, route to `deep`.
- Else if scope score is `>= 3` and the task is not fully execution-ready, route to `plan`.
- Else if scope score is `>= 3`, parallelism score is `>= 3`, and tmux preconditions are met, route to `team`.
- Else if scope score is `>= 2` and the task is execution-ready, route to `ralph`.
- Else route to `native`.

Execution-ready means most of these are true:

- target files, modules, or behavior are identifiable
- desired result is concrete
- success can be checked
- the request is not mainly asking for discovery

If execution-readiness is unclear, prefer `plan` over `ralph` and prefer `ralph` over `team`.

## Accepted manual overrides

Recognize these inline overrides anywhere in the user request:

- `route:auto`
- `route:native`
- `route:deep`
- `route:plan`
- `route:ralph`
- `route:team`
- `route:review`
- `route:security`

Also recognize plain-language equivalents such as:

- "use native codex"
- "interview me first"
- "plan first"
- "use ralph"
- "parallelize this"
- "review only"
- "security review first"

If the user gives both a route override and task instructions, obey the override unless it is clearly unsafe.

## Hard triggers

Use these as immediate routing hints before general scoring.

### Hard trigger for `review`

Route to `review` if the user primarily wants:

- findings
- regressions
- risk enumeration
- missing tests
- code audit
- PR review

Do not auto-implement first.

### Hard trigger for `security`

Route to `security` if the task centers on:

- authentication or authorization boundaries
- credentials, tokens, or secret storage
- sandbox escape or shell execution boundaries
- SSRF, injection, deserialization, file traversal, or trust-boundary exposure
- PII or compliance-sensitive handling

### Hard trigger for `deep`

Route to `deep` if the request is both:

- solution-shaped but not objective-shaped
- likely to produce rework if implemented immediately

Examples:

- "make the onboarding smoother"
- "optimize the bridge architecture"
- "I have an idea, ask me the right questions first"

### Hard trigger for `plan`

Route to `plan` when the user clearly wants an approach before execution:

- safest plan
- architecture options
- migration strategy
- rollout plan
- tradeoff analysis

### Hard trigger for `team`

Route to `team` only if all are true:

- the task is already scoped
- at least two meaningful lanes can run independently
- persistence outside one reasoning burst is useful
- tmux runtime is available

If any of those are false, do not auto-pick `team`.

## Route selection order

Apply these checks top to bottom. Stop at the first strong match.

### 1. `review`

Choose `review` when the user wants findings first rather than implementation.

Signals:

- "review", "audit", "look for bugs", "find issues", "PR review"
- The user wants risks, regressions, or missing tests enumerated first

Invoke:

```text
$code-review "<task>"
```

### 2. `security`

Choose `security` when the task centers on auth, secrets, permissions, PII, crypto, sandbox escape, unsafe file access, SSRF, injection, or attack surface review.

Signals:

- "security review"
- secret handling
- authn/authz changes
- permission boundaries
- public exposure or trust-boundary changes

Invoke:

```text
$security-review "<task>"
```

### 3. `deep`

Choose `deep` when intent is ambiguous and implementation would likely drift without clarification.

Signals:

- vague goals
- missing acceptance criteria
- unclear non-goals
- user says not to assume
- broad product or UX ideas with unclear boundaries

Depth guide:

- `--quick` for a light clarification pass before planning
- `--standard` by default
- `--deep` for high-risk, high-cost, or politically sensitive work

Depth choice:

- Use `--quick` when the task is almost ready but still fuzzy at the edges.
- Use `--standard` for most product and engineering discovery.
- Use `--deep` for security-sensitive, migration-heavy, or politically expensive work.

Invoke:

```text
$deep-interview --standard "<task>"
```

### 4. `plan`

Choose `plan` when the request is concrete enough to discuss, but still large enough that design, sequencing, or tradeoffs should be settled before coding.

Signals:

- "design this"
- "give me the safest plan"
- medium or large multi-step change
- migrations
- cross-module work
- destructive change with reversible alternatives

Invoke:

```text
$ralplan "<task>"
```

Use `--interactive` only when the user explicitly wants check-ins before approval.

### 5. `team`

Choose `team` only for durable, genuinely parallel workstreams where tmux-backed orchestration is worth the cost.

Signals:

- multiple independent workstreams
- long-running implementation plus verification
- repo-wide or subsystem-wide changes
- explicit request for parallel workers
- need for durable state outside one reasoning burst

Preconditions:

- `omx` available
- `tmux` available
- running inside tmux
- the task is already scoped well enough to split

Default launch shape:

```text
omx team 3:executor "<task>"
```

Do not auto-pick `team` for a small or ambiguous task. If scope is still fuzzy, route to `deep` or `plan` first.

When choosing `team`, be able to state the lanes explicitly, for example:

- lane 1: implementation
- lane 2: tests and verification
- lane 3: docs, rollout, or migration

If you cannot name the lanes, use `ralph` instead.

### 6. `ralph`

Choose `ralph` for scoped, execution-ready, mostly sequential work that benefits from persistence, but does not need durable parallel workers.

Signals:

- clear implementation request
- multi-step but mostly one-owner
- session resilience matters
- user wants "execute the plan" after planning is done

Invoke:

```text
omx ralph "<task>"
```

### 7. `native`

Choose native Codex by default when no stronger route is justified.

Signals:

- simple Q and A
- one-off explanation
- small, concrete edit
- straightforward debugging with a clear target
- lightweight file inspection
- any task where OMX overhead would exceed the likely benefit

Invoke:

```text
codex exec "<task>"
```

## Downgrade rules

If the preferred route cannot run, downgrade in this order:

- `team -> ralph -> plan -> native`
- `ralph -> plan -> native`
- `plan -> native`
- `deep -> native` only if clarification can happen inline without orchestration
- `review -> native review mindset`
- `security -> native security-focused review`

Always say which downgrade happened and why.

## Tie-breakers

- Between `native` and `plan`: choose `native` for analysis or explanation, `plan` for design decisions that will shape later implementation.
- Between `plan` and `ralph`: choose `plan` unless the implementation target is already concrete.
- Between `ralph` and `team`: choose `ralph` unless you can defend at least two independent lanes.
- Between `deep` and `plan`: choose `deep` when user intent is unclear, `plan` when intent is clear but implementation choices are open.

## Required output behavior

Before handing off, emit a short route note in one or two lines:

```text
Route: plan
Why: multi-step change with real tradeoffs; worth settling the approach before execution.
```

Keep the note short. Do not dump the whole matrix unless the user asks.

## Execution contract

After choosing a route:

- For `deep`, `plan`, `review`, or `security`, invoke the corresponding skill form.
- For `ralph` or `team`, invoke the real `omx` runtime path.
- For shell automation, bridge code, or remote wrappers, use `scripts/dispatch_omx.py` to render the concrete command.

## Examples

### Example: stay native

User:

```text
Explain what this regex does
```

Route:

```text
native
```

### Example: clarify first

User:

```text
I want to improve the onboarding flow but do not assume too much
```

Route:

```text
deep
```

### Example: plan before code

User:

```text
Design the safest migration from Redis sessions to stateless auth
```

Route:

```text
plan
```

### Example: sequential execution

User:

```text
Implement the approved plan and verify the tests
```

Route:

```text
ralph
```

### Example: parallel execution

User:

```text
Split the feature work, test coverage, and docs updates in parallel and keep durable state
```

Route:

```text
team
```

## Future extension

If the user later wants this policy to apply globally without explicitly calling the skill, promote this skill into a plugin or hook. Keep this skill as the single source of truth for the routing policy even after that promotion.
