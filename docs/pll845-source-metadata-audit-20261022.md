# Original PLL capsule metadata audit

Production attempt39735397718 failed before native activation. Every compressed source part was restored, but the archived storage-initialization-state.json did not match the controller report's recorded SHA. The rejected working file and failure evidence remain immutable; they are not a resumable checkpoint.

Source workflow at6fbd221520a35d6b5ef01cc1c67796175093ee3c copies current storage initialization and headroom evidence over restored metadata immediately before publication, after the controller has produced its output manifest. This is a possible explanation, not yet a waiver or proven exhaustive list of discrepancies.

The audit reads the exact original39674830790 archive in bounded compressed parts on a hosted runner. It verifies every part and whole archive, the original full raw/payload hashes, the archived result.json, and inventories all file differences and byte-identical tracked peers. No native process activates and no file is reconciled by this audit. A repair must explicitly establish the complete metadata-only differences and preserve strict native/model/input/checkpoint byte identity. Synthetic controls detect changed/missing native files, raw/summary corruption and unsafe paths.
