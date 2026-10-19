# Read-only transmitter stage and actual clock-terminal review

The completed strap6 nominal capture still rejects140 output samples and24HBTs.
The prior physical mapping placed18 failed HBTs in p8 macros and6 in the final
macro. Current interface gates also reject level8/level4; final strap widening
alone did not resolve these gates.

The new cloud review restores the exact strap6 full waveform and composed
wire model, reproduces every original engineering gate, then maps all31 clock
ports through the actual116611-resistor graph to124 native selector bases.
It measures saved public and transistor-base differential edge brackets,
native common-mode/amplitude and incident wire capacitance for all62 clock
conductors. Per-terminal measurements are retained; no averaging hides
skew. Same-polarity edge association is diagnostic and does not alter sampling
phases or turn a failed waveform into a pass. Intrinsic device capacitance,
RF distribution and substrate qualification are outside this wire-C report.

This reuses the complete saved native waveform; no new transient is started.
Original data truth, loads, voltages and device gates remain unchanged.
The active trunk256, CDR localbus and mainchip route jobs are preserved.
