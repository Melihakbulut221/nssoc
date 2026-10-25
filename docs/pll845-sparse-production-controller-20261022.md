# Full PLL sparse-storage production continuation

This candidate integrates the separately qualified sparse working-file and ordinary archive mechanisms into the existing full 1us PLL controller. It does not claim a completed trajectory or electrical acceptance before actual hosted execution.

The first intended source is immutable saved run 39674830790, at 892.691247612 ns with every 5106 recorded column retained. The original source archive is never deleted. No new initial condition, solver, timestep, load, device, OFF target, vector or acquisition gate is introduced.

## Runtime sequence

1. Reuse the frozen preallocated Btrfs workspace with its independent 12 GiB native, 4 GiB backing and 6 GiB allocation safeguards.
2. Verify the source descriptor, complete ordered archive, every source runtime/CRIU file and complete raw/payload SHA256. Materialize only the 2 MiB head and 4 MiB tail of the old raw as a new sparse working file at the original absolute path.
3. Restore the exact original process under unchanged command, image, libraries, CPU and environment checks. The qualified bounded cross-host logical-capsule test is prerequisite evidence; it does not stand in for this full continuation.
4. Once stopped, reconstruct the entire current logical raw from immutable source and current head/tail/append. Check the original payload and every current byte. A stat-identity-bound cache avoids only redundant stopped-state rechecks; the publisher independently checks the complete source and logical payload again.
5. Publish an ordinary complete tar member with every original byte, verifying each hosted part. A pending/reader-ready descriptor is emitted only after full publication. Failed/unclaimed sparse files are explicitly labelled not usable as waveforms and cannot resume.
6. If the native process exits successfully, a separate hosted job first checks enough free space for the full raw, one staged part and an additional 4 GiB reserve. It downloads and verifies the ordinary raw, then runs the unchanged all-column reader and both original acquisition-window checks. The sparse working file is never given to that reader.

Full device safety, PVT, complete serial CDR/PHY, x4 and final chip timing remain separate requirements. Completing storage, a native process or its full capture does not close them.

## Verification

On push, only cloud integration controls run. They retain the original native/reader/acquisition/storage controls, exact source-delta and migration checks, late-archive-corruption tests, owned-publication tests and full-reader capacity rejection tests. The production process is dispatched only after these controls pass, using the exact saved-source descriptor. All failed results and original hosted evidence remain retained.
