"""Load data/raw/<system>/<table>.parquet into data/warehouse/kelder_raw.duckdb, in the shape Fivetran produces.

Schemas raw_shopify, raw_recharge, raw_klaviyo, raw_ads. Timestamps are TIMESTAMPTZ (UTC),
JSON columns are JSON. The truth database is never loaded here.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
JSON_COLUMNS = {
    ("shopify", "orders"): ["discount_codes"],
    ("shopify", "subscription_contracts"): ["custom_attributes"],
    ("shopify", "subscription_contract_events"): ["detail"],
    ("recharge", "subscriptions"): ["properties"],
    ("recharge", "subscription_events"): ["payload"],
}


def load(raw_dir: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.duckdb")
    tmp.unlink(missing_ok=True)
    con = duckdb.connect(str(tmp))
    con.execute("set TimeZone = 'UTC'")
    for system_dir in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        system = system_dir.name
        schema = f"raw_{system}"
        con.execute(f"create schema {schema}")
        for pq in sorted(system_dir.glob("*.parquet")):
            table = pq.stem
            cols = con.execute(f"describe select * from read_parquet('{pq}')").fetchall()
            select = []
            for name, typ, *_ in cols:
                if name in JSON_COLUMNS.get((system, table), []):
                    select.append(f"cast({name} as json) as {name}")
                elif typ.startswith("TIMESTAMP"):
                    select.append(f"cast({name} as timestamptz) as {name}")
                else:
                    select.append(name)
            con.execute(f"create table {schema}.{table} as select {', '.join(select)} from read_parquet('{pq}')")
    con.execute("checkpoint")
    con.close()
    tmp.replace(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out", default=str(ROOT / "data" / "warehouse" / "kelder_raw.duckdb"))
    a = ap.parse_args()
    load(Path(a.raw), Path(a.out))
    print(f"loaded {a.out}")


if __name__ == "__main__":
    main()
