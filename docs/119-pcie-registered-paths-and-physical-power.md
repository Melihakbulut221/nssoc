# 119 — Registered PCIe paths and physical supply repair
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured development — 4 October 2026

The transmitter now registers its parallel scrambling candidates before selecting
them. A separate byte receiver registers its next read address. Both pass their
native-cell functional tests. Actual powered analog extraction also identified
excessive supply resistance, leading to a real metal/via revision and a repair
to an integer-overflow defect in the private extractor.

**Full Gen3 x4, closed-loop PLL/CDR, complete SERDES/PCS/LTSSM, qualified
parasitics/ESD, main-chip physical integration and production approval remain
open.** These are separate measured development steps, not a combined signoff.

Source commit `219b734012626ee8a424d9e385d23e0a844f2934` contains the implementation
and [root verification record](https://github.com/Melihakbulut221/nssoc/blob/219b734012626ee8a424d9e385d23e0a844f2934/hw/soc/pcie-evidence/20261004-timing-and-power/root-verification.json).
Its five disjoint focused pytest groups total **81 passed, zero failed, zero
skipped**. Native simulation, geometry and independent waveform cases below are
separate evidence, not additional unique pytest cases. [Document 118](118-pcie-continuous-ingress-and-phase-detector.md)
retains the preceding continuous-input and transistor phase-detector snapshot.

## Registered transmit and receive paths

The TX v4 stage captures all candidate scrambling masks and next-state rows
before selecting the accepted byte-count result. The real LFSR updates only when
that pending block is consumed. Input acceptance takes two cycles; the downstream
fixed 130/32 gearbox needs one block every 4.0625 cycles, so this staging retains
the demonstrated continuous-word rate without assuming a multicycle exception.
Headers, byte advance/XOR controls, reseeding, reset, flush and backpressure retain
their independent serial-oracle checks.

The new transmitter maps to **29,722 IHP cells** and passes three native tests.
Fourteen actual HDL faults and three process-lifetime controls pass their expected
rejection checks. After placement, clock-tree construction and global-route
repair, a complete native-Liberty Boolean comparison matches **3,850 state
elements and all 11,680 next-state/clock/reset/output functions**. Four actual
boundary inversions and six malformed-graph controls are rejected. The exact
repaired physical netlist also passes the original three port tests.

The following slacks use global-route estimates at the unchanged 4 ns clock,
0.2 ns input/output delay, 0.1 ns input slew and 0.01 pF output load:

| Cell corner | Setup, ns | Data hold, ns | Recovery, ns | Removal, ns |
| --- | ---: | ---: | ---: | ---: |
| SS | +0.096377 | +0.042409 | +0.152741 | +0.163086 |
| TT | +1.452184 | +0.085771 | +1.490495 | +0.159310 |
| FF | +2.226806 | +0.115435 | +2.295528 | +0.163655 |

These are **not detailed-route or qualified-RC results**. Detailed TX v4 routing
continues. The [physical-function receipt](https://github.com/Melihakbulut221/nssoc/blob/219b734012626ee8a424d9e385d23e0a844f2934/hw/soc/pcie-evidence/20261004-timing-and-power/tx-grt.json)
and [public archive receipt](https://github.com/Melihakbulut221/nssoc/blob/219b734012626ee8a424d9e385d23e0a844f2934/hw/soc/pcie-evidence/20261004-timing-and-power/tx-grt-release.json)
preserve the actual netlists, reports, proof inputs and simulator output.

The older RX v2 post-repair detailed route completed with zero router-reported
DRC violations. Fresh extraction nevertheless leaves **SS setup −0.768632 ns
and data hold −0.007571 ns**; recovery is +1.065718 ns and removal +0.491873 ns.
The nominal PDK RC model is reused across three cell corners, not qualified as
three process-RC corners. A zero router-DRC report does not establish foundry DRC.

Its critical path combines an address increment with the large packet-data
selector. The additive `soc_pcie_gen3_framer_rx_prefetch` module stores the
one-byte-ahead address, preserving the byte interface and output latency while
separating that carry propagation from the selector. It maps to **14,404 IHP
cells** and passes all six frozen receive cases. The same six cases pass at the
4,118-byte RTL capacity; 29 focused boundary, alias and actual-fault controls
also pass. Its physical closure is still in progress. The [receive receipt](https://github.com/Melihakbulut221/nssoc/blob/219b734012626ee8a424d9e385d23e0a844f2934/hw/soc/pcie-evidence/20261004-timing-and-power/rx-prefetch.json)
and [native archive](https://github.com/Melihakbulut221/nssoc/blob/219b734012626ee8a424d9e385d23e0a844f2934/hw/soc/pcie-evidence/20261004-timing-and-power/rx-prefetch-release.json)
keep both the older timing failure and the new functional evidence.

CI now exercises TX v4 and the prefetch receiver independently, including the
maximum RTL receive capacity. Native Icarus logs still contain unsupported timing
checks and the OSS wrapper's Python-executable diagnostic. Passing port tests
therefore does not claim SDF timing or clean simulator diagnostics.

## Real supply-metal failure and repair

Two complete 4 ns simulations retain all 351 intrinsic bank devices. One uses
deliberately ideal wires as a reference; the other retains every extracted wire
resistor and capacitor. Both use the actual free-running VCO, external supplies,
bias/data sources and loads. `BODY_ESD_RETURN` and `WIRE_CREF` remain explicitly
ideal external reference boundaries; no substrate connection is inferred from
a label.

The reference has 16 clock crossings in the 2–4 ns measurement window and passes
the finite bounds on all 122 HBTs. The original physical wires have no clock
crossings in that window and **19 HBT bound failures**, including a minimum
collector-emitter voltage of **7.744 mV**. The local sampler return rises by about
0.35 V. Forty-nine native 1 mA driving-point experiments measure representative
supply/return paths of roughly **51–113 Ω**. These unloaded path measurements are
not a replacement for the simultaneous powered simulation.

An [independent readback](https://github.com/Melihakbulut221/nssoc/blob/219b734012626ee8a424d9e385d23e0a844f2934/hw/soc/pcie-evidence/20261004-timing-and-power/powered-bank-peer.json)
rehashes all 86 archive members, remeasures every sample of both full waveforms
and all 122 HBT bounds, and verifies the 49 DC results and current signs. The
[original full capture](https://github.com/Melihakbulut221/nssoc/blob/219b734012626ee8a424d9e385d23e0a844f2934/hw/soc/pcie-evidence/20261004-timing-and-power/powered-bank-release.json)
preserves the failure and the earlier auditor's current-sign error.

The new overlay adds **335 actual via stacks and 91 parallel metal legs** while
retaining every old device, body, pin and routing polygon. It passes all 560 main
DRC categories with zero reported violations and a strict, unsimplified
**351-device/56-port LVS** comparison. All 804 actual terminal/public anchors
preserve the bijection between 128 conductors; 109 finite contacts remain.
Four actual geometry faults are rejected. An earlier two-via-spacing failure is
preserved alongside the corrected geometry in the [overlay evidence](https://github.com/Melihakbulut221/nssoc/blob/219b734012626ee8a424d9e385d23e0a844f2934/hw/soc/pcie-evidence/20261004-timing-and-power/power-overlay.json).

The first extraction of that wider metal correctly failed because it produced
four negative ground capacitors. Native Magic multiplied two signed 32-bit
geometric dimensions before assigning the result to floating-point area storage;
the new large straps exceeded that product range. The private v4 patch promotes
an operand before each of eight area products. It preserves the native storage
ABI, resistance formula, geometry and PDK, and does not clip or delete capacitors.
Promotion also retains half-unit areas that odd integer division previously
truncated; additional odd-grid checks remain a separate gate.

Thirty-two small native before/after fixtures, both complete wire banks and
thirteen actual raw-data corruption controls validate the bounded patch. The
original bank contains 32,855 resistors/16,215 capacitors; the overlay contains
33,733/16,788. Full conductor ownership, resistance, source capacitance totals
and attachment checks pass. The [native patch record](https://github.com/Melihakbulut221/nssoc/blob/219b734012626ee8a424d9e385d23e0a844f2934/hw/soc/pcie-evidence/20261004-timing-and-power/magic-area-v4.json)
retains the original failures and the initial audit mistakes. **This does not
yet demonstrate powered improvement or qualify the RC model.** The same powered
experiment must be repeated on the revised geometry.

## VCO model-range correction and remaining integration

The old VCO control PMOS uses W=32 µm, outside the model's documented width
calibration range. VCO v4 uses four real W=8 µm transistors. These have separate
junction/edge parasitics; equality is not assumed. Six paired nominal native
runs at control voltages 0.83/0.85/0.87 V pass the predeclared finite comparison:
frequency changes by 0.232–0.251%, supply current by 0.577–0.611%, and maximum
HBT collector-emitter voltage by 6.97 mV. Negative tuning gain is retained.
The [VCO comparison receipt](https://github.com/Melihakbulut221/nssoc/blob/219b734012626ee8a424d9e385d23e0a844f2934/hw/soc/pcie-evidence/20261004-timing-and-power/vco-v4.json)
binds all six public full-wave captures. This is not PVT, thermal, layout or PLL
qualification. The existing 351-device bank and long thermal experiment retain
their original v3 width limitation.

The work still needs closed-loop clock generation/recovery, complete serial and
ordered-set/training logic, sustained packet integrity and controller connection,
the revised VCO in physical geometry, powered supply verification, qualified
substrate/RC/ESD, and the full main-chip timing/LVS/DFT/production gates. The
current byte consumer remains a bandwidth limit. Existing long-running jobs
continue with explicit resource limits and no healthy-run elapsed-time cutoff.
