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
