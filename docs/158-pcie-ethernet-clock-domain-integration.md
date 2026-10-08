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
