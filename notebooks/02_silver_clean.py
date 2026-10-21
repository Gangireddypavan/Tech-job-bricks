# Databricks notebook source
# Phase 2: turn raw HN comment HTML into clean job-post text in hn_jobs.silver.posts.
#
# HN comment HTML is a small dialect: the first paragraph has no tag, later ones start
# with <p>, links are <a href="...">, code is <pre><code>, plus <i> and HTML entities.
# Rebuilt in full on every run (it's ~8k rows); gold re-extracts a post only when its
# text_hash changes.

import html
import json
import re

from pyspark.sql import functions as F
from pyspark.sql import types as T

dbutils.widgets.text("catalog", "hn_jobs")
dbutils.widgets.text("min_chars", "80")
CATALOG = dbutils.widgets.get("catalog")
MIN_CHARS = int(dbutils.widgets.get("min_chars"))

LINK_RE = re.compile(r'<a\s[^>]*href="([^"]*)"[^>]*>.*?</a>', re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def clean(text_html):
    """Return (header_line, text, links) for one HN comment."""
    if not text_html:
        return None
    links = []

    def keep_href(m):
        url = html.unescape(m.group(1))
        links.append(url)
        return url  # HN truncates anchor text, the href is the full URL

    s = LINK_RE.sub(keep_href, text_html)
    s = re.sub(r"<p>", "\n\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = TAG_RE.sub("", s)
    s = html.unescape(s).replace(" ", " ")
    paragraphs = [re.sub(r"[ \t]+", " ", p).strip() for p in s.split("\n\n")]
    paragraphs = [p for p in paragraphs if p]
    if not paragraphs:
        return None
    # Raw newlines inside a paragraph render as spaces on HN, but authors use them to end
    # the "Company | Role | ..." header line, so the header is the first line, not paragraph.
    header = next(line.strip() for line in paragraphs[0].split("\n") if line.strip())
    return {"header_line": header, "text": "\n\n".join(paragraphs), "links": links}


clean_schema = T.StructType([
    T.StructField("header_line", T.StringType()),
    T.StructField("text", T.StringType()),
    T.StructField("links", T.ArrayType(T.StringType())),
])
clean_udf = F.udf(clean, clean_schema)

# COMMAND ----------

bronze = spark.table(f"{CATALOG}.bronze.raw_comments")
cleaned = (
    bronze
    .where(~F.col("is_deleted") & ~F.col("is_dead") & F.col("text_html").isNotNull())
    .withColumn("c", clean_udf("text_html"))
    .where(F.col("c").isNotNull() & (F.length("c.text") >= MIN_CHARS))
    .select(
        "comment_id", "thread_id", "thread_month", "author", "created_at",
        F.concat(F.lit("https://news.ycombinator.com/item?id="), F.col("comment_id")).alias("hn_url"),
        F.col("c.header_line").alias("header_line"),
        F.col("c.text").alias("text"),
        F.col("c.links").alias("links"),
        F.length("c.text").alias("text_chars"),
        F.sha2(F.col("c.text"), 256).alias("text_hash"),
    )
)
cleaned.createOrReplaceTempView("cleaned")

# Same author posting identical text twice in one thread: keep the earliest.
spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.silver.posts
COMMENT 'Clean text of live top-level job posts from Who is hiring threads (one row per post)'
AS
SELECT * EXCEPT (rn) FROM (
  SELECT *, row_number() OVER (PARTITION BY thread_id, author, text_hash ORDER BY created_at, comment_id) AS rn
  FROM cleaned
) WHERE rn = 1
""")

# COMMAND ----------

stats = spark.sql(f"""
SELECT
  (SELECT count(*) FROM {CATALOG}.bronze.raw_comments) AS bronze_rows,
  (SELECT count(*) FROM {CATALOG}.bronze.raw_comments WHERE NOT is_deleted AND NOT is_dead) AS bronze_live,
  count(*) AS silver_rows,
  count(DISTINCT comment_id) AS distinct_ids,
  count(DISTINCT thread_id) AS threads,
  sum(CASE WHEN text LIKE '%<%>%' THEN 1 ELSE 0 END) AS rows_with_tags_left,
  sum(CASE WHEN text RLIKE '&(#x?[0-9a-fA-F]+|[a-z]+);' THEN 1 ELSE 0 END) AS rows_with_entities_left,
  sum(CASE WHEN header_line LIKE '%|%' THEN 1 ELSE 0 END) AS pipe_headers,
  percentile_approx(text_chars, 0.5) AS median_chars
FROM {CATALOG}.silver.posts
""").collect()[0].asDict()
print(json.dumps(stats, indent=2, default=str))
dbutils.notebook.exit(json.dumps(stats, default=str))
