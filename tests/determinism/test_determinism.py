"""The same seed produces byte-identical raw files."""

import hashlib
import json

from conftest import RAW

from generator.generate import run


def test_same_seed_same_bytes(tmp_path):
    fresh = run(tmp_path / "run1", verbose=False)["hashes"]
    stored_path = RAW / "hashes.json"
    if stored_path.exists():
        reference = json.loads(stored_path.read_text())
    else:
        reference = run(tmp_path / "run2", verbose=False)["hashes"]
    assert fresh == reference
    for rel, h in fresh.items():
        assert hashlib.sha256((tmp_path / "run1" / "raw" / rel).read_bytes()).hexdigest() == h
