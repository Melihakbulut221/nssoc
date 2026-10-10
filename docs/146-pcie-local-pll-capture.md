# 146 — Separate PLL capture from network publication
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Verified change — 6 October 2026

A network upload failure previously stopped the PLL simulation at 383.288 ns
of its requested 1 µs. The new capture path commits complete waveform parts
to local SSD storage, while a separate process publishes them. Network
outages can leave publication pending without stopping the native solver.
The earlier incomplete run remains an error; the new run starts at time zero.

All **69 current storage, capture and publication controls pass**. The finite
packet contains six source files, their saved controls and immutable launch
observations. Its archive has 3,967 members; the archive, validation and
package record have complete authenticated and anonymous download receipts.
The [delivery inventory](../hw/soc/pcie-evidence/20261006-local-pll-capture/delivery-inventory.json)
binds those sources, three public assets and independent reviews.

This delivery verifies the capture implementation and its controls. The new
PLL simulation is separate ongoing work: this packet contains no completed
1 µs acquisition result, lock verdict or numerical-convergence acceptance.
The [previous record](144-pcie-publication-recovery-and-incomplete-pll.md)
retains the original transport failure and recovered partial capture.

## Local commit and independent publication

The [durable spool](../scripts/durable_pcie_spool_v1.py) keeps the original
row order, raw-byte hashes and lossless compression. It writes each part and
its record to a fresh staging directory, synchronizes them to storage, then
renames the directory and durably updates the canonical ledger. Pending RAM
bytes are cleared only after that local commit. Existing committed parts are
never replaced; incomplete staging files and orphan directories remain
visible and are not silently accepted into the stream.

The [V5 acquisition bridge](../scripts/characterize_pcie_pll_acquisition_v5.py)
uses this queue without calling the network. Controlled completion and error
teardown retain native files and raw tails. Invalid headers or manifests
retain their diagnostic bytes; they do not become successful captures.

The [independent publisher](../scripts/publish_pcie_local_spool_v1.py) reads
committed parts and writes its own receipts. It uses the reviewed V4 release
publisher and the new evidence tag, verifies exact source bytes, and requires
both complete download paths before calling a part public. Transport failures
permit bounded retry; integrity and permanent failures stop publication with
local bytes retained. Stopping the worker reaps only its own child processes.
Local completion, public delivery and independent numerical replay remain
separate gates.

Storage is bounded: a physically allocated **10 GiB reserve** is separate
from the **8 GiB payload-and-metadata cap**, with a **1 GiB free-space floor**.
The reserve is not a filesystem quota. A long outage can exhaust the worker's
retry/evidence budget or local capacity; the implementation reports those
limits rather than promising unlimited offline operation.

## Actual controls and retained failures

| Current control group | Passing predicates |
| --- | ---: |
| Durable local spool | 30 |
| Native capture bridge | 18 |
| Independent publisher | 21 |
| Total | 69 |

The combined campaign passed 67 predicates. After strengthening header-prefix
retention, all 18 final capture predicates passed separately; the core and
publisher source bytes were unchanged. This covers 69 current predicates
across the saved campaigns, rather than claiming one clean 69-test run.
Across the full recorded history, **303 executions include 301 passes and
two retained host failures** caused by an invalid owned-process kind in an
early publisher. Their source versions, diagnostics and corrected runs remain
in the archive.

Controls exercise real files, subprocesses and local HTTP transfers. They
cover exact multi-part reconstruction, corrupted or reordered parts,
truncated rows and trailers, write/fsync/rename/ledger failures, storage caps,
invalid terminal manifests, offline publication followed by recovery,
permanent errors and SIGTERM at ownership boundaries. Independent saved
review reads all 3,967 archive members, including the full logical bytes of
sparse storage-limit fixtures. These injected file failures are not empirical
power-loss tests. Uncommitted bytes still in RAM can be lost on abrupt power
off, and partial waveform data is never a solver checkpoint.

## Numerical and delivery boundary

The new run retains all 539 devices, the 1 µs duration, 2.5 ps output step and
1.25 ps maximum solver step. The original startup, operating-point and safety
checks remain, as do the 100 ppm frequency and 50 ps phase criteria without
phase-offset removal. Native capture has no healthy elapsed-time timeout.
The storage change does not relax those acceptance gates.

Mutable native files, spool ledgers and publication journals are excluded
from this finite archive. Its immutable startup observation proves only that
the separately owned processes launched; it is not a current or terminal
status claim. Final capture completeness, public readback, full replay,
PLL acquisition and numerical convergence still need their own completed
receipts. PVT, qualified parasitics, PCIe PHY integration and chip signoff
remain open.
