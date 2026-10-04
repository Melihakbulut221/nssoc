# 117 — Routed PCIe receive, duplex and thermal verification
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured progress — 4 October 2026

The standalone receive framer now passes functional checks after real placement,
clock-tree synthesis and global routing, with positive setup/hold margins under
the unchanged 4 ns clock constraint. The transmit block completed detailed
routing with zero router DRC markers, but its extracted nominal RC reveals
remaining timing violations. **Neither result closes a complete Gen3 x4 PHY,
main-chip physical integration, qualified RC/ESD or production approval.**
[Document 116](116-pcie-receive-clock-layout-and-extraction.md) preserves the
preceding snapshot.

Source commit `caa7cd5337da31302204c3d841a6c1c6f655dd94` contains the implementation and immutable captures.
The [root verification record](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/root-verification.json) records
142 passing focused tests with no skips, source and evidence hashes, and clean
Ruff, workflow schema, SPDX, REUSE and staged whitespace checks. Native tests
below are separate measured runs, not additional unique root pytest cases.

## Receive timing repair and a real constant-connection defect

`soc_pcie_gen3_framer_rx_v2` uses lane-local shift registers instead of four
variable byte selectors, bounds buffer positions to the instantiated capacity,
and registers the outgoing byte. Header length remains 13 bits to reject a
402-byte declaration that would otherwise alias 146 bytes in an 8-bit field.
Output prefetch preserves first-byte latency and stalled data.

The final 14,398-cell mapping passes six native cases. Default and 4,118-byte RTL
configurations each pass six cases. Additional tests exercise 15 capacities,
11 actual HDL faults, the header alias, and 2,104,326 reachable position bounds.

The first physical experiment lost the constant-one driver on 1,200 reset pins.
Native functional expansion detected this despite positive timing numbers.
Those results remain rejected. Explicit native tie mapping and 1,200 physical
tie-high instances repair the connectivity; no exported-text patch or proof
assumption is used. The corrected physical netlist passes the original six port
tests. All 1,796 state identities and 5,419 next-state/clock/reset/output functions
match the original mapped design; ten controls reject faults. This is binary
functional equivalence, not SDF or four-state glitch equivalence.

| Corrected RX global-route estimate | Setup (ns) | Hold (ns) |
|---|---:|---:|
| Slow, 1.08 V, 125 °C | +0.099031 | +0.050644 |
| Typical, 1.20 V, 25 °C | +1.442430 | +0.081384 |
| Fast, 1.32 V, −40 °C | +2.238742 | +0.114237 |

Clock period remains 4 ns, both I/O delays 0.2 ns, input transition 0.1 ns and
output load 0.01 pF. No false paths or relaxed clocks were added. Detailed routing
and extraction remain separate gates. The [complete development capture receipt](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/receive-v2-release.json)
links all earlier variants, failed physical wiring and corrected raw results.
The [physical proof](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/receive-physical-proof.json) and
[control capture](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/receive-v2-controls.json) retain their exact verification scope.

## Actual native duplex packet transport

The new combined TX/RX wrapper connects packet framing, scrambling and the
four-lane block gearboxes. Five RTL cases and the same five cases on an actual
**44,225-cell IHP mapping** pass; ten actual HDL mutations are rejected. The
bench independently encodes RX traffic and uses bit-serial scrambling and CRC
oracles. Native compilation first aborted in Yosys; a fresh run with the same
RTL and recipe plus `YOSYS_MAX_THREADS=1` completed. The original exception is
preserved; thread allocation is consistent with the workaround, but its exact
cause is not proven.

The [native result](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/duplex-native.json),
[root source/XML review](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/duplex-root-review.json) and
[download-verified capture](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/duplex-native-release.json) preserve both attempts.
This wrapper still uses the frozen RXv1 framer. It handles an elastic, externally
aligned and deskewed stream with explicit stream epochs. Continuous serial
sampling, Ordered Sets, LTSSM, saturated throughput, SDF and main-chip physical
integration are not established by these tests. CI runs duplex RTL/mutations;
the native duplex recipe is retained in the local-run capture.

## Transmit detailed routing and the next repair

The first complete TXv3 route has zero final router DRC markers and a netlist
byte-identical to the previously proved, port-tested implementation. This is
signal routing, without a completed power grid or full foundry GDS verification.
Actual nominal OpenRCX extraction produces 226,688 resistor segments and 561,506
coupling capacitors. Under that unqualified nominal RC, slow-corner setup is
−0.974294 ns, removal −0.028608 ns and data hold +0.145084 ns. All three cell
corners use the same nominal RC; these are not RC process-corner results.

All 89 unannotated drivers are verified unconnected outputs of intentional
clock-load cells; no partially annotated driver is reported. A first post-route
repair crashes in native buffer removal and remains recorded. A sizing-only
follow-up resizes 1,784 cells and adds five hold buffers. All 2,158 state identities
and 6,604 functions still match. Its new route and extraction must finish before
any timing improvement is accepted. The [route/nominal-RC receipt](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/tx-detailed-route-release.json)
includes the failures and actual extracted network; the
[repair proof](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/tx-postroute02-proof.json) binds the new exact netlist.

## Preserved thermal failure and phase-aware follow-up

The first 1 µs transistor simulation completed 2,000,011 rows across 167 columns.
All 31 compressed parts are public and hash verified. All seven electrical safety
checks pass, but the original strict producer remains failed. Its end-point
thermal slope reaches 0.03025584 K/ns. The only native warning is a memory-size
advisory: exact ngspice source calculates all samples as in-memory storage even
when they stream to a FIFO. The original log and verdict are unchanged.

Separate cycle integration finds periodic ripple rather than observed final-window
runaway: the largest adjacent cycle-mean drift over all 53 thermal nodes is
1.41063e−6 K/ns. Injected real-wave linear and late drifts are detected. This
diagnosis does not establish timestep convergence or an 8 GHz operating point;
the final measured frequency is 7.702927 GHz.

A separately versioned method now binds the exact source-attributed advisory,
all original output bytes, generated native inputs and complete-cycle coverage.
Its 39 tests and ten phase-analysis tests pass; original 12 ns reductions are
reproduced exactly. A new counterexample shows that growing ripple can pass a mean-only criterion;
minimum/maximum envelopes therefore need a separate guard before stationarity
can be accepted. The [complete first-case replay](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/thermal-first1us-replay-v3.json)
independently downloads all 31 public parts and exactly reproduces the original
electrical, clock and thermal reductions. Its mean-only pass remains bounded by
the [growing-envelope counterexample](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/thermal-mean-only-limitation.json).
The independent half-timestep simulation and an envelope-sensitive method are
still required. Earlier failed methods remain immutable.

## More compact clock/divider layout

The same frozen VCOv3/divide-by-four v5 circuit now occupies
**1,520 × 1,317.03 µm**, compared with the previous 4,800 × 607.03 µm.
Five local groups use Metal4 escapes, Metal5 buses and real peripheral Metal4
clock trunks. The 119 circuit primitives and 31 finite taps remain unchanged.
Main DRC has zero markers in 560 categories; strict deep/flat LVS and LEF checks
pass. Seventeen actual negative controls are rejected, including both new
cross-row clock-trunk open/short faults.

An independent replay compares all 150 native PCell instances on every layer
with zero XOR, verifies all nine physical ports and the seven-layer obstruction
union, and compares every source primitive and connection. The
[native layout package](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/clock-divider-v6.json) and
[independent geometry review](https://github.com/Melihakbulut221/nssoc/blob/caa7cd5337da31302204c3d841a6c1c6f655dd94/hw/soc/pcie-evidence/20261004-routed-rx-and-thermal/clock-divider-v6-peer.json) preserve the
exact checks and raw layouts. No extracted oscillator/divider performance,
PLL/CDR lock, jitter, power-grid or chip-integration acceptance follows from
these geometric results.

## Analog geometry, wire extraction and remaining scope

The unsimplified padded bank preserves all 351 devices, 56 ports and 109 finite
body contacts. Exact routing geometry has 128 conductor components. All 1,061
terminals are accounted for: 748 actual metal reference points and 313 explicit
body/well terminals. Real open and return-net short controls reject. Wire R/C
and substrate spreading resistance are separate; no substrate nodes are united
by name and no vertical resistivity is invented.

Private native crash repair handles isolated ESD devices but still fails on
composite banks. The preserved diagnosis identifies a substrate-slot access,
disconnected 2D substrate regions and HBT terminal-map failures. Finite-field
trials also retain reciprocity failures and native crashes; neither extraction
approach is qualified for RF or full-chip signoff.

Complete PLL/CDR, continuous SERDES ingress,
Ordered Sets/LTSSM, qualified parasitics and ESD stress validation, main-chip
connection, final chip timing and manufacturing approval remain distinct gates.
