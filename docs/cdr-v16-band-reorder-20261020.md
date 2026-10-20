# CDR v16 physical-band reorder candidate

The completed v16 latch diagnosis reproduces the original sampling failures. A/B outputs settle late, and C/D additionally receive weak incoming data. Their long physical source/filter/consumer paths motivate this candidate.

The candidate starts from the **actual DRC/LVS-clean v16 GDS** with SHA256 c920186862bde235868d3fa009fedcff868246750f0fa38874e3c6b42ba7255e, not an earlier layout. It retains all484 native devices, child PCell hierarchy and all v13/v14/v15/v16 local metal and via additions. It partitions only the first six macro bands, enumerates all720 orders and chooses a strictly shorter retime span under explicit clock-span and unchanged data-input-span planning bounds.

Every non-trunk parent conductor must fit wholly within one movable band or the unchanged public supply entry region. A crossing conductor aborts generation. Only the original global TopMetal1 trunk rectangles are replaced by rectangles derived from the new actual branch positions. Source and candidate per-net spans and every considered order are retained.

The serialized GDS must exactly match the conserved parent-band geometry, unchanged translated child drawings and rebuilt trunks. The reference circuit is byte-identical. Public signal pin positions and LEF are regenerated to match the actual moved connections. The independent16-placement/eight-leaf geometry checker, its three faults, the original560-rule DRC, deep/flat484-device LVS and original physical/reference faults remain mandatory.

This is a physical repair candidate, **not** electrical acceptance. Geometric span bounds are not timing constraints or new waveform gates. Fresh whole-parent MIM-aware distributed extraction and the original full loaded early/late tests are required even if DRC/LVS passes. There is no change to circuit values, waveform oracle, sample phases, loads or acceptance limits. The rejected v17 resistor-divider experiment is not used.

All generation and verification execute in GitHub Actions. No local CAD output or source checkout is created.
