# Rejected route capsule admission for observation

This source-only helper admits exactly failed run 40095811631, source 4d85722e05fbda8440c6577d7d7baa18a642485b, through completed publication 40115867400 at 79477d53f7568266da6796c47748de96c4558273. It cannot admit an arbitrary failure or a live run. It does not modify the original controller, its normal source validator, its twenty controls, or its no-log-progress rejection.

## API

- `rejected_receipt()` verifies actual original/publication run and job identity, the exact-source release/tag and immutable small assets, and returns `report`, `inventory`, `parent`, `publication`, `descriptor`, `raw_hex`, and API metadata. The report is unchanged. There is no invented parts manifest.
- `restore_failed_capsule(pin, target, old_names)` requires a fresh absolute target and all 36 recorded work/checkpoint names, with no omissions or duplicates. It returns `(unchanged_failed_report, diagnostic_byte_proof)`. It writes those 36 files and original result.json only, after all 65 members have passed.
- `verify_current_inputs(callback, phase, previous=None)` accepts a callback returning `{label: {path, expected_sha256, actual_sha256}}`. Phases are before_restore and after_restore. It independently streams every absolute regular file, requires the fixed 27 authenticated original inputs, rejects duplicate paths/symlinks, and requires identical labels/paths/expected hashes before and after. The adapter must include its own derived source and every additional input in the mapping, with expectations from frozen method/receipt/derivation evidence. It must call before any native restoration and again after observation/cleanup, including a rejected observation.

## Proof and limits

The complete 1,560,640,815-byte original ZIP is size/SHA verified on the hosted runner before extraction. Canonical regular-file paths, no encryption/symlinks/special files, exact 65-member names, central-directory extents/CRC, and streamed per-member SHA are mandatory. All members, including nine empty files and unselected logs, are read through EOF. Files are staged in a fresh directory and exposed at target only after the whole scan passes. The exact 23-image file topology includes cores 1/7/8/9, pstree/mm/pagemap/pages and descriptors; all image bytes are pinned. Protobuf semantic validity and process liveness are not inferred from those file hashes. The later diagnostic restore must retain the actual native runtime and CRIU checks.

The original no-log rejection remains exact: one entrypoint, iteration 42, 50 percent/3313 violations, unchanged 90,392-byte native.log, native ELF 25a5e9ba… and saved route Tcl. The parent succeeded at run 40085912519, but the rejected child never reached original end-of-run input rechecks. Therefore sources_unchanged, active_drt_cross_runner_progress_proven, continuation and next_action must remain absent in the historical report. New current input hashes are separate evidence and cannot retroactively fill those fields.

The original CRIU source/version are fixed; its historical build SHA is recorded exactly. A new hosted build may have different bytes and must pass the adapter's own build/ELF checks. Matching source alone is not a runtime acceptance claim. No CPU movement, clock tick or observer sample creates route completion, a valid continuation, timing or PHY approval.

## Hosted controls, pending execution

The checker exercises 71 real structural/metadata/transport faults against the authenticated small evidence and tiny hosted ZIP/file fixtures, plus the original unchanged 20 normal-admission controls. It does not download the 1.56GB ZIP or restore any router. Tests include actual ANSI-byte stripping, exact receipt/image/prefix mutations, forbidden historical fields, safe path/CRC/member failures, selected-list completeness, real current-file mutation and before/after inventory change. The positive fixture scans unselected and empty members too. These controls are authored only; no local execution or native job is authorized by this document.

Root owns the separate 600-second diagnostic controller and persistent /proc observer. This helper has no Docker, CRIU, signal, ptrace, simulator, routing or workflow-dispatch code.
