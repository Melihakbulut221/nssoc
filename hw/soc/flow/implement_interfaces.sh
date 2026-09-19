#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Reproduce the integrated ECC SoC profile. Never writes the frozen pilot.
set -euo pipefail
SOC_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ROOT=$(cd "$SOC_DIR/../.." && pwd)
TAG=${1:?usage: implement_interfaces.sh unique-run-tag}
case "$TAG" in *[!a-zA-Z0-9_-]*|'') echo 'Use an alphanumeric run tag.' >&2; exit 2;; esac
OUT="$SOC_DIR/out/$TAG"
[ ! -e "$OUT" ] || { echo "Refusing to overwrite $OUT" >&2; exit 2; }
mkdir -p "$OUT"
python3 "$SOC_DIR/flow/prepare_interfaces.py"
python3 - "$ROOT" "$OUT.inputs.json" <<'PY'
import hashlib, json, pathlib, sys
root, out = map(pathlib.Path, sys.argv[1:])
files = set()
for directory in ('hw/rtl', 'hw/soc/rtl', 'hw/soc/gen', 'hw/soc/genp'):
    for ext in ('*.v', '*.vh'):
        files.update((root/directory).glob(ext))
record = {'configuration': {'MEM_RDREG': 1, 'REQ_REG': 1, 'SYNPRE': 1,
                           'MEM_HARDEN': 1, 'ROM_HARDEN': 1, 'APB_TIMEOUT': 256, 'clock_ns': 20},
          'sources': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(files)}}
record['implementation_files'] = {
    name: hashlib.sha256((root/name).read_bytes()).hexdigest()
    for name in ('hw/soc/flow/implement_interfaces.sh',
                 'hw/soc/flow/syn_soc_top.sh', 'hw/soc/flow/pnr_soc_top.sh',
                 'hw/soc/flow/prepare_interfaces.py',
                 'hw/soc/pnr/interface_flow.py',
                 'hw/soc/pnr/config-interfaces-synpre.json')}
out.write_text(json.dumps(record, indent=2)+'\n')
PY
IBEX_REGFILE=secded IBEX_FAULT_PORT=1 SOC_MEM=sram \
SOC_MEM_HARDEN=1 SOC_ROM_HARDEN=1 SOC_BOOT_HARDEN=1 SOC_CLKGATE=1 \
SOC_WAKE_GNT=0 SOC_ABC_D_PS=0 SOC_APB_TIMEOUT=256 \
SOC_MEM_RDREG=1 SOC_REQ_REG=1 IBEX_RF_SYNPRE=1 \
  bash "$SOC_DIR/flow/syn_soc_top.sh" 20 "$OUT" >"$OUT.build.log" 2>&1
mv "$OUT.inputs.json" "$OUT/inputs.json"
mv "$OUT.build.log" "$OUT/build.log"
# Bind the resulting netlist to its input inventory before P&R starts.
python3 - "$OUT" <<'PY'
import hashlib, json, pathlib, sys
out = pathlib.Path(sys.argv[1]); p = out/'inputs.json'; record=json.loads(p.read_text())
record['netlist_sha256'] = hashlib.sha256((out/'soc_top.netlist.v').read_bytes()).hexdigest()
p.write_text(json.dumps(record, indent=2)+'\n')
PY
SOC_INTERFACE_FLOW=1 PNR_CONFIG="$SOC_DIR/pnr/config-interfaces-synpre.json" \
SYN_NETLIST="$OUT/soc_top.netlist.v" PNR_STATE="$SOC_DIR/pnr/state/$TAG.json" \
  bash "$SOC_DIR/flow/pnr_soc_top.sh" "$TAG" \
  -F Yosys.JsonHeader -S Yosys.Synthesis -S Checker.YosysUnmappedCells \
  -S Checker.YosysSynthChecks -S Checker.NetlistAssignStatements \
  -i "$SOC_DIR/pnr/state/$TAG.json" >"$OUT/layout.log" 2>&1
