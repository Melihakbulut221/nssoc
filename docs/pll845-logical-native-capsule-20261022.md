# Real native checkpoint capsule and completed-capture archive qualification

Storage run 39726696717 passed the 12 original archive controls, 16 original sparse controls, 16 added archive controls, and the real 5,106-column prefix roundtrip with the original 16 reader controls. The previously masked failed-upload exceptions now retain the exact first error and one upload attempt.

The next cloud job starts from the same immutable native 845-device checkpoint used by the passing sparse cross-host Btrfs test. Before activation, it publishes the entire actual runtime/checkpoint/reference directory, reconstructing the sparse raw prefix into ordinary archive bytes. It moves the original cloud copy aside, downloads the new archive, restores a new sparse working file at the original checkpoint path, and verifies every runtime, CRIU image and reference file plus all logical raw bytes. No native process may be active during this operation.

It then performs the unchanged separate-host CRIU restoration, compressed Btrfs superblock check, native redump and same-process continuation. After actual native exit zero, it publishes and restores the complete native output through the logical archive helper. The original reader must see the same complete raw SHA256, all 12,818 timestamps and all 34 probe trajectories as the original 4 ns reference. Truncation, state-corruption and cold-restart controls remain unchanged.

This bounded qualification is not the full 1 us acquisition or device-safety signoff. The real 5,106-column checkpoint at 892.691 ns is untouched until archive/native compatibility is proven and integrated into the production controller. All clocks, native solver inputs and acceptance thresholds remain unchanged. All computation and evidence storage are on GitHub.
