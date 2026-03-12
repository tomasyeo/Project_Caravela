#!/usr/bin/env bash
# final_cleanup.sh — Remove worktrees and print pipeline summary
#
# Usage:
#   ./scripts/final_cleanup.sh
#
# Run after all 8 agents are wrapped up and you are satisfied with the output.
# This script removes all worktrees and prints a summary of what was produced.

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

pass()   { echo -e "  ${GREEN}✓${NC}  $1"; }
info()   { echo -e "  ${BLUE}→${NC}  $1"; }
warn()   { echo -e "  ${YELLOW}!${NC}  $1"; }
header() { echo -e "\n${BOLD}$1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo -e "\n${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Project Caravela — Final Cleanup${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"

# ── Confirm all agents wrapped up ─────────────────────────────────────────────
header "Checking agent commits on main"

MISSING=0
for AGENT_LABEL in "Agent 1a" "Agent 1b" "Agent 1c" "Agent 1d" "Agent 2" "Agent 3" "Agent 4" "Agent 5"; do
  if git log --oneline | grep -q "$AGENT_LABEL"; then
    pass "$AGENT_LABEL committed"
  else
    warn "$AGENT_LABEL — no commit found on main"
    MISSING=$((MISSING+1))
  fi
done

if [[ $MISSING -gt 0 ]]; then
  echo ""
  read -rp "  $MISSING agent(s) not found in git log. Continue anyway? (y/N): " CONFIRM
  [[ "${CONFIRM:-n}" =~ ^[Yy]$ ]] || { echo "  Aborted."; exit 1; }
fi

# ── Remove worktrees ───────────────────────────────────────────────────────────
header "Removing worktrees"

for WT in agent-1 agent-2 agent-3 agent-4 agent-5; do
  WT_PATH="$REPO_ROOT/worktrees/$WT"
  if [[ -d "$WT_PATH" ]]; then
    if git worktree remove "$WT_PATH" --force 2>/dev/null; then
      pass "Removed worktrees/$WT"
    else
      warn "Could not remove worktrees/$WT automatically — remove manually if needed"
    fi
  else
    info "worktrees/$WT — not present, skipping"
  fi
done

# ── Deliverables check ────────────────────────────────────────────────────────
header "Deliverables Checklist"

check_file() {
  local path="$1"; local label="$2"
  [[ -f "$path" ]] && pass "$label" || warn "MISSING: $label ($path)"
}

check_dir_count() {
  local dir="$1"; local pattern="$2"; local expected="$3"; local label="$4"
  local count; count=$(find "$dir" -name "$pattern" 2>/dev/null | wc -l | tr -d ' ')
  [[ "$count" -ge "$expected" ]] \
    && pass "$label ($count found)" \
    || warn "MISSING: $label (expected $expected, found $count)"
}

echo -e "\n  ${BLUE}Meltano${NC}"
check_file "meltano/meltano.yml" "meltano/meltano.yml"

echo -e "\n  ${BLUE}dbt${NC}"
check_file "dbt/dbt_project.yml"     "dbt/dbt_project.yml"
check_file "dbt/packages.yml"        "dbt/packages.yml"
check_file "dbt/models/sources.yml"  "dbt/models/sources.yml"
check_dir_count "dbt/models/staging" "stg_*.sql" 9 "9 staging models"
check_dir_count "dbt/models/marts"   "*.sql"      7 "7 mart models"
check_file "dbt/models/staging/schema.yml" "dbt/models/staging/schema.yml"
check_file "dbt/models/marts/schema.yml"   "dbt/models/marts/schema.yml"
check_dir_count "dbt/tests" "*.sql" 3 "3 singular tests"

echo -e "\n  ${BLUE}Dagster${NC}"
check_file "dagster/dagster_project/__init__.py" "dagster/__init__.py"
check_file "dagster/dagster_project/assets.py"   "dagster/assets.py"
check_file "dagster/dagster_project/schedules.py" "dagster/schedules.py"
check_file "dagster/pyproject.toml"              "dagster/pyproject.toml"

echo -e "\n  ${BLUE}Notebooks${NC}"
check_file "notebooks/utils.py"                       "notebooks/utils.py"
check_file "notebooks/00_eda.ipynb"                   "notebooks/00_eda.ipynb"
check_file "notebooks/01_sales_analysis.ipynb"        "notebooks/01_sales_analysis.ipynb"
check_file "notebooks/02_customer_analysis.ipynb"     "notebooks/02_customer_analysis.ipynb"
check_file "notebooks/03_geo_seller_analysis.ipynb"   "notebooks/03_geo_seller_analysis.ipynb"

echo -e "\n  ${BLUE}Parquet files${NC}"
for f in sales_orders customer_rfm satisfaction_summary geo_delivery seller_performance; do
  check_file "data/${f}.parquet" "data/${f}.parquet"
done

echo -e "\n  ${BLUE}Dashboard${NC}"
check_file "dashboard.py"       "dashboard.py"
check_file "dashboard_utils.py" "dashboard_utils.py"
check_file "pages/1_Executive.py"  "pages/1_Executive.py"
check_file "pages/2_Products.py"   "pages/2_Products.py"
check_file "pages/3_Geographic.py" "pages/3_Geographic.py"
check_file "pages/4_Customers.py"  "pages/4_Customers.py"

echo -e "\n  ${BLUE}Documentation${NC}"
check_file "docs/executive_brief.md" "docs/executive_brief.md"

# ── Git log summary ────────────────────────────────────────────────────────────
header "Pipeline Commit History"
git log --oneline | head -15

# ── Push prompt ───────────────────────────────────────────────────────────────
echo ""
read -rp "  Push final state to GitHub? (y/N): " PUSH_CONFIRM
if [[ "${PUSH_CONFIRM:-n}" =~ ^[Yy]$ ]]; then
  git push origin main && pass "Pushed to origin/main"
fi

echo ""
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Pipeline complete.${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Run dashboard:   ${BOLD}streamlit run dashboard.py${NC}"
echo -e "  Run dbt docs:    ${BOLD}cd dbt && dbt docs generate && dbt docs serve${NC}"
echo -e "  Run Dagster UI:  ${BOLD}cd dbt && dbt parse && cd .. && dagster dev${NC}"
echo ""
