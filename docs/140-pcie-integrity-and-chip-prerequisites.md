# 140 — Receiver critical path and matched chip experiment prerequisites
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured boundary — 6 October 2026

The V22 receiver experiment completes the same 4 ns timing screen but still
fails setup at slow and typical corners. **It is not adopted.** The separate
NPU repair now has an explicit prerequisite checker and a local, matched
physical experiment runner. Neither starts chip placement before the exact
repaired vendor-model boot has passed. Full PCIe Gen3 x4 PHY, final whole-chip
timing and manufacturing acceptance remain open.

The [finite inventory](../hw/soc/pcie-evidence/20261006-integrity-and-chip-prerequisites/delivery-inventory.json)
retains source files, raw results, independent reviews and historical failures.
Four public archives contain **874 members**, all streamed and rehashed in
the local delivery review. They preserve V22's failed first test capture,
corrected functional evidence, complete timing screen and the NPU prerequisite
checker. Active analog, routing, PLL and long packet simulations are separate.

## V22: removing one cache-write qualification does not close setup

V22 changes the resident cache data-write condition from `step && !fault_now`
to `step`. Data in an invalid cache entry may change during a fault; the
existing validity and public-output quarantine remain in place. The generator
checks an exact inverse against V21 so unrelated parser behavior cannot be
silently changed.

The first selected campaign records **26 passing and three failing tests**.
The witness counter updated at the following falling edge, after the testbench
had already checked it. The correction samples settled nonblocking updates
immediately after the same rising edge. That harness correction and a 16-byte
IDL case with a nonzero cache pointer produce nine passing targeted checks.
The original failing capture is retained. Across these two
campaigns there are 38 executions: 35 passed and three historical failures.
All 29 selected predicates are covered by the composite evidence; this is
not a claim that the entire first campaign was rerun after the harness change.

The records include 17 direct public profiles, 17 complete cycle-miter cases,
eight fault-epoch cache-write witnesses in each of three relevant captures,
4,096 literal vectors and six meaningful miter mutants. The two V22 maximum
4,118-byte predicates were not run. The separate long maximum-packet campaign
uses V18 and is not V22 evidence.

The completed native screen contains **101,044 cells and 9,612 flip-flops**.
Its imported cell-pin graph and registered timing boundary were independently
checked against the saved native outputs.

| Corner | Setup slack, ns | Hold slack, ns |
| --- | ---: | ---: |
| Slow | −3.544282 | +0.370623 |
| Typical | −0.745996 | +0.260212 |
| Fast | +0.857332 | +0.176000 |

Slow setup improves by only 20.441 ps relative to V21 and remains 207.999 ps
worse than V17. These are preplacement screen results under the unchanged
4 ns constraint, not detailed-route timing. The recorded critical path passes
through 19 buffers and seven muxes before a resident-verdict register. Removing
the cache write qualification leaves the principal data path unresolved.
The next architecture experiment must shorten that measured path while
preserving packet acceptance, fault quarantine and public cycle latency.

## NPU: bind proof, exact memory mapping and real boot before placement

The [initialization repair](137-npu-initialization-reconvergence.md) factors
one reconvergent mapped equation to preserve its Boolean function while
resolving the reproduced unknown-valued initialization case. Its completed
local mapping reproduces both historical mapped inputs exactly and preserves
all 32 SRAM identities and 79 logical ports.

The [new prerequisite checker](../scripts/check_npu_eco_physical_readiness.py)
joins that result to the accepted binary relation. It recounts **33,517 prior
equations, four separately proved hard equations and 800 grouped equations**,
with disjoint original identities: 34,321 total. The 64 grouped batches retain
10,828 symbolic inputs and no added assumptions. This reuses the recorded
cloud proof; it does not claim a new local replay of the original full graphs.

The checker verifies the complete local SRAM mapping outputs, exact inverse
ECO, sixteen Boolean assignments and the saved independent mapping review.
It then requires the final archive from the exact strict boot run, matching
its source revision, compiled inputs, firmware, vendor models, 3,000,000-cycle
bound and native command. The raw log must report successful power-on MBIST
and **all 28 firmware checks**. Missing, running, failed, truncated, changed or
foreign results cannot be accepted by a binary proof alone.

All 47 checker tests pass in both the author and independent review. Three
additional mutations of the actual saved equation catalog are rejected.
The captured real prerequisite result is **BLOCKED pending successful boot**;
synthetic passing fixtures only test the checker and do not replace that boot.

## A local physical runner with unchanged comparison conditions

The [new local runner](../scripts/run_npu_eco_physical.py) supports only the
exact original and factored mapped inputs. It reuses the frozen C10 physical
configuration, original 20 ns clock contract, all three corners, 301 signal
terminal boxes and 32 fixed SRAM placements. Each arm starts with a netlist
only, runs fresh placement, CTS and global routing, then exports the complete
setup/hold endpoint and electrical audit.

The actual template-stage geometry is retained separately from the final
geometry. Comparison reparses both captures, the raw timing audit and the
full prerequisite evidence. This closes a source-review finding in the first
runner draft, which had preserved only the final geometry. Mutating only the
saved original template now fails independent replay.

The runner also preserves failed attempts, owns its native process group and
has no healthy elapsed-time kill. An actual interruption injected between
process creation and handle assignment verifies cleanup of the exact child.
The final 57 runner and inherited physical-control tests pass. The existing
failed candidate's historical guards remain unchanged.

The exact 5,180-member physical input bundle and 1,398,053,408-byte runtime have
been restored and verified locally. This is input preparation, not a physical
result. Even a successful future placement comparison will be a global-route
estimate: qualified SRAM Liberty/RC, post-layout functional equivalence,
detailed routing, final timing and full-chip physical verification remain
required before adoption.

The [preceding report](139-pcie-compact-rc-and-repair.md) retains the completed
compact-divider failure, TX proof/port prerequisites and controlled PLL
numerical experiment. None of those open acceptance gates is cleared here.
