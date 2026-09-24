# Kelder Coffee context layer demo. See README.md.
SHELL := /bin/bash
PY := uv run python
STATE ?= with_context
PR_BODY ?= kelder-dbt/.pr/rot.md
WORKSPACE ?= installed
PROMPTS ?= all
N ?= 3

.PHONY: index all generate load build build-all test test-data test-truth test-dbt check freeze-verified charts workspaces leak-check trials summary context-files clean

all: generate load build-all test charts index

generate:
	$(PY) -m generator.generate

load:
	$(PY) -m loader.load_raw

build:
	$(PY) scripts/build_state.py $(STATE) --quiet

build-all:
	$(PY) scripts/build_state.py before --quiet
	$(PY) scripts/build_state.py with_context --quiet
	$(PY) scripts/build_state.py rot --quiet

# dbt tests run inside `make build`; this runs everything else
test: test-data test-truth

test-data:
	uv run pytest tests/targets tests/realism tests/incidents tests/determinism -q

test-truth:
	uv run pytest tests/truth tests/verified -q

check:
	$(PY) scripts/check.py --state $(STATE) --pr-body $(PR_BODY)

freeze-verified:
	$(PY) scripts/freeze_verified.py --approved-by "$(APPROVED_BY)"

charts:
	$(PY) charts/render.py

workspaces:
	$(PY) scripts/make_workspace.py --all

leak-check:
	uv run pytest tests/leaks -q

trials:
	$(PY) scripts/run_trials.py --workspace $(WORKSPACE) --prompts $(PROMPTS) --n $(N)

summary:
	$(PY) scripts/summarise_trials.py

context-files:
	$(PY) scripts/render_changelog.py

clean:
	rm -rf build data/warehouse/kelder_{before,with_context,rot,dev}.duckdb

index:
	$(PY) scripts/render_index.py
