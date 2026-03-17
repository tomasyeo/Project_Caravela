#!/usr/bin/env bash
# launch_dagster.sh — Project Caravela Dagster launcher
#
# Usage (from repo root):
#   ./scripts/launch_dagster.sh [OPTIONS]
#
# Options:
#   --project      GCP project ID (overrides GCP_PROJECT_ID from .env)
#   --credentials  Path to service account JSON key (overrides GOOGLE_APPLICATION_CREDENTIALS from .env)
#   --parse        Force-run 'dbt parse' to regenerate manifest.json before starting
#   --host         Webserver host (default: 127.0.0.1)
#   --port         Webserver port (default: 3000)
#   --help         Show this help message
#
# Environment:
#   Automatically sources .env from repo root (if present).
#   Sets DAGSTER_HOME=<repo_root>/dagster/dagster_home (project-local state).
#   dagster/dagster_home/dagster.yaml activates EnvFileLoader for the Dagster process.
#
# Prerequisites:
#   conda activate assignment2   # must be active before running this script
#
# Examples:
#   ./scripts/launch_dagster.sh
#   ./scripts/launch_dagster.sh --project my-gcp-project --credentials ~/keys/sa.json
#   ./scripts/launch_dagster.sh --parse   # regenerate manifest first

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

pass()   { echo -e "  ${GREEN}✓${NC}  $1"; }
fail()   { echo -e "  ${RED}✗${NC}  $1"; FAILED=$((FAILED + 1)); }
warn()   { echo -e "  ${YELLOW}!${NC}  $1"; }
info()   { echo -e "  ${BLUE}→${NC}  $1"; }
header() { echo -e "\n${BOLD}$1${NC}"; }

FAILED=0
FORCE_PARSE=false
HOST="127.0.0.1"
PORT="3000"

# ── Resolve repo root early (needed for .env path before arg parsing) ─────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# ── Load .env first so CLI args can override individual vars ──────────────────
if [[ -f "$REPO_ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "$REPO_ROOT/.env"
  set +a
fi

# ── Set DAGSTER_HOME to project-local directory ───────────────────────────────
# Must be exported before `dagster dev` starts — Dagster reads dagster.yaml
# (which activates the EnvFileLoader) only after locating DAGSTER_HOME.
export DAGSTER_HOME="$REPO_ROOT/dagster/dagster_home"

# ── Parse arguments (after .env so CLI flags override .env values) ───────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)     export GCP_PROJECT_ID="$2"; shift 2 ;;
    --credentials) export GOOGLE_APPLICATION_CREDENTIALS="$2"; shift 2 ;;
    --parse)       FORCE_PARSE=true; shift ;;
    --host)        HOST="$2"; shift 2 ;;
    --port)        PORT="$2"; shift 2 ;;
    --help)
      sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "Unknown option: $1. Use --help for usage."; exit 1 ;;
  esac
done

echo -e "\n${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Project Caravela — Dagster Launcher${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
info "Repo root:  $REPO_ROOT"
info "Webserver:  http://${HOST}:${PORT}"

# ── PRE-FLIGHT CHECKS ─────────────────────────────────────────────────────────
header "Pre-flight Checks"

# C-01: dagster binary on PATH (conda env must be active)
if command -v dagster &>/dev/null; then
  pass "C-01: dagster found ($(dagster --version 2>/dev/null | head -1))"
else
  fail "C-01: dagster not found — run: conda activate assignment2"
fi

# C-02: dbt binary on PATH (needed for dbt parse if manifest is missing)
if command -v dbt &>/dev/null; then
  pass "C-02: dbt found ($(dbt --version 2>/dev/null | grep 'Core' | head -1 | tr -d ' '))"
else
  warn "C-02: dbt not found in PATH — manifest.json must already exist"
fi

# C-03: GOOGLE_APPLICATION_CREDENTIALS
if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
  fail "C-03: GOOGLE_APPLICATION_CREDENTIALS is not set"
elif [[ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]]; then
  fail "C-03: GOOGLE_APPLICATION_CREDENTIALS set but file not found: $GOOGLE_APPLICATION_CREDENTIALS"
else
  pass "C-03: GOOGLE_APPLICATION_CREDENTIALS → $GOOGLE_APPLICATION_CREDENTIALS"
fi

# C-04: GCP_PROJECT_ID
if [[ -z "${GCP_PROJECT_ID:-}" ]]; then
  fail "C-04: GCP_PROJECT_ID is not set"
else
  pass "C-04: GCP_PROJECT_ID → $GCP_PROJECT_ID"
fi

# C-05: dagster project structure
if [[ -f "$REPO_ROOT/dagster/pyproject.toml" ]]; then
  pass "C-05: dagster/pyproject.toml found"
else
  fail "C-05: dagster/pyproject.toml missing — Dagster project not initialised"
fi

if [[ -f "$REPO_ROOT/dagster/dagster_project/__init__.py" ]]; then
  pass "C-06: dagster/dagster_project/__init__.py found"
else
  fail "C-06: dagster/dagster_project/__init__.py missing"
fi

# C-07: manifest.json — required at import time by dagster-dbt
MANIFEST="$REPO_ROOT/dbt/target/manifest.json"

if [[ "$FORCE_PARSE" == "true" ]]; then
  header "Regenerating manifest.json (--parse)"
  if command -v dbt &>/dev/null; then
    info "Running: dbt parse"
    # dbt parse exits 1 due to known protobuf bug in dbt 1.11.7 but manifest is
    # generated correctly — check file existence rather than exit code.
    cd "$REPO_ROOT/dbt"
    dbt parse || true
    cd "$REPO_ROOT"
    if [[ -f "$MANIFEST" ]]; then
      pass "manifest.json generated"
    else
      fail "dbt parse ran but manifest.json not found at $MANIFEST"
    fi
  else
    fail "--parse requested but dbt not found in PATH"
  fi
elif [[ -f "$MANIFEST" ]]; then
  MANIFEST_AGE=$(( $(date +%s) - $(stat -f %m "$MANIFEST" 2>/dev/null || stat -c %Y "$MANIFEST") ))
  MANIFEST_HOURS=$(( MANIFEST_AGE / 3600 ))
  pass "C-07: dbt/target/manifest.json found (age: ${MANIFEST_HOURS}h)"
  if [[ $MANIFEST_HOURS -gt 24 ]]; then
    warn "manifest.json is over 24h old — run with --parse to regenerate if models changed"
  fi
else
  fail "C-07: dbt/target/manifest.json not found — run: cd dbt && dbt parse"
fi

# ── Abort if any check failed ─────────────────────────────────────────────────
echo ""
if [[ $FAILED -gt 0 ]]; then
  echo -e "${RED}${BOLD}  $FAILED pre-flight check(s) failed. Resolve before starting Dagster.${NC}"
  echo -e "${BOLD}════════════════════════════════════════════════════${NC}\n"
  exit 1
fi

echo -e "${GREEN}${BOLD}  All checks passed.${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"

# ── LAUNCH DAGSTER ────────────────────────────────────────────────────────────
header "Launching Dagster"
info "Working dir: $REPO_ROOT/dagster"
info "UI will be available at: http://${HOST}:${PORT}"
info "Press Ctrl+C to stop"
echo ""
echo -e "  ${BOLD}Asset graph:${NC}  25 assets in 4 layers"
echo -e "             meltano_ingest (9 olist_raw/* tables)"
echo -e "             → 9 staging models"
echo -e "             → 7 mart models  (+ dim_date independent)"
echo -e "  ${BOLD}Schedule:${NC}     full_pipeline_job_schedule  |  daily 09:00 SGT"
echo ""

cd "$REPO_ROOT/dagster"
exec dagster dev --host "$HOST" --port "$PORT"
