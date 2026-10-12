# 160 — Supported-device TX multiplexer and extracted layout
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

The replacement final 2:1 TX multiplexer uses separate native HBT instances
within the foundry's `Nx=1…10` range. It passes three schematic operating
points, independent signal/device checks and standalone layout verification.
**Full corner coverage and post-layout electrical acceptance remain open;
this is not a complete 32:1 serializer, Gen3 x4 PHY or main-chip integration.**
It supersedes the out-of-domain electrical results in
[the earlier experiment](159-pcie-native-tx-multiplexer.md).

## Circuit repair and measured conditions

The [new circuit](../hw/soc/analog/pcie/tx_mux2_hbt_passive_fast_v1.spice)
contains nineteen HBTs and eight native self-heating resistors. Each data
branch has three separate `Nx=8` devices. Each selector and the tail have two
`Nx=8` devices; the reference uses `Nx=1`. Passive resistor dividers replace
the previous emitter followers. The existing four-HBT TX stage connects
directly to the outputs, giving **23 HBTs** in the schematic simulation.

The fixture still uses externally synchronized two 4 Gb/s input streams and
a 4 GHz select, giving an 8 GT/s final-stage stream. Data common mode is now
**1.93 V**, with ±0.15 V levels; select common mode is **1.23 V**, with ±0.30 V
levels. These are explicit requirements on an **unimplemented upstream
driver**, not measured outputs from a complete serializer or PLL. Nominal
supplies remain 2.5/1.8 V, references 0.5/1.5 mA, source resistance 25 Ω and
load 100 Ω differential plus 100 fF per output. Sources ramp from zero.

| Independently reviewed operating point | Minimum signed output margin |
| --- | ---: |
| Typical models, 27 °C, nominal supplies | 270.362 mV |
| Typical models, −40 °C, both supplies at 95% | 250.985 mV |
| Typical models, 125 °C, nominal supplies | 227.531 mV |

Each point covers 256 bits and 768 samples derived independently from the
actual input/select voltages. All 23 devices meet the unchanged post-settling
VCE 0.4–1.6 V, absolute VBE 1 V and collector-current 3 mA/emitter engineering
screens. Upper limits also pass over the complete power ramp. Native `OFF`
initialization flags and the zero-source operating point are checked; no
thermal model is disabled. These screens do not establish foundry SOA,
lifetime, jitter, channel compliance or BER.

The 0.5/0.25 ps comparison passes its prospective limits: maximum recorded
terminal-voltage difference **0.2465 mV**, relative power difference
**0.002303%**, and output-edge displacement **0.004574 ps**. Supply-power
integration uses the exact pinned ideal 2.5 V mux source after its ramp, saved
TX supply voltage and actual currents. Actual swapped-select and zero-bias
faults produce wrong output samples and are rejected without simulator errors.

Reducing data-bank capacitance repaired a hot-point signal-margin failure.
Changing common-mode requirements then repaired that point's device headroom.
Earlier supported-device failures and the original invalid-model attempts
remain in the evidence; they are not silently replaced by the positive runs.

## Physical result and remaining acceptance gates

The [generator](../hw/soc/flow/make_pcie_tx_mux2_hbt_passive_v1.py) creates a
**1,086 × 161.63 µm** macro with twelve ports, 27 core devices and 27 explicit
substrate contacts. The [checker](../hw/soc/flow/check_pcie_tx_mux2_hbt_passive_v1.py)
passes **560 DRC categories**, hierarchical and flat **54-device LVS**, and
five wrong-size, missing-device, open, short and off-grid controls. Canonical
regeneration matches every layer's polygons, labels, LEF and reference.
The separate TX driver is not placed into this macro.

Extraction preserves all 54 native devices, 154 intrinsic terminals,
112 physical reference points and 17 metal conductors. It produces
**173 distributed resistors and 291 capacitors**. Graph connectivity,
capacitance conservation, thirteen raw-data faults and six composition faults
pass. Finite native substrate contacts remain explicit. The extractor's
capacitance reference is separate from intrinsic body connections. This is
a development metal-RC model; substrate spreading and RF parasitics are not
qualified. The compact 54-device model passes with **270.352 mV** signed margin.
The distributed-RC model **fails**: minimum signed margin is **−84.941 mV**,
with **365 wrong-sign samples out of 768** and four selector-device headroom
failures. Both simulations complete without numerical diagnostics. The
1,086 µm-wide layout is therefore not accepted for 8 GT/s operation. The
706 µm-wide placement also passes DRC/LVS and fault checks but fails its
173 R / 271 C transient: **−118.833 mV** minimum margin and **411/768**
wrong-sign samples. Its transistor bounds pass. It is not adopted. A DC
diagnostic measures about **220 mV** ground difference between the reference
and tail emitters in that layout; a fresh layout widens current-carrying
metal and adds a local shared emitter connection. The widened 706 µm repair passes native DRC/LVS and all five fault
controls, but its 230 R / 301 C transient fails: **−283.715 mV**,
**232/768 wrong-sign samples** and device-headroom violations. Grouping
parallel devices reduces width to **322 µm**, with the same 54 native
devices. This banked layout also passes 560-rule DRC, hierarchical/flat LVS
and five fault controls; its 229 R / 301 C transient still fails:
**−273.006 mV**, **128/768 wrong-sign samples** and device-headroom
violations. Both compact references pass with 270.352 mV. Neither layout
is accepted electrically. A fresh upper-metal routing trial is unverified.

The 81-point HBT/resistor/temperature/common-supply matrix is complete and
independently reviewed: **66 pass, 15 fail device bounds**. All output sample
checks pass, including the failed **125 °C, 95%-supply typical-model point**.
Full PVT acceptance is therefore open. Independent rail
variation, mismatch, physical input/clock/bias drivers and full serial-chip
integration also remain open.

The [model-domain checker](../scripts/check_pcie_hbt_model_domain.py) rejects
out-of-range or unresolved multiplicities before simulation. Four regression
tests cover valid banks, the actual rejected historical source, invalid
parameters and empty/wrong-terminal inputs. The physical generator also
enforces the supported range. This domain check is not a circuit signoff.

The [evidence manifest](evidence/pcie-tx-mux2-supported-20261012.json) records
native captures, independent reviews, geometry, faults, extraction and public
archive identity. The [481-member archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-tx-mux2-supported-physical-20261012.tar.gz)
is 616,153,397 bytes with SHA-256
`135b634078a5c4e7134880163099f08b6bfb99ccce6063c2df2c74861cbd85ea`;
all members and the complete anonymous public download are verified. Active
full-matrix data and the later compact/extracted transient captures are
excluded from that archive. The original compact and 1,086 µm distributed-RC captures are now in a
[separate 122-member archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-tx-mux2-wire-failure-and-joint-tests-20261012.tar.gz):
102,762,559 bytes, SHA-256
`01d7203032a7c9a22a9fd8aac58a6133bca1518675195bda29ee17ca03bd6d29`,
with complete public byte/hash verification. It also includes the four
positive CPU/NPU/PCIe/Ethernet tests and metadata for the failed hot PLL
point. The 706 µm short and widened-power transient captures, new 322 µm
physical checks, NPU wake controls and post-CTS report are now in the
[325-member follow-up archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-tx-layout-repairs-npu-wake-and-postcts-20261012.tar.gz):
240,647,592 bytes, SHA-256
`2f11ae1c69ee21a69710157475d57cccb35f4a3f7e9c7c5835169e6f181b3432`.
Complete public download verification passes. The later 322 µm electrical
captures and full hot-PLL waveform are excluded from that archive. The
[updated evidence record](evidence/pcie-tx-wake-postcts-progress-20261012.json)
binds the latest completed verdicts and their limitations.

The completed 322 µm compact/distributed captures and full failed routed-core
LVS database, extracted circuit, independent reference and logs are now in a
[separate public archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-tx-banked-capture-and-full-core-lvs-20261012.tar.gz).
Its 203,436,852 bytes have SHA-256
`1044e318c216bb89b14df02fbb820629de29b3c008b4f4c9aa0ffe599e58ff22`;
[complete public readback passes](evidence/pcie-banked-full-core-lvs-public-20261012.json).
This also preserves the initial upper-metal spacing and subsequent connection
failures, and the next trial's methods. The corrected upper-metal geometry
passes DRC, hierarchical/flat LVS and five fault controls. Extraction initially
stopped because its helper still expected Metal5 public pins; a fresh helper
checks the actual TopMetal2 pin geometry. Its 229 R / 301 C transient completes with **−266.470 mV** minimum
signed margin and **128/768 wrong-sign samples**, plus device-bound
violations. Four lower ideal current references also fail the unchanged
output test; 250 µA clears device limits but has 163 wrong-sign samples.
These are rejected electrical trials. The completed upper-metal captures
are in the publicly verified
[110,364,055-byte archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-topmetal-tx-and-mapped-npu-wake-20261012.tar.gz),
SHA-256 `200190529af879819a6f2d73c77faa8a7124193ce5da4d61af73f3f220096f2f`.
Later bias captures/PVT reviews are a separate delivery. See the
[full latest measurement record](evidence/pcie-npu-topmetal-final-measurements-20261012.json).
