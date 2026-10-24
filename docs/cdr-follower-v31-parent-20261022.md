# Integrate the actual v31 followers into the actual v30 CDR

Leaf run39717037237 passes560-category DRC, strict deep/flat8-device transistor LVS and seven negative controls. GDS SHA-25621f6cbd93bf94c5d827a083883f88ec4c1c239d0be5ff2d9f0fbed74e106b03d.

The new parent uses the passed actual v30 parent39706018326, replacing only its two rc_retime children ac/bd with the actual new native leaf hierarchy. Exact external pin and boundary equality is mandatory; both HBT device records and their placements remain unchanged. The only schematic changes are Rac_D1/Rac_D3/Rbd_D1/Rbd_D3,4.5um->2.25um at4um width.

The serialized native parent must preserve every existing polygon, label, instance transform and historical M4 repair. No historical repair is replayed. Three intentional parent geometry/hierarchy corruptions must fail. The existing independent checker then compares all16 actual placements against all eight native child sources, followed by the unchanged full476-device DRC and unsimplified deep/flat LVS and original fault controls.

Passing parent physical verification does not establish electrical performance. Regenerate all wire and intrinsic-MIM parasitics and rerun the full nominal/fault waveform matrix with original clocks, duration, loads and thresholds. The actual v30 rejection remains recorded.
