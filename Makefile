# tabmill (tool repo) — Python + uv CLI (ADR-0002), built through the central builder.
# The builder auto-detects the Python stack from pyproject.toml; Makefile.local adapts it.
#
#   make deps | build | test | lint | fmt | run ARGS="..." | clean | help
#
# Runs on the host via uv (no Node involved), or inside the builder's Python container
# via `make buildsh`.

BUILDER_PATH ?= $(abspath $(HOME)/work/projects/builder)

ifeq ($(wildcard $(BUILDER_PATH)/Makefile),)
$(error Builder Makefile not found at $(BUILDER_PATH). Set BUILDER_PATH=<path to builder repo>)
endif

include $(BUILDER_PATH)/Makefile
