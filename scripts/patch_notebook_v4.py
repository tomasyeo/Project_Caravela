"""
patch_notebook_v4.py
Post-processes notebooks/04_agent_performance_analysis.ipynb to add:
  1. Interpretation markdown cells after every code cell
  2. Executive summary after §14

Run after generate_analysis_notebook.py:
    python scripts/generate_analysis_notebook.py
    python scripts/patch_notebook_v4.py
"""

import json, os

NB_PATH = os.path.join(os.path.dirname(__file__), "..", "notebooks",
                       "04_agent_performance_analysis.ipynb")

def md(source):
    return {"cell_type": "markdown", "metadata": {}, "source": source}

# ------------------------------------------------------------------
# Map: anchor text (unique substring of code cell) → interpretation
# ------------------------------------------------------------------
INTERPRETATIONS = {

    "Directive Word Count": """\
#### Interpretation — Directive Design by Agent

The two panels reveal an important asymmetry: directive **length** and directive **density** are
not the same thing, and they do not move together. Agent_3 (Analytics) received the longest
directive (1,575 words) yet has only moderate constraint density (1.77%). Agent_4 (Dashboard)
received fewer words (1,235) but the highest density of all eight agents (2.91%).

The most counterintuitive data point is agent_1d (dbt Tests): it sits in the middle of the
word-count range (1,075 words) yet has the *lowest* density of any agent (1.39%). For the agent
responsible for data quality validation — arguably the most binary task in the pipeline (pass or
fail) — this low constraint density suggests the directive leaned heavily on explanatory context
rather than hard constraints. This may be intentional (test thresholds are data-driven, not
specifiable in advance) or it may be a missed opportunity to lock down edge-case behaviour.

The colour gradient (green = minimal involvement, red = very high) reveals the first hint of the
co-design pattern: the two highest-involvement agents (a3 in red, a4 in orange-red) also happen
to own the two largest directives. This correlation is explored formally in §9 and §10.
""",

    "Requirements Owned per Agent": """\
#### Interpretation — Specification Scope and Adjusted ROI

The left panel shows an uneven distribution of requirements across agents: agent_3 (Analytics)
owns 10 requirements — more than double most other agents — while agents 1a and 4 each own just
1–2. This scope imbalance means that a single deviation by agent_1a (1 req, 1 dev) produces a
deviation rate of 1.0, while the same absolute count at agent_1c (9 reqs, 1 dev) produces 0.11.
Raw deviation rates are not comparable across agents without normalising for scope.

The right panel (Adjusted Spec ROI) shows the practical consequence of the cascade/external
adjustment. Agent_1b recovers from what would have been ROI ≈ 0 to ROI = 1.89 — reflecting that
2 of its 3 deviations were context-forced (upstream cascade + dbt-expectations deprecation) rather
than autonomous failures. Agents 1a and 4 remain at zero ROI because their deviations were
agent-initiated, not absorbed from upstream.

The high-ROI agents (1c, 1d, 5) share a common profile: many requirements, low involvement,
minimal deviations. They represent the framework's best-case regime: downstream agents benefiting
from resolved upstream contracts and operating largely without orchestrator intervention.
""",

    "RQ-1: Constraint Density vs Deviation Rate": """\
#### Interpretation — The Positive Density Correlation

This is the most counterintuitive chart in Act 1. If tighter constraints reliably prevented
deviations, we would expect a negative correlation: higher density → lower deviation rate. The
data shows the opposite: r ≈ +0.63, a moderately strong *positive* relationship.

The explanation is a **task-complexity confound**. The agents assigned to technically risky
tasks — ingestion (a1a), staging (a1b), dashboard (a4) — received denser constraints precisely
*because* those tasks were known to be complex and deviation-prone. The directive author was
compensating for anticipated difficulty. The correlation is not causal: denser constraints did
not *cause* more deviations. The underlying task complexity drove both.

The key counter-example is agent_1c (density=2.50, deviation_rate=0.11): high constraints, low
deviation. Agent_1c's task (dbt mart models) was genuinely well-specified — upstream staging
contracts were settled before it began — so the constraints could be acted on cleanly. This
single data point breaks the positive trend and suggests that constraint density works when the
underlying task environment is stable. It fails as a predictor when environmental uncertainty
dominates.

**Practical implication:** do not add constraints as a substitute for resolving environmental
uncertainty. Constraints work on stable surfaces. On volatile ones (new tools, unsettled upstream
contracts), they are overridden by reality.
""",

    "Deviation Rate (lower = better)": """\
#### Interpretation — Fidelity and First-Pass Rate Side by Side

Read these two panels together, not independently. Several patterns emerge:

**The clean performers (a1c, a1d, a5):** All three have low deviation rates and first-pass rates
of 1.0 — they shipped their output correctly on the first gate review. These agents operated in
stable, well-defined task environments (settled upstream contracts, clear deliverable surfaces).
Their fidelity is genuine, not luck.

**The co-design agents (a3, a4):** High deviation rates (0.5, 1.0) and low first-pass rates
(0.25, 0.33) look catastrophic in isolation. In context, they reflect the most iterative phase
of the project — agents 3 and 4 ran concurrently with heavy orchestrator involvement,
continuously refining outputs based on live feedback. Their "deviations" are orchestrator
enrichments. Evaluating them on fidelity is the wrong frame.

**Agent_1b in the middle:** Deviation rate of 1.0 (all requirements touched at least once)
but a moderate profile — this is the cascade absorption story. Two of three deviations were
imposed by upstream failures or tool ecosystem changes, not autonomous agent choices. The
adjusted metrics in §2 correct this picture.

**Key takeaway:** first-pass rate is the more actionable metric for autonomy planning. An agent
with a first-pass rate of 1.0 requires no gate-review iteration — it delivers and moves on. This
is the operational goal for any agent in a time-constrained pipeline.
""",

    "Directive Length vs Deviation Rate": """\
#### Interpretation — Word Count Predicts Nothing

Pearson r ≈ -0.17: essentially zero. There is no meaningful relationship between how many words
an agent received and whether it deviated. This is the null result that should make directive
authors uncomfortable.

The scatter confirms it visually: agent_5 received the 4th-longest directive (1,285 words) and
had zero deviations. Agent_1b received a 1,056-word directive and deviated on every requirement.
Agent_3 received the longest directive (1,575 words) and had the highest deviation count.

Writing more does not help. The evidence points to a different quality axis: **constraint
specificity** (are the hard requirements precisely stated?) and **environmental stability** (is
the technical surface the agent is working on already settled?). Both of those matter far more
than word count.

This finding has a direct budgetary implication: time spent adding explanatory paragraphs to
directives is largely wasted if the core constraints are not already precise. Effort should be
concentrated on the constraint sentences themselves, not the surrounding context.
""",

    "Autonomous Decision Quality": """\
#### Interpretation — Three Views of Gap-Handling Capability

These three panels reveal how agents behave when their directives run out.

**Autonomous Decision Quality** (left): Agent_5's 100% and agent_1c's 100% confirm that the
best-performing agents made no bad autonomous choices. Agent_1a's 50% (1 good, 1 bad) is the
worst result — and notably, the bad decision was the _view suffix naming choice that cascaded
into 4 downstream entries. One bad autonomous decision had disproportionate systemic cost.

**Knowledge Boundary Detection** (centre): The most important panel for understanding failure
modes. Agents_1c, 1d, 3, 4, 5 all score at 1.0 — they flagged uncertainty before acting, or had
no uncertain decisions at all. Agent_1a and agent_1b score below 1.0, reflecting **silent
failures**: decisions made without surfacing the uncertainty. Agent_1a's silent failure on naming
is precisely what the CAF=4.0 cascade traces back to.

**Spec Ambiguity Tolerance** (right): Most agents handle underspecified areas gracefully (scores
of 0.8–1.0). Agent_1b's lower score reflects its highest redirect count — it needed more
orchestrator clarification than others, consistent with operating in the most technically volatile
layer (staging, absorbing cascade + deprecated APIs).

The combined read: the highest-risk agent profile in this framework is **low KBD + low decision
quality** (agent_1a). The best is **high KBD + high quality** (a1c, a1d, a5). The distinction is
not capability — it is whether the agent treats ambiguity as something to surface or to resolve silently.
""",

    "Autonomous Decision Record — Good vs Bad": """\
#### Interpretation — The Cumulative Decision Record

The stacked bars give a cleaner view of the absolute decision volume. Two observations stand out:

**Agent_3 made the most autonomous decisions (5)** — reflecting the highest-involvement,
highest-exploration agent in the framework. Despite the volume, its 80% quality rate (4 good,
1 bad) holds up. Co-design mode does not degrade decision quality even under high iteration
pressure.

**The framework's overall autonomous decision quality is 83%** (20 good, 4 bad across all agents).
This is a meaningful number for calibrating expectations: in roughly 1 in 6 unspecified decisions,
an LLM agent in this framework will make a choice that requires correction. That rate is tolerable
*if* the KBD mechanism surfaces the uncertainty before the decision propagates. It becomes
costly when the wrong decision is made silently and caught late.

The four bad decisions (agent_1a×1, agent_1b×1, agent_2×1, agent_3×1) map neatly onto the
changelog corrections for those agents. None were catastrophic in isolation; agent_1a's was
costly because of its cascading position in the pipeline, not because it was technically more
egregious than the others.
""",

    "Change Taxonomy: Deviations + Scope Expansions": """\
#### Interpretation — Most "Deviations" Are Not Agent Failures

The pie chart is the most important corrective in this notebook. Break down the origins:
- **"orch" (orchestrator-initiated):** the largest single origin. These are scope expansions
  requested by the human — Lorenz/Gini metrics in analytics, dashboard layout adaptations,
  extra staging models. They appear in deviation counts but are evidence of productive co-design,
  not agent failure.
- **"agent":** the only origin type that reflects autonomous agent decision-making. Roughly 30%
  of all documented changes.
- **"external":** tool ecosystem forcing functions — dbt-expectations deprecation, filtering
  rule constraints. The agent had no choice.
- **"cascade":** upstream debt passed downstream — agent_1b absorbing agent_1a's _view suffix.

The stacked bar (right) shows which agents absorbed which types of changes. Agent_3 and agent_4
are dominated by "orch" (purple) — confirming that their high change counts reflect orchestrator
enrichment. Agent_1b has a significant "cascade" and "external" stack — confirming that its
deviation rate was driven by factors outside its control.

**If you removed "orch" and "external" origins from the deviation counts, the agent failure
rate across the framework would drop by roughly 50%.** The taxonomy is not an excuse; it is
a correction to a measurement that was capturing the wrong thing.
""",

    "Error Detection Latency": """\
#### Interpretation — Who Caused Systemic Cost?

The left panel (error detection latency) shows that most agents either caught their own errors
(latency=0) or had them caught at the immediate next gate (latency=1). No error propagated beyond
one stage — a direct validation of the gate architecture's effectiveness.

The centre panel (Cascade Amplification Factor) is where the real story is. Agent_1a's CAF=4.0
means a single deviation generated four times its weight in downstream rework. Every other agent
has CAF ≤ 1. This is the naming contract amplification effect: one wrong string ripples to every
downstream consumer of that string. Agent_1b's three deviations, by contrast, produced CAF=0 —
all absorbed locally, no downstream cost.

The right panel (Contract Debt Score) translates this into absolute downstream burden. Agent_1a
imposed 4 rework entries on the system; agent_3 imposed 2 (its seller cancellation bug fix
required dashboard adaptation); all others imposed 0. The ranking by contract debt is completely
different from the ranking by raw deviation count — which is precisely the point.

**The operational implication:** gate review effort should be front-loaded on agents with
high-cascade-risk tasks (naming-contract-heavy, shared-output-producing) rather than distributed
uniformly across all agents. Agent_1a warranted more scrutiny at GATE-0 than it received.
""",

    "Information Flow & Cascade Propagation": """\
#### Interpretation — The Cascade Sankey

The Sankey diagram visualises what the bar charts stated numerically: the cascade from agent_1a's
_view suffix naming decision entered the pipeline at the top and was fully absorbed at the
agent_1b boundary. The lower half of the diagram — mart models, Dagster, analytics, dashboard,
documentation — shows clean, uninterrupted flow.

The most significant visual feature is what is *absent*: no red flows reach the right side of
the diagram. This confirms that the gate architecture achieved its primary design goal —
containing blast radius. The intermediate cascade nodes ("_view naming cascade",
"dbt-expectations deprecation") appear and disappear within the first two agents, acting as
shock absorbers.

The width of the links represents relative rework cost. The _view cascade link (width=4) is
visibly wider than any other link, confirming that it was the single most expensive event in
the framework. The concurrent coordination overhead node (link from agents 3+4 to each other)
is comparatively narrow — live Parquet schema coordination added cost but not catastrophically.

**For a reader unfamiliar with the technical details:** this diagram shows that a naming mistake
at the very start of the pipeline created extra work in the next two steps, and then the rest of
the pipeline ran clean. The error was contained and did not reach the final products.
""",

    "Contract Surface Severity Distribution": """\
#### Interpretation — Most Contracts Held; One Didn't, and It Was the Naming One

The severity bar confirms that 5 of 8 contract surfaces recorded no violation at all ("—" or
"OK"). One Critical violation, one Low, one Informational. That's a clean record for a system
where 8 stateless agents had to agree on shared strings, schemas, and paths without runtime
enforcement.

The Critical violation (BigQuery table names, _view suffix) is the entire cascade story of Act 3
compressed into a single data point. The Parquet schema alignment between agents 3 and 4 (Low
severity) was resolved through live coordination during the concurrent phase — a process that
worked, but only because the orchestrator was actively monitoring both agents simultaneously.

The informational ADR authorship flag (co-authored, v2+ annotation) is worth noting: it is not
a bug but a documentation debt. When two parties co-produce a document, the ownership attribution
becomes ambiguous. This is a common failure mode in human teams too; the framework surfaced it
explicitly, which is better than leaving it unresolved.

**The structural finding:** ALL violations were naming violations — exact string mismatches, not
semantic disagreements. No two agents disagreed about data types, schema structure, or logical
design. This suggests that LLM agents are reasonably good at semantic alignment when given
sufficient context, but unreliable at exact-string conventions without explicit validation.
""",

    "Human Orchestrator Involvement Intensity": """\
#### Interpretation — A Bimodal Distribution, Not a Continuum

The involvement bar chart does not show a smooth gradient from minimal to very high. It shows
two clusters: agents 1a, 1c, 1d, 2, 5 at involvement ≤ 2 (green shades), and agents 3 and 4 at
involvement ≥ 4 (orange/red). Agent_1b (involvement=3, amber) sits alone in the middle.

This bimodal structure is meaningful. It suggests the framework naturally partitioned into two
operational modes: a large autonomous mode covering infrastructure, testing, and documentation,
and a small co-design mode covering analytical and UX work where human judgment was the primary
quality driver. The design choice to run agents 3 and 4 concurrently (⇌ annotation) reflects
the orchestrator's awareness that the co-design phase was a distinct, more intensive operation
requiring live coordination.

Agent_1b's position at involvement=3 is the outlier — the correction mode agent. It sits in
the friction zone not by design, but because it inherited cascade debt from agent_1a and
encountered tool ecosystem turbulence from dbt-expectations deprecation. The moderate involvement
it required was reactive, not planned. This is the least desirable operational mode, as §8b will
confirm through the quadratic output richness curve.
""",

    "Co-Design Mode: Output Richness vs Human Involvement": """\
#### Interpretation — The Friction Zone: Why Half-Measures Fail

The U-shape is the most structurally important finding in Act 4. At first glance, you might
expect a simple positive relationship: more involvement → better outputs. The data shows
something more nuanced — and more prescriptive.

**Involvement 1–2 (autonomous):** Agents operating with minimal oversight produce decent output
richness. They have clear mandates and execute them cleanly. The output may not be remarkable,
but it's solid. Agent_1c (involvement=1, richness=4) is the exemplar: the least supervised agent
produced the fourth-richest output.

**Involvement 3 (friction zone):** The vertex of the quadratic — the *minimum* richness point —
sits near involvement=2.6. Agent_1b at involvement=3 has the lowest output richness of any agent.
This is not coincidence. When the orchestrator's role is primarily *corrective* (fixing errors,
absorbing cascade, managing deprecated APIs) rather than *enriching* (brainstorming new value),
the interaction overhead reduces the agent's ability to produce clean, rich outputs without
adding creative value. The orchestrator is spending their attention on damage control, not
on quality uplift.

**Involvement 4–5 (co-design):** The richest outputs in the framework. Agents 3 and 4, despite
(because of?) heavy orchestrator involvement, produced the most analytically distinctive work.
The Lorenz curves, Gini coefficients, and HHI concentration metrics in agent_3's notebooks
exist because the orchestrator was brainstorming, not just correcting.

**The design implication is hard:** either trust the agent fully, or commit to co-design. Partial
involvement — where you're correcting mistakes but not enriching outputs — is strictly worse than
either alternative.
""",

    "Deviations vs Scope Expansions": """\
#### Interpretation — Scope Expansion Origin Determines Its Meaning

The stacked bar separates deviations (red) from scope expansions (purple). The ★ annotation
marks agents where scope expansions exceeded 1 — both are orchestrator-driven enrichment, not
agent overreach. Without the ★, agent_3's stack of 5 scope expansions would look like the most
undisciplined agent in the framework.

The scatter below (RQ-2) makes the involvement→scope_expansion relationship explicit: r = 0.86
is a strong positive correlation. Scope expansions concentrate in high-involvement agents
precisely because the orchestrator is generating them. This is not a flaw in the agents; it is
the orchestrator's fingerprint on the output.

**The diagnostic question this chart enables:** if you see an agent with high scope expansion
count, ask first: what was their involvement score? If involvement ≥ 4, the expansions are
likely orchestrator-generated value. If involvement ≤ 2, they may reflect an agent operating
beyond its mandate without authorisation. These are opposite interpretations of the same metric;
involvement score disambiguates them.

In this framework, every agent with scope_expansions > 1 had involvement ≥ 4. There were no
cases of high expansion + low involvement — the pattern held cleanly.
""",

    "RQ-5: Human Leverage Ratio": """\
#### Interpretation — The Efficiency Trade-Off Made Explicit

The leverage chart is where the cost of co-design becomes visible. Agent_1c (leverage=9.0)
delivered 9 requirements with a single unit of orchestrator attention — the framework's best
autonomous efficiency. Agent_4 (leverage=0.5) delivered 2 requirements at involvement=4 — the
lowest leverage in the framework.

But leverage and output richness run in opposite directions. Agent_1c's output richness is 4.
Agent_4's is also 4. They achieved equivalent richness through completely different mechanisms:
agent_1c through well-specified autonomous execution, agent_4 through intensive co-design
iteration. The former required almost no orchestrator time; the latter required near-continuous
involvement.

**The practical framework design question:** for tasks where the human's domain judgment is
the primary quality driver (analytical decisions, UX choices, communication strategy), accept
low leverage as the cost of co-design. For tasks where the specification can be fully detailed
in advance (data ingestion, testing, documentation), optimise for leverage — minimise involvement
without sacrificing fidelity.

Agent_1c demonstrates that leverage of 9.0 is achievable in this framework. The conditions: a
technically well-defined task, resolved upstream contracts, a clean handoff from gates 0–1. These
conditions don't happen by accident — they require investment earlier in the pipeline.
""",

    "Parallelizability Utilization": """\
#### Interpretation — 33% Parallelism and What the Changelog Reveals

The left panel shows that only 1 of 3 viable parallel pairs was executed. The two foregone
pairs — a1c+a1d (mart models + tests) and a4+a5 (dashboard + documentation) — represent
compressed delivery time that was left on the table. Agent_1c must finish before agent_1d
begins (tests depend on mart models), but this sequential constraint could be tightened: as
soon as agent_1c's first mart model passes, agent_1d could begin parallel test authoring. The
sequential execution was a conservative choice, not a technical necessity.

The right panel (changelog entries) shows review effort concentration. Agent_3's 12 entries
reflect both the highest involvement and the concurrent parallel phase — every live coordination
event during the a3+a4 simultaneous execution appears in the changelog. Agent_5's 0 entries is
the inverse signal: a perfectly spec-compliant agent requires no review action, no correction,
no logged decision. This is the operational ideal for autonomous agents.

**The overall picture:** the framework is deliberately sequential with one parallel exception.
That conservatism reduced coordination overhead and cascading risk, but at a delivery time cost.
As naming contracts stabilise and parallel phase protocols mature, the framework could capture
the two remaining parallel pairs without proportionally increasing risk.
""",

    "Involvement vs Review Effort": """\
#### Interpretation — Involvement Predicts Review Burden Linearly

The scatter confirms what the bar chart suggested: there is a strong positive relationship
between how involved the orchestrator was with an agent and how many changelog entries that
agent generated. Higher involvement does not just mean more iterations — it means more
*documented* gate decisions, more logged corrections, more recorded scope changes.

This has a direct capacity planning implication. If an orchestrator is planning a multi-agent
run and estimates involvement scores in advance, they can predict their own review burden. An
agent at involvement=5 (agent_3, 12 changelog entries) required roughly 6x the review effort
of an agent at involvement=2 (agent_1a, 4 entries). Treating all agents as equal review burdens
in a project plan is systematically incorrect.

The exclusion of agent_5 (0 entries) from this scatter is itself a finding: an agent that
requires no changelog entries is one that either performed perfectly or was not reviewed. In
this case, it was the former — zero deviations, zero corrections. For planning purposes, agents
assigned to well-specified, low-risk documentation tasks can be modelled with near-zero review
overhead.
""",

    "Eight-Dimension Agent Performance Radar": """\
#### Interpretation — Profile Shapes Reveal Collaboration Mode

The radar is most useful not as a ranking tool but as a **profile taxonomy**. Three distinct
shape signatures emerge:

**The "well-rounded autonomous" profile (a1c, a1d, a5 — green):** Large, balanced polygons
covering most of the radar area. High on fidelity, first-pass, decision quality, and cascade
cleanliness. Scope discipline is high (they stayed in mandate). These agents are the framework's
operational backbone — reliable, low-maintenance, and predictable.

**The "cascade cost" profile (a1a — green but dented):** Similar to the autonomous profile
except for a notable depression in the Cascade Cleanliness dimension. The _view suffix event
is visible here as a shape anomaly. The agent was autonomous and generally competent, but the
one naming error it made produced disproportionate systemic cost.

**The "co-design richness" profile (a3, a4 — red/orange):** Characteristically *asymmetric* —
high output richness, high decision quality, but lower fidelity, first-pass rate, and scope
discipline. These agents traded protocol compliance for analytical depth. The asymmetry is the
signature of co-design mode: the dimensions that reflect compliance are depressed; the dimensions
that reflect quality and exploration are elevated.

Reading the radar correctly means understanding that a large, irregular polygon is not a failure
— it is a different mode of operation with different success criteria.
""",

    "Three Collaboration Modes — Radar Comparison": """\
#### Interpretation — Each Mode Has a Characteristic Shape Signature

The three-panel view is the payoff of the entire analysis. Separating agents by collaboration
mode before comparing removes the confound that makes the combined radar hard to read.

**Autonomous Mode (left):** Agents a1a, a1c, a1d, a2, a5 show consistently balanced profiles.
The one visible weakness is agent_1a's cascade cleanliness dip — visible even in the autonomous
mode panel, where every other agent scores clean. This confirms that a1a is a genuine outlier
in this mode, not a co-design agent whose metrics were misattributed.

**Correction Mode (centre):** Agent_1b alone occupies this panel. Its profile is notably lower
on Knowledge Boundary Detection — the silent failure + cascade absorption story made visible in
the radar format. It scores reasonably on decision quality and output richness, but the KBD gap
and the lower first-pass rate confirm that this mode involves the orchestrator fixing problems
rather than building on a clean foundation.

**Co-Design Mode (right):** Agents a3 and a4 show the asymmetric richness signature — strong
output richness and decision quality, low scope discipline (high expansion rate). The shape is
recognisably different from both other modes. If you saw this radar profile without knowing the
involvement score, you might diagnose it as an underperforming agent. With the involvement score,
it reads correctly as a high-investment co-design output.

**The diagnostic value:** in future deployments, if an agent's radar profile matches the
"correction mode" signature (low KBD, low first-pass, moderate everything else), it is a signal
to investigate whether it is absorbing upstream cascade rather than failing independently.
""",

    "DELIVERABLE INVENTORY": """\
#### Interpretation — What 8 Days of Orchestrated AI Produced

23 distinct deliverable items. Read this list slowly before engaging with the metrics.

The framework delivered: a working 9-table ingestion pipeline, 9 staging models, 7 mart models
with 76 passing tests, a fully configured Dagster orchestration layer with daily scheduling,
3 analytical notebooks computing 11 business metrics plus concentration analytics, 6 Parquet
datasets, a 5-page interactive Streamlit dashboard with 4 global filters, a complete
documentation set including architecture diagrams, ADRs, an executive slide deck, and a
technical report.

This is a professional-grade, submittable data engineering project. The most important finding
in this section is not any metric — it is the completeness of the output.

Agent_3's contribution (3 notebooks, utils.py, 6 Parquet files) represents the largest single
deliverable surface. Its analytical richness — the Lorenz curves, Gini coefficients, HHI
concentration metrics that the orchestrator brainstormed — would not exist in a purely
autonomous execution. Agent_5's deliverables (architecture diagrams, technical report, slide
deck, ADRs) represent the kind of systematic documentation that human teams routinely deprioritize
under delivery pressure. The framework produced it by design, not by effort.

The orchestrator's direct contribution (CLAUDE.md, changelog.md, progress.md) is 3 items out
of 23 — a 13% direct contribution to the deliverable count, with 87% produced by agents. The
leverage is real.
""",

    "HUMAN vs AI FRAMEWORK COMPARISON": """\
#### Interpretation — Neither Side Wins Cleanly

The comparison table avoids the mistake of declaring a winner. Read each dimension as a genuine
trade-off rather than a score:

**Where the AI framework wins unambiguously:** documentation quality. The spec-driven approach
(agent_5, zero deviations) produced a complete, consistent documentation set. Human teams under
delivery pressure routinely defer documentation. The framework made it non-optional.

**Where the human team wins unambiguously:** tool discovery speed and analytical domain knowledge.
The dbt-expectations deprecation would have been caught during tech selection in a human team
with senior engineer involvement. It was discovered mid-agent in the AI framework. Agent_3
required heavy co-design to produce analytically interesting insights — a senior analyst brings
that judgment to day one.

**Where the comparison is genuinely ambiguous:** parallel execution (AI framework captured 33%
of potential parallelism; a human team naturally parallelises but informally), knowledge transfer
(AI framework's stateless sessions lose context between runs; a human team retains tribal
knowledge but loses it to attrition), deviation handling (gate reviews vs. PR review — similar
mechanism, different overhead profiles).

**The honest verdict from this comparison:** the AI framework is not cheaper if you count
specification effort as a real cost. It produces equivalent output with different labour inputs.
The human team spends effort on execution; the AI framework shifts that effort to specification
and orchestration. Whether the shift is advantageous depends entirely on the organisation's
comparative advantage in specification vs. execution skill.
""",

    "FRAMEWORK DESIGN FINDINGS": """\
#### Interpretation — Weighting the 16 Findings

Not all 16 findings are equally actionable. A reader deciding where to invest next should weight
them by the combination of: (a) magnitude of the event observed, and (b) ease of implementation.

**Highest priority (high impact, implementable immediately):**
- **F-05** (naming contract validation at gate entry): prevents the highest-cost event in the
  framework. A 5-line shell assertion script at GATE-0 would have caught the _view suffix before
  agent_1b began. ROI is extremely high.
- **F-09** (silent failure declaration convention): a directive template change requiring agents
  to emit `[UNCERTAIN: ...]` before unspecified decisions. Converts silent failures into visible
  choices. Near-zero implementation cost.

**High priority (high impact, moderate implementation):**
- **F-04** (avoid the friction zone): requires deliberate pre-assignment of agents to either
  autonomous or co-design mode. Harder than F-05/F-09 because it requires upfront task
  characterisation.
- **F-10** (pre-agreed Parquet contracts before parallel phases): one YAML file per parallel phase.
  Moderate effort, prevents the highest scope expansion count observed (a4: 5 expansions).

**Lower priority (useful, not urgent):**
- F-13 (canonical utility module), F-14 (tool version pinning), F-15 (commit attribution) are
  all genuine improvements but address lower-frequency or lower-impact issues.

The 16 findings are not a backlog to work through sequentially. F-05 and F-09 alone would have
prevented the largest single costly event in this dataset. Start there.
""",
}

# Executive summary cell (goes after the last existing cell)
EXECUTIVE_SUMMARY = """\
---

## Executive Summary

*This summary is written as an independent assessment, not as a continuation of the analysis.
It draws on all six acts but is intended to be readable without having read them.*

---

### What Was Assessed

Eight specialist LLM agents executed a production-grade data engineering project end-to-end:
Meltano ingestion → dbt transformation → BigQuery → Dagster orchestration → Streamlit dashboard
→ documentation. Agents worked sequentially (with one parallel phase) under written directives,
gate-reviewed by a single human orchestrator. The project delivered 23 distinct deliverables
in 8 days.

---

### One-Paragraph Finding Per Act

**Act 1 — Framework Design:** Directives averaged 1,010 words at moderate constraint density
(avg 2.07%). Longer directives are not better directives — word count showed near-zero
correlation with fidelity (r = -0.17). Constraint density is counterintuitively *positively*
correlated with deviation rate, driven by a task-complexity confound: technically challenging
tasks received both denser constraints and more tool-ecosystem failures. The only reliable
predictor of low deviation was stable upstream contracts, not directive length or density.

**Act 2 — Individual Performance:** Raw deviation rates are deeply misleading without an
involvement score as context. The three cleanest performers (agents 1c, 1d, 5) operated in
stable, well-defined task environments. The highest-deviation agents (3, 4) were in intensive
co-design mode — their "failures" are the orchestrator's fingerprint on enriched outputs. The
most dangerous failure mode — silent autonomous decision on an ambiguous constraint — appeared
once (agent_1a, _view suffix) and produced the highest systemic cost in the framework.

**Act 3 — System Effects:** One naming decision by agent_1a (CAF = 4.0) caused more downstream
rework than all other agents combined. Gate-based isolation with git worktree separation
successfully contained the blast radius — no cascade reached the mart model layer or beyond.
Every contract violation was a naming violation, not a semantic disagreement. The architecture's
primary design bet (gates contain errors) was confirmed empirically.

**Act 4 — Human–AI Dynamics:** The U-shaped relationship between involvement and output richness
is the most structurally interesting finding. Involvement = 3 (correction mode, agent_1b) produced
the *worst* output richness — worse than near-autonomous agents operating alone. The productive
collaboration modes are either full autonomy (involvement ≤ 2, agent-driven quality) or full
co-design (involvement ≥ 4, orchestrator-enriched quality). Partial involvement generates overhead
without generating value.

**Act 5 — System Assessment:** The framework produced a complete, submittable project. The
deliverable inventory is impressive by any measure. The human team comparison reveals a genuine
trade-off: the AI framework produces more systematic documentation but requires substantially
more upfront specification effort. Analytical originality required co-design investment —
something a senior analyst brings implicitly but an LLM agent needs explicitly brainstormed with.

**Act 6 — Synthesis:** 16 findings across the six acts converge on three high-leverage design
changes: naming contract validation at gate entry (F-05), a silent failure declaration convention
(F-09), and formalised intermediate output contracts before parallel phases (F-10). These three
changes would address the highest-cost events observed in this dataset.

---

### Top 5 Cross-Cutting Insights

**1. The orchestrator's most valuable contribution was specification authorship, not supervision.**
Every agent failure traces to a specification gap, not an LLM capability limit. Agent_1a's silent
naming decision was not caught because no directive said "flag naming choices before proceeding."
The cascade that followed was a specification debt, not an agent error. This shifts blame — and
the improvement investment — from the agent to the architect.

**2. The deviation taxonomy reveals that fewer than half of all documented changes were autonomous
agent failures.** Removing orchestrator-initiated enrichments and tool-ecosystem-forced adaptations
from the deviation count reduces the "failure" count by roughly 50%. The framework's raw deviation
metrics systematically overstate agent failure. Any evaluation of LLM-based pipelines that doesn't
distinguish these origins is measuring the wrong thing.

**3. The gate architecture empirically validated its primary design goal.** A severity-4 naming
violation (the highest-cost event in the dataset) was fully absorbed at the agent_1b gate boundary
with zero propagation to mart models. This is not an accident of timing — it is what gate-based
isolation is designed to do. The overhead of gate reviews demonstrably pays off in reduced cascade
blast radius.

**4. Autonomous agents at stable pipeline layers (1c, 1d, 5) approached near-zero orchestrator
overhead.** These agents delivered on specification with minimal involvement, high first-pass rates,
and clean cascade scores. They represent the framework's most cost-effective operating regime and
the best argument for its scalability: once upstream contracts are settled, downstream agents
can operate essentially unsupervised.

**5. This analysis measures compliance. It does not measure whether what was complied with was
correct.** Agent_1c's near-perfect fidelity is held up as exemplary throughout the notebook. But
fidelity is only meaningful if the specification was sound. The framework has no mechanism to
reward an agent that improves on specification, and no metric to evaluate whether the specified
approach was the best approach. A framework that perfectly executes a suboptimal design has
failed — but it will score well on every metric here.

---

### Was It Worth It? — A Cost-Benefit Assessment

No session time was instrumented, so this is directional reasoning, not measurement.

The orchestrator produced approximately 8,900 directive words across 9 files (including CLAUDE.md).
At an estimated 1.5–2 hours per directive (research, constraint authoring, cross-agent dependency
checking), specification effort was roughly 14–18 hours. Gate reviews across 4 gates, including
the co-design-intensive agent_3 phase, add perhaps another 10–15 hours of active involvement.
Total estimated orchestrator investment: 25–33 hours.

Against that, the framework delivered: 9 staging models, 7 mart models with 76 passing tests,
a complete Dagster orchestration layer, 3 analytical notebooks computing 11 metrics with
concentration analytics, 6 Parquet datasets, a 5-page Streamlit dashboard, and a full
documentation suite. A human team delivering equivalent output would conservatively require
3–4 engineer-weeks (120–160 hours).

**The verdict is positive but conditional.** If specification effort is counted as skilled labour
(which it is — it cannot be delegated to a non-technical PM), the productivity gain is real but
narrower than headline claims suggest. The framework does not eliminate the need for deep technical
expertise. It *relocates* it from execution to specification and review. Whether that relocation
is advantageous depends on whether the organisation is better at writing precise constraints than
at executing them.

The clearest advantage is one rarely cited in AI productivity literature: **documentation
completeness**. Human teams under delivery pressure defer documentation. This framework made
documentation a first-class deliverable with its own specialist agent. That is genuinely valuable,
and it is not captured in lines-of-code or story-point comparisons.

---

### The Specification Quality Paradox

This notebook's metrics reward compliance. They do not reward wisdom.

The framework cannot distinguish between two scenarios: (a) an agent that followed a correct
specification faithfully, and (b) an agent that followed an incorrect specification faithfully.
Both produce the same fidelity score. Only the downstream outcome — which may not be measured
until much later — reveals the difference.

Agent_1c is the example that makes this uncomfortable. Its deviation rate of 0.11 (one minor
deviation on nine requirements) earns it the best fidelity record of any multi-requirement agent.
But agent_1c benefited from the best specification conditions in the framework: resolved upstream
contracts, a clean handoff from agents 1a and 1b, and a technically well-defined task surface.
Its high fidelity may reflect a well-written spec in a stable environment as much as it reflects
agent quality.

More troublingly: the framework's incentive structure penalises agents that improve on their
specification. If agent_1c had identified a materially better mart model design and deviated to
implement it, the deviation would appear in the metrics as a failure. The framework rewards
compliance with the spec that was written, not compliance with the spirit of what the project
needed. Agent_3's most valuable contributions — the Lorenz/Gini/HHI analytics — are recorded
as "scope expansions" (orchestrator-initiated), systematically misattributing their analytical
value.

A mature evaluation framework for LLM agents needs a mechanism to assess not just *whether* the
agent followed its specification, but *whether following that specification was correct*. This
analysis does not provide that mechanism. It should be built.

---

### Critique — An Honest Assessment

*Written as an external evaluator, not as the framework's advocate.*

**What does not work in the framework:**

*The stateless agent model is fundamentally mismatched with iterative design.* Each agent
receives a directive and begins from zero, with no persistent memory of what prior agents
decided, discovered, or struggled with. The orchestrator is the sole cognitive state of the
system — a single point of failure and a bottleneck. When agent_2 needed to adapt its Dagster
AssetKey wiring to agent_1a's _view deviation, it required manual context injection from the
orchestrator. A genuinely robust multi-agent system needs either shared state or explicit context
propagation, not just well-written directives that try to anticipate every dependency.

*The involvement scale is doing too much work for too little precision.* A single ordinal score
(1–5) is expected to capture interaction frequency, intervention type (corrective vs. enriching),
the degree to which final output reflects agent vs. orchestrator judgment, and whether the mode
was planned or emergent. These are four distinct variables compressed into one. The U-shape
finding is interesting precisely because it partially disaggregates corrective from enriching
involvement — but that disaggregation happened at analysis time, not measurement time. The scale
was never designed to carry this distinction cleanly.

*Silent failure has no structural countermeasure.* Agent_1a made a naming decision without
declaring uncertainty. The directive did not require it to. The gate review caught it one step
late — at a cost of 4 rework entries. Adding a `[UNCERTAIN: ...]` marker to the directive format
would have converted this from a silent failure to a visible choice catchable in seconds. This
is the most straightforward fix in the entire recommendation set, and it requires only a template
change. The fact that it wasn't in place at project start is a specification design oversight.

*The parallel phase was under-prepared.* Agents 3 and 4 entered concurrent execution without a
written Parquet schema contract. The claim that this "worked" is true in the sense that the
project delivered. But agent_4 ended up with the highest scope expansion count of any agent (5),
driven by live adaptation to agent_3's outputs. That is not a success story. It is evidence that
the intermediate contract was never formalised and that the concurrency was managed through real-
time orchestrator intervention rather than design. The framework correctly identified 3 viable
parallel pairs but captured only 1, and executed that 1 with insufficient preparation.

**What does not work in this analysis:**

*N=8 is not a sample — it is an inventory.* Every Pearson correlation, trend line, and
quadratic fit in this notebook is computed on 8 observations. With N=8, a Pearson r=0.63 has a
95% confidence interval that spans from approximately +0.1 to +0.9 — the point estimate carries
substantial uncertainty. The quadratic fit for the U-shape (3 parameters, 8 data points, 5
effective degrees of freedom) will fit almost any smooth function. These results are descriptive
of *this specific set of agents*. They are not generalisable findings about LLM orchestration
systems. Presenting them alongside precise decimal values (r = 0.631, vertex = 2.6) implies a
statistical precision that the sample size does not support.

*The measurement instruments are retrospective and self-reported.* Involvement scores, decision
quality ratings, silent failure counts, and output richness assessments were all assigned by the
orchestrator after the project completed — by the same person who ran the framework and wrote the
directives. There is no independent verification, no second rater, no inter-rater reliability
check. The orchestrator may unconsciously rate agents they found easier to work with as higher
quality, rate their own involvement as lower than it was (self-serving attribution of credit to
agents), or misremember which decisions were autonomous vs. orchestrator-directed. These biases
are standard in retrospective assessment and the analysis does not acknowledge them adequately.

*The constraint density metric has a known flaw that was not corrected.* The keyword list
(`must|shall|required|not|only|never|always|exactly`) includes the word "not" — which appears
extensively in descriptive text ("is not", "does not", "should not consider") that is not
constraining in any meaningful sense. Agent_1d's directive (lowest density at 1.39) likely
contains many descriptive negations inflating the count. The metric was never validated against
human annotation of actual constraint sentences. A grep-based proxy that hasn't been calibrated
against human judgment should be presented with more epistemic humility than it is here.

---

### Key Issues — Ranked by Severity

| # | Issue | Severity | Act |
|---|---|---|---|
| 1 | No structural mechanism for agents to declare uncertainty before acting | Critical | §4, §6 |
| 2 | Stateless architecture forces orchestrator to be sole cognitive memory of the system | High | §8 |
| 3 | Parallel phase (a3+a4) entered without a written intermediate output contract | High | §10 |
| 4 | Specification metrics incentivise compliance over wisdom; no reward for spec improvement | Medium | §2, §13 |
| 5 | Tool ecosystem compatibility not pre-validated at directive authoring time | Medium | §5, §14 |
| 6 | 67% of viable parallelism was not captured (2 of 3 parallel pairs untested) | Medium | §10 |
| 7 | Measurement instruments are retrospective, self-reported, and unvalidated | Medium | §14 |

---

### Recommended Improvements — Prioritised

**P1 — Silent failure declaration protocol** *(immediate, directive template change)*
Add a mandatory convention to every directive: agents must emit `[UNCERTAIN: decision, option_chosen,
alternative_considered]` before executing any decision not covered in the directive. Convert
silent failures into visible choices. This prevents the highest-cost single event observed in
this dataset (agent_1a cascade, CAF=4.0) from recurring without changing any code.

**P2 — Naming contract validation at gate entry** *(immediate, 10-line shell script)*
Before any downstream agent begins, assert that all shared naming surfaces match: stream_name
== sources.yml table names, Parquet column names match declared schema, import paths match
declared module structure. A failed assertion blocks the downstream agent before it writes a
single line on a false foundation.

**P3 — Formalise intermediate output contracts before parallel phases** *(pre-parallel, 1 YAML file)*
Write `contracts/parquet_schema_v<n>.yaml` before agents 3 and 4 begin. Include column names,
types, nullable flags, and join keys. Gate-0 for the parallel phase signs off on this contract.
Neither agent starts until both contract producers and consumers have confirmed alignment.

**P4 — Separate the involvement score into two dimensions** *(next framework iteration)*
Replace the single 1–5 scale with: (a) Interaction frequency (how often the orchestrator
intervened) and (b) Intervention type (corrective / enriching / directive). This makes the
U-shape finding actionable — you can design for "low frequency, high enrichment" rather than
trying to optimise a blended score. It also enables better attribution: enriching interventions
belong to the orchestrator's contribution to output quality; corrective ones belong to the
agent's failure.

**P5 — Instrument the next run for real-time data** *(next framework iteration)*
Log agent session start/end times separately from commit timestamps. Have agents emit structured
`[DECISION: type, choice, rationale]` markers at every non-trivial autonomous decision in real
time. Record orchestrator intervention timestamps and types during sessions. This converts the
most critical retrospective estimates (involvement score, decision quality, silent failures) into
objective measurements — and eliminates the attribution bias inherent in self-reporting.

---

### The Verdict

This framework works. It delivered a complete, professional-grade data engineering project in
8 days with one primary orchestrator. The blast radius containment worked. The autonomous agents
at stable pipeline layers required near-zero oversight. The documentation quality — systematic,
complete, co-authored with a specialist agent — exceeded what a comparably-staffed human team
would typically produce under similar time pressure.

But it works in a specific regime: **technically well-defined deliverables, an orchestrator with
deep domain expertise to write precise constraints, and a project structure with clear linear
or modestly parallel execution paths**. Outside that regime — and agent_3's analytics phase
shows exactly where the boundary is — the framework degrades into expensive co-design that
requires the same expert judgment the human alternative would have applied directly.

The framework does not eliminate the need for expertise. It relocates expertise from execution
to specification. Whether that is an improvement depends on whether the organisation is better
at writing precise constraints than at executing them. For organisations with strong technical
leads and inconsistent execution capacity, the answer is likely yes. For organisations with
strong execution but weak specification practices, adoption of this framework without investing
in specification quality will produce exactly the silent failures and cascade events that this
analysis documented.

The most important open question this analysis cannot answer: **was the 25–33 hours of
specification and orchestration effort cheaper than having an experienced engineer execute the
project directly?** That question requires actual time logging. Until it is answered with data
rather than estimates, claims about productivity gains in LLM agentic systems remain directional,
not measured.

The framework has earned a second run. With the five improvements above implemented, the second
run would produce cleaner data, fewer cascade events, and a more honest measurement of where
the productivity gains actually come from.

---
*Notebook v4 · Generated by `scripts/generate_analysis_notebook.py` +
`scripts/patch_notebook_v4.py` · All data from primary sources: directive files, changelog.md,
progress.md, orchestrator involvement notes.*
""",

# ------------------------------------------------------------------
# Main patching logic
# ------------------------------------------------------------------
def patch():
    with open(NB_PATH) as f:
        nb = json.load(f)

    cells = nb["cells"]
    new_cells = []

    for cell in cells:
        new_cells.append(cell)

        if cell["cell_type"] != "code":
            continue

        src = "".join(cell["source"])

        # Find matching interpretation
        for anchor, interp in INTERPRETATIONS.items():
            if anchor in src:
                new_cells.append(md(interp))
                break  # only one interpretation per code cell

    # Append executive summary after the last cell
    new_cells.append(md(EXECUTIVE_SUMMARY))

    nb["cells"] = new_cells

    with open(NB_PATH, "w") as f:
        json.dump(nb, f, indent=1)

    n_md   = sum(1 for c in new_cells if c["cell_type"] == "markdown")
    n_code = sum(1 for c in new_cells if c["cell_type"] == "code")
    print(f"Patched: {NB_PATH}")
    print(f"Cells: {len(new_cells)} ({n_md} markdown, {n_code} code)")
    print(f"  — {len(new_cells) - len(cells)} cells added (interpretations + executive summary)")

if __name__ == "__main__":
    patch()
