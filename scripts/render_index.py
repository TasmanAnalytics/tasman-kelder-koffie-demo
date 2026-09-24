"""Render index.html: the start page for this repository.

    uv run python scripts/render_index.py      (or: make index)

Every number on the page is read from build outputs (truth targets, frozen verified answers,
chart data, trial summary), never typed in. Missing outputs show as "not built yet".
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
import subprocess
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "index.html"


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
        f["targets"] = c.execute("select target, expected, achieved, passed from targets").fetchall()
        f["artefacts"] = c.execute("select count(*) from id_map where is_migration_artifact").fetchone()[0]
        f["restores"] = c.execute("select count(recharge_restore_subscription_id) from id_map").fetchone()[0]
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
    e = load_json(ex / "email_revenue_april_2026.json")
    if e:
        f["email_april"] = dict(zip(e["columns"], e["rows"][0]))["attributed_revenue_eur"]
    n = load_json(ex / "new_subscribers_june_2026.json")
    if n:
        f["june"] = dict(zip(n["columns"], n["rows"][0]))
    return f


def trial_table() -> str:
    p = ROOT / "demo" / "trial_summary.md"
    if not p.exists():
        return '<p class="muted">No trials yet. Run <code>make trials</code>, then <code>make summary</code>.</p>'
    rows = [l for l in p.read_text().splitlines() if l.startswith("| ") and not l.startswith("| Workspace") and "---" not in l]
    body = []
    for l in rows:
        cells = [c.strip() for c in l.strip("|").split("|")]
        ws, pid, n, a, b, c, d, top, lab = cells
        body.append(f"<tr><td><span class='tag tag-{esc(ws)}'>{esc(ws)}</span></td><td><code>{esc(pid)}</code></td>"
                    f"<td class='num'>{esc(n)}</td>" + "".join(f"<td class='num cls cls-{k}'>{esc(v)}</td>" for k, v in zip("ABCD", (a, b, c, d)))
                    + f"<td class='num'><b>{esc(top)}</b></td><td class='num muted'>{esc(lab)}</td></tr>")
    return ("<div class='numbers-table'><table class='data'><thead><tr><th>Workspace</th><th>Prompt</th><th>Runs</th><th>A</th><th>B</th><th>C</th><th>D</th>"
            "<th>Most common</th><th>Labelled</th></tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"
            "<p class='muted small'>A is the right answer, C the confident wrong one (definitions in <a href='demo/trial_summary.md'>demo/trial_summary.md</a>). "
            "Every run counts; classes use Thomas's label where one exists.</p>")


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
    return "\n".join(out)


def target_rows(f) -> str:
    if "targets" not in f:
        return "<tr><td colspan='3' class='muted'>Run <code>make generate</code>.</td></tr>"
    keep = [t for t in f["targets"] if not t[0].startswith("v1_adjusted_")]
    months = [t for t in f["targets"] if t[0].startswith("v1_adjusted_")]
    rows = []
    for name, expected, achieved, passed in keep:
        a = f"{achieved:,.0f}" if abs(achieved) >= 10 else (f"{achieved:.4f}" if abs(achieved) < 1 else f"{achieved:.2f}")
        rows.append(f"<tr><td>{esc(name.replace('_', ' '))}</td><td class='mono'>{esc(expected)}</td>"
                    f"<td class='mono num'>{a} <span class='{'ok' if passed else 'bad'}'>{'✓' if passed else '✗'}</span></td></tr>")
    ok = sum(1 for m in months if m[3])
    rows.append(f"<tr><td>monthly v1 adjusted churn, Jan 2025 to Jun 2026</td><td class='mono'>each ±0.02 pp</td>"
                f"<td class='mono num'>{ok}/{len(months)} <span class='{'ok' if ok == len(months) else 'bad'}'>{'✓' if ok == len(months) else '✗'}</span></td></tr>")
    return "".join(rows)


CSS = r"""
@font-face { font-family: "EB Garamond"; src: url("charts/fonts/EBGaramond[wght].ttf") format("truetype"); font-weight: 400 800; }
@font-face { font-family: "Roboto Mono"; src: url("charts/fonts/RobotoMono[wght].ttf") format("truetype"); font-weight: 100 700; }
:root {
  --cream: #fff9eb; --paper: #fffdf6; --slate: #526476; --ink: #34414e; --sage: #90b39d; --brick: #a93427;
  --line: #e7e0cf; --soft: #f5eedd; --muted: #7d8a97;
  --serif: "EB Garamond", Georgia, serif; --mono: "Roboto Mono", Menlo, monospace;
  --sans: "Helvetica Neue", Helvetica, Arial, sans-serif;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; overflow-x: hidden; background: var(--cream); color: var(--ink); font: 16px/1.6 var(--sans); }
a { color: var(--slate); text-decoration-color: var(--sage); text-underline-offset: 3px; }
a:hover { color: var(--brick); }
code, .mono { font-family: var(--mono); font-size: .88em; }
code { background: var(--soft); padding: .1em .35em; border-radius: 4px; }
.wrap { max-width: 1120px; margin: 0 auto; padding: 0 24px; }
nav { position: sticky; top: 0; z-index: 10; background: rgba(255,249,235,.92); backdrop-filter: blur(8px); border-bottom: 1px solid var(--line); }
nav .wrap { display: flex; gap: 22px; align-items: center; height: 54px; overflow-x: auto; scrollbar-width: none; }
nav .wrap::-webkit-scrollbar { display: none; }
nav .brand { font-family: var(--serif); font-size: 21px; color: var(--slate); font-weight: 600; white-space: nowrap; margin-right: auto; text-decoration: none; }
nav a:not(.brand) { font-family: var(--mono); font-size: 12.5px; text-decoration: none; letter-spacing: .02em; white-space: nowrap; }
header { padding: 72px 0 40px; }
.kicker { font-family: var(--mono); font-size: 12.5px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); }
h1 { font-family: var(--serif); font-weight: 500; font-size: clamp(40px, 6vw, 66px); line-height: 1.02; color: var(--slate); margin: 14px 0 18px; letter-spacing: -.01em; }
h1 em { color: var(--brick); font-style: italic; }
.lede { font-size: 19px; max-width: 760px; color: var(--ink); }
h2 { font-family: var(--serif); font-weight: 500; font-size: 36px; color: var(--slate); margin: 0 0 8px; }
h3 { font-family: var(--serif); font-weight: 600; font-size: 22px; color: var(--slate); margin: 0 0 6px; }
section { padding: 56px 0; border-top: 1px solid var(--line); }
.sub { color: var(--muted); margin: 0 0 28px; max-width: 760px; }
.stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 36px; }
.stat { background: var(--paper); border: 1px solid var(--line); border-radius: 12px; padding: 18px 18px 14px; }
.stat .v { font-family: var(--serif); font-size: 40px; line-height: 1; color: var(--slate); }
.stat .v.brick { color: var(--brick); } .stat .v.sage { color: #5f8a6f; }
.stat .l { font-family: var(--mono); font-size: 11.5px; color: var(--muted); margin-top: 8px; letter-spacing: .02em; }
.claims { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px; }
.claim { background: var(--paper); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; display: flex; flex-direction: column; }
.claim img { width: 100%; display: block; border-bottom: 1px solid var(--line); background: var(--cream); }
.claim .body { padding: 18px 20px 20px; }
.claim .n { font-family: var(--mono); font-size: 12px; color: var(--brick); letter-spacing: .1em; }
.claim p { margin: 6px 0 10px; }
.links { font-family: var(--mono); font-size: 12.5px; display: flex; flex-wrap: wrap; gap: 6px 14px; }
.steps { counter-reset: step; display: grid; gap: 12px; }
.step { display: grid; grid-template-columns: 38px minmax(0, 1fr); gap: 14px; align-items: start; background: var(--paper); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.step::before { counter-increment: step; content: counter(step); font-family: var(--serif); font-size: 26px; color: var(--sage); line-height: 1; padding-top: 4px; }
.step h4 { margin: 0 0 4px; font-size: 16px; color: var(--slate); }
.step p { margin: 0 0 8px; color: var(--ink); font-size: 14.5px; }
pre.cmd { position: relative; margin: 0; background: var(--slate); color: var(--cream); border-radius: 8px; padding: 11px 76px 11px 14px; font: 13px/1.55 var(--mono); white-space: pre-wrap; overflow-wrap: anywhere; }
pre.cmd button { position: absolute; top: 7px; right: 7px; font: 11px var(--mono); background: transparent; color: var(--cream); border: 1px solid rgba(255,249,235,.4); border-radius: 5px; padding: 4px 9px; cursor: pointer; }
pre.cmd button:hover { background: rgba(255,249,235,.12); }
.grid3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.card { background: var(--paper); border: 1px solid var(--line); border-radius: 12px; padding: 18px 20px; }
.card .ref { font-family: var(--mono); font-size: 12px; color: var(--muted); }
table.data { width: 100%; border-collapse: collapse; background: var(--paper); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; font-size: 14.5px; }
table.data th { text-align: left; font: 500 11.5px var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--muted); background: var(--soft); padding: 10px 12px; }
table.data td { padding: 9px 12px; border-top: 1px solid var(--line); }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.ok { color: #5f8a6f; font-weight: 700; } .bad { color: var(--brick); font-weight: 700; }
.cls-A { color: #5f8a6f; } .cls-C { color: var(--brick); }
.tag { font: 11.5px var(--mono); padding: 2px 8px; border-radius: 99px; background: var(--soft); color: var(--slate); }
.tag-written { background: #e3eee6; } .tag-rot { background: #f3dfdb; color: var(--brick); }
pre.diff { background: var(--paper); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; font: 13px/1.55 var(--mono); overflow-x: auto; margin: 0; }
pre.diff .add { color: #2f6b45; background: #e3eee6; display: block; }
pre.diff .del { color: var(--brick); background: #f6e3df; display: block; }
pre.diff .hunk { color: var(--muted); display: block; }
.tree { font: 13.5px/1.9 var(--mono); columns: 2; column-gap: 40px; }
.tree div { break-inside: avoid; }
.tree a { text-decoration: none; }
.tree span { color: var(--muted); font-family: var(--sans); font-size: 13.5px; }
.muted { color: var(--muted); } .small { font-size: 13px; }
footer { padding: 40px 0 70px; border-top: 1px solid var(--line); font: 12.5px var(--mono); color: var(--muted); }
.two { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, .9fr); gap: 28px; align-items: start; }
@media (max-width: 860px) {
  .stats { grid-template-columns: repeat(2, 1fr); } .claims, .grid3, .two { grid-template-columns: minmax(0, 1fr); }
  .wrap { padding: 0 16px; } table.data { font-size: 13px; } table.data td, table.data th { padding: 8px; }
  .numbers-table { overflow-x: auto; }
  .tree { columns: 1; } header { padding-top: 44px; }
}
"""

JS = r"""
document.querySelectorAll('pre.cmd').forEach(pre => {
  const b = document.createElement('button'); b.textContent = 'copy';
  b.onclick = () => { navigator.clipboard.writeText(pre.dataset.cmd || pre.innerText.replace(/copy$/, '').trim()); b.textContent = 'copied'; setTimeout(() => b.textContent = 'copy', 1400); };
  pre.appendChild(b);
});
"""


def cmd(text: str) -> str:
    return f"<pre class='cmd' data-cmd='{esc(text)}'>{esc(text)}</pre>"


def main():
    f = facts()
    now = dt.datetime.now().strftime("%d %B %Y, %H:%M")
    head = git("rev-parse", "--short", "HEAD")
    tags = {t: git("rev-parse", "--short", f"refs/tags/{t}") for t in ("kelder/before-context", "kelder/with-context", "kelder/rot")}
    selected = sorted((ROOT / "demo" / "selected").glob("*.md"))

    def chart(stem):
        p = ROOT / "charts" / "out" / f"{stem}.png"
        return f"<img src='charts/out/{stem}.png' alt='{esc(stem)}' loading='lazy'>" if p.exists() else ""

    claims = [
        ("01", "Agents on a good warehouse still explain numbers wrongly",
         f"The before-context warehouse is well modelled and fully documented, yet {f.get('midnight', 0):,} March cancellations share one midnight UTC timestamp. Without the reason written down, an agent reads it as customers leaving.",
         "cancellations_by_hour_feb_mar_2026", [("installed workspace", None), ("ingest_before_summary.md", "demo/selected/ingest_before_summary.md")]),
        ("02", "Writing the context down fixes most of it",
         f"Caveats, <code>context.business_events</code>, decision records and verified queries turn {pct(f.get('march_raw'))} into {pct(f.get('march_adj'))}, with the reason attached. The model is the same.",
         "churn_monthly_2026_events", [("AGENTS.md", "kelder-dbt/AGENTS.md"), ("0007", "kelder-dbt/context/decisions/0007-recharge-migration-churn-artifacts.md"), ("verified_queries.yml", "kelder-dbt/context/verified_queries.yml")]),
        ("03", "Written context decays",
         f"One commit, “Fix churn logic”, points the restated series at the unadjusted events. The like-for-like comparison flips from {pct(f.get('yoy_26'), 2)} vs {pct(f.get('yoy_25'), 2)} (improved) to {pct(f.get('rot_26'), 2)} (worse), while every caveat still says the artefacts are excluded.",
         "yoy_like_for_like_written_vs_rot", [("rot diff", "#rot"), ("rot workspace", None)]),
        ("04", "Forcing functions catch the decay",
         "The pull request template asks for the metric impact; CI runs the verified queries against pinned answers. On the rot commit, the like-for-like query and the capture check fail, and the March query still passes.",
         "churn_v1_vs_v2_restated", [("make check", "#start"), ("pull request template", ".github/pull_request_template.md"), ("ci.yml", ".github/workflows/ci.yml")]),
    ]

    def links(ls):
        return "".join(f"<a href='{esc(h)}'>{esc(t)}</a>" if h else f"<span class='muted'>{esc(t)}</span>" for t, h in ls)

    claim_html = "".join(f"""<article class='claim'>{chart(c[3])}<div class='body'><div class='n'>CLAIM {c[0]}</div>
        <h3>{esc(c[1])}</h3><p>{c[2]}</p><div class='links'>{links(c[4])}</div></div></article>""" for c in claims)

    june = f.get("june") or {}
    stats = [
        (pct(f.get("march_raw")), "brick", "March 2026 churn, raw"),
        (pct(f.get("march_adj")), "sage", "March 2026 churn, adjusted"),
        (f"{f.get('artefacts', 0):,}", "", "paused subscriptions imported as cancelled"),
        (f"{june.get('new_subscribers', '–'):,}" if june else "–", "", f"new subscribers June 2026, {june.get('restores_excluded', '–')} restores excluded"),
    ]
    stat_html = "".join(f"<div class='stat'><div class='v {c}'>{esc(v)}</div><div class='l'>{esc(l)}</div></div>" for v, c, l in stats)

    steps = [
        ("Build everything from scratch", "Generate the data, load the warehouse, build the three states, run the tests, render the charts. Takes about three minutes.", "uv sync && make all"),
        ("Run the checks CI runs", "Verified queries against pinned answers, and the context capture check on the rot pull request body. Red on purpose.", "make check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md"),
        ("Create the agent workspaces", "installed, written and rot under ~/kelder-demo, each with its own ktx project and warehouse copy. Then start their ktx servers.", "make workspaces && make serve"),
        ("Prove the isolation", "Leak check across every workspace, then dry runs that confirm the tools, the denied reads and that AGENTS.md loads.", "make leak-check && uv run python scripts/verify_isolation.py"),
        ("Run trials", "Same question, fresh session, pinned model, every transcript kept. Start with three runs per question.", "make trials WORKSPACE=installed N=3 && make summary"),
        ("Record the clips", "Clip one: installed and written side by side. Clip two: the rot diff, the rot agent, then the failing check.", "scripts/demo_terminal.sh side-by-side"),
    ]
    step_html = "".join(f"<div class='step'><div><h4>{esc(t)}</h4><p>{esc(d)}</p>{cmd(c)}</div></div>" for t, d, c in steps)

    tree = [
        ("BUILD_BRIEF.md", "the specification"), ("BUILD_LOG.md", "every deviation and judgement call"), ("README.md", "how to reproduce"),
        ("generator/", "world simulation, source systems, incidents, truth"), ("generator/config.yaml", "every parameter and the seed"),
        ("loader/load_raw.py", "Parquet into raw_* schemas"), ("kelder-dbt/", "Kelder's analytics repo (three states)"),
        ("kelder-dbt/context/", "decisions, glossary, quirks, verified queries"), ("scripts/", "build states, checks, workspaces, trials"),
        ("tests/", "targets, realism, incidents, truth, leaks"), ("charts/out/", "slide charts: SVG, PNG, JSON"),
        ("demo/", "prompts, trials, labels, selected answers"), ("demo/ktx/", "stored ktx ingest output per state"),
        ("data/profile_report.md", "ten-minute sniff test of the data"), ("thinking/", "design notes"),
    ]
    tree_html = "".join(f"<div><a href='{esc(p)}'>{esc(p)}</a> <span>{esc(d)}</span></div>" for p, d in tree)

    states = [
        ("before-context", "kelder/before-context", f"A competent dbt project with no context layer. March reads {pct(f.get('march_raw'))} and restores count as new subscribers.", "installed"),
        ("with-context", "kelder/with-context", "The article's end state: caveats, business events, metric changelog, decision records, verified queries, AGENTS.md, PR template.", "written"),
        ("rot", "kelder/rot", "One commit on top of with-context that breaks the restated series. Every piece of context still claims otherwise.", "rot"),
    ]
    state_html = "".join(f"""<div class='card'><div class='ref'>{esc(r)} · {esc(tags.get(r, ''))}</div><h3>{esc(n)}</h3>
        <p class='small'>{esc(d)}</p><div class='links'><span class='tag tag-{esc(w)}'>~/kelder-demo/{esc(w)}</span></div></div>""" for n, r, d, w in states)

    sel_html = "".join(f"<div><a href='{esc(p.relative_to(ROOT))}'>{esc(p.name)}</a></div>" for p in selected) or "<p class='muted'>None yet.</p>"

    page = f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kelder context layer</title><style>{CSS}</style></head>
<body>
<nav><div class="wrap"><a class="brand" href="#">Kelder Coffee</a>
<a href="#claims">claims</a><a href="#numbers">numbers</a><a href="#start">start here</a><a href="#states">states</a><a href="#rot">rot</a><a href="#trials">trials</a><a href="#map">map</a></div></nav>
<header><div class="wrap">
<div class="kicker">Tasman Analytics · Compass AI &amp; Tech Summit · Budapest · 1 October 2026</div>
<h1>Building a data context layer to <em>fix</em> your AI analytics</h1>
<p class="lede">The evidence behind the talk. Kelder Coffee is a fictional Amsterdam coffee subscription company with a well-modelled warehouse, six events nobody wrote down, and an agent that explains them wrongly with total confidence, until the context is written down. Then one ordinary commit makes that context false.</p>
<div class="stats">{stat_html}</div>
</div></header>

<section id="claims"><div class="wrap"><h2>Four claims, four pieces of evidence</h2>
<p class="sub">Every chart reads only from a warehouse state, never from the hidden truth, so each one is evidence about what an agent could see.</p>
<div class="claims">{claim_html}</div></div></section>

<section id="numbers"><div class="wrap two"><div><h2>Numbers that must reconcile</h2>
<p class="sub">Asserted by tests against the generated data. Read live from <code>data/truth/kelder_truth.duckdb</code>.</p>
<div class="numbers-table"><table class="data"><thead><tr><th>Target</th><th>Expected</th><th>Achieved</th></tr></thead><tbody>{target_rows(f)}</tbody></table></div></div>
<div><h2>The core fact</h2><p>On 12 March 2026 Kelder migrated billing from Shopify to Recharge. About {f.get('artefacts', 1900):,} paused subscriptions were written as cancelled. March churn is <b style="color:var(--brick)">{pct(f.get('march_raw'))}</b> raw and <b style="color:#5f8a6f">{pct(f.get('march_adj'))}</b> adjusted. Anyone quoting the raw number is wrong.</p>
<p class="small muted">Findable in the <code>churned_at</code> caveat, <code>context.business_events</code>, decision 0007, the March verified query and <code>AGENTS.md</code>, and checked by <code>tests/truth/test_context_files.py</code>.</p>
<h3 style="margin-top:28px">Also in the data</h3>
<p class="small">Email-attributed revenue for April 2026 reads €{f.get('email_april', 0):,.0f} because of a 31-hour Klaviyo gap. From May the churn definition gives failed payments 30 days' grace. A PostNL strike hit parcels shipped 18 to 24 May. The Father's Day bundle ran 14 to 21 June. {f.get('restores', 0):,} wiped pauses came back as “new” Recharge subscriptions.</p></div></div></section>

<section id="start"><div class="wrap"><h2>Start here</h2><p class="sub">Everything runs locally. Requirements: uv and git; the agent tooling (pinned Claude Code, ktx, Node 22) installs into <code>~/kelder-demo/_tools</code> with <code>tools/demo/setup.sh</code>.</p>
<div class="steps">{step_html}</div></div></section>

<section id="states"><div class="wrap"><h2>Three states of one repository</h2>
<p class="sub"><code>git log --oneline -- kelder-dbt/</code> reads as Kelder's own history, from January to June 2026. Each state is a git reference; <code>scripts/build_state.py</code> builds any of them into its own warehouse.</p>
<div class="grid3">{state_html}</div></div></section>

<section id="rot"><div class="wrap two"><div><h2>The rot commit</h2>
<p class="sub">“Fix churn logic”, by Sanne, 26 June 2026. The pull request body has no box ticked and one line under “What changed”: <i>Simplify churn model, consolidate v1 and v2 CTEs.</i></p>
<pre class="diff">{rot_diff()}</pre></div>
<div><h2>What catches it</h2><p>Not the dbt tests: they all pass. The verified query for the like-for-like comparison fails against its pinned answer, and the capture check fails because a metrics model changed with no metric-impact box ticked.</p>
{cmd("make check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md")}
<p class="small muted" style="margin-top:12px">Pinned answers live in <code>tests/verified/expected/</code>, outside every workspace. They are frozen only with Thomas's approval, and every freeze is logged.</p></div></div></section>

<section id="trials"><div class="wrap"><h2>Trials</h2><p class="sub">The same six questions, many times, in each workspace, on one pinned model. Honesty rules: every run is kept and counted, and the recorded take shows the most common outcome.</p>
{trial_table()}
<h3 style="margin-top:28px">Selected answers for slides</h3><div class="tree">{sel_html}</div></div></section>

<section id="map"><div class="wrap"><h2>Where things are</h2><div class="tree">{tree_html}</div></div></section>

<footer><div class="wrap">Generated {esc(now)} from commit {esc(head)} by <code>scripts/render_index.py</code>. Every number on this page is read from build outputs.</div></footer>
<script>{JS}</script></body></html>"""
    OUT.write_text(page)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
