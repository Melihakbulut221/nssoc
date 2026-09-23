#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Reproduce the integrated ECC SoC profile. Never writes the frozen pilot.
set -euo pipefail
SOC_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ROOT=$(cd "$SOC_DIR/../.." && pwd)
TAG=${1:?usage: implement_interfaces.sh unique-run-tag [--synthesis-only] [librelane args...]}
shift
synthesis_only=0
if [ "${1:-}" = --synthesis-only ]; then synthesis_only=1; shift; fi
case "$TAG" in *[!a-zA-Z0-9_-]*|'') echo 'Use an alphanumeric run tag.' >&2; exit 2;; esac
export SOC_CORE_REQ_REG=${SOC_CORE_REQ_REG:-0}
export SOC_CORE_WB_STAGE=${SOC_CORE_WB_STAGE:-0}
case "$SOC_CORE_REQ_REG:$SOC_CORE_WB_STAGE" in
  0:0|0:1|1:0|1:1) ;;
  *) echo 'SOC_CORE_REQ_REG and SOC_CORE_WB_STAGE must be 0 or 1.' >&2; exit 2 ;;
esac
OUT="$SOC_DIR/out/$TAG"
[ ! -e "$OUT" ] || { echo "Refusing to overwrite $OUT" >&2; exit 2; }
mkdir -p "$OUT"
export SOC_INTERFACE_PROFILE=${SOC_INTERFACE_PROFILE:-base}
# Match the Make entrypoint: full CAN preparation imports the declared PyYAML
# dependency from the project environment; honor an explicit interpreter.
interface_python=${INTERFACE_PYTHON:-${PYTHON:-python3}}
if [ -z "${INTERFACE_PYTHON:-}" ] && [ -x "$ROOT/.venv/bin/python" ]; then
    interface_python="$ROOT/.venv/bin/python"
fi
"$interface_python" "$SOC_DIR/flow/prepare_interfaces.py" --profile "$SOC_INTERFACE_PROFILE"
# This entrypoint implements the current bootable profile. Historical knobs
# remain available through the individual synthesis/PNR scripts.
export IBEX_REGFILE=secded IBEX_FAULT_PORT=1 SOC_MEM=sram
export SOC_MEM_HARDEN=1 SOC_ROM_HARDEN=1 SOC_BOOT_HARDEN=1 SOC_CLKGATE=1
export SOC_WAKE_GNT=1 SOC_ABC_D_PS=0 SOC_APB_TIMEOUT=256 SOC_ETH_SRAM=1
export SOC_MEM_RDREG=1 SOC_REQ_REG=1 IBEX_RF_SYNPRE=1 SOC_BOOT_ROM=logic
export SOC_BOOT_ROM_IMAGE="$OUT/firmware/test_soc.bin" SOC_BOOT_ROM_DIR="$OUT/synthesis/boot-rom"
# Rebuild the loader used by both synthesis and PNR; do not inherit fault
# demonstration settings or a caller's stale ROM image.
BOOT_CORRUPT=none bash "$SOC_DIR/flow/build_sw_soc.sh" "$OUT/firmware" >"$OUT/firmware.log" 2>&1
python3 "$SOC_DIR/flow/gen_logic_boot_rom.py" --image "$SOC_BOOT_ROM_IMAGE" --output "$OUT/boot-rom-reference"
python3 - "$ROOT" "$OUT/inputs.json" <<'PY'
import hashlib, json, os, pathlib, sys
root, out = map(pathlib.Path, sys.argv[1:])
files = set()
for directory in ('hw/rtl', 'hw/soc/rtl', 'hw/soc/gen', 'hw/soc/genp', 'hw/soc/tb/sw'):
    for ext in ('*.v', '*.vh', '*.c', '*.h', '*.S', '*.ld'):
        files.update((root/directory).rglob(ext))
record = {'configuration': {'SOC_INTERFACE_PROFILE': os.environ['SOC_INTERFACE_PROFILE'],
                           'MEM_RDREG': 1, 'REQ_REG': 1, 'SYNPRE': 1,
                           'CORE_REQ_REG': int(os.environ['SOC_CORE_REQ_REG']),
                           'CORE_WB_STAGE': int(os.environ['SOC_CORE_WB_STAGE']),
                           'CORE_BRANCH_TARGET_ALU': int(os.environ['SOC_CORE_WB_STAGE']),
                           'MEM_HARDEN': 1, 'ROM_HARDEN': 1, 'APB_TIMEOUT': 256,
                           'WAKE_GNT': 1, 'BOOT_HARDEN': 1, 'CLKGATE': 1,
                           'SOC_BOOT_ROM': 'logic', 'IBEX_REGFILE': 'secded', 'IBEX_FAULT_PORT': 1,
                           'ETH_SRAM': 1, 'ETH_SRAM_BANK_WORDS': 256, 'clock_ns': 20, 'ethernet_clock_ns': 8},
          'sources': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(files)}}
record['implementation_files'] = {
    name: hashlib.sha256((root/name).read_bytes()).hexdigest()
    for name in ('hw/soc/flow/implement_interfaces.sh',
                 'hw/soc/flow/syn_soc_top.sh', 'hw/soc/flow/pnr_soc_top.sh',
                 'hw/soc/flow/prepare_interfaces.py', 'hw/soc/flow/interface_profile.py',
                 'hw/soc/rtl/soc_logic_boot_rom.v.in', 'sw/golden/secded.py',
                 'hw/soc/pnr/interface_flow.py',
                 'hw/soc/flow/build_sw_soc.sh', 'hw/soc/flow/gen_logic_boot_rom.py',
                 'hw/soc/flow/select_pnr_profile.py', 'hw/soc/flow/physical_env.sh',
                 'hw/soc/flow/check_timing_derate.tcl',
                 'hw/soc/flow/prune_orphan_guides.tcl',
                 'hw/soc/techmap/eth_ram.lib', 'hw/soc/techmap/eth_ram_map.v',
                 'hw/soc/sta/soc_interfaces.sdc', 'hw/soc/sta/soc_top_qspi_io.sdc',
                 'hw/soc/sta/soc_interfaces_external_irq.sdc')}
record['boot_image_sha256'] = hashlib.sha256(pathlib.Path(os.environ['SOC_BOOT_ROM_IMAGE']).read_bytes()).hexdigest()
record['boot_rom_sha256'] = hashlib.sha256((out.parent/'boot-rom-reference/soc_logic_boot_rom.v').read_bytes()).hexdigest()
out.write_text(json.dumps(record, indent=2)+'\n')
PY
bash "$SOC_DIR/flow/syn_soc_top.sh" 20 "$OUT/synthesis" >"$OUT/build.log" 2>&1
# Validate the actual mapped macro inventory and choose the matching ROM
# profile. Keep an explicit compatible floorplan override, if supplied.
profile_args=(--netlist "$OUT/synthesis/soc_top.netlist.v" --directory "$SOC_DIR/pnr" --rom logic)
if [ -n "${PNR_CONFIG:-}" ]; then profile_args+=(--config "$PNR_CONFIG"); fi
export PNR_CONFIG
PNR_CONFIG=$(python3 "$SOC_DIR/flow/select_pnr_profile.py" "${profile_args[@]}")
# Bind the resulting netlist to its input inventory before P&R starts.
python3 - "$OUT" <<'PY'
import hashlib, json, pathlib, sys
out = pathlib.Path(sys.argv[1]); p = out/'inputs.json'; record=json.loads(p.read_text())
import os
config = pathlib.Path(os.environ['PNR_CONFIG'])
record['physical_config'] = {'path': config.name, 'sha256': hashlib.sha256(config.read_bytes()).hexdigest()}
assert record['boot_image_sha256'] == hashlib.sha256(pathlib.Path(os.environ['SOC_BOOT_ROM_IMAGE']).read_bytes()).hexdigest(), 'Boot image changed during synthesis'
assert record['boot_rom_sha256'] == hashlib.sha256((out/'synthesis/boot-rom/soc_logic_boot_rom.v').read_bytes()).hexdigest(), 'Generated ROM changed during synthesis'
root = out.parents[3]
for section in ('sources', 'implementation_files'):
    for name, expected in record[section].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, 'Source changed during synthesis: '+name
record['netlist_sha256'] = hashlib.sha256((out/'synthesis/soc_top.netlist.v').read_bytes()).hexdigest()
p.write_text(json.dumps(record, indent=2)+'\n')
PY
if [ "$synthesis_only" = 1 ]; then
    echo "Synthesis/profile preparation complete: $OUT (no placement or signoff)"
    exit 0
fi
SOC_INTERFACE_FLOW=1 \
SYN_NETLIST="$OUT/synthesis/soc_top.netlist.v" PNR_STATE="$SOC_DIR/pnr/state/$TAG.json" \
  bash "$SOC_DIR/flow/pnr_soc_top.sh" "$TAG" \
  -F Yosys.JsonHeader -S Yosys.Synthesis -S Checker.YosysUnmappedCells \
  -S Checker.YosysSynthChecks -S Checker.NetlistAssignStatements \
  -i "$SOC_DIR/pnr/state/$TAG.json" "$@" >"$OUT/layout.log" 2>&1
