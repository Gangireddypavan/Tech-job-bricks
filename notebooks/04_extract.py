# Databricks notebook source
# Phase 3: LLM extraction of job-post fields into hn_jobs.gold.job_posts using ai_query.
#
# Incremental: each run takes the next `batch_size` posts (oldest first) that are not yet
# extracted, whose text changed, whose prompt version or model is stale, or that errored last time.
# The batch is materialized once into a staging table so each post costs exactly one LLM
# call, then MERGEd into gold. Run repeatedly (e.g. daily) until `pending_after` is 0.

# COMMAND ----------

# MAGIC %run ./extraction_spec

# COMMAND ----------

import json
import time

dbutils.widgets.text("catalog", "hn_jobs")
dbutils.widgets.text("endpoint", "databricks-gpt-oss-120b")
dbutils.widgets.text("batch_size", "1000")
CATALOG = dbutils.widgets.get("catalog")
ENDPOINT = dbutils.widgets.get("endpoint")
BATCH_SIZE = int(dbutils.widgets.get("batch_size"))

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.gold.job_posts (
  comment_id BIGINT NOT NULL, thread_month DATE, hn_url STRING,
  is_job_post BOOLEAN, company STRING,
  roles ARRAY<STRUCT<title: STRING, seniority: STRING>>, seniorities ARRAY<STRING>,
  skills ARRAY<STRING>, remote_policy STRING, remote_regions ARRAY<STRING>,
  locations ARRAY<STRING>, countries ARRAY<STRING>, employment_types ARRAY<STRING>,
  visa_sponsorship STRING, salary_min DOUBLE, salary_max DOUBLE, salary_currency STRING,
  salary_period STRING, equity BOOLEAN,
  raw_json STRING, error STRING, text_hash STRING, prompt_version STRING, model STRING,
  extracted_at TIMESTAMP
) COMMENT 'LLM-extracted fields per HN job post (ai_query, see extraction_spec PROMPT_VERSION)'
""")

pending_filter = f"""
  FROM {CATALOG}.silver.posts p
  LEFT JOIN {CATALOG}.gold.job_posts g ON p.comment_id = g.comment_id
  WHERE g.comment_id IS NULL OR g.text_hash <> p.text_hash
     OR g.prompt_version <> '{PROMPT_VERSION}' OR g.model <> '{ENDPOINT}' OR g.error IS NOT NULL
"""
pending_before = spark.sql(f"SELECT count(*) AS n {pending_filter}").collect()[0]["n"]

# COMMAND ----------

t0 = time.time()
spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.gold._extract_batch AS
SELECT comment_id, thread_month, hn_url, text_hash, r.result AS raw_json, r.errorMessage AS error
FROM (
  SELECT p.comment_id, p.thread_month, p.hn_url, p.text_hash, {ai_query_expr(ENDPOINT, 'p.text')} AS r
  FROM (
    SELECT p.* {pending_filter}
    ORDER BY p.created_at, p.comment_id
    LIMIT {BATCH_SIZE}
  ) p
)
""")
llm_seconds = round(time.time() - t0, 1)

spark.sql(f"""
MERGE INTO {CATALOG}.gold.job_posts t
USING (
  SELECT b.comment_id, b.thread_month, b.hn_url, j.is_job_post, j.company, j.roles,
         array_distinct(transform(j.roles, r -> r.seniority)) AS seniorities,
         j.skills, j.remote_policy, j.remote_regions, j.locations,
         transform(j.countries, c -> upper(trim(c))) AS countries,
         j.employment_types, j.visa_sponsorship, j.salary_min, j.salary_max,
         upper(j.salary_currency) AS salary_currency, j.salary_period, j.equity,
         b.raw_json,
         coalesce(b.error, CASE WHEN j.is_job_post IS NULL THEN 'unparseable model output' END) AS error,
         b.text_hash, '{PROMPT_VERSION}' AS prompt_version, '{ENDPOINT}' AS model,
         current_timestamp() AS extracted_at
  FROM (SELECT *, from_json(raw_json, '{RESULT_DDL}') AS j FROM {CATALOG}.gold._extract_batch) b
) s
ON t.comment_id = s.comment_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
""")

# COMMAND ----------

batch = spark.sql(f"""
  SELECT count(*) AS n, count(error) AS errors FROM {CATALOG}.gold._extract_batch
""").collect()[0]
summary = {
    "prompt_version": PROMPT_VERSION,
    "model": ENDPOINT,
    "batch_rows": batch["n"],
    "batch_errors": batch["errors"],
    "llm_seconds": llm_seconds,
    "pending_before": pending_before,
    "pending_after": spark.sql(f"SELECT count(*) AS n {pending_filter}").collect()[0]["n"],
    "gold_rows": spark.table(f"{CATALOG}.gold.job_posts").count(),
}
print(json.dumps(summary, indent=2))
dbutils.notebook.exit(json.dumps(summary))
