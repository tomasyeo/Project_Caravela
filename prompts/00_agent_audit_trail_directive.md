# AGENT AUDIT TRAIL — Mandatory Logging Block

> **Orchestrator instruction:** Append this block verbatim to every agent's directive before
> the agent begins work. Do not modify the structured markers — they are parsed by the
> retrospective assessment prompt. Fill in `[PROJECT_NAME]` and `[AGENT_ID]` only.

---

## Audit Trail Requirement

You are required to maintain a structured audit trail throughout your work on this task.
This log is a first-class deliverable — it is as important as the code or artefacts you produce.

Append your audit trail entries to a file named `audit_[AGENT_ID].md` in your working directory,
or include them at the end of your session summary if no file output is available.

Use the exact marker format below. Do not paraphrase the markers. Log entries in real time
as events occur — do not reconstruct them at session end.

---

### Log Format

```
PROJECT: [PROJECT_NAME]
AGENT:   [AGENT_ID]
```

**For every autonomous decision not explicitly covered in your directive:**
```
[DECISION]
  type:         naming | architecture | data | algorithm | interface | scope | other
  choice_made:  <what you did>
  alternative:  <what you considered but rejected>
  reason:       <why you chose this option>
  certainty:    confident | uncertain | unclear
```

**Before acting on any decision where your directive was ambiguous or silent:**
```
[UNCERTAIN]
  topic:        <what was unspecified or ambiguous>
  resolution:   <how you resolved it>
  impact:       <what downstream consumers of your output need to know>
  flag_review:  yes | no
```

**For every shared interface, name, path, or schema you produce or consume:**
```
[CONTRACT]
  surface:      <name of the shared interface — e.g. table name, file path, column schema>
  exact_value:  <the precise string or structure — e.g. "olist_raw.customers", "data/sales.parquet">
  role:         producer | consumer
  downstream:   <which agents or components consume this — if known>
```

**When you consider something and decide it is out of scope:**
```
[SCOPE_BOUNDARY]
  considered:   <what you considered doing>
  rejected:     yes
  reason:       out_of_spec | too_complex | dependency_unresolved | other
  note:         <any relevant context for the orchestrator>
```

**When a tool, library, or API behaves differently from what your directive assumed:**
```
[TOOL_EVENT]
  tool:         <library, service, or tool name>
  expected:     <what the directive assumed or what you expected>
  actual:       <what actually happened>
  resolution:   <how you adapted>
  spec_impact:  yes | no
```

**At the end of every work session, before handoff:**
```
[HANDOFF_SUMMARY]
  produced:     <list of artefacts produced, one per line>
  deviations:   <list of any departures from directive specification, one per line>
  uncertainties: <list of unresolved questions or assumptions made, one per line>
  downstream_note: <anything the next agent or gate reviewer must know>
```

**Orchestrator only — log at each gate review (not part of agent directive):**
```
[GATE_REVIEW]
  agent:        <agent ID being reviewed>
  gate:         <checkpoint name or number>
  outcome:      approved | revision_requested | blocked
  corrections:  <list of corrections issued, one per line, or "none">
  flags_reviewed: <list of [UNCERTAIN] flag_review:yes items resolved, or "none">
  note:         <orchestrator observations for retrospective>
```

---

### Logging Principles

1. **Log in real time.** Do not reconstruct entries from memory at session end.
   **Data quality warning:** Entries reconstructed after the fact suffer from recall bias and
   attribution bias. If you must reconstruct, mark the entry with `(reconstructed)` so the
   assessment prompt can weight it accordingly.
2. **Be precise on `exact_value` for `[CONTRACT]` entries.** Downstream cascade events are
   almost always caused by ambiguous naming. Write the exact string.
3. **If your directive explicitly covers a decision, you do not need a `[DECISION]` entry.**
   Only log decisions made in gaps — situations your directive did not address.
4. **`flag_review: yes` on any `[UNCERTAIN]` entry where you are less than 80% confident
   your resolution was correct.** The orchestrator reviews flagged entries at gate.
5. **The `[HANDOFF_SUMMARY]` is mandatory.** Even if you have no deviations or uncertainties,
   write `none` for those fields. A missing handoff summary will block gate approval.

---

### Example Entries

**Example A — API integration project:**
```
[UNCERTAIN]
  topic:        REST endpoint naming — directive says "create user endpoint" but does not
                specify singular vs. plural resource path convention
  resolution:   Used plural "/api/users" consistent with OpenAPI best practices
  impact:       agent_frontend must use "/api/users" in all fetch calls, not "/api/user"
  flag_review:  yes

[CONTRACT]
  surface:      User API endpoint path
  exact_value:  /api/users
  role:         producer
  downstream:   agent_frontend (API calls), agent_tests (integration test URLs)
```

**Example B — Data pipeline project:**
```
[DECISION]
  type:         architecture
  choice_made:  Used incremental materialization for the staging model
  alternative:  Full table refresh on every run
  reason:       Source table has 1M+ rows; incremental reduces cost and runtime
  certainty:    confident

[HANDOFF_SUMMARY]
  produced:     staging models (3 SQL files), schema.yml with tests
  deviations:   added a deduplication CTE — directive did not specify how to handle duplicates
  uncertainties: whether downstream mart models expect deduplicated input
  downstream_note: CRITICAL — confirm dedup key with agent_mart before building fact tables
```

---

*This audit trail block is part of the Multi-Agent Self-Assessment Framework.
Assessment prompt: `prompts/01_multiagent_assessment_prompt.md`*
