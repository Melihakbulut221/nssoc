# Native parent AVDD repair: complete loaded electrical verification

The exact11-feed/33-via physical candidate passed native560DRC/deep-flat484LVS
and alloriginal physical/geometry faults (run39272561102). Fresh full-parent
extraction39274072607 and MIM capture39275348623 preserve the actual11capacitors,
every native primitive terminal and all946 physical reference points.

Validation39276003536 proves native R/C edge/value/ownership and capacitance
conservation with13raw corruptions plus9intrinsic MIM corruptions rejected.
Composition has484native devices,16010R and11677C, exactly one model per each of
the11native MIMs;19composition faults rejected. Exact summary/parts pins are
under docs/evidence/cdr-parent-avdd-v13-mim-*-pass-20261019.json.

The new loaded run uses the original256bits/34.25ns capture with0.3125ps maximum
step,1107 native vectors, actual collector150fF and comparator50fF loads and10ohm
source resistors. Normal early/late data offsets and clock-stopped/VI-bias-off
fault cases remain. Sample phases0.3/0.6/0.9UI,100mV margin and37.5ps
clock-to-valid gate stay fixed; comparator/phase/current/device limits also stay
fixed. Every116HBT/46LVNMOS retains its original safety gate. Exact source-delta
and preserved dependency hash lists enforce this. No retained capacitor is
double-counted and no old interconnect model is reused.

Results must be inspected from the actual new run. Nominal success would still
require PVT and closed-loop clock recovery; these are external8GHz-clock
phase-detector tests. RF/body/reference qualification, full serial Gen3x4 PHY
and mainchip finalsetuphold are not claimed. All execution is in GitHub.
