# 153 — Separate verdict writer passes finite functional validation
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Completed campaign — 7 October 2026

The experimental V26 integrity receiver passes **45 current host predicates**, with one MAX4118 profile explicitly deselected. This closes the pending finite functional campaign from V25/V26 development; it does not establish timing improvement or complete packet-size coverage. The [inventory](../hw/soc/pcie-evidence/20261007-integrity-v26-controls/inventory.json) binds the exact ten product sources, XML results, negative controls and retained failures.

V26 moves canonical verdict writes into a separate sequential writer. It preserves the V25 command pipeline, ring slots, pointers and external interface. The writer is guarded by reset, enable, active state and command ownership, rather than the current combinational fault verdict. This candidate was designed to reduce a high-fanout enable path. The completed campaign verifies the intended fault quarantine and public behavior; a fresh native map and timing measurement are still required before that timing hypothesis can be assessed.

## What was exercised

| Boundary | Evidence |
| --- | --- |
| Public transactions | Nineteen direct cases and nineteen instrumented cases; two restricted nominal-plus-one latency checks |
| Command semantics | 4,102 finite comparisons, 512 wraps, ten X/Z hold cases and two unknown-control fault applications |
| Internal command faults | Twelve deliberate faults produce the required diagnostics |
| Whole-DUT faults | Thirteen public, eight architecture, two block and one canonical-observer mutation are rejected |
| Fault/restart sequence | Two bad blocks, one overflow and three recoveries; explicit ring16/MAX18 stress profile |

These are nested measurements inside the 45 host predicates and must not be added into an inflated test total. The X/Z command evidence is component-level. No general cycle-equivalence or all-state formal claim is made, and the excluded MAX4118 profile remains separate work.

The earlier campaign had 44 passing predicates and one host diagnostic mismatch. The deliberately broken writer did leak the rejected packet, but the observer reported a generic ordered-byte mismatch. The corrected observer identifies the exact forbidden payload `a35c96e1deb6`; the same mutation now fails with that explicit diagnostic. RTL and generated source bytes were unchanged between those campaigns. Both the earlier failure and current passing evidence remain available.

Two stale absolute-path aliases in the source freeze still referred to the pre-correction observer despite updated relative-path entries. The additive third freeze resolves both aliases to the already prepared source hashes, retaining the earlier freezes. The first final-record reader also counted pytest's `current` symlink as a second execution; its corrected successor excludes that alias and verifies the actual directory once. Neither correction weakens a DUT assertion or threshold.

## Retention and remaining work

The [459-member public capsule](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/pcie-integrity-v26-current-controls03-20261007.tar.xz) preserves current native controls, source snapshots and historical evidence. It contains 16,554,936 bytes with SHA256 `5f34105db465e684db888c4fb5349bbc085c9d1ccc619f7be3570c0bfb783c78`. Every member was read back locally and the complete anonymous public download matches. Result recount and source checks were performed by the root reviewer; no external independent review is claimed.

V26 remains an experimental candidate. Native mapping, mapped functional verification, the unchanged 4 ns timing target, routing and qualified extracted timing are not completed by this campaign. The [pump/filter measurements](152-pcie-pump-current-characterization.md) and [prior chip/RX timing results](151-pcie-ci-resume-and-timing-results.md) retain their separate scopes. Full PHY and final chip acceptance remain open.
