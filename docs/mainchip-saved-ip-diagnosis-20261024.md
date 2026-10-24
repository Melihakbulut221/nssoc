# Saved native instruction diagnosis

This readback is restricted to the latest authenticated process saved by run40120760532 at source84b513cb. It does not restore, start, modify or continue OpenROAD. The router's original no-log rejection and the20/4/8/8ns +5% timing contract remain authoritative.

The existing archive verifier authenticates all compressed parts and their combined digest before extracting the selected saved core/register, memory-map, file and process-tree images. The decoder is built from the same CRIU4.2.1 commit used for the actual checkpoint. Each of the four saved thread IPs is mapped through the actual VMA and regular-file record. The exact pinned portable runtime image supplies the executable/library bytes through a never-started Docker container. Mapping from file offset to ELF virtual address uses the actual executable PT_LOAD segment, so PIE and shared-library load bases are not guessed.

All decoded records, original selected image bytes, per-thread disassembly and exact source/archive hashes are retained in cloud evidence. A saved instruction pointer is one checkpoint observation, not a sampled profile or a causal proof. This may localize a hot routing algorithm or a synchronization wait; neither interpretation is accepted until the actual result is inspected. No routing, PHY or timing gate changes.

Primary format references: [CRIU images](https://criu.org/Images), [exact core schema](https://github.com/checkpoint-restore/criu/blob/9539417f3e3cfa4eb84c319cd71f4d52f1f08645/images/core-x86.proto), [exact memory-map schema](https://github.com/checkpoint-restore/criu/blob/9539417f3e3cfa4eb84c319cd71f4d52f1f08645/images/mm.proto).
