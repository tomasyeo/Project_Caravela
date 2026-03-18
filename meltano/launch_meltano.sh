#!/usr/bin/env bash
# launch_meltano.sh — Wrapper for Meltano with .env loading
# Usage:
#   ./launch_meltano.sh test    — validate tap and target config resolution
#   ./launch_meltano.sh run     — execute tap-csv → target-bigquery pipeline

set -euo pipefail
cd "$(dirname "$0")"

ENV_FILE="../.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Copy .env.example to .env and fill in values."
  exit 1
fi

case "${1:-}" in
  test)
    echo "=== Validating tap-csv config ==="
    meltano --env-file "$ENV_FILE" config print tap-csv
    echo ""
    echo "=== Validating target-bigquery config ==="
    meltano --env-file "$ENV_FILE" config print target-bigquery
    echo ""
    echo "=== All config validated ==="
    ;;
  run)
    echo "=== Running: tap-csv → target-bigquery ==="
    meltano --env-file "$ENV_FILE" run tap-csv target-bigquery
    ;;
  *)
    echo "Usage: $0 {test|run}"
    exit 1
    ;;
esac
