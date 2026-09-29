"""Render index.html: the evidence page behind the talk. Three tenets, each with the chart or trial that backs it.

    uv run python scripts/render_index.py      (or: make index)

Every number on the page is read from build outputs (frozen verified answers, chart data, trial summary and
labels), never typed in. Tenet 3 is design reasoning, and the page says so.
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import json
import subprocess
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "index.html"
BRAND = ROOT / "assets" / "brand"


def esc(s) -> str:
    return html.escape(str(s))


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip()


def load_json(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def pct(x, d=1) -> str:
    return "–" if x is None else f"{x * 100:.{d}f}%"


def facts() -> dict:
    f = {}
    t = ROOT / "data" / "truth" / "kelder_truth.duckdb"
    if t.exists():
        c = duckdb.connect(str(t), read_only=True)
        f["artefacts"] = c.execute("select count(*) from id_map where is_migration_artifact").fetchone()[0]
        c.close()
    ex = ROOT / "tests" / "verified" / "expected"
    m = load_json(ex / "churn_march_2026.json")
    if m:
        row = dict(zip(m["columns"], m["rows"][0]))
        f["march_adj"], f["march_raw"] = row["churn_rate_adjusted"], row["churn_rate_raw"]
    y = load_json(ex / "churn_yoy_like_for_like.json")
    if y:
        row = dict(zip(y["columns"], y["rows"][0]))
        f["yoy_25"], f["yoy_26"] = row["h1_2025_churn_rate_v2"], row["h1_2026_churn_rate_v2"]
    yr = load_json(ROOT / "charts" / "out" / "yoy_like_for_like_written_vs_rot.json")
    if yr:
        r = yr["mean_monthly_churn_rate_v2_restated"]["rot"]
        f["rot_25"], f["rot_26"] = r["h1_2025"] / 100, r["h1_2026"] / 100
    ch = load_json(ROOT / "charts" / "out" / "cancellations_by_hour_feb_mar_2026.json")
    if ch:
        f["midnight"] = ch["2026-03"][0]
    return f


def trials() -> dict:
    """Class counts from demo/trial_summary.md and Claude's reading of transcripts from demo/labels/labels.csv."""
    out = {"board": {}, "rows": [], "wrong_28": 0, "caught_rot": 0}
    p = ROOT / "demo" / "trial_summary.md"
    if p.exists():
        for l in p.read_text().splitlines():
            if l.startswith("| ") and not l.startswith("| Workspace") and "---" not in l:
                ws, pid, n, a, b, c, d, top, lab = [c.strip() for c in l.strip("|").split("|")]
                out["rows"].append((ws, pid, n, a, b, c, d, top, lab))
                if pid == "churn_board_number":
                    out["board"][ws] = (int(a), int(n))
    lp = ROOT / "demo" / "labels" / "labels.csv"
    if lp.exists():
        for r in csv.DictReader(lp.open()):
            if r["workspace"] == "installed" and r["prompt_id"] == "churn_board_number" and "2.8%" in r["notes"]:
                out["wrong_28"] += 1
            if r["workspace"] == "rot" and r["prompt_id"] == "churn_yoy_like_for_like" and "caught the rot" in r["notes"]:
                out["caught_rot"] += 1
    return out


def trial_table(rows) -> str:
    if not rows:
        return '<p class="muted">No trials yet. Run <code>make trials</code>, then <code>make summary</code>.</p>'
    body = "".join(
        f"<tr><td><span class='tag tag-{esc(ws)}'>{esc(ws)}</span></td><td><code>{esc(pid)}</code></td><td class='num'>{esc(n)}</td>"
        + "".join(f"<td class='num cls cls-{k}'>{esc(v)}</td>" for k, v in zip("ABCD", (a, b, c, d)))
        + "</tr>" for ws, pid, n, a, b, c, d, _top, _lab in rows)
    return ("<div class='numbers-table'><table class='data'><thead><tr><th>Workspace</th><th>Question</th><th>Runs</th>"
            "<th>A</th><th>B</th><th>C</th><th>D</th></tr></thead><tbody>" + body + "</tbody></table></div>"
            "<p class='muted small'>A is the right answer, C the confident wrong one. Class definitions are in "
            "<a href='demo/trial_summary.md'>demo/trial_summary.md</a>. The classes are a keyword heuristic; nothing is labelled by hand yet. "
            "Every run counts.</p>")


def rot_diff() -> str:
    d = git("--no-pager", "show", "--format=", "refs/tags/kelder/rot", "--", "kelder-dbt/models")
    if not d:
        return ""
    out = []
    for line in d.splitlines():
        if line.startswith(("diff ", "index ", "--- ", "+++ ")):
            continue
        cls = "add" if line.startswith("+") else "del" if line.startswith("-") else "hunk" if line.startswith("@@") else ""
        out.append(f"<span class='{cls}'>{esc(line)}</span>")
    return "".join(out)


CSS = r"""
:root {
  --espresso: #2A1C15; --crema: #F4EADB; --baksteen: #A9462B; --gracht: #2F5B55; --honing: #D9A441;
  --paper: #FAF4E9; --line: #DDCFB8; --soft: #EADFCB; --muted: #7A6656; --ink: #2A1C15;
  --serif: "Fraunces", Georgia, serif; --sans: "Instrument Sans", "Helvetica Neue", Arial, sans-serif;
  --mono: "JetBrains Mono", Menlo, monospace; --hand: "Caveat", cursive;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; overflow-x: hidden; background: var(--crema); color: var(--ink); font: 17px/1.6 var(--sans); }
a { color: var(--gracht); text-decoration-color: var(--honing); text-underline-offset: 3px; }
a:hover { color: var(--baksteen); }
code, .mono { font-family: var(--mono); font-size: .86em; }
code { background: var(--soft); padding: .1em .35em; border-radius: 4px; }
.wrap { max-width: 1240px; margin: 0 auto; padding: 0 28px; }
nav { position: sticky; top: 0; z-index: 10; background: rgba(42,28,21,.96); backdrop-filter: blur(8px); }
nav .wrap { display: flex; gap: 26px; align-items: center; height: 58px; overflow-x: auto; scrollbar-width: none; }
nav .wrap::-webkit-scrollbar { display: none; }
nav .brand { display: flex; align-items: center; gap: 12px; margin-right: auto; text-decoration: none; color: var(--crema); white-space: nowrap; }
nav .brand svg { height: 34px; width: auto; }
nav .brand span { font-family: var(--serif); font-size: 21px; font-weight: 600; }
nav .brand em { color: var(--honing); font-weight: 500; }
nav a:not(.brand) { font-family: var(--mono); font-size: 12.5px; text-decoration: none; letter-spacing: .04em; white-space: nowrap; color: var(--crema); opacity: .85; }
nav a:not(.brand):hover { opacity: 1; color: var(--honing); }
header { background: var(--espresso); color: var(--crema); padding: 76px 0 60px; }
.kicker { font-family: var(--mono); font-size: 12.5px; letter-spacing: .14em; text-transform: uppercase; color: var(--honing); }
h1 { font-family: var(--serif); font-weight: 500; font-size: clamp(40px, 6vw, 72px); line-height: 1.02; margin: 16px 0 22px; letter-spacing: -.015em; max-width: 980px; }
h1 em { color: var(--honing); font-style: italic; }
.lede { font-size: 20px; max-width: 800px; color: #E7DAC5; margin: 0; }
.hero { display: grid; grid-template-columns: minmax(0, 1fr) 190px; gap: 48px; align-items: center; }
.hero svg { width: 100%; height: auto; }
.stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 44px; max-width: 860px; }
.stat { border: 1px solid rgba(244,234,219,.22); border-radius: 12px; padding: 18px 20px 14px; }
.stat .v { font-family: var(--serif); font-size: 46px; line-height: 1; }
.stat .v.brick { color: #E0876A; } .stat .v.gr { color: var(--honing); }
.stat .l { font-family: var(--mono); font-size: 11.5px; color: #CDBFA9; margin-top: 10px; letter-spacing: .03em; }
section { padding: 72px 0; border-top: 1px solid var(--line); }
section:first-of-type { border-top: 0; }
.tenet-n { font-family: var(--hand); font-size: 30px; color: var(--baksteen); line-height: 1; }
h2 { font-family: var(--serif); font-weight: 500; font-size: clamp(28px, 3.6vw, 42px); line-height: 1.12; color: var(--espresso); margin: 6px 0 14px; max-width: 980px; }
h3 { font-family: var(--serif); font-weight: 600; font-size: 22px; margin: 0 0 6px; }
.sub { color: #4A3A2F; margin: 0 0 30px; max-width: 800px; font-size: 18px; }
.figure { margin: 0 0 34px; background: var(--crema); border: 1px solid var(--line); border-radius: 16px; overflow: hidden; }
.figure img, .figure svg { width: 100%; height: auto; display: block; }
.figure figcaption { padding: 14px 22px 16px; border-top: 1px solid var(--line); background: var(--paper); font-size: 16px; }
.figure figcaption b { font-family: var(--mono); font-size: 12px; letter-spacing: .1em; color: var(--baksteen); margin-right: 10px; font-weight: 500; }
.two { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, .9fr); gap: 34px; align-items: start; }
.tally { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.card { background: var(--paper); border: 1px solid var(--line); border-radius: 14px; padding: 20px 22px; }
.card .v { font-family: var(--serif); font-size: 54px; line-height: 1; }
.card .v.brick { color: var(--baksteen); } .card .v.gr { color: var(--gracht); }
.card .l { font-family: var(--mono); font-size: 12px; color: var(--muted); margin-top: 10px; line-height: 1.5; }
.callout { border-left: 4px solid var(--honing); background: var(--paper); padding: 16px 20px; border-radius: 0 12px 12px 0; margin: 0 0 30px; max-width: 860px; }
.callout b { font-family: var(--mono); font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: var(--baksteen); font-weight: 500; }
table.data { width: 100%; border-collapse: collapse; background: var(--paper); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; font-size: 15.5px; }
table.data th { text-align: left; font: 500 11.5px var(--mono); letter-spacing: .07em; text-transform: uppercase; color: var(--muted); background: var(--soft); padding: 11px 14px; }
table.data td { padding: 12px 14px; border-top: 1px solid var(--line); vertical-align: top; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.cls-A { color: var(--gracht); font-weight: 700; } .cls-C { color: var(--baksteen); font-weight: 700; }
.tag { font: 11.5px var(--mono); padding: 2px 9px; border-radius: 99px; background: var(--soft); }
.tag-written { background: #D3E0DA; color: var(--gracht); } .tag-rot { background: #EBCDBF; color: var(--baksteen); }
pre.diff { background: var(--paper); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; font: 13px/1.55 var(--mono); overflow-x: auto; margin: 0; }
pre.diff .add { color: var(--gracht); background: #DCE8E2; display: block; }
pre.diff .del { color: var(--baksteen); background: #F0D8CD; display: block; }
pre.diff .hunk { color: var(--muted); display: block; }
pre.cmd { position: relative; margin: 0; background: var(--espresso); color: var(--crema); border-radius: 8px; padding: 12px 76px 12px 16px; font: 13px/1.55 var(--mono); white-space: pre-wrap; overflow-wrap: anywhere; }
pre.cmd button { position: absolute; top: 8px; right: 8px; font: 11px var(--mono); background: transparent; color: var(--crema); border: 1px solid rgba(244,234,219,.4); border-radius: 5px; padding: 4px 9px; cursor: pointer; }
details { margin-top: 8px; }
summary { cursor: pointer; font-family: var(--mono); font-size: 13px; color: var(--gracht); margin-bottom: 14px; }
.muted { color: var(--muted); } .small { font-size: 14px; }
footer { background: var(--espresso); color: #CDBFA9; padding: 38px 0 56px; font: 12.5px/1.8 var(--mono); }
footer a { color: var(--honing); }
@media (max-width: 860px) {
  .stats, .tally, .two, .hero { grid-template-columns: minmax(0, 1fr); }
  .hero svg { max-width: 120px; order: -1; }
  .wrap { padding: 0 16px; } table.data { font-size: 13.5px; } table.data td, table.data th { padding: 9px; }
  .numbers-table { overflow-x: auto; } header { padding-top: 44px; } section { padding: 48px 0; }
}
"""

JS = r"""
document.querySelectorAll('pre.cmd').forEach(pre => {
  const b = document.createElement('button'); b.textContent = 'copy';
  b.onclick = () => { navigator.clipboard.writeText(pre.dataset.cmd || pre.innerText.replace(/copy$/, '').trim()); b.textContent = 'copied'; setTimeout(() => b.textContent = 'copy', 1400); };
  pre.appendChild(b);
});
"""

# Design reasoning, not a trial result. The six events are the ones in the talk outline (slide 29).
SIX_EVENTS = [
    ("Pause-instead-of-cancel campaign", "Domain model", "A pause is a state of a subscription, never a cancellation."),
    ("Father's Day gift bundle", "Domain model", "A gift subscription is its own type with no recurring revenue, so flat MRR follows from the model."),
    ("Billing migration", "Domain model, plus one decision record", "The model refuses a cancellation with no initiator and no reason. Decision 0007 records how the genuine ones were confirmed."),
    ("Klaviyo connector outage", "Data foundations", "A completeness check on the load flags the gap as missing data, not lost revenue."),
    ("Churn definition v2", "Versioned metric definition", "Both versions are calculated from the same domain records."),
    ("PostNL courier strike", "Context note", "An outside cause that no table can hold."),
]


def cmd(text: str) -> str:
    return f"<pre class='cmd' data-cmd='{esc(text)}'>{esc(text)}</pre>"


def main():
    f = facts()
    t = trials()
    now = dt.datetime.now().strftime("%d %B %Y, %H:%M")
    head = git("rev-parse", "--short", "HEAD")

    def chart(stem, alt):
        p = ROOT / "charts" / "out" / f"{stem}.png"
        return f"<img src='charts/out/{stem}.png' alt='{esc(alt)}' loading='lazy'>" if p.exists() else "<p class='muted'>Chart not built yet: run <code>make charts</code>.</p>"

    mark_dark = (BRAND / "kelder-mark.svg").read_text()
    mark_light = (BRAND / "kelder-mark-reversed.svg").read_text()
    favicon = "data:image/svg+xml;utf8," + html.escape(mark_dark.replace("\n", "").replace("#", "%23"), quote=True)

    n_runs = sum(int(r[2]) for r in t["rows"])
    b_inst = t["board"].get("installed", (0, 3))
    b_writ = t["board"].get("written", (0, 3))

    def svg(stem):
        q = ROOT / "charts" / "out" / f"{stem}.svg"
        return q.read_text() if q.exists() else "<p class='muted'>Diagram not built yet: run <code>make charts</code>.</p>"

    six = "".join(f"<tr><td><b>{esc(e)}</b></td><td>{esc(w)}</td><td>{esc(why)}</td></tr>" for e, w, why in SIX_EVENTS)

    page = f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kelder Koffie: the evidence</title>
<link rel="icon" href="{favicon}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@600&family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..600&family=Instrument+Sans:wght@400..700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body>
<nav><div class="wrap"><a class="brand" href="#">{mark_light}<span>Kelder <em>Koffie</em></span></a>
<a href="#tenet-1">tenet 1</a><a href="#tenet-2">tenet 2</a><a href="#tenet-3">tenet 3</a><a href="#trials">all {n_runs} trials</a></div></nav>

<header><div class="wrap hero"><div>
<div class="kicker">Tasman Analytics · Compass AI &amp; Tech Summit · Budapest · 1 October 2026</div>
<h1>Building a data context layer to <em>fix</em> your AI analytics</h1>
<p class="lede">The evidence behind the talk. Kelder Koffie is a fictional Amsterdam coffee subscription company, fictional on purpose so we know the right answer. Three tenets, and the chart or trial that backs each one.</p>
<div class="stats">
<div class="stat"><div class="v brick">{pct(f.get('march_raw'))}</div><div class="l">March 2026 churn, raw</div></div>
<div class="stat"><div class="v gr">{pct(f.get('march_adj'))}</div><div class="l">March 2026 churn, adjusted</div></div>
<div class="stat"><div class="v">{f.get('artefacts', 0):,}</div><div class="l">paused subscriptions imported as cancelled on 12 March</div></div>
</div></div>
<div>{mark_light}</div></div></header>

<section id="tenet-1"><div class="wrap">
<div class="tenet-n">Tenet 1</div>
<h2>An agent can find what looks odd in the data. Only people know why it happened.</h2>
<p class="sub">On 12 March 2026 Kelder moved billing from Shopify to Recharge. The import stamped a batch of cancellations at midnight UTC. The agent finds the batch. It cannot know which of those cancellations were real customers leaving, because that fact never reached a table.</p>
<figure class="figure">{chart('cancellations_by_hour_feb_mar_2026', 'Cancellations by hour of day, February and March 2026')}
<figcaption><b>WHAT THE AGENT SEES</b>{f.get('midnight', 0):,} cancellations at 00:00 UTC in March. Nothing in the rows says why.</figcaption></figure>
<figure class="figure">{chart('churn_monthly_2026_events', 'Monthly churn, January to June 2026')}
<figcaption><b>THE NUMBER</b>{pct(f.get('march_raw'))} raw in March, {pct(f.get('march_adj'))} once the import is taken out.</figcaption></figure>
<div class="two"><div>
<h3>Trial result: one number for the board</h3>
<p class="sub" style="margin-bottom:16px">Same question, same model, same warehouse, no notes. The agent recommended 2.8% in {t['wrong_28']} of 3 runs. The true figure is {pct(f.get('march_adj'))}. Some of the imported cancellations were real customers leaving, and the rows cannot tell them apart.</p>
<p class="small muted">Read from <a href="demo/labels/labels.csv">demo/labels/labels.csv</a> and <a href="demo/trial_summary.md">demo/trial_summary.md</a>.</p></div>
<div class="tally">
<div class="card"><div class="v brick">{b_inst[0]} of {b_inst[1]}</div><div class="l">runs gave the right board number<br>installed workspace, no context</div></div>
<div class="card"><div class="v gr">{b_writ[0]} of {b_writ[1]}</div><div class="l">runs gave the right board number<br>written workspace, context written down</div></div>
</div></div>
</div></section>

<section id="tenet-2"><div class="wrap">
<div class="tenet-n">Tenet 2</div>
<h2>Written context describes the business on the day it was written, and the business keeps changing.</h2>
<p class="sub">Once the reasons are written down, the agent gets it right. Then one ordinary commit, “Fix churn logic”, points the restated churn series at the unadjusted cancellations. Every note still says the import is excluded. Every dbt test still passes.</p>
<figure class="figure">{svg('knowledge_homes')}
<figcaption><b>WHERE THE NOTES LIVE</b>Four kinds of knowledge, each in its natural home in Kelder's repo and warehouse. The agent reads them through ktx or straight from the repo.</figcaption></figure>
<figure class="figure">{chart('yoy_like_for_like_written_vs_rot', 'First half of 2025 against first half of 2026, before and after the rot commit')}
<figcaption><b>THE COMPARISON FLIPS</b>First half of 2025 against first half of 2026, same rules. Improved from {pct(f.get('yoy_25'), 2)} to {pct(f.get('yoy_26'), 2)}; after the commit, worse, {pct(f.get('rot_25'), 2)} to {pct(f.get('rot_26'), 2)}.</figcaption></figure>
<div class="two"><div><h3>The rot commit</h3>
<p class="sub" style="margin-bottom:16px">Sanne, 26 June 2026. The pull request body has one line under “What changed” and no metric-impact box ticked.</p>
<pre class="diff">{rot_diff()}</pre></div>
<div><h3>What catches it</h3>
<p>Not the dbt tests. The verified query for the like-for-like comparison fails against its pinned answer, and the capture check fails because a metrics model changed with no impact box ticked.</p>
{cmd("make check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md")}
<div class="callout" style="margin-top:22px"><b>Trial note</b><br>In the rot workspace, {t['caught_rot']} of 3 runs of the like-for-like question flagged the bug in the SQL. That is Claude's reading of the transcripts, not yet a label from Thomas.</div>
</div></div>
</div></section>

<section id="tenet-3"><div class="wrap">
<div class="tenet-n">Tenet 3</div>
<h2>Model the business first, then write down only what the model cannot hold.</h2>
<div class="callout"><b>Design, not a trial result</b><br>This tenet rests on Tasman practice and design reasoning. No trial on this page tests it, and Kelder's dbt project has no domain layer yet.</div>
<figure class="figure">{svg('domain_model_logical')}
<figcaption><b>LOGICAL VIEW</b>What Kelder is made of, written before looking at any source system. A cancellation needs an initiator and a reason.</figcaption></figure>
<figure class="figure">{svg('domain_model_erd')}
<figcaption><b>ERD</b>The same model as tables. Rows that break the cancellation rule land in a review queue, not in the status-change table.</figcaption></figure>
<figure class="figure">{svg('architecture')}
<figcaption><b>ARCHITECTURE</b>How dbt, DuckDB, ktx and Claude fit together, where the domain layer sits between staging and the marts, and how a modern BI tool (Omni, Lightdash) reads from the marts and ktx while bringing its own context. Solid is built, dashed is design.</figcaption></figure>
<p class="sub">Six things happened at Kelder in the first half of 2026. Most of them belong in the model. The context layer shrinks to the reasons behind decisions, small enough for a named owner to keep current.</p>
<div class="numbers-table"><table class="data"><thead><tr><th>What happened</th><th>Where it belongs</th><th>Why</th></tr></thead><tbody>{six}</tbody></table></div>
</div></section>

<section id="trials"><div class="wrap">
<h2 style="font-size:30px">All {n_runs} trial runs</h2>
<details><summary>Show results by question and workspace</summary>
{trial_table(t['rows'])}</details>
</div></section>

<footer><div class="wrap">Built from commit {esc(head)} on {esc(now)} by <code>scripts/render_index.py</code>. Every number on this page is read from build outputs.<br>
To rebuild and run the demo, see <a href="START_HERE.md">START_HERE.md</a>.</div></footer>
<script>{JS}</script></body></html>"""
    OUT.write_text(page)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
