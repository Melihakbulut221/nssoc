#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Random co-simulation of the receive queue with opt-in timing knobs
# against its default build (docs/combined-timing.md sections 12 and 14).
#   scripts/check_pcie_rx_read_ahead.sh OUT [CYCLES] [DEFINE...]
# DEFINE defaults to SOC_PCIE_RX_READ_AHEAD; e.g. SOC_PCIE_RX_READ2, or
# SOC_PCIE_RX_READ2 SOC_PCIE_RESET_COPIES. Both modules come from the same
# hw/soc/rtl/pcie/soc_pcie_rx_credit.v: the reference is renamed and
# compiled without any define, the candidate with them. Four seeds at the
# SoC's parameters (completer-only), two with requester traffic, two at a
# smaller TLP size and one slot per class.
set -euo pipefail
OUT=$1; CYCLES=${2:-300000}
shift; [ $# -gt 0 ] && shift
DEFINES=("$@")
[ ${#DEFINES[@]} -gt 0 ] || DEFINES=(SOC_PCIE_RX_READ_AHEAD)
ROOT=$(cd "$(dirname "$0")/.." && pwd)
RTL=$ROOT/hw/soc/rtl/pcie/soc_pcie_rx_credit.v
mkdir -p "$OUT"
grep -q '^module soc_pcie_rx_credit #($' "$RTL" || { echo "unexpected module header in $RTL" >&2; exit 1; }
sed 's/^module soc_pcie_rx_credit #($/module soc_pcie_rx_credit_ref #(/' "$RTL" > "$OUT/reference.v"
BENCH_ARGS=()
{
  for d in "${DEFINES[@]}"; do
    case "$d" in
      SOC_PCIE_RX_READ_AHEAD|SOC_PCIE_RX_READ2|SOC_PCIE_RX_STAGED_COMMIT) ;;
      # The candidate has the reset-copy port; the bench drives it with rst_ni.
      SOC_PCIE_RESET_COPIES) BENCH_ARGS+=(-DCOSIM_RESET_COPIES) ;;
      *) echo "unsupported define $d" >&2; exit 2 ;;
    esac
    echo "\`define $d"
  done
  cat "$RTL"
  for d in "${DEFINES[@]}"; do echo "\`undef $d"; done
} > "$OUT/candidate.v"
echo "candidate defines: ${DEFINES[*]}"
fail=0
for cfg in "8 2 1 1" "8 2 1 2" "8 2 1 3" "8 2 1 4" "8 2 0 5" "8 2 0 6" "4 1 0 7" "4 1 1 8"; do
  read -r dw slots co seed <<< "$cfg"
  name=dw${dw}_s${slots}_c${co}_seed${seed}
  iverilog -g2012 -o "$OUT/$name.vvp" ${BENCH_ARGS[@]+"${BENCH_ARGS[@]}"} -Ptb_pcie_rx_credit_read_ahead.MAX_TLP_DWORDS=$dw \
    -Ptb_pcie_rx_credit_read_ahead.SLOTS_PER_CLASS=$slots -Ptb_pcie_rx_credit_read_ahead.COMPLETER_ONLY=$co \
    "$OUT/reference.v" "$OUT/candidate.v" "$ROOT/hw/soc/tb/tb_pcie_rx_credit_read_ahead.v"
  vvp -n "$OUT/$name.vvp" +seed=$seed +cycles=$CYCLES > "$OUT/$name.log" 2>&1 || true
  grep -E "^(SUMMARY|RESULT|MISMATCH)" "$OUT/$name.log" | head -12 | sed "s/^/$name: /"
  grep -q "^RESULT PASS" "$OUT/$name.log" || fail=1
  rm -f "$OUT/$name.vvp"
done
echo "RX_CREDIT_COSIM defines=$(IFS=,; echo "${DEFINES[*]}") fail=$fail"
exit $fail
