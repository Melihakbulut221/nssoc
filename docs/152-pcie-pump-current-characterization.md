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
pump-integration run. Native model translation, extracted feedback simulation
and a connected physical PLL parent remain required. It does not establish a
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
PVT, pump wire parasitics or full serial PHY operation. The new PFD physical
model is being tested in a separate 740-device composition; its result is pending.
