# PLL raw-data disk bottleneck and lossless storage probe

Actual PLL initial39502073954 saved immediately after0.01434seconds:
raw94,755,872,699bytes, host free11,935,662,080bytes, original reserve12GiB.
Streaming archive publication removed duplicate compressed staging but does not
compress the live native raw file. The live continuation is preserved.

A separate cloud-only probe restores the old immutable845-device4ns process
onto a private Btrfs loop filesystem with ZSTD, then checkpoints and restores
that same process again. It must reproduce the prior complete raw bytes and
original native34-probe reference exactly, with one entrypoint and all original
truncation/state/cold-restart faults rejected. This is storage compatibility
evidence only; the current full1us/all1694-vector process is not forked or changed.

The source case is copied byte-exact to a newly created image. No host device is
formatted. Docker runtime and process image remain on the original host filesystem.
The old case copy, failure logs and all bounded native evidence are retained.

Official references:
- https://btrfs.readthedocs.io/en/latest/Compression.html describes transparent
extent compression and its requirement for COW/checksums. No no-COW workaround is used.
- https://criu.org/Filesystems_pecularities documents Btrfs device mapping concerns;
therefore real native restore and re-checkpoint are required, not assumed.

After this probe passes, a separately pinned storage-only migration must preserve
the latest terminal full1us capsule, every raw byte and all native electrical gates,
and check both backing-host and virtual-filesystem free space. This small probe
alone does not prove full-capture disk capacity, electrical acquisition or full PHY.
