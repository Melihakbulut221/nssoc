# Intrinsic asynchronous preset / first-fall diagnostic

This is a new fixture-driven transistor experiment on the exact source candidate
a83bfc1da87695ae141468452680351077593efe, not the existing 55-device GDS.
Each case contains the actual 241 compact primitives: 106 HBTs, 127 self-heating
rppd resistors and eight intrinsic MIM capacitors. The candidate's topology,
device parameters and independent master/slave preset paths stay unchanged.

## Input evidence and deliberate diagnostic boundary

The completed PLL observer run 40084454916, summary asset 672131330 with SHA256
9656bff3e87627c0529bdff52921f2d8278d48fe05cc76516b507200f9c67863,
observed the actual first-divider output pair
v(xloop.w_t398_c)/v(xloop.w_t389_c).
The fixture uses its median common mode of 2.2605958859271773 V and the explicit
single-ended amplitude min(0.17063108996201803, 0.1730809974856169)/2 V.

The source generates a nominal 4 GHz clock with the original 125 ps UI and
10 ps transitions. It does not replay the PLL waveform. The measured median
period was 229.9490864896042 ps; the original acquisition remains rejected.
Full-capture extrema and median are scalar fixture definitions, not a stable
clock envelope, jitter limit or compliance result.

The external differential ARM stimulus uses the same declared high-CML fixture
levels. It is test equipment at the public interface, not an implemented global
reset driver. All five external sources begin at zero and ramp; the candidate
contains no ideal internal source, IC, nodeset, UIC or forced latch state.

## Fixed finite experiment

Four fresh time-zero cases cover P/P and N/P master/slave presets with initially
high and initially low external differential clocks. Supply is 2.5 V, temperature
27 C, native HBT/RES/CAP typical models. ARM is initially reset, released at
1.75 ns, asserted again while running at 12.03125 ns and released at
14.03125 ns. Every case captures the complete 0–34 ns interval at maximum
0.3125 ps steps with the unchanged tight trapezoidal solver profile.

The observer compares every original 256 UI center against a fixed source-event
state sequence. It measures both first-fall releases, the reset interval and the
master/slave differential margins without any fitted phase or polarity.
The first uninterrupted positive/high root interval is checked against the
original sa/sb oracle. The deliberate reset interrupts that normal stream;
post-reset expectations are prescribed before simulation, never fitted to data.

Every actual HBT collector/base/emitter/substrate and collector current is saved
and bound by recursive source port mapping. All 127 resistor thermal nodes and
every device terminal net are retained. Original limits remain VCE >= 0.4 V after
2 ns, whole-capture absolute VCE <= 1.6 V, VBE <= 1 V and IC/Nx <= 3 mA.
Differential signed margin is 0.1 V. A diagnostic failure remains a failure.

## Runtime and capture

The cloud restores the exact original 109934-byte model bundle and its complete
manifest, plus the separately qualified patched ngspice engine
103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509.
It checks native option readback, all zero-source OP vectors and every binary
capture column/sample. No waveform decimation or selected-column substitution is
used. All successful and failed decks, logs, OP records, complete native raw
files, model manifest and measurements are published from GitHub Actions.

The push job only prepares source and runs controls; it cannot invoke ngspice.
The manual intrinsic job is to be dispatched only after independent source
review. Source-controls and synthetic observer waveforms are not DUT evidence.

## Explicitly open

This first diagnostic has no external output load or downstream selector/child
macro; internal regenerative and reset-selector loading is actual. It is useful
for finding startup, wrong reset sign, release timing, regeneration and device
safety defects before investing in a new layout. It does not close loaded clock
drive, 31-node phase distribution, recovery/removal/metastability, PVT, noise,
new body contacts, DRC/LVS/RC, real ARM distribution, PLL connection or full PHY.
The previous 55-device physical/RC result cannot qualify this 241-device design.
