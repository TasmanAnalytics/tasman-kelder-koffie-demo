"""Freeze expected verified-query results from the with-context state.

Refuses unless every truth test passes. Never re-freeze to make a failing check pass: freeze only
when Thomas asks, and every freeze is logged in BUILD_LOG.md.

    uv run python scripts/freeze_verified.py --approved-by "Thomas, <date/time>"
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_state  # noqa: E402
import verified  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--approved-by", required=True, help="who asked for this freeze, and when")
    a = ap.parse_args()
    db = build_state.build("with_context", quiet=True)
    t = subprocess.run([sys.executable, "-m", "pytest", "tests/truth", "-q"], cwd=ROOT)
    if t.returncode:
        sys.exit("truth tests fail: refusing to freeze verified results")
    project = ROOT / "build" / "with_context" / "kelder-dbt"
    ref = subprocess.run(["git", "rev-parse", "refs/tags/kelder/with-context"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    verified.EXPECTED.mkdir(parents=True, exist_ok=True)
    ids = []
    for q in verified.load_queries(project):
        res = verified.run_query(db, q["sql"])
        res.update(id=q["id"], state="with_context", ref=ref)
        (verified.EXPECTED / f"{q['id']}.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
        ids.append(q["id"])
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(ROOT / "BUILD_LOG.md", "a") as f:
        f.write(f"\n- {stamp} Froze verified results for {len(ids)} queries from kelder/with-context ({ref[:10]}). Approved by: {a.approved_by}.\n")
    print(f"froze {len(ids)} expected results: {', '.join(ids)}")


if __name__ == "__main__":
    main()
