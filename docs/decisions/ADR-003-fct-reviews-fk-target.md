# ADR-003: `fct_reviews.order_id` FK Target — `stg_orders` vs `fct_sales`

| Field | Value |
|---|---|
| Date | 2026-03-11 |
| Status | Accepted |
| Deciders | AI Pipeline Architect; Data Engineer |
| BRD Reference | REQ-052.1; REQ-017.1; ASMP-004 |

---

## Context

`fct_reviews` contains a review for every order that received one. The `order_id` column needs a referential integrity test (`relationships`) targeting the table that contains all orders. Two candidates exist: `fct_sales` (the primary order-item fact table) and `stg_orders` (the staging model for the raw orders table).

This is the only place in the schema where a mart-layer fact table's FK points to a staging model rather than another mart.

---

## Options Considered

### Option A — FK targets `fct_sales`
`fct_reviews.order_id` → `fct_sales.order_id`

**Pros:**
- Keeps all mart-level FK relationships within the mart layer (consistent convention).

**Cons:**
- `fct_sales` only contains orders that have at least one order item. Source analysis confirmed 756 orders with reviews but zero items — these orders exist in `stg_orders` but not in `fct_sales`.
- With this target, the `relationships` test would fail on 756 legitimate review rows. Either the test would need to be suppressed (defeating the purpose) or 756 valid reviews would be silently dropped.

### Option B — FK targets `stg_orders`
`fct_reviews.order_id` → `stg_orders.order_id`

**Pros:**
- `stg_orders` contains all 99,441 orders — no itemless order exclusions. The `relationships` test passes cleanly.
- Correctly represents the business reality: a customer can review an order regardless of whether it has items in the order_items table.

**Cons:**
- Breaks the convention that mart FK tests only reference other mart models.
- Requires a comment in `schema.yml` to explain the cross-layer dependency — without it, future maintainers will incorrectly "fix" it to `fct_sales`.

---

## Decision

**Chosen: Option B — FK targets `stg_orders`**

Data integrity takes precedence over layer convention. The 756 itemless orders are a confirmed source data characteristic, not a data quality issue. Pointing the FK at `fct_sales` would cause the test to fail on valid data or require suppressing the test entirely, which is worse than a cross-layer reference.

The cross-layer dependency must be explicitly annotated in `schema.yml` and documented in the data lineage diagram (REQ-031.1).

---

## Consequences

- `schema.yml` must include a comment on `fct_reviews.order_id`: `# NOT ref('fct_sales') — 756 itemless orders exist`.
- The star schema ERD (REQ-032.1) must annotate this FK as a cross-layer dependency.
- The data lineage diagram (REQ-031.1) must call out `fct_reviews → stg_orders` as a deliberate cross-layer edge.
- `order_id` in `fct_reviews` is `not_null` but NOT `unique` — 547 orders have multiple reviews with distinct `review_id` values.
- REQ-017.1 cross-table test updated accordingly in BRD v2.2.

---

## References

- Changelog: not separately logged (captured in BRD v2.2 AUDIT-01 note)
- BRD: REQ-052.1 (fct_reviews deduplication and FK), REQ-017.1 (cross-table test inventory)
