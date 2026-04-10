# OMX Routing Matrix

Use this as a quick reference when the route is not obvious.

| Route | Best for | Avoid when | Canonical form |
| --- | --- | --- | --- |
| `native` | Simple, concrete, low-overhead tasks | The task is ambiguous or clearly multi-stage | `codex exec "<task>"` |
| `deep` | Requirement clarification and boundary setting | The task is already implementation-ready | `$deep-interview --standard "<task>"` |
| `plan` | Design, sequencing, migrations, tradeoffs | The task is tiny or already fully planned | `$ralplan "<task>"` |
| `ralph` | Scoped sequential execution with persistence | Work needs real parallel lanes or is still vague | `omx ralph "<task>"` |
| `team` | Durable parallel execution with tmux and worktrees | The task is small, ambiguous, or not in tmux | `omx team 3:executor "<task>"` |
| `review` | Findings-first code review | The user clearly asked to implement first | `$code-review "<task>"` |
| `security` | Threat review, auth, secrets, trust boundaries | The task is ordinary product work with no security center | `$security-review "<task>"` |

## Practical heuristics

- If you are torn between `native` and `plan`, start with `native` for small tasks and `plan` for anything with real tradeoffs.
- If you are torn between `plan` and `ralph`, choose `plan` unless execution is already well-scoped.
- If you are torn between `ralph` and `team`, choose `ralph` unless you can name distinct parallel lanes.
- If you are torn between `deep` and `plan`, choose `deep` when the intent is unclear and `plan` when the intent is clear but the implementation path is not.

## Decision summary

| Condition | Route |
| --- | --- |
| Findings-first request | `review` |
| Security-centered request | `security` |
| Ambiguity score `>= 3` | `deep` |
| Scope score `>= 3` and not execution-ready | `plan` |
| Scope score `>= 3`, parallelism score `>= 3`, tmux ready | `team` |
| Scope score `>= 2` and execution-ready | `ralph` |
| Otherwise | `native` |

## Team litmus test

Do not auto-route to `team` unless you can fill this in concretely:

- lane 1:
- lane 2:
- lane 3:

If you cannot, prefer `ralph`.
