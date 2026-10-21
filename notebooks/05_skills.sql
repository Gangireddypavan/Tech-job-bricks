-- Databricks notebook source
-- Skill-name normalization: one row per (job post, canonical skill) in the hn_jobs.gold.post_skills view.
--
-- The LLM's raw skill strings stay untouched in gold.job_posts.skills. Here each string gets a
-- match key (lowercase, only letters/digits/+/#: "Node.js", "NodeJS", "node js" -> "nodejs"),
-- the key is looked up in gold.skill_aliases, and keys with no alias fall back to their most
-- common spelling across all posts. Extend the alias list and re-run; no LLM calls needed.

CREATE OR REPLACE TABLE hn_jobs.gold.skill_aliases
COMMENT 'Match key -> canonical skill name (keys: lowercase, only [a-z0-9+#])'
AS SELECT * FROM VALUES
  ('nodejs', 'Node.js'), ('node', 'Node.js'),
  ('nextjs', 'Next.js'), ('next', 'Next.js'),
  ('react', 'React'), ('reactjs', 'React'),
  ('reactnative', 'React Native'),
  ('vue', 'Vue.js'), ('vuejs', 'Vue.js'), ('vue2', 'Vue.js'), ('vue3', 'Vue.js'),
  ('nuxt', 'Nuxt'), ('nuxtjs', 'Nuxt'),
  ('angular', 'Angular'), ('angularjs', 'AngularJS'),
  ('svelte', 'Svelte'), ('sveltekit', 'SvelteKit'),
  ('typescript', 'TypeScript'), ('ts', 'TypeScript'),
  ('javascript', 'JavaScript'), ('js', 'JavaScript'), ('es6', 'JavaScript'),
  ('python', 'Python'), ('python3', 'Python'),
  ('go', 'Go'), ('golang', 'Go'),
  ('rust', 'Rust'), ('java', 'Java'), ('kotlin', 'Kotlin'), ('scala', 'Scala'),
  ('ruby', 'Ruby'), ('rubyonrails', 'Ruby on Rails'), ('rails', 'Ruby on Rails'), ('ror', 'Ruby on Rails'),
  ('php', 'PHP'), ('laravel', 'Laravel'),
  ('django', 'Django'), ('flask', 'Flask'), ('fastapi', 'FastAPI'),
  ('spring', 'Spring'), ('springboot', 'Spring Boot'), ('springboot3', 'Spring Boot'),
  ('c#', 'C#'), ('csharp', 'C#'),
  ('net', '.NET'), ('dotnet', '.NET'), ('netcore', '.NET'), ('netframework', '.NET'), ('netframework48', '.NET'),
  ('aspnet', 'ASP.NET'), ('aspnetcore', 'ASP.NET'), ('aspnetmvc', 'ASP.NET'), ('aspnetwebforms', 'ASP.NET'),
  ('c++', 'C++'), ('cpp', 'C++'), ('c', 'C'),
  ('elixir', 'Elixir'), ('phoenix', 'Phoenix'), ('erlang', 'Erlang'), ('haskell', 'Haskell'), ('ocaml', 'OCaml'),
  ('swift', 'Swift'), ('swiftui', 'SwiftUI'), ('objectivec', 'Objective-C'),
  ('ios', 'iOS'), ('android', 'Android'), ('macos', 'macOS'),
  ('flutter', 'Flutter'), ('dart', 'Dart'),
  ('postgresql', 'PostgreSQL'), ('postgres', 'PostgreSQL'), ('psql', 'PostgreSQL'), ('postgressql', 'PostgreSQL'),
  ('mysql', 'MySQL'), ('sqlite', 'SQLite'), ('mongodb', 'MongoDB'), ('mongo', 'MongoDB'), ('redis', 'Redis'),
  ('sqlserver', 'SQL Server'), ('mssql', 'SQL Server'), ('microsoftsqlserver', 'SQL Server'), ('tsql', 'T-SQL'),
  ('sql', 'SQL'),
  ('elasticsearch', 'Elasticsearch'), ('elastic', 'Elasticsearch'), ('opensearch', 'OpenSearch'),
  ('clickhouse', 'ClickHouse'), ('snowflake', 'Snowflake'), ('bigquery', 'BigQuery'), ('databricks', 'Databricks'),
  ('spark', 'Spark'), ('apachespark', 'Spark'), ('pyspark', 'Spark'),
  ('kafka', 'Kafka'), ('apachekafka', 'Kafka'),
  ('dynamodb', 'DynamoDB'), ('cassandra', 'Cassandra'),
  ('aws', 'AWS'), ('amazonwebservices', 'AWS'),
  ('gcp', 'GCP'), ('googlecloud', 'GCP'), ('googlecloudplatform', 'GCP'),
  ('azure', 'Azure'), ('microsoftazure', 'Azure'),
  ('kubernetes', 'Kubernetes'), ('k8s', 'Kubernetes'), ('gke', 'GKE'), ('googlekubernetesengine', 'GKE'),
  ('eks', 'EKS'), ('amazoneks', 'EKS'), ('cloudbuild', 'Cloud Build'), ('googlecloudbuild', 'Cloud Build'),
  ('docker', 'Docker'), ('terraform', 'Terraform'), ('ansible', 'Ansible'), ('helm', 'Helm'),
  ('graphql', 'GraphQL'), ('grpc', 'gRPC'),
  ('tailwind', 'Tailwind CSS'), ('tailwindcss', 'Tailwind CSS'),
  ('pytorch', 'PyTorch'), ('torch', 'PyTorch'), ('tensorflow', 'TensorFlow'), ('jax', 'JAX'),
  ('linux', 'Linux'), ('git', 'Git'),
  ('html', 'HTML'), ('html5', 'HTML'), ('css', 'CSS'), ('css3', 'CSS'), ('scss', 'Sass'), ('sass', 'Sass'),
  ('nix', 'Nix'), ('bash', 'Bash'), ('shell', 'Bash'),
  ('webassembly', 'WebAssembly'), ('wasm', 'WebAssembly'),
  ('supabase', 'Supabase'), ('firebase', 'Firebase')
AS t(alias_key, canonical);

-- COMMAND ----------

-- A view, so it reflects each extraction batch as soon as it lands.
CREATE OR REPLACE VIEW hn_jobs.gold.post_skills
COMMENT 'One row per job post and canonical skill (normalized from gold.job_posts.skills)'
AS
WITH raw AS (
  SELECT j.comment_id, j.thread_month, trim(s) AS raw_skill,
         lower(regexp_replace(s, '[^A-Za-z0-9+#]', '')) AS skill_key
  FROM hn_jobs.gold.job_posts j
  LATERAL VIEW explode(j.skills) e AS s
  WHERE j.is_job_post AND j.error IS NULL
),
fallback AS (  -- most common spelling for keys with no alias
  SELECT skill_key, max_by(raw_skill, n) AS canonical
  FROM (SELECT skill_key, raw_skill, count(*) AS n FROM raw GROUP BY ALL)
  GROUP BY skill_key
)
SELECT r.comment_id, r.thread_month,
       coalesce(a.canonical, f.canonical) AS skill,
       collect_set(r.raw_skill) AS raw_skills,
       bool_or(a.canonical IS NOT NULL) AS via_alias
FROM raw r
LEFT JOIN hn_jobs.gold.skill_aliases a ON a.alias_key = r.skill_key
LEFT JOIN fallback f ON f.skill_key = r.skill_key
WHERE r.skill_key <> ''
GROUP BY r.comment_id, r.thread_month, coalesce(a.canonical, f.canonical);
