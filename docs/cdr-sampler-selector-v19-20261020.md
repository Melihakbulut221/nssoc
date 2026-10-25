# Native clock-selector size candidate

The rejected complete v16 waveform showed external-clock to native base-pair
crossing offsets of roughly 4.5 to 9.3 ps and track/hold collector-current steering
offsets of roughly 16 to 21 ps. These are observed nearest-edge offsets, not a
causal-delay proof. A/B output settling reached roughly 46 to 53 ps and exceeded
the unchanged 37.5 ps requirement. The v18 band reorder did not close this gap.

This candidate changes only the eight master/slave clock-steering HBTs
M_CS0/M_CS1/M_CH0/M_CH1/S_CS0/S_CS1/S_CH0/S_CH1 from Nx=8 to Nx=4.
The hypothesis is reduced clock-node capacitance and faster current steering.
Increased current density and changed junction voltages may instead reject it.
No benefit is claimed before the actual loaded native simulation.

Data and regenerative HBT sizes, all nine MOS devices, twelve resistors,
seventeen physical substrate taps, tail-current geometry, public port inventory,
and schematic topology are retained. Native PCells are regenerated with the
new selector geometry. An independent checker verifies 46 unchanged primitive
drawings/parameters, the eight explicit parameter changes and changed drawings.
Unsimplified deep and flat 54-device LVS must prove actual new dimensions and
connectivity. The original 560-rule DRC, LEF checks and physical/reference faults
remain, with an additional wrong-selector-Nx reference fault. Source-delta
checks bind all method changes and exactly eight schematic parameter edits.

This is a separate candidate; rejected v16/v18 evidence is retained. A passing
leaf layout is only the first prerequisite. The whole parent must be rebuilt,
fresh native terminal/plane/R/C extraction performed, and original full loaded
34.25 ns / 256-bit early/late and fault cases repeated. Old wire RC is not
qualified for changed geometry. Original voltage/current, sampling, phase,
load, solver and duration gates must not change. Full CDR/PLL, x4 serial PHY,
mainchip route, final timing and production acceptance remain open.
