# Fresh v49 physical wire input preparation

This stage consumes only the exact completed physical source40024005062. It requires full560DRC/0markers, deep/flat18-device LVS and all9fault controls before constructing extraction inputs. GDSf05e4b9c2125e0e65d18b10e6e9fc708067b0ea5b2055e9a747b8a062939c5dc is immutable.

The existing source-pinned native graph/physical-enclosure/terminal-anchor methods are adapted only for leaf paths, top identity,8ports,18devices and50terminals, LVNMOS handling and actual Metal5 public pins. Actual native pin annotations remain in this leaf, so no recovered annotation or parent-layout assumption is needed. Exact transformation checks and method hashes are recorded.

Expected intrinsic census:2HBT,3LVNMOS,4rppd,9ptap1. All50terminals remain represented:32physical metal points and18intrinsic body references. Adding8actual external pin points yields40logical anchors. Coincident points may share a solver port only with identical actual point/metal/ownership; all logical aliases are retained. Conductor components are derived from actual native metal/via geometry and checked against unsimplified LVS, never joined merely by their net label. Physical instances are bound by unique native terminal enclosure.

This stage does not claim RC has been extracted. Fresh native wire resistance/capacitance extraction, raw-value/point/topology auditing,13corruption controls, intrinsic-device composition, full loaded parent and bias integration remain required. Body references preserve intrinsic models but do not model substrate spreading impedance. Full serialPHY and final mainchip timing remain open.
