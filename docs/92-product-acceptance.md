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
| F0d | Recorded, refresh at delivery | Each ledger row names the revision actually tested. Clean remote `0727236` replay: 902 pytest passes / one tool-absence skip, 16 passing gates / zero failures / seven skips; [record](evidence/fresh-clone-0727236-20260920.json). Refresh again for later substantive source changes; bare-clone evidence remains separate. |
| F1 | Verified fix | SoC reset synchronization, flush regression and fresh NPU proofs; frozen pilot unchanged; [docs/87](87-engineering-closure.md), docs/89. |
| F2 | Verified fix, including cocotb | Whole-CPU firmware injection, watchdog reset, two APB retained-PC reads and ignored write pass under cocotb; [record](evidence/crash-cocotb-20260919.json). Register-map checks and added area are recorded in docs/86; full-program result in docs/89. |
| F3 | Verified fix | Shipping timeout enabled, APB pins quarantined until reset, one fabric error, retained event counter. Timeout-zero cost guard, never-ready test and APB/BUSSTAT/NPU proofs; [APB evidence](evidence/apb-timeout-20260919.json). |
| F4 | Review measurement delivered; product timing OPEN | Explicit flash/board SDC, minimum-divider arithmetic and unchanged default sampling; QSPI regression passes. Extracted violations remain failures; [QSPI STA evidence](evidence/qspi-sta-20260919.json). |
| F5 | Verified documentation fix | Orphan modules and their proofs are explicitly distinguished from instantiated hardware; docs/86. |
| F6 | ACCEPTANCE MET | Fresh remote `0727236`: **902 pytest passes / 1 tool-absence skip**. Exact original historical DEF/netlists and raw reports are restored from digest-checked snapshots into test scratch space. Paper: seven claims need build output, zero wrong; evidence digest tests pass. [Full clone record](evidence/fresh-clone-0727236-20260920.json). Seven front-door skips remain separately reported, not counted as passes. |
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
| Gigabit Ethernet | GMII MAC and native SRAM packet/CPU tests exist; [docs/90](90-gigabit-ethernet.md). ECO22 passes setup/hold in three Liberty corners with nominal RC; [record](evidence/ethernet-eco22-extracted-20260920.json). Electrical violations remain. The newer IRQ/logic-ROM candidate needs its own closure. PHY/pad integration and sustained traffic on hardware remain open. PIO is not a wire-rate DMA claim. |
| PCIe Gen3 x4 | OPEN: no complete controller/PHY instantiated. [docs/91](91-pcie-gen3-feasibility.md) records researched candidates and missing compatible physical IP. An FPGA hard-block wrapper or PIPE placeholder does not satisfy this gate. |
| Timing | OPEN: all applicable setup/hold, recovery/removal and electrical checks must pass with characterized clocks, corners and I/O budgets. [ECO22 native extraction](evidence/ethernet-eco22-extracted-20260920.json) passes setup/hold in three Liberty corners with nominal RC, but still fails capacitance, slew and fanout. The newer external-IRQ/logic-ROM candidate requires its own extracted checks. Global-route estimates are not extracted signoff. |
| Physical verification | OPEN: independent Magic/KLayout DRC, antenna, connectivity, stream XOR and appropriately scoped LVS. SRAM black-box LVS does not verify SRAM transistor interiors. A separate six-diode antenna repair passes its independent check; [record](evidence/ethernet-antenna-repair-20260920.json). The separate [ECO2 antenna check](evidence/ethernet-eco2-extracted-20260920.json) also reports zero, and its [scoped LVS passes](evidence/ethernet-eco2-lvs-20260920.json). Its DRC/XOR remain separate gates. The original baseline passes the updated KLayout main deck; [record](evidence/ihp-full-chip-drc-20260920.json). No failing deck is waived to obtain a green summary. |
| Pad ring and package | OPEN: compatible I/O/ESD cells, power/ground pads, package/bond plan and board-level budgets. `soc_top` is currently a core block. |
| DFT and memory test | OPEN: scan/test access, ATPG coverage and usable memory BIST with documented fault model. Parked BIST pins provide no array-test coverage. |
| Debug and interrupts | One synchronized external machine-interrupt level and vector 11 now have RTL/native-cell CPU evidence; [contract](94-external-interrupt.md). Final physical and fault qualification remain open. Usable halt/inspect/debug access remains unimplemented. |
| Clock, reset and power | OPEN: clock-source/PLL choice, POR/brownout integration, supply integrity and characterized startup behaviour. Top-level clock/reset inputs are not physical circuits. |
| Fault protection | Existing protection is scoped to documented structures. Lockstep/bus integrity, interface protection and radiation qualification remain open; no silicon or beam data exists. |
| Reproducible release | OPEN until source pins, build commands, generated dependencies, final evidence, firmware and interface limitations accompany the exact delivered revision. Historical artifacts recovered for F6 do not certify the current SoC. |

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

The original baseline's [full-chip abstract Magic check](evidence/ihp-magic-full-chip-20260920.json)
has completed with **642 boxes: 436 within LEF footprints and 206 outside**.
All outside boxes are within 0.5 µm of a macro. This is a measured failure,
not a waived abstract or a real macro-interior GDS signoff result. Its
completion does not close the physical-verification product gate.

The [CPU Ethernet loopback](evidence/ethernet-cpu-loopback-20260920.json)
now passes both RTL and the ECO13 native-cell netlist: eight frames, 2,171
payload bytes, eight CRC checks and matching software signatures/interrupt
checks. This closes that fault-free integration test; Ethernet PHY/pads,
final timing, fault qualification and hardware throughput remain open.

The next [clean remote replay at df0c190](evidence/fresh-clone-df0c190-20260920.json)
measures **707 passes / 26 skips**, with **16 passing CI gates, zero failures
and seven skips**. No run artifacts or generated dependencies were copied
into that clone. It includes the 35-test ECO checker and 19-test Ethernet
probe checker; the later primary-input-aware checker is tested separately.
Historical absent-artifact skips still prevent full F6 acceptance.

The [F7 routing-halo experiment](evidence/ihp-routing-halo-20260920.json)
now has implemented, checked preparation: 2,766 blockages around the original
24-SRAM baseline, same netlist and placement, and retained pin corridors.
The global-route trial is running; detailed routing and a new unchanged-deck
Magic verdict remain pending. This advances the named experiment while
leaving physical-verification acceptance open.

The [fresh remote source replay at 5675eea](evidence/fresh-clone-5675eea-20260920.json)
completes with **743 passes / 26 skips** and **16 passing CI gates / zero
failures / seven skips**. This includes the 43-test ECO guard, 19-test CPU
probe checker, 11-test guide cleanup and 17-test halo geometry checks.
The initial attempt to start CI before cloning finished ran no tests and
is retained separately as a corrected launch error. The successful replay
starts from a verified clean HEAD; no generated dependencies or physical
outputs were copied into the clone. F6's historical-artifact clause remains
open.

**Dated update, 2026-09-20:** the [native ECO18 retry](evidence/ethernet-eco18-extracted-20260920.json)
has finished. Route DRC, antenna and critical connectivity checks pass, as
does the restricted comparison preserving all 96,584 original cells. Slow
setup remains **-0.785313 ns / four violations** and fast hold **-0.039599 ns /
four violations**, with electrical failures. All ten GMII output ports pass
the stated budgets, but internal timing does not. Independent XOR/LVS and
updated main-deck DRC are running on this exact geometry. The subsequent
ECO19/ECO20 sizing trials are separately recorded estimates, not accepted
native replacements. Product timing and physical-verification gates remain
open; F6's missing historical outputs and the external product dependencies
are unchanged.

The [independent ECO18 stream XOR](evidence/ethernet-eco18-xor-20260920.json)
now passes: both the flow metric and an independent XML item count are zero.
This closes stream agreement for ECO18 only; its LVS/DRC and failing timing
remain separate gates.

The [ECO18 scoped LVS](evidence/ethernet-eco18-lvs-20260920.json) now passes
with 97,150 devices / 96,311 nets on both sides and zero mismatch counters.
SRAM interiors are still black boxes. Updated main-deck DRC is still running;
ECO18 timing/electrical failures remain open. ECO22 is a separate native
candidate testing 196 added load-group buffers; its passing structural
comparison is not a native timing or antenna verdict.

The [clean remote replay at cfa6c2e](evidence/fresh-clone-cfa6c2e-20260920.json)
now measures **768 passes / 26 skips**, and **16 passing CI gates / zero
failures / seven skips**. This includes the five automatic flow-integration
controls and 20 postroute controls added after the earlier 743-pass replay.
No generated dependencies or physical outputs were copied into this clone.
The measured ledger row is preserved verbatim; F6's absent historical
artifacts are still absent, and every skip remains explicitly reported.

**New RTL work, 2026-09-20:** [external IRQ support](94-external-interrupt.md)
now provides one synchronized machine-external level and vector 11. A real
CPU test exposed and reproduced an interrupt-stub `t0` clobber; the corrected
stub passes the same test. Debug/JTAG, physical integration, synchronizer
SEU/MTBF qualification and the full product gate remain open. Existing
ECO18/ECO22 physical measurements refer to the earlier source without this
new pin. Follow-up synthesis and broader firmware verification are pending.

**IRQ update, 2026-09-20:** the [delivered external IRQ evidence](evidence/external-irq-20260920.json)
now includes passing RTL/native-cell CPU tests, the expected legacy-`t0`
negative control, matched synthesis (+2 flops), and the passing 28-check
normal firmware regression. SDC exception scope passes on the new netlist;
its typical preplacement interstage hold slack is -0.033690 ns, retained
as a failure. This partially implements the interrupts row, while debug,
physical timing, pads and fault qualification remain open.

**Recovery update, 2026-09-20:** the [clean 82ab25c replay](evidence/fresh-clone-82ab25c-20260920.json)
completed with **787 pytest passes / 26 skips**, plus **16 passing front-door
gates / zero failures / seven skips**. Its GitHub push and PR workflows also
completed successfully (runs 35489687890 and 35489689118). These results
include the external IRQ change. Historical-artifact skips still leave F6
open; a skip is not a pass.

The [ECO18 updated main-deck DRC](evidence/ethernet-eco18-drc-20260920.json)
now passes with zero markers, independently recounted from the XML, and
all locked input digests still match. This closes that deck for ECO18 only;
its failing timing, Magic and macro-interior LVS are separate requirements.

The [ECO22 native extraction](evidence/ethernet-eco22-extracted-20260920.json)
now passes setup and hold in all three measured Liberty corners, with
nominal RC extraction: worst setup **+0.158629 ns**, worst hold
**+0.045536 ns**, zero setup/hold violations. Route DRC, antenna and critical
connectivity counts are zero, and postroute comparison preserves all
96,780 seed cells with only 550 antenna and 251,459 filler/decap additions.
Electrical checks still fail (up to 23 slew, nine capacitance and 43 fanout
violations). Independent DRC/XOR/LVS on this geometry remain open. Neither
this netlist nor its GDS contains the later external IRQ or logic-ROM work.

An explicit additional release gate is **physical boot-ROM contents**:
the SRAM stand-in cannot power up with executable firmware on silicon.
The [constant-ROM prototype](evidence/logic-boot-rom-prototype-20260920.json)
passes all 2,048 addresses and frozen-encoder comparisons in RTL and native
cells, rejects writes, and passes all 28 full-CPU boot/firmware checks with
no ROM preload. It synthesizes to standard cells with zero SRAM macros.
It is still an isolated copied-top experiment; the delivered top and layout
have not adopted it. Integration, image provenance, physical timing and
fault qualification remain required.

The halo routing run was interrupted before its final state was written.
A completed intermediate database preserves 93,459 original cells, 894
added antenna cells and all 2,766 routing blockages; the structural check
passes. Recovery resumes the remaining antenna iterations in a separate
output directory. The earlier supervisor's `RUNNING` field is stale after
the system restart; there is no final halo/Magic verdict yet.

**Integration update, 2026-09-20:** the earlier copied-top ROM prototype is
now followed by a [delivered logic-ROM profile](95-immutable-boot-rom.md).
Its [record](evidence/logic-boot-rom-integration-20260920.json) verifies
151 affected tests, a further 72 physical-source guards, the 28-check normal
CPU regression, and the exhaustive native-cell ROM test. Synthesis removes
the four ROM SRAMs and retains twenty RAM/Ethernet macros. The new physical
profile includes the external IRQ and has passed the actual lint error and
timing-construct checkers; 1,139 lint warnings remain reported. New placement
is in progress; no old layout result is transferred to it. Flash geometry
fallback tests are running separately.

ECO22's own [Magic/KLayout stream XOR](evidence/ethernet-eco22-xor-20260920.json)
passes with zero independently counted differences. Its own main-deck DRC
and scoped LVS are running. The electrical failures above still apply.

**Supplemental verification, 2026-09-20:** the [clean remote 7dd103d replay](evidence/fresh-clone-7dd103d-20260920.json)
passes **799 tests / 26 skips**, with **16 passing front-door gates / zero
failures / seven skips**. Both logic-ROM flash-geometry fallbacks now pass
28 CPU checks and select the secondary image. These measured results
supersede the pending fallback statement above. Missing historical artifacts
still leave F6 open.

ECO22's [scoped LVS](evidence/ethernet-eco22-lvs-20260920.json) now passes
with **97,334 devices / 96,507 nets** on each side and zero mismatch counters.
The SRAM interiors are black boxes. Its own independent main-deck DRC is
still running; neither this LVS nor stream XOR closes electrical failures.

The [recovered halo route](evidence/halo-routing-recovery-20260920.json)
now completes with zero route DRC, antenna and critical-connectivity counts.
The structural check preserves 93,459 original cells and permits only 1,075
antenna additions before filler insertion. The actual candidate was streamed
and its unchanged installed-deck DEF/LEF Magic check is running. This remains
the older 24-macro design, not the new IRQ/logic-ROM layout.

The [actual SRAM transistor-LVS investigation](evidence/sram-transistor-lvs-20260920.json)
fails with both installed and updated deep-mode decks. Full-flat controls
time out without a verdict. Isolated controls identify an unresolved metal
resistor model and power/hierarchy/port differences; none establishes a
passing SRAM. The new database-and-log auditor rejects skipped circuits and
strict-port failures even when the raw KLayout process exits zero. All
geometry, CDL, rules and failing reports are preserved without waivers.

The subsequent [clean 0a79a3b remote replay](evidence/fresh-clone-0a79a3b-20260920.json)
passes **816 tests / 26 skips**, with the same **16/0/7** front-door totals.
Both 7dd103d hosted workflows (35497437243 and 35497438504), including the
whole-CPU fixed-ROM normal/fallback checks, have now completed successfully.
The later [reader controls](evidence/sram-lvs-reader-controls-20260920.json)
retain an independent real-cell positive control, deliberate missing-device
negative control and a still-failing experimental pin-reader diagnostic.
They neither waive the SRAM failures nor close F6's historical-artifact gap.

**Physical follow-up, 2026-09-20:** ECO22's own [updated main-deck DRC](evidence/ethernet-eco22-drc-20260920.json)
now passes with **zero independently recounted XML markers**, successful
process completion and unchanged locked input hashes. Together with its
own stream XOR and scoped LVS this completes those three checks for that
candidate. Its electrical failures, Magic and SRAM-interior requirements
remain open; the later IRQ/logic-ROM design is still separate.

The [ECO24 buffer-tree trial](evidence/ethernet-eco24-branches-20260920.json)
preserves all 97,330 original routed cells, including 550 antenna diodes,
and adds 166 positive buffers (3,915.4752 square micrometres). Exact pin,
state and interface comparison passes. Fresh global routing has zero
overflow and estimated fanout violations fall to zero in all three corners.
Estimated slow setup remains -0.133847 ns and fast hold -0.325177 ns;
slew and one capacitance violation also remain. These are estimates with
retained failures, not native extracted or antenna acceptance results.

The [clean remote d93e64d replay](evidence/fresh-clone-d93e64d-20260920.json)
passes **818 tests / 26 skips**, with **16 passing front-door gates / zero
failures / seven skips**. Historical-artifact absence remains the open
part of F6.

The [ECO25 driver experiment](evidence/ethernet-eco25-drivers-20260920.json)
retains every original state element and diode, with 38 verified equivalent
buffer substitutions and two positive offload buffers (645.9264 µm² added
standard-cell area). Global estimates retain zero fanout violations, but have
41/16/10 slew and three capacitance violations in fast/typical/slow corners.
Fast hold is −0.308853 ns and slow setup is −0.117318 ns; these are failures.
This is an intermediate old-RTL candidate, without a native reroute verdict.

The [jumper-only control](evidence/ethernet-eco23-jumper-20260920.json)
completes native routing and extraction but retains 245 violating antenna nets
and 270 pins, plus −0.002292 ns slow setup. The small magnitude is still a
failure. It does not replace ECO22's antenna-clean geometry.

The [local SRAM leaf experiment](evidence/ethernet-eco26-leaves-20260920.json)
reduces estimated fast/typical/slow slew violations to 8/4/2, with one remaining
capacitance violation and zero fanout violations. Its 44 buffers, 20 delay cells
and three equivalent sizing changes preserve original logic/state but add
1,473.2928 µm². Slow setup (−1.239417 ns) and fast hold (−0.346552 ns) still fail;
the additional GMII delay trades a fast hold improvement for a slow setup
regression. No extracted or independent geometry verdict is transferred to it.

The [fixed-route generated-clock control](evidence/generated-clock-corner-isolation-20260920.json)
reproduces a difference between mixed-corner and independent single-corner STA
on identical geometry and constraints, also in a seven-cell native-IHP example.
This is a diagnostic discrepancy, not a timing waiver or an established upstream
root cause. `probe_generated_clock_corners.py` reproduces the small control;
`report_route_corners.py` reports fixed global-route segments in separate processes.

The [ECO27 experiment](evidence/ethernet-eco27-separated-20260920.json) retains
original state/connectivity with 33 added positive cells and 21 equivalent buffer
substitutions. Its exact effective environment gives slow setup −0.114930 ns and
fast hold +0.001602 ns; two slew and one capacitance violation remain. An earlier
captured-environment report appeared positive but is superseded by this exact
replay. There is no extracted timing or geometry acceptance for ECO27.

The **new IRQ and immutable-ROM design** has completed native global routing.
Its [first fanout repair](evidence/logicrom-eco1-fanout-20260920.json) preserves all
97,608 existing instances and adds 2,611 positive buffers. Independent pin/state
comparison passes; all 712 measured fanout violations are removed. Slow setup
−0.771703 ns, slew and capacitance failures remain. This design still requires
its own detailed route, extraction and geometry checks.

The [native-cell simulator control](evidence/native-cell-simulator-gate-20260920.json)
passes in Icarus 13 and fails in the installed Verilator build. The boot runner
now rejects that incompatibility before compiling the whole SoC. The earlier
Verilator timeouts and terminated diagnostic runs provide no boot evidence;
full four-state boot remains pending. The PDK models were not altered.

The [clean remote 84a049d replay](evidence/fresh-clone-84a049d-20260920.json)
passes **831 tests / 26 skips** and **16 front-door gates / zero failures /
seven skips**. F6's absent historical artifacts remain absent.

New-design SRAM refinements are measured separately:
[ECO2](evidence/logicrom-eco2-electrical-20260920.json) adds 75 positive buffers
and [ECO3](evidence/logicrom-eco3-electrical-20260920.json) adds another 17;
exact original state/pin comparison passes in both. ECO3 reduces electrical
failures to two slew/two capacitance violations with zero fanout violations;
slow setup remains −0.727914 ns. [ECO4](evidence/logicrom-eco4-sizing-20260920.json)
tries 35 equivalent buffer-strength changes and four additional offloads. It
removes capacitance violations but worsens slow setup to −0.791484 ns and retains
six slow-corner slew violations. It is not accepted as a timing improvement.

The [clean remote ba9297a replay](evidence/fresh-clone-ba9297a-20260920.json)
passes **849 tests / 26 skips**, with **16 front-door gates / zero failures /
seven skips**; this verifies the new diagnostic and native-model guards.

The [single-slow-corner sizing experiment](evidence/logicrom-eco5-sizing-20260920.json)
reduces estimated slow setup to −0.477510 ns. Its final 92 combinational and 34
sequential master substitutions have identical Liberty functions/state and exact
pin connectivity; four positive buffers were added. Setup and slew still fail.

Correction, 2026-09-20: the first full native-Icarus mapped-ROM boot has completed
with [a retained failure](evidence/logicrom-whole-gl-failure-20260920.json):
113 UART characters, one framing error, zero application checks and zero exit
magic at the million-cycle bound. This is a separate open defect from the
Verilator model incompatibility. Earlier RTL and block ROM passes remain scoped
to those tests; they do not close whole mapped boot.

[ECO6](evidence/logicrom-eco6-buffering-20260920.json) reduces slow setup to
−0.152243 ns while preserving exact original state/functions/connectivity.
[ECO7](evidence/logicrom-eco7-electrical-20260920.json) reaches zero electrical
violations in all corners. The two remaining negative paths are TX SRAM outputs
to capture flip-flops. [ECO8](evidence/logicrom-eco8-global-20260920.json) adds one
positive delay cell on each capture-clock leaf. **Correction, 2026-09-20:
the originally reported all-corner PASS used integer-truncated zero derate
and is withdrawn.** The same fixed placement and routes at the intended 5%
derate fail fast hold (−0.113588 ns) and slow setup (−1.049344 ns);
[corrected replay and rejected integer control](evidence/logicrom-derate-correction-20260920.json). This is still estimated RC, with no native detailed
route/extraction verdict, and belongs to the previous loader image.

The [startup counter diagnostic](evidence/logicrom-startup-counter-diagnostic-20260920.json)
finds unknown RAM SEC/DED counters at cycle 100 of the native mapped simulation,
while the CPU is still correctly clearing RAM. The old loader reads those
power-on values before clearing them. The proposed loader correction writes the
RAM-source clear unconditionally on power-on, without reading startup telemetry;
warm-boot and ROM records remain preserved. Corrected RTL and whole mapped boot
runs are pending. A changed fixed loader needs its own synthesis and physical run.

To retain disk headroom, obsolete global-estimate ODB/DEF files were moved into
[lossless local archives](evidence/local-geometry-archive-20260920.json). Every
archived byte was SHA256-verified before unlinking its raw counterpart. The
manifest gives original paths and restoration commands; netlists, reports,
constraints, native routed/signoff trees and current candidates remain in place.
This storage change does not change any pass/fail verdict.

**Verification update, 2026-09-20:** the corrected loader now passes normal RTL
boot and [both geometry fallback replays](evidence/logicrom-startup-clear-fallback-20260920.json),
28 application checks each, zero framing/protocol violations and the same
immutable image manifest. The fallback runs reject primary-image geometry with
cause 4 and boot image 1. These supersede the pending RTL statements above;
full native mapped boot and new-image physical implementation remain pending.

**Measured update, 2026-09-20:** the [routing-halo Magic replay](evidence/ihp-routing-halo-magic-20260920.json)
completes with **438 retained errors**, independently recounted from its XML:
436 inside the exact LEF footprints and two outside, versus the baseline's
436 inside / 206 outside. The two remaining external Metal2 wide-spacing
markers occur on RAM `A_DLY` and `A_ADDR[6]` pin routes. The 0.6 µm pin-aware
keep-out removes 204 external markers but does not close the experiment's
zero-external-marker criterion or any macro-interior requirement. The unchanged
installed deck reads this old 24-macro candidate through DEF/LEF abstracts;
raw process exit zero is execution success, not a clean DRC result.

**Native boot acceptance, 2026-09-20:** the corrected loader now passes the
[complete four-state mapped-SoC run](evidence/logicrom-startup-clear-native-pass-20260920.json):
637,224 cycles, all 28 application checks, exit code zero, exit magic
`600dc0de`, watchdog stages 1/0/0, zero flash protocol violations and zero
UART framing errors. Native IHP cell and SRAM models remain unchanged, with
no ROM/RAM preload and matching loader manifests. Input hashes stayed
unchanged for the full 3,169.87-second simulation. This supersedes the pending
local native-boot statements and closes the diagnosed power-on telemetry
read defect; the original failure remains the negative baseline. It does
not establish SDF timing, radiation qualification or final-image physical
acceptance. The independent hosted rebuild remains a separate run.

**Dated update, 2026-09-20: F6 original artifacts recovered.** The previous
absence statements above are superseded for the signoff-6x2 DEF/netlist,
s70-rom0 netlist and g0gates2 raw reports. A separate old local checkout
retained the exact original files: all three large-file hashes match the
pre-existing digest ledger, and recovered metrics/configs match the existing
records. The [2.7 MB selected snapshot](evidence/historical-recovery-20260920.json)
includes original JSON-header provenance and actual directory inventories.
It is restored only into test scratch space; frozen trees are untouched.
All 31 affected historical checks now pass, including real placement and
netlist mutation measurements. Five additional prepared-source checks pass
using [byte-replayed pinned dependencies](evidence/prepared-sources-20260920.json).
Archive corruption, traversal, missing/extra/duplicate files, links and live
file drift are rejected. [Control evidence](evidence/historical-recovery-controls-20260920.json).
F6's full fresh-clone acceptance is pending the next remote replay.

The halo's [two-net repair](evidence/ihp-two-net-route-20260920.json) passes
whole-block native route DRC (zero markers), antenna (zero nets/pins),
unchanged-cell/pin comparison and geometric continuity of both changed nets.
A removed-wire negative control fails as expected. The earlier six-violation
route is rejected. Own GDS has been generated; independent Magic is running
with unchanged native rules. Neither this result nor the old 438-marker
result is a verdict on the corrected-loader physical candidate.

**Dated update, 2026-09-20: F6 acceptance measured in a fresh remote clone.**
Head `0727236` completes the full local CI entry point with 902 pytest passes,
zero failures and one skip for the absent pinned TinyTapeout support tool.
The paper checker has seven claims needing build output and zero wrong.
The [clone evidence](evidence/fresh-clone-0727236-20260920.json) retains the
exact ledger row, hashes and skip reason. Front-door gates separately report
16 passes and seven skips (pandoc and six live-run checker bindings).
This closes the stated F6 acceptance, not current-image physical signoff.

**Timing correction:** ECO1–8 logic-ROM estimates inherited integer `5`
from a serialized native configuration; the native SDC divides by integer
100, silently applying zero derate. Their unchanged-5%-derate claim is
withdrawn. The corrected replay above leaves old measurements intact and
adds the actual failing 5% result. A new Tcl guard rejects truncating,
missing and invalid values before reading the ODB/SDC. The corrected loader
is being implemented with the original native Tcl environment (`5.0`).

The third halo two-net repair's own GDS now passes the
[independent upstream KLayout main deck](evidence/halo-lift3-drc-20260920.json):
zero markers, unchanged input/deck hashes, no optional recommended rules.
Its separate native Magic check is still running. This result belongs to the
older 24-SRAM halo image; it is not a DRC verdict on the corrected-loader and
external-interrupt physical implementation.

That corrected-loader/interrupt implementation has now completed its native
post-global-route timing repair with the original `5.0` derating environment.
[Independent fixed-route corner reports](evidence/startup-native-corners-20260920.json)
still fail: slow setup is **−2.866964 ns**, fast hold is **−0.089041 ns**,
and each corner has **703 fanout violations**; worst slew/capacitance counts
are 54/7. These are global-route estimates. The first report attempt rejected
an OpenSTA fanout row with an omitted slack column; the corrected parser counts
it as a violation, and 36 parser/derating checks pass. No timing or electrical
limit was relaxed to accept the reports.

**Paper measurement follow-up, 2026-09-20:** all six replica-placement
claims now execute the unchanged instrument against the exact recovered
DEF/netlist. The command prints its historical scope. The paper checker
now reports **26 re-derived, 15 manual, one needing build output, zero wrong**;
[command and controls](evidence/recorded-paper-replicas-20260920.json).
The remaining absent output is the historical LVS log; no LVS is inferred.

The final missing paper output was also recovered: the 67,302-byte
[s77lvs-b-blackbox stdout](evidence/s77lvs-b-blackbox/recovery.json) exactly
matches its pre-existing digest (`53505c83…`). The checker now reports
**27 re-derived, 15 manual, zero needing build output, zero wrong**.
Changed recorded bytes or a disagreeing live log fail. The historical
62,256-device / 61,912-net match still abstracts SRAM interiors and predates
the current RTL; no new LVS run or transistor-level verdict is inferred.

The shared [native derate guard](evidence/native-derate-guard-20260920.json)
also runs before ODB/SDC load in both bounded native resizer steps. Actual
installed LibreLane templates generate successfully; four Tcl controls prove
that integer `5` stops before loading and `5.0` retains factors 0.95/1.05.
The already-running native script is unchanged and already uses `5.0`.

A [fresh remote replay at e5575b4](evidence/fresh-clone-e5575b4-20260920.json)
measures **926 pytest passes, one absent-tool skip, zero failures**;
27 paper results are re-derived, 15 remain manual, zero lack build output.
This precedes the wrapper guard addition, which has 36 affected checks.

### Hosted NPU-stage failure and reboot recovery (20 September evening)

The independent [hosted run 35508536540](evidence/native-boot-hosted-npu-failure-20260920.json)
passed native-cell reset, RTL boot and gate compilation, then failed the full
mapped boot: 24 application checks completed before unknown values appeared
during the NPU phase. It reached the million-cycle bound without the success
magic. The ROM and flash bytes match the distinct local passing build;
Yosys and Icarus versions differ. Root cause remains under investigation using
the exact hosted netlist and flash under local Icarus 13. The earlier local
28-check pass is retained with its original scope; hosted acceptance is open.

The host reboot interrupted the pending local physical runs. Their partial
outputs are retained and input hashes rechecked before restarting in new
`restart1` directories. Neither old RUNNING metadata nor missing final state
files is a pass. See [recovery record](evidence/reboot-recovery-20260920-evening.json)
The ongoing product requirements remain in the acceptance table above.

A [fresh remote clone at 7d2484c](evidence/fresh-clone-7d2484c-20260920.json)
completed with **930 pytest passes, one absent-tool skip, zero failures**;
front-door gates remain 16 pass / 0 fail / 7 explicit skips. Paper checks
re-derived 27 results with 15 manual, zero missing output and zero wrong.


**2026-09-21 measured NPU boot correction:** the exact previously failed
hosted netlist now completes a local native-model replay in 653,726 cycles,
28/28 application checks, zero failure mask. The firmware initializes all
neuron payload/check feedback through verified serial register operations.
[Input identities, complete result and binary-equality proof](evidence/npu-native-startup-20260921.json)
retain the original hosted failure separately. An independent hosted rebuild,
physical closure and the other product gates above remain open.


[Three subsequent physical ECO experiments](evidence/startup-physical-eco123-20260921.json)
retain the 5% derating and original logical connectivity. Fanout violations
fall from 703 to zero. ECO3 has zero capacitance/fanout violations across all
three corners, zero slew violations at typical/slow and one at fast, but slow
setup is **-2.750971 ns** and fast hold **-0.363958 ns**. Sizing improves electrical
counts while worsening the earlier setup result, so none is accepted as final
closure. These are global-route RC estimates, not extracted signoff.
