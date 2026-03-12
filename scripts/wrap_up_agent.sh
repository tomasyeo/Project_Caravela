#!/usr/bin/env bash
# wrap_up_agent.sh — Commit agent output, merge to main, prep downstream worktree
#
# Usage:
#   ./scripts/wrap_up_agent.sh <agent_id>
#
# Run this AFTER you have reviewed the agent's output and are satisfied.
# This script:
#   1. Commits all changes in the agent's worktree
#   2. Merges the worktree branch into main
#   3. Pulls latest main into the next downstream worktree(s)
#
# Agent IDs:  1a  1b  1c  1d  2  3  4  5

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

pass()   { echo -e "  ${GREEN}✓${NC}  $1"; }
info()   { echo -e "  ${BLUE}→${NC}  $1"; }
warn()   { echo -e "  ${YELLOW}!${NC}  $1"; }
abort()  { echo -e "\n  ${RED}✗${NC}  $1\n"; exit 1; }
header() { echo -e "\n${BOLD}$1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

AGENT_ID="${1:-}"
[[ -z "$AGENT_ID" ]] && abort "Usage: ./scripts/wrap_up_agent.sh <agent_id>  (1a|1b|1c|1d|2|3|4|5)"

# ── Agent configuration ────────────────────────────────────────────────────────
case "$AGENT_ID" in
  1a) WORKTREE="agent-1"; LABEL="Agent 1a: Meltano configuration (meltano/meltano.yml)" ;;
  1b) WORKTREE="agent-1"; LABEL="Agent 1b: Staging models (9 models + sources.yml + dbt setup)" ;;
  1c) WORKTREE="agent-1"; LABEL="Agent 1c: Mart models (4 dims + 3 facts)" ;;
  1d) WORKTREE="agent-1"; LABEL="Agent 1d: dbt tests (schema.yml + singular tests, dbt build passes)" ;;
  2)  WORKTREE="agent-2"; LABEL="Agent 2: Platform Engineer — Dagster orchestration" ;;
  3)  WORKTREE="agent-3"; LABEL="Agent 3: Analytics Engineer — notebooks + Parquet exports" ;;
  4)  WORKTREE="agent-4"; LABEL="Agent 4: Dashboard Engineer — Streamlit dashboard" ;;
  5)  WORKTREE="agent-5"; LABEL="Agent 5: Data Scientist — executive brief" ;;
  *)  abort "Unknown agent ID: $AGENT_ID. Valid: 1a 1b 1c 1d 2 3 4 5" ;;
esac

WORKTREE_PATH="$REPO_ROOT/worktrees/$WORKTREE"

echo -e "\n${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Wrap-up: Agent $AGENT_ID${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"

[[ -d "$WORKTREE_PATH" ]] || abort "Worktree not found: $WORKTREE_PATH — has the agent been launched?"

# ── Check for changes ──────────────────────────────────────────────────────────
header "Checking for changes"

cd "$WORKTREE_PATH"
CHANGES=$(git status --porcelain | wc -l | tr -d ' ')

if [[ "$CHANGES" -eq 0 ]]; then
  warn "No changes detected in worktree. Agent may not have produced output."
  echo ""
  read -rp "  Continue anyway? (y/N): " CONFIRM
  [[ "${CONFIRM:-n}" =~ ^[Yy]$ ]] || abort "Aborted."
else
  info "$CHANGES file(s) changed:"
  git status --short | head -20
  [[ "$CHANGES" -gt 20 ]] && info "... and $((CHANGES - 20)) more"
fi

# ── Confirm before committing ──────────────────────────────────────────────────
echo ""
echo -e "  ${YELLOW}Commit message:${NC}"
echo -e "  ${BOLD}$LABEL${NC}"
echo ""
read -rp "  Proceed with commit and merge? (y/N): " CONFIRM
[[ "${CONFIRM:-n}" =~ ^[Yy]$ ]] || abort "Aborted. No changes committed."

# ── Commit in worktree ─────────────────────────────────────────────────────────
header "Committing in worktree"

git add -A
git commit -m "$LABEL" \
  && pass "Committed: $LABEL" \
  || abort "git commit failed — check for issues in the worktree"

# ── Merge into main ────────────────────────────────────────────────────────────
header "Merging into main"

cd "$REPO_ROOT"
git merge "$WORKTREE_PATH" --no-edit \
  && pass "Merged worktrees/$WORKTREE → main" \
  || abort "git merge failed — resolve conflicts in $WORKTREE_PATH then re-run"

# ── Prep downstream worktrees ──────────────────────────────────────────────────
prep_worktree() {
  local next_worktree="$1"
  local next_path="$REPO_ROOT/worktrees/$next_worktree"
  if [[ -d "$next_path" ]]; then
    info "Pulling latest main into worktrees/$next_worktree..."
    git -C "$next_path" pull origin main --quiet \
      && pass "worktrees/$next_worktree is up to date" \
      || warn "git pull failed for worktrees/$next_worktree — check manually"
  else
    info "Creating worktrees/$next_worktree from main..."
    git worktree add "$next_path" main --quiet \
      && pass "worktrees/$next_worktree created" \
      || warn "Failed to create worktrees/$next_worktree — launch_agent.sh will retry"
  fi
}

header "Prepping downstream worktrees"

case "$AGENT_ID" in
  1a|1b|1c)
    info "Next: Agent $(echo $AGENT_ID | sed 's/1a/1b/;s/1b/1c/;s/1c/1d/') in same worktree (agent-1)"
    pass "No new worktree needed" ;;
  1d)
    info "Unlocking parallel Agents 2 and 3..."
    prep_worktree "agent-2"
    prep_worktree "agent-3" ;;
  2)
    info "Agent 2 has no downstream dependency — Agent 4 waits for Agent 3."
    pass "No worktree prep needed" ;;
  3)
    prep_worktree "agent-4" ;;
  4)
    prep_worktree "agent-5" ;;
  5)
    pass "Agent 5 is the final agent — no downstream worktrees" ;;
esac

# ── Next step hint ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Agent $AGENT_ID wrapped up successfully.${NC}"

case "$AGENT_ID" in
  1a) echo -e "  Next: ${BOLD}./scripts/launch_agent.sh 1b${NC}" ;;
  1b) echo -e "  Next: ${BOLD}./scripts/launch_agent.sh 1c${NC}" ;;
  1c) echo -e "  Next: ${BOLD}./scripts/launch_agent.sh 1d${NC}" ;;
  1d) echo -e "  Next (parallel — open two terminals):"
      echo -e "    Terminal 1: ${BOLD}./scripts/launch_agent.sh 2${NC}"
      echo -e "    Terminal 2: ${BOLD}./scripts/launch_agent.sh 3${NC}" ;;
  2)  echo -e "  Waiting for Agent 3. When Agent 3 wraps up, run Agent 4." ;;
  3)  echo -e "  Next: ${BOLD}./scripts/launch_agent.sh 4${NC}" ;;
  4)  echo -e "  Next: ${BOLD}./scripts/launch_agent.sh 5${NC}" ;;
  5)  echo -e "  Pipeline complete. Run: ${BOLD}./scripts/final_cleanup.sh${NC}" ;;
esac

echo -e "${BOLD}════════════════════════════════════════════════════${NC}\n"
