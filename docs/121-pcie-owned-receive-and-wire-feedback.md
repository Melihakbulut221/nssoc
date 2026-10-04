# 121 — PCIe packet ownership and actual wire feedback
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured development — 4 October 2026

The receive path now retains packet ownership through independent descriptor
and body handshakes. Raw lane alignment has native-cell tests, and the earlier
CRC-capable wide receiver passes all twelve native cases. Detailed RX and TX
routing completed without router DRC errors, but actual nominal wire extraction
exposes remaining setup and hold failures. The local VCO layout improves wire
transfer while still failing its original 0.85 V powered experiment.

**Full Gen3 x4, PLL lock/CDR, complete SERDES/PCS/LTSSM, qualified RC/ESD,
main-chip physical integration and production approval remain open.**

Source commit `a26c53632d8e5abf93d5328943c00cf366103750` binds the
[root verification record](https://github.com/Melihakbulut221/nssoc/blob/a26c53632d8e5abf93d5328943c00cf366103750/hw/soc/pcie-evidence/20261004-owned-receive-and-wire-feedback/root-verification.json):
**198 distinct focused pytest checks passed** in seven root-run groups.
An earlier 39-test compilation failure is preserved separately, together with
the correction and rerun. Native simulations, proof controls and agent checks
are separate evidence and are not added to that count.
[Document 120](120-pcie-feedback-loop-and-wide-receive.md) retains the preceding
source-bound snapshot.

## Packet ownership and lane alignment

The owned receiver emits up to four ordered descriptors per clock. Its 32
physical ownership slots use six-bit identifiers with a generation bit and a
16-bit epoch. A valid packet releases its owner only after both its descriptor
and final body beat are accepted. Bad or nullified packets still require their
descriptor handshake. The read pointer advances on accepted body data, so a
held output beat cannot be overwritten by wrapped ring storage.

Two packet-capacity profiles exercise twenty actual RTL port cases each;
37 HDL mutations and a real process-termination control exercise the checker.
This owned path is **RTL-tested, not yet a native-cell physical result**.
Icarus 14 rejected an initialized wire used before declaration: the original
39 failed tests and exact old source remain archived. Moving six declaration
lines fixes both the original v1 interface and the separately named v2.
A source bridge checks the exact permitted change. The root rerun passes all
40 v1 controls and both bridge/v2-lifecycle checks. See the
[source revision record](https://github.com/Melihakbulut221/nssoc/blob/a26c53632d8e5abf93d5328943c00cf366103750/hw/soc/pcie-evidence/20261004-owned-receive-and-wire-feedback/owned-portability-summary.json)
and [public capture receipt](https://github.com/Melihakbulut221/nssoc/blob/a26c53632d8e5abf93d5328943c00cf366103750/hw/soc/pcie-evidence/20261004-owned-receive-and-wire-feedback/owned-release.json).

The separate lane aligner searches EIEOS while BlockAlignControl is asserted,
converts raw 32-bit slices to 130-bit blocks, and rejects invalid sync headers.
Its seven positive and twelve actual native-cell fault cases pass across the
original run and a recorded continuation: **3,397 IHP cells** in the baseline.
All 32 bit phases, gaps and lock loss are exercised. The initial interrupted
wrapper remains recorded; a separate lifecycle correction terminates and reaps
its real child processes. This does not implement variable SKP handling, lane
deskew, CDC, SDS or the complete PCS/LTSSM. The
[native union record](https://github.com/Melihakbulut221/nssoc/blob/a26c53632d8e5abf93d5328943c00cf366103750/hw/soc/pcie-evidence/20261004-owned-receive-and-wire-feedback/lane-alignment-native.json)
binds all runs and source revisions.

## CRC-capable native implementation and timing

The previously published integrity RTL maps structurally to **73,072 IHP
cells** and passes all twelve native port tests at the 150-byte profile.
Explicit XOR balancing maps the same RTL to **71,028 cells**. A native-cell
proof preserves every one of 8,426 register identities and compares all D,
clock and reset functions plus public outputs: 8,560 unconstrained inputs and
25,588 compared outputs. Full symbol lists match, and five separate boundary
faults are rejected. This is equivalence between two native implementations;
the second implementation does not have a separate twelve-case native replay.

Balancing improves slow-corner preplacement setup from **−23.828218 ns** to
**−10.986376 ns**, still failing at the unchanged 4 ns clock. The next critical
path runs through the ring read position and four ordered DWORD decisions.
The full native simulation, mappings, exact physical-import graph checks,
proof and early failures are available through the
[study receipt](https://github.com/Melihakbulut221/nssoc/blob/a26c53632d8e5abf93d5328943c00cf366103750/hw/soc/pcie-evidence/20261004-owned-receive-and-wire-feedback/integrity-study-release.json).

The separate byte RX prefetch v2 and TX v4 complete detailed routing with
**zero router DRC errors**. Their routed logical netlists are byte-identical to
the earlier proved netlists. Nominal OpenRCX extraction gives:

| Block | SS setup, ns | SS hold, ns | TT setup, ns | TT hold, ns | FF setup, ns | FF hold, ns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| RX prefetch v2 | −1.337970 | −0.084874 | +0.697838 | −0.016535 | +1.862821 | +0.033083 |
| TX v4 | −1.092813 | −0.039604 | +0.818086 | +0.024960 | +1.931556 | +0.067828 |

TX slow-corner recovery also fails at **−0.474642 ns**. The same nominal wire
model is used across the three cell corners; this is not qualified RC-corner
signoff. RX's 78 unannotated clock-load outputs all have zero connected loads,
as checked against the actual database. The clock, I/O delays, slews and loads
are unchanged. The preceding positive global-route estimates did not survive
detailed extraction. Full routed databases, SPEFs and methods are public in the
[RX receipt](https://github.com/Melihakbulut221/nssoc/blob/a26c53632d8e5abf93d5328943c00cf366103750/hw/soc/pcie-evidence/20261004-owned-receive-and-wire-feedback/rx-detailed-release.json)
and [TX receipt](https://github.com/Melihakbulut221/nssoc/blob/a26c53632d8e5abf93d5328943c00cf366103750/hw/soc/pcie-evidence/20261004-owned-receive-and-wire-feedback/tx-detailed-release.json).
Router DRC is not full foundry DRC/LVS. Subsequent timing repair remains active.

## Real wires, startup and preservation

The local VCO geometry retains all 62 original devices and thirteen finite
body contacts. It passes 560 main DRC categories, strict deep and flat LVS,
six LEF-port checks and nineteen rejected physical/reference faults.
Its complete development wire network contains **446 resistors and 488
capacitors**, with all 151 anchors connected and the full capacitance matrix
checked. Seventy-three native passive experiments show shorter stage routes:
collector-to-next-base resistance falls from 75.03–82.54 Ω to 42.91–53.06 Ω;
the measured conditional 8 GHz transfer rises from 0.836–0.937 to 0.9855–0.9939.

Nevertheless, the original 12 ns, 0.85 V comparison has **zero wired public
clock edges**, versus 48 intrinsic edges at 8.067168 GHz. All thirty HBT device
bounds pass their declared windows. Improved passive transfer and matching
LVS do not establish oscillation. The
[wired record](https://github.com/Melihakbulut221/nssoc/blob/a26c53632d8e5abf93d5328943c00cf366103750/hw/soc/pcie-evidence/20261004-owned-receive-and-wire-feedback/local-vco-wire.json)
binds full waveforms and all original failures. Lower-bias and further geometry
experiments continue separately.

A revised streaming runner preserves complete native PLL waveforms in verified
public parts while bounding scratch space. It fixes a completed-future race
and rejects the wrong Python/NumPy runtime before starting the simulator.
Original failures and real termination controls remain recorded. Two fresh
34 ns runs at 5 ps and 2.5 ps pass all 539 device screens; complete raw values
are replayed. Their feedback means are 97.803459 and 98.01714 MHz, which do not
establish lock or timestep convergence. The
[startup pair](https://github.com/Melihakbulut221/nssoc/blob/a26c53632d8e5abf93d5328943c00cf366103750/hw/soc/pcie-evidence/20261004-owned-receive-and-wire-feedback/pll-startup-stream.json)
is finite startup evidence. Longer acquisition and fixed frequency/phase gates
remain separate from these passed electrical screens.

All 121 earlier sampler waveforms are now losslessly preserved in eleven
verified public bundles, totaling **1,273,419,792 compressed source bytes**.
This is preservation of existing measurements, not 121 new passing runs.
Original warnings and model limitations remain in the
[preservation ledger](https://github.com/Melihakbulut221/nssoc/blob/a26c53632d8e5abf93d5328943c00cf366103750/hw/soc/pcie-evidence/20261004-owned-receive-and-wire-feedback/sampler-all121-wave-preservation.json).
