#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Random co-simulation of the replay store with SOC_PCIE_REPLAY_AHEAD
# against its default build (docs/combined-timing.md section 18).
#   scripts/check_pcie_replay_ahead.sh OUT [CYCLES] [DEFINE...]
# DEFINE defaults to SOC_PCIE_REPLAY_AHEAD; e.g. SOC_PCIE_REPLAY_AHEAD
# SOC_PCIE_REPLAY_INBANK SOC_PCIE_RESET_COPIES. Both modules come from the
# same hw/soc/rtl/pcie/soc_pcie_replay_tx.v: the reference (with its
# transmit slice) is renamed and compiled without any define, the
# candidate with them. Six runs: four seeds at the SoC's parameters (four
# slots of 38 bytes, timeouts of 256 and 1024 cycles), two at two slots of
# 22 bytes. A run passes only with no output difference in any cycle and
# the bench's coverage counts.
set -euo pipefail
OUT=$1; CYCLES=${2:-300000}
shift; [ $# -gt 0 ] && shift
DEFINES=("$@")
[ ${#DEFINES[@]} -gt 0 ] || DEFINES=(SOC_PCIE_REPLAY_AHEAD)
ROOT=$(cd "$(dirname "$0")/.." && pwd)
RTL=$ROOT/hw/soc/rtl/pcie
mkdir -p "$OUT"
grep -q '^module soc_pcie_replay_tx #($' "$RTL/soc_pcie_replay_tx.v" || { echo "unexpected module header" >&2; exit 1; }
grep -q 'SOC_PCIE_REPLAY_AHEAD' "$RTL/soc_pcie_replay_tx.v" || { echo "the source has no SOC_PCIE_REPLAY_AHEAD block" >&2; exit 1; }
sed -e 's/^module soc_pcie_replay_tx #($/module soc_pcie_replay_tx_ref #(/' \
    -e 's/\bsoc_pcie_stream_skid\b/soc_pcie_stream_skid_ref/g' "$RTL/soc_pcie_replay_tx.v" > "$OUT/reference.v"
BENCH_ARGS=()
{
  for d in "${DEFINES[@]}"; do
    case "$d" in
      SOC_PCIE_REPLAY_AHEAD|SOC_PCIE_REPLAY_INBANK|SOC_PCIE_REPLAY_WRITE_PREDECODE) ;;
      # The candidate has the reset-copy port; the bench drives it with rst_ni.
      SOC_PCIE_RESET_COPIES) BENCH_ARGS+=(-DCOSIM_RESET_COPIES) ;;
      *) echo "unsupported define $d" >&2; exit 2 ;;
    esac
    echo "\`define $d"
  done
  cat "$RTL/soc_pcie_replay_tx.v"
  for d in "${DEFINES[@]}"; do echo "\`undef $d"; done
} > "$OUT/candidate.v"
echo "candidate defines: ${DEFINES[*]}"
fail=0
for cfg in "4 38 256 1" "4 38 256 2" "4 38 1024 3" "4 38 256 4" "2 22 128 5" "2 22 128 6"; do
  read -r depth bytes timeout seed <<< "$cfg"
  name=d${depth}_b${bytes}_t${timeout}_seed${seed}
  iverilog -g2012 -o "$OUT/$name.vvp" ${BENCH_ARGS[@]+"${BENCH_ARGS[@]}"} -Ptb_pcie_replay_ahead.DEPTH=$depth \
    -Ptb_pcie_replay_ahead.MAX_BYTES=$bytes -Ptb_pcie_replay_ahead.TIMEOUT_CYCLES=$timeout \
    "$RTL/soc_pcie_crc32_byte.v" "$OUT/reference.v" "$OUT/candidate.v" "$ROOT/hw/soc/tb/tb_pcie_replay_ahead.v"
  vvp -n "$OUT/$name.vvp" +seed=$seed +cycles=$CYCLES > "$OUT/$name.log" 2>&1 || true
  grep -E "^(SUMMARY|RESULT|MISMATCH)" "$OUT/$name.log" | head -12 | sed "s/^/$name: /"
  grep -q "^RESULT PASS" "$OUT/$name.log" || fail=1
  rm -f "$OUT/$name.vvp"
done
echo "REPLAY_AHEAD_COSIM defines=$(IFS=,; echo "${DEFINES[*]}") fail=$fail"
exit $fail
