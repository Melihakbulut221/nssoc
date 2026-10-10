# 138 — PCIe power layout and timing convergence
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Result — 6 October 2026

The divider's new supply routing removes the four observed HBT headroom
failures. All **455 devices pass the finite electrical screens**, but the
loaded /4 and /80 divider functions still fail. A subsequent compact layout
passes its strict DRC/LVS campaign; its extracted circuit performance remains
a separate gate. **Complete PHY and final whole-chip timing are still open.**

The completed RX14a route improves slow setup by 39.125 ps. TX03 and both
new parser candidates regress. A second complete PLL transient passes its
individual late-window checks but fails the predeclared comparison between
time steps. The failed results are preserved alongside the successful checks.

## Supply repair and compact divider

PowerV2 adds real upper-metal supply straps and PDK via arrays to the divider.
The strict geometry audit retains the primitive identity, terminals and
supply topology. The main DRC and both deep and flat transistor LVS pass;
the complete 21-gate native campaign rejects its intended physical/reference
faults. An earlier geometry-reader lifetime error remains recorded; the
corrected reader retains the owning layouts for its KLayout regions.

The extracted divider wires contain **384 resistors and 657 capacitors**.
The combined loaded model contains 455 intrinsic devices, 1,273 resistors
and 1,422 capacitors. At the unchanged nominal 0.6 V control voltage, the
minimum settled HBT VCE rises from 0.183909 V to **0.455915 V**, clearing the
original 0.4 V screen. This is a measured supply repair, not a relaxed limit.

The VCO runs at approximately 8.10253 GHz and the first divide-by-two stage
at 4.0513 GHz. The following stage receives only about −77 to +58 mV
of differential clock swing and does not divide correctly. Its master
oscillates near 5.59 GHz. The authoritative loaded result remains
`FAIL_NATIVE_LOADED_FEEDBACK_SCREEN`; electrical headroom alone is insufficient.

The next compact layout shortens the signal routes while retaining all
91 intrinsic divider devices and their bias values. Its dimensions fall
from **1,520 × 807.03 µm to 960 × 469.03 µm**. It preserves 725 native leaves,
including 634 via leaves, and all 47 power-via arrays. An initial source
candidate's tap collisions were found before native execution and repaired
in CompactV2; the initial source and failed controls remain available.

CompactV2 passes the 21-gate native campaign, zero main DRC violations and
seven-port deep/flat LVS with **74/74 circuits**. Four actual geometry
mutations are also rejected. Independent review checks the raw saved
layout/LVS reports and frozen source pins. This delivery contains the
completed geometry evidence; it makes no claim about CompactV2's wire-RC
or loaded divider behavior.

## Routed signal timing

These measurements use detailed signal routes and the nominal OpenRCX
model with three standard-cell corners. They do **not** provide qualified
RC process corners, complete power integrity or chip signoff.

| Candidate, slow cell corner | Setup, ns | Hold, ns | Router DRC | Decision |
| --- | ---: | ---: | ---: | --- |
| RX14a | −0.402478 | +0.049182 | 0 | Setup remains open; 39.125 ps better than RX13 |
| TX03 | −0.601762 | +0.079316 | 0 | Reject timing adoption; 211.598 ps worse than TX02 |

RX14a's physical candidate passed the complete 1,804-state/5,443-function
comparison, ten meaningful fault controls and six native port cases.
TX03 passed its 3,850-state/11,680-function comparison, ten kernel faults,
ten binding controls and three native port cases. Each routed netlist is
byte-identical to its corresponding checked candidate. These functional
checks do not turn negative extracted setup slack into a passing result.

TX03's nominal recovery/removal slacks are +0.106387/+0.142089 ns. Its 150
reported unannotated outputs are independently checked as unconnected CTS
load outputs; their input pins occur on the appropriate extracted clock
nets. This classification is scoped to that saved design.

Fresh global-route estimates were substantially more optimistic than the
actual nominal routed timing. Follow-up repair experiments therefore load
the actual baseline SPEF after initializing the router, check that the
optimizer sees the measured negative slack, and require a new route and
extraction before adoption. Active follow-up candidates are outside this
finite evidence cut.

## Parser timing candidates

V20 changes the read/retire implementation; V21 registers the retire
descriptor and introduces one internal cycle. Public outputs, fault
quarantine, ownership and the intended latency relation are checked by
source-bound controls. Initial stimulus/coverage failures and their narrow
corrections remain separate records, rather than being relabeled as passes.
V21's original 16 public cases are covered by the retained 15 passing cases
plus one corrected targeted case; a complete positive-profile rerun is not
claimed.

| Same 4 ns preplacement profile | Cells | Flops | Slow setup, ns | Typical setup, ns | Fast setup, ns |
| --- | ---: | ---: | ---: | ---: | ---: |
| V17 reference | 100,817 | 9,410 | −3.336283 | −0.611557 | +0.943533 |
| V20 | 98,417 | 9,410 | −4.526273 | −1.393055 | +0.433082 |
| V21 | 101,103 | 9,612 | −3.564723 | −0.758974 | +0.847446 |

Both candidates retain positive hold in all three cell corners but worsen
slow setup relative to V17, so neither is adopted as timing closure. V21's
actual mapped graph verifies the registered payload boundary and absence
of the original ring-data bypass. Its remaining critical path ends at a
verdict-cache register through the parser's write logic. These are finite
preplacement results, not complete mapped-port or routed-chip qualification.

## PLL finite windows and time-step failure

The complete 2.5 ps-step transient contains **401,607 samples** and 539
intrinsic devices. All 159 public parts were read back; the independent
replay checks **331,727,382 saved values**. The individual 800–900 ns and
900–1,000 ns windows pass the declared finite screen:

| Window | Frequency error | Phase variation |
| --- | ---: | ---: |
| 800–900 ns | −20.739640 ppm | 1.866606 ps |
| 900–1,000 ns | −9.785919 ppm | 0.880741 ps |

The predeclared comparison against the completed 5 ps-step run nevertheless
**fails**. Matched phase differences of **694.834 ps and 695.349 ps** exceed
the unchanged 50 ps limit. Frequency differences of 0.7692 ppm and 5.9483 ppm
pass the separate 100 ppm limit. The phase failure is independently
recomputed from the saved edges; no offset is subtracted to change its verdict.

Across the final 20 matched edges, the difference spans only 0.723439 ps,
with a total change of −0.515190 ps. That supports a predominantly settled
phase offset after acquisition rather than accumulating late frequency
error. It does not demonstrate time-step convergence, complete lock,
PVT/jitter performance or a qualified integrated PHY clock.

## Reproduce and continue

The [delivery inventory](../hw/soc/pcie-evidence/20261006-power-compact-and-timing/delivery-inventory.json)
binds 50 source files, 17 public evidence capsules and 9,985 fully rehashed
members. It includes the previously delivered RX14a preroute capsule as a
dependency. Archive links, digests, member counts, actual native failures,
independent reviews and the exact source methods are retained together.
The first root inventory omitted the nested RX archive list; additive review
corrects that bookkeeping and preserves the earlier partial attempt.

The [NPU initialization repair](137-npu-initialization-reconvergence.md)
remains a separate whole-chip functional gate. Its strict unchanged-model
MBIST/28-check boot is [run 37403350883](https://github.com/Melihakbulut221/nssoc/actions/runs/37403350883)
on commit `c82d1280052c0da65281d87cda9af3b1c6177291`; this report does not
claim its final result. An earlier hosted runner shutdown is retained as an
infrastructure failure, and the replacement run's complete startup artifact
has been checked locally.

Qualified coupled RC, complete SRAM libraries, final whole-chip setup/hold,
full PHY/main-chip integration and manufacturing acceptance remain required.
