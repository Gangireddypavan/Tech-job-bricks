-- Fastest-growing skills: share of posts mentioning each skill in the first six months
-- (Jan-Jun 2025) vs the last six months (May-Oct 2026). Shares, not counts, because the
-- number of posts per thread varies month to month.
--
-- Keyword match on the cleaned post text (silver.posts), so it works before the LLM
-- extraction finishes. Patterns are case-insensitive (?i) except for words that are also
-- ordinary English (Go, Rust, Java, Swift, Ruby, Temporal), which must be capitalised.
WITH skills (skill, pattern) AS (
  VALUES
    ('Python',       r'(?i)\bpython\b'),
    ('TypeScript',   r'(?i)\btypescript\b'),
    ('JavaScript',   r'(?i)\bjavascript\b'),
    ('React',        r'(?i)\breact(\.?js)?\b(?!\s*native)'),
    ('React Native', r'(?i)\breact\s*native\b'),
    ('Node.js',      r'(?i)\bnode\.?js\b|\bNode\b'),
    ('Next.js',      r'(?i)\bnext\.?js\b'),
    ('Vue.js',       r'(?i)\bvue(\.?js)?\b'),
    ('Angular',      r'(?i)\bangular\b'),
    ('Svelte',       r'(?i)\bsvelte'),
    ('Go',           r'(?i)\bgolang\b|\bGo\b(?=\s*[,/)])|[,/(]\s*Go\b'),
    ('Rust',         r'\bRust\b'),
    ('Java',         r'\bJava\b(?!Script)'),
    ('Kotlin',       r'(?i)\bkotlin\b'),
    ('Scala',        r'\bScala\b'),
    ('Ruby on Rails',r'(?i)\bruby on rails\b|\bRails\b|\bRoR\b'),
    ('PHP',          r'\bPHP\b'),
    ('Elixir',       r'(?i)\belixir\b'),
    ('C#',           r'C#'),
    ('C++',          r'C\+\+'),
    ('Swift',        r'\bSwift(UI)?\b'),
    ('Django',       r'(?i)\bdjango\b'),
    ('FastAPI',      r'(?i)\bfastapi\b'),
    ('PostgreSQL',   r'(?i)\bpostgres(ql)?\b'),
    ('MySQL',        r'(?i)\bmysql\b'),
    ('MongoDB',      r'(?i)\bmongo(db)?\b'),
    ('Redis',        r'(?i)\bredis\b'),
    ('ClickHouse',   r'(?i)\bclickhouse\b'),
    ('Kafka',        r'(?i)\bkafka\b'),
    ('Spark',        r'(?i)\b(apache spark|pyspark)\b|\bSpark\b(?! Capital)'),
    ('dbt',          r'\bdbt\b'),
    ('Airflow',      r'(?i)\bairflow\b'),
    ('AWS',          r'\bAWS\b'),
    ('GCP',          r'(?i)\bgcp\b|\bgoogle cloud\b'),
    ('Azure',        r'\bAzure\b'),
    ('Kubernetes',   r'(?i)\bkubernetes\b|\bk8s\b'),
    ('Docker',       r'(?i)\bdocker\b'),
    ('Terraform',    r'(?i)\bterraform\b'),
    ('GraphQL',      r'(?i)\bgraphql\b'),
    ('Tailwind CSS', r'(?i)\btailwind\b'),
    ('Flutter',      r'(?i)\bflutter\b'),
    ('PyTorch',      r'(?i)\bpytorch\b'),
    ('LangChain',    r'(?i)\blangchain\b|\blanggraph\b'),
    ('Supabase',     r'(?i)\bsupabase\b'),
    ('Temporal',     r'\bTemporal\b')
),
posts AS (
  SELECT comment_id, text,
         CASE WHEN thread_month BETWEEN '2025-01-01' AND '2025-06-01' THEN 'early'
              WHEN thread_month BETWEEN '2026-05-01' AND '2026-10-01' THEN 'recent' END AS period
  FROM hn_jobs.silver.posts
),
totals AS (
  SELECT count_if(period = 'early') AS early_total, count_if(period = 'recent') AS recent_total
  FROM posts
),
counts AS (
  SELECT s.skill,
         count_if(p.period = 'early')  AS early_posts,
         count_if(p.period = 'recent') AS recent_posts
  FROM skills s
  JOIN posts p ON p.period IS NOT NULL AND p.text RLIKE s.pattern
  GROUP BY s.skill
)
SELECT c.skill,
       c.early_posts,
       round(100 * c.early_posts / t.early_total, 1)   AS early_pct,
       c.recent_posts,
       round(100 * c.recent_posts / t.recent_total, 1) AS recent_pct,
       round(100 * (c.recent_posts / t.recent_total - c.early_posts / t.early_total), 1) AS change_pts,
       round((c.recent_posts / t.recent_total) / nullif(c.early_posts / t.early_total, 0), 2) AS growth_x
FROM counts c CROSS JOIN totals t
WHERE c.early_posts + c.recent_posts >= 20      -- skip skills too rare to trend
ORDER BY growth_x DESC NULLS FIRST, change_pts DESC;
