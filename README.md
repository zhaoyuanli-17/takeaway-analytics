Takeaway Analytics

A Personal, Work-Context Driven Analytics Product (Real-World Data)

Why this project is different

This is an end-to-end analytics product built on my own real food delivery and work roster data (anonymized).
Instead of following a common tutorial dataset, this project proves my ability to:

clean messy multi-source data,

engineer business features,

validate hypotheses,

and deliver insights through an interactive Power BI decision layer.

Business questions

Baseline: What does my ordering and spending behavior look like over time?

Work context: Does roster/shift context explain behavior better than weekdays/weekends?

Cash-flow: Do payday and rent deadlines measurably change spending?

Food preference: What do I eat, and how do food preferences shift with context?

What you can review (verification-friendly)

Power BI dashboard (4 pages): Executive Overview · Work Context Impact · Cash-Flow Effects · Food Preference (NLP)

Reports: data quality report, insight summaries, assumptions & limitations

Reusable pipeline scripts: raw → clean → derived outputs (BI-ready)

Data sources (anonymized)

Food delivery order history from multiple platforms (e.g., Deliveroo, HungryPanda)

Work roster (shift start/end/type, hours)

Sampled menu items (manually curated) for interpretable NLP features

Note: Raw personal data is not published for privacy. The repo includes data dictionaries, processing scripts, and derived outputs so results are reproducible without exposing sensitive details.

Repository structure

data/raw/ – original exports (excluded or anonymized)

data/clean/ – cleaned, standardized tables

data/derived/ – star schema, enriched datasets, KPI tables, NLP features

src/ – cleaning, feature engineering, NLP utilities

reports/ – data quality + insights (business-readable)

powerbi/ – dashboard file / screenshots

Pipeline overview

Data cleaning & schema unification

timestamp normalization, missing value handling, duplicate field resolution

anomaly flags (delivery time issues, inconsistencies)

Analytics modeling

star-schema inspired structure (fact + dimensions) for BI consumption

Context enrichment (roster)

join orders to roster at order-date/time to derive shift features

NLP features (menu sampling)

rule-based categorization to extract interpretable signals (rice/fried/soup/noodle etc.)

Decision layer

Power BI dashboard built for stakeholder-style consumption

Dashboard walkthrough (how to talk through it)
Page 1 — Executive Overview

Establishes baseline behavior: orders, spend, AOV, median delivery experience, and platform split.

Page 2 — Work Context Impact (Key differentiator)

Replaces weekday/weekend assumptions with roster-driven context to explain behavior by shift type and post-shift ordering.

Page 3 — Cash-Flow Effects (Hypothesis testing)

Tests payday and rent assumptions:

No payday spending spike

Moderate median spend contraction near rent deadlines

Page 4 — Food Preference (NLP)

Shows context-driven food signals and an interpretable Comfort Food Score (built from category ratios such as rice/fried/soup) to approximate recovery-oriented consumption after shifts.

Key insights (summary)

Behavior is work-context driven, not calendar-driven.

Spending appears budget-stable (no payday spike), with controlled adjustment near fixed expenses.

Food choices shift with context, indicating functional/recovery-oriented consumption.

Limitations (transparent & professional)

Menu sampling: up to five representative items per restaurant were used to keep scope manageable; category ratios reflect sampled signals rather than full menus.

Vocabulary coverage: rule-based NLP may miss semantically equivalent terms (e.g., “chow mein” as noodle), leading to conservative estimates in some categories.

Findings focus on relative patterns rather than absolute preference ground truth.

Future improvements

Expand menu coverage or automate ingestion

Add synonym dictionary or embedding-based matching for better recall

Add automated refresh scheduling for derived tables and dashboard outputs

How to refresh (end-to-end system)

Drop new exports into data/raw/ (anonymized)

Run feature pipeline scripts in src/ to regenerate data/clean/ and data/derived/

Refresh Power BI to pick up updated outputs