"""Graph state schema (design v2 §4 + handoff v2.1).

Single owner of the state shape. failure_reason has exactly the 8 values from
handoff §3: implement_crash | test_failed_exhausted | timeout | no_test_command
| analyze_error | lock_unavailable | secret_detected | no_changes
"""

from typing import TypedDict

FAILURE_REASONS = frozenset(
    {
        "implement_crash",
        "test_failed_exhausted",
        "timeout",
        "no_test_command",
        "analyze_error",
        "lock_unavailable",
        "secret_detected",
        "no_changes",
    }
)

ORIGINS = frozenset({"cli", "github"})


class TaskState(TypedDict):
    task_id: str  # "cli-<YYYYMMDD-HHMMSS>" or "gh-<issue_number>"; also the checkpointer thread_id (수정9)
    task: str  # raw task description (CLI arg text or issue body) — addition to v2 §4 needed by analyze/implement/fix prompts
    origin: str  # "cli" | "github"
    issue_no: int | None
    repo_path: str  # absolute path to the target repo (v1: single repo)
    default_branch: str | None  # cached via `gh repo view --json defaultBranchRef` (v2 §7.4)
    branch: str  # "orch/gh-<issue>-<slug>" | "orch/cli-<ts>-<slug>" (수정4)
    plan: str  # analyze output, reused by implement/fix prompts
    attempt: int  # starts at 0 (수정8)
    fix_attempt: int  # starts at 0 (수정8)
    test_result: dict  # {"passed": bool|None, "output": str, "command": str|None}
    review_passed: bool | None  # None = not reviewed yet (P3 reviewer node)
    review_notes: str  # reviewer findings (also fed to fix on rejection)
    pr_url: str | None
    status: str  # "running" | "done" | "failed"
    error: str | None
    failure_reason: str | None  # one of FAILURE_REASONS
    idempotency_marker: str | None  # "orch:<task_id>:attempt=<n>" (v2 §7.5)
