---
name: opencode-free-limit-monitor
description: Watch OpenCode API limit, exit 42 means pause. LOCAL per-host monitor — no network, no cross-host dependency.
---

# OpenCode Free-Limit Monitor (uso LOCAL por host)

The opencode CLI can hit its daily free-usage API limit mid-run. Without monitoring, the run keeps going / stalls and the agent never notices — a phase silently never finishes. This skill makes the limit detectable and turns it into a clean "pause and wait for retomar" signal.

## Scope: LOCAL only

This monitor is **per-host and local**. It runs on the same machine where `opencode` executes. It does **not** use ZeroMQ, the network, or any remote Hermes. Each Hermes host runs its own copy and watches its own opencode independently. In a multi-host agent mesh (e.g. orchestrator + Acer + others), deploy this skill+script on *every* host — there is no central coordinator.

## The rule (mandatory)

**ALWAYS launch opencode through the wrapper** `bash ~/.hermes/scripts/opencode_run.sh run '<prompt>' --agent build --title '...'` — never call `~/.opencode/bin/opencode run` directly for long phases.

## What the wrapper does

1. Captures opencode stdout+stderr to a temp log.
2. A parallel `tail -F | grep -m1` watcher strips ANSI and matches a limit pattern:
   `usage exceeded|free usage|rate[ -]limit|[^0-9]429|too many requests|quota|limit reached|daily limit|upgrade to continue|retry in|try again later|exceeded your|usage limit`
3. On match it `kill -TERM` the opencode process and writes a flag, then the wrapper exits with **code 42**.
4. On normal completion it exits with opencode's real code.

## How the agent must react to exit 42

- Treat 42 as **LIMIT REACHED**, never as success.
- **STOP all opencode work. Do NOT auto-relaunch the next phase.**
- Record the pause point in `PLANO_CONCLUSAO.md` (which phase was in progress, what was already written — the run's partial output is usually safe/idempotent and can be resumed next run).
- Report to the user: "OpenCode atingiu o limite diário — pausei. Retomar amanhã ou quando você disser."
- Resume only on explicit "retomar" (or next day). The wrapper is idempotent: relaunching the same phase replays from existing files.

## How the agent must react to exit 0

- Still VERIFY by running the agent's claimed evidence (route:list count, tinker gate/queries, curl on the dev server). Do not trust the self-report.
- Then mark the phase done in the plan and proceed to the next.

## Setup / install

- Wrapper path: `~/.hermes/scripts/opencode_run.sh` (executable).
- Skill path: `~/.hermes/skills/software-development/opencode-free-limit-monitor/SKILL.md`.
- Idempotent installer: `bash install.sh` copies both into place using `$HOME` (works for any user/home).
- Override binary with `OPENCODE_BIN=/path/to/opencode bash opencode_run.sh ...` if needed.
- The dev server + queue worker should already be up (`php artisan serve --host=0.0.0.0 --port=8000` and `php artisan queue:work`) before launching a phase that needs them.

## Pitfalls

- A false positive only causes an early pause (user retries) — acceptable. A miss causes a silent stall — unacceptable; keep the pattern broad.
- `wait $OC` then `kill $WATCH` — if opencode finishes first, the watcher is reaped. If watcher fires first, it kills opencode. Either order is handled.
- Don't background the wrapper without `notify_on_complete=true`; otherwise the 42 won't reach you promptly.
