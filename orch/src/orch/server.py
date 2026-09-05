"""orch serve: stdlib-only dashboard backend (dashboard spec v1, A안).

- ThreadingHTTPServer on 127.0.0.1 only (localhost, no auth — v1).
- Registry: ~/.orch-repos.json (ORCH_REPOS env override, used by tests).
- Task listing reads the per-repo checkpoints DB (cli.db_path_for_repo).
- Run/resume/watch execute in background threads via cli.execute_* and
  poller.watch_loop(stop=event). No orchestration logic lives here.

API: GET /api/repos | GET /api/tasks?repo= | GET /api/events?repo=[&since=]
     POST /api/run {repo, task} | POST /api/resume {repo, task_id, reset_attempts?}
     POST /api/watch {repo, interval?, stop?} | GET / (dashboard.html)
"""

import json
import os
import plistlib
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import cli, lock, runners
from .poller import watch_loop

DEFAULT_PORT = 8471
SERVICE_LABEL = "com.orch.serve"

TASK_FIELDS = (
    "task_id", "origin", "issue_no", "branch", "plan", "attempt",
    "fix_attempt", "test_result", "pr_url", "status", "error", "failure_reason",
)


def phase_of(t: dict) -> str:
    """Infer the stage label from checkpoint values (no node instrumentation)."""
    if t.get("status") == "done":
        return "done"
    if t.get("status") == "failed" or t.get("failure_reason"):
        return "failed"
    if not t.get("branch"):
        return "analyzing"
    tr = t.get("test_result") or {}
    if (t.get("fix_attempt") or 0) > 0 and not tr.get("passed"):
        return "fixing"
    if tr:
        if not tr.get("passed"):
            return "testing"
        return "pr" if t.get("review_passed") else "reviewing"
    return "implementing"


def registry_path() -> str:
    return os.environ.get("ORCH_REPOS") or os.path.join(os.path.expanduser("~"), ".orch-repos.json")


def load_registry() -> dict:
    try:
        with open(registry_path(), encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, str) and os.path.isdir(v)}
    except (OSError, ValueError):
        return {}


def save_registry(reg: dict) -> None:
    path = registry_path()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2, sort_keys=True)


def parse_repos_arg(spec: str) -> dict:
    """'alias=/path,alias2=/path2' (or bare paths -> basename alias)."""
    out = {}
    for chunk in (spec or "").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" in chunk:
            alias, path = chunk.split("=", 1)
        else:
            path, alias = chunk, os.path.basename(os.path.abspath(chunk).rstrip(os.sep))
        alias, path = alias.strip(), os.path.abspath(path.strip())
        if alias and os.path.isdir(os.path.join(path, ".git")):
            out[alias] = path
    return out


def list_tasks(repo_path: str) -> list:
    """Newest-first task snapshots from the per-repo checkpoints DB.

    Reads via the public SqliteSaver API (never raw SQL). Empty list when
    the repo has no DB yet. Legacy global DB is deliberately NOT consulted
    here (per-repo isolation); old tasks remain resumable via CLI fallback.
    """
    db = cli.db_path_for_repo(repo_path)
    if not os.path.exists(db):
        return []
    cp = cli._make_checkpointer(repo_path)
    if cp is None:  # pragma: no cover
        return []
    best = {}
    for t in cp.list(None):
        tid = (t.config.get("configurable") or {}).get("thread_id")
        if not tid:
            continue
        key = (t.checkpoint.get("ts") or "", t.checkpoint.get("id") or "")
        if tid not in best or key > best[tid][0]:
            best[tid] = (key, t)
    rows = []
    for tid, (_, t) in sorted(best.items(), key=lambda kv: kv[1][0], reverse=True):
        v = t.checkpoint.get("channel_values", {}) or {}
        row = {k: v.get(k) for k in TASK_FIELDS}
        row["phase"] = phase_of(row)
        row["help"] = help_for(row.get("failure_reason"))
        rows.append(row)
    return rows


def stack_of(repo_path: str) -> str:
    """Human-readable test stack label for the dashboard hint line."""
    cmd = runners.detect_test_command(repo_path) or []
    argv0 = cmd[0] if cmd else ""
    if "pytest" in cmd:
        return "Python/pytest"
    if argv0 == "npm":
        return "Node/npm"
    if "godot" in argv0.lower():
        return "Godot"
    return "테스트 미감지"


class ServerState:
    def __init__(self, registry: dict):
        self.registry = registry
        self.mu = threading.Lock()
        self.running: set = set()          # task_ids with live worker threads
        self.results: dict = {}            # task_id -> last background outcome
        self.watches: dict = {}            # alias -> {"event", "thread", "interval"}
        self.history: dict = {}            # task_id -> [{ts, phase, status}] (N1 timeline)


def _snapshot_phases(state) -> dict:
    """{task_id: (phase, status)} across all registered repos (read-only)."""
    out = {}
    for _alias, path in list(state.registry.items()):
        try:
            for t in list_tasks(path):
                tid = t.get("task_id")
                if tid and tid not in out:
                    out[tid] = (t.get("phase"), t.get("status"))
        except Exception:
            continue
    return out


def _record_history(state, snap: dict) -> list:
    """Append phase transitions to per-task history. Returns new events
    [{task_id, ts, phase, status}]. First sighting records the entry phase."""
    events = []
    now = time.time()
    with state.mu:
        for tid, (phase, status) in snap.items():
            hist = state.history.setdefault(tid, [])
            if not hist or hist[-1]["phase"] != phase:
                ev = {"ts": now, "phase": phase, "status": status}
                hist.append(ev)
                del hist[:-200]
                events.append({"task_id": tid, **ev})
    return events


def _worker_run(state: ServerState, repo_path: str, task_text: str, task_id: str) -> None:
    try:
        final = cli.execute_run(repo_path, task_text, task_id)
        outcome = {"task_id": task_id, "kind": "run", "done": True,
                   "status": final.get("status"), "pr_url": final.get("pr_url"),
                   "failure_reason": final.get("failure_reason")}
    except lock.LockUnavailable:
        outcome = {"task_id": task_id, "kind": "run", "done": True,
                   "status": "failed", "failure_reason": "lock_unavailable"}
    except Exception as e:  # never kill the server on task errors
        outcome = {"task_id": task_id, "kind": "run", "done": True,
                   "status": "failed", "error": str(e)[:500]}
    with state.mu:
        state.results[task_id] = outcome
        state.running.discard(task_id)


def _worker_resume(state: ServerState, repo_path: str, task_id: str, reset: bool) -> None:
    try:
        res = cli.execute_resume(repo_path, task_id, reset_attempts=reset)
        if res["ok"]:
            final = res["final"]
            outcome = {"task_id": task_id, "kind": "resume", "done": True,
                       "status": final.get("status"), "pr_url": final.get("pr_url"),
                       "failure_reason": final.get("failure_reason")}
        else:
            outcome = {"task_id": task_id, "kind": "resume", "done": True,
                       "status": "failed", "error": res["error"]}
    except lock.LockUnavailable:
        outcome = {"task_id": task_id, "kind": "resume", "done": True,
                   "status": "failed", "failure_reason": "lock_unavailable"}
    except Exception as e:  # never kill the server on task errors
        outcome = {"task_id": task_id, "kind": "resume", "done": True,
                   "status": "failed", "error": str(e)[:500]}
    with state.mu:
        state.results[task_id] = outcome
        state.running.discard(task_id)


def _worker_watch(state: ServerState, alias: str, repo_path: str, interval: int,
                  stop: threading.Event) -> None:
    try:
        watch_loop(repo_path, interval, stop=stop)
    finally:
        with state.mu:
            cur = state.watches.get(alias)
            if cur is not None and cur["event"] is stop:
                del state.watches[alias]


class Handler(BaseHTTPRequestHandler):
    server_version = "orch-serve/1"

    def log_message(self, *args):  # quiet: 2s polling would spam stderr
        pass

    # -- helpers ---------------------------------------------------------
    def _send(self, code: int, obj) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except ValueError:
            return {}

    def _repo(self, alias: str) -> str | None:
        return self.server.state.registry.get(alias)

    # -- GET -------------------------------------------------------------
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/":
            return self._serve_dashboard()
        if parsed.path == "/api/repos":
            return self._send(200, {"repos": self._repos_snapshot()})
        if parsed.path == "/api/tasks":
            repo = self._repo((qs.get("repo") or [""])[0])
            if repo is None:
                return self._send(400, {"error": "unknown repo alias"})
            return self._send(200, {"tasks": list_tasks(repo)})
        if parsed.path == "/api/events":
            repo = self._repo((qs.get("repo") or [""])[0])
            if repo is None:
                return self._send(400, {"error": "unknown repo alias"})
            return self._send(200, self._events_snapshot(repo))
        if parsed.path == "/api/log":
            return self._serve_log((qs.get("task") or [""])[0])
        if parsed.path == "/api/agents":
            return self._send(200, {"profiles": runners.load_profiles(),
                                    "efforts": list(runners.EFFORT_LEVELS)})
        if parsed.path == "/api/models":
            return self._send(200, runners.available_models())
        return self._send(404, {"error": "not found"})

    def _serve_dashboard(self) -> None:
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
        try:
            with open(here, "rb") as f:
                body = f.read()
        except OSError:
            return self._send(500, {"error": "dashboard.html missing"})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_log(self, task_id: str, window_s: int = 50):
        """SSE timeline for one task: replay recorded history, then follow
        live transitions until window_s elapses or the client disconnects."""
        if not task_id:
            return self._send(400, {"error": "empty task"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def emit(ev: dict) -> None:
            line = ("data: " + json.dumps(ev) + "\n\n").encode("utf-8")
            self.wfile.write(line)
            self.wfile.flush()

        try:
            with self.server.state.mu:
                replay = list(self.server.state.history.get(task_id, []))
            for ev in replay[-50:]:
                emit({"task_id": task_id, **ev})
            seen = len(replay)
            end = time.time() + window_s
            while time.time() < end:
                time.sleep(1)
                with self.server.state.mu:
                    hist = list(self.server.state.history.get(task_id, []))
                for ev in hist[seen:]:
                    emit({"task_id": task_id, **ev})
                seen = len(hist)
        except (BrokenPipeError, ConnectionResetError):
            pass
        return None

    def _repos_snapshot(self) -> list:
        out = []
        for alias, path in self.server.state.registry.items():
            st = lock.status(path)
            out.append({"alias": alias, "path": path,
                        "locked": st is not None,
                        "lock_task": (st or {}).get("task_id"),
                        "stack": stack_of(path)})
        return out

    def _events_snapshot(self, repo: str) -> dict:
        with self.server.state.mu:
            running = sorted(self.server.state.running)
            recent = [self.server.state.results[k]
                      for k in sorted(self.server.state.results)[-20:]]
            watching = self.server.state.watches.get(
                next((a for a, p in self.server.state.registry.items() if p == repo), ""),
                None) is not None
        return {"ts": time.time(), "tasks": list_tasks(repo),
                "watching": watching, "running": running, "recent": recent}

    # -- POST ------------------------------------------------------------
    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        data = self._body()
        if parsed.path == "/api/run":
            return self._api_run(data)
        if parsed.path == "/api/resume":
            return self._api_resume(data)
        if parsed.path == "/api/watch":
            return self._api_watch(data)
        if parsed.path == "/api/agents":
            return self._send(200, {"profiles": runners.save_profiles(data)})
        return self._send(404, {"error": "not found"})

    def _api_run(self, data: dict):
        repo = self._repo(str(data.get("repo") or ""))
        task = str(data.get("task") or "").strip()
        if repo is None:
            return self._send(400, {"error": "unknown repo alias"})
        if not task:
            return self._send(400, {"error": "empty task"})
        if lock.status(repo) is not None:
            return self._send(409, {"error": "lock_unavailable",
                                    "detail": "repo is busy; try again later"})
        try:
            runners.assert_clean_tree(repo)
        except runners.NotARepoError as e:
            return self._send(400, {"error": "not_a_repo", "detail": str(e)[:500]})
        except runners.DirtyTreeError as e:
            return self._send(409, {"error": "dirty_tree", "detail": str(e)[:500]})
        task_id = cli._new_task_id()
        with self.server.state.mu:
            self.server.state.running.add(task_id)
        th = threading.Thread(target=_worker_run,
                              args=(self.server.state, repo, task, task_id),
                              daemon=True)
        th.start()
        return self._send(202, {"task_id": task_id})

    def _api_resume(self, data: dict):
        repo = self._repo(str(data.get("repo") or ""))
        task_id = str(data.get("task_id") or "")
        if repo is None:
            return self._send(400, {"error": "unknown repo alias"})
        if not task_id:
            return self._send(400, {"error": "empty task_id"})
        if lock.status(repo) is not None:
            return self._send(409, {"error": "lock_unavailable",
                                    "detail": "repo is busy; try again later"})
        with self.server.state.mu:
            self.server.state.running.add(task_id)
        th = threading.Thread(target=_worker_resume,
                              args=(self.server.state, repo, task_id,
                                    bool(data.get("reset_attempts"))),
                              daemon=True)
        th.start()
        return self._send(202, {"task_id": task_id})

    def _api_watch(self, data: dict):
        repo = self._repo(str(data.get("repo") or ""))
        if repo is None:
            return self._send(400, {"error": "unknown repo alias"})
        alias = str(data.get("repo"))
        with self.server.state.mu:
            cur = self.server.state.watches.get(alias)
            if data.get("stop"):
                if cur is None:
                    return self._send(200, {"watching": False})
                cur["event"].set()
                return self._send(200, {"watching": False, "stopping": True})
            if cur is not None:
                return self._send(409, {"error": "already watching"})
            try:
                interval = max(5, int(data.get("interval", 60)))
            except (ValueError, TypeError):
                return self._send(400, {"error": "bad interval"})
            ev = threading.Event()
            th = threading.Thread(target=_worker_watch,
                                  args=(self.server.state, alias, repo, interval, ev),
                                  daemon=True)
            self.server.state.watches[alias] = {"event": ev, "thread": th,
                                                "interval": interval}
            th.start()
            return self._send(202, {"watching": True, "interval": interval})


def serve(port: int, repos_spec: str) -> int:
    """Entry for `orch serve`. Merges --repos into the registry and serves."""
    reg = load_registry()
    reg.update(parse_repos_arg(repos_spec))
    save_registry(reg)
    if not reg:
        print("[orch] error: no repos registered; pass --repos alias=/path,...",
              flush=True)
        return 2
    state = ServerState(reg)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.state = state
    threading.Thread(target=_notifier_loop, args=(state,), daemon=True).start()
    print(f"[orch] dashboard at http://127.0.0.1:{server.server_port} "
          f"repos={','.join(sorted(reg))} (localhost only)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


# ---------------------------------------------------------------------------
# login-start service (macOS launchd, UX-1)
# ---------------------------------------------------------------------------

def service_plist_path() -> str:
    return os.path.join(os.path.expanduser("~"), "Library/LaunchAgents",
                        f"{SERVICE_LABEL}.plist")


def _orch_bin() -> str:
    """Absolute path to the orch executable (launchd rejects relative paths;
    PATH entries like '.venv/bin' would otherwise leak through)."""
    found = shutil.which("orch")
    if found:
        return os.path.realpath(os.path.abspath(found))
    return os.path.realpath(os.path.abspath(sys.argv[0]))


def _launchctl(*args) -> int:
    return subprocess.run(["launchctl", *args], capture_output=True).returncode


def _service_path() -> str:
    """PATH for the launchd service. launchd's default PATH lacks the user
    tool dirs (opencode/gh live in ~/.opencode/bin, ~/.local/bin), which
    silently broke task runs under the installed service (observed 2026-09-05:
    `opencode models` empty, runners unresolvable)."""
    seen, parts = set(), []
    cands = (os.environ.get("PATH", "").split(os.pathsep)
             + [os.path.expanduser("~/.opencode/bin"),
                os.path.expanduser("~/.local/bin"),
                "/opt/homebrew/bin", "/usr/local/bin",
                "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
    for p in cands:
        if p and p not in seen:
            seen.add(p)
            parts.append(p)
    return os.pathsep.join(parts)


def install_service(port: int) -> str:
    """Write the LaunchAgent plist and bootstrap it. Returns plist path."""
    path = service_plist_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    plist = {
        "Label": SERVICE_LABEL,
        "ProgramArguments": [_orch_bin(), "serve", "--port", str(port)],
        "EnvironmentVariables": {"PATH": _service_path()},
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": "/tmp/orch-serve.log",
        "StandardErrorPath": "/tmp/orch-serve.err",
    }
    with open(path, "wb") as f:
        plistlib.dump(plist, f)
    _launchctl("bootstrap", f"gui/{os.getuid()}", path)
    return path


def uninstall_service() -> bool:
    """Bootout and remove the plist. False when nothing was installed."""
    _launchctl("bootout", f"gui/{os.getuid()}", service_plist_path())
    try:
        os.remove(service_plist_path())
        return True
    except FileNotFoundError:
        return False


# ---------------------------------------------------------------------------
# completion notifications (macOS, UX-2)
# ---------------------------------------------------------------------------

_TERMINAL = ("done", "failed")


def _notify(title: str, message: str) -> None:
    if sys.platform != "darwin":
        return
    try:
        subprocess.run(["osascript", "-e",
                        f'display notification "{message}" with title "{title}"'],
                       capture_output=True, timeout=10)
    except Exception:
        pass  # notifications must never kill the server


def _phase_of_info(t: dict) -> str:
    return t.get("phase") or phase_of(t)


def _detect_transitions(old: dict, new: dict) -> list:
    """{task_id: status} snapshots -> [(task_id, status, {})] to announce.

    Only non-terminal -> terminal transitions (no spam for already-done
    tasks seen after a restart, and none for tasks never seen running).
    """
    out = []
    for tid, st in new.items():
        if st in _TERMINAL and tid in old and old.get(tid) not in _TERMINAL:
            out.append((tid, st, {}))
    return out


def _notifier_loop(state, interval: int = 5) -> None:
    last: dict = {}
    while True:
        time.sleep(interval)
        cur: dict = {}
        info: dict = {}
        try:
            for _alias, path in list(state.registry.items()):
                for t in list_tasks(path):
                    tid = t.get("task_id")
                    if tid:
                        cur[tid] = t.get("status") or "running"
                        info[tid] = t
        except Exception:
            continue
        _record_history(state, {tid: (_phase_of_info(info[tid]), cur[tid]) for tid in cur})
        for tid, st, _ in _detect_transitions(last, cur):
            t = info.get(tid, {})
            if st == "done":
                _notify(f"orch 완료: {tid}", str(t.get("pr_url") or "PR 없음")[:200])
            else:
                _notify(f"orch 실패: {tid}", str(t.get("failure_reason") or "")[:200])
        last = cur


# ---------------------------------------------------------------------------
# failure help in plain Korean (UX-4)
# ---------------------------------------------------------------------------

REASON_HELP = {
    "no_test_command": ("테스트 명령을 못 찾았어",
        "pytest 설정, package.json test 스크립트, Godot project.godot 중 하나가 필요해",
        "러너 표시를 추가하고 resume"),
    "test_failed_exhausted": ("3번 고쳐도 테스트 실패",
        "에이전트가 못 고친 문제야. 직접 보거나 작업을 쪼개서 다시 지시해",
        "브랜치는 그대로 있으니 이어서 수정"),
    "implement_crash": ("실행 중 꺼짐",
        "코딩 CLI 타임아웃/크래시야. 보통 다시 하면 돼",
        "resume 버튼"),
    "timeout": ("시간 초과",
        "10분(테스트) 또는 20분(코딩) 제한을 넘었어",
        "작업을 쪼개서 다시 지시"),
    "analyze_error": ("분석 실패",
        "계획 단계에서 막혔어 (CLI 오류 또는 작업 중 파일 변경)",
        "작업 설명을 구체적으로 바꿔서 재실행"),
    "lock_unavailable": ("다른 작업 실행 중",
        "저장소당 1개씩만 돌아가",
        "끝날 때까지 대기"),
    "secret_detected": ("시크릿 감지됨",
        "커밋 직전 키 패턴이 발견돼서 차단했어",
        "해당 파일을 확인하고 다시 지시"),
    "no_changes": ("변경 없음",
        "에이전트가 코드를 안 고쳤어",
        "작업 설명을 구체적으로 바꿔서 재실행"),
    "dirty_tree": ("커밋 안 된 변경 있음",
        "네 작업물이 있어서 시작을 거부했어 (쓸려 들어가는 것 방지)",
        "커밋/스태시 후 재실행"),
}


def help_for(code) -> dict:
    title, desc, action = REASON_HELP.get(
        code or "", ("상태 확인 필요", "알 수 없는 상태야", "서버 로그 확인"))
    return {"title": title, "desc": desc, "action": action}
