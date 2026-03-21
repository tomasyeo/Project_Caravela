"""
Generate notebooks/04_agent_performance_analysis.ipynb
v3.1 — Bug-fix pass:
  - r_density corrected to +0.541 (positive, not negative); finding rewritten
  - spec_roi = 0 addressed with adjusted metric + explicit note
  - agent_1b now plotted in §11b "Correction Mode" panel
  - agent_5 KBD fillna(1.0) not 0 (no uncertain decisions = no failures)
  - §8b co-design quadratic is U-shape (vertex≈2.6 = friction zone), not inverted-U
  - All correlations pre-computed in cell 0 for notebook-wide consistency
  - §5 wording fixed ("changes" not "deviations")

Narrative:
  Act 1 — Context          : Framework structure, directive design
  Act 2 — Agent Performance: Fidelity, decision quality, deviation taxonomy
  Act 3 — System Effects   : Cascade, contract debt, error propagation
  Act 4 — Human–AI Dynamics: Involvement spectrum, leverage, parallel execution
  Act 5 — System Assessment: 8-dim radar, artifacts, human team comparison
  Act 6 — Synthesis        : Findings, implications
"""

import json, os

NOTEBOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "notebooks", "04_agent_performance_analysis.ipynb"
)

def md(source):
    return {"cell_type": "markdown", "metadata": {}, "source": source}

def code(source, outputs=None):
    return {"cell_type": "code", "execution_count": None,
            "metadata": {}, "outputs": outputs or [], "source": source}

cells = []

# ============================================================
# CELL 0 — Imports + complete dataset + pre-computed stats
# ============================================================
cells.append(code("""\
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# ── Palette ─────────────────────────────────────────────────
BLUE   = '#1565C0'; ORANGE = '#E65100'; GREEN  = '#2E7D32'
PURPLE = '#7B1FA2'; TEAL   = '#00838F'; RED    = '#C62828'
AMBER  = '#FF8F00'; GREY   = '#546E7A'; PINK   = '#AD1457'
INV_COLOURS = {1:'#2E7D32',2:'#66BB6A',3:'#FF8F00',4:'#EF6C00',5:'#C62828'}

# ── Master agent dataset ────────────────────────────────────
# constraint_density: constraint words per 100 directive words
#   (computed from actual directive files via grep for
#    must|shall|required|not|only|never|always|exactly)
# Estimation fields (revision_cycles, good/bad decisions, etc.)
# derived from changelog entries, involvement notes, session transcripts.
agents_raw = [
  dict(
    id='agent_1a', role='Meltano Ingestion',
    directive_words=737,  reqs_owned=1,
    deviations=1,         scope_expansions=0,   changelog_entries=4,
    human_involvement=2,  concurrent_with=None,
    revision_cycles=2,
    good_auto_decisions=1, bad_auto_decisions=1,
    silent_failures=1,    total_uncertain_decisions=2,
    downstream_rework_caused=4,
    error_detection_latency=1,
    output_richness=2,    underspecified_redirects=1,
    constraint_density=2.30,
    # cascade/external deviations (excluded from adj_spec_roi)
    cascade_ext_devs=0,
    involvement_notes=(
      'Mostly autonomous. Troubleshot egress plugin BigQuery connectivity. '
      '_view suffix naming deviation not flagged before handoff.'
    ),
  ),
  dict(
    id='agent_1b', role='dbt Staging',
    directive_words=1056, reqs_owned=3,
    deviations=3,         scope_expansions=1,   changelog_entries=5,
    human_involvement=3,  concurrent_with=None,
    revision_cycles=3,
    good_auto_decisions=3, bad_auto_decisions=1,
    silent_failures=1,    total_uncertain_decisions=4,
    downstream_rework_caused=0,
    error_detection_latency=0,
    output_richness=3,    underspecified_redirects=2,
    constraint_density=2.08,
    cascade_ext_devs=2,   # 1 cascade-fix + 1 context-forced (dbt-expectations deprecation)
    involvement_notes=(
      '_view suffix cascade fix. Filtering rule issues. '
      'dbt-expectations deprecation forced alternatives; '
      'some originally planned rules were unsupported.'
    ),
  ),
  dict(
    id='agent_1c', role='dbt Marts',
    directive_words=999,  reqs_owned=9,
    deviations=1,         scope_expansions=0,   changelog_entries=3,
    human_involvement=1,  concurrent_with=None,
    revision_cycles=1,
    good_auto_decisions=2, bad_auto_decisions=0,
    silent_failures=0,    total_uncertain_decisions=2,
    downstream_rework_caused=0,
    error_detection_latency=0,
    output_richness=4,    underspecified_redirects=0,
    constraint_density=2.50,
    cascade_ext_devs=0,
    involvement_notes=(
      'Mostly autonomous — upstream agents resolved blockers. '
      'All 7 mart models passed dbt build on first submission.'
    ),
  ),
  dict(
    id='agent_1d', role='dbt Tests',
    directive_words=1075, reqs_owned=5,
    deviations=1,         scope_expansions=0,   changelog_entries=6,
    human_involvement=1,  concurrent_with=None,
    revision_cycles=1,
    good_auto_decisions=2, bad_auto_decisions=0,
    silent_failures=0,    total_uncertain_decisions=2,
    downstream_rework_caused=0,
    error_detection_latency=0,
    output_richness=4,    underspecified_redirects=0,
    constraint_density=1.39,
    cascade_ext_devs=0,
    involvement_notes='Mostly autonomous. 76/76 tests pass. Clean handoff from agent_1c.',
  ),
  dict(
    id='agent_2', role='Dagster Orchestration',
    directive_words=950,  reqs_owned=8,
    deviations=3,         scope_expansions=2,   changelog_entries=7,
    human_involvement=2,  concurrent_with=None,
    revision_cycles=2,
    good_auto_decisions=2, bad_auto_decisions=1,
    silent_failures=1,    total_uncertain_decisions=3,
    downstream_rework_caused=0,
    error_detection_latency=1,
    output_richness=3,    underspecified_redirects=1,
    constraint_density=1.89,
    cascade_ext_devs=1,   # 1 cascade-fix (adapted to _view AssetKeys from agent_1a)
    involvement_notes=(
      'Some out-of-spec changes, notably folder structure and '
      'incorrect @asset(deps=...) wiring direction. '
      'Orchestrator corrected structural deviations.'
    ),
  ),
  dict(
    id='agent_3', role='Analytics Engineering',
    directive_words=1575, reqs_owned=10,
    deviations=5,         scope_expansions=4,   changelog_entries=12,
    human_involvement=5,  concurrent_with='agent_4',
    revision_cycles=4,
    good_auto_decisions=4, bad_auto_decisions=1,
    silent_failures=0,    total_uncertain_decisions=5,
    downstream_rework_caused=2,
    error_detection_latency=0,
    output_richness=5,    underspecified_redirects=3,
    constraint_density=1.77,
    cascade_ext_devs=0,
    involvement_notes=(
      'Heaviest human involvement. Initial analysis was generic. '
      'Orchestrator brainstormed new insights and value-adds. '
      'Ran simultaneously with agent_4. '
      'scope_expansions = orchestrator-driven enrichment.'
    ),
  ),
  dict(
    id='agent_4', role='Dashboard Engineering',
    directive_words=1235, reqs_owned=2,
    deviations=2,         scope_expansions=5,   changelog_entries=3,
    human_involvement=4,  concurrent_with='agent_3',
    revision_cycles=3,
    good_auto_decisions=2, bad_auto_decisions=1,
    silent_failures=0,    total_uncertain_decisions=3,
    downstream_rework_caused=0,
    error_detection_latency=1,
    output_richness=4,    underspecified_redirects=2,
    constraint_density=2.91,
    cascade_ext_devs=0,
    involvement_notes=(
      'Heavy orchestrator involvement. Streamlit layout modified '
      'based on agent_3\\'s live outputs (concurrent phase). '
      'scope_expansions = adapting to agent_3 co-design outputs.'
    ),
  ),
  dict(
    id='agent_5', role='Documentation & Exec Comms',
    directive_words=1285, reqs_owned=8,
    deviations=0,         scope_expansions=0,   changelog_entries=0,
    human_involvement=2,  concurrent_with=None,
    revision_cycles=1,
    good_auto_decisions=4, bad_auto_decisions=0,
    silent_failures=0,    total_uncertain_decisions=0,
    downstream_rework_caused=0,
    error_detection_latency=0,
    output_richness=4,    underspecified_redirects=0,
    constraint_density=1.71,
    cascade_ext_devs=0,
    involvement_notes=(
      'Orchestrator requested docs/presentations beyond spec. '
      'ADRs co-authored (orchestrator + agent_5). '
      'Zero deviations — followed spec precisely.'
    ),
  ),
]

df = pd.DataFrame(agents_raw)
df['short_id']       = df['id'].str.replace('agent_','a')
df['label']          = df['id'] + '\\n' + df['role'].apply(lambda x: x.split()[0])
df['deviation_rate'] = df['deviations'] / df['reqs_owned']
df['expansion_rate'] = df['scope_expansions'] / df['reqs_owned']
df['spec_efficiency']= df['reqs_owned'] / df['directive_words'] * 1000
df['first_pass_rate']= 1 / df['revision_cycles']
df['auto_decision_quality'] = df['good_auto_decisions'] / (
    df['good_auto_decisions'] + df['bad_auto_decisions']).replace(0, np.nan)
# FIX: agent_5 has total_uncertain_decisions=0 → KBD is undefined (no uncertain decisions = no failures).
# Use fillna(1.0) not 0.0 — absence of uncertain decisions is perfect, not failure.
df['knowledge_boundary_detection'] = (
    (df['total_uncertain_decisions'] - df['silent_failures'])
    / df['total_uncertain_decisions'].replace(0, np.nan)
).fillna(1.0)
df['cascade_amplification_factor'] = df['downstream_rework_caused'] / df['deviations'].replace(0, 1)
df['contract_debt_score'] = df['downstream_rework_caused']
# Adjusted spec_roi: exclude cascade-fix and context-forced deviations
# (these were forced on agents by upstream errors or tool ecosystem constraints,
# not autonomous agent failures — all requirements were delivered per progress.md)
df['adj_devs']    = (df['deviations'] - df['cascade_ext_devs']).clip(lower=0)
df['adj_dev_rate']= df['adj_devs'] / df['reqs_owned']
# FIX: original spec_roi uses raw deviation_rate → collapses to 0.0 for 3 agents
# (agent_1a reqs=1/devs=1; agent_1b reqs=3/devs=3; agent_4 reqs=2/devs=2).
# Use adjusted deviation rate so that cascade/external deviations don't zero out the metric.
# Note: agent_1a and agent_4 still score low (agent-initiated deviations) —
# but agent_1b now correctly reflects that 2/3 deviations were context-forced.
df['spec_roi']    = (df['reqs_owned'] * (1 - df['adj_dev_rate'])) / (df['directive_words'] / 1000)
df['human_leverage']= df['reqs_owned'] / df['human_involvement']
df['spec_ambiguity_tolerance'] = df['reqs_owned'] / (df['reqs_owned'] + df['underspecified_redirects'])
df['inv_label']  = df['human_involvement'].map({1:'Minimal',2:'Low',3:'Moderate',4:'High',5:'Very High'})
df['inv_colour'] = df['human_involvement'].map(INV_COLOURS)
bar_cols = df['inv_colour'].tolist()

# ── Pre-compute all correlations (used in charts AND findings) ──
r_words    = np.corrcoef(df['directive_words'].values,     df['deviation_rate'].values)[0,1]
r_density  = np.corrcoef(df['constraint_density'].values,  df['deviation_rate'].values)[0,1]
r_inv_exp  = np.corrcoef(df['human_involvement'].values,   df['scope_expansions'].values)[0,1]
active_log = df[df['changelog_entries']>0]
r_inv_log  = np.corrcoef(active_log['human_involvement'].values,
                          active_log['changelog_entries'].values)[0,1]

print(f"Dataset loaded: {len(df)} agents, {len(df.columns)} attributes")
print(f"\\nPre-computed correlations:")
print(f"  r(directive_words,   deviation_rate) = {r_words:.3f}")
print(f"  r(constraint_density, deviation_rate) = {r_density:.3f}  ← POSITIVE (counter-intuitive; see §2)")
print(f"  r(human_involvement,  scope_expansions) = {r_inv_exp:.3f}")
print(f"  r(human_involvement,  changelog_entries) = {r_inv_log:.3f}")
print(f"\\nSpec ROI (adjusted — cascade/external deviations excluded):")
print(df[['id','deviations','cascade_ext_devs','adj_devs','spec_roi']].round(2).to_string(index=False))
"""))

# ============================================================
# TITLE + ABSTRACT
# ============================================================
cells.append(md("""\
---
# 04 — AI Agent Performance in Semi-Autonomous Data Engineering
## Multi-Agent LLM Orchestration · Project Caravela · v3.1

---

## Abstract

This notebook analyses eight LLM-powered specialist agents on a contract-driven, gate-reviewed
pipeline: Meltano → dbt → BigQuery → Dagster → Streamlit (~100 k Olist e-commerce orders).
Framework: git-worktree isolation, written directives per agent, four human-reviewed gates,
one parallel execution phase (agents 3+4).

**v3.1 bug-fix pass:** Corrected positive r_density correlation (finding rewritten);
adjusted Spec ROI formula (cascade/external deviations excluded); agent_1b now plotted in
split radar; agent_5 KBD set to 1.0 (no uncertain decisions); co-design threshold corrected
to U-shape (friction zone at involvement=3, not inverted-U); correlations moved to cell 0.

### Research Questions
| RQ | Question |
|---|---|
| RQ-1 | Does directive design (length, constraint density) predict agent fidelity? |
| RQ-2 | How does human involvement correlate with deviation and scope expansion? |
| RQ-3 | Which contract surfaces are fragile — and how far do violations propagate? |
| RQ-4 | Can concurrent execution reduce delivery time without degrading system quality? |
| RQ-5 | What distinguishes high-leverage agents from low-leverage ones? |
"""))

# ============================================================
# ACT 1 — CONTEXT
# ============================================================

cells.append(md("""\
---
## Act 1 — Context

> **What this Act is answering:** How was the multi-agent framework structured, and were agents
> resourced appropriately for their tasks? Before evaluating performance, we need to understand
> the playing field: how many requirements each agent owned, how much guidance they received,
> and how tightly that guidance was written.

### §1 · Framework Architecture

This section establishes the structural skeleton of the framework before any performance metrics
are introduced. We examine two dimensions of directive design: **volume** (total word count —
how much context and instruction an agent received) and **density** (constraint words per 100
directive words — how precisely those instructions were written). These are independent axes:
a long directive can be loosely written, and a short one can be tightly constrained.

Understanding this baseline matters because it shapes every downstream finding. If an agent
deviated, was it because the directive was too short? Too loosely worded? Or despite being long
and dense? The answer changes what we should fix.

```
GATE-0               GATE-1          GATE-2     GATE-3        GATE-4
  │                    │               │          │              │
  ▼                    ▼               ▼          ▼              ▼
1a(Meltano)→1b(Stg)→1c(Mart)→1d(Tests)→2(Dagster)→3(Analytics)→5(Docs)
                                                   ↕ concurrent
                                               4(Dashboard)──────────┘
```

**Directive Information Density** (constraint words per 100 total words) is a precision metric
distinct from raw word count — it captures how many explicit constraints an agent received
relative to directive volume. Computed from actual directive files via keyword grep
(`must|shall|required|not|only|never|always|exactly`).
"""))

cells.append(code("""\
fig = make_subplots(
    rows=1, cols=2,
    subplot_titles=['Directive Word Count', 'Constraint Density (constraint words / 100 total)'],
)
fig.add_trace(go.Bar(
    x=df['short_id'], y=df['directive_words'],
    marker_color=bar_cols, text=df['directive_words'],
    textposition='outside', name='Words',
), row=1, col=1)
fig.add_trace(go.Bar(
    x=df['short_id'], y=df['constraint_density'],
    marker_color=bar_cols, text=df['constraint_density'].round(2),
    textposition='outside', name='Density', showlegend=False,
), row=1, col=2)
for label, col in [('Minimal (1)','#2E7D32'),('Low (2)','#66BB6A'),
                    ('Moderate (3)','#FF8F00'),('High (4)','#EF6C00'),
                    ('Very High (5)','#C62828')]:
    fig.add_trace(go.Bar(x=[None],y=[None],name=label,marker_color=col))
fig.update_layout(
    height=430, template='plotly_white',
    title='Directive Design by Agent (bar colour = human involvement intensity)',
    legend=dict(orientation='h', y=-0.22), barmode='group',
)
fig.update_yaxes(title_text='Words', row=1, col=1)
fig.update_yaxes(title_text='Constraint density (%)', row=1, col=2)
fig.show()
print("Note: agent_1d has lowest density (1.39) despite being in the longest 1x-series directive.")
print("agent_4 has highest density (2.91) — most constraint-rich per word.")
"""))

cells.append(md("""\
### §2 · Specification Design

This section asks: **were directives efficient investments?** A long directive that produces
many compliant requirements is a better investment than a long directive that produces few. Spec
ROI formalises this — it rewards agents who delivered many requirements cleanly per 1,000 words
of directive received.

**Specification ROI** = `(reqs_owned × adjusted_fidelity) / (directive_words / 1000)`

The "adjusted" qualifier is critical. Three agents had raw deviation rates of 1.0 (all
requirements deviated at least once), which would collapse their ROI to zero. But not all
deviations are equal: some were **cascade-forced** (agent_1b adapting to agent_1a's _view
suffix) or **tool-ecosystem-forced** (dbt-expectations API deprecation). These are not agent
failures — they are the cost of operating in a real, changing technical environment. Adjusted
fidelity separates what the agent controlled from what was imposed on it.

*Adjusted fidelity* excludes cascade-fix and context-forced deviations (e.g. dbt-expectations
deprecation, _view suffix adaptation) — these were imposed by upstream errors or tool ecosystem
constraints, not autonomous agent failures. All 36/37 requirements were delivered as "complete"
per `progress.md`; the raw deviation_rate overstates failure for agents absorbing upstream debt.
"""))

cells.append(code("""\
fig = make_subplots(
    rows=1, cols=2,
    subplot_titles=['Requirements Owned per Agent',
                    'Adjusted Specification ROI\\n(excludes cascade/external deviations)'],
)
fig.add_trace(go.Bar(
    x=df['short_id'], y=df['reqs_owned'],
    marker_color=bar_cols, text=df['reqs_owned'],
    textposition='outside', name='Reqs',
), row=1, col=1)
fig.add_trace(go.Bar(
    x=df['short_id'], y=df['spec_roi'].round(2),
    marker_color=bar_cols, text=df['spec_roi'].round(2),
    textposition='outside', name='Spec ROI', showlegend=False,
), row=1, col=2)

# Annotate agents with remaining 0-ROI and explain why
for aid, reason in [('a1a','1 req, 1 agent-init. dev'), ('a4','2 reqs, 2 agent-init. devs')]:
    row = df[df['short_id']==aid].iloc[0]
    if row['spec_roi'] < 0.1:
        fig.add_annotation(
            x=aid, y=0.3, xref='x2', yref='y2',
            text=reason, showarrow=True, arrowhead=2,
            font=dict(size=9, color=RED),
        )
fig.update_layout(height=430, template='plotly_white',
    title='Specification Value: Scope and Directive Efficiency',
    legend=dict(orientation='h', y=-0.22), barmode='group')
fig.update_yaxes(title_text='Reqs owned', row=1, col=1)
fig.update_yaxes(title_text='Spec ROI (adj. compliant reqs / 1k words)', row=1, col=2)
fig.show()
print("Spec ROI values (adjusted):")
print(df[['id','reqs_owned','deviations','cascade_ext_devs','adj_devs','spec_roi']].round(2).to_string(index=False))
print("\\nagent_1a (ROI=0): single req, one agent-initiated deviation (_view suffix).")
print("agent_4  (ROI=0): two reqs, both agent-initiated; high involvement means output_richness=4.")
print("Spec ROI is not a quality score for co-design mode agents (see §8).")
"""))

cells.append(code("""\
# RQ-1: Constraint Density vs Deviation Rate
# FIX: r_density = +0.541 (POSITIVE) — corrected from earlier claim of negative trend.
fig = px.scatter(
    df, x='constraint_density', y='deviation_rate',
    size='reqs_owned', color='human_involvement',
    color_continuous_scale=['#2E7D32','#FF8F00','#C62828'],
    range_color=[1,5], text='short_id',
    title=f'RQ-1: Constraint Density vs Deviation Rate  (r={r_density:.2f})',
    labels={'constraint_density':'Constraint Density (%)',
            'deviation_rate':'Deviation Rate',
            'human_involvement':'Human\\nInvolvement'},
    template='plotly_white',
)
fig.update_traces(textposition='top center')
x_d = df['constraint_density'].values; y_d = df['deviation_rate'].values
coefs_d = np.polyfit(x_d, y_d, 1)
x_line = np.linspace(x_d.min(), x_d.max(), 50)
fig.add_trace(go.Scatter(x=x_line, y=np.polyval(coefs_d, x_line),
    mode='lines', line=dict(color=GREY, dash='dash'), name='Trend'))
fig.add_annotation(x=0.05, y=0.95, xref='paper', yref='paper', showarrow=False,
    text=(f'r(density, deviation) = {r_density:.2f} — POSITIVE<br>'
          f'r(word_count, deviation) = {r_words:.2f}<br>'
          'Higher density → higher deviation (confound: see below)'),
    bgcolor='white', bordercolor=RED, borderwidth=1, align='left')
fig.update_layout(height=470, coloraxis_colorbar=dict(
    tickvals=[1,2,3,4,5], ticktext=['Minimal','Low','Moderate','High','Very High']))
fig.show()

print(f"RQ-1 findings:")
print(f"  r(constraint_density, deviation_rate) = {r_density:.3f}  ← POSITIVE (surprising)")
print(f"  r(directive_words,     deviation_rate) = {r_words:.3f}")
print()
print("Counter-intuitive result: agents with more constraint-dense directives had HIGHER")
print("deviation rates. Likely a task-complexity confound — technically risky tasks")
print("(ingestion, staging, dashboard) received denser constraints AND experienced more")
print("tool-ecosystem deviations. The relationship is not causal.")
print("agent_1c (density=2.50) is the key exception: high density, low deviation.")
"""))

# ============================================================
# ACT 2 — AGENT PERFORMANCE
# ============================================================

cells.append(md("""\
---
## Act 2 — Individual Agent Performance

> **What this Act is answering:** How faithfully did each agent execute its specification, and
> when failures occurred, were they the agent's fault? Act 1 established how agents were
> resourced. Act 2 evaluates what they did with those resources — starting with the most direct
> measure of compliance (did the output match the spec?) and drilling into *why* it did or didn't.

### §3 · Specification Fidelity & First-Pass Rate

The most straightforward question in this analysis: **did the agent do what it was told?**
Two complementary metrics answer this from different angles.

**Deviation Rate** measures the proportion of an agent's requirements that involved at least
one deviation from specification. A rate of 0.0 means the agent executed perfectly within its
mandate. A rate of 1.0 means every requirement it owned involved some departure. Note that
"deviation" does not imply failure — some deviations were data-driven discoveries or corrections
to specification errors. Context matters enormously (see §5 taxonomy).

**First-Pass Gate Approval Rate** = 1 / revision_cycles — measures whether the agent shipped
a clean output on first human review. This is arguably the more operationally useful metric:
an agent with a high first-pass rate minimises orchestrator review overhead, regardless of
whether any of its underlying decisions were technically "deviations."

The critical interpretive lens for this section: agents with high involvement scores (red/orange
bars) are in **co-design mode** — their low fidelity reflects intentional orchestrator-driven
iteration, not autonomous agent failure. Involvement score is the essential confound variable.
- **Deviation Rate** = deviations / reqs_owned
- **First-Pass Gate Approval Rate** = 1 / revision_cycles — did the agent ship clean on first review?
"""))

cells.append(code("""\
fig = make_subplots(rows=1, cols=2,
    subplot_titles=['Deviation Rate (lower = better)',
                    'First-Pass Gate Approval Rate (higher = better)'])
fig.add_trace(go.Bar(
    x=df['short_id'], y=df['deviation_rate'].round(3),
    marker_color=bar_cols, text=df['deviation_rate'].round(2),
    textposition='outside', name='Dev rate',
), row=1, col=1)
fig.add_trace(go.Bar(
    x=df['short_id'], y=df['first_pass_rate'].round(2),
    marker_color=bar_cols, text=df['first_pass_rate'].round(2),
    textposition='outside', name='First-pass', showlegend=False,
), row=1, col=2)
fig.update_layout(height=430, template='plotly_white',
    title='Specification Fidelity: Two Complementary Views',
    legend=dict(orientation='h', y=-0.22), barmode='group')
fig.update_yaxes(title_text='Deviation rate', row=1, col=1)
fig.update_yaxes(title_text='First-pass rate (1.0 = shipped clean)', row=1, col=2)
fig.show()
print("\\nNote: a3 and a4 high deviation rate + low first-pass rate reflects co-design mode,")
print("not pure agent failure — see §8 for involvement-adjusted interpretation.")
"""))

cells.append(code("""\
# Directive length vs deviation rate
fig = px.scatter(df, x='directive_words', y='deviation_rate',
    size='reqs_owned', color='human_involvement',
    color_continuous_scale=['#2E7D32','#FF8F00','#C62828'],
    range_color=[1,5], text='short_id',
    title=f'Directive Length vs Deviation Rate  (r={r_words:.2f})',
    labels={'directive_words':'Directive Word Count', 'deviation_rate':'Deviation Rate',
            'human_involvement':'Human\\nInvolvement'},
    template='plotly_white',
)
fig.update_traces(textposition='top center')
x_w = df['directive_words'].values; y_w = df['deviation_rate'].values
coefs_w = np.polyfit(x_w, y_w, 1)
x_wl = np.linspace(x_w.min(), x_w.max(), 50)
fig.add_trace(go.Scatter(x=x_wl, y=np.polyval(coefs_w, x_wl),
    mode='lines', line=dict(color=GREY, dash='dash'), name='Trend'))
fig.add_annotation(x=0.05, y=0.95, xref='paper', yref='paper', showarrow=False,
    text=f'Pearson r = {r_words:.3f}\\nNear zero — word count does not predict fidelity',
    bgcolor='white', bordercolor=GREY, borderwidth=1)
fig.update_layout(height=450, coloraxis_colorbar=dict(
    tickvals=[1,2,3,4,5], ticktext=['Minimal','Low','Moderate','High','Very High']))
fig.show()
"""))

# ── §4 Autonomous Decision Quality ──────────────────────────
cells.append(md("""\
### §4 · Autonomous Decision Quality

No directive can anticipate everything. Agents will encounter gaps — ambiguous wording, missing
constraints, conflicting requirements, tool behaviour that wasn't specified. **What an agent does
in those gaps is one of the most important things this analysis can measure.**

This section examines three related but distinct aspects of gap-handling:

**Autonomous Decision Quality** = good / (good + bad) unspecified decisions. This measures
whether agents, when left to their own judgment, made sensible choices. A "bad" autonomous
decision is one the orchestrator had to reverse — not a stylistic disagreement, but a materially
incorrect implementation choice.

**Knowledge Boundary Detection (KBD)** = (uncertain_decisions − silent_failures) / uncertain_decisions.
This is the transparency dimension: did the agent *know* it was uncertain, and did it say so?
A **silent failure** is the worst outcome — the agent made an incorrect decision without flagging
ambiguity, leaving the orchestrator to discover the error only at gate review (or worse,
downstream). KBD of 1.0 means every uncertain decision was surfaced before acting.
*Note: agent_5 had zero uncertain decisions → KBD = 1.0 by definition (absence of uncertain decisions is not a failure).*

**Spec Ambiguity Tolerance** = reqs / (reqs + redirects_needed). High = handled underspecified
areas gracefully without requiring orchestrator clarification. Low = needed external help to
proceed. This metric penalises agents that block frequently on gaps rather than making reasonable
default choices.

Together, these three metrics reveal the agent's "judgment character": confident and correct,
uncertain and transparent, or — the failure mode — confident and wrong.
"""))

cells.append(code("""\
fig = make_subplots(rows=1, cols=3,
    subplot_titles=['Autonomous Decision Quality',
                    'Knowledge Boundary Detection',
                    'Spec Ambiguity Tolerance'])
for col_idx, (col, label) in enumerate([
    ('auto_decision_quality',        'Decision quality'),
    ('knowledge_boundary_detection', 'Boundary detection'),
    ('spec_ambiguity_tolerance',     'Ambiguity tolerance'),
], start=1):
    vals = df[col].fillna(0)
    colours = [TEAL if v >= 0.9 else AMBER if v >= 0.6 else RED for v in vals]
    fig.add_trace(go.Bar(
        x=df['short_id'], y=vals.round(2),
        marker_color=colours, text=vals.round(2),
        textposition='outside', name=label, showlegend=(col_idx==1),
    ), row=1, col=col_idx)
    fig.add_hline(y=1.0, line_dash='dot', line_color=GREEN, opacity=0.35,
                  row=1, col=col_idx)
fig.update_layout(height=430, template='plotly_white',
    title='Autonomous Decision Quality (all metrics: 1.0 = perfect, colour = Teal≥0.9 / Amber≥0.6 / Red<0.6)',
    legend=dict(orientation='h', y=-0.22))
fig.show()
print("\\nKBD vs auto_decision_quality — where they differ (agent has bad decisions but flagged uncertainty):")
print(df[df['silent_failures']==0][['id','auto_decision_quality','knowledge_boundary_detection']].round(2))
print("\\nagent_5: KBD=1.0 by definition (zero uncertain decisions = no failures to flag).")
"""))

cells.append(code("""\
fig = go.Figure()
fig.add_trace(go.Bar(
    x=df['short_id'], y=df['good_auto_decisions'],
    name='Good autonomous decisions', marker_color=GREEN,
    text=df['good_auto_decisions'], textposition='inside',
))
fig.add_trace(go.Bar(
    x=df['short_id'], y=df['bad_auto_decisions'],
    name='Bad autonomous decisions', marker_color=RED,
    text=df['bad_auto_decisions'], textposition='inside',
))
fig.update_layout(
    barmode='stack', height=400, template='plotly_white',
    title='Autonomous Decision Record — Good vs Bad Unspecified Decisions per Agent',
    xaxis_title='Agent', yaxis_title='Decision count',
    legend=dict(orientation='h', y=-0.2),
)
fig.show()
total_good = int(df['good_auto_decisions'].sum())
total_bad  = int(df['bad_auto_decisions'].sum())
print(f"Framework: {total_good} good / {total_bad} bad autonomous decisions")
print(f"Overall autonomous decision quality: {total_good/(total_good+total_bad):.1%}")
print("\\nagent_5: 4 good / 0 bad — cleanest record. agent_3: most decisions (5) — reflects co-design exploration.")
"""))

# ── §5 Deviation Taxonomy ────────────────────────────────────
cells.append(md("""\
### §5 · Deviation & Expansion Taxonomy

Counts without context mislead. This section exists to answer the question that §3 deliberately
left open: **of all the changes that happened, what actually caused them?**

The taxonomy classifies every documented deviation and scope expansion by two dimensions:
its **category** (what type of change it was) and its **origin** (who or what caused it).
The origin dimension is the most analytically important:

- **agent**: the LLM made an autonomous choice that departed from specification. This is the
  only origin type that reflects an agent failure in the conventional sense.
- **cascade**: the agent was *forced* to adapt because an upstream agent deviated first. The
  agent had no choice — complying with the upstream output required departing from the original
  spec. This is upstream debt, not agent failure.
- **external**: a third-party tool or library changed in a way that made spec compliance
  impossible at runtime. dbt-expectations API deprecation is the example here — the spec was
  correct when written; the tool invalidated it mid-execution.
- **orch**: the orchestrator explicitly requested a change, addition, or enrichment beyond
  what was specified. These are value-adds, not failures. They appear as scope expansions in
  the stacked bar charts.

**The central takeaway of this section:** if you remove "orch" and "external" origins from the
deviation count, the picture of agent performance changes dramatically. Most of what looks like
"agent failure" in raw metrics is actually orchestrator enrichment, tool ecosystem churn, or
upstream cascade. The taxonomy makes this visible.
"""))

cells.append(code("""\
taxonomy = pd.DataFrame([
    ('agent_1a','tool-switch',         1,'agent',    'tap-csv vs tap-spreadsheets-anywhere + _view suffix'),
    ('agent_1b','cascade-fix',         1,'cascade',  '_view suffix cascade from agent_1a'),
    ('agent_1b','context-forced',      1,'external', 'dbt-expectations deprecation; alternatives required'),
    ('agent_1b','constraint',          1,'external', 'Filtering rules: unsupported by metaplane fork'),
    ('agent_1b','scope-expansion',     1,'orch',     'Extra stg_product_category model'),
    ('agent_1c','data-discovery',      1,'agent',    'COALESCE dead-branch + WHERE filter removal'),
    ('agent_1d','data-defect-fix',     1,'agent',    'payment_reconciliation threshold calibration'),
    ('agent_2', 'architecture',        1,'agent',    'Folder structure deviated from spec'),
    ('agent_2', 'cascade-fix',         1,'cascade',  '_view AssetKeys + tap-csv subprocess adaptation'),
    ('agent_2', 'architecture',        1,'agent',    '@asset(deps=) → @multi_asset(specs=) wiring fix'),
    ('agent_3', 'scope-expansion',     2,'orch',     'New Lorenz/Gini/HHI metrics — orchestrator-requested'),
    ('agent_3', 'data-discovery',      1,'agent',    'ASMP-025 data cut artefacts identified'),
    ('agent_3', 'pre-impl-decision',   1,'agent',    'RFM frequency: 3-tier vs quintile'),
    ('agent_3', 'data-defect-fix',     1,'agent',    'Seller cancellation rate bug fix'),
    ('agent_3', 'scope-expansion',     1,'orch',     'concentration_metrics.parquet — new Parquet contract'),
    ('agent_4', 'scope-expansion',     3,'orch',     'Dashboard layout adapted to concurrent agent_3 outputs'),
    ('agent_4', 'architecture',        1,'agent',    'Glossary page + tab layout not in spec'),
], columns=['agent','category','count','origin','description'])

origin_colours = {'agent':BLUE,'external':ORANGE,'cascade':RED,'orch':PURPLE}
cat_colours = {'tool-switch':TEAL,'cascade-fix':RED,'context-forced':ORANGE,
               'data-discovery':GREEN,'scope-expansion':PURPLE,'architecture':AMBER,
               'pre-impl-decision':BLUE,'data-defect-fix':PINK,'constraint':GREY}

origin_totals = taxonomy.groupby('origin')['count'].sum()
cat_totals    = taxonomy.groupby('category')['count'].sum().sort_values(ascending=False)

fig = make_subplots(rows=1, cols=2,
    subplot_titles=['By Root-Cause Origin','By Category'],
    specs=[[{'type':'pie'},{'type':'bar'}]])

fig.add_trace(go.Pie(
    labels=origin_totals.index, values=origin_totals.values,
    marker_colors=[origin_colours.get(o,GREY) for o in origin_totals.index],
    hole=0.4, name='',
), row=1, col=1)

for cat in cat_totals.index:
    sub = taxonomy[taxonomy['category']==cat]
    fig.add_trace(go.Bar(
        x=sub['agent'], y=sub['count'], name=cat,
        marker_color=cat_colours.get(cat,GREY),
    ), row=1, col=2)

fig.update_layout(
    height=440, template='plotly_white', barmode='stack',
    title='Change Taxonomy: Deviations + Scope Expansions by Origin and Category',
    legend=dict(orientation='h', y=-0.28),
)
fig.show()
print("Change origin breakdown (deviations + scope expansions):")
for origin, count in origin_totals.items():
    print(f"  {origin:10s}: {count:2d} ({count/origin_totals.sum():.0%})")
orch_ext = origin_totals.get('orch',0) + origin_totals.get('external',0)
print(f"\\n'orch' + 'external' combined: {orch_ext}/{origin_totals.sum()} = {orch_ext/origin_totals.sum():.0%}")
print("These are NOT autonomous agent failures — they reflect orchestrator enrichment and tool constraints.")
"""))

# ============================================================
# ACT 3 — SYSTEM EFFECTS
# ============================================================

cells.append(md("""\
---
## Act 3 — System Effects: Cascade and Contract Fragility

> **What this Act is answering:** When one agent deviated, what happened downstream? Act 2
> measured individual agent behaviour. Act 3 measures the *systemic consequences* of that
> behaviour — how errors propagate through a sequential pipeline, how much rework they trigger,
> and which types of violations are structurally most dangerous. An agent that deviates once but
> causes four downstream corrections is more costly than an agent that deviates three times but
> absorbs all the consequences itself.

### §6 · Error Detection Latency, Cascade Amplification & Contract Debt

A deviation caught immediately costs almost nothing. A deviation caught two pipeline stages
later costs everything between — all the work done on a false foundation. This section measures
three dimensions of error propagation that raw deviation counts completely miss.

**Error Detection Latency** measures how many pipeline stages downstream an error travelled
before being caught. 0 = the agent caught it itself or the gate caught it immediately. 1 = the
next agent discovered it. 2+ = the error propagated across multiple gates. Lower is dramatically
cheaper: the cost of rework roughly doubles with every additional stage.

**Cascade Amplification Factor (CAF)** = `downstream_rework_caused / deviations`. This is the
"multiplier" metric. CAF = 1.0 means each deviation caused one fix. CAF = 4.0 (agent_1a) means
a single deviation caused four separate downstream rework entries. Naming contract violations
have high CAF because every downstream consumer of that name must adapt; data-defect fixes have
CAF ≈ 0 because they self-contain within the agent's own work.

**Contract Debt Score** = absolute downstream rework entries caused. This reranks agents by
*systemic impact* rather than raw output quality. An agent with one deviation and CAF=4 is more
expensive than an agent with three deviations and CAF=0. The leaderboard here will surprise
readers who formed their opinion of agents from Act 2 alone.
"""))

cells.append(code("""\
fig = make_subplots(rows=1, cols=3,
    subplot_titles=['Error Detection Latency\\n(0=self-caught, lower=cheaper)',
                    'Cascade Amplification Factor\\n(>1 = single dev caused multiple fixes)',
                    'Contract Debt Score\\n(downstream rework caused)'])

for col_idx, col in enumerate(
    ['error_detection_latency','cascade_amplification_factor','contract_debt_score'], start=1):
    vals = df[col]
    c_list = [RED if v > 1 else AMBER if v > 0 else GREEN for v in vals]
    fig.add_trace(go.Bar(
        x=df['short_id'], y=vals.round(2),
        marker_color=c_list, text=vals.round(2),
        textposition='outside', showlegend=False,
    ), row=1, col=col_idx)

fig.update_layout(height=440, template='plotly_white',
    title='System-Level Cost Metrics (Green = clean, Amber = moderate, Red = high concern)')
fig.show()

print("Contract Debt leaderboard (who imposed most cost downstream):")
debt = df[['id','deviations','downstream_rework_caused',
           'cascade_amplification_factor']].sort_values('downstream_rework_caused', ascending=False)
print(debt.round(2).to_string(index=False))
a1a_caf = df[df['id']=='agent_1a']['cascade_amplification_factor'].values[0]
print(f"\\nKey: agent_1a has 1 raw deviation but CAF={a1a_caf:.1f}")
print("One naming decision caused 4 downstream rework entries across agents 1b and 2.")
print("Contract debt is NOT proportional to raw deviation count.")
"""))

cells.append(code("""\
labels = [
    'agent_1a','agent_1b','agent_1c','agent_1d',
    'agent_2','agent_3','agent_4','agent_5',
    '_view naming\\ncascade','dbt-expectations\\ndeprecation',
    'staging contract\\n(clean post-fix)','concurrent\\ncoord overhead',
]
links = [
    (0, 8, 4, '_view suffix → 4 downstream entries'),
    (8, 1, 4, 'cascade absorbed by agent_1b'),
    (1, 9, 2, 'deprecated API discovered'),
    (9, 1, 2, 'alternatives implemented'),
    (1, 10, 4, 'staging layer fixed'),
    (10, 2, 4, 'mart models receive clean contract'),
    (2,  3, 3, 'mart → tests handoff'),
    (3,  4, 2, 'tests → dagster handoff'),
    (4,  5, 2, 'pipeline complete → analytics (concurrent)'),
    (4,  6, 2, 'pipeline complete → dashboard (concurrent)'),
    (5, 11, 2, 'agent_3 live outputs feed agent_4'),
    (11, 6, 2, 'agent_4 adapts to agent_3'),
    (6,  7, 2, 'dashboard → docs'),
]
src, tgt, val, lbl = zip(*links)
node_cols = [BLUE,BLUE,BLUE,BLUE,BLUE,TEAL,TEAL,GREEN,
             RED,ORANGE,AMBER,PURPLE]
fig = go.Figure(go.Sankey(
    node=dict(label=labels, color=node_cols, pad=15, thickness=20),
    link=dict(source=list(src), target=list(tgt), value=list(val), label=list(lbl)),
))
fig.update_layout(
    title='Information Flow & Cascade Propagation (link width = relative rework cost)',
    height=520, template='plotly_white', font=dict(size=11),
)
fig.show()
print("Cascade fully contained at the agent_1b boundary.")
print("No deviation reached mart models or downstream consumers.")
"""))

# ── §7 Contract Surface Analysis ────────────────────────────
cells.append(md("""\
### §7 · Contract Surface Analysis

In a sequential multi-agent pipeline, agents cannot directly communicate. They communicate
through **intermediate outputs**: file names, table names, column schemas, function signatures,
file paths. When agent A produces an output that agent B must consume, they have implicitly
agreed on a contract. If that contract is never written down and never validated, it is a
fragility waiting to manifest.

This section inventories every cross-agent contract surface in the framework, assesses whether
it held, and classifies severity if it didn't. The goal is to answer: **which types of contract
are most likely to break, and how bad is it when they do?**

A **contract surface** is any string, schema, or path that two agents must agree on
independently — without runtime enforcement. There is no type checker enforcing that
`stream_name` in `meltano.yml` matches `source_table` in `sources.yml`. There is no IDE warning
that the Parquet column schema exported by agent_3 must match what agent_4 reads. These
agreements exist only in the directives and in the orchestrator's head.

The fragility of a contract surface is determined by two factors: how easy it is to violate
inadvertently (naming contracts are easy to get wrong; logic contracts require deeper misalignment)
and how far violations propagate (a shared naming convention violation touches every downstream
consumer; a data-defect fix is local).

**All contract violations were naming violations** — not semantic disagreements about design.
This is a structural finding about where LLM agents are most likely to slip.
"""))

cells.append(code("""\
contracts = pd.DataFrame([
  ('BigQuery table names (stream_name)',  'agent_1a','agent_1b/2',
   'VIOLATED','Critical','_view suffix — 4 downstream changelog entries'),
  ('tap plugin name (tap-csv)',           'agent_1a','agent_2',
   'OK','—','Consistent in Dagster subprocess call'),
  ('Staging model schemas (stg_*.sql)',   'agent_1b','agent_1c',
   'OK*','—','*After cascade fix; clean handoff to 1c'),
  ('dbt manifest.json path',             'agent_1c/d','agent_2',
   'OK','—','__file__-relative; portable across machines'),
  ('Parquet schemas (data/*.parquet)',    'agent_3','agent_4',
   'MINOR','Low','primary_payment_type alignment; live coordination resolved it'),
  ('notebooks/utils.py API',            'agent_3','agent_4',
   'OK','—','Canonical single source; zero drift'),
  ('dashboard.py entry point',          'agent_4','agent_5',
   'OK','—','Consistent in docs and user guide'),
  ('ADR authorship',                    'orch+a5','readers',
   'AMBIGUOUS','Info','Co-authored; v2+ annotation resolves'),
], columns=['surface','producer','consumer','status','severity','resolution'])

print("CONTRACT SURFACE FRAGILITY INVENTORY\\n" + "="*68)
for _, r in contracts.iterrows():
    icon = '❌' if r['status']=='VIOLATED' else '⚠ ' if r['status'] in ('MINOR','AMBIGUOUS') else '✓ '
    print(f"\\n{icon} [{r['severity']:8s}] {r['surface']}")
    print(f"   {r['producer']} → {r['consumer']}")
    print(f"   {r['resolution']}")

sev_map = {'Critical':RED,'Low':AMBER,'—':GREEN,'Info':TEAL}
sev_counts = contracts['severity'].value_counts()
fig = px.bar(x=sev_counts.index, y=sev_counts.values,
    color=sev_counts.index, color_discrete_map=sev_map,
    title='Contract Surface Severity Distribution',
    labels={'x':'Severity','y':'Count'},
    template='plotly_white',
)
fig.update_layout(height=320, showlegend=False)
fig.show()
print("\\nKey finding (RQ-3): ALL contract violations were naming violations.")
print("Naming contracts (exact strings) are the primary fragility surface in multi-agent pipelines.")
"""))

# ============================================================
# ACT 4 — HUMAN–AI DYNAMICS
# ============================================================

cells.append(md("""\
---
## Act 4 — Human–AI Dynamics

> **What this Act is answering:** How did orchestrator involvement shape agent behaviour and
> output quality? Acts 2 and 3 measured what agents produced and what it cost. Act 4 asks why
> some agents performed differently from others — and discovers that human involvement is the
> primary explanatory variable. This act reframes the entire analysis: low fidelity is not
> uniformly bad, and high scope expansion is not uniformly undisciplined.

### §8 · Human–AI Collaboration Spectrum

This section introduces the most important interpretive lens in the notebook: **the involvement
score**. Without it, agents 3 and 4 look like the worst performers — low fidelity, most
revisions, highest scope expansion. With it, they are the most productive in terms of output
richness, because they were the most heavily co-designed.

The involvement score is an ordinal measure (1–5) of how deeply the orchestrator participated
in an agent's work, combining intervention frequency with intervention type. It is self-reported
by the orchestrator and carries the limitations that implies (see §14 limitations). Nevertheless,
it is the single most important contextual variable for interpreting everything measured in Acts 2–3.

The key finding of this section is not a number — it's a **reframe**. Three distinct
collaboration modes emerge from the data, each with its own success criteria:
- **Autonomous mode** (involvement ≤ 2): success = high fidelity, high first-pass rate, low cascade.
- **Correction mode** (involvement = 3): the agent made errors; the orchestrator fixed them. Neither
  the agent nor the orchestrator was enriching — only correcting. This is the least productive mode.
- **Co-design mode** (involvement ≥ 4): the orchestrator was actively shaping outputs, not just
  reviewing them. Success = output richness, not fidelity. Deviation and scope expansion are
  *evidence of investment*, not failure.

> **Core reframe:** Low fidelity scores and high scope expansions are NOT uniformly agent
> failures. They may indicate **intentional orchestrator co-design mode**. The involvement
> score disambiguates: low = agent autonomous behaviour; high = orchestrator-shaped output.

**Involvement Scale:** 1=Minimal · 2=Low · 3=Moderate (correction) · 4=High · 5=Very High (co-design)

**Parallel phase:** Agents 3+4 ran concurrently — the only parallel phase in the framework.
"""))

cells.append(code("""\
fig = go.Figure()
fig.add_trace(go.Bar(
    x=df['short_id'], y=df['human_involvement'],
    marker_color=[INV_COLOURS[h] for h in df['human_involvement']],
    text=df['inv_label'], textposition='outside', width=0.55,
))
for aid in ('agent_3','agent_4'):
    row = df[df['id']==aid].iloc[0]
    fig.add_annotation(
        x=row['short_id'], y=row['human_involvement']+0.35,
        text='⇌ concurrent', showarrow=False,
        font=dict(size=10, color=PURPLE))
fig.update_layout(
    title='Human Orchestrator Involvement Intensity per Agent',
    yaxis=dict(range=[0,6.8], tickvals=[1,2,3,4,5],
               ticktext=['1 Minimal','2 Low','3 Moderate','4 High','5 Very High']),
    xaxis_title='Agent', template='plotly_white', height=420,
)
fig.show()
print("Qualitative involvement notes (first-hand orchestrator summary):")
for _, r in df.iterrows():
    print(f"\\n[{r['id'].upper()}] {r['inv_label']} ({r['human_involvement']}/5)")
    print(f"  {r['involvement_notes']}")
"""))

cells.append(code("""\
# Co-Design Mode Detection — actual quadratic fit
# FIX: previous version claimed 'inverted U' but fit is concave UP (U-shape).
# Vertex ≈ 2.6 = MINIMUM output richness, not maximum.
# This reveals: involvement=3 is the 'friction zone' (orchestrator correcting but not enriching).
x_inv = df['human_involvement'].values
y_rich = df['output_richness'].values
coefs_q = np.polyfit(x_inv, y_rich, 2)
vertex  = -coefs_q[1] / (2 * coefs_q[0])

fig = px.scatter(
    df, x='human_involvement', y='output_richness',
    color='human_involvement',
    color_continuous_scale=['#2E7D32','#FF8F00','#C62828'],
    range_color=[1,5], size='reqs_owned', text='short_id',
    title=f'Co-Design Mode: Output Richness vs Human Involvement (vertex≈{vertex:.1f})',
    labels={'human_involvement':'Human Involvement (1=Minimal, 5=Co-design)',
            'output_richness':'Output Richness (1=baseline, 5=exceeds spec)'},
    template='plotly_white',
)
fig.update_traces(textposition='top center')
x_fit = np.linspace(1, 5, 50)
y_fit = np.polyval(coefs_q, x_fit)
fig.add_trace(go.Scatter(x=x_fit, y=y_fit, mode='lines',
    line=dict(color=PURPLE, dash='dash', width=2.5), name='Quadratic fit'))
# Annotate regions
for xpos, label, col in [(1.5,'Autonomous\\n(agent-driven quality)',GREEN),
                           (2.8,'Correction Zone\\n(friction, minimum richness)',AMBER),
                           (4.5,'Co-Design\\n(orchestrator-enriched)',RED)]:
    fig.add_annotation(x=xpos, y=float(np.polyval(coefs_q, xpos))+0.4,
        text=label, showarrow=False, font=dict(size=9, color=col))
if 1 <= vertex <= 5:
    fig.add_vline(x=vertex, line_dash='dot', line_color=AMBER, opacity=0.7,
        annotation_text=f'Friction zone vertex ≈ {vertex:.1f}',
        annotation_position='bottom right')
fig.update_layout(height=490, coloraxis_showscale=False)
fig.show()
print(f"Quadratic fit: a={coefs_q[0]:.3f}, b={coefs_q[1]:.3f}, c={coefs_q[2]:.3f}")
print(f"Shape: concave UP (U-shape) — vertex at x≈{vertex:.1f} = MINIMUM output richness")
print()
print("Interpretation: involvement=3 is the 'friction zone' — the orchestrator is")
print("correcting agent failures but not yet enriching outputs. involvement=1-2")
print("produces reasonable quality autonomously; involvement=4-5 produces the richest")
print("outputs through co-design. The U-shape suggests diminishing-to-improving returns.")
"""))

# ── §9 Scope Expansion & Leverage ───────────────────────────
cells.append(md("""\
### §9 · Scope Expansion & Human Leverage

Scope expansions — deliverables produced beyond what was specified — tell a different story
depending on who initiated them. An agent that autonomously adds features it wasn't asked for
is exhibiting undisciplined behaviour. An orchestrator that asks an agent to enrich its output
mid-execution is exhibiting productive co-design. The raw expansion count conflates both.

This section separates the two by cross-referencing expansion origin from the §5 taxonomy.
It then introduces a metric that captures the efficiency of the human orchestrator's time:

**Human Leverage Ratio** = `reqs_owned / human_involvement`

High leverage means the agent delivered many completed requirements per unit of orchestrator
attention. Low leverage means the orchestrator spent significant effort to get a relatively small
requirement set across the finish line. This is the closest proxy in this dataset to
"productivity gain per hour of human time."

Critically: **leverage and output richness are inversely correlated**. Co-design agents have
low leverage (high involvement, few formal requirements) but produce the richest outputs. Autonomous
agents have high leverage but may produce outputs that are technically correct but analytically
unremarkable. Neither is uniformly better — the choice depends on the task's output requirements.

A data pipeline benefits from high-leverage autonomous agents (do what you're told, correctly,
without supervision). An analytics layer where the human's domain judgment shapes the analysis
benefits from low-leverage co-design. The framework should be designed with this distinction
explicit, not implicit.
"""))

cells.append(code("""\
fig = go.Figure()
fig.add_trace(go.Bar(x=df['short_id'], y=df['deviations'],
    name='Deviations', marker_color=RED,
    text=df['deviations'], textposition='inside'))
fig.add_trace(go.Bar(x=df['short_id'], y=df['scope_expansions'],
    name='Scope Expansions', marker_color=PURPLE,
    text=df['scope_expansions'], textposition='inside'))
for _, row in df[df['scope_expansions']>1].iterrows():
    fig.add_annotation(
        x=row['short_id'],
        y=row['deviations']+row['scope_expansions']+0.3,
        text='★ orch-driven', showarrow=False,
        font=dict(size=9, color=PURPLE))
fig.update_layout(
    barmode='stack', height=400, template='plotly_white',
    title='Deviations vs Scope Expansions (★ = orchestrator-initiated expansion)',
    xaxis_title='Agent', yaxis_title='Count',
    legend=dict(orientation='h', y=-0.2))
fig.show()

fig2 = px.scatter(df, x='human_involvement', y='scope_expansions',
    size='reqs_owned', color='id', text='short_id',
    title=f'RQ-2: Human Involvement vs Scope Expansions  (r={r_inv_exp:.2f})',
    labels={'human_involvement':'Human Involvement','scope_expansions':'Scope Expansions'},
    template='plotly_white')
fig2.update_traces(textposition='top center')
fig2.update_layout(height=400)
fig2.show()
print(f"r(involvement, scope_expansions) = {r_inv_exp:.3f}")
print("Strong positive correlation: scope expansions are predominantly orchestrator-initiated.")
"""))

cells.append(code("""\
fig = px.bar(df, x='short_id', y='human_leverage',
    color='human_involvement',
    color_continuous_scale=['#2E7D32','#FF8F00','#C62828'],
    range_color=[1,5],
    text=df['human_leverage'].round(2),
    title='RQ-5: Human Leverage Ratio (reqs delivered per unit of orchestrator effort)',
    labels={'human_leverage':'Human Leverage (reqs / involvement score)','short_id':'Agent',
            'human_involvement':'Human\\nInvolvement'},
    template='plotly_white',
)
fig.update_traces(textposition='outside')
fig.update_layout(height=430, coloraxis_colorbar=dict(
    tickvals=[1,2,3,4,5], ticktext=['Minimal','Low','Moderate','High','Very High']))
fig.show()
print("Human Leverage leaderboard:")
lev = df[['id','reqs_owned','human_involvement','human_leverage']].sort_values(
    'human_leverage', ascending=False)
print(lev.round(2).to_string(index=False))
print("\\nagent_1c: highest leverage (9 reqs, involvement=1 — near-zero orchestrator time).")
print("agent_4: lowest leverage (2 reqs, involvement=4) — co-design mode trades efficiency for richness.")
"""))

# ── §10 Parallel Execution ───────────────────────────────────
cells.append(md("""\
### §10 · Parallel Execution & Orchestrator Review Cadence

Sequential pipelines are safe but slow. Every sequential constraint — agent B cannot start
until agent A finishes — compounds delivery time. The question this section asks is: **how much
parallelism was theoretically available, how much was captured, and what does that tell us about
the orchestrator's capacity planning?**

**Parallelizability Utilization** = actual parallel pairs / theoretically possible pairs.
Of 3 viable parallel opportunities, only 1 was executed (33%). The two foregone pairs
(a1c+a1d, a4+a5) represent compressed delivery time that was left on the table. Whether that
was a reasonable trade-off (simpler orchestration, lower coordination overhead) or a missed
opportunity depends on project constraints.

The second dimension of this section is **orchestrator review cadence**: how much review effort
did each agent require? Changelog entry count serves as a proxy — each entry represents a gate
decision, correction, or significant review action logged by the orchestrator. Agents with zero
changelog entries either performed perfectly (agent_5) or worked without meaningful gate review
(which would be a monitoring gap). In this framework, agent_5's zero entries reflect the former:
it followed spec exactly, requiring no corrections.

> **Commit authorship note:** All commits authored by orchestrator (`wrap_up_agent.sh`).
> Timestamps = *review completion time*, not agent work completion.
> Changelog entry count per agent proxies *gate review effort*, not agent session duration.
"""))

cells.append(code("""\
parallel_data = pd.DataFrame([
    ('a1c + a1d', False, 'agent_1d depends on agent_1c dbt build pass'),
    ('a3 + a4',   True,  '✓ Parallelized — shared Parquet contract; orchestrator coordinated live'),
    ('a4 + a5',   False, 'agent_5 needs dashboard structure from agent_4'),
], columns=['pair','parallelized','note'])

fig = make_subplots(rows=1, cols=2,
    subplot_titles=['Parallelizability Utilization (1/3 = 33%)',
                    'Changelog Entries: Orchestrator Review Effort per Gate'])
fig.add_trace(go.Bar(
    x=parallel_data['pair'], y=[1,1,1],
    marker_color=[GREEN if p else GREY for p in parallel_data['parallelized']],
    text=['PARALLELIZED' if p else 'Sequential' for p in parallel_data['parallelized']],
    textposition='inside', showlegend=False,
), row=1, col=1)
fig.add_annotation(x=0.24, y=0.92, xref='paper', yref='paper',
    text='1/3 pairs parallelized\\n= 33% utilization',
    showarrow=False, bgcolor='white', bordercolor=GREEN, borderwidth=1)
fig.add_trace(go.Bar(
    x=df['short_id'], y=df['changelog_entries'],
    marker_color=[INV_COLOURS[h] for h in df['human_involvement']],
    text=df['changelog_entries'], textposition='outside',
    showlegend=False,
), row=1, col=2)
fig.update_layout(height=430, template='plotly_white',
    title='Parallel Execution Utilization + Review Effort per Gate')
fig.show()
print("Parallel phase (agents 3+4):")
print("  + Compressed analytics + dashboard delivery into one gate")
print("  - Required live Parquet schema coordination (contract underdefined before start)")
print("  - agent_4 scope_expansions=5 (highest of any agent) — driven by agent_3 live outputs")
"""))

cells.append(code("""\
fig = px.scatter(active_log, x='human_involvement', y='changelog_entries',
    size='reqs_owned', color='id', text='short_id',
    title=f'Involvement vs Review Effort (changelog entries)  r={r_inv_log:.2f}',
    labels={'human_involvement':'Human Involvement',
            'changelog_entries':'Changelog Entries (gate decisions logged)'},
    template='plotly_white',
)
fig.update_traces(textposition='top center')
fig.update_layout(height=400)
fig.show()
print(f"r = {r_inv_log:.3f} (agents with ≥1 changelog entry; agent_5 excluded: 0 entries)")
print("Higher involvement → more logged gate decisions. agent_5 had no decisions to log")
print("(fully spec-driven, zero deviations).")
"""))

# ============================================================
# ACT 5 — SYSTEM-LEVEL ASSESSMENT
# ============================================================

cells.append(md("""\
---
## Act 5 — System-Level Assessment

> **What this Act is answering:** How does the system perform as a whole, and where are its
> structural strengths and weaknesses? Acts 2–4 examined individual agents and pairwise dynamics.
> Act 5 synthesises into a holistic assessment — both of individual agent profiles across all
> dimensions simultaneously, and of what the framework produced compared to its human-team
> alternative.

### §11 · Eight-Dimension Performance Radar

Every metric computed in Acts 2–4 is a partial view. An agent with high fidelity but poor
decision quality may be "following orders" but failing in the gaps. An agent with low fidelity
but high output richness may be the most valuable contributor. The radar synthesises all eight
performance dimensions into a single visual profile per agent.

**Reading the radar correctly is essential.** The temptation is to favour agents whose profile
fills the most area. But scope discipline is context-dependent: for an autonomous agent, low scope
discipline is undisciplined; for a co-design agent, it reflects orchestrator enrichment. The
split view (§11b) resolves this by grouping agents into their natural collaboration modes before
comparing — you should compare within modes, not across them.

The eight dimensions and their directionality:

| Dimension | Formula | High = ? |
|---|---|---|
| Fidelity | 1 − deviation_rate | Better (always) |
| First-Pass Rate | 1 / revision_cycles | Better (always) |
| Decision Quality | good / (good+bad) decisions | Better (always) |
| Cascade Cleanliness | 1 − downstream_rework/6 | Better (always) |
| Scope Discipline | 1 − expansion_rate (capped) | Better for autonomous; N/A for co-design |
| Spec Efficiency | reqs / directive_words × 1000 (norm.) | Better (always) |
| Output Richness | self-assessed 1–5 (norm.) | Better (always) |
| Knowledge Boundary | (uncertain − silent) / uncertain | Better (always) |

The one dimension worth singling out: **Cascade Cleanliness**. An agent can score highly on
all other seven dimensions and still impose enormous systemic cost if its deviations cascade.
Conversely, an agent with low fidelity can score well here if all its deviations were absorbed
locally. This is the dimension that most clearly separates individual performance from systemic
impact.
"""))

cells.append(code("""\
dims = ['Fidelity','First-Pass\\nRate','Decision\\nQuality',
        'Cascade\\nClean','Scope\\nDiscipline',
        'Spec\\nEfficiency','Output\\nRichness','Knowledge\\nBoundary']

df_r = df.copy()
df_r['spec_efficiency'] = df_r['spec_efficiency'] / df_r['spec_efficiency'].max()

def radar_row(r):
    return [
        max(0, 1 - r['deviation_rate']),
        r['first_pass_rate'],
        r['auto_decision_quality'] if pd.notna(r['auto_decision_quality']) else 1.0,
        max(0, 1 - r['downstream_rework_caused'] / 6),
        max(0, 1 - min(r['expansion_rate'], 1)),
        r['spec_efficiency'],
        r['output_richness'] / 5,
        r['knowledge_boundary_detection'],
    ]

fig = go.Figure()
for _, row in df_r.iterrows():
    scores = radar_row(row)
    vals   = scores + [scores[0]]
    thetas = dims + [dims[0]]
    col    = INV_COLOURS[row['human_involvement']]
    alpha  = 0.18 if row['human_involvement'] >= 4 else 0.38
    fig.add_trace(go.Scatterpolar(
        r=vals, theta=thetas,
        name=f"{row['short_id']} (inv={row['human_involvement']})",
        line=dict(color=col, width=2), fill='toself', opacity=alpha,
    ))
fig.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0,1])),
    title=('Eight-Dimension Agent Performance Radar<br>'
           '<sup>Green=autonomous · Red=co-design. '
           'Low scope discipline at high involvement = orchestrator enrichment, not failure.</sup>'),
    height=600, showlegend=True,
    legend=dict(orientation='h', y=-0.22),
)
fig.show()
"""))

cells.append(code("""\
# FIX: §11b now shows all three modes — Autonomous, Correction, Co-Design
# Previously agent_1b (involvement=3) was defined in 'collab' but never plotted.
autonomous = df_r[df_r['human_involvement'] <= 2]   # a1a, a1c, a1d, a2, a5
correction = df_r[df_r['human_involvement'] == 3]   # a1b only
codesign   = df_r[df_r['human_involvement'] >= 4]   # a3, a4

fig = make_subplots(rows=1, cols=3,
    subplot_titles=[
        f'Autonomous Mode\\n(involvement ≤ 2, n={len(autonomous)})',
        f'Correction Mode\\n(involvement = 3, n={len(correction)})',
        f'Co-Design Mode\\n(involvement ≥ 4, n={len(codesign)})',
    ],
    specs=[[{'type':'polar'},{'type':'polar'},{'type':'polar'}]])

for grp_df, col_idx in [(autonomous,1),(correction,2),(codesign,3)]:
    for _, row in grp_df.iterrows():
        scores = radar_row(row)
        col = INV_COLOURS[row['human_involvement']]
        fig.add_trace(go.Scatterpolar(
            r=scores+[scores[0]], theta=dims+[dims[0]],
            name=row['short_id'], line=dict(color=col, width=2),
            fill='toself', opacity=0.45,
        ), row=1, col=col_idx)

fig.update_layout(
    height=520, template='plotly_white',
    title='Three Collaboration Modes — Radar Comparison',
    legend=dict(orientation='h', y=-0.18),
)
fig.update_polars(radialaxis=dict(visible=True, range=[0,1]))
fig.show()
print("Autonomous (a1c, a1d, a5): consistently high across all 8 dims.")
print("Correction (a1b): moderate fidelity + lower first-pass — absorbed cascade + tool debt.")
print("Co-design (a3, a4): high output_richness + lower scope_discipline —")
print("  deliberate quality-efficiency trade-off in co-design mode.")
"""))

# ── §12 Artifacts + Human Team Comparison ───────────────────
cells.append(md("""\
### §12 · Quality Output Artifacts & Human Team Comparison

Metrics are abstractions. This section asks the concrete question: **what did the framework
actually produce?** And immediately follows with: **how does that compare to what a human team
of equivalent size would have produced in the same timeframe?**

The artifact inventory grounds the analysis in deliverables — not in deviation rates or
involvement scores, but in working code, passing tests, documentation, and deployed interfaces.
This is the most important reality check in the notebook. A framework that scores well on
analytical metrics but produces incomplete, non-functional outputs has failed regardless of its
Spec ROI. A framework that scores moderately on fidelity but ships a complete, professional-grade
project has succeeded.

The human team comparison is necessarily qualitative — no equivalent human team executed this
project, so all comparisons are estimates against typical team behaviour. The goal is not to
declare a winner, but to identify the genuine trade-offs that an organisation would face when
choosing between AI-orchestrated and conventionally-staffed delivery. Both sides have real
advantages; neither dominates cleanly.
"""))

cells.append(code("""\
artifacts = [
    ('agent_1a',       'Meltano pipeline (tap-csv → target-bigquery, 9 tables)'),
    ('agent_1b',       '9 dbt staging models + sources.yml + stg schema.yml'),
    ('agent_1b',       'stg_product_category_name_translation (extra, not in spec)'),
    ('agent_1c',       '4 dimension + 3 fact mart models (76/76 dbt tests pass)'),
    ('agent_1c',       'mart schema.yml with FK relationships'),
    ('agent_1d',       'Generic tests (dbt-expectations, 76/76 PASS)'),
    ('agent_1d',       'Singular SQL tests × 3 (boleto, reconciliation, date range)'),
    ('agent_2',        'Dagster project (25 assets, 4-layer topology)'),
    ('agent_2',        'Daily 09:00 SGT schedule + launch_dagster.sh'),
    ('agent_3',        '3 analytical notebooks (11 metrics + Lorenz/Gini/HHI)'),
    ('agent_3',        'notebooks/utils.py (REGION_MAP + 4 concentration helpers)'),
    ('agent_3',        '6 Parquet feature datasets in data/'),
    ('agent_4',        'Streamlit dashboard (5 pages, 4 filters, tab layout)'),
    ('agent_4',        'dashboard_utils.py (cached loaders + init_filters)'),
    ('agent_5',        'Pipeline architecture + data lineage + star schema diagrams'),
    ('agent_5',        'Executive slide deck (.pptx) + speaker notes'),
    ('agent_5',        'Technical report, local run setup, dashboard user guide'),
    ('orch + agent_5', 'ADR-001 (date_key type)'),
    ('orch + agent_5', 'ADR-002 (dataset rename)'),
    ('orch + agent_5', 'ADR-003 (fct_reviews FK target)'),
    ('orch + agent_5', 'ADR-004 (tap selection)'),
    ('orchestrator',   'CLAUDE.md specification (2,475 words, 8 sections)'),
    ('orchestrator',   'changelog.md (46 entries, 8-day window)'),
    ('orchestrator',   'progress.md (37 REQs tracked, 36/37 complete)'),
]
art_df = pd.DataFrame(artifacts, columns=['producer','artifact'])
print(f"DELIVERABLE INVENTORY ({len(art_df)} items)\\n{'='*60}")
for prod, grp in art_df.groupby('producer', sort=False):
    print(f"\\n[{prod.upper()}]")
    for _, r in grp.iterrows():
        print(f"  • {r['artifact']}")
"""))

cells.append(code("""\
comparison = [
    ('Composition',      '8 specialist agents + 1 orchestrator',
                         '5–6 engineers (DE×2, DA×1, Dash×1, DevOps×1)'),
    ('Spec effort',      '~8,912 directive words across all directives',
                         'Story tickets + informal Slack alignment'),
    ('Parallel exec',   '1/3 theoretical pairs used (33% utilization)',
                         'Natural parallel tracks per engineer'),
    ('Deviation handling','Explicit gate reviews (GATE-1 to GATE-4)',
                          'PR review + code review rounds'),
    ('Knowledge xfer',  'Directive + context per session (stateless)',
                         'Team onboarding + tribal knowledge (stateful)'),
    ('Tool discovery',  'dbt-expectations deprecation caught mid-agent',
                         'Surfaces in initial tech selection phase'),
    ('Analysis quality','Required heavy co-design for agent_3 (involvement=5)',
                         'Senior analyst domain knowledge available immediately'),
    ('Documentation',   'Systematic, spec-driven (agent_5), zero deviations',
                         'Variable — often deferred or incomplete'),
    ('Fidelity',        f"{int((1 - df['deviations'].sum()/df['reqs_owned'].sum())*100)}% overall raw "
                        f"({df['deviations'].sum()} dev / {df['reqs_owned'].sum()} reqs)",
                         'Typically 60–80% first-pass PR approval rates'),
]
print("HUMAN vs AI FRAMEWORK COMPARISON\\n" + "="*60)
for dim, ai_val, human_val in comparison:
    print(f"\\n{dim.upper()}")
    print(f"  AI Framework : {ai_val}")
    print(f"  Human Team   : {human_val}")
"""))

# ============================================================
# ACT 6 — SYNTHESIS
# ============================================================

cells.append(md("""\
---
## Act 6 — Synthesis

> **What this Act is answering:** What can we generalise from this, and what would we do
> differently? Act 6 is where observation becomes recommendation. The 16 findings in §13 are
> the analytical conclusions; §14 is where those conclusions are stress-tested against their
> own limitations and translated into future design guidance. The executive summary at the end
> delivers the unfiltered verdict: what worked, what didn't, and what should change.

### §13 · Framework Design Findings

Every preceding section generated partial conclusions. This section synthesises them into 16
findings organised by analytical theme: Specification design, Human–AI collaboration, Cascade
risk, Architecture, and Tool Ecosystem. Together they form the evidence base for the
recommendations in §14 and the executive summary.

Each finding follows a three-part structure:
- **Finding**: the empirical conclusion, stated as directly as possible
- **Evidence**: the specific data or observation that supports it
- **Implication**: what a practitioner should do differently as a result

The findings vary substantially in their practical importance. F-05 (naming contract validation)
and F-09 (silent failure declaration) would prevent the highest-cost events observed in this
project. F-13 (canonical utility module) and F-14 (tool version pinning) are useful but
lower-leverage. Readers should weight these accordingly rather than treating all 16 as equally
actionable.
"""))

cells.append(code("""\
findings = [
  ('F-01','Specification',
   'Directive length does not predict specification fidelity',
   'Pearson r(word_count, deviation_rate) = {:.2f} — near zero.'.format(r_words),
   'Invest in constraint precision and explicitness, not word volume.'),
  ('F-02','Specification',
   'Constraint density shows a counter-intuitive positive correlation with deviation rate',
   'r(constraint_density, deviation_rate) = {:.2f} — POSITIVE (surprising). '.format(r_density) +
   'Likely a task-complexity confound: technically risky tasks '
   '(ingestion, staging, dashboard) received denser constraints AND experienced more '
   'tool-ecosystem deviations. agent_1c (density=2.50, dev_rate=0.11) is the key counter-example.',
   'Constraint density alone is not a reliable directive quality metric. '
   'Control for task complexity before comparing across agents.'),
  ('F-03','Human–AI Collaboration',
   'Human involvement is the primary driver of scope expansion',
   'r(involvement, scope_expansions) = {:.2f} — strong positive.'.format(r_inv_exp),
   'Raw scope_expansion metrics are misleading without involvement annotation. '
   'Distinguish agent-initiated from orchestrator-initiated expansions.'),
  ('F-04','Human–AI Collaboration',
   'Involvement=3 is a "friction zone" — minimum output richness, not co-design peak',
   'Quadratic fit (U-shape) with vertex≈2.6: output richness lowest at moderate involvement. '
   'involvement=1-2: agent-driven quality. involvement=4-5: orchestrator-enriched quality.',
   'Avoid partial involvement: commit to either autonomous execution or full co-design mode. '
   'Partial correction (involvement=3) yields worse output richness than either extreme.'),
  ('F-05','Cascade Risk',
   'Naming contracts are the primary fragility surface in multi-agent pipelines',
   'All contract violations were naming violations (exact strings), not semantic disagreements. '
   '_view suffix (agent_1a) cascaded into 4 downstream entries.',
   'Add naming contract validation tests at each gate. '
   'Assert stream_name == sources.yml table name before agent_1b starts.'),
  ('F-06','Cascade Risk',
   'Contract Debt is not proportional to raw deviation count',
   'agent_1a: 1 deviation → CAF=4.0. agent_1b: 3 deviations → CAF=0 (all absorbed locally).',
   'Prioritise prevention of naming/contract deviations over data-defect deviations — '
   'the former amplify; the latter localise.'),
  ('F-07','Architecture',
   'Gate-based isolation successfully contained cascade blast radius',
   '_view suffix cascade fully contained at agent_1a/1b boundary. No deviation reached mart models.',
   'Git worktree + explicit gate review is an effective blast radius containment mechanism.'),
  ('F-08','Agent Performance',
   'Downstream agents absorb upstream technical debt cleanly when gates are thorough',
   'agents_1c, 1d: ≤1 deviation, involvement=1, high first-pass after upstream gates resolved issues.',
   'Front-load human review effort at ingestion and staging. '
   'Later agents become increasingly autonomous as contracts stabilise.'),
  ('F-09','Agent Performance',
   'Silent failures produce higher cascade cost than flagged deviations',
   'agent_1a _view suffix: silent failure → CAF=4.0. '
   'agent_1b deprecated API: self-caught within own work → CAF=0.',
   'Directive should explicitly instruct agents to flag naming or config uncertainty before proceeding.'),
  ('F-10','Parallel Execution',
   'Concurrent execution is viable but requires pre-agreed intermediate output contracts',
   'agents 3+4 ran simultaneously; agent_4 scope_expansions=5 (highest) driven by live agent_3 outputs. '
   '33% of theoretical parallelism was captured.',
   'Define a written Parquet schema contract before the parallel phase. '
   'Significant parallelism headroom remains (2 additional viable pairs).'),
  ('F-11','Human–AI Collaboration',
   'Co-design mode trades efficiency for output richness — not a framework failure',
   'agent_3: human_leverage=2.0 but output_richness=5. '
   'agent_1c: human_leverage=9.0, output_richness=4.',
   'Define separate success criteria: autonomous mode (fidelity + leverage); '
   'co-design mode (output richness + stakeholder value).'),
  ('F-12','Human–AI Collaboration',
   'Human involvement correlates with upstream problem resolution, not directive length',
   'agents_1c/1d (involvement=1) benefited from upstream gate passes, not shorter directives.',
   'Orchestrator effort should be concentrated at pipeline entry points. '
   'Later agents can be more autonomous once contracts are stable.'),
  ('F-13','Architecture',
   'A canonical utility module eliminates cross-agent schema drift',
   'notebooks/utils.py: REGION_MAP, constants, add_region() — zero naming drift across all consumers.',
   'Designate shared constant modules as explicit contract surfaces.'),
  ('F-14','Tool Ecosystem',
   'Third-party library deprecation is a latent risk in LLM-directed pipelines',
   'dbt-expectations API deprecation discovered mid-agent_1b — no pre-detection mechanism.',
   'Include tool version pinning and compatibility notes in directives for all dependencies '
   'with known churn.'),
  ('F-15','Attribution',
   'Commit authorship artifacts require explicit annotation in multi-agent frameworks',
   'All commits authored by orchestrator (wrap_up_agent.sh). '
   'Timestamps = review completion, not agent work completion.',
   'Log agent session start/end times separately. '
   'Consider agent-signed commit trailers for attribution clarity.'),
  ('F-16','Specification',
   'Adjusted Spec ROI (excluding cascade/external deviations) reveals directive efficiency gaps',
   'Raw ROI collapses to 0 for 3 agents due to cascade absorption or context-forced deviations. '
   'Adjusted ROI correctly surfaces agent_1b (adj_ROI=1.89) vs agent_1a (adj_ROI=0.0).',
   'Always distinguish agent-initiated from context-forced deviations when computing efficiency metrics.'),
]

print(f"{'='*72}")
print(f"FRAMEWORK DESIGN FINDINGS ({len(findings)} total)")
for fid, cat, finding, evidence, implication in findings:
    print(f"\\n[{fid}] {cat.upper()}")
    print(f"Finding    : {finding}")
    print(f"Evidence   : {evidence}")
    print(f"Implication: {implication}")
"""))

cells.append(md("""\
### §14 · Research Implications & Future Directions

This section closes the analytical loop by confronting the findings with their own limitations.
Every conclusion in §13 rests on a measurement instrument that has known flaws. Acknowledging
them is not academic boilerplate — it is what separates a rigorous analysis from a confident
one. The future instrumentation list converts the most critical limitations directly into
concrete improvements: if we ran this framework again with those instruments in place, several
of the findings would either be confirmed with higher confidence or revised.

### Limitations
- **N=8 agents**, single project, single domain — findings are illustrative, not generalisable.
- **Retrospective self-assessment**: involvement scores and decision quality ratings were
  assigned post-hoc by the orchestrator and may carry attribution bias.
- **Involvement score is ordinal, self-reported** — captures intent, not time spent or
  interaction count.
- **Estimated fields** (revision_cycles, good/bad decisions, silent_failures) inferred from
  changelog entries and involvement notes, not direct instrumentation.
- **Constraint density keyword list** (`must|shall|required|not|only|never|always|exactly`)
  is a proxy; "not" in particular captures negation broadly and may inflate counts.

### Highest-Value Future Instrumentation
1. **Agent session duration logging** — separate from commit timestamps.
2. **Real-time expansion classification** — log at gate time whether each scope expansion was
   agent-initiated or orchestrator-requested.
3. **Silent failure detection** — instruct agents to emit a structured `[UNCERTAIN: ...]`
   marker before making unspecified decisions.
4. **Intermediate output contracts as YAML** — formalise the Parquet schema agreement between
   agents 3+4 as a versioned contract file, analogous to `sources.yml`.
5. **Parallelism expansion** — 2 additional viable parallel pairs remain untested.

### What This Framework Does Well
- **Blast radius containment** via gate reviews — confirmed empirically (§6).
- **Documentation quality** — spec-driven agents produce systematic, complete deliverables.
- **Autonomous performance at stable layers** — agents 1c, 1d, 5 with near-zero orchestrator effort.

### What Requires Human Judgment
- **Initial analysis direction** (agent_3): LLMs optimise for plausible output, not
  intellectually interesting output. Orchestrator brainstorming was the quality driver.
- **Layout and aesthetic decisions** (agent_4): iterative visual feedback not internalised
  in stateless sessions without explicit co-design.
- **Specification authoring** (orchestrator): requires deep domain knowledge, cross-agent
  constraint awareness, and forward-looking contract design.

---

### Chapter 5 Preview — Software Development Analysis
*Next chapter: mine `changelog.md`, `progress.md`, and BRD as primary sources for
requirement-level and component-level analysis: implementation timeline (8-day window,
46% of changes on Mar 16), pipeline section deviation rates (staging=100%, ingestion=67%),
requirement completion rate (36/37), BRD acceptance criteria compliance.*

---
*Notebook v3.1 · Generated by `scripts/generate_analysis_notebook.py` ·
All data from primary sources: directive files (word counts via grep),
changelog.md (46 entries), progress.md (37 REQs), orchestrator involvement notes.*
"""))

# ============================================================
# Assemble + write
# ============================================================
notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11.0"},
    },
    "cells": cells,
}
os.makedirs(os.path.dirname(NOTEBOOK_PATH), exist_ok=True)
with open(NOTEBOOK_PATH, "w") as f:
    json.dump(notebook, f, indent=1)

n_md   = sum(1 for c in cells if c["cell_type"] == "markdown")
n_code = sum(1 for c in cells if c["cell_type"] == "code")
print(f"Written: {NOTEBOOK_PATH}")
print(f"Cells: {len(cells)} ({n_md} markdown, {n_code} code)")
print(f"Sections: 14 across 6 acts")
