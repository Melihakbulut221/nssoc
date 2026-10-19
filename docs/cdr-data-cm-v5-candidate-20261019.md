# Physical CDR data-buffer common-mode candidate

All CAD, waveform processing and native verification run on GitHub-hosted runners.
The local project directory is empty; the verified migration receipt is in release
cloud-migration-final-checkout-20261013.

The collector-v8 native path review (run39202786678) reproduced the rejected
nominal early and late loaded waveforms without changing samples or thresholds.
This diagnostic success is not electrical acceptance. Both nominal cases still
fail sampler-data and HBT operating-window checks.

Late XD129 reaches VCE0.384447V at19.64328125ns, with base1.778396V and
emitter1.330945V. The shared-emitter XOR data stage has insufficient headroom.
Collector-wire widening alone did not close sampling or device gates.

This candidate increases only the data buffer native rppd header length from
2.0um to2.4um at unchanged8um width. The four HBT sizes, two load resistors,
substrate contacts, terminals, routing construction and select-buffer source
remain unchanged. Lower data-buffer common mode is a design hypothesis, not a
measured improvement. No supply, clock, input waveform or acceptance threshold is
changed to compensate.

The new workflow first checks exact source deltas, regenerates actual PCell
geometry and runs the same560-rule DRC, deep/flat14-device transistor LVS and
five original fault controls. An additional LVS fault deliberately supplies the
old2um header reference; accepting that mismatch fails the campaign.

Pending: native leaf results, two-leaf replacement in the484-device parent,
fresh parent DRC/LVS, native terminal planes, binding and wire RC, full MIM
composition, and the same loaded256-bit early/late and fault waveforms.
No standalone idealized-buffer transient can substitute for those checks.
Sampling errors, TX32-tree electrical failures, closed-loop CDR, complete PHY,
mainchip integration and final timing remain open.

## Native leaf results and full-parent candidate

Run39204220474 passed the560-rule leaf DRC and deep/flat14-device transistor
LVS. All six faults were rejected, including a reference with the old2um header.
The actual native D4 rppd PCell is8um by2.4um. This proves leaf geometry only.

The data-cm-v9 parent replaces both da and dc leaves while retaining all other
14 macro instances, all484 primitive devices and all25 boundary ports. Its
source verifier preserves all six topology fault controls. In addition to the
original physical faults, the new parent LVS check must reject both old2um
header references against the new layout. Parent proof and fresh full loaded
transients remain pending; no timing or serial PHY closure is claimed.

## Sampling-path localization

A separate read-only hosted diagnostic partitions the original rejected collector-v8
waveforms by the unchanged0.3/0.6/0.9UI sample phases. It binds each sampler actual
data-pair input base to its native collector witness, checks polarity against the
logical boundary and records terminal voltages around the original acquisition
edge. Per-phase counts must reproduce every aggregate original sample failure.
No sample offset or limit is fitted. Diagnostic completion cannot pass the PHY.

## Native whole-parent physical results

Run39204778311 passed the full560-rule DRC and deep/flat484-device transistor
LVS with both modified data buffers. All six physical/reference faults were
rejected, including both old header lengths in the full-parent reference.
The next cloud job binds all158 child/public planes to the unsimplified native
LVS database, independently checks all16 placed leaf drawings and transforms,
and retains all19 plane fault controls. Wire RC and loaded waves remain open.

## Fresh terminal-plane proof

Run39205373042 passed all158 native plane bindings,51 logical-net identities,
1394 terminal bindings and19 fault controls. The independent GDS comparison
passed all16 actual macro placements and all eight native leaf drawings.
The next job reconstructs whole-parent conductors and intrinsic terminal
anchors from this new GDS and unsimplified LVS, without reusing old wire RC.

## Original sampler failures localized without changing gates

Run39205681729 successfully re-read both original collector-v8 captures, traced
the actual slave bases through the master pair and native input resistors, and
reproduced every original aggregate error at the unchanged0.3/0.6/0.9UI phases.
The earlier failed diagnostic39205141662 is preserved separately.

At nominal early, sampler A has121 wrong signs at0.3UI and zero at0.6/0.9UI,
but37 and8 samples respectively still miss the100mV margin. Sampler B remains
wrong91 times at each later phase. At nominal late, sampler B has128 wrong
signs at0.3UI and zero later, whereas sampler A remains wrong69 and61 times
at0.6/0.9UI. Both retimed samplers C/D still fail at all three phases. This
is a measured settling/acquisition problem, not an opportunity to discard the
early sampling phase. No gate was relaxed.

The unchanged sampler leaf is1588.695um wide by191.63um high; its recorded
clock spans are1002.405um and1263.805um. These measured geometric spans warrant
checking clock distribution and master/slave path delay against the native
waveforms before selecting the next placement/interconnect repair. Geometry
alone does not prove a delay or prescribe a passing replacement.

Current cloud work: new data-cm-v9 wire inputs39205842770; full-chip logic
resize routing39202263552. The physical data-header repair remains electrically
unproven until fresh full native RC/MIM composition and original loaded waves.

## New conductor and intrinsic-anchor proof

Run39205842770 reconstructed111 actual conductor components and946 physical
reference points, covering all1394 terminals with921 metal and473 retained
intrinsic-body dispositions. Native model conversion and fresh wire-only RC
now run as independent hosted jobs. The12 binding fault controls and13 raw
R/C corruption controls remain unchanged. This stage does not include
substrate spreading resistance, RF qualification or intrinsic MIM composition.

## Fresh wire RC and model binding

Run39206431723 passed all484 native device/1394 terminal model bindings and
12 corruptions. Run39206431729 passed the fresh wire-only graph audit with
15467 native resistors and11524 capacitors,111 conductors and946 points. All
13 raw corruption controls were rejected. This is wire-only RC, not qualified
substrate/RF PEX or electrical acceptance.

The next hosted capture restores those exact new sources and includes the11
actual MIM masks, moving bottom reference points only onto measured native
bottom-metal access. Every reference remains bound to the original native
conductor. Raw point/value audit and full loaded transients remain pending.

## Actual MIM-aware capture

Run39206881702 captured15490 resistors,11535 wire capacitors and11 explicit
native MIM devices. All946 physical points and111 conductor identities match
the new native geometry. Five intrinsic/device/wire corruptions were rejected.
The next hosted audit retains every raw R/C point and value, checks the11
MIM identities against this candidate binding and runs13 wire plus9 intrinsic
corruptions. The wire-only counts are not reused as MIM-aware counts.

## Full MIM raw audit

Run39207200884 passed raw resistor topology/value and every point-capacitance
attachment/conservation check for the new15490R/11535C capture, plus all13
wire and9 intrinsic MIM fault controls. The next composition retains all484
native devices and exactly one model per native capacitor; it must pass the
same19 composition controls before any loaded transient starts.
