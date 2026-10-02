# 106 — Faster setup and hold repair: measured bottlenecks and controlled experiments

**2 October update:** the first targeted hold run stopped before repair because
the C10 guard expected the small fixture's corner aliases. The exact PVT names
and distinct native wrapper identities are corrected below. No hold reduction
or new checkpoint has yet been demonstrated by this retry.

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
