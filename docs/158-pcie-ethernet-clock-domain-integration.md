# 158 — PCIe/Ethernet concurrent chip RTL and clock-domain integration
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Completed boundary — 8 October 2026

The actual `soc_top` now has an optional **250 MHz PCIe packet-controller to
50 MHz CPU/APB crossing**, while the Ethernet MAC runs at 125 MHz. Concurrent
CPU Ethernet and PCIe accesses pass, including the configuration with **16
native IHP FIFO SRAM instances and their destructive power-on MBIST**.
This closes a digital integration gap. **The complete serial Gen3 x4 PHY,
controller/PHY connection and corresponding full-chip layout remain open.**
There are no new main-chip GDS, extracted timing, DRC/LVS or production claims.

The [source changes](../hw/soc/rtl/soc_top.v) require both `SOC_PCIE_PACKET`
and `SOC_PCIE_ASYNC` for the new mode. The existing same-clock packet profile
and the default build retain their original clock selection. BAR0 continues
to expose only GPIO; this change does not make Ethernet or CPU memory accessible
through PCIe. GMII still needs an external Ethernet PHY.

## Actual concurrent CPU traffic

The [runner](../scripts/check_pcie_ethernet_soc.py) builds a real Ibex ROM that
sends Ethernet frames, polls and reads back every received byte, checks the
last-byte indication and MAC error flags, then toggles a GPIO success bit.
The testbench drives only fixture inputs. Read-only witnesses observe actual
CPU and PCIe APB handshakes; no CPU register, memory or internal bus is forced.

TX and RX GMII use independent 125 MHz phases. Captured TX frames are checked
for all 60 payload bytes, preamble/SFD and independently calculated CRC32,
then delivered at wire speed on RX after an interframe gap. Concurrent PCIe
traffic accesses GPIO, receives checked completions and exercises backpressure.
The 50 MHz APB PIO path is not claimed to sustain continuous gigabit traffic.

| Local campaign | Result |
| --- | --- |
| Existing CPU/GPIO PCIe regression | 2 scenarios passed |
| Concurrent Ethernet and same-clock PCIe | 2 scenarios passed |
| Concurrent Ethernet and 250 MHz PCIe | 2 scenarios passed |
| 250 MHz PCIe plus native Ethernet SRAM/MBIST | 2 scenarios passed, 0 skipped |

In the SRAM configuration, both scenarios perform at least three successful
CPU Ethernet round trips and 180 checked RX bytes. They observe **81 and 43
PCIe APB accesses**, **18 and 21 Ethernet/PCIe contention cycles**, and a real
PCIe access before MBIST finishes. The elaborated simulation contains exactly
16 `RM_IHPSG13_2P_256x16_c2_bm_bist` instances, using the unmodified c4 vendor
functional models. System RAM is still the RTL array profile in this campaign;
this is not a claim of a newly mapped 32-SRAM whole-chip netlist.

PCIe link loss during reception and after an actual CDC request capture
does not reset Ethernet. A pending, unaccepted GPIO write is cancelled;
reinitializing the link allows a fresh write. A write already accepted by APB
cannot be undone. Actual corrupt-GMII and missing-CDC-link-reset mutations both
fail the integration tests. The existing wrong-BAR/partial-write controls also
remain effective.

The first MBIST test bound was too short: six backgrounds over 2,048 words
require 184,320 March clocks per port, plus 4,096 cross-read clocks per port.
Sequential 50/125 MHz phases take approximately 5.275648 ms before the small
synchronizer/start overhead. The corrected bound is 5.6 ms. Both original
failures are retained. Another initial observer sampled APB SETUP before the
mailbox captured anything; its missing-reset mutation survived. The observer
now witnesses the actual captured request, and that mutation is rejected.
The incomplete SRAM run using the earlier observer was deliberately stopped
and preserved before the successful complete rerun.

## Four-phase APB mailbox and native-cell checks

The [bridge](../hw/soc/rtl/pcie/soc_pcie_apb_cdc.v) holds request and response
payloads until their respective two-flop control synchronizers complete a
four-phase handshake. Each destination transaction receives a new SETUP phase.
An old ACCESS held after completion cannot execute twice. System or PCIe link
reset asserts in both halves; each clock domain synchronizes release. The
source must keep its APB request stable until completion or coordinated reset.

RTL tests pass at source/destination half-periods **2/10, 11/3 and 5/7 ns**.
Each performs 97 completed transfers, slave waits, parked ACCESS, reset while
a destination clock is stopped, cancellation in ACCESS, and recovery. Four
actual HDL mutations are rejected. Native mapping produces **416 IHP cells**,
including a real tie-high cell. The same three port campaigns pass on that
netlist and again on the preplacement-repaired netlist.

The [development constraints](../scripts/pcie_apb_cdc_constraints.py) bind
49 request bits and 33 response bits to actual mapped registers, verify their
clock domains and the two-stage synchronizer chains, and reject five mutated
mapped graphs. Only the first synchronizer inputs receive asynchronous control
exceptions. Bundled-data paths retain explicit 16 ns and 3.2 ns maximum delays,
including launch clock-to-Q; unrelated-clock hold checks on those held payloads
are excluded. There is no blanket asynchronous clock-group cut. These are
standalone development constraints, not a delivered full-chip CDC signoff.

The ordinary SoC lint run also passes with the same 987 recorded warnings.
Adding the conditional clock port moved diagnostic locations; the ledger update
maps only exact unchanged source lines across all profiles. Warning classes,
messages, columns and multiplicities are unchanged. This is not warning-free
RTL or metastability signoff. A separate real lint of the packet-enabled
asynchronous profile reports 1,079 warnings and **118 unaccepted substantive
rows** under the ordinary owned-RTL policy. Replaying the pre-change packet
profile finds the same 118 rows (missing optional status-output connections,
width conversions in existing packet modules, and their local-reset diagnostic).
The new bridge introduces none of these rows; they are retained as an open
packet-profile lint gate, not silently added to the accepted warning ledger.

## Physical preparation and retained rejection

The first OpenROAD export lost the logical constant-one driver. Its favorable
STA report was insufficient: the exported netlist failed actual simulation.
Mapping the constant to `sg13g2_tiehi` fixes the import. No failure is waived.
An earlier pin-binding attempt also failed on renamed instances; preserving
names fixes that issue. Invalid Q-pin startpoint constraints were rejected and
replaced by verified launch-clock pins before the reported screen.

Native repair adds **56 buffers** and changes **85 drive strengths**. An
independent saved-graph replay compares **all 21 ports and 1,602 non-buffer pin
bits**. It permits only bijective Verilog name escaping, transparent native
buffers and sized cells with identical native functional-model bodies. All
seven deliberate graph corruptions are rejected. The resulting netlist has
472 cells and passes the three actual native port campaigns.

| Corner | Preplacement setup slack (ns) | Hold slack (ns) |
| --- | ---: | ---: |
| Slow | +2.482765 | +0.288476 |
| Typical | +2.819511 | +0.183575 |
| Fast | +2.954221 | +0.123165 |

These numbers apply only to the small APB bridge with the original 4/20 ns
constraints, ideal clocks and wire-load estimates. OpenROAD explicitly reports
that no parasitics have been estimated; its floorplan snapping warning is also
retained. There is no placement, route or qualified RC claim. The separate
[V30 receive path](157-pcie-balanced-fault-and-native-recovery.md) still fails
slow setup at −2.617440 ns; the new bridge's margin does not replace that result.

The retained raw runs, final-campaign source snapshots, compiled simulations,
native netlists, failed attempts and method scripts are bound by the
[delivery record](../hw/soc/pcie-evidence/20261008-joint-chip-integration/delivery.json).
The new workflow runs same-clock and asynchronous joint integration controls
and the native APB bridge checks. The prior native-V1 recovery is independently
confirmed by successful GitHub run
[37779143339](https://github.com/Melihakbulut221/nssoc/actions/runs/37779143339),
including its twelve native scenarios; this is distinct from new-head CI.

Full PLL/CDR acquisition and safe tuning, full SERDES/PCS/LTSSM, rated controller
receive integration, differential pads/ESD, qualified extraction and a newly
verified serial-PHY main-chip layout remain required. None is marked complete
by this digital integration campaign.

## Whole-chip mapped continuation

The [whole-chip synthesis flow](../hw/soc/flow/syn_soc_top.sh) now explicitly
selects `SOC_PCIE_PROFILE=packet-async` (or `packet` for the existing CPU-clock
mode). The default remains `off`. Previously that flow did not read the PCIe
controller sources or enable the packet ports. Invalid selections fail before
the output directory is touched. The selected profile exports the actual mapped
JSON and tie cells, preserving identifiers for physical constraint binding.

The first complete asynchronous run includes the actual Ibex, NPU, Ethernet,
packet controller, APB mailbox and power-on MBIST: **77,787 cells, 101 ports,
four native 2048×64 system SRAMs and sixteen native two-port Ethernet SRAMs**.
It uses the same Ethernet exercise firmware in an immutable logic ROM. The
4 ns ABC mapping target is explicitly 4,000 ps. CPU constraints remain 20 ns;
the packet clock is 4 ns and both GMII clocks are 8 ns. Core pipeline and
SYNPRE options are at their default zero settings. This is the base interface
profile, not the full CAN/SpaceWire profile or the earlier alternate 32-SRAM
physical implementation. It has not had a whole-netlist native boot replay.

The [mapped clock binder](../scripts/pcie_soc_constraints.py) identifies the
actual 49-bit request, 33-bit response and both two-stage control synchronizers
in this flattened chip, checking every selected register's clock. Packet IO
gets its own clock; Ethernet retains the existing development GMII budgets.
The 16/3.2 ns mailbox data budgets and narrow control exceptions remain intact.
Legacy single-clock `sta_soc_top.sh` now rejects packet netlists. The constraint
projection tests reject five actual mapped pin/clock corruptions; together with
the flow guards and existing source-list checks, **11 tests pass**.

Native OpenROAD preplacement repair inserts **10,400 buffers** and changes
**2,133 drive strengths**. Saved-graph replay checks all **101 ports and 278,235
non-buffer pin bits**, retaining all SRAM connections. Seven deliberate graph
corruptions fail. The import initially lacked the SRAM declarations, then the
comparison rejected OpenROAD's doubled internal backslash spelling. Both
failures are retained; only a bijective exact serialization of each original
identifier is accepted in the successful replay.

| Corner | Repaired, unplaced worst reported setup (ns) | Hold (ns) |
| --- | ---: | ---: |
| Slow | −5.646589 | −0.493968 |
| Typical | −2.206412 | −0.539480 |
| Fast | −0.194620 | −0.601382 |

**Timing remains failed.** The measured packet critical path is
`retry.head[1]` to `credit_data_limit_o[0]`. Ethernet SRAM read paths and SRAM/
GMII hold paths also remain open. The earlier unbuffered OpenSTA screen and its
large reset-fanout failures are retained, but the different tool builds are not
used to claim a numerical before/after improvement. Its initial slack collector
missed the `max/min` token; explicit saved-log replay recovers both values for
all three corners without changing a native run. The explicit external-IRQ
exception leaves its first-stage D listed as one unconstrained endpoint.

These are ideal-clock wire-load estimates with vendor SRAM views. No placed
macros, CTS, routed RC, new GDS, DRC/LVS acceptance or Gen3 x4 serial integration
is implied. The result is a mapped integration prerequisite, not a completed
physical chip. Exact summaries and raw delivery are in the
[main-chip evidence](../hw/soc/pcie-evidence/20261008-mainchip-packet-mapping/review.json)
and [archive record](../hw/soc/pcie-evidence/20261008-mainchip-packet-mapping/delivery.json).

## Credit-path repair after the joint mapping

The measured replay-to-credit path led to a same-cycle arithmetic change in
[transmit credits](../hw/soc/rtl/pcie/soc_pcie_credit_tx.v). Debit and no-debit
remaining-credit values are computed in parallel. The late reservation verdict
selects the result instead of entering two serial carry chains. Modulo widths,
state, clocks and protocol latency are unchanged.

The [reference proof](../scripts/check_pcie_credit_equivalence.py) compares with
the frozen source from `f533e9c`: **362 equivalence points pass**. Explicit
`clk2fflogic` clock/reset-event modeling is used; the initial direct async-FF
SAT attempt failed and is retained. Three real arithmetic mutations are rejected.
Four RTL credit cases, four actual IHP-cell credit cases and both asynchronous
CPU/Ethernet/PCIe scenarios pass. Eleven formal/mutation host controls pass.
The credit block maps to 988 native cells; the full chip maps to 77,697 cells.

The same OpenROAD binary, libraries, LEFs, repair command and role-normalized
4/20/8 ns constraints are independently checked against the prior screen.
The repaired graph again passes all ports and **278,091 pin bits**, with seven
actual corruptions rejected. Slow global setup improves **261.408 ps**;
typical improves 175.912 ps and fast improves 130.519 ps. No clock is relaxed.

| Corner | New global setup (ns) | New global hold (ns) |
| --- | ---: | ---: |
| Slow | −5.385181 | −0.469310 |
| Typical | −2.030500 | −0.539480 |
| Fast | −0.064101 | −0.601382 |

**This is not physical acceptance.** The slow Ethernet TX group regresses from
−1.238929 to −1.866908 ns in the resynthesized/repaired candidate, although
global setup improves. The new packet critical path is
`receive_ownership.qread[2]` to `quarantine.index[4]`. These paths, hold repair,
qualified SRAM/RC and the actual serial PHY remain open. The functionally
equivalent RTL factoring is retained; the failed physical candidate is not
adopted as a chip layout. The default non-packet layout profile is unaffected.
The [complete comparison](../hw/soc/pcie-evidence/20261008-parallel-credit-repair/review.json)
and [raw archive](../hw/soc/pcie-evidence/20261008-parallel-credit-repair/delivery.json)
retain both gains and regressions.

## 2026-10-08 receive banks, MBIST and local reset repair

The next measured receive path was queue-head selection through the flat
packet array and the CRC quarantine. The receiver now reads constant-base
banks in parallel before selecting the head byte. This preserves cross-bank
index behavior, packet ownership, reset and every external cycle. The frozen
reference proves **2,679 equivalence points** with explicit clock events and
undefined memory modeling. The initial proof without undefined modeling left
eight data bits unproved; that failed run is retained. No valid-only output
mask or input assumption was added to the successful proof.

The Ethernet critical path was SRAM readback into the MBIST background
counter. Its internal width now covers exactly `0..PARTITIONS+1`; the public
failure diagnostic remains eight bits. Explicit zero extension removes the
three width warnings found during review. The existing 36 MBIST transaction,
fault and abort tests pass. Formal comparisons also pass for the actual
16-bit/2048-word FIFO and 64-bit/8192-word system controllers, plus one-bit
and non-power-of-two/multi-cycle-read boundary configurations. This shared
MBIST source also affects non-packet profiles when MBIST is enabled; old GDS
and signoff results have not been regenerated for it.

The bank/MBIST candidate passes five RTL receive cases, five actual IHP-cell
receive cases and five complete packet-composition cases. The simultaneous
CPU/Ethernet/PCIe campaign with all 16 vendor FIFO SRAM models passes both
normal traffic and link-loss cases: **10.863244 ms simulated**, 604.29 seconds
wall time, no skipped case. Twenty-one host controls include two actual
bank-read corruptions rejected by the port scoreboards. The 77,097-cell
whole-chip map retains 101 ports and 20 vendor SRAMs. Its repaired graph
preserves all 276,116 non-buffer pin bits and rejects seven graph faults.

The subsequent candidate computes each transmit-credit class difference
before selecting it, rather than selecting two operands before subtraction.
All 362 frozen credit equivalence points and four native credit cases pass.
The APB destination outputs now use the local asynchronously cleared reset
release flop. Raw PCIe link reset still asserts both mailbox resets, but no
longer directly drives combinational CPU peripheral selection. All 217 CDC
equivalence points pass; the 416-cell native bridge passes 97 transfers at
each of three clock ratios, including reset during an ACCESS with the
destination clock stopped. The updated joint asynchronous CPU/Ethernet/PCIe
tests pass both cases; these last two cases use RTL FIFOs, not a second vendor
SRAM MBIST campaign. Four MBIST parameter proofs cover the explicit casts.

Both whole-chip screens use the same native libraries, LEFs, repair command,
4/20/8 ns clocks, derates and IO budgets. Pin identities are rebound to the
actual mapped registers; role-normalized constraints are equal. Final
explicit-cast mapping has 77,697 cells, 101 ports and 20 SRAMs. Its timing
matches the preserved pre-cast experiment exactly:

| Unplaced result | Previous credit repair | Bank/MBIST | Class credit/local reset |
| --- | ---: | ---: | ---: |
| Slow worst setup, ns | -5.385181 | -4.076292 | -3.431339 |
| Typical worst setup, ns | -2.030500 | -1.221225 | -0.975340 |
| Fast worst setup, ns | -0.064101 | +0.434292 | +0.356756 |
| Slow CPU setup, ns | -3.069961 | -2.637548 | +0.247116 |
| Slow Ethernet RX setup, ns | -1.050938 | -0.383086 | -0.704213 |
| Slow Ethernet TX setup, ns | -1.866908 | -0.621666 | -0.987873 |
| Slow worst hold, ns | -0.469310 | -0.488175 | -0.469247 |
| Typical worst hold, ns | -0.539480 | -0.539480 | -0.539480 |
| Fast worst hold, ns | -0.601382 | -0.601382 | -0.601382 |

The CPU setup improvement does **not** establish full-chip closure. Ethernet
and fast setup regress against the intermediate bank/MBIST candidate even
though they improve against the starting point. Hold remains negative.
The current packet critical path is transmit-packet index to replay
`next_store_sequence[11]`. Native SRAM timing/RC qualification, CTS/routing,
full-chip boot/DRC/LVS and the actual full serial Gen3 x4 PHY are still open.
The base SRAM/MBIST/Ethernet lint profile passes its unchanged 1,065-warning
ledger; this does not close the earlier packet-profile lint debt.

See the [bank/MBIST review](../hw/soc/pcie-evidence/20261008-rx-bank-mbist-repair/review.json)
and its [complete raw archive](../hw/soc/pcie-evidence/20261008-rx-bank-mbist-repair/delivery.json),
plus the [class/reset review](../hw/soc/pcie-evidence/20261008-class-cdc-chip-repair/review.json)
and [raw archive](../hw/soc/pcie-evidence/20261008-class-cdc-chip-repair/delivery.json).

### Replay control path experiments, 8 October 2026

The replay sequence increment is now computed ahead of the CRC verdict.
The cache refreshes every clock; an accepted packet ends capture, so the
next packet cannot commit before the updated sequence cache is available.
A separate explicit transmit frontier advances only when an original packet
finishes transmission. ACK processing moves the queue head forward and the
outstanding count backward equally, leaving this frontier unchanged. Replay
transmissions do not advance it. Neither change adds port latency.

Against the frozen pre-change RTL, both experiments prove 1,566 equivalence
points at the default parameters and 855 with a three-slot queue, smaller
packet capacity and short timeout. Seven RTL and seven native-cell cases
pass for each, including 4,097 real packets across sequence-number wrap.
Actual wrong-cache-increment, truncated carry and skipped-slot mutations are
rejected. Each candidate also passes two joint CPU/Ethernet/asynchronous
PCIe tests and five packet-composition cases. These joint cases use RTL
FIFO models; the earlier vendor-SRAM MBIST campaign is separate evidence.

| Same unplaced method, ns | Class/reset baseline | Sequence cache | Explicit frontier | Carry/CRC trial |
| --- | ---: | ---: | ---: | ---: |
| Slow setup | -3.431339 | -3.132355 | -2.435288 | -3.815347 |
| Typical setup | -0.975340 | -0.602120 | -0.179899 | -1.023483 |
| Fast setup | +0.356756 | +0.784566 | +0.850311 | +0.598505 |
| Slow hold | -0.469247 | -0.465004 | -0.530313 | -0.469247 |
| Typical hold | -0.539480 | -0.539480 | -0.539480 | -0.539480 |
| Fast hold | -0.601382 | -0.601382 | -0.601382 | -0.601382 |

The explicit-frontier map has 78,637 cells, 101 ports and 20 SRAM macros.
All 280,991 repaired non-buffer pin bits compare equal; seven injected graph
faults reject. The same native models, clock budgets and role-normalized CDC
constraints are checked for every timing comparison. Slow CPU setup is
+1.574598 ns; Ethernet RX/TX setup remains -0.375802/-0.474566 ns. Slow hold
regresses despite the setup gain. This is development progress, not timing
closure or acceptance of a routed chip.

A subsequent carry-save credit calculation combined with removal of a
redundant CRC-quarantine index clear passes functional, native and graph
checks but **regresses** setup. Its credit change is reverted; the complete
failed experiment is retained. CRC-only attribution is measured separately below.
The original fast hold path remains Ethernet transmit-enable clock-to-output
against the unchanged external hold budget. It still needs physical repair.

The [trial review](../hw/soc/pcie-evidence/20261008-replay-timing-trials/review.json)
and [complete raw archive](../hw/soc/pcie-evidence/20261008-replay-timing-trials/delivery.json)
retain the successful and rejected sources, logs, native maps and proofs.
There is still no full serial Gen3 x4 PHY instance, current routed-mainchip
verification or final setup/hold acceptance.


The CRC-only screen reaches slow/typical/fast setup
-2.430666/-0.438231/+0.734238 ns: its 4.622 ps slow gain does not offset the
258.332 ps typical regression. It is reverted. A separate class-cache
candidate decodes the packet class on the exact write of header byte two,
including partial/corrupt writes and invalid-cycle sidebands. Its 1,558/847
formal points, seven native cases, two joint cases and five composition
cases pass, with no additional lint warning after the first prototype is
corrected. Nevertheless its setup is -2.595271/-0.446848/+0.641717 ns, worse
than the explicit frontier at all three corners. It too is reverted.
The complete [isolation review](../hw/soc/pcie-evidence/20261008-replay-isolation-trials/review.json)
and [raw trial archive](../hw/soc/pcie-evidence/20261008-replay-isolation-trials/delivery.json)
retain both results and the discarded sources. Shipping replay RTL keeps
only sequence lookahead and the explicit frontier; credit and quarantine
RTL remain at the earlier class/reset baseline. The final selected-source
replay/formal controls pass 16 cases, with seven unrelated parameter cases
deselected from this focused rerun.

### Packet-chip physical bringup, 9 October 2026

The selected replay-frontier map has now entered the real LibreLane/OpenROAD
physical flow. A guarded preparation helper binds all four mapped clocks and
reuses the existing die, bank coordinates, SRAM masters and timing budgets.
The sixteen MBIST FIFO bank names differ from the older inferred-memory
floorplan. Placement uses their Verilog names; native PDN regular expressions
must also match OpenROAD's escaped bracket representation. The first two
failed name-binding attempts are retained, followed by the corrected run.

Actual database checks confirm all 20 macro masters, locations, orientations
and fixed placement status. All 60 SRAM supply-pin bindings are correct, and
both VPWR and VGND pass native power-grid connectivity checks. PDN via
warnings remain in the raw logs; connectivity does not establish IR drop,
electrical reliability or full-chip LVS/DRC. Four mutations of the actual map
and netlist reject a clock alias, missing bank, wrong master and mismatched
Verilog macro. No broad bank-name wildcard is used to bypass binding.

The synthesis SDC always used ideal clocks. The physical SDC preserves every
timing command and selects clock propagation by stage. A native tool probe
checks all four input clocks plus the generated Ethernet clock in both modes.
LibreLane's first mid-PnR STA did not supply its ideal-clock flag, despite
running before CTS; that report was interrupted and preserved. The packet
flow now explicitly sets the flag only for that pre-CTS STA. The other 79
flow steps, full timing report coverage and checker thresholds are unchanged.
Completed placement is reused for the corrected STA and CTS continuation.

The [physical bringup review](../hw/soc/pcie-evidence/20261009-packet-physical-bringup/review.json)
and [complete completed-stage archive](../hw/soc/pcie-evidence/20261009-packet-physical-bringup/delivery.json)
cover the native macro/PDN checks, initial placement, exact source/config
chain and preserved failures. The corrected CTS continuation is separate
work, excluded from that frozen archive. Post-CTS timing repair,
routing, extracted timing and full-chip physical acceptance remain open.
This is the byte-packet PCIe integration profile; it does not contain the full
8 GT/s x4 serial PHY or qualify the SRAM timing/RC views or package padframe.

The corrected continuation subsequently completed its pre-CTS STA,
post-placement electrical repair, detailed placement and CTS. The native CTS
log includes 4,845 PCIe clock sinks; the saved SDC marks all five clocks as
propagated. One unloaded net (`net86`) is skipped with a retained CTS warning.
These are stage-completion facts, not fresh post-CTS timing results: timing
metrics inherited in a state file must not be mistaken for a new analysis.
The separate [CTS checkpoint](../hw/soc/pcie-evidence/20261009-packet-physical-bringup/cts-review.json)
and [raw CTS archive](../hw/soc/pcie-evidence/20261009-packet-physical-bringup/cts-delivery.json)
preserve the actual ODB, DEF, netlists and SDC. The next local continuation
starts at post-CTS STA and includes timing repair and detailed routing.


### Packet reset data-path isolation, 9 October 2026

Fresh post-CTS reports expose a CPU-reset-to-packet-data path. The packet
reset already has an asynchronously cleared, two-stage local release;
ANDing its output with raw CPU reset reintroduces that asynchronous signal
into packet combinational logic. Using the existing local release removes
this bypass. The APB bridge's source response now also uses its local release,
matching the destination-side isolation. Reset pins retain asynchronous
assertion, including when the packet clock is stopped. No clock budget,
false path, pipeline latency or port is added.

A conservative traversal of the actual native whole-chip maps counts
**4,414** packet flip-flop data/output endpoints reachable from raw CPU reset
in the replay baseline, **104** with the top-level change alone, and **zero**
with both changes. Traversal stops at flip-flops and SRAMs; it does not
silently traverse sequential elements as combinational cells. The checker
also verifies the actual release-flop clock/reset bindings. Four mutations
of the real mapped graph reject an output bypass, data bypass, wrong release
clock and disconnected asynchronous reset. This is structural evidence,
not proof of analog reset recovery or metastability safety.

The exact extracted reset cone, observing both release bits and its output,
passes temporal induction **after an explicit initial power-on reset**.
Subsequent reset and clock transitions, including stopped-clock intervals,
are unconstrained. Four RTL faults produce counterexamples. Unconstrained
startup previously failed because independent uninitialized states differ;
that result is retained rather than reported as a passing startup proof.
The bridge proves all 217 sequential equivalence points against its frozen
reference. Two actual IHP reset flip-flops pass 897 state/output comparisons;
the 416-cell native bridge passes 97 transfers at each of three clock ratios.
Twelve focused host tests and two joint CPU/Ethernet/asynchronous-PCIe cases
pass. The native simulator's unsupported timing/`ifnone` warnings remain;
these are functional tests, without SDF or analog qualification.

| Same unplaced method, ns | Replay baseline | Top reset only | Both local releases |
| --- | ---: | ---: | ---: |
| Slow setup | -2.435288 | -2.764045 | -2.564759 |
| Typical setup | -0.179899 | -0.392776 | -0.267680 |
| Fast setup | +0.850311 | +0.707402 | +0.703496 |
| Slow hold | -0.530313 | -0.465004 | -0.465004 |
| Typical hold | -0.539480 | -0.539480 | -0.539480 |
| Fast hold | -0.601382 | -0.601382 | -0.601382 |

Both source edits are retained to remove the raw-reset data-domain bypass;
**unplaced setup regresses and timing remains open**. The combined map has
78,843 cells, 101 ports and 20 SRAMs. All 281,479 non-buffer pin bits compare
across native preplacement repair, and seven graph faults reject. A separate
physical candidate measures placement/CTS/routing effects using the original
mapped netlist. Its initial launch inadvertently repeated synthesis; that
attempt was stopped and retained, and the original-netlist JSON-header
checkpoint is reused. Neither that extra synthesis nor an unfinished physical
stage is accepted as evidence of timing closure.

The [reset repair review](../hw/soc/pcie-evidence/20261009-packet-reset-repair/review.json)
and [complete reset-study archive](../hw/soc/pcie-evidence/20261009-packet-reset-repair/delivery.json)
include both candidates, mapped outputs, raw proofs/simulations and preserved
failed startup/wrapper attempts. The active physical run is explicitly
excluded. The earlier replay physical run continues separately with its
frozen source. Full serial Gen3 x4 PHY, final routed timing, qualified SRAM/RC
and main-chip physical acceptance remain open.

### Complete pre-CTS clock policy and congestion recovery, 9 October 2026

Both prior physical continuations stopped in global routing. The combined
reset candidate finished with **1,250 overflow**; no detailed-routed database
or extracted timing was produced. Its independently repeated post-CTS screen
uses placement-estimated signal/clock RC and the three native library corners:

| Post-CTS placement screen, ns | Slow | Typical | Fast |
| --- | ---: | ---: | ---: |
| Worst reported setup | -7.370515 | -3.565318 | -1.546666 |
| Worst reported hold | -0.549185 | -0.399611 | -0.302936 |

These are not signoff results. The typical/fast setup paths now start at
`pcie_retrain_done_i`; the worst hold path starts at `pcie_rx_valid_i`.
The [path records](../hw/soc/pcie-evidence/20261009-packet-routing-recovery/previous-postcts-worst-paths.json)
retain the actual start/end points and method scope.

One-iteration native routing diagnostics show clock nets concentrated in the
congested regions. Moving clocks to TopMetal1–TopMetal2 worsened overflow from
10,049 to 19,417 under the same one-iteration method, so that trial was rejected.
The congestion-report row sums include intermediate routing reports and must
not be confused with the router's final overflow table. Congestion rejection
remains enabled throughout.

The earlier clock-policy correction covered only the first mid-PnR STA.
The new flow applies ideal clocks to **all fourteen OpenROAD stages through
CTS entry**, including placement and electrical repair. Native CTS explicitly
propagates the clock trees after constructing them; every subsequent flow
class remains unchanged. The 80 stage identities/order, missing/duplicate-CTS
rejection and actual native placement environments are checked. Completed
placement SDCs retain ideal clocks, and the new completed CTS SDC propagates
all five clocks, including generated `eth_gtx`.

A new candidate enables timing-driven placement and reduces target density
from 40% to 36%. Die, macro placement, original mapped design, timing budgets,
20% routing capacity adjustment and acceptance checks stay unchanged. Placement
and CTS have completed; post-CTS repair and routing still determine whether
this candidate improves timing and congestion. No pending stage is counted as
passing. The [recovery review](../hw/soc/pcie-evidence/20261009-packet-routing-recovery/review.json)
and [frozen diagnostic archive](../hw/soc/pcie-evidence/20261009-packet-routing-recovery/delivery.json)
preserve prior failures and completed placement stages. The later candidate
CTS and active repair stages are excluded from that first archive.

The bundled mid-PnR STA script handles only one corner per process. Its state
file can retain older metrics for other corners, and some unqualified helper
queries span corners. Those inherited or mixed values are not fresh
three-corner evidence. The independent screen explicitly names each corner
for every setup/hold path report; a new screen is queued after candidate
post-CTS repair. Final acceptance still requires extracted timing.

### Strict routing progress and Ethernet output hold repair, 9 October 2026

The timing-driven 36% placement finished post-CTS repair but initially stopped
with **106 global-route overflow**, improved from the previous 1,250.
Reusing that exact pre-routing state with `GRT_OVERFLOW_ITERS=200` reaches
**zero final overflow**, with congestion rejection still enabled. The
[native routing log](../hw/soc/pcie-evidence/20261009-ethernet-output-hold/strict-grt.log)
records a router-selected NDR fallback on `clknet_0_eth_rx_clk_i`. This clock
routing change requires subsequent timing/physical verification. Post-routing
repair remains active; global-route success is not detailed-route or timing
acceptance.

An independent copy of the completed post-CTS database identifies ten Ethernet
output hold paths with enough setup margin for native delay cells. The
[repair helper](../hw/soc/pnr/eth_output_hold_eco.tcl) inserts two transparent
`sg13g2_dlygate4sd3_1` cells on each TX data/enable/error output. Existing cell
locations and orientations are held during legalization, then their original
placement statuses are restored. Every serialized SDC command remains identical.
The helper rejects duplicate application on an actual saved database.

The [three-corner Ethernet measurements](../hw/soc/pcie-evidence/20261009-ethernet-output-hold/ethernet-slacks.json)
use placement-estimated RC, the same libraries and unchanged I/O budgets:

| Worst of ten Ethernet outputs, ns | Slow | Typical | Fast |
| --- | ---: | ---: | ---: |
| Setup before | +3.461991 | +4.142604 | +4.511979 |
| Setup after | +2.199269 | +3.354426 | +3.982798 |
| Hold before | +0.528468 | +0.049899 | -0.208535 |
| Hold after | +1.609908 | +0.731951 | +0.259062 |

All ten output endpoints are required in each of the six reports; missing
corner/endpoint controls reject. The [pin-graph comparison](../hw/soc/pcie-evidence/20261009-ethernet-output-hold/pin-graph.json)
preserves 101 ports and 290,001 non-buffer pin bits and rejects seven actual
connection/function faults. Disconnected CTS load buffers remain explicit graph
objects. The portable helper produces a byte-identical ODB and Verilog to the
measured trial, as recorded in its
[native controls](../hw/soc/pcie-evidence/20261009-ethernet-output-hold/helper-controls.json).
Earlier trials that allowed existing cells to move remain in the archive.

**Whole-chip timing is still open.** The
[complete corner comparison](../hw/soc/pcie-evidence/20261009-ethernet-output-hold/whole-chip-comparison.json)
retains worst setup of −5.108523 / −2.334330 / −0.791834 ns. Fast-corner worst
hold is now a CPU-domain path at −0.067636 ns. This isolated correction has not
been accepted as a routed main-chip change. The separate replay-bank RTL
candidate continues its physical flow and must be assessed independently.

The [public capsule](../hw/soc/pcie-evidence/20261009-ethernet-output-hold/delivery.json)
contains the completed output trials and graph proofs, original post-CTS state,
failed 106-overflow route and successful strict global route: **138 members,
149,910,657 bytes**. Complete anonymous readback matches SHA256
`5fab7688de2c1a9ffee2458fbc724a12789f8b7c1558f9b60424cd9177d7f70f`.
Active later repair/routing stages are excluded.


### RX read proof strengthened; one-hot trial rejected, 9 October 2026

A parallel index-decode trial for receive ownership passed the existing
undefined-state sequential proof but worsened the independent unplaced timing
screen. It has **not** been adopted. With the same replay-bank candidate,
slow/typical/fast setup changes from −2.538696 / −0.236299 / +0.723702 ns to
−2.733356 / −0.375394 / +0.562434 ns; mapped cells increase from 78,018 to
78,078, preserving 101 ports. These are mapping screens, not routed timing.
The [comparison](../hw/soc/pcie-evidence/20261009-rx-read-proof/preplacement-comparison.json)
retains exact start/end points.

An actual wrong-byte-index mutation also passed the old sequential proof:
1,173 points reported proved. This exposed a verification gap around initially
undefined memory reads. That result is not accepted as evidence of correctness.
The [new independent cut](../scripts/check_pcie_rx_read_cut.py) supplies every
stored bit and address as an arbitrary defined input, comparing the actual
candidate read expression against the frozen flat reference. It covers every
language-defined address, including cross-bank reads; it does not mask outputs
using `out_valid` or assume reachable state. Out-of-array reads have undefined
Verilog semantics and are explicitly outside this cut's assertion domain.

RX [combined equivalence](../scripts/check_pcie_chip_timing_equivalence.py) now
requires both checks. The same wrong-index candidate is
[rejected](../hw/soc/pcie-evidence/20261009-rx-read-proof/wrong-index-joint.json)
by the new cut despite the old sequential stage reporting 1,173 proved points.
Two positive dimensions, actual packet/DLLP wrong-byte controls and a changed
state-shape control pass five tests; the two existing RX sequential cases also
pass with the additional cut. No production RTL or timing constraint changed.

The [public experiment capsule](../hw/soc/pcie-evidence/20261009-rx-read-proof/delivery.json)
contains the candidates, rejected setup results and preparation attempts, exact
proof sources, failed mutation detection, corrected cuts and native logs:
**123 members, 21,318,338 bytes**. Complete anonymous readback matches SHA256
`6201795773c66861e33c4ec9a19658ac10a1c4a1e5131b7d5ed3e8b36cfd0436`.


### Shorter LCRC end-of-packet verdict, 9 October 2026

The [receive quarantine](../hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v) now tests the
inverse CRC residue on the late byte path. Reversing eight reflected polynomial
steps maps `DEBB20E3` to `00BE26ED`; the new predicate compares the CRC seed XOR
the incoming byte against this value. It preserves the original CRC update,
packet state, storage, handshakes and cycle latency. This removes the full byte
CRC update from the EOP acceptance dependency without adding an output buffer.

The [independent checker](../scripts/check_pcie_crc_residue.py) binds the frozen
pre-change controller and unchanged CRC primitive. It requires the entire
controller to match apart from this one predicate, then proves equality for all
**41 CRC-state/data-byte/SOP input bits** using native SAT. Three actual wrong
predicates fail; changed length, handshake and CRC update definitions are also
rejected. Seven source controls pass. The initial test expected the newer
Yosys counterexample banner; older Yosys aborts at `-verify` with a different
explicit proof-failure diagnostic. That failed test expectation and its corrected
portable assertion are retained in the capsule. Six integrity tests and five
buffered packet/credit tests pass with zero failures or skips.

The [whole-chip mapping screen](../hw/soc/pcie-evidence/20261009-crc-residue/preplacement-comparison.json),
combined with the earlier replay-bank candidate, improves worst setup:

| Unplaced setup slack, ns | Slow | Typical | Fast |
| --- | ---: | ---: | ---: |
| Replay-bank baseline | −2.538696 | −0.236299 | +0.723702 |
| Inverse-residue verdict | −2.475437 | −0.184042 | +0.793174 |

The candidate maps to 78,184 cells and 101 ports. Its pre-placement electrical
repair preserves [279,794 non-buffer pin bits](../hw/soc/pcie-evidence/20261009-crc-residue/pin-graph.json)
and rejects seven actual graph faults. This functional RTL correction is adopted;
its physical implementation is a separate active run with the same clock periods,
I/O budgets, macro placement, die, 36% placement density and 20% global-routing
reservation. These unplaced results do **not** establish setup/hold closure,
routed layout, qualified extraction or serial PHY acceptance.

The [completed proof/mapping capsule](../hw/soc/pcie-evidence/20261009-crc-residue/delivery.json)
contains exact sources, tests, native mapping and corner reports, excluding the
active physical run: **208 members, 24,310,218 bytes**. Complete anonymous readback
matches SHA256 `9c4b300cbc4eac1038ac35e0363e696fc6b255d7d40caf1162e0c44e06e0a9d5`.

### Three-corner hold repair on the placed packet chip, 9 October 2026

The replay-bank candidate now has a separate, verified post-CTS repair state.
It uses the pre-residue RTL candidate; it must not be confused with the active
CRC-residue placement. Native hold repair inserts 190 buffers, followed by
short-branch delays and link/retrain input-tree resizing. Existing placements
are frozen during legalization of the added delay cells. The final state has
219 more transparent buffers than its original post-CTS baseline.

The [fresh three-corner screen](../hw/soc/pcie-evidence/20261009-replay-hold-eco/corner-review.json)
uses propagated clocks and placement-estimated signal/clock RC:

| Worst slack, ns | Slow | Typical | Fast |
| --- | ---: | ---: | ---: |
| Setup before repair | −3.721334 | −1.451861 | −0.193468 |
| Setup after repair | −3.721334 | −1.192443 | +0.079398 |
| Hold before repair | −0.018985 | −0.070460 | −0.208139 |
| Hold after repair | +0.136141 | +0.047381 | +0.005748 |

An additional native census of **all negative hold endpoints** returns zero in
each corner. This is broader than merely reading the first path in a report.
SDC commands are unchanged. The [whole-chip graph check](../hw/soc/pcie-evidence/20261009-replay-hold-eco/pin-graph.json)
preserves all 101 ports and 288,121 non-buffer pin bits and rejects seven actual
corruptions, including data, clock, reset, tie, missing buffer, port and wrong
function. The reports include all path groups when selecting the worst slack.

Rejected experiments remain available: unfrozen legalization worsened slow
setup, isolated input strengthening introduced short-path violations, and one
attempt failed on stale parasitic estimates after resizing. The corrected
sequence refreshes parasitics before buffer insertion and explicitly measures
all three corners again. The final candidate has started a separate strict
routing run with 13% track reservation and 200 overflow iterations, retaining
clock periods, I/O budgets and zero-overflow requirements. That run is pending.

**This closes hold only in the placement estimate.** Slow and typical setup
still fail; the 5.748 ps fast hold margin must survive actual routing/extraction.
The result does not establish final timing, full serial PHY integration or
manufacturing readiness.

The [completed evidence capsule](../hw/soc/pcie-evidence/20261009-replay-hold-eco/delivery.json)
contains 323 members and **324,803,276 bytes**, including the frozen baseline,
repair states, native logs, failed experiments and graph controls. Active
routing directories and logs are excluded. Complete anonymous readback matches
SHA256 `1b7b1ac679a07bba8d09f834ed636a49b5fb7b6ecec9de9c21ae5439b903d65b`.

### Credit class verdict and replay metadata trial, 9 October 2026

The CRC candidate's actual pre-repair post-CTS slow critical path runs from
replay `new_slot[1]` to `credit_data_limit_o[22]`, with −4.121705 ns slack.
A separate candidate decodes the fixed replay-bank metadata before selecting
the bank and computes all three Boolean credit-availability decisions before
the late class selection. There is no added state, packet latency or modified
credit arithmetic in these two changes.

The [credit reference proof](../hw/soc/pcie-evidence/20261009-credit-verdict/credit-proof.json)
passes 340 sequential equivalence points, including explicit clock/reset events.
Four actual faults are rejected: wrong selected class, inverted data-credit
sign, ignored data availability and ignored same-cycle debit. The replay change
also passes [743 points at depth three](../hw/soc/pcie-evidence/20261009-credit-verdict/replay-depth3-proof.json),
in addition to the previously recorded default-depth proof. Three integrated
credit/replay and five buffered-packet RTL tests pass without skips.

The [unplaced comparison](../hw/soc/pcie-evidence/20261009-credit-verdict/comparison.json)
uses the same native libraries and constraints; only mapped flip-flop identities
change in the generated CDC bindings. All 101 ports and twenty SRAM macros remain.

| Worst slack, ns | Slow | Typical | Fast |
| --- | ---: | ---: | ---: |
| Prior CRC setup | −2.475437 | −0.184042 | +0.793174 |
| Candidate setup | −2.286632 | −0.075190 | +0.849711 |
| Prior CRC hold | −0.473121 | −0.539480 | −0.601382 |
| Candidate hold | −0.488082 | −0.539480 | −0.601382 |

Slow setup improves by 188.805 ps, but slow hold worsens by 14.961 ps. The design
maps to 78,170 cells. The [repair graph check](../hw/soc/pcie-evidence/20261009-credit-verdict/pin-graph.json)
preserves 280,009 pin bits and rejects seven actual corruptions. A separate
physical run stops after native CTS, then automatically reports all three
corners before selecting further repairs. The candidate is **not adopted as
production RTL**; setup/hold, routed extraction and full serial PHY remain open.

The [completed source/proof/mapping capsule](../hw/soc/pcie-evidence/20261009-credit-verdict/delivery.json)
contains **225 members and 24,570,734 bytes**, excluding the active
physical run. Complete anonymous readback matches SHA256
`351e9b3a87f12a60a46c0f4acfff3d9f87e63ccf5bdf84409606908eef3cf03a`.


### Metadata invariant resolved; timing candidate rejected, 9 October 2026

A further replay candidate registers the class and payload count before the
reservation handshake. Its original optimistic undefined-state equivalence
result was insufficient: the strict two-state induction left thirteen points
unproven. Those failures remain in the evidence.

The [new reset-based proof review](../hw/soc/pcie-evidence/20261009-metadata-invariant/proof-review.json)
uses unbounded PDR on the actual RTL, including its CRC logic, at the production
defaults of four slots and 38 bytes per slot. Whenever `reserve_valid_o` is true,
both registered metadata values equal the unchanged slot decode. All remaining
functional RTL is text-identical. Idle metadata is deliberately outside that
contract. Fifteen RTL tests pass, and two actual corruptions of class and
payload are rejected by packet reservation assertions. The proof does not
establish arbitrary parameter values or physical timing.

The [published proof capsule](../hw/soc/pcie-evidence/20261009-metadata-invariant/delivery.json)
contains 258 members and **2,753,417 bytes**, with complete anonymous readback
matching SHA256
`6714ebfbf7021c995c344d8b11a6b549d7c33f7c3e665d95b5f955411b900003`.
It includes the failed proof attempts and the exact successful native model.
A copied runner's description incorrectly mentions abstracted CRC acceptance;
the reviewed native model contains no such abstraction, as the review records.
Later timing runs are outside this proof capsule.

Despite passing this functional proof, the candidate is **not adopted**.
The [preplacement screen](../hw/soc/pcie-evidence/20261009-metadata-invariant/timing-rejection.json)
worsens setup in all three corners relative to the preceding credit-verdict
candidate: slow −2.286632 → −2.463721 ns, typical −0.075190 → −0.262949 ns,
and fast +0.849711 → +0.838629 ns. This preliminary screen is sufficient to
reject the experiment; it is not a placement, routed timing or graph-acceptance
claim. The next arithmetic candidate targets the two serial subtractors on the
actual consumed-credit to credit-limit path, without changing packet latency.


### Placement hold repair with complete endpoint census — 9 October 2026

The CRC candidate's [repair review](../hw/soc/pcie-evidence/20261009-bindfix-c4-hold/hold-review.json)
records zero negative hold endpoints in all three placement-estimated corners.
Worst hold is +0.195945 / +0.073940 / +0.001016 ns (slow / typical / fast).
Targeted SOP/DLLP, self-feedback and setup-headroom-qualified branch buffering
preserves the post-native-repair worst setup: −4.120471 / −1.268695 / −0.107212 ns.
The final sibling branch uses a buffer with sufficient input capacitance to avoid
accelerating the other path from the same register. All 101 ports and 288,294
non-buffer pin bits are graph-equivalent; seven corruptions are rejected.

This is **not overall setup-neutral**: the earlier native hold stage worsened
typical setup by 106.551 ps and fast setup by 263.645 ps relative to its input.
The candidate is not adopted and has no routed hold acceptance. Its narrowest
hold margin is only 1.016 ps. Setup remains negative.
The [complete source/repair capsule](../hw/soc/pcie-evidence/20261009-bindfix-c4-hold/hold-delivery.json)
has 177 members / 213,918,222 bytes and verified anonymous whole-file SHA256
`9080c50068d02cfe3f7aab99b70be30efeff114ac736ac71f73024d81ee9af57`.


### Routed baseline: zero router DRC and antenna violations, timing fails

The original packet-interface chip candidate `postgrt13-01` completed detailed
routing with **zero router DRC errors**, followed by **zero antenna nets/pins**
and completed nominal RC extraction. These checks do not establish full foundry
DRC/LVS or integrate the missing serial PHY. The
[three-corner extracted-RC review](../hw/soc/pcie-evidence/20261009-routed-rc-baseline/review.json)
records the actual post-route failures:

| Extracted nominal RC | Slow | Typical | Fast |
| --- | ---: | ---: | ---: |
| Worst setup, ns | −13.556860 | −7.122849 | −3.342535 |
| Worst hold, ns | −0.125114 | −0.420728 | −0.577340 |
| Setup violating endpoints | 9,599 | 5,683 | 1,522 |
| Hold violating endpoints | 2 | 33 | 123 |
| Max slew violations | 451 | 218 | 135 |
| Max capacitance violations | 44 | 44 | 45 |

An [independent OpenROAD readback](../hw/soc/pcie-evidence/20261009-routed-rc-baseline/independent-slack.json)
of the same ODB, SDC, libraries and SPEF reproduces all six worst slacks. Reports
must take the minimum across **all clock groups**, not the first reported group.
The critical PCIe path includes a NOR2_1 output driving 0.625582 pF; its cell
arc contributes 5.627487 ns and its output transition is 7.976495 ns. Load and
buffering repairs are under evaluation on a separate copy. Any modified candidate
requires new routing, extraction and functional checking.

The [routed evidence capsule](../hw/soc/pcie-evidence/20261009-routed-rc-baseline/delivery.json)
contains the routed ODB/DEF/netlists/SDC/SPEF, native reports and independent
readback: **198 members / 196,812,649 bytes**, anonymously downloaded and verified
against SHA256 `c306c89ac31fd37018740deb988c011ee15553d38d4d47608ece10bff8f8266f`.
It preserves this failed baseline; it is not timing acceptance. The separate CRC
placement hold experiment above is a different candidate and cannot replace these
routed results. The three library corners share nominal wire RC, so this also
is not qualified multi-corner interconnect signoff.
