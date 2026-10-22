# Native sparse-prefix runtime qualification

The storage-only run [39712609867](https://github.com/Melihakbulut221/nssoc/actions/runs/39712609867) passed on ext4 and compress-force=zstd:3 Btrfs. Both fixtures retained16777398 logical bytes using5246976 physical bytes before append, and reconstructed every original byte after header backpatching and partial append. All16 corruption scenarios were rejected. These sizes are fixture measurements, not a projected production capacity guarantee.

The next workflow reuses the existing bounded4ns physical845-device ngspice checkpoint test. Preparation, all circuit/model bytes, original34 probes, .3125ps stepping, KLU, zero-source OP,102OFF flags, host/container comparisons, golden numerical hash and three numerical corruption controls are unchanged. Only the stopped fixture's raw storage is migrated to a sparse prefix before actual CRIU restore.

The exact immutable checkpoint prefix is retained. Native output into the archived-only hole, changed previous payload, missing source, wrong header boundary or failed logical reconstruction are fatal. The direct original reader must reject the sparse file; only its fully reconstructed logical bytes can enter the original numerical reader. Every final native time and all34 probes must equal the uninterrupted oracle bit for bit.

Passing this test would qualify a bounded same-host runtime behavior only. Cross-host restoration, compressed-Btrfs native restoration, original5106-column reader equivalence and complete published capsule reconstruction remain required before using it on the actual892.69ns/1us PLL checkpoint. The real checkpoint is not touched by this workflow.
