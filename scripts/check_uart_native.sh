#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Re-run the serial/APB contracts on an IHP-mapped UART with untouched models.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$ROOT"
OUT=$(realpath -m "${1:-hw/soc/out/uart-native}")
case "$OUT" in "$ROOT"/hw/soc/out/*) ;; *) echo 'Output must be inside hw/soc/out' >&2; exit 2 ;; esac
[ ! -e "$OUT" ] || { echo "Refusing to replace evidence: $OUT" >&2; exit 2; }
PY=${PY:-$ROOT/hw/.venv/bin/python}
export PATH="$(dirname "$PY"):$PATH"
# Like cocotb's Python runner, preserve this interpreter's search path.
# OSS CAD Suite's vvp launcher exports its own PYTHONHOME; Makefile-driven
# embedding otherwise searches that suite for the venv's Python stdlib.
export PYTHONPATH
PYTHONPATH=$("$PY" -c 'import os,sys; print(os.pathsep.join(sys.path))')
command -v cocotb-config >/dev/null
command -v yosys >/dev/null
command -v iverilog >/dev/null
mkdir -p "$OUT"
if [ -z "${PDK:-}" ]; then
    "$PY" hw/soc/flow/prepare_ihp_native_boot.py > "$OUT/prepare.log"
    PDK="$ROOT/hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2"
fi
PDK=$(realpath "$PDK")
LIB="$PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib"
MODEL="$PDK/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v"
export OUT LIB MODEL
"$PY" - <<'PY'
from pathlib import Path
import hashlib, json, os
out=Path(os.environ['OUT']); lib=Path(os.environ['LIB']); model=Path(os.environ['MODEL'])
sources=[Path('scripts/check_uart_native.sh'),Path('hw/soc/rtl/soc_uart.v'),lib,model]
sources += [Path('hw/soc/tb/cocotb')/p for p in (
    'Makefile.soc_uart','Makefile.soc_uart_rx','test_soc_uart.py',
    'test_soc_uart_rx.py','test_soc_uart_defects.py')]
identities={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
(out/'inputs.json').write_text(json.dumps(identities,indent=2)+'\n')
def q(p):
    s=str(p.resolve())
    if any(c in s for c in '\n\r"\\'):
        raise ValueError('Unsupported Yosys path')
    return '"'+s+'"'
text=f'read_verilog {q(Path("hw/soc/rtl/soc_uart.v"))}\nhierarchy -check -top soc_uart\nsynth -top soc_uart -flatten\n'
text+=f'dfflibmap -liberty {q(lib)}\nabc -liberty {q(lib)} -D 20000\nclean\n'
text+=f'tee -o {q(out/"area.rpt")} stat -liberty {q(lib)}\nwrite_verilog -noattr {q(out/"netlist.v")}\nwrite_json {q(out/"netlist.json")}\n'
(out/'synth.ys').write_text(text)
PY
yosys -V > "$OUT/yosys-version.log"
iverilog -V > "$OUT/iverilog-version.log" 2>&1
timeout 300 yosys -Q -T "$OUT/synth.ys" > "$OUT/synth.log" 2>&1
for suite in soc_uart soc_uart_rx test_soc_uart_defects; do
    mk=Makefile.soc_uart
    [ "$suite" != soc_uart_rx ] || mk=Makefile.soc_uart_rx
    module=$suite
    [ "$suite" = test_soc_uart_defects ] || module=test_$suite
    timeout 300 make -C hw/soc/tb/cocotb -f "$mk" \
        "COCOTB_TEST_MODULES=$module" "MODULE=$module" \
        "VERILOG_SOURCES=$OUT/netlist.v $MODEL" \
        "SIM_BUILD=$OUT/$suite/build" "COCOTB_RESULTS_FILE=$OUT/$suite/results.xml" \
        > "$OUT/$suite.log" 2>&1
done
"$PY" - <<'PY'
from pathlib import Path
import ast, collections, hashlib, json, os, xml.etree.ElementTree as ET
out=Path(os.environ['OUT'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
identities=json.loads((out/'inputs.json').read_text())
assert all(sha(Path(p))==h for p,h in identities.items()), 'Inputs changed while running'
cells=json.loads((out/'netlist.json').read_text())['modules']['soc_uart']['cells']
types=collections.Counter(c['type'] for c in cells.values())
assert types and all(t.startswith('sg13g2_') for t in types), 'Unmapped cells'
tests={}
for suite in ['soc_uart','soc_uart_rx','test_soc_uart_defects']:
    module=suite if suite.startswith('test_') else 'test_'+suite
    source=Path('hw/soc/tb/cocotb')/(module+'.py')
    tree=ast.parse(source.read_text())
    expected={n.name for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and
              any(ast.unparse(d).startswith('cocotb.test(') for d in n.decorator_list)}
    xml=out/suite/'results.xml'; rows=ET.parse(xml).findall('.//testcase')
    assert expected and len(rows)==len(expected) and {t.get('name') for t in rows}==expected
    assert all(not any(t.find(x) is not None for x in ['failure','error','skipped']) for t in rows)
    tests[suite]={'passed':len(rows),'xml_sha256':sha(xml),'log_sha256':sha(out/(suite+'.log'))}
result=dict(status='PASS',scope='IHP standard-cell UART functional simulation, no SDF, layout, analog CDC or fault qualification.',
            source_sha256=identities,sources_unchanged=True,tests=tests,cell_types=dict(types),
            netlist_sha256=sha(out/'netlist.v'),area_report=(out/'area.rpt').read_text(),
            yosys_version=(out/'yosys-version.log').read_text().strip(),
            iverilog_version=(out/'iverilog-version.log').read_text().splitlines()[0])
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS native UART:',sum(t['passed'] for t in tests.values()),'serial/APB tests')
PY
