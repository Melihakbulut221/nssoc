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
