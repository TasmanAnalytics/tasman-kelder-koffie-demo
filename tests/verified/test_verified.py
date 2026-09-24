"""Verified queries against built states, and the context capture check (brief 6.4 to 6.6)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_context_capture as capture  # noqa: E402
import verified  # noqa: E402

TEMPLATE = (ROOT / ".github" / "pull_request_template.md").read_text()
METRIC_FILE = "kelder-dbt/models/marts/metrics_subscriber_churn_monthly.sql"


def _frozen():
    return sorted(verified.EXPECTED.glob("*.json"))


def _results(state):
    db = ROOT / "data" / "warehouse" / f"kelder_{state}.duckdb"
    project = ROOT / "build" / state / "kelder-dbt"
    if not db.exists() or not project.exists():
        pytest.skip(f"{state} not built")
    return {qid: (ok, problems) for qid, ok, problems in verified.check_state(db, project)}


@pytest.fixture(autouse=True)
def _needs_frozen(request):
    if "frozen" in request.keywords and not _frozen():
        pytest.skip("verified results not frozen yet (make freeze-verified APPROVED_BY=...)")


@pytest.mark.frozen
def test_with_context_passes_every_verified_query():
    res = _results("with_context")
    assert len(res) == 7
    assert all(ok for ok, _ in res.values()), {k: p for k, (ok, p) in res.items() if not ok}


@pytest.mark.frozen
def test_rot_fails_exactly_the_like_for_like_query():
    res = _results("rot")
    failing = {k for k, (ok, _) in res.items() if not ok}
    assert failing == {"churn_yoy_like_for_like"}
    assert res["churn_march_2026"][0]


def test_verified_queries_file_has_no_expected_results():
    text = (ROOT / "build" / "with_context" / "kelder-dbt" / "context" / "verified_queries.yml")
    if not text.exists():
        pytest.skip("with_context not built")
    body = text.read_text()
    for number in ("0.0329", "0.0939", "0.0284", "0.0244", "1768", "24418"):
        assert number not in body


def _body(*ticks, what="Something."):
    b = TEMPLATE.replace("## What changed\n", f"## What changed\n\n{what}\n")
    for t in ticks:
        b = b.replace(f"- [ ] {t}", f"- [x] {t}")
    return b


def test_capture_passes_when_no_metric_models_change():
    ok, _ = capture.evaluate(["kelder-dbt/models/staging/shopify/stg_shopify__orders.sql"], _body(), None)
    assert ok


def test_capture_fails_the_rot_pull_request():
    rot_body = (ROOT / "build" / "rot" / "kelder-dbt" / ".pr" / "rot.md")
    body = rot_body.read_text() if rot_body.exists() else _body(what="Simplify churn model, consolidate v1 and v2 CTEs.")
    ok, msgs = capture.evaluate([METRIC_FILE, "kelder-dbt/.pr/rot.md"], body, False)
    assert not ok
    assert any("found 0" in m for m in msgs)


def test_capture_no_move_is_tested_not_trusted():
    assert capture.evaluate([METRIC_FILE], _body(capture.NO_MOVE), True)[0]
    assert not capture.evaluate([METRIC_FILE], _body(capture.NO_MOVE), False)[0]
    assert not capture.evaluate([METRIC_FILE], _body(capture.NO_MOVE), None)[0]


def test_capture_metrics_move_needs_a_context_edit_and_decision_link():
    body = _body(capture.MOVE_CHANGELOG)
    assert not capture.evaluate([METRIC_FILE], body, None)[0]
    assert capture.evaluate([METRIC_FILE, capture.CONTEXT_EDITS[0]], body, None)[0]
    with_decision = _body(capture.MOVE_CHANGELOG, capture.DECISION)
    assert not capture.evaluate([METRIC_FILE, capture.CONTEXT_EDITS[0]], with_decision, None)[0]
    linked = with_decision + "\nSee context/decisions/0010-something-new.md\n"
    assert capture.evaluate([METRIC_FILE, capture.CONTEXT_EDITS[0]], linked, None)[0]


def test_capture_requires_exactly_one_impact_option():
    two = _body(capture.NO_MOVE, capture.MOVE_EVENTS)
    assert not capture.evaluate([METRIC_FILE, capture.CONTEXT_EDITS[1]], two, True)[0]


def test_capture_watches_fct_subscription_models():
    assert capture.watched(["kelder-dbt/models/marts/fct_subscriptions.sql", "kelder-dbt/models/marts/fct_subscription_events.sql"])
    assert not capture.watched(["kelder-dbt/models/marts/fct_orders.sql"])
