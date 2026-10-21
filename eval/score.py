"""Score extraction methods against hand labels.

Usage:
    python eval/score.py eval/labels.jsonl <predictions.json> [eval/results.md]

predictions.json is the JSON output of
    databricks experimental aitools tools query -o json \
      "SELECT method, comment_id, raw, error FROM hn_jobs.gold.eval_predictions"
"""

import json
import re
import sys
from collections import defaultdict

SKILL_ALIASES = {
    "postgres": "postgresql", "golang": "go", "k8s": "kubernetes", "ts": "typescript",
    "js": "javascript", "googlecloud": "gcp", "googlecloudplatform": "gcp",
    "amazonwebservices": "aws", "rails": "rubyonrails", "ror": "rubyonrails",
}
AMBIGUOUS_REMOTE = {44759963, 49523808, 49924972}


def unwrap(v):
    """ai_extract v2.1 wraps every scalar as {"value": ...}; strip that."""
    if isinstance(v, dict):
        if set(v) == {"value"}:
            return unwrap(v["value"])
        return {k: unwrap(x) for k, x in v.items()}
    if isinstance(v, list):
        return [unwrap(x) for x in v]
    return v


def norm_skill(s):
    s = re.sub(r"[^a-z0-9#+]", "", s.lower())
    if s.endswith("js") and len(s) > 4:
        s = s[:-2]
    return SKILL_ALIASES.get(s, s)


def norm_company(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def company_ok(label, pred):
    a, b = norm_company(label), norm_company(pred)
    return bool(a) and bool(b) and (a in b or b in a)


def close(a, b, tol=0.05):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol * max(abs(a), abs(b), 1)


def has_pay(lab):
    return lab["salary_min"] is not None or lab["salary_max"] is not None


def salary_ok(lab, pred):
    if not has_pay(lab):
        return pred.get("salary_min") is None and pred.get("salary_max") is None
    return (close(lab["salary_min"], pred.get("salary_min"))
            and close(lab["salary_max"], pred.get("salary_max"))
            and (pred.get("salary_currency") or "").upper() == lab["salary_currency"]
            and pred.get("salary_period") == lab["salary_period"])


def score(labels, preds):
    m = defaultdict(list)
    tp = fp = fn = 0
    misses = defaultdict(list)
    for cid, lab in labels.items():
        p = preds.get(cid)
        if p is None:
            m["parsed"].append(False)
            continue
        m["parsed"].append(True)
        m["is_job_post"].append(bool(p.get("is_job_post")) == lab["is_job_post"])
        if not lab["is_job_post"]:
            continue
        if lab["company"] is not None:
            ok = company_ok(lab["company"], p.get("company"))
            m["company"].append(ok)
            if not ok:
                misses["company"].append((cid, lab["company"], p.get("company")))
        ok = p.get("remote_policy") == lab["remote_policy"]
        m["remote_policy"].append(ok)
        if cid not in AMBIGUOUS_REMOTE:
            m["remote_policy (unambiguous)"].append(ok)
        if not ok:
            misses["remote_policy"].append((cid, lab["remote_policy"], p.get("remote_policy")))
        ls = set(lab["seniority"])
        ps = {r.get("seniority") for r in (p.get("roles") or [])} or {"unspecified"}
        m["seniority (exact set)"].append(ls == ps)
        m["seniority (jaccard)"].append(len(ls & ps) / len(ls | ps))
        if ls != ps:
            misses["seniority"].append((cid, sorted(ls), sorted(ps)))
        ok = salary_ok(lab, p)
        m["salary"].append(ok)
        if has_pay(lab):
            m["salary (posts with pay)"].append(ok)
        if not ok:
            misses["salary"].append((cid, (lab["salary_min"], lab["salary_max"], lab["salary_currency"], lab["salary_period"]),
                                     (p.get("salary_min"), p.get("salary_max"), p.get("salary_currency"), p.get("salary_period"))))
        m["visa_sponsorship"].append(p.get("visa_sponsorship") == lab["visa_sponsorship"])
        m["equity"].append(bool(p.get("equity")) == lab["equity"])
        m["employment_types"].append(set(p.get("employment_types") or []) == set(lab["employment_types"]))
        if "countries" in lab:  # added with prompt v3
            lc = set(lab["countries"])
            pc = {c.strip().upper() for c in (p.get("countries") or [])}
            m["countries (exact set)"].append(lc == pc)
            m["countries (jaccard)"].append(len(lc & pc) / len(lc | pc) if lc | pc else 1.0)
            if lc != pc:
                misses["countries"].append((cid, sorted(lc), sorted(pc)))
        lk = {norm_skill(s) for s in lab["skills"]}
        pk = {norm_skill(s) for s in (p.get("skills") or [])}
        tp += len(lk & pk); fp += len(pk - lk); fn += len(lk - pk)
        if pk - lk:
            misses["skills (extra)"].append((cid, sorted(pk - lk)))
        if lk - pk:
            misses["skills (missed)"].append((cid, sorted(lk - pk)))
    out = {k: sum(v) / len(v) for k, v in m.items()}
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    out["skills precision"], out["skills recall"] = prec, rec
    out["skills F1"] = 2 * prec * rec / (prec + rec) if prec + rec else 0
    return out, misses


def main():
    labels = {}
    for line in open(sys.argv[1], encoding="utf-8"):
        if line.strip():
            d = json.loads(line)
            labels[d["comment_id"]] = d
    rows = json.load(open(sys.argv[2], encoding="utf-8-sig"))
    by_method = defaultdict(dict)
    for r in rows:
        try:
            by_method[r["method"]][int(r["comment_id"])] = unwrap(json.loads(r["raw"]))
        except (TypeError, ValueError):
            pass

    results = {meth: score(labels, preds) for meth, preds in sorted(by_method.items())}
    methods = list(results)
    metrics = list(results[methods[0]][0])
    lines = ["| metric | " + " | ".join(methods) + " |", "|---|" + "---|" * len(methods)]
    for k in metrics:
        lines.append(f"| {k} | " + " | ".join(f"{results[x][0].get(k, 0):.0%}" for x in methods) + " |")
    table = "\n".join(lines)
    print(table)

    detail = []
    for meth in methods:
        detail.append(f"\n### {meth} misses")
        for field, items in results[meth][1].items():
            detail.append(f"- **{field}** ({len(items)}): " + "; ".join(str(i) for i in items))
    print("\n".join(detail))
    if len(sys.argv) > 3:
        with open(sys.argv[3], "w", encoding="utf-8") as f:
            f.write("# Extraction eval results\n\n50 posts from `hn_jobs.gold.eval_sample`, labels in "
                    "`eval/labels.jsonl` (48 job posts + 2 non-job comments).\n\n")
            f.write(table + "\n" + "\n".join(detail) + "\n")


if __name__ == "__main__":
    main()
