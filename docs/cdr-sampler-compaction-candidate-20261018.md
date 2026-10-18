# CDR sampler physical compaction candidate

All work runs on GitHub-hosted runners. No native artifacts are restored locally.

The original loaded PD394 v3 failed both nominal cases, and all six external bias/common-mode experiments in run39088526670 failed. None is adopted. Existing layout evidence shows four sampler leaves each880um wide, with27 active/passive primitives on a32um pitch and a10um signal-bus pitch. The parent has long external detours in addition to these leaf wires; the sampler is only one required part of the repair.

This candidate regenerates real native GDS with device pitch20um, eight substrate-tap pitch60um, signal-row pitch6um and outline width560um. It preserves all15HBT12rppd8contacts, device parameters, netlist, wire widths, native via arrays and external circuit. There is no uniform shape scaling, RC multiplier, new source bias or relaxed electrical gate. The original source remains intact.

The hosted run regenerates both layouts, verifies every native PCell drawing and exact reference after top-name normalization, then runs the unchanged560-category DRC, deep/flat unsimplified35device LVS, ten original fault controls and actual OpenROAD LEF readback. The verifier differs only in the imported candidate top name. Physical failures must be retained. The geometry audit is not a DRC, LVS or electrical acceptance substitute.

After a physical pass, replace all four sampler instances through a source-bound parent manifest, regenerate the entire parent layout and evaluate parent routing compaction. Repeat parent DRC/LVS, fresh native MIM-aware RC, exact device/terminal binding and complete original loaded early/late tests. Reusing old native IDs or the old sampler RC is invalid. Clock recovery, full serialx4 integration, all-corner timing and production acceptance remain open.
