# ADR-004: Meltano Extractor — `tap-spreadsheets-anywhere` vs `tap-csv`

| Field | Value |
|---|---|
| Date | 2026-03-11 |
| Status | Accepted |
| Deciders | Platform Engineer |
| BRD Reference | REQ-001.2; ASMP-001 |

---

## Context

Meltano requires an extractor (tap) to read the 9 Olist CSV source files and stream them to BigQuery. Two Meltano-native CSV taps were evaluated: `tap-csv` (the standard CSV tap) and `tap-spreadsheets-anywhere` (a more flexible file-based tap). The choice affects memory handling for large files and encoding support for non-standard CSVs.

Two known source data constraints drove this decision:
1. `olist_geolocation_dataset.csv` has 1,000,163 rows — memory handling matters
2. `product_category_name_translation.csv` has a UTF-8 BOM — encoding configuration matters

---

## Options Considered

### Option A — `tap-csv`
The standard Meltano CSV extractor.

**Pros:**
- Simpler configuration
- Well-documented in Meltano Hub
- Maintained by Meltano core team

**Cons:**
- Loads entire file into memory before streaming — unsafe for the 1M-row geolocation file on machines with limited RAM
- No per-file encoding configuration — UTF-8 BOM on `product_category_name_translation.csv` would corrupt the first column header, requiring a pre-processing step outside Meltano

### Option B — `tap-spreadsheets-anywhere`
A flexible file-based tap supporting per-stream configuration.

**Pros:**
- Streams file contents — safe for the 1M-row geolocation file regardless of available memory
- Supports configurable per-file `encoding` field — `encoding: utf-8-sig` resolves the UTF-8 BOM on the translation file without external pre-processing
- Single tap handles all 9 files in one `meltano run` invocation
- Per-stream `stream_name` control gives explicit BigQuery table naming, which is the contract for `sources.yml`

**Cons:**
- Slightly more complex per-stream configuration
- Less prominent in Meltano Hub documentation than `tap-csv`

---

## Decision

**Chosen: Option B — `tap-spreadsheets-anywhere`**

The two source data constraints (`geolocation` memory risk and `translation` BOM encoding) both require capabilities that `tap-csv` lacks. `tap-spreadsheets-anywhere` resolves both in native tap configuration with no external pre-processing required. The additional configuration complexity is justified.

---

## Consequences

- All 9 source files are configured as named streams in `meltano.yml` under a single `tap-spreadsheets-anywhere` extractor
- `product_category_name_translation` stream must include `encoding: utf-8-sig` — omitting it corrupts the first column header
- `stream_name` values in `meltano.yml` are the naming contract for `sources.yml` — they must match exactly
- `olist_geolocation_dataset.csv` (1M rows) loads safely but takes several minutes — Dagster asset appears unresponsive during this period; expected behaviour
- REQ-001.2 Open Items (1) and (2) closed by this selection

---

## References

- BRD: REQ-001.2 (ingestion acceptance criteria), ASMP-001 (tap selection rationale)
- CLAUDE.md: Meltano Configuration section
