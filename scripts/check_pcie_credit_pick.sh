#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Random co-simulation of the credit transmitter with SOC_PCIE_CREDIT_PICK
# against its default build (docs/combined-timing.md section 19).
#   scripts/check_pcie_credit_pick.sh OUT [CYCLES]
# Both modules come from the same hw/soc/rtl/pcie/soc_pcie_credit_tx.v:
# the reference is renamed and compiled without the define, the candidate
# with it. Four seeds; a run passes only with no output difference in any
# cycle and the bench's coverage counts (grants, replays, limit updates,
# initializations, protocol errors, link losses, resets).
set -euo pipefail
OUT=$1; CYCLES=${2:-300000}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
RTL=$ROOT/hw/soc/rtl/pcie/soc_pcie_credit_tx.v
mkdir -p "$OUT"
grep -q '^module soc_pcie_credit_tx ($' "$RTL" || { echo "unexpected module header in $RTL" >&2; exit 1; }
grep -q 'SOC_PCIE_CREDIT_PICK' "$RTL" || { echo "the source has no SOC_PCIE_CREDIT_PICK block" >&2; exit 1; }
sed 's/^module soc_pcie_credit_tx ($/module soc_pcie_credit_tx_ref (/' "$RTL" > "$OUT/reference.v"
{ echo '`define SOC_PCIE_CREDIT_PICK'; cat "$RTL"; echo '`undef SOC_PCIE_CREDIT_PICK'; } > "$OUT/candidate.v"
fail=0
iverilog -g2012 -o "$OUT/cosim.vvp" "$OUT/reference.v" "$OUT/candidate.v" "$ROOT/hw/soc/tb/tb_pcie_credit_pick.v"
for seed in 1 2 3 4; do
  vvp -n "$OUT/cosim.vvp" +seed=$seed +cycles=$CYCLES > "$OUT/seed$seed.log" 2>&1 || true
  grep -E "^(SUMMARY|RESULT|MISMATCH)" "$OUT/seed$seed.log" | head -12 | sed "s/^/seed$seed: /"
  grep -q "^RESULT PASS" "$OUT/seed$seed.log" || fail=1
done
rm -f "$OUT/cosim.vvp"
echo "CREDIT_PICK_COSIM fail=$fail"
exit $fail
