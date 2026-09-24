"""Workspace leak check (brief section 8). Fails the build if any workspace could see the answer.

Run with `make leak-check` after `make workspaces`.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_workspace  # noqa: E402
import mcp_probe  # noqa: E402

DEMO = make_workspace.DEMO
ALL = ["installed", "written", "rot", "bare"]
PRESENT = [w for w in ALL if (DEMO / w).exists()]
BLIND = [w for w in ("installed", "bare") if w in PRESENT]
BANNED_WORDS = ["migration", "artefact", "artifact", "backfill", "legacy_pause", "restore_source", "is_legacy", "0007",
                "0009", "business_events", "metric_changelog", "changelog", "decision record", "definition change",
                "strike", "outage"]
ARTICLE = ["tasman.ai/news/how-to-build-a-context-layer", "cms.tasman.ai", "how-to-build-a-context-layer"]
BUILDER_NAMES = {"kelder_truth.duckdb", "BUILD_BRIEF.md", "BUILD_LOG.md", "world.py", "calibrate.py", "incidents.py",
                 "truth.py", "world_commerce.py", "config.yaml", "profile_report.md", "hashes.json"}
# ktx ingest output is derived from the data by a tool: matches are reported, not failures
KTX_OUTPUT_DIRS = {"semantic-layer", "wiki", "raw-sources", ".ktx"}

if not PRESENT:
    pytest.skip("no workspaces: run `make workspaces`", allow_module_level=True)


def _files(ws: Path):
    for p in sorted(ws.rglob("*")):
        if p.is_file():
            yield p


def _is_text(p: Path) -> bool:
    if p.suffix in {".duckdb", ".wal", ".parquet"}:
        return False
    try:
        chunk = p.read_bytes()[:4096]
    except OSError:
        return False
    return b"\x00" not in chunk


@pytest.mark.parametrize("ws", PRESENT)
def test_no_builder_files_or_git(ws):
    root = DEMO / ws
    bad = []
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if p.name == ".git" or p.name in BUILDER_NAMES:
            bad.append(str(rel))
        if rel.parts and rel.parts[0] in {"demo", "generator", "tests", "thinking", "data", "charts"}:
            bad.append(str(rel))
        if "expected" in rel.parts and "verified" in rel.parts:
            bad.append(str(rel))
    assert not bad, bad


@pytest.mark.parametrize("ws", PRESENT)
def test_no_article_url(ws):
    hits = [str(p) for p in _files(DEMO / ws) if _is_text(p) and any(a in p.read_text(errors="ignore") for a in ARTICLE)]
    assert not hits, hits


@pytest.mark.parametrize("ws", BLIND)
def test_blind_workspaces_have_no_context_words(ws, record_property):
    root = DEMO / ws
    fails, reported = [], []
    pat = re.compile("|".join(re.escape(w) for w in BANNED_WORDS), re.I)
    for p in _files(root):
        if not _is_text(p):
            continue
        for m in pat.finditer(p.read_text(errors="ignore")):
            hit = (str(p.relative_to(root)), m.group(0))
            (reported if set(p.relative_to(root).parts) & KTX_OUTPUT_DIRS else fails).append(hit)
    record_property("ktx_ingest_matches", reported)
    if reported:
        print(f"\nREPORTED (ktx ingest output, not a failure) in {ws}: {sorted(set(reported))[:50]}")
    assert not fails, sorted(set(fails))[:50]


@pytest.mark.parametrize("ws", BLIND)
def test_blind_warehouse_has_no_context_layer(ws):
    con = duckdb.connect(str(DEMO / ws / "warehouse.duckdb"), read_only=True)
    schemas = {r[0] for r in con.execute("select schema_name from duckdb_schemas()").fetchall()}
    cols = {r[0] for r in con.execute("select column_name from duckdb_columns()").fetchall()}
    con.close()
    assert "context" not in schemas
    assert not {"is_migration_artifact", "is_legacy_pause_restore"} & cols


@pytest.mark.parametrize("ws", BLIND)
def test_blind_workspaces_have_no_agents_md(ws):
    root = DEMO / ws
    for name in ("AGENTS.md", "CLAUDE.md", ".github"):
        assert not list(root.rglob(name)), name
    assert not (root / "kelder-dbt" / "context").exists()


@pytest.mark.parametrize("ws", [w for w in ("written", "rot") if w in PRESENT])
def test_agents_md_is_imported_and_nothing_else(ws):
    root = DEMO / ws
    assert (root / "CLAUDE.md").read_text().strip() == "@kelder-dbt/AGENTS.md"
    assert (root / "kelder-dbt" / "AGENTS.md").exists()


@pytest.mark.parametrize("ws", PRESENT)
def test_settings_deny_web_and_bash(ws):
    s = json.loads((DEMO / ws / ".claude" / "settings.json").read_text())
    perms = s["permissions"]
    allow = perms.get("allow", [])
    for tool in ("Bash", "WebSearch", "WebFetch"):  # noqa
        assert tool in perms["deny"], tool
        assert not any(a == tool or a.startswith(tool + "(") for a in allow), tool
    assert set(allow) <= {"Read", "Grep", "Glob"} | {a for a in allow if a.startswith(("mcp__warehouse__", "mcp__ktx__"))}
    assert perms.get("defaultMode") in ("dontAsk", "default")
    assert not s.get("enableAllProjectMcpServers", False)
    # other workspaces and the build repository are not readable
    for other in [w for w in ALL if w != ws]:
        assert f"Read(/{DEMO / other}/**)" in perms["deny"], other
    assert f"Read(/{ROOT.parent}/**)" in perms["deny"]


def _server(ws):
    cfg = json.loads((DEMO / ws / ".mcp.json").read_text())["mcpServers"]
    assert len(cfg) == 1, cfg
    return next(iter(cfg.items()))


@pytest.mark.parametrize("ws", PRESENT)
def test_one_mcp_server_read_only_without_file_access(ws):
    name, spec = _server(ws)
    text = (DEMO / ws / ".mcp.json").read_text()
    assert str(ROOT) not in text
    if name == "ktx":
        assert spec["type"] == "http" and spec["url"].startswith("http://127.0.0.1:")
        cfg = (DEMO / ws / "kelder-dbt" / "ktx.yaml").read_text()
        assert "backend: none" in cfg.split("llm:")[1].split("ingest:")[0], "LLM must be off in workspaces"
        assert str(DEMO / ws / "warehouse.duckdb") in cfg
        assert str(ROOT) not in cfg
        for other in [w for w in ALL if w != ws]:
            assert str(DEMO / other) not in cfg
        patched = (make_workspace.DEMO / "_tools" / "npm" / "node_modules" / "@kaelio" / "ktx" / "dist" / "connectors" / "duckdb" / "connector.js").read_text()
        assert "enable_external_access: 'false'" in patched
    else:
        args = spec["args"]
        assert "--read-write" not in args and "--no-ephemeral-connections" in args
        assert any("enable_external_access = false" in a for a in args)
        assert str(DEMO / ws / "warehouse.duckdb") in args


@pytest.mark.parametrize("ws", PRESENT)
def test_mcp_server_refuses_files_and_writes(ws):
    name, _ = _server(ws)
    try:
        r = mcp_probe.probe(DEMO / ws / ".mcp.json")
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"{ws}: MCP server not reachable ({e}); for ktx run scripts/ktx_serve.py start")
    expected = sorted(make_workspace.KTX_TOOLS) if name == "ktx" else sorted(make_workspace.FALLBACK_TOOLS)
    assert r["tools"] == expected, r["tools"]
    p = r["probes"]
    assert not p["plain_query"]["is_error"], p["plain_query"]
    for key in ("read_local_file", "read_text_file", "glob_files", "attach_other_db", "write_table", "change_setting"):
        assert p[key]["is_error"], (key, p[key]["text"])


@pytest.mark.parametrize("ws", [w for w in ("written", "rot") if w in PRESENT])
def test_ktx_wiki_matches_context_files(ws):
    """context/ is canonical: every context markdown file is a verbatim wiki page, and nothing else is claimed."""
    root = DEMO / ws / "kelder-dbt"
    wiki = root / "wiki" / "global"
    if not wiki.exists():
        pytest.skip("not a ktx workspace")
    pages = [p.read_text() for p in wiki.glob("*.md")]
    for md in sorted((root / "context").rglob("*.md")):
        body = md.read_text().strip()
        assert any(body in page for page in pages), f"{md.relative_to(root)} missing from wiki/global"


def test_no_claude_md_above_the_demo_directory():
    d = DEMO.resolve()
    hits = []
    for parent in [d, *d.parents]:
        for name in ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md"):
            if (parent / name).exists():
                hits.append(str(parent / name))
    assert not hits, hits


def test_dedicated_config_dir_has_no_memory_or_instructions():
    cfg = make_workspace.CONFIG_DIR
    assert cfg.exists()
    for name in ("CLAUDE.md", "projects", "agents", "commands", "skills", "plugins"):
        p = cfg / name
        assert not (p.exists() and (p.is_file() or any(p.iterdir()))), p


def test_no_user_level_memory_that_could_load():
    home = Path.home()
    assert not (home / ".claude" / "CLAUDE.md").exists()
    for projects in (home / ".claude" / "projects", make_workspace.CONFIG_DIR / "projects"):
        for w in ALL:
            slug = str(DEMO / w).replace("/", "-")
            assert not (projects / slug / "memory").exists(), projects / slug
