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
