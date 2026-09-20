#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0

# Run after make soc-prepare. Tools resolve through tools.soc.mk, as in the
# normal RTL and synthesis flows. This requires Icarus >=13 and rejects an
# incompatible untouched native flip-flop model before whole-chip simulation.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$ROOT"
OUT=${1:-hw/soc/out/native-boot}
OUT=$(realpath -m "$OUT")
case "$OUT" in
  "$ROOT"/hw/soc/out/*) ;;
  *) echo 'Native boot output must be inside hw/soc/out' >&2; exit 2 ;;
esac
if [ -e "$OUT" ]; then
  echo "Refusing to replace existing evidence: $OUT" >&2
  exit 2
fi
mkdir -p "$OUT"

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

unset BOOT_CORRUPT SW_DEFINES SOC_VVP_ARGS SOC_BOOT_ROM_DIR SOC_BOOT_ROM_IMAGE
unset SOC_RAM_RDREG SOC_ROM_RDREG SOC_SCRUB_IVL SOC_DED_WORD SOC_STRAP SOC_TIMEOUT_CYCLES
export UART_SCALER=0 SOC_PROBE=0 SOC_RAM_RANDOM=1 SOC_CLKGATE=1 SOC_APB_TIMEOUT=256
export IBEX_REGFILE=secded IBEX_FAULT_PORT=1 SOC_MEM_HARDEN=1 SOC_ROM_HARDEN=1
export SOC_BOOT_ROM=logic SOC_MEM_RDREG=1 SOC_REQ_REG=1 SOC_RF_SYNPRE=1 SOC_WAKE_GNT=1
timeout 1800 bash hw/soc/flow/sim_soc.sh "$OUT/rtl" > "$OUT/rtl-driver.log" 2>&1
export SOC_BOOT_ROM_IMAGE="$OUT/rtl/test_soc.bin" SOC_MEM=sram
export IBEX_RF_SYNPRE=1 SOC_ETH_SRAM=1
timeout 3600 bash hw/soc/flow/syn_soc_top.sh 20 "$OUT/synthesis" > "$OUT/synthesis-driver.log" 2>&1
python3 hw/soc/flow/sim_logic_boot_gl.py \
  --synthesis "$OUT/synthesis" --firmware "$OUT/rtl" \
  --pdk "$PDK_ROOT/ihp-sg13g2" --tool "$IVERILOG" \
  --output "$OUT/gates" | tee "$OUT/gates-driver.log"
