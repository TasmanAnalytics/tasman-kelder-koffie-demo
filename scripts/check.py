"""Run the checks CI runs on a pull request, locally, with red and green output for recording.

    uv run python scripts/check.py --state rot --pr-body kelder-dbt/.pr/rot.md

1. Verified queries against the state's warehouse, compared with frozen expected results.
2. The context capture check on the files the change touches and the pull request body.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_context_capture as capture  # noqa: E402
import verified  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASES = {"rot": ("refs/tags/kelder/with-context", "refs/tags/kelder/rot"),
         "with_context": ("refs/tags/kelder/with-context~1", "refs/tags/kelder/with-context"),
         "before": ("refs/tags/kelder/before-context~1", "refs/tags/kelder/before-context"),
         "head": ("origin/main", "HEAD")}
COLOR = sys.stdout.isatty() or os.environ.get("FORCE_COLOR")
G, R, B, D, X = (("\033[32m", "\033[31m", "\033[1m", "\033[2m", "\033[0m") if COLOR else ("", "", "", "", ""))


def changed_files(base: str, head: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", base, head], cwd=ROOT, check=True, capture_output=True, text=True)
    return [l for l in out.stdout.splitlines() if l]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True, choices=sorted(BASES))
    ap.add_argument("--pr-body", required=True)
    ap.add_argument("--base", help="override the base ref for the changed-files diff")
    ap.add_argument("--head", help="override the head ref")
    ap.add_argument("--db", help="override the warehouse file")
    ap.add_argument("--project", help="override the extracted kelder-dbt directory")
    a = ap.parse_args()
    base, head = BASES[a.state]
    base, head = a.base or base, a.head or head
    db = Path(a.db) if a.db else ROOT / "data" / "warehouse" / f"kelder_{a.state}.duckdb"
    project = Path(a.project) if a.project else ROOT / "build" / a.state / "kelder-dbt"
    if not db.exists() or not project.exists():
        sys.exit(f"{db.name} or build/{a.state} missing: run `make build STATE={a.state}` first")

    print(f"{B}Verified queries{X} {D}({a.state} warehouse vs pinned answers){X}")
    results = verified.check_state(db, project)
    for qid, ok, problems in results:
        print(f"  {G + 'PASS' if ok else R + 'FAIL'}{X}  {qid}")
        for p in problems[:6]:
            print(f"        {R}{p}{X}")
    v_ok = all(ok for _, ok, _ in results) if results else None
    if not results:
        print(f"  {D}no verified queries in this state{X}")

    print(f"\n{B}Context capture check{X} {D}({base.split('/')[-1]}..{head.split('/')[-1]}){X}")
    changed = changed_files(base, head)
    body_path = Path(a.pr_body) if Path(a.pr_body).is_absolute() else ROOT / a.pr_body
    if not body_path.exists() and a.pr_body.startswith("kelder-dbt/"):
        body_path = project.parent / a.pr_body  # the body is committed with the state's kelder-dbt/
    body = body_path.read_text()
    c_ok, msgs = capture.evaluate(changed, body, v_ok)
    for m in msgs:
        print(f"  {m}")
    print(f"  {G + 'PASS' if c_ok else R + 'FAIL'}{X}")

    all_ok = (v_ok is not False) and c_ok
    print(f"\n{B}{G + 'All checks passed' if all_ok else R + 'Checks failed'}{X}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
