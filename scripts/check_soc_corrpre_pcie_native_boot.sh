#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0

# Run after make soc-prepare. Tools resolve through tools.soc.mk, as in the
# normal RTL and synthesis flows. This requires Icarus >=13 and rejects an
# incompatible untouched native flip-flop model before whole-chip simulation.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$ROOT"
OUT=${1:-hw/soc/out/corrpre-pcie-native-boot}
OUT=$(realpath -m "$OUT")
case "$OUT" in
  "$ROOT"/hw/soc/out/*) ;;
  *) echo 'Native boot output must be inside hw/soc/out' >&2; exit 2 ;;
esac
if [ -e "$OUT" ]; then
  echo "Refusing to replace existing evidence: $OUT" >&2
  exit 2
fi
export SOC_CORE_REQ_REG=${SOC_CORE_REQ_REG:-0}
export SOC_CORE_WB_STAGE=${SOC_CORE_WB_STAGE:-0}
case "$SOC_CORE_REQ_REG:$SOC_CORE_WB_STAGE" in
  0:0|0:1|1:0|1:1) ;;
  *) echo 'Native boot core selectors must be 0 or 1' >&2; exit 2 ;;
esac
# Execute-path timing knobs (docs/ibex-execute-timing.md); sim_soc.sh and
# syn_soc_top.sh read them from the environment and refuse bad values.
export SOC_CORE_BT_ALU=${SOC_CORE_BT_ALU:-0}
export IBEX_BRANCH_2CYCLE=${IBEX_BRANCH_2CYCLE:-0}
export IBEX_EX_STAGE=${IBEX_EX_STAGE:-0}
export IBEX_PMP_REQ_REG=${IBEX_PMP_REQ_REG:-0}
# docs/combined-timing.md knobs, read by sim_soc.sh and syn_soc_top.sh.
export SOC_ETH_FIFO_RDREG=${SOC_ETH_FIFO_RDREG:-0}
export SOC_BUSSTAT_EVPEND=${SOC_BUSSTAT_EVPEND:-0}
export SOC_PCIE_RX_READ_AHEAD=${SOC_PCIE_RX_READ_AHEAD:-0}
export SOC_BUS_WDATA_OWN=${SOC_BUS_WDATA_OWN:-0}
export SOC_PCIE_RX_READ2=${SOC_PCIE_RX_READ2:-0}
export SOC_BUS_IREQ_REG=${SOC_BUS_IREQ_REG:-0}
export SOC_PCIE_RESET_COPIES=${SOC_PCIE_RESET_COPIES:-0}
export SOC_ETH_FIFO_WRREG=${SOC_ETH_FIFO_WRREG:-0}
export SOC_PCIE_REPLAY_INBANK=${SOC_PCIE_REPLAY_INBANK:-0}
export SOC_PCIE_TX_WORD_REG=${SOC_PCIE_TX_WORD_REG:-0}
export SOC_PCIE_REPLAY_AHEAD=${SOC_PCIE_REPLAY_AHEAD:-0}
export SOC_PCIE_CREDIT_PICK=${SOC_PCIE_CREDIT_PICK:-0}
# Register-file and memory knobs (same document). One variable each, set
# for both the RTL run (SOC_*) and the synthesis (IBEX_RF_*) below.
NATIVE_RF_CHKDEFER=${NATIVE_RF_CHKDEFER:-0}
NATIVE_RF_PREDECODE=${NATIVE_RF_PREDECODE:-0}
NATIVE_MEM_RDREG=${NATIVE_MEM_RDREG:-1}
case "$NATIVE_RF_CHKDEFER:$NATIVE_RF_PREDECODE:$NATIVE_MEM_RDREG" in
  [01]:[01]:[12]) ;;
  *) echo 'NATIVE_RF_CHKDEFER/PREDECODE must be 0 or 1, NATIVE_MEM_RDREG 1 or 2' >&2; exit 2 ;;
esac
export NATIVE_MEM_RDREG SOC_RF_CHKDEFER=$NATIVE_RF_CHKDEFER IBEX_RF_CHKDEFER=$NATIVE_RF_CHKDEFER
export SOC_RF_PREDECODE=$NATIVE_RF_PREDECODE IBEX_RF_PREDECODE=$NATIVE_RF_PREDECODE
mkdir -p "$OUT"
python3 - "$OUT/core-configuration.json" <<'PY'
import json
import os
from pathlib import Path
import sys
Path(sys.argv[1]).write_text(json.dumps({
    'RF_CORRPRE': 1,
    'SOC_PCIE_PROFILE': 'packet-async',
    'pcie_traffic_tested': False,
    'RF_SYNPRE': 0,
    'experimental_candidate_not_mainchip_acceptance': True,
    'CORE_REQ_REG': int(os.environ['SOC_CORE_REQ_REG']),
    'CORE_WB_STAGE': int(os.environ['SOC_CORE_WB_STAGE']),
    'CORE_BRANCH_TARGET_ALU': int(os.environ['SOC_CORE_WB_STAGE']) | int(os.environ['SOC_CORE_BT_ALU']),
    'CORE_BT_ALU': int(os.environ['SOC_CORE_BT_ALU']),
    'IBEX_BRANCH_2CYCLE': int(os.environ['IBEX_BRANCH_2CYCLE']),
    'IBEX_EX_STAGE': int(os.environ['IBEX_EX_STAGE']),
    'IBEX_PMP_REQ_REG': int(os.environ['IBEX_PMP_REQ_REG']),
    'ETH_FIFO_RDREG': int(os.environ['SOC_ETH_FIFO_RDREG']),
    'BUSSTAT_EVPEND': int(os.environ['SOC_BUSSTAT_EVPEND']),
    'PCIE_RX_READ_AHEAD': int(os.environ['SOC_PCIE_RX_READ_AHEAD']),
    'BUS_WDATA_OWN': int(os.environ['SOC_BUS_WDATA_OWN']),
    'PCIE_RX_READ2': int(os.environ['SOC_PCIE_RX_READ2']),
    'BUS_IREQ_REG': int(os.environ['SOC_BUS_IREQ_REG']),
    'PCIE_RESET_COPIES': int(os.environ['SOC_PCIE_RESET_COPIES']),
    'ETH_FIFO_WRREG': int(os.environ['SOC_ETH_FIFO_WRREG']),
    'PCIE_REPLAY_INBANK': int(os.environ['SOC_PCIE_REPLAY_INBANK']),
    'PCIE_TX_WORD_REG': int(os.environ['SOC_PCIE_TX_WORD_REG']),
    'PCIE_REPLAY_AHEAD': int(os.environ['SOC_PCIE_REPLAY_AHEAD']),
    'PCIE_CREDIT_PICK': int(os.environ['SOC_PCIE_CREDIT_PICK']),
    'RF_CHKDEFER': int(os.environ['SOC_RF_CHKDEFER']),
    'RF_PREDECODE': int(os.environ['SOC_RF_PREDECODE']),
    'MEM_RDREG': int(os.environ['NATIVE_MEM_RDREG']),
    'interface_profile': os.environ.get('SOC_INTERFACE_PROFILE', 'base'),
    'status': 'requested configuration; consult RTL, synthesis and gate results',
}, indent=2) + '\n')
PY

python3 hw/soc/flow/prepare_ihp_native_boot.py | tee "$OUT/prepare-models.log"
export PDK_ROOT="$ROOT/hw/soc/tools/ihp-native-boot-c4b8b4e"
eval "$(make --no-print-directory -f hw/soc/tools.soc.mk printvars)"
"$IVERILOG" -V > "$OUT/iverilog-version.log" 2>&1
"$YOSYS" -V > "$OUT/yosys-version.log" 2>&1
cp hw/soc/pnr/ihp-native-boot.lock.json "$OUT/model-lock.json"
python3 - "$IVERILOG" "$PDK_ROOT" "$OUT" <<'PY'
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, 'hw/soc/flow')
from sim_logic_boot_gl import check_native_cell
tool, pdk, out = sys.argv[1:]
version = (Path(out) / 'iverilog-version.log').read_text()
match = re.search(r'Icarus Verilog version (\d+)', version)
if not match or int(match[1]) < 13:
    raise SystemExit('Native boot requires Icarus >=13')
library = Path(pdk) / 'ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v'
result = check_native_cell('iverilog', tool, library, Path(out) / 'native-cell-preflight')
print(json.dumps(result, indent=2))
if not result['passed']:
    raise SystemExit('Native model compatibility failed before RTL/synthesis')
PY

# Recoverability is checked before the hours-long whole-chip run. The
# historical failing mapped cone must still fail its functional assertion.
python3 scripts/check_scrub_native.py --tools "$(dirname "$IVERILOG")" \
  --pdk "$PDK_ROOT/ihp-sg13g2" --output "$OUT/scrub-native" \
  > "$OUT/scrub-native-driver.log" 2>&1

unset BOOT_CORRUPT SW_DEFINES SOC_VVP_ARGS SOC_BOOT_ROM_DIR SOC_BOOT_ROM_IMAGE
unset SOC_RAM_RDREG SOC_ROM_RDREG SOC_SCRUB_IVL SOC_DED_WORD SOC_STRAP SOC_TIMEOUT_CYCLES
export UART_SCALER=0 SOC_PROBE=0 SOC_RAM_RANDOM=1 SOC_CLKGATE=1 SOC_APB_TIMEOUT=256
export IBEX_REGFILE=secded IBEX_FAULT_PORT=1 SOC_MEM_HARDEN=1 SOC_ROM_HARDEN=1
export SOC_BOOT_ROM=logic SOC_MEM_RDREG=$NATIVE_MEM_RDREG SOC_REQ_REG=1 SOC_RF_SYNPRE=0 SOC_RF_CORRPRE=1 SOC_WAKE_GNT=1
timeout 1800 bash hw/soc/flow/sim_soc.sh "$OUT/rtl" > "$OUT/rtl-driver.log" 2>&1
export SOC_BOOT_ROM_IMAGE="$OUT/rtl/test_soc.bin" SOC_MEM=sram
export IBEX_RF_SYNPRE=0 IBEX_RF_CORRPRE=1 SOC_ETH_SRAM=1 SOC_PCIE_PROFILE=packet-async
timeout 3600 bash hw/soc/flow/syn_soc_top.sh 20 "$OUT/synthesis" > "$OUT/synthesis-driver.log" 2>&1
grep -F 'Parameter \CORRPRE = 1' "$OUT/synthesis/syn.log" > "$OUT/synthesis-corrpre-selection.log"
python3 hw/soc/flow/sim_logic_boot_gl.py \
  --pcie-profile packet-async \
  --synthesis "$OUT/synthesis" --firmware "$OUT/rtl" \
  --pdk "$PDK_ROOT/ihp-sg13g2" --tool "$IVERILOG" \
  --output "$OUT/gates" | tee "$OUT/gates-driver.log"
