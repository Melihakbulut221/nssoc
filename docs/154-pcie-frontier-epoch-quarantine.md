# 154 — PCIe receive frontier timing and epoch quarantine
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured result — 8 October 2026

The V27 receiver moves the visible commit pointer into a separate sequential
writer. It removes the [V26](153-pcie-verdict-writer-functional-validation.md)
critical endpoint, but does not meet the original 4 ns clock. **This is an
experimental receiver candidate, not a completed PHY or main-chip integration.**
The [retention record](../hw/soc/pcie-evidence/20261008-integrity-v27/retention01.json)
binds the source, tests, preserved failure and native evidence.

| Liberty corner | Setup worst slack (ns) | Hold worst slack (ns) | Setup improvement against V26 (ps) |
| --- | ---: | ---: | ---: |
| Slow | −3.210865 | +0.401006 | 26.992 |
| Typical | −0.540794 | +0.260212 | 38.099 |
| Fast | +0.997122 | +0.176000 | 13.923 |

The library corners, 4 ns constraint, input delays, output loads and repair
method are unchanged. These are preplacement estimates with ideal clocks;
they do not include routed parasitics or qualify final hold. Slow and typical
setup still fail. Slow setup also remains 19.183 ps worse than V23, so V27 is
not an accepted replacement for chip integration.

## Circuit change and verification boundary

The [generator](../scripts/generate_pcie_integrity_frontier_v27.py) checks the
exact V26 source hash and proves that reversing its four recorded edits recovers
that source. Reset, flush, stream start and explicit abort clear the pointer.
An inactive epoch clears it on the following clock. On a parser-fault edge,
the old pending command may update this pointer while the original controller
clears active, output, descriptor and command ownership. The changed pointer
is inaccessible to retirement in that faulted epoch; a restart clears it before
new traffic can use it. Other ring contents, parser logic, interface and public
latency are unchanged by the source edit.

The [actual HDL controls](../sw/tests/test_pcie_gen3_integrity_v27_frontier.py)
run the existing independent nineteen-case serial-packet oracle without editing
its assertions or expected packets. An unchanged V26 instance receives the same
inputs. Control outputs are compared cycle by cycle, and payload/metadata are
compared whenever valid. The finite campaign passes 34,248 checked cycles,
including fifteen pending-command parser-fault edges. Thirteen of those really
change the candidate's pointer relative to the reference while all public
ownership remains cleared. This is finite known-control evidence, not an
all-state formal proof or complete packet-size qualification.

Five deliberately broken candidates are rejected: early visibility, missing
command application, dropping the final command, failure to clear on restart,
and keeping a faulted epoch active. The first restart mutation was not detected
by its selected stimulus because it tested an early pending command before a
nonzero visible frontier. That host predicate failed and its raw output is
retained. The targeted retry uses the existing occupied-descriptor epoch test;
it rejects the same mutation. No RTL, comparison or threshold was changed for
that correction. Six initially passing host predicates and the corrected
seventh pass; these counts must not be added to nineteen as independent coverage.

## Native implementation and remaining path

Native IHP mapping produces 93,601 cells. The complete import proof checks
341,541 cell-pin bits, all 24 ports and six deliberate graph faults. The
metadata/tie import preserves every original mapped connection. It is not
complete mapped functional equivalence.

The new [worst path](../hw/soc/pcie-evidence/20261008-integrity-v27/slow-critical-path.txt)
starts at `framer.remaining[4]` and ends at `framer.slot_keep[11][0]`.
The long parser-fault path still reaches ring payload control. Repairing the
pointer endpoint alone therefore does not close receiver timing. Further
changes must preserve fault cancellation, same-edge accepted output, pending
command ownership and fresh-epoch reuse before physical adoption.

All controls, the initially missed mutation, methods and the three native RAM
directories are retained in the [126-member capsule](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/pcie-integrity-v27-frontier-20261008.tar.gz):
30,387,798 bytes, SHA256
`44f2904c3ea674dab1300ecc373b6a0ef20b0224e9ee617c8f9212421e96497c`.
Every archive member was replayed locally, and the complete anonymous public download matches its byte count and SHA256. The root reviewer performed these
checks; no external independent review is claimed.

PCIe's complete PLL/CDR/SERDES, PCS/LTSSM/controller operation and main-chip
physical connection remain open. This change does not instantiate a serial PHY
in `soc_top`, create a new chip GDS, or qualify a host link. PCIe/Ethernet and
remaining interface integration remain the priority before unrelated work.
