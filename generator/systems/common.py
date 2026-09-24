"""Helpers shared by the source-system renderers."""

from __future__ import annotations

import json
import re
import unicodedata

import numpy as np
import pandas as pd

from ..common import NEVER, local_to_utc


def ids(rng: np.random.Generator, n: int, base: int, max_gap: int = 97) -> np.ndarray:
    """Increasing, gappy integer ids like a real platform's."""
    if n == 0:
        return np.empty(0, dtype=np.int64)
    return base + np.cumsum(rng.integers(1, max_gap, n)).astype(np.int64)


def hex_ids(rng: np.random.Generator, n: int, prefix: str = "", length: int = 26) -> np.ndarray:
    """Opaque string ids (Klaviyo style). Unique by construction: a sequence mixed with random characters."""
    alphabet = np.array(list("0123456789ABCDEFGHJKMNPQRSTVWXYZ"))
    seq = np.arange(n, dtype=np.int64)
    head = np.array([np.base_repr(int(s), 32).rjust(6, "0") for s in seq])
    tail = alphabet[rng.integers(0, len(alphabet), (n, length - 6))]
    tail = np.array(["".join(r) for r in tail])
    return np.char.add(np.char.add(prefix, head), tail)


def utc(local_seconds) -> pd.Series:
    """Local wall seconds -> tz-aware UTC timestamps; NEVER becomes NaT."""
    a = np.asarray(local_seconds, dtype=np.int64)
    never = a >= NEVER // 2
    u = local_to_utc(np.where(never, 0, a))
    out = pd.to_datetime(u, unit="s", utc=True)
    out = pd.Series(out)
    out[never] = pd.NaT
    return out.astype("datetime64[us, UTC]")


def utc_from_utc_seconds(u) -> pd.Series:
    a = np.asarray(u, dtype=np.int64)
    never = a >= NEVER // 2
    out = pd.Series(pd.to_datetime(np.where(never, 0, a), unit="s", utc=True))
    out[never] = pd.NaT
    return out.astype("datetime64[us, UTC]")


def fivetran(df: pd.DataFrame, synced, deleted=False) -> pd.DataFrame:
    df = df.copy()
    df["_fivetran_synced"] = synced if isinstance(synced, pd.Series) else pd.Series([synced] * len(df), index=df.index)
    df["_fivetran_synced"] = pd.to_datetime(df["_fivetran_synced"], utc=True).astype("datetime64[us, UTC]")
    df["_fivetran_deleted"] = deleted
    return df


def synced_after(ts_col: pd.Series, rng: np.random.Generator, cap: pd.Timestamp, lo_min=5, hi_min=180) -> pd.Series:
    """A sync time shortly after the row last changed, capped at the extract cutoff."""
    off = pd.to_timedelta(rng.integers(lo_min * 60, hi_min * 60, len(ts_col)), unit="s")
    s = ts_col + off.values
    s = s.where(s < cap, cap)
    return s.fillna(cap)


def to_json(objs) -> list[str | None]:
    return [None if o is None else json.dumps(o, ensure_ascii=False, sort_keys=True) for o in objs]


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]+", "", s)
