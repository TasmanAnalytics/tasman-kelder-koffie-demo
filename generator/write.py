"""Deterministic Parquet output: data/raw/<system>/<table>.parquet."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def write_table(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df.reset_index(drop=True), preserve_index=False)
    # drop pandas metadata so the bytes depend only on the data and the schema
    table = table.replace_schema_metadata(None)
    pq.write_table(table, path, compression="zstd", compression_level=3, write_statistics=True, row_group_size=250_000)


def write_system(root: Path, system: str, tables: dict[str, pd.DataFrame]) -> dict[str, str]:
    hashes = {}
    for name in sorted(tables):
        p = root / system / f"{name}.parquet"
        write_table(tables[name], p)
        hashes[f"{system}/{name}.parquet"] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes
