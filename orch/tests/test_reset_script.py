"""Integration tests for scripts/reset_e2e_fixture.sh.

Runs the real script end-to-end against a local bare origin built from the
same seed layout as the real fixture repo (calc.py + tests/test_calc.py) —
no network, no gh involved.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "reset_e2e_fixture.sh"
pytestmark = pytest.mark.skipif(not shutil.which("bash"), reason="bash unavailable")


def sh(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def git(*args: str, cwd: str) -> subprocess.CompletedProcess:
    return sh("git", *args, cwd=cwd)


def run_script(*args: str, **kw) -> subprocess.CompletedProcess:
    return sh("bash", str(SCRIPT), *args, **kw)


@pytest.fixture()
def fixture_env(tmp_path, monkeypatch):
    """Local bare origin (calc.py seed, mirroring the real fixture) + clone + env."""
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    seed.mkdir()
    git("init", "-q", str(seed), cwd=str(tmp_path))
    git("config", "user.email", "t@t", cwd=str(seed))
    git("config", "user.name", "t", cwd=str(seed))
    (seed / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (seed / "tests").mkdir()
    (seed / "tests" / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )
    git("add", "-A", cwd=str(seed))
    git("commit", "-qm", "init", cwd=str(seed))
    sh("git", "clone", "-q", "--bare", str(seed), str(origin))
    sh("git", "clone", "-q", str(origin), str(tmp_path / "e2e"))

    monkeypatch.setenv("ORCH_E2E_DIR", str(tmp_path / "e2e"))
    monkeypatch.setenv("ORCH_E2E_REMOTE", str(origin))
    return {"tmp": tmp_path, "origin": origin, "e2e": tmp_path / "e2e"}


def residue_types(e2e: Path) -> set[str]:
    """Human-readable labels for whatever residue the fixture currently holds."""
    out: set[str] = set()
    if git("status", "--porcelain", cwd=str(e2e)).stdout.strip():
        out.add("dirty")
    if git("symbolic-ref", "--short", "-q", "HEAD", cwd=str(e2e)).stdout.strip() != "main":
        out.add("detached")
    if git("for-each-ref", "refs/heads", cwd=str(e2e)).stdout.count("\n") > 1:
        out.add("branches")
    return out


def pollute(e2e: Path) -> None:
    """Deposit one of each residue class the real e2e runs leave behind."""
    (e2e / ".graft").mkdir()
    (e2e / ".graft" / "cache.json").write_text("{}\n")
    (e2e / "__pycache__").mkdir()
    (e2e / "__pycache__" / "calc.pyc").write_bytes(b"\x00")
    git("checkout", "-q", "--detach", "HEAD", cwd=str(e2e))
    git("commit", "-qam", "drift", cwd=str(e2e))
    git("checkout", "-qb", "orch/cli-20260905-999999-xyz", cwd=str(e2e))
    git("checkout", "-q", "main", cwd=str(e2e))


def test_check_detects_residue(fixture_env):
    pollute(fixture_env["e2e"])
    r = run_script("--check", "--no-remote")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "RESIDUE" in r.stdout


def test_reset_restores_known_clean(fixture_env):
    pollute(fixture_env["e2e"])
    r = run_script("--no-remote")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CLEAN" in r.stdout
    e2e = str(fixture_env["e2e"])
    assert git("status", "--porcelain", cwd=e2e).stdout.strip() == ""
    assert git("symbolic-ref", "--short", "-q", "HEAD", cwd=e2e).stdout.strip() == "main"
    assert residue_types(fixture_env["e2e"]) == set()
    # seed content back, agent debris gone
    assert "def add" in (fixture_env["e2e"] / "calc.py").read_text()
    assert not (fixture_env["e2e"] / ".graft").exists()


def test_reset_repairs_detached_head_and_drift(fixture_env):
    e2e = str(fixture_env["e2e"])
    git("checkout", "-q", "--detach", "HEAD", cwd=e2e)
    git("commit", "-qam", "drift", cwd=e2e)
    r = run_script("--no-remote")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git("symbolic-ref", "--short", "-q", "HEAD", cwd=e2e).stdout.strip() == "main"
    assert git("rev-parse", "--short", "HEAD", cwd=e2e).stdout.strip() == git(
        "rev-parse", "--short", "origin/main", cwd=e2e
    ).stdout.strip()


def test_recreate_reclones_when_missing(fixture_env):
    shutil.rmtree(fixture_env["e2e"])
    r = run_script("--recreate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (fixture_env["e2e"] / "calc.py").exists()
    assert run_script("--check").returncode == 0


def test_reseed_rotates_seed(fixture_env):
    r = run_script("--reseed", "--no-remote")
    assert r.returncode == 0, r.stdout + r.stderr
    e2e = str(fixture_env["e2e"])
    seed = git("rev-parse", "--short", "HEAD", cwd=e2e).stdout.strip()
    assert git("log", "--oneline", cwd=e2e).stdout.strip().splitlines() == [git("log", "--format=%h %s", "-1", cwd=e2e).stdout.strip()]  # fresh history
    # subsequent reset lands on the new seed, not the old origin/main
    git("commit", "-q", "--allow-empty", "-m", "drift", cwd=e2e)
    assert run_script("--no-remote").returncode == 0
    assert git("rev-parse", "--short", "HEAD", cwd=e2e).stdout.strip() == seed


def test_reseed_remote_force_push(fixture_env):
    r = run_script("--reseed", "--remote")
    assert r.returncode == 0, r.stdout + r.stderr
    origin_main = git("rev-parse", "--short", "refs/heads/main", cwd=str(fixture_env["origin"])).stdout.strip()
    assert origin_main == git("rev-parse", "--short", "HEAD", cwd=str(fixture_env["e2e"])).stdout.strip()


def test_remote_prune_deletes_stale_branches(fixture_env):
    e2e = str(fixture_env["e2e"])
    git("push", "-q", "origin", "HEAD:refs/heads/orch/stale-task", cwd=e2e)
    r = run_script("--remote")
    assert r.returncode == 0, r.stdout + r.stderr
    heads = git("for-each-ref", "refs/heads", cwd=str(fixture_env["origin"])).stdout
    assert "orch/stale-task" not in heads
    assert "main" in heads


def test_corrupt_head_repaired(fixture_env):
    (fixture_env["e2e"] / ".git" / "HEAD").write_text("garbage\n")
    r = run_script("--no-remote")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git("symbolic-ref", "--short", "-q", "HEAD", cwd=str(fixture_env["e2e"])).stdout.strip() == "main"


def test_check_clean_exit_zero(fixture_env):
    assert run_script("--check").returncode == 0
