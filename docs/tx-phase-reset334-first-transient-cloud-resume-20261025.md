# Cloud-only resume recipe for the first physical334 loaded transient

This run-specific receipt supersedes the historical activation wording in the protected design document. It does not change any tested controller, workflow, model, source, clock, threshold or acceptance gate.

The sole first p-high run is [40178775666](https://github.com/Melihakbulut221/nssoc/actions/runs/40178775666), attempt1, tested source `7398bb00efc4ec6ff053aeb50e03028570f0cfa0`, on `codex/tx-clock-phase-parent`. Its workflow is `.github/workflows/tx-phase-reset334-transient-cloud.yml` (ID395788082). Source controls121125132309 passed; native job121125295778 entered its owned-process step at09:01:52UTC on2026-10-25.

The source-bound result release is [423271065](https://github.com/Melihakbulut221/nssoc/releases/tag/cloud-results-40178775666-1-tx-phase-reset334-transient-native-initial-p-initial-high), tag `cloud-results-40178775666-1-tx-phase-reset334-transient-native-initial-p-initial-high`. At this audit's single observation the run was still in progress and the release had zero assets. There is no published checkpoint or valid continuation descriptor yet. Do not dispatch another initial process.

## Project inputs are hosted

No workstation directory, local checkout, CAD installation or local archive is needed. `ROOT=/home/runner/work/nssoc/nssoc` is the deliberate GitHub-hosted checkout location, asserted by the controller. The prepared case and model paths under that root are reconstructed on each hosted runner; they are not references to the user's computer.

The exact source is checked out by Actions. The same Python3.12, pinned Python dependencies and CRIU9539417f3e3cfa4eb84c319cd71f4d52f1f08645 are installed in the hosted workflow. Native engine103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509 comes from the hashed runtime archive. Model files and the one OSDI come from the hashed model archive; the complete recursive SPICE include/.lib closure must resolve under the hosted checkout and match the preparation's protected-input map.

The following existing assets were read through metadata only and were present with state=uploaded and the listed size/digest. No archive was downloaded in this audit.

| Hosted input | Asset | Bytes | SHA256 |
| --- | ---: | ---: | --- |
| Frozen native runtime archive | 644932665 | 23540070 | 71a7334475d5d9c18dc01e47661e2ff356a516586e6cc0f1ad1f0e4ae916694b |
| Compact models/OSDI archive | 634990104 | 109934 | 276fbd8b9128750b2f524ec7b0f9e43a45652af62e477a6d618a74ab804a91bf |
| Qualified preparation summary | 674346276 | 11244 | 7a5da3a0e8e7afd80ace24da03365dd4aad223ba9dc4f9fbdedf08bf2b1b9be4 |
| Qualified preparation parts | 674346341 | 889 | df73e849b0aa18cd39816021a0f56b7e8f12cbf32a3dfbab285ebcec574f2de0 |
| Qualified preparation archive part | 674346396 | 356475 | c9f227d485aecdc9d923a148cf91cd36c8c51144bdbdad115c2e7b0c0b6eb365 |
| Actual four fresh318 zero-OP summary | 674456611 | 166304 | 1ea5094100e4815c4ca26dcefcb7457c5a070b1fd849107f9c88cd3293258929 |

Preparation run40171468821 contains the immutable deck/contract and both physical334 RC models. The continuation regenerates the same exact runtime paths and input bytes from these hosted prerequisites, then restores native case files and the saved process. It does not rerun the original four-case preparation or restart the transient.

## Admit a checkpoint only after full publication

1. Read the exact Actions run and jobs. Require attempt1, the exact source/branch/workflow and terminal workflow conclusion=success. Native-step success alone is insufficient because publication follows it. A live, cancelled, failed or partially published run is not a continuation source.
2. Read the release and tag metadata. Require an ordinary commit tag at the exact tested source, target_commitish equal to that source, draft=false and prerelease=true. Never move a tag or overwrite an existing asset.
3. Fetch only the small summary and parts JSON in RAM initially. For this run the stem is `tx-phase-reset334-transient-native-initial-p-initial-high-40178775666-1`. Require exact names `<stem>.summary.json` and `<stem>.parts.json`, exact API asset sizes/digests, and independently compute SHA256 of their original bytes.
4. The saved summary must have status `SAVED_PHYSICAL334_THREE_MODEL_NATIVE_PROCESS_REQUIRES_CONTINUATION_AND_FULL_REVIEW`, case=p-initial-high, native_process_saved=true, sources_unchanged=true, full_capture=false, single_entrypoint=true, the exact engine/controller hashes and next_phase=continue_same_native_process. Require a nonempty checkpoint_images map. Each image hash must match its `outputs["checkpoints/state/"+name]` entry; native_image_sha256 must match `outputs["native-image.tar"]`. Preserve all work/ files, including bench.cir, contract.json, spinit, boots.log and native.log, plus wave.raw if present. Do not summarize away the raw-prefix fields or any partial row.
5. Require parts format=ordered-tar-gzip-parts-v1, exact stem/source_directory, contiguous index/order, exact unique part names, and every listed part present with matching asset size/digest. Sum sizes and retain the combined archive SHA256. This is a metadata admission check, not proof that the raw/archive bytes have been reread.
6. The existing hosted restore must then download and verify every ordered part and the combined archive hash before selected extraction. Its safe tar reader rejects unsafe, duplicate or nonregular entries and verifies each selected member against the authenticated summary. Selection is every work/ and checkpoints/ entry plus native-image.tar and result.json. The controller also verifies the full checkpoint-image inventory and copied-image inventory. Do not replace this with a partial download or selected-column capture.

If the result instead reports complete capture, perform the unchanged full electrical review; do not resume a terminated process. A rejected complete capture remains rejected. A failure with a saved emergency capsule requires separate source-reviewed recovery admission; the normal continuation deliberately refuses failed sources. Publication-only failure should recover already preserved evidence, not rerun the DUT blindly.

## Exact continuation descriptor and dispatch

The source descriptor must contain exactly these eight keys, with types enforced by the existing controller:

| Key | Value for the first continuation |
| --- | --- |
| run | integer40178775666 |
| attempt | integer1 |
| group | tx-phase-reset334-transient-native-initial-p-initial-high |
| source_head | 7398bb00efc4ec6ff053aeb50e03028570f0cfa0 |
| controller_sha256 | db0108b0b553d24d1ce8d4813806f41821bbf607053538a2ebe59127629eb0f0 |
| summary_sha256 | SHA256 of the exact completed original summary bytes; unavailable until publication |
| parts_sha256 | SHA256 of the exact completed original parts JSON bytes; unavailable until publication |
| case | p-initial-high |

Derive these values from the actual terminal evidence, never from guessed filenames alone. For later continuations use the newest authenticated successful saved run and its actual initial/cross group; never revert to an older trajectory. Save the complete descriptor and supporting asset IDs/hashes in a cloud receipt before dispatch.

Before dispatch, check the workflow's current runs and retain a single owned p-high process. Verify the chosen branch HEAD still has the exact controller/support/checker/workflow and protected prerequisite bytes. Documentation-only branch advances are compatible; executable changes require review. Do not use the root branch or a tag as the dispatch ref: normal continuation validates head_branch=codex/tx-clock-phase-parent.

Dispatch the registered workflow once through GitHub API/UI with ref=codex/tx-clock-phase-parent and inputs `mode=native`, `stage=cross`, `source_descriptor=<the exact eight-key JSON string>`. Keep run_attempt=1; do not use Actions re-run. Identify the new run/source from the authoritative API and precreate its release before the dependent native job reaches preflight:

`cloud-results-<new-run>-1-tx-phase-reset334-transient-native-cross-p-initial-high`

The release must point at that new run's actual source SHA. Only the previously audited cloud-results-* evidence tag policy applies. The native job re-runs all source controls through its needs dependency, verifies the exact release before runtime installation, and revalidates the original source run and full archive. The ordinary eight-hour cloud monitor observes status; it does not perform this engineering transition automatically.

## Same-process and numerical conditions

The owned segment budget is13200seconds (220minutes) within the360-minute hosted job. At the segment boundary, or below the unchanged20GiB reserve, the running owned Docker process is checkpointed with CRIU. Initial startup retains the72GiB free-space requirement. A complete process is reviewed rather than checkpoint-resumed.

Cross-host restore requires exact runtime input bytes and absolute paths, Docker command/mount order, image identity, original cpuset availability, glibc tunables, kernel release, architecture, CPU flags, CRIU source/binary/version and native executable hash. A strict mismatch is a refusal; it is not waived or replaced by a cold start. The archived Docker image carries the original shared libraries. The hosted checkpoint copy checks all image hashes before restore.

The boots file must remain exactly one native-entrypoint line. Every prior native-log byte and raw payload byte, including a partial final row, must remain unchanged. Only the original No. Points header field may differ; the vector/header identity and time column0 remain fixed. A continued segment must append complete native rows. Failure to show progress is a diagnostic rejection, not an excuse to restart.

Final acceptance still requires all4727 time-inclusive columns through34ns, the original0.3125ps maximum step, actual318 OFF readbacks, a full4726-state zero OP, all318 HBT safety rows and all three fixed parent/child phase/reset oracles. The original first-fall bound is62.5ps and the signal margin is100mV. No31.25ps proof, all31 clock-tree acceptance, routed reset distribution, real PLL waveform replay, full PHY or main-chip timing is inferred.

## Remaining operational risks and checkpoint scope

- The current live run has not yet published a durable native checkpoint. An abrupt hosted-runner loss before a successful dump/publication can lose that segment's progress; this source does not claim continuous crash-proof checkpointing.
- A saved process is resumable only after the complete evidence is published and authenticated. The140-minute nominal margin is not a guarantee against disk pressure, upload failure or the hard360-minute runner limit. Preserve fallback artifacts and original errors; do not infer complete publication from a partial release.
- Identical future hosted kernel/CPU/CRIU builds are not guaranteed. Compatibility refusal must be diagnosed from the retained capsule; the controller must not be weakened to force a restore.
- Release assets and pinned repository history must remain available. A deleted/changed dependency is detected by its hash and must be recovered from authenticated cloud evidence.
- This is the first actual318 process using the derived portable lifecycle. Source controls and prior8088 lifecycle qualification do not themselves prove this run's future checkpoint/restore.

The inspected root checkpoint was `2ec5dbcec84491c92fe29ae37230c3e8b982728a`, CLOUD_RESUME v34 and monitor inventory34/109handles. It did not yet list the new two transient handles. The parent is preparing v35/115handles including40178169815 and40178775666; this audit does not claim that update was already published. The authoritative owned checkpoint is docs/evidence/tx-phase-cloud-checkpoint-20261024.json and the exact dispatch receipt is docs/evidence/tx-phase-reset334-first-transient-dispatch-20261025.json.
