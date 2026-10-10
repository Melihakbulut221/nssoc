# 114 — PCIe TX timing, interstage clock limiting and finite taps
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured progress — 4 October 2026

The later complete native-bank connectivity repair, packet framing and TX
function proof are recorded in [document 115](115-pcie-framing-and-native-bank.md).
The earlier failures and open states below remain the original checkpoint.

The standalone four-lane TX path now passes its three-corner **global-route
estimated** setup/hold screen at 4 ns. A transistor clock limiter fixes the
selected divider failures. Native extraction now preserves finite substrate
contacts, while a complete padded-bank comparison exposes missing ESD devices
and disconnected serial ports in the Magic result. These results advance the
open GR801-class design; full Gen3 x4 and main-chip physical acceptance remain
open. The preceding measurements are retained in
[document 113](113-pcie-clocked-pads-and-transport.md).

The analog/extraction sources and compact captures are pinned to
`f3e580fa9bd072c91837dd7d219b30bfea0ab519`. The
[root integrity receipt](https://github.com/Melihakbulut221/nssoc/blob/f3e580fa9bd072c91837dd7d219b30bfea0ab519/hw/soc/pcie-evidence/20261004-timing-and-taps/root-frozen-verification.json)
checks 17 live source pins and four whole capsules. Root reruns pass 41 new
divider tests, 49 finite-tap tests and 45 thermal/streaming tests. These checks
do not replace native waveform measurement or physical signoff.

## TX feedback and physical timing

The original conditional scrambler feedback failed the 4 ns cell-only screen.
TXv2 replaces that chain with balanced prefix byte counts and constant GF(2)
state transforms. Its functional checks pass, but the slow-corner preplacement
screen remains negative. TXv3 registers the incoming block and its prefix
counts before state selection. The extra initial cycle preserves sustained
word throughput and reset/flush behavior.

| Development implementation | Native IHP cells | RTL / native cases | Actual rejected RTL faults | Repaired preplacement SS setup |
|---|---:|---:|---:|---:|
| TXv2 parallel prefix | 20,846 | 3 / 3 | 10 | −0.932817 ns |
| TXv3 two-stage pipeline | 25,697 | 3 / 3 | 12 | +0.433223 ns |

Each runner also passes three process-lifetime controls. The source-bound
[TXv2 capture](https://github.com/Melihakbulut221/nssoc/blob/3e8f86081df7098c4bcb1966b9758b33a74becc0/hw/soc/pcie-evidence/20261004-timing-and-taps/tx-path-v2.json)
and [TXv3 capture](https://github.com/Melihakbulut221/nssoc/blob/3e8f86081df7098c4bcb1966b9758b33a74becc0/hw/soc/pcie-evidence/20261004-timing-and-taps/tx-path-v3.json)
retain failed predecessors, native logs, actual mutations and independent
source/output reviews. The saturated TXv3 case transfers 495 blocks and 2,010
words without steady-state bubbles. This is a transport test with explicit
caller-supplied masks, not complete ordered-set policy or a trained PCIe link.

Actual TXv3 placement, CTS and global routing use the same 4 ns target, 0.2 ns
I/O delays, 0.1 ns input transition and 0.01 pF output load. All three native
SG13G2 Liberty corners are loaded together. Clocks propagate through the real
CTS tree. No false paths, multicycle exceptions or clock relaxation are added.
Initial placement gives −2.149679 ns setup; initial global routing gives
−0.404412 ns setup and −0.002553 ns hold. Electrical repair, explicit input
buffering and a further setup repair produce:

| Cell corner | Setup slack | Hold slack |
|---|---:|---:|
| Slow, 1.08 V, 125 °C | +0.018697 ns | +0.066373 ns |
| Typical, 1.20 V, 25 °C | +1.477523 ns | +0.114728 ns |
| Fast, 1.32 V, −40 °C | +2.243468 ns | +0.148566 ns |

The final report has zero slew/capacitance violations and zero setup TNS.
The requested additional 0.10 ns setup margin is **not** achieved; the native
optimizer warning remains in the capture. All three original port tests pass
again against the exact repaired netlist. Icarus does not implement the cell
timing checks, and this replay has no SDF; it establishes functional behavior
separately from STA. Full formal equivalence after resizing/pin swaps remains
a separate verification step at this checkpoint.

The [physical timing receipt](https://github.com/Melihakbulut221/nssoc/blob/eaaf104bb63ca1271c39f9dd9d1b8314b59c9929/hw/soc/pcie-evidence/20261004-timing-and-taps/tx-v3-global-route.json)
and [63-member native archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/pcie-tx-path-v3-global-route-native-20261004.tar.xz)
retain all placement/CTS/global-route databases, constraints, netlists and
failed repairs. Archive bytes were verified through authenticated and public
downloads. RC is estimated from routing with Metal2 signal / Metal4 clock
parameters. This is a standalone block without a complete power grid,
qualified extracted RC, final detailed-route DRC/LVS or main-chip adoption.

## Transistor divider repair

Divider v3 increases four second-stage latch loads. It restores amplitude at
the previously failing hot/slow point but produces extra output transitions,
so it fails division. V4 inserts a real four-HBT interstage limiter and restores
the divide relation; its hot/slow second-clock amplitude still misses the
unchanged ±0.30 V target. Both failures remain recorded.

V5 changes only the two limiter collector resistor lengths from 4.0 to 4.4 µm.
The native circuit has 64 HBTs, 42 resistors, 12 MIM capacitors and one HV PMOS.
All eight selected positive cases pass, and four actual functional faults are
rejected. Each execution has clean native diagnostics and explicitly verified
zero operating-point startup. At hot/slow the input/output frequencies are
6.79774 / 1.69945 GHz; nominal is 8.04729 / 2.0119 GHz. This verifies division
of the measured oscillator frequency, not lock to an exact reference.

Margins remain narrow: the worst positive settled VCE is 0.405311 V against a
0.4 V lower guard, and the weakest second-clock peak is 0.306914 V against
0.30 V. Upper VCE and current checks cover the full capture; the lower VCE
guard applies after 4 ns. Negative cases that violate electrical limits are
not counted as safe positive cases. The
[divider receipt and raw-wave references](https://github.com/Melihakbulut221/nssoc/blob/f3e580fa9bd072c91837dd7d219b30bfea0ab519/hw/soc/pcie-evidence/20261004-timing-and-taps/divider-limiter-v3-v5.json)
retain all 18 new pilot/campaign waves with author remeasurement and immutable
public preservation. No independent second simulator, complete PVT/mismatch,
jitter, extracted layout, closed PLL or CDR is claimed.

## Finite contacts and the remaining full-bank failure

The private Magic correction scales native area/perimeter resistance
coefficients with the extraction grid and removes premature integer
truncation. It preserves distinct tap and body nodes. An isolated fixture
recovers 108 substrate and 24 well branches across three sizes and all eight
orientations. Both 5 nm and 10 nm internal grids give the same physical result;
a 2 × 2 µm contact is 81.6667 Ω. Strict native KLayout comparison and three
actual geometry faults pass their expected outcomes. The
[finite-tap evidence](https://github.com/Melihakbulut221/nssoc/blob/f3e580fa9bd072c91837dd7d219b30bfea0ab519/hw/soc/pcie-evidence/20261004-timing-and-taps/finite-taps.json)
records the private build and preserves the original PDK/runtime unchanged.

Applying that extractor to the unchanged actual padded bank recovers all 108
`SUB`–`ESD_RETURN` finite taps and its well tap. The **complete Magic graph
still fails**: 32 ESD devices are absent and all 16 serial pad ports are
disconnected from their expected functional terminals. Even the partial graph
without ESD does not match. The
[failed bank audit](https://github.com/Melihakbulut221/nssoc/blob/f3e580fa9bd072c91837dd7d219b30bfea0ab519/hw/soc/pcie-evidence/20261004-timing-and-taps/padded-bank-native-failure.json)
preserves that result separately from the earlier passing KLayout DRC/LVS.
No devices were blackboxed or omitted to turn this comparison into a pass.
Native ESD recognition and pad-stack connectivity require further correction.

## Longer thermal observation

The earlier 40 ns oscillator observations still fail thermal convergence;
their [complete waves are now public](https://github.com/Melihakbulut221/nssoc/blob/f3e580fa9bd072c91837dd7d219b30bfea0ab519/hw/soc/pcie-evidence/20261004-timing-and-taps/thermal40-full-waves-release.json).
Native resistor-model calibration measures five thermal time constants between
69.60 and 84.37 ns and verifies the energy balance and powered DC endpoint.
The model equations give a 99 ns passive upper bound. This motivates longer
cold-start observation; it does not guarantee nonlinear oscillator equilibrium.
The [calibration receipt](https://github.com/Melihakbulut221/nssoc/blob/f3e580fa9bd072c91837dd7d219b30bfea0ab519/hw/soc/pcie-evidence/20261004-timing-and-taps/thermal-poles.json)
includes two real negative controls among four native runs.

A separate tiny capture prototype compares ordinary-file and FIFO binary
output in four real 1 ns executions, including two actual late rail-collapse
faults. Both output pairs agree exactly, and the faults remain visible. The
[source-bound streaming receipt](https://github.com/Melihakbulut221/nssoc/blob/f3e580fa9bd072c91837dd7d219b30bfea0ab519/hw/soc/pcie-evidence/20261004-timing-and-taps/streaming.json)
and independent peer audit establish recording continuity only. A longer
bounded-publication method is under development; these 1 ns tests do not
establish 1 µs behavior or thermal closure.

Full SERDES/PCS/LTSSM, PLL/CDR, qualified coupled/substrate extraction and ESD,
main-chip clock/reset/pad integration, the earlier Ethernet/NPU timing and
full-chip I/O LVS gates, DFT and manufacturing approval remain open.
