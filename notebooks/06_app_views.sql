-- Databricks notebook source
-- Views the app and the Genie space read. All are views over gold.job_posts, so they
-- pick up each extraction batch immediately.

-- Fixed reference exchange rates for comparing salaries across currencies. Approximate
-- 2026 averages, not live rates: good enough for medians and trends, not for payroll.
CREATE OR REPLACE TABLE hn_jobs.gold.fx_to_usd
COMMENT 'Approximate USD value of one unit of each currency (fixed 2026 reference rates)'
AS SELECT * FROM VALUES
  ('USD', 1.0), ('EUR', 1.08), ('GBP', 1.27), ('CAD', 0.73), ('AUD', 0.66), ('NZD', 0.60),
  ('CHF', 1.12), ('SEK', 0.095), ('NOK', 0.093), ('DKK', 0.145), ('PLN', 0.25), ('CZK', 0.043),
  ('INR', 0.012), ('SGD', 0.74), ('JPY', 0.0066), ('ILS', 0.27), ('BRL', 0.18), ('MXN', 0.055),
  ('ZAR', 0.055), ('HKD', 0.128), ('AED', 0.27)
AS t(currency, usd_per_unit);

-- COMMAND ----------

CREATE OR REPLACE VIEW hn_jobs.gold.jobs
COMMENT 'One row per HN "Who is hiring?" job post (non-job comments and failed extractions removed). Salaries also converted to annual USD.'
AS
WITH base AS (
  SELECT j.*,
         CASE j.salary_period WHEN 'hour' THEN 2080 WHEN 'month' THEN 12 ELSE 1 END * fx.usd_per_unit AS to_annual_usd
  FROM hn_jobs.gold.job_posts j
  LEFT JOIN hn_jobs.gold.fx_to_usd fx ON fx.currency = j.salary_currency
  WHERE j.is_job_post AND j.error IS NULL
),
usd AS (
  SELECT *,
         round(salary_min * to_annual_usd) AS min_usd,
         round(salary_max * to_annual_usd) AS max_usd
  FROM base
)
SELECT comment_id, thread_month, hn_url, company,
       roles, seniorities, skills, remote_policy, remote_regions, locations, countries,
       employment_types, visa_sponsorship, equity,
       salary_min, salary_max, salary_currency, salary_period,
       -- annual USD; NULL when the currency has no reference rate or the value is implausible
       CASE WHEN min_usd BETWEEN 10000 AND 1000000 THEN min_usd END AS salary_min_usd,
       CASE WHEN max_usd BETWEEN 10000 AND 1000000 THEN max_usd END AS salary_max_usd,
       CASE WHEN coalesce(min_usd, max_usd) BETWEEN 10000 AND 1000000
            THEN round((coalesce(min_usd, max_usd) + coalesce(max_usd, min_usd)) / 2) END AS salary_mid_usd
FROM usd;

-- COMMAND ----------

CREATE OR REPLACE VIEW hn_jobs.gold.post_roles
COMMENT 'One row per role advertised in a job post, with its seniority level'
AS
SELECT j.comment_id, j.thread_month, r.title, r.seniority
FROM hn_jobs.gold.jobs j
LATERAL VIEW explode(j.roles) e AS r;

-- COMMAND ----------

CREATE OR REPLACE VIEW hn_jobs.gold.post_countries
COMMENT 'One row per job post and country (ISO 3166-1 alpha-2) the roles can be done from'
AS
SELECT DISTINCT j.comment_id, j.thread_month,
       CASE c WHEN 'UK' THEN 'GB' ELSE c END AS country_code  -- UK is common but not ISO
FROM hn_jobs.gold.jobs j
LATERAL VIEW explode(j.countries) e AS c
WHERE c RLIKE '^[A-Z]{2}$';
