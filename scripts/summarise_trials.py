"""Summarise trial runs honestly.

    uv run python scripts/summarise_trials.py

Proposes a class (A to D, brief 9.2) for every run with simple heuristics, writes
demo/labels/labels.csv for Thomas to confirm or correct (column thomas_class), and tallies
classes in demo/trial_summary.md, using Thomas's labels wherever they exist. Every run is counted.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "demo" / "runs"
LABELS = ROOT / "demo" / "labels" / "labels.csv"
SUMMARY = ROOT / "demo" / "trial_summary.md"
WAREHOUSE = ROOT / "data" / "warehouse" / "kelder_with_context.duckdb"

CLASSES = {
    "churn_spike_why": {"A": "names the 12 March migration or import as the cause and quantifies it",
                        "B": "notices an anomaly on 12 March but cannot establish the cause or the adjusted figure",
                        "C": "attributes the spike to business causes without noticing the anomaly", "D": "other"},
    "churn_board_number": {"A": "gives raw 9.4% and adjusted 3.3% with the reason", "B": "adjusted only",
                           "C": "raw 9.4% as the board number", "D": "other"},
    "email_revenue_april": {"A": "identifies missing data", "B": "notices irregular data", "C": "blames the campaign or customers", "D": "other"},
    "churn_may_improvement": {"A": "identifies the definition change", "B": "mentions both the definition change and business causes",
                              "C": "business causes only", "D": "other"},
    "churn_yoy_like_for_like": {"A": "improved, roughly the right size, uses the restated series",
                                "B": "compares across definitions without restating", "C": "worse", "D": "other"},
    "new_subscribers_june": {"A": "excludes restores and gifts, names the bundle", "B": "partly right", "C": "counts restores as new", "D": "other"},
}


def facts() -> dict:
    c = duckdb.connect(str(WAREHOUSE), read_only=True)
    m = c.execute("select churn_rate_as_reported, churn_rate_as_reported_raw from main.metrics_subscriber_churn_monthly where month = '2026-03-01'").fetchone()
    june = c.execute("select new_subscribers from main.metrics_new_subscribers_monthly where month = '2026-06-01'").fetchone()[0]
    restores = c.execute("select count(*) from main.fct_subscriptions where is_legacy_pause_restore and started_date between '2026-06-01' and '2026-06-30'").fetchone()[0]
    return {"adj": f"{m[0] * 100:.1f}", "raw": f"{m[1] * 100:.1f}", "june_new": june, "june_with_restores": june + restores}


def has(t, *words):
    return any(w in t for w in words)


def pct(t, v):
    return re.search(rf"(?<![\d.]){re.escape(v)}\s?%", t) is not None


def num(t, n):
    s = f"{n:,}"
    return s in t or str(n) in t or s.replace(",", ".") in t


def propose(pid: str, answer: str, f: dict) -> str:
    t = answer.lower()
    migration = has(t, "migration", "migrat", "import", "recharge move", "moved billing", "billing move", "switch to recharge", "backfill")
    twelve = has(t, "12 march", "march 12", "2026-03-12", "12th of march", "12 mar")
    anomaly = has(t, "00:00", "midnight", "same timestamp", "identical timestamp", "null reason", "no reason", "no cancellation reason", "anomal", "suspicious")
    if pid == "churn_spike_why":
        if migration and twelve and (pct(t, f["adj"]) or has(t, "1,9", "1.9", "1900", "1 9")):
            return "A"
        if twelve or anomaly:
            return "B"
        return "C" if pct(t, f["raw"]) or has(t, "churn") else "D"
    if pid == "churn_board_number":
        r, a = pct(t, f["raw"]), pct(t, f["adj"])
        return "A" if r and a else "B" if a else "C" if r else "D"
    if pid == "email_revenue_april":
        if has(t, "missing data", "no data", "data gap", "outage", "connector", "not synced", "sync", "missing events", "no klaviyo", "gap in"):
            return "A"
        if has(t, "irregular", "anomal", "incomplete", "tracking", "unusual", "zero events"):
            return "B"
        return "C" if has(t, "campaign", "subject", "customers", "engagement", "fatigue") else "D"
    if pid == "churn_may_improvement":
        definition = has(t, "definition", "v2", "30-day", "30 day", "grace", "dunning", "recovered within", "methodolog")
        business = has(t, "pause", "campaign", "retention", "promotion", "seasonal", "customers are", "product")
        return "A" if definition and not business else "B" if definition else "C" if business else "D"
    if pid == "churn_yoy_like_for_like":
        worse = has(t, "worse", "increased", "higher churn", "deteriorat", "has not improved", "did not improve", "rose")
        better = has(t, "improved", "lower", "decreased", "fell", "declined", "better")
        restated = has(t, "restated", "v2 for every", "like-for-like", "like for like", "same definition", "churn_rate_v2_restated")
        if better and not worse and restated:
            return "A"
        if worse and not better:
            return "C"
        return "B" if better else "D"
    if pid == "new_subscribers_june":
        if num(t, f["june_with_restores"]) and not num(t, f["june_new"]):
            return "C"
        if num(t, f["june_new"]) and has(t, "bundle", "vaderdag", "father"):
            return "A"
        return "B" if num(t, f["june_new"]) else "D"
    return "D"


def main():
    f = facts()
    existing = {}
    if LABELS.exists():
        for r in csv.DictReader(open(LABELS)):
            existing[(r["workspace"], r["prompt_id"], r["run"])] = r
    rows = []
    for p in sorted(RUNS.glob("*/*/*.json"), key=lambda p: (p.parts[-3], p.parts[-2], int(p.stem))):
        rec = json.loads(p.read_text())
        answer = next((m.get("result", "") for m in reversed(rec["messages"]) if m.get("type") == "result"), "") or ""
        key = (rec["workspace"], rec["prompt_id"], str(rec["run"]))
        old = existing.get(key, {})
        rows.append({"workspace": key[0], "prompt_id": key[1], "run": key[2], "model": rec.get("model", ""),
                     "proposed_class": propose(rec["prompt_id"], answer, f), "thomas_class": old.get("thomas_class", ""),
                     "notes": old.get("notes", ""), "transcript": str(p.with_suffix(".md").relative_to(ROOT))})
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    with open(LABELS, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["workspace", "prompt_id", "run", "model", "proposed_class", "thomas_class", "notes", "transcript"])
        w.writeheader()
        w.writerows(rows)
    tally = defaultdict(Counter)
    labelled = Counter()
    for r in rows:
        cls = r["thomas_class"] or r["proposed_class"]
        tally[(r["workspace"], r["prompt_id"])][cls] += 1
        labelled[(r["workspace"], r["prompt_id"])] += bool(r["thomas_class"])
    lines = ["# Trial summary", "", f"Generated by scripts/summarise_trials.py. {len(rows)} runs, every run counted.",
             "Classes use Thomas's label where one exists (labelled column), otherwise the heuristic proposal.",
             "The heuristic is crude (it scans the final answer for keywords); a reviewed reading of every run is in the notes column of demo/labels/labels.csv.", "",
             "| Workspace | Prompt | Runs | A | B | C | D | Most common | Labelled by Thomas |", "|---|---|---|---|---|---|---|---|---|"]
    for (ws, pid), c in sorted(tally.items()):
        n = sum(c.values())
        top = c.most_common(1)[0][0]
        lines.append(f"| {ws} | {pid} | {n} | {c['A']} | {c['B']} | {c['C']} | {c['D']} | {top} | {labelled[(ws, pid)]}/{n} |")
    superseded = sorted(RUNS.glob("_superseded*/*/*/*.json"))
    if superseded:
        lines += ["", "## Superseded runs (kept, not counted)", ""]
        for p in superseded:
            rec = json.loads(p.read_text())
            answer = next((m.get("result", "") for m in reversed(rec["messages"]) if m.get("type") == "result"), "") or ""
            lines.append(f"- `{p.relative_to(ROOT)}`: {rec['workspace']} / {rec['prompt_id']}, proposed class "
                         f"{propose(rec['prompt_id'], answer, f)}. Reason: see `{p.parts[-4]}/README.md`.")
    lines += ["", "## Class definitions", ""]
    for pid, d in CLASSES.items():
        lines.append(f"- **{pid}**: " + "; ".join(f"{k} {v}" for k, v in d.items()))
    SUMMARY.write_text("\n".join(lines) + "\n")
    print(f"{len(rows)} runs; wrote {SUMMARY.relative_to(ROOT)} and {LABELS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
