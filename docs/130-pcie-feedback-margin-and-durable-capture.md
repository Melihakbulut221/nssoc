# 130 — PCIe feedback margin and durable native capture
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Continued after the actual power loss — 5 October 2026

The disconnected-clock probe now passes all 437 electrical screens while
correctly reporting the missing divided clock. Both nominal control endpoints
also pass after changing two physical resistor dimensions in the schematic.
The exact new divider still needs its own layout and parasitic verification.
**This is a finite circuit improvement, not completed PCIe Gen3 x4 or
main-chip qualification.**

The [delivery inventory](../hw/soc/pcie-evidence/20261005-feedback-margin-and-durable-capture/delivery-inventory.json)
binds the new sources, saved controls, independent reviews and immutable public
captures. [Report 129](129-pcie-loaded-feedback-and-rx-timing.md) retains the
preceding L6.4 results and their actual failures unchanged.

## The two L4 resistors clear the disconnected-clock headroom screen

Only the first conditioner's upward-bias `rppd` lengths change from 6.4 to
4 µm; width remains 1 µm. Independent expanded-graph comparison preserves
all 437 device identities and changes only those two length parameters.
The 889-resistor/765-capacitor VCO wire model, 50 fF public pin loads,
34 ns capture, 5 ps maximum timestep, 27 °C temperature and measurement
functions remain unchanged. Eleven source controls precede the new captures.

| Actual L4 capture | Minimum settled HBT VCE | VCO frequency | Feedback frequency | Electrical screens |
| --- | ---: | ---: | ---: | --- |
| Nominal control 0.85 V | 0.526905 V | 7.601783408 GHz | 95.006551916 MHz | 437 pass |
| Nominal control 0.60 V | 0.525944 V | 8.103519853 GHz | 101.254401151 MHz | 437 pass |
| Clock disconnected, control 0.60 V | 0.441864 V | 8.102618495 GHz | No feedback edges | 437 pass |

The disconnected-clock minimum rises from 0.343411 V at L6.4 to
0.441864 V at L4, crossing the same 0.4 V development headroom screen.
Its eleven functional failures remain failures: disconnecting the clock
must not produce a nominal PASS. It is now an electrically healthy detected
fault under these finite conditions. This criterion is not a foundry
safe-operating-area guarantee.

At nominal 0.60 V, the limiting device moves from the divider into the
unchanged VCO. The first divider's tail minimum is 0.544588 V, while
the global minimum is 0.525944 V. Peak current is 2.772636 mA/Nx against
the unchanged 3 mA/Nx development screen. These distinct minima must not
be substituted for one another when comparing revisions.

The nominal captures each contain 6,819 rows and 786 columns. Independent
reductions rehash all archived members and every binary sample, recalculate
all device screens, check 64 native OFF flags and recount actual /4 and /80
periods without importing producer measurement functions. All 227 and 242
complete nominal VCO cycles respectively cross both −300 mV and +300 mV.
The disconnected-clock capture has 6,832 rows; its complete VCO cycles also
pass that amplitude check while the divided feedback is absent.

The actual wrong-modulus control preserves /4 but produces /64 instead of
/80: measured feedback is 126.579232875 MHz. All 437 electrical screens
pass, while four functional checks fail as intended. Independent reviews
of all four captures cover **21,449,154 binary values** and retain both
faults' native FAIL statuses. The paired wrong-modulus comparison uses the
original L8 capture; no L6.4 wrong-modulus capture is invented.

The physical VCO and schematic divider form a mixed model. The divider's
new dimensions, its wires, the CMOS counter, clock-bank integration, PVT,
thermal effects and jitter still require separate evidence. Fixed-control
oscillation at these endpoints does not demonstrate PLL acquisition or lock.

## Publication failures no longer immediately abort a healthy native producer

The preceding long PLL attempt terminated on an actual GitHub TLS download
failure. Its failed result, first seven public parts, retained eighth part
and waveform tail remain recorded. V3 adds bounded retry for transient
transport failures while retaining hard rejection for wrong bytes or
permanent HTTP errors. Successful publication still requires exact
authenticated and anonymous download checks before a queued part can be
reclaimed. A partial transfer is never counted as a published full capture.

Thirty-one transport controls cover retry classification, byte integrity,
bounded stderr, interrupted publication and cleanup of owned descendants.
The separate producer bridge has fifteen distinct controls; two affected
tests were rerun after replacing their volatile input path with a tracked,
hash-pinned fixture. Those reruns are not additional distinct tests.
Integration controls use sleeper processes to exercise ownership and
backpressure; they are not substitutes for a SPICE simulation.

The producer bridge preserves the previous physical deck and measurement
functions. Its fresh native run retains 539 device records, a 1 µs stop,
2.5 ps maximum timestep, original 100 ppm/50 ps acceptance limits and
800–900/900–1000 ns measurement windows. The run has started; no completed
1 µs result or timestep-pair agreement is claimed in this delivery.

A live L4 capture publication also exercised the retry path: its first
authenticated download reached the 120-second transport deadline, the
failure was retained, and the next attempt passed. This transport deadline
does not impose an elapsed-time limit on a healthy native simulator.

## Physical continuation and retained scope

TX02 and RX12 detailed routing continue on their existing owned processes.
Each has a durable continuation to fresh nominal RC extraction, saved-output
review, complete capture packaging and verified publication. The reviewers
retain measured setup, hold, recovery and removal values without assuming
that a new candidate improves them. The RX12 pre-route preservation capsule
contains the completed new candidate, binary proof and six physical-port
tests; it is not a completed route or final timing result.

The next analog layout is the standalone current divider: 34 HBT devices,
33 resistors and six MIM capacitors, with explicit substrate contacts.
The older physical divider generator embeds an older VCO, so merely changing
its two resistor values would leave the wrong circuit. New geometry must
preserve the current circuit and pass independent DRC/LVS and actual
open/short/wrong-device controls before any new wire-model claim.

Full-chip setup/hold and qualified RC, full SERDES/CDR/PLL, training and
controller policies, analog pads/ESD, SRAM/DFT obligations, main-chip
integration and manufacturing acceptance remain open.

## Follow-up: recover the complete CI run and retain interrupted diagnostics

The actual hosted RTL job for commit `380cfc7` reached its 30-minute job
deadline before completing the suite. Its retained log also exposed a separate
default source-binding failure: the DLLP consumer V2 comparison Makefile names
a nonexistent RTL observer. The observer is in the testbench directory and
requires both compared consumer implementations.

The shared runner now passes those three existing sources explicitly, matching
the earlier native checker. The hash-pinned historical Makefile, observer and
DUTs remain byte-identical. A fresh real Icarus/cocotb invocation through that
runner passes **all nine comparison cases, with zero skipped cases**. The
runner's separate memory-parity accounting entry is not a skipped DLLP case;
the hosted memory-parity job passed independently.

The runner also writes each active suite's output directly to its artifact
log. A real subprocess interruption test proves that diagnostics already
emitted survive cancellation. All **16 runner regression controls pass**.
The two complete hosted jobs now allow 360 minutes; individual suite failure
and timeout handling still rejects unsuccessful execution. This delivery does
not claim that the next full hosted run has completed.

The [validation receipt](../hw/soc/pcie-evidence/20261005-cocotb-runner-recovery/validation.json)
records the exact source hashes, native case counts and limits. The
[capture inventory](../hw/soc/pcie-evidence/20261005-cocotb-runner-recovery/inventory.json)
retains the original cancelled log, both regression runs, complete native log
and XML, and authenticated/anonymous publication readbacks. The compiled
native capture is preserved in its immutable public capsule.

## Follow-up: RX12 completes routing, with a smaller remaining setup miss

RX12 has now completed detailed signal routing and fresh nominal RC extraction.
Eight targeted buffer isolations and two buffer upsizes preserve the candidate's
proved logical behavior. The final routed netlist is byte-identical to that
candidate. The router reports zero DRC violations; this is a standalone receiver
result, not full-chip foundry DRC or LVS acceptance.

| Cell-library corner, shared nominal RC | Setup slack, ns | Hold slack, ns | Recovery, ns | Removal, ns |
| --- | ---: | ---: | ---: | ---: |
| Slow | **−0.521801** | +0.035180 | +0.362229 | +0.872480 |
| Typical | +1.192867 | +0.062631 | +1.672244 | +0.583272 |
| Fast | +2.156512 | +0.077598 | +2.465179 | +0.411854 |

Slow setup improves by **88.680 ps** relative to the published RX11 result
of −0.610481 ns. It still fails. Hold, recovery and removal remain positive
in all three measured cell corners, and no slew/capacitance violations are
reported. The 78 unannotated outputs are individually checked as unused
clock-load outputs; their actual input pins are present on the correct
extracted clock nets. No partially unannotated pins are accepted.

The saved proof covers 1,804 state bits and 5,443 functions, with ten actual
mutation controls and six native physical-port checks. Publication packaging
does not rerun those completed native checks or invent a new reference run.
The [finite handoff](../hw/soc/pcie-evidence/20261005-rx12-routed-timing/ready-finite.json)
and [independent timing review](../hw/soc/pcie-evidence/20261005-rx12-routed-timing/repair12-peer/review.json)
retain the exact constraints, sources, results and limitations. A separate
[root readback](../hw/soc/pcie-evidence/20261005-rx12-routed-timing/root-inventory.json)
rehashes all 115 capsule members and 109 compact evidence files. All three
immutable public assets pass authenticated and anonymous download verification.

These measurements use the existing default-150 byte receiver and one nominal
RC extraction across three cell libraries. They do not qualify separate RC
process corners, the final wide PCS receiver, or main-chip timing. The next
repair targets the actual remaining slow-corner paths; this delivery retains
their failing values as the baseline.
