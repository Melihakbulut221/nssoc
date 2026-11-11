#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Random co-simulation of the receive queue with SOC_PCIE_RX_READ_AHEAD
# against its default build (docs/combined-timing.md section 12).
#   scripts/check_pcie_rx_read_ahead.sh OUT [CYCLES]
# Both modules come from the same hw/soc/rtl/pcie/soc_pcie_rx_credit.v: the
# reference is renamed and compiled without the define, the candidate with
# it. Four seeds at the SoC's parameters (completer-only), two with
# requester traffic, two at a smaller TLP size and one slot per class.
set -euo pipefail
OUT=$1; CYCLES=${2:-300000}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
RTL=$ROOT/hw/soc/rtl/pcie/soc_pcie_rx_credit.v
mkdir -p "$OUT"
grep -q '^module soc_pcie_rx_credit #($' "$RTL" || { echo "unexpected module header in $RTL" >&2; exit 1; }
sed 's/^module soc_pcie_rx_credit #($/module soc_pcie_rx_credit_ref #(/' "$RTL" > "$OUT/reference.v"
{ echo '`define SOC_PCIE_RX_READ_AHEAD'; cat "$RTL"; echo '`undef SOC_PCIE_RX_READ_AHEAD'; } > "$OUT/candidate.v"
fail=0
for cfg in "8 2 1 1" "8 2 1 2" "8 2 1 3" "8 2 1 4" "8 2 0 5" "8 2 0 6" "4 1 0 7" "4 1 1 8"; do
  read -r dw slots co seed <<< "$cfg"
  name=dw${dw}_s${slots}_c${co}_seed${seed}
  iverilog -g2012 -o "$OUT/$name.vvp" -Ptb_pcie_rx_credit_read_ahead.MAX_TLP_DWORDS=$dw \
    -Ptb_pcie_rx_credit_read_ahead.SLOTS_PER_CLASS=$slots -Ptb_pcie_rx_credit_read_ahead.COMPLETER_ONLY=$co \
    "$OUT/reference.v" "$OUT/candidate.v" "$ROOT/hw/soc/tb/tb_pcie_rx_credit_read_ahead.v"
  vvp -n "$OUT/$name.vvp" +seed=$seed +cycles=$CYCLES > "$OUT/$name.log" 2>&1 || true
  grep -E "^(SUMMARY|RESULT|MISMATCH)" "$OUT/$name.log" | head -12 | sed "s/^/$name: /"
  grep -q "^RESULT PASS" "$OUT/$name.log" || fail=1
  rm -f "$OUT/$name.vvp"
done
echo "READ_AHEAD_COSIM fail=$fail"
exit $fail
