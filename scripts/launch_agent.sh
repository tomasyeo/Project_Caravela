#!/usr/bin/env bash
# launch_agent.sh — Launch a pipeline agent in interactive Claude Code session
#
# Usage:
#   ./scripts/launch_agent.sh <agent_id>
#
# Agent IDs:  1a  1b  1c  1d  2  3  4  5
#
# Examples:
#   ./scripts/launch_agent.sh 1a    # Meltano configuration
#   ./scripts/launch_agent.sh 1b    # Staging models
#   ./scripts/launch_agent.sh 2     # Platform Engineer (Dagster)
#
# The script creates/prepares the worktree, then launches an interactive
# Claude Code session with the agent's directive appended to the system prompt.
# When Claude exits, your terminal returns to normal.

set -euo pipefail

RED='\033[0;31m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()   { echo -e "  ${BLUE}→${NC}  $1"; }
warn()   { echo -e "  ${YELLOW}!${NC}  $1"; }
abort()  { echo -e "\n  ${RED}✗${NC}  $1\n"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

AGENT_ID="${1:-}"
[[ -z "$AGENT_ID" ]] && abort "Usage: ./scripts/launch_agent.sh <agent_id>  (1a|1b|1c|1d|2|3|4|5)"

# ── Agent configuration ────────────────────────────────────────────────────────
case "$AGENT_ID" in
  1a) DIRECTIVE="agent_1a_meltano.md";           MODEL="claude-opus-4-6";   WORKTREE="agent-1"; LABEL="Meltano Configuration" ;;
  1b) DIRECTIVE="agent_1b_staging.md";           MODEL="claude-opus-4-6";   WORKTREE="agent-1"; LABEL="Staging Models" ;;
  1c) DIRECTIVE="agent_1c_marts.md";             MODEL="claude-opus-4-6";   WORKTREE="agent-1"; LABEL="Mart Models" ;;
  1d) DIRECTIVE="agent_1d_testing.md";           MODEL="claude-opus-4-6";   WORKTREE="agent-1"; LABEL="dbt Tests" ;;
  2)  DIRECTIVE="agent_2_platform_engineer.md";  MODEL="claude-sonnet-4-6"; WORKTREE="agent-2"; LABEL="Platform Engineer (Dagster)" ;;
  3)  DIRECTIVE="agent_3_analytics_engineer.md"; MODEL="claude-opus-4-6";   WORKTREE="agent-3"; LABEL="Analytics Engineer (Notebooks)" ;;
  4)  DIRECTIVE="agent_4_dashboard_engineer.md"; MODEL="claude-sonnet-4-6"; WORKTREE="agent-4"; LABEL="Dashboard Engineer (Streamlit)" ;;
  5)  DIRECTIVE="agent_5_data_scientist.md";     MODEL="claude-opus-4-6";   WORKTREE="agent-5"; LABEL="Data Scientist (Executive Brief)" ;;
  *)  abort "Unknown agent ID: $AGENT_ID. Valid: 1a 1b 1c 1d 2 3 4 5" ;;
esac

DIRECTIVE_PATH="$REPO_ROOT/directives/$DIRECTIVE"
WORKTREE_PATH="$REPO_ROOT/worktrees/$WORKTREE"

echo -e "\n${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Agent $AGENT_ID — $LABEL${NC}"
echo -e "${BOLD}  Model: $MODEL${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════${NC}\n"

# ── Verify directive file exists ───────────────────────────────────────────────
[[ -f "$DIRECTIVE_PATH" ]] || abort "Directive file not found: $DIRECTIVE_PATH"
info "Directive: directives/$DIRECTIVE"

# ── Verify prerequisite agents are wrapped up ──────────────────────────────────
check_agent_committed() {
  local agent_label="$1"
  local count
  count=$(git -C "$REPO_ROOT" log --oneline --grep="$agent_label" | wc -l | tr -d ' ')
  [[ "$count" -gt 0 ]] \
    || abort "$agent_label does not appear committed to main yet. Run wrap_up_agent.sh first."
}

case "$AGENT_ID" in
  1b) check_agent_committed "Agent 1a" ;;
  1c) check_agent_committed "Agent 1b" ;;
  1d) check_agent_committed "Agent 1c" ;;
  2|3) check_agent_committed "Agent 1d" ;;
  4)  check_agent_committed "Agent 3" ;;
  5)  check_agent_committed "Agent 4" ;;
esac

# ── Worktree setup ─────────────────────────────────────────────────────────────
if [[ -d "$WORKTREE_PATH" ]]; then
  info "Worktree exists — syncing to latest main..."
  git -C "$WORKTREE_PATH" reset --hard main --quiet \
    || warn "git reset failed — worktree may have uncommitted changes. Continuing."
else
  info "Creating worktree at worktrees/$WORKTREE..."
  git -C "$REPO_ROOT" worktree add --detach "$WORKTREE_PATH" --quiet
  info "Worktree created."
fi

# ── Summary before launch ──────────────────────────────────────────────────────
echo ""
info "Worktree:  worktrees/$WORKTREE"
info "Directive: directives/$DIRECTIVE"
info "Model:     $MODEL"
echo ""
echo -e "  ${YELLOW}Starting interactive Claude session. Press Ctrl+C to exit.${NC}"
echo -e "  ${YELLOW}Run wrap_up_agent.sh $AGENT_ID when satisfied with the output.${NC}"
echo ""

# ── Launch ─────────────────────────────────────────────────────────────────────
cd "$WORKTREE_PATH"
exec claude \
  --model "$MODEL" \
  --append-system-prompt-file "$DIRECTIVE_PATH"
