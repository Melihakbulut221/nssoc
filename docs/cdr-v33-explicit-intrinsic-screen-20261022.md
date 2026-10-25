# V33 exploratory intrinsic screen on frozen v32 wiring

V32 passed nominal device gates but worsened C/D settling after stronger slave bleeds. The new experiment separates that change from collector loading in the current476-device model:

- bleed12: restore only slave track/hold bleeds from6.4/4.8um to12.8/9.6um; keep2.6um collector loads.
- load20: same bleed restoration plus16 sampler collector-load lengths2.6 to2.0um at unchanged32um width.
- load16: same bleed restoration plus collector-load lengths2.6 to1.6um.

The0.9um input bias resistors that improved nominal headroom remain unchanged. Physical slave selectors and collector-load identities are derived from v32 native master/slave topology. Counts, widths and original lengths are asserted before any change.

These are intrinsic PDK parameter screens. Candidate layouts and fresh RC do not yet exist; all17918 wire resistors and12850 wire capacitors remain identical circuit cards. The original model is preserved beside each explicit candidate and changed composition.

Each variant retains all256 bits, full34.25ns/.3125ps capture,1104 columns, original clock/data phase,150fF/50fF loads,37.5ps deadline and all transistor/MOS/phase/VI gates. Both early and late cases run. Every rejection is published with the complete waveform. No outcome closes physical CDR or full PHY. A useful result selects a real GDS candidate that must independently pass DRC/LVS, fresh extraction and all original loaded tests.

The older v5 resistor screen had different484-device wiring and major access losses; its failures remain recorded. This screen tests the measured v32 topology, not a claim that reducing loads necessarily fixes the circuit.
