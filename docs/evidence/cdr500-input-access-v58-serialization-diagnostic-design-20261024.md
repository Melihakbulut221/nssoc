# CDR500 serialized geometry diagnostic — 2026-10-24

Run40094547119 at source4ad6e787 reached the unchanged serialized material XOR guard and rejected at generator line571. The pre-serialization candidate checks had returned; the full DRC, LVS and strict wire stages were not started. The complete failed summary/parts are pinned in the serialization-rejection receipt. No mismatch layer or shape was yet reported.

This change inserts reporting immediately before the unchanged original serialized-layer loop. It enumerates every original layer, records the exact original guard XOR and both directed differences, and separately reports merged-region XOR without using it for acceptance. It also compares every original child drawing, label and placement, records original and serialized parent instances/labels, and preserves the actual9+3+8 control records. It does not insert, delete or edit geometry and does not change the original XOR predicate.

The physical controller exposes an explicit --serialization-diagnostic mode and the branch-local workflow invokes it for this one readback. A failed original generator still rejects and publishes the full witness. Even an unexpectedly successful generator returns from this mode before physical execution; no DRC/LVS/RC/electrical acceptance is claimed. The diagnostic mode must be removed from the workflow for a future reviewed physical qualification.

The next decision must follow the actual all-layer/cell native witness. A representation issue, real GDS shape loss, name remap or other cause is not presumed. Original guards remain mandatory. All source and results stay in GitHub; no local files or native tools are used.
