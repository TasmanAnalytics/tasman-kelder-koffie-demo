"""Context capture check: a change that can move a metric must say so in the pull request.

    python scripts/check_context_capture.py --changed <file with one path per line> --pr-body <file>

Rules (BUILD_BRIEF.md 6.6):
- If nothing under kelder-dbt/models/marts/metrics_*, kelder-dbt/models/**/fct_subscription* or
  the semantic layer definitions changed, pass.
- Otherwise exactly one metric-impact option must be ticked.
- "No user-visible metrics move" is tested, not trusted: every verified query must still match.
- "Metrics move: ..." requires an edit to metric_changelog.csv or business_events.csv.
- "Decision record added or superseded (link)" requires a link to a decision record path.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

WATCHED = [
    "kelder-dbt/models/marts/metrics_*",
    "kelder-dbt/models/*fct_subscription*",
    "kelder-dbt/models/**/fct_subscription*",
    "kelder-dbt/semantic-layer/*",
    "kelder-dbt/semantic-layer/**",
]
NO_MOVE = "No user-visible metrics move"
MOVE_CHANGELOG = "Metrics move: metric_changelog updated"
MOVE_EVENTS = "Metrics move: business_events row added"
DECISION = "Decision record added or superseded (link)"
IMPACT = [NO_MOVE, MOVE_CHANGELOG, MOVE_EVENTS]
CONTEXT_EDITS = ["kelder-dbt/seeds/context/metric_changelog.csv", "kelder-dbt/seeds/context/business_events.csv"]
DECISION_LINK = re.compile(r"context/decisions/\d{4}-[\w-]+\.md")


def ticked(body: str) -> dict[str, bool]:
    out = {}
    for opt in IMPACT + [DECISION]:
        m = re.search(r"^\s*[-*]\s*\[([ xX])\]\s*" + re.escape(opt), body, flags=re.M)
        out[opt] = bool(m and m.group(1).lower() == "x")
    return out


def watched(changed: list[str]) -> list[str]:
    return [f for f in changed if any(fnmatch.fnmatch(f, p) for p in WATCHED)]


def evaluate(changed: list[str], body: str, verified_ok: bool | None) -> tuple[bool, list[str]]:
    """Returns (passed, messages). verified_ok is the verified-query result, or None if not run."""
    msgs = []
    hits = watched(changed)
    if not hits:
        return True, ["no metric or subscription models changed: capture check not required"]
    msgs.append("metric-bearing files changed: " + ", ".join(hits))
    t = ticked(body)
    n = sum(t[o] for o in IMPACT)
    if n != 1:
        msgs.append(f"exactly one metric-impact option must be ticked; found {n}")
        return False, msgs
    ok = True
    if t[NO_MOVE]:
        if verified_ok is None:
            msgs.append("'No user-visible metrics move' ticked: verified queries were not run")
            ok = False
        elif not verified_ok:
            msgs.append("'No user-visible metrics move' ticked, but verified queries changed")
            ok = False
        else:
            msgs.append("'No user-visible metrics move' ticked and every verified query still matches")
    else:
        if not any(f in changed for f in CONTEXT_EDITS):
            msgs.append("a 'Metrics move' option is ticked, but neither metric_changelog.csv nor business_events.csv changed")
            ok = False
        else:
            msgs.append("metrics move and the context tables were updated")
    if t[DECISION] and not DECISION_LINK.search(body):
        msgs.append("decision record option ticked, but no link to context/decisions/NNNN-*.md in the body")
        ok = False
    return ok, msgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed", required=True, help="file listing changed paths, one per line")
    ap.add_argument("--pr-body", required=True)
    ap.add_argument("--verified-ok", choices=["yes", "no", "unknown"], default="unknown")
    a = ap.parse_args()
    changed = [l.strip() for l in Path(a.changed).read_text().splitlines() if l.strip()]
    body = Path(a.pr_body).read_text()
    vo = {"yes": True, "no": False, "unknown": None}[a.verified_ok]
    ok, msgs = evaluate(changed, body, vo)
    for m in msgs:
        print(m)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
