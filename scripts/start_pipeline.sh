#!/usr/bin/env bash
# start_pipeline.sh — Project Caravela pipeline startup script
#
# Usage:
#   ./scripts/start_pipeline.sh [OPTIONS]
#
# Options:
#   --project      GCP project ID (or set GCP_PROJECT_ID env var)
#   --credentials  Path to service account JSON key (or set GOOGLE_APPLICATION_CREDENTIALS)
#   --create-datasets  Pre-create olist_raw and olist_analytics datasets if missing
#   --skip-agent   Run prerequisite checks only, do not spawn Agent 1a
#   --help         Show this help message
#
# Examples:
#   ./scripts/start_pipeline.sh --project my-gcp-project --credentials ~/keys/sa.json
#   ./scripts/start_pipeline.sh --project my-gcp-project --create-datasets
#   ./scripts/start_pipeline.sh --skip-agent   # prereq check only

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Colour

# ── Helpers ───────────────────────────────────────────────────────────────────
pass() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; FAILED=$((FAILED + 1)); }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
info() { echo -e "  ${BLUE}→${NC} $1"; }
header() { echo -e "\n${BOLD}$1${NC}"; }

FAILED=0
CREATE_DATASETS=false
SKIP_AGENT=false

# ── Parse arguments ────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      export GCP_PROJECT_ID="$2"; shift 2 ;;
    --credentials)
      export GOOGLE_APPLICATION_CREDENTIALS="$2"; shift 2 ;;
    --create-datasets)
      CREATE_DATASETS=true; shift ;;
    --skip-agent)
      SKIP_AGENT=true; shift ;;
    --help)
      sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *)
      echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Resolve repo root ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo -e "\n${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Project Caravela — Pipeline Startup${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
info "Repo root: $REPO_ROOT"

# ── PREREQUISITE CHECKS ────────────────────────────────────────────────────────
header "Prerequisite Check"

# P-01: GOOGLE_APPLICATION_CREDENTIALS set and file exists
if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
  fail "P-01: GOOGLE_APPLICATION_CREDENTIALS is not set"
elif [[ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]]; then
  fail "P-01: GOOGLE_APPLICATION_CREDENTIALS is set but file not found: $GOOGLE_APPLICATION_CREDENTIALS"
else
  pass "P-01: GOOGLE_APPLICATION_CREDENTIALS → $GOOGLE_APPLICATION_CREDENTIALS"
fi

# P-02: GCP_PROJECT_ID set
if [[ -z "${GCP_PROJECT_ID:-}" ]]; then
  fail "P-02: GCP_PROJECT_ID is not set"
else
  pass "P-02: GCP_PROJECT_ID → $GCP_PROJECT_ID"
fi

# P-03: BigQuery dataset olist_raw exists
if [[ $FAILED -eq 0 ]]; then
  if bq show "${GCP_PROJECT_ID}:olist_raw" &>/dev/null; then
    pass "P-03: BigQuery dataset olist_raw exists"
  elif [[ "$CREATE_DATASETS" == "true" ]]; then
    warn "P-03: olist_raw not found — creating..."
    if bq mk --dataset "${GCP_PROJECT_ID}:olist_raw"; then
      pass "P-03: BigQuery dataset olist_raw created"
    else
      fail "P-03: Failed to create olist_raw"
    fi
  else
    fail "P-03: BigQuery dataset olist_raw not found (run with --create-datasets to create)"
  fi
else
  warn "P-03: Skipped (credentials not verified)"
fi

# P-04: BigQuery dataset olist_analytics exists
if [[ $FAILED -eq 0 ]]; then
  if bq show "${GCP_PROJECT_ID}:olist_analytics" &>/dev/null; then
    pass "P-04: BigQuery dataset olist_analytics exists"
  elif [[ "$CREATE_DATASETS" == "true" ]]; then
    warn "P-04: olist_analytics not found — creating..."
    if bq mk --dataset "${GCP_PROJECT_ID}:olist_analytics"; then
      pass "P-04: BigQuery dataset olist_analytics created"
    else
      fail "P-04: Failed to create olist_analytics"
    fi
  else
    fail "P-04: BigQuery dataset olist_analytics not found (run with --create-datasets to create)"
  fi
else
  warn "P-04: Skipped (credentials not verified)"
fi

# P-05: All 9 source CSVs present in raw_data/
CSV_COUNT=$(ls raw_data/*.csv 2>/dev/null | wc -l | tr -d ' ')
if [[ "$CSV_COUNT" -eq 9 ]]; then
  pass "P-05: 9 source CSVs found in raw_data/"
elif [[ "$CSV_COUNT" -gt 0 ]]; then
  fail "P-05: Expected 9 CSVs in raw_data/, found $CSV_COUNT"
else
  fail "P-05: No CSVs found in raw_data/"
fi

# P-06: All 9 directive files present
DIRECTIVE_COUNT=$(ls directives/*.md 2>/dev/null | wc -l | tr -d ' ')
if [[ "$DIRECTIVE_COUNT" -eq 9 ]]; then
  pass "P-06: 9 directive files found in directives/"
else
  fail "P-06: Expected 9 directive files in directives/, found $DIRECTIVE_COUNT"
fi

# P-07: logs/ directory exists (create if not)
mkdir -p logs
pass "P-07: logs/ directory ready"

# ── Check claude CLI ───────────────────────────────────────────────────────────
if command -v claude &>/dev/null; then
  pass "CLI:  claude found ($(claude --version 2>/dev/null | head -1))"
else
  fail "CLI:  claude not found — install Claude Code first"
fi

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
if [[ $FAILED -gt 0 ]]; then
  echo -e "${RED}${BOLD}$FAILED prerequisite(s) failed. Resolve before proceeding.${NC}"
  exit 1
fi

echo -e "${GREEN}${BOLD}All prerequisites passed.${NC}"

if [[ "$SKIP_AGENT" == "true" ]]; then
  info "Skipping agent spawn (--skip-agent). Run without --skip-agent to start Agent 1a."
  exit 0
fi

# ── SPAWN AGENT 1a ─────────────────────────────────────────────────────────────
header "Spawning Agent 1a — Meltano Configuration"

WORKTREE_PATH="$REPO_ROOT/worktrees/agent-1"

if [[ -d "$WORKTREE_PATH" ]]; then
  warn "Worktree already exists at $WORKTREE_PATH"
  info "Pulling latest main into worktree..."
  git -C "$WORKTREE_PATH" pull origin main
else
  info "Creating worktree at $WORKTREE_PATH..."
  git worktree add "$WORKTREE_PATH" main
fi

info "Launching Agent 1a (claude-opus-4-6)..."
info "Output → logs/agent1a_output.json"
echo ""

cd "$WORKTREE_PATH"

claude -p \
  --model claude-opus-4-6 \
  --append-system-prompt-file "$REPO_ROOT/directives/agent_1a_meltano.md" \
  --output-format json \
  --dangerously-skip-permissions \
  "Execute your directive. Produce meltano/meltano.yml. Report structured status on completion." \
  > "$REPO_ROOT/logs/agent1a_output.json" 2>&1

EXIT_CODE=$?
cd "$REPO_ROOT"

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}Agent 1a completed (exit 0).${NC}"
else
  echo -e "${RED}${BOLD}Agent 1a exited with code $EXIT_CODE.${NC}"
fi

info "Parsing status from output..."
STATUS=$(python3 -c "
import json, sys
try:
    data = json.load(open('logs/agent1a_output.json'))
    result = data.get('result', '')
    # Find JSON block in result
    import re
    match = re.search(r'\{[^{}]*\"status\"[^{}]*\}', result, re.DOTALL)
    if match:
        inner = json.loads(match.group())
        print(inner.get('status', 'UNKNOWN'))
    else:
        print('UNKNOWN (no status JSON found in result)')
except Exception as e:
    print(f'PARSE_ERROR: {e}')
" 2>/dev/null)

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Agent 1a Status: $STATUS${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
echo ""

if [[ "$STATUS" == "DONE" ]]; then
  echo -e "${GREEN}Review logs/agent1a_output.json, then run Agent 1b:${NC}"
  echo ""
  echo "  cd worktrees/agent-1 && git pull && cd \"\$OLDPWD\""
  echo "  claude -p --model claude-opus-4-6 \\"
  echo "    --append-system-prompt-file directives/agent_1b_staging.md \\"
  echo "    --output-format json --dangerously-skip-permissions \\"
  echo "    \"Execute your directive. Produce all 9 staging models + sources.yml + dbt_project.yml + packages.yml.\" \\"
  echo "    > logs/agent1b_output.json 2>&1"
else
  echo -e "${YELLOW}Review logs/agent1a_output.json for details before retrying.${NC}"
  echo "  cat logs/agent1a_output.json | python3 -c \"import json,sys; d=json.load(sys.stdin); print(d.get('result',''))\""
fi

echo ""
