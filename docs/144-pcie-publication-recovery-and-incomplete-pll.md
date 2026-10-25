# 144 — Recover publication without accepting an incomplete PLL run
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured result — 6 October 2026

The release publisher now recovers an uncertain, absent upload without
clobbering an existing asset. Fifteen actual child-process controls pass, and
the real failed PLL part is published and read back byte-for-byte through
both authenticated and anonymous downloads. The interrupted PLL simulation
remains **incomplete at 383.288 ns of its requested 1 µs**. Recovering its
capture does not complete the simulation or establish PLL lock.

The [delivery inventory](../hw/soc/pcie-evidence/20261006-publisher-recovery-and-pll-capture/delivery-inventory.json)
binds two source files, two full archives containing 2,704 members, five public
assets and the independent reviews. The [preceding physical record](143-pcie-divider-and-routed-transmitter.md)
retains the divider and routed-transmitter results. This delivery changes
transport handling only; it claims no new physical or timing acceptance.

## Actual failure and preserved numerical evidence

The original publisher's upload of part 120 exceeded its 120-second transport
deadline. Its owned upload process exited with return code **−15** after
120.129 seconds. The following lookup found no matching asset. Both the saved
release metadata and a separate complete eight-page API read showed 743
assets and no part 120. There is no evidence that this upload succeeded or
that pagination caused the failure.

The earlier publisher attempted that upload once. Its caller treated the
following absence as an integrity error and stopped the owned native solver.
The original result remains `ERROR_NATIVE_OR_STREAM_CAPTURE`; ngspice's −15
is retained. Numerical convergence, the declared lock windows and the final
phase/frequency criteria were not evaluated to completion.

The failed-run archive preserves 2,392 members, including the original result,
process records, the failed upload, 120 earlier successful publication
receipts, raw tails, deck and source pins. Independent review reads every
archive member and checks its original bytes. No exit code, successful
completion or continuation from a partial waveform is invented.

The separately recovered part is exactly **13,509,560 bytes**, with SHA-256
`1438044b6cbf5f301fec01c5e159c1ac651e3d30085d2666a702e065415b98e7`.
It is public asset 614632793 on the original continuation release. Both
complete download paths match. The old failed receipt remains unchanged.

## Publisher correction and tests

The [V4 publisher](../scripts/publish_pcie_native_capture_v4.py) preserves
V3's checked source, process ownership, 120-second per-attempt deadline and
full download comparisons. It adds a bounded reconciliation loop:

- An uncertain transport failure permits another non-clobbering upload only
  after a metadata read confirms the asset is absent.
- An existing asset must match name, size, digest and completed upload state.
  Corruption, duplicate names and permanent errors fail explicitly.
- A successful upload followed by delayed visibility triggers metadata-only
  retries; it does not issue a duplicate upload.
- Each attempt rechecks local bytes and records its transport and reconciliation
  evidence. Explicit cancellation reaps the owned child group.

The [fifteen controls](../sw/tests/test_pcie_native_publisher_v4.py) exercise
actual subprocesses and local HTTP downloads. They cover upload timeout and
transient failure, a completed but uncertain upload, a concurrent existing
asset, delayed visibility, bounded retry exhaustion, corruption and changed
local bytes, authentication failure, full CLI dual downloads, and SIGTERM
during upload and backoff. All fifteen pass in 4.11 seconds. An independent
review checks the frozen source, XML, 61 owned-child records and full
compressed output. The controls archive has 312 members. Ruff also passes.

The two complete archives and their validation records are available on the
[new evidence release](https://github.com/Melihakbulut221/nssoc/releases/tag/evidence-20261006-pcie-closure).
Every delivered asset has both complete authenticated and anonymous byte
readback receipts. The recovered raw part remains on the original release;
new captures use the new tag.

## Remaining work

The fresh PLL run still needs a durable local capture path separated from
network publication, followed by the complete original numerical checks.
That implementation is not part of this delivery. Partial raw data is not a
solver checkpoint: the next exact run must start at time zero.

Main-chip repair, new receiver/transmitter routing, the next loaded-divider
experiment and later packet-integrity candidates are excluded from this
finite record. Final setup/hold closure, qualified SRAM timing and RC,
complete PCIe PHY and chip integration, and manufacturing acceptance remain
open. No clock period, timing exception, analog criterion or product gate is
relaxed here.
