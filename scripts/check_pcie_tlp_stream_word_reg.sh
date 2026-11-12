#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Random co-simulation of the transaction stream with SOC_PCIE_TX_WORD_REG
# against its default build (docs/combined-timing.md section 17).
#   scripts/check_pcie_tlp_stream_word_reg.sh OUT [CYCLES]
# Both modules come from the same hw/soc/rtl/pcie/soc_pcie_tlp_stream.v:
# the reference is renamed and compiled without the define, the candidate
# with it; each has its own soc_pcie_tlp_regs. Four seeds; a run passes
# only with no output difference in any cycle and the coverage counts of
# the bench (completions with and without data, stalls, APB accesses,
# resets).
set -euo pipefail
OUT=$1; CYCLES=${2:-300000}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
RTL=$ROOT/hw/soc/rtl/pcie
mkdir -p "$OUT"
grep -q '^module soc_pcie_tlp_stream #($' "$RTL/soc_pcie_tlp_stream.v" || { echo "unexpected module header" >&2; exit 1; }
sed 's/^module soc_pcie_tlp_stream #($/module soc_pcie_tlp_stream_ref #(/' "$RTL/soc_pcie_tlp_stream.v" > "$OUT/reference.v"
{ echo '`define SOC_PCIE_TX_WORD_REG'; cat "$RTL/soc_pcie_tlp_stream.v"; echo '`undef SOC_PCIE_TX_WORD_REG'; } > "$OUT/candidate.v"
grep -q 'SOC_PCIE_TX_WORD_REG' "$OUT/reference.v" || { echo "the source has no SOC_PCIE_TX_WORD_REG block" >&2; exit 1; }
fail=0
iverilog -g2012 -o "$OUT/cosim.vvp" "$RTL/soc_pcie_tlp_regs.v" "$OUT/reference.v" "$OUT/candidate.v" \
  "$ROOT/hw/soc/tb/tb_pcie_tlp_stream_word_reg.v"
for seed in 1 2 3 4; do
  vvp -n "$OUT/cosim.vvp" +seed=$seed +cycles=$CYCLES > "$OUT/seed$seed.log" 2>&1 || true
  grep -E "^(SUMMARY|RESULT|MISMATCH)" "$OUT/seed$seed.log" | head -12 | sed "s/^/seed$seed: /"
  grep -q "^RESULT PASS" "$OUT/seed$seed.log" || fail=1
done
rm -f "$OUT/cosim.vvp"
echo "TLP_STREAM_WORD_REG_COSIM fail=$fail"
exit $fail
