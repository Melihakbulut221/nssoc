# 133 — Balanced commit selection: functional checks and timing regression
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Result — 5 October 2026

V18 preserves the measured parser behavior and reduces mapped cell count,
but worsens setup against V17. **It is not adopted as a timing improvement.**
The original 4 ns clock, three cell corners, port constraints, CPU6 and
2 GiB native address-space limit are unchanged. These are preplacement
measurements; no placement, CTS, detailed routing or extracted timing is
claimed for this candidate.

| Corner | V17 setup, ns | V18 setup, ns | V18 hold, ns | Setup change, ps |
| --- | ---: | ---: | ---: | ---: |
| Slow | −3.336283 | **−3.415667** | +0.401006 | −79.384 |
| Typical | −0.611557 | **−0.682798** | +0.260213 | −71.241 |
| Fast | +0.943533 | +0.900579 | +0.176000 | −42.954 |

V18 has 100,625 mapped cells, 192 fewer than V17, and the same 9,410 flops.
This is a mapped cell count, not a placed area measurement. The native
import comparison covers 366,485 cell-pin bits and detects six injected
graph faults. It does not constitute complete mapped functional equivalence.
The [saved timing comparison](../hw/soc/pcie-evidence/20261005-balanced-commit-screen/records/timing-comparison.json)
retains every reported group and both V11/V17 comparisons. V11 remains the
stable reference; V17 remains the better measured read-tree experiment.

## Change and actual functional evidence

The [generator](../scripts/generate_pcie_integrity_commit_v18.py) replaces
five procedural commit assignments with lane-local values and known binary
write flags. Original branches and same-lane assignment ordering are
unchanged. Two adjacent-pair selections then choose the latest written
lane, falling back to the previous commit pointer. The exact inverse
restores the entire pinned V17 source. Read-tree sensitivity, other parser
outputs, sequential controls and interface latency are unchanged.

The completed selected campaign has **21 passing pytest executions, 20
distinct predicates**, 26 direct/public-miter cases and 16 actual RTL fault
mutations. One source-inverse predicate is called both directly and through
the public miter. The complete-parser comparison checks all 28 outputs over
32,768 trials. Its first 16,384 trials independently span four parser states
and all 8⁴ token tuples; the second half adds unknown controls and literal
X/Z data. Six commit-specific faults are included in the sixteen mutations.

The first focused harness correlated the parser state with the first token,
which omitted the intended LOOK/STP witness. Its proposed upper-value
Z-to-X mutation was also equivalent after pointer arithmetic. That campaign
was explicitly superseded; its source, partial native results and stop
receipt remain intact. The corrected harness decouples the state/token bits
and targets the literal previous-pointer fallback. It detects the missing
LOOK witness and the real Z conversion. The DUT was not changed to satisfy
these observer corrections.

**Two MAX4118 profile tests were excluded from this finite campaign.** Their
separate local extension was started after this capture was frozen; it is
not counted here as passing. The native timing profile remains MAX150.

## Reproducibility and next path

The [delivery inventory](../hw/soc/pcie-evidence/20261005-balanced-commit-screen/delivery-inventory.json)
binds nine source files, six independently verified public assets and three
complete capsules. All **391 archive members**, including embedded manifests,
were read and hashed again for this delivery. The raw public scenarios,
initial superseded harness, corrected native comparisons and mapped timing
outputs are retained. Compact copies preserve their original bytes; license
sidecars describe those copies without editing them.

The new slow critical path ends at the slot-tag register exposed as
`framer.verdict_cache[18].resident_tag[0]`, with arrival 7.196189 ns.
Fourteen buffers contribute 2.066417 ns and 28 other Boolean cells contribute
4.340551 ns. This identifies the next experiment's late write-control path;
it does not establish that changing it will improve timing.

Residual setup, the maximum-packet extension, complete formal and mapped
functional verification, physical implementation, qualified RC, full PHY
integration and whole-chip production approval remain open. Concurrent
TX/RX routes, PLL simulation and divider wire extraction have separate
evidence and acceptance boundaries.
