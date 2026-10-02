# 106 — Faster setup and hold repair: measured bottlenecks and controlled experiments

**2 October, 15:18 UTC update:** the electrical margin repair completes with
repeatable estimates of **1,311 setup, 67 hold, zero slew and one capacitance
violation**. It improves setup and capacitance but regresses hold against its
parent, so the candidate remains rejected. Complete ALU partition traversal
proves 250 of 269 groups; 19 time out. The ALU candidate/vendor four-state boot
fails near the NPU test despite passing power-on MBIST. The physical method
therefore remains blocked. These are experimental results, not final timing
or full-chip LVS closure; the latest evidence and next steps are below.

**2 October, later update:** one physical XOR-buffer ECO reduces setup
violations from 1,384 to 1,378 and WNS from −4.909516 to −4.744948 ns, with
all measured hold endpoints unchanged. The original C10 guard still fails;
the exported candidate remains rejected. Combined setup/hold repair and
independent reloads are running separately. Details and evidence follow below.

**2 October update:** the corrected targeted hold diagnostic completed. Hold
violations decrease from 113 to 104 with setup aggregates unchanged, but the
historical C10 setup guard still fails and post-routing endpoint regressions
remain. No checkpoint is adopted. The final sections record the completed
native result, its limits and the separately preserved original failure.

**1 October status:** the cloud setup A/B and full-endpoint no-op diagnostic
have completed. Both setup candidates remain rejected; the diagnostic preserves
all seven post-routing endpoint exports but does not reproduce the prior hold
TNS drift. No new checkpoint is selected. The final section records the result
and the next planned repair-boundary measurement. Earlier sections retain their
dated research and execution snapshots.

**29 September 2026: research and native command compatibility, not a measured
speedup or timing closure.** The latest completed input for this investigation
is checkpoint9: setup **−4.898848 ns**, hold **−1.838546 ns**, using global-route
parasitic estimates. Checkpoint10 remains a separate running baseline.
The [research receipt](evidence/timing-repair-research-20260929.json) records
the input hashes, sampled paths, native parser output and proposed experiments.
The full input is in the existing
[checkpoint9 asset](evidence/timing-checkpoint009-assets-20260929.json).

## What is actually costing time

The nine completed batches consumed 15.47 hours in total. Checkpoint9 alone
took 4,239.91 seconds for 100 setup iterations; it ended with 37 resized gates,
36 inserted buffers and 40 pin swaps. The reported intermediate WNS and the
final WNS differ after legalization and parasitic updates, so only the latter
is used to compare completed checkpoints.

The installed OpenROAD is **dcf36133a369abc8f3c5e5738cd4d82e4903c0e0** inside
LibreLane 3.0.5. Its default maximum is one repair per pass, followed by
parasitic and timing updates. Increasing that maximum to four is a concrete
experiment for doing more useful work between these expensive updates. The
algorithm can still perform fewer moves or revert unsuccessful ones. This
does **not** predict a fourfold speedup.
[Pinned implementation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/RepairSetup.cc#L716-L777),
[update loop](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/RepairSetup.cc#L392-L398).

The log's “repairing 1397 endpoints” is a selected population, not proof that
each batch visits all 1397. The first endpoint loop follows the current worst
path, and the 100-iteration limit can expire there. Reducing `-repair_tns` to
10 therefore is **not** an established tenfold improvement.
[Endpoint loop](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/RepairSetup.cc#L463-L488).

## Experiments, in priority order

| Experiment | Evidence and intended benefit | Acceptance boundary |
|---|---|---|
| Setup: one versus four repairs per pass | Same complete checkpoint and 100 iterations; change only `-max_repairs_per_pass`. Reduce repeated analysis per useful move. | Compare final WNS/TNS improvement per wall-clock hour, violating endpoints, hold, slew/cap, area and peak memory. Reject regressions. |
| Early, setup-preserving hold repair | The controller currently postpones hold until setup reaches +0.1 ns. GMII TX paths have positive setup slack already. | Omit `-allow_setup_violations`; retain +0.1/+0.15 ns margins and compare all corners before/after. Existing setup violations remain failures. |
| Electrical ECO before further timing search | Checkpoint9 still has two slew and four capacitance failures; the controller always supplies `NSSOC_TIMING_FIRST_CHUNK=0`, so its guarded `repair_design` does not execute. | Reconcile the four previously prepared buffer replacements against the newest checkpoint; apply to an isolated ODB and measure upstream loading, legalization and routing. The netlist-only candidate is not a physical result. |
| Shorten a specific critical connection | `_072583_/Y` drives only `_072584_/B`, but its reported load is 0.088638 pF and slew 1.153508 ns. Cell origins are 463.620 µm apart. | Try local critical-cone placement or an appropriate buffering change. Preserve macro positions and logical equivalence; compare newly routed parasitics. |
| Preserve routing state across process checkpoints | Native route-segment read/write commands exist; checkpoint10's initial global route took 145 seconds. | First prove segment/ODB/netlist consistency and same-checkpoint STA replay. This saves initialization work, not the entire hour-scale optimization cost. |

The [opt-in Tcl profiles](../hw/soc/pnr/timing_repair_experiment.tcl) provide
`setup_baseline`, `setup_batch4` and `hold_guarded`. Sourcing the file performs
no optimization. A new isolated runner must load a complete checkpoint,
propagated clocks, all corners and global-route parasitics, then invoke one
profile. Both setup experiments retain the same existing constraints, move
restrictions, 100-iteration checkpoint boundary and buffer setting. Hold's
setup guard is supported by the
[pinned command implementation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/Resizer.tcl#L309-L374).

The [native parser probe](../sw/tests/timing_repair_profiles_native.tcl) passed
against this exact binary. It verifies the translated arguments, the single
A/B difference, rejection of an unknown profile and `allow_setup=0` for hold.
It substitutes the optimization calls: **no design is loaded, no timing is
measured and no speedup is established by this probe**. An initial probe
harness returned a list where native Tcl expected a boolean; the corrected
harness returns zero. Both raw outputs are preserved in the receipt.

The active hash-pinned runner was not modified. These profiles have **not**
been applied to the chip or automatically queued. At the next controlled
handover, use the newest completed checkpoint and preserve it before testing;
do not restart the experiment from an older checkpoint over newer work.

## Hold has an immediately testable independent opportunity

The report contains at most ten paths per group, not a full violation census.
Of its 50 paths, 34 fail: ten QSPI outputs, ten GMII TX outputs, nine GMII RX
inputs and five internal register paths. The worst hold is QSPI OE bit3.
The ten reported GMII TX setup slacks are **+3.735519…+3.819765 ns**.
For `eth_tx_er_o`, setup is **+3.816676 ns** and hold **−0.525305 ns**. This is
measured room for a guarded delay experiment, subject to fresh corner analysis.
QSPI output setup margins require dedicated reports; they are not in the
current first-ten core setup sample.

QSPI also needs a timing-contract audit. `soc_top_qspi_io.sdc` currently uses
`clk_i` with the same output max +3/min −4 ns budget for SCK, data, OE and CS.
The RTL launches flash data on SCK's falling edge, while the flash model checks
setup/hold against its rising edge. The SDC explicitly calls its board/pad
allowance an assumption. A source-synchronous SCK/data model, including
divider modes, gated/start/stop edges, CS and direction turnaround, may avoid
unnecessary delay insertion. That requires justified board/pad skew and
protocol checks; reducing the −4 ns number alone is not a repair. Existing
constraints remain unchanged by this research.

## The residual setup path needs more than a generic sizing recommendation

Checkpoint9's worst reported path changed from checkpoint8. It now starts at
RF x10 bit31 (`_133854_/Q`) and reaches `_132609_/D`, whose Q is the pipeline's
register-file read-address bit2. The common cone includes ECC, arithmetic,
PMP/address checking and LSU/control. Its report lists one launch output,
23 buffer outputs and 67 other combinational outputs. Because input-pin rows
are omitted, their increments do not separate net delay from cell delay.

The `_072583_/Y` row alone contributes a reported 0.987785 ns increment; this
includes any unreported incoming-net contribution. Its long connection to
`_072584_/B` is net `_018489_`. The 463.620 µm figure is instance-origin
Manhattan distance, **not extracted wire length**. The selected library has
only drive-1 XOR2/XNOR2, so increasing this XNOR's drive is not an available
simple substitution. This makes a local placement/buffering experiment more
specific than another blind whole-design sizing pass.

`CORE_REQ_REG=1`, `CORE_WB_STAGE=1`, `BranchTargetALU=1` and syndrome
precomputation are **already enabled in this physical candidate**. Enabling
them again cannot provide new gains. Cutting the remaining internal CPU cone
with another stage would be a larger microarchitecture change requiring stall,
misaligned access, precise exception/PMP and fault-injection verification.
Removing ECC/PMP is not an accepted timing fix. Likewise, the ABC unit
experiment in [docs/84](84-the-registered-request-phase.md) previously changed
sizing without reducing logic depth; it is not a demonstrated shortcut here.

## Runtime and signoff limits

The host has little available RAM and almost no free swap; this limits parallel
physical experiments. Checkpoint9 averaged approximately 2.65 CPU cores, so
adding threads is not evidence of proportional acceleration. Memory pressure
alone also does not prove the current process is stalled.

Current online OpenROAD documentation includes options absent from this binary:
`-skip_crpr`, `-phases` and `repair_design -reroute` must not be copied into its
runner. `-max_buffer_percent` controls hold buffering in this version; increasing
it does not accelerate setup. Fresh-process checkpoints retain value because
the predecessor long run exhausted its address-space allocation.

No experimental result is accepted solely from resizer's intermediate log.
Legalization, incremental routing and updated multi-corner STA come first;
detailed routing, qualified RC extraction, equivalence and physical checks
remain required for final closure. The previously clean filled-chip DRC result
belongs to a different physical candidate and is not transferred to this one.

## Three-method local campaign, 29 September 2026

The user authorized applying all three methods and changed monitoring from
hourly to **every three hours**. The existing heartbeat was updated in place;
it still checks local and GitHub progress, investigates actual stalls and
continues the remaining product work. No duplicate automation was created.

The [local controller](../scripts/run_timing_experiments.py),
[measured LibreLane step](../hw/soc/pnr/timing_experiment_step.tcl),
[flow entry point](../hw/soc/pnr/timing_experiment_flow.py) and
[critical placement helper](../hw/soc/pnr/critical_xnor_placement.tcl) implement:

1. A target-specific XNOR placement candidate, followed by legalization,
   incremental global routing and fresh measurements. Cell/net identities must
   still match the latest checkpoint. A shorter connection must survive
   legalization; logical netlist bytes and all 32 SRAM placements must remain
   unchanged. A changed connection is rejected for investigation, not silently
   treated as the old path.
2. Early hold repair with `allow_setup=0` and the existing +0.1/+0.15 ns margins.
3. A one-versus-four setup repair comparison from exactly the same selected
   input checkpoint. The one-repair run is the control, not a fourth method.

Each candidate has complete before/after setup and hold WNS/TNS, violating
endpoint counts, slew/capacitance counts, area, instance count and duration.
Setup A/B requires identical input hashes, exact initial counts and initial
numeric measurements agreeing within 1e-6 absolute / 1e-12 relative tolerance;
the different profile names do not invalidate the comparison. Eligible results
must improve their target timing class without worsening the other measured
timing/electrical classes. Source-checkpoint WNS is also preserved; the older
checkpoint lacks the new full metric set, so unavailable source TNS/counts are
not fabricated. Subsequent selected inputs provide the complete metric set.
Batch4 is called faster than an eligible control only if both measured setup
WNS and TNS improvement per wall-clock hour increase. This is a single-run
comparison, not a general performance guarantee.

The new controller is **2506944**, Linux starttime **66086546**, with its plan
and outputs under `hw/soc/out/timing-three-methods-20260929`. These are dated
identities, not reusable PID authorization. The
[launch receipt](evidence/timing-three-methods-launch-20260929.json) binds the
actual command, immutable method copies, configuration, handover and tests.
The current status is `WAITING_FOR_ORIGINAL_CHECKPOINT`: the three profiles are
implemented and automatically sequenced, but their chip measurements have not
started at this snapshot.

Only the old Python controller was paused, preventing it from launching
checkpoint11. Its separate-session checkpoint10 child continues normally.
After native completion, the new controller verifies the child's exit code,
completion markers, SRAM preservation, every input pin and output views before
retiring the old controller. It archives checkpoint9 only after the newer state
is verified and no longer references it. Every archive is checked member by
member before expanded copies are removed; selected views remain available.

The [process guard](../scripts/timing_process_guard.py) uses a pidfd and exact
PID/starttime/argv identity, rather than signaling a numeric PID blindly.
Each new heavy stage requires 5 GiB available RAM and 1 GiB free disk, with an
8 GiB address-space cap and no elapsed-time kill. The independent supply queue
uses its existing 9 GiB threshold. The timing controller can reserve an idle
supply queue by pausing only its verified controller and rechecking for a
startup race; it restores that controller after the heavy stage exits. A live
orphan worker prevents release of this reservation. A crashed controller's
reservation requires inspection by the heartbeat, not blind resumption.

**Validation completed:** 45 small process/selection/archive tests passed,
including an actual synthetic orphan, identity mismatch rejection, corrupt
archive rejection and cross-domain timing regression rejection. The native
profile parser passed. The native OpenDB/OpenDP placement control shortened a
synthetic connection from **400 to 202 µm**, including actual legalization, and
passed placement checking; negative controls reject connection/macro changes
and lost improvement. These synthetic results are not a chip placement result.
A native two-flop smoke check matched the new measurement getters to the
printed timing reports. The installed LibreLane CLI/flow boundary was checked
without loading the full chip.

To recover local space, ten untracked archive caches totaling **484,813,540
bytes** were removed only after matching their local bytes to authenticated
GitHub asset metadata and existing public/authenticated download proofs. Their
release assets remain available; active timing/supply inputs were excluded.
The first cleanup attempt assumed one release for every asset and stopped
before deleting anything. The corrected attempt queries each exact asset ID.
No other project's files were touched.

All resulting geometry still needs detailed routing, qualified extraction,
equivalence, DRC/LVS and final timing review. The controller's selection is an
estimate for further verification, never a production acceptance decision.

## 30 September: failed launch corrected; checkpoint10 retained

Checkpoint10 completed at the end of the original repair sequence. Independent
replay of all 15 output pins, the native log and reports confirms setup
**−4.710829 ns** and hold **−1.840329 ns**. Setup improved by 0.188019 ns from
checkpoint9, while hold worsened by 0.001783 ns. There are still two slew and
six capacitance violations. These are global-route estimates, not final timing.
The original two-XNOR connection remains intact and its instance-origin
Manhattan distance remains 463.620 µm.

The first campaign then failed before loading the chip: the installed
LibreLane CLI requires `--force-run-dir` to name an existing directory. The
controller had not created its candidate directories. Critical placement,
guarded hold and the setup control each exited with code 2; batch4 never
started. The earlier CLI smoke test exercised the `--from`/`--to` boundary
without this directory argument, so it did not catch the error. The earlier
45 passing tests did not establish a complete native launch.

The controller now creates each candidate directory exclusively before launch;
existing directories are rejected to preserve old evidence. A new
[native CLI regression](../sw/tests/timing_experiment_flow_native.py) invokes
the actual entry point with the real configuration, PDK and completed state:
a missing directory is rejected, and creating it reaches the native flow
boundary. Only the expensive execution boundary is intercepted in this test.
A separate controller regression verifies directory creation before process
spawn and refuses reuse. Recovery controls rehash the completed baseline,
compare log measurements to its receipt, require the recorded successful native
exit, reject a live predecessor or unreleased resource reservation, and preserve
the original failed campaign unchanged. All 54 controller/process tests pass.

The new immutable campaign lives at
`hw/soc/out/timing-three-methods-20260930-retry1`; its controller started at
02:28 TRT as PID2549495, starttime67663117. The first candidate completed in 270.05 seconds. It shortened the connection
from 463.620 to 233.940 µm and preserved the native netlist byte for byte.
However, its fresh-route before/after metrics are identical: setup WNS
−4.909516 ns, hold WNS −1.840965 ns, setup TNS −4320.800144 ns and hold
TNS −26.461045 ns. The candidate was therefore rejected; checkpoint10 remains
the selected input and guarded hold repair has started. The original
checkpoint and freshly rebuilt global-route estimates must not be conflated. The
[recovery receipt](evidence/timing-three-methods-recovery-20260930.json) and
[raw package](evidence/timing-three-methods-recovery-assets-20260930.json)
preserve checkpoint10, failed logs, corrected methods and launch controls.

The latest GitHub `checks` jobs also failed their SPDX gate: five Tcl files
used Apache-2.0 where this repository requires CERN-OHL-W-2.0. Correcting only
those headers makes SPDX, all five generator checks and the derived paper
claims gate pass locally. The paper check reports 27 re-derived claims,
15 manual/outstanding claims and zero wrong claims; those outstanding claims
are not treated as accepted. The 9c80233 CI run had 2031 passing tests and
126 skips, independently of its failed licence gate; formal work was still
running at the inspection snapshot. Corrected CI results require a new run.

The user subsequently changed monitoring to **every eight hours**. The actual
existing heartbeat setting was verified active at that interval. The separate
full-I/O supply extraction still waits for its unchanged 9 GiB available-memory
threshold. No final timing, complete LVS or manufacturing approval is claimed.

## 30 September, morning: CI fixed; hold sweep behavior identified

All four GitHub workflows for `f20628639d550ee665156b872c0bcdc46f730cfe`
completed successfully: both `checks` runs, `publications` and `pcie-transaction`.
The previous licence-gate failures are resolved. This is software/formal CI
completion, not physical timing, complete LVS, PCIe PHY or production acceptance.
Per checks run, 2040 pytest cases pass and 126 are skipped; RTL cocotb reports
503 passes and 22 skips. Verified formal artifacts contain 116 passing SoC
and 54 passing pilot tasks. Six historical engine attempts are explicitly
excluded, with their original stalled/unknown outcomes retained; the required
replacement proofs remain in the passing task set. The two duplicate push/PR
runs are not added together. The PR merge commit and source commit have the
same Git tree. The receipt preserves the exact task/exclusion inventories.

The local guarded-hold job remains active. Between the 02:40 delivery and the
06:25 observation, the same native process accumulated 3,486,489 CPU ticks and
advanced from approximately iteration170 to2430. All 19 immutable method/input
pins still match. Supply extraction remains intentionally reserved while this
heavy job runs; its stopped controller is not a failed extractor.

The nearly flat progress table required source-level diagnosis. In the pinned
[RepairHold implementation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/RepairHold.cc#L413-L529),
`max_iterations` and `max_passes` are checked outside a sweep, while the inner
loop visits every endpoint collected for that sweep. The present run collects
**4073 endpoints below the requested +0.15 ns margin**; only **113 endpoints**
have negative hold slack in the initial full measurement. Consequently,
`-max_iterations 100` does not stop this hold sweep at its hundredth row, and
simply reducing `max_passes` would not bound the inner sweep either. The setup
comparison uses a different implementation; this finding is specific to hold.

Most reported negative-slack improvement occurs early: rounded TNS changes
from −26.461 ns to −5.128 ns by iteration110. After that, the run spends much
of its work increasing positive margins; the rounded WNS remains about
−1.091 ns and TNS about −5.125 ns. These are intermediate figures, not completed
post-legalization measurements. The table's endpoint column is the global worst
endpoint, not necessarily the endpoint currently being repaired. The buffer
counter can reset after a journal rollback; it is not a cumulative chip total.
Those details follow the
[rollback and reporting code](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/RepairHold.cc#L651-L815).
They rule out treating a repeated endpoint label or a reset counter as proof
that the native job is hung. The healthy running process and its pinned inputs
are preserved.

The new opt-in `hold_guarded_targeted` profile selects the 16 worst distinct
negative-hold endpoints across loaded corners and gives each one a single native
repair pass. Its helper accepts 1–32 targets. It preserves the +0.10 ns setup
margin, +0.15 ns hold margin and setup protection, records immutable target/result
receipts, and requires the usual legalization and full timing/electrical
remeasurement. A shared budget limits actual instance growth to 40% of the
initial cell count. The native per-pin limit resets at each call, so the wrapper
checks growth before and after every call and rejects the isolated candidate if
native repair overshoots the shared budget. A pass can still visit several
drivers; this is not a wall-time
guarantee. Remaining positive-margin work is explicitly unfinished. The pinned
private API is version-specific. The tracked flow accepts this profile, but the
ongoing four-stage campaign and its immutable copies continue unchanged; no chip
speedup or result from this new method is claimed.

`sw/tests/timing_hold_targeted_native.tcl` exercises actual native repair on a
three-flop SG13G2 fixture with fast, typical and slow corners. Selecting one target
inserts one buffer and improves its hold slack from −0.683040 to −0.437707 ns;
the unselected output remains −0.478646 ns. Setup remains positive
(16.680 to 16.143 ns), and SDC bytes are unchanged. A separate setup-tight target
rejects insertion and preserves both cell count and setup slack. Invalid limits,
missing native API, receipt overwrite and no-negative-target controls also pass.
The native two-target control stops after consuming its one-cell shared budget;
a separate native two-buffer insertion exceeds that budget and is rejected.
These are small-fixture regression results, not chip timing closure. The
[verification receipt](evidence/timing-hold-targeted-20260930.json) and
[published raw evidence](evidence/timing-hold-targeted-assets-20260930.json)
preserve the CI inventories, upstream implementation, QSPI audit and native
regression inputs/results.

The separate QSPI audit traces its 4.25 ns hold requirement to a −4.0 ns
`clk_i`-referenced output delay plus 0.25 ns clock uncertainty. The −4.0 ns is
the repository flash model's 2.0 ns hold value plus an assumed 2.0 ns board/pad
allowance. SCK, data, OE and chip-select currently share this budget even though
they have different roles. Replacing it requires independently validated SCK
and data flight-time, output-enable/disable, chip-select and read-turnaround
contracts. Merely increasing the software divider, inserting a sequencer
register, or adding a multicycle exception is not a demonstrated physical hold
fix. Existing divider/abort/lane tests pass (three selected tests); those RTL
checks do not qualify board or pad timing. The active constraints are unchanged.

## 30 September, afternoon: guarded hold completed and rejected

The guarded hold experiment completed at 11:23 TRT with native exit code zero,
after 31,832 seconds (8 h 50 min). Independent streaming verification checks all
31 archived files, the final completion markers, the unchanged SDC, all 32 SRAM
master/placement/orientation records and all 303 top-level DEF pin records.
The following values are measured **after legalization and the incremental
global-route parasitic update**, not the earlier progress table:

| Metric | Freshly rebuilt input | Completed hold candidate |
|---|---:|---:|
| Setup WNS (ns) | −4.909516 | −4.875384 |
| Setup TNS (ns) | −4320.800144 | −4283.189810 |
| Negative setup endpoints | 1384 | 1385 |
| Hold WNS (ns) | −1.840965 | −1.078148 |
| Hold TNS (ns) | −26.461045 | −4.776081 |
| Negative hold endpoints | 113 | 11 |
| Slew / capacitance violation counts | 0 / 1 | 0 / 1 |
| Instance count | 103697 | 108085 |

The candidate is **rejected**, despite the substantial hold improvement. It adds
one negative setup endpoint, and its setup WNS is 0.164555 ns worse than the
selected C10 checkpoint's recorded −4.710829 ns. Both independent regression
checks fail. The rebuilt input above is a separate reference; beating it does
not permit regression from the selected checkpoint. C10 remains selected. The
raw rejected output is retained and published; no timing result is waived or
relabelled as accepted. The [completed hold review](evidence/timing-guarded-hold-complete-20260930.json)
and [raw asset inventory](evidence/timing-guarded-hold-complete-assets-20260930.json)
preserve the exact comparison and native evidence.

At 14:25 TRT the controller has no live native child and is waiting to start
`setup_baseline`. Approximately 3.2 GiB of memory is available against its
unchanged 5 GiB requirement; swap is nearly exhausted and disk headroom is
approximately 1 GiB. The supply reservation was correctly released at 11:23;
that separate queue now waits for its own unchanged 9 GiB memory requirement.
Neither queue is a running physical measurement. Scoped process inspection
finds no leftover large NSSOC worker to retire safely. Other projects and
applications are untouched, and no duplicate heavy job is launched.

Future controller copies now record the pending profile, original request time,
required memory/disk and exact shortfall while waiting, so an updated heartbeat
timestamp cannot be mistaken for native progress. Sixty controller/process
tests pass, including insufficient-memory/disk controls that prohibit worker
inspection or launch before resources are available. The active campaign's
19 pinned inputs and fixed thresholds remain unchanged. Its next stages are
still the same-input one-repair versus four-repairs setup comparison; the
targeted hold profile remains an unexecuted chip experiment.

All four workflows for `761f1478dd876b21e2136326d091036af26d5bfc` are verified
successful: 2043 pytest passes and 126 skips per checks run, 503 RTL passes with
22 reported skips, and 116 SoC plus 54 pilot formal passes. The six historical
excluded attempts and the conditional native-boot skip remain explicit. These
CI results do not close the physical or product acceptance requirements.

## 30 September, evening: move the setup comparison to GitHub workers

The local controllers remain unable to start the next experiment while available
memory is below their 5 GiB timing and 9 GiB supply-extraction guards. The public
repository can use standard GitHub Linux workers with 16 GB RAM. The platform
has a six-hour limit per job; moving a calculation does not remove that limit.
See the [worker specifications](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
and [execution limits](https://docs.github.com/en/actions/reference/limits).

The cloud setup comparison gives `setup_baseline` and `setup_batch4` separate
workers, using the same selected C10 checkpoint and the exact six immutable
method files from the existing campaign. The new
[input manifest](https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/docs/evidence/timing-cloud-input-20260930.json) pins every dependency,
including all 5080 PDK files, the SRAM views, transitive SDC sources and every
view referenced by the original state. The
[published input archive](evidence/timing-cloud-input-assets-20260930.json)
contains 5180 files and is independently verified after upload. The PDK root
symlink is materialized as ordinary files; only JSON path values are relocated.
Reversing the 30 recorded path substitutions exactly recovers the original
configuration and state. Original native geometry and constraint files retain
their hashes. Historical SDF, Liberty and GDS views carried with the checkpoint
are not new candidate signoff results.

The cloud runner retains the original 8 GiB native address-space cap, timing
constraints and 100-iteration repair recipes. It does not impose an elapsed-time
native watchdog. Bounded polling steps can save progress while the worker keeps
running; these snapshots are explicitly incomplete and cannot serve as restart
checkpoints. Completed outputs require native completion markers, unchanged
inputs and constraints, all 32 SRAM placements, and the same before/after and
selected-C10 regression guards. Only matching initial measurements permit the
one-repair versus four-repairs speed comparison. Routing, RC extraction,
equivalence and final timing acceptance remain separate requirements.
The [migration receipt](evidence/timing-cloud-migration-20260930.json) records
input verification and distinguishes preparation from a running or completed
cloud experiment.

The first submission failed before starting any job because the job-level
environment used the unavailable `runner` context. The corrected definition
passes actionlint 1.7.12, and the original definition is a verified negative
control. [The replacement run](https://github.com/Melihakbulut221/nssoc/actions/runs/36757448901)
started native global routing for `setup_batch4`: its startup artifact verifies
32 macros and 14.69 GiB available host memory before launch. This is not a peak
RSS measurement. The idle local timing controller was paused only after
checking its exact identity, absence of children and all 19 immutable inputs.
The baseline worker also entered native global routing, with 14.46 GiB
available before launch. Both startup captures have identical input, runtime,
method and SDC identities; no completed comparison is claimed. The final local
regression includes 101 timing/process tests and 51 supply tests, all passing.

The [validation and startup package](evidence/cloud-migration-validation-assets-20260930.json)
retains all earlier failed checks beside their corrected successful runs, both
verified native startup artifacts and the exact committed source snapshots.
It is independently verified after publication. The first available-memory
measurements establish that the local launch blocker is bypassed; they do not
establish a speedup, successful repair or final timing closure.


## 30 September, late evening: completed cloud comparison

Both native setup jobs and their strict comparison completed successfully on
GitHub. The [completed paired audit](evidence/timing-cloud-ab-complete-20260930.json)
verifies their exact source/runtime/input identities, all captured output
bytes and inherited dependencies, 32 SRAM placements and unchanged SDCs.
Their freshly rebuilt initial timing, electrical and area measurements match.
The [baseline and comparison archive](evidence/timing-cloud-baseline-and-comparison-assets-20260930.json)
and the separate [batch-four archive](evidence/timing-cloud-batch4-complete-assets-20260930.json)
retain both complete native results. The local RAM guards were preserved;
the deliberately paused local controllers did not run duplicate jobs.

| Same-input global-route experiment | One repair per pass | Up to four repairs per pass |
|---|---:|---:|
| Native elapsed minutes | 96.01 | 74.51 |
| Completed setup WNS (ns) | -4.331184300 | -4.255827690 |
| Completed setup TNS (ns) | -3632.587777 | -3595.444468 |
| Setup violating endpoints (initially 1,384) | 1340 | 1313 |
| Setup WNS gain per hour (ns/hour) | 0.361419 | 0.526387 |
| Setup TNS gain per hour (ns/hour) | 430.086304 | 584.097601 |
| Accepted by existing no-regression checks | No | No |

Batch-four took **22.39% less wall time in this one paired trial**, with a
better setup endpoint count and improvement per hour. Separate hosted workers
and one observation do not establish a general speed guarantee. Both candidates
retain 113 hold endpoints, hold WNS -1.840965380 ns, zero slew violations and one
capacitance violation. Both have the same hold TNS change from
-26.461044910775 ns to -26.461059121630 ns. The unchanged 0.000001 ns guard rejects
that change and also rejects the hold WNS difference from selected C10's
recorded -1.840329 ns. The latter difference already exists before either
setup optimization; it must not be attributed entirely to repair. No numerical
noise exception or comparison waiver has been applied.

The comparison therefore has **no eligible profile and no selected candidate**.
C10 remains selected, and its preserved files are unchanged. The next step is
to diagnose the source-versus-rebuilt timing difference and the common hold TNS
change with matched parasitic/reproducibility evidence, then test a repair that
passes the existing guards. GitHub job success means complete measured outputs;
it does not mean final timing closure. Routing, qualified RC extraction,
multi-corner timing and equivalence remain required.


A bounded log/source follow-up found that the four before/after hold reports
across both profiles are byte-identical (102,796 bytes each). They contain
50 selected paths, including 34 reported violations, rather than a complete
census of all 113 violating endpoints. Their equality therefore cannot prove
that every hold path is unchanged. The C10-to-fresh worst endpoint is the same
`qspi_io_oe_o[3]` at the fast corner. Restart preparation removes database wires
and rebuilds global routing, estimated parasitics, legalization and mirroring
before setup repair; the reference difference must be investigated at that
boundary. Both TNS values in seconds are exactly representable as float32,
eight representable steps apart. That observation supports a numerical or
aggregation-order hypothesis but does not establish it. A matched-state no-op
measurement and full-precision endpoint census are still required; the existing
guards and both rejected verdicts remain unchanged. The diagnosis and its raw
pins are included in the paired audit and durable archive above.

### 2026-10-01 — isolate full-endpoint hold readback on GitHub

The completed cloud A/B removed the local available-memory wait; it did not
close timing. The next isolated workflow, `timing-hold-diagnostic`, reuses the
same published C10 input archive and LibreLane runtime. Its diagnostic methods
are separately copied and hashed, leaving the previous campaign's methods and
all local fallback inputs intact. It requires at least 9 GiB available memory
before native execution and retains the 8 GiB address-space cap. Tiny native
controls must pass before the full chip is loaded. No new local physical job is
started on the memory-constrained workstation.

The measurement separates initial ODB reload, rebuilt global routes, and the
published A/B legalization boundary from repeated queries and invalidated
STA caches on an otherwise unchanged state. It exports every native endpoint
at each corner in SI seconds, together with full-precision native aggregates
and deterministic endpoint sums. Constraint, connectivity, placement, routing
and observable Pi/Elmore model fingerprints identify the no-op boundary.
Unconstrained endpoints and missing models are explicit. These are estimated
parasitic observations, not qualified extracted-RC signoff.

The runner rejects incomplete census, wrong units, changed source inputs or
changed no-op fingerprints. It preserves startup, progress and final artifacts
on GitHub, including failed controls; observers do not impose a native elapsed
timeout. The hosted platform's six-hour job ceiling still applies. Neither a
successful diagnostic nor a floating-point discrepancy changes the existing
acceptance tolerance, selects a candidate or closes a production gate. New
native results must be reviewed independently before drawing a timing conclusion.

The first [native startup attempt](https://github.com/Melihakbulut221/nssoc/actions/runs/36812467876)
confirmed 15,678,377,984 bytes available before native execution. Its tiny
fixture failed at the routing-layer range parser (`Metal2:Metal5`); the pinned
OpenROAD command requires `Metal2-Metal5`. Full-chip execution did not begin.
Independent ZIP review also caught GitHub's default omission of the staged
`.github` workflow file. The rerun fixes the range syntax and explicitly
includes hidden files from the curated diagnostic output directories. The
first failed ZIP remains incomplete and is not retrospectively accepted.
The [method, completed CI and I/O audit archive](evidence/cloud-hold-methods-ci-and-io-audit-assets-20261001.json)
preserves the pre-rerun source and validation; new native results are separate.

The [second native attempt](https://github.com/Melihakbulut221/nssoc/actions/runs/36812843776)
passed the routing parser but exposed a time-unit metadata assertion bug before
full-chip loading. Pinned OpenSTA `unit_scale` returns a C++ `float`: nominal
1 ns is represented as `9.9999997171806854e-10` seconds, not binary64 literal
`1e-9`. The helper and independent reader now preserve and exactly check both
the native binary32 value and the separate nominal unit. Adjacent binary32
values, binary64 substitution and wrong units are rejected. No raw slack is
rescaled and no timing tolerance is changed. This metadata correction does not
establish the cause of the earlier chip hold TNS difference.

The [corrected native run](https://github.com/Melihakbulut221/nssoc/actions/runs/36813322010)
passed all four tiny control cases and entered full-chip global routing.
[Independent startup review](evidence/cloud-hold-native-startup-20261001.json)
verified all 80 captured files, seven method files, original input templates,
path relocations, and the native controls' complete five-stage replay: 12
endpoints, three corners and two negative endpoints per stage. Repeated/cache
updates preserved the physical fingerprints; the real rerouted mutation was
rejected as a no-op. The full-chip log shows 32 SRAM macros, 55,952 blockages,
1,313 clock nets and extra global-route iteration 1/50. Available memory before
that native phase was 15,689,404,416 bytes. This is verified cloud execution,
not a measured peak memory figure or a completed timing result.

The [original startup and failure archive](evidence/cloud-hold-native-startup-assets-20261001.json)
retains the raw ZIPs and corrections. The full-chip eight-stage diagnostic is
still incomplete at this snapshot; no candidate or timing result is accepted.
The deliberately paused local controllers remain paused and their inputs were
verified unchanged. Further progress is followed on this existing cloud run.


### 2026-10-01 — completed no-op diagnostic; repair-boundary cause still open

[Run 36813322010](https://github.com/Melihakbulut221/nssoc/actions/runs/36813322010)
completed successfully at 07:17 TRT. The full-chip native phase took 705.054
seconds; the preceding tiny controls took 15.004 seconds. This supersedes the
startup-only snapshot above. The
[completed diagnostic receipt](evidence/cloud-hold-complete-diagnosis-20261001.json)
records eight stages and independent replay of all 16 endpoint tables against
the producer's recorded byte counts and hashes. It exports 23,527 endpoint
identities and 70,581 endpoint/corner rows per stage. Each corner has 17,145
constrained and 6,382 explicitly unconstrained endpoints; complete export does
not imply complete timing constraints.

All seven stages after global-route reconstruction have **identical complete
endpoint values and identical constraint, netlist, placement, route and
observable Pi/Elmore fingerprints**. Repeated queries, arrival invalidation,
full timing invalidation, RC re-estimation and incremental routing without
repair produce zero hold TNS change in this run. The 32 SRAM placements and
original SDC remain preserved. The separate initial ODB reload has no rebuilt
estimated parasitics and must not be used as the matched timing reference.

| Rebuilt global-route corner | Negative hold endpoints | Hold WNS (ns) | Native hold TNS (ns) |
|---|---:|---:|---:|
| Fast, 1.32 V, −40 °C | 113 | −1.840965380 | −26.461044911 |
| Typical, 1.20 V, 25 °C | 31 | −0.925876931 | −10.257279470 |
| Slow, 1.08 V, 125 °C | 10 | −0.282388224 | −2.074237226 |

The result reproduces the earlier A/B **before** TNS exactly, but does not
reproduce its −14.210855 fs after-repair change. Native TNS agrees with a single
binary32 rounding of the independently summed endpoint values in this run;
that observation does not explain the historical change. The old after-repair
results lack complete endpoint exports, so repair-induced path changes and
incremental aggregate arithmetic remain unresolved alternatives. The original
C10 producer's estimated-RC cache was not restored; its rounded −1.840329 ns
hold WNS still differs from the rebuilt −1.840965380 ns. Neither difference is
waived. Pi/Elmore getters also cannot distinguish an absent Elmore value from a
zero value, so their unchanged fingerprints have that explicit limit.

The new [bounded setup probe](https://github.com/Melihakbulut221/nssoc/actions/runs/36858091870)
is running on GitHub at source `0e76a3a4d9b3234b4958ab9f5da6c5ab55ee246a`; native completion
is pending. It captures full endpoint/corner values before repair, immediately
after repair, after normal legalization/routing/RC update, and after full timing
cache recomputation. The immediate post-repair stage is explicitly provisional.
One global optimization iteration and one endpoint pass are allowed, with at
most four driver moves; a move can change multiple cells. Post-loop last-gasp
and critical-VT sweeps are disabled. These are experiment work-budget limits,
not relaxed timing requirements. The native setup API does not enforce its
`max_buffer_percent` option; the probe additionally checks net instance growth
against 40% of its initial population. It cannot adopt a candidate. The existing
0.000001 ns comparison tolerance, selected C10 reference and production gates
remain unchanged. All 167 selected source tests passed. Native execution requires
9 GiB available memory and is capped at 8 GiB address space on the cloud worker;
no native process was launched locally.

The original final artifact is 478,807,891 bytes and contains 144 files
(945,676,244 bytes expanded). Because local storage cannot safely hold the
complete download and extraction, the isolated
[archive run](https://github.com/Melihakbulut221/nssoc/actions/runs/36857496790)
verified the complete ZIP and reran the exact producer-commit verifier on
GitHub before publishing its unchanged bytes. That archive job completed
successfully. Independent local review verified all 26 compact receipt files,
the exact native and archival Git sources, and fresh release API metadata.
The [original full diagnostic ZIP](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/timing-hold-diagnostic-complete-20261001.zip)
was checked byte for byte after both authenticated and anonymous cloud downloads. No native physical calculation was repeated for
archival verification. A successful diagnostic or archive publication does
not close final timing, extracted RC or signoff.

The [compact follow-up archive](evidence/cloud-hold-complete-and-io-topology-followup-assets-20261001.json)
preserves the independent endpoint analysis, full-archive verification receipt,
I/O topology source audit and exact setup-probe methods. Its members and complete
compressed bytes were verified after both authenticated and anonymous downloads.

The [setup-probe startup archive](evidence/cloud-setup-probe-startup-assets-20261001.json)
proves that four tiny native controls passed and full-chip native work started.
The 378,274-byte original ZIP, 76 captured files, eleven exact Git method sources
and 26 relocated input references were independently checked. Available memory
before native chip work was 15,690,600,448 bytes (14.61 GiB); the recorded route
log reached extra iteration 3/50. This clears the local resource bottleneck for
this run. Startup does not prove the repair or four final chip snapshots have
completed. The native log still reports missing SRAM Liberty models and a
base-flow multi-clock warning; this remains diagnostic global-route timing.


### 2026-10-01, 20:40 TRT — setup probe stopped by native journal assertion

The [probe failure receipt](evidence/cloud-setup-probe-failure-20261001.json)
supersedes the earlier running snapshot. Run 36858091870 finished with failure
at 15:01 TRT. Its native phase ran for 405.029 seconds: global routing completed
with zero overflow, and the initial snapshot exported 23,527 endpoints with 113
negative hold endpoints. Setup repair began, then OpenROAD aborted with signal 6
at `dbDatabase::commitEco` / `Resizer::journalEnd` because its journal stack was
empty. No post-repair snapshot or accepted timing result exists. The
[original failed artifact](https://github.com/Melihakbulut221/nssoc/actions/runs/36858091870/artifacts/11160082372)
is retained unchanged; this was a native assertion, not a RAM-availability wait.

Inspection of the pinned OpenROAD `RepairSetup.cc` identifies a boundary case:
when pass 1 improves timing with `max_passes=1`, the improvement branch commits
and closes the journal. The `max_iterations=1` branch then commits it again
without checking `journal_open`. The proposed compatible correction keeps the
global iteration limit at 1 and allows a per-endpoint ceiling of 2, reopening the
journal before the global limit closes it and exits both loops. A second pass is
still prevented by that global limit. This source-supported workaround requires
native verification; no runtime binary, setup/hold margin, acceptance tolerance,
physical input or selected candidate is changed.

The corrected source `df3dd93fca89487dac46e6506c005713dd294430` passed 172
selected tests, including execution of the actual Tcl command construction and
rejection of the unsafe old limits. [Retry 36901798029](https://github.com/Melihakbulut221/nssoc/actions/runs/36901798029)
was started on GitHub at 20:45 TRT. It remains incomplete; the source correction
is not a claim of successful physical repair. The four generic CI checks for
the previous delivered `48b34dd` commit completed successfully.

The corrected retry startup was independently checked: all eleven method files
match `df3dd93`, all 76 captured files match their recorded hashes, and the four
native controls passed. The new Tcl arguments retain the one-iteration budget
with the corrected per-endpoint cap. Native chip work started with 14.62 GiB
available RAM and an 8 GiB address-space cap. The startup snapshot shows global
routing, not a completed repair or proof that the former crash boundary passed.


### 2026-10-01 — native setup probe completed; persisted JSON comparison corrected

[Retry 36901798029](https://github.com/Melihakbulut221/nssoc/actions/runs/36901798029)
completed all four native snapshots at source `df3dd93`. The controls returned 0
in 15.005 seconds and the full-chip native phase returned 0 in 855.061 seconds.
This verifies passage through the previous journal assertion boundary. The
overall workflow nevertheless **failed** during final independent capture
validation: changed endpoint records used Python tuples, which became lists
when saved as JSON. Reconstructing the same values then failed exact dictionary
equality. The original failed workflow and artifact remain preserved.

Commit `bebfbe704748d8ab347db9a4db86b53670a6624c` makes those two array fields
JSON-stable. It changes no slack value, identity check, threshold or acceptance
guard. A persisted CLI roundtrip test fails with the original implementation
and passes after the correction; all 24 comparator tests pass. Independent
replay of the real result finds exactly 666 tuple/list fields across three
nonempty comparisons, with no other comparison value or structural difference.
All five stored comparisons now reconstruct exactly. No native rerun was needed
for this representation correction.

The [completed probe diagnosis](evidence/cloud-setup-probe-complete-diagnosis-20261001.json)
pins all 16 selected native metadata, SDC and endpoint files, plus the original
source configuration. Each stage exports 23,527 endpoint identities and 70,581
endpoint/corner rows. There are 6,382 explicitly unconstrained identities per
corner; complete export is not complete timing-constraint coverage.

| Stage | Setup WNS (ns) | Setup TNS (ns) | Setup violations | Hold violations |
|---|---:|---:|---:|---:|
| Matched before | −4.909516349 | −4320.800144342 | 1384 | 113 |
| Immediately after repair, provisional | −4.738650361 | −4104.378149350 | 1377 | 113 |
| After legalization/routing/RC update | −4.738764048 | −4104.394975002 | 1377 | 113 |
| After full timing-cache update | −4.738764048 | −4104.394975002 | 1377 | 113 |

Repair changes 37 endpoint minima in each corner, or 111 endpoint/corner pairs.
Every changed minimum remains positive, but some hold margins do decrease:
fast and slow each have 15 regressions and 22 improvements; typical has 16
regressions and 21 improvements. Among the changed fast-corner endpoints, the
smallest margin is 26.215 ps before and 17.773 ps after. These reductions are
retained in the diagnosis. All 113 negative global endpoint values, and all
negative per-corner rise/fall/minimum values, are exactly unchanged. Native hold
TNS and the independent negative-slack sums also remain unchanged. Subsequent
legalization/RC and full-cache updates cause no additional hold endpoint changes.
The historical −14.210855 fs TNS difference remains unreproduced and unresolved.

The original 72,242,239-byte journal-failure ZIP is now durably published and
[independently reviewed](evidence/cloud-setup-probe-failure-assets-20261001.json),
including authenticated and anonymous cloud byte roundtrips. The **new**
269,855,333-byte completed-native artifact has now passed the separate
[full cloud archive verification](evidence/cloud-setup-probe-complete-assets-20261001.json).
Run 36915992602 checked all 125 original members and reran the producer verifier
with only the pinned JSON array correction. Original measurements and capture
bytes remain unchanged. The original verifier reproduced the recorded failure;
the corrected verifier passed with a 4 GiB address-space limit. No native
calculation was repeated. Independent local review checked all 48 compact
receipt members, original and overlaid Git sources, and fresh release metadata.
The unchanged ZIP is publicly archived with verified authenticated and anonymous
cloud byte roundtrips. This verifies the captured diagnostic's inventories and
recorded physical/parasitic fingerprints, not qualified extracted-RC signoff.
No candidate is adopted, and setup/hold closure, qualified extracted timing,
SRAM Liberty coverage and production approval remain open.


### 2026-10-02 — archive tests work in shallow CI checkouts

The general checks at source `fb3f749` failed twelve archive-helper tests because
the fixture read the historical `df3dd93` commit with `git show`, while GitHub's
checkout contained only the current commit. This was a test-input availability
failure, not a change to timing measurements or an RTL failure. The
[history-free reproduction](evidence/ci-archive-fixture-fix-20261002.json) first
reproduced all twelve failures in a one-commit repository without that history.
The fixed fixture stores the exact 11,341-byte producer source and verifies both
its original SHA-256 and the corrected comparator's SHA-256 before testing the
representation-only difference. Production archival still fetches and verifies
its exact Git sources. No source pin or acceptance guard was relaxed.

All 38 tests pass in the history-free reproduction, and 112 selected archival
regression tests pass in the project. The original failing CI remains preserved;
a new source run is required before claiming the whole CI is green. The
separate SoC formal job in run 36917226540 completed with 116 fresh tasks and
six explicitly recorded historical exclusions; it does not establish physical
or PCIe PHY qualification.

The repaired source `52977da` now passed the actual GitHub
[`checks` job](https://github.com/Melihakbulut221/nssoc/actions/runs/36960651450/job/110693372453):
2,553 Python tests passed with 127 explicit skips, and the repository check
summary reports 19 passed, zero failed and two skipped. The same source's RTL,
memory-parity, Python-quality, PCIe transaction and publication jobs also passed.
Formal jobs were still running at this observation; this is not a claim that
the entire workflow or any production acceptance gate has passed.


### 2026-10-02 — bounded negative-endpoint hold probe

The new `timing-targeted-hold` cloud workflow reuses the pinned existing
`hold_guarded_targeted` recipe on original C10: at most 16 distinct negative
endpoints, ranked across all three corners, with one native pass per endpoint.
Setup margin remains 0.1 ns, hold margin 0.15 ns, setup-violation insertion is
disallowed, and the entire batch shares the original 40% instance-growth budget.
The four-stage export records matched-before, provisional post-repair,
post-legalization/routing/RC and full-cache-update endpoint values. It retains
all configured corners, fixed SDC and 32 SRAM masters/positions/orientations.

Before C10 is loaded, the exact same native executable must pass the existing
small targeted fixture, including setup-headroom and global-budget negative
controls. Before any full-chip repair, the matched baseline must reproduce
23,527 endpoints, 113 negative hold endpoints and the source PVT corners.
The original implementation mistakenly used the tiny fixture aliases; the
correction and failed native evidence are recorded below.
An unexpected baseline stops repair. The independent verifier checks the
complete selection/call history, all stage inventories and original C10 as
well as matched-before aggregate guards.

This is a new measurement experiment, not a completed hold reduction or a
resumable candidate. It exports no full-chip ODB/DEF and never adopts the
result automatically. Original C10 remains selected; its historical-vs-fresh
timing discrepancy and qualified SRAM Liberty/RC limitations remain open.
Actual native fixture, chip result and any speed improvement require the
new GitHub run's evidence; local pure-Python/Tcl tests cannot establish them.

The [source-validation record](evidence/timing-targeted-hold-source-20261002.json)
pins all five new methods and the unchanged existing native fixture/recipe.
All 196 selected pure-Python/Tcl tests passed. Review also caught OpenSTA's
six-decimal UI slack formatting: target-receipt comparison now reproduces the
pinned native float32 division, small-value clamp and formatting exactly.
Full endpoint SI values and acceptance tolerances remain unchanged.


### 2026-10-02 — actual pre-repair failure and exact runtime identity correction

[Run 36962503055](https://github.com/Melihakbulut221/nssoc/actions/runs/36962503055)
passed its small native fixture, loaded C10, globally routed and exported the
matched baseline. It then stopped **before any chip repair**: the baseline
guard compared C10's exact `nom_fast_1p32V_m40C`, `nom_slow_1p08V_125C` and
`nom_typ_1p20V_25C` names with the tiny fixture's `fast/slow/typical` aliases.
The original source configuration and native endpoint table independently
confirm 23,527 unique endpoints and 113 negative endpoints. The repair-begin
marker and all post-repair stages are absent. The original failed artifact
remains failed; it is not evidence of an unsuccessful optimization attempt.

The [retry diagnosis](evidence/timing-targeted-hold-retry-20261002.json)
records reproduction of both original Python/Tcl rejections and acceptance of
the same actual census after correcting the exact corner names. It also
preserves a second, independent validator defect: the base fixture hashes the
PATH launcher, while the targeted fixture hashes Tcl's native entry wrapper.
Their hashes legitimately differ. Read-only inspection of the exact pinned
AppImage proves launcher → entry wrapper → actual ELF, with separate exact
paths, byte lengths and SHA-256 values. The new gate checks all three before
C10 loading and again after its small fixture, retains the two small wrapper
files, and requires the base command to use the pinned launcher. A different
file is rejected; hash equality is not waived. Wrapper evidence is captured
through an exclusive binary stream so the launcher symlink becomes verified
regular-file bytes; binary-content and conflict regressions cover this case. The original failed receipt
is preserved separately from a prospective validator reconstruction.

All 257 selected pure tests passed, covering the corrected guard, runtime
identity mutations, archive boundaries and existing hold/setup comparators.
No local native calculation was performed. Source recipe, fixture, setup/hold
thresholds, fixed SDC, SRAM placement and all acceptance guards are unchanged.
New cloud native evidence is still required to demonstrate that these repairs
allow the full four-stage diagnostic to finish.

The separate failure-archive workflow will preserve the original 72,449,994-byte
ZIP unchanged, verify all 114 captured members, replay bounded source/control
receipts and publish only after authenticated and anonymous byte roundtrips.
Its source tests passed; publication is not asserted until the cloud receipt
is verified. Neither this archive nor the retry adopts a physical candidate.


The original failed ZIP is now [published and independently verified](evidence/timing-targeted-hold-failure-assets-20261002.json):
cloud archive run 36968700231 checked all 114 members and both public/private
byte roundtrips. Local compact-receipt review replayed original source/control
checks and the unchanged 23,527/113 baseline. This preserves the failure.

[Corrected retry 36968724381](https://github.com/Melihakbulut221/nssoc/actions/runs/36968724381)
runs exact source `ea0d78f4be2f808318508f020b0d81c44ff380c7`. Its
[verified startup capture](evidence/timing-targeted-hold-startup-20261002.json)
now passes the actual native targeted gate, all three runtime identities and
the independent corrected validator; both wrapper captures are regular files.
The 05:25:53 UTC snapshot precedes matched-before export and the repair-begin
marker. The run continues; no reduction or full four-stage completion is yet
claimed.


### 2026-10-02 — targeted hold diagnostic completed; nine violations closed

The corrected [native run 36968724381](https://github.com/Melihakbulut221/nssoc/actions/runs/36968724381)
completed all four stages and passed its full capture validator. The
[compact independent review](evidence/timing-targeted-hold-complete-20261002.json)
checks the 16 exact producer methods, native controls, all four raw global
endpoint tables, target ordering, calls, budget, fixed SDC and unchanged
acceptance policy. Each table contains 23,527 identities, of which 17,145 have
finite timing values; the 6,382 unconstrained identities remain explicit.
Complete export does not mean complete constraint coverage.

| Stage | Hold WNS (ns) | Hold TNS (ns) | Negative endpoints |
| --- | ---: | ---: | ---: |
| Matched before | −1.840965380 | −26.461044911 | 113 |
| Immediately after repair, provisional | −1.091349233 | −12.089680368 | 104 |
| After legalization/routing/RC | −1.078215073 | −11.974233161 | 104 |
| After full timing-cache update | −1.078215073 | −11.974233161 | 104 |

The native repair call took 59.334 seconds; the full native phase including
loading and four exports took 645.056 seconds. All 16 selected endpoints receive
one pass, and instance count increases by 66, from 103,697 to 103,763. Nine
negative endpoints close and no new negative global endpoint appears. Setup
WNS remains −4.909516349 ns, TNS −4320.800144342 ns and violating count 1,384
through every stage. Slew/capacitance violation counts remain 0/1. These are
global-route estimates and a single bounded experiment, not final extracted
timing or a measured whole-flow speedup.

Post-routing tradeoffs are retained: 55 global endpoint minima improve and
59 regress. Of the latter, 58 remain positive; already-negative `eth_tx_en_o`
changes from −0.503306286 to −0.509050246 ns, a 5.743961 ps regression. The
largest regression, 6.019185 ps at `_134889_/D`, remains positive. Before
routing/RC updates there were 24 improvements and no regressions. The two
final raw global endpoint tables are byte-identical, so a further timing-cache
update does not remove these measured regressions.

The historical selected C10 setup WNS is −4.710829 ns. Its 0.198687349 ns gap
from the fresh matched baseline already exists before repair and is unchanged
afterward. This is the failing historical aggregate guard; the historical
manifest has no setup TNS, violating-count or electrical-count values to support
a comparison of those quantities. The matched-before aggregate guard passes,
while the selected-C10 guard and overall estimate acceptance remain false.
No threshold or epsilon is changed to hide that gap or individual regressions.

**No candidate is adopted, and this diagnostic exports no resumable ODB/DEF.**
The next timing work must resolve the historical-versus-fresh setup
reproducibility gap and account for the post-routing endpoint regressions
before selecting a new physical checkpoint. Local review deliberately used
compact members; full physical/all-corner-path replay and durable publication
are performed separately in the cloud. The producer's own full capture
validator already passed, including its 32-SRAM and physical fingerprint checks.


The subsequent [full archive replay and publication](evidence/timing-targeted-hold-complete-assets-20261002.json)
now closes the deferred captured-data checks. Cloud run 36971230497 at
`1c14157656de96986df09e9eb6d41b645b250e98` verifies the original
270,228,757-byte ZIP, all 153 members and 518,785,253 expanded bytes. It fetches
the exact original 16 methods, manifest and two licenses from immutable
`ea0d78f`, runs the original Python validator without an overlay, and rechecks
all source/capture bytes afterward. Full physical inventories, corner/path
exports and endpoint comparisons pass this captured-data replay; no native
calculation is repeated. The original C10 estimate guard remains false.

The unchanged ZIP is publicly archived as
`timing-targeted-hold-complete-20261002.zip`; authenticated and anonymous
roundtrip hashes match. Independent local review uses only its compact
receipt, exact Git sources and fresh release metadata. This establishes
durable, verified diagnostic evidence; it does not supply a resumable physical
checkpoint, qualified RC timing, transistor LVS or manufacturing acceptance.


## 2 October: preserve repair progress across independent native reloads

[Two new isolated repair methods](evidence/timing-closure-method-20261002.json)
are prepared from the same original C10. The combined method applies the
existing 100-iteration setup batch-four recipe, followed by at most four guarded
16-target hold batches. It retains the original setup/hold margins and a
cumulative 40% growth bound. It exports an isolated ODB/DEF even when rejected,
then measures that export in two independent native processes. Original C10
and matched-before guards apply to the reloaded values. Exact replay agreement
does not replace detailed routing, qualified RC, equivalence or physical signoff.
A tiny ODB/SDC child-process control must pass before the expensive setup work.

The second method targets the current worst setup launch cone: `_071517_/X`
drives only `_071519_/A` through net `_017423_`, with 345.06 µm Manhattan
instance-origin separation. A single `sg13g2_buf_2` near the XOR is intended to
unload the long connection. Moving the sink alone would lengthen its two other
short local connections. Actual improvement requires the new routed measurement.
The trial checks the complete original connection graph after contracting only
the inserted non-inverting buffer, including power connections and top ports.

The local three-cell native fixture passes after inserting one buffer: all three
corners are reported, SDC and contracted connectivity are preserved, and missing
API, extra-fanout and repeated-insertion controls reject invalid changes. This
is a tiny fixture result; no new chip timing improvement has yet been measured.
All full chip calculations remain on GitHub. Rejected outputs are retained and
never automatically replace the selected checkpoint.


## 2 October: first targeted physical buffer result and next measured target

[Run 36990647399](https://github.com/Melihakbulut221/nssoc/actions/runs/36990647399)
completed at exact source `945881e8bd9854419f1f3066039c380658693a81`.
Native execution took 585.22 seconds. The one inserted `sg13g2_buf_2` preserves
the entire original graph after contraction, including power connections.
All 32 SRAM placements and constraints are unchanged. The
[independent compact review](evidence/timing-xor-buffer-native-20261002.json)
verifies 21 original source files, native controls, 131 selected capture members,
and the complete 23,527-endpoint population at each of three corners per stage.
Full geometry replay and independent candidate ODB/DEF reload are still separate.

| Measured quantity | Matched original C10 | After one buffer and routing |
| --- | ---: | ---: |
| Setup violating endpoints | 1,384 | 1,378 |
| Setup WNS, ns | −4.909516349 | −4.744947546 |
| Setup TNS, ns | −4320.800144342 | −4144.873855694 |
| Hold violating endpoints | 113 | 113 |
| Hold WNS, ns | −1.840965380 | −1.840965380 |
| Hold TNS, ns | −26.461044911 | −26.461044911 |
| Slew / capacitance violations | 0 / 1 | 0 / 1 |

The final explicit timing-cache update changes neither these aggregates nor
the full hold path/endpoint values. Relative to the matched fresh baseline the
aggregate no-regression guard passes, but historical C10 setup/hold guards remain
unmet. This is measured progress, not an accepted checkpoint or timing closure.
The rejected candidate's ODB, DEF, netlist and SDC are retained in the original
cloud artifact with hashes; the large database/DEF bytes were not downloaded
or reloaded locally.

The critical path moves from RF x24 bit25 to RF x11 bit27 (`_134050_`), which
starts seven of the ten reported worst core-clock paths. The next fixed
experiment keeps the proved first buffer and targets `_070589_/Y` on
`_016495_`. This XNOR drives exactly `_070602_/A2` and `_072894_/A1`, whose
origins are 319.56 and 302.88 µm away. Its reported load is 0.068221621 pF.
A second nearby buffer must preserve both sinks and contract back to the same
original graph. Other startpoints already reach −4.717023 ns, so this next
target alone is not guaranteed to satisfy the historical −4.710829 ns guard.

The [two-buffer method](evidence/timing-xor-pair-method-20261002.json) is now
implemented independently of the frozen first producer. It starts from original
C10, measures the first buffer before inserting the second, and retains four
complete stages. Its tiny native fixture passes from seven to nine cells,
including both exact sink sets, graph contraction, power and three corners.
Missing/wrong/extra sinks, invalid supply links and repeated insertion reject.
The root's 91 adjacent source tests pass. Actual two-buffer chip timing remains
pending; neither the fixture nor the method receipt predicts acceptance.

An [independent cloud ECO proof method](evidence/timing-eco-logic-method-20261002.json)
will first replay the complete original single-buffer capture using its own
Git-verified producer validator. It then compares original C10 with the exported
netlist using the existing retained-input/state and combinational-clone equation
checker. Actual standard-cell Liberty and unchanged SRAM port declarations are
pinned inputs. The checker now accepts opaque macro Verilog interfaces as well
as Liberty interfaces; its equation proof engine is unchanged. Tiny native
controls accept a positive buffer and reject changed macro inputs or unknown
pins; 78 source tests pass. This proof cannot establish SRAM internal behavior,
analog operation, CDC, timing, extracted connectivity or physical acceptance.


### First buffer: independent digital-core equation proof completed

[Run 36994331741](https://github.com/Melihakbulut221/nssoc/actions/runs/36994331741)
at `4290c9f89b941f3c9475d7a2bfe66f5617897c01` passes the limited digital-core
proof after independently replaying all 144 files of the original immutable
capture in the cloud. The original 21 producer methods match their exact Git
source before their validator runs. The [native proof receipt](evidence/timing-eco-logic-native-20261002.json)
records the separately verified runtime, original C10 and candidate netlists,
standard-cell Liberty, SRAM port declarations and three native controls.

The proof retains 75,750 cell equations; positive buffers increase from 23,234
to 23,235 and 4,713 tie cells remain unchanged. These totals reconcile exactly
to 103,697 and 103,698 netlist cells. There are no resizing, input permutation,
clone or disconnected-output changes. All 32 opaque SRAM instance interfaces
retain their input equations. The whole cloud step takes 66 seconds; the two
Yosys elaborations peak at about 891 and 883 MB.

Independent compact review and root rechecking cover 31 selected output hashes,
eight proof-source Git identities, return codes and the reconciled counts.
No full netlist equation calculation or full ZIP download ran locally. This
establishes only the stated mapped digital-core contract: SRAM interiors,
padframe, analog behavior, initialization, CDC, timing, physical connectivity
and manufacturing approval remain outside the proof. It does not override the
failed historical timing guards or adopt the candidate.


### Two-buffer result: reproducible first improvement, smaller second gain

[Run 36993662400](https://github.com/Melihakbulut221/nssoc/actions/runs/36993662400)
at `2df6aff4479c5b8bd05c327391e309c71b34d600` completes native execution in
900.09 seconds. The [independent review](evidence/timing-xor-pair-native-20261002.json)
verifies 26 exact method sources, 146 selected captured files, complete graph
contraction and all 23,527 endpoint values across three corners and four stages.
Root independently repeats these compact checks. The original baseline and
first-buffer graph and metrics exactly reproduce the earlier single-buffer run.

| Quantity | Matched C10 | First buffer | Both buffers |
| --- | ---: | ---: | ---: |
| Setup violating endpoints | 1,384 | 1,378 | 1,376 |
| Setup WNS, ns | −4.909516349 | −4.744947546 | −4.721119495 |
| Setup TNS, ns | −4320.800144342 | −4144.873855694 | −4120.158337173 |
| Hold violating endpoints | 113 | 113 | 113 |

All hold endpoint/corner values remain unchanged, as do the 32 SRAM placements
and SDC. The explicit timing-cache update changes no metric. The matched fresh
no-regression check passes, but the original historical setup/hold guards still
fail; the rejected candidate is retained and not adopted. This review did not
download the full 326 MB ZIP, candidate database or DEF, or repeat their native
routing locally.

The new worst path starts at RF x30 bit12 (`_133935_`); a measured 317.22 µm
single-sink XNOR connection `_072567_/Y` to `_072570_/A` has a 0.850183 ns
reported arc. A separate path from `_132612_` remains at −4.717023 ns and has
a 320.76 µm single-sink NAND4 connection `_074829_/Y` to `_074831_/B`, whose
reported arc is 1.057705 ns. These are the next two bounded buffering targets;
their observed delays are not predictions of attainable timing improvement.


The [four-buffer method](evidence/timing-xor-four-method-20261002.json) now replays
the two verified targets before adding the RF30 and NAND4 buffers, each with
its own timing snapshot. All six stages retain complete hold endpoint/corner
reports. Exact four-buffer graph contraction includes every original cell,
port, signal and supply connection, and all 32 SRAM placements remain fixed.
The original two-buffer producer's 26 source files are unchanged. A real tiny
13-to-17-cell native control passes with missing, wrong and extra sinks tested
for all four target connections; 108 adjacent source tests pass. Actual chip
measurements are still required; neither historical guards nor adoption
requirements are relaxed.


### Current-profile PMP comparator candidate: complete binary-output proof

The two-buffer critical path still traverses approximately 4.318 ns of ALU
carry/sum logic and 4.726 ns of PMP comparison logic; these measured path sections
motivate parallel arithmetic experiments beyond local buffering. Their full
routed timing benefit has not yet been measured.

The [PMP experiment](evidence/pmp-prefix-current-20261002.json) changes only the
two unsigned greater-than/less-than expressions in the exact C10 generated PMP
source. A balanced most-significant-difference reduction replaces their serial
mapping opportunity. Every remaining source byte is preserved by reversible
transformation. Address masks, permissions, region priority and the existing
pipeline configuration are unchanged; default generated RTL is not overwritten.

A fresh native Yosys all-output combinational miter passes for every binary input
with the current granularity=0, four regions and **three** channels. No internal
name correspondence or input assumptions are used. The wrong-comparison negative
control fails as required. Eighteen tests include real HDL comparison controls
at seven widths, unsigned high-bit and equality boundaries, corrupted source
and prepared-input rejection. The [complete small evidence archive](evidence/pmp-prefix-current-20261002.tar.xz)
retains original/candidate/negative source, scripts and both raw proof logs.
This proves the stated functional transformation; it does not cover four-state
X propagation, other PMP configurations, mapped timing or physical acceptance.

The completed one-buffer, two-buffer, digital-core proof and parent-marker
artifacts are now [permanently archived](evidence/closure-archives-native-20261002.json).
Cloud publication verifies each unchanged original ZIP and both authenticated
and anonymous release downloads. These archives preserve failures and rejected
candidates as recorded; publication does not convert them into accepted results.


### Current-profile ALU experiment queued for real synthesis

The [critical-path source mapping](evidence/critical-path-prefix-analysis-20261002.json)
locates the persistent serial carry and PMP suffix in both measured critical
paths. The [ALU method](evidence/alu-prefix-c10-method-20261002.json) packages the
exact original C10 synthesis recipe and 99 source/license members in a 627,080-byte
snapshot. Forty-seven current tracked inputs match the receipt; generated inputs
also remain bound to the original C10 source hashes. CORE_REQ_REG, CORE_WB_STAGE,
SYNPRE, MEM_RDREG, REQ_REG and WAKE_GNT stay enabled, with ECC, PMP, all interfaces
and both memory-test integrations retained.

Cloud execution first proves every original-versus-prefix ALU output and rejects
a wrong-sum mutation. Only then does it run the original pinned Yosys 0.67+146
recipe on the relocated baseline. The emitted netlist must reproduce the C10
synthesis hash before the candidate is synthesized. A path-related or other
baseline byte mismatch is preserved for diagnosis and cannot silently pass.
Thirty-three source/recipe/proof-failure tests pass. The current candidate changes
only the 33-bit addition and introduces no state or latency; default RTL remains
unchanged. The earlier RTL-to-mapped unique-case counterexample is retained as a
separate qualification issue. Fresh boot/MBIST, mapped correspondence, memory
mapping, physical layout and all-corner timing remain required after synthesis.


### Four buffers measured: local buffering reaches diminishing returns

[Run 36997063834](https://github.com/Melihakbulut221/nssoc/actions/runs/36997063834)
completes the [four-buffer experiment](evidence/timing-xor-four-native-20261002.json).
Root and an independent review verify all 31 methods, the full contracted
connection graph, unchanged 32 SRAM placements and every hold endpoint/corner
value across six stages. The original baseline and first two insertions reproduce
the earlier experiments exactly.

| Quantity | Two buffers | Three buffers | Four buffers |
| --- | ---: | ---: | ---: |
| Setup violating endpoints | 1,376 | 1,376 | 1,376 |
| Setup WNS, ns | −4.721119495 | −4.717023216 | −4.716302016 |
| Setup TNS, ns | −4120.158337173 | −4115.444880881 | −4113.288468943 |
| Hold violating endpoints | 113 | 113 | 113 |

The last two insertions gain only 4.817 ps of worst setup slack and close no
additional endpoint. Hold values remain unchanged, with zero slew and one
capacitance violation. The explicit full timing update repeats the fourth-stage
metrics. The original C10 acceptance guard still fails, and the exported
candidate remains rejected. Compact review does not repeat physical extraction
or download the complete 469,941,582-byte artifact.

The new worst path starts at RF x1 bit1 (`_133476_`) and ends at `_132609_`;
the top ten reports share that startpoint. Its next long connection alone is
not sufficient justification for another buffer-only experiment. The parallel
ALU and PMP candidates target the shared logical delay instead.


### Current-profile ALU proof and exact baseline synthesis completed

[Run 36998734236](https://github.com/Melihakbulut221/nssoc/actions/runs/36998734236)
passes the [fresh all-output proof and matched synthesis](evidence/alu-prefix-c10-native-20261002.json).
The wrong-sum negative produces a real counterexample. The relocated original
recipe reproduces the C10 synthesis netlist byte-for-byte; only then is the
parallel-adder candidate synthesized. Both native synthesis runs report zero
structural problems. Root repeats the compact source, input, recipe and proof
log review independently, including all 99 snapshot members and 47 tracked
source pins.

| Synthesis quantity | Original | Parallel adder |
| --- | ---: | ---: |
| Mapped cells | 74,077 | 74,544 |
| Known-cell area, µm² | 1,128,717.828 | 1,133,966.812 |
| DFF cells | 10,009 | 10,009 |
| Clock-gating cells | 3 | 3 |
| Abstract SRAM instances before physical replacement | 20 | 20 |

Known-cell area rises 0.465%; this excludes unknown macro areas and is not total
physical die area. Original and candidate synthesis take 188.55 and 196.54
seconds, respectively. The 20 abstract memories require the established
replacement into 32 physical SRAM macros; that transformation has not yet been
verified for this candidate. Current-profile mapped correspondence, full boot
and MBIST, memory replacement, fresh layout and all-corner timing remain
required. No timing benefit or accepted candidate is claimed from synthesis.


The complete four-buffer and ALU synthesis artifacts are also
[permanently archived and roundtrip verified](evidence/closure-archives-second-native-20261002.json).
This retains the 469.9 MB rejected physical candidate and the 11.0 MB matched
synthesis/proof output unchanged; archive publication adds no timing acceptance.


### Mapped PMP candidate: unconstrained proofs and three-corner block timing

The [bounded isolated PMP experiment](evidence/pmp-prefix-mapped-20261002.json)
passes three independent all-output comparisons: original RTL to its mapped
netlist, candidate RTL to its mapped netlist, and mapped original to mapped
candidate. Each covers every binary assignment to all 278 input bits; no
internal cutpoints or input assumptions are used. The deliberately wrong
comparison produces retained JSON/VCD counterexamples. All three output ports
are timed independently at typical, slow and fast corners.

| Isolated zero-wire quantity | Original | Parallel comparator |
| --- | ---: | ---: |
| Mapped cells | 3,697 | 3,942 |
| Library cell area, µm² | 35,618.6376 | 37,278.7002 |
| Slow worst arrival, ns | 4.973281860 | 4.824049473 |

Worst arrival improves by 106.175 ps at typical, 149.232 ps at slow and
70.862 ps at fast, with a 4.66% block-area increase. These measurements use
identical 20 ns virtual clock, input driving cell, output load and 5% derates,
with **zero wire parasitics**. They do not establish routed setup or hold gain.
The mapper is pinned AppImage Yosys 0.62; exact whole-C10 synthesis remains a
separate step using its original 0.67+146 runtime. Default RTL is unchanged.

Two independent reviews verify all 33 input/generated pins, 38 output files,
three proof logs, the negative counterexample and all six native STA logs.
Root repeats the source/output hashing and report parsing. Forty-four focused
tests and Ruff pass. The [complete small native capsule](evidence/pmp-prefix-mapped-20261002.tar.xz)
preserves generated netlists, raw reports, methods and upstream notices. An
earlier report-parser failure remains recorded; the final method reran all
proofs and six timing cases successfully. Full-SoC correspondence, physical
placement, extracted RC and all-corner closure remain required.


### Actual mapped boot and memory replacement gate prepared

The [qualification method](evidence/alu-qualification-method-20261002.json)
consumes the exact permanently archived pair of completed synthesis outputs;
it does not synthesize again. The original 20-to-32 SRAM replacement must
reproduce its historical byte hash before candidate replacement proceeds.
Every retained nonmemory cell pin equation and external port remains checked,
alongside the exact 16 SP and 16 DP physical memory instance identities.

Four separate native jobs cover original/candidate cores with vendor/independent
behavioral SRAM models. They use the actual 3120-byte C10 loader, regenerated
ROM identity and unchanged firmware flash. The obsolete earlier 3084-byte
loader is rejected. Native cell compatibility and full compilation must pass
before the startup artifact is published; only then does simulation begin.
The test requires successful system and Ethernet power-on MBIST plus all
28 firmware checks. A 3,000,000-cycle functional bound accommodates the
983,048-cycle MBIST; the 20 ns system and 8 ns Ethernet clocks are unchanged.
No ROM/RAM preload or elapsed native watchdog is introduced. Flushed cycle
markers appear live and immutable log-prefix receipts preserve progress.

Root and independent source review pass 68 focused tests, Ruff and Actionlint.
This prepares real simulation; no native map/boot success is inferred from
source tests. Original/candidate mapped equivalence remains a separate gate,
and fresh geometry must start from the new netlist after qualification.


### Independent mapped-state proof gate

The [mapped-state method](evidence/alu-mapped-state-method-20261002.json)
compares the archived full original/candidate netlists without resynthesis.
It exposes only actual storage: 10,009 reset FFs, three clock-gate latches, and
20 opaque SRAMs. Every mapped combinational cell remains in the proof. All
34,321 external-output, FF data/clock/reset, gate enable/clock/latch-next and
memory-input equations must agree for every shared binary assignment.

Public Q aliases propose 9,892 state correspondences; 117 anonymous FF pairs
are only an untrusted ordering proposal until their complete equations pass.
Clock-gate state and output equations are checked against the exact pinned
Liberty latch table. No named combinational cutpoint is assumed equal.
Twenty-seven pure tests and five tiny native controls pass: the equal case
proves, while wrong state pairing, reset, output and gate-latch mutations each
produce a real counterexample. Root rechecks all source and tiny output pins.

The full native proof is still required on GitHub. A pass would establish
binary next-state correspondence under equal corresponding initial states
and identical SRAM contracts; reset reachability, four-state behavior, clock
domain crossing, memory interiors and physical acceptance remain separate.
A failed or timed-out proof preserves its actual outcome and cannot pass this
gate or be replaced by the narrower buffer-only ECO checker.


[Run 37002748526](https://github.com/Melihakbulut221/nssoc/actions/runs/37002748526)
now passes the [actual memory replacement and all four native compile gates](evidence/alu-qualification-startup-native-20261002.json).
Original replacement reproduces its exact hash; the candidate retains all
74,524 pre-existing nonmemory cells, their pin equations and 79 external ports,
with the required 32 physical SRAM identities. Native cell compatibility and
actual complete-core compilation succeed in all four cases. Root repeats the
110-member compact source, recipe, model, firmware and log checks. The eight
identical IHP specify warnings about unsupported edge-sensitive `ifnone` paths
are retained; the real functional reset/capture/hold control passes, while
SDF/timing-model qualification is outside these tests.

The four boot/MBIST simulations are running. Startup success is not a completed
boot result. Their flushed progress is preserved by the producer, but available
read-only APIs do not expose unfinished job logs; no throughput or completion
estimate is inferred from elapsed time. Mapped equivalence and fresh physical
timing remain independent gates.


### Registered acknowledgement candidate: actual-core contract still required

The measured critical path continues from the PMP result through the request
grant, LSU completion and ID/RF next-address logic; that final section contributes
6.596 ns in the retained path report. The current request queue captures the
payload in a register but returns its upstream grant combinationally from the
permission-qualified request. An [isolated acknowledgement-register
experiment](evidence/core-ack-candidate-method-20261002.json) cuts this feedback
at the cost of one additional acknowledgement and downstream-request cycle.
The helper transforms the exact C10 request-pipe source reversibly; default
RTL and all 81 pinned C10 source inputs remain unchanged.

The actual candidate module passes a held-request, stalled-downstream and
common-reset simulation. Six negative controls reject withdrawn request,
changed payload, changed permission, unsolicited grant, premature downstream
exposure and corrupted payload. Root repeats all 22 focused tests, checks the
source and raw output hashes independently, and retains the native log text.
These are finite module-contract controls, **not proof of actual Ibex behavior**.

Before adoption, the actual core must demonstrate stable permission-approved
requests through delayed acknowledgement, precise split-transfer and error
handling, load-use and writeback hazards, clock-gating/interrupt behavior, and
common-reset cancellation. The existing immediate-grant request-pipe proof
does not establish this narrower contract. No timing improvement, sequential
equivalence or full-core qualification is claimed for this candidate yet.


### Combined physical repair completed; electrical regression prevents adoption

[Run 36990647336](https://github.com/Melihakbulut221/nssoc/actions/runs/36990647336)
finishes normally after 7,905.65 seconds of native execution. The
[verified result](evidence/timing-combined-repair-native-20261002.json) retains
the original 100-iteration setup batch and four guarded hold batches. Two fresh
native processes reload the exported ODB/SDC and agree exactly on all metrics,
fingerprints and 70,581 endpoint/corner records. Root independently repeats the
compact review of 123 selected files, 21 methods and unchanged acceptance guards;
large physical views and full endpoint validation are verified in the producer,
not recomputed locally.

| Estimated GRT quantity | Matched C10 baseline | Fresh repaired reload |
| --- | ---: | ---: |
| Setup violating endpoints | 1,384 | 1,311 |
| Setup WNS, ns | −4.909516349 | −4.209004700 |
| Setup TNS, ns | −4320.800144342 | −3554.924433047 |
| Hold violating endpoints | 113 | 66 |
| Hold WNS, ns | −1.840965380 | −0.155300439 |
| Hold TNS, ns | −26.461044911 | −2.117501507 |
| Slew / capacitance violations | 0 / 1 | 2 / 3 |
| Instances | 103,697 | 103,889 |

All 32 SRAM placements remain unchanged. The pre-export in-memory state had
57 hold endpoints and zero slew violations; independent rerouting changes the
parasitic estimates and exposes 66 hold endpoints and two slew violations.
Netlist, placement and SDC remain identical across this transition. The two
fresh reloads agree with each other, so the fresh values govern this candidate.

The historical selected-C10 guard passes, but the matched-baseline guard fails
on electrical regression. `fanout1387/X` and `fanout1391/X` exceed both slew and
capacitance limits; `fanout1228/X` also exceeds capacitance. Consequently the
aggregate guard rejects the candidate despite setup and hold improvements.
The exported state supports a separate electrical-repair continuation with an
exactly reproduced baseline; the original C10 remains selected. Detailed-route
RC, zero-violation timing, physical verification and adoption are still open.

The [full rejected candidate archive](evidence/closure-combined-archive-native-20261002.json)
is permanently published with its original 329,082,361 bytes, SHA-256 and both
authenticated and anonymous download roundtrips verified. Publication preserves
the measured failure and does not promote the candidate.


### Full mapped ALU state relation failed; counterexample preserved

[Run 37003975081](https://github.com/Melihakbulut221/nssoc/actions/runs/37003975081)
completes both native frontends and reaches the full binary equivalence check.
It [finds a real counterexample](evidence/alu-mapped-state-failure-20261002.json)
after 252.39 seconds. Root independently verifies the source pins, compact logs,
failed result and all 10,828 binary input/state bits in the counterexample.
This is a failed proof, not a missing tool, skipped check or resource timeout.

The proposed relation contains 9,892 anchored and 117 anonymously paired FFs;
the latter pairing was explicitly untrusted pending proof. The first miter
exposes an aggregate mismatch only, so this result does not yet distinguish
incorrect state pairing from a genuine mapped-logic difference. A separate
replay will expose every original/candidate boundary output for the exact saved
assignment. It will retain the failed unconstrained proof and introduce no new
internal-state assumptions. ALU adoption remains blocked, independently of the
four still-running boot/MBIST simulations and physical timing qualification.

The [original failed artifact](evidence/closure-alu-state-failure-archive-native-20261002.json)
is now permanently archived, including both large lifted graphs and the exact
counterexample. Its archival plan explicitly requires the producer's failure;
successful publication cannot convert that proof outcome into a pass.
The [separate replay method](evidence/alu-state-replay-method-20261002.json)
downloads these same pinned bytes and reports every compared boundary bit for
the saved assignment. Its actual tiny native control finds all seven injected
differences; 52 focused tests pass. This diagnostic fixes inputs solely to locate
the known counterexample and cannot establish equivalence.


### Actual-core acknowledgement experiment ready for native execution

The [directed actual-core harness](evidence/core-ack-protocol-method-20261002.json)
restores all 81 sources from the exact C10 archive and embeds the original
`soc_top` Ibex instance verbatim. It uses the current SECDED register file,
writeback stage, branch-target ALU, LSU, PMP and actual core clock-enable logic.
All 47 tracked inputs and any existing generated checkout files are cross-checked;
a clean checkout does not regenerate Ibex or change the source profile.

Five positive cases cover the original queue, registered acknowledgement, and
three common-reset placements. Firmware checks aligned and split data accesses,
load-use/branch dependencies, eight first/second-beat PMP or bus faults with
exact trap cause/address/PC, and WFI/software-interrupt wakeup. Observers check
held requests, token/response ownership, real clock edges at acknowledgement and
six actual stopped-clock intervals. Four deliberate mutations test unsolicited
grant, early downstream exposure, corrupted payload and a stuck-open clock gate.
The last check was added after peer review found that a sleep Boolean alone
did not establish clock stoppage.

Preparation, firmware assembly/linking and 55 focused tests pass. Root verifies
the source/prepared-file pins and independently runs the new tests. Native Ibex
execution is delegated to the new cloud workflow. The external memories are
explicit protocol models; full SoC fabric, SRAM/MBIST, exhaustive exception
interleavings and physical timing remain separate gates. No core-level or
product acceptance follows from preparing this harness.


### Three-net electrical continuation prepared from the saved physical candidate

The [electrical continuation](evidence/timing-electrical-method-20261002.json)
starts from the exact archived combined-repair ODB/SDC. It first replays that
producer's complete source-bound validator and reproduces all five physical
fingerprints and the fresh 1311/66 setup/hold baseline. The original C10 state
remains unchanged; no new 100-iteration setup batch is needed.

The full candidate netlist member is CRC/SHA verified through a ranged read.
The actual three driver connections are `fanout1387/X→net1387` and
`fanout1391/X→net1391` (eight SRAM data loads each), and
`fanout1228/X→net1228` (four SRAM data loads plus a buffer input). The pinned
OpenROAD revision exposes a native single-net repair API, confirmed against its
implementation and upstream test. A real four-cell IHP control passes, reduces
total capacitance violations from two to one, preserves the unrelated driver
and constraints, and rejects wrong/protected/missing targets and a missing API.
The remaining unrelated fixture violation is not represented as closure.

The cloud experiment calls that API only for the three observed nets, preserves
protected/clock objects and all 32 SRAM placements, exports the result, and
performs two independent native reloads. Historical C10, matched C10 and the
starting candidate all remain acceptance references. Original-to-parent and
parent-to-electrical retained-state/logic equation checks are mandatory; their
limited scope does not establish transistor LVS or SRAM internals. All-corner
zero violations and detailed-route signoff remain required after this experiment.


### Mapped counterexample localized to QSPI state correspondence

[Run 37006276805](https://github.com/Melihakbulut221/nssoc/actions/runs/37006276805)
[reproduces the saved counterexample](evidence/alu-state-replay-native-20261002.json)
and exposes all compared boundaries. Root verifies the complete compact artifact,
all ten Git method blobs, all 10,828 fixed input bits and every one of the 34,321
output comparisons. Exactly 14 next-state D bits differ, all in QSPI logic.
For this assignment, external outputs, SRAM inputs, FF clocks/resets and
clock-gate boundary functions agree.

The anonymous FF proposal crossed unrelated QSPI, UART and CAN state cells.
A corrected correspondence is being checked against the exact cell identities
before a fresh unconstrained proof. Matching one saved assignment, or locating
the pairing defect, cannot establish equivalence. The original failed proof and
all candidate-adoption restrictions remain unchanged.

### Corrected state correspondence and actual-core compiler retry

The [new unconstrained proof method](evidence/alu-state-repair-method-20261002.json)
corrects exactly three anonymous FF pairings, at indices 9982, 9983 and 9988.
Exact cell identities and independent QSPI, CAN and UART fanout witnesses bind
the proposal to the original mapped netlists. All 10,828 symbolic input bits and
34,321 compared boundary bits remain; no counterexample input is fixed. The
original failed proof and its method remain unchanged. Actual small native
controls reject the wrong permutation and a wrong reset, and prove the corrected
permutation. The full chip proof is a separate cloud run, still required before
ALU adoption.

The first actual-core run failed before RTL compilation because Ubuntu's GCC
10.2 rejects the newer `_zicsr` spelling. The
[compiler correction](evidence/core-ack-compiler-fix-20261002.json) passes ISA 2.2
directly to the assembler and checks the exact CSR, WFI and MRET opcodes before
compiling firmware. Local linking produces the same 4,228 firmware bytes; the
actual Ibex instance, testbench and firmware source are unchanged. The rerun must
still pass on the cloud compiler and execute every directed protocol case.
Root independently passes 125 focused tests and both workflow/source linters.
Neither preparation result establishes timing closure, transistor LVS or
manufacturing approval.

### Actual-core finite test result and alert-observer correction

[Run 37009833138](https://github.com/Melihakbulut221/nssoc/actions/runs/37009833138)
executes five positive and four deliberate negative cases. Both independent
reviews verify the complete 2.5 MB artifact, all 71 result files, 87 prepared
files and eight Git-bound methods. The original and candidate complete the
directed program in 807 and 839 cycles, respectively, and produce the same
2,048-word architectural memory signature. Reset cancellation, eight precise
faults and six stopped-clock intervals are observed.

The [raw result and correction](evidence/core-ack-observer-fix-20261002.json)
also preserve a real testbench defect discovered in the compile logs: its
one-bit wire truncated the actual three-bit register-file ECC alert output.
This result cannot qualify the corrected observer. The wire now retains all
three bits; four small native controls accept zero and reject each individual
error bit. A new compile gate rejects port-width warnings and records all six
compilation results. Root passes 56 focused tests, including these controls;
the complete actual-core cloud workload must run again before the next gate.
Default RTL and directed firmware remain unchanged.

The earlier compiler failure and fixed-assignment ALU diagnostic are now
[permanently archived](evidence/closure-replay-ack-archives-native-20261002.json),
with both original outcomes and exact bytes preserved. Successful archival
does not alter either engineering result.

### Electrical repair closes slew but fresh capacitance and timing guards fail

[Run 37007664485](https://github.com/Melihakbulut221/nssoc/actions/runs/37007664485)
finishes in 1,530 seconds. The
[independently reviewed result](evidence/timing-electrical-first-native-20261002.json)
preserves all 32 SRAM placements, adds three positive buffers and passes both
limited digital equation checks: original C10 to combined candidate, then
combined candidate to this electrical candidate. These checks exclude physical
connectivity and SRAM interiors.

Both fresh native reloads agree: setup 1,312, hold 65, setup WNS −4.255417 ns,
hold WNS −0.158980 ns, slew zero and capacitance three. Their fingerprints and
all 70,581 exported endpoint/corner records agree. In-memory zero capacitance
violations therefore did not survive new routing and parasitic estimation.
The candidate is rejected: capacitance still exceeds matched C10, and several
setup/hold metrics regress against the combined candidate.

Fresh capacitance is 0.329943 pF at `fanout1387/X`, 0.309706 pF at
`fanout1391/X`, and 0.309938 pF at the previously untargeted `fanout1593/X`,
against a 0.300000 pF limit. These are original drivers; the three inserted
buffers are not the violating pins. `fanout1228` is no longer violated.
The next isolated continuation will start from these saved candidate bytes and
target the measured remaining nets. A tighter repair target is experimental
headroom, not proof of a bound on routing-estimation error: `fanout1387` rose
from approximately 0.145 pF incrementally to 0.330 pF after fresh routing.
Every original acceptance guard and the fresh reload checks remain required.

### Full-width actual-core replay passed; measured-net continuation prepared

[Run 37012329552](https://github.com/Melihakbulut221/nssoc/actions/runs/37012329552)
passes the [corrected finite actual-core workload](evidence/core-ack-full-width-native-20261002.json).
All six compile logs are empty, the full three-bit ECC alert is observed, and
all five positive/four negative cases retain the expected verdicts. Root
independently rehashes the complete artifact and every result/preparation/source
pin, replays coverage parsing, and checks all architectural signatures. The
cloud firmware is byte-identical to the preceding cloud run; a different local
compiler's binary hash is kept distinct. This closes this finite test gate,
while exhaustive refinement, full-SoC boot and physical timing remain required.

The [next electrical method](evidence/timing-electrical-margin-method-20261002.json)
uses the three remaining measured drivers with 20% tighter repair targets. It
verifies their complete 19-terminal graph, including the actual antenna input,
and reproduces the saved candidate in two native processes before mutation.
Two final reloads and both limited logic proofs remain mandatory. Four original
references are preserved: historical C10, matched C10, the combined candidate
and the electrical candidate. Clearing capacitance alone cannot conceal an
existing setup/hold regression. A real tiny native control and 140 independently
repeated focused tests pass; full-chip execution remains a cloud experiment.

The first electrical result and the earlier narrow-observer result are now
[permanently archived](evidence/closure-electrical-observer-archives-native-20261002.json)
with their limitations and rejection decisions unchanged.

### Exact C10 request-ack qualification and complete ALU proof continuation

The corrected actual-core protocol result is now
[permanently archived](evidence/closure-core-ack-full-width-archive-native-20261002.json).
The [request-ack qualification method](evidence/core-ack-qualification-method-20261002.json)
requires those exact bytes and all nine directed outcomes before synthesis.
It restores the original 81 C10 sources, changes only the isolated request-pipe
candidate, and requires byte reproduction of original synthesis and 32-SRAM
mapping. Four independent full-SoC boots then compare original/candidate with
vendor/independent SRAM models, the unchanged loader, power-on MBIST and all
28 firmware checks. Clock periods and the three-million-cycle bound remain
unchanged. This is finite workload qualification; the extra acknowledgement
cycle still requires architectural and physical review before adoption.
Root and peer independently pass 100 focused source/receipt/worker controls;
no full-core simulation or synthesis was executed locally for this change.

The corrected ALU boundary proof in
[run 37009833162](https://github.com/Melihakbulut221/nssoc/actions/runs/37009833162)
[times out](evidence/alu-state-repair-timeout-native-20261002.json).
The native SAT solver reaches its 1,800-second bound, with 1,353,890 variables
and 3,486,072 clauses. It reports neither a proof nor a new counterexample.
All 10,828 inputs remain symbolic and all 34,321 output obligations are present;
the three corrected state pairings retain all 10,009 original/candidate state
identities. Root verifies 33 captured compact outputs and eleven Git-bound
methods. The final post-proof input recheck was not reached and the large graph
was not downloaded locally. The complete failed artifact will be preserved
without changing its verdict.

The next proof implementation partitions every original output obligation
exactly once while retaining its unconstrained combinational dependencies.
No internal matching assumption or omitted output can count as closure. Until
all groups pass, the ALU physical experiment and default RTL adoption remain
gated. The selected C10 layout and open transistor LVS findings are unchanged.

### Request-ack synthesis reproduced; both original ALU boot cases passed

[Run 37016005414](https://github.com/Melihakbulut221/nssoc/actions/runs/37016005414)
passes the corrected actual-core prerequisite, exact original synthesis and
32-SRAM mapping gates. The
[four compact startup artifacts](evidence/core-ack-qualification-startup-native-20261002.json)
carry identical synthesis/mapping receipts. Original netlists reproduce the
expected bytes; the request-ack candidate has synthesis hash `a0f6f4b0…` and
mapped hash `f476fb89…`. All four native-cell and compile gates pass. Root
independently hashes every compact ZIP, its 40 outputs and 23 Git-bound methods.
The large mapping artifact was verified by its producer and was not downloaded
or fully replayed locally. Four boot workers have started; these startup
artifacts do not establish any completed boot or timing result.

In the separate ALU qualification run, both original-design cases now pass:
[vendor SRAM](evidence/alu-qualification-original-vendor-native-20261002.json)
and [independent SRAM](evidence/alu-qualification-original-independent-native-20261002.json).
Each records power-on MBIST at cycle 983,043 and finishes at cycle 1,596,123,
with all 28 checks passing, zero failure mask, the required watchdog result,
no flash violations and a valid UART pass message. Root independently verifies
both complete compact artifacts and every result/method pin. The native-library
warnings concern unsupported timing-path constructs in functional, no-SDF
simulation; this is not cell timing validation. Both ALU candidate results are
still pending at this observation.

The failed monolithic proof is also
[permanently archived](evidence/closure-alu-state-timeout-archive-native-20261002.json)
with its timeout and missing proof verdict preserved.

### Exact native graph spelling repaired; complete parallel ALU proof prepared

The first margin experiment
[stopped before mutation](evidence/timing-electrical-margin-first-native-20261002.json).
Both native baseline processes reproduced setup 1,312, hold 65, zero slew and
three capacitance violations with all five physical fingerprints identical.
The exact graph guard then rejected the spelling of four SRAM bank instances:
OpenDB retains a literal backslash before each bracket, while the source
Verilog identifier does not. No repair call ran and no new candidate exists.

The [representation correction](evidence/timing-electrical-margin-name-fix-method-20261002.json)
retains both spellings, binds the native names to the captured placement, and
compares all 19 native terminal rows exactly. It does not strip characters from
observed names. A real four-cell OpenROAD fixture accepts the native escaped
name and rejects the unescaped name, wrong pin and omitted terminal before
mutation. A separate query of the exact C10 SRAM LEF confirms that `d[21]`,
`d[23]` and `d[15]` themselves remain literal, unescaped INPUT/SIGNAL pin names.
Root verifies 129 compact failed-run captures, the immutable producer methods,
the native control evidence and 155 focused tests. The retry retains both
pre-repair baselines, all four rejection guards, both final independent reloads
and both limited digital ECO proofs.

The [complete partitioned ALU method](evidence/alu-state-partitions-method-20261002.json)
builds one optimized miter and distributes 269 output groups over four workers.
It covers every one of the original 34,321 output bits exactly once, with all
10,828 original input/state bits symbolic. Each group starts from the same
immutable graph; pruning removes only unobserved output cones. No internal
cutpoint or assumed equality is introduced. Acceptance reparses all raw native
verdicts and requires every group to pass. Tiny positive, wrong-output and
wrong-clock cases verify actual native proof behavior, continuation after a
counterexample, and rejection of missing/duplicate group evidence. Root and
independent review pass 105 focused tests. Full-chip proof remains a separate
cloud execution; timeout or partial coverage is explicitly unproved.

The [first partition preparation](evidence/alu-state-partition-preparation-failure-20261002.json)
stops before native miter construction. Its direct Python comparison of the
corrected proposal rejects integer dictionary keys after JSON has serialized
them as strings. The [corrected preparation method](evidence/alu-state-partitions-repair-method-20261002.json)
uses the frozen producer's serializer and requires the exact preserved proposal
size and SHA-256. Wrong state mappings still fail; graph and label comparisons
remain exact and are now reported separately. Independent review also requires
complete method/output inventories and the manifest-pinned runtime at every
common-artifact boundary. Root passes 114 tests, verifies all 83 tiny native
outputs, and confirms ten proof-construction/verdict functions are unchanged.
No proof result is inferred from the failed preparation or these local controls.

The earlier electrical graph-guard failure is
[permanently archived](evidence/closure-electrical-margin-first-archive-native-20261002.json),
including the unchanged two baseline results and the zero-repair-call outcome.

[Retry 37019936771](https://github.com/Melihakbulut221/nssoc/actions/runs/37019936771)
now [completes common-miter preparation](evidence/alu-state-partitions-common-native-20261002.json).
Native construction takes 205.97 seconds, with exact graph/label reproduction
and the original proposal bytes verified. Root checks 99 compact captured
members, twelve Git-bound methods, the full 269-group plan and all tiny native
verdicts. Four proof workers are running. The 187.9 MB common miter was not
downloaded or rehashed locally; complete native group results remain required.
The initial preparation failure is
[archived separately](evidence/closure-alu-partition-first-archive-native-20261002.json)
with its failure verdict unchanged.

### Final electrical margin result and remaining functional proof failures

The [completed margin repair](evidence/timing-electrical-margin-native-20261002.json)
reproduces both original baselines, passes the exact 19-terminal graph guard,
and inserts three buffers. Two independent reloads agree on all 70,581
endpoint/corner records and five physical fingerprints. Setup WNS is
−4.199984360 ns and hold WNS is −0.160562008 ns. The remaining electrical
violation is `fanout3120/X`: 0.308227360 pF against a 0.300000012 pF limit.
Both limited digital ECO proofs pass. Historical/matched C10 guards pass, but
hold regresses against both nearer parents; all original rejection guards
remain active. Root verifies 186 compact captures, 41 Git-bound methods and
recomputes the rejection. Large physical views were not downloaded locally.
The next repair must address the residual capacitance and regressed hold
paths together, using this complete, repeatable result.

[Complete partition traversal](evidence/alu-state-partitions-incomplete-native-20261002.json)
visits all 269 groups. Exactly 250 prove; 19 time out, leaving 2,432 of the
34,321 output equations unproved. No counterexample is reported in this run.
Root and independent review verify all four compact shard archives and reparse
every native verdict; successful worker completion alone is not a proof.
Only the timed-out groups will be refined into smaller observation slices,
without changing inputs, state pairing, or introducing internal assumptions.

The [ALU candidate/vendor boot](evidence/alu-qualification-candidate-vendor-failure-native-20261002.json)
passes MBIST at cycle 983,043 but fails the complete finite workload. Its raw
log is identical to the passing original for 14,040 bytes through test 25,
then reports a UART framing error and X-valued RAM ECC counters. It reaches
the unchanged three-million-cycle bound without the pass marker. Root verifies
all 331 compact outputs and ten immutable methods. This narrows the diagnostic
window; it does not yet identify the faulty logic or simulation behavior.
A separate bounded, read-only internal trace is being prepared. The failed
qualification remains intact, and no timing result can waive that failure.

The [matched physical method](evidence/alu-physical-method-20261002.json)
retains the same source constraints, 301 signal-terminal geometries and exact
32 SRAM placements for fresh original/candidate placement, CTS and global
routing. Independent native API review corrects missing routing configuration
inheritance; root repeats 73 focused tests. The manual-only workflow is blocked
by both the absent complete formal proof and the explicit unresolved boot
failure. No full-chip physical experiment was dispatched for this method.

Separately, the request-ack workflow's
[unchanged original/vendor reference](evidence/core-ack-qualification-original-vendor-native-20261002.json)
passes MBIST and all 28 checks at the same cycle 1,596,123. Root verifies its
201 outputs and 23 Git-bound methods. Candidate results remain independent;
this passing reference is not acknowledgement-pipeline acceptance. The selected
C10 layout and unresolved qualified I/O tap extraction contract remain unchanged.

The [ALU candidate/independent-memory case](evidence/alu-qualification-candidate-independent-failure-native-20261002.json)
now fails with the same finite-workload symptoms as the vendor-memory case.
Both logs match after normalizing only the fatal source-line number. Root
verifies all 332 compact outputs, ten Git-bound methods and 300 progress-prefix
receipts. Both original cases pass and both candidate cases fail. The unchanged
qualification outcome must be diagnosed before any candidate physical work.

The [paired diagnostic trace method](evidence/alu-boot-trace-method-20261002.json)
replays the exact original and candidate vendor netlists with a separate
1.6-million-cycle diagnostic bound. It observes 51 validated aliases (441 bits),
all three native clock gates and all four actual SRAM sampling interfaces.
Recording begins immediately after MBIST; bounded buffers preserve the first
unknown and its context. Counter-write milestones observe address `0x1e9c`,
byte enables, data, grant and the actual SRAM row. Disabled write bytes are
masked; active unknown controls still trigger. The original three-million-cycle
qualification and all DUT statements, firmware, reset and clocks stay unchanged.
Root repeats 53 tests and native tiny controls; independent review checks the
actual SRAM event order. Both dynamically imported ROM/boot helpers are pinned
to their original Git bytes and captured. A trace is diagnostic evidence;
possible simulation scheduling effects and the failed qualification still
require interpretation. No native full-SoC trace has run locally.

The [first trace launch](evidence/alu-boot-trace-history-fix-20261002.json) stops
before compilation or native SoC execution: shallow checkout lacks the exact
historical producer commit needed by `git show`. Both compact failure artifacts
and the raw error are preserved. The workflow now fetches Git history; all seven
original producer method blobs are reproduced locally. Runner, observer,
workload and qualification conditions remain byte-identical.

The [refined proof method](evidence/alu-state-refinement-method-20261002.json)
reuses the exact original common miter and all six original proof artifacts.
A pure observation wrapper splits only the 19 timeout groups into 152 groups
of 16 bits. Every original input remains symbolic; no new internal equality
or state mapping is introduced. Final acceptance reparses all 250 prior PASS
groups plus every new native verdict and requires disjoint, exhaustive coverage
of the same 34,321 original outputs. Four workers recheck complete source,
prior-proof and prepared-model inventories again after execution. Root passes
213 selected controls and independently rehashes 129 tiny native outputs;
peer review independently verifies complete coverage and positive/negative
proof behavior. Full native proof remains separate. The actual four-state boot
failure blocks physical use even if this binary refinement eventually passes.

### Source-bound residual capacitance and hold repair

The [next isolated repair method](evidence/timing-residual-repair-method-20261002.json)
uses the completed, rejected margin candidate as its explicit experimental input.
It repairs the single remaining `fanout3120` capacitance net and attempts ten
exact hold endpoints: the nine newly negative endpoints and the worst endpoint.
The native six-terminal net graph and all ten actual flip-flop data pins are
checked before mutation. One bounded pass per negative hold endpoint retains
the native setup guard, with 100 ps setup and 20 ps hold repair margins. These
targets do not alter the SDC, Liberty limits, or timing acceptance conditions.

Two independent baseline processes must first reproduce the complete parent.
Acceptance then requires all five timing references, the complete endpoint
census, all protected connections and 32 SRAM placements, two identical fresh
reloads, and both limited digital ECO proofs. Native repair can affect sibling
loads, so the full-design guards remain mandatory. Tiny real OpenROAD controls
show two inserted buffers for the positive case and no insertion when setup
blocks repair; negative controls reject unsafe targets. Root and independent
review each pass 221 focused tests. Full-chip repair and final acceptance remain
separate; this method does not adopt the parent candidate.

The margin result, incomplete partition proof and all four completed ALU boot
cases are [permanently archived](evidence/closure-final-native-archives-20261002.json).
Twelve unchanged ZIP assets have verified cloud-local, authenticated release,
and anonymous release roundtrips. The incomplete proof and both failed candidate
boots keep their original verdicts. Publication is preservation, not acceptance.

### 2026-10-03 resumed work and completed residual results

The [completed residual repair](evidence/timing-residual-repair-native-20261003.json)
adds eleven buffers. Both fresh reloads reproduce 1,311 setup and 58 hold
violations, zero slew violations and zero capacitance violations. Setup WNS is
−4.230063411 ns; hold WNS is −0.157984292 ns. The earlier input had 67 hold
violations and one capacitance violation. However, setup WNS regresses by about
30 ps against that input. The unchanged parent guards therefore reject the
candidate. The selected C10 design has not been replaced.

Root verifies 462 compact archive members and 48 Git-bound methods, independently
replays all five full endpoint exports and both protected-status tables, and
reproduces the rejection. Both reloads agree exactly on their complete 70,581
endpoint/corner records. The two limited digital ECO proofs pass within their
published scope. Large physical views and the full artifact ZIP were not
downloaded or rehashed locally; permanent cloud archival is a separate action.

The [next-step analysis](evidence/timing-residual-next-step-20261003.json)
locates the setup change on the same `_134021_` to `_132609_` path. Fresh-route
parasitics on `fanout483` and `fanout639` account for most of the extra arrival
delay. An isolated drive-strength experiment is being prepared. The worst
hold endpoint `_135215_/D` receives no buffer despite positive setup slack.
The existing log does not identify which native eligibility or rollback guard
prevented insertion; additional targeted diagnostics are required. Neither an
unsupported root cause nor a relaxed acceptance limit is assumed.

The [completed refined proof](evidence/alu-state-refinement-incomplete-native-20261003.json)
proves another 1,616 output bits: 33,505 of 34,321 are now proved. Exactly 51
refined groups, covering 816 bits, time out. All four workers completed;
there are no counterexamples or infrastructure failures in this run. The
aggregate correctly remains failed/incomplete. Independent review reparses
all 421 old and new native group verdicts and verifies the compact shard ZIPs.

The [bounded per-bit benchmark](evidence/alu-state-bit-benchmark-method-20261003.json)
selects sixteen remaining equations to measure whether smaller observations
reduce SAT cost. It preserves the original graph, all 10,828 symbolic inputs,
and the exact prior proof coverage. No internal assumptions or new state
pairing are introduced. Each SAT call has a 120-second limit. Native tiny
controls prove the equal case and reject changed clocks or outputs; independent
review verifies their captured logs. This sample cannot establish full
equivalence, and the unresolved four-state boot failure still blocks adoption.

The [completed trace and ACK review](evidence/alu-trace-and-ack-final-native-20261003.json)
confirms that both ACK candidates fail the original finite boot workload while
both references pass. The first ALU trace is diagnostic-only: unused,
undriven bits of a retained `u_bus.push` alias trigger the recorder immediately
after MBIST in both designs. Its identical early windows therefore do not
capture the later failure. The counter milestones remain useful: printed
check labels skip 11 until the end, so counter value 24 after label 25 is
expected. The earlier interpretation of a missing counter-25 write was
incorrect. No RTL cause has yet been established.

The [corrected trace trigger](evidence/alu-boot-trace-driven-alias-method-20261003.json)
resolves every one of the 441 sampled bits in each exact netlist to native
outputs, constants or eight explicitly unconsumed aliases. Only the six
unused `push[5:0]` bits are removed from the first-unknown condition; every raw
field remains recorded. Active request, response, clock and SRAM unknowns
still trigger. Native controls reproduce the old floating-Z trigger and reject
active X/Z cases. Independent review passes 62 focused tests and checks both
full binding receipts. The same bounded original/candidate pair must now run
again; the original failed qualification is unchanged.

[Run 37071773733](https://github.com/Melihakbulut221/nssoc/actions/runs/37071773733)
now [passes startup verification](evidence/alu-boot-trace-driven-alias-startup-20261003.json)
for both exact netlists. Each complete 92-member compact archive matches its
API digest; 91 output hashes and sixteen Git-bound methods per case reproduce.
Native observer controls pass, both actual core compilations succeed and
the two long replays start. Firmware, models, runtime and observer bench are
identical across the pair. Complete native trace results remain pending.

Separately, the [APB CI guard correction](evidence/apb-timeout-disabled-ci-20261003.json)
addresses a tool-dependent total-cell comparison. The disabled-timeout RTL
and its pinned predecessor both retain 93 flip-flops and identical pre-ABC
primitive counts, but generic ABC decomposes them into 104 versus 103 cells.
The test now checks exact pre-ABC cost, retained flip-flops, constant timeout
outputs and actual native equivalence of all 97 compared points. Changed
address wiring and reset behavior fail the negative controls. Five focused
tests pass independently; no design RTL or historical fixture was changed.

The completed residual repair, incomplete refinement, first diagnostic trace
and final ACK qualification are now
[permanently archived](evidence/closure-resumed-results-archives-native-20261003.json).
All fourteen original ZIP assets have cloud-local, authenticated release and
anonymous release hash checks. Independent review verifies all four publication
receipts and fresh source/release metadata; the large residual ZIP stayed in
the cloud. The rejected timing candidate, incomplete proof and failed boots
retain their original outcomes.

### Isolated critical-buffer and hold-journal followup

The [new source-bound method](evidence/timing-critical-followup-method-20261003.json)
starts from the exact rejected residual candidate. A separate native process
attempts one guarded repair of `_135215_/D` and records eligibility, buffer
selection, journal actions and rise/fall timing at all three corners. Its
mutated database never feeds the setup experiment. Native journal messages do
not reveal the transient values inside the rollback condition; an unobserved
slew-versus-setup cause must remain unresolved.

After that child exits, the original residual database is independently loaded
and its full baseline reproduced. Exactly `fanout639` changes from
`sg13g2_buf_4` to `sg13g2_buf_8`. Native graph, placement, power connections,
master geometry and protection flags are checked before the change. Placement
legalization and fresh global routing are necessary because the larger cell
occupies thirteen rather than eight sites and changes its input capacitance.
Two fresh reloads, every endpoint, all 32 SRAM placements, protected objects,
both limited digital ECO proofs and all six historical timing references remain
mandatory. This is an experiment using estimated route parasitics; the selected
C10 design and acceptance limits remain unchanged.

The frozen method passes 367 focused and adjacent tests; independent source
review passes 155 of those tests. Real four-cell OpenROAD controls verify the
replacement, eighteen rejection cases, deliberately created overlap and its
legalization, unchanged connections and constraints, and three timed corners.
The final control completes in 0.970 seconds with a 2 GiB address-space bound.
A separate small native check verifies the hold rise/fall report APIs. No full
chip was loaded locally for these method checks. The cloud workflow retains
startup and intermediate captures and has no native elapsed watchdog; its
hosted job still has a 360-minute platform ceiling. Actual chip results remain
pending.

The [completed per-bit benchmark](evidence/alu-state-bit-benchmark-native-20261003.json)
proves twelve of sixteen selected equations. Four actual SAT calls reach the
120-second limit: `ff_d[738]`, `ff_d[5732]`, `gate_enable[0]` and `gate_next[0]`.
There are no counterexamples. Combining only these exact twelve proofs with
the prior disjoint coverage gives 33,517 of 34,321 bits proved; 804 remain.
Independent review reparses all sixteen new logs and all 421 earlier group
verdicts and reproduces the observation wrapper. Root rechecks every member
of the complete compact ZIP and all twenty Git-bound methods. The useful next
step is single-bit evaluation of the 800 previously untested bits, while the
four measured hard cones need a separately validated solver experiment.
The sample is not full equivalence, and the failed four-state boot remains a
separate blocker.

The APB correction also [passes the actual cloud checks job](evidence/apb-timeout-disabled-cloud-ci-20261003.json):
3,834 pytest tests pass, 34 are skipped and one warning is retained. The outer
check wrapper reports nineteen passes and two skips. These outcomes do not
cover the separate still-running formal jobs and do not turn unavailable-tool
or PDK skips into passes.

The critical followup is now running as
[37075371532](https://github.com/Melihakbulut221/nssoc/actions/runs/37075371532).
Its [immutable startup capture](evidence/timing-critical-followup-startup-20261003.json)
matches all 56 source files against the published commit. Acquisition and the
original residual producer's validator pass in the cloud. Four base native
controls pass, and the captured worker is proceeding through logical controls.
Independent review and root rehash 156 selected compact members; the full ZIP
digest is API-provided, not locally recomputed. This early snapshot does not
yet contain the new sizing preflight, hold child or a full-chip timing result.
