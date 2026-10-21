"""Build the Genie space definition for the HN jobs tracker.

Usage:
    python genie/build_space.py create <warehouse_id> <parent_path> > genie/create.json
    python genie/build_space.py update                                > genie/update.json
then
    databricks genie create-space --json @genie/create.json
    databricks genie update-space <space_id> --json @genie/update.json

IDs are derived from content hashes so rebuilding gives stable, sorted IDs.
"""

import hashlib
import json
import sys

CAT = "hn_jobs.gold"
TITLE = "HN Tech Job Market"
DESCRIPTION = (
    "Ask questions about the tech job market from Hacker News 'Who is hiring?' threads since "
    "January 2025: skills in demand, salaries, seniority, remote policy and countries."
)


def hid(*parts):
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def col(name, description=None, synonyms=None, match=False, exclude=False):
    c = {"column_name": name}
    if description:
        c["description"] = [description]
    if synonyms:
        c["synonyms"] = synonyms
    if match:
        c["enable_format_assistance"] = True
        c["enable_entity_matching"] = True
    if exclude:
        c["exclude"] = True
    return c


TABLES = {
    f"{CAT}.jobs": [
        col("comment_id", "HN comment id. One row per job post; the key other tables join on."),
        col("thread_month", "First day of the month of the 'Who is hiring?' thread the post was in.",
            ["month", "date", "period"]),
        col("hn_url", "Link to the post on Hacker News."),
        col("company", "Hiring company name.", ["employer", "firm"], match=True),
        col("roles", "Roles advertised (title + seniority). Use post_roles to count by seniority."),
        col("seniorities", "Distinct seniority levels across the post's roles."),
        col("skills", "Skills as extracted, not normalized. Use post_skills to count skills."),
        col("remote_policy", "remote (fully remote possible), hybrid, onsite, or unspecified.",
            ["remote", "work from home", "WFH", "in office", "location policy"], match=True),
        col("remote_regions", "Where remote employees may be based, e.g. US, EU, Worldwide."),
        col("locations", "Office cities/countries as written in the post."),
        col("countries", "ISO alpha-2 codes of countries the roles can be done from. Use post_countries to count."),
        col("employment_types", "full-time, part-time, contract, internship."),
        col("visa_sponsorship", "yes / no / unspecified.", ["visa", "sponsorship"], match=True),
        col("equity", "True if equity or stock options are offered.", ["stock options", "RSUs"]),
        col("salary_min", "Lower bound of the stated pay, in salary_currency per salary_period."),
        col("salary_max", "Upper bound of the stated pay, in salary_currency per salary_period."),
        col("salary_currency", "ISO currency code of the stated pay.", match=True),
        col("salary_period", "year, month or hour."),
        col("salary_min_usd", "salary_min converted to annual USD at fixed reference rates."),
        col("salary_max_usd", "salary_max converted to annual USD at fixed reference rates."),
        col("salary_mid_usd", "Midpoint of the stated pay range in annual USD. Use this for salary comparisons.",
            ["salary", "pay", "compensation", "comp", "wage"]),
    ],
    f"{CAT}.post_skills": [
        col("comment_id", "Job post id (jobs.comment_id)."),
        col("thread_month", "Month of the thread the post was in.", ["month"]),
        col("skill", "Canonical skill name: a language, framework, database, cloud or tool.",
            ["technology", "tech", "tech stack", "language", "framework", "tool"], match=True),
        col("raw_skills", exclude=True),
        col("via_alias", exclude=True),
    ],
    f"{CAT}.post_roles": [
        col("comment_id", "Job post id (jobs.comment_id)."),
        col("thread_month", "Month of the thread the post was in.", ["month"]),
        col("title", "Role title as written in the post.", ["job title", "position"]),
        col("seniority", "intern, junior, mid, senior, staff+, lead, manager or unspecified.",
            ["level", "experience level"], match=True),
    ],
    f"{CAT}.post_countries": [
        col("comment_id", "Job post id (jobs.comment_id)."),
        col("thread_month", "Month of the thread the post was in.", ["month"]),
        col("country_code", "ISO 3166-1 alpha-2 country code, e.g. US, GB, DE, CA.",
            ["country", "location", "nation"], match=True),
    ],
}

JOINS = [
    ("jobs", "post_skills"), ("jobs", "post_roles"), ("jobs", "post_countries"),
]

LAST6 = "add_months((SELECT MAX(jobs.thread_month) FROM hn_jobs.gold.jobs), -5)"
EXAMPLES = [
    ("What are the top 10 skills in the last 6 months?",
     f"SELECT post_skills.skill, COUNT(DISTINCT post_skills.comment_id) AS posts, "
     f"ROUND(100.0 * COUNT(DISTINCT post_skills.comment_id) / (SELECT COUNT(*) FROM hn_jobs.gold.jobs "
     f"WHERE jobs.thread_month >= {LAST6}), 1) AS pct_of_posts "
     f"FROM hn_jobs.gold.post_skills WHERE post_skills.thread_month >= {LAST6} "
     f"GROUP BY post_skills.skill ORDER BY posts DESC LIMIT 10"),
    ("How has the share of remote jobs changed month by month?",
     "SELECT jobs.thread_month, COUNT(*) AS posts, "
     "ROUND(100.0 * AVG(CASE WHEN jobs.remote_policy = 'remote' THEN 1 ELSE 0 END), 1) AS pct_remote, "
     "ROUND(100.0 * AVG(CASE WHEN jobs.remote_policy = 'hybrid' THEN 1 ELSE 0 END), 1) AS pct_hybrid, "
     "ROUND(100.0 * AVG(CASE WHEN jobs.remote_policy = 'onsite' THEN 1 ELSE 0 END), 1) AS pct_onsite "
     "FROM hn_jobs.gold.jobs GROUP BY jobs.thread_month ORDER BY jobs.thread_month"),
    # Deduplicate (post, seniority) first: post_roles has one row per role, so a post with
    # three senior roles would otherwise count three times in the median.
    ("What is the median salary by seniority?",
     "SELECT post_roles.seniority, COUNT(*) AS posts_with_salary, "
     "PERCENTILE_APPROX(jobs.salary_mid_usd, 0.5) AS median_salary_usd "
     "FROM (SELECT DISTINCT post_roles.comment_id, post_roles.seniority FROM hn_jobs.gold.post_roles) post_roles "
     "JOIN hn_jobs.gold.jobs ON post_roles.comment_id = jobs.comment_id "
     "WHERE jobs.salary_mid_usd IS NOT NULL GROUP BY post_roles.seniority ORDER BY median_salary_usd DESC"),
    # Filtering on a level and a country: use the arrays on jobs, so each post is one row.
    ("What is the median salary for staff+ roles in Canada?",
     "SELECT COUNT(*) AS posts_with_salary, PERCENTILE_APPROX(jobs.salary_mid_usd, 0.5) AS median_salary_usd "
     "FROM hn_jobs.gold.jobs WHERE jobs.salary_mid_usd IS NOT NULL "
     "AND array_contains(jobs.seniorities, 'staff+') AND array_contains(jobs.countries, 'CA')"),
    ("Which countries have the most job posts?",
     "SELECT post_countries.country_code, COUNT(DISTINCT post_countries.comment_id) AS posts "
     "FROM hn_jobs.gold.post_countries GROUP BY post_countries.country_code ORDER BY posts DESC LIMIT 15"),
    ("How has demand for Python changed over time?",
     "SELECT jobs.thread_month, COUNT(DISTINCT jobs.comment_id) AS posts, "
     "ROUND(100.0 * COUNT(DISTINCT post_skills.comment_id) / COUNT(DISTINCT jobs.comment_id), 1) AS pct_posts_mentioning "
     "FROM hn_jobs.gold.jobs LEFT JOIN hn_jobs.gold.post_skills "
     "ON post_skills.comment_id = jobs.comment_id AND post_skills.skill = 'Python' "
     "GROUP BY jobs.thread_month ORDER BY jobs.thread_month"),
]

SAMPLE_QUESTIONS = [
    "What are the fastest-growing skills this year?",
    "What share of jobs are fully remote?",
    "What is the median salary for senior engineers in the US?",
    "Which companies post the most often?",
    "How many jobs mention Rust each month?",
]

TEXT_INSTRUCTIONS = [
    "## PURPOSE",
    "- Answer questions about the tech job market from Hacker News 'Ask HN: Who is hiring?' threads, "
    "January 2025 onward. One row in jobs is one company's post in one monthly thread.",
    "",
    "## DISAMBIGUATION",
    "- 'Last N months' means the N most recent thread_month values in jobs, not calendar time from today.",
    "- For trends over time, report the share of that month's posts, because the number of posts per "
    "thread varies a lot month to month.",
    "",
    "## DATA QUALITY NOTES",
    "- Pay is only present for posts that state it. Compare salaries with salary_mid_usd (annual USD at "
    "fixed reference rates), not salary_min/salary_max, which are in the original currency and period.",
    "- A post can advertise several roles with one pay range, so salary by seniority is approximate.",
    "- Salary medians must count each post once: filter on jobs.seniorities / jobs.countries instead of "
    "joining post_roles or post_countries, or deduplicate the joined rows first.",
    "- All fields were extracted from free text by an LLM and can contain small errors.",
    "",
    "## Instructions you must follow when providing summaries",
    "- State the months covered and how many posts each figure is based on.",
    "- Round percentages to one decimal place.",
]


def serialized_space():
    tables = [
        {"identifier": ident, "column_configs": sorted(cfgs, key=lambda c: c["column_name"])}
        for ident, cfgs in sorted(TABLES.items())
    ]
    joins = sorted([
        {"id": hid("join", left, right),
         "left": {"identifier": f"{CAT}.{left}", "alias": left},
         "right": {"identifier": f"{CAT}.{right}", "alias": right},
         "sql": [f"`{left}`.`comment_id` = `{right}`.`comment_id`", "--rt=FROM_RELATIONSHIP_TYPE_ONE_TO_MANY--"]}
        for left, right in JOINS
    ], key=lambda j: j["id"])
    examples = sorted([
        {"id": hid("example", q), "question": [q], "sql": [s]} for q, s in EXAMPLES
    ], key=lambda e: e["id"])
    samples = sorted([
        {"id": hid("sample", q), "question": [q]} for q in SAMPLE_QUESTIONS
    ], key=lambda s: s["id"])
    return {
        "version": 2,
        "config": {"sample_questions": samples},
        "data_sources": {"tables": tables},
        "instructions": {
            "text_instructions": [{"id": hid("text"), "content": [l + "\n" for l in TEXT_INSTRUCTIONS]}],
            "example_question_sqls": examples,
            "join_specs": joins,
        },
    }


def main():
    space = json.dumps(serialized_space())
    if sys.argv[1] == "create":
        payload = {"warehouse_id": sys.argv[2], "parent_path": sys.argv[3], "title": TITLE,
                   "description": DESCRIPTION, "serialized_space": space}
    elif sys.argv[1] == "update":
        payload = {"title": TITLE, "description": DESCRIPTION, "serialized_space": space}
    elif sys.argv[1] == "examples":  # emit example SQL, one per line, for validation
        for _, s in EXAMPLES:
            print(s)
        return
    else:
        raise SystemExit(__doc__)
    print(json.dumps(payload, indent=1))


if __name__ == "__main__":
    main()
