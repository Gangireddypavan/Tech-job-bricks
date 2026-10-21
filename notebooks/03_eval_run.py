# Databricks notebook source
# Phase 3 eval: run each extraction method on the fixed 50-post sample and store the raw
# JSON output in hn_jobs.gold.eval_predictions. Scoring happens in eval/score.py.

# COMMAND ----------

# MAGIC %run ./extraction_spec

# COMMAND ----------

import json
import time

dbutils.widgets.text("catalog", "hn_jobs")
dbutils.widgets.text("methods", "gpt-oss-120b,llama-3.3-70b,ai_extract")
CATALOG = dbutils.widgets.get("catalog")
METHODS = [m.strip() for m in dbutils.widgets.get("methods").split(",") if m.strip()]

ENDPOINTS = {
    "gpt-oss-120b": "databricks-gpt-oss-120b",
    "gpt-oss-20b": "databricks-gpt-oss-20b",
    "llama-3.3-70b": "databricks-meta-llama-3-3-70b-instruct",
    "llama-4-maverick": "databricks-llama-4-maverick",
    "qwen3-next-80b": "databricks-qwen3-next-80b-a3b-instruct",
    "qwen35-122b": "databricks-qwen35-122b-a10b",
    "gemma-3-12b": "databricks-gemma-3-12b",
}

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.gold.eval_predictions (
  method STRING, comment_id BIGINT, raw STRING, error STRING, run_at TIMESTAMP
) COMMENT 'Raw extraction output per method on gold.eval_sample'
""")


def select_for(name):
    if name == "ai_extract":
        return f"""
          SELECT comment_id, CAST(r:response AS STRING) AS raw, r:error_message::STRING AS error
          FROM (SELECT comment_id, {ai_extract_expr()} AS r FROM {CATALOG}.gold.eval_sample)"""
    return f"""
      SELECT comment_id, r.result AS raw, r.errorMessage AS error
      FROM (SELECT comment_id, {ai_query_expr(ENDPOINTS[name])} AS r FROM {CATALOG}.gold.eval_sample)"""


timings = {}
for name in METHODS:
    method = f"{name}@{PROMPT_VERSION}"
    spark.sql(f"DELETE FROM {CATALOG}.gold.eval_predictions WHERE method = '{method}'")
    t0 = time.time()
    try:
        spark.sql(f"""
          INSERT INTO {CATALOG}.gold.eval_predictions
          SELECT '{method}', comment_id, raw, error, current_timestamp() FROM ({select_for(name)})
        """)
        timings[method] = {"seconds": round(time.time() - t0, 1)}
    except Exception as e:
        timings[method] = {"seconds": round(time.time() - t0, 1), "failed": str(e)[:500]}
    print(method, timings[method])

# COMMAND ----------

counts = {r["method"]: {"rows": r["n"], "errors": r["errs"]} for r in spark.sql(f"""
  SELECT method, count(*) AS n, count(error) AS errs FROM {CATALOG}.gold.eval_predictions GROUP BY method
""").collect()}
for m in timings:
    timings[m].update(counts.get(m, {}))
dbutils.notebook.exit(json.dumps(timings))
