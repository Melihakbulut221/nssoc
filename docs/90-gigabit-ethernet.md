<!--
SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
SPDX-License-Identifier: CC-BY-4.0
-->
# Gigabit Ethernet MAC integration

2026-09-19. `soc_eth` adds a fixed **1 Gb/s, full-duplex GMII MAC** to
`soc_top`. The external copper/fibre PHY, pad ring, package and board are not
implemented here. PCIe has a separate dependency assessment in docs/91.

## RTL and software boundary

The upstream MAC is `alexforencich/verilog-ethernet` at
`77320a9471d19c7dd383914bc049e02d9f4f1ffb`, including its bundled AXIS snapshot,
under MIT. `make soc-interfaces-prepare` fetches the clean pinned dependency;
`prepare_interfaces.py` retains license notices and hashes every input.
The generated bundle adds synchronous reset to the TX frame pointer, padding
counter and error register. The upstream checkout remains unchanged. Native
gate simulation exposed X propagation through their mapped feedback with
FPGA initialization removed; explicit reset makes ASIC startup deterministic.

The MAC inserts preamble/SFD, pads short TX payloads to 60 bytes, appends CRC32,
and uses a 12-byte interframe gap. Each direction has a 2048-byte frame-aware
asynchronous FIFO carrying data, last and error bits. RX bad-FCS and overflowing
frames are discarded; oversized TX frames are discarded. Reset asserts
asynchronously and releases synchronously in the 50 MHz APB and independent
125 MHz RX/TX domains. The external TX clock is forwarded as `eth_gtx_clk_o`.
GMII clocks must continue while normal packet transfers are active.

The interface is programmed IO, without DMA. It cannot sustain an uninterrupted
1 Gb/s stream through the 50 MHz APB port. It has no 10/100 Mb/s mode, MAC-address
filter, network stack or ECC/TMR protection of the new packet buffers/control
state. The CRC is a link-integrity check, not radiation hardening. MDIO is a
software-controlled MDC/data/output-enable interface with synchronized input;
there is no autonomous management transaction engine or auto-negotiation driver.

APB slot `0x01A`, base **0xFF91A000**, project device ID `0xE01`, logical IRQ25
maps to Ibex fast IRQ13 / `mip` bit29. No existing address or IRQ moved.

| Register | Offset | Fields |
|---|---:|---|
| CTRL | 0x000 | TX enable bit0, RX enable bit1; writing bit2 flushes both FIFOs/MAC |
| STATUS | 0x004 | TX ready bit0, RX valid bit1, RX last bit2, RX error bit3, reset active bit4 |
| TX | 0x008 | Data bits7:0, last bit8, abort/bad bit9; one byte per write |
| RX | 0x00C | Data bits7:0, last bit8, error bit9, valid bit31; read pops one byte |
| EVENTS | 0x010 | Sticky W1C; a concurrent event wins over clearing |
| IRQEN | 0x014 | Event masks bits8:0, RX-available level mask bit9 |
| MDIO | 0x018 | MDC bit0, MDIO output bit1, output-enable bit2, synchronized input bit8 |
| ID | 0x0FC | `0x474D4901` |

Event bits0..8 are TX good, RX good, TX bad, RX bad, RX overflow,
TX underflow, RX bad FCS, RX bad frame and TX overflow, respectively.
Empty RX reads, disabled/full TX writes, undefined registers and writes to
read-only registers return PSLVERR. Writes require byte strobe0; strobe1 gates
the upper event/mask bits and TX last/abort. Firmware must enable TX/RX before
using the FIFOs. `hw/soc/tb/sw/soc_eth.h` supplies the software constants.

## Verification and physical mapping

```sh
make soc-interfaces-prepare
scripts/run_cocotb.sh soc_eth
SOC_MEM_RDREG=1 SOC_REQ_REG=1 SOC_RF_SYNPRE=1 SW_DEFINES=-DETHERNET_DEMO \
  bash hw/soc/flow/sim_soc.sh hw/soc/out/ethernet-demo
bash hw/soc/flow/test_eth_sram.sh hw/soc/out/eth-sram
bash hw/soc/flow/implement_interfaces.sh unique-run-tag
```

The six block tests pass in RTL and with the **native PDK SRAM and standard-cell
models**, without initialization of DUT registers from the testbench. They
check independently computed wire CRC/padding, 1514-byte TX/RX frames spanning
both SRAM banks, bad-FCS discard/recovery, overflow preserving a committed RX
frame, oversized/incomplete TX discard/flush, APB errors, byte strobes, MDIO and
interrupt/reset behavior. The gate runner requires Icarus 13 or newer because
Icarus 12 does not drive the PDK flip-flop delayed timing pins. These are
functional, zero-delay tests without extracted SDF or analog PHY compliance.

The CPU demo executes firmware that sends 60 bytes, loops actual GMII output
pins into the receive pins, checks the payload/last indication, observes `mip`
bit29 and drains the receive interrupt. It does not inject a pre-completed
packet directly into an internal FIFO.
The fresh run finishes after **159269 cycles**. Source hashes, native gate-test
XML and the complete CPU transcript are committed in
[the Ethernet evidence record](evidence/ethernet-20260919.json).

**First mapping, superseded 2026-09-19:** Yosys 0.33 maps the FIFO pair to **four
`RM_IHPSG13_2P_1024x16_c2_bm_bist` macros**, with 508 standard-cell flip-flops
and **2615 total cells** including macros. Combined typical Liberty area is
**667066.4354 um2**, of which **620615.3428 um2** is SRAM. The register-array
experiment used 41486 flip-flops; it is not the physical profile. These are
standalone MAC synthesis figures, not placed whole-chip area.

`SOC_ETH_SRAM=1` selects the mapping in the whole-SoC synthesis script and is
mandatory in `implement_interfaces.sh`. Only the Ethernet memories are selected;
the frozen accelerator's memories and protection are not remapped. The active
~~floorplan extends 540 um to the right for the four new SRAMs and carries all
twelve macro physical views~~. **Corrected 2026-09-19:** the active mapping uses
sixteen `RM_IHPSG13_2P_256x16_c2_bm_bist` macros, eight per FIFO, keeping each
FIFO at 2048 bytes. The die is now **3326.4 × 2475.9 um**, with two new SRAM
columns and **24 macros total**. Each has physical views and power hooks;
RX/TX clocks remain explicitly constrained to 8 ns.
Cross-domain paths have an 8 ns maximum datapath budget; only asynchronous
hold checks are excepted. A broad clock-group false path would hide this bound
and is deliberately absent. GMII input/output budgets are stated board/PHY
assumptions in `soc_interfaces.sdc`; they require replacement against real
pad, package and PHY characterization.

The old eight-macro routed results in docs/88 **do not validate this revision**.
Its physical timing and DRC must be measured afresh; passing RTL/gate packet
tests is not a physical signoff or a radiation qualification.

## Measured SRAM replacement

The first 1024-word-bank implementation failed 125 MHz setup after clock-tree
construction and timing repair: **−0.805066 ns**, with 17 setup violations at
the slow corner. The critical path starts at the TX SRAM's read output.
Its native slow Liberty clock-to-output delay leaves too little of the 8 ns
period for the bank mux and destination register. This is an implementation
failure, not an input/output constraint to waive.

The 256-word banks pass the same **six native gate-level packet tests**,
including overflow, bad FCS, flush and a full-size packet. Standalone mapping
uses **2693 cells, 512 flip-flops, 16 SRAM macros**, and **968710.3670 um2**
of combined cell/macro area. It costs more SRAM area than the first mapping.
The complete SoC synthesis has **65667 cells, 9352 flip-flops, 24 macros** and
**1045780.5456 um2 of standard-cell area**, excluding macro area.

Identical pre-layout STA budgets, OpenSTA 3.1.0, ideal clocks, 5% derates:

| TX-domain setup margin | First 1024-word banks | Active 256-word banks |
|---|---:|---:|
| Fast | +4.717523 ns | +5.083783 ns |
| Typical | +2.846943 ns | +4.077037 ns |
| Slow | −0.434501 ns | +1.520293 ns |

These are setup comparisons without wire RC or CTS; **hold still fails** in
both pre-layout netlists. The new physical optimization includes fast, typical
and slow corners, whereas the first candidate optimized only typical and slow.
Signoff checker limits are unchanged. The first candidate was stopped during
post-global-route repair; it has no completed detailed-route/GDS result.

The scripts used for the comparison, exact path reports, hashes, gate-test XML,
whole-SoC synthesis input inventory and the first candidate's native post-CTS
metrics are in [the SRAM comparison record](evidence/ethernet-sram256-20260919.json).
The new physical run is `interfaces-eth256-20260919`; its completion and
extracted timing must be reported separately from the setup-only comparison.

## Restart and timing-replay correction

The checkpoint resumed into `interfaces-eth256-resume-20260919-184950`.
The original post-CTS design is retained; global routing and antenna repair
ran on the resumed candidate. Final detailed routing and extracted timing
remain pending at this update.

**Diagnostic correction, 2026-09-19:** an independent read-only timing probe
initially reported slow setup **−0.721402 ns** on the post-GRT design-repair
ODB. It loaded the same Liberty models and SDC but omitted the native process's
`_LAYER_RC_*` and `_VIA_R_*` environment entries, silently using tech-LEF wire
RC defaults. This is **not comparable with the native flow**. Sourcing a step's
`_env.tcl` alone did not reproduce its complete timing environment.

Repeating that probe on the **same ODB**, with the native layer/via overrides,
measured **−6.660567 ns** slow setup. The ODB has saved global routes; their
absence was checked and rejected as the explanation. Neither probe is final
extracted STA, and neither changes the ongoing repair run. The corrected
comparison, exact scripts, model environment and artifact hashes are in
[the replay record](evidence/timing-replay-20260919.json). The earlier ideal-clock,
no-wire-RC SRAM comparison above has a different, explicitly pre-layout scope.

A separate optimizer experiment used the identical post-antenna input state
and identical resolved configuration, changing only the setup search to
120 iterations and four repairs per pass. OpenROAD 26Q1-2938-g0e2d771c5e
aborted in `rsz::SizeUpMove::doMove` with a C++ vector bounds assertion. It
produced **no completed output state** and is rejected. The baseline flow and
its default one-repair-per-pass policy remain unchanged. The failed trial's
script, configuration identity and error are retained in the replay record.

A subsequent standalone **512-word-bank** comparison maps the same FIFO
capacity to **8 macros, 2593 cells and 510 flip-flops**, with combined
cell/macro area **754922.4916 um2**. Using the same ideal-clock budgets, TX setup
margin is +5.043968 ns fast, +3.382492 ns typical and **+0.424931 ns slow**.
Its smaller area trades away 1.095362 ns of the active 256-word mapping's
slow setup margin, so it was **not adopted**. This is a synthesis/STA experiment;
no routed result or packet-regression success is claimed for the 512-word
candidate. Scripts and hashes are appended to the SRAM comparison record.

The native post-global-route repair subsequently completed and saved a new
ODB/netlist. Replaying that saved state with the native layer/via RC gives
setup/hold in ns: **fast +3.262364 / -0.150652, typical +2.042962 / +0.131439,
slow -2.045677 / +0.385958**. The fast values agree with the fresh native
`STAMidPNR-3` report; the other corners were explicitly remeasured rather than
read from inherited state metrics. The worst slow path starts at register-file
read address B bit 2 and ends at register x28 check bit 6. It is not an Ethernet
SRAM path. These are global-route estimates, not final extracted timing.

The existing netlist guards were also applied directly to this post-GRT
netlist: boot, NPU and watchdog replica cones remain disjoint, and the
asynchronous-reset cone guard passes. The exact saved artifacts, probe command,
results and guard log are appended to `timing-replay-20260919.json`.
Detailed routing is still in progress at this observation.

### Native whole-netlist fault-free execution

2026-09-19. The old `fi_core_gl.sh` could not elaborate this design: it
omitted the ECC ROM check macros and dual-port Ethernet SRAM models.
The flow now selects their native PDK models from the actual netlist, initializes
the ROM check banks with the frozen SECDED encoder, and connects the added
interface inputs to explicit idle levels. `fi_core.sh` now checks that
`SOC_REQ_REG` and `SOC_RF_SYNPRE` select the requested elaborated branches.
Historical defaults remain unchanged.

The current post-global-route netlist and a matching RTL build both complete
the same ROM workload with watchdog disabled (`+armed=0`): signature `9c07ef12`, mask and exit zero, four rounds,
19 UART characters with hash `6d6942c8`, and no asserted watchdog, trap, NMI,
alert or double-fault channel. The measured cycle counters are **27,306 at
gate level and 27,307 in RTL**, so this is a matching-answer check, not a
cycle-equivalence claim. The native gate run uses Icarus 13; the RTL bytecode
uses its matching configured Icarus 12 runtime.

The [baseline record](evidence/ethernet-gate-baseline-20260919.json) includes
commands, both complete result records, source/model provenance, hashes and
failed attempts. This is a zero-delay, fault-free check with idle interfaces;
it does not establish SDF timing, an injected-fault coverage rate or Ethernet
traffic behaviour. Missing gate-level shadow instrumentation is recorded as
unavailable, never as a zero error count.

2026-09-19, watchdog-enabled follow-up: the same native post-global-route
netlist also completes with the watchdog armed and matches RTL's published
answer, with no watchdog event, NMI, trap or alert. The existing software
`FI_WDOG_RELOAD=255u` override sets a 4096-cycle interval; RTL's measured
maximum kick gap is 2894 cycles. RTL completes in 27307 cycles and the gate
bench in 27306; these counters are not a cycle-equivalence claim.

The earlier workload's default reload 127 permits only 2048 cycles. Running
that program with the watchdog armed produces four stage-1 events and four
NMIs in **both** RTL and gates, despite returning the right answer. Those
logs remain recorded as a failed clean-control condition. The software
override, exact ROM identity and both outcomes are appended to the
[baseline evidence](evidence/ethernet-gate-baseline-20260919.json). This is a
fault-free control, not a completed injected-fault campaign or SDF signoff.

2026-09-20, extracted candidate: `interfaces-eth256-resume-20260919-184950`
now has detailed routing, nominal interconnect extraction and both GDS streams.
Three independent native STA runs measure:

| Corner | Whole-design setup WNS (ns) | Hold WNS (ns) | Worst GMII TX output setup / hold (ns) |
|---|---:|---:|---:|
| Fast | +3.283147 | −0.036038 | +3.283147 / +0.712912 |
| Typical | +2.348404 | +0.083726 | +2.348404 / +1.370800 |
| Slow | −1.828438 | +0.243966 | +0.632443 / +2.582863 |

The slow corner has 513 setup violations and the fast corner four hold
violations. The worst setup path runs from the APB address register to the
Ethernet TX SRAM write enable; CPU paths also fail. All ten GMII TX data/control
ports meet the stated core-to-port budgets, but this does not close internal
SRAM timing or characterize a PHY, pad or package. The experimental extra
falling-edge output stage passed six native packet tests; it is not adopted,
since the extracted shipping outputs now meet these budgets.

Router DRC is zero; three antenna nets/pins still fail. The connectivity checker
reports zero **critical** disconnected pins, with 256 unused macro outputs
reported as noncritical unconnected pins. Independent Magic/KLayout DRC, stream
XOR and scoped LVS are running separately. Exact source artifacts and the
unmodified native measurements are pinned in the
[extracted layout record](evidence/ethernet-extracted-layout-20260920.json).
This candidate remains a failing physical implementation.

![Measured placement of the 24 SRAM macro candidate](img/interfaces-ethernet-layout.png)

The [vector placement view](img/interfaces-ethernet-layout.svg) is generated
from this run's actual final DEF and metrics; all 18 geometry/metric checks
pass. It shows macro footprints and logic density, with routing hidden.
It is a view of the failing candidate above, not a clean-layout claim.

### Antenna repair follow-up, 2026-09-20

The separate `eth256-antfix-20260919` candidate raised the permitted antenna
repair iterations to eight without changing antenna thresholds. Three further
iterations reduced violating nets **3 → 2 → 1 → 0**, inserting **six diodes**;
the final detailed-router DRC count is **zero**. The subsequent independent
checker was interrupted by SIGTERM, so it was replayed against the saved route
as `eth256-antcheck-20260920`: **zero violating nets and pins**, flow complete.
The [record](evidence/ethernet-antenna-repair-20260920.json) binds the command,
metrics and output hashes. This closes that candidate's antenna check only.
The original extracted timing/GDS above, the ongoing independent decks, and
the later timing ECO are distinct artifacts; their results cannot be mixed
into a passing final candidate.

### Independent extracted-netlist LVS, 2026-09-20

`eth256-lvs-20260920` completed on the original 24-macro
`interfaces-eth256-resume-20260919-184950` candidate. Netgen reports
**Circuits match uniquely**, with **94,490 devices and 94,219 nets** on
each side, all **seven LVS counters zero**, and **zero Magic illegal
overlaps**. The [record](evidence/ethernet-lvs-20260920.json) contains the
command and hashed inputs/reports. SRAM interiors are black boxes; standard
cells and every macro pin are compared. This result does not cover the later
antenna-repaired or timing-ECO candidates and does not close DRC or timing.
