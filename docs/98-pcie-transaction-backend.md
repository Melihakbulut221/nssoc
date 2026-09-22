# 98 — PCIe transaction-layer register backend
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

22 September 2026. The requested Gen3 x4 link remains open. This is the
first project-authored digital block toward it, not a complete PCIe controller,
PIPE implementation, PHY, enumerated device or layout. It is deliberately
listed in `hw/known-unbuilt.txt`: no instance is connected to `soc_top` yet.
The existing full-core physical run therefore does not contain this block.

## Implemented boundary

[`soc_pcie_tlp_regs.v`](../hw/soc/rtl/pcie/soc_pcie_tlp_regs.v) accepts one
**complete transaction descriptor** on valid/ready. Header DWORD 0 occupies
bits 127:96, then DWORDs 1, 2 and 3 in descending order. A separate 32-bit
payload uses the local APB byte-lane order. `rx_payload_dw_i` must contain the
actual received payload length, independently measured by an upstream packet
assembler. It is not sufficient to copy the header's Length field into it.
There are no serial, lane, SOP/EOP or CRC inputs here.

Upstream logic must delimit and validate the complete packet, reject bad
LCRC/ECRC, enforce routing/flow control, retain ordering and supply the assigned
bus/device/function ID. These upstream requirements are not implemented by
this backend. The interface is **not PIPE**. All ports use one clock; any
clock-domain adapter must be separately implemented and verified.

| Operation | Implemented behavior |
|---|---|
| Type-0 configuration | Single-function ID match; parameterized vendor/device ID readback; writable memory-space-enable bit; 32-bit, non-prefetchable, 4 KiB BAR0 with size probing and byte-enabled writes. Other configuration fields return zero. |
| Memory read/write | One DWORD, 3-DW or 4-DW header; a 4-DW address must have a zero high DWORD for this 32-bit BAR. Address must fall inside enabled BAR0. Last BE must be zero. |
| Local register access | APB address is the 12-bit BAR offset; writes preserve First BE as strobes. Read strobes are zero. Setup/access phases and transaction fields are held through wait states. |
| Completion | Read data, captured requester/completer IDs, eight-bit tag, lower address and requested byte span. Configuration writes receive a no-data completion; memory writes are posted and receive none. |
| Zero-length memory operation | Length is one DWORD with First/Last BE zero. No local bus side effect; reads return a dummy DWORD with **Byte Count 1**, writes do nothing. Encoded Length zero instead means 1024 DWORDs and is unsupported. |
| Unsupported request | Supported-format non-posted requests outside the aperture or subset receive UR; posted requests report a local error without a completion. |
| Malformed/unsupported descriptor | Payload-count mismatch, poison, digest, nonzero TC/attributes, hints, translation and unsupported format are reported and dropped before APB. Incoming completions/messages are not answered with another completion. |
| APB error/timeout | Read returns CA, posted write reports a local error. No automatic retry or rollback; a timed-out peripheral write may already have had a side effect. Peripheral-specific abort/reset handling remains an integration requirement. |
| Reset | Aborts local pending response/access and clears BAR/memory enable. This is a reset input, not implementation of hot reset or FLR. |

The default vendor ID is `ffff`, deliberately indicating no assigned product
identity. The test fixture uses `1234:5678` only for simulation. Neither is a
PCI-SIG vendor allocation. No capability chain, PCIe capability, negotiated
speed/width, bus mastering, MSI/MSI-X, PM or AER register is advertised.
`error_o` is a local pulse, not an AER message or a persistent error counter.
Configuration access tests do not establish successful host enumeration.

## Verification and the corrected first attempt

[The measured record](evidence/pcie-transaction-backend-20260922.json) binds
source hashes, commands and outputs. The descriptor test covers all sixteen
First BE patterns with both header widths, distinct tags/requesters, BAR
probing/reprogramming, reserved configuration writes, malformed and unsupported
requests, APB errors, randomized wait/response stalls and reset in every phase.
The same six tests pass at timeout settings 1, 8 and the default 256 cycles.

Two additional tests connect the backend to the **unmodified SoC GPIO RTL**.
TLP writes drive its output/direction pins; reads return actual GPIO state.
That fixture blocks partial writes before its APB3 slave because the slave
has no byte-strobe input. Connecting an APB4 master to an APB3 slave without
this check would silently convert a byte write into a full-word write. This
fixture is a block integration test, not a modification of the product top.

Port-only formal assertions check response stability under backpressure, APB
setup/access stability, decode/enable guards, requester/completer/tag retention
and bounded APB waiting. The eight-cycle formal instance passes depth-24 BMC,
unbounded PDR and all five reachability covers. The default timeout has
simulation coverage; no proof at a different parameter is attributed to it.
Five scratch-copy mutations (BAR decode, byte strobes, abort status, completion
tag and zero-length byte count) each produce a functional assertion failure;
compilation failure or missing XML is not accepted as a detected defect.
The mapped default-parameter implementation uses 916 IHP cells with a Liberty
cell-area sum of 19,426.743 square micrometres. All six descriptor tests also
pass on the unmodified IHP cell models at the default 256-cycle timeout, with
Icarus 14 and specify support enabled. This is functional gate simulation,
without SDF or placement. Icarus 12 left delayed timing inputs unknown and
failed; no cell-model patch or X masking was used.

The regular cocotb discovery, complete SoC formal target and hosted RTL job
include the new suites/obligations. The separate `pcie-transaction` workflow
repeats the controls, GPIO fixture, formal tasks and native-cell replay using
checksum-verified IHP library files. The first hosted run failed before simulation because the OSS CAD Suite
launcher replaced the embedded Python search path. Both PCIe Makefiles now
preserve the interpreter selected by cocotb. The same clean-environment
failure was reproduced locally, then all 18 descriptor executions, five
mutation controls, two GPIO tests and six native tests passed with the fix.
[The portability record](evidence/pcie-runtime-portability-20260922.json)
preserves the failed hosted artifact and the new source-bound local results.
The corrected hosted replay is pending; configuration is not a hosted PASS.

The initial local tests also expected an incorrect four-byte count for a
zero-length read. Independent review against the
[AMD PG156 completion descriptor](https://docs.amd.com/api/khub/documents/i5H6gUtR_mD96EDqiB2hvg/content)
identified the required one-byte count with one dummy DWORD. Both RTL and the
oracle were corrected; the fifth mutation preserves this regression. Initial
logs remain historical and do not establish protocol correctness. The first
256-cycle test also exposed an overly short *testbench* wait budget, which was
corrected before accepting that parameter run. An initial formal invocation
used the wrong working directory and produced no proof; its log is retained.

Header and completion field placement were cross-checked against the
[public transaction-layer implementation](https://github.com/alexforencich/verilog-pcie/blob/25156a9a162c41c60f11f41590c7d006d015ae5a/rtl/pcie_axil_master_minimal.v).
This is a format reference, not an imported controller or a compliance oracle.
No external PCIe core is instantiated. Normative PCI-SIG conformance review
and an independent protocol verification environment remain required.

```sh
# Two discoverable block suites; the runner separately reports unrelated skips.
scripts/run_cocotb.sh soc_pcie
# Three timeout baselines and five expected functional failures; fresh output.
python3 scripts/check_pcie_tlp_controls.py --out hw/soc/out/pcie-controls-new
# BMC, unbounded proof, covers (use the pinned OSS CAD Suite).
make -C hw/soc/formal pcietlp
# IHP mapping and native-model replay; provide the pinned PDK files.
python3 scripts/check_pcie_tlp_native.py --out hw/soc/out/pcie-native-new \
  --yosys /absolute/oss-cad-suite/bin/yosys \
  --iverilog-dir /absolute/oss-cad-suite/bin \
  --liberty /absolute/sg13g2_stdcell_typ_1p20V_25C.lib \
  --models /absolute/sg13g2_stdcell.v
```

## Remaining implementation

The next digital boundaries are complete packet assembly/validation, full
Endpoint configuration/capabilities, multi-DWORD transfer/completion handling,
interrupts, DLL sequence/ACK/NAK/replay and credit flow control, and PHY-side
LTSSM/training/Gen3 encoding/equalization/lane alignment. Root Port behavior
is also absent. Host access policy, arbitration, CDC/reset and protection must
be implemented before connecting a host master to the SoC fabric.

A real four-lane 8 GT/s PHY still requires analog TX/RX, clock generation and
recovery, termination/equalization, receiver detection and electrical models,
followed by process-specific layout, extraction/PVT and channel validation.
This block supplies none of these and no serial link-up is generated. The
[PCIe feasibility record](91-pcie-gen3-feasibility.md) and
[product gate](92-product-acceptance.md) remain OPEN. Neither this generic
synthesis nor the unrelated current-full PNR run is a PCIe layout result.
