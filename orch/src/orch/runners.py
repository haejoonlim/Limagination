"""The ONLY external-execution layer (design v2 §3, handoff §5).

Everything that spawns a process lives here:
- coding CLI (opencode / claude / codex) with timeouts and process-tree kill
- test command detection & execution (v2 §7.6: no guessing)
- git with ref guards (main/master push + force-push blocked at this layer)
- gh (issues / pr)
- secret pattern scan (v2 §7.3, minimal regex defense line)

Graph nodes branch ONLY on the dicts returned here — they never call subprocess.

P0 spike findings baked into config:
- `opencode run` works headless ONLY with a dedicated minimal config (the user's
  global config loads 7 MCP servers that block startup) and stdin closed.
- `claude -p` is not logged in headless on this machine (kept as fallback entry).
- `codex exec` needs `< /dev/null` + `--skip-git-repo-check`; currently
  quota-exhausted (kept as fallback entry).
"""

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile

CODING_CLI_TIMEOUT_S = 1200  # 20 min (v2 §7.8-2)
TEST_TIMEOUT_S = 600  # 10 min (v2 §7.8-2)

# ---------------------------------------------------------------------------
# Coding CLI configuration — selection order is DATA, not hardcoded branches
# (design v2 §9: "하드코딩 대신 설정값으로 분리"). Override with
# ORCH_CODING_CLI=<name> to force one.
# ---------------------------------------------------------------------------

_HEADLESS_OPENCODE_CONFIG = {
    "$schema": "https://opencode.ai/config.json",
    # no "mcp" key: skip the 7 global MCP servers that block headless startup
    # least privilege (imagraph harness profile): everything the task needs
    # (edit, pytest/npm, git add/commit/checkout, gh) stays allowed; only
    # destructive/exfiltrating patterns are denied.
    "permission": {
        "bash": {
            "*": "allow",
            "rm *": "deny",
            "sudo *": "deny",
            "curl *": "deny",
            "wget *": "deny",
            "git push*": "deny",
            "git reset*": "deny",
            "git clean*": "deny",
        },
    },
}

_RUNNERS: list[dict] = [
    {
        "name": "opencode",
        "cmd": ["opencode", "run"],
        "env": {},  # OPENCODE_CONFIG injected per-call (temp file)
        "plan_args": ["--agent", "plan"],
    },
    {
        "name": "claude",
        "cmd": ["claude", "-p"],
        "env": {},
        "plan_args": [],  # read-only-ness enforced via prompt suffix
    },
    {
        "name": "codex",
        "cmd": ["codex", "exec", "--skip-git-repo-check"],
        "env": {},
        "plan_args": [],  # codex exec defaults to sandbox: read-only
    },
]

_READONLY_PROMPT_SUFFIX = (
    "\n\nSTRICT READ-ONLY MODE: analyze only. Do NOT create, modify, or delete "
    "any file. Do NOT run any state-changing command."
)


def _runner_config() -> dict:
    """Pick the first installed runner, or the one forced via ORCH_CODING_CLI."""
    forced = os.environ.get("ORCH_CODING_CLI")
    if forced:
        for r in _RUNNERS:
            if r["name"] == forced:
                if not shutil.which(r["cmd"][0]):
                    raise RuntimeError(f"ORCH_CODING_CLI={forced} but {r['cmd'][0]} is not installed")
                return r
        raise RuntimeError(f"unknown ORCH_CODING_CLI={forced!r} (known: {[r['name'] for r in _RUNNERS]})")
    for r in _RUNNERS:
        if shutil.which(r["cmd"][0]):
            return r
    raise RuntimeError(
        "no coding CLI found (looked for: "
        + ", ".join(r["cmd"][0] for r in _RUNNERS)
        + ")"
    )


# ---------------------------------------------------------------------------
# Agent profiles: per-agent model/effort + per-role mapping (dashboard-managed)
# ---------------------------------------------------------------------------

EFFORT_LEVELS = ("minimal", "low", "medium", "high", "max")


def profiles_path() -> str:
    return os.environ.get("ORCH_AGENTS") or os.path.join(os.path.expanduser("~"), ".orch-agents.json")


def default_profiles() -> dict:
    return {
        "agents": {r["name"]: {"enabled": True, "model": "", "effort": ""}
                   for r in _RUNNERS},
        "roles": {
            # subagent: opencode-only --agent override for the implement role.
            # analyze always uses the plan agent (read-only).
            "analyze": {"agent": "opencode", "model": "", "effort": "", "subagent": ""},
            "implement": {"agent": "opencode", "model": "", "effort": "", "subagent": ""},
            "review": {"agent": "opencode", "model": "", "effort": "", "subagent": ""},
        },
    }


def load_profiles() -> dict:
    """Load ~/.orch-agents.json merged over defaults. Missing/corrupt file
    (or wrong shape) falls back to defaults — never raises."""
    prof = default_profiles()
    try:
        with open(profiles_path(), encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return prof
        for name, cfg in (data.get("agents") or {}).items():
            if name in prof["agents"] and isinstance(cfg, dict):
                for k in ("enabled", "model", "effort"):
                    if k in cfg:
                        prof["agents"][name][k] = cfg[k]
        for role, cfg in (data.get("roles") or {}).items():
            if role in prof["roles"] and isinstance(cfg, dict):
                for k in ("agent", "model", "effort", "subagent"):
                    if k in cfg:
                        prof["roles"][role][k] = cfg[k]
    except (OSError, ValueError):
        pass
    return prof


def save_profiles(data: dict) -> dict:
    """Validate + persist agent profiles. Unknown agents/roles/keys are
    dropped; returns the normalized document that was written."""
    clean = default_profiles()
    if isinstance(data, dict):
        for name in clean["agents"]:
            cfg = (data.get("agents") or {}).get(name)
            if isinstance(cfg, dict):
                if isinstance(cfg.get("enabled"), bool):
                    clean["agents"][name]["enabled"] = cfg["enabled"]
                for k in ("model", "effort"):
                    if isinstance(cfg.get(k), str):
                        clean["agents"][name][k] = cfg[k][:200]
        for role in clean["roles"]:
            cfg = (data.get("roles") or {}).get(role)
            if isinstance(cfg, dict):
                if cfg.get("agent") in clean["agents"]:
                    clean["roles"][role]["agent"] = cfg["agent"]
                for k in ("model", "effort", "subagent"):
                    if isinstance(cfg.get(k), str):
                        clean["roles"][role][k] = cfg[k][:200]
    path = profiles_path()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, sort_keys=True)
    return clean


# ---------------------------------------------------------------------------
# Model discovery for pickers (UI): live where possible, cache where not
# ---------------------------------------------------------------------------

CLAUDE_MODEL_ALIASES = ["sonnet", "opus", "haiku"]

_MODELS_CACHE = {"ts": 0.0, "data": {}}
_MODELS_TTL_S = 3600


def _codex_cache_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".codex", "models_cache.json")


def _opencode_models() -> list:
    if not shutil.which("opencode"):
        return []
    rc, out, _ = _run(["opencode", "models"], timeout_s=30)
    if rc != 0:
        return []
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _codex_models() -> list:
    try:
        with open(_codex_cache_path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    models = data.get("models") if isinstance(data, dict) else None
    if isinstance(models, list):
        for m in models:
            if isinstance(m, dict):
                ident = m.get("slug") or m.get("id") or m.get("name")
                if ident:
                    out.append(str(ident))
            elif isinstance(m, str):
                out.append(m)
    return out


def available_models() -> dict:
    """{agent: [model ids]} for pickers. opencode live, codex from its cache
    file, claude curated aliases (no listable source). 1h process cache."""
    import time
    now = time.time()
    if now - _MODELS_CACHE["ts"] < _MODELS_TTL_S and _MODELS_CACHE["data"]:
        return _MODELS_CACHE["data"]
    data = {
        "opencode": _opencode_models(),
        "codex": _codex_models(),
        "claude": list(CLAUDE_MODEL_ALIASES),
    }
    _MODELS_CACHE.update({"ts": now, "data": data})
    return data


def _model_effort_args(name: str, model: str, effort: str) -> list:
    """CLI flags carrying model/effort per runner. Empty values are omitted."""
    args: list = []
    if name == "opencode":
        if model:
            args += ["--model", model]
        if effort:
            args += ["--variant", effort]
    elif name == "claude":
        if model:
            args += ["--model", model]
        if effort:
            args += ["--effort", effort]
    elif name == "codex":
        if model:
            args += ["-m", model]
        if effort:
            args += ["-c", f'model_reasoning_effort="{effort}"']
    return args


def _resolve_runner(role: str) -> tuple:
    """(runner_dict, model, effort, subagent) for a role ("analyze"|"implement").

    Precedence: ORCH_CODING_CLI (preserves _runner_config errors) > role's
    agent (must be known, enabled, installed) > first installed+enabled in
    _RUNNERS order. Model/effort/subagent: role-level wins, else agent-level
    (subagent lives on the role only; empty = default behavior).
    """
    prof = load_profiles()
    forced = os.environ.get("ORCH_CODING_CLI")
    if forced:
        runner = _runner_config()  # raises on unknown/missing, as before
        rcfg = prof["roles"].get(role, {})
        acfg = prof["agents"].get(runner["name"], {})
        return runner, rcfg.get("model") or acfg.get("model") or "", \
            rcfg.get("effort") or acfg.get("effort") or "", \
            rcfg.get("subagent") or ""
    want = prof["roles"].get(role, {}).get("agent") or "opencode"
    by_name = {r["name"]: r for r in _RUNNERS}
    candidates = ([want] if want in by_name else []) + \
        [r["name"] for r in _RUNNERS if r["name"] != want]
    for name in candidates:
        if not prof["agents"].get(name, {}).get("enabled", True):
            continue
        if not shutil.which(by_name[name]["cmd"][0]):
            continue
        rcfg = prof["roles"].get(role, {})
        acfg = prof["agents"].get(name, {})
        return by_name[name], rcfg.get("model") or acfg.get("model") or "", \
            rcfg.get("effort") or acfg.get("effort") or "", \
            rcfg.get("subagent") or ""
    raise RuntimeError("no enabled coding CLI installed")


def _kill_process_tree(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, AttributeError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass


def _run(cmd, *, cwd=None, env=None, timeout_s: int) -> tuple[int, str, str | None]:
    """Run a command with stdin closed; kill the whole process tree on timeout.

    Returns (returncode, combined_output, error). error is set only on timeout
    (already-killed tree) — non-zero exits are NOT errors here; callers decide.
    """
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        out, _ = proc.communicate(timeout=timeout_s)
        return proc.returncode, out, None
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc)
        try:
            out, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            out = ""
        return proc.returncode, out or "", f"timeout after {timeout_s}s (process tree killed)"


# ---------------------------------------------------------------------------
# run_coding_cli — frozen interface (handoff §5)
# ---------------------------------------------------------------------------

def run_coding_cli(prompt: str, *, timeout_s: int = CODING_CLI_TIMEOUT_S,
                   forbid_edits: bool = False, cwd: str | None = None,
                   role: str | None = None) -> dict:
    """Invoke the configured coding CLI non-interactively.

    Returns {"ok": bool, "output": str, "error": str|None}.
    ok=True means exit 0 within the timeout (whether it obeyed the prompt is a
    graph-level concern, e.g. the analyze integrity guard).
    role overrides the forbid_edits-derived role ("review" etc.).
    """
    eff_role = role or ("analyze" if forbid_edits else "implement")
    runner, model, effort, subagent = _resolve_runner(eff_role)
    name = runner["name"]
    cmd = list(runner["cmd"]) + _model_effort_args(name, model, effort)
    if name == "opencode" and eff_role == "implement" and subagent:
        cmd += ["--agent", subagent]
    if name == "opencode" and eff_role == "review" and subagent:
        cmd += ["--agent", subagent]

    if forbid_edits:
        # review with an explicit reviewer subagent uses it instead of the
        # default read-only agent; analyze always keeps the plan agent.
        if not (eff_role == "review" and subagent):
            cmd += list(runner.get("plan_args", []))

    env = os.environ.copy()
    env.update(runner.get("env", {}))

    if name == "opencode":
        # Dedicated minimal headless config (P0 spike: global config's MCP
        # servers block startup). Written per-call, removed afterwards.
        fd, cfg_path = tempfile.mkstemp(prefix="orch-opencode-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(_HEADLESS_OPENCODE_CONFIG, f)
        env["OPENCODE_CONFIG"] = cfg_path
        # opencode resolves its project dir from $PWD/launch context, not the
        # child process cwd (P0 probe: `pwd` reported the parent's dir), so pin
        # it explicitly.
        if cwd:
            cmd += ["--dir", os.path.abspath(cwd)]
            env["PWD"] = os.path.abspath(cwd)
    elif forbid_edits:
        prompt = prompt + _READONLY_PROMPT_SUFFIX

    try:
        rc, output, err = _run(cmd + [prompt], cwd=cwd, env=env, timeout_s=timeout_s)
    finally:
        if name == "opencode":
            try:
                os.remove(cfg_path)
            except OSError:
                pass

    return {
        "ok": rc == 0 and err is None,
        "output": _strip_ansi(output),  # agent CLIs emit terminal colors/progress
        "error": _strip_ansi(err),  # "timeout after Ns..." when timed out
    }


_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][0-9A-B]")

def _strip_ansi(s: str | None) -> str | None:
    """Remove terminal escape codes from agent output.

    Raw output lands in commit messages and PR bodies (observed: color codes
    and spinners in orch PR text), so scrub at the single collection point.
    """
    if s is None:
        return None
    return _ANSI_RE.sub("", s)


# Tool-owned metadata dirs an agent CLI may scaffold even in read-only mode
# (observed: opencode writes .graft/cache.json). Not user work.
STATUS_NOISE_TOPDIRS = frozenset({".graft", ".opencode", ".claude", ".codex"})


def meaningful_status_lines(status_stdout: str) -> set:
    """git status --porcelain lines minus agent-metadata noise."""
    kept = set()
    for raw in (status_stdout or "").splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("??"):
            top = line[2:].strip().split("/", 1)[0]
            if top in STATUS_NOISE_TOPDIRS:
                continue
        kept.add(line)
    return kept


class DirtyTreeError(Exception):
    """Target repo has uncommitted user changes; refusing to start."""


class NotARepoError(DirtyTreeError):
    """Target path is not a git repository at all."""


def assert_clean_tree(repo_path: str) -> None:
    """Refuse to start a task on a dirty worktree (observed 2026-09-05: two
    parties' uncommitted work — P1 feel code + D-209 telemetry — was swept
    into an orch implement commit via `git add -A`).

    Raises DirtyTreeError describing the meaningful changes. Agent-metadata
    noise (.graft/ etc.) and orch's own .orch/ dir are ignored.
    """
    try:
        probe = git("rev-parse", "--git-dir", repo_path=repo_path)
    except OSError:
        raise NotARepoError(f"{repo_path} is not a git repository")
    if not probe["ok"]:
        raise NotARepoError(f"{repo_path} is not a git repository")
    res = git("status", "--porcelain", repo_path=repo_path)
    if not res["ok"]:
        raise DirtyTreeError(f"cannot inspect worktree: {res['error']}")
    meaningful = set()
    for ln in meaningful_status_lines(res.get("stdout")):
        path = ln[3:].strip() if len(ln) > 3 else ""  # porcelain 'XY <path>'
        if path == ".orch" or path.startswith(".orch/"):
            continue  # orch's own lock dir, not user work
        if "__pycache__" in path or path.endswith(".pyc") or \
                path == ".pytest_cache" or path.startswith(".pytest_cache/"):
            continue  # test-run byproducts (often from orch's own test gate)
        meaningful.add(ln)
    if meaningful:
        preview = "\n".join(sorted(meaningful)[:10])
        raise DirtyTreeError(
            f"repo has uncommitted changes; commit or stash first:\n{preview}")


# ---------------------------------------------------------------------------
# Test detection & execution — v2 §7.6: detect or fail, never guess
# ---------------------------------------------------------------------------

def _godot_binary() -> str | None:
    """Resolve the Godot editor binary: GODOT_BIN env > PATH > well-known
    macOS install. None when not installed (caller falls through to None)."""
    env = os.environ.get("GODOT_BIN")
    if env and os.access(env, os.X_OK):
        return env
    found = shutil.which("godot")
    if found:
        return found
    mac = "/Applications/Godot.app/Contents/MacOS/Godot"
    if os.access(mac, os.X_OK):
        return mac
    return None


def detect_test_command(repo_path: str) -> list[str] | None:
    """Return the test command argv, or None when nothing known is detected."""
    def exists(*parts: str) -> bool:
        return os.path.exists(os.path.join(repo_path, *parts))

    def contains(path: str, needle: str) -> bool:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                return needle in f.read()
        except OSError:
            return False

    # pytest (any explicit indicator)
    if (
        exists("pytest.ini")
        or exists("conftest.py")
        or (exists("pyproject.toml") and contains(os.path.join(repo_path, "pyproject.toml"), "[tool.pytest"))
        or (exists("setup.cfg") and contains(os.path.join(repo_path, "setup.cfg"), "[tool:pytest]"))
        or (exists("tox.ini") and contains(os.path.join(repo_path, "tox.ini"), "[pytest]"))
    ):
        return [sys.executable, "-m", "pytest", "-q"]

    # a tests/ directory with test_*.py files
    tests_dir = os.path.join(repo_path, "tests")
    if os.path.isdir(tests_dir) and any(f.startswith("test_") for f in os.listdir(tests_dir)):
        return [sys.executable, "-m", "pytest", "-q"]

    # npm test (only when a test script exists)
    pkg = os.path.join(repo_path, "package.json")
    if exists("package.json"):
        try:
            with open(pkg, encoding="utf-8", errors="replace") as f:
                scripts = (json.load(f) or {}).get("scripts") or {}
            if "test" in scripts:
                return ["npm", "test", "--silent"]
        except (OSError, ValueError):
            pass

    # Godot boot smoke check (project.godot present + binary installed).
    # Boots headless, runs one frame, quits: catches GDScript parse errors
    # and startup crashes. Shallow by design (no per-file test runner exists
    # in vanilla Godot); deeper SceneTree checks stay manual. v1 scope.
    if exists("project.godot"):
        godot = _godot_binary()
        if godot is not None:
            return [godot, "--headless", "--path", os.path.abspath(repo_path), "--quit"]

    return None


def run_tests(repo_path: str) -> dict:
    """Run detected tests. passed=None means detection failed (-> no_test_command)."""
    command = detect_test_command(repo_path)
    if command is None:
        return {"passed": None, "output": "", "command": None}
    rc, output, err = _run(command, cwd=repo_path, timeout_s=TEST_TIMEOUT_S)
    if err is not None:  # timeout
        return {"passed": False, "output": output + f"\n[orch] {err}", "command": shlex.join(command)}
    return {"passed": rc == 0, "output": output, "command": shlex.join(command)}


# ---------------------------------------------------------------------------
# git with ref guards (v2 §7.8-3, handoff §5)
# ---------------------------------------------------------------------------

_PROTECTED_REFS = {"main", "master", "refs/heads/main", "refs/heads/master"}


def _git_guard(args: list[str]) -> str | None:
    """Return a refusal message when the git invocation is forbidden, else None."""
    if not args:
        return None
    sub = args[0]

    if sub == "push":
        if any(a in ("--force", "--force-with-lease", "-f") for a in args):
            return "ref guard: force-push is forbidden"
        # push target refs are the non-option positionals after the remote
        positional = [a for a in args[1:] if not a.startswith("-")]
        # first positional is the remote (origin), remaining are refspecs
        for spec in positional[1:]:
            spec = spec.lstrip("+")
            if spec.startswith(":"):
                # ':ref' deletes a remote ref
                dst = spec[1:]
                if dst in _PROTECTED_REFS:
                    return f"ref guard: deleting protected ref {dst!r} is forbidden"
                continue
            src, _, dst = spec.partition(":")
            target = dst if dst else src  # 'HEAD:master' pushes to master
            if target in _PROTECTED_REFS:
                return f"ref guard: direct push to protected ref {target!r} is forbidden"

    if sub in ("branch", "tag") and "-D" in args or sub == "push" and "--delete" in args:
        pass  # branch deletion of orch/* branches is allowed; main/master deletes not attempted by graph

    if sub == "reset" and any(a in ("--hard",) for a in args):
        return "ref guard: `git reset --hard` is forbidden (would discard work)"

    return None


def git(*args, repo_path: str) -> dict:
    """Run git with ref guards. Returns {"ok", "stdout", "stderr", "error"}."""
    args = list(args)
    refusal = _git_guard(args)
    if refusal:
        return {"ok": False, "stdout": "", "stderr": refusal, "error": refusal}
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {
        "ok": proc.returncode == 0,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "error": None if proc.returncode == 0 else f"git {' '.join(args)} failed: {proc.stderr.strip()}",
    }


def gh(*args, repo_path: str | None = None) -> dict:
    """Run gh. Returns {"ok", "stdout", "stderr", "error"}."""
    proc = subprocess.run(
        ["gh", *args],
        cwd=repo_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {
        "ok": proc.returncode == 0,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "error": None if proc.returncode == 0 else f"gh {' '.join(args)} failed: {proc.stderr.strip()}",
    }


# ---------------------------------------------------------------------------
# Secret scan (v2 §7.3 — minimal regex defense line, NOT a full scanner)
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("openai_style_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
]


def check_secrets(diff_text: str) -> list[str]:
    """Return names of matched secret patterns; empty list = clean.

    Only ADDED lines ('+' prefix, excluding '+++ ' file headers) are scanned —
    removals and context lines can't leak anything new.
    """
    matched: list[str] = []
    for line in diff_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        payload = line[1:]
        for name, pattern in _SECRET_PATTERNS:
            if pattern.search(payload):
                matched.append(name)
                break
    # secret-looking FILE PATHS added by the diff
    for m in re.finditer(r"^diff --git a/(.+)$", diff_text, re.M):
        path = m.group(1).strip()
        base = os.path.basename(path)
        if (
            base == ".env"
            or path.endswith(".pem")
            or base in ("id_rsa", "id_dsa", "id_ed25519")
            or base.endswith(".keystore")
        ):
            matched.append("secret_file_added")
            break
    return sorted(set(matched))
