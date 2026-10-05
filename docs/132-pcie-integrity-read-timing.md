# 132 — Integrity read-path timing and retained frontend failures
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured candidate, unchanged baseline — 5 October 2026

The V17 integrity receive candidate completes the bounded functional controls,
native mapping, imported-netlist checks and the original 4 ns preplacement
screen. Its slow-corner setup improves by **215.728 ps**, but slow and typical
setup remain negative. **V11 remains the stable baseline; V17 is not adopted
as a timing-closed or physically integrated implementation.**

The [finite delivery inventory](../hw/soc/pcie-evidence/20261005-integrity-read-timing/delivery-inventory.json)
binds nine active V17 source files, eighteen historical V15/V16 source
snapshots, six complete public capsules and twelve public asset identities.
All 728 archive members were independently read and hashed for this delivery.
The saved publication evidence also has sixty completed transport attempts,
120 fully re-read compressed streams and closed process-owner receipts.
No native computation, functional control or public download was repeated
merely to package these results.

## Read representation and frontend behavior

The [V17 generator](../scripts/generate_pcie_integrity_read_v17.py) changes the
V11 read selector to static per-slot eligibility and a balanced payload mux.
Procedural leaf selection keeps eligibility at a known zero or one. The
payload mux retains literal X/Z values, including selected Z data. Each leaf
has an explicit, complete eight-term event list: its read address, six
payload/metadata words and its verdict word. The V11 writers, ownership,
commit/retire controls and public fault priorities remain unchanged.

The preceding V16 representation used implicit array sensitivity. Actual
compiler warnings showed whole-array sensitivity expansion; its ring-128
Icarus compilation did not finish. A separately preserved constant-word
sensitivity diagnostic compiled the original 4,096-case ring-128 read bench
in **0.456774 s** and completed simulation in **166.126216 s**. That 0.457 s
figure is the bounded diagnostic compile, not a timing claim for the entire
V17 suite or native mapping. The
[diagnostic record](../hw/soc/pcie-evidence/20261005-integrity-read-timing/records/pcie-integrity-v17-20261005/frontend-diagnostic-validation.json)
retains the commands, identities, actual warnings and original incompletion.

Native measurement then gives a read-pointer-to-output-register-D depth of
**31 cells** for data, SOP, EOP, DLLP and sequence, and **32 cells** for keep.
The rejected V14 implementation measured 62 cells at those destinations.
These are emitted mapped-cell path depths, not the theoretical RTL tree
height. V17 uses **100,817 mapped cells** against V11's **83,778**, an increase
of **17,039 cells**, with 9,410 flops. The increased cell count is retained as
an implementation cost; it is not a measured placed silicon area.

## Actual preplacement timing

The same 4 ns clock, I/O constraints, three cell corners, CPU6 and 2 GiB
native address-space limit were retained. The
[candidate decision](../hw/soc/pcie-evidence/20261005-integrity-read-timing/records/pcie-integrity-v17-20261005/candidate-decision.json)
keeps all reported path groups and the comparison with V11:

| Cell corner | Worst max-path slack, ns | Worst min-path slack, ns | Max-path improvement over V11, ns |
| --- | ---: | ---: | ---: |
| Slow (SS) | **−3.336283** | +0.401006 | +0.215728 |
| Typical (TT) | **−0.611557** | +0.260212 | +0.147133 |
| Fast (FF) | +0.943533 | +0.176000 | +0.087128 |

The maximum-delay setup failures remain at SS and TT. All reported minimum
slacks are positive in this preplacement screen. The typical and fast
minimum slacks decrease by 0.000199 ns and 0.000192 ns relative to V11; those
small regressions are preserved alongside the setup improvement. Placement,
CTS, detailed routing and extracted-RC timing have not been performed for
this V17 candidate. These values do not replace the separate RX13/TX03
routing results or constitute full-chip timing closure.

## Finite verification and the preserved rejected attempts

V17 has **39 passing pytest executions representing 38 distinct predicates**;
one inherited predicate was selected twice. The selected run has no skips.
**Two MAX4118 test IDs were explicitly deselected and have not been run for
V17.** The finite controls include:

- 12,288 literal randomized read cases at ring sizes 16, 64 and 128;
- 59 directed four-state cases and 31 isolated event-sensitivity cases;
- 30 actual RTL fault mutations;
- thirteen direct public cases and thirteen V11/V17 public miter cases;
- an imported native graph comparison covering 367,008 cell-pin bits and
  six actual graph mutations.

The [control validation](../hw/soc/pcie-evidence/20261005-integrity-read-timing/records/pcie-integrity-v17-20261005/pcie-integrity-v17-core-controls-validation-20261005.json)
and [native validation](../hw/soc/pcie-evidence/20261005-integrity-read-timing/records/pcie-integrity-v17-20261005/pcie-integrity-v17-native-validation-20261005.json)
retain the exact source and result bindings. The imported graph check does
not replace mapped functional replay or a full formal equivalence proof.

V15 passed its 29 selected control executions, then Yosys terminated with
`std::bad_alloc` and return code −6 under the unchanged 2 GiB limit. ABC,
a mapped implementation and timing did not complete. V16's full controls
and native mapping likewise did not complete: its compiler was superseded
only after V17's complete selected suite and independent peers passed.
The exact original jobs, partial captures, the first teardown observation
race and the subsequent guarded cleanup are preserved with their real
statuses. Neither variant is relabelled as a passing implementation.

The original V15 and V16 files remain byte-for-byte unchanged locally. Their
published historical copies live under the evidence directory with their
original repository-relative paths, outside active `sw/tests` discovery.
Only the nine completed V17 sources enter this delivery's active source
allowlist. A fresh checkout can inspect either historical attempt without
adding the stalled V16 test to ordinary CI collection.

One V17 archive member deserves a precise qualification: the archiver's own
stdout log was captured as an empty file before the process wrote its final
summary. The
[archive-cut note](../hw/soc/pcie-evidence/20261005-integrity-read-timing/records/pcie-integrity-v17-20261005/native-archive-cut-note.json)
binds that original member and the later complete stdout separately. The
archive bytes and their full member readback remain intact; the final log
was not inserted into an already published capsule.

Remaining work includes the residual SS/TT setup paths, the two unrun
MAX4118 cases, full formal and mapped functional validation, physical
implementation, qualified RC, whole-chip LVS, full PCIe PHY integration and
production approval. The active follow-up experiments are outside this
finite delivery.
