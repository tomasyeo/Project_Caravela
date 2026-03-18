# Business Requirements Document
## Olist E-Commerce Data Pipeline

| Field | Value |
|---|---|
| Version | 1.0 |
| Status | Draft |
| Prepared by | Patrick — Requirements Analyst |
| Primary Source | `requirements.md` |
| Supplementary Sources | `README.md`, `technical_report.md`, `olist_profile.txt` |
| Date | 2026-03-08 |

---

## Foreword

This document is addressed to the **AI Pipeline Architect** as the primary implementation lead for the Olist E-Commerce Data Pipeline project.

The requirements in this BRD are organised by domain. Implementation authority is delegated per section as follows:

- **AI Pipeline Architect** — Overall pipeline architecture and tooling recommendations (Sections 6, 7). Full discretion to make architecture recommendations.
- **Data Engineer** — Schema design, ELT pipeline, and data quality implementation (Sections 2, 3, 4). Full discretion to modify schema detail as required upon actual dataset analysis.
- **Data Analyst** — Analysis layer, key metrics, and exploratory data analysis (Section 5). Full discretion over metric selection, implementation planning, and recommendations.
- **Data Scientist** — Executive stakeholder presentation (Section 8). Full discretion over content and delivery.

Each section is self-contained. Requirements within each section must be read in conjunction with the assumptions (ASMP entries) that support them. All ad hoc changes and deviations to the implementation plan must be recorded in the changelog document per REQ-037.2.

---

## Assumptions Register

| ID | Statement | Supported REQ-IDs | Source |
|---|---|---|---|
| ASMP-001 | Meltano is selected as the ingestion tool. Source data is provided as CSV files directly — not retrieved from Kaggle. | REQ-001.2 | User confirmation — no source document |
| ASMP-002 | Google BigQuery is the sole data warehouse and ingestion target for this project. DuckDB is not referenced in any requirement, constraint, or assumption. | REQ-001.2, REQ-003.1, REQ-008.1, REQ-009.1 | User confirmation — no source document |
| ASMP-003 | dbt is selected as the ELT transformation tool targeting Google BigQuery. | REQ-008.1, REQ-009.1, REQ-010.1, REQ-014.1 | User confirmation — no source document |
| ASMP-004 | Data engineer has full discretion to modify schema detail as required during implementation. Schema defined in this BRD is based on supplementary source documents and is subject to change upon actual dataset analysis. | REQ-005.1, REQ-006.1, REQ-007.1, REQ-008.1, REQ-012.1, REQ-013.1 | User confirmation — no source document |
| ASMP-005 | Derived column implementation is deferred to data engineer discretion. No specific derived columns are mandated. | REQ-013.1 | User confirmation — no source document |
| ASMP-006 | Null value and duplicate test implementation is deferred to data engineer discretion. | REQ-018.1 | User confirmation — no source document |
| ASMP-007 | Business logic tests are in scope for data quality testing. Specific rules are deferred to data engineer discretion. | REQ-017.1 | User confirmation — no source document |
| ASMP-008 | Key metrics scope and implementation (monthly sales trends, top-selling products, customer segmentation) are deferred to data analyst discretion during implementation planning. | REQ-022.1 | User confirmation — no source document |
| ASMP-009 | "Top-selling products" means highest revenue generated. | REQ-022.1 | User confirmation — no source document |
| ASMP-010 | Dagster is selected as the orchestration tool. Pipeline runs are manual execution only — no scheduled runs required. | REQ-026.1, REQ-027.1, REQ-028.1 | User confirmation — no source document |
| ASMP-011 | AI pipeline architect has full discretion to make recommendations on pipeline architecture documentation. | REQ-034.1 | User confirmation — no source document |
| ASMP-012 | Project implementation documentation and local run setup documentation are required deliverables. | REQ-035.1, REQ-036.1 | User confirmation — no source document |
| ASMP-013 | Data scientist has full discretion over Section 8 executive presentation content and delivery. | REQ-038.1 through REQ-043.1 | User confirmation — no source document |
| ASMP-014 | BRD foreword delegation model — pipeline architect as primary lead, with domain-specific delegation per section — confirmed verbally with no source document. | All | User confirmation — no source document |
| ASMP-015 | API keys for Google Cloud BigQuery connection will be provided to the data engineer. No source document specifies the provisioning process or timeline. | REQ-003.1 | User confirmation — no source document |
| ASMP-016 | Data analyst has full discretion to make recommendations on analysis implementation as appropriate. Parquet persistence for Streamlit deployment is a confirmed requirement. | REQ-022.1, REQ-025.1 | User confirmation — no source document |
| ASMP-017 | A changelog document is required to log all ad hoc changes and deviations to the implementation plan during implementation. | REQ-037.2 | User confirmation — no source document |

---

## Section 1 — Data Ingestion

---

**REQ-001.2**
Type: FR
Priority: P0
Section: Data Ingestion
Statement: The system must ingest the Brazilian E-Commerce Dataset by Olist, provided as CSV files, into Google BigQuery using Meltano as the ingestion tool.
Rationale: Raw source data must be loaded into the data warehouse before any transformation or analysis can occur.
Acceptance Criteria: All Olist CSV source files are successfully loaded into the BigQuery `raw` schema. Meltano is used as the ingestion tool. No source files are missing from the raw schema upon completion of ingestion.
Dependencies: NONE
Source: `requirements.md` §1; ASMP-001; ASMP-002
Open Items: NONE

---

**REQ-002.1**
Type: CON
Priority: P0
Section: Data Ingestion
Statement: The ingestion layer must use Meltano as the sole ingestion tool.
Rationale: Meltano was confirmed as the ingestion tool replacing the original Python/SQL script approach.
Acceptance Criteria: No ingestion scripts other than Meltano pipelines are present in the repository for the purpose of loading source data into BigQuery.
Dependencies: REQ-001.2
Source: ASMP-001
Open Items: NONE

---

**REQ-003.1**
Type: CON
Priority: P0
Section: Data Ingestion
Statement: The ingestion target must be Google BigQuery.
Rationale: BigQuery is the confirmed data warehouse for this project.
Acceptance Criteria: All raw source data is verifiably present in a Google BigQuery `raw` schema upon completion of ingestion. API keys for BigQuery connection will be provided per ASMP-015.
Dependencies: REQ-001.2
Source: ASMP-002; ASMP-015
Open Items: NONE

---

## Section 2 — Data Warehouse Design

---

**REQ-004.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a star schema in Google BigQuery consisting of a minimum of one fact table and three dimension tables.
Rationale: A star schema enables efficient analytical querying for BI and reporting use cases.
Acceptance Criteria: The BigQuery `analytics` schema contains at minimum `fct_sales`, `dim_customers`, `dim_products`, and `dim_date` tables. Each dimension table has a defined primary key. `fct_sales` contains foreign keys referencing each dimension table. Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-003.1
Source: `requirements.md` §2; `technical_report.md` §Schema Design Justification; ASMP-004
Open Items: NONE

---

**REQ-005.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a `dim_customers` dimension table containing at minimum customer unique identifier, city, state, and zip code prefix attributes.
Rationale: Customer attributes are required to support geographic filtering and customer-level analysis.
Acceptance Criteria: `dim_customers` exists in the BigQuery `analytics` schema with `customer_unique_id` as primary key and columns for `customer_city`, `customer_state`, and `customer_zip_code_prefix`. Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-004.1
Source: `technical_report.md` §Schema Design; ASMP-004
Open Items: NONE

---

**REQ-006.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a `dim_products` dimension table containing at minimum product identifier and product category attributes.
Rationale: Product attributes are required to support product-level filtering and category analysis.
Acceptance Criteria: `dim_products` exists in the BigQuery `analytics` schema with `product_id` as primary key and a `product_category` column. Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-004.1
Source: `technical_report.md` §Schema Design; ASMP-004
Open Items: NONE

---

**REQ-007.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a `dim_date` dimension table containing at minimum date key, year, month, day, day of week, and quarter attributes.
Rationale: Date attributes are required to support time-based filtering and trend analysis.
Acceptance Criteria: `dim_date` exists in the BigQuery `analytics` schema with `date_key` as primary key and columns for `year`, `month`, `day`, `day_of_week`, and `quarter`. Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-004.1
Source: `technical_report.md` §Schema Design; ASMP-004
Open Items: NONE

---

**REQ-008.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a `fct_sales` fact table containing at minimum order identifier, order item identifier, customer unique identifier, product identifier, seller identifier, date key, order status, price, and freight value.
Rationale: Transaction-level data is required to support sales analysis and reporting.
Acceptance Criteria: `fct_sales` exists in the BigQuery `analytics` schema with foreign keys referencing `dim_customers`, `dim_products`, and `dim_date`. All listed columns are present. Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-004.1; REQ-005.1; REQ-006.1; REQ-007.1
Source: `technical_report.md` §Schema Design; ASMP-003; ASMP-004
Open Items: NONE

---

**REQ-009.1**
Type: CON
Priority: P0
Section: Data Warehouse Design
Statement: The star schema must be implemented in Google BigQuery via dbt models.
Rationale: dbt is the confirmed transformation tool for producing the star schema from raw source data.
Acceptance Criteria: All star schema tables (`fct_sales`, `dim_customers`, `dim_products`, `dim_date`) are produced by dbt models targeting the BigQuery `analytics` schema. No manual SQL scripts are used to produce the final schema.
Dependencies: REQ-004.1
Source: ASMP-002; ASMP-003
Open Items: NONE

---

## Section 3 — ELT Pipeline

---

**REQ-010.1**
Type: FR
Priority: P0
Section: ELT Pipeline
Statement: The ELT pipeline must transform raw source data from the BigQuery `raw` schema into the star schema in the BigQuery `analytics` schema using dbt.
Rationale: Raw data must be cleaned, structured, and loaded into the star schema before analysis can occur.
Acceptance Criteria: All raw tables in the BigQuery `raw` schema are transformed into the star schema tables in the BigQuery `analytics` schema via dbt models. No raw tables are directly referenced in downstream analysis or reporting.
Dependencies: REQ-001.2; REQ-004.1; REQ-009.1
Source: `requirements.md` §3; `technical_report.md` §Pipeline Architecture; ASMP-003
Open Items: NONE

---

**REQ-011.1**
Type: FR
Priority: P0
Section: ELT Pipeline
Statement: The ELT pipeline must implement a staging layer consisting of dbt staging models that clean and validate raw source data prior to final schema production.
Rationale: A staging layer ensures data quality and consistency before raw data is loaded into the star schema.
Acceptance Criteria: dbt staging models exist for each raw source table. Staging models perform at minimum column renaming, type casting, and null handling. Final star schema tables are produced from staging models, not directly from raw tables.
Dependencies: REQ-010.1
Source: `technical_report.md` §Data Lineage; ASMP-003
Open Items: NONE

---

**REQ-012.1**
Type: FR
Priority: P0
Section: ELT Pipeline
Statement: The ELT pipeline must implement a data lineage path from raw source tables through staging models to final star schema tables as follows: `raw.orders` → `stg_orders`, `raw.order_items` → `stg_order_items`, `raw.customers` → `stg_customers`, `raw.products` + `raw.product_category_name_translation` → `stg_products`, staging models → `fct_sales`, `dim_customers`, `dim_products`, `dim_date`.
Rationale: Documented lineage ensures traceability from source to final schema and supports data quality verification.
Acceptance Criteria: All lineage paths listed in the statement are implemented as dbt model dependencies. dbt lineage graph reflects the documented path without gaps or untracked transformations. Data engineer may modify lineage as required upon actual dataset analysis per ASMP-004.
Dependencies: REQ-010.1; REQ-011.1
Source: `technical_report.md` §Data Lineage; ASMP-003; ASMP-004
Open Items: NONE

---

**REQ-013.1**
Type: FR
Priority: P1
Section: ELT Pipeline
Statement: The ELT pipeline must implement derived columns within the star schema. Specific derived columns are deferred to data engineer discretion during implementation.
Rationale: Derived columns support downstream analysis and reporting use cases.
Acceptance Criteria: At least one derived column is present in the star schema. All derived columns are produced by dbt models and are documented in the dbt model descriptions. Data engineer determines derived column scope per ASMP-005.
Dependencies: REQ-010.1; REQ-011.1
Source: `requirements.md` §3; ASMP-005
Open Items: Specific derived columns to be determined by data engineer during implementation planning.

---

**REQ-014.1**
Type: CON
Priority: P0
Section: ELT Pipeline
Statement: The ELT pipeline must use dbt as the sole transformation tool targeting Google BigQuery.
Rationale: dbt was confirmed as the transformation tool for this project.
Acceptance Criteria: All transformation logic is implemented as dbt models. No custom SQL transformation scripts outside of dbt are present in the repository.
Dependencies: REQ-010.1
Source: ASMP-003
Open Items: NONE

---

## Section 4 — Data Quality Testing

---

**REQ-015.1**
Type: FR
Priority: P0
Section: Data Quality Testing
Statement: The pipeline must implement data quality tests using custom SQL queries against the BigQuery `analytics` schema.
Rationale: Data quality tests ensure the integrity and completeness of the star schema before downstream analysis.
Acceptance Criteria: A suite of custom SQL quality check scripts exists in the repository targeting the BigQuery `analytics` schema. All tests are executable and produce a pass/fail result. No untested tables exist in the `analytics` schema.
Dependencies: REQ-010.1; REQ-011.1
Source: `requirements.md` §4; `README.md`; ASMP-002
Open Items: NONE

---

**REQ-016.1**
Type: FR
Priority: P0
Section: Data Quality Testing
Statement: The pipeline must implement referential integrity tests verifying that all foreign key values in `fct_sales` exist in their respective dimension tables.
Rationale: Referential integrity failures produce incorrect analytical results and must be detected before analysis.
Acceptance Criteria: Custom SQL tests verify that every `customer_unique_id`, `product_id`, and `date_key` value in `fct_sales` exists in `dim_customers`, `dim_products`, and `dim_date` respectively. Tests produce a quantified count of integrity violations. Zero violations is the passing condition.
Dependencies: REQ-015.1; REQ-004.1
Source: `technical_report.md` §Pipeline Architecture; ASMP-002
Open Items: NONE

---

**REQ-017.1**
Type: FR
Priority: P0
Section: Data Quality Testing
Statement: The pipeline must implement business logic tests against the BigQuery `analytics` schema. Specific business logic rules are deferred to data engineer discretion during implementation.
Rationale: Business logic tests verify that data conforms to expected domain rules beyond structural integrity.
Acceptance Criteria: At least one business logic test is implemented and documented. Each test produces a pass/fail result. Data engineer determines specific business logic rules per ASMP-007.
Dependencies: REQ-015.1
Source: `requirements.md` §4; ASMP-007
Open Items: Specific business logic rules to be determined by data engineer during implementation planning.

---

**REQ-018.1**
Type: FR
Priority: P1
Section: Data Quality Testing
Statement: The pipeline must implement null value and duplicate tests against the BigQuery `analytics` schema. Specific test scope is deferred to data engineer discretion during implementation.
Rationale: Null values and duplicate records produce unreliable analytical results and must be detected.
Acceptance Criteria: At least one null value test and one duplicate test are implemented and documented. Each test produces a pass/fail result. Data engineer determines specific scope per ASMP-006.
Dependencies: REQ-015.1
Source: `requirements.md` §4; ASMP-006
Open Items: Specific null value and duplicate test scope to be determined by data engineer during implementation planning.

---

**REQ-019.1**
Type: NFR
Priority: P1
Section: Data Quality Testing
Statement: All data quality tests must be executable as a single command from the project repository.
Rationale: A single executable command ensures tests can be run consistently by any team member without manual coordination.
Acceptance Criteria: A single command exists in the repository that executes all data quality tests in sequence and produces a consolidated pass/fail report. All tests complete without manual intervention.
Dependencies: REQ-015.1
Source: `requirements.md` §4
Open Items: NONE

---

## Section 5 — Data Analysis with Python

---

**REQ-020.2**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The analysis layer must use SQLAlchemy as the connector to Google BigQuery for all data retrieval operations.
Rationale: SQLAlchemy is the confirmed connector method between the Python analysis layer and BigQuery.
Acceptance Criteria: All data retrieval in Python scripts and Jupyter notebooks uses SQLAlchemy as the BigQuery connector. Connection is verified by successfully executing at least one query against the `analytics` schema.
Dependencies: REQ-003.1; REQ-004.1
Source: `requirements.md` §5
Open Items: NONE

---

**REQ-021.1**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The analysis layer must perform exploratory data analysis using pandas against data retrieved from Google BigQuery.
Rationale: pandas is explicitly named in the project brief as the required tool for exploratory data analysis.
Acceptance Criteria: A Jupyter notebook exists in the repository containing pandas-based EDA. EDA must include at minimum descriptive statistics and at least one data visualisation. All data is retrieved from the BigQuery `analytics` schema via SQLAlchemy per REQ-020.2.
Dependencies: REQ-020.2
Source: `requirements.md` §5
Open Items: NONE

---

**REQ-022.1**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The analysis layer must calculate and present key business metrics. Specific metrics are deferred to data analyst discretion during implementation planning.
Rationale: Key metrics translate pipeline output into actionable business insights for stakeholders.
Acceptance Criteria: At least three distinct business metrics are calculated and documented in a Jupyter notebook. Each metric is derived from data in the BigQuery `analytics` schema. Data analyst determines specific metric scope per ASMP-008.
Dependencies: REQ-021.1
Source: `requirements.md` §5; ASMP-008; ASMP-009
Open Items: Specific metrics to be determined by data analyst during implementation planning. Suggested starting points from brief: monthly sales trends, top-selling products by revenue, customer segmentation by purchase behaviour.

---

**REQ-023.1**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The repository must contain Jupyter notebooks with basic analysis performed against the BigQuery `analytics` schema.
Rationale: Jupyter notebooks are an explicitly required deliverable in the project brief.
Acceptance Criteria: At least one Jupyter notebook exists in the repository. The notebook contains executable code that connects to BigQuery via SQLAlchemy per REQ-020.2, performs EDA per REQ-021.1, and calculates key metrics per REQ-022.1. The notebook runs end-to-end without errors against the `analytics` schema.
Dependencies: REQ-020.2; REQ-021.1; REQ-022.1
Source: `requirements.md` Deliverables
Open Items: NONE

---

**REQ-024.1**
Type: FR
Priority: P1
Section: Data Analysis with Python
Statement: The analysis layer must include an interactive Streamlit dashboard providing at minimum Executive Overview, Product Performance, and Geographic Analysis views with global filters for Date Range, Product Category, and Customer State.
Rationale: An interactive dashboard makes analytical findings accessible to business and technical stakeholders beyond static notebook outputs.
Acceptance Criteria: `dashboard.py` exists in the repository and runs without errors. The dashboard contains three named views: Executive Overview, Product Performance, and Geographic Analysis. Global filters for Date Range, Product Category, and Customer State are functional and apply consistently across all views. All data is sourced from persisted Parquet files per REQ-025.1.
Dependencies: REQ-020.2; REQ-022.1; REQ-025.1
Source: `README.md`
Open Items: NONE

---

**REQ-025.1**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The analysis layer must persist feature datasets as Parquet files for use by the Streamlit dashboard deployment.
Rationale: Parquet persistence decouples the Streamlit dashboard from live BigQuery queries, ensuring reliable and performant dashboard deployment.
Acceptance Criteria: At least one Parquet file containing a feature dataset is produced by the analysis layer and committed to the repository. The Streamlit dashboard sources its data from persisted Parquet files, not live BigQuery queries. Data analyst determines specific dataset scope per ASMP-016.
Dependencies: REQ-022.1; REQ-024.1
Source: User confirmation; ASMP-016
Open Items: Specific feature datasets to be determined by data analyst during implementation planning.

---

## Section 6 — Pipeline Orchestration

---

**REQ-026.1**
Type: FR
Priority: P1
Section: Pipeline Orchestration
Statement: The pipeline must implement Dagster as the orchestration tool to coordinate execution of the ingestion, transformation, and data quality stages.
Rationale: Dagster was confirmed as the orchestration tool to replace the original shell script approach.
Acceptance Criteria: A Dagster project exists in the repository. Dagster assets or jobs are defined for at minimum the ingestion, dbt transformation, and data quality check stages. All stages are executable via Dagster without manual script invocation.
Dependencies: REQ-001.2; REQ-010.1; REQ-015.1
Source: ASMP-010
Open Items: NONE

---

**REQ-027.1**
Type: FR
Priority: P1
Section: Pipeline Orchestration
Statement: The pipeline must support manual execution of all orchestrated stages via Dagster.
Rationale: Manual execution is the confirmed run mode for this project — scheduled runs are not required.
Acceptance Criteria: All Dagster jobs and assets are executable on demand via the Dagster UI or CLI without requiring a schedule or sensor trigger. Pipeline completes all stages end-to-end when manually executed.
Dependencies: REQ-026.1
Source: ASMP-010
Open Items: NONE

---

**REQ-028.1**
Type: CON
Priority: P1
Section: Pipeline Orchestration
Statement: The pipeline must not implement scheduled or automated runs.
Rationale: Scheduled runs were explicitly confirmed as out of scope for this project.
Acceptance Criteria: No Dagster schedules or sensors are configured in the repository. Pipeline execution is initiated exclusively by manual trigger.
Dependencies: REQ-026.1
Source: ASMP-010
Open Items: NONE

---

**REQ-029.1**
Type: NFR
Priority: P1
Section: Pipeline Orchestration
Statement: The Dagster orchestration layer must provide visibility into pipeline execution status for all orchestrated stages.
Rationale: Execution visibility enables the team to identify and diagnose pipeline failures without inspecting raw logs.
Acceptance Criteria: Dagster UI is accessible during pipeline execution and displays run status, asset materialisation state, and error messages for each stage. All pipeline stages are represented as named assets or jobs in the Dagster UI.
Dependencies: REQ-026.1
Source: `requirements.md` §6
Open Items: NONE

---

## Section 7 — Documentation

---

**REQ-030.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a pipeline architecture diagram illustrating the end-to-end data pipeline system.
Rationale: An architecture diagram enables technical stakeholders to understand the overall system design without reading code.
Acceptance Criteria: A pipeline architecture diagram exists in the repository as an image or interactive file. The diagram reflects the confirmed tooling: Meltano, BigQuery, dbt, Dagster, and Streamlit. The diagram is committed to the main branch of the GitHub repository.
Dependencies: REQ-001.2; REQ-009.1; REQ-014.1; REQ-026.1
Source: `requirements.md` §7; `README.md`; ASMP-011
Open Items: NONE

---

**REQ-031.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a data lineage diagram illustrating the flow of data from raw source tables through staging models to the final star schema.
Rationale: A data lineage diagram supports traceability and audit of data transformations.
Acceptance Criteria: A data lineage diagram exists in the repository as an image or interactive file. The diagram reflects all confirmed lineage paths per REQ-012.1. The diagram is committed to the main branch of the GitHub repository.
Dependencies: REQ-012.1
Source: `requirements.md` §7; `README.md`
Open Items: NONE

---

**REQ-032.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a star schema diagram illustrating the structure of the `analytics` schema including all tables, columns, primary keys, and foreign keys.
Rationale: A star schema diagram enables data engineers and analysts to understand the data model without inspecting the database directly.
Acceptance Criteria: A star schema diagram exists in the repository as an image or interactive file. The diagram reflects the confirmed schema per REQ-004.1 through REQ-008.1. The diagram is committed to the main branch of the GitHub repository.
Dependencies: REQ-004.1; REQ-005.1; REQ-006.1; REQ-007.1; REQ-008.1
Source: `requirements.md` §7; `README.md`
Open Items: NONE

---

**REQ-033.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a technical report documenting the pipeline architecture, tool selection rationale, and schema design justification reflecting the confirmed tooling of Meltano, BigQuery, dbt, Dagster, and Streamlit.
Rationale: A technical report provides a written record of architectural decisions for technical stakeholders.
Acceptance Criteria: A technical report exists in the repository. The report documents rationale for Meltano, BigQuery, dbt, Dagster, and Streamlit. The report includes schema design justification. The report is committed to the main branch of the GitHub repository.
Dependencies: REQ-030.1
Source: `requirements.md` §7; `technical_report.md`; ASMP-011
Open Items: NONE

---

**REQ-034.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain an AI pipeline architecture document and diagram produced by the AI pipeline architect, who has full discretion to make recommendations on architecture design.
Rationale: AI pipeline architecture documentation captures the pipeline architect's recommendations for system design and tooling.
Acceptance Criteria: An AI pipeline architecture document and a corresponding diagram both exist in the repository. Both are produced by the AI pipeline architect. Both are committed to the main branch of the GitHub repository.
Dependencies: REQ-030.1
Source: ASMP-011
Open Items: Scope and content of AI pipeline architecture document and diagram deferred to AI pipeline architect discretion.

---

**REQ-035.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a project implementation document describing how the pipeline was built and how each component was implemented.
Rationale: Project implementation documentation enables team members and reviewers to understand the build process without prior context.
Acceptance Criteria: A project implementation document exists in the repository. The document covers each pipeline component: ingestion, transformation, data quality, analysis, orchestration, and documentation. The document is committed to the main branch of the GitHub repository.
Dependencies: NONE
Source: ASMP-012
Open Items: NONE

---

**REQ-036.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a local run setup document providing step-by-step instructions to execute the pipeline on a local machine.
Rationale: Local run setup documentation enables any team member to reproduce the pipeline without prior knowledge of the implementation.
Acceptance Criteria: A local run setup document exists in the repository. The document provides step-by-step instructions covering environment setup, dependency installation, credential configuration, and pipeline execution via Dagster. A person with no prior context must be able to execute the pipeline end-to-end by following the document alone. The document is committed to the main branch of the GitHub repository.
Dependencies: REQ-026.1; REQ-027.1
Source: ASMP-012
Open Items: NONE

---

**REQ-037.2**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a changelog document that records all ad hoc changes and deviations to the implementation plan made during implementation.
Rationale: A changelog ensures traceability between the agreed implementation plan and the as-built system, capturing decisions made during implementation that differ from the original plan.
Acceptance Criteria: A changelog document exists in the repository. Each entry records at minimum the date, the affected component, a description of the change or deviation to the implementation plan, and the reason for the change. The changelog is updated at the time each deviation occurs — not retrospectively at project completion. The document is committed to the main branch of the GitHub repository.
Dependencies: NONE
Source: ASMP-017
Open Items: NONE

---

## Section 8 — Executive Stakeholder Presentation

---

**REQ-038.1**
Type: FR
Priority: P0
Section: Executive Stakeholder Presentation
Statement: The project must produce a slide deck presenting the pipeline architecture, key findings, and business recommendations to a mixed audience of technical and business executives.
Rationale: A slide deck is an explicitly required deliverable in the project brief.
Acceptance Criteria: A slide deck exists in the repository committed to the main branch. The deck contains at minimum an executive summary, technical solution overview, and business recommendations sections. The deck is accessible without specialist software. Data scientist has full discretion over content and delivery per ASMP-013.
Dependencies: REQ-033.1
Source: `requirements.md` Deliverables; `README.md`; ASMP-013
Open Items: Specific content, structure, and delivery deferred to data scientist discretion.

---

**REQ-039.1**
Type: FR
Priority: P0
Section: Executive Stakeholder Presentation
Statement: The presentation must include an executive summary providing a concise overview of the problem, solution, and business impact within a maximum of 3 minutes of presentation time.
Rationale: An executive summary is an explicitly recommended component of the presentation in the project brief.
Acceptance Criteria: The slide deck contains a clearly labelled executive summary section. The section is deliverable within 3 minutes of presentation time. Data scientist has full discretion over content per ASMP-013.
Dependencies: REQ-038.1
Source: `requirements.md` §8; ASMP-013
Open Items: NONE

---

**REQ-040.1**
Type: FR
Priority: P0
Section: Executive Stakeholder Presentation
Statement: The presentation must include a technical solution overview providing a high-level description of the pipeline architecture without overwhelming technical detail.
Rationale: Technical executives require sufficient technical depth to evaluate the solution without alienating business executives.
Acceptance Criteria: The slide deck contains a clearly labelled technical solution overview section. The section references the confirmed tooling: Meltano, BigQuery, dbt, Dagster, and Streamlit. Architecture diagrams per REQ-030.1 are referenced or embedded. Data scientist has full discretion over content per ASMP-013.
Dependencies: REQ-038.1; REQ-030.1
Source: `requirements.md` §8; `technical_report.md` §Pipeline Architecture; ASMP-013
Open Items: NONE

---

**REQ-041.1**
Type: FR
Priority: P1
Section: Executive Stakeholder Presentation
Statement: The presentation must include an honest assessment of technical risks, limitations, and mitigation strategies relevant to the pipeline implementation.
Rationale: Risk and mitigation is an explicitly recommended component of the presentation in the project brief.
Acceptance Criteria: The slide deck contains a clearly labelled risk and mitigation section. At least one technical risk is identified with a corresponding mitigation strategy. Data scientist has full discretion over content per ASMP-013.
Dependencies: REQ-038.1
Source: `requirements.md` §8; ASMP-013
Open Items: Specific risks and mitigations deferred to data scientist discretion.

---

**REQ-042.1**
Type: FR
Priority: P0
Section: Executive Stakeholder Presentation
Statement: The presentation must include interactive aids supporting the delivery of findings to the mixed executive audience.
Rationale: Interactive aids enhance stakeholder engagement and comprehension of analytical findings.
Acceptance Criteria: At minimum one interactive aid — either `presentation.html` or the Streamlit dashboard per REQ-024.1 — is available and functional during the presentation. Data scientist has full discretion over selection and use per ASMP-013.
Dependencies: REQ-024.1; REQ-038.1
Source: `README.md`; ASMP-013
Open Items: NONE

---

**REQ-043.1**
Type: NFR
Priority: P0
Section: Executive Stakeholder Presentation
Statement: The presentation must be deliverable within a total duration of 15 minutes — 10 minutes presentation and 5 minutes Q&A.
Rationale: Duration is explicitly specified in the project brief.
Acceptance Criteria: The presentation is completed within 10 minutes. A Q&A period of 5 minutes follows. All team members are present and prepared to answer questions from both technical and business executives.
Dependencies: REQ-038.1
Source: `requirements.md` §8
Open Items: NONE

---

## Requirements Index

| REQ-ID | Type | Priority | Section |
|---|---|---|---|
| REQ-001.2 | FR | P0 | Data Ingestion |
| REQ-002.1 | CON | P0 | Data Ingestion |
| REQ-003.1 | CON | P0 | Data Ingestion |
| REQ-004.1 | FR | P0 | Data Warehouse Design |
| REQ-005.1 | FR | P0 | Data Warehouse Design |
| REQ-006.1 | FR | P0 | Data Warehouse Design |
| REQ-007.1 | FR | P0 | Data Warehouse Design |
| REQ-008.1 | FR | P0 | Data Warehouse Design |
| REQ-009.1 | CON | P0 | Data Warehouse Design |
| REQ-010.1 | FR | P0 | ELT Pipeline |
| REQ-011.1 | FR | P0 | ELT Pipeline |
| REQ-012.1 | FR | P0 | ELT Pipeline |
| REQ-013.1 | FR | P1 | ELT Pipeline |
| REQ-014.1 | CON | P0 | ELT Pipeline |
| REQ-015.1 | FR | P0 | Data Quality Testing |
| REQ-016.1 | FR | P0 | Data Quality Testing |
| REQ-017.1 | FR | P0 | Data Quality Testing |
| REQ-018.1 | FR | P1 | Data Quality Testing |
| REQ-019.1 | NFR | P1 | Data Quality Testing |
| REQ-020.2 | FR | P0 | Data Analysis with Python |
| REQ-021.1 | FR | P0 | Data Analysis with Python |
| REQ-022.1 | FR | P0 | Data Analysis with Python |
| REQ-023.1 | FR | P0 | Data Analysis with Python |
| REQ-024.1 | FR | P1 | Data Analysis with Python |
| REQ-025.1 | FR | P0 | Data Analysis with Python |
| REQ-026.1 | FR | P1 | Pipeline Orchestration |
| REQ-027.1 | FR | P1 | Pipeline Orchestration |
| REQ-028.1 | CON | P1 | Pipeline Orchestration |
| REQ-029.1 | NFR | P1 | Pipeline Orchestration |
| REQ-030.1 | FR | P0 | Documentation |
| REQ-031.1 | FR | P0 | Documentation |
| REQ-032.1 | FR | P0 | Documentation |
| REQ-033.1 | FR | P0 | Documentation |
| REQ-034.1 | FR | P0 | Documentation |
| REQ-035.1 | FR | P0 | Documentation |
| REQ-036.1 | FR | P0 | Documentation |
| REQ-037.2 | FR | P0 | Documentation |
| REQ-038.1 | FR | P0 | Executive Stakeholder Presentation |
| REQ-039.1 | FR | P0 | Executive Stakeholder Presentation |
| REQ-040.1 | FR | P0 | Executive Stakeholder Presentation |
| REQ-041.1 | FR | P1 | Executive Stakeholder Presentation |
| REQ-042.1 | FR | P0 | Executive Stakeholder Presentation |
| REQ-043.1 | NFR | P0 | Executive Stakeholder Presentation |

---

## Completeness Summary

| Requirement Type | Count | Sections Present |
|---|---|---|
| FR (Functional) | 34 | 1, 2, 3, 4, 5, 6, 7, 8 |
| NFR (Non-Functional) | 3 | 4, 6, 8 |
| CON (Constraint) | 6 | 1, 2, 3, 6 |
| ASMP (Assumption) | 17 | All |

**Priority distribution:**
- P0: 35 requirements
- P1: 8 requirements
- P2: 0 requirements

**Flagged gaps (no source material — not invented):**
- NFRs absent from Sections 5 and 7 — source material contains no performance, availability, or latency requirements for these sections.
- CONs absent from Sections 4, 7, and 8 — source material contains no technology, budget, or regulatory constraints specific to these sections.

---

*End of Document — BRD Olist E-Commerce Data Pipeline v1.0*
