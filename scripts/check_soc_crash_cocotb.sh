#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Run an independent cocotb observer on an already built CRASH_DUMP_DEMO.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
BUILD=$(realpath -e "${1:?usage: check_soc_crash_cocotb.sh CRASH_DUMP_DEMO-build-directory}")
COCOTB_CONFIG=${COCOTB_CONFIG:-$ROOT/hw/.venv/bin/cocotb-config}
export PYGPI_PYTHON_BIN=${COCOTB_PYTHON:-$ROOT/hw/.venv/bin/python}
VVP=${VVP:-$(make --no-print-directory -f "$ROOT/hw/soc/tools.soc.mk" printvars | sed -n 's/^VVP="\(.*\)"$/\1/p')}
test -s "$BUILD/tb_soc.vvp"
test -s "$BUILD/flash0.hex"
test -x "$COCOTB_CONFIG"
test -x "$PYGPI_PYTHON_BIN"
test -x "$VVP"
# OSS CAD Suite's launcher overwrites PYTHONHOME with its bundled Python,
# which may differ from the interpreter that installed this cocotb. Its
# bundled libc can also be older than the host Python requires. Use the
# same simulator/libvvp with the host loader and host Python dependencies.
# Native Icarus installations continue to use their configured launcher.
VVP_CMD=("$VVP")
VVP_RELEASE=$(cd "$(dirname "$(readlink -f "$VVP")")/.." && pwd -P)
if [[ -x "$VVP_RELEASE/libexec/vvp" &&
      -f "$VVP_RELEASE/lib/libvvp.so.1" ]] &&
   grep -q 'export PYTHONHOME=' "$VVP"; then
  mkdir -p "$BUILD/cocotb-runtime"
  ln -sfn "$VVP_RELEASE/lib/libvvp.so.1" "$BUILD/cocotb-runtime/libvvp.so.1"
  VVP_CMD=(env "LD_LIBRARY_PATH=$BUILD/cocotb-runtime" "$VVP_RELEASE/libexec/vvp")
fi
unset PYTHONHOME PYTHONEXECUTABLE
export LIBPYTHON_LOC
LIBPYTHON_LOC=$("$COCOTB_CONFIG" --libpython)
export PYTHONPATH="$ROOT/hw/soc/tb/integration${PYTHONPATH:+:$PYTHONPATH}"
export COCOTB_TEST_MODULES=test_crash_recovery COCOTB_TOPLEVEL=tb_soc TOPLEVEL_LANG=verilog
export COCOTB_RESULTS_FILE="$BUILD/crash-cocotb.xml"
rm -f "$COCOTB_RESULTS_FILE"
sha256sum "$BUILD/tb_soc.vvp" "$BUILD/flash0.hex" \
  "$ROOT/hw/soc/tb/integration/test_crash_recovery.py" > "$BUILD/crash-cocotb-inputs.sha256"
"${VVP_CMD[@]}" -M "$("$COCOTB_CONFIG" --lib-dir)" -m "$("$COCOTB_CONFIG" --lib-name vpi icarus)" \
  "$BUILD/tb_soc.vvp" +allow_double_fault +flash0="$BUILD/flash0.hex" \
  2>&1 | tee "$BUILD/crash-cocotb.log"
"$PYGPI_PYTHON_BIN" - "$COCOTB_RESULTS_FILE" <<'PY'
import sys
import xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
cases = list(root.iter('testcase'))
assert len(cases) == 1, f'Expected one completed crash recovery test, found {len(cases)}'
assert not any(list(root.iter(tag)) for tag in ('failure', 'error', 'skipped')), 'Crash recovery test did not pass'
print('cocotb CPU crash recovery: 1 passed, 0 failed, 0 skipped')
PY
