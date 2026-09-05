"""Repo-level execution lock (v2 §7.1 + handoff 수정3).

Lock file: <repo>/.orch/lock  (git-ignored)
Format:    {"pid": int, "task_id": str, "started_at": iso8601}

Acquire rules (수정3):
- no lock file          -> acquire
- lock exists, PID alive -> fail (LockUnavailable)
- lock exists, PID dead  -> reclaim it (log explicitly), then acquire

Release is attempted on normal exit, exceptions, and SIGINT/SIGTERM via
finally/atexit/signal handlers wired in cli.py.
"""

import atexit
import json
import os
import signal
import time
from datetime import datetime, timezone


class LockUnavailable(Exception):
    """Raised by acquire() when another live process holds the lock."""


def lock_path(repo_path: str) -> str:
    return os.path.join(repo_path, ".orch", "lock")


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    return True


def _read_lock(repo_path: str) -> dict | None:
    try:
        with open(lock_path(repo_path), encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("pid"), int):
            return data
    except (OSError, ValueError):
        pass
    return None  # missing/corrupt = no lock


def status(repo_path: str) -> dict | None:
    """Read-only lock status for monitors (dashboard /api/repos).

    Returns live-holder info, or None when free, stale (dead pid), or
    missing. Never creates, modifies, or reclaims the lock file.
    """
    data = _read_lock(repo_path)
    if data is None:
        return None
    if not _pid_alive(data["pid"]):
        return None
    return {
        "pid": data["pid"],
        "task_id": data.get("task_id"),
        "started_at": data.get("started_at"),
    }


def _write_lock(repo_path: str, task_id: str) -> None:
    os.makedirs(os.path.dirname(lock_path(repo_path)), exist_ok=True)
    tmp = lock_path(repo_path) + f".tmp.{os.getpid()}"
    payload = {
        "pid": os.getpid(),
        "task_id": task_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    os.replace(tmp, lock_path(repo_path))


def acquire(repo_path: str, task_id: str, *, log=None) -> None:
    """Acquire the lock or raise LockUnavailable (handoff §5: -> bool semantics
    via exception; cli converts to lock_unavailable failure)."""
    lp = lock_path(repo_path)
    existing = _read_lock(repo_path)
    if existing is not None:
        if _pid_alive(existing["pid"]):
            raise LockUnavailable(
                f"repo is locked by pid={existing['pid']} task={existing.get('task_id')!r} "
                f"since {existing.get('started_at')} (lock: {lp})"
            )
        # stale lock: reclaim, explicitly logged (수정3)
        if log:
            log(
                f"reclaiming stale lock held by dead pid={existing['pid']} "
                f"task={existing.get('task_id')!r}"
            )
        os.remove(lp)
    _write_lock(repo_path, task_id)
    if log:
        log(f"lock acquired (pid={os.getpid()}, task={task_id!r})")


def release(repo_path: str, *, log=None) -> None:
    """Release the lock only if we still own it (never delete someone else's)."""
    existing = _read_lock(repo_path)
    if existing is None:
        return
    if existing.get("pid") != os.getpid():
        if log:
            log(
                f"lock now held by pid={existing.get('pid')}, not removing it"
            )
        return
    try:
        os.remove(lock_path(repo_path))
        if log:
            log("lock released")
    except OSError:
        pass


def unlock_force(repo_path: str, *, log=None) -> bool:
    """Human override: remove the lock file unconditionally (`orch unlock --force`)."""
    try:
        os.remove(lock_path(repo_path))
    except FileNotFoundError:
        if log:
            log("no lock file present")
        return False
    if log:
        log("lock file removed (--force)")
    return True


class LockManager:
    """Ties acquire/release to process lifetime: finally + atexit + SIGINT/SIGTERM."""

    def __init__(self, repo_path: str, task_id: str, *, log=None):
        self.repo_path = repo_path
        self.task_id = task_id
        self.log = log
        self.acquired = False
        self._prev_handlers: dict = {}

    def __enter__(self) -> "LockManager":
        acquire(self.repo_path, self.task_id, log=self.log)
        self.acquired = True
        atexit.register(self._release_quiet)
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                self._prev_handlers[sig] = signal.signal(sig, self._on_signal)
            except (ValueError, OSError):
                pass  # not main thread / unsupported
        return self

    def _on_signal(self, signum, frame):  # noqa: ARG002 (frame unused)
        if self.log:
            self.log(f"signal {signal.Signals(signum).name} received; releasing lock")
        self._release_quiet()
        # re-raise default behavior so exit code reflects the signal
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    def _release_quiet(self) -> None:
        if self.acquired:
            self.acquired = False
            release(self.repo_path, log=self.log)
            atexit.unregister(self._release_quiet)

    def __exit__(self, exc_type, exc, tb) -> None:
        for sig, handler in self._prev_handlers.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass
        self._release_quiet()


def wait_for_lock(repo_path: str, timeout_s: float, poll_interval: float = 0.5, *, log=None) -> bool:
    """Best-effort wait used by `watch` when the repo is momentarily busy."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _read_lock(repo_path) is None:
            return True
        time.sleep(poll_interval)
    return _read_lock(repo_path) is None
