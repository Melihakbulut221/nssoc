# 102 — Remaining product gaps, 26 September 2026
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

This audit examines `ec7a92fca6344875cbf35512a69da60c05cde8a0`, the two
user-supplied reviews, current RTL, acceptance registers, recorded source hashes,
local job state, GitHub delivery and official IHP/Gaisler material. The
[machine-readable snapshot](evidence/open-items-audit-20260926.json) records
attachment hashes, source identities, live observations and their time.
It is an evidence audit, not a fresh physical or complete hardware regression.
Review documents supply requirements and hypotheses; their old findings do not
override newer measurements. No manufacturing approval is recorded.

## 1. What is actually closed

* The [prepared local pytest replay](evidence/prepared-pytest-edc4e2d-20260926.json)
  ran **1,669 cases, zero failures, zero skips**, on source commit `edc4e2d`.
  All fourteen former fixture skips executed. The publication commit changes
  documentation/evidence, not the measured RTL or tests. This result does not
  include every cocotb, formal, physical or production check.
* Exact GDS `f218313c8a9e3ebe95e35cf0fc505852d88d342e9c2c6b4423f10a309f1a4cf1`
  has [accepted local physical evidence](evidence/sram-repaired-core-physical-20260926.json):
  560 native main categories, seven density categories, 31 antenna categories
  and eleven supplemental wide-spacing rules report zero markers. Full
  transistor LVS matches 130 circuits and 5,129,488 primitives on each side.
  The GDS and public physical/test archives were rehashed during this audit.
  This is the **32-SRAM digital core**, without a padframe or PCIe PHY.
* UART RX, external IRQ, APB timeout, reset repair, real-codec register-file
  contracts, register-offset/HAL generation, scoped lint and distribution
  licensing have implementation and test evidence. Historical claims that
  these are wholly absent must not be repeated.

## 2. Product blockers and the evidence needed to close them

| ID | Remaining work | Present evidence and required closure |
|---|---|---|
| P01 | Complete SRAM characterization | Repaired DP TT/SS/FF capacitance-only patterns pass. These are selected stimuli/load/slew points, not complete libraries. Both SP and DP need address/data/mask coverage; read/write/enable/address constraints in both directions; setup/hold, minimum pulse width, collision behavior, load/slew/PVT grids, internal power and leakage. Generate complete Liberty only after independent table validation. [Characterization scope](101-sram-characterization.md#6-remaining-acceptance-work). |
| P02 | Qualified distributed and coupled RC extraction | Current accepted transient circuits retain capacitors but omit distributed resistance. Transistor PVT does not provide process-correlated RC corners. Earlier extraction diagnostics exposed contact/terminal attachment and capacitance-serialization problems; isolated repairs/benchmarks do not qualify the entire flow. Validate connectivity, resistor attachment, coupling conservation, process references and corner correlation for the final geometry. |
| P03 | Final timing and electrical closure | No accepted final STA exists for the repaired 32-SRAM GDS with characterized replacement memories. Historical ECO24 slow setup is **−3.254664 ns with 75 slew violations**; its zero capacitance violations and positive hold do not transfer to the repaired core. Re-extract final interconnect and verify setup/hold, recovery/removal, pulse widths, I/O budgets, clock uncertainty, derating, slew/capacitance/fanout and justified CDC/reset exceptions. [Historical receipt](evidence/eco24-extracted-timing-20260923.json). |
| P04 | Complete PCIe Gen3 x4 controller | Only standalone register TLP/backend and DWORD stream blocks exist. Neither is instantiated in `soc_top`. Complete link training, Data Link handling, sequencing/ACK/replay/credits/CRC, Gen3 encoding/scrambling, lane handling, configuration/interrupt behavior and host integration still need design and verification. The existing single-DWORD register subset is not a complete endpoint or root port. [RTL scope](98-pcie-transaction-backend.md). |
| P05 | PCIe analog PHY and physical integration | Two SPICE sources implement experimental TX cells/four-cell bank. No complete RX, CDR/PLL, serializer/deserializer, equalization, reference/calibration, ESD/pads, channel/package model or PHY GDS/LEF exists. Forty non-faulty pre-layout cases meet a limited screen, but thirteen hot-corner runs retain warnings; three faulty cases were detected. Resolve numerical/model issues, implement physical cells and prove extracted PVT/jitter/channel behavior before integration. No PCIe compliance or BER result exists. [Analog scope](99-pcie-phy-development.md). |
| P06 | Ethernet product behavior | A fixed 1 Gb/s full-duplex GMII MAC exists, using APB programmed I/O. It has no DMA and cannot sustain uninterrupted wire-rate traffic through the 50 MHz APB path. External PHY, pads/board timing, autonomous management/auto-negotiation driver and hardware traffic qualification remain open. Packet buffers/control are not ECC/TMR protected. [MAC contract](90-gigabit-ethernet.md). |
| P07 | Other interfaces at the pins | SpaceWire, classic CAN, SPI and I2C have RTL/profile-specific evidence. SpaceWire/CAN require explicit `full`; the default `base` disables them. They still need final pin/pad timing, external transceivers or pull-ups as applicable, clock-domain/reset checks and board tests. UART RX works, but that does not establish a final pad-qualified product. [Profiles](88-interface-integration.md). |
| P08 | Padframe, package and power | Select and integrate IO/ESD/power cells, pad/bond plan, package, seal-ring/boundary requirements and board budgets. Verify supply integrity under activity, electromigration/current density, thermal limits and signal integrity for the assembled product. A routed core power grid and static historical IR reports are insufficient. |
| P09 | Clock, POR and brownout circuits | Top-level clock/reset inputs are not an on-chip source, POR or brownout detector. Define external versus on-chip clocking and startup contracts, implement required circuits, and validate reset release and failure behavior across supplies/corners. PCIe clock recovery/shared clocking is separately absent. |
| P10 | DFT, MBIST and debug access | No delivered scan/ATPG coverage, usable array MBIST or RISC-V debug/JTAG path. `soc_top` still ties debug request and test enables inactive; native-memory BIST inputs are parked. Scrubbing and fault injection are not manufacturing tests. Close with implemented access, fault-model/coverage reports and functional revalidation. |
| P11 | End-to-end fault/radiation qualification | SecureIbex/lockstep is disabled and shadow interfaces are disconnected. Protection is scoped, not comprehensive. Extend fault campaigns to relevant fabric/peripheral state, multiple-bit and logic-transient faults, explicit functional/code coverage and X/error handling. Radiation/beam, reliability and silicon data do not exist. Treat the AER multi-node/mesh work as an additional architecture gap, not implemented by one local NPU. |
| P12 | Final integrated verification | Complete a source-bound full cocotb/formal/firmware/native-netlist campaign for the delivered configuration; check equivalence and timing-aware behavior against final views. Whole-core `reg_ch0` and M-extension formal obligations remain non-closing. Legacy SRAM-ROM parity remains distinct from the selected logic-ROM implementation. Validate hardware driver transports on a board and retain independent error controls. |
| P13 | Reproducible release and evidence delivery | Reconcile status/verification ledgers with latest receipts; retain exact historical provenance. Finish portable physical reproduction, historical artifact recovery where claimed, durable binary hosting, publication-claim review and release metadata. Commit-history/identity work and release/DOI are still review items, not implemented by adding documents. |
| P14 | Foundry and post-fabrication acceptance | Produce a coherent final submission package, select/agree the applicable PDK/decks and license/submission route, obtain external review/acceptance and then perform silicon/package/board qualification. Passing local reports do not issue foundry approval. See section 6. |

P08–P10 require new physical/product content; they are not repairable merely by
rerunning the existing core checks. Adding that content changes the final
geometry, so its physical, electrical and timing checks must be run again.

## 3. What is still running locally

The snapshot records SP TT as running, SP SS/FF as waiting for audited TT,
and the independent SP completion auditor as waiting. The repaired DP read-setup
search is running; it covers **only one rising address arc at TT**, 100 ps ramps,
5 fF load and a 25 ps maximum timestep. Completion would not close P01 or P02.

The repaired DP 25 ps transient and timestep comparison completed locally.
Across forty transitions, maximum absolute changes relative to 50 ps are
0.020866732 ns delay and 0.001574689 ns slew; supply energies are approximately
118.1765 and 118.1169 pJ. Two numerical step sizes do not prove the zero-step
limit. These newer results were not separately published as completed
characterization at the audit time. Active simulations were not restarted or
modified for this audit. Terminal results must be audited before publication.

## 4. Verification and documentation gaps found in this audit

1. **Formal inventory freshness:** the selected published sweep covers 161
   tasks; the current inventory contains **170 mandatory tasks and six explicit
   historical exclusions**. The added tasks are BMC/prove/cover for the PCIe
   register backend, PCIe stream and request pipeline. Separate block evidence
   exists; the finding is not that these nine tasks have never passed.
   Comparing 174 recorded source hashes finds five changed paths, including
   `soc_top.v` and the formal Makefile. The old aggregate cannot certify the
   current source as a whole. The six historical scrub-engine exclusions are
   distinct from the open whole-core/M-extension obligations; real-codec scrub
   contracts have newer accepted proofs.
2. **CI scope:** the latest hosted full check was still running at the snapshot;
   native boot is opt-in and was skipped. Ordinary push/PR checks select the
   `base` interface profile, so they do not automatically validate SpaceWire/CAN.
   Three earlier local front-door skips (pandoc, LibreLane checker interpreter,
   prepared SoC lint) are separate from the now-closed fourteen pytest skips.
   Prepared lint has separate local passing evidence, not a retroactive pass
   for those skipped gates.
3. **Status freshness:** README/project-status still select 1,293 pytest passes
   and an older route-estimate timing result. They name their revisions, so
   these are historical measurements, but they are not the newest status.
   The top-level verification log is also historical; later receipts are
   dispersed. Consolidate current sources without attributing all passes to
   one untested combined revision.
4. **Delivery:** remote work branch is `ec7a92f`, while default `main` is
   `473b84f`; PR #1 is still draft. Push is not merge or a product release.
   Do not rewrite history or merge solely to make this status green.
5. **Evidence availability:** the preceding digest check had 292 verified
   entries and 329 missing historical run artifacts, with zero changed or
   extractor-drift entries. Missing historical entries are not 329 new design
   defects; they require recovery/explicit disposition wherever a claim relies
   on them. The complete pending characterization campaign is not yet published.

## 5. Reconciliation with both supplied reviews

The second register has **25 rows: nine DONE within their stated scope, ten
PARTIAL, six OPEN**. These are register categories, not a percentage-complete
product score. The snapshot retains every row's original disposition.

| Review IDs | Remaining disposition after cross-check |
|---|---|
| First F0/F0a/F0b/F0c | Recorded fixes and provenance/rendering controls exist. Preserve their scope. |
| First F0d/F10 | New pytest evidence exists; latest aggregate ledger/status reconciliation remains P13. |
| First F1/F2/F3 | Reset, retained crash telemetry and APB timeout have fixes/tests. Not newly missing. |
| First F4 | Timing contract/regressions exist; final extracted closure remains P03. |
| First F5/F9 | Orphan reachability and source-versus-instantiation documentation exist. |
| First F6/F7 | Published exact-core geometry/DRC/LVS now exists; historical artifact and complete-product qualification remain P08/P13/P14. Do not repeat the old statement that no layout evidence or no DRC-clean core exists. |
| First F8 | Accepted alternative register-file contracts/equivalence exist; whole-core/M-extension obligations remain P12. |
| First sections 5/8 | Product gaps and standing evidence/frozen-source constraints continue to apply. The original section 5 asked for an inventory; the user's later product requests independently authorize engineering work. |
| Second 0.1, 1.1–1.4 | TT guide, tracked checkpoint hygiene, optional LGPL profile, Tcl skip handling and CI wording have scoped closure. Historical commits still retain previously public checkpoints. |
| Second 1.5–1.8 | Evidence hosting, history/identity, documentation reconciliation and product gates remain open/partial. |
| Second 2.1–2.3 | Hardware jobs/tool bootstrap exist; complete current-source regression, full-profile/native boot and reproducible final physical flow remain. |
| Second 2.4–2.6 | Final timing, named historical evidence and whole-core/M-extension proof gaps remain. |
| Second 3.1–3.2 | Orphan/RAM parity, UART RX, peripheral formal and direct tests improved; legacy ROM, wider FI/coverage and final product verification remain. |
| Second 3.3–3.4 | Scoped lint/nettype and REUSE distribution checks pass. Recorded warnings are not physical signoff or patent clearance. |
| Second 3.5 | Concise README/diagram/status machinery exists; latest evidence selection and broader claim reconciliation remain. |
| Second 3.6 | PNR/energy selection tooling repaired; final timing and actual workload power remain separate. |
| Second 3.7 | Common driver/backends exist; actual hardware transport qualification remains. |
| Second 3.8 | Register offsets and shared HAL closed within scope; bit-field extensions/full firmware qualification not claimed. Boot-range CBMC exists; a claim that all software proof is absent would be wrong. |
| Second 3.9 | Repo guidance, Python tools and paper/thesis gates improved; complete scientific-claim/type review, release and DOI remain. |
| Second section 4 | P01–P14 apply. Original dummy-fill/SRAM-LVS/external-IRQ absences are partly superseded by actual implementation; final whole-product acceptance is not. |

## 6. External dependencies and GR801 comparison

The [IHP open PDK status](https://github.com/IHP-GmbH/IHP-Open-PDK#current-status----preview)
still labels the open release a preview not intended for production. This is
not a claim that SG13G2 silicon cannot be fabricated. IHP offers a separate
[open-silicon MPW route](https://dk.ihp-microelectronics.com/OpenSourceRequest.php),
and its [submission process](https://github.com/IHP-GmbH/Open-Silicon-MPW/blob/main/Submission-process.md)
requires foundry evaluation and confirmation. No accepted submission or slot
for this SoC is recorded. The low-cost open route states Apache-2.0 design and
publication conditions plus an agreement; this repository's mixed hardware/IP
licenses must be reconciled with the chosen route without silently relicensing
third-party IP. Eligibility requires confirmation, not a local checker result.

The [published library inventory](https://ihp-open-pdk-docs.readthedocs.io/en/main/contents/01_libraries.html)
lists primitive, standard-cell, IO and SRAM libraries, not a ready PCIe PHY.
That supports the missing-public-macro finding, not a claim about every private
or commercial IP offering.

The [official GR801 specification](https://www.gaisler.com/products/gr801)
includes PCIe Gen3 x4 root/endpoint capability, 10/100/1000 GMII Ethernet,
a four-port SpaceWire router, two CAN FD ports, two I2C and three UARTs, and
an 8-bit camera interface. This design currently has one PIO SpaceWire link,
classic CAN, one I2C and one UART, fixed Gigabit Ethernet and no CPI. These
are **reference-product differences**. The user's explicit PCIe Gen3 x4/Gigabit
targets do not automatically require duplicating every other GR801 feature.
A shared protocol name alone does not establish feature or qualification parity.

## 7. Dependency order

Finish and audit the current SRAM runs, then qualify extracted RC and complete
memory libraries before final core STA. In parallel engineering tracks, develop
the PCIe controller/PHY and implement pad/power/clock/reset/test/debug interfaces.
Only the assembled product can undergo final geometry/timing/electrical and
functional qualification. Refresh the complete regression and release evidence
against that exact result, then seek the applicable external fabrication review.
There is no defensible completion percentage or manufacturing date from the
current evidence.

## Subsequent local closure work

The dated observations above remain the audit snapshot. The
[local continuation](103-local-closure-progress.md) publishes subsequent RTL
regression, complementary profile coverage, DP numerical-step comparison and
native-resistor TX engineering. README/project-status now selects the completed
1,669-case pytest receipt and the exact 32-SRAM physical checkpoint, retaining
historical timing as historical. These changes close evidence freshness items
within those scopes; they do not close P01–P14 as complete product gates.

The subsequent [TX-cell and read-arc work](103-local-closure-progress.md#complete-experimental-tx-cell-layout)
closes the previously absent single experimental TX-cell geometry with main
DRC, strict LVS and negative controls. It also completes one repaired DP read
setup bracket and complementary retention observation. P01 and P05 remain open
at product scope: these are neither a complete SRAM library nor a Gen3 x4 PHY.

The later [destructive SRAM test engine](103-local-closure-progress.md#destructive-sram-test-engine-and-raw-port)
adds a raw-word March engine and exclusive test-port wrapper with executable
fault and native functional-model checks. It narrows P10's missing implementation
work but does not close chip-level MBIST access, scan/ATPG or debug qualification.

The [subsequent completed campaign](103-local-closure-progress.md#completed-local-verification-and-delivery)
closes the stale 170-task formal-inventory result at its recorded revision and
adds a full 1,825-case local Python replay with zero skips. Repaired SP TT selected
patterns also pass independent completion checks. The new full DP resistor
extraction **fails capacitance conservation**, so P02/P03 remain blocked by an
actual measured defect, not merely an unexecuted job. SP SS/FF and queued TT25
remain pending, and P01/P04–P14 are not promoted to complete by these receipts.
