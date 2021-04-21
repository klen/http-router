VIRTUAL_ENV 	?= env
PACKAGE 	?= http_router

all: $(VIRTUAL_ENV)

$(VIRTUAL_ENV): setup.cfg
	@[ -d $(VIRTUAL_ENV) ] || python -m venv env
	@$(VIRTUAL_ENV)/bin/pip install -e .[tests,build]
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

.PHONY: register
# target: register - Register module on PyPi
register:
	@python setup.py register

LATEST_BENCHMARK = $(shell ls -t .benchmarks/* | head -1 | head -c4)
test t: $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/pytest tests.py --benchmark-autosave --benchmark-compare=$(LATEST_BENCHMARK)

mypy: $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/mypy $(PACKAGE)

$(PACKAGE)/%.c: $(PACKAGE)/%.pyx $(PACKAGE)/%.pxd
	$(VIRTUAL_ENV)/bin/cython -a $<

compile: $(PACKAGE)/router.c $(PACKAGE)/routes.c
	$(VIRTUAL_ENV)/bin/python setup.py build_ext --inplace
