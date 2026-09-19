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
| F0d | Recorded, refresh at delivery | Each ledger row names the revision actually tested. Latest prepared-source and final delivery runs must be recorded separately from the earlier bare-clone result; [verification record](evidence/verification-20260919.json). |
| F1 | Verified fix | SoC reset synchronization, flush regression and fresh NPU proofs; frozen pilot unchanged; [docs/87](87-engineering-closure.md), docs/89. |
| F2 | Function verified; method difference explicit | Double fault, watchdog reset and retained fault PC are exercised by the whole-CPU ROM/Verilog regression, rather than the specifically requested cocotb harness. Register-map checks and added area are recorded in docs/86; fresh CPU result in docs/89. |
| F3 | Verified fix | Shipping timeout enabled, APB pins quarantined until reset, one fabric error, retained event counter. Timeout-zero cost guard, never-ready test and APB/BUSSTAT/NPU proofs; [APB evidence](evidence/apb-timeout-20260919.json). |
| F4 | Review measurement delivered; product timing OPEN | Explicit flash/board SDC, minimum-divider arithmetic and unchanged default sampling; QSPI regression passes. Extracted violations remain failures; [QSPI STA evidence](evidence/qspi-sta-20260919.json). |
| F5 | Verified documentation fix | Orphan modules and their proofs are explicitly distinguished from instantiated hardware; docs/86. |
| F6 | OPEN | Committed metrics/configuration and digest checks exist. Bare clone at `e2193ec` still has 34 skips, including missing build artifacts. Neither acceptance clause is declared met by reducing a counter alone. |
| F7 | Review documentation delivered; physical closure OPEN | Named, costed routing keep-out experiment and accurate deck scopes in [ROADMAP](../ROADMAP.md). Actual macro-edge and vendor-cell violations still need resolution and rerun. |
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
| Gigabit Ethernet | GMII MAC and native SRAM packet/CPU tests exist; [docs/90](90-gigabit-ethernet.md). Final 125 MHz setup/hold, PHY integration and sustained traffic on hardware remain open. PIO is not a wire-rate DMA claim. |
| PCIe Gen3 x4 | OPEN: no complete controller/PHY instantiated. [docs/91](91-pcie-gen3-feasibility.md) records researched candidates and missing compatible physical IP. An FPGA hard-block wrapper or PIPE placeholder does not satisfy this gate. |
| Timing | OPEN: all applicable setup/hold, recovery/removal and electrical checks must pass with characterized clocks, corners and I/O budgets. Current post-global-route repair is not extracted signoff. |
| Physical verification | OPEN: independent Magic/KLayout DRC, antenna, connectivity, stream XOR and appropriately scoped LVS. SRAM black-box LVS does not verify SRAM transistor interiors. No failing deck is waived to obtain a green summary. |
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
