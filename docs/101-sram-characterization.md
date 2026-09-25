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
