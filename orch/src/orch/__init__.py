"""orch — fully autonomous langgraph coding orchestrator.

Pipeline: fetch_task -> analyze -> create_branch -> implement -> test -> create_pr
with fix loop (fix -> test) and fail_task sink. No human approval gates.

Spec source of truth:
- Handoff v2.1 (2026-09-04) — 10 fixes overriding design v2 where they conflict.
- Design v2 edge table (5장) for graph topology.

Key interfaces (handoff §5, frozen):
- runners.run_coding_cli(prompt, *, timeout_s=1200, forbid_edits=False) -> dict
- runners.run_tests(repo_path) -> {"passed": bool|None, ...}  (None => no_test_command)
- runners.git(*args, repo_path) -> dict  (ref guard enforced here)
- runners.check_secrets(diff_text) -> list[str]
- lock.acquire(repo_path, task_id) -> bool / lock.release(repo_path)

Graph nodes only branch on the dicts returned by runners; nodes never call
subprocess directly.
"""

__version__ = "0.1.0"

MAX_ATTEMPTS = 3  # implement crash retries: 1 initial + 2 retries (수정8)
MAX_FIX_ATTEMPTS = 3  # test-failure fixes (수정8)
IDEMPOTENCY_PREFIX = "orch"
