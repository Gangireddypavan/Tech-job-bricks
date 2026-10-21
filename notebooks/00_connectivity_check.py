# Databricks notebook source
# Phase 0: can serverless compute reach the HN APIs? Free Edition limits outbound
# traffic to a list of trusted domains, so we probe each endpoint we might use.
import json
import requests

PROBES = {
    "algolia_search": "https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=1",
    "algolia_item": "https://hn.algolia.com/api/v1/items/1",
    "firebase_item": "https://hacker-news.firebaseio.com/v0/item/1.json",
    "hn_site": "https://news.ycombinator.com/item?id=1",
}

results = {}
for name, url in PROBES.items():
    try:
        r = requests.get(url, timeout=15)
        results[name] = {"ok": r.ok, "status": r.status_code, "bytes": len(r.content)}
    except Exception as e:
        results[name] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}

print(json.dumps(results, indent=2))
dbutils.notebook.exit(json.dumps(results))
