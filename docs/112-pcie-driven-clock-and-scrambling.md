# 112 — Driven clock macro, extraction controls and payload scrambling
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured progress — 4 October 2026

This step addresses the measured clock-load failure in [document 111](111-pcie-clock-path-and-gearbox.md).
A stronger, real HBT output stage now drives the selected load cases; its actual
standalone GDS and LEF pass native physical controls. A separate four-lane
scrambler adds payload processing. These components advance the open GR801-class
SoC objective. They do not establish a working Gen3 x4 serial link or main-chip
physical integration.

Sources and compact native captures are frozen at
`ec67512edcf89b5cc42c0cd90b87e99e60eed2c3`. The
[root review](https://github.com/Melihakbulut221/nssoc/blob/ec67512edcf89b5cc42c0cd90b87e99e60eed2c3/hw/soc/pcie-evidence/20261004-phy-clock/root-review.json)
rehashes the source pins and every listed member of four captures, and records
98 focused tests. Native campaign results below have distinct scopes; their
counts must not be summed into a product coverage claim.

## Actual clock drive and its remaining limits

`clock_vco_hbt_v3.spice` has 30 HBT instances. Each differential output uses four
parallel Nx4 followers and four Nx2 sinks. Every primitive retains a legal native
Nx value. The previous oscillator and limiter are unchanged. The nominal
opposed-equivalent load of approximately 0.907/0.923 pF now measures 8.05419 GHz,
0.48353 V peak differential swing, 1.24878 V common mode and 89.54 mW. The original
single branch measured only about 0.10056 V under that load.

The selected union of 55 positive corner/load cases passes the unchanged
screens. Four genuine functional faults reject, and two half-time-step controls
pass. The minimum passing VCE is 0.412805 V; the maximum is **1.596854 V**, leaving
only **3.146 mV** to the unchanged 1.6 V ceiling. That small observed margin is
not an adequate fabrication qualification. Earlier four/six-branch candidates
and their voltage failures remain recorded. No all-PVT 8 GHz frequency,
steady-state thermal, phase-noise, jitter, BER or PLL claim follows.

The campaign initially exhausted storage. Forty-five complete, pinned records
were recovered verbatim; a partial waveform was rejected. Only the ten missing
cases were rerun, and the disjoint union was checked. The
[driver summary](https://github.com/Melihakbulut221/nssoc/blob/ec67512edcf89b5cc42c0cd90b87e99e60eed2c3/hw/soc/pcie-evidence/20261004-phy-clock/driver-summary.json),
[independent review](https://github.com/Melihakbulut221/nssoc/blob/ec67512edcf89b5cc42c0cd90b87e99e60eed2c3/hw/soc/pcie-evidence/20261004-phy-clock/driver-peer.json)
and [full-wave release receipt](https://github.com/Melihakbulut221/nssoc/blob/ec67512edcf89b5cc42c0cd90b87e99e60eed2c3/hw/soc/pcie-evidence/20261004-phy-clock/driver-release.json)
preserve this distinction. The peer reparsed 19 retained waves; it did not
independently remeasure every positive waveform.

The real standalone macro measures 1880 × 277.03 µm. Main DRC reports zero
violations in 560 categories. Strict deep and flat transistor LVS match;
independent expansion checks retain all 30 HBTs despite four native m=4 combined
records. Twelve finite substrate taps and one well tap remain, with distinct
body and external-return nets. Six-port LEF validation also checks that pin
access does not overlap obstructions. Seventeen actual reference/geometry/LEF
faults are rejected. A first follower-open mutation missed the translated route;
that failed control remains preserved, and the corrected physical cut was
rerun. See the [layout report](https://github.com/Melihakbulut221/nssoc/blob/ec67512edcf89b5cc42c0cd90b87e99e60eed2c3/hw/soc/pcie-evidence/20261004-phy-clock/vco-layout.json)
and [native GDS/LEF capture](https://github.com/Melihakbulut221/nssoc/blob/ec67512edcf89b5cc42c0cd90b87e99e60eed2c3/hw/soc/pcie-evidence/20261004-phy-clock/vco-layout.tar.xz).
This is a separate macro, without extracted RF performance or pad integration.

## Extraction repair with a bounded physical contract

A private Magic patch and project technology overlay correct the emitter-contact
recognition and per-tile terminal-search orientation defects. All 24 native HBT
fixtures now have the expected collector/base/emitter mapping. Sixteen nonunity
Nx devices still lose multiplicity in native Magic extraction, so native full
HBT PEX remains rejected.

A separately checked hybrid fixture retains devices from strict native KLayout
LVS and extracts only identical copied Metal1/Via1/Metal2 routes. It has 73
independent conductors, 146 terminal anchors, 73 positive resistance paths and
a conserved 73 × 73 capacitance matrix. The finite substrate tap is retained;
external SUB is not silently shorted to the device body. Five real geometry
faults reject while an unchanged clone passes. Initial flattened controls that
confounded rotated device dimensions remain preserved. The
[hybrid report and exclusions](https://github.com/Melihakbulut221/nssoc/blob/ec67512edcf89b5cc42c0cd90b87e99e60eed2c3/hw/soc/pcie-evidence/20261004-phy-clock/hbt-hybrid.json)
do not qualify device-metal capacitance, distributed intrinsic terminals,
substrate spreading or RF parasitics. The installed PDK and original runtime are
unchanged.

## Four-lane payload scrambler

The new synthesizable module processes 32 payload bits on each of four logical
lanes with distinct seeds. Explicit per-byte advance/XOR masks and after-word
reseed events preserve caller ownership of ordered-set policy. State changes
only on accepted input; stalls hold the output, and reset/flush clear it and
reseed all lanes. Headers are outside this interface. The XOR transform also
supports descrambling when the caller supplies the correct receive policy.

Three RTL cases and the same three native TT-cell cases pass without skips at
a 4 ns testbench clock. The mapped module has 2,627 IHP cells. An independent
bit-cell recurrence, eight published lane-zero state anchors, per-lane queues,
mixed byte controls, stalls and resets check actual ports. Seven source mutations
fail. See the [source-bound scrambler capture](https://github.com/Melihakbulut221/nssoc/blob/ec67512edcf89b5cc42c0cd90b87e99e60eed2c3/hw/soc/pcie-evidence/20261004-phy-clock/scrambler.json).
Cell simulation without extracted interconnect/SDF is not physical 250 MHz
closure. Ordered-set classification, training-sequence DC balance, block
alignment, lane assignment/deskew and LTSSM are still separate work.

The polynomial and transport context were checked against Intel's
[Stratix V transceiver handbook](https://www.intel.com/programmable/technical-pdfs/683779.pdf).
Seeds and byte-control rules were checked against the PCI-SIG Base Specification,
section 4.2.2.4, available through a [document mirror](https://studylib.net/doc/28447088/pcie-v4.0).
No third-party scrambler implementation was copied.

Coarse tuning, cascaded real feedback division, closed PLL/CDR, complete
SERDES/PCS/LTSSM, qualified parasitics/ESD and main-chip clock/reset/CDC/pad
integration remain open. Fresh whole-chip timing, LVS and manufacturing gates
must follow their actual integration. Progress captures do not override those
gates or the previous Ethernet/NPU timing failures.

The next actual clock/pad integration and its still-open timing/analog gates
are recorded in [document 113](113-pcie-clocked-pads-and-transport.md).
