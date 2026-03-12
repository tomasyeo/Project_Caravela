#!/usr/bin/env bash
# precheck.sh — Project Caravela pipeline pre-flight check
#
# Usage:
#   ./scripts/precheck.sh [--create-datasets] [--project ID] [--credentials PATH]
#
# Options:
#   --project         GCP project ID (or set GCP_PROJECT_ID env var)
#   --credentials     Path to service account JSON key (or set GOOGLE_APPLICATION_CREDENTIALS)
#   --create-datasets Create olist_raw and olist_analytics datasets if missing

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

pass()   { echo -e "  ${GREEN}✓${NC}  $1"; }
fail()   { echo -e "  ${RED}✗${NC}  $1"; FAILED=$((FAILED+1)); }
warn()   { echo -e "  ${YELLOW}!${NC}  $1"; }
info()   { echo -e "  ${BLUE}→${NC}  $1"; }
header() { echo -e "\n${BOLD}$1${NC}"; }

FAILED=0
CREATE_DATASETS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)       export GCP_PROJECT_ID="$2"; shift 2 ;;
    --credentials)   export GOOGLE_APPLICATION_CREDENTIALS="$2"; shift 2 ;;
    --create-datasets) CREATE_DATASETS=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo -e "\n${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Project Caravela — Pre-flight Check${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
info "Repo: $REPO_ROOT"

# ── CLI tools ──────────────────────────────────────────────────────────────────
header "CLI Tools"

command -v claude &>/dev/null \
  && pass "claude CLI found" \
  || fail "claude not found — install Claude Code"

command -v bq &>/dev/null \
  && pass "bq (BigQuery CLI) found" \
  || fail "bq not found — install Google Cloud SDK"

command -v git &>/dev/null \
  && pass "git found" \
  || fail "git not found"

command -v dbt &>/dev/null \
  && pass "dbt found ($(dbt --version 2>/dev/null | head -1))" \
  || fail "dbt not found — run: conda activate assignment2"

command -v meltano &>/dev/null \
  && pass "meltano found" \
  || warn "meltano not found in PATH — may need: conda activate assignment2"

# ── Credentials ────────────────────────────────────────────────────────────────
header "Credentials & Environment"

if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
  fail "GOOGLE_APPLICATION_CREDENTIALS is not set"
elif [[ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]]; then
  fail "GOOGLE_APPLICATION_CREDENTIALS set but file not found: $GOOGLE_APPLICATION_CREDENTIALS"
else
  pass "GOOGLE_APPLICATION_CREDENTIALS → $GOOGLE_APPLICATION_CREDENTIALS"
fi

if [[ -z "${GCP_PROJECT_ID:-}" ]]; then
  fail "GCP_PROJECT_ID is not set"
else
  pass "GCP_PROJECT_ID → $GCP_PROJECT_ID"
fi

# ── BigQuery datasets ──────────────────────────────────────────────────────────
header "BigQuery Datasets"

if [[ $FAILED -gt 0 ]]; then
  warn "Skipping BigQuery checks — credentials not verified"
else
  for DATASET in olist_raw olist_analytics; do
    if bq show "${GCP_PROJECT_ID}:${DATASET}" &>/dev/null; then
      pass "${GCP_PROJECT_ID}:${DATASET} exists"
    elif [[ "$CREATE_DATASETS" == "true" ]]; then
      warn "${DATASET} not found — creating..."
      bq mk --dataset "${GCP_PROJECT_ID}:${DATASET}" \
        && pass "${GCP_PROJECT_ID}:${DATASET} created" \
        || fail "Failed to create ${DATASET}"
    else
      fail "${GCP_PROJECT_ID}:${DATASET} not found  (add --create-datasets to auto-create)"
    fi
  done
fi

# ── Source data ────────────────────────────────────────────────────────────────
header "Source Data"

CSV_COUNT=$(ls raw_data/*.csv 2>/dev/null | wc -l | tr -d ' ')
if [[ "$CSV_COUNT" -eq 9 ]]; then
  pass "9 source CSVs present in raw_data/"
  while IFS= read -r f; do info "$(basename "$f")"; done < <(ls raw_data/*.csv)
elif [[ "$CSV_COUNT" -gt 0 ]]; then
  fail "Expected 9 CSVs in raw_data/, found $CSV_COUNT"
else
  fail "No CSVs found in raw_data/"
fi

# ── Project structure ──────────────────────────────────────────────────────────
header "Project Structure"

DIRECTIVE_COUNT=$(ls directives/*.md 2>/dev/null | wc -l | tr -d ' ')
[[ "$DIRECTIVE_COUNT" -eq 9 ]] \
  && pass "9 directive files in directives/" \
  || fail "Expected 9 directive files, found $DIRECTIVE_COUNT"

for DIR in meltano dbt dagster notebooks data pages scripts; do
  [[ -d "$DIR" ]] && pass "$DIR/ directory exists" || fail "$DIR/ directory missing"
done

for FILE in dashboard.py dashboard_utils.py CLAUDE.md progress.md changelog.md; do
  [[ -f "$FILE" ]] && pass "$FILE exists" || fail "$FILE missing"
done

[[ -f "data/brazil_states.geojson" ]] \
  && pass "data/brazil_states.geojson exists" \
  || fail "data/brazil_states.geojson missing"

# ── dbt setup ─────────────────────────────────────────────────────────────────
header "dbt Setup"

[[ -f "dbt/packages.yml" ]] \
  && pass "dbt/packages.yml exists" \
  || fail "dbt/packages.yml missing — Agent 1b must create this"

if [[ -d "dbt/dbt_packages" ]]; then
  pass "dbt packages installed (dbt/dbt_packages/ exists)"
else
  warn "dbt packages not installed — run: cd dbt && dbt deps  (after Agent 1b completes)"
fi

if [[ -f "dbt/target/manifest.json" ]]; then
  pass "dbt/target/manifest.json exists (Dagster can start)"
else
  warn "dbt/target/manifest.json missing — run: cd dbt && dbt parse  (after Agent 1d completes)"
fi

# ── Runtime directories ────────────────────────────────────────────────────────
header "Runtime Directories"

mkdir -p logs worktrees
pass "logs/ ready"
pass "worktrees/ ready"

# ── Summary ────────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}════════════════════════════════════════════════════${NC}"
if [[ $FAILED -gt 0 ]]; then
  echo -e "${RED}${BOLD}  $FAILED check(s) failed. Resolve before starting.${NC}"
  echo -e "${BOLD}════════════════════════════════════════════════════${NC}\n"
  exit 1
else
  echo -e "${GREEN}${BOLD}  All checks passed. Ready to launch Agent 1a.${NC}"
  echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
  echo -e "\n  Next: ${BOLD}./scripts/launch_agent.sh 1a${NC}\n"
fi
