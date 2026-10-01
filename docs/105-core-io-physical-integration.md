# Core, I/O and MBIST status physical integration

The 27 September integration candidate combines the selected physical core,
native IHP I/O ring and the synthesized 192-bit read-only MBIST status mailbox.
It is an engineering candidate, **not production acceptance**. The independent
I/O-cell LVS campaign fails all seven selected signal/supply masters. Full-chip
LVS, finishing, full timing and manufacturer acceptance therefore remain open.

**29 September audit correction:** the inset and offset contact audits treated
quarter-turn placement codes as degrees. Their historical all-314-port
no-opposite-contact claims are withdrawn. A corrected replay on the current
filled GDS now verifies all 314 placements and 10,526 windows with zero direct
opposite-supply contacts; the final section below contains its evidence. This
does not invalidate native DRC, which uses actual GDS geometry. The complete
314-I/O physical connectivity audit subsequently passed on 30 September; see
the completed tiled result below.

**30 September completed connectivity audit:** all 10,526 declared supply
windows on 314 I/O instances now pass the complete tiled metal-connectivity
check, with independently verified geometry and checkpoint chains. Each of
VDD, VSS, IOVDD and IOVSS is one distinct physical component. This closes the
declared-window continuity check for the pinned filled GDS; transistor LVS,
RC, electrical qualification and final timing remain separate.

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

## Complete fill candidate; fresh native measurements required

[Fill run 36474119630](https://github.com/Melihakbulut221/nssoc/actions/runs/36474119630)
completed all 56 windows. The [independent verification receipt](evidence/chip-filled-candidate-20260928.json)
binds the source commit, all 77 input/method hashes, the executed corruption
controls, exact window bounds and every completed checkpoint. It verifies the
1,505,717,713-byte tile ZIP against its GitHub artifact digest and streams every
compressed and decompressed tile input, output and checkpoint through checksum
validation. Each of the 56 per-window geometry reports agrees with its recorded
input/output hashes and reports no preservation errors. This streaming check
avoids storing another 1.5 GB on the local disk.

The final geometry audit retains all 264 original cells and adds 56 fill cells
containing 1,171,794 polygons on designated filler layers. The candidate GDS
SHA-256 is `6198700f94cfcbd57cfd86bace7b3de848249695351b4366237cf44eac7d14a3`.
The [verification archive](evidence/chip-filled-candidate-assets-20260928.json)
contains the raw audits, producer sources, verification methods and both the
failed initial archive-reader attempt and successful direct streaming check.
The final GDS is retained in the [immutable native input bundle](evidence/chip-filled-native-input-assets-20260928.json).
A separate archival worker copies both original GitHub ZIP artifacts unchanged
into the existing release and verifies their authenticated and public bytes;
archival completion requires its successful receipt.

The `chip-filled-native` workflow runs all eight native groups on this new GDS:
five main DRC partitions, antenna, supplemental wide metal and density. The 100
rule/license members remain byte-identical to the preceding bundle. Local
preparation verifies the new GDS, all method pins and native dependencies before
dispatch. Neither the previous 443-category pass nor the previous 207 density
markers are results for this filled geometry. The earlier BEOL measurement
continues independently on its original input. Generation and preserved source
geometry do not establish density closure, native DRC, extracted LVS, RC/timing,
PCIe PHY completion, DFT or manufacturing approval.

## Filled-layout density closure and remaining BEOL measurement

The [verified filled-layout measurements](evidence/chip-filled-native-partial-20260929.json)
from [run 36481064898](https://github.com/Melihakbulut221/nssoc/actions/runs/36481064898)
are bound to GDS `6198700f94cfcbd57cfd86bace7b3de848249695351b4366237cf44eac7d14a3`.
All **37 density rules execute with zero markers**. Antenna has 31 categories
with zero markers, supplemental wide metal has 11 with zero markers, and the
four completed main partitions cover 443 FEOL/geometry categories with zero
markers. The filled-layout BEOL partition remains pending; these results do
not establish a complete 560-category main DRC pass. Native rules and thresholds
are unchanged. Each completed worker's source, input hashes, native category
inventory, report/log digests and exit status were checked independently.

The [native evidence archive](evidence/chip-filled-native-partial-assets-20260929.json)
preserves the seven completed raw reports and verification method. The
[original fill ZIP archives](evidence/chip-filled-raw-artifacts-assets-20260929.json)
are now permanent release assets: 41,621,861 bytes for the candidate and
1,505,717,713 bytes for all raw tile records. Their exact original bytes were
verified against artifact digests and authenticated/public release downloads;
the large tile archive was independently streamed and checked locally.

Separately, the unfilled GDS's BEOL measurement completed successfully. Its
[completed receipt](evidence/chip-irq-full-native-completed-20260929.json) and
[raw archive](evidence/chip-irq-full-native-completed-assets-20260929.json)
record all 560 main DRC categories with zero markers, alongside the original
207 density violations. This is historical evidence for GDS `dbaf641d...`,
not BEOL acceptance of the filled candidate. No physical result is transferred
between the two geometries.

## I/O tap parameter and ground-port diagnosis

The [read-only diagnosis](evidence/io-tap-and-supply-contract-20260929.json)
compares the pinned original vendor GDS, CDL, electrical model, native extractor
and existing failed LVS database. All 64 CDL taps use square width/length and
perimeter `2*(w+l)`. For the DCN and DCP diode taps, those square dimensions
match the physical area's square root rounded to the 5 nm grid. Native
extraction instead measures the actual perforated tap region:

| Tap | Physical area (µm²) | Physical perimeter (µm) | CDL area (µm²) | CDL perimeter (µm) |
|---|---:|---:|---:|---:|
| DCN | 141.2964 | 221.76 | 141.253 | 47.54 |
| DCP | 33.5104 | 197.12 | 33.524 | 23.16 |

Direct geometry calculations exactly reproduce the native extracted area and
perimeter. The pinned `ptap1` electrical subcircuit uses its supplied resistance;
its width/length parameters are declared but unused. This explains the view
contract discrepancy, but does not justify substituting measured values into
the reference or disabling parameter comparison. The tap reference/extractor
contract still needs an independently justified resolution.

The diode child ports split by extraction are physically joined to the same
`pad` net at their parent. Separately, the input pad has **two distinct `iovss`
clusters**. Both are exposed by the original LEF: their TopMetal2 rectangles
span y=8.5–31 and 36–58.5 µm for one cluster, and y=127.5–132.5 µm for the other,
all across x=0–80 µm. The native per-net TopMetal2 regions exactly match those
LEF rectangles and are subsets of the original GDS drawing. Consequently,
parent routing must connect both clusters; their shared name alone cannot
establish continuity. This diagnostic does not prove that the current routed
chip joins them. The existing abstract OpenROAD power-grid check remains
separate from transistor-level connectivity.

The [diagnostic archive](evidence/io-tap-and-supply-contract-assets-20260929.json)
retains the methods, original small reference inputs, native LVS database,
logs and intermediate attempts. No mask, reference value, extraction rule or
connectivity requirement was changed. All seven I/O master LVS failures and
full-chip LVS remain open, along with final RC/timing, complete SRAM
characterization, PCIe Gen3 x4 PHY/controller, DFT and manufacturer acceptance.

## Confirmed supply contacts and a new ring-clearance candidate

The [physical contact diagnosis](evidence/chip-supply-short-diagnosis-20260929.json)
finds **seven VDD routing contacts to native input-pad VSS metal** in the
IRQ-buffered chip. The same preliminary connectivity finding occurs before
and after fill. A follow-up geometric check uses the pinned native TopMetal1
conductor definition: drawing plus filler, minus slit, resistor and inductor
recognition regions. All seven contacts retain nonzero conductive overlap.

Four contacts are on the north edge, each with 2.288 µm² overlap, and three
are on the south edge, each with 6.952 µm² overlap. For example, a VDD stripe
at x=2783.06–2785.26 µm reaches y=3023.04 µm and intersects the preserved
native VSS port beginning at y=3022 µm. The routed database assigns that
stripe to VDD. Native pad geometry and the independently extracted contact
region establish the wrong-rail connection. The earlier OpenROAD power-grid
check did not detect this physical interface defect. Existing DRC passes
therefore do not establish correct power connectivity.

The initial drawing-only TopMetal1/TopVia2/TopMetal2 graph also reports separate
IOVSS components. Those preliminary reports omit lower-layer connections and
are not a full-chip open-circuit verdict. Their sources, positive/missing-via
controls, initial API/parser failures and subsequent contact verification are
retained in the [diagnostic archive](evidence/chip-supply-diagnosis-and-recovery-assets-20260929.json).
The authoritative finding here is the seven direct opposite-supply contacts;
complete power connectivity and transistor LVS remain open.

The [new candidate](evidence/chip-supply-inset-candidate-20260929.json) changes
`CORE_AREA` from `[200, 200, 3800, 3000]` to `[230, 230, 3770, 2970]` µm.
This moves the generated ring and stripe endpoints inward by 30 µm, away
from the native pad supply bands. The mapped netlist, fixed native I/O and
core placements, IRQ buffer placement, clocks, PDK, ring widths and spacings
are unchanged. The [portable inputs](evidence/chip-supply-inset-input-assets-20260929.json)
verify 777 unchanged prior bundle members; three copies/templates of the
configuration and the candidate metadata change, with two preparation records
added. Local preparation verifies all 783 bundle inputs and eight method/input
hashes, then loads the actual LibreLane configuration and netlist state.

The `chip-supply-inset-route` workflow regenerates floorplan, PDN and routing
from the mapped netlist. This is a proposed geometric repair. Its output must
be checked for opposite-supply contacts, continuity of all required pad
components, native DRC/antenna/density, full transistor LVS and timing. Previous
physical results cannot certify the new geometry. This chip candidate still
uses the previously bundled core; the separate pipeline timing candidate has
not yet been integrated into it.

## Timing allocation failure and checkpointed recovery

The long local setup repair stopped with **`std::bad_alloc` and signal 6** after
29 hours 20 minutes of OpenROAD runtime. It ran under an 8 GiB address-space
limit; its last reported iteration was 1290, with estimated WNS −3.935 ns and
TNS −3264.3 ns. No completed repair checkpoint was emitted. The producer and
its postroute verifier correctly record failure. These intermediate numbers
are not final timing results.

The [recovery record](evidence/timing-checkpointed-recovery-20260929.json)
starts from the unchanged pre-repair state. A fresh OpenROAD process performs
at most 100 setup or hold iterations per batch, then must emit a complete
state, preserve all 32 SRAM masters/locations/orientations and satisfy input
hash and explicit-completion checks before that checkpoint is promoted.
The next process uses the completed state. A failed batch leaves the last
completed checkpoint intact. Older completed batches are compressed and
verified before cleanup, and are retained uncompressed if the current state
still references them. No elapsed-time watchdog is added. Routing, extracted
RC, final setup/hold/slew/capacitance checks and logic equivalence remain
mandatory after estimated repair converges.

The first recovery launch failed command-line validation because its output
directory had not been created; no native stage ran. The separate corrected
attempt is now performing setup repair. Its methods and running snapshot,
the original allocation failure and resource-cleanup receipts are preserved
in the diagnostic archive. Disk cleanup removed only verified duplicate test
fixtures/Git objects and release-backed untracked download copies; originals
or checksum-bound release assets remain available. Two unsuccessful attempts
to archive redundant fixture copies exhausted the available space; their
incomplete output archives were removed, and the source fixtures were not
removed by those failed attempts. No timing or manufacturing approval is
claimed.

### 29 September: supply-contact repair verified and checkpoint parser recovered

The [new route](https://github.com/Melihakbulut221/nssoc/actions/runs/36501093402)
completed from commit `5eb9ad79fb8508601f1b593f3add5328fffc6a5a`.
The [original 515-member artifact ZIP](evidence/chip-supply-inset-route-raw-assets-20260929.json)
is permanently published and verified against authenticated and anonymous
downloads. Input provenance covers 783 bundle members and eight method pins.
All 315 original core/I/O placements and the native IRQ buffer are retained;
recursive native core/I/O/buffer geometry matches the original libraries.
The router inserted three actual `sg13g2_antennanp/A` diodes, consistent with
the resolved PDK configuration. An initial verifier that expected a different
diode master rejected the result; that failed log is preserved. The corrected
verifier checks the actual configured master and IRQ net connections.

The historical [supply-contact audit](evidence/chip-supply-inset-contact-verification-20260929.json)
attempted 10,526 named supply-port rectangles on 314 native I/O instances.
Its all-port result is withdrawn: the method interpreted placement quarter-turn
codes 0–3 as degrees in `ICplxTrans`. Consequently its transformed port locations
on the rotated sides were wrong. The original result remains preserved as a
failed verification method, not evidence of complete contact closure. A correct
replay must use 0/90/180/270 degrees and check every transform against the GDS.

Raw GDS SHA-256 is
`3cf5276540e3fabe6c9eeea4a267635fa15b3ed0eb9e74b58a54578fb4ec5c58`.
Normalization changes only the inherited density boundary on layer 189/0 to
the actual 4000 × 3200 µm die, preserving every other shape, text and hierarchy
record through serialization. The resulting GDS SHA-256 is
`0c2ca467f735b72c06e2d62065cc9d27d3677508040ed9c7524ef652f5737027`.
The [fresh native-check inputs](evidence/chip-supply-inset-native-input-assets-20260929.json)
retain all 100 rule/license members unchanged. The `chip-supply-inset-native`
workflow runs all eight groups on that exact new GDS. Density is remeasured;
no old marker count or pass is inherited. New fill may still be necessary.

The [historical filled layout checks](evidence/chip-filled-native-completed-20260929.json)
also completed: 560 main DRC categories, 31 antenna categories, 11 supplemental
wide-metal categories and all 37 executed density rules have zero markers.
BEOL finished in 15,432 seconds. These measurements belong only to GDS
`6198700f94cfcbd57cfd86bace7b3de848249695351b4366237cf44eac7d14a3`,
which has the previously established supply short. DRC clearance does not
establish correct electrical connectivity, and these results do not qualify
the new geometry.

The first 100-iteration local timing batch exited successfully, preserved all
32 SRAM macro placements and wrote its ODB, DEF, netlist and SDC. The controller
then rejected the valid `worst slack max/min` report format. The
[parser recovery](evidence/timing-checkpoint-parser-recovery-20260929.json)
preserves that failure, verifies the complete checkpoint and original input
hashes, and accepts only one numeric value with the expected max/min mode
inside unique report delimiters. Wrong-mode, malformed and duplicate reports
are rejected. A separate controller continues from the saved checkpoint;
it does not repeat the completed initial electrical repair. The recovered
global-route estimates are setup −8.121617 ns and hold −1.844665 ns. Both fail.
Missing SRAM Liberty and final extracted RC remain independent timing gates;
these estimates are not full-chip signoff.

The [verification and checkpoint archive](evidence/chip-supply-inset-verification-assets-20260929.json)
contains raw audits, historical native reports, failure logs, recovery methods
and the completed timing ODB/DEF/netlist/SDC. Native checks, full power
continuity, I/O transistor LVS, SRAM characterization, final timing, complete
PCIe PHY/controller, DFT and actual manufacturer acceptance remain open.

### 29 September: fresh inset checks expose a north-ring spacing defect

[Seven completed groups](evidence/chip-supply-inset-native-partial-20260929.json)
on the normalized inset GDS `0c2ca467…` were independently checked against
the exact worker source, input hashes and complete category inventories.
Antenna passes all 31 categories with zero markers. FEOL and geometry pass
443 main categories with zero markers. BEOL is still running on this same
geometry; its eventual result must remain separate from later candidates.

The unchanged supplemental wide-metal rules find **72 `TM2.bR.transparent`
markers**, and all 37 density rules execute with **206 density markers**.
These failures are retained. The [spacing diagnosis](evidence/chip-ring-offset-candidate-20260929.json)
locates every wide-metal marker between the same two north TopMetal2 edges:
the horizontal VDD stripe ends at y=2966.88 µm, and the VDD ring begins at
y=2971.80 µm. Their gap is 4.92 µm, below the required 5 µm. Both shapes are
assigned to VDD in the routed database; being on the same net does not waive
the physical spacing rule. The previous ring-to-ring 5 µm check did not cover
this stripe-to-ring interface.

The [next routing input](evidence/chip-ring-offset-input-assets-20260929.json)
changes only `PDN_CORE_RING_HOFFSET` from 4.5 to 6.0 µm in the three matching
configuration copies/templates. The 30 µm core-area inset, fixed core/I/O/IRQ
placements, mapped netlist, clocks, PDK, ring widths and ring spacings remain
unchanged. This proposes a 1.5 µm outward displacement of the horizontal ring
sections. If the stripe phase remains unchanged, the measured north gap
would become 6.42 µm; that is a prediction requiring verification of the new
routed geometry. Original preparation records remain in the new bundle;
779 prior members are byte-identical, and two new preparation records are
added. Real LibreLane configuration and state loading verifies the intended
parameters before dispatch through `chip-ring-offset-route`.

The [raw measurement and preparation archive](evidence/chip-ring-offset-preparation-assets-20260929.json)
retains all seven native result groups, complete catalogs and logs, the exact
spacing diagnosis, candidate recipe, preflight and current timing snapshot.
The first cache-cleanup check stopped because the real Python import had
created one additional bytecode file; all inventoried source files matched.
The subsequent cleanup recorded that generated file and removed only the
reconstructible extraction cache. Active timing inputs were not changed.

Density fill is deferred until the spacing candidate has been routed and
checked, so fill is generated for the intended geometry. The healthy BEOL
measurement continues. Local checkpointed setup repair also continues;
intermediate optimization values do not establish final timing. No supply
continuity, full-chip LVS, density, timing or manufacturing gate is accepted
by this preparation.

### 29 September: routed offset geometry verified; fill gated by native checks

The [horizontal-offset routing run](https://github.com/Melihakbulut221/nssoc/actions/runs/36513698428)
completed from commit `daa1e7e48177737b9fc0e2c98ea2e9f0b4707fca`.
Its [original artifact ZIP](evidence/chip-ring-offset-route-raw-assets-20260929.json)
is permanently archived; all 532 members were streamed and checked, with
420 final-state/metadata/report files retained locally. Provenance checks
cover 785 bundled inputs and eight method pins. Exact recursive native core,
I/O and IRQ-buffer geometry and all fixed placements are preserved.

The [new audit](evidence/chip-ring-offset-route-verification-20260929.json)
measures the north VDD stripe-to-ring gap at **6.42 µm** in the final routed
database, exceeding the 5 µm requirement. The original stripe edge remains
at y=2966.88 µm, while the ring edge moves to y=2973.30 µm. The database hash
is matched to the original artifact inventory. This verifies the intended
geometric change; the complete unchanged native wide-metal rule set must
still run on the streamed GDS. The associated all-10,526-port no-opposite-contact
claim is withdrawn for the same quarter-turn/degrees bug described above.
Full rail continuity and transistor LVS remain separate requirements.

Raw GDS SHA-256 is
`8bb61b107bdb01b8ad5b9d02cd26e1de98b49320e52509ca8bd0e37d9d1eae6e`.
The boundary-only normalization preserves every other shape, text and
hierarchy record. Its output SHA-256 is
`8e26e98cbedfbf924e4a9655a1e2584ba4b52a77e4ae55320483d4a3363d66c5`.
Both the [native-rule input](evidence/chip-ring-offset-native-input-assets-20260929.json)
and [fill input](evidence/chip-ring-offset-fill-input-assets-20260929.json)
contain that exact GDS. Actual runner preflights verify 108 and 77 input/method
hashes respectively. All 100 native rule/license members remain unchanged;
the fill binary, corresponding source, existing boundary-layer patch and
configuration are also unchanged from the earlier fill campaign.

The `chip-ring-offset-fill` workflow first runs native antenna and supplemental
wide-metal checks on separate workers. The fill job depends on **both jobs
succeeding**, including complete category coverage and zero markers. If either
fails, generation does not start. If both pass, the existing audited 56-window
fill generator runs automatically, including corruption controls and source
geometry preservation. Generation success will still require new main DRC,
antenna, wide-metal and density measurements on the actual filled output;
no earlier-layout result is transferred.

The [verification archive](evidence/chip-ring-offset-route-verification-assets-20260929.json)
retains the new audits, preparation methods, preflight receipts and timing
snapshot. To preserve room for local checkpoint generation, only historical
route files and archive download copies with exact reconstruction/immutable
release proofs were removed. Current geometry and active timing inputs were
retained. The new workflow is a verification and candidate-generation chain,
not full-chip LVS, final timing or manufacturing acceptance.

### 29 September: native spacing and antenna gates pass; fill runs automatically

The [offset-layout native results](evidence/chip-ring-offset-native-gates-20260929.json)
pass all **31 antenna categories and 11 supplemental wide-metal categories
with zero markers** on GDS `8e26e98c…`. Both reports were independently parsed
and matched to the full category catalogs, logs, 108 input/method hashes and
worker commit `9a1dd0055eff603190881e98ad4d9b3ebed3ba70`. Thus the previous
72 north stripe/ring spacing markers are closed on this particular unfilled
candidate under the unchanged native check. This does not certify main DRC,
density, full power continuity, transistor LVS or any subsequent filled GDS.

Both required jobs succeeded and the same workflow automatically started
fill at 04:16:53 UTC. The producer subsequently completed successfully.
Its candidate and tile artifacts are being independently checked; no filled
GDS or density acceptance is claimed from the workflow conclusion alone.
The [exact producer archival plan](evidence/chip-ring-offset-fill-archive-plan-20260929.json)
binds the source run, full commit, branch, workflow, push event and two expected
artifact names. The separate `chip-ring-offset-fill-archive` worker waits for
that producer to finish successfully, resolves the final artifact IDs and
SHA-256 digests, and retains the exact original ZIPs as immutable release
assets. It checks downloaded bytes, existing-asset identity, authenticated
release downloads and anonymous downloads. Different existing bytes are never
overwritten. Failed or incomplete producers cannot authorize publication;
partial downloads and error receipts are retained. The worker has the hosted
platform limit and adds no internal elapsed-time cutoff.

The [next saved local timing checkpoint](evidence/timing-checkpoint002-20260929.json)
completed another 100-iteration setup batch, preserved the SRAM macro guard
and saved all required views. Independently rechecked output hashes bind setup
−6.640525 ns and hold −1.838572 ns, both still violating. The third batch is
running. The previous completed batch was compressed and every archived
member was checked before the controller reclaimed its expanded files;
the new state did not refer to those removed files. This is recoverable
optimization progress, not final timing closure. SRAM Liberty, qualified RC,
final routing/STA and equivalence remain required.

The [new raw archive](evidence/chip-offset-native-gates-and-timing-assets-20260929.json)
contains both native reports, the complete first-batch archive, the second
checkpoint ODB/DEF/netlist/SDC and reports, the current running snapshot and
archival preparation. Its timing archive was also checked member by member.
All existing failures and incomplete product gates remain recorded.

### 2026-09-29 — offset fill verified; full native campaign prepared

The offset fill producer completed all 56 windows. The
[fill verification](evidence/chip-offset-filled-verification-20260929.json)
binds input `8e26e98cbedfbf924e4a9655a1e2584ba4b52a77e4ae55320483d4a3363d66c5`
to filled GDS `a5c79c3920154af5a523e3a1224402d6e863b9f7dd91c367ac6256d9045ad8ff`.
All 77 input hashes and corruption controls were checked. A complete streamed
read of the 1,508,405,039-byte tile ZIP checked every compressed file and its
expanded GDS against the producer's per-window record. The independent local
geometry audit retained all original per-cell shapes and instances: 271
original cells, 56 new fill cells and 1,206,127 added fill shape definitions.
These checks establish preservation and provenance; density and electrical
acceptance are separate measurements.

The [raw candidate and tile ZIPs](evidence/chip-offset-filled-raw-assets-20260929.json)
are now permanent release assets. Archival worker
[36523414115](https://github.com/Melihakbulut221/nssoc/actions/runs/36523414115)
completed on `b4deabfca0b41d1849c57f9341bd298132ca5d55`; its plan, utility,
helper and producer identity were rechecked against that commit. Exact ZIP
sizes and digests match both the original artifact metadata and release API;
the worker verified authenticated and anonymous downloads. Local streaming
also independently verified the tile ZIP and all 392 member files.

The new `chip-offset-filled-native` workflow uses a
[hash-bound filled input bundle](evidence/chip-offset-filled-native-input-assets-20260929.json)
for all eight groups: antenna, supplemental wide, FEOL devices, pin/forbidden
geometry, grid, angle, BEOL and density. All 100 rule and licence members are
unchanged from the prior offset bundle. No old GDS result is transferred to
this filled geometry, and a queued or running job is not a passing result.

The [previous inset campaign](evidence/chip-supply-inset-native-completed-20260929.json)
also completed: BEOL has 117 categories and 72 `TM2.bR` markers, all at the
known north gap between y=2966.88 and y=2971.8 micrometres. The native and
transparent supplemental checks divide the edge pairs differently; exact
marker strings are not equal. The unchanged inset candidate still fails
wide spacing and density (206 markers). These historical failures remain
separate from the new offset filled candidate.

The [third saved timing checkpoint](evidence/timing-checkpoint003-20260929.json)
has setup −6.438917 ns and hold −1.990734 ns: setup improved from checkpoint2,
while hold worsened. Both remain failing global-route estimates. All output
hashes and the previous checkpoint archive were rechecked. The fourth batch
resumed after a resource wait: 282,397,867 bytes of old route extraction
copies were removed only after exact comparison with the retained original
ZIP, verified release identity and exclusion of active timing inputs. No
healthy job was stopped and no clock, SRAM macro or native rule was relaxed.

[Raw verification and checkpoint3 views](evidence/chip-offset-filled-verification-assets-20260929.json)
preserve the new proof records, previous inset failures and timing reports.
Full chip transistor LVS, SRAM Liberty/distributed RC, final routed timing,
complete PCIe Gen3 x4 PHY/controller, DFT and actual manufacturer approval
remain open.

### 2026-09-29 — filled density and seven native groups verified

The [partial native result](evidence/chip-offset-filled-native-partial-20260929.json)
for [36527710008](https://github.com/Melihakbulut221/nssoc/actions/runs/36527710008)
is independently tied to source `cb76088b65e58ae6b3d0d53e10c1083d94595fbc`
and filled GDS `a5c79c3920154af5a523e3a1224402d6e863b9f7dd91c367ac6256d9045ad8ff`.
Antenna has 31 categories/zero markers, supplemental wide has 11/zero,
and FEOL plus geometry has 443/zero. All 37 native density rules executed
with zero markers. Each report, log, category catalog and 108 input hashes
(109 for density) was checked. BEOL is still running; the seven completed
groups do not establish a complete native DRC pass.

A [supply connectivity investigation](evidence/chip-offset-filled-supply-investigation-20260929.json)
now probes the actual GDS without using labels or abstract net joins. The
upper-metal-only extraction sees separate VDD and VSS, but three IOVSS
clusters at the 27 input pads. This limited stack cannot decide whether lower
metals join those clusters, so it is not proof of a full-chip open circuit.
The attempted seven-metal flat extraction exceeded its 1.5 GiB address-space
cap while constructing Metal1; its failure and method are retained. A separate
hierarchical extraction preserves the same cap, uses all seven native metal
conductors and six via layers, and excludes MIM-covered TopVia1. Native
conductor derivations and connection rules were checked against the pinned
LVS sources. That extraction is still running and has no accepted result.

Small seven-metal controls exposed a query hazard: two disconnected instances
can return the same child-local circuit/cluster ID. Optional path probing in
this binding did not distinguish those instances. The acceptance guard now
requires all cross-instance supply probes to resolve to the top circuit;
child-local identities remain unresolved. The parent-bridge control passes
and the disconnected-instance control is rejected. The ongoing extraction's
raw result must pass this separate guard before any continuity claim. Even
then, its scope is the input-pad power probes; transistor/substrate extraction,
other pins, resistance, final timing and manufacturing acceptance remain open.

The [raw partial-native and supply-audit package](evidence/chip-offset-filled-native-supply-assets-20260929.json)
preserves seven native reports, the failed flat attempt, the running
hierarchical method/snapshot, all control versions and native reference files.
Local timing checkpoint4 continues independently with its pinned inputs.

### 2026-09-29 — fourth recoverable timing checkpoint

The [fourth checkpoint](evidence/timing-checkpoint004-20260929.json) completed
and its saved ODB, DEF, netlist, SDC and reports were independently rehashed.
The predecessor archive was also checked member by member. Setup is
−6.364772 ns and hold −1.838065 ns; both still fail global-route estimates.
The fifth batch is running with the same clock constraints, SRAM placements
and pinned controller inputs. Its [raw checkpoint views](evidence/timing-checkpoint004-assets-20260929.json)
are preserved separately from the running fifth batch. Final routing,
qualified RC/SRAM Liberty, STA and equivalence remain required.

### 2026-09-29 — filled native DRC complete; supply extraction recovery

The [completed verification](evidence/chip-offset-filled-native-completed-20260929.json)
checks all eight groups of run36527710008 against the same filled GDS
`a5c79c3920154af5a523e3a1224402d6e863b9f7dd91c367ac6256d9045ad8ff`.
BEOL completed in 13,018.79 seconds with all 117 categories and zero markers.
Together with FEOL and geometry, all 560 main categories pass. Antenna has
31 categories/zero markers, supplemental wide has 11/zero, and all 37 density
rules executed with zero markers. The verifier independently rechecks every
report, log, category catalog, input bundle member and source-method digest.
This closes this candidate's eight native DRC groups; transistor LVS, qualified
RC, final timing and manufacturer acceptance are separate unfinished gates.

The [hierarchical supply extraction](evidence/chip-filled-supply-recovery-20260929.json)
has now failed with `std::bad_alloc` in `LayoutToNetlist.extract_netlist` under
its 1.5 GiB address-space cap. It produced no accepted connectivity result.
The original method and failure log are retained. The
[recovery package](evidence/chip-filled-supply-recovery-assets-20260929.json)
also preserves all eight raw DRC reports, the original IO LEF and unchanged
native metal/via derivation references.

`chip-filled-supply-connectivity` prepares that exact GDS and runs
`scripts/check_chip_supply_connectivity.py` on a separate GitHub worker.
The extraction cap is the smaller of 12 GiB and available memory minus 1 GiB;
the worker must have at least 4 GiB for extraction. Controls run before the
full chip, and stage/resource/error records survive failed runs. There is no
inner elapsed-time watchdog; the hosted platform still imposes its six-hour
job limit. Existing healthy local timing work is unchanged.

The new acceptance guard rejects child-local circuit IDs, shorted supplies,
split identities and missing rails. Local hierarchical positive and
disconnected-instance controls pass, as do five acceptance regression tests.
Any future passing extraction proves only the 27 input-pad power ports through
seven metals and six vias. It does not establish every chip pin, transistor or
substrate connection, nor replace full-chip LVS. The recovery job has no
accepted chip result at this delivery.

### 2026-09-29 — corrected I/O transforms and fifth timing checkpoint

The [corrected contact audit](evidence/chip-filled-corrected-io-contacts-20260929.json)
converts the placement file's quarter-turn codes 0–3 into 0/90/180/270 degrees
before constructing complex transforms. Every one of the 314 native I/O
placements is checked against an actual instance in the filled `a5c…` GDS.
Replaying the native conductor/opposite-routed-supply contact measurement with
those corrected transforms reports zero contacts in all 10,526 port windows.
The original inset and unfilled offset receipts remain invalid historical
method outputs; this new result applies to the current filled GDS only.

The new `scripts/plan_chip_supply_probes.py` independently enumerates every
POWER/GROUND rectangle from the original IO LEF, verifies placement multiplicity
against the actual GDS hierarchy and checks every transformed rectangle with
KLayout. It rejects unsupported geometry, incomplete pins, invalid coordinates
and ambiguous rotation encodings. Its output agrees exactly, including
multiplicity, with the corrected audit: IOVDD 3,188, IOVSS 4,781, VDD 1,279 and
VSS 1,278 windows across six metal layers. Twenty-one planner tests cover these
parsing and transform hazards. This inventory is preparation for a complete
ring connectivity measurement. Windows alone do not prove conductor coverage;
the extractor must intersect them with native geometry and account for every
resulting component. Neither the inventory nor the direct-contact audit proves
rail continuity, transistor/substrate LVS or manufacturing readiness.

The [raw correction package](evidence/chip-filled-corrected-io-contacts-assets-20260929.json)
preserves the old failure, corrected method/log/result, independent inventory,
placement/LEF inputs, routed supply boxes, native rule references and tests.
The running 27-input-pad cloud extraction uses actual GDS transforms directly
and is unaffected by the metadata conversion bug; it remains a separate job.

The [fifth timing checkpoint](evidence/timing-checkpoint005-20260929.json)
completed with setup −6.157546 ns and hold −1.988766 ns. Setup improved while
hold worsened; both remain failing global-route estimates. Saved outputs,
controller inputs and every member of the archived fourth checkpoint were
rechecked. The sixth batch is active with unchanged constraints and SRAM
placements. Its predecessor's [raw views](evidence/timing-checkpoint005-assets-20260929.json)
are preserved; no final routed timing or equivalence acceptance is claimed.

### 2026-09-29 — conductor-piece probes and native I/O topology

`scripts/probe_supply_components.py` prepares the next whole-ring connectivity
measurement. It intersects each supply search window with the registered
conductor layer, decomposes its polygons into convex, hole-free pieces and
queries an interior witness in every piece. Queries use the original extracted
layer, preserving connections outside the window. Empty windows, multiple
identities and child-local circuit identities cannot pass as one top-level net.

Six small geometry controls pass: a hole at the window centre, disconnected
islands, a connection outside the window, an empty required port, a one-database-
unit-wide conductor and two floating instances with identical child-local IDs.
The first development attempt used `each_point_hull` on a `SimplePolygon` and
failed; its source and traceback are retained. The corrected binding uses
`each_point`, and all six controls run through the pinned KLayout executable.

The [native-cell measurement](evidence/native-io-component-probes-20260929.json)
then exercised all 13 I/O masters used in the chip. Seven native conducting
metals and six vias were extracted locally under a 768 MiB address-space cap.
All 494 declared supply windows resolve to cell-level nets, and an independent
comparison matches every window, including multiplicity, against the previously
verified whole-ring inventory. The [raw package](evidence/native-io-component-probes-assets-20260929.json)
preserves the methods, controls, native derivation references, LEF and results.

Same-named supply windows can resolve to distinct **cell-local** nets: for
example, `sg13g2_IOPadIn` has two IOVSS identities, and the output/bidirectional
pads have two IOVDD and two IOVSS identities. Filler cells can also expose
separate conductors across layers. Their physical parent must provide the
intended joins. These standalone measurements do not establish a chip-level
open or a successful chip connection. The active 27-input-pad extraction is
unchanged; complete 314-instance continuity, transistor/substrate LVS and final
timing remain open.

### 2026-09-29 — reusable connectivity checkpoints and sixth timing result

`scripts/supply_checkpoint.py` prepares a reusable record for a future complete
I/O connectivity run. It writes the native compressed KLayout database, reads
it back and compares registered layer names, database units and sampled net
equivalence. Raw cluster numbers may be renumbered; the comparison preserves
the connectivity relation across all queried windows, including unresolved
child-local identities. Loading requires an independently pinned manifest and
matching database size/hash, method hashes and KLayout version.

The [checkpoint controls](evidence/supply-checkpoint-controls-20260929.json)
found that the default extraction configuration can omit floating child
instances when saving. Their geometry disappeared after reload, so the first
attempt failed. The caller must set `include_floating_subcircuits=True`
**before extraction**; the save helper rejects a disabled flag and verifies
the resulting roundtrip. This retains isolated instances without joining them.
Three corrected roundtrips pass: a connected seven-metal hierarchy, a floating
hierarchy that remains unresolved, and windows with outside connections,
separate islands and empty geometry. Six rejection cases cover damaged files,
wrong/changed manifest pins, wrong source pins, overwrite and disabled floating
retention. The [raw controls](evidence/supply-checkpoint-controls-assets-20260929.json)
preserve both failed attempts and the successful database files.

This is a tested checkpoint mechanism, not a completed chip checkpoint. The
active cloud extractor and its pinned inputs remain unchanged; it does not
currently serialize its graph. A future run must enable floating retention
before extraction and use complete I/O probe coverage. Full-chip continuity,
transistor/substrate LVS and manufacturing acceptance remain open.

The [sixth timing checkpoint](evidence/timing-checkpoint006-20260929.json)
completed with setup −5.990112 ns and hold −1.980585 ns. Both improved slightly
from checkpoint5 but remain failing global-route estimates. Output hashes,
controller inputs and every member of the predecessor archive were verified.
The seventh batch is running; the completed [raw checkpoint views](evidence/timing-checkpoint006-assets-20260929.json)
are separately preserved. No final routed timing or equivalence pass is claimed.

### 2026-09-29 — complete window-plan consumer and seventh timing result

`scripts/audit_supply_checkpoint.py` connects the verified window inventory to
a saved physical connectivity database. Its CLI requires independent hashes
for the checkpoint manifest and the window plan. It rejects different GDS
identities, incorrect units, missing floating-hierarchy retention, incomplete
instance/master/rail/layer counts and malformed windows. Every declared window
is queried through `probe_supply_components`; missing windows, split rails,
child-local identities and shared nets between different supplies prevent a
pass. Layer mapping uses the registered native `metal8` through `metal134`
conductors; names never create virtual connections.

The [consumer controls](evidence/supply-checkpoint-plan-controls-20260929.json)
exercise the full save/load/CLI path on four small, explicitly synthetic
layouts: connected rails pass; a short, a split rail and an absent port fail.
A window plan bound to a different GDS is also rejected. Ten additional plan
validation regressions pass. The [raw control package](evidence/supply-checkpoint-plan-controls-assets-20260929.json)
contains the exact GDS, plans, databases, manifests, results and test methods.
These are consumer tests, not a chip-level connectivity result. The actual
314-instance/10,526-window plan is ready, but its full-chip checkpoint has not
yet been produced. The running 27-input-pad cloud job is unchanged.

The [seventh timing checkpoint](evidence/timing-checkpoint007-20260929.json)
has setup −5.515583 ns and hold −1.840246 ns, both still failing global-route
estimates. All output and controller input hashes and the preceding checkpoint
archive were verified. The [raw views](evidence/timing-checkpoint007-assets-20260929.json)
are preserved, and the eighth batch is active. Final routed timing, qualified
SRAM RC/Liberty and equivalence remain open.


### 2026-09-29 — checkpoint verification in a separate process

The previous synchronous save helper temporarily holds both the original and
reloaded connectivity graphs. `scripts/supply_checkpoint_staged.py` adds a
separate-process path for future large extractions. `prepare` saves the compressed
database, registered layers, original probe snapshot and input/method hashes to
`prepared.json`. This is explicitly unverified; existing consumers cannot load
it. The producer then exits. A fresh process verifies the independently pinned
prepared receipt, source/database hashes, tool version, registered layers and
probe equivalence before creating `manifest.json`. The existing complete-window
consumer can then use that manifest without changing its acceptance rules.

Linux process birth and boot identifiers prevent verification while the original
producer remains alive. Verification rejects incomplete records, changed source
pins, corrupted databases, altered probe expectations, method changes and an
existing final manifest. It preserves the original prepared record. The original
synchronous helper remains unchanged for small controls and historical replay.

The [native staged controls](evidence/supply-checkpoint-staged-controls-20260929.json)
run actual KLayout producers and CLI verifiers in separate processes under a
256 MiB address-space limit. A connected hierarchy remains connected; floating
child instances remain unresolved. Live-producer verification, prepared-only
consumption, five provenance/data corruptions and final-manifest overwrite are
rejected. The [raw package](evidence/supply-checkpoint-staged-controls-assets-20260929.json)
contains those native databases, receipts, logs and the runnable control script
`sw/tests/supply_checkpoint_staged_native.py`.

These small controls establish serialization behavior, not whole-chip memory
requirements or rail continuity. The active 27-input-pad cloud extraction is
unchanged and has no checkpoint output. A future complete 314-instance run must
enable floating retention before extraction, prepare its checkpoint, exit, run
the staged verifier, then audit all 10,526 declared supply windows. Full-chip
transistor/substrate LVS, final timing and manufacturing acceptance remain open.


### 2026-09-29 — hosted extraction timeout and local complete-I/O recovery

[Run 36551234397](https://github.com/Melihakbulut221/nssoc/actions/runs/36551234397)
was cancelled at 18:46 TRT. The job annotation explicitly reports the hosted
six-hour execution limit. Its preserved extraction record stops at
`EXTRACTING_FULL_METAL`; no rail result, completed graph or native exit-code file
exists. The artifact ZIP digest and every extracted member were checked, as
were all 108 preparation pins, seven extraction pins, the unchanged filled GDS,
original native references and source method at commit `4313fe5`. This is a
[verified failure record](evidence/chip-supply-local-recovery-20260929.json),
not a completed connectivity measurement. The previous native DRC results are
unchanged.

`scripts/extract_supply_checkpoint.py` now prepares the complete 314-instance,
10,526-window graph for local recovery. It checks the pinned GDS, independent
window-plan hash and native conductor/via definitions, retains floating
hierarchy before extraction and saves a staged checkpoint. The controller then
waits for producer exit, verifies the checkpoint in a separate process and runs
the complete-window consumer. No elapsed-time watchdog terminates these local
steps. All source inputs are hashed before queueing and rechecked before each
stage; failed attempts remain available.

Integration controls found another persistence distinction: raw source layers
used during Boolean preparation appear in `layer_names()` but are omitted from
the saved connected graph. Omitting their names did not fix this, and explicit
re-registration was rejected by the native API. The corrected producer declares
its checkpoint contract **before serialization**: all seven native conducting
metals and all six vias. The helper records excluded preparation-layer names,
requires every probe layer in the declared contract and still demands exact
reloaded layer/probe equivalence. No required conductor, via, probe or electrical
connection is removed. The original synchronous save helper remains unchanged.

Thirteen exact Boolean-layer controls verify drawing plus fill, slit/resistor
cuts, top-metal inductor cuts and the MIM exclusion on TopVia1. Four synthetic
GDS cases then exercise extraction, staged save, fresh-process verification and
all-window audit: connected supplies pass; a short, a split and an absent port
fail. Omission of a probe layer is rejected. The previous staged native controls
also pass again. Failed attempts and corrected controls are preserved in the
[raw recovery package](evidence/chip-supply-local-recovery-assets-20260929.json).
These controls do not establish actual chip continuity or full-chip LVS.

The detached local controller is queued with an 8 GiB address-space cap,
requiring 9 GiB available RAM (including a 1 GiB reserve) and 1 GiB free disk
before each stage. Only about 1.4 GiB RAM was available at queue creation, so
**the full extraction has not started**. These are conservative execution
settings, not measured minimum chip memory requirements. The controller checks
resources every 30 seconds and starts automatically when they are sufficient.
The running timing repair remains untouched. No replacement hosted extraction
was launched; the timeout outputs and local continuation state are retained.


The final delivery check detected a changed timeout-receipt hash in the first
idle local queue: re-running the failure verifier had refreshed that receipt
after queue creation. No extraction stage had started, and all physical inputs
and method hashes were unchanged. The old controller's PID/birth, process group
and absence of children were verified before stopping it. The replacement queue
binds its own immutable receipt copy; all pinned inputs were checked again.
The [correction record](evidence/chip-supply-local-queue-correction-20260929.json)
and [raw controller package](evidence/chip-supply-local-queue-correction-assets-20260929.json)
preserve the drift, old identity and replacement method. Resource thresholds
and physical acceptance requirements are unchanged; the replacement still
waits for sufficient RAM.


### 2026-09-29 — eighth timing checkpoint and mapped-path diagnosis

The [eighth checkpoint](evidence/timing-checkpoint008-20260929.json) completed
with setup −5.360166 ns and hold −1.840246 ns. Setup improved by 0.155417 ns
from checkpoint7; hold is unchanged. Both remain failing global-route estimates.
All output/controller hashes and every member of the archived preceding
checkpoint were verified. The ninth batch started from these outputs with the
same clocks and SRAM placements. The [raw checkpoint package](evidence/timing-checkpoint008-assets-20260929.json)
preserves ODB, DEF, netlist, constraints and native reports.

An independent [report-to-netlist diagnostic](evidence/timing-checkpoint008-diagnosis-20260929.json)
locates the worst reported setup path at the slow corner: register-file x16
bit13 (`_133180_/Q`) to instruction-fetch address bit31 (`_126138_/D`). The
endpoint Q maps to `prefetch_buffer_i.fetch_addr_q[31]`. Arrival is 28.596535 ns
against a 23.236368 ns requirement with the unchanged 20 ns core clock. This
establishes the mapped endpoints and reported combinational path, not a source
RTL repair or final delay qualification. The diagnostic covers the 60 setup
paths in this report, not every path in the chip.

The worst of 50 reported hold paths is the fast-corner QSPI output-enable
`qspi_io_oe_o[3]`: arrival 2.409754 ns against 4.250000 ns required. The electrical
report still contains **two slew violations and three capacitance violations**.
Both slew failures are `fanout1387/X` and `fanout1391/X`; those two and
`fanout3120/X` fail capacitance. Their exact mapped buffer masters and port nets
are retained in the [diagnostic package](evidence/timing-checkpoint008-diagnosis-assets-20260929.json),
which references the independently published raw checkpoint. These are concrete
remaining repair targets; none was waived or claimed closed by the checkpoint.
The independently queued complete-I/O extraction still requires sufficient RAM.


### 2026-09-29 — ninth timing checkpoint and isolated buffer candidate

The [ninth checkpoint](evidence/timing-checkpoint009-20260929.json) has setup
−4.898848 ns and hold −1.838546 ns. Both improved from checkpoint8 but remain
failing global-route estimates. All output/controller hashes and every member
of the archived eighth checkpoint were checked. The tenth batch is active;
its ninth-checkpoint inputs and clock/macro constraints remain unchanged.
The [raw ninth checkpoint](evidence/timing-checkpoint009-assets-20260929.json)
contains the native database, netlist, constraints and reports.

Electrical repair is still required: the ninth report has two slew and four
capacitance violations. An [isolated netlist candidate](evidence/checkpoint009-buffer-candidate-20260929.json)
changes exactly four `sg13g2_buf_1` instances. `fanout1387` and `fanout1391`
become `sg13g2_buf_4`; `fanout1228` and `fanout1593` become `sg13g2_buf_2`.
The first pair's reported loads are 0.556475 and 0.547383 against the original
0.3 capacity limit; the other pair is 0.335437 and 0.329623. The native output
limits are 1.2 for buf4 and 0.6 for buf2 in each of the three selected PVT
libraries. Selection reserves 20 percent of that capacity; no library limit,
clock period or timing constraint is relaxed.

The candidate preserves all instance names and pin connections. Reversing only
those four master substitutions reproduces the original netlist byte for byte.
Native Liberty functions and two-pin interfaces agree across all three PVT
corners. An exhaustive local test of the four replacements runs all 256 input
combinations over 0, 1, X and Z using the original native Verilog models. It
passes. Icarus warnings about unsupported timing checks elsewhere in the full
cell-model file are retained; this is a combinational functional test, not a
timing simulation or a full-chip equivalence proof.

The [candidate package](evidence/checkpoint009-buffer-candidate-assets-20260929.json)
preserves the modified netlist, generator, native three-corner Liberty files,
original Verilog models, testbench and raw log. This candidate has **not** been
applied to an ODB or layout. Larger cells need legal placement, routing, fresh
parasitics and renewed timing/DRC checks; higher input capacitance may affect
upstream drivers. The unchanged running tenth batch must not be overwritten
with this older candidate. Any later integration must reconcile against its
latest output and revalidate affected instances. The complete-I/O extraction
queue remains separate and still waits for sufficient RAM.


### 2026-09-29 — investigation of faster setup and hold repair

[The timing-repair study](106-timing-repair-research.md) identifies a native
four-repairs-per-pass experiment, setup-preserving early GMII hold repair,
remaining electrical ECOs and a specific long XNOR connection on checkpoint9's
critical path. The opt-in profiles passed native Tcl argument validation only;
their physical speedup and resulting timing remain unmeasured. The active
baseline and all constraints are unchanged. The study also corrects the tempting
assumption that selecting ten percent of endpoints guarantees tenfold faster
repair: this version can spend its entire iteration budget following the worst
path before visiting the remaining endpoints.

### 2026-09-29 — three timing methods implemented and queued locally

The [three-method campaign](106-timing-repair-research.md) now has immutable
local copies and an active controller. It waits for checkpoint10 to finish,
then verifies the completed views before trying targeted XNOR placement, early
setup-preserving hold repair and a one-versus-four setup comparison from the
same input. The old parent controller is intentionally paused; its current
OpenROAD child continues. This prevents a competing checkpoint11 from starting.

The [launch receipt](evidence/timing-three-methods-launch-20260929.json) records
the handover, source/configuration hashes and 45 passing process/selection/archive
tests. Native parser and synthetic placement controls also pass. No chip result
or speedup from these new profiles is available at this snapshot. The existing
local/GitHub progress monitor now runs every three hours and retains autonomous
stall investigation. SRAM, final timing, extraction and product acceptance
requirements remain unchanged.

### 2026-09-30 — checkpoint10 and recovery of the three-method campaign

[Checkpoint10 and the recovery receipt](evidence/timing-three-methods-recovery-20260930.json)
confirm setup −4.710829 ns, hold −1.840329 ns, two slew and six capacitance
violations. The first three-method campaign failed at CLI directory validation
before chip loading. The corrected controller creates fresh run directories,
revalidates the completed baseline and has started the targeted placement
candidate. [The timing study](106-timing-repair-research.md) explains the failure,
new native launch regression and remaining timing/physical acceptance scope.
The placement candidate subsequently completed: the connection shortened from
463.620 to 233.940 µm, but its before/after summary timing did not improve. It
was rejected and guarded hold repair started from checkpoint10. Monitoring
now runs every eight hours. No new candidate result is accepted yet.

### 2026-09-30, morning — CI closure and diagnosis of the long hold sweep

All four `f206286` GitHub workflows now pass. Native job logs and selected
artifact hashes independently confirm the result, including 116 SoC and
54 pilot formal tasks; skips and historical excluded attempts retain their
separate status. [The timing study](106-timing-repair-research.md) records why
the live hold job exceeds the nominal 100-iteration setting: the native inner
sweep visits all 4073 endpoints below the requested positive margin before
checking that limit. CPU and log progress are confirmed; it was not stopped.
The supply queue remains intentionally reserved while timing runs. A bounded
per-pin method passed a native three-corner, three-flop regression and is available
for a subsequent isolated experiment. It has not yet run on the chip. The
[verification receipt](evidence/timing-hold-targeted-20260930.json) retains that
scope; the current campaign, constraints and incomplete physical acceptance
remain intact.

### 2026-09-30, afternoon — completed hold experiment rejected; setup awaits RAM

The [completed hold review](evidence/timing-guarded-hold-complete-20260930.json)
verifies the 8 h 50 min native result and all 31 archived files. Negative hold
endpoints fall from 113 to 11, with final global-estimate hold WNS −1.078148 ns.
The candidate adds one negative setup endpoint and is worse than C10's selected
setup WNS, so it is rejected and C10 remains selected. The preserved result is
not final routed timing or physical acceptance.

The native child exited cleanly and the supply reservation was released.
At 14:25 the next setup experiment waits for 5 GiB available RAM; approximately
3.2 GiB is available. Supply extraction separately requires 9 GiB. The
[timing study](106-timing-repair-research.md) records the exact comparisons,
resource diagnosis and tested reporting improvement for future controller
copies. The active immutable campaign and all acceptance requirements remain
unchanged. All four `761f147` GitHub workflows are independently verified
successful; their software/formal scope does not establish chip signoff.

### 2026-09-30 — preserve I/O substrate globals and isolate an unchanged cell hierarchy

The native I/O CDL declares `*.GLOBAL sub!`, which the pinned SPICE reader treats
as a comment. Previously, selecting reachable subcircuits also discarded this
library-level declaration. `normalize_io_cdl.py` now converts this explicit CDL
metadata to `.GLOBAL`; `io_cell_schematic.py` retains the declaration when
selecting cells. It never infers a global from a node name or connects it to a
chosen supply. For the real Vdd reference, the change is exactly the addition of
`.GLOBAL sub!` before the previous selected device bodies. A native four-resistor
control confirms that the two child substrate nets now bind to one declared
global; the old comment form and a wrong-global negative control leave them
separate. Device parameters are unchanged. The full-chip reference generator has
not yet been migrated to this helper, and no whole-chip LVS pass is implied.

The adapter also rejects output/receipt path aliases, uses exclusive writes and
rejects CRLF inputs instead of silently changing bodies claimed to be preserved.
Seventy-three related regressions pass. These checks do not repair the remaining
physical device or substrate mismatches by changing expected parameters.

Loading the full 71,399,990-byte I/O GDS exceeded the isolated diagnostic address
space caps before LVS comparison. `scripts/extract_gds_hierarchy.py` now streams
only the chosen root and every referenced cell while copying their original
records unchanged. Vdd needs four of the 46 cells, producing 2,435,898 bytes.
Library header/units and every selected cell hash are preserved; output is
independently re-indexed. Unsupported records, malformed dependencies, missing
references, cycles and unsafe output paths are rejected. Actual extraction used
19,896 KiB peak RSS under a 100 MiB address-space cap. Thirty-five tests pass,
including a native geometry/XOR control with both single and array references.
This preserves the selected root's geometry, not all unselected library cells.

The [I/O global and hierarchy evidence](evidence/io-substrate-global-repair-20260930.json)
records the exact source hashes, native control and cell-comparison outcomes,
including resource failures. The [raw package](evidence/timing-guarded-hold-complete-assets-20260930.json)
retains failed attempts alongside the corrected methods. The seven I/O
transistor LVS gates and full-chip acceptance remain separate requirements.

The native Vdd A/B comparison now completes with the unchanged deck and GDS.
The extracted netlists are byte-identical; the schematic differs only by the
explicit vendor global declaration. `sg13g2_RCClampResistor` changes from
`NoMatch` to `Match`. Overall Vdd still fails: `sg13g2_Clamp_N43N43D4R` and
`sg13g2_RCClampInverter` remain `NoMatch`, and the parent is `Skipped`.
Tap area/perimeter differences and split child terminals requiring actual
parent connectivity remain under investigation; no expected parameters,
physical nets or comparison rules were changed to obtain the child match.

The first subset run hit a proven thread-creation failure at a 1 GiB virtual
address-space cap. Its failure and guarded cleanup are retained. Both subsequent
comparisons completed under a 1.5 GiB cap, using approximately 454 MiB peak RSS;
there was no elapsed-time watchdog. Only Vdd was rerun with the new adapter,
and no seven-master or whole-chip acceptance is claimed. The combined controller,
I/O and GDS extraction regression suite passes all 168 selected tests.


### 2026-09-30 — tiled cloud supply extraction replaces the monolithic recovery job

The previous hosted whole-graph extraction reached GitHub's six-hour job limit
without a complete connectivity result. The new `chip-supply-tiled` workflow
uses 64 independent native extraction jobs over an 8 × 8 spatial partition.
Preparation retains the complete chip geometry, all seven conducting metals
and six via levels, and the pinned inventory of 314 I/O instances and 10,526
port windows. Two-DBU overlaps include all 210 face and corner adjacencies.
Tiles are joined only by matching physical overlap geometry and identical
interior witness locations. Supply names and reused child cluster IDs never
create connections. Unsupported arbitrary-slope clipping fails explicitly.

Each extraction process exits before a separate native checkpoint replay.
The aggregate checks every tile, overlap and window; it also verifies the
actual prepared/promoted manifests, compressed connectivity database hashes,
source/method/tool identities and canonical replayed witness partitions.
Missing or conflicting evidence is a failure. This addresses the previously
unsplittable extraction stage; production-chip preparation runtime and memory
requirements have not yet been measured for this new method.

Thirteen small native cases match the complete window equivalence classes of
independent unsplit extraction. They include exact tile-corner contact, a
one-DBU gap, all six via levels, a missing via, MIM exclusion, resistor cuts,
multiple components, open/short faults and repeated floating child instances.
Eleven corrupted coverage/checkpoint cases and one unsafe clipping case are
rejected. Fifty-one focused Python tests, Ruff and workflow/Bash parsing pass.
The native controls use KLayout 0.30.7 and peak at 90,388 KiB RSS. The workflow
runs both the Python and native controls before preparing the chip geometry.

The [migration receipt](evidence/chip-supply-tiled-migration-20260930.json)
records exact source, input and validation hashes. The compact
[raw control package](evidence/chip-supply-tiled-native-controls-assets-20260930.json)
is an 81,044-byte release asset containing 460 inventoried files; local,
authenticated and anonymous download round trips agree. Its archived source
snapshots are bound by hashes and explicitly distinguished from their base
Git commit. No large production layout is copied into the documentation site.

The initial workflow uses fresh inputs. Recovery uses a new dispatch with
both `resume_run_id` and an independently verified `resume_bundle_sha256`;
input and method hashes must still agree. Completed tile checkpoints are
replayed before reuse, and absent tiles are extracted. Rerunning every job of
the same run can collide with its immutable artifact names, so explicit new-run
resume is preferred. Native phases use a 4 GiB address-space cap and a 1 GiB
available-memory reserve; eight workers may run concurrently. GitHub's
360-minute per-job limit remains, without a native elapsed-time watchdog.

[The production-chip cloud run](https://github.com/Melihakbulut221/nssoc/actions/runs/36758126140)
passed its pinned-input and native-control gates and began full geometry
preparation at 21:24 TRT. At that startup snapshot, the prepared bundle and
tile measurements were incomplete; the completed result below supersedes that
status. The idle local supply controller was intentionally paused after
identity, zero-child and input-pin checks. The immutable input files remain
unchanged. Startup alone did not establish connectivity or physical acceptance.

### 2026-09-30 — complete tiled supply result and independent archive replay

[Run 36758126140](https://github.com/Melihakbulut221/nssoc/actions/runs/36758126140)
completed at 21:53:40 TRT: preparation, all 64 extraction/replay jobs and the
strict aggregate passed. The full hosted workflow took 31 minutes 3 seconds,
including setup and queueing; the geometry preparation itself took 365.154
seconds. All 314 I/O instances and 10,526 declared windows have exactly one
physical component per supply, with four different components for the four
rails. Every one of 210 overlaps agrees across 63,774 conductor witnesses.
No label-based connections or comparison-rule exceptions were introduced.

The [completed result](evidence/chip-supply-tiled-complete-20260930.json) binds
the result to filled GDS `a5c79c3920154af5a523e3a1224402d6e863b9f7dd91c367ac6256d9045ad8ff`,
plan and bundle hashes. Independently downloaded 67 original artifact ZIPs
match GitHub's recorded sizes and SHA-256 values. The local auditor streams
all 1,043,577,744 bytes of prepared geometry, checks all 64 separate prepared
receipts and every native checkpoint's source, promotion, database and witness
chain, then recombines the graph and compares every window assignment with
the cloud result. It passed in 4.45 seconds with 126,136 KiB peak RSS under
a 768 MiB address-space cap. This reuses recorded native measurements; it
does not repeat native geometry extraction locally.

The [durable raw archives](evidence/chip-supply-tiled-complete-assets-20260930.json)
retain the complete prepared geometry, all native databases, measurements,
logs, method snapshots and independent replay receipts. Twenty new archive
identity/path/corruption controls pass; the selected archive, supply and
publication regression totals 102 passing tests. Native GDS read warnings
remain visible in the raw logs; each serializer's geometry XOR checks passed.

This accepted result covers the declared I/O supply-window metal graph of
this exact layout. It does not certify transistor devices, ESD behavior,
current capacity, extracted RC, final timing or a different core candidate.
The seven I/O transistor LVS failures remain open. The local monolithic
supply controller stays intentionally paused after its cloud handover.

### 2026-09-30 — strict Vdd parent-context comparison completed; mismatches remain

The Vdd clamp reference has 172 MOS fingers at 4.4 µm, for 756.8 µm total
width. The extracted child has 22 devices with the same total width, but
separate drain ports that physically join in the parent. The latest
explicit-global Vdd subset had not previously been tested using the native
deck's flat parent context. An isolated
[cloud comparison](https://github.com/Melihakbulut221/nssoc/actions/runs/36768228777)
used the same byte-preserved GDS and schematic for deep and flat modes.
All 53 pinned deck files, strict top ports, tap extraction and A/P comparisons
remain unchanged. No expected parameter is replaced by an extracted value.

The [runner evidence](evidence/io-parent-context-lvs-20260930.json) records
84 selected Python tests and eight small native framework controls. A real
parent metal/via bridge passes; same-name disconnected drains, a missing via,
wrong MOS W/L, tap A/P and reversed tap terminals are rejected. These generic
KLayout controls are not an IHP device or Vdd acceptance result. The actual
Vdd comparison uses the unmodified IHP deck on an isolated cloud worker with
a 4 GiB address-space cap, a 5 GiB available-RAM guard and no elapsed native
watchdog. Mismatching or incomplete native results remain failures and their
artifacts are retained. Both real Vdd comparisons completed and failed strict
LVS. The flat layout correctly combines the clamp into one 756.8 µm / 0.6 µm
MOS, confirming the parent-drain diagnosis. It still has nine primitive devices
against eight in the reference, two separate IOVSS nets, and three extracted
taps against two reference taps. Tap area/perimeter disagreements remain.
The 625,063-byte raw artifact, 106 input pins, 12 native output hashes and
40 control output hashes were independently verified. Reopening both native
LVS databases reproduces the failures without repeating geometry extraction.
These results identify the remaining boundary/connectivity and tap-reference
problems; they do not accept Vdd or any of the seven I/O masters. The complete
chip's declared-window metal result above is a separate comparison scope.

The [follow-up raw evidence](evidence/cloud-supply-and-io-followup-assets-20260930.json)
retains the real deep/flat databases, reports, failed diagnostic attempts,
native controls and independent replays.

The separate [publication CI failure](evidence/publication-cache-repair-20260930.json)
was resolved by a bounded scratch dependency preparation stage and a resource
cache. The final freshness checks and 300-second final command budget remain
unchanged. Both corrected CI runs passed; one complete artifact was independently
checked against 39 exact source inputs, four fresh documents and their content
and archive digests. This publication result is separate from physical acceptance.

### 2026-09-30 — cloud batch-four timing repair completed; candidate not adopted

The [batch-four cloud job](https://github.com/Melihakbulut221/nssoc/actions/runs/36757448901)
completed its native experiment in 4,470.62 seconds (74 minutes 31 seconds).
The [independent audit](evidence/timing-cloud-batch4-complete-20260930.json)
verified all 41 ZIP members, the complete captured/inherited dependency closure,
32 unchanged SRAM masters/locations/orientations and byte-identical source,
before, after and output SDCs. The
[durable archive](evidence/timing-cloud-batch4-complete-assets-20260930.json)
contains the actual native outputs and the review; inherited GDS/SDF/Liberty
views are identified as old inputs, not new signoff results.

| Global-route estimate | Fresh before | Completed batch-four |
|---|---:|---:|
| Setup WNS (ns) | -4.909516349 | -4.255827690 |
| Setup TNS (ns) | -4320.800144342 | -3595.444468374 |
| Setup violating endpoints | 1,384 | 1,313 |
| Hold WNS (ns) | -1.840965380 | -1.840965380 |
| Hold violating endpoints | 113 | 113 |
| Slew / capacitance violations | 0 / 1 | 0 / 1 |

Despite the setup improvement, the existing no-regression policy rejects this
candidate. Hold TNS worsens by 0.0000142108547 ns relative to the fresh before
measurement, and hold WNS is 0.0006363801399 ns worse than selected C10's
recorded -1.840329 ns. Both exceed the unchanged 0.000001 ns comparison tolerance.
The latter difference is already present in the fresh before measurement;
it is not all introduced by the setup repair. The baseline job remains active
at this snapshot. No completed A/B speedup or preferred profile is established,
and selected C10 remains unchanged. The next comparison must first verify the
baseline's input identity and fresh measurements, then diagnose the rejected
hold checks without waiving them. These are global-route estimates; final
routing, qualified RC, multi-corner timing and equivalence remain open.

### 2026-09-30 — both cloud timing profiles and comparison completed

The baseline subsequently completed, and the
[paired result](evidence/timing-cloud-ab-complete-20260930.json) supersedes the
pending-baseline snapshot above. It took 96.01 minutes and reached setup WNS
-4.331184300 ns with 1,340 violating endpoints, versus batch-four's 74.51 minutes,
-4.255827690 ns and 1,313 endpoints. Both fresh initial measurements agree.
Both candidates fail the existing hold guards, so the strict comparison selects
neither. This one paired trial supports an observed performance improvement;
it does not accept a new layout or establish final timing. The
[detailed comparison](106-timing-repair-research.md) records the measurements,
limitations and next diagnostic work. Local RAM no longer blocks these completed
experiments; the immutable local fallback controllers stay paused.

### 2026-10-01 — distinguish parent connectivity from the strict tap contract

A [new bounded audit](evidence/io-tap-contract-audit-20261001.json) recursively
resolves ordered CDL ports and local/global net scopes, then sums explicit tap
area/perimeter using decimal arithmetic. It uses the captured strict Vdd
flat/deep netlists; it does not run LVS or change layout/reference geometry.
Unsupported multipliers and unknown tap/instance parameters are rejected.
Legacy positive R/W/L metadata is recorded under the pinned reader's explicit
A/P precedence. Thirty-one tests cover quantity, scope, terminal ordering,
unknown parameters and the conditional metal-only join calculation.

If tap-recognition masks and their measured A/P remain fixed, hypothetically
joining the two IOVSS pieces gives area 2117.58205 square micrometres and
perimeter 1113.69 micrometres, versus reference 2104.583 and 243.16. The separate
VSS A/P disagreement remains. This calculation proves that **metal-only joining
under those fixed-mask assumptions is insufficient**; it does not predict an
actual ring-parent extraction whose overlapping recognition regions change.
Both currently pinned upstream main (`5e6d592`) and dev (`c702f87`) retain the
same Vdd tap totals. A library update alone is not a demonstrated Vdd fix.

A separate source-supported correction was identified: the old
`sg13g2_IOPadVss` DCN guard maps to `iovss`, whereas current upstream maps it to
`iovdd`, consistent with the [IHP developer's correction](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/714#issuecomment-3396005804).
It has not been applied blindly: formal port order also changed, so a coherent
GDS/CDL/LEF version and actual parent-context comparison are required. The
[IHP library discussion](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/955#issuecomment-4352461493)
also describes arbitrary tap shapes and hierarchical overlap. These sources
identify missing contract/geometry work; they do not authorize dropping A/P or
using virtual name joins as transistor LVS. All seven I/O masters and full-chip
transistor LVS remain open.


### 2026-10-01 — Vss reference migration contract verified; native LVS remains open

The [ordered-interface audit](evidence/io-tap-topology-contract-20261001.json)
checks the old `c4b8b4e` library against pinned upstream main `5e6d592` and dev
`c702f87`. The upstream
[coordinated I/O update](https://github.com/IHP-GmbH/IHP-Open-PDK/commit/1a29eb4980d520d9ce7273593dc1599310cb81a9)
changes the Vss pad's DCN guard from `iovss` to `iovdd` and changes its formal
port order in the same GDS/CDL/LEF revision. Named diode-terminal comparison
confirms the old reference mismatch and the newer reference match. This is a
schematic interface result, not a transistor extraction result.

The old Vss formal order is `(iovdd, iovss, vdd, vss)`; the new order is
`(vdd, vss, iovdd, iovss)`. For positional callers, the zero-based permutation
`[2, 3, 0, 1]` preserves the named rail mapping. Blindly reusing the old argument
list swaps core and I/O rails in the four-distinct-rail control. Actual chip
callers and the active PDK were not changed. Mixed old-GDS/new-reference
controls are rejected; 18 new topology tests and 31 existing contract tests pass.

The Vss LEF macro body is byte-identical across the three checked versions,
while the complete GDS identities differ. This does not establish which device
shapes changed. Old GDS bytes were stream-verified; newer main/dev GDS views
are bound to upstream Git blob metadata but were not downloaded or geometrically
compared in this bounded audit. A coherent single-revision GDS/CDL/LEF candidate
and strict native parent-context LVS are still required. Tap A/P mismatches,
all seven I/O-master failures and full-chip transistor LVS remain open.

The separate [completed timing diagnostic](106-timing-repair-research.md)
now establishes stable complete hold-endpoint exports across seven post-routing
no-op stages, with 113/31/10 violations at fast/typical/slow corners. It did not
reproduce the historical after-repair TNS change and did not select a new core.
The assembly therefore inherits no new timing or production acceptance from
this diagnostic or from the Vss reference audit.

The [compact follow-up archive](evidence/cloud-hold-complete-and-io-topology-followup-assets-20261001.json)
retains the raw upstream commit/API observations, ordered-port contract audit,
source snapshots and controls for this update. This publication does not change
the open native transistor LVS result.


### 2026-10-01 — isolated coherent Vss library experiment

The new `coherent-io-lvs` workflow prepares an isolated comparison using GDS,
CDL and LEF from the same IHP commit
`5e6d592e4002946a4616f798c357f0f3c06cf3b6`, with the matching pinned native
LVS deck. All three downloaded views must match their exact Git blob identity
and byte count. The experiment extracts the unchanged Vss hierarchy and runs
strict deep and flat LVS after the existing physical-parent positive and
negative controls. It does not replace the active PDK or chip layout.

The current CDL uses an explicit two-terminal `XR` tap with `A` and `P` values.
A reversible dialect adapter changes only its instance prefix to `R`; ordered
terminals, model and both parameters stay unchanged. The exact Vss and two
diode reference dependencies are selected first, because two unrelated library
cells contain model-less tap declarations. No model is invented for those
cells and no implicit `sub!` global or virtual connection is added. The old
positional-caller migration contract remains `[2, 3, 0, 1]`; no caller changes
are part of this experiment.

Native comparison remains pending. Any mismatch or extraction warning is
retained as failure; a future Vss-only pass would not establish seven-master
or full-chip transistor LVS, repair the separate Vdd tap mismatch, or grant
production acceptance.


The first coherent run, [36916335752](https://github.com/Melihakbulut221/nssoc/actions/runs/36916335752),
passed its eight native physical-parent controls but stopped before Vss LVS.
The conservative GDS subset reader rejected padding after `ENDLIB` at byte
71,422,884. A bounded read of the pinned upstream file confirms a four-byte
`ENDLIB` followed by exactly 1,116 zero bytes, ending at byte 71,424,000.
This is a transport-format preparation failure, not a new transistor LVS
verdict. The [preparation failure receipt](evidence/coherent-vss-preparation-failure-20261001.json)
records a runner-specific adapter that retains the original view and creates a
separate byte-identical prefix through `ENDLIB`, with explicit source/prefix/tail
hashes. The shared strict GDS parser remains unchanged. All 147 selected tests,
including the unchanged subset-reader regression tests and five new corruption
controls, pass. The corrected native retry still requires validation.
