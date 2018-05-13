SEGMENTS_DIR=home/.local/opt/custom_segments
PYTHON_VENV=python3 -m venv
VIRTUALENV_PYTHON=./virtualenv/bin/python3
VIRTUALENV_PIP=./virtualenv/bin/python3 -m pip
VIRTUALENV_MYPY=./virtualenv/bin/python3 -m mypy
VIRTUALENV_PYTEST=./virtualenv/bin/python3 -m pytest -v


.PHONY: test lint

all: lint test

virtualenv:
	@echo Building virtualenv
	@$(PYTHON_VENV) virtualenv && \
		$(VIRTUALENV_PIP) install -r requirements.txt

lint: virtualenv
	@echo Running linter
	@MYPYPATH=mystubs:$(SEGMENTS_DIR) $(VIRTUALENV_MYPY) -m mypy -p segments

test: virtualenv
	@echo Running tests
	@PYTHONPATH=$(SEGMENTS_DIR) $(VIRTUALENV_PYTEST) tests

clean:
	@echo Cleaning sources
	rm -rf virtualenv

