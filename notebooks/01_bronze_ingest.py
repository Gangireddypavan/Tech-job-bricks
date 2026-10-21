# Databricks notebook source
# Phase 1: fetch every top-level comment from the monthly "Ask HN: Who is hiring?"
# threads since START_DATE and MERGE them into hn_jobs.bronze.raw_comments.
#
# Sources:
#   - Algolia HN API: thread discovery + the full comment tree in one call per thread.
#   - Official HN Firebase API: the authoritative list of top-level comment ids (`kids`)
#     and per-item fetches for anything Algolia's tree is missing.
# Re-running is safe: rows are keyed on comment_id and updated in place.

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
from pyspark.sql import types as T

dbutils.widgets.text("start_date", "2025-01-01")
dbutils.widgets.text("catalog", "hn_jobs")
START_DATE = dbutils.widgets.get("start_date")
CATALOG = dbutils.widgets.get("catalog")

ALGOLIA = "https://hn.algolia.com/api/v1"
FIREBASE = "https://hacker-news.firebaseio.com/v0"
TITLE_RE = re.compile(r"^Ask HN: Who is hiring\? \((\w+) (\d{4})\)", re.IGNORECASE)

session = requests.Session()
session.headers["User-Agent"] = "hn-jobs-tracker (Databricks Free Edition)"


def get_json(url, params=None, retries=4):
    for attempt in range(retries):
        try:
            r = session.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == retries - 1:
                raise


def ts(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc) if epoch else None

# COMMAND ----------

# Find the threads. All of them are posted by the `whoishiring` account; the same
# account also posts "Who wants to be hired?" and "Freelancer?" threads, so filter on title.
start_epoch = int(datetime.fromisoformat(START_DATE).replace(tzinfo=timezone.utc).timestamp())
hits, page = [], 0
while True:
    resp = get_json(
        f"{ALGOLIA}/search_by_date",
        {
            "tags": "story,author_whoishiring",
            "numericFilters": f"created_at_i>={start_epoch}",
            "hitsPerPage": 100,
            "page": page,
        },
    )
    hits += resp["hits"]
    page += 1
    if page >= resp["nbPages"]:
        break

threads = []
for h in hits:
    m = TITLE_RE.match(h["title"] or "")
    if not m:
        continue
    month = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%B %Y").date()
    threads.append({"thread_id": int(h["objectID"]), "title": h["title"], "thread_month": month,
                    "created_at": ts(h["created_at_i"])})
threads.sort(key=lambda t: t["thread_month"])
print(f"{len(threads)} threads: {threads[0]['thread_month']} .. {threads[-1]['thread_month']}")

# COMMAND ----------

def fetch_thread(thread):
    tid = thread["thread_id"]
    tree = get_json(f"{ALGOLIA}/items/{tid}")
    by_id = {c["id"]: c for c in tree.get("children", [])}
    kids = (get_json(f"{FIREBASE}/item/{tid}.json") or {}).get("kids", [])

    rows = []
    for c in by_id.values():
        rows.append({
            "comment_id": c["id"], "author": c.get("author"), "created_at": ts(c.get("created_at_i")),
            "text_html": c.get("text"), "is_deleted": c.get("author") is None and c.get("text") is None,
            "is_dead": False, "source": "algolia",
        })

    # Fill gaps from Firebase: ids HN lists as top-level kids that Algolia didn't return.
    missing = [k for k in kids if k not in by_id]
    with ThreadPoolExecutor(max_workers=16) as pool:
        for item in pool.map(lambda k: get_json(f"{FIREBASE}/item/{k}.json"), missing):
            if not item:
                continue
            rows.append({
                "comment_id": item["id"], "author": item.get("by"), "created_at": ts(item.get("time")),
                "text_html": item.get("text"), "is_deleted": bool(item.get("deleted")),
                "is_dead": bool(item.get("dead")), "source": "firebase",
            })

    for r in rows:
        r.update(thread_id=tid, thread_month=thread["thread_month"])
    thread.update(top_level_count=len(rows), algolia_count=len(by_id), firebase_kids=len(kids),
                  filled_from_firebase=len(missing))
    return rows


all_rows = []
for t in threads:
    all_rows += fetch_thread(t)
    print(f"{t['thread_month']}: {t['top_level_count']:>4} posts "
          f"(algolia {t['algolia_count']}, hn kids {t['firebase_kids']}, filled {t['filled_from_firebase']})")
print(f"total top-level comments: {len(all_rows)}")

# COMMAND ----------

fetched_at = datetime.now(timezone.utc)

thread_schema = T.StructType([
    T.StructField("thread_id", T.LongType(), False),
    T.StructField("title", T.StringType()),
    T.StructField("thread_month", T.DateType()),
    T.StructField("created_at", T.TimestampType()),
    T.StructField("top_level_count", T.IntegerType()),
    T.StructField("algolia_count", T.IntegerType()),
    T.StructField("firebase_kids", T.IntegerType()),
    T.StructField("filled_from_firebase", T.IntegerType()),
    T.StructField("fetched_at", T.TimestampType()),
])
comment_schema = T.StructType([
    T.StructField("comment_id", T.LongType(), False),
    T.StructField("thread_id", T.LongType(), False),
    T.StructField("thread_month", T.DateType()),
    T.StructField("author", T.StringType()),
    T.StructField("created_at", T.TimestampType()),
    T.StructField("text_html", T.StringType()),
    T.StructField("is_deleted", T.BooleanType()),
    T.StructField("is_dead", T.BooleanType()),
    T.StructField("source", T.StringType()),
    T.StructField("fetched_at", T.TimestampType()),
])

spark.createDataFrame([{**t, "fetched_at": fetched_at} for t in threads], thread_schema) \
    .createOrReplaceTempView("new_threads")
spark.createDataFrame([{**r, "fetched_at": fetched_at} for r in all_rows], comment_schema) \
    .createOrReplaceTempView("new_comments")

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.bronze.threads (
  thread_id BIGINT NOT NULL, title STRING, thread_month DATE, created_at TIMESTAMP,
  top_level_count INT, algolia_count INT, firebase_kids INT, filled_from_firebase INT,
  fetched_at TIMESTAMP
) COMMENT 'Monthly "Ask HN: Who is hiring?" threads'
""")
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.bronze.raw_comments (
  comment_id BIGINT NOT NULL, thread_id BIGINT NOT NULL, thread_month DATE, author STRING,
  created_at TIMESTAMP, text_html STRING, is_deleted BOOLEAN, is_dead BOOLEAN, source STRING,
  fetched_at TIMESTAMP
) COMMENT 'Top-level comments (job posts) from Who is hiring threads, raw HTML'
""")

spark.sql(f"""
MERGE INTO {CATALOG}.bronze.threads t USING new_threads s ON t.thread_id = s.thread_id
WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *
""")
merge = spark.sql(f"""
MERGE INTO {CATALOG}.bronze.raw_comments t USING new_comments s ON t.comment_id = s.comment_id
WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *
""").collect()[0].asDict()

# COMMAND ----------

summary = {
    "threads": len(threads),
    "first_month": str(threads[0]["thread_month"]),
    "last_month": str(threads[-1]["thread_month"]),
    "comments_fetched": len(all_rows),
    "filled_from_firebase": sum(t["filled_from_firebase"] for t in threads),
    "merge": {k: int(v) for k, v in merge.items()},
    "table_rows": spark.table(f"{CATALOG}.bronze.raw_comments").count(),
}
print(json.dumps(summary, indent=2))
dbutils.notebook.exit(json.dumps(summary))
