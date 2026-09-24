"""Shared helpers: configuration, seeded random streams, local time arithmetic, profile samplers.

Internally the generator keeps time as int64 seconds of *local Europe/Amsterdam wall time*
("local seconds", as if the wall clock were UTC). That keeps "05:00 local" stable across
daylight saving changes. Conversion to real UTC happens only when rendering source systems.
"""

from __future__ import annotations

import datetime as dt
import zlib
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
DAY = 86_400
HOUR = 3_600
NEVER = np.iinfo(np.int64).max // 4  # sentinel for "no time"


def _stringify_dates(x):
    if isinstance(x, dict):
        return {str(k) if isinstance(k, (dt.date, dt.datetime)) else k: _stringify_dates(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_stringify_dates(v) for v in x]
    if isinstance(x, (dt.date, dt.datetime)):
        return str(x)
    return x


def load_config(path: Path | str = CONFIG_PATH) -> dict:
    """Load config.yaml. Dates come back as ISO strings so they parse the same everywhere."""
    with open(path) as f:
        return _stringify_dates(yaml.safe_load(f))


def rng_for(seed: int, name: str) -> np.random.Generator:
    """One independent, stable random stream per module or purpose."""
    return np.random.default_rng([seed, zlib.crc32(name.encode())])


# ---------------------------------------------------------------------------
# Local time <-> UTC for Europe/Amsterdam
# ---------------------------------------------------------------------------


def _last_sunday(year: int, month: int) -> dt.date:
    d = dt.date(year, month, 31)
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)


@lru_cache(maxsize=None)
def _dst_bounds(year: int) -> tuple[int, int, int, int]:
    """(start_local, end_local, start_utc, end_utc) in seconds for the given year."""
    s = _last_sunday(year, 3)
    e = _last_sunday(year, 10)
    s_utc = int(dt.datetime(s.year, s.month, s.day, 1, tzinfo=dt.timezone.utc).timestamp())
    e_utc = int(dt.datetime(e.year, e.month, e.day, 1, tzinfo=dt.timezone.utc).timestamp())
    # local wall times: DST starts at 01:00 UTC, when 02:00 CET jumps to 03:00 CEST;
    # it ends at 01:00 UTC, when 03:00 CEST falls back to 02:00 CET.
    return s_utc + 2 * HOUR, e_utc + 2 * HOUR, s_utc, e_utc


def _year_of(sec: np.ndarray) -> np.ndarray:
    return sec.astype("datetime64[s]").astype("datetime64[Y]").astype(int) + 1970


def local_to_utc(local: np.ndarray) -> np.ndarray:
    """Local wall seconds to UTC epoch seconds. The repeated October hour resolves to CEST."""
    local = np.asarray(local, dtype=np.int64)
    out = local - HOUR
    years = _year_of(local)
    for y in np.unique(years):
        s_loc, e_loc, _, _ = _dst_bounds(int(y))
        m = (years == y) & (local >= s_loc) & (local < e_loc)
        out[m] = local[m] - 2 * HOUR
    return out


def utc_to_local(utc: np.ndarray) -> np.ndarray:
    utc = np.asarray(utc, dtype=np.int64)
    out = utc + HOUR
    years = _year_of(utc)
    for y in np.unique(years):
        _, _, s_utc, e_utc = _dst_bounds(int(y))
        m = (years == y) & (utc >= s_utc) & (utc < e_utc)
        out[m] = utc[m] + 2 * HOUR
    return out


def fix_nonexistent(local: np.ndarray) -> np.ndarray:
    """Move local times inside the skipped spring hour forward by one hour."""
    local = np.asarray(local, dtype=np.int64).copy()
    years = _year_of(local)
    for y in np.unique(years):
        s_loc, _, _, _ = _dst_bounds(int(y))
        m = (years == y) & (local >= s_loc - HOUR) & (local < s_loc)  # 02:00 to 03:00 local
        local[m] += HOUR
    return local


# ---------------------------------------------------------------------------
# Calendar helpers on local seconds
# ---------------------------------------------------------------------------


def ts(s: str) -> int:
    """Parse 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM[:SS]' as local (or naive) seconds."""
    s = str(s).strip()
    if len(s) == 10:
        s = s + "T00:00:00"
    s = s.replace(" ", "T")
    if len(s) == 16:
        s = s + ":00"
    return int(np.datetime64(s, "s").astype(np.int64))


def month_start(year: int, month: int) -> int:
    return int(np.datetime64(f"{year:04d}-{month:02d}-01T00:00:00", "s").astype(np.int64))


def month_key(sec) -> np.ndarray:
    """'YYYY-MM' strings for local seconds."""
    return np.datetime_as_string(np.asarray(sec, dtype=np.int64).astype("datetime64[s]").astype("datetime64[M]"))


def month_index(sec) -> np.ndarray:
    """Months since 1970-01 for local seconds."""
    return np.asarray(sec, dtype=np.int64).astype("datetime64[s]").astype("datetime64[M]").astype(np.int64)


def month_start_from_index(idx) -> np.ndarray:
    return np.asarray(idx, dtype=np.int64).astype("datetime64[M]").astype("datetime64[s]").astype(np.int64)


def add_months(sec, n) -> np.ndarray:
    """Same day-of-month n months later (clipped to month end), time of day kept."""
    sec = np.asarray(sec, dtype=np.int64)
    n = np.asarray(n, dtype=np.int64)
    day = sec // DAY
    tod = sec - day * DAY
    d64 = day.astype("datetime64[D]")
    m = d64.astype("datetime64[M]")
    dom = (d64 - m).astype(np.int64)
    m2 = m + n.astype("timedelta64[M]")
    days_in_m2 = ((m2 + np.timedelta64(1, "M")).astype("datetime64[D]") - m2.astype("datetime64[D]")).astype(np.int64)
    dom2 = np.minimum(dom, days_in_m2 - 1)
    return (m2.astype("datetime64[D]").astype(np.int64) + dom2) * DAY + tod


def iso_dow(sec) -> np.ndarray:
    """0 = Monday .. 6 = Sunday."""
    day = np.asarray(sec, dtype=np.int64) // DAY
    return (day + 3) % 7  # 1970-01-01 was a Thursday


def at_time_of_day(sec, hh: int, mm: int = 0) -> np.ndarray:
    day = np.asarray(sec, dtype=np.int64) // DAY
    return day * DAY + hh * HOUR + mm * 60


def next_time_of_day(sec, hh: int, mm: int = 0) -> np.ndarray:
    """First instant >= sec at the given local time of day."""
    sec = np.asarray(sec, dtype=np.int64)
    t = at_time_of_day(sec, hh, mm)
    return np.where(t >= sec, t, t + DAY)


def to_datetime64(sec) -> np.ndarray:
    return np.asarray(sec, dtype=np.int64).astype("datetime64[s]")


# ---------------------------------------------------------------------------
# Profile sampling
# ---------------------------------------------------------------------------


class ProfileSampler:
    """Sample local times in [a, b) following a day-of-week and hour-of-day profile."""

    def __init__(self, hour_weights, dow_weights):
        hw = np.asarray(hour_weights, dtype=float)
        self.hour_p = hw / hw.sum()
        self.hour_cdf = np.cumsum(self.hour_p)
        dw = np.asarray(dow_weights, dtype=float)
        self.dow_accept = dw / dw.max()

    def sample(self, rng: np.random.Generator, a, b, day_boost=None) -> np.ndarray:
        """a, b arrays of local seconds (b > a). day_boost: optional callable(day_sec, idx) -> weight multiplier."""
        a = np.asarray(a, dtype=np.int64)
        b = np.asarray(b, dtype=np.int64)
        n = len(a)
        out = np.full(n, -1, dtype=np.int64)
        todo = np.arange(n)
        d0 = a // DAY
        nd = (b - 1) // DAY - d0 + 1
        for _ in range(60):
            if len(todo) == 0:
                break
            k = len(todo)
            day = d0[todo] + np.floor(rng.random(k) * nd[todo]).astype(np.int64)
            acc = self.dow_accept[(day + 3) % 7]
            if day_boost is not None:
                acc = acc * day_boost(day * DAY, todo)
            u = rng.random(k)
            hour = np.searchsorted(self.hour_cdf, rng.random(k), side="right")
            hour = np.minimum(hour, 23)
            t = day * DAY + hour * HOUR + np.floor(rng.random(k) * HOUR).astype(np.int64)
            ok = (u < acc) & (t >= a[todo]) & (t < b[todo])
            out[todo[ok]] = t[ok]
            todo = todo[~ok]
        if len(todo):
            span = b[todo] - a[todo]
            out[todo] = a[todo] + np.floor(rng.random(len(todo)) * span).astype(np.int64)
        return fix_nonexistent(out)


def weighted_choice_without_replacement(rng: np.random.Generator, weights: np.ndarray, k: int) -> np.ndarray:
    """Indices of k items sampled without replacement, probability proportional to weight.

    Uses the Efraimidis-Spirakis exponential-key method: deterministic for a given stream.
    """
    weights = np.asarray(weights, dtype=float)
    n = len(weights)
    if k <= 0 or n == 0:
        return np.empty(0, dtype=np.int64)
    if k > (weights > 0).sum():
        raise ValueError(f"cannot draw {k} from {int((weights > 0).sum())} positive-weight items")
    keys = np.full(n, np.inf)
    pos = weights > 0
    keys[pos] = rng.exponential(size=pos.sum()) / weights[pos]
    idx = np.argpartition(keys, k - 1)[:k]
    return np.sort(idx)


def choice_from_dict(rng: np.random.Generator, d: dict, n: int):
    keys = list(d.keys())
    p = np.array([d[k] for k in keys], dtype=float)
    p = p / p.sum()
    idx = rng.choice(len(keys), size=n, p=p)
    return np.array(keys, dtype=object)[idx], idx
