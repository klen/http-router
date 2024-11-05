VIRTUAL_ENV 	?= env
PACKAGE 	?= http_router

all: $(VIRTUAL_ENV)

$(VIRTUAL_ENV): pyproject.toml
	@[ -d $(VIRTUAL_ENV) ] || python -m venv env
	@$(VIRTUAL_ENV)/bin/pip install -e .[tests,dev]
	@$(VIRTUAL_ENV)/bin/pre-commit install --hook-type pre-push
	@touch $(VIRTUAL_ENV)

VERSION	?= minor

.PHONY: version
version: $(VIRTUAL_ENV)
	bump2version $(VERSION)
	git checkout master
	git pull
	git merge develop
	git checkout develop
	git push origin develop master
	git push --tags

.PHONY: minor
minor:
	make version VERSION=minor

.PHONY: patch
patch:
	make version VERSION=patch

.PHONY: major
major:
	make version VERSION=major

.PHONY: clean
# target: clean - Display callable targets
clean:
	rm -rf build/ dist/ docs/_build *.egg-info $(PACKAGE)/*.c $(PACKAGE)/*.so $(PACKAGE)/*.html
	find $(CURDIR) -name "*.py[co]" -delete
	find $(CURDIR) -name "*.orig" -delete
	find $(CURDIR)/$(MODULE) -name "__pycache__" | xargs rm -rf

LATEST_BENCHMARK = $(shell ls -t .benchmarks/* | head -1 | head -c4)
test t: $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/pytest tests.py --benchmark-autosave --benchmark-compare=$(LATEST_BENCHMARK)

mypy: $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/mypy $(PACKAGE)

$(PACKAGE)/%.c: $(PACKAGE)/%.pyx $(PACKAGE)/%.pxd
	$(VIRTUAL_ENV)/bin/cython -a $<

cyt: $(PACKAGE)/router.c $(PACKAGE)/routes.c

compile: cyt
	$(VIRTUAL_ENV)/bin/python setup.py build_ext --inplace
