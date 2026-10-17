#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Functional RAM parity using native, checksum-pinned IHP macro models.
# PDK is an explicit override to an already installed ihp-sg13g2 directory.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$ROOT"
OUT=$(realpath -m "${1:-hw/soc/out/memory-parity}")
case "$OUT" in "$ROOT"/hw/soc/out/*) ;; *) echo 'Output must be inside hw/soc/out' >&2; exit 2 ;; esac
[ ! -e "$OUT" ] || { echo "Refusing to replace evidence: $OUT" >&2; exit 2; }
PY=${PY:-$ROOT/hw/.venv/bin/python}
command -v iverilog >/dev/null
mkdir -p "$OUT"
if [ -z "${PDK:-}" ]; then
    "$PY" hw/soc/flow/prepare_ihp_native_boot.py > "$OUT/prepare.log"
    PDK="$ROOT/hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2"
fi
iverilog -V > "$OUT/iverilog-version.log" 2>&1
for harden in 0 1; do
    for words in 8192 16384; do
        [ "$harden:$words" != 1:16384 ] || continue
        for rdreg in 0 1; do
            name="h${harden}-w${words}-r${rdreg}"
            timeout 300 "$PY" hw/soc/flow/sim_mem_parity.py --pdk "$PDK" \
                --output "$OUT/$name" --harden "$harden" --words "$words" \
                --rdreg "$rdreg" > "$OUT/$name.log" 2>&1
            echo "PASS RAM parity $name"
        done
    done
done
# Deliberately corrupt the macro read bus in a scratch RTL copy. The same
# test must reject it after elaboration, rather than merely fail to build.
"$PY" - "$OUT" <<'PY'
from pathlib import Path
import sys
out = Path(sys.argv[1])
source = Path('hw/soc/rtl/soc_mem_sram.v').read_text()
old = 'assign row_dout = dsel;'
assert source.count(old) == 1
(out / 'negative-macro.v').write_text(source.replace(old, "assign row_dout = dsel ^ 64'h1;"))
PY
set +e
timeout 300 "$PY" hw/soc/flow/sim_mem_parity.py --pdk "$PDK" \
    --output "$OUT/negative" --macro-source "$OUT/negative-macro.v" \
    > "$OUT/negative.log" 2>&1
code=$?
set -e
[ "$code" = 1 ] || { echo "Negative control returned $code instead of assertion failure" >&2; exit 1; }
"$PY" - "$OUT" <<'PY'
from pathlib import Path
import json, sys, xml.etree.ElementTree as ET
out = Path(sys.argv[1]); result = json.loads((out / 'negative/result.json').read_text())
assert not result['passed'] and result['tests'] == 1 and result['sources_unchanged']
assert result['macro_source_override']
assert ET.parse(out / 'negative/results.xml').find('.//testcase/failure') is not None
assert 'AssertionError' in (out / 'negative.log').read_text()
print('EXPECTED FAIL: corrupted macro read bus rejected by functional assertion')
PY
