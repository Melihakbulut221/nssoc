# Four collector trunk candidate: DRC passes, LVS fails

Run39438730794 passed serialized exact geometry delta controls and all16
native child placements/drawings. It removed7858.4um of horizontal parent wire.
Full native560-category DRC has zero markers. Strict transistor LVS remains
NoMatch with484devices on both sides, so the candidate is rejected and no
wire extraction or waveform acceptance follows from its DRC result.

The read-only cloud diagnosis restores the exact failed GDS/LVS database and
the independently passing original v20 GDS/flat LVS database. It probes every
133macro interface plus25public ports on actual native layers, verifies all
original158anchors form51distinct nets, then reports candidate open/shorted
logical groups. It also intersects each new TM1 trunk with original retained
TM1 and probes any intersection in the original native database.

The original mismatch remains a failure even if interface anchors are all
correct; internal terminal mismatches require further native inspection.
No geometry, extraction rules, schematic, DRC or LVS threshold is altered.
Use observed native net/geometry evidence to repair routing before re-running
the complete original physical gates.
