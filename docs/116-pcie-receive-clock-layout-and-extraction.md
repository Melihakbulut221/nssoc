# 116 — PCIe receive framing, divider layout and extraction limits
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

The [next measured update](117-pcie-routed-receive-duplex-and-thermal.md) records subsequent RX, duplex, compact-clock and extraction work; this snapshot remains historical.

## Measured progress — 4 October 2026

The new RX packet framer passes actual native-cell tests, the combined TX path
also passes native replay, and the VCO/divide-by-four circuit now has its own
routed layout with passing transistor connectivity checks. **Complete Gen3 x4,
qualified parasitics/ESD and main-chip physical integration remain open.**
[Document 115](115-pcie-framing-and-native-bank.md) retains the preceding TX and
analog-bank measurements.

Source commit `d6df7838f52f3a80690942b608f6a66756823dab` contains these changes.
The [root verification record](https://github.com/Melihakbulut221/nssoc/blob/d6df7838f52f3a80690942b608f6a66756823dab/hw/soc/pcie-evidence/20261004-receive-and-clock-layout/root-verification.json)
records 95 passing tests with no skips, exact source and evidence identities,
and the retained earlier environment failure. Workflow schema, source whitespace,
SPDX and REUSE checks pass; raw logs retain their original whitespace.

## Real active-stream receive framing

`soc_pcie_gen3_framer_rx` accepts already aligned, deskewed and descrambled
four-lane Data Blocks. It checks all four sync headers, STP length/CRC4/parity,
normal TLP header length, and STP/SDP/IDL/EDS/EDB token placement. A TLP stays
quarantined until its immediate successor establishes whether it is nullified.
EDB discards the packet and reports its sequence; a valid successor is retained
and processed after the complete packet is delivered. Malformed framing halts
the stream until an explicit new stream start. Output backpressure and idle
intervals do not invent an elapsed packet timeout.

| Executed configuration | RTL cases | Native cases | Native cells |
|---|---:|---:|---:|
| Default 150-byte RX buffer | 6 | 6 | 12,376 |
| Maximum 4,118-byte RX buffer | 6 | Not executed | Not measured |
| Combined TX framer and frozen TXv3 transport | 2, previously recorded | 2 | 23,025 |

The [RX record and original controls](https://github.com/Melihakbulut221/nssoc/blob/d6df7838f52f3a80690942b608f6a66756823dab/hw/soc/pcie-evidence/20261004-receive-and-clock-layout/receive-framing.json),
[native RX capture](https://github.com/Melihakbulut221/nssoc/blob/d6df7838f52f3a80690942b608f6a66756823dab/hw/soc/pcie-evidence/20261004-receive-and-clock-layout/receive-native.tar.xz)
and [combined native TX capture](https://github.com/Melihakbulut221/nssoc/blob/d6df7838f52f3a80690942b608f6a66756823dab/hw/soc/pcie-evidence/20261004-receive-and-clock-layout/combined-tx-native.tar.xz)
retain actual inputs, full logs and results. Fifteen actual RX HDL faults and two
capacity guards are rejected. A separate reusable native launcher repeats the
same 12,376-cell mapping and six cases, with six cell-inventory controls; this
is a repeated verification, not six additional protocol cases.

The external stream owner still supplies training/Ordered Set handling. LCRC
and DLLP CRC16 checks belong to the downstream packet layer. These byte-buffered,
backpressured interfaces do not establish continuous PMA ingress or saturated
Gen3 x4 throughput. They are not a complete PCS/LTSSM or a serial main-chip link.

## Actual divide-by-four physical circuit

The layout instantiates the frozen VCOv3 and divide-by-four v5 circuit:
64 HBTs, 42 physical resistors, 12 MIM capacitors and one HV PMOS, plus 30 finite
substrate contacts and one finite well contact. Both independent supply rails,
all clock terminals and all native device masks are retained.

The [native physical package](https://github.com/Melihakbulut221/nssoc/blob/d6df7838f52f3a80690942b608f6a66756823dab/hw/soc/pcie-evidence/20261004-receive-and-clock-layout/div4-v5-layout.tar.xz)
passes all 560 main DRC categories with zero markers and strict deep/flat LVS
with 109 compared records after device combination. Fifteen actual negative
controls are rejected. Reinstantiation checks all 150 primitive/tap geometries
with zero layer XOR; all nine ports and seven metal obstruction layers are
verified. The [independent review](https://github.com/Melihakbulut221/nssoc/blob/d6df7838f52f3a80690942b608f6a66756823dab/hw/soc/pcie-evidence/20261004-receive-and-clock-layout/div4-v5-peer.json)
rechecks the complete source topology and every capsule member. The initial
four TopMetal1 area failures and their real connection-strap repair are retained.

This first layout is **4,800 × 607.03 µm**. Its long routes require compact
placement and extracted clock/load analysis. Passing geometry and LVS do not
establish post-layout 8 GHz operation, divide-by-four performance, PLL lock or
main-chip integration. Earlier transistor-level simulations remain separate.

## Complete-bank C accounting and the remaining native crash

The unchanged 351-device bank now also passes complete native capacitance
accounting: all 1,539 exported capacitors participate in the 210-node,
44,100-entry matrix comparison. The separately named `ESD_RETURN` reference,
finite contacts and floating annotations remain explicit. The frozen native
serialization tolerance is unchanged. This verifies consistent export of the
model, not absolute RF capacitance or qualified resistance.

The [bank evidence and failures](https://github.com/Melihakbulut221/nssoc/blob/d6df7838f52f3a80690942b608f6a66756823dab/hw/soc/pcie-evidence/20261004-receive-and-clock-layout/bank-conservation.tar.xz)
retain the four import/export command-state experiments. GDS export before
extraction can leave state that omits 81 resistors; an explicit native
`extract unique all` restores the complete baseline. Both complete baselines
pass C accounting. All seven imported routing-metal unions and six reconstructed
via-cut layers match; reconstructed base-contact geometry is still missing
119.168 µm². The separate RX study similarly distinguishes exact merged metal
geometry from internal off-grid edges and incomplete base-contact reconstruction.

Unreduced resistance extraction still crashes, including on either polarity of
one unchanged native ESD PCell. The native backtrace identifies a substrate-slot
access for further private-runtime investigation. The 24-HBT trial exits zero
but reports missing terminal connections and is also rejected. No crash,
partial output or zero exit with missing devices is accepted as a PEX result.

## Verification portability and work continuing

Hosted TX-framer positive RTL and native tests passed, but 13 mutation tests
failed before HDL execution because their local checkout path to Icarus did not
exist on the runner. The tests now select installed executable tools from PATH.
[Actual independent replay](https://github.com/Melihakbulut221/nssoc/blob/d6df7838f52f3a80690942b608f6a66756823dab/hw/soc/pcie-evidence/20261004-receive-and-clock-layout/tool-discovery.json)
passes all 32 TX/RX mutation and capacity controls using external Icarus 12;
root replay using Icarus 14 also passes all 32. Original test bytes, hosted launch
failures and the root's initial Python-environment failure remain available.
CI now includes native combined TX and RX replay plus maximum-buffer RX RTL.
Hosted completion must be checked separately from local results.

Standalone physical TX routing and the two-case long thermal campaign are ongoing.
RX timing repair, true duplex transport, compact clock routing and the native
resistance crash are active development tasks. Full PLL/CDR, SERDES/PCS/LTSSM,
qualified RC/ESD, final chip timing, pad/DFT integration and manufacturer
approval remain explicit gates.
