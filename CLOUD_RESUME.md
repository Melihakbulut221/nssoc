# Cloud continuation — checkpoint v242

Updated: 2026-11-01T12:56:53.404555+00:00

Latest user instruction: do all work in the cloud and leave no local project data. This overrides the old goal's local-work wording. All CAD,simulation,native archive/geometry/waveform acquisition and numerical analysis run on GitHub. Local coordination is source/API-derived text in RAM only. Never acquire native ODB/DEF/GDS/SPICE/raw archives locally,including RAM. Workspace and project temp directories are empty; no local CAD processes. Preserve unrelated user files.

## First next task: actual native audit after master representation correction
Run41308526628,source05d336a1b1b681c9d96b71d464c5ea430835e438,branch codex/mainchip-scoped-restoration,release430583367,tagcloud-results-41308526628-1-mainchip-bulk-postdrt-antenna. It was dispatched ONCE after independent successful controls41308125643 and exact-source empty release reservation/readback. Inspect actual run status; do not redispatch after an observation timeout. Native outcome is PENDING here.

Controls41308125643 passed49 actual core/source cases plus all2361 frozen original source pins and three authenticated derived inputs. Preserve source7a0776718ec37a106b7dfde0cbd477c6a2a5522f,original exact OpenROAD ELF/runtime/container and all original geometry/clock/connectivity/diode/final gates. The new core only converts innermost master-pin rectangle tuples to lists,matching the persisted JSON representation. Before/after serialized master bytes must be identical; no sorting,geometry changes,dropped duplicates or reordered coordinates/groups. Every other snapshot object is retained unchanged. Per-native-call master-representation reports record actual tuple counts and hashes.

The original scoped class fix remains: validate608antenna/220counterpart/1691protected/1351diode ownership,keep all828 routed-owner records/connections,restore other temporaryFIXED classes with the original function,and retain complete unowned records/net order/outsideNETS bytes. No new route/repair/reconstruction/stale-wire clear occurs.

Current sequence remains restore-plan,restore-import,restored-audit,candidate2702PGcontact audit,final-check,final-audit. Completing the experiment is not zeroDRC or timing acceptance. Inspect full source/runtime/current/saved-input invariants,cgroup/returncodes,full original1691clock gate,two connectivity modes,all1351diode pins,2702PG contacts,DRC/antenna result and native publication. If a new gate fails,preserve its full evidence and fix the evidenced cause without relaxing predicates.

## Actual prior native result and root cause
Run41305082558/sourcebe65a271b066faeffee86237fa879f5f96b70273 FAILED overall but actual restore-plan and restore-import returned0. Restored expected and actual DEF both186265982bytes,SHA256a5183887cf3733b0c8cf9070af98156596d624a11808e955403daf350b80a36c. CandidateODB214409779bytes,SHA256d526feec659883b65dc737853d4d6a192d529384e2676d8a2d17e9b5e7d6de7e. The subsequent unchanged route-delta validator stopped at "unchanged routed snapshot masters"; original clock/connectivity/PG/final audits did not finish. Full89fileproof08928e966747c93c5fd9a9fd95c3059872cf2ec4 under docs/evidence/scoped-restoration-native-terminal-41305082558 is imported.

Native archive release430558340 has51 authenticated members. Its single421497727byte gzip hasSHA256275b702ebfbe7d0bcbb5e28facceb82386417f606aec759123f9be03733de1fd. Full snapshots remain cloud-only:
insertion627376262bytes,SHA256501e93ae94d2a08477d59f14f8bee320412a0de83578ec1c6ad7a818878e772f;
restored627640193bytes,SHA2567d9512e51de23b4cc927752bf56d969e78b59f5e78f902c6544ece93b7e9a2a5.

Readout41307592168/sourceedd99c33b8ee783afc882b216e88ba7871f5bd13,release430576850,after20 independent controls41307350399,proved all58 persisted master descriptors EXACTLY EQUAL. There are154480instances on both sides. Block,clock_record_pins,diode_template,immutable,instances and protected hashes all match. No master,geometry,layer,coordinate,multiplicity or MPin-order difference exists in the saved JSON. Full27fileproof01464772eb673c65db84070ef44da02af7b7019b and13filecontrols proofd799b06a8233741699f7c3fc9fc47d459ef3a915 are imported.

Source explains the false equality rejection: mainchip_original_clock_drc.master_pin_boxes returns sorted tuples; native snapshot stores those tuples inside masters; the saved insertion JSON decodes them as lists. Python list/tuple equality fails despite identical serialized values. The new49 controls reproduce that failure and ensure geometry/layer/coordinate order/group order/multiplicity/width/pin-type corruption remains detectable. No gate is removed or normalized to success.

## Saved raw routing remains the same
Producer41292673925/source7a0776718ec37a106b7dfde0cbd477c6a2a5522f was terminal failure after bounded8 DRT returned with397 last-router violations. Release430474717 retains728 authenticated members. Raw routed-fixed.odb214409779bytes,SHA256b87a2d43fe33dd8ca99f0faa2bdf38337ae30d6c5b72a337472919ac57f64e63; rawDEF186123105bytes,SHA2560ac5108f828158156a858086a2edaff204020a14e17cb491d0ab173131345511. Pre-routefixed.def185488886bytes,SHA2569f28be4140f481886d501b26370ffcd431ceb8a436de1aff0946ee39573456d5.
Actual precursor diagnosis41302468053 proved220 authorized counterpart class/geometry changes and no selected unowned normalized geometry or connection-prefix changes across143820nets. Keep608diode ownership distinct from828routing ownership. Do not blindly reroute all828 or claim exportedODB persists TritonRoute optimizer history. Once restoration passes,derive the next repair from actual residual DRC ownership/shape evidence.

## PHY: phase improved,whole candidate still rejected
Run41306148937/source2a62d651d415fba8db3c5b758d1b66c05cde3a38,branch codex/cdr-divider-width,release430565351 is TERMINAL REJECTION. Actual ngspice returned0 after863.844793s,zero diagnostics. Device/VI gates pass and phase37.0801368476mV now passes the unchanged30mV gate,improving on the parent29.3294064481mV. All six original data gates remain failures. A/B worstclock-to-valid42.34375/37.96875ps exceed37.5ps; C/D have30/33 wrong-sign samples. X/Y have418/6 wrong-sign samples. Do not treat the phase improvement as full CDR/PHY acceptance.

This candidate changes only12rppd widths1um->2um; all original lengths,HBT Nx and200MOS units remain. ModelSHA2567468f677a97cba341dbdc350ec2a1ab5c70cfd48f1233f81e449e23935b69fc6. Complete111fileproof9da21f3fe75a760e893f6f898eb9240c751c1ee3 under docs/evidence/divider-width-native-terminal-41306148937 is imported. Native waveforms/model/runtime remain on the release,not local. It may be studied as an explicitly unaccepted experimental parent; no regenerated physical layout/freshRC acceptance follows.

Next analog work should use this actual retained waveform to isolate remaining sampler/clock-to-valid and downstream buffer delays. Reproduce original measurements before deriving a new electrical change. The previous40-HBT Nx trial41299745896 remains rejected at20.883396mV and420/34X/Y wrong-sign counts; do not silently retain it. The older12-divider goldenparent modelSHA2560a2ce363d3f8159a290f8642fe3a26c7ac1997ca4d8b934e4530fb4823974ef3 remains separately identified. Four MOS unit widths8/9/8.890/8.885um have independent20-stage physical proof41290670037; that is not whole650-device layout/freshRC. Preserve221original taps.

## Final RC/STA handoff is separately required
Old route12 admission expects153130 retained instances,zero added diodes and pre-diode resized netlistSHA2563c053c4cda51a001b926cce347b97de5c825cbff2082de550eeb9e31ff7fe5cd. It is not directly compatible with the current154480-instance/1351-new-diode route. After actual restoration passes,qualify exact currentODB/DEF and a matching diode-inclusive netlist with original functional connectivity,1691protected records,all1351diode pins and2702PG contacts. Do not delete the old assertion or substitute an old netlist. See docs/mainchip-restored-route-timing-handoff.md and docs/evidence/restored-route-timing-handoff-v241.json.

Preserve original numerical RC/STA behavior and separate physical/timing decisions. Fresh nominal SPEF on the actual restored route is required. Three cell corners remain nom_slow_1p08V_125C,nom_typ_1p20V_25C,nom_fast_1p32V_m40C;20/4/8/8ns clocks with5percent derates. Require nonnegative setup/hold slack and zero setup/hold/slew/capacitance/fanout violations,propagated clocks and full reports. NominalRC alone does not qualify foundryRCmin/max,full-chipDRC/LVS or production approval.

## Unchanged full objective and limits
Full serial PLL/CDR/SERDES,training/LTSSM,replay/credit,lane mapping/descrambler/TX and serialsoc_topownership remain open. Packet-interface SoC layout is not full serialPHY integration. Authorized specification access request is already pending; do not repeat it. No silicon/radiation/production approval.

UI125ps; samplers100mV/37.5ps; XOR100mV/75ps. HBTactiveVCE>=0.4V,absVCE<=1.6V,absVBE<=1V,strictIc/emitter<3mA using actualNx. MOSterminal<=1.32V,activeVDS>=0,individualtailcurrents>=0,sixteenstagecurrent-sums>=0.5mA. SevenMIM<=1.6V; phase>=30mV; PLL62.5ps. Never relax these to label completion.

## Evidence handling and continuation
The current native terminal collector is saved in docs/evidence/cloud-collector-recipes-20261029/cloud-master-restoration-v242.json. Run it only after authoritative terminal status. It preserves all selected derived text/log/source files and verifies native release parts by metadata only. Seventeen explicit container/bootstrap records are artifact-authenticated but outside the native capsule index; this distinction is in the prior receipt. JSONL supervisor events are fully preserved and parsed. Do not download the native artifact or release archive locally.

Create proof branches directly at final[skip ci]commits; no temporary branch at an old tested commit. Never retry uncertain mutations blindly. Whole-repo recursive Git trees truncate; traverse bounded subtrees and verify imported subtree hashes. All failed controls/native results remain preserved.
Inventory665runs. Eight-hour cloud monitor is read-only,automatic_native_dispatch:false. Full goal remains ACTIVE and UNFINISHED.
