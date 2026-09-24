"""Run verified queries against a warehouse state and compare them with frozen expected results.

Expected results live in tests/verified/expected/<id>.json, never in kelder-dbt/ or a workspace.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import os

import duckdb
import yaml

ROOT = Path(__file__).resolve().parent.parent
# KELDER_VERIFIED_EXPECTED lets tests point at a scratch copy; the pinned answers live in tests/verified/expected
EXPECTED = Path(os.environ.get("KELDER_VERIFIED_EXPECTED", ROOT / "tests" / "verified" / "expected"))


def load_queries(project: Path) -> list[dict]:
    p = project / "context" / "verified_queries.yml"
    if not p.exists():
        return []
    return yaml.safe_load(p.read_text())["queries"]


def run_query(db: Path, sql: str) -> dict:
    con = duckdb.connect(str(db), read_only=True)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = [[_plain(v) for v in r] for r in cur.fetchall()]
    finally:
        con.close()
    return {"columns": cols, "rows": rows}


def _plain(v):
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        return None if math.isnan(v) else v
    try:
        return float(v)
    except (TypeError, ValueError):
        return str(v)


def same(a, b, tol=1e-9) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
        except (TypeError, ValueError):
            return False
    return a == b


def compare(actual: dict, expected: dict) -> list[str]:
    problems = []
    if actual["columns"] != expected["columns"]:
        problems.append(f"columns differ: {actual['columns']} vs expected {expected['columns']}")
        return problems
    if len(actual["rows"]) != len(expected["rows"]):
        problems.append(f"{len(actual['rows'])} rows, expected {len(expected['rows'])}")
        return problems
    for i, (ra, re_) in enumerate(zip(actual["rows"], expected["rows"])):
        for c, va, ve in zip(actual["columns"], ra, re_):
            if not same(va, ve):
                problems.append(f"row {i + 1} {c}: {va!r}, expected {ve!r}")
    return problems


def check_state(db: Path, project: Path) -> list[tuple[str, bool, list[str]]]:
    out = []
    for q in load_queries(project):
        exp_path = EXPECTED / f"{q['id']}.json"
        if not exp_path.exists():
            out.append((q["id"], False, ["no frozen expected result (run make freeze-verified when approved)"]))
            continue
        expected = json.loads(exp_path.read_text())
        try:
            actual = run_query(db, q["sql"])
        except duckdb.Error as e:
            out.append((q["id"], False, [f"query failed: {e}"]))
            continue
        problems = compare(actual, expected)
        out.append((q["id"], not problems, problems))
    return out
