# Multi-Agent Pipeline Framework: Setup Guide

This guide walks you through setting up the complete multi-agent data
pipeline framework from scratch. By the end, you'll have a repo with
six directive files, git worktrees for agent isolation, and an
orchestrator ready to run.

---

## Prerequisites

Before starting, confirm you have the following installed and configured.

### Claude Code CLI

```bash
# Install (requires Node.js >= 18)
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version

# Authenticate (one of these)
export ANTHROPIC_API_KEY="sk-ant-..."    # API key approach
claude                                    # or browser auth via Pro/Max plan
```

You need a **Max plan** (recommended) or API access. The Max plan
gives you Opus access and enough token headroom for multi-agent runs.
Max20 ($200/month) is ideal for sustained parallel agent sessions.

### Git

```bash
git --version    # >= 2.20 for worktree support
```

### jq (for parsing agent JSON output)

```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# Verify
jq --version
```

### Python & Node.js (for agent tooling)

Agents will install their own dependencies, but the base runtimes
must be available:

```bash
python3 --version    # >= 3.10
node --version       # >= 18
npm --version
```

### Project-Specific Dependencies

These vary by your pipeline but the agents expect them available:

```bash
# Meltano (Agent 1)
pip install meltano

# dbt (Agent 1)
pip install dbt-bigquery

# Dagster (Agent 2)
pip install dagster dagster-dbt dagster-webserver

# Jupyter + analytics (Agent 3)
pip install jupyter pandas plotly google-cloud-bigquery pyarrow

# Streamlit (Agent 4)
pip install streamlit plotly

# ML / Data Science (Agent 5)
pip install scikit-learn joblib statsmodels xgboost lightgbm
```

### Google Cloud / BigQuery

Agent 1 writes to BigQuery via Meltano, and Agents 3 and 5 read from it.
Ensure application default credentials are set:

```bash
gcloud auth application-default login
```

Or set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable
pointing to a service account key file.

---

## Step 1: Initialize the Repository

Start with an empty or existing project repo. The framework adds
structure on top of whatever you already have.

```bash
# If starting fresh
mkdir my-data-pipeline && cd my-data-pipeline
git init
git commit --allow-empty -m "Initial commit"

# If using an existing repo
cd my-data-pipeline
```

---

## Step 2: Create the Directory Structure

```bash
# Directive files (the brains of each agent)
mkdir -p directives

# Agent output directories (agents create files here)
mkdir -p meltano
mkdir -p dbt/models/staging dbt/models/marts dbt/tests
mkdir -p dagster/assets
mkdir -p notebooks
mkdir -p data
mkdir -p pages

# Agent 5 output directories
mkdir -p features
mkdir -p models/artifacts models/metrics

# Orchestrator logs
mkdir -p logs

# Worktree directory (will hold git worktrees)
mkdir -p worktrees

# Claude Code project context
mkdir -p .claude
```

---

## Step 3: Create the CLAUDE.md

This file provides project-level context that every agent inherits
automatically. Claude Code reads `.claude/CLAUDE.md` at session start.

```bash
cat > .claude/CLAUDE.md << 'EOF'
# Project Context

## Architecture
This is a multi-agent data pipeline project. Each agent owns a specific
scope and produces deliverables that downstream agents consume.

## Agent Ownership
- meltano/ and dbt/  → Agent 1 (Data Engineer)
- dagster/           → Agent 2 (Platform Engineer)
- notebooks/ and data/ → Agent 3 (Analytics Engineer)
- dashboard.py, dashboard_utils.py, pages/ → Agent 4 (Dashboard Engineer)
- features/, models/, ml_utils.py → Agent 5 (Data Scientist)

## Rules
- Never modify files outside your designated directories.
- Never hardcode credentials, project IDs, or service account paths.
- Use environment variables for all configuration.
- Document every assumption with a comment or markdown cell.

## Open Items
- I-01: Tap plugin — [STATUS: PENDING/RESOLVED]
- I-02: Target plugin — [STATUS: PENDING/RESOLVED]
- I-03: Write disposition — [STATUS: PENDING/RESOLVED]
- I-04: Table naming convention — [STATUS: PENDING/RESOLVED]

## BigQuery
- Project: [YOUR_GCP_PROJECT]
- Dataset (raw): [YOUR_RAW_DATASET]
- Dataset (analytics): [YOUR_ANALYTICS_DATASET]
EOF
```

**Action required:** Fill in the bracketed placeholders with your actual
project details. The open items (I-01 through I-04) must be marked
RESOLVED before the orchestrator will proceed.

---

## Step 4: Create the Directive Files

Each directive file contains the complete system prompt for one agent.
Copy the contents from the documents we've built:

```bash
# Copy from the outputs we've produced.
# Each file should contain the full system prompt markdown
# from the multi_agent_directives.md document.

# directives/orchestrator.md          ← from orchestrator_directive.md
# directives/agent_data_engineer.md   ← Agent 1 section from multi_agent_directives.md
# directives/agent_platform_engineer.md  ← Agent 2 section
# directives/agent_analytics_engineer.md ← Agent 3 section
# directives/agent_dashboard_engineer.md ← Agent 4 section
# directives/agent_data_scientist.md     ← Agent 5 section
```

To extract each agent's prompt from the multi_agent_directives.md:
each agent's section starts after `### System Prompt` and is enclosed
in a triple-backtick markdown code block. Extract the content **inside**
the code block (without the backticks) and save it as the directive file.

Verify all six files exist:

```bash
ls -la directives/
# orchestrator.md
# agent_data_engineer.md
# agent_platform_engineer.md
# agent_analytics_engineer.md
# agent_dashboard_engineer.md
# agent_data_scientist.md
```

---

## Step 5: Set Up Git Worktrees

Worktrees give each agent its own isolated filesystem. They share
the same git history but have independent working directories, so
agents can't accidentally overwrite each other's work.

```bash
# Commit the framework structure first
git add -A
git commit -m "Framework: directive files, directory structure, CLAUDE.md"

# Create a worktree for each agent
git worktree add worktrees/data-engineer    main
git worktree add worktrees/platform-engineer main
git worktree add worktrees/analytics-engineer main
git worktree add worktrees/dashboard-engineer main
git worktree add worktrees/data-scientist     main
```

Verify:

```bash
git worktree list
# /path/to/my-data-pipeline                   abc1234 [main]
# /path/to/my-data-pipeline/worktrees/data-engineer    abc1234 [data-engineer]
# /path/to/my-data-pipeline/worktrees/platform-engineer abc1234 [platform-engineer]
# /path/to/my-data-pipeline/worktrees/analytics-engineer abc1234 [analytics-engineer]
# /path/to/my-data-pipeline/worktrees/dashboard-engineer abc1234 [dashboard-engineer]
# /path/to/my-data-pipeline/worktrees/data-scientist     abc1234 [data-scientist]
```

Each worktree has full access to the repo contents (including
`directives/` and `.claude/CLAUDE.md`). The orchestrator will
merge completed work back to main between phases.

**Add worktrees to .gitignore** so they don't nest recursively:

```bash
echo "worktrees/" >> .gitignore
echo "logs/" >> .gitignore
git add .gitignore && git commit -m "Ignore worktrees and logs"
```

---

## Step 6: Verify the Environment

Run this checklist before your first pipeline execution:

```bash
echo "=== Environment Check ==="

# Claude Code
claude --version && echo "✓ Claude Code installed" || echo "✗ Claude Code missing"

# Git worktrees
test -d worktrees/data-engineer && echo "✓ Worktrees created" || echo "✗ Worktrees missing"

# Directive files
for f in orchestrator agent_data_engineer agent_platform_engineer agent_analytics_engineer agent_dashboard_engineer agent_data_scientist; do
  test -f "directives/${f}.md" && echo "✓ directives/${f}.md" || echo "✗ directives/${f}.md MISSING"
done

# CLAUDE.md
test -f .claude/CLAUDE.md && echo "✓ CLAUDE.md exists" || echo "✗ CLAUDE.md missing"

# Python dependencies
python3 -c "import meltano" 2>/dev/null && echo "✓ meltano" || echo "✗ meltano not installed"
python3 -c "import dbt" 2>/dev/null && echo "✓ dbt" || echo "✗ dbt not installed"
python3 -c "import dagster" 2>/dev/null && echo "✓ dagster" || echo "✗ dagster not installed"
python3 -c "import pandas" 2>/dev/null && echo "✓ pandas" || echo "✗ pandas not installed"
python3 -c "import streamlit" 2>/dev/null && echo "✓ streamlit" || echo "✗ streamlit not installed"
python3 -c "import sklearn" 2>/dev/null && echo "✓ scikit-learn" || echo "✗ scikit-learn not installed"
python3 -c "import joblib" 2>/dev/null && echo "✓ joblib" || echo "✗ joblib not installed"

# GCP credentials
python3 -c "from google.cloud import bigquery; bigquery.Client()" 2>/dev/null \
  && echo "✓ BigQuery credentials" || echo "✗ BigQuery credentials not configured"

# jq
jq --version >/dev/null 2>&1 && echo "✓ jq installed" || echo "✗ jq missing"

echo "=== Check Complete ==="
```

Fix any `✗` items before proceeding.

---

## Step 7: Resolve Prerequisites (I-01 through I-04)

The orchestrator will not spawn Agent 1 until all four open items
are resolved. Update `.claude/CLAUDE.md` with the answers:

**I-01: Tap plugin**
Which Meltano tap extracts your source data? (e.g., `tap-postgres`,
`tap-csv`, `tap-github`). Confirm it's installable via
`meltano add extractor <tap-name>`.

**I-02: Target plugin**
Confirm `target-bigquery` and its configuration (project ID,
dataset name, credentials path via env var).

**I-03: Write disposition**
Choose `replace` (full refresh) or `append` (incremental).
Default is `replace` unless you specify otherwise.

**I-04: Table naming convention**
Define the exact naming pattern Meltano will use for BigQuery
tables. This is critical — Agent 1 uses this to align `sources.yml`
with Meltano output. Example: `<stream_name>` written to
`raw_dataset.<stream_name>`.

Once resolved, update CLAUDE.md:

```bash
# Edit .claude/CLAUDE.md and change each item to RESOLVED
# Include the actual values, e.g.:
# - I-01: Tap plugin — [STATUS: RESOLVED] tap-postgres
# - I-02: Target plugin — [STATUS: RESOLVED] target-bigquery, project=my-project, dataset=raw
# - I-03: Write disposition — [STATUS: RESOLVED] replace
# - I-04: Table naming convention — [STATUS: RESOLVED] raw.<stream_name>
```

Commit the update:

```bash
git add .claude/CLAUDE.md
git commit -m "Resolve prerequisites I-01 through I-04"
```

**Propagate to all worktrees** so agents see the updated context:

```bash
for wt in data-engineer platform-engineer analytics-engineer dashboard-engineer data-scientist; do
  cd worktrees/$wt && git pull origin main && cd ../..
done
```

---

## Step 8: Launch the Orchestrator

The orchestrator runs as an interactive Opus session in the repo root.
It reads its own directive file and manages the full pipeline.

```bash
# From the repo root
claude --model opus \
       --append-system-prompt-file directives/orchestrator.md
```

This opens an interactive session. The orchestrator's directive is
appended to Claude Code's default system prompt, so it has full
access to bash, file reading, and all built-in tools — plus the
orchestration instructions.

**Your opening prompt to the orchestrator:**

```
Execute the pipeline. All prerequisites (I-01 through I-04) are
resolved in CLAUDE.md. Begin with Phase 0 prerequisite verification,
then proceed through all phases. Report status at each gate.
```

The orchestrator will then:

1. Read `.claude/CLAUDE.md` and verify I-01 through I-04 are RESOLVED
2. Spawn Agent 1 in `worktrees/data-engineer/` via `claude -p`
3. Parse Agent 1's output, verify deliverables exist
4. Merge Agent 1's worktree back to main
5. Update parallel worktrees with Agent 1's output
6. Spawn Agents 2 and 3 in parallel
7. Wait for both, merge results
8. Spawn Agent 4
9. Merge Agent 4's results
10. Spawn Agent 5
11. Run final validation
12. Produce the pipeline build report

---

## Step 9: Monitor Execution

While the orchestrator runs, you can observe progress in several ways:

### Watch the orchestrator's session

The interactive session shows the orchestrator's reasoning and bash
commands in real time. You'll see it spawning agents, reading output
files, and making gate decisions.

### Check agent logs

Each agent writes JSON output to `logs/`:

```bash
# In a separate terminal
tail -f logs/agent1_output.json
tail -f logs/agent2_output.json
tail -f logs/agent3_output.json
tail -f logs/agent4_output.json
tail -f logs/agent5_output.json
```

### Parse agent results

```bash
# Check if Agent 1 finished and get its status
cat logs/agent1_output.json | jq -r '.result' | head -50

# Check cost
cat logs/agent1_output.json | jq '.cost_usd'
```

### Check worktree state

```bash
# See what Agent 1 produced
ls worktrees/data-engineer/meltano/
ls worktrees/data-engineer/dbt/models/staging/
ls worktrees/data-engineer/dbt/models/marts/
```

---

## Step 10: Handle Failures

The orchestrator handles most failures automatically via its retry
policy. But there are cases where it will escalate to you.

### If the orchestrator asks for input

It will present the failure context, what it tried, and a specific
question. Answer in the interactive session. Common scenarios:

- **Ambiguous prerequisite:** "I-04 says 'raw.<stream_name>' but
  Agent 1 found the tap outputs as '<tap_name>_<stream_name>'.
  Which naming is correct?" → Provide the correct naming.

- **Agent exceeded retries:** "Agent 1 FAILED after 2 retries.
  Error: dbt compilation error on stg_orders — column 'order_date'
  not found in source." → Check the actual source schema and
  clarify in CLAUDE.md, then tell the orchestrator to retry.

### If you need to restart from a specific phase

```bash
# Kill the current orchestrator session (Ctrl+C or /exit)

# The worktrees preserve state. Re-launch and instruct:
claude --model opus \
       --append-system-prompt-file directives/orchestrator.md

# Then prompt:
"Agent 1 completed successfully in the previous run. Skip to Phase 2.
Agent 1's deliverables are already merged to main. Proceed with
Agents 2 and 3."
```

### If you need to re-run a single agent manually

```bash
# Example: re-run Agent 3 in isolation
cd worktrees/analytics-engineer
git pull origin main    # ensure it has latest from Agent 1

claude -p \
  --model claude-opus-4-20250514 \
  --append-system-prompt-file ../../directives/agent_analytics_engineer.md \
  --output-format json \
  --dangerously-skip-permissions \
  "Execute your directive. Produce all deliverables in notebooks/ and data/. \
   Report structured status on completion." \
  > ../../logs/agent3_output.json 2>&1

cd ../..

# Check output
cat logs/agent3_output.json | jq -r '.result'
```

---

## Step 11: Merge Final Results

After the orchestrator reports COMPLETE, all agent work should
already be merged to main (the orchestrator does this between phases).
Verify:

```bash
# Check main branch has everything
git log --oneline -10
# Should show commits from each agent phase

# Verify all deliverables
echo "=== Deliverable Check ==="
test -f meltano/meltano.yml && echo "✓ meltano.yml"
ls dbt/models/staging/*.sql 2>/dev/null | wc -l | xargs -I{} echo "✓ {} staging models"
ls dbt/models/marts/*.sql 2>/dev/null | wc -l | xargs -I{} echo "✓ {} mart models"
test -f dbt/models/sources.yml && echo "✓ sources.yml"
test -f dagster/definitions.py && echo "✓ dagster definitions"
ls notebooks/*.ipynb 2>/dev/null | wc -l | xargs -I{} echo "✓ {} notebooks"
ls data/*.parquet 2>/dev/null | wc -l | xargs -I{} echo "✓ {} parquet files"
test -f dashboard.py && echo "✓ dashboard.py"
ls pages/*.py 2>/dev/null | wc -l | xargs -I{} echo "✓ {} dashboard pages"
test -f features/feature_engineering.py && echo "✓ feature engineering"
test -f features/feature_definitions.yml && echo "✓ feature definitions"
test -f models/train.py && echo "✓ model training script"
test -f models/evaluate.py && echo "✓ model evaluation script"
ls models/artifacts/*.joblib 2>/dev/null | wc -l | xargs -I{} echo "✓ {} model artifacts"
test -f models/README.md && echo "✓ models README"
test -f ml_utils.py && echo "✓ ml_utils.py"
echo "=== Check Complete ==="
```

---

## Step 12: Clean Up Worktrees

Once everything is merged and verified:

```bash
git worktree remove worktrees/data-engineer
git worktree remove worktrees/platform-engineer
git worktree remove worktrees/analytics-engineer
git worktree remove worktrees/dashboard-engineer
git worktree remove worktrees/data-scientist
rmdir worktrees    # should be empty now
```

---

## Quick Reference

### File Map

| File | Purpose | Created By |
|------|---------|------------|
| `directives/orchestrator.md` | Orchestrator system prompt | You (setup) |
| `directives/agent_data_engineer.md` | Agent 1 system prompt | You (setup) |
| `directives/agent_platform_engineer.md` | Agent 2 system prompt | You (setup) |
| `directives/agent_analytics_engineer.md` | Agent 3 system prompt | You (setup) |
| `directives/agent_dashboard_engineer.md` | Agent 4 system prompt | You (setup) |
| `directives/agent_data_scientist.md` | Agent 5 system prompt | You (setup) |
| `.claude/CLAUDE.md` | Shared project context | You (setup) |
| `logs/agent*_output.json` | Agent execution logs | Orchestrator |
| `meltano/`, `dbt/` | Pipeline config + models | Agent 1 |
| `dagster/` | Orchestration layer | Agent 2 |
| `notebooks/`, `data/` | Analysis + Parquet exports | Agent 3 |
| `dashboard.py`, `pages/` | Interactive dashboard | Agent 4 |
| `features/`, `models/`, `ml_utils.py` | ML pipeline + artifacts | Agent 5 |

### Command Cheat Sheet

```bash
# Launch orchestrator
claude --model opus --append-system-prompt-file directives/orchestrator.md

# Run single agent manually
claude -p --model opus \
  --append-system-prompt-file directives/agent_data_engineer.md \
  --output-format json --dangerously-skip-permissions \
  "Execute your directive."

# Check agent output
cat logs/agent1_output.json | jq -r '.result'
cat logs/agent1_output.json | jq '.cost_usd'

# Create worktrees
git worktree add worktrees/<name> main

# Propagate main to worktrees
cd worktrees/<name> && git pull origin main && cd ../..

# Clean up worktrees
git worktree remove worktrees/<name>
```

### Cost Estimation

Rough per-run estimates (varies significantly by task complexity):

| Agent | Model | Estimated Cost |
|-------|-------|----------------|
| Orchestrator | Opus | $2–5 (long-running session) |
| Agent 1 (Data Engineer) | Opus | $3–8 (most deliverables) |
| Agent 2 (Platform Engineer) | Sonnet | $0.50–2 |
| Agent 3 (Analytics Engineer) | Opus | $2–6 |
| Agent 4 (Dashboard Engineer) | Sonnet | $0.50–2 |
| Agent 5 (Data Scientist) | Opus | $3–8 |
| **Total** | | **~$11–31 per run** |

These are rough estimates. Actual cost depends on how many retries
occur, how complex the dbt models are, and how much back-and-forth
each agent does with its tools. Check `cost_usd` in each agent's
output JSON for actuals.
