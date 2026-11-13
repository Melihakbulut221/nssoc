# Slave-latch load/sink co-scaling experiment

This is a rejected-baseline circuit experiment, not a new layout or accepted PHY.
The baseline is lowz4_bd10. Native topology report run43472881982 binds the eight
slave collector loads and four 16-device slave-tail banks. The experiment sets
m=2 on only those 64 MOS sinks and eight rppd loads. Master tails and all bench
reference currents remain unchanged. Existing lowz4 divider and bd10 headroom
changes are retained.

Hypothesis: parallel sink/load scaling can reduce the slave output resistance
while approximately preserving its nominal current-times-load voltage drop.
This is not a predicted pass: wire IR drop, altered capacitance, device bias,
clock steering, master timing and downstream XOR delay can still reject it.
Unlike earlier reference-current-only trials, this isolates slave stages and
also changes their collector loads. All original external loads, input bits,
clock, simulator options and measurement thresholds remain unchanged.

Effective primitive multiplicity increases by 72; the original extracted wire
geometry is only an experimental approximation. The report cannot be called a
fresh actual650 extraction. No physical implementation or acceptance is claimed.
The complete resulting native waveform and circuit inputs are retained in a
separate cloud artifact. Frozen data, device, phase and VI checks decide the
electrical outcome. A useful candidate would still need real layout, DRC/LVS,
fresh extraction and rerunning all required cases.
