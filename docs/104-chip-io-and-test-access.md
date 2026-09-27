# Chip I/O and read-only MBIST access

This continuation implements an IHP I/O shell and a dedicated serial MBIST
result port around a **selected mapped core**. It also produces a separate
native-cell pad-ring placement. It does not establish a complete padframe,
PCIe PHY, scan/ATPG coverage, package, final timing or manufacturing acceptance.

## Implemented shell

`scripts/generate_chip_io.py` validates the selected Yosys `soc_top` port
signature against `hw/soc/chip-io-contract.json`. The generated `nssoc_chip`
instantiates that parameter-resolved core, 102 signal I/O cells, four supply
cells and `soc_status_serial`. It must not be elaborated against the default
parameterized `soc_top` RTL. The measured candidate uses CPU request/writeback
stages 1/1 and physical register-file `SYNPRE=1`.

The I/O masters are the actual PDK `sg13g2_IOPadIn`, `sg13g2_IOPadOut4mA` and
`sg13g2_IOPadInOut4mA`, with distinct VDD/VSS and IOVDD/IOVSS connections.
GPIO, QSPI and MDIO retain separate core input, output and enable semantics.
I2C connects the pad's output data permanently low; enabling its driver pulls
the line low and disabling it releases the external pull-up. SpaceWire and
CAN still require their external transceivers. GMII still requires its external
Ethernet PHY. These digital I/O cells are not PCIe differential PHY pads.

The four supply instances are an initial structural connection, **not a
qualified current/ESD budget**. Their number/distribution, drive strengths,
bond-pad landing geometry, voltage domains and package/board loads require
product-level analysis. Native behavioral simulation does not model these
analog properties.

## Serial test-result protocol

The four dedicated pins are `pad_test_req`, `pad_test_clk`, `pad_test_ready`
and `pad_test_data`. This interface is read-only: it cannot start MBIST, release
a failed CPU reset, write memory or alter normal SoC operation. Power-on reset
remains the mechanism that starts the destructive MBIST.

1. During POR, hold request low. Start both source and test clocks after reset;
   each domain synchronizes reset release separately.
2. Toggle request and keep its new level fixed throughout the transaction.
   Continue test clocks while waiting for ready to go low and then high.
3. Once ready rises, sample data **before each rising test-clock edge**, for
   exactly 192 bits. The least significant bit is first. The first bit becomes
   available after the edge that accepts the snapshot; do not clock it away
   before sampling it. Further clocks return zeros.
4. Toggle request again for another snapshot. Never issue another request
   before the previous handshake/frame completes. POR invalidates a partial
   frame; the host must reset its request level to zero and restart.

The source clock atomically captures a 192-bit snapshot and holds it until the
next request. A two-stage acknowledgement synchronizer precedes capture in
the test-clock domain. This is a bundled-data CDC: **physical constraints must
bound snapshot-bus delay relative to acknowledgement**, preserve synchronizers
and verify reset recovery/removal. No blanket false path or current simulation
result establishes that timing condition. If the source clock stops, a fresh
request remains unacknowledged; stopping the test clock preserves a partial
frame. This is neither IEEE JTAG nor RISC-V debug.

| Bits | Meaning |
|---|---|
| 0 | Combined MBIST busy |
| 1 | Combined MBIST done |
| 2 | Combined MBIST failed |
| 4:3 | Ethernet FIFO done vector |
| 6:5 | Ethernet FIFO failed vector |
| 19:7 | System-RAM failing address |
| 83:20 | Expected raw SRAM word |
| 147:84 | Actual raw SRAM word |
| 150:148 | March phase |
| 158:151 | Background index |
| 159 | Reserved, zero |
| 191:160 | Magic/version `0x4d420001` |

`python -m sw.golden.chip_status FRAME_HEX` decodes 24 bytes in wire order,
with the first sampled bit in byte zero's least significant bit. It rejects
truncation, wrong byte order/magic/version and a nonzero reserved bit. This
utility decodes a capture; it does not communicate with fabricated hardware.

## Local verification

- Native IHP Verilog I/O models exercise all mapped signal pins, bidirectional
  release/readback, I2C open-drain behavior and an exact 192-bit MBIST frame.
  The core in this transport fixture is an explicitly labelled pin-stimulus
  stub, **not a CPU execution result**. Five wrapper mutations are rejected:
  I2C driving high, GPIO permanently enabled, an invalid input connection, a
  genuine two-lane permutation and exchanged expected/actual status words.
  Walking-one stimulus checks every input/output lane independently.
- Independent mailbox RTL tests exercise repeated frames, source changes before
  serial acknowledgement, stopped clocks, idle behavior, zero fill and POR.
  Five RTL mutations are rejected. Verilator reports no warnings for the mailbox.
- Yosys checks the shell with the real selected mapped SoC. Independent comparison
  preserves all 79 core ports and 76,248 core cell records/connections, and
  checks every core port and every native I/O instance at the new top level.
  This is structural linkage, not a complete gate-level chip simulation.
- The targeted Python/RTL/host-decoder and existing lint-contract campaign
  passes 31 tests. The final run also includes 121 documentation checks, for
  152 passing cases with no skips. Claims retain their distinct scopes.

## Native-cell physical candidate

`scripts/make_chip_io_floorplan.py` generates `nssoc_io_floorplan`: an initial
4,000 × 3,200 µm ring with the 106 signal/supply cells, four native corners and
native fillers. Filler dimensions come from LEF; their names are not lengths.
All 314 placements are checked for non-overlapping LEF footprints and die
containment. Each of 1,256 adjacent TopMetal1 supply-pin contacts is checked for
continuity and different-rail separation. A missing cell and a wrongly rotated
cell are rejected. GDS readback must reproduce every master, orientation and
coordinate exactly.

The first direct-abutment ring produced 82 native `Cnt.b` contact-spacing
markers at supply-cell boundaries. A native 1 µm filler after each signal/supply
cell removes those direct active-cell adjacencies while preserving all four
abstract supply rails. The new GDS passes all nine selected native contact
categories with zero markers. No foundry rule or native cell geometry was
modified. The original full FEOL/geometry run also exceeded its 3 GiB address
space limit in native angle processing; its partial report is not a pass.
A fresh all-main-rule run uses separately checked table groups and resource
admission for the larger angle job. Its completion is a separate required gate.

This GDS contains **only the I/O ring**. It excludes the digital core and new
serial logic, signal routes, completed bond pads/passivation/seal ring and
package. Abstract rail checks do not replace extracted supply connectivity,
ESD/latch-up analysis, IR/EM, native DRC or full-chip LVS. It is deliberately a
separate candidate from the concurrently running core timing layouts.

## Replay

Use the installed project toolchain and a pinned SG13G2 PDK. Choose fresh output
directories so failed and completed evidence is preserved.

```sh
python scripts/generate_chip_io.py --core-json SELECTED_CORE.json --output NEW_SHELL_DIR
python scripts/check_chip_io.py --pdk PINNED_PDK --output hw/soc/out/NEW_IO_TEST
hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage python scripts/make_chip_io_floorplan.py \
  --pdk PINNED_PDK --pads NEW_SHELL_DIR/pads.json --output NEW_RING_DIR
```

The shell's manifest hashes the core JSON, pin contract and generator. Local
reports must be tied to that exact core and the pinned native models. A modified
core or pad assignment requires a new structural, functional and physical run.
