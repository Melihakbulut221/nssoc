# Exact publisher-added CRIU log

The first readback 40184778567 stopped at the strict archive check before any waveform analysis: `criu-build.log` was absent from the controller result inventory. Its complete rejected result, original job log and publication hashes remain preserved.

The actual producer at `2e63863abb0309c245d89e2a3d4934fe40a2b2ed` copies only `criu-build.log` at workflow line 89, after the controller returns and before line 95 packs the output directory. Its exact 5731-byte workflow is pinned separately. `criu-build.json` is not an additional permitted path.

The correction admits exactly one mandatory publisher file after verifying all seven parts and the combined archive SHA256. Every original result.outputs member and result.json still has its original independent hash checked. The added log receives a streamed hash/size and is reported under whole-archive attestation, explicitly without claiming a prepublication per-file hash. It is not retained or used as analysis input. Missing, duplicate, renamed, linked and unknown additions still reject. Thirteen hosted controls exercise the source binding and archive distinctions; the original eleven archive faults, all other controls, full electrical review and nineteen actual-input faults are unchanged.

Readback and native simulation remain disabled pending source review and hosted controls. No local authored control or archive was executed/read.
