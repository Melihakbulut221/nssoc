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


## Cloud-only continuation and cleanup (12 October 2026)

At the user's request, local CAD controllers were stopped for migration. Subsequent replay proofs, mapping and timing screens run on GitHub-hosted runners. The [migration record](evidence/cloud-migration-20261012.json) distinguishes verified cloud-backed deletions, unique data still being uploaded and unfinished engineering work. Original bytes are removed only after their complete archive or file matches a GitHub release SHA-256, with a published restoration manifest. Local cleanup is not yet complete.

The [paired hosted ACK measurement](evidence/cloud-ack-screen-20261012.json) reproduces all seven setup and six hold groups across three corners using the same source capsule, runtime, ports, parameters and twenty SRAM macros. Although the isolated replay/link tests and arithmetic identity proof pass, the ACK lookahead candidate worsens slow PCIe setup from −1.414698 ns to −1.558253 ns. Its CPU setup improvement does not compensate for that regression; the candidate is rejected for adoption. These are unplaced development-RC measurements, not routed timing closure or a full serial PHY result.


## Hosted routing and native TX follow-up (13 October 2026)

The [paired global-routing experiment](evidence/cloud-global-route-pair-20261013.json)
uses the same restored design, native runtime, original SDC and PDK RC settings.
Three resized buffers and one inserted buffer improve slow PCIe setup from
−6.146189 ns to −5.539688 ns in this global-route estimate. The CPU slow setup
is still −6.465747 ns; fast PCIe hold is −0.920199 ns. Other groups regress,
and the native report still lists one unconstrained endpoint and 1,078
unannotated drivers. This candidate is **not adopted**. The earlier routed
ODB/SPEF result is a separate measurement and must not be combined with these
estimates. [OpenROAD parasitics documentation](https://openroad.readthedocs.io/en/latest/main/src/est/README.html)
describes the distinction between placement and global-routing estimates;
neither supplies final extracted timing acceptance here.

The [eight hosted TX measurements](evidence/pcie-tx-cloud-points-20261013.json)
restore the original device and wire models with SHA-256 checks. The unchanged
independent reviewer checks all 768 output samples and the complete startup
and operating bounds of 23 HBTs. Input common modes and amplitudes were declared
before simulation; the 8 GT/s rate, sample phases, 100 mV margin, loads and
native device limits remain unchanged.

| Input operating point | Compact margin (mV) | Compact device failures | Wire margin (mV) | Wire wrong signs / 768 | Wire device failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original baseline | 270.352 | 0 | −266.470 | 128 | 19 |
| Smaller input swing | 240.652 | 0 | −259.576 | 144 | 15 |
| Lower data common mode | 240.821 | 0 | −259.519 | 144 | 7 |
| Further common-mode reduction | 239.925 | 2 | −259.031 | 144 | 5 |

The original failed wire result reproduces within 1 µV with exactly 128 wrong
sign samples. All new wire operating points fail and are rejected. The first
hosted review attempt mistakenly selected the unused compact input file for
wire captures; its native waveforms and failure are preserved. The repaired
controller binds the review to the actually simulated mux. The frozen review
algorithm and limits are unchanged. The [metal-R/metal-C diagnostic](evidence/pcie-tx-cloud-rc-diagnostic-20261013.json)
is complete: setting all 229 explicit metal resistors to 1 mΩ removes wrong
signs and all device-bound failures but leaves only 96.382 mV margin, below
the unchanged 100 mV requirement. Removing capacitance alone still produces
96 wrong signs and 19 device failures. Removing both effects gives 270.333 mV,
close to the compact model. These artificial parasitic mutations diagnose the
interconnect mechanism only and cannot be used for layout or PHY acceptance.
The [seven net-class follow-ups](evidence/pcie-tx-cloud-net-diagnostic-20261013.json)
also complete. Reducing only internal metal resistance removes all 19 device
bound violations but still gives −140.752 mV and 128 wrong samples. Reducing
only supply resistance leaves six device failures; reducing return, input,
output or bias resistance alone leaves 19. All fail the unchanged output
requirement. Real internal interconnect and RC coverage still need repair;
no diagnostic source is substituted for the physical design. Full serial PHY, main-chip route
acceptance and final setup/hold remain open. All compute runs on hosted runners.


The [hosted real-layout trial](evidence/pcie-tx-cloud-real-layout-20261013.json)
regenerates the baseline and two actual thick-metal variants. Both variants
move the vertical Metal4 trunks to TopMetal1, increase lane/bank spacing, and
remove the broad Metal5 bypass that would intersect the new via stacks. One
variant additionally narrows signal buses to 3 µm. All three pass all 560 DRC
categories with zero markers and both hierarchical and flat 54-device native
LVS. Wrong finger count, missing HBT, open output, supply short and off-grid
geometry are each rejected. The first cloud attempt failed because a Python
controller running inside the AppImage attempted a nested FUSE mount; running
that controller outside the AppImage fixes the infrastructure without changing
physical acceptance. The successful run is 38311705739 at a17f5e98.

These layouts are not electrically adopted. The next hosted extraction uses
the exact archived Magic area-product runtime, actual newly generated geometry,
112 physical metal probes, the unchanged native RC graph audit, and thirteen
corruption controls. The cross-conductor mutation explicitly uses actual TX
ports P_op/P_on instead of inherited PLL port names. No artificial resistance
reduction is used in these geometry candidates. Full-wave acceptance, RF PEX
qualification, full serial PHY and final chip timing remain open.
