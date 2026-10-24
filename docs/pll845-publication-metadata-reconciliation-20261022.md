# Exact historical metadata reconciliation and isolated future publication

Audit39743545709 consumed all396 parts and106073878727 compressed bytes of the original39674830790 capsule. It verified the116738387899-byte original raw and its entire payload hash. No recorded native/model/CRIU/input file was missing or changed. The sole recorded mismatch is storage-initialization-state.json: the publisher copied current host state over an inherited initialization-state path after controller hashing.

Both identities remain in that exact archive: original8ad8d2... in preallocated-storage-proof/state.json, published7e96ec... in storage-evidence/run-39674830790-attempt-1/preallocated-storage-proof/state.json. Extra nested log/headroom files are explicitly inventoried too.

The production restore now binds this exact source descriptor and independent audit, checks every archived file against the audited inventory, retains the published metadata in a new evidence namespace, and restores ONLY the original metadata path from its byte-identical archived peer. It then verifies every original controller output hash. Native model, runtime, CRIU, input, complete raw and original payload identities remain unchanged. No wildcard mismatch exception is introduced.

Future publication copies current storage/headroom evidence under storage-publication/run-ID-attempt-N, records its hashes in the new current report, and refuses overwrite. It no longer writes over controller-recorded initialization files. The reconciliation policy is included in the24-entry native method map. Cloud controls must pass the original storage/native/reader/acquisition tests plus exact-policy, native/checkpoint corruption, metadata-peer, missing/extra member and publication-collision controls before actual continuation.

This restores resume integrity only. Original full1us simulation, all5106 columns and both original acquisition windows still must complete; device/PVT/fullPHY/mainchip acceptance is separate.
