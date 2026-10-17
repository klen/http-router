PACKAGE ?= http_router

.PHONY: all test t mypy ruff clean cyt compile version minor patch major

all:
	uv sync --all-extras
	uv run pre-commit install --hook-type pre-push

LATEST_BENCHMARK = $(shell ls -t .benchmarks/*/*.json 2>/dev/null | head -1)

test t:
	uv run pytest tests.py --benchmark-autosave --benchmark-compare=$(LATEST_BENCHMARK)

mypy:
	uv run mypy $(PACKAGE)

ruff:
	uv run ruff check $(PACKAGE)

clean:
	rm -rf build/ dist/ *.egg-info $(PACKAGE)/*.c $(PACKAGE)/*.so $(PACKAGE)/*.html
	find . -name "*.py[co]" -delete
	find . -name "*.orig" -delete
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

$(PACKAGE)/%.c: $(PACKAGE)/%.py $(PACKAGE)/%.pxd
	uv run cython -a $<

cyt: $(PACKAGE)/router.c $(PACKAGE)/routes.c

compile: cyt
	uv run python setup.py build_ext --inplace

VERSION ?= minor

version:
	uv run bump2version $(VERSION)
	git checkout master
	git pull
	git merge develop
	git checkout develop
	git push origin develop master
	git push --tags

minor:
	make version VERSION=minor

patch:
	make version VERSION=patch

major:
	make version VERSION=major
