"""Build one warehouse state from a git reference.

    uv run python scripts/build_state.py before|with_context|rot [--ref <git ref>|WORKTREE]

Extracts kelder-dbt/ at the reference (git archive), copies kelder_raw.duckdb to the state's
warehouse file and runs `dbt build` there. The generator, loader and tests always come from the
current checkout, so states stay reproducible while the tooling evolves.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = ROOT / "data" / "warehouse"
BUILD = ROOT / "build"
REFS = {"before": "refs/tags/kelder/before-context", "with_context": "refs/tags/kelder/with-context",
        "rot": "refs/tags/kelder/rot", "head": "HEAD"}


def extract(ref: str, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    if ref == "WORKTREE":
        shutil.copytree(ROOT / "kelder-dbt", dest / "kelder-dbt",
                        ignore=shutil.ignore_patterns("target", "logs", "dbt_packages", ".ktx", ".user.yml"))
    else:
        data = subprocess.run(["git", "archive", "--format=tar", ref, "kelder-dbt"], cwd=ROOT, check=True,
                              capture_output=True).stdout
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(dest, filter="data")
    return dest / "kelder-dbt"


def build(state: str, ref: str | None = None, quiet: bool = False) -> Path:
    ref = ref or REFS[state]
    project = extract(ref, BUILD / state)
    raw = WAREHOUSE / "kelder_raw.duckdb"
    if not raw.exists():
        sys.exit("kelder_raw.duckdb missing: run `make load` first")
    target_db = WAREHOUSE / f"kelder_{state}.duckdb"
    target_db.unlink(missing_ok=True)
    shutil.copyfile(raw, target_db)
    env = dict(os.environ, KELDER_DUCKDB_PATH=str(target_db), DBT_PROFILES_DIR=str(project))
    dbt = [str(Path(sys.executable).parent / "dbt"), "build", "--project-dir", str(project),
           "--target-path", str(BUILD / f"{state}-target"), "--log-path", str(BUILD / f"{state}-logs")]
    if quiet:
        dbt.append("--quiet")
    print(f"building {state} from {ref} -> {target_db.name}", flush=True)
    r = subprocess.run(dbt, env=env, cwd=project)
    if r.returncode:
        sys.exit(f"dbt build failed for {state} ({ref})")
    return target_db


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("state", choices=sorted(REFS))
    ap.add_argument("--ref", default=None, help="git ref, or WORKTREE for the working tree's kelder-dbt/")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    build(a.state, a.ref, a.quiet)


if __name__ == "__main__":
    main()
