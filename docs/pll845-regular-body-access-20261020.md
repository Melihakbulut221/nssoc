# Whole PLL regular n-well body access — 2026-10-20

Composition run39355410610 rejected one actual open model boundary: native core_vdd body cluster203 has no explicitly extracted ptap1/ntap1 device connecting it to metal. The other61 body groups have named tap models. A native net name does not by itself justify inserting a metal/body short.

The new native KLayout proof locates every affected LV PMOS S/D region in exactly one actual NWell polygon. Physically separate well islands retain separate body nodes. Regular n-type active tap regions are derived from actual Active/pSD/nSD-block/GatPoly/SalBlock geometry within those islands. Every tap must have an actual contact point already present in the audited1604-point wire mesh, with full contact/Metal1 overlap and independent native-LVS/wire-component owner checks. If an actual reference is missing, the job must reject and require a fresh RC extraction; it may not invent a same-net anchor.

The auxiliary contact model is the pinned PDK ntap1 resistance equation applied to the measured tap area/perimeter. These are geometry-extracted access models, not newly discovered devices in the original845-device LVS census. Distributed resistance inside the well/tap and substrate spreading remain unmodeled and unqualified.

The native verifier must reject removal of each selected contact, selected metal, actual tap diffusion and well island, plus each wrong conductor-owner assignment. Original GDS, LVS and the3380R/5104C wire mesh remain immutable.

The prior composition also proved that14 of52 native MIM terminal nodes differ from the corresponding inspection-anchor node. The composer preserves the actual raw extracted node for each of these; it never replaces that node merely because an alternate anchor lies on the same conductor. All26 MIMs are emitted once. This attachment-plane check should also be applied to the earlier CDR composition before more CDR physical tuning.

## Corrected target census

Run39356172553 rejected the draft's incorrect130-device target before any body-access model was accepted. The immutable composition records show exactly125 LV PMOS body terminals on cluster203 (native IDs195 through319). The whole PLL still contains130 LV PMOS; the remaining five already belong to other body groups with named contact models.

The revised native verifier derives the complete target identity set from the frozen composition, requires exactly125 IDs, and requires exact equality with the native KLayout device set. It separately retains the full130 LV PMOS census. This corrects the scope of the body-access check; it does not remove a missing device or weaken the original845-device model binding.

## Actual missing reference points

Run39356595862 passed the corrected125-device identity scope, then rejected a real regular tap on NWELL_003 because no original RC point lies on its drawn contact. The previous immutable wire model therefore cannot represent every required body-access plane.

The revised generator chooses new points only at actual drawn contacts wholly inside the physical tap and Metal1, independently probes native LVS and wire ownership, and preserves every original1604 physical/1877 logical reference unchanged. Extended anchors and the contact plan are separate artifacts. Adding a point explicitly requires fresh native RC and a fresh raw audit before composition. This changes extraction reference points, not the GDS or the original failed/captured evidence.
