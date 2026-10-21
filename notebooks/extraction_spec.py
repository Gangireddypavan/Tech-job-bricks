# Databricks notebook source
# Shared extraction spec: one set of instructions + output schema used by the eval
# (03_eval_run) and the production extraction (04_extract). Load with `%run ./extraction_spec`.

import json

# Bump when INSTRUCTIONS or the schema change; stored with every prediction/extraction.
PROMPT_VERSION = "v4"

INSTRUCTIONS = """\
You extract structured data from one Hacker News "Who is hiring?" job post. The post is written
by the hiring company. Read the whole post and follow these rules exactly.

is_job_post: true if a company (or its recruiter) is advertising roles it is hiring for. false for
  anything else: commentary about the thread or the market, people selling services or consulting,
  people looking for work. When false, leave the other fields empty/null/unspecified.
  A company describing itself and inviting candidates to reach out or apply IS a job post, even
  if it never says "hiring" or lists no role titles.

company: the hiring company's name only (no URL, no tagline).

roles: one entry per distinct role advertised. title = the role as written (shortened if long).
  seniority, from explicit wording in the title or requirements:
    intern     - internship, co-op
    junior     - junior, entry-level, new grad, associate, "0-2 years"
    mid        - mid-level, "Engineer II", "3-4 years"
    senior     - senior, Sr., "5+ years"
    staff+     - staff, principal, distinguished, fellow, architect
    lead       - lead, tech lead, team lead (individual-contributor lead roles)
    manager    - engineering manager, director, head of, VP, CTO
    unspecified - no level or years stated (a bare "Software Engineer" is unspecified)
  "Multiple roles"/"various" with no titles listed -> one entry, title "Multiple roles", unspecified.
  A title covering two levels ("Senior or Staff", "Senior/Staff") -> two entries, one per level.

skills: concrete technologies the post says the team uses or the role needs: programming languages,
  frameworks, libraries, databases, cloud platforms, infrastructure tools. Use canonical names
  (React not React.js, Go not Golang, PostgreSQL not Postgres, Kubernetes not k8s, AWS, GCP).
  Do NOT include job titles, domains or soft skills ("backend", "machine learning", "distributed
  systems", "leadership", "UI/UX"); algorithms, protocols or styles (Raft, Paxos, REST); fields
  or techniques (computer vision, SLAM, NLP, LLMs, AI, 3D); products the company merely integrates
  with or its customers run; technologies that appear only inside a URL. Empty list if none are named.

remote_policy: the most flexible arrangement the post offers.
  remote      - fully remote work is available (even if an office is also offered)
  hybrid      - some required days in an office, no fully remote option
  onsite      - in-office only
  unspecified - the post does not say
remote_regions: where remote employees may be based, as written short ("US", "EU", "Worldwide",
  "US time zones"). Empty list if not remote or not restricted.
locations: office cities/countries mentioned for the roles. Empty list if none.
countries: the countries the roles can be done from, as ISO 3166-1 alpha-2 codes (US, GB, DE, CA).
  Include every office country (from cities too: "NYC" -> US, "Berlin" -> DE) and every country
  named for remote work ("Remote (US)" -> US, "Remote: Argentina, Brazil" -> AR, BR). Regions
  ("EU", "LATAM", "Worldwide", "US time zones") are not countries: keep them in remote_regions
  only. Empty list if no country can be determined.

employment_types: any of full-time, part-time, contract, internship that the post states.

visa_sponsorship: yes / no if the post says so explicitly, otherwise unspecified.

salary: the pay range stated for the roles. If several roles list ranges, use the lowest minimum
  and the highest maximum. Write full numbers (120k -> 120000). A bare single figure sets both min
  and max; "up to X" sets only salary_max; a single "X+" sets only salary_min. A range keeps both
  ends even when the upper end carries a "+": "150-230k+" -> min 150000, max 230000.
  salary_currency is the ISO code. Use the symbol or code written in the post ("$" -> USD unless
  another dollar is clear, "£" -> GBP, "€" -> EUR). When the figures have NO currency symbol or code,
  use the currency of the office country, never default to USD: Berlin -> EUR, Paris -> EUR,
  London -> GBP, Toronto -> CAD, New York -> USD. salary_period
  is year, month or hour as stated (assume year for figures above 20000 with no period). Funding
  amounts, revenue and equity percentages are NOT salary. If no pay is stated, all salary fields null.

equity: true if equity, stock options or RSUs are offered, else false.
"""

SENIORITY = ["intern", "junior", "mid", "senior", "staff+", "lead", "manager", "unspecified"]
REMOTE = ["remote", "hybrid", "onsite", "unspecified"]
EMPLOYMENT = ["full-time", "part-time", "contract", "internship"]
VISA = ["yes", "no", "unspecified"]
PERIOD = ["year", "month", "hour"]

FIELDS = ["is_job_post", "company", "roles", "skills", "remote_policy", "remote_regions", "locations",
          "countries", "employment_types", "visa_sponsorship", "salary_min", "salary_max", "salary_currency",
          "salary_period", "equity"]

# JSON schema for ai_query(responseFormat => ...) structured output.
JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "job_post",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "is_job_post": {"type": "boolean"},
                "company": {"type": "string"},
                "roles": {"type": "array", "items": {
                    "type": "object",
                    "properties": {"title": {"type": "string"},
                                   "seniority": {"type": "string", "enum": SENIORITY}},
                    "required": ["title", "seniority"], "additionalProperties": False}},
                "skills": {"type": "array", "items": {"type": "string"}},
                "remote_policy": {"type": "string", "enum": REMOTE},
                "remote_regions": {"type": "array", "items": {"type": "string"}},
                "locations": {"type": "array", "items": {"type": "string"}},
                "countries": {"type": "array", "items": {"type": "string"}},
                "employment_types": {"type": "array", "items": {"type": "string", "enum": EMPLOYMENT}},
                "visa_sponsorship": {"type": "string", "enum": VISA},
                "salary_min": {"type": ["number", "null"]},
                "salary_max": {"type": ["number", "null"]},
                "salary_currency": {"type": ["string", "null"]},
                "salary_period": {"type": ["string", "null"], "enum": PERIOD + [None]},
                "equity": {"type": "boolean"},
            },
            "required": FIELDS,
            "additionalProperties": False,
        },
    },
}

# Same fields in ai_extract's schema dialect (no nullable unions; missing values come back null).
AI_EXTRACT_SCHEMA = {
    "is_job_post": {"type": "boolean"},
    "company": {"type": "string"},
    "roles": {"type": "array", "items": {"type": "object", "properties": {
        "title": {"type": "string"}, "seniority": {"type": "enum", "labels": SENIORITY}}}},
    "skills": {"type": "array", "items": {"type": "string"}},
    "remote_policy": {"type": "enum", "labels": REMOTE},
    "remote_regions": {"type": "array", "items": {"type": "string"}},
    "locations": {"type": "array", "items": {"type": "string"}},
    "countries": {"type": "array", "items": {"type": "string"}},
    "employment_types": {"type": "array", "items": {"type": "enum", "labels": EMPLOYMENT}},
    "visa_sponsorship": {"type": "enum", "labels": VISA},
    "salary_min": {"type": "number"},
    "salary_max": {"type": "number"},
    "salary_currency": {"type": "string"},
    "salary_period": {"type": "enum", "labels": PERIOD},
    "equity": {"type": "boolean"},
}

# Spark DDL used to parse model JSON into typed columns.
RESULT_DDL = (
    "is_job_post BOOLEAN, company STRING, roles ARRAY<STRUCT<title: STRING, seniority: STRING>>, skills ARRAY<STRING>, "
    "remote_policy STRING, remote_regions ARRAY<STRING>, locations ARRAY<STRING>, "
    "countries ARRAY<STRING>, employment_types ARRAY<STRING>, visa_sponsorship STRING, salary_min DOUBLE, salary_max DOUBLE, "
    "salary_currency STRING, salary_period STRING, equity BOOLEAN"
)


def sql_str(s):
    """Quote a Python string as a SQL string literal."""
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def ai_query_expr(model, text_col="text"):
    prompt = f"concat({sql_str(INSTRUCTIONS + chr(10) + 'POST:' + chr(10))}, {text_col})"
    return (f"ai_query({sql_str(model)}, {prompt}, "
            f"responseFormat => {sql_str(json.dumps(JSON_SCHEMA))}, "
            f"modelParameters => named_struct('temperature', CAST(0.0 AS DOUBLE)), "
            f"failOnError => false)")


def ai_extract_expr(text_col="text"):
    return (f"ai_extract({text_col}, {sql_str(json.dumps(AI_EXTRACT_SCHEMA))}, "
            f"map('version', '2.1', 'instructions', {sql_str(INSTRUCTIONS)}))")
