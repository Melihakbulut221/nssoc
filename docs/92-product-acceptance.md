<!--
SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
SPDX-License-Identifier: CC-BY-4.0
-->
# 92 — Product acceptance and complete external-review checklist

2026-09-19. The user requested every item in `nssoc-external-review.md`
and a complete product. This checklist keeps review acceptance separate from
product acceptance. A documented failure, an IP survey, a simulation model,
or a passing block test does not close a physical product requirement.
The review's historical reproduction is in [docs/89](89-external-review-follow-up.md).

## External-review acceptance

| Item | Current disposition | Evidence and remaining work |
|---|---|---|
| F0, F0a | Verified fix | Idempotent mirror handling retains the reworded-fragment negative control; [docs/86](86-the-external-review.md). |
| F0b | Verified fix | Upstream-prefixed historical commits retain provenance; public history is checked where applicable; docs/86. |
| F0c | Verified fix | Transparent `mbox` rendering and renderer regression; docs/86. |
| F0d | Recorded, refresh at delivery | Each ledger row names the revision actually tested. Clean remote `686e379` replay: 16 passing gates, zero failures, seven skips; [record](evidence/fresh-clone-netlist-20260920.json). Refresh again for later substantive source changes; bare-clone evidence remains separate. |
| F1 | Verified fix | SoC reset synchronization, flush regression and fresh NPU proofs; frozen pilot unchanged; [docs/87](87-engineering-closure.md), docs/89. |
| F2 | Verified fix, including cocotb | Whole-CPU firmware injection, watchdog reset, two APB retained-PC reads and ignored write pass under cocotb; [record](evidence/crash-cocotb-20260919.json). Register-map checks and added area are recorded in docs/86; full-program result in docs/89. |
| F3 | Verified fix | Shipping timeout enabled, APB pins quarantined until reset, one fabric error, retained event counter. Timeout-zero cost guard, never-ready test and APB/BUSSTAT/NPU proofs; [APB evidence](evidence/apb-timeout-20260919.json). |
| F4 | Review measurement delivered; product timing OPEN | Explicit flash/board SDC, minimum-divider arithmetic and unchanged default sampling; QSPI regression passes. Extracted violations remain failures; [QSPI STA evidence](evidence/qspi-sta-20260919.json). |
| F5 | Verified documentation fix | Orphan modules and their proofs are explicitly distinguished from instantiated hardware; docs/86. |
| F6 | OPEN | Committed metrics/configuration and digest checks exist. The historical bare clone at `e2193ec` had 34 skips. Added 2026-09-20: the [complete recorded netlist](evidence/ethernet-netlist-20260920.json) enables seven actual structural guards; a fresh remote clone measured 652 passes and 27 skips. The numeric threshold is met, but missing historical outputs still violate the complete first clause. Paper claims needing build output fell to seven; [record](evidence/fresh-clone-netlist-20260920.json). |
| F7 | Review documentation delivered; physical closure OPEN | Named, costed routing keep-out experiment and accurate deck scopes in [ROADMAP](../ROADMAP.md). The original 24-SRAM GDS now passes the [updated unmodified KLayout main deck](evidence/ihp-full-chip-drc-20260920.json); Magic and the final optimized geometry still require closure. |
| F8 | Accepted alternative proved | Real-codec contract and direct pinned-upstream equivalence with scrub on/off, induction and negative controls; docs/87. Core-level `reg_ch0` remains a non-verdict and is not relabelled PASS. |
| F9 | Verified documentation fix | Same orphan-module scope as F5; no inference from source/proof counts to instantiated logic. |
| F10 | Verified documentation fix | Collection command is authoritative; historical counts stay dated rather than silently overwritten; docs/86. |
| Section 5 | Inventory delivered; product work OPEN | The missing-silicon table exists in ROADMAP. Listing a pad ring, scan or debug gap is not implementing it. |
| Section 8 | Ongoing release gate | Keep frozen sources unchanged, bind measurements to commands/source hashes, rerun affected proofs, measure added cost, preserve correction history and distinguish SKIP from PASS. |

The verified-green baseline and the review's deliberate non-findings remain
constraints: do not rewrite the timer chain, reset memory arrays, edit the
frozen FIFO, delete orphan research blocks, or present probe modules as product
hardware merely to increase apparent coverage.

## Product release gates

| Requirement | Current implementation and closure condition |
|---|---|
| Integrated functional core | ECC memory, protected register file, boot recovery and telemetry have block/formal/CPU evidence. Final RTL and final netlist must match the delivered layout. |
| SpaceWire | Integrated RTL and packet/link regression; implementation scope in [docs/88](88-interface-integration.md). Final pins, physical timing and external transceiver integration remain product gates. |
| CAN, SPI, I2C | Integrated RTL, APB access and protocol tests; docs/88. External electrical interfaces, pad timing and board validation remain product gates. |
| Gigabit Ethernet | GMII MAC and native SRAM packet/CPU tests exist; [docs/90](90-gigabit-ethernet.md). All ten GMII data/control output ports pass the stated budgets in the three separately extracted baseline corners; [record](evidence/ethernet-extracted-layout-20260920.json). Internal 125 MHz paths still fail setup. PHY/pad integration and sustained traffic on hardware remain open. PIO is not a wire-rate DMA claim. |
| PCIe Gen3 x4 | OPEN: no complete controller/PHY instantiated. [docs/91](91-pcie-gen3-feasibility.md) records researched candidates and missing compatible physical IP. An FPGA hard-block wrapper or PIPE placeholder does not satisfy this gate. |
| Timing | OPEN: all applicable setup/hold, recovery/removal and electrical checks must pass with characterized clocks, corners and I/O budgets. The extracted baseline fails slow setup and fast hold, plus slew/capacitance. Added 2026-09-20: [ECO2 native extraction](evidence/ethernet-eco2-extracted-20260920.json) passes hold in all three corners but still fails slow setup (-1.063485 ns), capacitance, slew and fanout. Later global-route estimates are not extracted signoff. |
| Physical verification | OPEN: independent Magic/KLayout DRC, antenna, connectivity, stream XOR and appropriately scoped LVS. SRAM black-box LVS does not verify SRAM transistor interiors. A separate six-diode antenna repair passes its independent check; [record](evidence/ethernet-antenna-repair-20260920.json). The separate [ECO2 antenna check](evidence/ethernet-eco2-extracted-20260920.json) also reports zero, and its [scoped LVS passes](evidence/ethernet-eco2-lvs-20260920.json). Its DRC/XOR remain separate gates. The original baseline passes the updated KLayout main deck; [record](evidence/ihp-full-chip-drc-20260920.json). No failing deck is waived to obtain a green summary. |
| Pad ring and package | OPEN: compatible I/O/ESD cells, power/ground pads, package/bond plan and board-level budgets. `soc_top` is currently a core block. |
| DFT and memory test | OPEN: scan/test access, ATPG coverage and usable memory BIST with documented fault model. Parked BIST pins provide no array-test coverage. |
| Debug and interrupts | OPEN: usable halt/inspect/debug access and an explicit external-interrupt product contract; internal peripheral interrupts alone do not provide these. |
| Clock, reset and power | OPEN: clock-source/PLL choice, POR/brownout integration, supply integrity and characterized startup behaviour. Top-level clock/reset inputs are not physical circuits. |
| Fault protection | Existing protection is scoped to documented structures. Lockstep/bus integrity, interface protection and radiation qualification remain open; no silicon or beam data exists. |
| Reproducible release | OPEN until source pins, build commands, generated dependencies, final evidence, firmware and interface limitations accompany the exact delivered revision. Historical absent artifacts remain explicitly absent. |

Current physical candidate: `interfaces-eth256-resume-20260919-184950`, using
the input inventory in [the Ethernet evidence](evidence/ethernet-sram256-20260919.json).
The failed multi-repair optimizer and the missing-RC diagnostic correction are
preserved in [the timing replay record](evidence/timing-replay-20260919.json).
Neither is accepted as a replacement for the native physical flow.

Added 2026-09-20: the next [fresh remote clone at c966a43](evidence/fresh-clone-c966a43-20260920.json)
measures 653 passes / 26 skips and the same 16/0/7 CI gate totals. This adds the
recorded-netlist clock-gate census; it does not close the historical-artifact
part of F6. The later [ECO7 functional controls](evidence/ethernet-eco7-controls-20260920.json)
pass structural logic/state checks and the fault-free watchdog-armed workload.
Its native routing/extraction is still pending; the ECO2 timing result above
remains the latest completed optimized physical measurement.

**Dated update, 2026-09-20:** ECO7 is no longer pending. Its
[native extracted measurement](evidence/ethernet-eco7-extracted-20260920.json)
passes hold in all three corners, route DRC and both antenna checks. Slow
setup remains **-0.529278 ns / 109 violations**, with slew/capacitance/fanout
failures. This supersedes ECO2 as the latest completed optimized native
measurement; independent ECO7 DRC/XOR/LVS are still separate open gates.
The [later repair experiments](evidence/ethernet-clock-repair-20260920.json)
reduce estimated fanout to zero but still fail timing and slew. None is a
released final layout. All four SRAM Magic comparison arms are complete and
fail; [the evidence](evidence/ihp-magic-sram-followup-20260920.json) preserves
the deck/reader distinctions rather than waiving a failing result.
