#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Map the complete MAC to native SRAM/standard cells and exercise GMII/APB.
set -euo pipefail
SOC_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUT=${1:-$SOC_DIR/out/eth-sram}
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
eval "$(make --no-print-directory -f "$SOC_DIR/tools.soc.mk" printvars)"
GL_IVERILOG=${GL_IVERILOG:-$HOME/.local/opt/iverilog13/usr/bin/iverilog}
major=$("$GL_IVERILOG" -V 2>/dev/null | sed -n '1s/.*version \([0-9]*\).*/\1/p')
[ "${major:-0}" -ge 13 ] || { echo 'Native SG13G2 models require Icarus >=13' >&2; exit 2; }
MACRO=RM_IHPSG13_2P_256x16_c2_bm_bist
LIB="$SG13G2_SRAM_DIR/lib/${MACRO}_typ_1p20V_25C.lib"
python3 "$SOC_DIR/flow/prepare_interfaces.py"
cat > "$OUT/synth.ys" <<EOF
read_liberty -lib $SG13G2_TYP
read_liberty -lib $LIB
read_verilog $SOC_DIR/rtl/soc_eth.v $SOC_DIR/gen/interfaces.bundle.vh
synth -top soc_eth -flatten -run begin:fine
memory_libmap -lib $SOC_DIR/techmap/eth_ram.lib
techmap -map $SOC_DIR/techmap/eth_ram_map.v
synth -top soc_eth -run fine
select -assert-count 16 t:$MACRO
dfflibmap -liberty $SG13G2_TYP
abc -liberty $SG13G2_TYP
setundef -zero
clean
check -assert
stat -liberty $SG13G2_TYP -liberty $LIB
write_verilog -noattr $OUT/eth.netlist.v
write_json $OUT/eth.netlist.json
EOF
"$YOSYS" -Q -s "$OUT/synth.ys" > "$OUT/synth.log" 2>&1
SRAM_V="$SG13G2_SRAM_DIR/verilog"
export PATH="$SOC_DIR/../../.venv/bin:$SOC_DIR/../.venv/bin:$PATH"
export PYTHONPATH="$SOC_DIR/tb/cocotb${PYTHONPATH:+:$PYTHONPATH}"
cat > "$OUT/Makefile" <<EOF
SIM = icarus
TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $OUT/eth.netlist.v $SG13G2_VLOG $SRAM_V/$MACRO.v $SRAM_V/RM_IHPSG13_2P_core_behavioral_bm_bist_ideal.v $SRAM_V/RM_IHPSG13_2P_core_behavioral_ideal.v
TOPLEVEL = soc_eth
MODULE = test_soc_eth
COMPILE_ARGS += -DFUNCTIONAL
SIM_BUILD = $OUT/sim_build
COCOTB_RESULTS_FILE = $OUT/results.xml
include \$(shell cocotb-config --makefiles)/Makefile.sim
EOF
make -C "$OUT" ICARUS_BIN_DIR="$(dirname "$GL_IVERILOG")" > "$OUT/test.log" 2>&1
python3 - "$OUT" "$SOC_DIR" "$SG13G2_TYP" "$LIB" "$SG13G2_VLOG" <<'PY'
import hashlib, json, pathlib, sys, xml.etree.ElementTree as ET
out, soc, *libraries = map(pathlib.Path, sys.argv[1:])
cases = ET.parse(out/'results.xml').findall('.//testcase')
assert len(cases) >= 6 and all(len(c) == 0 for c in cases), 'Gate-level regression failed/skipped'
paths = [soc/'rtl/soc_eth.v', soc/'gen/interfaces.bundle.vh',
         soc/'flow/prepare_interfaces.py', soc/'flow/test_eth_sram.sh',
         soc/'techmap/eth_ram.lib', soc/'techmap/eth_ram_map.v',
         soc/'tb/cocotb/test_soc_eth.py', out/'eth.netlist.v', *libraries]
record = {'tests': [c.attrib['name'] for c in cases], 'passed': len(cases),
          'sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
(out/'evidence.json').write_text(json.dumps(record, indent=2)+'\n')
print(f'Native SRAM gate-level Ethernet: {len(cases)} passed, no failures or skips')
PY
