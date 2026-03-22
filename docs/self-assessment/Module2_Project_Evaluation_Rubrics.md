# Module 2 Project

## Overview

In this project, as part of the data-engineering team, you are tasked to build an end-to-end data pipeline and analysis workflow for an e-commerce company. You'll start with raw data files, load them into a data warehouse, perform ETL processes, ensure data quality, and conduct analysis in Python.

You will present the project solution, key findings, and data driven business recommendations to a mixed audience of business (e.g., CEO, CMO) and technical (e.g., CTO, VP of Engineering) executives. This presentation would translate the technical work and data analysis into a compelling business narrative.

---

## Project Steps

### 1. Data Ingestion

**Source data (pick any one of these):**
- Brazilian E-Commerce Dataset by Olist
- Instacart Market Basket Analysis Dataset *(Note: the data dictionary is not available for this dataset, but most columns are easily interpretable)*
- London Bicycles dataset *(Note: this BigQuery dataset is located in EU, hence your DBT project's location has to be set to EU as well)*

Limit to the core datasets — you do not have to use all of them.

You are not limited to what you learned in the course; you can use any database technology.

**Ingest the data to your database/data warehouse**, e.g.:
- Write Python scripts to load the CSV and Excel files into the database tables.
- Or use any "ingestion" method to ingest the data.

| Grade | Criteria |
|-------|----------|
| **Excellent** | Successfully ingested data. Able to justify the decision of ingestion to the data warehouse and showed all comparisons between the various methods: listing pros and cons. |
| **Good** | Successfully ingested data. Able to justify the decision of ingestion to the data warehouse. |
| **Fair** | Attempted data ingestion but did not justify the decision of ingestion to the data warehouse. |
| **Poor** | Data ingestion was not completed or attempted. |

> **Evaluator notes:** Ingested CSV into BQ using Meltano. Also provided some justifications on why Meltano was used (in a slide).

---

### 2. Data Warehouse Design

- Design a star schema for the e-commerce data
- Create dimension tables (e.g., DimCustomer, DimProduct, DimDate) and fact tables (e.g., FactSales)
- Implement the schema in your chosen database

| Grade | Criteria |
|-------|----------|
| **Excellent** | Designed a star schema. Created most dimension and fact tables. Able to provide good justifications on the design decisions. |
| **Good** | Designed a star schema. Created most dimension and fact tables. |
| **Fair** | Attempted to design a star schema but with significant errors. Created some tables but with incorrect structure. Implementation had major gaps. |
| **Poor** | Data warehouse design was not completed or attempted. |

> **Evaluator notes:** 7 tables were created using DBT (4 dims and 3 fact tables).
>
> - **Fact tables:** `fact_sales`, `fact_reviews`, `fact_payments` — *why sales and payment in different fact tables?*
> - **Dim tables:** `dim_customers`, `dim_products`, `dim_sellers`, `dim_date`
>
> Believe sales and payment are in different fact tables because of different granularity — `fact_sales` is actually a sales-item table.

---

### 3. ELT Pipeline

- You can use dbt to transform the raw data into the star schema (not limited to dbt)
- Implement data cleaning and validation steps
- Create derived columns (e.g., `total_sale_amount`, `customer_lifetime_value`)

| Grade | Criteria |
|-------|----------|
| **Excellent** | Implemented ELT pipelines with data cleaning and validation. Also implemented derived columns (business logic) (e.g. fact tables). Was able to justify the design process with clear reasons. |
| **Good** | Implemented ELT pipelines with data cleaning and validation. Also implemented derived columns (business logic) (e.g. fact tables). |
| **Fair** | ELT pipelines are implemented to some degree. Data cleaning and validation were incomplete. Derived columns (business logic) were not fully implemented (e.g. no fact tables). |
| **Poor** | There are no ELT pipelines implemented. |

> **Evaluator notes:** Pipeline shown in the slides:
>
> `CSV → Meltano → BQ → dbt → BQ → Jupyter → Parquet → Streamlit`
>
> Interesting that Jupyter is used in this pipeline as well — why not use Streamlit to directly connect to BQ (via SQLAlchemy)?
>
> Also, with new data coming in everyday, new data will be added to BQ everyday, which means the Jupyter notebook has to run everyday for Streamlit to reflect the new data. Is the Jupyter notebook also part of the Dagster pipeline? If yes, introducing the Jupyter notebook may result in an additional point of failure in the pipeline.

---

### 4. Data Quality Testing

- Use Great Expectations or custom SQL queries to define and test data quality rules
- Implement tests for null values, duplicates, referential integrity, and business logic

| Grade | Criteria |
|-------|----------|
| **Excellent** | Used testing tools to a large degree. Good coverage in test cases. Went beyond to implement other test cases that were not taught in class. |
| **Good** | Used testing tools but with minor issues. Implemented tests for null values, duplicates, referential integrity, and business logic. |
| **Fair** | Attempted data quality testing but with significant gaps. Some tests were implemented but missing some basic test cases. |
| **Poor** | Data quality testing was not completed or attempted. |

> **Evaluator notes:** GX was used for data quality testing. Reported 76 tests, 0 failures.

---

### 5. Data Analysis with Python

When designing a data pipeline, it is essential to consider the end goal: making the data in your data warehouse accessible and usable for BI analysts, data scientists, and business stakeholders to extract valuable insights.

- Connect to the data warehouse using SQLAlchemy
- Perform simple exploratory data analysis using pandas
- Calculate key metrics like:
  - Monthly sales trends
  - Top-selling products
  - Customer segmentation by purchase behavior

| Grade | Criteria |
|-------|----------|
| **Excellent** | Data analysis was attempted with key metrics and provided reasons why they are important. Was able to link back to some of the design decisions made in the data pipelines based on the analysis or powers such analysis. |
| **Good** | Data analysis was attempted with key metrics and provided reasons why they are important. |
| **Fair** | Data analysis was attempted with some key metrics. |
| **Poor** | Data analysis was not completed or attempted. |

> **Evaluator notes:** The team presented a Streamlit dashboard with the following pages:
> - Executive overview
> - Product performance
> - Geographic analysis
> - Customer analysis
> - Glossary
>
> Importantly, filters were also implemented in the sidebar to allow users to filter by date, product category, etc.

---

### 6. Pipeline Orchestration *(Optional)*

Use any orchestration framework to orchestrate the entire pipeline. Schedule regular runs of the ELT process and data quality checks.

You can use any technology that allows scheduled runs, including (but not limited to):
- Orchestration tools (Dagster, Airflow, etc.)
- Managed services (e.g. Google Cloud Composer)
- Cron jobs
- CI/CD via GitHub Actions

| Grade | Criteria |
|-------|----------|
| **Excellent** | Entire pipeline is automated with some orchestration framework. Team was able to provide very clear justifications on why the framework was chosen and list pros vs cons on other frameworks. |
| **Good** | Entire pipeline is automated with some orchestration framework. |
| **Fair** | Added some pipeline orchestration but not complete. |
| **Poor** | Pipeline orchestration was not completed or attempted. |

> **Evaluator notes:** Dagster orchestration was mentioned briefly.

---

### 7. Documentation

- Document your code, data lineage, and pipeline architecture using tools like DRAW.IO or EXCALIDRAW to illustrate the architecture of your data pipeline system
- Prepare a report summarizing the technical approach and your findings/insights, including relevant tables/charts/graphs
  - Explain why certain tools were chosen over others
  - Explain why you decided to use your particular schema design and how it supports efficient querying (schema design justification)

| Grade | Criteria |
|-------|----------|
| **Excellent** | Documented code, data lineage, and pipeline architecture using tools like DRAW.IO or EXCALIDRAW. Prepared a comprehensive report summarizing the technical approach, findings, and insights with relevant tables/charts/graphs. Explained tool choices and schema design justification. |
| **Good** | Provided documentation with minor gaps. Report included most key information. |
| **Fair** | Documentation was incomplete or lacked detail. Report was missing key sections or explanations. |
| **Poor** | Documentation was not completed or attempted. |

> **Evaluator notes:** Well-written `README.md`, as well as documentation on dashboard, data dictionary, and troubleshooting was provided in the GitHub repo.

---

### 8. Executive Stakeholder Presentation

Present the project's architecture, insights, and business recommendations to business and technical executives. This presentation should use the slide deck and optionally any interactive aids.

| Grade | Criteria |
|-------|----------|
| **Excellent** | Delivers a highly polished and persuasive presentation tailored for a mixed executive audience. Clearly articulates the business value and actionable insights (the "so what") derived from the data. Confidently justifies the technical architecture and tool choices in terms of scalability, maintainability, cost, and direct business impact. Seamlessly and professionally handles C-level questions. |
| **Good** | Delivers a clear and professional presentation. Summarizes key insights and metrics effectively. Explains the technical architecture and tool choices with correct justifications. Answers stakeholder questions accurately. The presentation may lean slightly too technical for business leaders or too high-level for technical leaders, but is solid overall. |
| **Fair** | Presentation is largely a technical report (e.g., a verbal "read-me" of the documentation). Shows metrics but fails to explain the business implications (the "so what" is missing). Technical justifications are passable. |
| **Poor** | Presentation is unclear or not attempted. Cannot explain the project's purpose, architecture, or findings to a non-technical audience. |

> **Evaluator notes:** The team presented a Streamlit dashboard with the following pages: Executive overview, Product performance, Geographic analysis, Customer analysis, and Glossary.
>
> From the Streamlit dashboard: Identified top 15 categories by revenue, category revenue Lorenz curve, top 15 categories by freight-to-price ratio.
>
> Some recommendations were given verbally, but it will be better if put onto a slide (easier to digest).
>
> The team claim to have used 5 AI agents — data engineer, platform eng, analytics eng, dashboard eng, data scientist. Orchestrator: human + Claude.
>
> Believe this is the first team that used AI agents to completely create the ELT pipeline — overall good work and interesting implementation via AI agents. Perhaps more can be shared with the class on any downsides/difficulties with using AI agents. Can all the AI agents really replace the work of the data engineer/data scientist wholesale or is manual intervention required?
>
> **Overall, great work!**

---

## Deliverables

| # | Deliverable | Weight |
|---|-------------|--------|
| 1 | GitHub repository in a single master branch with all code and documentation | 20% |
| 2 | Written report as a slide deck | 60% |
| 3 | Jupyter notebooks with basic analysis | 20% |

---

## Evaluation Criteria

**Focus:**
- Accuracy and integrity of the data pipeline
- Quality of code and adherence to best practices
- Overall architecture and scalability of the solution
- Good documentation of your overall system — why certain designs and tools were considered

**Good to have:**
- Depth of data analysis and insights generated
