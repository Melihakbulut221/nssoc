# 152 — Nominal charge-pump and filter current measurements
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured result — 7 October 2026

The exact thirteen-device pump/filter slice from the connected 570-instance study now completes all **twelve nominal 34 ns simulations**: idle, source, sink and both commands at clamped control voltages of 0.5, 0.6 and 0.7 V. Each capture contains 108,811 samples and 28 columns. All thirteen device screens and the prescribed command/supply/clamp checks pass in each case. These are finite model screens, not device qualification or closed-loop operation.

The [inventory](../hw/soc/pcie-evidence/20261007-pump13-points/inventory.json) binds sources, controls, all native results and the complete public capsule. The [205-member capsule](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/pcie-pump13-twelve-points-20261007.tar.gz) contains the raw gzip waveforms and retained failures. Its 164,566,312 bytes have SHA256 `3c5e7689b8f87856f7a6fb51db0169252315b82fec680575552a312c21dc2767`; complete local member readback and a full anonymous download match. External simulator/model dependencies are hash-pinned, not bundled in this capsule.

## Currents and limits

Two independent ideal-current-source operating points establish the simulator clamp-current sign. Positive current into the clamp means net current delivered to the control node. Four deliberate sign/observation mutations are rejected, giving six sign controls.

The following means use the complete fixed 4–34 ns measurement window. Commands are ideal 0/2.5 V levels; AVDD is 2.3 V and DVDD is 2.5 V in this experiment.

| Clamp voltage | Idle current (µA) | Source command (µA) | Sink command (µA) | Both commands (µA) |
| --- | ---: | ---: | ---: | ---: |
| 0.5 V | +46.088506 | +82.085090 | +5.706672 | +41.719351 |
| 0.6 V | +33.017214 | +69.013235 | −9.713786 | +26.299899 |
| 0.7 V | +19.945937 | +55.941259 | −24.095419 | +11.918648 |

The slice provides opposite net-current directions at 0.6 and 0.7 V under these ideal commands. At 0.5 V the sink command still leaves positive net current, so this point does not demonstrate bidirectional control. Passing electrical screens alone would not detect that functional limitation.

These slice currents must not be substituted directly for the loaded PLL current. The actual 570-instance command and boundary waveforms must first match the subtraction baseline, or a separately measured correction must establish the difference. The earlier 0.7 V loaded experiment also retains its divide-by-four failure. No tuning interval, feedback polarity, loaded reachability or PLL lock is accepted here.

## Execution and saved-data validation

The former 45 MiB per-file native limit could overflow the 64 MiB case budget before a failed raw tail was saved. The only executable-driver change reduces that native limit to 8 MiB. The graph, twelve stimuli, step size of 0.3125 ps, 34 ns duration, sample limits and physical checks are unchanged. Two native files plus the conservative gzip, receipt, source and failed-tail allowances total 53,104,010 bytes, leaving 14,004,854 bytes inside the case budget. An actual owned child hits the 8 MiB limit and is reaped; the test does not merely inspect a configured constant.

There are **72 passing source/storage/startup/resource controls**, including that real child, followed by the six actual sign controls. A single controller ran all twelve cases sequentially on CPU 10 with a 2 GiB address-space limit and no healthy-run elapsed timeout. Closed waveforms are synchronized on SSD; this is not a resumable solver checkpoint or live power-loss-tail guarantee.

A separate saved-data reader checks every result input/output hash, all raw bytes, all sample-count trailers and all thirteen device-screen records. Across **1,305,732 samples**, it independently sums **672 current integrals** using scalar trapezoids and `math.fsum`; the maximum mean-current arithmetic difference is 2.710505431213761e−20 A. This is a separate computation by the same root reviewer, not an external review. The initial reader failed to normalize internal-device current names; that attempt remains in the capsule, and the corrected reader changes only the name mapping and integral census.

Next work is exact loaded-boundary replay, diagnosis of the retained divide-by-four failure, and then source-bound closed-loop acquisition and convergence checks. Full CDR/PHY operation, physical integration, final chip timing and manufacturing acceptance remain open.

## Loaded-boundary replay — 9 October 2026

The complete saved bytes of the full 570-instance and isolated pump traces
are now verified before comparing their waveforms at all three control voltages. Supplies and clamp
voltages agree, but the loaded PFD's nominally idle outputs contain roughly
**18 mV UP and 29 mV DOWN excursions**. Ideal zero-valued commands therefore
do not reproduce the instantaneous loaded pump boundary.

Three new native thirteen-device simulations replay **every saved sample of
all five boundary voltages**, including startup. Each finishes 34 ns with
**544,198 samples**, clean startup diagnostics and all thirteen finite device
screens passing. On the union of the two time grids over the original 4–34 ns
window, the maximum boundary residual is below 2.18e-14 V. Across the nine MOS
current observations, the largest instantaneous residual is 8.09 nA and the
largest mean residual is 42.74 pA. These are measured numerical residuals,
not newly chosen physical acceptance thresholds.

| Clamp | Ideal-idle pump current (µA) | Loaded-boundary pump replay (µA) | Loaded570 minus replay clamp current (nA) |
| --- | ---: | ---: | ---: |
| 0.5 V | 46.088506101 | 46.088504406 | +26.671971 |
| 0.6 V | 33.017214352 | 33.017212688 | +0.292124 |
| 0.7 V | 19.945936517 | 19.945934867 | +2.243614 |

The full570 clamp includes oscillator/control-node loads absent from the
thirteen-device slice. Its current is **not assumed equal** to the slice's
current. The last column is their measured difference under matching imposed
voltages. The sub-2 pA correction to the ideal-idle pump mean supports this
particular nominal idle comparison; it does not establish dynamic source/sink
transfer, PVT reachability, feedback polarity or PLL lock. The original 0.5 V
HBT screen failure and 0.7 V strict divide-by-four count failure remain recorded.

The [streaming comparison tool](../scripts/compare_pcie_pump_boundary.py)
checks compressed/output hashes, every raw byte and payload hash, header/table
identity, sample-count trailer, finite values in **all** columns and strictly
increasing time. It retains only requested observations in memory. Twelve
reader controls pass, including corruption of an unselected column and a time
failure across a block boundary. It compares internal pump quantities and
keeps global supply/clamp currents out of the equality comparison.

The first native replay reached its predeclared 300,000-row resource bound
and was stopped with the failed capture retained. The second declares
1,000,000 rows and 256 MiB per point before launch, while preserving all
voltage/current screens, stimuli and solver settings. It completes the same
34 ns experiment. The [replay review](../hw/soc/pcie-evidence/20261009-pump-loaded-boundary/replay-review.json)
and [delivery record](../hw/soc/pcie-evidence/20261009-pump-loaded-boundary/delivery.json)
record completed local/native checks and the complete anonymous public
readback of the 312,231,678-byte replay capsule. Its SHA256 is
`20b5b060380f4443edbd83d6b90c067832ec1e956e12fb55ba3f637163af32bc`.
Failed and successful replay captures are included. The three original
570-instance captures are separate: their [delivery receipts](../hw/soc/pcie-evidence/20261009-pump-loaded-boundary/loaded570-delivery.json)
bind 2,721,803,628 bytes, with complete public readback for each archive.
Two readbacks use contiguous, non-overlapping HTTP ranges, exact response
bounds and the SHA256 of all bytes concatenated in order; no partial download
is presented as a complete verification.

A separate fixed-ordinal diagnostic explains the 0.7 V count anomaly more
precisely. Every consecutive CML edge advances by four nearest VCO edges,
including the intervals whose half-open bucket counts are five and three.
Those changes coincide with relative edge phase crossing zero by only tens
of femtoseconds. This is evidence for a boundary-counting sensitivity, not a
replacement passing verdict.

## Half-step and actual closed-feedback response

The unchanged 0.7 V circuit now completes **217,641 samples** at 0.15625 ps,
half the original maximum step. All twelve predeclared numerical comparisons
pass: complete edge census, window membership, absolute same-ordinal edge
differences and frequency differences for the oscillator, CML output and
feedback. The largest edge difference is **0.512 ps** and frequency differences
are **15.51 ppm or less**. No time alignment, phase subtraction or cropping
was used. The original strict divide-by-four predicate still fails; this is
numerical agreement between two retained failing functional verdicts, not a
passing divider replacement. See the [comparison](../hw/soc/pcie-evidence/20261009-feedback-response/halfstep-comparison.json).
Its [complete half-step capsule](../hw/soc/pcie-evidence/20261009-feedback-response/halfstep-delivery.json)
contains 29 members and 1,818,129,507 bytes. Complete anonymous readback matches
SHA256 `068f5c0b605cea33b5673a774d70c8b3d801c937463252e2b16291b93ad2b4a5`.

The actual **570-device feedback circuit**, with reset released at 8.1 ns,
reference starting at 14 ns and **no external VCTRL clamp**, completes 34 ns.
All 570 finite electrical screens and thirteen divider predicates pass.
VCTRL spans 0.796497–1.028892 V during 4–14 ns,
0.855121–1.046270 V during 14–24 ns, and 0.852718–1.025888 V during 24–34 ns.
This short record has too few reference periods to establish acquisition
or stationary phase. The [native result](../hw/soc/pcie-evidence/20261009-feedback-response/startup-native.json)
and [source/observation preflight](../hw/soc/pcie-evidence/20261009-feedback-response/startup-preflight.json)
bind the circuit, complete observations, zero-source operating point and
actual HBT startup flags.

Initial deck-preflight failures and a post-run receipt destination error are
retained. The solver completed the intended `closed-02` circuit; its wrapper
wrote completion metadata under the earlier failed attempt's directory.
The [receipt repair](../hw/soc/pcie-evidence/20261009-feedback-response/receipt-finalization.json)
verified all input/output hashes, raw capture and screen records before
moving that metadata. No waveform, circuit or predicate was altered.
The [complete startup capsule](../hw/soc/pcie-evidence/20261009-feedback-response/startup-delivery.json)
contains 54 members and 917,339,671 bytes, including failed attempts and the
receipt repair. Its anonymous public readback matches SHA256
`5dfd04929b31ead6ea35404a6ea2542e3bd92b127964a1cfce729bb96f0744df`.

A separate 1 µs run retains the same circuit and 0.3125 ps maximum step, with
explicit 3.3-million-row and 40 GiB point limits. Its result is pending.
The [response reviewer](../scripts/review_pcie_feedback_response.py) measures
frequency and continuous feedback edge count at reference edges. It never
wraps phase modulo a cycle, which would hide cycle slips, and reports a static
phase offset without treating zero offset as a lock requirement. Independent
fixtures detect positive and negative multi-cycle drift, missing feedback,
incomplete time coverage and unordered samples. The bounded saved-waveform
reader and reviewer have **25 passing controls**. Period spread in a finite
nominal simulation is not qualified jitter, phase noise, BER, PVT, extracted
layout or full serial PHY acceptance.

## Native pump/filter layout — 9 October 2026

The [layout generator](../hw/soc/flow/make_pcie_pump_filter13_v1.py)
now creates the exact thirteen-device pump/filter core with SG13G2 PCells:
five HV NMOS, four HV PMOS, three RPPD resistors and one MIM capacitor.
Thirteen real substrate contacts and four individual well contacts bring the
physical reference to **30 devices**. The **544 × 206.63 µm** macro exposes
seven ports: UP, DOWN, VCTRL, separate oscillator and pump supplies, AVSS and
SUB. Its generated identifiers are lowercase. SUB and AVSS remain separate;
each PMOS body connects through its actual well contact.

The unchanged upstream main DRC deck reports **zero violations across 560
rule categories**. Strict native LVS matches all thirty devices in both deep
and flat extraction, with seven extracted ports. The
[verification tool](../hw/soc/flow/check_pcie_pump_filter13_v1.py) rejects five
actual faults: wrong transistor width, missing well contact, a removed VCTRL
route, a physical rail short and an off-grid metal shape. The
[native records](../hw/soc/pcie-evidence/20261009-pump-filter-layout/native-controls.json)
retain every command, verdict and pinned input.

The first geometry had three latch-up spacing markers and four Metal3
spacing markers. Moving NMOS substrate contacts closer and separating PMOS
well-contact escape tracks removed them without changing core dimensions
or connectivity. The [failed first check](../hw/soc/pcie-evidence/20261009-pump-filter-layout/first-drc-failure.json)
remains available.

OpenROAD reads the [LEF macro](../hw/soc/pcie-evidence/20261009-pump-filter-layout/nssoc_pump_filter13_layout_v1.lef)
with the expected outline, all seven pin geometries and direction/use values,
and obstructions on all seven routing layers. No obstruction covers a pin.
Removing one LEF port or adding an obstruction over it is rejected by the
[native LEF checks](../hw/soc/pcie-evidence/20261009-pump-filter-layout/lef-controls.json).
Six source controls also preserve distinct supplies, ground and substrate,
and reject changed pump/filter definitions.
The [public raw capsule](../hw/soc/pcie-evidence/20261009-pump-filter-layout/delivery.json)
includes GDS, LEF, schematic, generators, native reports, faults and the failed
attempts: 151 members, 483,285 bytes. Complete anonymous readback matches SHA256
`e9f3cf9f2bae6d0d37332d083e4da638db426742834f72f0da5cc1a9a57a3c39`.

This is a verified **component layout**, not a complete PLL or main-chip
instance. The full570 transient above used the earlier schematic pump/filter;
it does not validate the seventeen added physical contacts, extracted wire
parasitics or closed-loop behavior of this layout. The native physical-model binding below addresses the seventeen contacts.
Parasitic extraction and subsequent feedback simulations remain required.

## Native thirty-device pump model — 9 October 2026

The [compact circuit](../hw/soc/pcie-evidence/20261009-pump30-model/pump30-compact.spice)
now follows all thirty devices and named terminals from the actual passing LVS
extraction. The translator explicitly converts the extractor's MOS source/gate/
drain/body order to the compact model's drain/gate/source/body order. It preserves
native junction areas, perimeters and transistor dimensions. Each of the seventeen
2 × 2 µm contacts uses the pinned PDK area/perimeter conductance equation, giving
81.666667 Ω per contact. This is a finite contact model; it does not add spatial
substrate or wire parasitics.

The [independent translation checker](../scripts/check_pcie_pump30_binding.py)
derives connectivity and parameters from native device identities rather than
accepting the generated manifest as its reference. Its
[eight actual fault controls](../hw/soc/pcie-evidence/20261009-pump30-model/binding-controls.json)
reject drain/source exchange, changed width, default contact resistance, bypassed
body contact, wrong supply, missing contact, exchanged external ports and a
duplicate parameter.

Three new 34 ns native simulations hold VCTRL at 0.6 V and command idle, source
or sink. All thirty finite electrical screens, zero-source operating-point checks
and strict simulator diagnostics pass, with **108,811 samples per case**.
The [native summary](../hw/soc/pcie-evidence/20261009-pump30-model/native-review.json)
and [paired comparison](../hw/soc/pcie-evidence/20261009-pump30-model/current-comparison.json)
retain input/output hashes and compare against the earlier schematic thirteen-device
model over the same 4–34 ns window:

| Command | Schematic current into VCTRL | Physical-device current into VCTRL | Difference |
| --- | ---: | ---: | ---: |
| Idle | +33.017214352 µA | +33.017213349 µA | −1.003 pA |
| Source | +69.013234581 µA | +69.012809898 µA | −424.684 pA |
| Sink | −9.713785610 µA | −9.713784878 µA | +0.731 pA |

Positive clamp current represents current delivered by the circuit into VCTRL,
as established by independent native injection/withdrawal controls. The first
postprocessing attempt incorrectly negated this value. Its
[rejection record](../hw/soc/pcie-evidence/20261009-pump30-model/rejected-sign-comparison.json)
is preserved; the corrected comparison revalidates saved raw bytes and sign-control
outputs. No solver waveform was changed.

The seventeen contacts are therefore exercised in this component simulation.
This does not establish the layout's wire RC, extracted PLL dynamics, PVT,
phase noise, jitter, serial link operation or main-chip timing. A separate
587-device feedback candidate replaces the old thirteen-device pump/filter with
this native thirty-device model. Its 557 other device records and 2,685 existing
wire elements match the previous composition exactly. Its completed finite transient is
reported below; the physical parent PLL and pump wire extraction remain open.

The [complete public capsule](../hw/soc/pcie-evidence/20261009-pump30-model/delivery.json)
contains the new captures, paired schematic baselines, sign controls, sources,
translation faults and rejected comparison: **164 members, 90,338,951 bytes**.
Complete anonymous readback matches SHA256
`cbdb6d4eb20725b27cac3a8621f4cac437aae3a3fc6974aa40d9f25e70559b53`.

## Phase-detector component layout — 9 October 2026

The [phase-detector generator](../hw/soc/flow/make_pcie_pfd102_v1.py)
now implements the frozen PFD's 51 HV PMOS and 51 HV NMOS devices using native
PCell geometry. Each PMOS has its own physical well contact, and each placement
has a substrate contact: **255 physical devices**, including 153 finite contacts.
The initial linear layout is **4,104 × 476.63 µm**. Its eight ports are REF, FB,
RESET, UP, DOWN, VDD, VSS and SUB, using lowercase identifiers. VSS and SUB
remain distinct; the component preserves the PFD's REF/FB port convention.
The full feedback candidate still connects those ports with its explicitly
recorded feedback polarity.

The unchanged upstream DRC deck reports **zero violations in 560 rule
categories**. Both deep and flat native LVS match all 255 devices and all eight
ports. The [strict native checks](../hw/soc/flow/check_pcie_pfd102_v1.py)
reject five actual faults: changed NMOS width, removed well contact, removed
UP route, a physical ground/substrate short and off-grid Metal1 geometry.
The [comparison records](../hw/soc/pcie-evidence/20261009-pfd102-layout/native-controls.json)
retain the exact sources, GDS and commands.

The [LEF macro](../hw/soc/pcie-evidence/20261009-pfd102-layout/nssoc_pfd102_layout_v1.lef)
also passes native OpenROAD outline, direction/use, pin geometry and obstruction
checks. Missing and obstructed pin faults are rejected by the
[LEF checker](../hw/soc/flow/check_pcie_pfd102_lef.py).
Seven source controls preserve reference/feedback/reset wiring, transistor
widths and body connections and reject changed or missing source definitions.
Initial test-fixture naming mistakes are retained in the raw campaign, followed
by the corrected seven passing controls.

This is an initial physical component, with area and wire loading still to be
optimized and characterized. Its 153 added physical contacts and wire parasitics
are not exercised by either the older 570-device run or the new 587-device
pump-integration run. The native model translation and finite feedback test are reported below.
Wire-extracted feedback simulation and a connected physical PLL parent remain required. It does not establish a
complete serial Gen3 x4 PHY or main-chip timing closure.

The [public physical PFD capsule](../hw/soc/pcie-evidence/20261009-pfd102-layout/delivery.json)
contains both generated versions, full GDS/LEF, source, native DRC/LVS and
fault records: **161 members, 1,172,516 bytes**. Complete anonymous readback
matches SHA256
`26f73f50fef30a74a33f0c9e3c582c32586cfcf8056759e161b98f9fb018be8d`.

## Physical pump in the actual feedback loop — 9 October 2026

The separate **587-device** feedback simulation has now completed. It retains
the original reset/reference stimulus, uses the actual thirty-device pump model,
and has no external VCTRL clamp. All **587 finite electrical screens and thirteen
divider predicates pass**, with 108,847 saved samples over 34 ns at a maximum
0.3125 ps timestep. The [native result](../hw/soc/pcie-evidence/20261009-feedback587/native-result.json)
and [postflight](../hw/soc/pcie-evidence/20261009-feedback587/postflight.json)
verify all 1,137 saved observations, 1,138 transient columns, 64 actual HBT startup
flags and a zero-source operating point. Four deck faults are rejected.

VCTRL spans 0.796496–1.028935 V during 4–14 ns, 0.855080–1.046317 V during
14–24 ns, and 0.852679–1.025944 V during 24–34 ns. Native execution took
1,516.99 seconds with a 2 GiB address-space bound and no healthy-run elapsed
timeout. A first launch rejected a stale CPU-affinity assertion before capture;
that failed attempt is retained separately.

The [full feedback capsule](../hw/soc/pcie-evidence/20261009-feedback587/delivery.json)
contains 77 members and **920,924,995 bytes**, including complete raw observations,
source and failed preparation attempts. Complete anonymous readback matches
SHA256 `52dd87b7d34058e36dd53cbc301922e83936337ff5977b28d653bddd60e6c701`.
This finite nominal result does not establish PLL acquisition, phase noise,
PVT, pump wire parasitics or full serial PHY operation. The PFD physical model is tested in the separate 740-device composition below.


## Physical PFD and pump in the feedback loop — 9 October 2026

The new **740-device** composition passes its finite native transient. It replaces
102 schematic PFD devices with the layout's **255 devices**, including all 153
finite body contacts. The other 485 devices and 2,685 previously extracted chain
wire elements remain unchanged. PFD REF/FB feedback polarity is explicitly
preserved. This does not add PFD or pump wire parasitics.

The [independent model binding](../hw/soc/pcie-evidence/20261009-feedback740/pfd-binding-controls.json)
checks every extracted device identity, named terminal, geometry and finite
contact resistance against the native LVS database. Eight actual mutations are
rejected: exchanged drain/source, incorrect width, default contact resistance,
bypassed body contact, wrong supply rail, missing contact, exchanged external
ports and duplicate parameter.

All **740 finite electrical screens and thirteen divider predicates pass** in
[native simulation](../hw/soc/pcie-evidence/20261009-feedback740/native-result.json),
with 108,847 samples over 34 ns, maximum step 0.3125 ps. The
[postflight](../hw/soc/pcie-evidence/20261009-feedback740/postflight.json) verifies
1,189 saved observations, 1,190 transient columns, all 64 native HBT startup
flags and the zero-source operating point. It rejects four actual deck faults.
The original reset/reference stimuli remain; there is no VCTRL clamp.

VCTRL spans 0.796496–1.028935 V during 4–14 ns, 0.855080–1.046317 V during
14–24 ns, and 0.852679–1.025942 V during 24–34 ns. Native execution took
993.18 seconds with a 2 GiB address-space bound and no healthy-run elapsed
timeout. These are finite nominal electrical checks, not PLL lock, phase noise,
PVT, extracted full-loop timing, serial PHY or main-chip timing acceptance.

The [complete public capsule](../hw/soc/pcie-evidence/20261009-feedback740/delivery.json)
contains the finite run, full raw observations, native-device translation,
eight model faults, postflight and exact campaign sources: **67 members,
956,046,595 bytes**. Complete anonymous readback matches SHA256
`5a22455866482f27ff21c07780528090caf2ba0d81150bc7423f19a6238296cf`.

## Pump layout metal RC and finite device tests — 9 October 2026

The [pump wire model](../hw/soc/analog/pcie/pll_pump30_wire_v1.spice) now combines
all thirty native devices and finite body contacts with **84 distributed metal
resistors and 155 capacitors**. Every metal/via polygon is copied from the same
LVS-checked pump GDS. Exact geometric probing binds twelve conductor components
to the unsimplified native LVS nets, without merging components by net names.
All thirty devices have unique physical PCell enclosures. The reference-point
census covers 52 metal device terminals, 29 retained intrinsic body/well terminals
and seven public pins. MOS source/drain points use their own native terminal
geometry; gate points use the connected gate-poly/contact geometry.

The [wire audit](../hw/soc/pcie-evidence/20261009-pump-wire/wire-audit.json)
checks exact exported resistor edges and values, each distributed ground-cap
attachment, every mutual-cap attachment, and the entire 13-by-13 collapsed
capacitance matrix. Thirteen actual raw-data corruptions are rejected, including
redistributing ground capacitance while keeping the same matrix and shifting a
mutual-cap attachment within one conductor. The [composition controls](../hw/soc/pcie-evidence/20261009-pump-wire/composition-controls.json)
independently require all thirty device records and all 239 native wire records;
six more mutations reject changed device pins, missing contact, changed body,
missing resistor, changed capacitor and shorted capacitance reference.

The eighth macro port, `wire_cref`, is the extractor's capacitance reference.
It remains distinct from the seven original ports, including `sub`. The finite
testbench explicitly holds it at zero volts. Intrinsic body regions and finite
contacts remain present; this does not model substrate spreading resistance or
qualify RF reference-plane placement.

Three [native 34 ns tests](../hw/soc/pcie-evidence/20261009-pump-wire/native-review.json)
at ideal 0.6 V VCTRL pass all thirty electrical screens, zero-source operating
point and diagnostic checks: idle, source and sink, each with 108,811 samples and
80 columns at 0.3125 ps maximum step. The first launch rejected a CPU-affinity
mismatch and cleaned up its owned process. The corrected fresh run uses CPU12;
the failed attempt is retained. No electrical acceptance threshold was relaxed.

| Current delivered to VCTRL, µA | Compact physical model | With pump metal RC |
| --- | ---: | ---: |
| Idle | +33.017213 | +33.111677 |
| Source | +69.012810 | +67.276185 |
| Sink | −9.713785 | −8.723883 |

The [paired measurement](../hw/soc/pcie-evidence/20261009-pump-wire/current-comparison.json)
uses the previously verified clamp-current sign convention and the complete
4–34 ns window. These are ideal-command component tests. They do not establish
closed-loop lock, PVT, EM/ESD, qualified extraction or full PCIe PHY operation.
A separate 740-device feedback run now includes this pump wire network, retains
the other 710 devices and all previous 2,685 wire elements, exposes the new
reference explicitly, and saves all 1,236 observations. Its finite transient
result now passes, as recorded below; the PFD wire network is not included in
that particular run.

The [complete component capsule](../hw/soc/pcie-evidence/20261009-pump-wire/delivery.json)
contains 98 members and **140,292,447 bytes**, including geometry, restored/pinned
extractor provenance, raw extraction, controls, failed attempts and complete
finite captures. Complete anonymous readback matches SHA256
`e30ef936125b9f8d13267a9563713ba4f2b8e9cbbad6470f5b06fd444b09066d`.

## PFD metal RC composition — 9 October 2026

The same geometry-binding and native wire-audit method now covers the PFD layout.
All 255 unsimplified native devices have unique PCell location witnesses. Its
714 intrinsic terminals comprise 459 metal references and 255 retained body/well
references. Eight public pins bring the metal probe count to 467. The unchanged
GDS metal/via unions form 57 physical conductors, each uniquely bound to an actual
native LVS net without joining conductors by names.

The [distributed extraction](../hw/soc/pcie-evidence/20261009-pfd-wire/wire-audit.json)
contains **770 resistors and 1,354 capacitors**. Exact native/export resistor
edges and values, individual ground and mutual-cap attachments, and the entire
58-by-58 collapsed capacitance matrix pass. Thirteen raw-data corruptions fail.
The [composition check](../hw/soc/pcie-evidence/20261009-pfd-wire/composition-controls.json)
retains every native device parameter, separately binds each named terminal,
and requires all 2,124 wire records. Six additional actual corruptions fail.
The ninth PFD macro port exposes `wire_cref` independently of its original eight
ports; substrate spreading and RF reference-plane placement remain unqualified.

These are **geometry, extraction-consistency and composition results**, not a
PFD transient or full PHY pass. A separate feedback experiment combines both
pump and PFD wire models with the 740-device chain: 5,048 wire elements and 1,647
saved observations. Both new capacitance references are exposed independently
and explicitly held at zero in the fixture. The first launch exceeded the old
64 KiB capture-header bound; its failure and partial capture are retained. A
fresh run uses a 128 KiB bounded header reader with the same exact column,
vector, alias and format checks. The full 1,648-column synthetic header and
eight corrupt-header controls pass. Electrical acceptance limits are unchanged;
the completed transient fails three divider checks and one HBT current screen.
Its actual-header and operating-point postflight passes only that narrower scope.
The failed electrical verdict is retained; details and the layout repair follow below.

The [public component capsule](../hw/soc/pcie-evidence/20261009-pfd-wire/delivery.json)
contains the candidate model, actual geometry, raw RC and controls: **45 members,
592,028 bytes**, with complete anonymous readback matching SHA256
`f6ab91257969c9195138655de53bade5148133371fda54b1c61dd45d2d4e4261`.
The separate feedback experiment is excluded from this frozen component capsule.

## Closed feedback with pump metal RC — 9 October 2026

The [actual native result](../hw/soc/pcie-evidence/20261009-feedback740-pump-wire/native-result.json)
passes the unchanged **740 device electrical screens and thirteen divider
predicates** over 34 ns with 108,847 samples at maximum 0.3125 ps spacing.
The loop contains 2,924 wire elements, including the pump's 84 resistors and
155 capacitors, and has no external VCTRL clamp. The zero-source operating point,
all 64 native HBT startup flags, clean diagnostics and full compressed raw-data
readback pass. The [postflight](../hw/soc/pcie-evidence/20261009-feedback740-pump-wire/postflight.json)
checks the actual deck and exact 1,236 observations / 1,237 transient columns,
and rejects clamp, held-reset, missing-vector and wrong-timestep faults.

| Window, ns | VCTRL minimum, V | VCTRL maximum, V |
| --- | ---: | ---: |
| 4–14 | 0.766871 | 1.008689 |
| 14–24 | 0.858230 | 1.035557 |
| 24–34 | 0.855486 | 1.018107 |

These are finite nominal startup measurements. PFD wire RC is absent from this
particular capture. The separate combined-wire run failed its finite prerequisites,
so its queued 200 ns continuation stopped without launching. PLL lock, PVT,
phase noise, BER, ESD and full serial PHY/main-chip integration are not accepted.

The [complete public capsule](../hw/soc/pcie-evidence/20261009-feedback740-pump-wire/delivery.json)
contains the exact campaign sources, complete raw observations, composition and
checks: **54 members, 996,004,517 bytes**. Full anonymous readback matches SHA256
`02302f7401db2536b8ae4051149839dae8eea7c8cb1c9e6f381ee51885fd25c7`.


## Compact row PFD repair — 9 October 2026

The [first combined pump/PFD wire capture](../hw/soc/pcie-evidence/20261009-feedback740-allwire-failed/native-review.json)
completed 108,847 samples but failed
`feedback_twenty_percent_duty`, `native_hbt_div4` and `whole_native_div80`.
HBT `xloop.xchain.xosc.xd0056` reached 3.004934 mA per emitter against the
unchanged 3 mA screen. In the 24–34 ns window the
[saved PFD device supplies](../hw/soc/pcie-evidence/20261009-feedback740-allwire-failed/rail-measurements.json)
reached 2.372721 V minimum and grounds 0.198583 V maximum with an ideal 2.5 V
external supply. UP reached only 0.967615 V, while DOWN stayed between
2.220125 and 2.727041 V. These measurements motivate shorter wiring and wider
supply metal; they do not establish rail bounce as the sole cause.

The new [row-layout generator](../hw/soc/flow/make_pcie_pfd102_row_v1.py)
places twelve devices per row, uses 8 µm supply buses and separate metal layers
for local buses and vertical trunks. The resulting macro is **824 × 2,184.03 µm**.
It preserves the 102 MOS devices and all 153 finite substrate/well contacts.
[Native checks](../hw/soc/pcie-evidence/20261009-pfd-row/native-layout.json)
report zero DRC markers across 560 categories, both hierarchical and flattened
255-device LVS matches, and rejection of five physical/reference faults.
[LEF checks](../hw/soc/pcie-evidence/20261009-pfd-row/lef-controls.json)
verify eight pins and two corrupted physical views. The generator uses the
alternative macro's existing top-cell name; both versions must not be loaded
into one library under the same name.

[Source reproduction](../hw/soc/pcie-evidence/20261009-pfd-row/source-equivalence.json)
compares every layer union and transformed text label, LEF, schematic and
placement records with the checked prototype. GDS timestamps differ, so this
is geometry equality, not byte equality. New native LVS device identities
are rebound to the new geometry; old instance numbering is not reused.
The [binding controls](../hw/soc/pcie-evidence/20261009-pfd-row/binding-controls.json)
reject eight actual changes.

The [new extraction](../hw/soc/pcie-evidence/20261009-pfd-row/wire-audit.json)
contains **776 resistors and 1,296 capacitors**. Exact resistor topology/values,
capacitor attachments and the collapsed matrix pass, with
[thirteen raw faults rejected](../hw/soc/pcie-evidence/20261009-pfd-row/wire-faults.json).
Dropping a resistor in this new topology opens its graph before value comparison;
the mutation fixture now expects that specific failure, with the checker unchanged.
[Composition controls](../hw/soc/pcie-evidence/20261009-pfd-row/composition-controls.json)
retain all 255 device and 2,072 wire records and reject six corruptions.

A fresh 740-device feedback simulation now contains this row PFD, the physical
pump wire model and 4,996 total wire elements. Its first finite capture was miswired by an extracted-port-order change; see
the boundary correction below. The unchanged electrical/divider criteria must
pass on the corrected instance before longer acquisition or electrical adoption. The geometry results do not qualify RC accuracy,
PLL lock, CDR, serial Gen3 operation or a complete PHY layout.

The [complete component capsule](../hw/soc/pcie-evidence/20261009-pfd-row/delivery.json)
contains 148 members / 1,591,809 bytes. Full anonymous readback matches SHA256
`b26bd4bef1edfa97dd8d78dbf2a4e5c84d58968f3755be5889aa92c5746dd2d5`.
The active full-loop run is excluded from this frozen component archive.


## Short local PFD buses — 9 October 2026

A [second layout generator](../hw/soc/flow/make_pcie_pfd102_local_v2.py)
removes the global-bus extension from internal signals used in only one row.
Only 29 of the 57 conductors need global trunks. Device pitch and all finite
contacts remain unchanged; the row pitch drops from 260 to 160 µm and the
left routing corridor shrinks. The resulting macro measures **654 × 1,384.03 µm**.
It uses the same top-cell name as the alternative PFD layouts and must be
selected as one alternative, not loaded alongside them into the same library.

The [native physical checks](../hw/soc/pcie-evidence/20261009-pfd-local/native-layout.json)
again pass all 560 DRC categories with zero markers and both hierarchical and
flattened 255-device LVS. All five physical/reference faults are rejected.
[LEF checks](../hw/soc/pcie-evidence/20261009-pfd-local/lef-controls.json)
verify eight public pins and reject two faults; the
[source reproduction](../hw/soc/pcie-evidence/20261009-pfd-local/source-equivalence.json)
matches every geometry layer and recursive label, LEF, schematic and placements.

[New native device binding](../hw/soc/pcie-evidence/20261009-pfd-local/binding-controls.json)
rejects eight corruptions. The [wire audit](../hw/soc/pcie-evidence/20261009-pfd-local/wire-audit.json)
retains **771 resistors and 1,256 capacitors**, with all 467 terminal/port probes
connected to their actual physical conductors. Thirteen
[raw extraction faults](../hw/soc/pcie-evidence/20261009-pfd-local/wire-faults.json)
and six [composition faults](../hw/soc/pcie-evidence/20261009-pfd-local/composition-controls.json)
are rejected. The sum of ground and mutual capacitances, counting each edge
once, falls from 9.269185 to 7.353597 pF in this unqualified extraction model.
This aggregate decrease is not a timing or signal-integrity acceptance result.

The new 740-device loop includes 4,951 wire elements and all 1,647 observations.
Its first launch stopped at the CPU-affinity guard because the guard still
expected CPU14 after the launcher selected free CPU10; ownership cleanup reaped
that process. Its second run corrected that guard, but was subsequently stopped
after the PFD instance pin-order defect below was found. Both failures and their
partial captures are retained. Neither run validates the new layout electrically.

The [local-bus component capsule](../hw/soc/pcie-evidence/20261009-pfd-local/delivery.json)
contains the geometry, generator, native extraction and controls, with complete
anonymous SHA256 readback. Active loop simulations are excluded from this archive.
The [failed all-wire capture](../hw/soc/pcie-evidence/20261009-feedback740-allwire-failed/delivery.json)
is separately preserved in full: 94 members / 1,334,985,869 bytes, SHA256
`5cb49361abd75209e909d5f26d99535881a2a8dd6dea6221eb9e7d1a13824151`.
An HTTP500 interrupted its first readback; missing ranges were retried and the
entire ordered digest verified. Its publication success does not change its
failed electrical verdict. Full serial PHY and final chip timing remain open.

The documentation links a compact failed-capture review to stay within the
existing site asset budget. Its full native-result digest and capsule member
are recorded; complete device records and waveforms remain in the public archive.


## PFD macro boundary correction — 9 October 2026

Native extraction reordered the compact row/local PFD ports from
`sub vdd ref fb reset vss up down` to `sub vdd ref vss up fb down reset`.
The first two new-layout loop compositions had copied the old positional
instance. This connected the new PFD's VSS to the reference pulse and exchanged
reset/output/feedback connections. The completed row capture and cancelled
local capture are **invalid layout comparisons**, not evidence against either
new geometry. The earlier linear-PFD all-wire failure used its correct pin
order and remains a separate valid failed experiment.

The new [independent boundary checker](../scripts/check_pcie_pfd_instance.py)
compares the actual extracted declaration and loop instance by pin name.
It requires the established negative-VCO-slope polarity (`PFD.ref → loop.fb`,
`PFD.fb → loop.ref`), correct supplies, reset, UP/DOWN and separate capacitance
reference. Corrected composition now derives its argument order from that
declaration rather than inheriting another layout's order.

Ten [regression tests](../sw/tests/test_pcie_pfd_instance.py) include the exact
miswired call, missing/duplicate interfaces, power/reset/polarity/output swaps,
and a consistently permuted declaration and call. Both corrected native inputs
pass the [row](../hw/soc/pcie-evidence/20261009-pfd-boundary/row-controls.json)
and [local](../hw/soc/pcie-evidence/20261009-pfd-boundary/local-controls.json)
controls: five real incorrect bindings fail and the matched permutation passes.
The [invalid local run](../hw/soc/pcie-evidence/20261009-pfd-boundary/invalid-local-cancellation.json)
was stopped using the recorded parent PID and birth identity; its owner reaped
the native child. Fresh row/local 740-device simulations retain the original
stimuli, electrical/divider acceptance criteria and sample/storage limits.
Their completed electrical results are recorded below.


## Corrected feedback failures and four-times-area filter — 9 October 2026

The corrected [row](../hw/soc/pcie-evidence/20261009-bindfix-c4-hold/row-failure.json)
and [local](../hw/soc/pcie-evidence/20261009-bindfix-c4-hold/local-failure.json)
740-device, 34 ns simulations both finish with clean diagnostics, full compressed
capture readback and passing device electrical screens. **Both transient verdicts
fail.** The row case fails feedback duty and the native /4 and /80 predicates;
the local case additionally fails received-to-feedback counting. The local
feedback duty is 17.5523% and 16.5324%; the second interval is outside the unchanged
17–23% screen. The prepared 200 ns continuation stopped at its failed prerequisite.

Complete failed captures are public with anonymous whole-file SHA256 readback:
[row delivery](../hw/soc/pcie-evidence/20261009-bindfix-c4-hold/row-delivery.json)
and [local delivery](../hw/soc/pcie-evidence/20261009-bindfix-c4-hold/local-delivery.json).
No threshold was relaxed and publication does not change either verdict.

A separate [physical filter candidate](../hw/soc/flow/make_pcie_pump_filter13_c4_v2.py)
increases the MIM capacitor from 10 × 10 to 20 × 20 µm. Its
[native DRC/LVS](../hw/soc/pcie-evidence/20261009-bindfix-c4-hold/pump-native.json)
passes with zero errors across 560 DRC categories and 30-device hierarchical
and flat LVS; five actual faults are rejected. The
[LEF check](../hw/soc/pcie-evidence/20261009-bindfix-c4-hold/pump-lef.json)
passes with two faults. Extraction is regenerated from the new geometry,
including changed internal node identities. The
[binding controls](../hw/soc/pcie-evidence/20261009-bindfix-c4-hold/pump-binding.json)
reject nine corruptions, including reverting the capacitor area. The
[wire audit](../hw/soc/pcie-evidence/20261009-bindfix-c4-hold/pump-wire.json)
and [composition](../hw/soc/pcie-evidence/20261009-bindfix-c4-hold/pump-composition.json)
retain all 84 resistors and 155 capacitors. RC remains unqualified.

The [component capsule](../hw/soc/pcie-evidence/20261009-bindfix-c4-hold/pump-delivery.json)
contains 142 members / 431,798 bytes, SHA256
`2b47ae162480c21367096566b09b76e488607071a33843e20685799e871d1feb`.
The connected 740-device test has now **failed**. Its
[finite review](../hw/soc/pcie-evidence/20261009-feedback-levelshift/c4-failure-review.json)
retains all electrical and divider predicates. Six VCO HBTs exceed the original
3 mA/finger screen: measured peaks are 3.800–3.878 mA/finger, mainly around
1.04–1.13 ns. The [current diagnosis](../hw/soc/pcie-evidence/20261009-feedback-levelshift/c4-current-diagnosis.json)
locates these events while the control voltage is still about 0.36 V. Feedback
duties are 16.943% and 16.820%, below the unchanged 17% lower bound. The native
/4 and /80 checks also fail. The capacitor candidate is **not adopted**, and
its failed prerequisite does not authorize a longer acquisition run.

The [complete failed capture](../hw/soc/pcie-evidence/20261009-feedback-levelshift/c4-failure-delivery.json)
contains 68 members / 1,329,822,510 bytes, with verified anonymous readback SHA256
`83c3e5fd550b9bbdb88a270431b4b923c4ba59ef6c365a8701db63e506344d70`.
Component DRC/LVS success does not override this connected electrical failure.

### Physical feedback level shifter — 9 October 2026

A [measurement of the original feedback waveform](../hw/soc/pcie-evidence/20261009-feedback-levelshift/duty-diagnosis.json)
shows the rising count-to-feedback edge delayed about 1.53 ns, versus about
1.10–1.14 ns for the falling edge. A separate candidate doubles the two
LV-driven HV NMOS widths from 4 to 8 µm, retaining the other devices and the
original 10 × 10 µm pump capacitor. This is an experiment, not an accepted PLL.

The [physical cell](../hw/soc/flow/make_pcie_feedback_levelshift6_v1.py)
contains six MOS devices and nine finite contacts. Its
[native checks](../hw/soc/pcie-evidence/20261009-feedback-levelshift/native-layout.json)
pass 560 DRC categories with zero errors and both hierarchical and flat
15-device LVS. Five actual geometry/reference faults are rejected.
The [LEF check](../hw/soc/pcie-evidence/20261009-feedback-levelshift/lef-controls.json)
rejects missing and blocked pins; the initial wrong fault-target attempt is
preserved separately in the capsule. An
[independent model binding](../hw/soc/pcie-evidence/20261009-feedback-levelshift/binding-controls.json)
checks actual native terminals and parameters and rejects eight corruptions.

The [component capsule](../hw/soc/pcie-evidence/20261009-feedback-levelshift/component-delivery.json)
contains 104 members / 250,037 bytes, anonymously verified against SHA256
`e3334905c3e544c78c562f4efcbbe14033ef391038d440e60d3a9ec3bf40175b`.
Separate 740-device schematic and 749-device native-cell finite simulations are
running. The latter retains all 734 other devices and 4,951 existing wire
records; this first native-cell run excludes the new level shifter's own wire RC.
New wire extraction is being audited separately. Neither experiment establishes
PLL lock, PVT/RF qualification, full physical PLL integration or a serial Gen3 x4 PHY.


The level-shifter's separate [wire audit](../hw/soc/pcie-evidence/20261009-feedback-levelshift/wire-audit.json)
now preserves all **44 resistors and 79 capacitors** across eight physical metal
conductors. All 42 native terminals are accounted for: 27 have geometrically
verified metal reference points, and 15 retain their intrinsic body/well
identities without a substrate-spreading model. Seven public ports bring the
reference-point count to 34. Every native resistor, point capacitance and mutual
attachment is checked; no intrinsic alias is used to conceal a wire open.
[Thirteen raw corruptions](../hw/soc/pcie-evidence/20261009-feedback-levelshift/wire-faults.json)
and [six device/wire composition faults](../hw/soc/pcie-evidence/20261009-feedback-levelshift/wire-composition.json)
are rejected. This extraction remains **unqualified for RF/signoff**.

The [complete wire/component capsule](../hw/soc/pcie-evidence/20261009-feedback-levelshift/wire-delivery.json)
has 141 members / 326,796 bytes, anonymously verified against SHA256
`917126d1a1a609388922564dff64bd899e4a03c23b9c478129f116baf3b5e4bd`.
A separate connected 749-device experiment includes these wire records and all
4,951 preceding wire records, with 1,677 saved observations. The new capacitance
reference has its own explicit external 0 V source and is passed through each
hierarchy boundary; 28 pin swaps and four reference-hop corruptions are rejected.
The full 34 ns transient, all-device screens and original divider checks are
still running. No PLL or full-PHY acceptance follows from source composition.


### Physical CML-to-LV receiver — 9 October 2026

The [receiver generator](../hw/soc/flow/make_pcie_feedback_receiver19_v1.py)
implements the unchanged 19-device receiver schematic with 19 substrate and
five well contacts: **43 actual native devices**. The schematic's unused AVDD
argument is omitted from the six-port macro; CVDD powers the receiver. The
source expansion explicitly checks that no device uses the omitted argument.
The first layout passed DRC but failed LVS because its short LV transistor
source/drain escapes overlapped. Extending Metal1 outward before escaping to
Metal3 fixes this physical short; failed geometry and reports are retained.

The [final native controls](../hw/soc/pcie-evidence/20261009-feedback-receiver/native-layout.json)
pass 560 DRC categories, hierarchical and flat 43-device LVS, and reject five
actual reference/geometry faults. [Native OpenROAD LEF checks](../hw/soc/pcie-evidence/20261009-feedback-receiver/lef-controls.json)
pass all six ports and reject missing/blocked pins.
The [model binding](../hw/soc/pcie-evidence/20261009-feedback-receiver/binding-controls.json)
rejects eleven corruptions, including a 1 nm width change, changed MIM geometry
and off-grid native geometry. Binary floating-point serialization noise is
rounded to the pinned 1 nm geometry grid only within two binary ULPs; other
changes are rejected. Finite contacts and native terminal identities are retained.

The [wire audit](../hw/soc/pcie-evidence/20261009-feedback-receiver/wire-audit.json)
accounts for all 116 native terminals: 74 metal references and 42 intrinsic
body/well references. Six public ports give 80 geometrical probes on 15 physical
conductors. All **121 resistors and 201 capacitors** survive export and device
composition. [Thirteen raw corruptions](../hw/soc/pcie-evidence/20261009-feedback-receiver/wire-faults.json)
and [six composition corruptions](../hw/soc/pcie-evidence/20261009-feedback-receiver/wire-composition.json)
are rejected. Substrate spreading and RF distribution remain unqualified.

The [complete source/layout/binding/wire capsule](../hw/soc/pcie-evidence/20261009-feedback-receiver/delivery.json)
contains 239 members / 855,218 bytes. Anonymous complete readback verifies SHA256
`85a04584c40a2fb95a50be79a5c9bd3c50c91e081589b57ed377f3156db68ceb`.
A new connected 773-device experiment incorporates this receiver and all
5,396 wire records. It retains 1,749 saved observations and the original device
screens and 13 divider checks. The first dispatch was stopped because its copied
final screen census still expected 749 devices; the failed attempt and sources
are preserved. A fresh corrected attempt is running. Physical receiver success
is not full PLL layout, acquisition, CDR or serial Gen3 x4 acceptance.


### Stronger feedback level shifter: duty fixed, divider acceptance still fails

The [34 ns connected-feedback result](../hw/soc/pcie-evidence/20261009-feedback-leveldrive/review.json)
keeps the original 740-device electrical screens and thirteen divider predicates.
Increasing only the two level-shifter NMOS widths from 4 to 8 µm restores the
measured feedback duties to **21.4371% and 20.8014%**. All 740 electrical screens
and eleven divider predicates pass, but the native /4 and whole /80 checks fail.
The /4 interval census includes one five-cycle and one three-cycle interval;
the /80 census is **81, 80**. No acquisition continuation is accepted from this run.

The [saved-waveform phase diagnostic](../hw/soc/pcie-evidence/20261009-feedback-leveldrive/phase-diagnostic.json)
finds four-cycle nearest-edge ordinal steps for /4, with phase from −4.951 to
+1.159 ps. This helps locate the interval-boundary sensitivity but does not
replace the failed original predicate or establish correct division under all
conditions. The /80 nearest-edge steps are 81 and 79; its remaining error cannot
be dismissed as successful PLL lock. VCTRL spans 0.66984–0.83850 V in the final
24–34 ns window. Physical level-shifter and receiver variants are being measured
separately with their native contacts and wire parasitics.

The [complete failed-candidate capsule](../hw/soc/pcie-evidence/20261009-feedback-leveldrive/delivery.json)
contains 64 members / 1,330,181,228 bytes. Anonymous full readback verifies SHA256
`f69d9b1b31eb5ecf4bd48d628a22e8cd3d07880de91f53a2d61178ca6c1eb409`.
The [source/zero-source-OP postflight](../hw/soc/pcie-evidence/20261009-feedback-leveldrive/postflight.json)
passes without overriding the transient failure. Full PLL acquisition, PVT,
physical-parent integration and serial Gen3 x4 remain open.


### Feedback DFF physical prerequisite — geometry passes, speed screen fails

The [new DFF generator](../hw/soc/flow/make_pcie_feedback_dff48_v1.py)
preserves the existing 48-device LV flip-flop and adds 48 substrate and 22 well
contacts: **118 native devices**. Its initial layout failed four TopMetal1 width
checks at the small MIM top electrodes. Extending routing metal over the entire
electrode fixes the narrow connection without changing the MIM dielectric area.
The [corrected layout](../hw/soc/pcie-evidence/20261009-feedback-dff/native-layout.json)
passes all 560 DRC categories, deep/flat LVS and five actual fault controls.
The [eight-port LEF](../hw/soc/pcie-evidence/20261009-feedback-dff/lef-controls.json)
passes native loading and missing/blocked-pin controls.

The [118-device compact-model binding](../hw/soc/pcie-evidence/20261009-feedback-dff/binding-controls.json)
rejects eleven terminal/parameter faults. The [wire audit](../hw/soc/pcie-evidence/20261009-feedback-dff/wire-audit.json)
retains 357 resistors and 597 capacitors across 28 conductors, with 210 metal
terminal references, 114 intrinsic body/well references and eight public ports.
Thirteen raw corruptions and six composition faults are rejected. This remains
unqualified interconnect extraction, with no spatial substrate model.

**The physical DFF is not accepted for the feedback chain.** Its
[12 ns, 2 GHz component screen](../hw/soc/pcie-evidence/20261009-feedback-dff/finite-review.json)
passes all 118 electrical screens but fails to transmit alternating data. The
output never reaches 0.6 V; its maximum is about 0.327 V. A held-reset fault also
fails the functional checks. Layout/LVS success therefore does not establish
clock-rate functionality.

The [same native devices without wire RC](../hw/soc/pcie-evidence/20261009-feedback-dff/schematic-review.json)
do toggle, but fail the original 150–200 ps post-edge settling aperture and one
all-sample voltage screen (about 1.510 V against the existing 1.5 V limit).
A [vendor DFF plus inverter comparison](../hw/soc/pcie-evidence/20261009-feedback-dff/standard-cell-review.json)
passes its electrical screens but also misses that settling aperture. Its first
attempt failed because the safety parser required micrometre spelling whereas
the vendor uses nanometres; the corrected attempt preserves exact SI values and
the vendor schematic. Neither comparison changes the original failed verdict
or qualifies a replacement counter.

The [complete source, layout, wire and finite-failure capsule](../hw/soc/pcie-evidence/20261009-feedback-dff/delivery.json)
contains 232 members / 217,968,926 bytes. Anonymous complete readback verifies
SHA256 `4682a69ad17041260ff9446d8fc0f0f1729675b62bd83c42dbb6cc92e7027f38`.
The failed geometries, failed parser prefix, full waveforms and IHP source notice
are retained. Compact physical placement and full-chain clock-rate validation
remain necessary before integrating a counter macro into the PLL.


### Connected native level shifter: loading moves the remaining failure

Both 749-device, 34 ns connected-feedback runs have completed and retain their
failed overall verdicts. Without the new cell's wire RC, all electrical screens
pass and duties are 21.4369%/20.8011%, but the /4 and /80 checks still fail. See the
[physical-cell review](../hw/soc/pcie-evidence/20261009-feedback749/physical-review.json).

With all 44 R / 79 C records included, the [wire-loaded review](../hw/soc/pcie-evidence/20261009-feedback749/wire-review.json)
passes every electrical screen and twelve of thirteen divider predicates. The
/4 census is consistently four and the /80 census is **80, 80**. Feedback duties
are 22.3981%/22.3657%. The remaining failure is `state_logic_rails`: the modulo-five
count output is still about **0.416–0.422 V** at three state-zero sample points,
above the unchanged 0.20 V low-level bound. Correct interval counts cannot waive
that logic-level failure. The final 24–34 ns VCTRL range is 0.85343–0.87758 V;
this finite observation does not establish lock or acquisition.

Actual native PFD/pump boundaries and source/zero-source-OP postflights pass.
The [complete physical-cell capture](../hw/soc/pcie-evidence/20261009-feedback749/physical-delivery.json)
and [complete wire-loaded capture](../hw/soc/pcie-evidence/20261009-feedback749/wire-delivery.json)
are published with anonymous whole-file SHA256 verification. A separate candidate
changes only the count output's two series NMOS widths from 1.12 to 2.24 µm;
all other 747 devices, 5,074 wire records and acceptance limits remain unchanged.
The completed finite result of that candidate is recorded below.


### Receiver loading isolated with an identical saved input — 9 October 2026

The [773-device connected physical-receiver run](../hw/soc/pcie-evidence/20261009-receiver-loading/connected773-review.json)
fails its functional checks despite passing all electrical screens. In its final
24–34 ns window, the receiver clock spans only 0.897–1.031 V. The
[device-node diagnostic](../hw/soc/pcie-evidence/20261009-receiver-loading/connected773-node-diagnostic.json)
finds severe attenuation between the CML inputs, differential-pair gates and
AC-coupled inverter input. The source/zero-source-OP postflight passes; it does
not override the failed transient. Its [complete failed capture](../hw/soc/pcie-evidence/20261009-receiver-loading/connected773-delivery.json)
contains 72 members / 1,378,636,774 bytes, with anonymous full readback matching
SHA256 `be5db132b90912baf6b94079c338de41784711ef6f40b64110a1650cfbf3d022`.

A separate comparison replays the exact saved 749-device CML, supply and reset
waveforms through 12 ns, without downsampling. Each case contains the actual
43-device receiver and the same 48-device schematic toggle load. Only the
receiver geometry/interconnect representation changes. Functional checks require
one receiver edge per input period, divide-by-two operation and full logic swing;
all 91 device screens remain enabled.

| Receiver representation | Clock range at 4–12 ns | Functional result |
| --- | ---: | --- |
| [Original wire layout](../hw/soc/pcie-evidence/20261009-receiver-loading/original-review.json) | 1.176–1.199 V | Fail: no clock edges |
| [Shorter buses and relocated pins](../hw/soc/pcie-evidence/20261009-receiver-loading/short-review.json) | 1.080–1.197 V | Fail: no clock edges |
| [Clustered devices, 24 µm pitch](../hw/soc/pcie-evidence/20261009-receiver-loading/cluster-review.json) | 1.131–1.199 V | Fail: no clock edges |
| [Same native compact devices, no wire RC](../hw/soc/pcie-evidence/20261009-receiver-loading/compact-review.json) | −0.00028–1.191 V | Pass: all four checks |

All four cases pass their electrical screens. This isolates an interconnect-loading
problem in this fixture; the ideal voltage replay does not reproduce source
impedance or qualify the coupled PLL. The compact positive control is not a
physical-layout acceptance result.

The [corrected clustered layout](../hw/soc/pcie-evidence/20261009-receiver-loading/cluster-layout.json)
passes 560 DRC categories, deep/flat LVS and five actual faults; its
[LEF controls](../hw/soc/pcie-evidence/20261009-receiver-loading/cluster-lef.json) also pass.
An earlier compressed-lane prototype accidentally shared gate/substrate routes;
LVS rejected it and its files remain in the evidence. The corrected
[123 R / 199 C extraction](../hw/soc/pcie-evidence/20261009-receiver-loading/cluster-wire-audit.json)
and [six composition faults](../hw/soc/pcie-evidence/20261009-receiver-loading/cluster-composition-controls.json)
pass. Smaller ground capacitance does not ensure bandwidth: the
[role-bound capacitance comparison](../hw/soc/pcie-evidence/20261009-receiver-loading/wire-capacitance-diagnostic.json)
also records increased coupling at several internal nodes. RF/substrate and
signoff extraction remain unqualified.

The [complete replay/layout comparison capsule](../hw/soc/pcie-evidence/20261009-receiver-loading/comparison-delivery.json)
contains 416 members / 887,885,528 bytes. Anonymous full readback matches
SHA256 `23bae7c78ddaf434339c24f2794589d1beecbd46fa8125e61b54b7babad348fa`.
It retains full waveforms, the failed 50,000-row attempt and its fresh 200,000-row
retry; no electrical or functional threshold was relaxed. Further spacing and
receiver-drive candidates are separate experiments, not accepted PHY integration.


### Count output repair passes the original 749-device finite screen

The [completed 34 ns result](../hw/soc/pcie-evidence/20261009-feedback749-count/finite-review.json)
passes all **749 electrical screens and thirteen divider predicates**. The only
device change from the preceding wire-loaded candidate is the two series NMOS
widths in the modulo-five output NAND: 1.12 → 2.24 µm. The
[change controls](../hw/soc/pcie-evidence/20261009-feedback749-count/change-controls.json)
retain every other device, all 5,074 wire records, the source/reset waveforms and
the original acceptance criteria.

The three state-zero count samples improve from approximately 0.416–0.422 V to
**0.02828, 0.02796 and 0.02873 V**, below the unchanged 0.20 V limit. Native /4
intervals are consistently four, whole /80 intervals are **80, 80**, and feedback
duties are 21.6468% and 21.6049%. Final-window VCTRL spans 0.85343–0.87756 V.
These finite observations establish neither lock nor acquisition.

The [native source/zero-source-OP postflight](../hw/soc/pcie-evidence/20261009-feedback749-count/postflight.json)
and actual [PFD](../hw/soc/pcie-evidence/20261009-feedback749-count/pfd-boundary.json)
and [pump](../hw/soc/pcie-evidence/20261009-feedback749-count/pump-boundary.json)
instance-boundary checks pass. The [complete passed capture](../hw/soc/pcie-evidence/20261009-feedback749-count/delivery.json)
contains 67 members / 1,355,127,810 bytes, with anonymous full readback matching
SHA256 `accaee9c1b6a99b8e2f2593cef5d699a63e8f686a6d862140ceb9ec85879c136`.

The separate 200 ns continuation has completed with failures. Its
[preflight comparison](../hw/soc/pcie-evidence/20261009-feedback749-count/continuation-controls.json)
requires byte-identical native model files and a deck differing only in the
transient stop time. All device/wire records, sources, 0.3125 ps maximum timestep
and electrical/functional thresholds remain unchanged. Storage bounds are
700,000 rows, 12 GiB per point and 14 GiB aggregate, with no elapsed-time timeout.
The longer result fails /4 and /80 counting and the strict clean-diagnostic gate;
see the long-response result below. This 749-device chain still uses a schematic
receiver/counter alongside physical subblocks; it is not a completed physical
PLL parent, serial Gen3 x4 PHY or final main-chip timing result.

### Physical receiver route correction passes loaded replay — 9 October 2026

The `ordered` receiver retains the paired layout's nineteen core devices,
twenty-four finite contacts and all device sizes. It routes `pre`, `mid`, `gate`,
`gain`, `ip` and `inn` on the nearest available bus rows, shortening the sensitive
amplifier connections. Native component DRC, deep/flat transistor LVS, five
actual geometry/reference faults, six-port LEF and its two fault controls pass.
Native binding and wire-graph/composition controls also pass. The extracted
model retains **123 resistors and 193 capacitors**; this is not qualified RF PEX.

With the same saved input excitation and actual 48-device flip-flop load, all
four replay criteria and all **91 electrical screens** pass: one receiver edge
per input period, correct divide-by-two operation and full logic swing. Clock
voltage spans **0.08325–1.19990 V** over the unchanged 4–12 ns window. The prior
paired candidate failed early edges and low-level swing; reducing only the
self-bias resistor also failed, so neither is adopted.

The [complete passed physical-receiver capsule](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-receiver-ordered-passed-20261009.tar.gz)
contains 170 members / 239,487,059 bytes, with complete anonymous readback matching
SHA256 `a642d986c72d09aafa28b8f547540e8d4762a8aad91a8deb43bb04e7402be3c2`.
It includes generator/source, GDS/LEF, native comparisons, fault controls, wire
models, complete waveform and device screens. The
[five preceding failed physical candidates](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-receiver-sized-comparison-20261009.tar.gz)
are preserved separately: 919 members / 1,166,489,004 bytes, complete anonymous
readback SHA256 `7975acf871e78d568e3b4bb3b78b63411db867c8005a463fd693507915b3d9bd`.
The uniformly scaled candidate additionally fails the unchanged 10 µm MOS model
width bound; its 11.84 µm tail device is not accepted.

A new 773-device connected-loop run combines this receiver with the passing
749-device count-drive parent. All other 730 devices and all 5,074 parent wire
records are preserved; total wire records become 5,390. Named instance-boundary
and native-deck fault controls pass before launch. The 34 ns transient is
running with real source loading, original supplies/reset/reference and no
control-voltage clamp. Saved-voltage replay success does **not** establish this
connected result, a physical PLL parent, lock/PVT qualification or a Gen3 x4 PHY.

### Completed older 570-device one-microsecond response — 9 October 2026

The earlier 570-device chain reaches the exact 1 µs endpoint with 3,201,211 raw
rows and verified compression readback. All device electrical screens pass,
but the original strict /4 and /80 edge-count checks fail. Of 1,974 /4 intervals,
1,757 contain four VCO periods, 109 contain five and 108 contain three; 97 /80
intervals contain eighty periods and one contains eighty-one. These failures
are retained, not converted into lock acceptance.

The native clean-diagnostic gate also rejects ngspice's memory-estimate warning:
its estimated full in-memory waveform exceeds then-available DRAM. The complete
streamed capture remains available; its original status is
`ERROR_NATIVE_OR_CAPTURE`. A separate, byte-verified diagnostic review of the
unchanged record measures 800–1,000 ns: feedback **99.993005 MHz**, VCO
**7.999302 GHz**, feedback frequency error **−69.95 ppm**, and unwrapped phase
change **−0.001387 cycles**. VCTRL still spans **0.55852–0.79228 V**. Neither these
nominal measurements nor the observed convergence override the failed checks.
Complete large-waveform publication is in progress as ordered byte parts; the
newer 749-device, wire-loaded 200 ns run is a separate failed experiment,
reported below.

### Ordered receiver in the actual closed loop — 9 October 2026

The ordered receiver's successful 91-device saved-voltage replay did **not**
carry over to a passing 773-device closed-loop startup. The actual 34 ns capture
has clean native diagnostics and all 773 electrical screens pass, but two of
thirteen divider checks fail. The first measured CML-to-receiver interval
contains two input cycles. Only two feedback rising edges occur within the
window, below the existing minimum of three; the single measurable interval
contains exactly 80 VCO cycles. This is insufficient evidence for division
acceptance, rather than a measured non-80 interval.

An independent whole-wave byte/payload review finds receiver output minima of
0.613 V at 4–4.5 ns and 0.515 V at 4.5–5 ns, followed by fuller swing later.
Actual deck, zero-source operating point, all saved vectors, startup flags and
named pump/PFD boundaries pass their separate checks. The failed functional
verdict is unchanged. The [complete failed 773-device capture](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-feedback773-ordered-failed-20261009.tar.gz)
contains 83 members / 1,414,076,786 bytes, with complete anonymous readback SHA256
`c07eb430e9b03e3f6a4b4d65b80f2e5ed3ef0c289ce65abbaad47b475e62ba8d`.

Reducing the ordered receiver's self-bias resistance fails the loaded replay
(0.343 V minimum clock level); reducing the second inverter NMOS width by 25%
also fails (0.550 V maximum clock level). Both retain passing electrical screens.
A smaller, 3.125% width reduction, 5.92 to 5.735 µm, passes native component
DRC/LVS, binding/wire checks and all four loaded-replay predicates, with clock
swing 0.042075–1.197579 V. Its subsequent actual 773-device, 34 ns run passes
all electrical screens and twelve of thirteen divider predicates with clean
native diagnostics. CML-to-receiver edge counting now passes. The sole failed
predicate requires at least three feedback rising edges: two were captured,
and the measured interval contains exactly 80 VCO cycles. The failed verdict
is retained. The same circuit's 50 ns continuation now passes all 773
electrical screens and all thirteen divider predicates, with clean native
diagnostics and complete compressed capture readback. Three measured feedback
intervals each contain exactly 80 VCO cycles. Sources, timestep, minimum edge
count and acceptance thresholds are unchanged; five continuation faults and
four actual-deck faults are rejected. Actual named PFD/pump boundaries and
postflight checks pass. This finite nominal result does not establish PLL lock,
PVT or full serial PHY acceptance; the two fast CMOS toggles remain schematic.

The [short failed capture](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-feedback773-trim-short-failed-20261009.tar.gz)
is retained as an 83-member / 1,414,347,338-byte capsule with full anonymous
readback SHA256
`f0c3194003517bd85195f243775b0458d8cbc2537b900493b1f51d9ba96b4d47`.
The [complete passing 50 ns capture](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-feedback773-trim-long50-passed-20261009.tar.gz)
is also fully read back anonymously: 77 members / 2,082,934,478 bytes, SHA256
`213ddd83fe811d90eb415561ea853b9e788fc7bf821bd2aea894e68559015097`.

### Physical standard-cell toggle with metal RC — 9 October 2026

A separate feedback-connected divide-by-two macro combines the frozen IHP
`sg13g2_dfrbpq_2` and `sg13g2_inv_1` cells. Native extraction produces 36 MOS
fingers, including both physical fingers of the two double-finger output
devices. The reference preserves total widths; native simulation retains
extracted junction areas and perimeters. Body terminals retain the actual
VSS/VDD connections. A metal reset strap joins two reset metal islands that
were previously connected only through polysilicon. The final `layout05`
passes all 560 enabled DRC categories with zero violations, deep and flat
36-device LVS, and five deliberate faults: wrong width, missing finger,
open output connection, shorted outputs and a one-nanometre off-grid shift.

The wire model contains all **70 resistors and 167 capacitors**. Its terminal
mapping preserves 104 logical references at 66 distinct physical contact
points; only geometrically identical points share an extraction port.
Shared diffusion terminals and native salicide-abutted source/tap connections
are identified from actual geometry. Thirteen raw extraction corruptions and
six composed-SPICE faults are rejected. This is metal RC from the experimental
Magic technology; intrinsic electrode/body spreading resistance and qualified
foundry PEX remain outside its scope.

The 12 ns transistor transient of this physical macro, including all metal RC,
passes all 36 electrical screens and actual division by two at a 2 GHz input.
Twenty output windows, 300–450 ps after each input edge, pass, and each of ten
measured output intervals contains two input clocks. Holding reset active
correctly fails both functional predicates while passing electrical screens.
This **does not repair or replace** the earlier general-DFF 150–200 ps aperture
failure. The test uses internal feedback D=QB and an external clock; it is not
a PLL, PVT, jitter, full serial PHY or main-chip timing acceptance.

The [complete standard-cell toggle development capsule](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-std-toggle36-metal-rc-20261009.tar.gz)
preserves failed prefixes, original aperture failures, physical sources,
IHP source notice, raw extraction and full finite waveforms: 444 members /
181,765,679 bytes, complete anonymous readback SHA256
`4296e0155e8dc0b73df3c596435fe54108840c05cb37e599d14daad550ddfe24`.

A new connected experiment replaces only the first 48-device schematic toggle
by these 36 extracted devices and 237 wire elements. The resulting chain has
761 devices and 5,627 wire elements; all other device and wire records are
unchanged. Named pin and capacitor-reference boundary checks reject swaps
before simulation. Initial harness failures (CPU-affinity guard and a missing
wire-only clock observation) are preserved. The fresh run records that actual
clock conductor explicitly and uses 1,787 columns. The completed 50 ns run
now passes all 761 electrical screens and all thirteen divider checks, with
clean diagnostics and complete compressed readback. Three feedback intervals
each contain exactly 80 VCO cycles. Actual-deck postflight and independently
checked PFD, pump and physical-toggle boundaries pass. This establishes the
finite nominal loaded-chain result; the second fast toggle and modulo-five
counter are still schematic, and the separate MOS-corner failures below remain
open. There is no full physical PLL parent or serial PHY acceptance.

The [complete connected physical-toggle capture](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-feedback761-physical-fast0-passed-20261009.tar.gz)
contains 98 members / 2,124,562,697 bytes. Complete anonymous readback matches
SHA256 `2a18cbc6df436ee0c0dd70c921a02760477f68f794ff9ed1f46db0d08831e92d`.

The reusable [toggle layout generator](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/flow/make_pcie_feedback_toggle36_v1.py)
now emits a 15.360 × 6.370 µm GDS, a six-pin LEF and the explicit-finger LVS
reference from pinned PDK sources. Translation to a zero-origin outline
preserves every layer by XOR and preserves labels; the canonical output also
matches the independently generated abstract and reference. The
[native DRC/LVS checker](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/flow/check_pcie_feedback_toggle36_v1.py)
retains the five physical/reference faults. The
[OpenROAD LEF checker](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/flow/check_pcie_feedback_toggle36_lef.py)
checks pin rectangles, directions, power uses and obstruction clearance, and
rejects missing pins, obstructed pins and changed outlines. These are component
checks; the macro has not yet been placed and routed into the full PLL parent.
The [canonical geometry and native abstract checks](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-std-toggle36-abstract-20261009.tar.gz)
are public as a separate 171-member / 524,033-byte capsule. Complete anonymous
readback matches SHA256
`2a6bb03d96fc38d3a566c5fa488daa998069c0896f4c16013ef735040671793c`.

Subsequent MOS-corner screens **fail** with the same nominal metal RC and
2 GHz stimulus. At SS / 1.08 V / 125 °C, all 36 electrical screens pass, but
output intervals contain 5, 4, 5 and 5 input clocks instead of two, and the
300–450 ps output windows fail. At FF / 1.32 V / −40 °C, division and output
windows pass, but three transistor terminal differences reach 1.552698,
1.582365 and 1.587677 V, exceeding the unchanged 1.5 V screen. Held-reset
controls fail functionally as expected. The nominal macro therefore does
not qualify across these corners.

A separate schematic experiment uses the PDK `sg13g2_dfrbp_2` cell's native
complementary output directly for feedback. Its 34 device instances pass the
nominal test. At SS / 1.08 V / 125 °C, all electrical screens and division by
two pass, but the original output-window requirement still fails. This is
not an accepted physical replacement or a reason to relax the prior criteria.

The [complete MOS-corner and complementary-output experiments](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-toggle-mos-corners-20261009.tar.gz)
are public as 121 members / 179,440,385 bytes. Complete anonymous readback matches
SHA256 `f1de5133e26b63b87db5bfdfb3f9d71e66b84abcd3fb23b5de8b968e39324062`;
all failed corner verdicts remain unchanged.

### Second physical HBT prescaler experiment — 9 October 2026

An isolated 768-device experiment replaces the two schematic 48-device CMOS
fast toggles with a second instance of the existing physical 91-device HBT /4
macro. The chain is now /4 × /4 × /5 = /80. This moves the nominal CMOS counter
input from approximately 2 GHz to 500 MHz without an ideal internal clock.
Both HBT instances retain identical extracted devices and metal RC under an
independently checked node renaming; the first divider still drives the actual
second divider load. New body and wire reference ports are explicit fixture
assumptions. The resulting census is 98 HBTs, 768 native devices and 6,421 wire
records; all 1,921 observation vectors are retained.

Eight source/deck faults and five waveform-checker faults are rejected. The
50 ns / 0.3125 ps actual native transient has completed and **fails**. The second
macro receives about 2.36 V common mode; four of its HBTs have settled VCE below
0.08 V. The first divider's output swing collapses below 0.05 V, and no feedback
edges reach the PFD. All divider and feedback predicates remain failed.
The inherited startup checker also rejects the actual 98-HBT census because
it was fixed to 64; independent postflight verifies all 98 native OFF flags,
zero-source OP, and exact 768-device / 6,421-wire connectivity. That harness
limitation does not explain away the electrical and functional failures.

The [complete failed-run records and loading diagnosis](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-feedback768-div16-records-20261009.tar.gz)
are public: 542,134 bytes, complete anonymous SHA256 readback
`2161c2a88f10e4a57c0af4f0b88299965427555b34b2294438630cc2a8f850ec`.
The separate 2,234,985,696-byte waveform has completed byte-exact multipart
publication and full anonymous readback; the failed functional verdict remains.

A new 772-device experiment inserts two real Nx=2 NPN emitter followers and
two 1 × 3.6 µm PDK resistor sinks between the physical divider macros. The
original device and wire records are preserved except for the intentional
second-macro input connections. The added buffer is initially schematic;
its independent 160.000 × 137.030 µm GDS/LEF now passes all 560 main DRC
categories, strict deep LVS, seven-pin native LEF checks and nine negative
controls. Two explicit substrate contacts are present; their parallel
combination is included in LVS. These checks do not validate loaded timing.
Eight source/deck
faults, six startup-checker unit faults and five waveform-checker faults are
rejected. The corrected isolated startup checker requires all 100 actual HBT
flags and retains strict diagnostics and zero-source OP. The complete 50 ns native
run fails: all 772 electrical screens pass, but division and feedback fail.
Independent full-waveform review of 10–50 ns finds 79 first-divider intervals
with four VCO edges and one with five; the second divider mostly has zero or
one upstream edges per interval and no usable feedback. The strict native gate
also retains its 2.3019 GB memory-estimate warning as a failure. Postflight
independently verifies all 100 actual startup flags and zero-source OP.
The [complete failed-run records and review](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-feedback772-buffered-div16-records-20261009.tar.gz)
have full anonymous readback: 556,144 bytes, SHA256
`8234da7f525d635f45881e363dda6a40094c8399063387df6bd6910b06a46604`.
The 2,248,285,957-byte waveform is being published separately in exact parts. Reusing component layouts does not place or route their parent,
qualify PVT, establish PLL acquisition or complete the serial Gen3 x4 PHY.

### Count-drive chain: failed 200 ns response — 9 October 2026

The 749-device continuation reaches 200 ns with complete compressed readback.
All 749 electrical screens pass, but late /4 intervals contain 5 and 3 VCO
edges, and late /80 intervals contain 81, 79 and 81. The thirteen original
functional checks remain unchanged and two fail. The strict clean-diagnostic
gate also rejects ngspice's memory-estimate warning. Actual-deck postflight,
all 64 startup flags and zero-source OP pass independently. Neither the earlier
34 ns result nor this longer capture establishes PLL acquisition.

The [failed long-response records](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-feedback749-long200-records-20261009.tar.gz)
are public: 630,762 bytes, complete anonymous readback SHA256
`b095927a60e03bc0b6859610c7bb17eb9d97b18d0587136349699a0e02f0790d`.
The 7,983,371,881-byte complete waveform is being published separately in
byte-exact parts. Full public-waveform delivery and PLL acceptance are pending.


The [independent four-device buffer layout and native checks](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-hbt-levelshift4-layout-20261009.tar.gz)
are public as 93 members / 239,723 bytes. Complete anonymous readback matches
SHA256 `0afd462bbcc1f73f4d2108acbcd2a9dd3f7809ab26bfa1cc5340f6b9b28973fd`.
A diagnostic read of the running capture's first 10 ns shows the first HBT
macro dividing by four again, while the second macro still fails division.
That prefix is not a complete electrical or functional acceptance.

A separate 749-device experiment extends the passed 761-device physical-toggle
chain by replacing its second 48-device schematic toggle with the same
36-device / 70R / 167C physical macro. Both fast /2 stages then use their actual
extracted layouts, with independent explicit wire-reference ports. Every
other device and wire record remains identical; the total is 5,864 wire
records and 1,824 saved columns. Each toggle's named boundary rejects all
21 pin swaps and three reference-hop faults; four deck faults are rejected.
The 50 ns native run passes all 749 electrical screens and thirteen division
predicates. Independent complete waveform readback reproduces the measurement;
actual saved PFD, pump, receiver, level-shifter and both toggle boundaries
pass, together with zero-source OP and all 64 HBT startup flags. This is a
nominal finite response. The modulo-five counter is still schematic, the known
MOS-corner failures remain open, and no full PLL parent, acquired loop or
serial Gen3 x4 PHY acceptance is claimed. Full multipart waveform publication
is in progress.

### High-input HBT /2 and 1 GHz slow-corner continuation — 9 October

The added high-common-mode /2 stage now has a separate physical implementation:
[schematic](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/analog/pcie/clock_div2_high_input_v1.spice),
[layout generator](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/flow/make_pcie_clock_div2_high_input_v1.py) and
[native checker](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/flow/check_pcie_clock_div2_high_input_v1.py).
It preserves exactly the high-input network and second toggle of the v10
HBT /4: 19 HBTs, 20 rppd resistors and four MIM capacitors. Twelve explicit
substrate contacts are additional physical devices. The 960.000 × 297.030 µm
macro passes all 560 main DRC categories with zero violations, strict deep
LVS (44 devices after parallel contact merging), seven-pin LEF checks and
12 negative controls. An independent unsimplified extraction is being used
for terminal and metal-RC binding; it retains the twelve contacts separately.

The canonical generator reproduces the experimental layout's intrinsic
instances, routes, power straps, ports, schematic and LEF exactly, with zero
XOR on every geometry layer. The [complete physical component capsule](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-highinput43-layout-20261009.tar.gz)
contains 219 members / 1,362,767 bytes; full anonymous readback matches
SHA256 `25d2e4005d0642f7fa54c661577d94959e893391415efd7a9816652f3b76b195`.
This is component connectivity and main-rule validation, not loaded division,
qualified extraction, PLL lock or full-chip integration acceptance.

A separate 756-device /80 feedback candidate keeps the passed physical HBT
/4, inserts this high-input /2 **schematically**, then uses the physical
36-MOS /2 at nominal 1 GHz and the existing schematic modulo-five counter.
The original 5,627 wire records are retained with explicit receiver-input
and counter-clock changes. Seven source/deck faults, 24 physical-toggle
boundary faults, six startup-helper faults and six measurement faults are
rejected before its 50 ns native run. The complete run fails the division checks and strict native diagnostic gate;
all 756 electrical screens pass. Independent full-waveform review retains
that failure and validates the actual saved circuit boundaries.
The new HBT layout and its eventual RC are not yet in this running candidate.

The existing 36-MOS / 70R / 167C physical toggle was also exercised separately
at 1 GHz, MOS SS / 1.08 V / 125 °C, with nominal metal RC. With only 180 ps
between reset release and the first clock, steady /2 passes but the required
initial phase fails. A distinct 23 ns run with 1.18 ns reset-release lead
passes all 36 electrical screens, nine consecutive two-clock division
intervals and all twenty rail windows sampled 850–950 ps after each edge.
Complete waveform readback reproduces the measurement; stopped-Q,
wrong-complement and missing-clock-pulse controls are rejected.

The [complete failed and passed 1 GHz reset-lead captures](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-toggle-ss1ghz-reset-lead-20261009.tar.gz)
retain both results. Their measured reset requirement must still be checked
in the actual feedback chain. The earlier 2 GHz SS division failure and FF
terminal-voltage failures are unchanged; this does not close full PVT, PLL,
SERDES or serial Gen3 x4 PHY qualification.


### Physical high-input stage: wire model and connected run — 9 October

The unsimplified high-input extraction retains 55 native devices, including
all twelve finite substrate contacts. Geometry/source binding checks 168
terminals, 124 metal anchors, 24 conductors and all device identities and
parameters. The native wire export contains 224 resistors and 402 capacitors.
All resistance components connect their anchors; the exact native/export
resistance multiset and every point-ground and mutual-capacitance attachment
and value are preserved. Thirteen raw-extraction corruptions and four model
composition faults are rejected.

The nine-port model exposes BODY_SUBSTRATE and WIRE_CREF independently of its
seven physical pins. It retains 51 intrinsic body/well terminals without
claiming substrate-spreading extraction or qualified RF parasitics. The
[complete wire extraction, binding and model capsule](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-highinput55-wire-model-20261009.tar.gz)
contains 67 members / 320,210 bytes; full public readback matches SHA256
`12d9d19478e877f740e108e4fe6b8512210b0fa3b009bcc6bd9c6b72ee0f2774`.

A separate 768-device connected feedback run now replaces the schematic
high-input stage with this actual physical model. It has 83 HBTs, 6,253 wire
records and 1,901 saved columns. Both new reference ports use independent
explicit external fixtures. Thirty-eight high-input boundary faults, 24
physical-toggle faults, seven deck faults, six startup-helper faults and six
measurement faults pass before native launch. Its 10–50 ns measurement window
was declared before the run; it does not reinterpret the earlier 4–50 ns
candidate's failures. The completed native run passes all 768 electrical screens and twelve of
thirteen functional checks; the first /4 edge-count check fails. The /8 and
/80 checks pass, but the unchanged aggregate acceptance gate remains failed.
Full waveform readback reproduces the result and validates the actual PFD,
pump, high-input stage, receiver, toggle and level-shifter boundaries. This
is not PLL acquisition or serial PHY acceptance.


### Physical modulo-five counter development — 10 October

A separate fifteen-cell implementation uses native IHP DFF, inverter and NAND
cells. Exhaustive evaluation of the actual cell connection graph checks all
eight states, including invalid-state recovery, and rejects four wiring faults.
After two metal-spacing fixes, its layout passes all 560 main DRC categories,
strict deep and flat LVS for 142 MOS fingers, and five physical/reference
fault controls. Metal extraction retains 323 resistors and 741 capacitors.
All 568 native terminals are classified explicitly: 380 metal references,
142 body references and 46 shared-diffusion references. Thirteen raw RC faults
and six model-conversion faults are rejected.

An unloaded 80 ns / 500 MHz native run without wire RC passes the state sequence
but fails a 1.5 V MOS terminal-difference screen at 1.520163 V. That failure is
retained. With the actual metal RC, all 142 electrical screens, all 39 declared
state/complement windows and seven five-clock intervals pass; the largest
terminal difference is 1.491070 V. Holding reset low rejects the functional
check. This finite nominal result does not establish PVT or loaded behavior.

The counter is now in a separate 710-device connected-feedback candidate,
replacing the old 181-device schematic counter while preserving every other
device and wire. The circuit has 6,928 wire records. Two state observation
nodes are renamed bijectively; no ideal internal source is introduced. The
first launch failed because a wire-only boundary observation was omitted;
a stronger preflight caught a second missing boundary before another native
launch. Both failed attempts are retained. The corrected `710c` campaign saves
all 1,979 columns and passes counter/toggle boundary controls before its
50 ns native run. Full parent layout, loaded timing, PVT and acquired-loop
acceptance remain open.

### Modulo-five physical abstract and MOS-corner screens — 10 October

The reusable [142-MOS layout generator](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/flow/make_pcie_feedback_mod5_142_v1.py)
now produces a 61.920 × 18.670 µm macro with six explicit LEF ports. Independent
all-layer XOR verifies that normalization only translates the previously
extracted layout by +240 / +220 nm; schematic and finger records are byte
identical. Fresh native DRC, deep/flat transistor LVS and five fault controls
pass. Native LEF import passes and rejects missing-pin, blocked-pin and wrong-
outline mutations. Complete nominal and held-reset waveform readback reproduces
the original measurements and retains the held-reset functional failure.

The [complete component layout, extraction and nominal-waveform archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-mod5-142-native-layout-20261010.tar.gz)
contains 296 members / 355,858,430 bytes, SHA256
`021c8e5bd4d99fc0671203114b509ee6aa362e06e3926093912e037b06796761`.
Every public byte was checked against the locally verified archive using
complete HTTP206 ranges after the first readback timed out. This immutable
archive predates the two additional MOS-corner runs described below.

The unchanged 80 ns / 500 MHz component stimulus was also evaluated at slow
MOS / 1.08 V / 125 °C and fast MOS / 1.32 V / −40 °C. Rail windows remain
1.0–1.8 ns after each clock; their tolerance is 10% of the declared supply.
The absolute low-voltage device terminal-difference limit remains 1.5 V.

| MOS corner, nominal metal RC | 39 state/complement windows and divide-by-five | All 142 electrical screens |
| --- | --- | --- |
| Typical, 1.20 V, 27 °C | Pass | Pass |
| Slow, 1.08 V, 125 °C | Pass | Pass |
| Fast, 1.32 V, −40 °C | Pass | **Fail: 18 devices, maximum 1.617755 V** |

Both new held-reset controls fail the functional check. The slow control
passes the electrical screen; the fast control also has electrical failures.
These are unloaded MOS-corner experiments with fixed nominal interconnect,
not full PVT qualification. The fast-corner failure remains open and prevents
accepting this component across the stated supply range.


The [complete additional MOS-corner captures and independent remeasurement](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-mod5-142-mos-corners-20261010.tar.gz)
contain 59 members / 470,652,197 bytes, SHA256
`6739e402e8a5b3762ae4e25453b0ddf06e40054465ea1f89ef93234a19b38d1a`.
Every public byte was verified after resuming the interrupted readback.
Independent full-capture remeasurement reproduces the electrical and functional
results of both corners and both held-reset controls; the fast-corner failure
is preserved.


### Physical /2–/2–/5 parent and remaining output delay — 10 October

The [214-MOS parent generator](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/flow/make_pcie_feedback_div20_214_v1.py)
connects two physical /2 macros and the 142-MOS modulo-five macro with actual
parent metal. Its normalized outline is 129.920 × 32.150 µm with eight LEF pins.
The [native DRC/LVS checker](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/flow/check_pcie_feedback_div20_214_v1.py)
passes all 560 DRC categories, unsimplified deep/flat 214-device LVS and five
injected faults. The [LEF checker](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/flow/check_pcie_feedback_div20_214_lef.py)
passes native import and rejects missing-pin, obstruction and outline faults.
Twenty-layer XOR and exact SPICE/LEF comparison bind the reusable generator to
the independently generated, extracted candidate.

These physical checks do **not** close the electrical acceptance gate. Three
successive parent layouts were tested with the same 80 ns / 2 GHz stimulus,
0.3–0.8 ns Q1 rail window, ±0.12 V rail tolerance and 1.5 V device limit:

| Parent geometry | Q1 incident metal capacitance | First high-window minimum | Nominal result |
| --- | ---: | ---: | --- |
| Original full-width output stubs | 16.842 fF | 1.019275 V | Q1 rail failure |
| Short output stubs | 13.226 fF | 1.048824 V | Q1 rail failure |
| Short stubs and low Q1 track; reusable generator | 11.366 fF | 1.062726 V | Q1 rail failure |

All 214 electrical screens, divide-by-two/four/twenty counts, Q0 windows and
counter state/complement windows pass in each nominal trial, but 39 of 77 Q1
windows fail. Both earlier geometries and all failures are retained. The
short-stub change removes only Metal4; the low-track change affects only
Metal4/Metal5/Via4. An explicit native-net bijection and three corrupted-netlist
controls validate unchanged 214-device connectivity. Independent complete
waveform readback reproduces every electrical and functional predicate, including
held-reset failures. These are fixed nominal metal-RC experiments, not qualified
substrate/RF extraction, PVT or a complete PHY.

The two earlier complete physical trials are publicly archived, with every byte
verified by resumed range readback:

- [div20-parent-original-failed](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-div20-parent-original-failed-20261010.tar.gz): 229 members / 376,772,429 bytes; SHA256 `4dd4a31d13071779094aec3e62a89c69520f93604b3f43f99e530406d68d0239`.
- [div20-parent-shortpins-failed](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-div20-parent-shortpins-failed-20261010.tar.gz): 231 members / 376,591,539 bytes; SHA256 `e2ea5c11ebf88798bb85bf8e75e63c5c9e71eb924e34fb13dd706a485ba1beca`.

A separate 710-device connected-feedback run incorporates both physical toggles
and the physical 142-MOS counter without the new parent interconnect. Its 50 ns
capture passes all 710 electrical screens and twelve of thirteen functional
predicates, including three exact eighty-VCO-cycle intervals. It fails the
unchanged feedback-duty check: measured duties are 26.4146%, 26.2244% and
26.6980%. Complete waveform remeasurement and actual PFD, level-shifter,
receiver, toggle and counter boundary checks retain that failure. No PLL-lock
or PHY acceptance is inferred. An isolated 236-MOS parent adds two PDK drive-four
buffers; its DRC/LVS and wire checks pass, but nominal Q1 rail and interval-count
checks fail. Buffer insertion is therefore not an accepted fix.


### Drive-four complement counter (10 October 2026)

The 710-device capture isolates a loaded level-conversion asymmetry: the actual
counter output remains near 20% duty, while feedback rises roughly 1.76 ns after
it and falls roughly 2.42 ns after it. A new physical counter replaces only the
Q2B inverter with the PDK's `sg13g2_inv_4`, preserving its single inversion. This
adds six real MOS fingers, for 148 total; it does not insert another output
buffer stage or change the modulo-five state machine.

The reusable generator and native DRC/LVS and LEF checkers are
[make_pcie_feedback_mod5_148_v1.py](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/flow/make_pcie_feedback_mod5_148_v1.py),
[check_pcie_feedback_mod5_148_v1.py](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/flow/check_pcie_feedback_mod5_148_v1.py) and
[check_pcie_feedback_mod5_148_lef.py](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/hw/soc/flow/check_pcie_feedback_mod5_148_lef.py).
The 63.360 x 18.670 um macro has zero markers across 560 DRC categories,
strict deep and flat transistor LVS with 148 fingers, five rejected circuit or
geometry faults, and native OpenROAD verification of six LEF pins and three
rejected LEF faults. Canonical regeneration reproduces all geometric layers,
SPICE, finger reference and LEF exactly.

Its actual 336-resistor/753-capacitor metal model passes terminal binding,
thirteen RC fault controls and six composition fault controls. The standalone
80 ns, 500 MHz tests retain the same 39 state/complement windows and divide-five
checks. All complete waveforms were reread to independently reproduce every
148-device electrical check and functional predicate:

| MOS point; fixed nominal wire RC | Functional result | Electrical result |
| --- | --- | --- |
| Nominal, 1.20 V, 27 C | PASS | PASS |
| Slow, 1.08 V, 125 C | PASS | PASS; maximum terminal difference 1.340528 V |
| Fast, 1.32 V, -40 C | PASS | FAIL; 20 devices, maximum terminal difference 1.618954 V |

The 1.5 V terminal-difference bound remains unchanged. Held-reset controls reject
functionally at all three points; the fast held-reset case also fails four
electrical screens. These results do not establish PVT or a safe loaded parent.

A separate 716-device connected-feedback experiment uses this physical counter,
both physical divide-two toggles, and 6,953 wire records. Its named-port binding
and 24 counter-boundary fault controls pass. A first positional-binding attempt
was rejected before simulation and is retained. The corrected 50 ns experiment
is still running at this publication; the feedback-duty criterion stays at
17–23%. Neither full serial Gen3 x4 PHY nor final chip setup/hold is closed.

The [complete 148-MOS physical and corner capsule](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-mod5-strong148-native-and-corners-20261010.tar.gz) contains 295 members / 725,687,873 bytes, SHA256 `3317e5dc0597c6899393516c492774cb6855e860289e87d9f2b492fbe1f4860d`. Every public HTTP range was read and compared byte-for-byte with the complete hashed archive. The capsule retains all six full native waveforms, fast-corner failures, geometry and fault controls; it excludes the still-running connected-feedback experiment.
