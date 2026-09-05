# orch — autonomous coding orchestrator

One terminal command (or one GitHub issue) in, a merged-ready PR out:
**branch → AI coding → tests → retries (≤3) → PR**, fully autonomous, no
human approval gates. Built with langgraph 1.2.11 on Python 3.11.

Spec sources: design v2 (`2026-09-04-orch-design.txt`) as overridden by the
v2.1 handoff (`2026-09-04-orch-handoff.txt`, §3 wins on conflict).

## Install

```bash
cd Limagination/orch
uv sync
# use .venv/bin/orch (no global install needed)
```

## Usage

```bash
# one-shot task (dry-run first — analyze only, changes nothing)
.venv/bin/orch run "<task description>" --repo <PATH> --dry-run

# full autonomous run
.venv/bin/orch run "<task description>" --repo <PATH>

# watch GitHub issues labeled `orch` (FIFO, sequential; adds `orch-retry` support)
.venv/bin/orch watch --repo <PATH> [--interval 60]

# resume a checkpointed task (thread_id == task_id); add --reset-attempts to retry a failed one
.venv/bin/orch resume cli-20260905-004827 --repo <PATH> [--reset-attempts]

# force-remove a stuck repo lock (stale-lock recovery is automatic; this is the human override)
.venv/bin/orch unlock --force --repo <PATH>

# dashboard backend (localhost web UI): register repos once, then browse
.venv/bin/orch serve --port 8471 --repos soul-commander=/path/to/soul-commander
# open http://127.0.0.1:8471 — task list, run/resume buttons, watch toggle
# (phase badges, detail view with live timeline, dark toggle, task presets)
# agents tab: per-agent model/effort + per-role (analyze/implement) mapping.
# stored in ~/.orch-agents.json; empty model/effort = CLI default.
# login-start service (macOS): auto-start on login, auto-restart on crash
.venv/bin/orch serve --install [--port 8471]
.venv/bin/orch serve --uninstall
```

## Pipeline

```
fetch_task → analyze → create_branch → implement → test ─pass→ create_pr → done
                                          │  ↑crash<3  │fail<3
                                          └─(crash≥3)  fix ──→ test (always re-test)
                                          (no diff) → fail_task(no_changes)
all failures → fail_task → END(failed)
```

- **Coding CLI**: `opencode run` (headless: dedicated minimal `OPENCODE_CONFIG`
  without MCP servers; `--dir` pins the repo). Fallbacks configured in
  `runners.py`: `claude -p` (not logged in headless here), `codex exec`
  (quota-limited). Selection order is data — override with `ORCH_CODING_CLI=<name>`.
- **Tests**: auto-detected (pytest / npm test). Detection failure is a hard
  `no_test_command` failure — never guessed.
- **Locking**: `.orch/lock` (JSON with pid) per repo; stale locks from dead
  processes are reclaimed automatically; SIGINT/SIGTERM/atexit release it.
- **Retry caps**: implement crash ×3 total, fix ×3 total — never changed
  without user approval (cost control).
- **Ref guard** (`runners.git`): push to `main`/`master`, force-push, and
  `reset --hard` are refused before git executes.
- **Secret scan**: added lines scanned for key patterns / secret-looking file
  additions before each commit; hits → `secret_detected`, commit blocked.
- **Idempotency**: implement/fix commits embed `orch:<task_id>:attempt=<n>`;
  re-entry with the marker in HEAD skips re-running that stage (safe resume).
- **Checkpoints**: per-repo `.orch/checkpoints-<slug>.db` (legacy global
  `checkpoints.db` is read-only fallback for old tasks);
  `orch resume <task_id>` continues where it stopped.

## Failure reasons

`implement_crash` · `test_failed_exhausted` · `timeout` · `no_test_command` ·
`analyze_error` · `lock_unavailable` · `secret_detected` · `no_changes`

CLI origin prints the reason to stdout; GitHub origin comments it on the issue
(branched work is always preserved, never deleted).

## Known risks (accepted for v1)

- Tests run locally with no sandbox — only use on repos you trust
  (10-min timeout with process-tree kill is the only containment).
- Secret scan is a regex minimum, not a scanner.
- One task per repo at a time (lock); no parallel worktrees in v1.

## Development

```bash
uv run pytest          # 64 tests: helpers + graph topology (runners stubbed) + server
```
