# 156 — PCIe output transfer timing rejection
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Result — 8 October 2026

V29 separates the six output payload fields from the parser-fault ownership
controller. The functional campaign passes, but slow setup **regresses by
105.538 ps against [V28](155-pcie-payload-epoch-quarantine.md)**. V29 is rejected
for chip integration. V28 also remains below the unchanged 4 ns requirement;
neither candidate closes receiver timing or complete PCIe integration.

| Liberty corner | Setup worst slack (ns) | Hold worst slack (ns) |
| --- | ---: | ---: |
| Slow | −3.204153 | +0.401006 |
| Typical | −0.553742 | +0.260411 |
| Fast | +0.991930 | +0.176086 |

The native experiment uses the same original 4 ns clock, PDK corners, input
delays, loads, mapping script and preplacement repair as V28. It has ideal
clocks and wire-load models, with no placement, CTS or extracted routing.
Positive hold in this screen is not final hold closure. Mapping yields
96,841 cells, twenty more than V28. The import comparison checks all 352,419
cell-pin bits, 24 ports and six deliberately incorrect connectivity graphs.
The [retention record](../hw/soc/pcie-evidence/20261008-integrity-v29/retention01.json)
retains these results and the negative setup comparison.

## Changed behavior and actual checks

The [generator](../scripts/generate_pcie_integrity_output_v29.py) pins the V28
source hash and checks the exact inverse of four edits. Data, keep, SOP, EOP,
DLLP type and sequence move together from the old retire descriptor in their
own sequential writer. Reset values are retained. Output validity, descriptor
ownership, fault priority and public handshakes retain their original logic.

A parser-fault edge can copy inaccessible contents while invalidating the
owner. A fresh valid owner must copy every field again. A stalled valid beat
cannot be overwritten; a beat accepted on the fault edge is still sampled
before the sequential fault cancellation. This is neither a CRC bypass nor a
delayed fault response.

The [HDL campaign](../sw/tests/test_pcie_gen3_integrity_v29_output.py) reuses the
unaltered nineteen-case independent serial-packet oracle and the V26 public
reference. The fixture only aliases the new framer into the existing runner.
All nineteen cases pass over 34,248 compared public cycles. A read-only
observer checks all six actual output fields on every clock: 7,993 transfers,
267 stalled cycles and one actual fault-edge copy that changes inaccessible
contents. No internal state is forced. The existing ring and frontier fault
observers remain active as well.

Five actual HDL mutations are rejected: bypassing the old descriptor, losing
keep, losing sequence, overwriting a stalled beat and retaining output
ownership on a fault. The initial host run records six passes and one failure:
the last mutant was caught by the earlier V27 ownership observer, but the host
expected a different assertion name. Only that exact diagnostic match was
corrected; its targeted rerun passes. No RTL, oracle, stimulus or threshold
was changed to make the negative control pass. Both attempts are retained.
There are seven distinct host predicates, not eight additive tests.

This is a finite 150-byte profile. It does not establish MAX4118 behavior,
complete mapped functional equivalence, all-state formal equivalence or an
autonomous serial host link.

## Integration boundary and retained evidence

The measured critical path still starts at `framer.remaining[4]`. Its native
endpoint is recorded in the [path attribution](../hw/soc/pcie-evidence/20261008-integrity-v29/critical-path-attribution.json);
35 Boolean cells and two muxes remain on the reported path, alongside buffers
and the launch flop. Output-writer isolation alone does not solve this parser
control path. Further architectural repair must retain accepted-byte, fault,
restart and capacity behavior, and be measured before adoption.

The [128-member raw capsule](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/pcie-integrity-v29-output-20261008.tar.gz)
is 30,914,684 bytes, SHA256
`93ebeb59a0163b4bfb9956757ad386dca20f14355954e0b47845fa6c65b3d283`.
It contains the actual control fixtures and failures, sources, native mapping,
import and timing outputs. Every member has been read back locally; the complete anonymous public download also matches the byte count and SHA256. External
tools and PDK files are pinned rather than bundled. Review is by the root
agent; no external independent review is claimed.

The [current main-chip boundary inspection](../hw/soc/pcie-evidence/20261008-integrity-v29/main-chip-boundary01.json)
records the real `soc_top` packet profile: eight-bit packet ports and external
link/training state feed `soc_pcie_buffered_flow_packets`. It is not a complete
four-lane serial PHY instance. PLL/CDR, complete SERDES/PCS/LTSSM, qualified
parasitics and analog pads, actual main-chip placement/routing and chip-level
verification remain open. This experiment produces no new main-chip GDS.
These interface dependencies remain the priority before unrelated work.
