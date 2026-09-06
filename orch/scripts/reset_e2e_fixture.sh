#!/usr/bin/env bash
# reset_e2e_fixture.sh — reset the orch e2e fixture repo to a known-clean main.
#
# Every e2e run leaves residue behind: agent task branches, .graft/ metadata,
# __pycache__, drifted commits, even detached/corrupt HEAD states. This script
# makes every e2e start from the same seed commit instead of accumulating it.
#
# Usage:
#   scripts/reset_e2e_fixture.sh [options] [REPO_DIR]
#
# Modes (default: reset):
#   (default)      Clean REPO_DIR: hard-reset main to the seed commit, wipe
#                  untracked/ignored residue, delete non-main local branches.
#   --check        Verify only — exit 0 if clean, 1 if residue remains.
#   --recreate     REPO_DIR missing or broken? Re-clone it from the remote.
#   --reseed       After cleaning, rewrite main as a fresh single-commit
#                  "init" from the current template content (rotates the
#                  seed; combined with --remote it force-pushes, rewriting
#                  origin/main — review before using).
#   --remote       Also prune stale origin branches and force-push main if
#                  origin/main drifted from the seed (network + force push).
#   --no-remote    Skip all origin contact (offline repair; only works when
#                  the seed commit already exists locally).
#
# Environment overrides (positional REPO_DIR wins over ORCH_E2E_DIR):
#   ORCH_E2E_DIR     fixture path           (default /tmp/orch-e2e)
#   ORCH_E2E_REMOTE  GitHub <owner>/<repo>, or a local path/URL (tests use
#                    a local bare origin; anything with / or :// clones as-is)
#
# The seed is discovered from origin/main after fetch; the reseed flow records
# it in SEED file. Origin must contain the canonical clean main.

set -euo pipefail

MODE="reset"
REMOTE_MODE="fetch" # fetch | skip | push
REPO=""
for arg in "$@"; do
  case "$arg" in
    --check)    MODE="check" ;;
    --recreate) MODE="recreate" ;;
    --reseed)   MODE="reseed" ;;
    --remote)   REMOTE_MODE="push" ;;
    --no-remote) REMOTE_MODE="skip" ;;
    -h|--help)  awk 'NR>1 && !/^#/ {exit} NR>1 {print}' "$0"; exit 0 ;;
    -*)         echo "unknown option: $arg (see --help)" >&2; exit 2 ;;
    *)          REPO="$arg" ;;
  esac
done
REPO="${REPO:-${ORCH_E2E_DIR:-/tmp/orch-e2e}}"
GH_REMOTE="${ORCH_E2E_REMOTE:-haejoonlim/orch-e2e-fixture}"
SEED_FILE=".orch-e2e-seed"

say()  { printf '%s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

git_in() { git -C "$REPO" "$@"; }
# Git plumbing that is *expected* to fail on broken states must not trip set -e.
ok() { "$@" >/dev/null 2>&1; }

clone_fresh() {
  case "$GH_REMOTE" in
    /*|file://*|*://*) CLONE_URL="$GH_REMOTE" ;;
    *)                 CLONE_URL="https://github.com/$GH_REMOTE.git" ;;
  esac
  say "recreate: cloning $CLONE_URL → $REPO"
  rm -rf "$REPO"
  ok git clone -q "$CLONE_URL" "$REPO" \
    || die "clone failed (gh auth? repo exists?)"
}

# Resolve the seed commit: recorded → origin/main → local main.
resolve_seed() {
  if [ -f "$REPO/$SEED_FILE" ]; then
    SEED=$(cat "$REPO/$SEED_FILE")
    ok git_in rev-parse --verify -q "$SEED^{commit}" && return 0 \
      || warn "recorded seed $SEED is gone locally; re-discovering"
  fi
  if [ "$REMOTE_MODE" != "skip" ] && ok git_in fetch -q origin; then
    SEED=$(git_in rev-parse --short origin/main 2>/dev/null || true)
    [ -n "$SEED" ] && return 0
  fi
  SEED=$(git_in rev-parse --short main 2>/dev/null || true)
  [ -n "$SEED" ] || die "no seed: origin unreachable and no local main in $REPO"
  warn "using local main $SEED as seed (origin unavailable — verify it is clean)"
}

# Clean the worktree and branch state back to the seed.
clean_to_seed() {
  resolve_seed
  # Repair corrupt HEAD, then force main back to the seed. -B also recovers
  # from detached HEAD / orphan checkout in one step.
  if ! ok git_in checkout -q -f -B main "$SEED"; then
    printf 'ref: refs/heads/main\n' > "$REPO/.git/HEAD"
    git_in checkout -q -f -B main "$SEED"
  fi
  git_in clean -qfdx # .graft/, __pycache__, build output — all of it
  while IFS= read -r branch; do
    [ "$branch" = "main" ] && continue
    git_in branch -q -D "$branch"
  done < <(git_in for-each-ref --format='%(refname:short)' refs/heads/)
  if [ "$REMOTE_MODE" = "push" ]; then
    while IFS= read -r rbranch; do
      case "$rbranch" in origin/HEAD|origin/main) continue ;; esac
      say "remote: pruning $rbranch"
      git_in push -q origin --delete "${rbranch#origin/}" || warn "could not delete $rbranch"
    done < <(git_in for-each-ref --format='%(refname:short)' refs/remotes/origin 2>/dev/null || true)
  else
    ok git_in fetch -q --prune origin || true
  fi
  printf '%s\n' "$SEED" > "$REPO/$SEED_FILE"
  # The marker must not read as residue on the next --check.
  mkdir -p "$REPO/.git/info"
  grep -qxF "$SEED_FILE" "$REPO/.git/info/exclude" 2>/dev/null \
    || printf '%s\n' "$SEED_FILE" >> "$REPO/.git/info/exclude"
}

# True (exit 0) when the fixture is known-clean: on the seed, on main,
# worktree matching the seed, and main is the only local branch.
is_clean() {
  [ "$(git_in rev-parse --short HEAD)" = "$SEED" ] || return 1
  [ -z "$(git_in status --porcelain)" ] || return 1
  [ "$(git_in symbolic-ref --short -q HEAD)" = "main" ] || return 1
  [ "$(git_in for-each-ref refs/heads | wc -l | tr -d ' ')" = "1" ] || return 1
  return 0
}

case "$MODE" in
  check)
    ok git_in rev-parse --git-dir || { say "MISSING (no repo)"; exit 1; }
    resolve_seed
    if is_clean; then say "CLEAN  $REPO @ $SEED"; exit 0; fi
    say "RESIDUE $REPO — HEAD $(git_in rev-parse --short HEAD) (seed $SEED), $(git_in status --porcelain | wc -l | tr -d ' ') dirty paths, $(git_in for-each-ref refs/heads | wc -l | tr -d ' ') branches"
    exit 1
    ;;
  recreate)
    ok git_in rev-parse --git-dir && warn "$REPO exists; recreating anyway" || true
    clone_fresh
    clean_to_seed
    ;;
  reset)
    ok git_in rev-parse --git-dir || { warn "$REPO missing — falling back to clone"; clone_fresh; }
    clean_to_seed
    ;;
  reseed)
    clean_to_seed
    # Fresh single-commit root from the clean worktree — not an empty commit
    # stacked on the old history.
    git_in checkout -q --orphan fresh-seed
    git_in add -A
    git_in commit -qm "init" --allow-empty
    git_in branch -q -M main
    SEED=$(git_in rev-parse --short HEAD)
    printf '%s\n' "$SEED" > "$REPO/$SEED_FILE"
    if [ "$REMOTE_MODE" = "push" ]; then
      say "remote: force-pushing new seed $SEED to origin/main (history rewrite)"
      git_in push -q -f origin main
    else
      warn "new seed $SEED exists locally only; combine with --remote to publish it"
    fi
    ;;
esac

if is_clean; then
  say "CLEAN  $REPO @ $SEED (main, worktree matches seed)"
else
  die "residue remains after reset — inspect $REPO manually"
fi

# origin/main drifted from the seed means the upstream template changed:
# resetting locally to an older seed would diverge every future e2e.
# (After --reseed a difference is expected — the new seed is local-only
# until --remote publishes it.)
if [ "$MODE" != "reseed" ] && [ "$REMOTE_MODE" != "skip" ] && ok git_in rev-parse -q --verify origin/main; then
  if [ "$(git_in rev-parse origin/main)" != "$(git_in rev-parse "$SEED")" ]; then
    warn "origin/main ($(git_in rev-parse --short origin/main)) != seed $SEED — fixture template changed upstream; review before resetting again"
  fi
fi
