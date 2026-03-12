# ADR-001: `date_key` Type — DATE vs INTEGER (YYYYMMDD)

| Field | Value |
|---|---|
| Date | 2026-03-11 |
| Status | Accepted |
| Deciders | AI Pipeline Architect; Data Engineer |
| BRD Reference | REQ-008.1; REQ-007.1; REQ-017.1 |

---

## Context

`dim_date` requires a primary key (`date_key`) that can be joined to all three fact tables (`fct_sales`, `fct_reviews`, `fct_payments`). The key must be derived from source timestamps in the staging layer and used as a foreign key in the fact tables. Two common conventions exist: DATE (native SQL date type) and INTEGER in YYYYMMDD format (e.g., 20171124).

The decision was flagged as a blocking open item in REQ-008.1 and REQ-017.1 because the `date_key` range test syntax differs between the two types.

---

## Options Considered

### Option A — DATE
`dim_date.date_key` is a `DATE` column. Staging models derive it via `DATE(CAST(timestamp_col AS TIMESTAMP))`.

**Pros:**
- `dbt_utils.date_spine` produces `DATE` natively — no extra casting in `dim_date`.
- FK joins work natively (same type both sides) — no implicit casting at query time.
- Range tests use ISO string literals (`'2016-01-01'`), which are readable and unambiguous.
- Aligns with BigQuery's native date arithmetic functions.

**Cons:**
- Slightly less portable to systems that prefer integer keys (not a concern for this project).

### Option B — INTEGER (YYYYMMDD)
`dim_date.date_key` is an `INT64` column (e.g., 20171124).

**Pros:**
- Human-readable when scanned in a query result without formatting.
- Common in legacy data warehouses and some BI tools.

**Cons:**
- `dbt_utils.date_spine` produces DATE — `dim_date` would require an explicit `FORMAT_DATE('%Y%m%d', date_day)::INT64` cast.
- All three staging models would also need `FORMAT_DATE` → `INT64` cast for FK columns.
- Range tests require integer literals (`20160101`) — easy to mistype; no built-in validation.
- No BigQuery-specific benefit; integer date keys are a pre-SQL-date-type workaround.

---

## Decision

**Chosen: Option A — DATE**

`dbt_utils.date_spine` is the authoritative source for `dim_date` rows. It natively produces DATE — choosing INTEGER would add casting in both `dim_date` and all three staging models for zero benefit in the BigQuery context. DATE type also produces cleaner, more readable SQL in notebooks and the dashboard layer.

---

## Consequences

- `dim_date.date_key` is type `DATE`; PK test uses `not_null` + `unique`.
- All three staging models cast source timestamps: `DATE(CAST(timestamp_col AS TIMESTAMP)) AS date_key`.
- `dim_date` range test: `expect_column_values_to_be_between(min_value='2016-01-01', max_value='2018-12-31')`.
- REQ-008.1 Open Item (3) closed; REQ-017.1 blocking flag removed.

---

## References

- Changelog entry: `changelog.md` 2026-03-11 (`date_key` type confirmed)
- BRD: REQ-008.1 (fct_sales schema), REQ-007.1 (dim_date), REQ-017.1 (date_key range test)
