# Whole PLL regular n-well body access — 2026-10-20

Composition run39355410610 rejected one actual open model boundary: native core_vdd body cluster203 has no explicitly extracted ptap1/ntap1 device connecting it to metal. The other61 body groups have named tap models. A native net name does not by itself justify inserting a metal/body short.

The new native KLayout proof locates every affected LV PMOS S/D region in exactly one actual NWell polygon. Physically separate well islands retain separate body nodes. Regular n-type active tap regions are derived from actual Active/pSD/nSD-block/GatPoly/SalBlock geometry within those islands. Every tap must have an actual contact point already present in the audited1604-point wire mesh, with full contact/Metal1 overlap and independent native-LVS/wire-component owner checks. If an actual reference is missing, the job must reject and require a fresh RC extraction; it may not invent a same-net anchor.

The auxiliary contact model is the pinned PDK ntap1 resistance equation applied to the measured tap area/perimeter. These are geometry-extracted access models, not newly discovered devices in the original845-device LVS census. Distributed resistance inside the well/tap and substrate spreading remain unmodeled and unqualified.

The native verifier must reject removal of each selected contact, selected metal, actual tap diffusion and well island, plus each wrong conductor-owner assignment. Original GDS, LVS and the3380R/5104C wire mesh remain immutable.

The prior composition also proved that14 of52 native MIM terminal nodes differ from the corresponding inspection-anchor node. The composer preserves the actual raw extracted node for each of these; it never replaces that node merely because an alternate anchor lies on the same conductor. All26 MIMs are emitted once. This attachment-plane check should also be applied to the earlier CDR composition before more CDR physical tuning.
