.PHONY: help setup test access smoke release rebound-plan

UV ?= $(shell command -v uv 2>/dev/null || if [ -x "$$HOME/Library/Python/3.9/bin/uv" ]; then echo "$$HOME/Library/Python/3.9/bin/uv"; fi)
VENV_PYTHON ?= .venv/bin/python

ifneq ($(shell command -v $(UV) 2>/dev/null),)
RUN_PYTHON = $(UV) run python
RUN_PYTEST = $(UV) run pytest
RUN_INSPECT = $(UV) run --package cei-inspect python
RUNNER_NOTE = uv
else
RUN_PYTHON = $(VENV_PYTHON)
RUN_PYTEST = $(VENV_PYTHON) -m pytest
RUN_INSPECT = $(VENV_PYTHON)
RUNNER_NOTE = $(VENV_PYTHON)
endif

help:
	@echo "Available targets:"
	@echo "  make setup      Install/update the pinned uv environment"
	@echo "  make test       Run unit and task-construction tests (runner: $(RUNNER_NOTE))"
	@echo "  make access     Check official dataset accessibility"
	@echo "  make smoke      Run a 2-sample smoke on accessible Jenny tasks"
	@echo "  make release    Build release summary artifacts"
	@echo "  make rebound-plan RUN_ID=<id>  Plan targeted failed/parse reruns without model calls"

setup:
	$(UV) sync

test:
	$(RUN_PYTEST) tests -q

access:
	$(RUN_PYTHON) scripts/check_dataset_access.py

smoke:
	./scripts/run_jenny_religion.sh --limit 2 --models 1 --max-conn 2 --run-id smoke

release:
	$(RUN_PYTHON) scripts/build_release_artifacts.py

rebound-plan:
	@test -n "$(RUN_ID)" || (echo "Set RUN_ID=<inspect-run-id>" >&2; exit 1)
	$(RUN_PYTHON) scripts/plan_rebounds.py --run-id "$(RUN_ID)"
