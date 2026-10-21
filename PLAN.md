# HN "Who is hiring?" Tech Job Market Tracker — Plan

Goal: collect every top-level job post from the monthly HN "Ask HN: Who is hiring?" threads since
January 2025, use an LLM to pull out structured fields, show charts, and answer plain-English
questions. Everything runs on a **Databricks Free Edition** workspace.

## Status (2026-10-22)

- **Workspace:** CLI profile `Brick` (dbc-e68d2f1a-611c). Catalog `hn_jobs` created on Free Edition, with
  schemas `bronze`/`silver`/`gold` and volume `bronze.landing`.
- **Outbound access:** Algolia, the HN Firebase API and news.ycombinator.com are all reachable from
  serverless. Ingestion runs inside the workspace, so the local-upload fallback isn't needed.
- **Phase 1 done:** [notebooks/01_bronze_ingest.py](notebooks/01_bronze_ingest.py) loaded 22 threads
  (2025-01 → 2026-10) into `bronze.threads` and 7,890 top-level comments into `bronze.raw_comments`.
  For every thread, the stored count equals HN's own list of top-level comments (`kids`).
  - 6,981 came from Algolia. The 909 that Algolia lacked (fetched from Firebase) are all deleted or dead.
  - **6,932 usable posts** (not deleted, not dead, ≥ 80 characters) go forward to Phase 2.
- **Models (Phase 0 done):** the chat endpoints available are gpt-oss-120b/20b, qwen35-122b,
  qwen3-next-80b, llama-3.3-70b, llama-4-maverick, llama-3.1-8b, gemma-3-12b and deepseek-v4-flash.
  There are no Claude or GPT-5-class models. Results of
  [notebooks/00_ai_query_check.sql](notebooks/00_ai_query_check.sql) (strict `json_schema`,
  3 real posts):
  - **gpt-oss-120b:** correct on all 3, and it doesn't invent skills (20 s). **Leading candidate.**
  - **llama-3.3-70b:** fast (6 s), but it listed "Software Engineers" as a skill. Fallback.
  - **qwen35-122b:** too slow (195 s for 3 posts) and filled skills with generic terms.
  - **deepseek-v4-flash:** "not supported for batch inference", so it can't be used with `ai_query`.
  - Gotcha: with `failOnError => false`, the result struct is `{result, errorMessage}`, not `response`.
  - The final model choice comes from the 50-post eval in Phase 3. `ai_extract` v2.1 (with `instructions`)
    is a second option to evaluate there.
- **Phase 2 done:** [notebooks/02_silver_clean.py](notebooks/02_silver_clean.py) builds `silver.posts`.
  It holds **6,923 posts**, with HTML converted to text, link URLs kept in full, `header_line` (the first
  line), `links[]`, `text_hash` and `hn_url`.
  - 92% of posts have a `Company | Role | …` header. Median length is 1,010 characters.
  - Any `<…>` left in the text is genuine: deliberately disguised emails, `<https://…>` links and placeholders.
- **Phase 3 eval done. Model: `databricks-gpt-oss-120b` with prompt v2.**
  - The prompt and schema live in one place, [notebooks/extraction_spec.py](notebooks/extraction_spec.py),
    which carries a `PROMPT_VERSION`. The schema gained an `is_job_post` field, because the threads also
    contain commentary and consultants selling services (2 of the 50 sample posts).
  - The sample is 50 fixed posts in `gold.eval_sample`. Labels are in [eval/labels.jsonl](eval/labels.jsonl),
    the runner is [notebooks/03_eval_run.py](notebooks/03_eval_run.py), the scorer is
    [eval/score.py](eval/score.py), and the results are in [eval/results.md](eval/results.md)
    (v1 in [eval/results_v1.md](eval/results_v1.md)).
  - v1, with the same prompt for all three methods:

    | Metric | gpt-oss-120b | llama-3.3-70b | ai_extract |
    |---|---|---|---|
    | Seniority, exact set | 88% | 81% | 79% |
    | Skills F1 | 89% | 79% | 86% |

    The three tie on remote policy (94–96%) and salary (96%). llama invented a salary once, and
    ai_extract invented staff+ levels.
  - v2 changes the prompt after reviewing the v1 misses: "up to X" and "X+" are bounds, there are
    explicit non-skill exclusions, "Senior/Staff" splits into two levels, and is_job_post covers posts
    that never say "hiring". Two salary labels changed to match the clarified rule (both are noted in
    the labels file).
  - **gpt-oss-120b v2:** seniority 94% exact (97% Jaccard), skills F1 99%, salary 100%, is_job_post
    100%, remote 92% (98% on unambiguous posts). All targets are met.
  - Caveat: v2 was tuned on the same 50 posts it was scored on, so these numbers are optimistic.
    Spot-check a fresh sample after the first production batch.
  - **Prompt v3** adds `countries` as ISO alpha-2 codes. These cover office countries and countries named
    for remote work. Regions like EU, LATAM or Worldwide stay in `remote_regions`.
  - **Production extraction:** [notebooks/04_extract.py](notebooks/04_extract.py) writes to
    `gold.job_posts`. It's incremental, taking the oldest pending posts first, and re-extracts a post if
    its text, the prompt version or a previous error changes. The batch is staged once, so each post gets
    exactly one LLM call.
  - **First 20 posts (2026-10-22), reviewed by hand against each post:** 20/20 parsed, 0 errors, 45 s.
    - Countries: correct on 20/20. 4 are empty, but correctly so, because those posts only name a region.
    - Remote: 19/20. Accretional is "on-site 4 days/week" and came back onsite, but the rules say hybrid.
    - Salary: 6 of the 8 posts with pay are correct. SmarterDx "150-230k+" lost its 230k max. Kombo
      (Berlin, "60k-100k") got USD instead of EUR.
    - Skill names aren't canonical yet (NextJS, Typescript, Node, "Google Cloud Platform"). This needs the
      planned alias-normalization step.
    - 6,903 posts are still pending.
  - **Prompt v4** fixes the salary rules. A range keeps both ends even when the upper one has a "+"
    ("150-230k+" → 150k–230k). Figures with no currency symbol use the office country's currency, never
    a default of USD. On re-check, all 8 posts with pay among the first 20 are now correct (SmarterDx and
    Kombo are fixed). As a side effect, Accretional's "4 days on-site" now comes back hybrid.
  - **Skill normalization:** [notebooks/05_skills.sql](notebooks/05_skills.sql) builds `gold.skill_aliases`
    (a match key mapped to a canonical name, about 130 entries) and `gold.post_skills` (one row per post
    and canonical skill). It never calls the LLM. Keys with no alias fall back to their most common
    spelling. After the full run, review the top unmapped keys and extend the alias list.
  - **Full run:** [scripts/run_extraction.ps1](scripts/run_extraction.ps1) loops `04_extract` in batches of
    1,000 until nothing is pending, then rebuilds `post_skills`. It logs to `logs/extraction.log` and stops
    at the first failed batch (for example when the daily quota runs out). Re-running it resumes. Started
    2026-10-22. In practice it runs at about 5 minutes per 1,000 posts, because larger batches run in parallel.
- **Model comparison on prompt v4** (50 posts, with country labels added). Results are in
  [eval/results_v4.md](eval/results_v4.md):

  | Model | Seniority | Remote | Salary | Countries | Skills F1 | 50 posts |
  |---|---|---|---|---|---|---|
  | **gpt-oss-120b** | 90% | 94% | 100% | 94% | 97% | 134 s |
  | llama-4-maverick | 88% | 88% | 100% | 96% | 95% | 24 s |
  | ai_extract | 85% | 94% | 100% | 94% | 94% | 63 s |
  | gpt-oss-20b | 88% | 88% | 98% | 96% | 91% | 81 s |
  | llama-3.3-70b | 85% | 88% | 92% | 83% | 85% | 15 s |
  | qwen3-next-80b | 83% | 83% | 100% | 90% | 84% | 25 s |
  | gemma-3-12b | 79% | 75% | 79% | 90% | 79% | 21 s |
  | qwen35-122b | 90% | 100% | 100% | 100% | 97% | 365 s |

  qwen35-122b's scores cover only the 43 of 50 posts where its output could be parsed (7 were unreadable),
  and it would need about 14 h for all posts, so it isn't usable. **gpt-oss-120b stays the model.**
- **Phase 4 app (built 2026-10-22, running locally, not deployed yet):**
  - Views for the app and Genie are in [notebooks/06_app_views.sql](notebooks/06_app_views.sql). `gold.jobs`
    holds job posts only and adds `salary_*_usd`, which is annual USD at fixed reference rates from
    `gold.fx_to_usd`. `gold.post_roles` and `gold.post_countries` are exploded views, with UK normalized
    to GB. `post_skills` is now a view too, so the app updates as each batch lands.
  - Genie space "HN Tech Job Market" (`01f1cd86c2551a3d8fd3868fbfa90429`) is defined in
    [genie/build_space.py](genie/build_space.py). It covers the 4 views with joins, column descriptions
    and synonyms, entity matching, 5 checked example SQLs, sample questions and a short note on data
    quality. The Conversation API works on Free Edition.
  - Streamlit app in [app/](app/):
    - Pages: Overview (KPIs, posts per month, remote mix, seniority mix), Skills (top 25, trend lines,
      fastest growing and declining), Salary (median and IQR by seniority, remote, skill, country and
      month), Locations (log-scale map and country table), Explore (searchable posts linking to HN), and
      Ask (Genie chat with the answer, chart, table, SQL and follow-ups).
    - Sidebar filters cover months, remote policy, seniority and country.
  - Run locally with `pwsh scripts/run_app_local.ps1` → http://localhost:8501 (uses CLI profile Brick).
    `app/app.yaml` takes the warehouse and Genie space from app resources (`sql-warehouse`, `genie-space`)
    for deployment.
- **Full extraction done (2026-10-22):** all 6,923 posts in 7 batches, 0 errors, about 47 min. That is
  6,805 job posts plus 118 non-job comments flagged by `is_job_post`, covering 2025-01 → 2026-10.
- **Deployed (2026-10-22):** Databricks App `hn-jobs` → https://hn-jobs-7474646996633052.aws.databricksapps.com
  - Resources: `sql-warehouse` (CAN_USE) and `genie-space` (CAN_RUN).
  - The app's service principal (`97d22809-0db5-4064-a90e-aa811def1343`) has USE CATALOG `hn_jobs`,
    USE SCHEMA + SELECT on `hn_jobs.gold`, and SELECT on `hn_jobs.silver.posts` (for the progress banner).
  - Source is uploaded to `/Workspace/Users/pavangangireddy53@gmail.com/hn_jobs_app`. The runtime installs
    Streamlit 1.66.1 from `requirements.txt`. pip warns that the preinstalled FastAPI wants an older
    starlette; that's harmless because the app doesn't use FastAPI.
  - Redeploy after changes:
    `databricks workspace import-dir app /Workspace/Users/pavangangireddy53@gmail.com/hn_jobs_app --overwrite`
    then `databricks apps deploy hn-jobs --source-code-path /Workspace/Users/pavangangireddy53@gmail.com/hn_jobs_app`.
  - Free Edition stops the app 24 h after each start or deploy. Restart it with `databricks apps start hn-jobs`.
  - All 6 pages checked on the deployed app in Chrome (2026-10-22). Two fixes came out of the check:
    - The map no longer scroll-zooms.
    - Salary medians by seniority now count each post once. `post_roles` has one row per role, so a post
      with 3 senior roles used to weigh 3×. The Salary page deduplicates (post, level). The Genie example
      was corrected, a seniority + country example was added, and a data-quality note was added. Genie now
      answers the senior US median as $187,200 (was $190,000), on 651 posts. The full 6,923 posts take roughly 4–5 h of serverless
    time if throughput doesn't improve with batch size, so run in batches of about 1,000.

## Free Edition limits that shape the design

| Limit | What it means for us |
|---|---|
| Outbound internet is restricted to a short list of trusted domains (verifying with LinkedIn lifts this) | HN APIs may be blocked from inside the workspace. **Step 0 checks this first.** Fallback: fetch on your PC and upload the files. |
| Serverless compute only, one 2X-Small SQL warehouse, at most 5 concurrent job tasks | Keep the data small and the jobs simple. That's fine at this size (≈10k posts, estimated). |
| Daily fair-use quota: if you go over it, compute shuts down for the rest of the day | Run the LLM extraction **incrementally in batches** (for example 500–1,000 posts per run) and never re-process a post. |
| Model serving: no GPU, no provisioned throughput, some models missing | Use the **Foundation Model APIs that come with the workspace** (pay-per-token) through `ai_query`. Choose the model from what the workspace's Serving page actually lists. |
| Databricks Apps: 1–3 per account (the docs disagree), auto-stop after 24 h | One app. Restart it when you need it. |
| One AI Search (vector) endpoint | Not needed. Questions go through text-to-SQL, not RAG. |

## Architecture (medallion layout in Unity Catalog `hn_jobs`)

```
HN Algolia API ──► bronze.raw_comments ──► silver.posts ──► gold.job_posts (+ exploded tables)
 (notebook, or local      (raw JSON)        (clean text)     (LLM-extracted fields)
  script + Volume upload)                                         │
                                       ┌──────────────────────────┤
                                       ▼                          ▼
                             Databricks App (Streamlit)    Genie space ("ask a question")
                             charts + Q&A tab ────────────► Genie Conversation API
```

## Phases

### 0. Workspace check (about 30 min)
- Create catalog `hn_jobs`, schemas `bronze`/`silver`/`gold`, and Volume `bronze.landing`.
- In a notebook, try `requests.get("https://hn.algolia.com/api/v1/items/1")`. If it fails, either use the
  local-upload path or verify with LinkedIn.
- List the available Foundation Model endpoints and run `ai_query` once on a sample post.

### 1. Ingestion → bronze
- Find the threads: Algolia `search_by_date?tags=story,author_whoishiring` and filter for titles starting
  with "Ask HN: Who is hiring?" and dated 2025-01-01 or later (about 22 threads so far).
- For each thread, `GET /api/v1/items/{id}` returns the whole comment tree. Keep **top-level comments only**,
  since those are the job posts and replies are not.
- Store `comment_id, thread_id, thread_month, author, created_at, html, fetched_at`. Do a MERGE on `comment_id`
  so re-runs are safe.
- If outbound access is blocked, run the same code as `ingest/fetch_hn.py` on your PC, write JSONL, and
  upload it with `databricks fs cp` to the Volume. Auto Loader then reads it into bronze.

### 2. Cleaning → silver
- Convert HTML to text and unescape entities. Drop deleted/dead posts and posts under 80 characters.
- The first line is usually `Company | Role | Location | REMOTE | $salary`. Keep it as `header_line`, because
  it helps the extraction prompt.

### 3. AI extraction → gold
- Use `ai_query(model, prompt, responseFormat => <JSON schema>)` in a SQL notebook. It only processes
  `comment_id`s not already in gold, with a `LIMIT` batch size per run.
- Schema per post:
  - `company`, `roles[]` (title, seniority: intern/junior/mid/senior/staff+/lead/manager/unspecified)
  - `skills[]` (normalized names), `remote_policy` (remote / hybrid / onsite / unspecified),
    `remote_regions[]`
  - `locations[]`, `visa_sponsorship` (yes/no/unspecified)
  - `salary_min`, `salary_max`, `currency`, `period` (year/month/hour), `equity` (bool)
- Post-processing in SQL/Python: a skill alias map (`react.js`→`React`, `golang`→`Go`, …), convert salary to
  annual USD using fixed FX rates, and flag outliers.
- **Quality check:** hand-label 50 posts and compare. Target ≥90% on remote policy and seniority, and ≥85% on
  salary range. Adjust the prompt before the full backfill.
- Exploded tables for charts: `gold.post_skills`, `gold.post_roles`, `gold.post_locations`.

### 4. Web app (Databricks App, Streamlit + Plotly)
- **Trends:** posts per month (a proxy for hiring demand), top skills and their month-over-month change,
  the remote/hybrid/onsite share over time, and the seniority mix.
- **Salary:** median and IQR by seniority, skill and remote policy (only posts that state a salary, with n shown).
- **Explore:** filter by month, skill, remote and seniority, plus a table of posts that link back to HN.
- **Ask:** a chat box. It sends the question to a **Genie space** built on the gold tables (with curated
  instructions and sample questions), then shows Genie's answer, the SQL it generated, and a chart.
  Fallback if the Genie API isn't available on Free Edition: our own text-to-SQL that uses `ai_query`
  with the table schema, read-only, and a row limit.
- Data access goes through `databricks-sql-connector` to the single SQL warehouse, with results cached for 1 h.

### 5. Automation
- A Lakeflow Job runs monthly (on the 2nd, and again on the 15th to catch late posts): ingest, clean,
  extract, refresh.
- During the backfill, run extraction daily in batches until it catches up, so we stay under the daily quota.

## Repo layout
```
ingest/fetch_hn.py          # Algolia fetcher (works locally or in a notebook)
notebooks/01_bronze.py  02_silver.py  03_extract.sql  04_gold_tables.sql
eval/labels.csv  eval/score.py
app/app.py  app/app.yaml  app/requirements.txt
databricks.yml              # Asset Bundle: jobs + app, deployed with `databricks bundle deploy`
```

## Risks
- **Quota stops during the backfill.** Mitigation: batch it and make it resumable.
- **Model availability on Free Edition varies.** The model name is a single config value.
- **Genie API access on Free Edition is unverified.** The text-to-SQL fallback is planned.
- **Salary text is messy** (ranges, k, €, hourly). It has a dedicated eval column, and nulls are allowed.

## Open decisions (I need your input)
1. Ingestion path if HN is blocked: local fetch + upload (no account change), or LinkedIn verification.
2. LLM: the default is the strongest chat model your workspace lists. Do you have a preference?
3. Q&A: Genie (recommended) or the custom text-to-SQL?
