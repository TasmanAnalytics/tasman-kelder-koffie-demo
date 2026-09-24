"""Generate the Kelder world, render it through the source systems, apply incidents, write Parquet and the truth DB.

Usage: uv run python -m generator.generate [--out data]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from . import incidents, report, truth
from .calibrate import solve
from .catalogue import build_catalogue
from .common import ROOT, load_config, rng_for, ts
from .systems import ads, klaviyo, recharge, shopify
from .systems.common import utc
from .world_commerce import Commerce
from .write import write_system


def run(out: Path, verbose: bool = True) -> dict:
    t0 = time.time()
    log = (lambda *a: print(f"[{time.time() - t0:6.1f}s]", *a, flush=True)) if verbose else (lambda *a: None)
    cfg = load_config()
    cat = build_catalogue(cfg)
    world, calib = solve(cfg, cat, verbose=False)
    log("world", {k: (round(v, 5) if isinstance(v, float) else v) for k, v in calib.items()})
    com = Commerce(cfg, cat, world).run()
    log("commerce", len(com.orders), "orders")
    reg = shopify.Registry()
    shop = shopify.render(cfg, cat, world, com, reg)
    log("shopify rendered")
    rc_clean, internal = recharge.render(cfg, cat, world, com, reg)
    man = incidents.Manifest()
    rc = incidents.recharge_migration(cfg, rc_clean, internal, world, reg, man)
    rc = recharge.finalise(rc, utc([ts(cfg["dates"]["cutoff_local"])])[0], rng_for(cfg["seed"], "recharge.sync"))
    log("recharge rendered with migration incident")
    kl = klaviyo.render(cfg, com, reg)
    kl_clean_events = kl["events"]
    kl["events"] = incidents.klaviyo_outage(cfg, kl["events"], man)
    log("klaviyo rendered with outage incident")
    ad = ads.render(cfg, com)
    incidents.log_billing_freeze(cfg, world, man)
    incidents.log_strike(cfg, com, reg, man)
    manifest = man.frame()
    raw = out / "raw"
    hashes = {}
    for system, tables in (("shopify", shop), ("recharge", rc), ("klaviyo", kl), ("ads", ad)):
        hashes.update(write_system(raw, system, tables))
    log("parquet written", len(hashes), "files")
    tt = truth.compute(cfg, world, com, kl_clean_events, kl["events"], reg, internal, manifest)
    tt["targets"] = truth.targets_table(cfg, tt["metrics_monthly"], int(world.subs.artefact.sum()), int(world.subs.queued.sum()))
    tt["calibration"] = __import__("pandas").DataFrame([{k: (float(v) if isinstance(v, (int, float)) else str(v)) for k, v in calib.items()}])
    truth.write(out / "truth" / "kelder_truth.duckdb", tt)
    log("truth written")
    (out / "raw" / "hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True))
    report.write(out / "profile_report.md", cfg, tt, shop, rc, kl, ad, manifest)
    log("profile report written")
    failed = tt["targets"][~tt["targets"].passed]
    if len(failed):
        log("TARGETS FAILED:\n" + failed.to_string())
    return dict(hashes=hashes, targets=tt["targets"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data"))
    a = ap.parse_args()
    run(Path(a.out))


if __name__ == "__main__":
    main()
