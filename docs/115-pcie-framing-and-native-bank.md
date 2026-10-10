# 115 — PCIe packet framing and complete native bank connectivity
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

The subsequent [receive, divider-layout and extraction record](116-pcie-receive-clock-layout-and-extraction.md) adds native RX/combined TX and complete-bank C accounting.

## Measured progress — 4 October 2026

The unchanged padded analog bank now passes a complete intrinsic-device graph
comparison in the corrected private Magic flow. All 351 devices and 56 ports
participate. A new Gen3 TX packet framer also passes real RTL and native-cell
tests. **Full PCIe Gen3 x4, qualified parasitics/ESD and main-chip physical
integration remain open.** Earlier failed results remain in
[document 114](114-pcie-timing-divider-and-native-taps.md).

Sources and compact measurements are pinned to
`a04825b89e007849fc57d376522b11ba28239a70`. The
[root verification receipt](https://github.com/Melihakbulut221/nssoc/blob/a04825b89e007849fc57d376522b11ba28239a70/hw/soc/pcie-evidence/20261004-framing-and-native-bank/root-verification.json)
records 186 passing root tests, zero failures/skips, and exact source/capsule
identities. Workflow schema, SPDX and REUSE checks pass. Hosted results are
separate from these local checks; the new framer is added to the native CI matrix.

## Active-stream TX packet framing

`soc_pcie_gen3_framer_tx` buffers a complete encoded packet, validates normal
3DW/4DW TLP header length and digest accounting, constructs STP or SDP, and
stripes bytes across four 128-bit lane payloads. It emits registered Data Blocks
with header `10`, holds them under backpressure, and fills unused symbols with
IDL. A standalone STP primitive computes the 11-bit length field, CRC4 and parity.
The independent serial polynomial oracle covers all 2,048 length encodings and
three sequence patterns: 6,144 actual port vectors. Primitive encoding tests
include reserved lengths; the packet framer separately rejects invalid packets.

The caller supplies the two-byte sequence prefix and all TLP/LCRC bytes, or the
six DLLP bytes including CRC16. The nullify flag appends EDB after the complete
TLP; it never silently rewrites LCRC. A new optional wrapper connects this framer
to the existing scrambled, pipelined TXv3 gearbox. It does not initialize a Link,
schedule Ordered Sets/SKP or implement PMA clocking.

| Executed configuration | RTL cases | Native-cell cases | Native cells |
|---|---:|---:|---:|
| STP primitive | 1 / 6,144 vectors | 1 / 6,144 vectors | 29 |
| Default 150-byte packet buffer | 4 | 4 | 10,935 |
| Maximum 4,118-byte packet buffer | 4 | Not executed | Not measured |
| Framer plus frozen TXv3 transport | 2 | Not executed | Not measured |

Thirteen actual HDL faults are rejected; two CLI capacity guards also pass.
The [framer receipt](https://github.com/Melihakbulut221/nssoc/blob/a04825b89e007849fc57d376522b11ba28239a70/hw/soc/pcie-evidence/20261004-framing-and-native-bank/framer-tx.json)
and [170-member native capture](https://github.com/Melihakbulut221/nssoc/blob/a04825b89e007849fc57d376522b11ba28239a70/hw/soc/pcie-evidence/20261004-framing-and-native-bank/framer-tx.tar.xz)
preserve source, simulator and library identities. The input is one byte per
clock and packets are buffered individually; this does not establish saturated
Gen3 x4 packet throughput. Capacity 4,118 excludes the 4,122-byte combination of
4,096-byte payload, 4DW header, Digest, sequence prefix and LCRC. TLP Prefix/PMUX,
receive framing, complete PCS/LTSSM and new-framer physical timing remain separate.

## Native ESD and pad connectivity repair

The first correction restores geometry-based recognition of the ordinary 2-kV
ESD PCell family. A private Magic build adds the existing interaction operator
to GDS import and repairs its marked-region copy traversal. Exact semiconductor
mask controls and measured emitter geometry limit recognition to the tested
family. All 32 fixture devices retain ordered supply, pad and substrate terminals.
Eight actual geometry faults exercise omissions, opens, shorts and unsupported
geometry. KLayout's normalized width comparison alone misses the width faults;
the native emitter measurement detects them. Neither result is described as
ESD pulse, current-density or reliability qualification.

The complete bank then recovered all devices but still had 16 disconnected
serial ports. A real pad/via fixture identifies the cause: the Metal6/Metal7
paint rules incorrectly referenced the Metal5 no-fill obstruction. A separate
two-line technology overlay uses each metal's own obstruction plane. It restores
exactly 16 pad-to-core conductor pairs across both route families and all eight
orientations. Both native engines check the intended partitions and five actual
missing-via, open, wrong-layer and short controls. The original GDS, installed
PDK and runtime are unchanged.

The final bank contains 122 HBTs, 108 finite substrate contacts, one well contact,
57 rppd resistors, 24 rsil resistors, six MIM capacitors, one HV PMOS and 32 ESD
devices. The complete graph has 1,541 vertices and 2,122 edges. All 56 external
ports are fixed; only internal net names are matched existentially. All 108
`SUB`–`ESD_RETURN` contacts retain distinct nodes and the native 81.6667 Ω value.
The PMOS body remains connected through its finite well contact.

The [complete-bank receipt](https://github.com/Melihakbulut221/nssoc/blob/a04825b89e007849fc57d376522b11ba28239a70/hw/soc/pcie-evidence/20261004-framing-and-native-bank/bank-native-graph.json)
and [independent root bijection check](https://github.com/Melihakbulut221/nssoc/blob/a04825b89e007849fc57d376522b11ba28239a70/hw/soc/pcie-evidence/20261004-framing-and-native-bank/bank-root-bijection.json)
verify every normalized exact-valued device color and edge. Six whole-graph
faults are rejected. A preliminary comparison falsely distinguished equivalent
Decimal spellings; its failure is retained alongside the corrected numeric
comparison. No topology tolerance, omitted device, blackbox or reference-net
union is used. ESD emitter annotations and extra PMOS diffusion annotations have
explicit connectivity-only normalization; their parasitic accuracy is not claimed.

This closes the complete intrinsic-device connectivity comparison for this
unchanged analog bank. Raw capacitances, import geometry fidelity, RF behavior,
ESD stress and the older full-chip I/O LVS gate require their own verification.

## Physical TX function proof and RC limits

The repaired standalone TXv3 netlist from document 114 now has a
[native-Liberty function proof](https://github.com/Melihakbulut221/nssoc/blob/a04825b89e007849fc57d376522b11ba28239a70/hw/soc/pcie-evidence/20261004-framing-and-native-bank/tx-v3-function-equivalence.json):
all 6,604 state/output boundaries match, including D/clock/reset functions for
2,158 flip-flops. Exact Boolean DAG tuples establish equality without hash-based
decisions, unknown functions, blackboxes or omitted boundaries. Nine graph-level
counterexamples test the checker; these are not nine resynthesized faulty chips.
The proof concerns binary functional behavior, not four-state timing equivalence.
Actual detailed routing is running separately from the positive global-route
estimated timing; no final routed setup/hold result is available here.

A [small native wire contract](https://github.com/Melihakbulut221/nssoc/blob/a04825b89e007849fc57d376522b11ba28239a70/hw/soc/pcie-evidence/20261004-framing-and-native-bank/openrcx-wire-contract.json)
checks 14 isolated wires on all seven routing metals, legal DEF-unit scaling,
and actual shortened/disconnected geometry controls. The model's resistance
uses process target sheet values while LEF uses sheet maxima. OpenRCX also
includes the route rectangle's half-width end extensions. These conventions
explain the measured resistance difference without a fitted correction factor.

For two parallel 100 µm Metal2 wires, the 0.22 µm edge gap exports 11.1099 fF
mutual capacitance. At 2.0 µm gap the native result exports zero mutual coupling
and fails the positive-coupling check. The pinned rule table already contains
these wider-gap zeros; extraction used zero coupling threshold. The current
[upstream rule file](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/5e6d592e4002946a4616f798c357f0f3c06cf3b6/ihp-sg13g2/libs.tech/librelane/openrcx/IHP_rcx_patterns.rules)
is byte-identical. This exposes model limitations, not a qualified replacement
RC model. Independent finite field-solver comparisons are ongoing; nominal
export consistency does not establish absolute capacitance or RC corners.

## Long thermal capture is running

A versioned FIFO producer now owns both the native simulator and publication
process groups. Healthy runs have no elapsed timeout. On actual failure or
cancellation it terminates and reaps both groups, including descendants whose
leader already exited. Twelve independent lifecycle tests and a complete
12 ns native replay pass; all 4,009,837 scalar values remain available. The
[source/native control archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/clock-trim-longstream-v2-source-native-controls.tar.xz)
has authenticated and public whole-file hash verification.

The two 1 µs cold-start cases started locally on 4 October. The
[startup/progress receipt](https://github.com/Melihakbulut221/nssoc/blob/a04825b89e007849fc57d376522b11ba28239a70/hw/soc/pcie-evidence/20261004-framing-and-native-bank/longstream-started.json)
records the first complete published part. Every sample is retained, with a
bounded single-part queue; backpressure pauses the producer during compression
and verified publication. The earlier 40 ns thermal failures remain unchanged.
The initial test suite's immediate-kernel-state race is preserved and corrected
with identity, bounded stop observation and an actual late-write deadline check;
all 54 active stream tests now run without deselection and pass.

Full oscillator convergence, PLL/CDR lock and jitter, complete SERDES/PCS/LTSSM,
qualified PEX/ESD, final chip timing, pad/DFT integration and manufacturer
approval remain open. None of the running or isolated measurements is promoted
to whole-product acceptance.
