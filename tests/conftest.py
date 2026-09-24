"""Shared fixtures. Tests run against data/ produced by `make generate` (and warehouse states for dbt-level tests)."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("KELDER_DATA", ROOT / "data"))
RAW = DATA / "raw"
TRUTH = DATA / "truth" / "kelder_truth.duckdb"
WAREHOUSE = DATA / "warehouse"


def raw_path(system: str, table: str) -> str:
    return str(RAW / system / f"{table}.parquet")


@pytest.fixture(scope="session")
def raw():
    if not (RAW / "shopify" / "orders.parquet").exists():
        pytest.fail("data/raw is missing: run `make generate` first")
    con = duckdb.connect()
    con.execute("set TimeZone = 'UTC'")
    for system in ("shopify", "recharge", "klaviyo", "ads"):
        con.execute(f"create schema {system}")
        for p in sorted((RAW / system).glob("*.parquet")):
            con.execute(f"create view {system}.{p.stem} as select * from read_parquet('{p}')")
    yield con
    con.close()


@pytest.fixture(scope="session")
def truth():
    if not TRUTH.exists():
        pytest.fail("truth DB is missing: run `make generate` first")
    con = duckdb.connect(str(TRUTH), read_only=True)
    yield con
    con.close()


def warehouse(state: str):
    p = WAREHOUSE / f"kelder_{state}.duckdb"
    if not p.exists():
        pytest.skip(f"{p.name} not built: run `make build STATE={state}`")
    return duckdb.connect(str(p), read_only=True)
