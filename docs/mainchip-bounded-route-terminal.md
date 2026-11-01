# Bounded routing terminal result

Run 41292673925 (source 7a0776718ec37a106b7dfde0cbd477c6a2a5522f) completed with failure. The actual eight-bound route itself returned and saved four native DEF/ODB checkpoints. The final router count was 397 violations. Neither the final full-chip DRC nor setup/hold was executed after this result.

Both primary and cleanup class-restoration plans failed at mainchip_original_clock_restoration.py:215 because a selected record did not satisfy the required FIXED class. The preserved result is raw routed geometry, not an accepted restored candidate.

The next cloud-only diagnostic must authenticate the native publication and inspect the actual class and geometry changes before proposing a fix. Keep the strict original protected-record, topology/connectivity, diode and final timing gates. Do not bypass this assertion or blindly rerun all 828 routed owners.

Release 430474717 retains two native archive parts and their original SHA256/size index. The complete safe text proof and selected decoded records are under docs/evidence/bounded-route-native-terminal-41292673925. The mixed workflow artifact contains native data and must not be acquired locally. Source/API-derived text was handled only in RAM; no native archives or geometry files were downloaded locally.

The collector first rejected two unlisted text suffixes (.stderr then .tcl), before publication. Its allowlist was extended only to explicit text stdout/stderr and Tcl source. No native payload or source acceptance gate was relaxed. The final collector verified every selected text artifact checksum, both release manifest hashes, archive-part asset metadata, all six decoded report hashes, and the published proof by full file readback.

This result does not close physical signoff, serial PHY integration or timing.
