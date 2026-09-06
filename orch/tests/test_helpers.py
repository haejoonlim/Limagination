"""Unit tests (handoff P2 list): branch naming/slug, ref guard, lock
acquire/reclaim, idempotency marker, secret detection.

Pure-function and tmp-repo tests only — no coding CLI, no network.
"""

import json
import os
import subprocess
import sys

import pytest

from orch import graph, lock, runners
from orch.lock import LockUnavailable, lock_path


# ---------------------------------------------------------------------------
# branch naming & slug (수정4)
# ---------------------------------------------------------------------------

def test_slugify_basic():
    assert graph._slugify("Add login feature") == "add-login-feature"


def test_slugify_caps_at_30():
    long = "a" * 50
    assert len(graph._slugify(long)) == 30


def test_slugify_first_30_chars_only():
    # hyphens produced by substitution count toward the cap
    assert graph._slugify("A" * 29 + " b") == "a" * 29  # 30th char is space -> '-... stripped'


def test_slugify_collapses_and_trims_hyphens():
    assert graph._slugify("--Hello,,  World!!--") == "hello-world"


def test_slugify_empty_becomes_task():
    assert graph._slugify("") == "task"
    assert graph._slugify("!!!@@@###") == "task"
    assert graph._slugify(None) == "task"


def test_branch_name_github_origin():
    assert graph.make_branch_name("github", 42, "Fix login bug") == "orch/gh-42-fix-login-bug"


def test_branch_name_cli_origin():
    name = graph.make_branch_name("cli", None, "Fix login bug")
    assert name.startswith("orch/cli-")
    parts = name.split("-")
    # 'orch/cli' is one token (split on '-'): ['orch/cli', YYYYMMDD, HHMMSS, slug...]
    assert len(parts[1]) == 8 and parts[1].isdigit()
    assert len(parts[2]) == 6 and parts[2].isdigit()
    assert name.endswith("fix-login-bug")


# ---------------------------------------------------------------------------
# idempotency marker (v2 §7.5)
# ---------------------------------------------------------------------------

def test_marker_format():
    assert graph.make_marker("gh-12", 2) == "orch:gh-12:attempt=2"


@pytest.fixture()
def git_repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "f.txt").write_text("hi")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "init"], check=True)
    return str(tmp_path)


def test_marker_in_head_true(git_repo):
    marker = graph.make_marker("gh-1", 0)
    subprocess.run(["git", "-C", git_repo, "commit", "--allow-empty", "-qm", f"work\n\n{marker}"], check=True)
    assert graph.marker_in_head(git_repo, marker) is True


def test_marker_in_head_false(git_repo):
    assert graph.marker_in_head(git_repo, "orch:nope:attempt=9") is False


# ---------------------------------------------------------------------------
# ref guard (v2 §7.8-3) — blocks BEFORE any git execution
# ---------------------------------------------------------------------------

def test_guard_blocks_push_to_main():
    msg = runners._git_guard(["push", "origin", "main"])
    assert msg and "forbidden" in msg


def test_guard_blocks_push_to_master_refspec():
    msg = runners._git_guard(["push", "origin", "HEAD:master"])
    assert msg and "forbidden" in msg


def test_guard_blocks_force_push():
    for flag in ("--force", "-f", "--force-with-lease"):
        assert runners._git_guard(["push", flag, "origin", "some-branch"])


def test_guard_allows_feature_branch_push():
    assert runners._git_guard(["push", "-u", "origin", "orch/gh-1-x"]) is None


def test_guard_blocks_hard_reset():
    assert runners._git_guard(["reset", "--hard", "HEAD~1"])


def test_git_refuses_without_executing(tmp_path):
    # not even a git repo here: refusal must happen before git runs
    res = runners.git("push", "origin", "main", repo_path=str(tmp_path))
    assert res["ok"] is False
    assert "forbidden" in res["stderr"]


# ---------------------------------------------------------------------------
# lock (수정3): acquire / duplicate / stale reclaim / release / force
# ---------------------------------------------------------------------------

def test_lock_acquire_and_release(tmp_path):
    lock.acquire(str(tmp_path), "cli-1", log=None)
    assert os.path.exists(lock_path(str(tmp_path)))
    data = json.load(open(lock_path(str(tmp_path))))
    assert data["pid"] == os.getpid() and data["task_id"] == "cli-1"
    lock.release(str(tmp_path))
    assert not os.path.exists(lock_path(str(tmp_path)))


def test_lock_blocks_second_holder(tmp_path):
    lock.acquire(str(tmp_path), "cli-1")
    with pytest.raises(LockUnavailable):
        lock.acquire(str(tmp_path), "cli-2")
    lock.release(str(tmp_path))


def test_lock_reclaims_dead_pid(tmp_path):
    # make a lock owned by a definitely-dead pid
    out = subprocess.run(["/bin/sh", "-c", "echo $$; exit 0"], capture_output=True, text=True)
    dead_pid = int(out.stdout.strip())
    os.makedirs(os.path.join(str(tmp_path), ".orch"))
    with open(lock_path(str(tmp_path)), "w") as f:
        json.dump({"pid": dead_pid, "task_id": "old", "started_at": "2026-01-01T00:00:00+00:00"}, f)
    assert not lock._pid_alive(dead_pid)
    lock.acquire(str(tmp_path, ), "cli-9", log=None)  # must reclaim, not raise
    data = json.load(open(lock_path(str(tmp_path))))
    assert data["task_id"] == "cli-9"
    lock.release(str(tmp_path))


def test_lock_release_never_steals_other_pid(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), ".orch"))
    with open(lock_path(str(tmp_path)), "w") as f:
        json.dump({"pid": os.getpid() + 424242, "task_id": "other", "started_at": "x"}, f)
    lock.release(str(tmp_path), log=None)  # must NOT remove it
    assert os.path.exists(lock_path(str(tmp_path)))


def test_lock_force_removal(tmp_path):
    lock.acquire(str(tmp_path), "cli-1")
    assert lock.unlock_force(str(tmp_path), log=None) is True
    assert lock.unlock_force(str(tmp_path), log=None) is False  # nothing left


# ---------------------------------------------------------------------------
# secret scan (v2 §7.3)
# ---------------------------------------------------------------------------

def test_secrets_clean_diff():
    assert runners.check_secrets("+def add(a, b):\n+    return a + b\n") == []


def test_secrets_detect_aws_key():
    diff = "+key = AKIAIOSFODNN7EXAMPLE\n"
    assert "aws_access_key" in runners.check_secrets(diff)


def test_secrets_detect_openai_style_and_github_token():
    diff = "+OPENAI_KEY=sk-proj-abcdefghij0123456789abcd\n+GH=ghp_" + "a" * 36 + "\n"
    hits = runners.check_secrets(diff)
    assert "openai_style_key" in hits and "github_token" in hits


def test_secrets_detect_private_key_block():
    diff = "+-----BEGIN RSA PRIVATE KEY-----\n+abc\n"
    assert "private_key_block" in runners.check_secrets(diff)


def test_secrets_detect_env_file_added():
    diff = "diff --git a/.env b/.env\nnew file\n+++ b/.env\n+SECRET=x\n"
    assert "secret_file_added" in runners.check_secrets(diff)


def test_secrets_ignore_removed_and_context_lines():
    diff = "-AKIAIOSFODNN7EXAMPLE\n AKIAIOSFODNN7EXAMPLE\n"
    assert runners.check_secrets(diff) == []


# ---------------------------------------------------------------------------
# test command detection (v2 §7.6) — detect or None, never guess
# ---------------------------------------------------------------------------

def test_detect_pytest_in_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    assert runners.detect_test_command(str(tmp_path)) is not None


def test_detect_none(tmp_path):
    (tmp_path / "README.md").write_text("nothing here")
    assert runners.detect_test_command(str(tmp_path)) is None


def test_detect_package_json_test_script(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"test": "vitest run"}}))
    assert runners.detect_test_command(str(tmp_path)) == ["npm", "test", "--silent"]


def test_detect_godot_boot_check(tmp_path, monkeypatch):
    (tmp_path / "project.godot").write_text("[application]\n")
    monkeypatch.setattr(runners, "_godot_binary", lambda: "/fake/godot")
    cmd = runners.detect_test_command(str(tmp_path))
    assert cmd[0] == "/fake/godot"
    assert "--headless" in cmd and "--quit" in cmd and str(tmp_path) in cmd


def test_detect_godot_none_without_binary(tmp_path, monkeypatch):
    (tmp_path / "project.godot").write_text("[application]\n")
    monkeypatch.setattr(runners, "_godot_binary", lambda: None)
    assert runners.detect_test_command(str(tmp_path)) is None


def test_godot_binary_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("GODOT_BIN", sys.executable)
    assert runners._godot_binary() == sys.executable


def test_strip_ansi_removes_terminal_codes():
    dirty = "\x1b[0m→ \x1b[0mRead foo.py\n\x1b[32mok\x1b[0m"
    clean = runners._strip_ansi(dirty)
    assert "\x1b" not in clean
    assert "Read foo.py" in clean and "ok" in clean
    assert runners._strip_ansi(None) is None


def _git(repo, *args):
    import subprocess
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


def _dirty_repo(tmp_path):
    d = tmp_path / "dirty"
    d.mkdir()
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "t@t")
    _git(d, "config", "user.name", "t")
    (d / "a.txt").write_text("x")
    _git(d, "add", "-A")
    _git(d, "commit", "-qm", "init")
    return str(d)


def test_assert_clean_tree_passes_when_clean(tmp_path):
    runners.assert_clean_tree(_dirty_repo(tmp_path))  # no raise


def test_assert_clean_tree_ignores_agent_noise_and_orch_dir(tmp_path):
    repo = _dirty_repo(tmp_path)
    import os
    os.makedirs(os.path.join(repo, ".graft"))
    open(os.path.join(repo, ".graft", "cache.json"), "w").write("{}")
    os.makedirs(os.path.join(repo, ".orch"))
    open(os.path.join(repo, ".orch", "lock"), "w").write("{}")
    runners.assert_clean_tree(repo)  # no raise


def test_assert_clean_tree_refuses_user_changes(tmp_path):
    import pytest
    repo = _dirty_repo(tmp_path)
    open(os.path.join(repo, "work.txt"), "w").write("uncommitted")
    with pytest.raises(runners.DirtyTreeError, match="uncommitted changes"):
        runners.assert_clean_tree(repo)


def test_assert_clean_tree_ignores_nested_git_repo(tmp_path):
    """An untracked dir that is itself a git repo is a separate project
    (observed: soul-commander/ + RecallInfinity/ nested in Limagination),
    not this repo's uncommitted work."""
    import subprocess
    repo = _dirty_repo(tmp_path)
    nested = os.path.join(repo, "sibling-project")
    os.makedirs(nested)
    subprocess.run(["git", "init", "-q", nested], check=True)
    open(os.path.join(nested, "own.txt"), "w").write("x")
    runners.assert_clean_tree(repo)  # no raise


def test_assert_clean_tree_still_blocks_untracked_dir_with_buried_repo(tmp_path):
    """A plain untracked dir whose .git sits deeper still counts: its own
    top-level files are real untracked content."""
    import subprocess
    repo = _dirty_repo(tmp_path)
    outer = os.path.join(repo, "not-a-project")
    os.makedirs(os.path.join(outer, "deeper"))
    subprocess.run(["git", "init", "-q", os.path.join(outer, "deeper")], check=True)
    open(os.path.join(outer, "own.txt"), "w").write("x")
    with pytest.raises(runners.DirtyTreeError, match="uncommitted changes"):
        runners.assert_clean_tree(repo)


def test_implement_and_fix_prompts_forbid_tests_docs_ci():
    from orch.graph import _fix_prompt, _implement_prompt
    for p in (_implement_prompt("plan", "task", "m"), _fix_prompt("plan", "out", "m")):
        assert "scripts/tests/*" in p and "docs/*" in p and ".github/*" in p


def test_assert_clean_tree_rejects_non_repo(tmp_path):
    import pytest
    with pytest.raises(runners.NotARepoError):
        runners.assert_clean_tree(str(tmp_path / "nosuchdir"))


def test_assert_clean_tree_ignores_test_byproducts(tmp_path):
    import os
    repo = _dirty_repo(tmp_path)
    # Mirror the real fixture layout (/tmp/orch-e2e): tests/ itself is
    # TRACKED (test_calc.py committed), so pytest byproducts appear at full
    # path (?? tests/__pycache__/) where the filter can see them. A fully
    # untracked tests/ dir collapses to one '?? tests/' line and must NOT be
    # ignored — that could be real user work.
    os.makedirs(os.path.join(repo, "tests"))
    open(os.path.join(repo, "tests", "test_x.py"), "w").write("x")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "track tests")
    os.makedirs(os.path.join(repo, "tests", "__pycache__"))
    open(os.path.join(repo, "tests", "__pycache__", "x.pyc"), "w").write("b")
    open(os.path.join(repo, "stray.pyc"), "w").write("b")
    runners.assert_clean_tree(repo)  # no raise


def test_assert_clean_tree_blocks_untracked_tests_dir(tmp_path):
    """A fully-untracked tests/ dir (possible real work) must still block."""
    import os
    repo = _dirty_repo(tmp_path)
    os.makedirs(os.path.join(repo, "tests", "__pycache__"))
    open(os.path.join(repo, "tests", "__pycache__", "x.pyc"), "w").write("b")
    try:
        runners.assert_clean_tree(repo)
    except runners.DirtyTreeError:
        pass
    else:
        raise AssertionError("expected DirtyTreeError for untracked tests/ dir")
