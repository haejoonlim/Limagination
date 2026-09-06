"""Parent-death watchdog for long-running coding-CLI subprocesses.

Problem (observed 2026-09-05): runners._run spawns the coding CLI with
start_new_session=True so an internal timeout can killpg the whole tree. The
side effect: when the *orch* process itself dies — dashboard crash, CI
timeout, `kill -9`, or a harness killing the run — no signal handler runs in
the dead parent, and the CLI (e.g. a review agent) keeps running as an
orphan, burning quota indefinitely.

Fix: interpose this tiny stdlib-only process between orch and the real
command. It shares the session/process group with the coding CLI it spawns,
so an internal timeout (orch killpg) still takes both down. It then polls
its parent pid: the instant orch dies — even under SIGKILL — the watchdog
kills its own process group and exits. Signals (SIGTERM/SIGINT) sent to the
watchdog are forwarded to the group, matching normal terminal behavior.

Usage: python _watch.py <parent_pid> -- <cmd...>
Env:   ORCH_WATCH_PIDFILE=/path  (test hook: writes the child pid there)
"""

import os
import signal
import subprocess
import sys
import time


def _parent_alive(expected_ppid: int) -> bool:
    """True while the direct parent is still the process we were spawned by.

    NOT os.kill(pid, 0): a SIGKILLed-but-unreaped parent lingers as a zombie,
    and os.kill(zombie, 0) still succeeds, so the watchdog would never fire.
    When the real parent dies the kernel reparents us (launchd/init), so
    getppid() changing is the authoritative death signal.
    """
    try:
        return os.getppid() == expected_ppid
    except OSError:
        return False


def _kill_own_group(signum: int) -> None:
    try:
        os.killpg(os.getpgid(0), signum)
    except (ProcessLookupError, PermissionError):
        pass


def main() -> int:
    argv = sys.argv[1:]
    try:
        sep = argv.index("--")
    except ValueError:
        return 2
    parent_pid = int(argv[0])
    cmd = argv[sep + 1:]
    if not cmd:
        return 2

    def _on_signal(signum, _frame):  # noqa: ARG001
        _kill_own_group(signum)
        sys.exit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _on_signal)
        except (ValueError, OSError):
            pass  # not the main thread / unsupported

    try:
        proc = subprocess.Popen(cmd)  # inherits orch's PIPE fds + this group
    except FileNotFoundError:
        return 127

    pidfile = os.environ.get("ORCH_WATCH_PIDFILE")
    if pidfile:
        try:
            with open(pidfile, "w", encoding="utf-8") as f:
                f.write(str(proc.pid))
        except OSError:
            pass

    poll_s = float(os.environ.get("ORCH_WATCH_POLL_S", "0.25"))
    while proc.poll() is None:
        if not _parent_alive(parent_pid):
            # orch is gone (killed / crashed / killed by harness). Take the
            # whole group down with us.
            _kill_own_group(signal.SIGKILL)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            return 1
        time.sleep(poll_s)
    return proc.returncode if proc.returncode is not None else 0


if __name__ == "__main__":
    raise SystemExit(main())
