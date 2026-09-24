"""Build one state's ktx context (ingest) and store the output in demo/ktx/<state>/.

    uv run python scripts/ktx_build.py before|with_context|rot [--force]

Ingest calls a language model, so the output is stored and never regenerated casually: the
script refuses to overwrite demo/ktx/<state>/ without --force. It runs ktx in a scrubbed
environment (no ANTHROPIC_BASE_URL or other session variables), with telemetry and update checks off.

- Database connection: the state's warehouse, read-only (ktx is patched to also disable DuckDB
  file access; see tools/demo/setup.sh).
- Context source: a clean copy of the state's kelder-dbt/ (what a workspace sees) plus its dbt manifest.
- with_context and rot: every markdown file under kelder-dbt/context/ is stored verbatim as a
  global wiki page, so context/ stays the single canonical location (tests/leaks checks they match).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_workspace  # noqa: E402

NPM_BIN = make_workspace.DEMO / "_tools" / "npm" / "node_modules" / ".bin"
# ktx 0.16.0 sends `temperature`, which the Claude 5 models reject, so ingest uses the 4.5 family.
# The demo agent itself is pinned separately (KELDER_MODEL, claude-opus-5-5).
MODELS = {
    "default": "claude-sonnet-4-5",
    "triage": "claude-haiku-4-5-20251001",
    "candidateExtraction": "claude-sonnet-4-5",
    "curator": "claude-opus-4-5",
    "reconcile": "claude-opus-4-5",
    "repair": "claude-haiku-4-5-20251001",
}
EMBEDDINGS = "backend: sentence-transformers\n    model: all-MiniLM-L6-v2\n    dimensions: 384"
STORED = ["ktx.yaml", "semantic-layer", "wiki"]


def ktx_env(runtime: Path) -> dict:
    from dotenv import dotenv_values

    key = dotenv_values(ROOT / ".env").get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY missing from .env")
    return {
        "PATH": f"{NPM_BIN}:{ROOT / '.venv' / 'bin'}:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": os.environ["HOME"],
        "ANTHROPIC_API_KEY": key,
        "KTX_TELEMETRY_DISABLED": "1",
        "DO_NOT_TRACK": "1",
        "KTX_NO_UPDATE_CHECK": "1",
        "KTX_RUNTIME_ROOT": str(runtime),
        "LANG": "en_GB.UTF-8",
    }


def ktx(args: list[str], project: Path, env: dict, log: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [str(NPM_BIN / "ktx"), *args, "--project-dir", str(project)]
    r = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if log:
        with open(log, "a") as f:
            f.write(f"$ ktx {' '.join(args)}\n{r.stdout}\n{r.stderr}\n")
    return r


def set_llm(project: Path, enrichment: str = "llm"):
    p = project / "ktx.yaml"
    s = p.read_text()
    llm = "llm:\n  provider:\n    backend: anthropic\n    anthropic:\n      api_key: env:ANTHROPIC_API_KEY\n  models:\n" + "".join(
        f"    {k}: {v}\n" for k, v in MODELS.items())
    s = re.sub(r"llm:\n  provider:\n    backend: none\n  models: \{\}\n", llm, s)
    if "adapters:" not in s:
        s = s.replace("ingest:\n", "ingest:\n  adapters:\n    - dbt\n", 1)
    s = re.sub(r"(scan:\n  enrichment:\n    mode: )none", rf"\g<1>{enrichment}", s)
    # local embeddings (ktx-managed sentence-transformers), for ingest and for scan enrichment
    s = re.sub(r"(ingest:\n(?:  adapters:\n    - dbt\n)?  embeddings:\n)    backend: none\n    dimensions: 8\n",
               lambda m: m.group(1) + "    " + EMBEDDINGS.replace("\n    ", "\n    ") + "\n", s)
    s = s.replace("scan:\n  enrichment:\n    mode: llm\n", "scan:\n  enrichment:\n    mode: llm\n    embeddings:\n      "
                  + EMBEDDINGS.replace("\n    ", "\n      ") + "\n", 1)
    p.write_text(s)


def clean_source(state: str, dest: Path) -> Path:
    src = ROOT / "build" / state / "kelder-dbt"
    if not src.exists():
        sys.exit(f"state {state} not built: run make build STATE={state}")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=lambda d, n: [x for x in n if x in make_workspace.EXCLUDE])
    manifest = ROOT / "build" / f"{state}-target" / "manifest.json"
    (dest / "target").mkdir()
    shutil.copyfile(manifest, dest / "target" / "manifest.json")
    return dest


def build(state: str, force: bool = False) -> Path:
    out = ROOT / "demo" / "ktx" / state
    if out.exists() and not force:
        sys.exit(f"{out.relative_to(ROOT)} exists; ingest output is never regenerated casually (use --force)")
    work = ROOT / "build" / "ktx" / state
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    project = work / "project"
    project.mkdir()
    source = clean_source(state, work / "kelder-dbt")
    env = ktx_env(ROOT / "build" / "ktx" / "runtime")
    log = work / "ingest.log"
    db = ROOT / "data" / "warehouse" / f"kelder_{state}.duckdb"
    r = ktx(["setup", "--no-input", "--yes", "--skip-llm", "--skip-embeddings", "--database", "duckdb",
             "--database-connection-id", "kelder", "--database-url", str(db), "--source", "dbt",
             "--source-connection-id", "kelder_dbt", "--source-path", str(source), "--source-profiles-path", str(source),
             "--source-target", "dev", "--source-warehouse-connection-id", "kelder"], project, env, log)
    set_llm(project)
    env_dbt = dict(env, KELDER_DUCKDB_PATH=str(db))
    t0 = dt.datetime.now()
    r = ktx(["ingest", "--all", "--yes", "--plain"], project, env_dbt, log)
    print(r.stdout[-2500:])
    wiki_files = []
    if (source / "context").exists():
        for md in sorted((source / "context").rglob("*.md")):
            r2 = ktx(["ingest", "--file", str(md), "--verbatim", "--connection-id", "kelder", "--yes", "--plain"], project, env, log)
            wiki_files.append({"file": str(md.relative_to(source)), "ok": r2.returncode == 0})
            print(("ok   " if r2.returncode == 0 else "FAIL ") + str(md.relative_to(source)))
    ktx(["admin", "reindex"], project, env, log)
    status = ktx(["status"], project, env, log).stdout
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for name in STORED:
        p = project / name
        if p.is_dir():
            shutil.copytree(p, out / name)
        elif p.exists():
            shutil.copyfile(p, out / name)
    version = subprocess.run([str(NPM_BIN / "ktx"), "--version"], env=env, capture_output=True, text=True).stdout.strip()
    meta = {"state": state, "ktx_version": version, "models": MODELS, "embeddings": "sentence-transformers all-MiniLM-L6-v2 (384)", "enrichment": "llm",
            "started": t0.isoformat(timespec="seconds"), "finished": dt.datetime.now().isoformat(timespec="seconds"),
            "ingest_exit_code": r.returncode, "wiki_verbatim": wiki_files, "status": status}
    (out / "ingest_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    shutil.copyfile(log, out / "ingest.log")
    print(f"stored {out.relative_to(ROOT)}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("state", choices=["before", "with_context", "rot"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    build(a.state, a.force)


if __name__ == "__main__":
    main()
