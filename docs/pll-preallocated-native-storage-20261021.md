# Pre-download shared compressed storage qualification

The original native4ns/34-probe checkpoint test previously passed exact restoration,
Btrfs redump,12818-row bit equality and all3native+5path rejection controls in39544302605.
This new qualification changes only storage preparation.

Before downloading a capsule, allocate an owned backing image with posix_fallocate,
leaving6GiB outside. Format with mkfs.btrfs -K and mount with nodiscard,
compress-force=zstd:3 and noatime. Verify actual st_blocks allocation after formatting
and after native completion. The physical host must retain4GiB and the native Btrfs
filesystem12GiB before resume. These are independent budgets, not sparse virtual capacity.

Preserve original filesystem-relative workspace paths and Docker external-file superblock
sharing. Copy only the clean repository before capsule download; no second94.76GB raw copy.
Source files, Docker image, commands, native trajectory, all34probes and original acceptance
remain unchanged. A different filesystem or released backing allocation is rejected.

References:
- https://btrfs.readthedocs.io/en/latest/mkfs.btrfs.html (-K disables format-time discard)
- https://btrfs.readthedocs.io/en/latest/btrfs-man5.html (mounted discard is separate)
- https://criu.org/External_bind_mounts (shared external mount superblock semantics)

Passing this native bounded test would validate the new allocation/mount order and
byte-preserving continuation. It cannot prove full1us capacity, acquisition or fullPHY.
Production migration must then consume only the latest terminal-success full checkpoint.
