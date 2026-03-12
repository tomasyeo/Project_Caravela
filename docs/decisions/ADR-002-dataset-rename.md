# ADR-002: BigQuery Dataset Names — `olist_raw` / `olist_analytics` vs `raw` / `analytics`

| Field | Value |
|---|---|
| Date | 2026-03-11 |
| Status | Accepted |
| Deciders | AI Pipeline Architect; Data Engineer |
| BRD Reference | REQ-003.1; ASMP-001 |

---

## Context

The original BRD (v2.5) specified BigQuery dataset names `raw` (ingestion target) and `analytics` (transformation target). During the dbt stack review (T-01), it was identified that `raw` is a reserved word in BigQuery standard SQL. The correct names to use were decided before any implementation had begun — zero migration cost.

---

## Options Considered

### Option A — Keep `raw` / `analytics`
Use the original names as specified.

**Pros:**
- No changes required to BRD, CLAUDE.md, meltano.yml, dbt_project.yml, sources.yml, Dagster config, scripts.

**Cons:**
- `raw` is a reserved word in BigQuery standard SQL. Using it as a dataset name requires backtick-quoting (`` `raw` ``) in every query.
- dbt's BigQuery adapter handles this quoting in some versions but not all — behaviour is version-dependent and not documented as a guarantee.
- Any hand-written SQL query or notebook query referencing `raw` without backticks would fail silently or with a cryptic parse error.
- Risk surfaces at runtime, not at configuration time.

### Option B — Rename to `olist_raw` / `olist_analytics`
Prefix both dataset names with the project identifier.

**Pros:**
- Eliminates the reserved word ambiguity entirely.
- Dataset names are also more descriptive — useful in GCP Console when the project contains multiple datasets.
- Zero cost pre-implementation; requires updating ~35 references in BRD and CLAUDE.md only.

**Cons:**
- Requires updating all references in configuration files (one-time, pre-implementation).

---

## Decision

**Chosen: Option B — `olist_raw` / `olist_analytics`**

The reserved word risk in Option A is version-dependent and would surface as a non-obvious runtime failure. Renaming pre-implementation eliminates the risk at zero cost. The project identifier prefix also improves clarity in the GCP Console.

---

## Consequences

- All Meltano, dbt, Dagster, and script configuration must use `olist_raw` and `olist_analytics`.
- `sources.yml` source name: `olist_raw`. All `AssetKey` prefixes in Dagster: `["olist_raw", ...]`.
- `.env.example` documents both dataset names as environment variable hints.
- REQ-003.1 Open Item 2 closed.
- 35+ references updated across BRD v2.6 and CLAUDE.md.

---

## References

- Changelog entry: `changelog.md` 2026-03-11 (dataset rename)
- BRD: REQ-003.1 (BigQuery dataset configuration), ASMP-001 (Meltano plugin and dataset config)
