-- Databricks notebook source
-- Phase 0: Unity Catalog objects for the HN jobs tracker.
-- Free Edition workspaces come with a `workspace` catalog on default storage; if
-- CREATE CATALOG is not permitted, run the same statements with `workspace` and
-- prefix schema names with `hn_` instead (see PLAN.md, Phase 0).

CREATE CATALOG IF NOT EXISTS hn_jobs
  COMMENT 'Hacker News "Who is hiring?" job market tracker';

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS hn_jobs.bronze COMMENT 'Raw HN comments as fetched';
CREATE SCHEMA IF NOT EXISTS hn_jobs.silver COMMENT 'Cleaned top-level job posts';
CREATE SCHEMA IF NOT EXISTS hn_jobs.gold   COMMENT 'LLM-extracted fields and chart tables';

-- COMMAND ----------

CREATE VOLUME IF NOT EXISTS hn_jobs.bronze.landing
  COMMENT 'JSONL drops from fetch_hn.py (local or notebook)';
