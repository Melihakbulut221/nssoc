# Core-only chip I/O and MBIST status

This release excludes PCIe and Ethernet. The core-only I/O contract is bound to
the exact mapped JSON from successful producer 44238569057, commit
bfb1fcc1bcd1d2def770ac26bd978767b0466e32. Its retained ports were compared with
that actual mapping, not inferred only from the old RTL interface.

Generate the structural shell with `scripts/generate_chip_io.py --profile
core-only --core-json <authenticated-mapped-json> --output <new-directory>`.
The generator rejects a different mapped-source hash or mismatching port
signature. The default legacy profile remains available; its generated RTL
and pad inventory must remain byte-identical.

The shell preserves GPIO/QSPI bidirectional wiring, I2C open-drain controls,
SpaceWire, CAN, SPI, UART, watchdog and interrupt/status signals. No PCIe or
Ethernet port or Ethernet MBIST result is exposed in this release.

## Read-only status protocol, version 2

The frame remains 192 bits, shifted least-significant bit first. Request a fresh
snapshot, observe ready low then high, and sample data before each rising test
clock edge. The source holds an atomic snapshot across the handshake.

| Bits | Content |
|---|---|
| 0, 1, 2 | System MBIST busy, done, failed |
| 15:3 | First failing address |
| 79:16 | Expected data |
| 143:80 | Actual data |
| 146:144 | Phase |
| 154:147 | Background |
| 159:155 | Reserved, zero |
| 191:160 | Magic/version `0x4d420002` |

`sw/golden/chip_status.py` decodes versions 1 and 2, rejects unknown versions
and nonzero reserved bits, and returns Ethernet fields only for version 1.

## Qualification boundary

The cloud qualification authenticates the mapped source, checks legacy output
stability, and executes the real status-mailbox RTL through generated shell
wiring with explicit core and I/O-cell stubs. Those stubs do not validate
transistor pad behavior or the actual processor.

This is structural preparation. Whole-chip pad placement, supply/ESD design,
pad-cell LVS, package choice, and routed chip timing remain open. The serializer
adds a separate test clock and bundled-data CDC constraints; the core-only
single-clock CTS result must not be reused as whole-chip timing acceptance.

## Observed cloud result, 2026-11-18

[Qualification run 44245032516](https://github.com/Melihakbulut221/nssoc/actions/runs/44245032516)
passed at d3db62865a2fcb8dcb35b4a7bdf5956d5c73eb57: 19 tests, no skips or
failures. This includes the generated core-only shell serial-frame simulation,
legacy mailbox fault controls, versioned host decoding, malformed contract
rejections and an altered mapped-source rejection. The legacy generated RTL
and pad inventory remain byte-identical.

The selected shell contains 76 signal pads and four supply pads. This is an
inventory, not power-integrity, ESD, package or physical acceptance. The new
test uses explicit core/I/O-cell stubs and the real status-mailbox RTL.

Artifact 14400854380 SHA256:
85ce7d5ab1218a14df2458e8e76abca0837410dee9a9bd63ece3f286d50386f8.
All inner file hashes and the 19 JUnit case results were independently checked.
The evidence manifest is in
[core-only-io-qualification-20261118.json](evidence/core-only-io-qualification-20261118.json).
