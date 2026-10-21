"""Data access: one cached SQL warehouse connection, cached read-only queries, and the
sidebar filters (shared by every page except Ask) turned into a WHERE clause on gold.jobs."""

import os
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

import pandas as pd
import pycountry
import streamlit as st
from databricks import sql
from databricks.sdk.core import Config

GOLD = os.getenv("HN_GOLD_SCHEMA", "hn_jobs.gold")
SILVER = os.getenv("HN_SILVER_SCHEMA", "hn_jobs.silver")


@st.cache_resource(ttl=3600)
def _connection():
    cfg = Config()  # local: DATABRICKS_CONFIG_PROFILE; deployed: the app's service principal
    return sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}",
        credentials_provider=lambda: cfg.authenticate,
    )


@st.cache_data(ttl=600, show_spinner="Querying Databricks…")
def query(statement: str, params: tuple = ()) -> pd.DataFrame:
    """Run a read-only statement. params is a tuple of (name, value) pairs for :name markers."""
    for attempt in (1, 2):
        try:
            with _connection().cursor() as cur:
                cur.execute(statement, dict(params) if params else None)
                return cur.fetchall_arrow().to_pandas()
        except Exception:
            if attempt == 2:
                raise
            _connection.clear()  # stale connection (warehouse restarted, token expired): reconnect once


@dataclass(frozen=True)
class Filters:
    start: date
    end: date
    remote: tuple = ()
    seniority: tuple = ()
    countries: tuple = ()

    def where(self, alias="j"):
        """SQL predicate over gold.jobs (aliased `alias`) plus its parameters."""
        clauses = [f"{alias}.thread_month BETWEEN :start AND :end"]
        params = [("start", self.start), ("end", self.end)]

        def markers(prefix, values):
            names = [f"{prefix}{i}" for i in range(len(values))]
            params.extend(zip(names, values))
            return ", ".join(f":{n}" for n in names)

        if self.remote:
            clauses.append(f"{alias}.remote_policy IN ({markers('r', self.remote)})")
        if self.seniority:
            clauses.append(f"arrays_overlap({alias}.seniorities, array({markers('s', self.seniority)}))")
        if self.countries:
            clauses.append(f"arrays_overlap({alias}.countries, array({markers('c', self.countries)}))")
        return " AND ".join(clauses), tuple(params)

    @property
    def months(self):
        return f"{self.start:%b %Y} – {self.end:%b %Y}"


@lru_cache(maxsize=None)
def country_name(code):
    c = pycountry.countries.get(alpha_2=code)
    return getattr(c, "common_name", None) or (c.name if c else code)


@lru_cache(maxsize=None)
def country_alpha3(code):
    c = pycountry.countries.get(alpha_2=code)
    return c.alpha_3 if c else None


def extraction_progress():
    df = query(f"""
        SELECT (SELECT count(*) FROM {SILVER}.posts) AS total,
               (SELECT count(*) FROM {GOLD}.job_posts WHERE error IS NULL) AS done""")
    return int(df.total[0]), int(df.done[0])


def sidebar_filters():
    """Draw the sidebar filters and store the selection in session state."""
    months = query(f"SELECT DISTINCT thread_month FROM {GOLD}.jobs ORDER BY 1").thread_month.tolist()
    if not months:
        st.warning("No extracted job posts yet. Run the extraction (scripts/run_extraction.ps1) first.")
        st.stop()

    with st.sidebar:
        st.header("Filters")
        if len(months) > 1:
            start, end = st.select_slider("Months", options=months, value=(months[0], months[-1]),
                                          format_func=lambda d: f"{d:%b %Y}")
        else:
            start = end = months[0]
            st.caption(f"Months: {start:%b %Y}")
        remote = st.multiselect("Remote policy", ["remote", "hybrid", "onsite", "unspecified"])
        seniority = st.multiselect("Seniority", ["intern", "junior", "mid", "senior", "staff+",
                                                 "lead", "manager", "unspecified"])
        top = query(f"""SELECT country_code, count(*) AS n FROM {GOLD}.post_countries
                        GROUP BY 1 ORDER BY n DESC LIMIT 60""").country_code.tolist()
        countries = st.multiselect("Countries", top, format_func=lambda c: f"{country_name(c)} ({c})")

        total, done = extraction_progress()
        if done < total:
            st.info(f"AI extraction in progress: {done:,} of {total:,} posts processed. "
                    "Charts fill in as batches finish.")

    st.session_state["filters"] = Filters(start, end, tuple(remote), tuple(seniority), tuple(countries))


def current_filters() -> Filters:
    return st.session_state["filters"]
