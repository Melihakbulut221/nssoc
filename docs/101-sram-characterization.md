# 101 — SRAM characterization and production verification

This local campaign starts from the exact [32-SRAM core whose full transistor
LVS passed](100-routed-closure.md). It measures real transistor waveforms and
runs independent physical checks. **Complete SRAM characterization and product
manufacturing acceptance remain open.** No synthetic Liberty file is used to
make the timing gate appear closed.

The [campaign receipt](evidence/sram-qualification-20260925.json) records the
measured results and archive hashes. [Component notices](evidence/sram-qualification-20260925-NOTICES.txt)
cover the circuits, generated models, geometry and retained rule sources.

## 1. Circuit identity and simulation memory use

The original simulation circuits are exact MOS-to-PDK-wrapper adaptations of
the independent CDL inputs used by the accepted full-chip LVS. Both circuits
retain every terminal and dimension. Their **unsimplified** instance counts are
202,800 MOS devices for SP512×64 and 37,076 for DP256×16. The previously reported
202,510 and 36,776 are the locked LVS deck's **simplified** recursive device
counts; they are not the raw SPICE instance counts.

The original SP simulation exhausted its 12 GiB address-space budget while
parsing repeated model definitions. `share_sram_psp_models.py` specializes the
original PSP model expressions once per distinct geometry. It supports only
the actual default single-finger, multiplicity-one, pre-layout wrapper profile;
other terminal syntax, parameter sets or dimensions outside the model domain
are rejected. Circuit nodes, transistor dimensions and all other source lines
are preserved. The installed PDK and original circuit remain unchanged.

All 25 distinct geometries used across the two macros are compared with the untouched PDK wrapper at TT/1.2 V/25 °C,
SS/1.08 V/125 °C and FF/1.32 V/−40 °C. Two-dimensional drain/gate DC sweeps and
independent drain/gate transient pulses pass. A changed transistor width and an
added 10 fF capacitance are rejected. The full DP waveform then agrees with the
original simulation across all 87 saved voltage columns: maximum voltage
error is about 1×10⁻⁹ V and the largest measured timing difference is about
1.1×10⁻¹⁰ ns. Held-output corruption and a 300 ps output shift are rejected.
These controls qualify this deterministic model-sharing experiment; they do
not establish statistical mismatch, aging or extracted-layout equivalence.

## 2. Measured DP timing and supply energy

The complete DP circuit uses two addresses, byte/full-word writes and a 24 ns
read-clock pause. Measurements reconstruct memory from the observed input
waveforms, check stable readback/hold windows, and measure 20 rising plus 20
falling output transitions. Delay is clock 50% to output 50%; output slew is
20%–80%. The input-transition column gives the stimulus's full-swing ramp.
Linear threshold interpolation does not remove the finite-step uncertainty.

| Corner | Input transition (ns) | Output load (fF) | Maximum delay (ns) | Maximum output slew (ns) | Supply energy (pJ) |
|---|---:|---:|---:|---:|---:|
| TT, 1.2 V, 25 °C | 0.1 | 5 | 1.664528 | 0.170607 | 55.677310 |
| SS, 1.08 V, 125 °C | 0.1 | 5 | 2.729708 | 0.286509 | Not captured |
| FF, 1.32 V, −40 °C | 0.1 | 5 | 1.091591 | 0.113130 | Not captured |
| TT, 1.2 V, 25 °C | 0.5 | 5 | 1.716035 | 0.170338 | 55.732409 |
| TT, 1.2 V, 25 °C | 0.5 | 20 | 1.832866 | 0.317990 | 56.404771 |
| SS, 1.08 V, 125 °C | 0.5 | 20 | 2.998778 | 0.540077 | 45.178749 |

These are individual measured points, not a complete interpolation table.
The 50 ps maximum-step TT result has a separate 25 ps run: its worst delay is
1.637258 ns. The roughly 27 ps difference is retained rather than rounded away.
Energy integrates total delivered supply power over 8–78 ns, excluding the
supply ramp. It includes all activity and leakage in this pattern; it is not
isolated leakage or a per-arc internal-power model.

Every newly completed DP case also rejects five real-wave/input corruptions:
a held output bit, an extra read-clock edge, a wrong write address, a changed
supply and a wrong declared clock transition. Analytic unit signals independently
check interpolation, delay, slew, energy and malformed/truncated-wave rejection.

## 3. SP readback and timing

The full **202,800-MOS SP512×64** circuit completes its 150 ns TT/1.2 V/25 °C
transient with 100 ps input ramps, **20 fF** output loads and a 50 ps maximum step.
An independent audit reconstructs actual writes at addresses **0 and 257**,
checks four 64-bit read windows and verifies that a byte-5 write changes only
its selected byte. All readback checks pass. Separate corruptions of a read bit,
the byte-write result, the clock and the address are each rejected.

Consecutive read cycles provide **60 rising and 60 falling** output timing
transitions. Maximum measured clock-to-output delay is **2.206444 ns**; maximum
20%–80% output slew is **0.314075 ns**. Total supply energy over 8–150 ns is
**143.692697 pJ**, or **1.011920 mW** averaged over that particular pattern.
This is a completed schematic TT measurement, not SP PVT coverage, isolated
leakage, a per-arc power table or extracted-layout qualification.

## 4. Setup constraints and extracted parasitics

A six-point full-circuit screen completes for the DP read-address `a2[0]`
rising transition at TT/1.2 V/25 °C, 100 ps input ramps and 5 fF output loads.
Every 30 ns simulation completes normally with a 25 ps maximum step. The initial
read of `0xA55A` is a positive control; the requested new word is `0xC33C`.

| Address 50% relative to clock 50% | Stable observed word | New address captured |
|---|---|---|
| 500 ps before | `0xC33C` | Yes |
| 100 ps before | `0xC33C` | Yes |
| Simultaneous | `0xC33C` | Yes |
| 100 ps after | `0xC33C` | Yes |
| 500 ps after | `0xA55A` | No |
| 2 ns after | `0xA55A` | No |

This brackets a capture transition between 100 and 500 ps after the clock for
this one stimulus, rather than establishing a Liberty setup constraint. It does
not measure delay-degradation criteria, hold constraints, other address bits,
input directions or PVT corners. No complete setup/hold or post-layout timing
model is accepted.

The RC extractor's independent macro LVS matches the original reference. Its
warning about unclassified `cont_drw` geometry was investigated rather than
suppressed. Exactly **7,504 contact cuts** lie outside the three classified
source/drain/gate-contact groups. A complete geometric difference check places
all of them inside body-tap regions, with no unexplained residual geometry.
The nominal technology stack has no explicit contact-above entry for these
body taps. The retained diagnostic GDS identifies every affected contact.
This is a limitation of the modeled body/substrate network; completed nominal
wire extraction alone cannot establish complete body-contact RC or production
PEX acceptance.

A separate extraction of `DP8TCell` from the exact same macro layout completes
and passes its internal LVS, producing eight MOS devices, 51 capacitors and
92 resistors. An independent graph audit then **rejects the RC export**: two
resistance components have no electrical attachment, and eight have only one
attachment to a transistor/capacitor/external pin. All 92 resistors are in these
unloaded or dangling networks; original transistor terminals remain on unsplit
ideal nets. The standalone cell also has one unexported floating body node;
this latter observation is not generalized to the full macro.

Inspection of the pinned exporter confirms that it appends extracted R/C
components to a copy of the original netlist without reconnecting transistor
terminals to the distributed resistor nodes. The full-macro extraction was
therefore explicitly stopped after this failed control. Its partial output,
termination reason, completed macro LVS and all cell-level results are retained.
No completed full-macro RC netlist or extracted timing pass is claimed. Correct
terminal attachment, substrate/body connectivity and independent validation of
the exported electrical network are required before using this PEX route.

## 5. Independent physical checks

The first unchanged-GDS density run found 32 inherited SRAM outlines on layer
189/0. The deck therefore used the memory outlines as the chip area and reported
geometry outside that boundary. It subsequently reached its 7 GiB address-space
limit. The original antenna run also reached that limit; its partial zero-marker
report is **not a pass**. The original main run was explicitly stopped in favor
of complete checks on the corrected boundary candidate. All these records are
retained.

`normalize_core_boundary.py` replaces only layer 189/0 with the actual top-level
189/4 die rectangle: **3326.4 × 2475.9 µm**, matching the physical run's declared
die area. It reloads the written GDS and requires every other per-cell shape,
text and instance transform to remain identical. No fabricated layer is cropped,
no fill is inserted and no density threshold is changed. Controls reject an
outside shape, missing die and ambiguous die outlines.

The corrected GDS's density deck completed normally in 1,973 seconds. It
reports **177 markers across 12 nonempty categories** (19 categories total),
including active density, Metal2–Metal5 global/local density, and both top-metal
minimum densities. TopMetal2 covers 5.97% of the die against the deck's 25%
minimum. This is a completed **FAIL**, requiring actual fill work and subsequent
checks on that changed geometry. No threshold or violation is waived.

The corrected GDS's first recommended main check reaches the 12 GiB address-space
bound during connectivity extraction and returns **ERROR**, with no complete
DRC category inventory. The independent antenna deck **passes with zero markers
in all 31 categories**, with normal process completion at the 12 GiB limit.
A second main run keeps
the identical GDS, rule tables and recommended rules, and raises only the
address-space limit to 16 GiB after the SP simulation and antenna run finish and
at least 12 GiB of memory is available. This retry also ends in
`std::bad_alloc` during `LayoutToNetlist::extract_netlist`, before the complete
category inventory exists. **Neither main attempt is a DRC pass or a completed
geometric failure verdict.** Main-deck closure needs a further bounded
extraction strategy or greater available resources; no connectivity rule is
disabled to bypass the failure. The old full-chip LVS
remains bound to its original GDS; the boundary-only transformation proof is
separate evidence, not a claim of a new full LVS run.

## 6. Remaining acceptance work

Complete both memories' address/data/mask coverage; characterize all clock,
address, data and enable setup/hold and pulse-width arcs across PVT and the
required load/slew grid; qualify power/leakage and collision behavior; validate
extracted RC and repeat timing on extracted circuits. Only then generate and
independently validate complete Liberty tables, bind them into the final SoC
STA, and close setup/hold/recovery/removal and electrical limits.

Independent complete physical decks must pass the final manufactured geometry,
including required fill and its parasitics. Pads/ESD/package, power integrity,
DFT/MBIST, process/manufacturing review and silicon qualification remain separate
product gates in [docs/92](92-product-acceptance.md).

## 7. Reproduction and evidence boundaries

The four lossless bundles are pinned to immutable commit `f03269e`:

- [Boundary-corrected GDS and contact diagnostic geometry](https://github.com/Melihakbulut221/nssoc/blob/f03269ea40440a77f795c52ae91bbae797af2947/docs/evidence/sram-qualification-20260925-physical-views.tar.xz)
- [Complete transistor stimuli, waveforms, model controls and PEX records](https://github.com/Melihakbulut221/nssoc/blob/f03269ea40440a77f795c52ae91bbae797af2947/docs/evidence/sram-qualification-20260925-analog.tar.xz)
- [Full density/antenna records and retained main-DRC resource failures](https://github.com/Melihakbulut221/nssoc/blob/f03269ea40440a77f795c52ae91bbae797af2947/docs/evidence/sram-qualification-20260925-physical-checks.tar.xz)
- [Reproduction scripts, exact rule sources, source bindings, test logs and notices](https://github.com/Melihakbulut221/nssoc/blob/f03269ea40440a77f795c52ae91bbae797af2947/docs/evidence/sram-qualification-20260925-methods.tar.xz)

The campaign archives retain complete stimuli, raw waveforms, simulator/deck
logs, measurement scripts, per-file SHA-256 manifests and the boundary-corrected
GDS. Failed and resource-limited predecessors remain included. The original
full-chip sources, original GDS and older PVT waveforms are in the immutable
[32-SRAM integration archives](100-routed-closure.md). Installed tool executables
are dependencies, not distributed artifacts.

The runs pin ngspice 42, KLayout-PEX 0.4.4, KLayout 0.30.7 from the recorded
LibreLane 3.0.5 AppImage for foundry decks, the installed IHP model revision
`c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c`, and the independent rule revision
`5e6d592e4002946a4616f798c357f0f3c06cf3b6`. The boundary transformation uses
KLayout 0.30.11 and verifies the serialized output. Exact executable and input
hashes accompany each experiment. Recorded absolute paths must be restored or
explicitly relocated and rebound before another machine replays a campaign.
Publication does not imply that a second complete replay was performed.

The focused local regression contains 82 pytest checks and four native KLayout
boundary checks. It covers real fault rejection, malformed/truncated waveform
handling, analytic threshold interpolation and energy, all-three-deck result
acceptance, and cleanup of a timed-out process whose child ignores SIGTERM.
Ruff and the document build are checked separately. These software checks
validate the measurement machinery; they do not replace transistor, timing or
physical results.


## 8. 26 September: fill, route grid repair and additional SP corners

A subsequent local campaign adds 991,043 fill shapes in 35 bounded regions.
An independent serialized-GDS audit preserves all original device/routing
geometry, text and instance transforms. Density checking of this filled
precursor completes with **zero markers**. Its active density is 36.54%;
Metal1–Metal5 are 38.36%, 38.26%, 40.25%, 46.99% and 46.88%; TopMetal1 and
TopMetal2 are 42.03% and 42.84%. These measured densities replace the previous
177-marker failure only for this changed candidate.

A separate grid audit finds six off-grid Metal2 polygons in the generated
SRAM routes: two in SP512×64 and four in DP256×16. The source-bound repair
moves their coordinates by at most 2 nm onto the required 5 nm grid. Independent
comparison of the written GDS proves that these are the only changed polygons;
the total cell-definition XOR area is 0.00348 µm². A complete local-coordinate
scan checks 1,998,803 polygons and all instance placements without an off-grid
result. This geometric audit alone is not DRC acceptance.

Both corrected standalone macros pass the unchanged recommended main deck:
**560 categories and zero markers each**. Their transistor LVS also passes.
The exact repaired, filled **full core** independently passes fresh density
and antenna checks with zero markers, and fresh full transistor LVS with
**130 matching circuits and 5,129,488 simplified recursive primitives per side**.
No circuit is skipped. The historical address-swap negative control remains
bound to its original GDS; it is not presented as a newly repeated test.

Complete main DRC is still being closed. A new execution profile retains all
37 upstream tables and all recommended rules, running FEOL/geometry in deep
mode and BEOL in tiling mode. Positive and deliberately faulty controls match
the complete unchanged deck's category descriptions and exact marker geometry:
560 categories, respectively zero and three markers. On the full repaired core,
the first 8 GiB run reaches its address-space limit in the angle table. Its
415-category partial report has zero markers, but **is not a pass**. The same
complete profile is retried at 16 GiB with one worker. Its FEOL/geometry
partition now completes normally: **443 categories, zero markers**, in 4,204.42 s.
The original 500 µm tiled BEOL attempt was explicitly superseded after its
long-running Metal1 spacing operation; its incomplete result is not accepted.
A separate 8 GiB deep-mode attempt reaches its one-hour bound in `M1.e` and
also has no complete verdict.

A fresh full 117-category BEOL run uses 50 µm execution tiles and the original
30 µm tile borders. The isolated entrypoint differs only in the tile-size
setting; all rule bodies, thresholds, selectors and recommended checks match
the lock. Positive and negative controls retain all 560 category descriptions
and exactly the same unique error geometries. Overlapping tiles emit one
duplicate Metal1 error in the faulty control: all five raw markers are retained
and correspond to the reference's four unique errors. No deduplication or
waiver is applied to the full-core acceptance, which requires zero raw markers.
The two-thread full-core attempt was explicitly superseded after the Metal1
spacing step ran for approximately 50 minutes. Fresh one-versus-eight-thread
controls have identical complete 117-category inventories and raw marker
multisets for both the clean and faulty geometries. A bounded eight-thread run
now uses the same GDS, rule bodies, tile size and borders. The combined main
DRC gate remains open until every category completes on that exact GDS.

The complete 202,800-MOS SP schematic also completes both additional PVT
patterns, with the same 100 ps input ramps, 20 fF loads and 50 ps maximum step.
Each case checks four reads, the byte write, 60 rising and 60 falling transitions,
and rejects five actual-wave/input corruptions.

| Corner | Maximum delay (ns) | Maximum 20%–80% slew (ns) | Pattern supply energy (pJ) |
|---|---:|---:|---:|
| SS, 1.08 V, 125 °C | 3.666113 | 0.513396 | 116.711508 |
| FF, 1.32 V, −40 °C | 1.446675 | 0.185632 | 182.129327 |

These extend the TT measurements above. They remain schematic points for the
specified two-address pattern, not complete timing/power tables or extracted
signoff. Supply energy covers 8–150 ns and includes both switching and leakage.

An isolated KLayout-PEX exporter experiment preserves native terminal provenance
and reconnects all 24 D/G/S terminals of the eight-MOS bitcell to their extracted
resistor networks. Independent graph checks reject a wrong terminal and a removed
resistor branch. All original MOS parameters, capacitances and resistance
connectivity/values are preserved. Capacitor-only internal nodes and incomplete
body/tap modeling remain, so this is **not qualified distributed RC**. The
installed extractor is unchanged; original and modified GPL sources are retained.
An alternative full-macro extraction using the original IHP Magic technology
exposes a different problem. Its VIA1/VIA2 import performs a morphological closing
operation which can join cuts on distinct signals at their legal spacing. The
full extracted circuit retains 37,076 MOS devices but has 10,258 nets, against
10,272 in the independent source. Pin annotation polygons are completely within
the actual drawing geometry; making labels unique does not resolve the mismatch.
No RC timing result from this original import is accepted.

An isolated copy of the technology removes only the two via-array closing
sequences while retaining the existing 5 nm import expansion. The installed PDK,
source GDS, extraction parameter tables and independent DRC/LVS decks remain
unchanged. With that experimental import, an independent graph proof establishes
a complete net bijection and exact MOS edge/width/length multiset: **37,076 MOS,
10,272 nets and all 88 named ports**. Drain/source symmetry is allowed; gates,
bulk terminals and external pin identities are preserved. No device or net is
skipped. Normalizing floating-point representations changes dimensions by at
most 4.44×10⁻¹⁶ µm. A real gate short, a 5 nm width change and swapped output
ports are each rejected. This qualifies the measured transistor-connectivity
transformation, not distributed RC, process models or manufacturing.

The same corrected import now also passes the complete SP graph comparison:
**202,800 MOS, 68,588 nets and all 148 named ports**, with the same three
short/width/output-swap faults rejected. This independently establishes both
macro transistor topologies; it does not transfer parasitic qualification.

Four independent via controls now reproduce and isolate the import fault:
VIA1 and VIA2 each have a separately routed case and an intentional metal bridge.
All four pass the unchanged recommended 560-category main DRC. The original
import shorts the separate routes; the corrected import keeps them separate
while preserving both the real bridges and the actual via connections. The first
control geometry had an insufficient Metal1 enclosure and correctly failed DRC;
that failed control is retained alongside the corrected legal geometry.

A separate PSP specialization preserves the extracted AS/AD/PS/PD junction
parameters and requires an explicit `pre_layout` choice. It matches the untouched
PDK wrappers for all 158 distinct junction profiles in the full DP extraction,
plus two zero-AS fallback controls, at TT/SS/FF and both layout settings. DC and
transient drain/gate currents differ by at most 4.45×10⁻¹⁶ A in positive cases.
A changed drain junction and a wrong layout-mode choice are both rejected.
The initial source-junction fault was unobservable because source and body were
tied; its failed experiment is retained and the corrected control exercises the
independently pulsed drain. These checks qualify the measured wrapper conversion,
not extractor accuracy, capacitance coverage or complete SRAM RC timing.

The capacitance export itself exposed another tool limitation: Magic 8.3.623's
SI formatter writes 79,534 positive capacitances below 1 aF as zero; increasing
`-y` does not affect this path. An isolated build from upstream commit
`fd12c39c37f26a0fe6e04698b1011e31b8bd3229` first reproduces every original MOS
node/parameter and capacitor endpoint/value. Four output statements, covering
both flat and hierarchical nodal/coupling capacitors, are then changed to write
double-precision farads. Geometry, extraction coefficients, MOS and resistor
serialization are unchanged. The first two-statement experiment missed the
hierarchical path and failed; it remains in the evidence.

The corrected export accounts for **all 202,642 positive capacitors** against
the original `.ext` file after resolving every alias. There are no zero-valued
exported capacitors. The 20 zero-valued source nodes and zero substrate entry
are explicitly counted; no positive source capacitor is omitted. Total source
capacitance is 27.418462 pF, including 0.026241 pF lost to zero in the original
formatter. Maximum per-pair export error is 3.125×10⁻²¹ F, within the recorded
1×10⁻²³ F + 1×10⁻⁵ relative tolerance. Removing a real capacitor or moving its
endpoint is rejected. This establishes serialization fidelity, not field-solver
accuracy or conservation after distributed resistance extraction.

The same complete capacitance accounting now passes for the SP macro:
**821,222 positive capacitors**, no zero-valued exports, 116.687724 pF total,
and a maximum per-pair rounding difference of 1.5625×10⁻²¹ F. The 18 zero-valued
source entries are explicitly counted. All 202,800 MOS nodes and junction
parameters are preserved; removing a capacitor or changing its endpoint is
rejected. SP-specific junction-profile equivalence also passes DC/transient
checks at TT/SS/FF in both layout settings, with junction and layout-mode faults
rejected. These are export/model-conversion checks; SP parasitic timing remains
separate.

The one-arc DP read-address experiment is also refined: the original −100 ps
setup point passes, while −125, −150 and −175 ps fail to capture the new word.
The measured pass/fail bracket is now 25 ps for rising `a2[0]`, TT/1.2 V/25 °C,
100 ps ramps and 5 fF output load, with a 25 ps maximum integration step. Negative
setup here means the input crosses 50% after the clock does. This does not close
other pins, edge directions, loads, slews, PVT corners, hold or extracted timing.

The first original-import RC run timed out after 30 minutes. A longer original
retry was stopped once the connectivity mismatch was established. Both partial
results are retained. With the independently checked import, full DP resistance
extraction completes in 4,749.58 seconds and accounts for all 10,272 original
nets. The resulting 148,334-resistor / 116,681-capacitor export fails the strict
RC acceptance check because **259 capacitor values are negative**. No value is
clipped, removed or silently accepted.

A separate topology-only diagnostic preserves those signed values to isolate
the fault. Collapsing every resistor reproduces the exact 37,076-MOS graph and
all 88 ports; deliberately disconnecting a real MOS terminal is rejected.
There are no unanchored resistor components or capacitor-only nodes. This is
not a pass for the RC circuit. Projecting all exported capacitors through that
proved mapping finds **189,054 missing, 20 extra and 10,251 mismatched net pairs**
against the independently audited C-only matrix. The totals are 43.910525 pF
versus 27.418462 pF.

Inspection of the pinned Magic source explains the coupling-matrix change:
`ResReadCapacitor` adds each coupling capacitance to both nodal totals in signal
mode, `ResDistributeCapacitance` distributes those totals by node area, and
`efFlatSingleCap` drops coupling attached to a killed original node. The negative
values need a separate diagnosis; they are not presumed to have the same cause.
A small-cell reproducer identifies two additional area-allocation defects.
The single-breakpoint east/west width has the opposite sign to the north/south
formula. Fixing that line alone still fails: labels spanning several tiles
also force their common lower-left drive point onto tiles that do not contain
it. In the NOR control, point (238, 268) is applied to tile (238, 325)–(280, 794),
producing an area contribution of −2,394 internal units².

An isolated experiment corrects the width sign and only assigns a label point
to tiles containing it. NOR, flip-flop, 8T bitcell and read/write-block controls
then have no negative resistance-node area or exported capacitor. Their source
`.ext` record multisets remain identical, allowing unordered capacitor endpoints.
All four resistor-collapsed MOS graphs match and all four deliberately disconnected
terminal controls are rejected. Resistance values and intermediate nodes do change
with corrected point placement; no resistance-accuracy claim is inferred from the
graph proof. The fresh full DP extraction now completes with these repairs:
146,385 positive resistors and 115,837 positive capacitors, no zero components,
no self-resistors, no unanchored resistor groups and no capacitor-only nodes.
Its collapsed graph matches all 37,076 MOS and 88 ports, and the disconnected
terminal control is rejected. The separate capacitor-matrix audit still fails:
189,054 missing pairs, 20 extra pairs and 10,251 mismatched pairs, with total
43.910549 pF versus the 27.418462 pF reference. Removing negative capacitances
does not restore the coupling matrix. Original, failed one-line and diagnostic
builds and controls are retained.

A source comparison with official Magic 8.3.684, commit
`4f53bb3091d1e4a9b2009a58f157a8a4331d4c84`, finds that upstream has already
corrected the single-breakpoint width sign. Its
[signal-mode coupling substitution](https://github.com/RTimothyEdwards/magic/blob/4f53bb3091d1e4a9b2009a58f157a8a4331d4c84/resis/ResReadExt.c)
and sub-attofarad SI formatter behavior remain in the retrieved source.
An isolated build of that exact upstream commit also reproduces SIGSEGV on
the native two-port wire control, during extraction and before an RC netlist
exists. The source archive, configure/build/install logs, runtime hashes and
failed control are retained. No active 8.3.623 runtime or installed PDK was
replaced. The newer driver/sink implementation is not qualified by this
failed diagnostic comparison.

The extraction remains unqualified. The published technology's nwell/dnwell
resistance limitations also remain. The independent full DP simulation with all 202,642 audited layout capacitors
and no distributed resistance passes its 78 ns TT pattern at 1.2 V / 25 °C,
100 ps input ramps and 5 fF loads. All read/hold/byte-write checks pass and
wrong-output / wrong-supply controls are rejected. The maximum measured delay
is 2.642361 ns; pattern supply energy over 8–78 ns is 118.177575 pJ. These are
measurements of this capacitance-only netlist, not full distributed-RC signoff.
The same pattern also passes at SS/hot and FF/cold, using the same nominal
layout capacitances; these are transistor PVT points, not independent RC corners.
Each has 20 rising and 20 falling checked transitions and rejects the two faults.

| Corner | Maximum delay (ns) | Maximum slew (ns) | Energy, 8–78 ns (pJ) |
|---|---:|---:|---:|
| TT, 1.20 V, 25 °C | 2.642361 | 0.242731 | 118.177575 |
| SS, 1.08 V, 125 °C | 4.406627 | 0.422697 | 90.135549 |
| FF, 1.32 V, −40 °C | 1.711762 | 0.154103 | 145.968695 |

The generic energy helper retains its historical “schematic” scope string in
raw records; the pinned circuit actually contains all audited layout capacitors.
No raw measurement record is rewritten to change that label.

The predecessor SP capacitance-only transient used four simulator threads.
It was later explicitly stopped when the repaired geometry changed its model;
its partial output is preserved without timing acceptance. A fresh repaired-SP
transient now uses the audited new model.
A full-DP 0–5 ns startup control produces byte-identical voltage/current output
at one and four threads; elapsed time decreases from 341.970 to 280.886 seconds.
That limited benchmark justifies the execution change, not complete SP waveform
equivalence. The slow single-thread SP attempt was explicitly superseded and
retained without a waveform acceptance result.

The campaign retains every failed or explicitly superseded run. The 105
intermediate fill GDS payloads are losslessly archived with manifests; the
original per-file xz streams were independently reconstructed byte-for-byte
before redundant transport copies were removed. Final campaign publication
and complete main/PEX outcomes are pending. Full characterization, final SoC
STA, pad/package qualification and foundry manufacturing approval remain open.

The original two-port sheet-resistance controls terminate with SIGSEGV before
producing a resistance network, including an independent build of upstream
8.3.684. A retained backtrace identifies an uninitialized coordinate for an
aliased port without a canonical `NODE` record. An isolated 8.3.623 experiment
initializes that coordinate and suppresses redundant alias-port extraction until
its canonical node exists. It checks all 88 DP and 148 SP logical ports, including
repeated physical port regions, and the 28 deliberately aliased wire controls.
Missing/wrong aliases and conflicting port indices are rejected.

The repaired wire experiment then exposes a separate resistor-reader offset:
a float-valued resistance still receives an obsolete half-unit rounding addition,
creating a 0.0005 Ω error. Removing that addition makes all 28 rectangular sheet
controls match the technology's nominal sheet resistance times length/width:
seven metals, two orientations and two aspect ratios. Wrong values, endpoints
and a duplicate resistor are rejected. These checks do not calibrate process
resistivity or qualify contacts, wells, coupling or complete SRAM RC accuracy.

Four actual-cell controls compare the area/label-point runtime with the additional
alias-port and resistor-reader repairs. Their raw internal node names can differ;
a complete independent weighted-network comparison instead establishes a unique
electrical node mapping, exact resistor values/multiplicity and physical MOS
geometry, terminals and junction parameters. Capacitance differences stay within
explicit six-significant-digit source-printing intervals. Repeated `RNODE` records
are counted and summed according to the retained reader implementation, rather
than discarded. All 16 deliberate lost-resistor, wrong-value, gate and capacitance
faults are rejected. The earlier strict-string and duplicate-record failures
remain in the archive. Full-macro RC and capacitance conservation remain separate
mandatory checks; the known coupling-to-ground substitution is still unqualified.
The completed full-DP resistor-reader re-export also preserves every MOS and
capacitor and all 146,385 resistor branches/endpoints, with exactly the expected
0.0005 Ω correction within the recorded output-rounding intervals. All three
wrong-value/lost-branch/wrong-endpoint controls are rejected.

The pinned Magic extraction technology explicitly leaves reverse-biased well
capacitances and nwell/dnwell resistances unspecified and describes fringe
capacitance approximation. Its MOS channel capacitances are delegated to the
device model. This campaign therefore preserves the measured nominal wiring
capacitances and extracted junction geometry, while keeping process-model
accuracy and substrate-network qualification open.

A further via/lead control exposes an independent RC-corner parser defect.
The original nominal cases match the published coefficients, but fractional
TopMetal2 sheet values (14.5 and 7.5 mΩ/square) enter a parser branch that exits
before registering their resistance class. The high/low corner outputs omit
that metal's contribution and emit truncation/class-inventory diagnostics.
A rejected experiment multiplying coefficients and changing `rscale` shows why
unit rescaling alone is insufficient: exported resistances become ten times
larger. Both failures remain evidence, with their original logs and outputs.

A separate complete Magic build instead retains sheet coefficients and their
class serialization as floating-point values. All other process coefficients,
units and the installed PDK are unchanged. It passes 84 analytic rectangular
sheet cases (seven metals, three resistance corners, two orientations and two
aspect ratios) plus 18 analytic single-via/rectangular-lead cases (six vias and
three resistance corners). Each family rejects three real value/connection
faults. The via ports are on separate conductor leads: the initial coincident
contact-label control lost its layer identity and is retained as a failed
control, not used to justify the fix. These are native extractor controls,
not a DRC-qualified via test chip or measured process calibration.

Four actual SRAM subcircuits also retain the same source records and complete
weighted R/MOS graphs under this fractional-sheet build. All 16 graph/value/
capacitance faults are rejected. One cell changes 25 internal node names;
the unique graph mapping accounts for every node instead of treating text
identity as electrical equivalence. These new small-control passes do not
replace the full-macro RC result or repair its failed coupling conservation.

A separate same-geometry test also checks whether named extraction variants
actually provide wiring capacitance. The nominal two-conductor structure emits
three positive capacitors totaling 2.658826 fF. Each of `hrhc`, `lrhc`, `hrlc` and
`lrlc` emits **zero** wiring capacitors. All five processes complete normally;
this is a completed **FAIL_MISSING_WIRING_CAPACITANCE_CORNERS**. The pinned
technology restricts the wiring-capacitance definitions to its nominal variant.
The sheet/via resistance tests above therefore establish resistance corners
only. Neither the variant names nor the three transistor PVT patterns establish
qualified high/low RC corners. No missing corner coefficient is fabricated.

### 26 September update: wide-metal spacing checks exposed a real gap

The completed 50 µm tiled main run on GDS `8874f5c5…` reports **672 raw
`M3.e` markers across the complete 560-category inventory**. None is waived.
An unchanged-deck comparison on the full SP macro passes in deep, flat and
500 µm tiled modes, but reports 30 markers with 50 µm tiles. This discrepancy
is **not evidence that the smaller-tile markers are harmless**.

A new independent geometry control contains five pairs of 0.7 µm-wide
parallel conductors, lengths 10–686.08 µm, with a deliberately illegal
0.21 µm gap. Two additional pairs use the legal 0.24 µm gap. The locked
`Mn.e` implementation misses all five faults in deep, flat and tiled modes.
KLayout documents that default shielding can hide coincident features when
one checked layer is a subset of the other; this applies to the wide subset
produced by erosion followed by dilation. See its
[shielding explanation](https://www.klayout.de/doc/about/drc_ref_layer.html#width).

A separate **supplemental** flat check adds `transparent` to that operation,
retaining the locked 0.39 µm width, 0.24 µm gap and >1 µm parallel-run limits.
It detects all five faulty pairs (ten directed markers), with no markers on
the two legal pairs. On the actual SRAMs it identifies **two distinct pairs
in SP and four in DP**, across Metal2 and Metal3. The original deck and all
contradictory/failing reports are preserved. A historical unchanged-deck PASS
therefore does not close wide-line spacing or production acceptance.

A new geometry candidate retracts the six affected rail edges by 30 nm,
without altering the circuit hierarchy or device layers. Its complete
flattened metal differences match the six prescribed cuts exactly. Both
macros then pass the supplemental check. The first candidate's unchanged
main check catches pin annotation polygons extending beyond the trimmed
metal; a second candidate also trims those corresponding pin polygons.
Full main DRC, transistor LVS, fresh parasitic characterization and chip
integration of the final candidate are required before it replaces the
previous evidence. No timing or physical PASS is transferred to a changed GDS.

The clean **local** source replay at `de73328` completes 1,607 pytest passes,
zero failures and 14 explicitly recorded skips; its front door has 18 passes,
zero failures and three skips. Earlier README-length and missing-publication-
marker failures are retained. This is source regression evidence, not a
foundry approval or a replacement for the open physical gates.

The rail-and-pin second candidate now passes **all 560 unchanged main categories
and full transistor LVS for both standalone macros**. An expanded independent
check covers eleven wide-line rules (Metal1–Metal5 `e`/`f`, plus recommended
TopMetal2 `bR`). Eleven deliberately illegal controls are detected and their
eleven legal counterparts produce no markers; both repaired macros also have
zero supplemental markers. Fresh whole-core checks are still running. Trimming
a 0.70 µm rail to 0.67 µm changes its resistance and current density, so old
parasitic, timing or reliability results cannot be carried over as acceptance.

### Independent two-conductor capacitance benchmark

A nominal FasterCap/KPEX benchmark uses two overlapping but electrically
separate 10 µm by 1 µm Metal1/Metal2 rectangles. The original export has **no
exposed subcircuit ports**, even when matching pin polygons are supplied. Its
five positive capacitors do reproduce the grounded 2×2 numerical matrix within
the export's six-significant-digit rounding, but the native empty-port component
is not a usable connected model. A separate explicit three-port matrix model
passes two ngspice AC excitations; actual coupling-deletion and 10% coefficient
fault circuits fail the expected current-column check.

The 0.01 and 0.003 requested numerical tolerances complete normally. The latter
reports a 0.00177261 final refinement difference; the grounded matrix changes
by **0.815%** relative to the coarse result. The stricter 0.001 attempt fails at
its 2 GiB address-space bound. KPEX nevertheless returns zero and exports an
intermediate matrix, so the independent child-log audit explicitly **rejects**
that result. Successful wrapper exit alone is not a solver acceptance gate.

The completed 0.003 result gives 1.006375 fF mutual capacitance; the native Magic
control gives 0.67225 fF, a **49.7% difference**. Both use the same two conductor
rectangles, but their dielectric, substrate and fringing approximations are
not independently process-calibrated equivalents. This comparison establishes
a discrepancy to resolve, not which extractor is physically correct. It is not
a SRAM extraction, an RC process corner, a calibrated parasitic model or foundry
approval; no arbitrary scale factor is applied to force agreement.

The public `check_fastercap_completion.py` now rejects fatal diagnostics even
when a caller supplies return code zero. It also requires the final matrix,
completion footer and achieved requested tolerance. Fifteen focused tests pass;
replaying the actual two completed logs and the masked out-of-memory log gives
the expected two accepts and one rejection. This is an execution gate, not
parasitic-model qualification.

The repaired macros also pass fresh OpenDB LEF imports checked against their
new GDS and independent CDL: 148 SP ports and 88 DP ports, named pin metal
coverage, direction/use and internal geometry coverage by obstructions or pins.
Four actually imported corrupt LEFs (shifted clock pin or missing Metal1
obstruction, for each macro) are rejected. The nominal macro outlines and
Metal4 external power accesses remain unchanged.

A separate prepared-fixture replay executes all fourteen tests skipped by the
clean local clone, with fourteen passes and no skips. The base, full-array,
base-SRAM-logic and full-SRAM-logic lint profiles also complete with their
existing 987, 1,015, 1,012 and 1,040 warnings respectively: no new/stale inventory
entries, no unaccepted own-source warnings and no RTL source drift. These are
separate measurements, not edits to the historical clean-clone skip record.

For the two-conductor control, the bundled stack has a 0.54 µm Metal1–Metal2
surface gap and dielectric constant 4.1. Its ideal parallel-plate value for
10 µm² is 0.6722624 fF, within 18.5 ppm of Magic's area coefficient result.
Nine native offset extractions, including ±5 nm and ±10 nm, show a continuous
response around coincident edges at those sampled points. Thus neither an
area-term discrepancy nor a large sampled edge discontinuity explains away the
49.7% finite-conductor difference. Fringing, shielding, substrate treatment and
process calibration remain to be resolved. No model coefficient is adjusted.

The eleven-rule transparent supplement also has a validated 50 µm tile / 30 µm
border / two-thread execution variant. Exact offending-edge coverage agrees
with flat execution on short controls, 686.08 µm controls crossing many tiles,
and both original/repaired macros. Raw duplicated and clipped tile markers
are retained; the audit compares physical coverage and rejects deleted gaps,
spurious gaps and truncated coverage. This validates the tested execution
variant; its whole-core result remains a separate required measurement.


### Current rail-and-pin candidate and process reference

The exact repaired whole-core GDS (`f218313c8a9e3ebe95e35cf0fc505852d88d342e9c2c6b4423f10a309f1a4cf1`)
now passes full transistor LVS (130 matching circuits and 5,129,488 primitives
per side), seven density categories, 31 antenna categories and the eleven
unshielded wide-line rules. The completed supplemental run uses eight threads,
50 µm tiles and a 30 µm border; its independent six-case geometry audit passes.
The earlier flat and two-thread full-core supplement timeouts remain failures.
The fresh 443-category FEOL/geometry and 117-category BEOL partitions now
both pass: **all 560 native main categories have zero markers**. The
[physical checkpoint](evidence/sram-repaired-core-physical-20260926.json) binds
all results to that exact GDS; the
[lossless GDS/report archive](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/docs/evidence/sram-repaired-core-physical-20260926.tar.xz)
retains the actual candidate, raw reports and source identities. This is a
32-SRAM digital core, not a complete pad-framed product or manufacturing approval.

The original V4 controller still records its final error because it required
the earlier failed two-thread supplement. The independent finalizer verifies
every complete native report, the exact 560-category inventory, LVS database,
GDS hash and the successful separately validated eight-thread supplement.
No failed or timed-out measurement is promoted. The report parser was updated
only after both physical consumers reached terminal states: exact declared
`name:variant` cell identities are now supported, with all markers retained.
Thirty-one public parser tests pass, including nine new cases; the two actual
failing macro reports retain their 16/8 markers, and ten corrupted reports are
rejected. Original parser/test source bytes remain explicitly snapshotted.

Both repaired SRAM macros also pass fresh MOS graph and full C-export audits:
37,076 DP and 202,800 SP transistors, including all named ports, with deliberate
connection/width/output faults rejected. Comparison through independently proved
net bijections preserves every transistor including junction parameters, but
changes 1,300 DP and 1,184 SP capacitor endpoint pairs. Even with ideal fixed
supplies, 971 DP and 793 SP pairs change. Consequently the earlier layout
transient measurements are historical results, not timing acceptance for this
new geometry. Fresh simulations are required.

The pinned SG13G2 process specification Rev. 1.2, pages 6, 18 and 24,
provides useful **informational** area-capacitance references. Visual and XML
inspection confirms that the section 2.17 limits are bold blue: they are
measured on each wafer but do not cause wafer rejection. The stated test is
250 × 1,200 µm² at 0 V and 100 kHz. Published adjacent-metal min/target/max
values are 54/68/82 aF/µm² for M1–M2 through M4–M5, 36/42.5/49 for
M5–TopMetal1 and 10/13/16 for TopMetal1–TopMetal2. These are not a complete
qualified RC corner model; see the official
[process parameter tables](https://ihp-open-pdk-docs.readthedocs.io/en/main/process_specs/02_process_control_params.html)
and [parameter classification](https://ihp-open-pdk-docs.readthedocs.io/en/main/process_specs/01_02_process_control.html).

Reproducing that large plate exposes another extractor arithmetic defect:
Magic's overlap/shield area uses signed 32-bit integers. A 250 × 1,200 µm²
rectangle at the actual 5 nm grid contains 12 billion grid squares; its mutual
capacitance disappears in the predecessor runtime. An isolated 64-bit-area
build retains the process coefficients and passes ten actual extraction
controls spanning the overflow boundary and fully intervening Metal2 shields.
Five of those same structures fail on the predecessor runtime. Native `.ext`
six-significant-digit rounding is explicitly bounded; the initially tighter
1 ppm comparison failure is retained rather than discarded.

The isolated build extracts nominal area coefficients of 67.225, 42.708 and
12.965 aF/µm² for those three groups, respectively, on both the published test
area and the 10 µm² control. They lie within the informational ranges; this
checks the area term only. Full SRAM re-extraction with this runtime now passes both complete MOS graph
and capacitor-export audits. Independent canonical comparisons find **zero**
changed transistor/junction records or capacitor endpoint-pair sums against the
already audited repaired-geometry models, for both macros. The new-geometry
transient inputs therefore represent the same C-only equations; this does not
transfer any old-geometry timing result or qualify distributed RC.
The finite-wire fringing discrepancy, coupled-RC conservation, correlated
process corners, complete characterization, final STA and manufacturing
approval remain unresolved. No global PDK or running tool was replaced.


The fresh SP run also exposes a convergence-reporting distinction. Ngspice 42
reports an initial singular matrix, then completes dynamic GMIN stepping. The
matching distribution source resets temporary diagonal conductance to the
configured `gshunt` and performs a final Newton iteration before reporting
completion; the default `gshunt` is zero and the benchmark does not override it.
This is recorded numerical startup recovery, not evidence of a completed
transient. The [ngspice 42 manual](https://ngspice.sourceforge.io/docs/ngspice-42-manual.pdf)
describes this operating-point recovery sequence.

The new `check_ngspice_transient.py` requires a completed ngspice 42 footer,
matching waveform row count and exactly ordered startup recovery. It retains
the specific recovered warning and rejects unknown, repeated, late or
unrecovered warnings. All 24 focused tests pass. Two actual small circuit runs
(direct and forced dynamic GMIN), three completed DP waveform replays, an actual
bad-model run and the intentionally stopped old SP run produce their expected
verdicts. The SP finalizer will still require the entire new 150 ns waveform,
read/write/hold checks and deliberately corrupted-wave controls before accepting
that single C-only functional point. Full RC and timing qualification stay open.


The first fresh repaired-DP C-only TT run now completes the full 78 ns pattern:
37,076 MOS devices and all 202,674 capacitors, 1.2 V, 25 °C, 100 ps input ramps,
5 fF loads and a 50 ps maximum step. Six reads, both addresses, byte writes and
the clock-pause hold checks pass across 694 stable samples. Its 20 rising and
20 falling transitions give a maximum delay of **2.642352 ns**, maximum
20%–80% slew of **0.242744 ns**, and **118.176514 pJ** total supply energy over
8–78 ns. Wrong-output and wrong-supply waveform controls are rejected. This is
a new measurement of the repaired geometry, not a copied old result; the
50 ps numerical resolution bound and missing distributed resistance remain
explicit. The [complete point record](evidence/sram-repaired-dp-tt-20260926.json)
includes the archive hash and every member hash; the
[lossless waveform/model archive](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/docs/evidence/sram-repaired-dp-tt-20260926.tar.xz)
contains the actual measured circuit, stimuli, log and waveform. Pinned external
PDK, OSDI and simulator dependencies are identified separately; no tool binary is
redistributed. The completed SS and FF transistor-corner results are listed below.

A separate 25 ps maximum-step replay is running to measure numerical sensitivity
for all forty observed transitions. A dependent one-arc setup measurement waits
for that complete baseline and then measures a fresh read-address capture and
5% delay-degradation bracket; it does not reuse the schematic bracket. Its
preflight retains the initial rejection of a 50 ps waveform by the 25 ps
sample-count gate. An explicitly separate 50 ps replay uses the corresponding
40-sample minimum and rejects four waveform faults; the queued 25 ps campaign
still requires at least 80 stable samples. These are pending measurements, not
completed setup tables or Liberty qualification.

### Fresh repaired-DP transistor corners

Both additional 78 ns corner patterns complete with six reads, two addresses,
byte writes, hold checks and both deliberately corrupted-wave checks passing.
Each uses the exact same 37,076-MOS, 202,674-capacitor circuit, 100 ps input ramps,
5 fF output loads and 50 ps maximum timestep. Each point measures twenty rising
and twenty falling transitions.

| Transistor corner | Supply / temperature | Maximum delay | Maximum 20%–80% slew | Supply energy, 8–78 ns |
|---|---|---|---|---|
| TT | 1.20 V / 25 °C | 2.642352 ns | 0.242744 ns | 118.176514 pJ |
| SS | 1.08 V / 125 °C | 4.406603 ns | 0.422727 ns | 90.134740 pJ |
| FF | 1.32 V / −40 °C | 1.711751 ns | 0.154099 ns | 145.967020 pJ |

The [corner record](evidence/sram-repaired-dp-corners-20260926.json) and
[lossless corner waveforms](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/docs/evidence/sram-repaired-dp-corners-20260926.tar.xz)
reference the already published TT circuit/model archive and preserve exact
corner stimuli, logs and hashes. These change transistor PVT with nominal
geometric capacitance; they are not qualified RC process corners. The generic
energy helper retains its historical “schematic” scope string; the actual
measured circuit contains all stated capacitors. Energy is total pattern supply
energy, not per-arc internal power or isolated leakage. Distributed resistance,
complete Liberty tables, final SoC timing and manufacturing acceptance stay open.

The [dated local-method checkpoint](evidence/sram-local-methods-20260926.json)
and its [source archive](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/docs/evidence/sram-local-methods-20260926.tar.xz)
preserve 345 source/record members, including geometry repair, verification,
prior failed supplements, parser source history and code for pending simulations.
Pending-job code is not evidence of completed execution. The full SP, step
sensitivity and one-arc setup campaigns remain active and are not frozen as passes.

The exact local commit `e5da995bcda6b5e8a23ee57007f8672ae3831130` passes a
fresh clean-clone replay before pushing: **1,655 pytest passes, zero failures,
14 explicit fixture/tool skips**; the front door records 18 passes, zero failures
and three skips. The [audited replay](evidence/sram-local-replay-e5da995-20260926.json)
and [raw replay archive](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/docs/evidence/sram-local-replay-e5da995-20260926.tar.xz)
retain the complete JUnit inventory, skipped reasons, command, logs and source
tree. This is a local clone, not a GitHub runner or a new physical measurement.
The earlier prepared-fixture and lint results retain their separate scopes.

**26 September — all fourteen pytest skips executed:** a new isolated local
clone of `edc4e2da7b6e806c021dc90cec46939fb242846e`, with freshly regenerated
Ibex RTL and the pinned TinyTapeout tooling, completes the full suite with
**1,669 passes, zero failures and zero skips**. The test inventory is identical
to the earlier 1,655-pass/14-skip replay. No test assertions, skip conditions or
RTL sources were changed to obtain this result.

The [audited prepared replay](evidence/prepared-pytest-edc4e2d-20260926.json)
identifies all fourteen previously skipped cases individually. Twelve exercise
Ibex delayed-store/branch behavior, including the two required failing-control
configurations; one checks the generated register-file entry contract; one
verifies the TinyTapeout tool revision. The
[raw archive](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/docs/evidence/prepared-pytest-edc4e2d-20260926.tar.xz)
contains the full JUnit inventory, preparation and pytest logs, runner and
independent audit source, with per-member and archive SHA-256 digests.

Preparation checked out Ibex `34b0705760ef3dfa00e99637432473d2be8f22f3` and
TinyTapeout tools `01d5d2814fa9dd61e9d211e0b235a4a592a9316a`. It downloaded
sv2v v0.0.13, verified its release ZIP against the repository's pinned SHA-256,
and regenerated all 34 Verilog files through `hw/soc/flow/sv2v_ibex.sh`.
Icarus Verilog 12.0 executed the CPU simulations. The prepared clone remains
clean; fetched/generated dependencies are confined to ignored directories.

To prepare these particular dependencies in a fresh checkout with the existing
Python test environment and Icarus available:

```sh
make -f hw/soc/tools.soc.mk fetch-sv2v fetch-ibex
bash hw/soc/flow/sv2v_ibex.sh hw/soc/ext/ibex hw/soc/gen hw/soc/tools/sv2v-Linux/sv2v
git clone https://github.com/TinyTapeout/tt-support-tools tt/tt
git -C tt/tt checkout --detach 01d5d2814fa9dd61e9d211e0b235a4a592a9316a
.venv/bin/python -m pytest sw/tests -q -rs
```

Other suite dependencies remain as documented by the project; the archive
records the actual local environment and commands. This closes the fourteen
pytest skips, not the three separate historical CI front-door skips or the
outstanding characterization/manufacturing gates. The earlier clean-clone
record remains unchanged as historical evidence.

## 25 ps numerical-step publication

The [completed comparison](evidence/sram-repaired-dp-timestep-20260926.json)
now publishes the full 25 ps waveform and all forty transition comparisons.
Only the maximum numerical step changes from the separately published 50 ps
TT case: circuit, model specialization, load and stimulus bytes are identical
after normalizing output-directory paths. Maximum absolute differences are
0.020866732 ns delay and 0.001574689 ns slew; total supply energies are
118.176514 and 118.116859 pJ. Both functional error controls were rejected.
The archive retains the failed initial invocation and its failed comparison.
This measures numerical sensitivity; it does not establish the zero-step limit,
complete Liberty tables or qualified distributed/coupled RC.

The [local closure continuation](103-local-closure-progress.md) records newer
RTL/profile checks separately from these transistor-level measurements.

### Repaired DP read setup and complementary retention, 26 September

[The completed eight-run measurement](103-local-closure-progress.md#repaired-sram-read-constraint-measurement)
finds a rising `a2[0]` setup boundary between −265.625 ps (fail) and −250 ps
(pass) for the repaired capacitance-only layout at TT/1.2 V/25°C, 100 ps ramps,
5 fF load and 25 ps maximum step. Old-word retention on those same waveforms
passes at +265.625 ps but fails at +250 ps. That observation is not an
independent hold-characterization run. Full tables, both transition directions,
other pins and PVT/load/slew coverage remain required; no Liberty acceptance
is implied by this single boundary.

## Native intrinsic-ground-capacitance reader repair

The [reader experiment](evidence/magic-groundcap-reader-20260926.json) identifies
another specific defect in Magic 8.3.623: `ResReadCapacitor` adds incident coupling
to the extresist nodal total, while `ResReadNode` did not read the intrinsic
node-to-ground capacitance in field 3 of the native `.ext` record. The isolated
[source patcher](../scripts/patch_magic_groundcap_reader.py) now adds that field.
It accepts only two exact, recorded source identities and writes a new file;
it does not change the installed PDK or any previous runtime.

Four actual cells were extracted with and without this change, first on the
historical tool configuration and then on the combined fractional-sheet,
port-alias and serialization configuration with the repaired DP GDS. Each pair
passes an [independent accounting audit](../scripts/audit_magic_groundcap.py):
source geometry/capacitance records agree; physical MOS instances establish an
explicit node bijection; every weighted resistor, MOS terminal and `killnode`
record agrees; and the added capacitance on each logical net equals the native
intrinsic input within the existing serialization tolerance. Resistors are
not collapsed for the topology comparison. Repeated `rnode` names are summed,
as the native reader does, instead of overwriting earlier records.

The four intrinsic totals are 842.073617, 3084.704356, 1517.165600 and
8402.020590 aF. Both tool configurations pass all four paired controls and
reject 24 deliberate faults each. Twenty targeted software tests pass with
zero skips. Bytewise/order-dependent initial checks and incomplete accounting
attempts remain archived. The largest cell has ten historical and nine combined
coordinate-metadata differences despite identical weighted topology; these are
reported explicitly, and **spatial capacitance placement is not proved**.

[Historical stage inputs](evidence/rc-stage-inputs-20260926.json) make the
separate full-macro diagnostic replayable. Native record removal explains
189,054 lost coupling pairs; distributed ground capacitance mostly reflects
incident coupling alone. One supply-pair residual remains. Repairing the
intrinsic input does not preserve those coupling pairs, remove duplicated
retained capacitances, establish physical RC corners or qualify extraction.
The existing capacitance-conservation failure is not changed into a PASS.

The archive also contains an immutable method snapshot of the next **running**
RC extraction on the repaired full DP macro. It contains no accepted full-macro
result. Final capacitance-only characterization evidence remains separate
until topology, coupling, parasitic models and process corners are validated.

The [completed corner timestep comparison](evidence/sram-dp-corner-timestep-20260926.json)
now adds SS at 1.08 V/125°C and FF at 1.32 V/−40°C to the earlier TT comparison.
Both fresh 78 ns patterns complete at a 25 ps maximum step, using the same
repaired 37,076-transistor, 202,674-capacitor macro, 100 ps ramps and 5 fF loads.
Each passes the observed read/write/hold/byte pattern and rejects the two
measurement faults. All forty read transitions per corner are compared against
identical-model/stimulus 50 ps runs; neither run has a recorded warning/error.

| Transistor corner | Maximum absolute delay change | Maximum absolute output-slew change | 50 ps / 25 ps supply energy |
|---|---:|---:|---:|
| SS, 1.08 V, 125°C | 16.273267 ps | 1.050383 ps | 90.134740 / 90.176169 pJ |
| FF, 1.32 V, −40°C | 22.532888 ps | 4.746665 ps | 145.967020 / 145.827227 pJ |

These measured differences are numerical sensitivity, not a zero-step limit
or an accuracy guarantee. They do not supply additional slew/load points,
complete timing constraints or RC process corners. The earlier methods-only
running snapshot remains unchanged; this new record contains completed results.

The [new full-DP source preflight](evidence/repaired-dp-rc-source-preflight-20260926.json)
also passes: all 350,997 native source records, including 37,076 MOS devices
and 192,423 coupling records, match the independently audited repaired
capacitance-only extraction up to record order and capacitor orientation.
A removed coupling is detected. The reference was restored from its published
archive and matched its original digest. This verifies the completed input
extraction stage while the resistance extraction continues; it does not accept
the unfinished RC network or its serialized capacitance matrix.

The combined raw controller inherited the word “ten” in its free-text scope
from the historical run. Its actual coordinate-difference records contain nine;
the public metadata records this prose erratum without changing frozen inputs
of the ongoing extraction. The numeric checks and verdict are unaffected.

## Repaired SP TT completion and full DP RC rejection

The [completed repaired SP TT receipt](evidence/sram-repaired-sp-tt-20260926.json)
records 202,800 MOS devices and 821,222 geometry capacitors, a 150 ns pattern,
100 ps input ramps, 20 fF output loads and a 50 ps maximum numerical step.
All four reads at two addresses, including a byte-masked write, pass 417 stable
samples. Wrong output, ignored byte write, extra clock, wrong address and wrong
supply waveforms are each rejected. Across 120 measured transitions the largest
rising/falling delays are 3.889866/3.965940 ns and the corresponding maximum
20–80% slews are 0.430800/0.404061 ns. Integrated pattern supply energy from
8 to 150 ns is 377.998133 pJ. These selected measurements are not timing tables,
isolated internal power or leakage characterization.

The original producer reports ERROR because it rejects every warning. Its log
contains a singular-matrix startup warning, followed by successful dynamic GMIN
recovery and completed transient execution. The separate completion auditor,
implemented before the result was available, verifies that recovery, the complete
waveform, unchanged inputs and the five negative controls. Both verdicts and the
warning remain in the raw archive. Neither a zero-warning claim nor a final STA
acceptance follows. Repaired SP SS/FF patterns are running. A 25 ps TT replay is
queued behind both corner jobs to limit memory use; its
[method snapshot](evidence/closure-followup-methods-20260926.json) is not a result.

The new [full repaired DP RC diagnostic](evidence/sram-repaired-dp-rc-diagnostic-20260926.json)
contains 146,385 resistors and 115,869 capacitors. After collapsing resistors, an
exact graph bijection matches all 37,076 MOS devices, 10,272 nets and 88 ports to
the independent schematic. Removing a real terminal resistor breaks that match.
All resistor components have anchors; no capacitor endpoint is an isolated
capacitor-only node. Terminal resistance attachment and physical model accuracy
still require review. The first audit attempt lacked KLayout in its interpreter;
its failure was retained before executing the unchanged audit with `kpex-env`.

**Capacitance conservation fails.** Relative to the independently audited
capacitance-only export, 189,054 node pairs are missing, twenty are extra and
10,251 retained pairs have different values. The reference capacitor-value sum
is 27.396033 pF versus 51.847337 pF in the RC export; this sum is a diagnostic,
not a circuit's equivalent capacitance. The
[text-stage attribution](evidence/closure-followup-methods-20260926.json) finds
that native resistor extraction grounds incident coupling during distribution,
while some original ground and coupling records remain in the serialized output.
It accounts for the output to the recorded residual on one power pair. Restoring
intrinsic ground C in the reader therefore does not supply a conserved spatial
coupled-C model. This RC export is rejected for final timing or simulation claims
that require qualified RC. No characterized Liberty or final STA is generated
from it.
