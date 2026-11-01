# Cloud continuation — checkpoint v251

Updated: 2026-11-01T15:41:41.424855+00:00

Latest instruction: **her şeyi bulutta yap, lokalde bir şey bırakma temizle.**
It overrides the earlier local-execution wording in the active goal. All CAD, simulation, native archive/layout/waveform acquisition and numerical/geometric analysis run on GitHub. Local coordination uses source/API-derived text in RAM only. Never acquire native ODB/DEF/GDS/SPICE/raw archives locally, including RAM. The local workspace and project temp entries were verified empty, with no local CAD processes. Unrelated user files remain untouched.

## Latest result: remaining physical failures classified; original64-pass stage qualified

Cloud run41321744519/source4090f5c3ce1d7655de4144299f69df278a2d7a16 passed16 controls and authenticated all1749 native members from release430648315. Every actual DRC/antenna record is retained. Counts:329 shorts +70 metal-spacing markers =399;19 antenna nets/23 rows. Among320 named owners:92 original diode owners,36 previous counterpart owners,186 outside-scope signal owners,4 protected nets and2 power nets. 369 markers involve an outside-scope signal;6 involve protected nets;13 involve power. All antenna rows lie inside the existing828-net scope. Source reports and42-file proof9663c2bcc94ceae21d7739bc6279740522e53524 are imported under docs/evidence/postrestore-classification-terminal-41321744519.

The actual routing effort was explicitly limited to8 passes by mainchip_bounded_route_stage.py at7a0776718ec37a106b7dfde0cbd477c6a2a5522f, despite the original environment requiring64. Complete the intended effort on the same seed/scope first, so a scope expansion is not conflated with additional router optimization. Existing final399/19/23 rejection remains authoritative until a new native candidate is measured.

New mainchip_full_route_stage.py/source0502f3cbb7e74286d6cb024504d593be04bd778a executes the byte-identical original64-pass Tcl (SHA2564769e146e1bf59e08fb4c08c436d1f0f285de4086f8c72974825305db6fa9a7b). Cloud run41322259020 passed all11 lifecycle controls,0 failures/errors/skips. It preserves partial failures and rejects8-pass programs, stale/symlink outputs, repeated calls, wrong commands/budgets, missing outputs, source drift and false acceptance. Source proof fcde4e2991da08c38e0521c8dd4e2756da787287 is imported under docs/evidence/full64-controls-terminal-41322259020. **No native64-pass run has been launched or accepted.** This will be a new trial from the same saved-diode seed, not a claim of internal router-iteration resume.

Next concrete work: integrate full64 execute_stage after the original828-net clear and before current qualified restoration/connectivity/PG/final audits; fix exact host preservation cases before dispatch. The original cloud_mainchip_saved_diode_routing.perform acquires CURRENT, failed donor41172959321/release429743993 and saved reconstruction41190910993/release429853533 before tail.restore_prefix; do not omit either seed acquisition. The existing scoped-restoration host only replays a saved8-pass route and cannot itself run64. Preserve original frozen source projection, owned container, native runtime and source pins. Adapt new routed-fixed/candidate pins from measured results rather than keeping old hardcoded pins. Keep all1351 diode attachments/1691 protected nets and all original physical gates. Independently qualify combined source, reserve exact-source cloud release, then dispatch exactly once. If using staged routing followed by restoration, preserve original failures and distinguish route completion from full physical acceptance.

No native data is stored locally. Full serial PHY still fails width8 device/data/phase gates; final RC/STA needs the actual current diode-inclusive matching netlist. Goal remains active and unachieved.

## Previous checkpoint v250: completed native audits and rejected candidate

All project CAD, simulation, native data acquisition and analysis run on GitHub. The local workspace and project temporary locations were verified empty; no local CAD processes were present. Source/API-derived text coordination uses RAM only. Do not download native ODB/DEF/GDS/SPICE/raw archives locally.

Actual run 41317927121/source 340fb4f217e920c1bc4d5fa552e4b11eb81d0a4b completed all six native phases: qualified connectivity for 828 nets in both modes, 2702 direct diode power contacts, and unchanged 1691 protected clock/fixed nets passed. The physical candidate is still rejected: 399 DRC markers, 19 antenna nets and 23 violation rows remain. No final timing or full serial PHY acceptance.

The host job is red with three preservation errors: original-clock-gate/before.def and after.def are already authenticated in the native capsule but refused by the derived suffix filter; oversized host-progress.json is outside the native publication prefixes. Preserve these failures and fix the exact output cases with refusal controls in a successor; do not rerun CAD merely to recolor CI. The permanent native release is 430648315, archive SHA256 c9cf1d646a8116c5ddc77dcb0d36838677c9d6243f4db08df9ac17369d65f95f. No candidate data needs a local copy.

Width8 full-wave diagnosis 41319989811/source 7866608fd58ceb372fa927b408ba7087c54d9610 passed 48 controls and reproduced the six original measurements and all device tables. Its proof is imported below docs/evidence/divider-width8-wave-terminal-41319989811. It confirms failure, not PHY acceptance: phase 25.861 mV is below 30 mV; eight HBT limit violations and one aggregate stage-tail current violation remain. Full raw waves stay in release 430594515.

Readout 41320700483 failed because the final*.json selector included the 27 MB all-net antenna table. Corrected source 23a41f2b4c6d057babbffad3dfd3b768f1809e49 uses an explicit bounded-report allowlist and four selection controls while still hashing EVERY archive member. Run 41321233030 is the single dispatched successor; inspect its actual terminal result before relying on its readout.

Next: collect that existing readout, classify the 399 DRC markers and 19 antenna owners on the actual current candidate, then qualify the next physical repair. Export and prove a matching diode-inclusive netlist and fresh RC before unchanged multi-corner setup/hold gates; old route12 netlist/RC is stale. PHY work must address the measured internal divider/buffer/device failures, not declare width-only screening complete. All work continues in the cloud.

## Previous checkpoint v249: qualified native adapter and dispatch

The private adapter is implemented at source 340fb4f217e920c1bc4d5fa552e4b11eb81d0a4b on codex/mainchip-qualified-restoration. It binds the unchanged qualified core to the original native connectivity reader, preserving all original wire-only reports. Candidate ODB bytes and both GDS qualification records are hash-bound. The original source, predicate and graph functions are not mutated. Native source additions are authenticated in the existing source capsule.

Independent control run 41317771048 completed successfully: all 49 restoration controls, 67 inherited graph/GDS/model controls and 12 boundary controls passed. The actual original native reader function body reproduced all 1656 graphs across the authenticated 828-net dataset with simulated ODB accessors. Graph, predicate and scope source files were byte-identical to frozen native dependencies. This is boundary qualification, not actual ODB execution. Complete 48-file proof 26ef125546aa247ab72707f20c04a30c0040ee33 is imported under docs/evidence/qualified-native-binding-controls-41317771048.

**Actual native run 41317927121 is dispatched on that exact source**, with the independent control run supplied. Empty exact-source release 430648315 / cloud-results-41317927121-1-mainchip-bulk-postdrt-antenna was reserved and verified before native admission. The native run's repeated source controls also passed. Poll that existing run and its release; do not restart it merely because observation expires.

The sequence is original class restoration, full restored snapshot / 1691 protected-net audit, qualified physical connectivity, 2702 direct power contacts, final DRC/antenna checks and final unchanged-snapshot comparison. No routing, reconstruction or physical geometry edits were added. The result explicitly names qualified physical audits and retains original_wire_only_acceptance=false. A successfully completed invocation does not establish a zero-violation result; inspect the actual census and bounded_cycle_qualified.

Next: collect and authenticate the terminal native capsule, preserve failed and successful phases, and repair whichever actual physical gate fails. If physical checks pass, export a matching diode-inclusive netlist from the actual current database and extract fresh RC before the unchanged multi-corner timing gates. Full serial Gen3 x4 PHY remains unaccepted. No final timing or production acceptance is claimed.

All CAD, native acquisition and analysis remain on GitHub. No local project files or native payloads are needed. Completed collection, dispatch and reservation recipes are saved in docs/evidence/cloud-collector-recipes-20261029/cloud-qualified-native-v249.json and must not be rerun as creation mutations.

## Previous result: complete 828-net qualified connectivity model passed

Cloud run 41316154727 at source 77247c06db249537a643fb2e6e9a256bdbcfe557 (codex/mainchip-qualified-pin-connectivity) completed successfully. All 67 controls passed: 52 inherited and 15 qualified-model controls. The complete authenticated 828-net dataset passed both overlap modes after replaying all 1656 original graphs. All 142 original wire-only failures and 686 original passes remain preserved. Only the actual 1300 pin observations / 77 master pins independently verified against frozen GDS, LEF and placement transforms were admitted as physical conductors. All 1351 diode attachment requirements remain enforced. No logical-name bridging, inferred vias or geometry edits are allowed.

The pure core is scripts/mainchip_qualified_pin_connectivity.py at that source, with the wrapper scripts/cloud_mainchip_qualified_pin_connectivity.py and 19-file manifest scripts/mainchip-qualified-pin-pins.json. Complete 34-file proof 90231e2a46b2bccd0169c304cddae2b7aa8cade7 is imported under docs/evidence/qualified-pin-connectivity-terminal-41316154727. The successful result is explicitly NOT execution of the native adapter and is not chip acceptance.

**Completed in v249:** the private native adapter is implemented and independently qualified; actual native run 41317927121 is now the authoritative next step, as described above.

Then execute the remaining 2702 power-contact checks and final DRC/antenna checks. Fresh matching-netlist RC/STA and full serial PHY remain open. No native adapter, new physical route, full chip LVS/DRC, fresh RC, final timing, or full PHY acceptance is claimed by this result.

All CAD and analysis stay on GitHub. Local workspace/task temp entries are empty; source/API-derived text coordination uses RAM only. Completed collector recipes are preserved and must not be rerun as creation mutations.

## Previous result: actual GDS pin correspondence passed

Cloud run41314829887/sourceb0cc820906e9cc75c3a7d55fce11297a8e4f1da1,branch codex/mainchip-pin-gds COMPLETED SUCCESSFULLY. All52controls passed (23inherited graph+29geometry/parser/grid controls). Against the authenticated current restored snapshot, all1300pin observations across the142original wire-only failing nets matched77unique master/pin definitions. Native-to-LEF region equality, GDS drawing-metal coverage including polygon holes, and all placed orientation/origin transforms passed. Missing/mismatched pins:0. Both actual SRAM masters RM_IHPSG13_1P_2048x64_c2_bm_bist and RM_IHPSG13_2P_256x16_c2_bm_bist were included. Actual required GDS reference libraries use0.001um DBU,matching the1000DBU/um native database.

All original native archive members from release430583367 and all five original Ciel PDK archives at revisionc4b8b4e5e7a05f375cca3815d51b3a37721fbf5c were authenticated. Actual comparison used only libs.ref GDS/LEF files and the pinned drawing-layer map. No pin-marker layer was counted as conducting metal. Full33-file proof35f96b34545c1db4fef2b963816958337ec1f499 is imported under docs/evidence/restored-pin-gds-terminal-41314829887. Full native layouts remain cloud-only and unchanged. Peak runner RSS2374316KiB.

Earlier run41314212802/source6a256976d29b2dd5d36b1726245b70ee456dca82 passed45controls and authenticated native/PDK inputs, but its reader stopped at a noninteger GDS-to-ODB scale while scanning all PDK GDS files,including QA/test layouts. This was not a measured chip-connectivity failure. Full29-file proofde9dc9a9d34228bb0c134dd73e59db7eee33bb41 is imported. The successor limits candidate material to actual reference-library paths, records units for every GDS, converts only matching master cells on an exact integer common grid, refuses rounding/overflow, and adds7controls.

**Completed in v248:** the explicit physical-conductor core is implemented and qualified on all 828 nets. See the latest result above for the remaining native adapter binding.

The native integration point is scripts/mainchip_scoped_counterpart_restoration_native.py at source05d336a1b1b681c9d96b71d464c5ea430835e438. Its restored-audit clones targeted.bind_phase(plan,scope); that function currently wraps native.connectivity(path,scope_core.observation_scope(plan,scope),out). Add the qualified adapter privately without mutating frozen source functions. Original validate_connectivity returns changed_nets/both_modes_complete and requires every pin/diode to share a single conductive component in both modes. Keep original wire-only reports separate and explicit. Native host source additions must be included in NEW_NATIVE and their source manifest/projection; require independent same-source controls and exact-source empty release reservation before native execution.

Then run the remaining native2702PG-contact, final DRC/antenna and clock/placement preservation audits. Final full-chip timing and fullserialPHY remain unaccepted. No route/database/pin geometry was edited in these read-only diagnoses; no final chipGDS, fullDRC/LVS, newRC orSTA was executed.

Completed collector recipes: docs/evidence/cloud-collector-recipes-20261029/cloud-pin-gds-v247.json. They have already published both proof branches; do not rerun their creation mutations. The full source and primary OpenDB transform references are preserved in each proof. All work remains on GitHub; workspace/task temp are empty.

## Current mainchip result and next repair

Restoration41308526628/source05d336a1b1b681c9d96b71d464c5ea430835e438, release430583367, is a terminal failure. The master representation correction passed for58masters/1666rectangle tuples; serialized before/after SHA25623119c37fd7402fc26de7f2fc59cb6f7db0859a4a82dec7ca62eb205dcf193fa. All1691 original clock/fixed-net records and attached geometry passed unchanged. The next original wire-only connectivity gate rejected the candidate. Power-contact, final DRC/antenna, RC and timing have not completed.

CandidateODB:214409779bytes,SHA256d526feec659883b65dc737853d4d6a192d529384e2676d8a2d17e9b5e7d6de7e.
Native archive:469346574bytes,SHA25665f84c98d2207f238194a97f27728405d3c44f278a85db2837d3b89a04985385, release430583367.
The full1726-member derived artifact and native release contain828 original connectivity graphs and828 restored-owner reports. All1656 large per-net records remain in the native cloud archive; they are authenticated and indexed, not falsely claimed copied into Git. The other95 proof files are already imported under docs/evidence/scoped-restoration-native-terminal-41308526628.

Diagnosis41311644194/source8f8f13a42d0edf2a3d11ef0931351c2974ba9c29 PASSED13controls and exact replay of every failed original graph. Of828owners,142fail the original wire-only predicate:113antenna owners and29counterpart owners. Full22-file proof390b08ec7dbbaeb0009aaf64ecaed3c3d71c0f37 is imported under docs/evidence/restored-connectivity-diagnosis-41311644194. This is diagnosis, not repair.

Pin-metal diagnosis41312549409/sourcea8588f493cc2816fa4e5c601209a4fd89f670dc8 PASSED all23controls (13original+10new) and actual authenticated readout. Adding only the observed ODB/LEF pin-metal rectangles in a separate diagnostic graph connects all142nets, under BOTH positive-area and closed-boundary overlap. Original pin access is missing on0nets;57nets have a single actual pin rectangle that directly bridges original wire components. No joining by logical pin name, inferred via, or unobserved filled gap is allowed. Original wire-only gate and original failures remain unchanged. Full24-file proof1f8da68823e1451c7b04a3a831d57d6b2e6060ce is imported under docs/evidence/restored-pin-metal-diagnosis-41312549409.

**Completed in v247-v248:** actual GDS/LEF/placement correspondence and full 828-net qualified physical connectivity now pass. Remaining native PG, DRC/antenna and matching-netlist RC/STA work is described above.

No new native routing was run during these diagnoses. The saved8-pass router reported397last-router violations; this is not final DRC acceptance. Preserve608diode ownership separately from828routing ownership,1691protected nets,1351diodes and2702required PG contacts.

## Current PHY results

Width2 native41306148937/source2a62d651d415fba8db3c5b758d1b66c05cde3a38, release430565351: actual engine returned0 in863.844793s, no diagnostics. Device/VI gates pass; phase37.0801368476mV passes the unchanged30mV limit. All six data gates fail. Full111-file proof was imported earlier.

Full-wave diagnosis41309130293/sourced516afbe5391c42d1f1e378102116cc593a23680 passed34controls and reproduced every original measurement. At0.6UI all255 A-source values are valid and divider signs correct, but111A-buffer signs are wrong. C/D dividers have64/100 source-valid wrong-sign samples. A bit128 buffer remains old polarity at1.0UI. Full24-file prooff5623ecd4f4b400c63548f01966be8fae753fcbd is imported.

The4um and8um trials independently start from the golden1um parent and change only12rppd widths. All lengths,HBT Nx,200MOS units,ports and electrical gates remain unchanged. Retained wireRC is screening only: no regenerated layout or freshPEX is claimed.

- **4um41310177288/source d86d44b42ab1dca1af333efa65098c872649bb74**, release430594411: source controls passed75new+75inherited refusals and original binding. Native was stopped at the original1200-second engine budget (observed return-15). **No measurement result exists; electrical acceptance/rejection is unknown.** Full110-file proofc8fa7776e54f75ebc84317908b89a681abc524c4 is imported. ModelSHA256ed9291cabadfbad104fe8ed168114d2c000133011491c073e7aa660ba0d6b9a6.
- **8um41310192873/source66fb47bb12eff45c83b3d2819d281f99960ac4cc**, release430594515: actual engine returned0 in934.837169s, no diagnostics. All six data gates, device gate and phase gate fail. Phase25.8611110771mV is below30mV. A/B have64/29below100mV samples; C/D have92/28wrong-sign samples; X/Y have412/60wrong-sign samples. Full111-file proof9bb52e88a8b91196606b747cfa02263f61ad6bef is imported. ModelSHA256a8d8fa39039fe91a3ccca1ba724daef23b7a19c6fa28d551cda346ade90d4175.

Next PHY work must use these actual measured paths and device records to select a circuit repair. Wider dividers alone have not solved the loaded path. If4um completion is still needed, treat any larger execution allowance as an explicit new host experiment with identical model/stimulus/electrical gates, independent controls and exact-source release reservation. Do not present the timeout as a measured circuit failure. Preserve all rejected attempts.

## Timing and full-chip scope

docs/mainchip-restored-route-timing-handoff.md and docs/evidence/restored-route-timing-handoff-v241.json remain source-audit handoff, not executed RC/STA.
Old route12 requires153130instances/zero added diodes and netlistSHA2563c053c4cda51a001b926cce347b97de5c825cbff2082de550eeb9e31ff7fe5cd. Current layout has154480instances. Export and verify a matching diode-inclusive netlist from the current actualODB; old netlist/SPEF cannot be reused.
After physical connectivity and PG validation, generate fresh nominalSPEF, then the unchanged slow1.08V125C/typ1.20V25C/fast1.32V-40C corners,20/4/8/8ns clocks and5%derate. Require nonnegative setup/hold and zero setup/hold/slew/cap/fanout violations with propagated clocks. NominalRC is not foundry RCmin/max qualification.

Full serialPLL/CDR/SERDES, training/LTSSM, replay/credits, lane mapping/descrambling/TX, serial soc_top ownership, complete DRC/LVS/ESD and production approval remain open. Packet-interface SoC routing is not full serialPHY integration. No fullPHY, final timing or production acceptance is claimed.

## Cloud resumption and monitor

Authoritative branch:codex/complete-open-work. This checkpoint imports267files from the four new proofs (22+110+111+24). Existing sources and full artifacts stay on GitHub. Read each exact run before dispatch; do not duplicate jobs after observation timeouts. Current run/job snapshots and source bindings are in docs/evidence/cloud-active-checkpoint-20261024.json. Earlier failure receipts and sources remain intact there.

Eight-hour monitor configuration stays read-only,automatic_native_dispatch:false. Its last saved live observation had an HTTP502 error; do not claim monitor health without a new successful full observation. Two old checks.yml runs41292160619 and41293340525 were still active at the prior snapshot; consult the current API snapshot.

The current pin-metal collector recipe is docs/evidence/cloud-collector-recipes-20261029/cloud-pin-metal-v246.json. It has already run successfully; do not rerun its branch-creation mutations. All numerical/physical continuation remains cloud-only.
