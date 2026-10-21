-- Databricks notebook source
-- Phase 0: confirm ai_query + structured output works on a Foundation Model endpoint.
-- Runs on 3 fixed real posts so models can be compared side by side:
--   databricks experimental aitools tools query --file notebooks/00_ai_query_check.sql \
--     --param model=databricks-gpt-oss-120b

WITH sample AS (
  SELECT comment_id, text_html
  FROM hn_jobs.bronze.raw_comments
  WHERE NOT is_deleted AND NOT is_dead AND length(text_html) >= 80
  ORDER BY xxhash64(comment_id)
  LIMIT 3
)
SELECT
  comment_id,
  r.result       AS extracted,
  r.errorMessage AS error
FROM (
  SELECT comment_id, ai_query(
    :model,
    'Extract fields from this Hacker News "Who is hiring?" job post (HTML). '
      || 'Use null when the post does not state a value. Salary numbers are annual amounts in the '
      || 'stated currency unless the post says otherwise.\n\nPOST:\n' || text_html,
    responseFormat => '{
      "type": "json_schema",
      "json_schema": {
        "name": "job_post",
        "strict": true,
        "schema": {
          "type": "object",
          "properties": {
            "company":       {"type": "string"},
            "seniority":     {"type": "string", "enum": ["intern","junior","mid","senior","staff+","lead","manager","unspecified"]},
            "skills":        {"type": "array", "items": {"type": "string"}},
            "remote_policy": {"type": "string", "enum": ["remote","hybrid","onsite","unspecified"]},
            "salary_min":    {"type": ["number","null"]},
            "salary_max":    {"type": ["number","null"]},
            "currency":      {"type": ["string","null"]}
          },
          "required": ["company","seniority","skills","remote_policy","salary_min","salary_max","currency"],
          "additionalProperties": false
        }
      }
    }',
    modelParameters => named_struct('temperature', CAST(0.0 AS DOUBLE)),
    failOnError => false
  ) AS r
  FROM sample
);
