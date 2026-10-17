PACKAGE ?= http_router

.PHONY: all test t mypy ruff clean cyt compile version minor patch major

all:
	uv sync --all-extras
	uv run pre-commit install --hook-type pre-push

LATEST_BENCHMARK = $(shell ls -t .benchmarks/*/*.json 2>/dev/null | head -1)

test t:
	uv run pytest tests --benchmark-autosave --benchmark-compare=$(LATEST_BENCHMARK)

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

# ==============
#  Bump version
# ==============

RELEASE	?= minor
MANAGER	?= uv

.PHONY: release
# target: release - Bump version
release:
	@echo "Starting release process (bumping $(RELEASE) version)..."
	@git checkout main
	@git pull
	@git checkout develop
	@git pull
	@echo "Bumping version and creating release commit and tag..."
	@uvx bump-my-version bump $(RELEASE)
	@echo "Version bumped to `$(MANAGER) version --short`."
	@$(MANAGER) lock
	@echo "Committing version bump and creating tag..."
	@VERSION=`$(MANAGER) version --short`; \
		{ \
			printf 'build(release): %s\n\n' "$$VERSION"; \
			printf 'Changes:\n\n'; \
			git log --oneline --pretty=format:'%s [%an]' main..develop | grep -Evi 'github|^Merge' || true; \
		} | git commit -a -F -
	@echo "Merging changes between branches..."
	@git checkout main
	@git merge --ff-only develop
	@VERSION=`$(MANAGER) version --short`; \
		git push origin main; \
		git tag -a "$$VERSION" -m "$$VERSION"; \
		git push origin "$$VERSION"
	@git checkout develop
	@git merge --ff-only main
	@git push origin develop
	@echo "Release process complete for `$(MANAGER) version --short`"

.PHONY: minor
minor: release

.PHONY: patch
patch:
	make release RELEASE=patch

.PHONY: major
major:
	make release RELEASE=major

version v:
	uv version --short

