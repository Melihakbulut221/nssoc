# 106 — Faster setup and hold repair: measured bottlenecks and controlled experiments

**Implementation update:** the three-method local campaign and its controlled
handover are now running. See the implementation section below. The original
checkpoint is still finishing; no full-chip speedup is claimed yet.

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
The baseline worker is starting; no completed comparison is claimed.
