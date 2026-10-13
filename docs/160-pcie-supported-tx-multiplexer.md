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

The [new hosted extraction](evidence/pcie-tx-cloud-extraction-20261013.json)
passes for all three actual layouts (run 38312857503). The original geometry
produces 229 resistors and 301 capacitors; both thick-metal candidates produce
173 resistors and 267 capacitors. All 112 physical anchors remain connected
within the 17 original conductors. Exact native/export resistor edge values,
per-point ground capacitance, mutual capacitance attachments and the collapsed
capacitance matrix pass the frozen audit; all thirteen corruption controls are
rejected. These counts alone do not establish better electrical behavior.
The source-bound native-device composition and unchanged 8 GT/s full-wave
review completed in 38313404684; electrical adoption remains false.

The [cloud restore readback](evidence/cloud-output-restore-20261013.json)
reconstructs 49 migration batches, 32,196 original files and 36,080,201,324
logical bytes. This includes thirteen backward archive hard links, each
verified against an already hashed target and its own original manifest.
Ten safety tests per group reject unsafe or incorrect restore records and
exercise deletion/resume gates. The first reader lacked hard-link support;
its failed run is retained. Later uploads and the remaining local files are
outside this completed snapshot; cleanup is still in progress.

The [completed actual-layout waveform comparison](evidence/pcie-tx-cloud-layout-waveforms-20261013.json)
reproduces the baseline margin within 1 µV and its 128 wrong-sign samples.
Both thick-metal layouts eliminate all nineteen HBT operating/startup bound
failures and emit no native diagnostic warnings. Their signal screen still
fails: the regular-bus variant gives −251.503 mV and the narrow-bus variant
−253.319 mV, both with 128 wrong signs across the unchanged 768 samples.
Successful workflow execution therefore does not mean electrical acceptance.
Neither layout is adopted; actual interconnect delay still requires work.


The [fixed-phase diagnosis](evidence/pcie-tx-cloud-phase-diagnostic-20261013.json)
locates all 128 wrong signs at 0.3 UI (37.5 ps after the source bit boundary).
For the thick-metal variant, the TX zero crossing occurs 45.06–58.40 ps
after that boundary and reaches 100 mV in 52.01–67.23 ps. The mux contributes
most of this delay. At 0.5 UI there are no wrong signs, but 96 samples fall
below 100 mV. The 0.7 UI group has no failures.

A [separate propagation-delay diagnosis](evidence/pcie-tx-cloud-latency-diagnostic-20261013.json)
uses only the first 64 bits to estimate one constant delay, then freezes it.
For the thick-metal geometry the estimate is 55.681 ps. Evaluation of bits
64–254 gives 573 samples, no wrong signs and 249.106 mV minimum margin.
Bit 255 is explicitly excluded because shifted samples exceed the captured
time range. Polarity inversion creates 573 errors and a one-UI slip creates
300. The narrow-bus variant gives 249.620 mV with the same evaluation coverage.
The original 768-sample failed gates are preserved; no waveform, sample limit
or adoption flag is changed. This diagnostic does not implement a CDR.

This distinction matters for the requested PCIe product. The primary
[Tektronix PCI Express measurement MOI, version 4.6](https://download.tek.com/document/PCIE_DPOJET_MOI.pdf),
sections 5.12–5.13, measures data-dependent and uncorrelated jitter against a
recovered data clock, using repeating compliance patterns and specified
clock-recovery settings. Our inference is that source-referenced propagation
delay and serial-data eye degradation require separate measurements. The
existing short PRBS development captures and fixed-delay diagnostic implement
neither that compliance method nor a physical CDR. They cannot establish
PCI-SIG compliance, BER, channel/equalizer behavior, PVT coverage, or complete
Gen3 x4 PHY acceptance. The source-referenced integration screen still fails.

The next actual geometry trial prioritizes qn/qp, ea/eb, tail and selector
buses near the devices, with a second variant increasing HBT access vias
from four to eight columns. Both initially fail one TM2.bR marker in run
38315004937. The unchanged PDK rule requires 5 µm next to a wide line over a
long parallel span; the three gaps adjacent to reordered 16 µm supply buses
are enlarged from 3 to 5 µm. Their repeated complete geometry-to-transient
pipeline is run 38315447654. No rule is disabled and no failing result is
replaced by the propagation-delay diagnostic.


The [completed critical-bus trial](evidence/pcie-tx-cloud-critical-route-20261013.json)
passes physical DRC/LVS, native wire extraction and source-bound composition
for the paired control and both reordered geometries (run 38315447654).
Each preserves 54 native devices. The control has 173 wire resistors and
267 capacitors, reordered buses have 173 resistors and 270 capacitors, and
the wider-via variant has 781 resistors and 650 capacitors. The unchanged waveform
screen still fails with 128 wrong signs: control −251.503 mV, reordered buses
−242.423 mV, and reordered buses with wider via access −238.701 mV minimum
margin. All three have zero HBT bound failures and no native diagnostic
warnings. Neither new geometry is adopted. Further validation must separate
source latency from serial eye distortion while preserving the failed
integration screen; these results do not close the full serializer, PLL/CDR,
qualified RF PEX, main-chip routing or final timing.


The [source-bound timing-path trace](evidence/cloud-timing-paths-20261013.json)
resolves all 39 reported corner/group worst paths in the historical four-cell
trial. Its worst CPU path runs from the Ibex register-file read address to
a CLINT SECDED check bit; its PCIe path runs from replay read position to
TX data. Ethernet SRAM outputs still reach cross-check addresses in the
same cycle in that old physical database. The later source change 7ad40bde
adds cross-read capture registers, so further old-layout-only buffering would
miss an already implemented architectural repair.

The [newer physical resume input](evidence/cloud-newer-postcts-input-20261013.json)
therefore pins the completed `metadata-postcts19` chip database, original SDC
and original three-corner reader. Hosted run 38317996877 first reproduces
all reported saved slacks using nine hash-identical Liberty files, then
performs fresh global routing with the existing pinned PDK RC model. The
newer chip includes Ethernet cross-read capture, registered replay successor
and RX-return metadata. This job has not yet returned at this checkpoint;
it cannot establish detailed routing, qualified extraction or serial PHY
acceptance. The locally queued credit-offer physical job had not started,
so it is not represented as a completed physical checkpoint.


The [native CMOS input-driver experiments](evidence/pcie-cmos-data-driver-20261013.json)
replace four ideal mux data inputs with actual foundry `sg13g2_buf_16` cells
and native resistors; the selector and bias sources remain ideal. Run
38320024701 rejects the direct resistive level-shift candidate: the 2.5 V
network backfeeds the 1.2 V CMOS outputs, eight of sixteen LV MOS devices
exceed the prospective 1.32 V terminal-voltage screen, and the differential
data become ambiguous. The supply absorbs 3.681 mW on average. This is a
recorded circuit failure, not an accepted interface.

Run 38320561121 inserts sixteen native HV NMOS devices so that the LV
outputs drive only gates. All thirty-two MOS devices pass the engineering
voltage screens and the CMOS supply now delivers 1.373 mW on average. The
candidate is still rejected: 208 of 768 original input-bit samples have
wrong signs, and four downstream HBT devices have insufficient VCE
headroom (minima 0.201833 V and 0.303712 V versus the unchanged 0.4 V bound).
The downstream reviewer reports zero wrong signs against the *actual mux
inputs*; this does not prove that those inputs represent the correct source
bits at the required time. A separate final-output comparison now uses the
original PRBS bits at all 768 unchanged source-relative sample times and
the original 100 mV limit. Its polarity, one-bit-delay, low-amplitude and
incomplete-capture controls run on hosted workers. No fitted phase replaces
the failed source-relative gate. Both supply-disconnection fault captures
are retained. No full serializer, PLL/CDR, physical driver layout, PVT
qualification, foundry SOA or full PHY acceptance is claimed.


The additional original-bit screen completed in hosted run 38321423547.
The powered HV candidate has 192 wrong signs among 768 final-output samples,
with a minimum margin of −306.263 mV. The disconnected-pullup control has
440 wrong signs and all 768 samples below 100 mV. All seven oracle corruption
and coverage tests pass in both hosted jobs. These results confirm why the
input-relative reviewer cannot stand in for the original source-bit check;
the candidate remains rejected and no output phase or threshold is changed.


The [paired launch-contract study](evidence/pcie-cmos-launch-contract-20261013.json)
in run 38322832591 retains all original final-output observation times and
limits. Its prospective external interface presents A data 125 ps before
selection, while B launch is unchanged. This is a separately declared
upstream data-availability requirement; it does not implement the upstream
serializer or move the output oracle. Both coincident-launch controls retain
192 wrong signs. With the inactive-bank launch, both candidates have zero
wrong signs and zero samples below 100 mV. The lighter v3 driver reaches
210.161 mV minimum output margin, but still has four HBT headroom failures
(minimum VCE 0.262526 V) and 128 selected-input samples below 150 mV. It is
not adopted. Legacy half-rate input observations remain recorded, including
unselected slots in which the next value is already being prepared.

The following v4 candidate connects the native HV drains directly to the
loaded data node, removing the intermediate resistor/drain RC node. Its
four 4 um HV branches and two native rail-setting resistors per input still
require native transient and device checks. The v3 control is retained; no
limits, data sequence, or final-output sample phases are relaxed.


The [direct-drain v4 study](evidence/pcie-cmos-direct-driver-20261013.json)
completes native captures in run 38323278847 but is rejected. With early
A launch its final output passes all 768 samples with 154.679 mV minimum,
yet 511 selected-input samples fall below 150 mV and the unchanged independent
input-ambiguity guard rejects the capture. The exact current native
transistor bindings identify four **selector** HBTs with bases on `sp/sn`
and minimum VCE 0.256488 V. The absence of a downstream failure list after
the input guard aborts is not a passing device review. Device IDs from older
layout revisions cannot substitute for the current netlist bindings.

The next paired study retains v3 and changes only its series resistor from
9.08 um to 6.92 um in v5. Separately, the `clock_small` operating point
reduces the ideal selector amplitude from 300 mV to 80 mV at the same 1.23 V
common mode to provide more selector headroom. It does not change any
voltage, timing or sample acceptance limit. Both changes require measured
results; real upstream serialization and actual clock generation remain
required even if the nominal component screen eventually passes.


The [selector headroom comparison](evidence/pcie-cmos-selector-headroom-20261013.json)
completed in run 38323831698. With v5 and the 80 mV selector amplitude, all
768 original output samples pass (minimum 226.386 mV), all selected-input
samples exceed 150 mV (minimum 150.123 mV), and the independent 23-HBT
review and all 32 MOS engineering voltage screens pass without diagnostics.
The input margin exceeds its gate by only 0.123 mV, so this is not yet a
robust operating point or a layout adoption.

A follow-up campaign keeps the same source bits, launch contract, sample
times and limits. It repeats the nominal case at 0.25 ps maximum step and
screens slow/fast/skew CMOS combinations plus hot/low-supply and cold/high-
supply combinations. Core and analog rail waveforms are checked against the
requested voltages; MOS corners apply to the actual native models. These
ten diagnostic conditions are not an exhaustive foundry PVT or Monte Carlo
qualification. Actual upstream serialization, selector clock generation,
PLL/CDR, frontend layout/extraction and main-chip integration remain open.


The [ten-condition follow-up](evidence/pcie-cmos-driver-corners-20261013.json)
completed in run 38324432662. The nominal result survives halving the step:
selected-input minimum changes from 150.122620 to 150.117650 mV. Only the
nominal, quarter-step, fast-MOS and `mos_fs` cases pass every declared
selected-contract gate. The circuit is rejected for PVT adoption. At
125 C with low supplies and slow models, 64 original output samples have
wrong signs and 192 are below 100 mV. At -40 C with high supplies and fast
models, two tail HBTs reach only 0.361612 V VCE and sixteen LV MOS devices
exceed the engineering voltage bound; one internal CMOS node reaches
1.362852 V. Other slow/mixed conditions also miss the input differential
requirement. The slow-MOS and hot/low captures complete natively, then the
independent input-validity guard rejects them. They are not simulator
convergence failures or passing device reviews.

These results motivate moving the CMOS-to-CML boundary earlier in the
serializer and providing more real input settling time. A native four-to-one
CML tree with lower-rate CMOS inputs is a next design candidate, not an
implemented fix. Actual bias/clock circuits must also address cold tail
headroom and CMOS overshoot; per-corner ideal voltage tuning cannot replace
those circuits. The existing 54-device physical proof covers only the final
two-to-one mux. Any added stage requires complete new device accounting,
startup/whole-wave checks, physical connectivity, DRC/LVS and extraction.

The primary [IHP MOS documentation](https://ihp-open-pdk-docs.readthedocs.io/en/latest/contents/device_libraries/mosfets.html)
identifies the model and corner libraries and explains how total width and
fingers map to extraction. The [I/O architecture documentation](https://ihp-open-pdk-docs.readthedocs.io/en/latest/contents/io_library/02_drive_strength.html)
identifies its native level shifter and output stages. The pinned local
`sg13g2_LevelUp` SPICE subcircuit was inspected as another possible input
interface, but it has not been measured at the required rate here. Neither
reference constitutes a high-speed qualification or permission to relax
our voltage gates.
