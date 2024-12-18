.PHONY: test

test:
	uv run pytest tests/

feat:
	uv urn pytest tests/test_feat.py

dev:
	uv run python -m demo

.PHONY: release

VERSION ?= x.x.x
BRANCH = version/$(VERSION)

# Command definitions
UV_CMD = uv run
HATCH_VERSION_CMD = $(UV_CMD) hatch version
CURRENT_VERSION = $(shell $(HATCH_VERSION_CMD))

# Helper functions
define parse_version
	$(eval MAJOR=$(shell echo $(1) | cut -d. -f1))
	$(eval MINOR=$(shell echo $(1) | cut -d. -f2))
	$(eval PATCH=$(shell echo $(1) | cut -d. -f3))
endef

define check_version_order
	$(call parse_version,$(1))  # Parse first version into MAJOR, MINOR, PATCH
	$(eval V1_MAJOR=$(MAJOR))
	$(eval V1_MINOR=$(MINOR))
	$(eval V1_PATCH=$(PATCH))
	$(call parse_version,$(2))  # Parse second version into MAJOR, MINOR, PATCH
	$(eval V2_MAJOR=$(MAJOR))
	$(eval V2_MINOR=$(MINOR))
	$(eval V2_PATCH=$(PATCH))
	@if [ "$(V2_MAJOR)" -gt "$(V1_MAJOR)" ] || \
		([ "$(V2_MAJOR)" -eq "$(V1_MAJOR)" ] && [ "$(V2_MINOR)" -gt "$(V1_MINOR)" ]) || \
		([ "$(V2_MAJOR)" -eq "$(V1_MAJOR)" ] && [ "$(V2_MINOR)" -eq "$(V1_MINOR)" ] && [ "$(V2_PATCH)" -gt "$(V1_PATCH)" ]); then \
		echo "Version $(2) is valid."; \
	else \
		echo "Error: Version $(2) must be larger than $(1)"; \
		exit 1; \
	fi
endef

define increment_patch_version
	$(call parse_version,$(1))
	$(eval NEW_PATCH=$(shell echo $$(($(PATCH) + 1))))
	$(eval NEW_VERSION=$(MAJOR).$(MINOR).$(NEW_PATCH))
endef

# Main release target
release: check-branch check-version update-version git-commit git-merge git-tag git-push hatch-build new-branch

# Version checking and updating
check-branch:
	@if [ "$$(git rev-parse --abbrev-ref HEAD)" != "$(BRANCH)" ]; then \
		echo "Error: You must be on branch $(BRANCH) to release."; \
		echo "Did you forget to provide VERSION?"; \
		exit 1; \
	fi

check-version:
	@if [ "$(CURRENT_VERSION)" = "" ]; then \
		echo "Error: Unable to retrieve current version."; \
		exit 1; \
	fi
	$(call check_version_order,$(CURRENT_VERSION),$(VERSION))

update-version:
	@echo "Updating Pixi version to $(VERSION)..."
	@$(HATCH_VERSION_CMD) $(VERSION)

# Git operations
git-commit:
	@echo "Committing changes..."
	@git add -A
	@git commit -m "Release version $(VERSION)"

git-merge:
	@echo "Merging $(BRANCH) into master..."
	@git checkout master
	@git merge "$(BRANCH)"

git-tag:
	@echo "Tagging the release..."
	@git tag -a "v$(VERSION)" -m "Release version $(VERSION)"

git-push:
	@echo "Pushing to remote repository..."
	@git push origin master
	@git push origin "v$(VERSION)"

# Build and publish operations
hatch-build:
	@echo "Building version $(VERSION)..."
	@$(UV_CMD) hatch build

pypi-release:
	@$(UV_CMD) publish
	@git branch -d $(BRANCH)
	@git push origin --delete $(BRANCH)

# Branch management
delete-branch:
	@git branch -d $(BRANCH)
	@git push origin --delete $(BRANCH)

new-branch:
	@echo "Creating new version branch..."
	@if [ "$(CURRENT_VERSION)" = "" ]; then \
		echo "Error: Unable to retrieve current version."; \
		exit 1; \
	fi
	$(call increment_patch_version,$(CURRENT_VERSION))
	@echo "Creating branch version/$(NEW_VERSION)"
	@git checkout -b "version/$(NEW_VERSION)"

.PHONY: release check-branch check-version update-version git-commit git-merge git-tag git-push hatch-build pypi-release delete-branch new-branch