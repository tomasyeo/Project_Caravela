# Multi-Agent Self-Assessment Framework — User Guide

**Version 1.0**
How to instrument, run, and interpret a retrospective performance assessment
of any project built with multiple LLM agents.

---

## What This Framework Does

You built something using multiple LLM agents — each with its own directive, each producing
artefacts that were reviewed before the next agent started. This framework helps you answer:

- Did the agents follow their specifications?
- Where did autonomous decisions go right or wrong?
- How did errors propagate between agents?
- Was the orchestrator's involvement productive or corrective?
- What would you change for the next run?

It produces two deliverables: a **Jupyter notebook** with quantitative analysis and
visualisations, and a **markdown executive summary** with findings, critique, and
recommendations.

---

## The Three Files

The framework consists of three files in `prompts/`. Each serves a distinct purpose
at a different point in the project lifecycle.

```
prompts/
  00_agent_audit_trail_directive.md   ← BEFORE the project (instrumentation)
  01_multiagent_assessment_prompt.md  ← AFTER the project (standalone prompt)
  01_multiagent_assessment_skill.md   ← AFTER the project (Claude Code skill)
```

| File | When | Where | What It Does |
|---|---|---|---|
| `00_agent_audit_trail_directive.md` | Before agents start | Appended to each agent's directive | Instructs agents to log decisions, contracts, uncertainties, and handoffs in a structured format |
| `01_multiagent_assessment_prompt.md` | After project completes | Any LLM conversation (Claude, GPT, etc.) | Standalone prompt — paste it, attach your logs, answer questions interactively |
| `01_multiagent_assessment_skill.md` | After project completes | Claude Code session (`/multiagent-assess`) | Skill version — auto-scans project files, less manual data entry |

**You need the audit trail directive (file 00) AND one of the two assessment files (file 01).**
The skill and prompt produce identical analysis — they differ only in how data is collected.

---

## Phase 1: Before the Project — Instrument Your Agents

### What to do

1. Open `prompts/00_agent_audit_trail_directive.md`.
2. For each agent in your project, append the entire audit trail block to the end of that
   agent's directive (system prompt, task description, or instruction file).
3. Replace `[PROJECT_NAME]` with your project name and `[AGENT_ID]` with a unique identifier
   (e.g., `agent_1a`, `backend_api`, `data_transform`).
4. Keep a copy of the `[GATE_REVIEW]` block for yourself — you (the orchestrator) log gate
   reviews separately. This block is NOT included in agent directives.

### What the agents will produce

Each agent writes an `audit_[AGENT_ID].md` file containing structured entries:

| Marker | When Logged | Why It Matters |
|---|---|---|
| `[DECISION]` | Agent makes a choice not explicitly covered by its directive | Measures autonomous decision quality |
| `[UNCERTAIN]` | Agent encounters ambiguity and resolves it | Measures knowledge boundary detection (KBD) |
| `[CONTRACT]` | Agent produces or consumes a shared interface (table name, file path, API endpoint, schema) | Enables cascade and contract surface analysis |
| `[SCOPE_BOUNDARY]` | Agent considers and rejects something as out of scope | Documents scope discipline |
| `[TOOL_EVENT]` | A tool or library behaves differently than expected | Tracks external deviations |
| `[HANDOFF_SUMMARY]` | End of every work session (mandatory) | Structured handoff — lists artefacts, deviations, uncertainties |

### What you (the orchestrator) log

At each gate review checkpoint, write a `[GATE_REVIEW]` entry in your own notes or in
`changelog.md`:

```
[GATE_REVIEW]
  agent:        agent_1b
  gate:         Gate 2 — staging models
  outcome:      revision_requested
  corrections:  customer_unique_id join was wrong — needed two-hop resolution
  flags_reviewed: flag_review:yes on stg_products COALESCE approach — approved
  note:         Agent produced 9 models as spec'd but FK resolution logic was incorrect
```

### What if you didn't instrument?

The framework still works — but with lower data quality. During the assessment phase, you'll
estimate values from memory, git history, and session notes instead of reading them from
structured logs. The analysis flags estimated values with `(est.)` and names the biases
introduced (recall bias, attribution bias, self-serving framing) in its critique section.

**Instrumentation is the single highest-ROI improvement you can make for assessment quality.**
A 5-minute setup per agent saves 30 minutes of reconstruction and produces metrics you can
actually trust.

---

## Phase 2: After the Project — Run the Assessment

You have two options. Both produce the same analysis.

### Option A: Standalone Prompt (any LLM)

**Best for:** Using a non-Claude LLM, sharing with colleagues who don't use Claude Code,
or running the assessment in a web interface.

**Steps:**

1. Open a new conversation with Claude (claude.ai), ChatGPT, or any capable LLM.

2. Paste the entire contents of `prompts/01_multiagent_assessment_prompt.md` as your first
   message.

3. Attach or paste your available project materials:
   - `audit_*.md` files (highest quality)
   - `changelog.md` (gate decisions, corrections)
   - `progress.md` (requirement completion status)
   - Agent directive files (for word count and constraint density analysis)
   - Git history or session transcripts (fallback)

4. The LLM will walk you through an interactive protocol:

   ```
   Step 1 → Qualification: "Does this project have ≥2 agents with gate reviews?"
   Step 2 → Project type:  "This appears to be a Data Pipeline project. Confirm?"
   Step 3 → Audience:      "Research, personal, or both?"
   Step 4 → Data collection: Per-agent metrics (pre-populated from your attachments)
   Step 5–8 → Analysis:    Automated — the LLM computes metrics and generates narrative
   Step 9 → Output:        Two files generated
   ```

5. Expect 30–60 minutes of interactive data collection (Step 4), then generation.

**Tips:**
- Answer one question at a time. The prompt enforces sequential clarification.
- If you can't recall a value, say so. The framework marks unknowns explicitly and
  notes which analyses degrade — it never silently assumes values.
- Attach directive files if possible — this enables automated constraint density
  computation rather than manual estimation.


### Option B: Claude Code Skill (Claude Code only)

**Best for:** Projects already using Claude Code, where the codebase is on your local
machine and audit trail files are in the repo.

**Setup (one-time per project):**

```bash
# From your project root
mkdir -p .claude/commands
cp prompts/01_multiagent_assessment_skill.md .claude/commands/multiagent-assess.md
```

**Run:**

```
# Inside a Claude Code session in the project directory
/multiagent-assess
```

**What happens differently from the standalone prompt:**

The skill adds **Step 1: Scan Available Project Files** before qualification. Claude Code
reads your repo directly and pre-populates data from:

```
audit_*.md           → per-agent decision logs, contract surfaces, handoff summaries
changelog.md         → gate decisions, deviations, corrections
progress.md          → requirement completion status per agent
directives/ or agents/ → directive files (auto-computes word count + constraint density)
CLAUDE.md            → project scope, agent list, architecture
requirements/ or docs/ → BRD, specifications
```

After scanning, it reports what it found and what's missing. You only need to provide
data that couldn't be extracted from files — typically involvement scores, decision quality
ratings, and involvement notes (subjective assessments that require orchestrator judgment).

**The skill version requires less manual input but produces the same analysis.**

---

## Phase 3: Understanding the Output

### Output A — Analysis Notebook

A Python script that generates a Jupyter notebook (`.ipynb`). Run it with:

```bash
python generate_[project_name]_analysis.py
# Then open the notebook
jupyter notebook [project_name]_agent_analysis.ipynb
```

The notebook follows a **six-act structure**:

| Act | What It Answers | Key Visualisations |
|---|---|---|
| 1. Context | How was the work divided? How were directives designed? | Directive word count bar, constraint density scatter, resource allocation |
| 2. Individual Performance | Did each agent follow its spec? How were autonomous decisions? | Deviation rate bars, KBD scores, first-pass rates, deviation taxonomy sunburst |
| 3. System Effects | How did errors propagate between agents? | Cascade amplification heatmap, contract surface fragility table |
| 4. Human–AI Dynamics | Was orchestrator involvement productive or corrective? | Involvement spectrum, co-design mode detection, human leverage scatter |
| 5. System-Level | How does the overall system compare to a human team? | 8-dimension radar, artefact inventory, human vs. AI comparison |
| 6. Synthesis | What are the key findings and what would you change? | Numbered findings with evidence, limitations, research value statement |

Every chart is followed by an **interpretation cell** that explains what the
visualisation shows, calls out specific data points, states the finding, and flags
any surprises.

### Output B — Executive Summary

A markdown document with nine sections:

1. **What Was Assessed** — scope, agents, duration
2. **One-Paragraph Finding Per Act** — the headline from each act
3. **Top 5 Cross-Cutting Insights** — findings that only emerge by reading all acts together
4. **Was It Worth It?** — cost-benefit assessment of orchestrator investment vs. output value
5. **The Specification Quality Paradox** — did following the spec produce a correct result?
6. **Critique** — unvarnished structural weaknesses in the framework AND in the analysis itself
7. **Key Issues Ranked by Severity** — table of issues with severity and originating act
8. **Recommended Improvements** — prioritised, concrete, P1 = highest ROI
9. **The Verdict** — clear position on whether the framework worked and under what conditions
10. **Research Value Statement** — N, measurement quality, open questions

---

## Key Concepts You'll Encounter

### The Six Interpretive Principles

These are embedded in the analysis and cannot be overridden. They shape how every metric
is interpreted.

| # | Principle | One-Sentence Summary |
|---|---|---|
| 1 | The Involvement Reframe | High deviation + high involvement = co-design (good); high deviation + low involvement = fidelity problem (bad) |
| 2 | The Origin Taxonomy | Only agent-origin deviations are "failures" — cascade, external, and orchestrator-origin deviations are structural, not behavioural |
| 3 | The Three Collaboration Modes | Autonomous (≤2), Correction (=3, least productive), Co-Design (≥4) — each evaluated by different success criteria |
| 4 | Silent Failure Priority | An undetected bad decision is costlier than a detected one — KBD matters more than raw decision quality |
| 5 | Cascade Debt ≠ Deviation Count | One high-cascade deviation costs more than three zero-cascade deviations |
| 6 | Compliance ≠ Wisdom | High fidelity to a bad spec is worse than useful deviation — the framework can't tell the difference |

### Key Metrics

| Metric | Formula | What It Measures |
|---|---|---|
| Deviation Rate | deviations / requirements_owned | How often the agent departed from spec |
| First-Pass Rate | 1 / revision_cycles | How clean the agent's first output was |
| Auto Decision Quality | good / (good + bad) | Quality of decisions made in directive gaps |
| Knowledge Boundary Detection (KBD) | (uncertain - silent_failures) / uncertain | Does the agent know what it doesn't know? |
| Cascade Amplification Factor (CAF) | downstream_rework / max(deviations, 1) | How much one agent's errors cost other agents |
| Spec ROI | (reqs × (1 - adj_dev_rate)) / (words / 1000) | Requirements delivered per 1,000 directive words |
| Human Leverage | requirements_owned / involvement_score | Requirements delivered per unit of orchestrator effort |

### The Involvement Scale

```
1 = Minimal    — reviewed output, no interventions
2 = Low        — 1–2 corrections at gate
3 = Moderate   — repeated corrections; orchestrator fixing failures (correction mode)
4 = High       — actively shaping outputs mid-execution
5 = Very High  — full co-design; brainstorming alongside agent
```

Score 3 is the "dead zone" — the orchestrator is working hard but only fixing problems,
not enriching. The analysis specifically investigates agents in correction mode to determine
whether the root cause was a directive gap, a model limitation, or an ambiguous specification.

---

## Adapting for Your Project

### Minimum viable setup (no instrumentation)

If you've already completed a multi-agent project without the audit trail directive:

1. Use the standalone prompt (Option A).
2. Gather what you have: git history, changelogs, session transcripts, your memory.
3. Be honest about estimates. The framework handles missing data gracefully — it marks
   `(est.)` and `(unknown)`, names which analyses degrade, and critiques its own data quality
   in the output.
4. Next time, add the audit trail directive. The difference in output quality is substantial.

### Different project types

The framework adapts its terminology and activated analyses to the project type:

- **Data Pipeline** → analyses focus on data contracts, schema surfaces, cascade propagation
- **Software Development** → analyses focus on API contracts, interface surfaces, integration debt
- **Research Synthesis** → analyses focus on source quality, methodology surfaces, conclusion validity
- **Content / Creative** → analyses focus on style consistency, brand surfaces, revision depth
- **Hybrid** → all applicable analyses activated

The metrics and principles are invariant — only the language changes.

### Hybrid human-AI teams

If your project mixed human engineers and LLM agents in the same pipeline, the framework
detects this at qualification and asks you to propose a custom involvement scale. The standard
1–5 scale assumes a single orchestrator + LLM agents. For hybrid teams, you'll define a scale
based on the ratio of human-generated to AI-generated content and the nature of human-AI
handoffs.

---

## Frequently Asked Questions

**Q: How many agents do I need?**
Minimum 2, each with a separate directive and at least one gate review between them. There is
no maximum, but the optional analyses (cascade topology, co-design quadratic detection) become
more informative with 5+ agents.

**Q: Does it work with agents other than Claude?**
Yes. The audit trail directive works with any LLM that can follow structured logging
instructions. The standalone assessment prompt works with any capable LLM. The skill version
requires Claude Code specifically.

**Q: What if some of my agents didn't produce audit logs?**
The framework handles partial data. Agents with logs get directly-measured metrics; agents
without logs get estimated metrics marked `(est.)`. The critique section explicitly names
which metrics were estimated and what biases that introduces.

**Q: Can I run this on a project with only 1 agent?**
No. The framework's value is in measuring inter-agent dynamics: cascade propagation, contract
surfaces, involvement spectrum. A single-agent project should use a simpler evaluation
protocol. The qualification step will stop you if this threshold isn't met.

**Q: How long does the assessment take?**
- With full audit trail logs: ~30 minutes of interactive data collection + generation
- Without instrumentation: ~60 minutes (more questions to answer from memory)
- Claude Code skill version: ~20 minutes (auto-scans files, fewer questions)

**Q: Is the analysis objective?**
No — and it says so explicitly. The critique section names four structural limitations:
sample size (N < 20 = descriptive only), self-reported retrospective data (recall and
attribution bias), proxy metric validity (e.g., constraint density via keyword grep),
and the specification quality confound (high fidelity ≠ correct specification). The framework
measures compliance, not wisdom (Principle 6).

---

## Quick-Start Checklist

### Before your next multi-agent project

- [ ] Copy `prompts/00_agent_audit_trail_directive.md` into each agent's directive
- [ ] Replace `[PROJECT_NAME]` and `[AGENT_ID]` placeholders
- [ ] Keep the `[GATE_REVIEW]` block for your own gate review notes
- [ ] Maintain a `changelog.md` with gate decisions and corrections

### After the project completes

- [ ] Gather all `audit_*.md` files, `changelog.md`, `progress.md`, and directive files
- [ ] Choose your method: standalone prompt (any LLM) or Claude Code skill
- [ ] If using the skill: `cp prompts/01_multiagent_assessment_skill.md .claude/commands/multiagent-assess.md`
- [ ] Run the assessment and answer the clarification questions
- [ ] Review the two outputs: analysis notebook + executive summary
- [ ] Read the critique section — the framework's own limitations are documented there

---

*Multi-Agent Self-Assessment Framework v1.0*
*Reference implementation: Project Caravela (2026)*
