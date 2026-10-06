# 148 — Recover independent publication from a concurrent log-file change
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Verified correction — 6 October 2026

The [delivery inventory](../hw/soc/pcie-evidence/20261006-local-publisher-log-race/delivery-inventory.json)
binds the two sources, completed tests, independent reviews and four public
assets with complete authenticated and anonymous byte readbacks. The corrected
worker is running separately from the native simulation.

The independent V1 publisher stopped while its child compressed and removed
a transport log. Its parent enumerated the old `stdout.bin` name, then tried
to read its size after removal. The resulting `FileNotFoundError` stopped
publication. **The separately owned PLL simulation continued committing
waveform parts to SSD.** This failure exercised the isolation introduced in
the [local capture implementation](146-pcie-local-pll-capture.md).

The [V2 worker](../scripts/publish_pcie_local_spool_v2.py) invalidates the
whole size sample when a file disappears and restarts the scan from the root,
up to four attempts. It does not count a missing entry as zero bytes. Other
filesystem errors remain fatal, symbolic links and non-regular files are
rejected, and hard-linked names are counted conservatively. The original
capacity limits, free-space floor and reserved command/terminal headroom
remain unchanged. This is a sampled storage guard, not an atomic filesystem
quota or protection against an adversarial process moving directories.

The remainder of the worker is byte-equivalent to V1: part/receipt checks,
bounded retry classification, native-source preservation and owned-child
cancellation behavior are unchanged. A fresh V2 process rechecks every
previous public part through the existing V4 release publisher. Existing
files are reconciled and fully downloaded through both paths, without
clobbering or trusting old receipts as a substitute for readback. No native
simulation restart or solver-checkpoint claim is involved.

## Tests and failure evidence

All **31 current controls pass**: the original 21 worker predicates plus ten
new source/race/recovery predicates. The new controls perform actual rename,
compression/removal and subtree-removal operations during size sampling.
They also check a sparse file above the capacity limit, permission and I/O
errors, exhaustion of all four scans, a symbolic link and recovery of an
already uploaded asset with **zero new uploads** and both full readbacks.

Three recorded campaigns contain 93 executions: 88 passes and five retained
test-implementation failures. These failures exposed a truncated hash literal,
a missing iterator method in the test proxy and a one-blank-line mismatch
in the complete-source comparison. The final complete campaign passes all
31 predicates. Independent review rehashes 1,448 source/control files,
reconstructs the complete V1/V2 byte relationship and checks the saved
publication and owned-process receipts. A reporting-only list error in the
first review has an additive correction; its original bytes remain retained.

The original production failure remains separately sealed with 1,313 archive
members. V1 had verified 61 complete public parts. Part index 61 had uploaded
as asset 614811208 but had not completed both readbacks when the parent failed.
The child’s stop flag records subsequent error cleanup; the outer receipt
records `explicit_stop: false`. It was not a user cancellation. Any successful
V2 readback is a new observation and does not rewrite that failed attempt.

## Scope

The finite source/control packet excludes the active publisher journal and
mutable native spool. Its immutable launch receipt proves startup, not future
completion. Continued publication, complete native capture, acquisition
measurements and numerical replay require their own terminal receipts.
This operational correction does not close the full PCIe PHY, qualified
parasitics or final chip timing and manufacturing acceptance.
