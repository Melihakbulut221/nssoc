# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0

.DEFAULT_GOAL := help
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PYTHON ?= python3
PY := $(ROOT)/.venv/bin/python
CBMC ?= $(ROOT)/hw/soc/tools/cbmc/usr/bin/cbmc

.PHONY: help setup test rtl-test check soc-prepare soc-sim soc-boot-regression rf-contract rf-equivalence boot-proof
help:
	@echo 'make setup PYTHON=/usr/bin/python3  Python 3.9-3.13 environments'
	@echo 'make test / rtl-test / check       Python, RTL, or local CI'
	@echo 'make soc-prepare / soc-sim         Fetch pinned Ibex/tools, then boot the SoC'
	@echo 'make soc-boot-regression           Normal boot and both geometry fallbacks'
	@echo 'make rf-contract / rf-equivalence  Real-codec proofs (set OSS_CAD_SUITE)'
	@echo 'make boot-proof CBMC=/path/to/cbmc  Check the ROM geometry predicate'
	@echo 'make soc-interfaces-test / soc-interfaces-sim  Pin and CPU interface tests'
	@echo 'make soc-interfaces-layout RUN_TAG=name      Fresh synthesis and P&R'
	@echo 'make soc-interfaces-decks RUN_TAG=name STATE=/path/state_out.json'

setup:
	@$(PYTHON) -c 'import sys; assert (3,9) <= sys.version_info[:2] <= (3,13), "cocotb 2.0.1 requires Python 3.9-3.13; set PYTHON to a compatible interpreter"'
	$(PYTHON) -m venv $(ROOT)/.venv
	$(PYTHON) -m venv $(ROOT)/hw/.venv
	$(PY) -m pip install -r $(ROOT)/sw/requirements.txt
	$(ROOT)/hw/.venv/bin/python -m pip install -r $(ROOT)/hw/requirements.txt

test:
	cd $(ROOT) && $(PY) -m pytest -q

rtl-test: soc-interfaces-prepare
	cd $(ROOT) && scripts/run_cocotb.sh

check:
	cd $(ROOT) && scripts/ci_local.sh all

soc-prepare:
	$(MAKE) -f $(ROOT)/hw/soc/tools.soc.mk fetch-sv2v fetch-ibex fetch-rvgcc
	bash $(ROOT)/hw/soc/flow/sv2v_ibex.sh $(ROOT)/hw/soc/ext/ibex $(ROOT)/hw/soc/gen $(ROOT)/hw/soc/tools/sv2v-Linux/sv2v
	$(MAKE) soc-interfaces-prepare

soc-sim:
	cd $(ROOT) && PATH="$(ROOT)/.venv/bin:$$PATH" bash hw/soc/flow/sim_soc.sh

soc-boot-regression:
	bash $(ROOT)/scripts/check_soc_boot.sh

rf-contract:
	$(MAKE) -C $(ROOT)/hw/soc/formal regfilecontract
	$(MAKE) -C $(ROOT)/hw/soc/formal regfilecontrols

rf-equivalence:
	$(MAKE) -C $(ROOT)/hw/soc/formal regfileequivalence

boot-proof:
	cd $(ROOT) && $(PY) scripts/check_boot_geometry.py --cbmc $(CBMC)

.PHONY: soc-interfaces-prepare
soc-interfaces-prepare:
	$(MAKE) -f $(ROOT)/hw/soc/tools.soc.mk fetch-verilog-i2c fetch-spacewire_reloaded fetch-can
	$(PYTHON) $(ROOT)/hw/soc/flow/prepare_interfaces.py

.PHONY: soc-interfaces-test soc-interfaces-sim
soc-interfaces-test: soc-interfaces-prepare
	cd $(ROOT) && scripts/run_cocotb.sh soc_interfaces

soc-interfaces-sim: soc-interfaces-prepare
	cd $(ROOT) && PATH="$(ROOT)/.venv/bin:$$PATH" SW_DEFINES=-DINTERFACE_DEMO IBEX_REGFILE=secded SOC_MEM_HARDEN=1 SOC_ROM_HARDEN=1 SOC_MEM_RDREG=1 SOC_REQ_REG=1 SOC_RF_SYNPRE=1 bash hw/soc/flow/sim_soc.sh hw/soc/out/interfaces-cpu

.PHONY: soc-interfaces-layout
soc-interfaces-layout:
	bash $(ROOT)/hw/soc/flow/implement_interfaces.sh $(RUN_TAG)

.PHONY: soc-interfaces-decks
soc-interfaces-decks:
	bash $(ROOT)/hw/soc/flow/verify_interfaces_layout.sh "$(RUN_TAG)" "$(STATE)"
