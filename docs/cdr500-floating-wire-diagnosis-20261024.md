# PD500 terminal-free metal diagnosis

The physical candidate from run 40073349301 passes the native 560-category DRC and unsimplified deep/flat 500-device LVS. Its fresh whole-parent wire-input run 40073945226 rejects a native metal net with no intrinsic terminals. Physical matching alone does not satisfy the strict electrical-conductor contract.

This isolated diagnostic restores the exact rejected GDS, LVS database and strict probe by published hashes. It reruns that unchanged probe and requires the same rejection, then independently enumerates every native net without intrinsic terminals. Exact metal/via polygons, label-free connectivity, root versus child ownership, original-root overlap and intersections with preserved v14 source-bypass strips are recorded. No geometry is changed and no original gate is weakened.

The initial commit contains the diagnostic and source rejection receipt. A successful diagnostic is evidence of ownership and connectivity only; it is not RC, electrical, PHY, timing or production acceptance. Repair selection requires inspecting its native results.
