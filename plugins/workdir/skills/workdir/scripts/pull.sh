#!/usr/bin/env bash
# pull.sh — Plan and execute git pulls across all repos in a workdir workspace.
#
# Two-phase invocation (driven by the workdir skill's pull.md):
#   pull.sh             # Phase 1: fetch + plan. Emits preview table + saves plan TSV. No mutations beyond fetch.
#   pull.sh --execute   # Phase 2: read plan TSV, execute AUTO actions + strategy-based actions, print summary.
#
# Config (optional): <WORKDIR>/.workdir/pull.config.json
#   { "scanDepth": 2, "includeWorkspaceRoot": false,
#     "divergedStrategy": "rebase" | "merge" | "ask",
#     "dirtyOverlapStrategy": "stash" | "ask" | "skip",
#     "parallelism": 8 }

set -o pipefail
# Deliberately NO `set -e` (per-repo failures must be isolated) and NO `set -u` (empty assoc
# arrays + optional config keys cause spurious unbound-variable errors that would mask real bugs).

# Walk up from $(pwd) to locate the managed workspace (the directory containing a `.workdir/`
# or legacy `.init-workdir/` marker). Mirrors how git locates `.git/`. Refuses to run if no
# marker exists anywhere up the tree — prevents accidental scans of `~/` or unrelated dirs.
ORIG_PWD=$(pwd)
WORKDIR="$ORIG_PWD"
while [ "$WORKDIR" != "/" ] && [ ! -d "$WORKDIR/.workdir" ] && [ ! -d "$WORKDIR/.init-workdir" ]; do
  WORKDIR=$(dirname "$WORKDIR")
done
if [ "$WORKDIR" = "/" ]; then
  echo "ERROR: no .workdir/ marker found in any parent of $ORIG_PWD" >&2
  echo "       Run /workdir init <github|gitlab> from your workspace root first," >&2
  echo "       or cd into a managed workspace before invoking /workdir pull." >&2
  exit 1
fi
[ "$WORKDIR" != "$ORIG_PWD" ] && echo "Detected workdir: $WORKDIR (invoked from $ORIG_PWD)"

STATE_DIR="$WORKDIR/.workdir"
PLAN_FILE="$STATE_DIR/.pull-plan.tsv"
SUMMARY_FILE="$STATE_DIR/.pull-summary.tsv"
CONFIG="$STATE_DIR/pull.config.json"

# Defaults
SCAN_DEPTH=2
INCLUDE_WORKSPACE_ROOT=false
DIVERGED_STRATEGY=rebase
DIRTY_OVERLAP_STRATEGY=stash
PARALLELISM=8

# Auto-migrate legacy state dir (v1 .init-workdir/ → v2 .workdir/)
if [ -d "$WORKDIR/.init-workdir" ] && [ ! -d "$WORKDIR/.workdir" ]; then
  mv "$WORKDIR/.init-workdir" "$WORKDIR/.workdir"
fi

# Read config if present
if [ -f "$CONFIG" ]; then
  eval "$(python3 - "$CONFIG" <<'PY'
import json, sys, shlex
try:
    cfg = json.load(open(sys.argv[1]))
except Exception as e:
    print(f'echo "WARN: failed to parse pull.config.json: {e}" >&2')
    sys.exit(0)
mapping = {
    'scanDepth': 'SCAN_DEPTH',
    'includeWorkspaceRoot': 'INCLUDE_WORKSPACE_ROOT',
    'divergedStrategy': 'DIVERGED_STRATEGY',
    'dirtyOverlapStrategy': 'DIRTY_OVERLAP_STRATEGY',
    'parallelism': 'PARALLELISM',
}
for key, var in mapping.items():
    if key in cfg:
        val = cfg[key]
        if isinstance(val, bool):
            val = 'true' if val else 'false'
        print(f'{var}={shlex.quote(str(val))}')
PY
  )"
fi

# Parse args
MODE=plan
while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute) MODE=execute; shift ;;
    --dry-run) MODE=plan; shift ;;
    -h|--help)
      sed -n 's/^# \?//;/^[A-Z]/q;p' "$0" | sed -n '1,/^$/p'
      exit 0
      ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$STATE_DIR"
export GIT_TERMINAL_PROMPT=0

# ------------------------------------------------------------------------------
# Repo discovery
# ------------------------------------------------------------------------------
find_repos() {
  # Find every .git (file or directory) at depth 1..SCAN_DEPTH+1 under WORKDIR.
  # The repo root is the parent of .git.
  local mindepth=2
  local maxdepth=$((SCAN_DEPTH + 1))
  if [ "$INCLUDE_WORKSPACE_ROOT" = "true" ]; then
    mindepth=1
  fi
  find "$WORKDIR" -mindepth "$mindepth" -maxdepth "$maxdepth" -name ".git" \
       \( -type d -o -type f \) 2>/dev/null \
    | sed 's|/\.git$||' \
    | sort -u
}

# ------------------------------------------------------------------------------
# Per-repo probe — emits one TSV line
# ------------------------------------------------------------------------------
probe_repo() {
  local repo="$1"
  local rel="${repo#$WORKDIR/}"
  [ "$rel" = "$repo" ] && rel="."

  local branch upstream dirty untracked inprogress ahead behind submodules lfs stashes
  local gitdir

  branch=$(git -C "$repo" symbolic-ref --short HEAD 2>/dev/null || echo "DETACHED")
  upstream=$(git -C "$repo" rev-parse --abbrev-ref '@{u}' 2>/dev/null || echo "-")
  gitdir=$(git -C "$repo" rev-parse --absolute-git-dir 2>/dev/null || echo "")

  inprogress="-"
  if [ -n "$gitdir" ]; then
    [ -f "$gitdir/MERGE_HEAD" ] && inprogress="merge"
    if [ -d "$gitdir/rebase-merge" ] || [ -d "$gitdir/rebase-apply" ]; then
      inprogress="rebase"
    fi
    [ -f "$gitdir/CHERRY_PICK_HEAD" ] && inprogress="cherry-pick"
  fi

  if [ -n "$(git -C "$repo" status --porcelain=v1 -uno 2>/dev/null)" ]; then
    dirty="dirty"
  else
    dirty="clean"
  fi
  untracked=$(git -C "$repo" status --porcelain=v1 2>/dev/null | grep -c '^??' || true)

  ahead=0; behind=0
  if [ "$upstream" != "-" ] && [ "$branch" != "DETACHED" ]; then
    # `HEAD...UPSTREAM` --left-right --count → "<ahead>\t<behind>"
    local counts
    counts=$(git -C "$repo" rev-list --left-right --count "HEAD...$upstream" 2>/dev/null)
    if [ -n "$counts" ]; then
      ahead=$(echo "$counts" | awk '{print $1+0}')
      behind=$(echo "$counts" | awk '{print $2+0}')
    fi
  fi

  [ -f "$repo/.gitmodules" ] && submodules="yes" || submodules="no"
  if [ -f "$repo/.gitattributes" ] && grep -q 'filter=lfs' "$repo/.gitattributes" 2>/dev/null; then
    lfs="yes"
  else
    lfs="no"
  fi
  stashes=$(git -C "$repo" stash list 2>/dev/null | wc -l | tr -d ' ')

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$rel" "$branch" "$upstream" "$ahead" "$behind" "$dirty" "$untracked" "$inprogress" "$submodules" "$lfs" "$stashes"
}

# ------------------------------------------------------------------------------
# Fetch (parallel) — runs in a subshell-friendly way
# ------------------------------------------------------------------------------
fetch_repo() {
  local repo="$1"
  local rel="${repo#$WORKDIR/}"
  local out rc
  out=$(git -C "$repo" fetch --prune --quiet 2>&1)
  rc=$?
  if [ $rc -ne 0 ]; then
    # Avoid concurrent-write hazards by using one file per repo.
    local safe
    safe=$(echo "$rel" | tr '/ ' '__')
    printf '%s' "$out" | tr '\n' ' ' | cut -c1-200 > "$FAIL_DIR/$safe.err"
    echo "$rel" >> "$FAIL_DIR/.failed-list"
  fi
}
export -f fetch_repo
export WORKDIR FAIL_DIR

# ------------------------------------------------------------------------------
# Bucket categorization
# Reads a TSV probe line, prints a bucket name + planned action.
# ------------------------------------------------------------------------------
categorize() {
  local rel="$1" branch="$2" upstream="$3" ahead="$4" behind="$5" dirty="$6" inprogress="$7"
  local fetchfail="$8"   # "yes" or "no"

  if [ "$fetchfail" = "yes" ]; then
    echo "SKIP-fetchfail|fetch failed — see error above"
    return
  fi
  if [ "$inprogress" != "-" ]; then
    echo "SKIP-inprogress|active $inprogress — resolve manually"
    return
  fi
  if [ "$branch" = "DETACHED" ]; then
    echo "SKIP-noremote|detached HEAD"
    return
  fi
  if [ "$upstream" = "-" ] || [ -z "$upstream" ]; then
    echo "SKIP-noremote|no upstream for branch '$branch'"
    return
  fi
  if [ "$ahead" = "0" ] && [ "$behind" = "0" ]; then
    if [ "$dirty" = "dirty" ]; then
      echo "OK-uptodate|up-to-date (working tree dirty)"
    else
      echo "OK-uptodate|already up-to-date"
    fi
    return
  fi
  if [ "$behind" = "0" ]; then
    echo "NOOP-ahead|$ahead unpushed commit(s); nothing to pull"
    return
  fi
  if [ "$dirty" = "clean" ]; then
    if [ "$ahead" = "0" ]; then
      echo "AUTO-ff|git pull --ff-only"
    else
      case "$DIVERGED_STRATEGY" in
        rebase) echo "ASK-diverged|git pull --rebase ($ahead ahead, $behind behind)" ;;
        merge)  echo "ASK-diverged|git pull --no-rebase ($ahead ahead, $behind behind)" ;;
        ask)    echo "ASK-diverged|needs decision ($ahead ahead, $behind behind)" ;;
      esac
    fi
    return
  fi
  # dirty + something to pull
  case "$DIRTY_OVERLAP_STRATEGY" in
    stash)
      if [ "$ahead" = "0" ]; then
        echo "ASK-dirty|stash → pull --ff-only → pop"
      else
        case "$DIVERGED_STRATEGY" in
          rebase) echo "ASK-dirty|stash → pull --rebase → pop" ;;
          merge)  echo "ASK-dirty|stash → pull --no-rebase → pop" ;;
          ask)    echo "ASK-dirty|needs decision (dirty + diverged)" ;;
        esac
      fi
      ;;
    ask)  echo "ASK-dirty|needs decision (dirty + behind=$behind, ahead=$ahead)" ;;
    skip) echo "SKIP-dirty|skipping (config: dirtyOverlapStrategy=skip)" ;;
  esac
}

# ------------------------------------------------------------------------------
# Pretty preview
# ------------------------------------------------------------------------------
print_plan_table() {
  local plan="$1"
  echo ""
  echo "Workdir: $WORKDIR"
  local total
  total=$(wc -l < "$plan" | tr -d ' ')
  echo "Repos:   $total"
  echo ""
  printf '%-40s %-20s %-12s %-22s %s\n' "Repo" "Branch" "A/B" "Bucket" "Planned action"
  printf '%-40s %-20s %-12s %-22s %s\n' "$(printf -- '-%.0s' {1..40})" "$(printf -- '-%.0s' {1..20})" "$(printf -- '-%.0s' {1..12})" "$(printf -- '-%.0s' {1..22})" "$(printf -- '-%.0s' {1..30})"

  local has_ask=0 has_skip=0
  while IFS=$'\t' read -r rel branch upstream ahead behind dirty untracked inprogress submodules lfs stashes bucket action; do
    local ab="${ahead}/${behind}"
    [ "$dirty" = "dirty" ] && ab="${ab}*"
    printf '%-40s %-20s %-12s %-22s %s\n' "$rel" "$branch" "$ab" "$bucket" "$action"
    [[ "$bucket" == ASK-* ]] && has_ask=1
    [[ "$bucket" == SKIP-* ]] && has_skip=1
  done < "$plan"

  echo ""
  echo "Legend:  A/B = ahead/behind upstream; '*' = dirty working tree"
  echo "Strategy: divergedStrategy=$DIVERGED_STRATEGY  dirtyOverlapStrategy=$DIRTY_OVERLAP_STRATEGY"
  if [ $has_ask -eq 1 ] || [ $has_skip -eq 1 ]; then
    echo ""
    echo "Note: ASK-* and SKIP-* rows will be surfaced for review after --execute completes."
  fi
}

# ------------------------------------------------------------------------------
# Execute a single repo according to its planned bucket
# Emits one TSV outcome line: REL\tBUCKET\tOUTCOME\tDETAIL
# ------------------------------------------------------------------------------
execute_repo() {
  local rel="$1" branch="$2" upstream="$3" ahead="$4" behind="$5" dirty="$6" bucket="$7"
  local repo="$WORKDIR/$rel"
  [ "$rel" = "." ] && repo="$WORKDIR"

  local outcome="" detail=""
  case "$bucket" in
    OK-uptodate|NOOP-ahead|SKIP-inprogress|SKIP-noremote|SKIP-fetchfail|SKIP-dirty)
      outcome="skipped"
      detail="(no action)"
      ;;
    AUTO-ff)
      if git -C "$repo" pull --ff-only --quiet 2>&1 >/dev/null; then
        outcome="pulled"; detail="ff $behind commit(s)"
      else
        outcome="FAILED"; detail="git pull --ff-only failed"
      fi
      ;;
    ASK-diverged)
      case "$DIVERGED_STRATEGY" in
        rebase)
          if git -C "$repo" pull --rebase --quiet 2>&1 >/dev/null; then
            outcome="rebased"; detail="$behind pulled, $ahead replayed"
          else
            git -C "$repo" rebase --abort 2>/dev/null
            outcome="NEEDS-RESOLUTION"; detail="rebase conflicts; aborted"
          fi
          ;;
        merge)
          if git -C "$repo" pull --no-rebase --quiet 2>&1 >/dev/null; then
            outcome="merged"; detail="$behind pulled into local"
          else
            git -C "$repo" merge --abort 2>/dev/null
            outcome="NEEDS-RESOLUTION"; detail="merge conflicts; aborted"
          fi
          ;;
        ask)
          outcome="NEEDS-DECISION"; detail="divergedStrategy=ask"
          ;;
      esac
      ;;
    ASK-dirty)
      case "$DIRTY_OVERLAP_STRATEGY" in
        stash)
          local stash_msg="workdir-pull-$(date -u +%Y%m%dT%H%M%SZ)"
          if ! git -C "$repo" stash push --include-untracked -m "$stash_msg" --quiet 2>/dev/null; then
            outcome="NEEDS-DECISION"; detail="stash push failed"
          else
            # Pull according to diverged state
            local pull_ok=0
            if [ "$ahead" = "0" ]; then
              git -C "$repo" pull --ff-only --quiet 2>&1 >/dev/null && pull_ok=1
            else
              case "$DIVERGED_STRATEGY" in
                rebase) git -C "$repo" pull --rebase --quiet 2>&1 >/dev/null && pull_ok=1 || git -C "$repo" rebase --abort 2>/dev/null ;;
                merge)  git -C "$repo" pull --no-rebase --quiet 2>&1 >/dev/null && pull_ok=1 || git -C "$repo" merge --abort 2>/dev/null ;;
                ask)    outcome="NEEDS-DECISION"; detail="divergedStrategy=ask; stash preserved as $stash_msg" ;;
              esac
            fi
            if [ $pull_ok -eq 1 ]; then
              # Try to pop. If conflict, leave stash and report.
              if git -C "$repo" stash pop --quiet 2>/dev/null; then
                outcome="pulled+restored"; detail="stashed/pulled/popped cleanly"
              else
                outcome="NEEDS-RESOLUTION"; detail="stash pop conflicts; stash preserved ($stash_msg)"
              fi
            else
              [ -z "$outcome" ] && { outcome="NEEDS-RESOLUTION"; detail="pull failed; stash preserved ($stash_msg)"; }
              # Restore working tree from stash
              git -C "$repo" stash pop --quiet 2>/dev/null || true
            fi
          fi
          ;;
        ask)
          outcome="NEEDS-DECISION"; detail="dirtyOverlapStrategy=ask"
          ;;
        skip)
          outcome="skipped"; detail="(dirtyOverlapStrategy=skip)"
          ;;
      esac
      ;;
    *)
      outcome="skipped"; detail="(unknown bucket $bucket)"
      ;;
  esac

  printf '%s\t%s\t%s\t%s\n' "$rel" "$bucket" "$outcome" "$detail"
}

# ------------------------------------------------------------------------------
# Pretty summary after execute
# ------------------------------------------------------------------------------
print_summary_table() {
  local sum="$1"
  echo ""
  echo "Pull summary:"
  echo ""
  printf '%-40s %-22s %-22s %s\n' "Repo" "Bucket" "Outcome" "Detail"
  printf '%-40s %-22s %-22s %s\n' "$(printf -- '-%.0s' {1..40})" "$(printf -- '-%.0s' {1..22})" "$(printf -- '-%.0s' {1..22})" "$(printf -- '-%.0s' {1..30})"
  while IFS=$'\t' read -r rel bucket outcome detail; do
    printf '%-40s %-22s %-22s %s\n' "$rel" "$bucket" "$outcome" "$detail"
  done < "$sum"
  echo ""
  # Counts
  local pulled rebased merged restored failed needs_dec needs_res
  pulled=$(awk -F'\t' '$3=="pulled"' "$sum" | wc -l | tr -d ' ')
  rebased=$(awk -F'\t' '$3=="rebased"' "$sum" | wc -l | tr -d ' ')
  merged=$(awk -F'\t' '$3=="merged"' "$sum" | wc -l | tr -d ' ')
  restored=$(awk -F'\t' '$3=="pulled+restored"' "$sum" | wc -l | tr -d ' ')
  failed=$(awk -F'\t' '$3=="FAILED"' "$sum" | wc -l | tr -d ' ')
  needs_dec=$(awk -F'\t' '$3=="NEEDS-DECISION"' "$sum" | wc -l | tr -d ' ')
  needs_res=$(awk -F'\t' '$3=="NEEDS-RESOLUTION"' "$sum" | wc -l | tr -d ' ')
  echo "Totals: $pulled ff-pulled, $rebased rebased, $merged merged, $restored stash-restored"
  if [ "$failed" -gt 0 ] || [ "$needs_dec" -gt 0 ] || [ "$needs_res" -gt 0 ]; then
    echo "        $failed FAILED, $needs_dec NEEDS-DECISION, $needs_res NEEDS-RESOLUTION"
    echo ""
    echo "Repos needing attention:"
    awk -F'\t' '$3=="FAILED" || $3=="NEEDS-DECISION" || $3=="NEEDS-RESOLUTION" {printf "  - %s [%s]: %s\n", $1, $3, $4}' "$sum"
  fi
}

# ==============================================================================
# MAIN
# ==============================================================================

if [ "$MODE" = "plan" ]; then
  echo "Discovering repos under $WORKDIR (depth $SCAN_DEPTH)..."
  mapfile -t REPOS < <(find_repos)
  if [ ${#REPOS[@]} -eq 0 ]; then
    echo "No git repositories found."
    exit 0
  fi
  echo "Found ${#REPOS[@]} repo(s). Fetching in parallel (-P $PARALLELISM)..."

  # Parallel fetch — each failure becomes a per-repo .err file under FAIL_DIR, plus an entry in
  # .failed-list (one rel per line). Concurrent appends to .failed-list are line-atomic for short writes.
  FAIL_DIR=$(mktemp -d)
  export FAIL_DIR
  : > "$FAIL_DIR/.failed-list"
  printf '%s\n' "${REPOS[@]}" | xargs -I {} -P "$PARALLELISM" bash -c 'fetch_repo "$@"' _ {}

  # Probe + categorize each repo, write plan TSV (USE '|' RECORD SEPARATOR — read with IFS=$'\t'
  # collapses consecutive tabs, which would drop empty fields and shift columns).
  : > "$PLAN_FILE"
  for repo in "${REPOS[@]}"; do
    line=$(probe_repo "$repo")
    # Use a non-whitespace separator to preserve empty fields. probe_repo uses '\t'; convert.
    IFS=$'\t' read -r rel branch upstream ahead behind dirty untracked inprogress submodules lfs stashes < <(printf '%s' "$line")
    # Defensive defaults in case any field got collapsed
    upstream="${upstream:--}"
    inprogress="${inprogress:--}"
    ahead="${ahead:-0}"
    behind="${behind:-0}"
    ff="no"
    if grep -Fxq "$rel" "$FAIL_DIR/.failed-list" 2>/dev/null; then
      ff="yes"
    fi
    bucketline=$(categorize "$rel" "$branch" "$upstream" "$ahead" "$behind" "$dirty" "$inprogress" "$ff")
    bucket="${bucketline%%|*}"
    action="${bucketline#*|}"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$rel" "$branch" "$upstream" "$ahead" "$behind" "$dirty" "$untracked" "$inprogress" "$submodules" "$lfs" "$stashes" \
      "$bucket" "$action" >> "$PLAN_FILE"
  done

  print_plan_table "$PLAN_FILE"

  # Report fetch failures distinctly (in addition to SKIP-fetchfail rows)
  if [ -s "$FAIL_DIR/.failed-list" ]; then
    echo ""
    echo "Fetch errors:"
    while IFS= read -r rel; do
      safe=$(echo "$rel" | tr '/ ' '__')
      echo "  - $rel: $(cat "$FAIL_DIR/$safe.err" 2>/dev/null)"
    done < "$FAIL_DIR/.failed-list"
  fi

  rm -rf "$FAIL_DIR"

  echo ""
  echo "Plan saved to: $PLAN_FILE"
  echo "To proceed:    bash $(realpath "$0") --execute"
  exit 0
fi

# ----- Execute mode -----
if [ ! -f "$PLAN_FILE" ]; then
  echo "ERROR: no plan found at $PLAN_FILE" >&2
  echo "Run pull.sh (without --execute) first to generate one." >&2
  exit 1
fi

: > "$SUMMARY_FILE"
while IFS=$'\t' read -r rel branch upstream ahead behind dirty untracked inprogress submodules lfs stashes bucket action _trail; do
  [ -z "$rel" ] && continue
  outcome=$(execute_repo "$rel" "$branch" "$upstream" "$ahead" "$behind" "$dirty" "$bucket")
  echo "$outcome" >> "$SUMMARY_FILE"
done < "$PLAN_FILE"

print_summary_table "$SUMMARY_FILE"
echo ""
echo "Summary saved to: $SUMMARY_FILE"
