# CDR v24 fresh extraction

The four smaller-selector samplers passed physical verification in run39490302719. This workflow extracts their actual serialized parent anew; no v23 RC is reused. The GDS top name remains unchanged for the physical validator, while a distinct compact-model name and immutable artifact hashes identify v24.

Required checks remain476 devices,1382 terminals,25 ports,160 hierarchy interfaces,51 logical nets,111 wire components and938 physical points. The original19 interface faults,12 binding controls and13 raw RC corruption controls remain enabled. Native HBT sizes must additionally match the actual parent reference schematic.

This is preparation for the original loaded early/late electrical tests. It does not establish electrical timing, closed-loop acquisition, qualified RF/substrate extraction or full PHY acceptance.

Mainchip recovery run39491419606 verified the saved global-route database and guides and opened152762 instances with the pinned OpenROAD runtime. It did not recover the interrupted detailed-router process or close final timing. A portable process checkpoint must be proven before another long routing run.

All extraction and validation run on GitHub-hosted runners. Local project source and CAD outputs remain absent.
