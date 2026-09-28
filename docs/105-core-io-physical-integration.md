# Core, I/O and MBIST status physical integration

The 27 September integration candidate combines the selected physical core,
native IHP I/O ring and the synthesized 192-bit read-only MBIST status mailbox.
It is an engineering candidate, **not production acceptance**. The independent
I/O-cell LVS campaign fails all seven selected signal/supply masters. Full-chip
LVS, finishing, full timing and manufacturer acceptance therefore remain open.

## Exact core and power domains

This assembly uses the preserved **CORE_REQ_REG=0 / CORE_WB_STAGE=0** core,
including its 32 independently referenced system/Ethernet SRAM instances. Its
pre-dummy-fill GDS SHA-256 is
`421c1f5b190bc0ecf2cac640785f3951a662a2d0ba275951fa00b9e29b2508d9`.
The simultaneously running request/writeback-stage **1/1** timing candidate is
a different layout and cannot inherit this assembly's results.

The 4,000 × 3,200 µm parent places the 3,326.4 × 2,475.9 µm core at
(336.8, 362.05) µm and retains the 314 native ring placements. The ring includes
102 signal pads, four supply pads, corners and fillers. New standard cells
implement the status mailbox and parent clock trees. VDD/VSS feed the core and
mailbox; IOVDD/IOVSS remain on the native ring. The previous default secondary
power grid and blanket core obstructions produced disconnected rails. Their
failed runs are preserved.

The corrected flow requires native `check_power_grid` to succeed separately
for **VDD, VSS, IOVDD and IOVSS**, instead of allowing the native flow's caught
connectivity errors to continue as warnings. All four pass the new PDN check.
This is abstract OpenDB supply connectivity, not extracted GDS connectivity,
current capacity, IR/EM, ESD or package qualification.

## Actual geometry controls the routing abstract

`hw/soc/flow/compact_core_abstract.py` conservatively compacts the five lower
routing-metal obstruction layers of the native OpenROAD abstract. It retains
all upper-metal obstructions and all pin/via/macro metadata. Its independent
verifier rejects removed upper shapes, a shrunken lower envelope and changed
pin metadata. Unsupported or incomplete inputs fail closed.

`hw/soc/flow/cover_core_abstract.py` additionally checks the selected GDS against
the selected PDK layer map. Both **drawing and filler** purposes count as real
conductors. Lower metals are blocked over the entire macro die after checking
hierarchical bounds. Uncovered upper-metal geometry receives conservative
obstruction rectangles; upper-metal power pins must be backed by actual GDS
metal. The input GDS is never modified. Six deliberately invalid hierarchical
fixtures are rejected; both filled and unfilled valid fixtures pass.

The initial drawing-only check missed upper-metal dummy fill and is explicitly
superseded. The complete filled-GDS check found 27,008 TopMetal1 filler polygons
and 30,186 TopMetal2 filler polygons. Including them correctly caused the
parent's power-connectivity check to fail. The finished original core GDS is
preserved unchanged; the assembly instead selects its preserved **pre-fill**
geometry. After parent routing, whole-chip dummy fill and fresh density,
antenna, DRC, LVS and RC checks are required. The earlier filled-core density
pass does not apply to this assembly.

On the selected pre-fill core, the native ODB-only abstract also omitted
67.4695 µm² of upper-metal drawing geometry. Adding 84 conservative rectangles
closes that abstract-coverage gap. Replaying the tracked helper reproduces the
selected LEF byte for byte, SHA-256
`b4c9db893d0ebad2ed3a89b8f6f79e2762992d8fc13d9f609ac7d8fef9f7e2ff`.

## I/O transistor LVS: discovered blocker

The native I/O CDL has an empty `.PARAM` line, 64 X-prefixed `ptap1` devices and
29 resistors using the `res_rppd` model spelling. The pinned native KLayout
reader represents these taps as R-prefixed `CustomTap` devices and these poly
resistors as `rppd`. `hw/soc/flow/normalize_io_cdl.py` performs only these
explicit dialect conversions. Every node and parameter value is retained;
conversion is reversible. It is not a replacement SPICE model.

Independent parsing of the **original** vendor file agrees with the native
reader on all 64 tap terminal pairs, areas and perimeters, and all 29 resistor
terminal triples, widths, lengths, spacing, multiplier and bend parameters.
Five deliberate node/parameter corruptions are rejected. This establishes
conversion fidelity only.

The separate native-deck LVS campaign on the original native GDS **fails all
seven selected masters**: `sg13g2_IOPadIn`, `sg13g2_IOPadOut4mA`,
`sg13g2_IOPadInOut4mA`, `sg13g2_IOPadVdd`, `sg13g2_IOPadVss`,
`sg13g2_IOPadIOVdd` and `sg13g2_IOPadIOVss`. No skipped or mismatching circuit is
accepted. For example, input-pad extraction splits protection-diode nodes,
reports different tap perimeters, and does not reproduce the source's series
resistor in `sg13g2_SecondaryProtection`. These remain unresolved connectivity,
reference-model or extraction-deck issues; the report does not assume which
side is authoritative without further proof.

The [upstream I/O update at 1a29eb4](https://github.com/IHP-GmbH/IHP-Open-PDK/commit/1a29eb4980d520d9ce7273593dc1599310cb81a9)
was also investigated. Its GDS was independently downloaded and checked against
the GitHub blob ID and byte count. Its selected input pad still fails the
unchanged strict native LVS comparison. The original PDK and running parent
layout are not replaced with that candidate. The upstream main revision checked
on 27 September is the same `5e6d592` as the pinned LVS deck, so this experiment
already uses that published deck revision. No tap extraction, port matching,
parameter comparison or internal circuit is disabled to obtain a pass.

## Remaining acceptance work

Physical integration does not supply missing core/SRAM Liberty. The parent
uses real native standard-cell/I/O timing libraries and 20 ns CPU, 8 ns Ethernet
and 200 ns serial-test clocks, but the hard core has no qualified aggregate
Liberty. Parent timing reports cannot establish full-chip timing, SRAM arcs or
the mailbox's bundled-data CDC constraint. The status port also remains
read-only; it is not scan/ATPG, JTAG or RISC-V debug.

Qualified SRAM PVT/RC, complete PCIe Gen3 x4 PHY/controller and differential
pads, package/bond/passivation/seal-ring integration, full-chip DRC/LVS/RC,
DFT/CDC coverage and actual manufacturer approval remain required. See the
[product gap ledger](102-remaining-product-gaps.md) and
[local closure history](103-local-closure-progress.md). No production claim
is derived from a zero router marker count or from the earlier IO-only DRC pass.

## Completed routed assembly

The local parent flow completed detailed routing and antenna repair with
**zero router DRC markers and zero antenna nets/pins**. Native GDS streamout
then failed because identical I/O LEF/GDS views were specified twice. After
byte-verifying both aliases, a separate recovery resumed only streamout from
the exact completed route/RCX/diagnostic-STA checkpoint. No route, cell view or
PDK file was changed by that recovery.

The resulting chip GDS has SHA-256 `40b683aefbedccfde313fb8323ef4591794fae4557a8722d8af86158fff91e6b`.
An independent recursive comparison preserves the exact shapes, text and child
placements of **217 selected core/I/O cells**, allowing only the consistent
cell renaming performed by streamout. All **315 fixed placements** (one core
and 314 ring instances) match the intended transforms. A renamed-cell control
passes; extra metal, missing text, wrong layer, moved instance and missing
instance controls all fail. This comparison does not certify the new parent's
interconnect connectivity or DRC.

Final OpenDB verification also checks the core's two supply ports and the
ring's 1,256 supply ports before rerunning all four required power-grid checks.
They pass. Full transistor I/O LVS still fails as documented above; no final
chip LVS or native whole-chip DRC pass is asserted.

The three parent-only diagnostic STA corners report positive worst setup/hold
slacks (aggregate 14.148 ns / 0.115 ns). The opaque core and missing product
I/O/CDC timing contract make these **ineligible as final-chip timing evidence**.
The separate pipeline-core run still has negative intermediate timing and is
not part of this assembly's acceptance.

## Published replay evidence

The [source-bound integration receipt](evidence/core-io-integration-20260927.json)
and [asset inventory](evidence/core-io-integration-assets-20260927.json) retain
the passing method/geometry/power checks and the failed native transistor LVS
results with their distinct scopes. Source `452ff73` passes 48 focused source
tests without skips; the separate native controls are described above.

The [complete local experiment archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/core-io-assembly-and-lvs-blockers-20260927.tar.xz)
contains 1,891 members, including the actual chip GDS, selected core
and native I/O views, source, intermediate/failing attempts and native reports.
Archive size is 134,860,300 bytes; SHA-256
`aedd72e7d017b2fd56601e94d8b9d36aff1d7a830df62678342878bd49c83071`. Every member was read back and hashed, and both authenticated
and anonymous GitHub downloads match the local archive. Native tool binaries
and the original core ODB remain hash-bound replay dependencies identified
in the archive. Publication is not manufacturing approval.

The [follow-up method and delivery-check archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/core-io-followup-methods-and-checks-20260927.tar.xz)
contains the completed 290-test/documentation/license/digest checks, the
lossless scratch-reclamation inventory and a dated snapshot of the still-active
local BEOL and separate pipeline-timing jobs. The BEOL method checks the exact
new chip GDS against 117 pinned native categories under a 6 GiB address-space
limit and a 90-minute execution bound. **Its running snapshot is not a DRC
pass.** The separate core's intermediate setup slack remains negative; its
post-route equation comparison has not executed. Archive SHA-256
`971d30cf3e7b2fe80b7bf6f89dd5829d6e6f445f0fa7e01797fb239667b3ae66` (78,696 bytes) is verified locally and through both
GitHub download paths.

## I/O resistor recognition repair and remaining transistor mismatches

Source `def94d52bf54991a7cb3b6293ac8264fd45cb558` resolves a specific extraction
failure in the installed `c4b8b4e` I/O library. The physical resistor bodies,
poly, implant, salicide-block and extraction-block masks were already present,
but their **PolyRes recognition layer `128/0` was missing**. The unchanged
`5e6d592` LVS deck requires this layer. Without it, the 1 × 2 µm secondary
protection resistor disappears and its `pad` and `core` nodes appear shorted.

The new [repair generator](../hw/soc/flow/repair_io_resistor_markers.py) binds
the exact original GDS, CDL and electrical model hashes. It creates a separate
library and adds only 27 recognition rectangles: one in
`sg13g2_SecondaryProtection` and 26 in `sg13g2_RCClampResistor`. The 26 clamp
resistors each have width 1 µm and length 20 µm, independently specified in
the original CDL. It does not edit the installed PDK or promote this candidate
into the previously published chip GDS.

A read-back comparison covers all **46 cells and 41 layer/datatype pairs**:
all other polygon regions, all texts, and all child instance transforms/arrays
are preserved. An independent fixture passes; eight injected faults covering
missing recognition, mask changes, wrong dimensions, active overlap, text and
hierarchy changes are rejected by the repair/preservation checks.

A second, separate discrepancy is the default `ps=180n` spacing parameter on
straight resistors. The hash-bound native `rppd` electrical model uses `ps`
only in `leff=(b+1)*l+(2/kappa*weff+ps)*b`. For explicitly specified **`b=0`**,
this reduces to `leff=l`, independent of `ps`. The conversion canonicalizes
these 29 straight-resistor declarations to `ps=0`, which the native extractor
emits. It preserves every terminal and every other parameter. Bent resistors
are unchanged; missing, duplicate or symbolic bend/spacing values are rejected.
Tap area/perimeter comparisons remain enabled and unchanged.

Completed results on this new library are:

| Measurement | Result and limit |
|---|---|
| `sg13g2_RCClampResistor` native transistor LVS | Pass, unchanged native comparison; the 26 series resistors reduce to one 1 × 520 µm resistor on each side |
| Native LVS fault controls | Missing marker, wrong physical resistor length and wrong schematic connection each fail with a real `NoMatch` |
| RC clamp and input-pad main DRC | Both pass, zero markers; each catalog matches all 560 native main categories, including recommended rules |
| Seven I/O masters, transistor LVS | **All seven still fail** after the repair; no skipped circuit is accepted |
| Source regression | 181 tests pass, no skips; REUSE 1,477/1,477 at the source commit |

The input-pad experiment now extracts the secondary resistor with the correct
1 × 2 µm dimensions and separate `pad`/`core` nets. Remaining failures include
substrate-tap area/perimeter disagreement and supply/hierarchy connectivity.
For example, the DCN tap CDL specifies `A=141.253 µm²`, `P=47.54 µm`, while
native extraction gives `A=141.2964 µm²`, `P=221.76 µm`. Simply flattening and
making `sub!` explicit as a schematic global still fails. No tap parameter was
replaced by an extracted value to obtain a pass; no supply island was virtually
shorted to hide a physical connectivity requirement. A subcell success is not
seven-master or full-chip LVS acceptance. The two successful main DRC runs
also do not establish density, antenna, ESD, package or manufacturing approval.

The [repair receipt](evidence/io-resistor-repair-20260927.json),
[asset manifest](evidence/io-resistor-repair-assets-20260927.json) and
[complete experiment archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/io-resistor-recognition-and-native-checks-20260927.tar.xz)
retain the original failures, repaired GDS/CDL, sources, native reports and
fault controls. The archive has 179 members and 10,227,692 bytes, SHA-256
`f0ac1e16db48a2a87eaac40bcab89504602e28ba44237f5bbcdcc6b5141885ce`.
Every member was read back; authenticated and anonymous GitHub downloads match.

## Full-chip DRC resource failure and timing checkpoint

The first BEOL attempt on chip GDS `40b683...` emitted repeated
`ERROR: Worker thread: std::bad_alloc` under its 6 GiB address-space limit.
It was stopped and recorded as **ERROR**, with its original log retained.
A strengthened [DRC gate](../hw/soc/flow/check_ihp_drc.py) now requires the
execution log for every deck and rejects worker errors, allocation failures,
crashes and tracebacks even if the process returns zero and the report contains
zero markers. The relevant regression has 46 passing cases, included in the
181 total above.

The separately recorded retry uses the identical chip GDS and unchanged
117-category BEOL rule selection, one thread, a 10 GiB address-space limit
and a 90-minute bound. It terminates early on a logged execution error.
The archive captures it **running**, not passed. The pipeline-1/1 core has
progressed through setup/hold repair into detailed routing. Its final RCX/STA
and post-route equation checks have not completed at this checkpoint. Neither
running process establishes final timing or full-chip DRC acceptance. Qualified
SRAM Liberty/distributed RC, the complete PCIe Gen3 x4 PHY/controller,
complete DFT and actual manufacturer acceptance remain separate open gates.


## User-requested removal of the active BEOL time limit

The user subsequently requested that this BEOL run continue until it finishes,
without termination solely because its 90-minute deadline expires. The active
worker was **not restarted**: PID 1856520 and its original birth identity,
GDS, rule deck, command and resource limits are preserved. Input hashes were
verified before the handover. The previous running snapshot above records the
original policy; [this policy receipt](evidence/chip-beol-no-deadline-20260927.json)
supersedes its elapsed-time limit.

The [deadline-free supervisor](../hw/soc/flow/wait_without_deadline.py) pauses
only the original Python watchdog, PID 1856502, which is in a different process
group from KLayout. It leaves KLayout running. When the worker exits, it resumes
the original watchdog, whose completion check precedes its timeout check, so
that the original process exit status, input-hash checks and report/catalog
validation remain authoritative. A logged execution error also resumes the
original error handler, which precedes the timeout check. Memory limits and
rejection of incomplete/error-bearing reports remain in force.

Three live-process controls verify completion beyond the former deadline,
preservation of a nonzero worker exit, and preservation of the execution-error
handler. The receipt's `WAITING_WITHOUT_DEADLINE` state is a running-policy
record, **not a completed or passing DRC result**. If this observer is interrupted,
the original watchdog must remain paused while the worker is still running;
resume it for final validation only after the worker has exited, or to handle
a logged error. Its intentional stopped state must not be mistaken for a
stopped KLayout worker.


## Local output capacity while the physical jobs continue

The September 27 hourly follow-up found less than 700 MiB of free local disk.
To preserve capacity for pending routed views, only archived intermediate copies
were reclaimed. The [reclamation receipt](evidence/resource-reclamation-20260927.json)
records each removed path, original byte count, SHA-256 and exact archive member.
All original bytes remain recoverable; active inputs and final views remain local.

The first group comprises 28 pre-route assembly ODB/DEF copies and two superseded
I/O diagnostic GDS files, already present in independently verified published
archives: 208,197,902 bytes. A new [early pipeline stage archive](evidence/pipeline-early-stage-assets-20260927.json)
preserves a further 28 completed intermediate ODB/DEF files: 897,208,888 bytes.
The initial selection guard rejected a still-referenced stage-30 view, so the
final selection excludes it along with every original input pin and every
stage-31-or-later state reference. Nothing was removed until all archive members
and authenticated and anonymous GitHub downloads had passed byte verification.

Total reclaimed space is 1,105,406,790 bytes. The new archive contains 48 members,
is 98,348,800 bytes, and has SHA-256
`cc4c0c527dec0f808afe808791a4553abd8d9adf6a0afa11c93bcca7742f0f69`.
This is storage recovery, not a new physical pass. The initial detailed routing
reached zero router violations before antenna repair triggered another routing
pass; intermediate violations from that ongoing pass are not its final verdict.
The unchanged whole-chip BEOL measurement remains a separate unfinished check.


## Completed BEOL and queued pipeline recovery

The pre-fill core-plus-ring BEOL run finished at 19:24:58 TRT on September 27,
after 19,069.96 seconds. [The completed result](evidence/chip-beol-complete-20260927.json)
records exit zero, all 117 selected native categories and zero markers.
The deadline-free observer resumed the original controller after worker exit;
its original input-hash, log and category checks completed successfully.
This supersedes the running BEOL status above. Full-chip FEOL, density, antenna,
transistor LVS and final timing remain separate gates. The focused DRC-result,
deadline-supervisor and asset-verification regression suite passes 59 tests.

The separate pipeline-1/1 core finished routing and filler insertion with zero
router violations, zero antenna net/pin violations and zero disconnected pins.
Its cell-frequency-report step then failed while writing an ODB on a full
filesystem. [Recovery evidence](evidence/pipeline-disk-recovery-20260927.json)
retains the failure and exact completed stage-40 state. A local continuation
waits for both download channels of the large checkpoint archive to be verified,
then reclaims only those archived intermediate/partial files and resumes the
unchanged flow from `Odb.CellFrequencyTables` in a fresh directory. The original
failure stays recorded. RCX, final diagnostic STA and post-route equation proof
remain pending; routing and physical/timing checks are not bypassed.

[Completed native reports and recovery methods](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/chip-beol-completed-native-reports-20260927.tar.xz):
137,976 bytes, 41 members, SHA-256
`1d89b46f34d3dd0114646ea16c85ced3caabcd00511976b6e8e80f1a68950b66`. Every member and both authenticated and anonymous downloads
were byte-verified. [Asset inventory](evidence/chip-beol-complete-assets-20260927.json).
This small published archive includes the successful BEOL report and first
failed attempt, the pipeline disk-full diagnostics, 59-test log and continuation
source. The large routing checkpoint archive is separately still undergoing
public byte verification at this snapshot and is not claimed complete here.


## Remaining native rule campaign and timing diagnosis

A [resource-serialized campaign](evidence/chip-full-rule-campaign-20260927.json)
is queued behind the pipeline recovery. It uses the exact same pre-fill
core-plus-ring GDS as the completed BEOL check and reuses only that hash-bound
117-category result. Fresh measurements cover 7 density, 31 antenna,
443 FEOL/geometry and 11 supplemental categories. The native table/catalog
checks and rule decks remain unchanged. The prior successful deep-angle method
uses one worker and a 12 GiB address-space cap; there is no elapsed-time cutoff.
Execution errors remain errors and any geometry markers remain failures.
This queued campaign does not establish full-chip LVS or production approval.

The separate pipeline's completed global-route estimate reports worst listed
setup -7.733286 ns and hold -1.810861 ns, with eight maximum-capacitance
violations. The setup path runs from register-file x8 bit19 to mcycle bit1;
the hold path ends at `qspi_io_oe_o[3]`. These are intermediate estimates,
not the pending post-route parasitic measurement or final timing.

The [method archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/chip-full-rule-campaign-methods-20260927.tar.xz) preserves the queued controller source,
timestamped snapshot, raw intermediate timing reports and 84 passing native
result/catalog regression tests. 19 members, 65,176 bytes,
SHA-256 `098bddf5156f4deec57a0eb00fcf51e72f784b41253a270b7cbbc712ab206302`; every member and both download channels were
byte-verified. [Asset inventory](evidence/chip-full-rule-campaign-assets-20260927.json).


## Corrected chip boundary and completed pipeline timing measurement

The fresh whole-chip density run identified an actual input error: its inherited
`prBoundary` covered only 8,235,833.76 square micrometres while the complete
4,000 by 3,200 micrometre chip occupied 12,800,000. The native deck explicitly
reported shapes outside that boundary. That measurement was stopped for invalid
normalization, not for elapsed time; its controller error and log remain retained.

The existing boundary normalizer replaced only layer 189/0 using the exact
parent die rectangle on 189/4. A full GDS serialization roundtrip preserves every
other cell shape, text and instance transformation exactly; four positive/error
controls pass. Corrected GDS SHA-256 is `f9dc37b738fb33f2919c847263cc11cc6fc857653d1c394634ce9c4cd8966f52`.
[The evidence](evidence/chip-boundary-timing-followup-20260927.json) distinguishes
this geometry-preservation result from native DRC/LVS acceptance. All native
groups, including BEOL, must run freshly on this new GDS; the old BEOL pass is
not transferred. The corrected density run is in progress, followed by antenna,
FEOL/geometry, BEOL and supplemental checks under the resource-admission guard.

The separate pipeline-1/1 recovery completed RC extraction, all three timing
corners and GDS streamout. Its source-bound digital equation check passes within
its stated scope. The actual timing measurement **fails**:

| Corner | Setup WNS (ns) | Hold WNS (ns) | Setup endpoints | Hold endpoints | Cap violations | Slew violations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Fast | 3.107980 | -2.428406 | 0 | 76 | 22 | 0 |
| Typical | 0.548414 | -1.586352 | 0 | 30 | 22 | 3 |
| Slow | -9.014226 | -0.096859 | 1445 | 6 | 22 | 170 |

The reports contain `clk_i`, both Ethernet clock groups and generated `eth_gtx`,
in addition to asynchronous/path-delay groups. Despite the tool's generic
base-SDC warning, the explicit signoff SDC was supplied and these groups were
measured. Missing Liberty for 32 SRAM instances and nominal RC still preclude
qualified final timing even independently of the numerical failures.

A fresh standard-cell repair candidate now enables gate cloning, raises the
buffer allowance, and gives setup/hold repair 2,000/1,000 algorithm iterations
with 40-percent electrical margins. CPU/Ethernet periods remain 20/8 ns. Macro
masters, placements and orientations must remain unchanged. Hold repair may
trade setup slack; both must pass fresh measurements afterward. It reroutes and
re-extracts before another equation check, with no elapsed-time termination.
This is a running repair attempt, not a closed timing result.

The [complete corrected-boundary and measured-pipeline archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/chip-boundary-and-pipeline-measurements-20260927.tar.xz)
contains 174 members (139,110,184 bytes), including the new chip GDS,
completed pipeline GDS/ODB/SPEF, raw three-corner reports, equation proof, retained
failures, and both running-method snapshots. SHA-256 `257c2c816582c22332838b0bd09e0935e1145ca6a47c1d953aeb3c95e2269f78`.
[The asset inventory](evidence/chip-boundary-timing-followup-assets-20260927.json)
also records the now fully verified large routing-recovery archive and the
small corrected-restart method archive. All members and both public download
channels were verified.

Local storage recovery preserved all original measurement trees: a previously
verified published 1,223,361,276-byte archive cache was reclaimed after rechecking
its local SHA and current GitHub identity; the exact restore URL/hash are retained.
Byte-identical immutable CI-clone archives were hard-linked, retaining every path
and byte while recovering about 1.99 GB. These shared archived files must be
copied before any future modification. This storage work is not physical signoff.


## Completed chip density failure and controller recovery

The corrected-boundary native density measurement finished with process exit
zero but **207 violation markers**. It is a failed physical check, not acceptance.
All 37 density/slit rules ran; the report has 18 categories, of which 11 contain
markers. Seven slit categories are always emitted by this upstream deck, while
other categories appear only when a violation is found. The controller's old
fixed seven-category assertion therefore failed after the valid measurement.
Both the original controller error and native report are preserved.

The [new coverage check](../hw/soc/flow/check_ihp_density_coverage.py) requires the
complete ordered execution inventory and final completion record, rejects tool
errors, invalid boundary normalization, missing slit categories and unknown
categories, and retains every marker. 104 focused regression tests pass,
including failing-report and incomplete-execution controls. The continuation
also rechecks all original input, report and log hashes before reusing this
completed density **failure**; no density rerun or waiver is used.

| Native violation | Markers |
| --- | ---: |
| Local active minimum (`AFil.g2`) | 4 |
| Global M2/M3/M4/M5 minimum | 4 |
| Local M2 filler minimum | 55 |
| Local M3 filler minimum | 24 |
| Local M4 filler minimum | 59 |
| Local M5 filler minimum | 59 |
| Global TM1/TM2 minimum | 2 |

Global M2/M3/M4/M5 densities are 13.77/29.89/17.95/17.63 percent against
35 percent minima; TM1/TM2 are 23.64/18.27 percent against 25 percent minima.
The remaining unchanged antenna, FEOL/geometry, BEOL and supplemental checks
are queued behind the memory-admission guard. Whole-chip fill and fresh checks
will be required; the new controller does not turn this layout into a passing one.
The separate timing ECO remains in progress and is not this chip's geometry.

[Completed evidence](evidence/chip-density-recovery-20260927.json) and
[asset inventory](evidence/chip-density-recovery-assets-20260927.json) bind the
raw density report/log, retained controller failure, repaired continuation and
104-test log to the [immutable archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/chip-density-failure-and-campaign-recovery-20260927.tar.xz).
All 28 archive members and both public download channels were byte-verified:
144,660 bytes, SHA-256 `8ef5c6df7f707a26c94e0ec89466ab6c4f6c53f641d4ae976ce855e02504a0ff`.
Full-chip LVS, qualified final timing and manufacturing approval remain open.


## Parallel native chip checks on GitHub workers

The `chip-native-parallel` workflow separates antenna, FEOL devices, pin/forbidden,
grid, angle, BEOL and supplemental wide-metal checks into seven independent jobs.
Each restores the same corrected chip GDS
`f9dc37b738fb33f2919c847263cc11cc6fc857653d1c394634ce9c4cd8966f52`
and the exact previously pinned native/adapted decks. The bundle preserves the
validated table selectors, 50-micrometre BEOL tiling and supplemental rules;
it changes no geometries, thresholds or exclusions. It includes expected category
names and descriptions from complete prior controls, whose combined main catalog
must match all 560 native categories. Every new report must match its own catalog.

The [input asset inventory](evidence/chip-native-parallel-input-assets-20260928.json)
binds all 102 bundle members, including the GDS and rule inputs. Archive size is
19,206,144 bytes; SHA-256
`89f0c98d84bbaa2ba2bc656e8fe2306fd950fee0fe2e74c39641d3911692f5ce`.
Local member checks and both public download channels were verified. Workers
recheck the archive, each extracted file and the pinned LibreLane executable;
input hashes, raw reports, execution logs and failure results are retained.
Unsafe paths, links, duplicate/unlisted members and changed bytes are rejected.

There is no native elapsed-time watchdog. GitHub-hosted jobs have a six-hour
platform limit; a truncated or missing result is incomplete evidence and requires
recovery, never acceptance. `fail-fast: false` lets independent groups finish even
when another group fails. The local timing ECO keeps running. Once the cloud run
starts, only the idle local DRC controller may be paused after checking its PID,
birth identity and lack of a running native child, avoiding duplicate work.

The already measured 207 density violations remain open and are not rerun by this
workflow. A passing antenna/main shard would not close density, full-chip LVS,
qualified SRAM/RC timing, PCIe or manufacturing approval. These jobs measure the
current geometry; any subsequent fill or repair requires fresh checks.


[GitHub run 36376213858](https://github.com/Melihakbulut221/nssoc/actions/runs/36376213858)
started all seven worker jobs at source commit
`849a5998d2822e3272af104dd071e1b86674b34f`.
The [start receipt](evidence/chip-native-parallel-start-20260928.json) records
running jobs, not physical verdicts. The idle local DRC controller is intentionally
paused after verifying its identity and absence of native children; the local
timing repair remains active. Local real-bundle preparation, 112 targeted tests,
REUSE and strict documentation checks passed before dispatch.


The first [two completed cloud measurements](evidence/chip-native-first-two-results-20260928.json)
have been downloaded and independently verified against all 106 input hashes,
including the exact chip GDS, rule files, executable and method. Grid checks
passed 161 categories with zero markers; pin/forbidden checks passed 20 categories
with zero markers. Raw report/log hashes, process exit codes and exact category
names/descriptions were checked. The other five groups were still running at
this snapshot; the running antenna log endpoint returned HTTP 404, so no live-log
progress claim is inferred from that unavailable response.

The [raw evidence archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/chip-native-first-two-results-20260928.tar.xz) contains 21 members,
51,732 bytes, SHA-256 `9665e4991f10f6d969b65add80a5123a7fdf5d6fdee38f2daef5cacce0fa5447`;
all members and both public downloads were byte-verified.
[Asset inventory](evidence/chip-native-first-two-assets-20260928.json).
These partial passes do not remove the 207 density violations or close whole-chip
DRC, LVS, final timing or manufacturing acceptance.


## Completed cloud attempt and BEOL dependency repair

The [complete first attempt](evidence/chip-native-complete-attempt-20260928.json)
ended with four passing groups: FEOL devices 52, grid 161, pin/forbidden 20 and
angle 210 categories, all with zero markers (443 total). Antenna completed with
four markers: two each under `Ant.e_TopMetal1` and `Ant.e_TopMetal2`.
The supplemental wide-metal check completed with 296 `TM2.bR.transparent` markers.
These are real reported failures, retained without waiver. The six completed
measurements were independently checked against the exact 106 input hashes per
job and their complete category names/descriptions, reports and exit codes.

BEOL failed before rule execution because its adapted deck could not find its
TECH JSON at the original relative path. The portable bundle also lacked that
deck's default parameter JSON. Both files existed in the local method and match
unchanged checksum-locked upstream data. The new bundle adds those two copies;
all 100 existing non-packaging members, including the GDS and native rules, are
byte-identical. A new preflight rejects the old bundle and validates 84 native
include/parameter dependencies in the repaired bundle before extraction. Local
real-bundle preparation passes. Push-triggered recovery now runs only BEOL;
manual dispatch can explicitly select one group or all groups.

Raw antenna markers identify two gate polygons near (2152.22, 2790) micrometres,
with cumulative metal/gate ratio about 24,287.7 against the native diode-protected
20,000 limit. The supplemental markers include four-micrometre TM2 gaps along
the lower I/O region. These locations guide the next geometry/connectivity
investigation; they are not yet repaired. The 207 density violations also remain.

[Both immutable assets](evidence/chip-native-complete-attempt-assets-20260928.json)
preserve the original seven raw results (including BEOL failure), marker locations,
verification and recovery methods, and the corrected input bundle. Every archive
member and both public download channels were checked. Neither this dependency
repair nor the partial passing catalogs establish full-chip physical acceptance.

## Recovering the post-route proof waiter

The original equation-check helper reached its 46,800-second waiting limit while
the physical timing repair was still progressing. It recorded an error before
running any proof; the physical producer continued. The
[recovery record](evidence/pipeline-proof-wait-recovery-20260928.json) preserves
that error, the original method hash and the replacement's initial input hashes.

`scripts/verify_completed_pipeline.py` replaces the elapsed waiting cutoff with
checks of the producer PID and Linux process start identity. It rejects an exited
or reused process, failed/unknown producer status, changed input inventory or
bytes, and an incomplete final netlist/library/macro configuration. A successful
producer exit during the final-result read is handled explicitly. Its output is
written to a fresh `postroute-proof-v2` directory; the original failure remains.
Neither waiting nor equation execution has an elapsed timeout. The proof process
retains its 4 GiB address-space limit. Eighteen focused tests exercise these gates,
including waiting beyond the old 13-hour limit. The live replacement has verified
53 pinned inputs and is waiting for the same physical producer to finish.

At this recovery, the local timing repair reached iteration 650 with estimated
WNS -5.676 ns and TNS -5161.5 ns, compared with iteration 590 at -6.029 ns and
-5479.3 ns. These are intermediate global-route estimates, not final STA.
GitHub BEOL run 36381684222 remains in its native execution step; its live log is
not yet available through the job log API, so within-step progress is unknown.

Read-only marker localization also identifies the antenna gate shapes inside
`sg13g2_buf_1$1` at placement (2151.680, 2788.810) micrometres. A sampled TM2
violation lies between top-cell strips ending at y=183.84 and starting at
y=187.84 micrometres. This four-micrometre gap is consistent with the configured
PDN ring spacing of four micrometres. Net connectivity and the complete marker
population still need correlation before a physical repair. The source GDS is
unchanged. No antenna, spacing, density, timing or manufacturing gate is closed
by the waiter recovery or this localization.

## PDN spacing candidate with preserved I/O placement

The sampled TM2 gap is now traced to the VDD and VSS core-ring segments in the
original routed DEF. Both rings are eight micrometres wide; their lower centres
are at y=191.84 and y=179.84 micrometres, leaving a four-micrometre gap. The native
TM2 wide-line rule requires five micrometres for these long parallel segments.

An [isolated candidate](evidence/chip-pdn-spacing-candidate-20260928.json) changes
only `PDN_CORE_RING_HSPACING` from 4 to 5 in the original assembly configuration.
It regenerates floorplanning and PDN from the same source netlist. Independent
DEF inspection measures five-micrometre gaps at both the top and bottom rings
and confirms the same masters, coordinates and orientations for all 314 native
I/O instances and the core instance. OpenROAD reports all shapes connected on
VDD, VSS, IOVDD and IOVSS. This is a power-connectivity and PDN-geometry result.

Two setup failures are retained: a missing required output directory and an old
pre-PDN database removed during earlier cache compaction. Regenerating from the
source netlist avoids relying on the absent intermediate. Raw warnings remain,
including unavailable core Liberty, macro antenna metadata and omitted via
locations. They are not waived by the four connected power-rail results.

The [immutable candidate asset](evidence/chip-pdn-spacing-candidate-assets-20260928.json)
contains 155 members: methods, both failed attempts, the successful PDN run,
original/candidate DEF evidence and the verification record. All archive members
and authenticated/anonymous release downloads were byte-checked. The original
GDS and running timing repair are unchanged. The candidate still needs placement,
routing, native DRC/antenna/density and extracted connectivity checks; the original
296 supplemental markers, four antenna markers and 207 density markers remain
open until a complete repaired layout passes those measurements.

## Completed BEOL recovery and full main-category coverage

[BEOL recovery run 36381684222](https://github.com/Melihakbulut221/nssoc/actions/runs/36381684222)
completed successfully after 14,087 seconds of native execution. Its raw report
contains all 117 expected BEOL categories and zero markers. Independent local
verification checked the 108 input hashes, GDS identity, report and log hashes,
process exit and complete category names/descriptions. The six earlier groups
were also reverified against their original 106-input inventories, using the
archived original runner for that runner's changed source hash.

The [combined record](evidence/chip-main-drc-completed-20260928.json) establishes
all **560 main categories with zero markers** on GDS `f9dc37b7...`. The combined
catalog hash matches the locked complete-main reference. This excludes the
separate failing antenna (4), supplemental wide-metal (296) and density (207)
results, all retained. Full-chip DRC, LVS, final timing and manufacturing approval
therefore remain unaccepted.

The [published raw evidence](evidence/chip-main-drc-completed-assets-20260928.json)
includes the BEOL artifact and completed job log, local verification method and
result, and the separate repaired-ring routing queue setup. All 22 archive
members and both public download channels were checked. Earlier raw results
remain in their existing immutable assets.

The 5-micrometre ring candidate is queued to continue after PDN generation into
placement, routing and streamout in a fresh directory. Admission requires 6 GiB
available memory and 1.5 GiB free disk; execution has a 4 GiB address-space cap
and no elapsed timeout. At dispatch it is waiting for memory, not running native
routing. A first idle queue was replaced before any native child started because
preflight found that the final state uses `klayout_gds`; its original method and
disposition are retained. The corrected queue leaves the active core timing ECO
and completed cloud inputs untouched. Its eventual GDS still requires full
physical audits, including whole-chip boundary verification.

## General CI dependency and hierarchy-inventory repair

Hourly inspection found seven failures in both general checks jobs for source
`6218d09`: six mailbox behavior tests could not find Icarus, and the lexical RTL
inventory omitted the generated `nssoc_chip` wrapper and falsely classified
`soc_status_serial` as an orphan. The
[diagnosis](evidence/chip-ci-recovery-20260928.json) retains the original totals:
1,826 passed, seven failed and 168 skipped in that job. Other job successes do
not erase these failures or turn the skips into passes.

The checks job now installs Icarus. Inventory reachability includes the actual
generated chip wrapper as a root; the mailbox was not added to an exception list.
A negative control removes its generated instance and verifies that it becomes
unreachable. Forty focused mailbox, inventory and interface-profile tests pass
locally, together with the relevant lint, configuration and YAML checks. Hosted
re-execution is still pending.

The workflow also disables cancellation of in-progress runs on subsequent
pushes. Earlier hourly runs repeatedly show cancelled conclusions; the previous
workflow explicitly enabled this cancellation. Current long formal proofs can
now finish while newer checks wait. The
[immutable evidence asset](evidence/chip-ci-recovery-assets-20260928.json)
preserves both failed job logs, run snapshots and repair sources; all nine
archive members and authenticated/anonymous download bytes were verified.
This CI repair does not change physical inputs or close manufacturing gates.

## Independent worker for repaired-ring routing

The local routing queue remains below its 6 GiB memory admission threshold while
the core timing repair continues. The
[portable routing preparation](evidence/chip-ring-cloud-preparation-20260928.json)
moves that separate ring candidate to a dedicated GitHub worker. Before dispatch,
the idle local queue was identity-checked and paused with no native child running.
It must not resume while the cloud attempt is active.

The [immutable input bundle](evidence/chip-ring-routing-input-assets-20260928.json)
contains 768 members, including the unchanged PDN state and physical inputs,
required local PDK views and flow method. Every member and both public download
channels were checked. The runner permits only JSON path relocation; scalar
changes, changed source-file selection, missing files and path escapes are
rejected. Local preparation and real LibreLane configuration/state loading pass.
The dedicated workflow resumes after PDN generation, retains outputs on failure,
and does not cancel healthy work on new pushes. It has the hosted six-hour limit
and a 4 GiB process address-space cap, with no additional elapsed watchdog.

This is a routing dispatch mechanism. It does not waive the remaining antenna,
wide-metal, density, LVS or timing failures; its new GDS requires independent
boundary, assembly and complete native physical checks before acceptance.

[Run 36422747834](https://github.com/Melihakbulut221/nssoc/actions/runs/36422747834)
has entered its routing step on source `ea16be5`; the
[dispatch receipt](evidence/chip-ring-cloud-start-20260928.json) records its
identity and local handoff. A second same-source push run was still pending with
no jobs and was cancelled as a duplicate. The active worker was retained. After
successful local preflight, the disposable extracted bundle cache was removed
to reclaim disk; the verified release archive and original inputs remain.

## Completed repaired-ring routing and fresh native checks

[Run 36422747834](https://github.com/Melihakbulut221/nssoc/actions/runs/36422747834)
completed routing in 1,101 seconds. The
[completed routing audit](evidence/chip-ring-routing-completed-20260928.json)
checks its eight method pins, 767 bundle inputs and exact relocated configuration
and state. The embedded core and native I/O geometry remain unchanged; all 315
fixed placements and both 5 micrometre horizontal power-ring gaps are verified
in the final outputs. The whole-chip density annotation now covers the actual
4,000 by 3,200 micrometre die; every other shape, text and hierarchy record is
preserved across that transformation.

The new normalized GDS is
`52d0b63d8db96ac69d582e493d138d4c3291a3a33dd5c7fe7c666c5687798432`.
Router DRC and antenna counts are zero, but native physical acceptance remains
open. The previous layout's 560-category pass and its antenna, wide-metal and
density failures do not certify this new geometry. Density on this GDS is
unmeasured. Core parameters remain request/writeback 0/0; the active local 1/1
core timing ECO is separate.

The [raw completed routing asset](evidence/chip-ring-routing-completed-assets-20260928.json)
preserves the run, audit records, original producer methods and normalized GDS.
The [fresh native input asset](evidence/chip-ring-native-input-assets-20260928.json)
uses this new GDS and retains all 100 rule/license members byte-for-byte from the
previous native bundle. Local preparation checks 84 dependencies and 108 input
pins. A separate `chip-ring-native` workflow runs antenna and supplemental wide
metal checks on independent workers. Old chip checks remain manually available;
source pushes no longer repeat completed old-GDS BEOL work. Full native main
DRC, density/fill, LVS and final timing are still required.

## Formal stage timeout recovery

The [retained diagnosis](evidence/chip-formal-stage-recovery-20260928.json)
shows that the old PR sweep stopped its SoC stage at the runner's 9,000-second
limit while QSPI cover reachability was advancing. Its inventory contains 125
PASS and 45 missing tasks, with unchanged sources; this is an incomplete proof,
not a passing result or a demonstrated design counterexample. New checks split
pilot and SoC into separate workers and disable that internal elapsed watchdog.
Each worker still requires every declared nonexcluded task in its scope, fresh
source checks and zero stage exit status. Partial-stage reports explicitly deny
complete-sweep scope; both workers must pass for the workflow to pass. The hosted
six-hour job limit remains. Existing healthy workers are not cancelled.

The earlier general checks repair has now passed in both push and PR checks
jobs; their formal sweeps are still running. The publication job's PyPI timeout
was recovered by rerunning only that failed job; its second attempt passed.

## Wide-metal repair verified; IRQ antenna ECO candidate

The [fresh native results](evidence/chip-ring-native-results-20260928.json)
independently verify all 108 input hashes per worker, process exit codes, raw
reports and exact category names/descriptions. All eleven supplemental wide-metal
categories now have zero markers on the routed five-micrometre ring layout.
This closes the previously observed 296 wide-metal markers for this candidate.
The [immutable raw results](evidence/chip-ring-native-results-assets-20260928.json)
retain both completed measurements, including the failed antenna report.

Antenna still reports four markers in its 31-category inventory. They identify
the same two receiver gate polygons on `u_core/input31`, connected to
`irq_external_i`; the cumulative ratio remains 24,287.697565 against 20,000 with
an existing diode. The spacing repair did not resolve this independent failure.

The [IRQ buffer candidate](evidence/chip-irq-buffer-candidate-20260928.json)
inserts one native `sg13g2_buf_16` between the IRQ input pad and the existing core
terminal. The embedded core and all other chip connections are unchanged; only
that core input connection, one new wire and the buffer instance change. Its
proposed location, (2148, 2853.9) micrometres, is an existing north-oriented
standard-cell row outside the core and its halo, near the north IRQ pin. The
resizer protection pattern includes the new buffer and its two nets.

The native standard-cell Verilog model passes a 0/1/X/Z receiver-chain check;
a deliberately inverted buffer fails. These are functional checks without
propagation-delay or analog qualification. Icarus timing-check warnings from
unrelated cells in the complete library are retained. Fifty-six focused
source-transformation, relocation, archive and delivery tests pass locally.

The [portable ECO inputs](evidence/chip-irq-buffer-input-assets-20260928.json)
retain 762 previous bundle members unchanged and preserve all new candidate
sources and simulation records. A dedicated `chip-irq-route` workflow starts
from the new mapped netlist and regenerates floorplan, PDN, placement and routing;
it cannot reuse a stale routed database. Local preparation verifies 781 inputs
and real LibreLane configuration/netlist-state loading passes. Physical placement, buffer retention,
connectivity, native antenna/DRC, density and timing still require verification.
This candidate is not an antenna closure claim. The completed unbuffered routing
workflow is now manual-only, avoiding redundant routing when shared code changes.

## IRQ buffer routed; independent physical checks pending

[Run 36445480475](https://github.com/Melihakbulut221/nssoc/actions/runs/36445480475)
completed the buffer candidate's full floorplan-to-GDS flow. The
[completed routing audit](evidence/chip-irq-routing-completed-20260928.json)
verifies the source commit, eight method pins, all 781 bundled inputs and exact
configuration/state relocation. The final DEF retains the buffer at (2148,
2853.9) micrometres, the original 315 core/I/O placements and both 5 micrometre
horizontal ring gaps. Its buffer output net connects only to the original core
IRQ terminal; the long input net connects the pad, buffer input and two native
antenna cells. The final netlist preserves that same buffer path.

GDS comparison verifies the unchanged embedded core and native I/O hierarchy
and all 217 selected cell geometries. The added buffer also matches the native
standard-cell GDS exactly. Mirrored antenna cells abutting the buffer share its
GDS transform anchor; the audit identifies the buffer by native geometry and
transform, rather than treating every cell at that anchor as the buffer.
OpenROAD checks on the final routed ODB pass for VDD, VSS, IOVDD and IOVSS.
These connectivity checks do not establish transistor LVS or IR/EM acceptance.

Whole-chip boundary normalization changes only annotation layer 189/0 and
preserves every other shape, text and hierarchy record. The
[immutable completed-routing archive](evidence/chip-irq-routing-completed-assets-20260928.json)
retains the raw run, audits, final GDS and original producer sources. The
[new native input bundle](evidence/chip-irq-native-input-assets-20260928.json)
uses that normalized GDS with unchanged native rules. The separate
`chip-irq-native` workflow runs antenna and wide-metal checks on it.

Router DRC and antenna counts are zero. Native antenna closure is still pending;
the prior four-marker failure remains evidence on the preceding unbuffered GDS.
The earlier wide-metal pass also does not transfer automatically to this newly
routed geometry. Full native main DRC, density/fill, extracted LVS, final timing,
SRAM characterization, PCIe PHY, DFT and manufacturing approval remain open.

## IRQ buffer native antenna closure and full-chip checks

[Run 36452984245](https://github.com/Melihakbulut221/nssoc/actions/runs/36452984245)
completed both independent checks on normalized IRQ-buffered GDS
`dbaf641d4839e977855e3a6bd4df646ff4a7da9a31a45ec2d67df71e45661ac6`.
The [verified results](evidence/chip-irq-native-results-20260928.json) show
**31 antenna categories with zero markers** and **11 supplemental wide-metal
categories with zero markers**. Verification covers all 108 input/method hashes
per worker, source commit, native category names/descriptions, successful exit,
raw report/log hashes and parsed marker counts. The previous four antenna
markers belong to the preceding unbuffered layout and remain preserved as failed
evidence. Their closure is established by a fresh native measurement on the
buffered geometry, without changing rule thresholds or receiver gate metadata.

The [immutable result archive](evidence/chip-irq-native-results-assets-20260928.json)
contains both raw reports, logs, provenance, verifier and original producer
sources. These two passing groups do not establish full-chip DRC, LVS or timing.

The [full native input bundle](evidence/chip-irq-full-native-input-assets-20260928.json)
keeps the same GDS and 101 members byte-for-byte unchanged, including all native
rule/dependency files. Only the packaging method and configuration change to add
the complete native density command. The `chip-irq-full-native` workflow runs
five main DRC partitions and density on independent workers. Main partitions
must match the complete 560-category catalog. Density requires all 37 ordered
rule-execution records, successful completion and valid boundary normalization;
its report has seven mandatory slit categories and additional categories only
when violations occur. A fixed report-category count cannot prove density
coverage. Deep mode, recommended checks and density sanity checks remain enabled.
No native process elapsed-time watchdog is added; hosted platform limits still
apply, and an interrupted measurement cannot pass.

Local preparation verifies the complete immutable bundle, native dependencies,
GDS and pinned executable before dispatch. Forty-six focused bundle/coverage
tests pass, including missing-rule and disabled-check rejection. Main DRC and
density results on this GDS are pending; the previous layout's 560-category pass
and 207 density markers are historical and cannot be transferred. Any subsequent
fill changes require fresh geometry-specific verification. Full-chip transistor
LVS, final setup/hold/slew/capacitance timing, SRAM characterization, PCIe PHY,
DFT and actual manufacturer acceptance remain open.

## Density measurement and chip fill candidate

The [fresh partial native results](evidence/chip-irq-full-native-partial-20260928.json)
show **443 FEOL/geometry categories with zero markers** and a **207-marker density failure** on the
IRQ-buffered GDS. The 117-category BEOL partition is still running. All 37 density rules executed in order and the process exited
successfully; the density failure is a real geometric finding. The
[immutable raw reports](evidence/chip-irq-full-native-partial-assets-20260928.json)
retain each marker, native description, execution log and exact input hashes.

The deficits comprise four local active-area windows, six global metal-density
checks (Metal2–5 and TopMetal1–2), and 197 local Metal2–5 windows. All are minimum
coverage failures. Although the total equals the preceding layout's 207 markers,
this result is independently measured on the current GDS, not inherited.

The [fill method controls](evidence/chip-irq-fill-method-20260928.json) exercise
two real generator windows, resume after the first window and final geometry
preservation. Three deliberate mutations—removing original geometry, adding a
non-fill shape and removing an original instance—are all rejected. The
[method evidence archive](evidence/chip-irq-fill-method-assets-20260928.json)
contains exact tested sources, inputs, outputs, logs, compressed checkpoints and
full-chip preparation provenance. These small controls establish the method's
behavior; they do not qualify the full-chip candidate.

The [portable fill inputs](evidence/chip-irq-fill-input-assets-20260928.json)
include the unchanged chip GDS, pinned prebuilt generator, complete corresponding
source and target configuration. The generator's existing local patch changes
only its fill/density boundary mapping from layer 39 to 189; no rule thresholds
change. Generation proceeds sequentially through 56 windows of at most 500 by
500 micrometres, with a 30 micrometre geometry halo. Each window sees the current
layout, including previously inserted neighboring fill. The merge retains the
original chip and adds only audited differences on designated fill layers.
Original geometry and hierarchy are independently compared again after the
last window. Per-window inputs, outputs and checkpoints are retained.

The separate `chip-irq-fill` worker runs the real corruption controls before full
chip generation. Neither generation nor geometry preservation has a native
elapsed-time watchdog; the hosted platform limit remains. Partial or interrupted
work is not accepted. The completed candidate must undergo fresh native density,
main DRC, antenna, wide-metal, extracted connectivity and RC/timing verification.
The running unfilled-layout checks remain useful independent evidence and are
not cancelled. Full-chip acceptance and manufacturing approval remain open.
