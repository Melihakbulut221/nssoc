# Current binding namespace for candidate fresh RC

This source-only primitive removes the historical binding dependency from the frozen MIM intrinsic validator. It does not extract RC, restore native input, run a simulator or qualify an actual production binding. The canonical-view producer remains null, and the standalone native entry always refuses execution, even if a caller changes an authorization flag.

The exact two definitions from `audit_cdr_v59_mim_intrinsic.py` at ebe4ebb3ca2aef7b23cfc68f4b17588c03cd84fb are loaded into a new namespace. Complete file and individual definition byte hashes must match hardcoded immutable pins. Imports, assignments and module main code are excluded; decorators, defaults, annotations and imports inside the selected definitions are refused. The original historical admission module is never imported or changed.

`CurrentBinding` receives an explicit reader, expected current source/run/attempt and descriptor byte pin. On every `stage_report('binding')` call it rereads both descriptor and summary bytes, checks their identities and agreement, and checks the complete current binding scope. It returns an independent copy. A separate future host still must authenticate the actual binding producer, complete native inputs, output map, source controls and reservations. This byte/schema check grants no native authority and cannot substitute for that admission.

`intrinsic_namespace` connects only this current binding reader to the unchanged `require`/`validate_mim` functions. Two separately constructed namespaces share no mutable admission global. Wire and audit workers remain main-only orchestration boundaries; this change does not invoke them. The broader boundary plan is preserved in docs/cdr-via2-m3-fresh-rc-entry-plan.md.

Hosted source controls use explicit synthetic descriptor/summary data and seven synthetic MIM records. They test the real frozen validator with two different current bindings, stale source/run, changed summary/descriptor bytes, incomplete census/control records, immutable source/definition tampering, hidden historical-module imports, namespace cross-talk and unconditional native refusal. Synthetic file creation is confined to GitHub ephemeral fixtures; no actual project native payload is acquired. Complete raw job logs and source-control streams are preserved on either outcome.

The recorded binding status is checked as an input contract; a successful synthetic fixture is not evidence that a new physical, RC or electrical stage has run. All numerical thresholds and original intrinsic validation bodies remain unchanged.

## Native versus compact model schema correction

The 43 synthetic controls at c002048efbe5e260bf6f90cb10889f4326633c3c passed, but their HBT rows incorrectly used the native model spelling in the compact model field. That proof remains synthetic-only and did not demonstrate compatibility with the actual binding producer. Before any native use, integration review found that the frozen producer emits `native_model=npn13G2` and `model=npn13g2`.

The successor separately verifies the complete native census, complete compact census, and each native-to-compact pairing. Its independent literal fixture follows the unchanged producer schema; AST inspection binds the spelling and both fields to the exact frozen producer source. It rejects the old uppercase compact spelling, missing native fields, wrong native census, and swapped per-row model pairs even when both aggregate censuses still match. The original 3550-byte intrinsic validator and all numerical limits are unchanged. Standalone native execution remains unconditionally disabled.
