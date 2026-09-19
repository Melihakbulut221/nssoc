#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Run independent physical decks on an existing interface layout.
# Magic DRC uses DEF/LEF; KLayout DRC and XOR use the GDS streams.
# SRAM interiors are black boxes in LVS; every macro pin is compared.
# A failing deck remains a nonzero exit, including known vendor violations.
set -euo pipefail

RUN_TAG=${1:?usage: verify_interfaces_layout.sh <new-run-tag> <state_out.json>}
INPUT_STATE=${2:?usage: verify_interfaces_layout.sh <new-run-tag> <state_out.json>}
[[ "$RUN_TAG" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || {
    echo 'invalid run tag' >&2; exit 1;
}
SOC_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
INPUT_STATE=$(realpath -e "$INPUT_STATE")
OUT=$SOC_DIR/out/$RUN_TAG
CONFIG=$SOC_DIR/pnr/config-fp${RUN_TAG}-decks.json
if [[ -e "$OUT" || -e "$CONFIG" || -e "$SOC_DIR/pnr/runs/$RUN_TAG" ]]; then
    echo 'refusing to overwrite an existing physical verification run' >&2
    exit 1
fi

python3 - "$SOC_DIR" "$INPUT_STATE" "$CONFIG" "$OUT" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

soc, state_path, config_path, out = map(Path, sys.argv[1:])
try:
    state_path.relative_to(soc / 'pnr' / 'runs')
except ValueError:
    raise SystemExit('Input state must belong to this SoC run directory')
state = json.loads(state_path.read_text())
profile = soc / 'pnr' / 'config-interfaces-synpre.json'
config = json.loads(profile.read_text())
original = json.loads((state_path.parent.parent / 'resolved.json').read_text())
for key in ('DESIGN_NAME', 'PDK', 'DIE_AREA', 'CORE_AREA', 'CLOCK_PERIOD'):
    if original.get(key) != config[key]:
        raise SystemExit(f'Input layout does not match the interface profile: {key}')
artifacts = {}
for key in ('odb', 'def', 'nl', 'pnl', 'gds', 'mag_gds', 'klayout_gds'):
    if not isinstance(state.get(key), str):
        raise SystemExit(f'Missing completed layout artifact: {key}')
    path = Path(state[key])
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f'Missing completed layout artifact: {key}: {path}')
    artifacts[key] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
config.update(RUN_MAGIC_DRC=True, RUN_KLAYOUT_DRC=True,
              RUN_KLAYOUT_XOR=True, RUN_LVS=True, MAGIC_DRC_USE_GDS=False,
              KLAYOUT_DRC_OPTIONS={'run_mode': 'deep', 'no_recommended': True})
config.pop('EXTRA_SPICE_MODELS', None)
config.pop('//lvs', None)
config['//interface_decks'] = (
    'Magic DRC uses the DEF/LEF view; KLayout DRC evaluates the complete GDS '
    'with the unmodified PDK deck in deep mode, optional recommended rules off. '
    'XOR compares both GDS streams. LVS compares standard cells and every macro '
    'pin, but excludes vendor SRAM interiors by omitting their CDL models. '
    'No checker or timing constraint is relaxed.')
out.mkdir(parents=True)
config_path.write_text(json.dumps(config, indent=4) + '\n')
(out / 'inputs.json').write_text(json.dumps({
    'state': str(state_path),
    'state_sha256': hashlib.sha256(state_path.read_bytes()).hexdigest(),
    'profile_sha256': hashlib.sha256(profile.read_bytes()).hexdigest(),
    'artifacts': artifacts,
    'drc_scope': {'magic': 'DEF/LEF view', 'klayout': 'complete GDS, unmodified PDK deck; deep mode, optional recommended rules off'},
    'lvs_scope': 'standard-cell connectivity and macro pin connectivity; SRAM interiors black-boxed',
}, indent=2) + '\n')
(out / 'input-netlist.txt').write_text(str(Path(state['nl']).resolve()) + '\n')
PY

export PNR_CONFIG="$CONFIG"
export PNR_STATE="$SOC_DIR/pnr/state/${RUN_TAG}-seed.json"
export SYN_NETLIST
SYN_NETLIST=$(cat "$OUT/input-netlist.txt")
export SOC_INTERFACE_FLOW=1
bash "$SOC_DIR/flow/pnr_soc_top.sh" "$RUN_TAG" \
    -F KLayout.XOR -T Checker.LVS -i "$INPUT_STATE" 2>&1 | tee "$OUT/decks.log"
