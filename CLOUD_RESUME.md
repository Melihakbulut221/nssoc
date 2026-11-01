# Cloud continuation — checkpoint v238

Updated: 2026-11-01T11:41:05.379638+00:00

Latest user instruction: all work in the cloud; leave no local project data. It overrides the older goal's local-work wording. All native acquisition, CAD, geometry analysis and simulations run on GitHub-hosted runners. Local coordination is source/API-derived text in RAM only. Do not acquire native archives, ODB/DEF/GDS, transistor models or waveforms locally, including RAM. Workspace/project temporary entries are empty, with no native CAD processes.

## First next task: repair scoped class restoration against the saved route
The actual saved-route diagnosis is now COMPLETE: run41302468053/source7e465ee49cb69783919e14ba17fa3f6dd76c3f09, branch codex/mainchip-route-class-diagnosis, release430540422. Independent controls41302309403 passed26 checks. Full safe text proof3a41a57034270dd8a6bbef69334725035d6105db, prefix docs/evidence/route-class-native-terminal-41302468053. Complete per-record catalogs remain on that release with their exact hashes in complete-output-index.json; the91.8MBcatalog was not downloaded locally.

Actual143820net comparison:608 original antenna/diode owners,220 separately authorized counterpart routing owners,1691protected clock/fixed records. Original class map covers143212 selected records:142878 FIXED->FIXED,220 FIXED->ROUTED,114 unwired->unwired. Exactly220 records changed normalized geometry; ALL are authorized counterparts. Zero normalized changes outside counterparts, zero connection-prefix changes, exact net order and exact bytes outside NETS. All220 strict restoration failures are in counterpart scope. First failure is $abc$1804206$new_n104941.

Root cause: the original targeted clear explicitly removes/reclassifies608+220 wires to ROUTED. The immutable antenna plan correctly remains608 owners. The inherited restore_plan still calls the original restore_classes on the complete non608 class map, including220 authorized counterparts now legitimately ROUTED. Original restore_classes requires FIXED for every wired selected record and therefore rejects those220. The scope adapter updated clear and restored-audit ownership, but did not adapt restore-plan.

Implement a scoped restoration plan using the unchanged validated targeted scope. Validate143820 total records, the original608/220/1691/1351 census and full original plan digest. Preserve every current828 routed-owner record and its connections. For220 counterparts require original classROUTED/currentROUTED; preserve their new geometry. Restore the remaining temporary FIXED records through the unchanged original function. Check all remaining selected normalized records against pre-route fixed.def, maintain exact outside-NETS bytes and net census/order. Do not weaken any original clock/geometry/connectivity/diode/final-gate validator.

Then perform actual native OpenROAD restore-import, restored-audit, final-check/final-audit against this SAVED route, using the original exact engine and authenticated runtime. Actual source scripts: mainchip_bulk_postdrt_antenna_native.restore_plan and its phase('restored-audit'); mainchip_targeted_counterpart_routing_native.bind_phase already supplies expanded route_delta/fullDEF/connectivity ownership. Restore-plan integration is NOT implemented yet. Do not claim a DEF plan proves native ODB readback or final signoff.

## Saved route to reuse, not reroute blindly
Producer41292673925/source7a0776718ec37a106b7dfde0cbd477c6a2a5522f completed FAILURE. Release430474717/tagcloud-results-41292673925-1-mainchip-bulk-postdrt-antenna contains the complete native archive. The bounded router returned and saved all four raw DEF/ODB checkpoints. Last router count397DRC; restored/final audits never ran.

Raw routed-fixed.odb / route-partial.odb:214409779bytes,SHA256b87a2d43fe33dd8ca99f0faa2bdf38337ae30d6c5b72a337472919ac57f64e63.
Raw routed-fixed.def / route-partial.def:186123105bytes,SHA2560ac5108f828158156a858086a2edaff204020a14e17cb491d0ab173131345511.
Pre-route fixed.def:185488886bytes,SHA2569f28be4140f481886d501b26370ffcd431ceb8a436de1aff0946ee39573456d5.
Full archive751995332bytes,SHA256136e2aaa710f7e51c2ed31ef42054309a7c2c13be7a85e2d849db8cfbeaf436f; all728members authenticated by actual reader.

Class restoration and397DRC remain open. A saved ODB proves retained geometry, not persisted TritonRoute optimizer history. Qualify further routing against the restored snapshot; do not blindly repeat all828 stale-wire clears. See docs/mainchip-routing-restart-review.md and docs/mainchip-bounded-route-terminal.md.

Initial reader41301914645 stopped before DEF comparison because it incorrectly expected828 entries in the608-owner antenna plan. Failure proof750b7c23d9decb159d3d3290bb101c4765c666b7 is preserved. Initial controls41301583231 failed on an unwired-only synthetic fixture that omitted the original restorer's required wired replacement; corrected22controls41301770098 and later26controls41302309403 passed. All failed evidence is retained, not reclassified as a pass.

## PHY latest attempt is rejected; no native PHY run is currently active
HBT-load native41299745896/source12f3e0f3bf7010289dc0f993ac71dbfa55cc19e4 is TERMINAL REJECTION. Engine0,1059.425s,zero diagnostics; original device and VI gates pass, all six data stages fail, phase20.883396mV fails30mV. The40-HBT Nx reduction made phase worse than the divider parent's29.329406mV and increased X/Y wrong-sign counts to420/34. Do not carry it forward as an accepted electrical or physical candidate. Full113fileproof221c55f256afab55630d4e8cb1903ab4e1b3d942/prefixdocs/evidence/hbt-load-native-terminal-41299745896; native release430521829 remains cloud-only.

The previous12-divider/200MOS parent41295928971 also remains rejected. Golden parent modelSHA0a2ce363d3f8159a290f8642fe3a26c7ac1997ca4d8b934e4530fb4823974ef3. Native proof19d07ce5f55be3d0c09014f56df9e76a51c9aa1a. Next analog work must use actual waveform/current evidence to address sampler and downstream delay; no limit relaxation or unsupported single-wide MOS return. Corrected reader41298781054/sourceeb9b2602db8d971e405310142ab88d3fc652d308 reproduced original measurements with33controls. Its earlier phase-loop-variable bug in41298254630 remains rejected and preserved.

Four actual MOS unit widths8/9/8.890/8.885um passed20native stages in41290670037:four zero-DRC,eight unsimplified deep/flatLVS,exact junction parameters,eight negative controls. Proof6e9362d5c95e1c2b2fca62d9c71aec8ac4e099e4/release430461761. This does not prove the whole650device layout/freshRC. Preserve original221taps; do not blindly add200tap wrappers.

## Unchanged acceptance and full remaining objective
UI125ps; samplers100mV/37.5ps; XOR100mV/75ps. HBTactiveVCE>=0.4V,absVCE<=1.6V,absVBE<=1V,strictIc/emitter<3mA using actualNx. MOSterminal<=1.32V,activeVDS>=0,individualtailcurrents>=0,sixteenstagecurrent-sums>=0.5mA. SevenMIM<=1.6V; phase>=30mV; PLL62.5ps. FinalSTA20/4/8/8ns+5%,threePVT,zero setup/hold/transition/capacitance violations.

Full serial PLL/CDR/SERDES,training/LTSSM,replay/credit,lane mapping/descrambler/TX and serialsoc_top ownership remain open. Packet-interface SoC layout is not full serial PHY integration. No production/silicon/radiation approval. Authorized specification access request is already pending; do not repeat it.

Use separately successful same-source controls and independently created/read-back empty exact-source release before native acquisition/dispatch. Never blindly retry dispatch or publication after timeout. Proof branches start at their final[skip ci]commit. GitHub's whole-repo recursive tree listing now truncates; use bounded subtree traversal and compare imported subtree Git hashes.

Inventory655runs. Eight-hour cloud monitor remains read-only,automatic_native_dispatch:false. Full objective remains ACTIVE and UNFINISHED.
