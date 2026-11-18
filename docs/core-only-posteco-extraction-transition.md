# Post-ECO extraction transition

Active detailed route: https://github.com/Melihakbulut221/nssoc/actions/runs/44337630426
Execution head:19924a826cfca054f30f19cdde091fbe6c744960. Preserve this run; later commits do not change its code.

Do not blindly reuse `cloud_core_only_canonical_extracted_timing.py`: its canonicalization helper intentionally binds the original 104885-instance source and requires nonempty rename maps. The selected pin-aware ECO has105251instances and inherits the previously canonicalized identifiers. Keep its names stable for fault localization and parent integration.

After the new routed artifact is available and authenticated, adapt `cloud_core_only_routed_extraction.py` (the path without re-renaming) to the new artifact and all authenticated predecessor files. Run `audit_core_only_extraction_names.py` read-only before extraction, with NSSOC_EXTRACTION_EXPECTED_INSTANCES=105251, NSSOC_EXTRACTION_NAME_ODB and NSSOC_EXTRACTION_NAME_REPORT. This new guard has not yet been executed; the future native run must prove it. It must fail for unexpected/unsafe identifiers rather than silently rewrite them.

Retain nominal native RCX integrity checks, fresh standalone three-corner OpenSTA,20ns/5percent constraints, actual name-based SPEF inventory, every partially/unannotated-driver classification, and source hashes. No global-route estimate fallback. Expected name safety alone does not qualify annotation coverage. Do not require the original source's exact 102601 SPEF nets or1403 unannotated outputs for a different ECO; classify the new measured graph and reject loaded gaps. Qualified min/max RC, complete SRAM/IO models and hierarchical parent/core timing remain separate open requirements.
