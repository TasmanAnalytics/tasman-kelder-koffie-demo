"""Render ktx-viewer.html: a browsable view of what ktx inferred, for each state.

    uv run python scripts/render_ktx_viewer.py      (or: make ktx-viewer)

ktx 0.16.0 has no UI, so this reads the ingest output stored in demo/ktx/<state>/ (wiki pages as markdown,
semantic-layer sources as YAML) and writes one self-contained page. Nothing is edited or removed. Every
description, tag and link on the page comes from those files. The only thing this script adds is a
comparison marker per item ("same as with-context", "differs", "no page of this name in with-context"), computed from file content and file name (ktx names pages per ingest, so a renamed page shows as not present).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
KTX = ROOT / "demo" / "ktx"
OUT = ROOT / "ktx-viewer.html"
STATES = [
    ("before", "Before context", "Nothing written down. ktx works from the dbt project and the warehouse only."),
    ("with_context", "With context", "Decision records, glossary and changelog ingested. The state the talk treats as correct."),
    ("rot", "Rot", "One commit on top of with-context. The docs and the code have drifted apart."),
]
FRONT = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.S)


def load_wiki(state: str) -> list[dict]:
    pages = []
    for p in sorted((KTX / state / "wiki").rglob("*.md")):
        raw = p.read_text()
        m = FRONT.match(raw)
        meta, body = (yaml.safe_load(m.group(1)) or {}, m.group(2)) if m else ({}, raw)
        title = next((ln[2:].strip() for ln in body.splitlines() if ln.startswith("# ")), p.stem)
        pages.append({
            "key": p.stem,
            "path": str(p.relative_to(KTX / state / "wiki")),
            "title": title,
            "summary": meta.get("summary", ""),
            "tags": meta.get("tags") or [],
            "sl_refs": meta.get("sl_refs") or [],
            "usage": meta.get("usage_mode", ""),
            "body": body.strip(),
            "hash": hashlib.sha1(body.strip().encode()).hexdigest()[:10],
        })
    return pages


def load_sl(state: str) -> tuple[list[dict], dict]:
    base = KTX / state / "semantic-layer"
    sources, schema = [], {}
    for p in sorted(base.rglob("*.yaml")):
        data = yaml.safe_load(p.read_text()) or {}
        if p.parent.name == "_schema":
            schema.update(data.get("tables") or {})
            continue
        sources.append({
            "name": data.get("name", p.stem),
            "kind": "metric" if p.stem.startswith("metrics_") else "model",
            "description": (data.get("descriptions") or {}).get("user", ""),
            "columns": [
                {"name": c.get("name"), "description": (c.get("descriptions") or {}).get("user", ""),
                 "tests": sorted((c.get("constraints") or {}).get("dbt", {}).keys())}
                for c in data.get("column_overrides") or []
            ],
            "measures": [
                {"name": m.get("name"), "expr": m.get("expr", ""), "description": m.get("description", ""),
                 "segments": m.get("segments") or []}
                for m in data.get("measures") or []
            ],
            "segments": data.get("segments") or [],
            "yaml": p.read_text(),
            "hash": hashlib.sha1(p.read_text().encode()).hexdigest()[:10],
        })
    tables = {
        name: {
            "table": t.get("table", name),
            "columns": [{"name": c["name"], "type": c.get("type", ""),
                         "description": (c.get("descriptions") or {}).get("ai", "")} for c in t.get("columns") or []],
        }
        for name, t in schema.items()
    }
    return sources, tables


def load_state(key: str, label: str, blurb: str) -> dict:
    meta_path = KTX / key / "ingest_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    sources, tables = load_sl(key)
    return {
        "key": key, "label": label, "blurb": blurb,
        "ingest": {k: meta.get(k) for k in ("ktx_version", "started", "finished", "enrichment", "embeddings")},
        "wiki": load_wiki(key), "sl": sources, "tables": tables,
    }


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kelder ktx viewer</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..600&family=Instrument+Sans:wght@400..700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--espresso:#2A1C15;--crema:#F4EADB;--baksteen:#A9462B;--gracht:#2F5B55;--honing:#D9A441;--paper:#FAF4E9;--line:#DDCFB8;--soft:#EADFCB;--muted:#7A6656;--ink:#2A1C15;
--serif:"Fraunces",Georgia,serif;--sans:"Instrument Sans","Helvetica Neue",Arial,sans-serif;--mono:"JetBrains Mono",Menlo,monospace}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{background:var(--paper);color:var(--ink);font:15px/1.55 var(--sans);display:flex;flex-direction:column}
code,.mono{font-family:var(--mono);font-size:.86em}
header{background:var(--espresso);color:var(--crema);padding:12px 20px;display:flex;gap:20px;align-items:center;flex-wrap:wrap}
header h1{font:500 21px var(--serif);margin:0}
.tabs{display:flex;gap:6px}
.tab{font:500 12.5px var(--mono);letter-spacing:.04em;background:transparent;color:var(--crema);border:1px solid #5b463a;border-radius:99px;padding:6px 14px;cursor:pointer}
.tab[aria-pressed=true]{background:var(--honing);color:var(--espresso);border-color:var(--honing)}
.blurb{font-size:13px;color:#CDBFA9;flex:1;min-width:240px}
.layout{flex:1;display:flex;min-height:0}
aside{width:340px;border-right:1px solid var(--line);background:var(--crema);display:flex;flex-direction:column;min-height:0}
.side-top{padding:12px;border-bottom:1px solid var(--line)}
.side-top input{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--paper);font:14px var(--sans);color:var(--ink)}
.mode{display:flex;gap:6px;margin-bottom:10px}
.mode button{flex:1;font:500 12px var(--mono);letter-spacing:.06em;text-transform:uppercase;padding:7px;border:1px solid var(--line);background:var(--paper);border-radius:8px;cursor:pointer;color:var(--muted)}
.mode button[aria-pressed=true]{background:var(--gracht);color:var(--crema);border-color:var(--gracht)}
.list{overflow:auto;flex:1}
.item{display:block;width:100%;text-align:left;padding:10px 14px;border:0;border-bottom:1px solid var(--line);background:transparent;cursor:pointer;color:var(--ink);font:inherit}
.item:hover{background:var(--soft)}.item[aria-current=true]{background:var(--soft);box-shadow:inset 3px 0 var(--baksteen)}
.item .t{font:600 14px var(--serif);display:block}
.item .s{font-size:12px;color:var(--muted);display:block;margin-top:2px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.grp{font:500 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--baksteen);padding:12px 14px 4px}
main{flex:1;overflow:auto;padding:28px clamp(16px,4vw,56px) 80px;min-width:0}
main .wrap{max-width:900px}
h2{font:500 32px/1.15 var(--serif);margin:0 0 6px}h3{font:600 20px var(--serif);margin:26px 0 8px}
.kicker{font:500 12px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--baksteen)}
.lede{color:var(--muted);margin:8px 0 14px}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
.chip{font:400 12px var(--mono);border:1px solid var(--line);background:var(--crema);border-radius:99px;padding:2px 10px;color:var(--muted)}
button.chip{cursor:pointer;color:var(--gracht);border-color:var(--gracht)}button.chip:hover{background:var(--gracht);color:var(--crema)}
.badge{font:500 11px var(--mono);letter-spacing:.06em;border-radius:6px;padding:2px 7px;margin-left:8px;vertical-align:middle;white-space:nowrap}
.b-same{background:#D6E3DF;color:var(--gracht)}.b-diff{background:#F2E1B8;color:#8A5F12}.b-only{background:#F0D9CF;color:var(--baksteen)}
.doc{background:#fff;border:1px solid var(--line);border-radius:12px;padding:6px 26px 18px}
.doc h1{font:500 26px var(--serif);margin:20px 0 8px}.doc h2{font-size:22px;margin:22px 0 6px}.doc h3{font-size:17px}
.doc table{border-collapse:collapse;margin:12px 0;font-size:13.5px}.doc th,.doc td{border:1px solid var(--line);padding:5px 10px;text-align:left}.doc th{background:var(--crema)}
.doc pre,pre.yaml{background:var(--espresso);color:var(--crema);padding:14px 16px;border-radius:10px;overflow:auto;font:13px/1.5 var(--mono)}
.doc code{background:var(--soft);padding:1px 5px;border-radius:4px}.doc pre code{background:none;padding:0}
table.cols{width:100%;border-collapse:collapse;font-size:14px}
table.cols th{font:500 11px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted);text-align:left;border-bottom:2px solid var(--line);padding:6px 8px}
table.cols td{border-bottom:1px solid var(--line);padding:8px;vertical-align:top}
table.cols td:first-child{font-family:var(--mono);font-size:13px;white-space:nowrap}
.measure{border:1px solid var(--line);border-radius:10px;background:#fff;padding:10px 14px;margin:8px 0}
.measure .n{font:600 14px var(--mono)}.measure .e{font:13px var(--mono);color:var(--gracht);margin:2px 0}
.stats{display:flex;gap:22px;flex-wrap:wrap;margin:8px 0 0}.stats div{font:12px var(--mono);color:#CDBFA9}.stats b{color:var(--honing);font-size:15px;margin-right:4px}
details{margin:14px 0}summary{cursor:pointer;font:13px var(--mono);color:var(--gracht)}
.empty{color:var(--muted);font-style:italic}
@media(max-width:820px){.layout{flex-direction:column}aside{width:100%;max-height:42vh}}
</style></head><body>
<header><h1>Kelder ktx viewer</h1><div class="tabs" id="tabs"></div><div class="blurb" id="blurb"></div></header>
<div class="layout"><aside><div class="side-top"><div class="mode" id="mode"></div><input id="q" placeholder="Search this state" autocomplete="off"></div><div class="list" id="list"></div></aside>
<main><div class="wrap" id="view"></div></main></div>
<script>
const DATA = __DATA__;
const CMP = "with_context";
const S = {state: "with_context", mode: "wiki", sel: null, q: ""};
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const cur = () => DATA.find(d => d.key === S.state);
const other = () => DATA.find(d => d.key === CMP);

function inline(t){
  return esc(t).replace(/`([^`]+)`/g,"<code>$1</code>").replace(/\*\*([^*]+)\*\*/g,"<b>$1</b>").replace(/(^|[\s(])_([^_]+)_(?=[\s).,]|$)/g,"$1<i>$2</i>");
}
function md(src){
  const lines = src.split("\n"); let out = "", i = 0;
  while(i < lines.length){
    const l = lines[i];
    if(/^```/.test(l)){let b=[];i++;while(i<lines.length&&!/^```/.test(lines[i]))b.push(lines[i++]);i++;out+="<pre><code>"+esc(b.join("\n"))+"</code></pre>";continue}
    let m = l.match(/^(#{1,4})\s+(.*)/); if(m){out+=`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`;i++;continue}
    if(/^\|/.test(l) && /^\|[\s:|-]+\|?\s*$/.test(lines[i+1]||"")){
      const row = r => r.replace(/^\||\|\s*$/g,"").split("|").map(c=>c.trim());
      out+="<table><tr>"+row(l).map(c=>`<th>${inline(c)}</th>`).join("")+"</tr>"; i+=2;
      while(i<lines.length&&/^\|/.test(lines[i])){out+="<tr>"+row(lines[i]).map(c=>`<td>${inline(c)}</td>`).join("")+"</tr>";i++}
      out+="</table>";continue}
    if(/^\s*[-*]\s+/.test(l)){out+="<ul>";while(i<lines.length&&/^\s*[-*]\s+/.test(lines[i]))out+=`<li>${inline(lines[i++].replace(/^\s*[-*]\s+/,""))}</li>`;out+="</ul>";continue}
    if(/^\s*\d+\.\s+/.test(l)){out+="<ol>";while(i<lines.length&&/^\s*\d+\.\s+/.test(lines[i]))out+=`<li>${inline(lines[i++].replace(/^\s*\d+\.\s+/,""))}</li>`;out+="</ol>";continue}
    if(!l.trim()){i++;continue}
    let p=[];while(i<lines.length&&lines[i].trim()&&!/^(#|```|\||\s*[-*]\s|\s*\d+\.\s)/.test(lines[i]))p.push(lines[i++]);
    out+=`<p>${inline(p.join(" "))}</p>`;
  }
  return out;
}
function badge(item, kind){
  if(S.state === CMP) return "";
  const o = other()[kind].find(x => (kind==="wiki"?x.key:x.name) === (kind==="wiki"?item.key:item.name));
  if(!o) return '<span class="badge b-only">not in with-context under this name</span>';
  return o.hash === item.hash ? '<span class="badge b-same">same as with-context</span>' : '<span class="badge b-diff">differs from with-context</span>';
}
function match(text){return !S.q || text.toLowerCase().includes(S.q.toLowerCase())}

function renderTop(){
  $("tabs").innerHTML = DATA.map(d=>`<button class="tab" aria-pressed="${d.key===S.state}" data-s="${d.key}">${esc(d.label)}</button>`).join("");
  $("blurb").innerHTML = esc(cur().blurb);
  $("mode").innerHTML = ["wiki","sl"].map(m=>`<button aria-pressed="${S.mode===m}" data-m="${m}">${m==="wiki"?"Wiki ("+cur().wiki.length+")":"Semantic layer ("+cur().sl.length+")"}</button>`).join("");
}
function renderList(){
  const c = cur(); let h = "";
  if(S.mode==="wiki"){
    const rows = c.wiki.filter(p=>match(p.title+p.summary+p.tags.join(" ")+p.body));
    if(!rows.length) h = '<div class="grp">No pages</div>';
    rows.forEach(p=>{h+=`<button class="item" data-k="${esc(p.key)}" aria-current="${S.sel===p.key}"><span class="t">${esc(p.title)}</span><span class="s">${esc(p.summary)}</span></button>`});
  } else {
    [["model","Models"],["metric","Metrics"]].forEach(([k,label])=>{
      const rows = c.sl.filter(s=>s.kind===k && match(s.name+s.description+s.columns.map(x=>x.name+x.description).join(" ")));
      if(rows.length) h += `<div class="grp">${label}</div>`;
      rows.forEach(s=>{h+=`<button class="item" data-k="${esc(s.name)}" aria-current="${S.sel===s.name}"><span class="t mono">${esc(s.name)}</span><span class="s">${esc(s.description)}</span></button>`});
    });
    const tabs = Object.entries(c.tables).filter(([n])=>match(n));
    if(tabs.length) h += '<div class="grp">Warehouse tables</div>';
    tabs.forEach(([n])=>{h+=`<button class="item" data-k="table:${esc(n)}" aria-current="${S.sel==="table:"+n}"><span class="t mono">${esc(n)}</span></button>`});
  }
  $("list").innerHTML = h;
}
function renderView(){
  const c = cur(), v = $("view");
  const stats = `<div class="stats"><div><b>${c.wiki.length}</b>wiki pages</div><div><b>${c.sl.length}</b>semantic-layer sources</div><div><b>${Object.keys(c.tables).length}</b>warehouse tables</div><div>ingested ${esc((c.ingest.finished||"").slice(0,16).replace("T"," "))} with ${esc(c.ingest.ktx_version||"")}</div></div>`;
  if(!S.sel){
    v.innerHTML = `<div class="kicker">${esc(c.label)}</div><h2>What ktx inferred</h2><p class="lede">${esc(c.blurb)} Pick a page or a source on the left.</p>${stats}`;
    return;
  }
  if(S.mode==="wiki"){
    const p = c.wiki.find(x=>x.key===S.sel); if(!p){S.sel=null;return renderView()}
    v.innerHTML = `<div class="kicker">Wiki page${badge(p,"wiki")}</div><h2>${esc(p.title)}</h2><p class="lede">${esc(p.summary)}</p>
      <div class="chips">${p.tags.map(t=>`<span class="chip">${esc(t)}</span>`).join("")}${p.sl_refs.map(r=>{const ok=c.sl.some(s=>s.name===r);return ok?`<button class="chip" data-go="${esc(r)}">sl: ${esc(r)}</button>`:`<span class="chip">ref: ${esc(r)}</span>`}).join("")}${p.usage?`<span class="chip">usage: ${esc(p.usage)}</span>`:""}</div>
      <div class="doc">${md(p.body)}</div><details><summary>${esc(p.path)}</summary><pre class="yaml">${esc(p.body)}</pre></details>`;
  } else if(S.sel.startsWith("table:")){
    const t = c.tables[S.sel.slice(6)];
    v.innerHTML = `<div class="kicker">Warehouse table</div><h2 class="mono">${esc(t.table)}</h2><p class="lede">Columns as ktx described them during ingest.</p>
      <table class="cols"><tr><th>Column</th><th>Type</th><th>Description</th></tr>${t.columns.map(x=>`<tr><td>${esc(x.name)}</td><td class="mono">${esc(x.type)}</td><td>${esc(x.description)}</td></tr>`).join("")}</table>`;
  } else {
    const s = c.sl.find(x=>x.name===S.sel); if(!s){S.sel=null;return renderView()}
    const refs = c.wiki.filter(p=>p.sl_refs.includes(s.name));
    v.innerHTML = `<div class="kicker">${s.kind==="metric"?"Metric source":"Model"}${badge(s,"sl")}</div><h2 class="mono">${esc(s.name)}</h2>
      <p class="lede">${esc(s.description)||'<span class="empty">No source-level description.</span>'}</p>
      ${refs.length?`<div class="chips">${refs.map(p=>`<button class="chip" data-wiki="${esc(p.key)}">wiki: ${esc(p.title)}</button>`).join("")}</div>`:""}
      ${s.measures.length?`<h3>Measures</h3>${s.measures.map(m=>`<div class="measure"><div class="n">${esc(m.name)}</div><div class="e">${esc(m.expr)}${m.segments.length?" where "+esc(m.segments.join(", ")):""}</div><div>${esc(m.description)}</div></div>`).join("")}`:""}
      ${s.segments.length?`<h3>Segments</h3><div class="chips">${s.segments.map(g=>`<span class="chip">${esc(typeof g==="string"?g:(g.name||JSON.stringify(g)))}</span>`).join("")}</div>`:""}
      <h3>Columns</h3><table class="cols"><tr><th>Column</th><th>Description</th><th>dbt tests</th></tr>${s.columns.map(x=>`<tr><td>${esc(x.name)}</td><td>${esc(x.description)}</td><td class="mono">${esc(x.tests.join(", "))}</td></tr>`).join("")}</table>
      <details><summary>Source YAML</summary><pre class="yaml">${esc(s.yaml)}</pre></details>`;
  }
}
function render(){renderTop();renderList();renderView()}
document.addEventListener("click", e=>{
  const t = e.target.closest("[data-s],[data-m],[data-k],[data-go],[data-wiki]"); if(!t) return;
  if(t.dataset.s){S.state=t.dataset.s;S.sel=null}
  else if(t.dataset.m){S.mode=t.dataset.m;S.sel=null}
  else if(t.dataset.k){S.sel=t.dataset.k}
  else if(t.dataset.go){S.mode="sl";S.sel=t.dataset.go}
  else if(t.dataset.wiki){S.mode="wiki";S.sel=t.dataset.wiki}
  render(); if(t.dataset.k||t.dataset.go||t.dataset.wiki) $("view").parentElement.scrollTop=0;
});
$("q").addEventListener("input", e=>{S.q=e.target.value;renderList()});
render();
</script></body></html>
"""


def main() -> None:
    data = [load_state(k, label, blurb) for k, label, blurb in STATES]
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    OUT.write_text(PAGE.replace("__DATA__", payload))
    for d in data:
        print(f"{d['key']}: {len(d['wiki'])} wiki pages, {len(d['sl'])} sources, {len(d['tables'])} tables")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
