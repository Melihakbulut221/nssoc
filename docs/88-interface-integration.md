# 88 — SpaceWire, CAN, SPI and I2C integration

2026-09-19. This work extends `soc_top`, not the frozen Tiny Tapeout pilot.
The four previously reserved slots now contain real RTL, physical pins and
interrupts. No device is represented by a successful dummy register bank.

## Scope and dependencies

| Block | Implementation | Integration |
|---|---|---|
| SpaceWire | Pinned SpaceWire Reloaded `spwstream`, generic RX/TX | Single endpoint; APB PIO; 64-character RX, 16-character TX; strict timecodes; IRQ line 5 |
| CAN | Pinned Mohor CAN 2.0B controller | SJA1000 byte registers through the proved APB/Wishbone bridge; IRQ line 6 |
| SPI | Project `soc_spi.v` | 8-bit transactions, modes 0–3, two chip selects; IRQ line 7 |
| I2C | Pinned MIT `i2c_master` plus project APB wrapper | 7-bit addressing, read/write, repeated START, stretching, NACK and timeout; IRQ line 8 |

The PnP identification values retain their assigned device numbers. Software
must use the **project register maps** below for SpaceWire, SPI and I2C; these
are not binary-compatible GRLIB drivers. CAN uses the documented SJA1000 map.
SpaceWire is PIO, not the originally proposed DMA channel or a four-port router.
CAN is classical 2.0B, not CAN FD. SPI supports continuous-CS multi-byte transfers through its HOLD control bit.

`make soc-interfaces-prepare` fetches the three commits pinned in
`hw/soc/tools.soc.mk` and runs `hw/soc/flow/prepare_interfaces.py`. The generator
refuses dirty or differently pinned upstream trees. It expands their includes
into ignored `hw/soc/gen/interfaces.bundle.vh`, retains upstream notices, and
writes input and output SHA-256 values to `interfaces.bundle.json`. The `.vh`
extension deliberately keeps the bundle out of the Ibex `gen/*.v` source glob.
Verilog-2005 keyword directives permit upstream's port named `do` in Icarus's
SystemVerilog mode; Yosys uses its native Verilog frontend. Upstream's implicit
wire declarations are permitted within the generated bundle. No upstream
checkout is modified.

SpaceWire and CAN carry LGPL-2.1-or-later, I2C MIT. These dependencies are now
used in this SoC build; the earlier assessment-only statement in docs/65 is
historical. They are not copied into the frozen pilot or relabelled under the
project's licence. External LVDS transceivers for SpaceWire, a CAN transceiver,
and open-drain I2C pads/pull-ups remain board/pad integration requirements.

PCI/PCIe and Ethernet are separate from these four blocks. The repository's
original scope excluded them; this change does not implement or advertise them.
PCIe needs a specified PHY/controller boundary; no open digital RTL wrapper can
substitute for the missing mixed-signal PHY. Hardware fabrication, radiation
qualification, and the vendor SRAM DRC/LVS issue are not closed by this change.

## APB register contracts

All offsets are byte offsets from the generated `SOC_*_BASE`. SpaceWire, SPI
and I2C use aligned 32-bit accesses with all strobes asserted. Unsupported
addresses, partial writes and forbidden/busy operations return PSLVERR without
performing the operation. Reads have no side effects except receive-data pops.

### SpaceWire, `0xFF90D000`

| Offset | Name | Fields |
|---|---|---|
| 0x00 | CONTROL | bit 0 autostart, 1 start, 2 disable; reset 4 |
| 0x04 | STATUS | bit 0 started, 1 connecting, 2 running, 3 TX ready, 4 RX valid, 5 TX half full, 6 RX half full |
| 0x08 | DIVIDER | TX bit period is divider+1 system clocks; minimum 1; reset 4 |
| 0x0c | TX | write 9-bit character: flag in bit 8, data in bits 7:0; full is an error |
| 0x10 | RX | read/pop 9-bit character; empty is an error |
| 0x14 | IMASK | mask for CAUSE |
| 0x18 | CAUSE | sticky W1C: disconnect, parity, escape, credit, timecode in bits 0–4; bit 5 is live RX valid |
| 0x1c | TIMECODE_TX | writing sends timecode, control bits 7:6 and count 5:0 |
| 0x20 | TIMECODE_RX | last in-sequence timecode |

A new error/timecode wins over simultaneous W1C. RX-valid clears only when the
FIFO empties. A flag character with data 0 is EOP, 1 is EEP. The core performs
link startup, parity, credit flow control and disconnect recovery. With the
50 MHz build clock, startup and default transmit speed are 10 Mbit/s. The
generic receiver supports at most half the system clock; this is not a
200 Mbit/s fast-receiver implementation. Firmware must pace timecode requests.

### I2C, `0xFF913000`

| Offset | Name | Fields |
|---|---|---|
| 0x00 | STATUS | bit 0 command active, 1 core busy, 2 bus owned, 3 bus active, 4 RX valid |
| 0x04 | PRESCALE | 16-bit, minimum 4, reset 125; nominal SCL = clk/(4*prescale) |
| 0x08 | ADDRESS | 7-bit target address |
| 0x0c | COMMAND | bit 0 read, 1 write, 2 START, 3 STOP; bit 4 abort/reset; read+write together is rejected |
| 0x10 | DATA | write next TX byte while idle; read/pop RX byte |
| 0x14 | IMASK | mask for CAUSE |
| 0x18 | CAUSE | W1C: bit 0 done, 1 NACK, 2 RX valid, 3 timeout; RX-valid reasserts until drained |
| 0x1c | TIMEOUT | read-only system-clock limit, default 500000 cycles |

One outstanding command is allowed. Another command is rejected until the
previous command completes and its RX byte is consumed. A command without
STOP retains the bus for the next command/repeated START. The total command
timeout bounds indefinite stretching; timeout or software abort resets the
engine and releases both open-drain outputs. It does not promise that an
external device holding the bus low has recovered. This is a single-controller
interface; multi-controller arbitration is not claimed. Input pins have two
synchronizer stages. Firmware polling is also bounded in `soc_interfaces.h`.

### SPI, `0xFF912000`

| Offset | Name | Fields |
|---|---|---|
| 0x00 | CONTROL | bit 0 CPOL, 1 CPHA, 2 chip-select index, 3 IRQ enable, 4 HOLD_CS |
| 0x04 | DIVIDER | 16-bit clocks per SCK half period, minimum 2, reset 4 |
| 0x08 | DATA | write starts one 8-bit MSB-first transaction; read last RX byte |
| 0x0c | STATUS | bit 0 busy, 1 done (W1C), 2 CS active |

Configuration and TX writes while busy fault. Completion wins over a
simultaneous DONE clear. CS remains asserted for one full half-period after
the final edge. With HOLD_CS set, it stays asserted across successive bytes
until firmware clears HOLD_CS. Changing mode or CS index while CS is active
faults. Reset releases both chip selects and restores mode 0.

### CAN, `0xFF911000`

Offsets 0x00–0xff are the upstream byte registers. Use `lb/lbu/sb`: the lowest
address bits travel in PSTRB through this fabric, and `soc_apb_wb` restores the
byte address and correct data lane. Multi-byte strobes and offsets above 0xff
fault. The core's active-low interrupt and bus-off outputs are inverted at the
SoC boundary. The CAN clock and Wishbone clock both use `clk_i`.

## Verification and physical flow

`make rtl-test` includes `Makefile.soc_interfaces`, with actual pin-level peers:

- SPI: every mode and both chip selects, varied payloads, busy-write rejection,
  completion interrupts, invalid dividers and invalid APB accesses. An independent
  peer exchanges different MOSI/MISO payloads at the minimum divider, checks
  sampling edges and verifies exactly sixteen clock edges per byte. Continuous
  chip select is also checked across five-byte frames.
- SpaceWire: two real endpoints, 160 transferred characters (credit recycling),
  EOP/EEP, reverse traffic, strict timecodes, disconnect/reconnect and disable.
- I2C: an independent pin-level slave verifies write, read, repeated START,
  address NACK, clock stretching, stuck-bus timeout, explicit abort and errors.
  Four-byte bursts verify continuation without repeated addressing and the
  controller's three ACKs followed by final NACK on a read.
- CAN: two real nodes exchange standard-ID and 29-bit extended-ID frames,
  eight-byte payloads and an extended remote request in the reverse direction,
  including ACK, RX interrupt and buffer release; every CPU byte lane is exercised.

The final standalone interface run reports **11 passed, 0 failed, 0 skipped**.
The CPU run with full ECC RAM/ROM, `MEM_RDREG=1`, `REQ_REG=1` and register-file
`SYNPRE=1` reports **29 passed application checks** in 663477 cycles. All four
fault-free upstream register-file equivalence tasks (both SYNPRE settings, with
and without scrub) prove by induction. The full RTL sweep on GitHub reports
**471 passed, 0 failed, 15 explicitly skipped**, including all eleven final
interface tests (run `35436883155`, source commit `4ef4491`).

`SW_DEFINES=-DINTERFACE_DEMO` adds check 31 to the real Ibex firmware. The SoC
board model loops SPI and SpaceWire at the pins, resolves the I2C open-drain
pins, and leaves I2C unaddressed to exercise NACK. The program checks actual
CPU interrupt entry for SPI, SpaceWire and I2C, plus CAN byte-register access.
The standalone CAN test supplies the second transmitting/acknowledging node.

The synthesis and layout profile retains ECC RAM and ROM and enables the
existing `MEM_RDREG=1` and `REQ_REG=1` pipelines, with `SYNPRE=1` for the
register file. Its 50 MHz floorplan is generated with a 1100 um channel and
40% placement target in `config-interfaces.json`; `config-interfaces-synpre.json`
records the selected variant. The die is 2306.4 by 2475.9 um (5.7104 mm²).
This profile does not change the RTL defaults. Results are recorded only after
the corresponding tool run completes; synthesis is not counted as layout.

The final mapped netlist has 61,991 cells, including 8,820 resettable flip-flops,
three clock gates and eight SRAM macros. Yosys reports 977,098.6638 um² of
standard-cell area; that figure excludes the SRAM macro areas.

`interface_flow.py` preserves Classic's entire step list and its checker
configuration, adding only `-max_iterations 600` to setup repair after CTS
and global routing. The installed OpenROAD otherwise allows unlimited setup
iterations: the first attempt repeatedly returned to the same -0.501 ns
placement estimate after iteration 330. The bound limits optimization effort;
it does not waive timing failures, relax the 20 ns clock, or narrow the checked
corners. The generated Tcl is saved in each resizer step's directory.

The first global route at the inherited 30% capacity reserve failed with
20 Metal5 overflows. Reusing the same post-CTS placement with a 20% reserve
produced **zero global overflow on every layer**, routing 83,881 nets
(`interfaces-route20-20260919`). The selected profile records that reserve.
`GRT_ALLOW_CONGESTION` remains false. This global-route result does not replace
detailed-routing DRC, final extracted timing, or the separate physical decks.


## Reproduction

```sh
make setup PYTHON=/usr/bin/python3
make soc-prepare
make soc-interfaces-test
make soc-interfaces-sim
export OSS_CAD_SUITE=/absolute/path/to/oss-cad-suite
make rf-equivalence
make soc-interfaces-layout RUN_TAG=interfaces-reproduction
```

The layout command requires the same rootless LibreLane, OpenROAD shims and
pinned IHP PDK as the existing SoC flow. It refuses to overwrite its synthesis
output, snapshots the RTL input hashes, binds them to the mapped netlist hash,
and keeps the physical log under `hw/soc/out/<tag>/layout.log`. Macro-internal DRC/LVS is disabled in the inherited configuration because
of the recorded vendor SRAM problem; this flow does not provide SRAM signoff. The wrappers and the new peripheral control state are not
radiation-hardened replicas.
