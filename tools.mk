# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0

# Toolchain resolution, shared by every makefile in this repository.
#
# Why this file exists. The formal gate used to resolve `sby` through a
# glob over several oss-cad-suite checkouts, taking whichever the
# wildcard listed first. On the development machine that silently
# selected a *different project's* toolchain, so a run of the 37-task
# formal gate was executed by tools nothing in this repository pinned.
# Three yosys builds were reachable at once: 0.67+146 in a Downloads
# checkout, 0.67+94 in a sibling project's tools directory, and a third
# in ~/.local/bin that a bare `yosys` resolves to. The results were not
# wrong, but they were not reproducible either, and a report that cannot
# name the tool that produced it is evidence of nothing.
#
# The rule here: one checkout, named explicitly, overridable, and
# verified. Set OSS_CAD_SUITE to point somewhere else; run
# `make -f tools.mk toolcheck` to see what would actually be used.

# The pinned checkout, relative to THIS makefile even under make -C.
# Override on the command line or in the
# environment to use a different one:
#   make OSS_CAD_SUITE=$HOME/oss-cad-suite ...
TOOLS_MK_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
OSS_CAD_SUITE ?= $(TOOLS_MK_ROOT)/hw/soc/tools/oss-cad-suite

# The version this repository's recorded results were produced with.
# `toolcheck` compares against it and warns on a mismatch rather than
# failing, so a newer toolchain is usable but never silent.
OSS_CAD_SUITE_YOSYS_PIN ?= 0.67+146

TOOL_BIN := $(OSS_CAD_SUITE)/bin

SBY       := $(TOOL_BIN)/sby
EQY       := $(TOOL_BIN)/eqy
YOSYS     := $(TOOL_BIN)/yosys
IVERILOG  := $(TOOL_BIN)/iverilog
VVP       := $(TOOL_BIN)/vvp
VERILATOR := $(TOOL_BIN)/verilator

# Never mix this checkout with unrelated PATH binaries. An explicitly selected
# installation remains selected even if incomplete, and toolcheck diagnoses it.

ifeq ($(.DEFAULT_GOAL),)
.DEFAULT_GOAL := toolcheck
endif

.PHONY: fetch-oss-cad-suite
fetch-oss-cad-suite:
	$(or $(PYTHON),python3) $(TOOLS_MK_ROOT)/scripts/bootstrap_oss.py --destination "$(OSS_CAD_SUITE)"

.PHONY: toolcheck
toolcheck:
	@echo "OSS_CAD_SUITE = $(OSS_CAD_SUITE)"
	@test -d "$(OSS_CAD_SUITE)" || { \
	  echo "ERROR: checkout not found. Run make -f tools.mk fetch-oss-cad-suite or set OSS_CAD_SUITE."; \
	  exit 1; }
	@for t in sby eqy yosys iverilog vvp verilator; do \
	  test -x "$(TOOL_BIN)/$$t" || { echo "ERROR: missing executable $(TOOL_BIN)/$$t"; exit 1; }; \
	done
	@echo "sby       = $(SBY)"
	@echo "yosys     = $(YOSYS)"
	@echo "iverilog  = $(IVERILOG)"
	@v=$$("$(YOSYS)" -V 2>/dev/null | sed -n 's/^Yosys \([^ ]*\).*/\1/p'); \
	 echo "yosys version = $$v (pinned $(OSS_CAD_SUITE_YOSYS_PIN))"; \
	 if [ "$$v" != "$(OSS_CAD_SUITE_YOSYS_PIN)" ]; then \
	   echo "WARNING: yosys differs from the version the recorded results were produced with."; \
	   echo "         Re-derive any number you are about to quote, or set OSS_CAD_SUITE to the pinned checkout."; \
	 fi
