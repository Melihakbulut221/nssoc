## 2026-10-16 — Source-bound joint setup/hold driver diagnosis staged

New setup-hold-driver-review-cloud restores exact completed fifty-buffer global STA and the96target/576path conflict trace. It ranks measured weak-driver load stages (>=0.1pF,>=0.5ns) on reported negative slowsetup paths, and records whether each stage is also on any of the96reported fasthold paths. Thresholds select diagnostic candidates only; absence from these reported min paths is not a safety proof. Exact original phase/path/slack summaries and archive hashes must match; all raw stage rows and failures remain in the result. Use the evidence to choose jointsetup/hold repairs rather than indiscriminate delay insertion. Existing fourbranch hold and PLL/full32 jobs remain live; do not duplicate them. Cloud-only.

## 2026-10-16 — Contact repair verified; four SRAM hold branch experiment LIVE

**The25prior cross-net shape overlaps are closed within the exported-signal geometry scope.** Physical108-net repair **38835470494** and independent geometry **38838028482** completed: **3,322,234shapes/113,606nets**, zero cross-net contacts, zero continuity failures, and **113,498originalfixedwires byte-identical**. This does not claim PG/CUT/internalmacro/spacing/foundryDRC/transistorLVS. Antenna remains645nets/801pins. Endpoint38838026271 gives slowsetup-8.010138ns, fast hold-0.169942ns/96endpoints (5new versusoriginal), no lostconstraints. Annotation38838030769 matchesall113606SPEFnets,0loadedunannotateddrivers. Full receipt: `docs/evidence/cloud-protected-contact-repair-results-20261016.json`. Candidate is NOT adopted as timing/signoff success.

Four measured SRAM hold branch repair **38837758293/job116770585137**, source **3340a780106fc391adccd2d58f60ffdd6301e3a7**, is LIVE. Exactparent38824521607 has50addedcells and zero signalcontacts; four sg13g2_dlygate4sd3_1 additions make54cumulative additions. All113841parentcellgeometry/otherpins/PG/NDR stay exact; original-to-final logic and inversion control, fullreroute, postroutecell/pin proof, freshRC and unchangedSTA are mandatory. Recipe/alteredevidence/runtime/compile controls passed. Do not duplicate this live job.

Independent reviewers support `measured_hold_batch` only with pinned parent/source and postrouteproof. Endpoint reviewer source **0b464ebf8179bee2f526477981a590d8cf1df267** additionally compares all22544endpoints against the exact50cell parent (38835900898) and originalbaseline; all four targeted hold repairs require nonnegative hold AND setup at all originalcorners. Controls **38838421565** passed, including newsetupfailure,missingconstraints/missingtarget and changedparent rejection. Run all3independent workflows after physicalcompletion using exact new summary/manifest SHA256. The other92jointsetup/hold failures remain open.

FullserialPHY and finaltiming remain open; PLL/full32captures remain live (see JSON snapshot). Work is cloud-only; localproject0entries.

## 2026-10-16 — Four measured SRAM hold branches staged on the exact50-buffer parent

New measured-hold-eco workflow inserts four sg13g2_dlygate4sd3_1 cells only at the native mapped SRAM input branches from completed96target/576path trace38836226947. Parent is exact38824521607 (50addedcells), with independently verified zero signal contacts/continuity failures. The new candidate contains54cumulative addedcells and4stage additions; all113841parentcells/PG/NDR and allotherpins remain exact. Reproduce both original baseline and parent STA, prove original-to-final Boolean equivalence plus inversion rejection, full reroute, post-route geometry/pin proof, freshallnetRC and unchanged originalcornerSTA. The candidate is NOT accepted by experiment completion; allendpoint/geometry/annotation profiles now support this cumulative54-cell candidate only with pinned parent and post-route proofs. All92other hold/setup conflicts stay open. Do not duplicate the push-triggered physical job. Cloud-only; no local checkout.

## 2026-10-16 — All96candidate hold conflicts measured; next repair targets identified

Native trace **38836226947** completed successfully on the actual50-buffer routed candidate38824521607. All **96hold endpoints /576original-corner min-max paths** exactly reproduce native raw-SI timing; no missing requests, no changed constraints, no source drift. Summary SHA256 `9bd5d1a86cb83d83d8df5505e1a7cf47c1fc086ef45431274798083749709348`. Full trace and exact native pin mappings are in `docs/evidence/cloud-measured-load-hold-conflicts-20261016.json`.

**92targets also fail setup.** Do not insert indiscriminate endpoint delays. The four positive-setup targets are Ethernet RX SRAM bank4 A_MEN (slow setup+1.664060ns/fast hold-0.082131ns), bank6 A_ADDR[5] (+3.049428ns/-0.180218ns), bank7 A_ADDR[5] (+3.044847ns/-0.176063ns), and bank7 A_MEN (+2.161792ns/-0.077772ns). These are measured opportunities for targeted branch delay experiments, not proven repairs. Use native mapped instance names (including their real escapes), not textual escape stripping. Preserve allothercells/pins/PG/NDR, prove logic including a negative control, then legalize/reroute/reextract and measure all endpoints/corners. The other92targets need setup/hold repair together; fullPHY/finaltiming remain open.

The108-net contact repair38835470494, full1usPLL38813902351 and full32captures38810163678/38834025040 remain the existing live jobs; inspect before duplicating. All completed3/50-buffer candidate independent results are preserved. Cloud-only; local workspace empty.

## 2026-10-16 — Both unprotected reroute candidates independently measured

Physical50-buffer **38824521607** and3-buffer **38822066992** completed. Their allendpoint/geometry/RC-annotation checks also completed: respectively **38835900898/38835903867/38835906929** and **38835909902/38835913004/38835915870**. Full receipts, summaries and immutable archive hashes are in `docs/evidence/cloud-unprotected-load-candidates-20261016.json`.

Both have zero signal continuity failures, zero cross-net signal shape contacts and zero loaded unannotated drivers. The50-buffer route has3,317,801shapes/113,606exportednets and antenna644nets/805pins; the3-buffer route has3,323,261shapes/113,559nets and antenna620nets/781pins. This does not establish PG/CUT/internalmacro/spacing/LVS/qualifiedRC or production acceptance.

Neither is adopted. Fifty-buffer worst slow setup=-7.694043ns, fast hold=-0.180218ns: fast hold91→96 (7new/2resolved), typical setup1285→1311 (50new/24resolved). Three-buffer worst slow setup=-11.085521ns, fast hold=-0.130130ns: fast hold91→87 (0new/4resolved), typical setup1285→503 (24new/806resolved), slow setup9601→9377 (8new/232resolved), fast setup53→55. No loss of constraints; all per-edge/per-corner regressions remain saved.

New all-candidate hold-conflict reporting passed controls **38836124406**. Native trace **38836226947**, source **6895e40f0777d79f04acc19100b4fe2d12ecfcd7**, is running on the50-buffer candidate. It reports every negative-hold endpoint's min/max paths at all original cell corners, preserves missing constraints, and requires exact raw-SI/native-report agreement plus full original candidate timing reproduction. Use this evidence for joint setup/hold repair; never mask failures by shifting constraints.

The108-net contact repair **38835470494** remains a separate live experiment; do not duplicate it. Full1us PLL and full32 Sparse captures remain active (see current JSON snapshots). FullPHY/finaltiming are open. All work is cloud-only; local directory remains empty.

## 2026-10-16 — 108-net contact repair is LIVE after controls

Run **38835470494**, job **116763502825**, source **376793a946b712d1b25e5919af165ba65647b70b** is in the native repair step. Source recipe/legacy profiles, runtime, compilation, archive alias checks, and five contact-release corruption controls passed. Do not duplicate or interrupt this live job. It releases the exact eight independently measured intersecting original nets, routes108nets and requires113,498other routednets to remain byte-identical. This is an experiment, not acceptance. After completion obtain new exact summary/manifest SHA256 and run all three independent candidate workflows.

Completed independent endpoint and geometry results are archived in `docs/evidence/cloud-protected-load-independent-results-20261016.json`. Prior protected50 candidate is rejected: setup worst improves to-8.012368ns, but fast hold reaches-0.172269ns/96endpoints (5new). Contact screen finds25shape overlaps across8netpairs, and antenna645nets/801pins remains. NativeDRT0 was not sufficient; no failure was waived. Full serialPHY, routed final physical acceptance and final timing remain open. Cloud-only, local directory0entries.

## 2026-10-16 — Protected candidate rejected by independent contact screen; repair staged

Protected50 candidate38830273683 has **25 area intersections across8different-net pairs**, despite nativeDRT0. Independent geometry38834266592 measures3,322,536shapes/113,606nets, zero continuity failures, but the contact screen fails. Antenna remains645nets/801pins. All endpoints38834263964: slow setup9601→9539, typical1285→972, fast53→31, no new setup violations; fast hold91→96 with5new failing endpoints, no lost constraints. It is NOT accepted.

Cloud diagnosis38835042687 reproduced all25intersection rectangles from exact shape records and identified8protected wires touching6changed/new routes, allwire/via contacts (no pin-contact waiver). Exact diagnostic bytes are pinned in `cloud-protected-contact-diagnosis-20261016.json`. New protected-contact-eco workflow releases only those8additional originalnets and reroutes108nets, requiring exact preservation of113,498remaining encodedfixedroutes, alloriginalcells/pins/PG/NDR, logic/inversion controls, freshRC and unchangedSTA. Original protected50 mode remains the default. Independent validators accept the108-net variant only with the exact eight-net diagnosis and matching proof; five corruption/omission controls precede native execution. This is a repair experiment, not signoff; run allendpoint/geometry/annotation checks after completion. Do not duplicate its push-triggered run.

Other live analog/unprotected experiments continue. FullPHY/finaltiming remain open. Cloud-only; local workspace empty.

## 2026-10-16 — Protected 50-buffer routing completed; independent checks running

Run **38830273683** completed with zero native detailed-route violations and exact preservation of **113,506 encoded FIXED nets**; 100 changed/new nets were routed and all 113,606 nets received fresh nominal extraction. Logic equivalence within its recorded scope passed and the inversion negative control was rejected. The candidate is **not adopted**.

Worst slow setup improves from **-11.940513 ns to -8.012368 ns**, but worst fast hold worsens from **-0.151066 ns to -0.172269 ns**. Typical hold stays positive at +0.005612 ns. The next setup bottleneck contains NAND4 output `$abc$1705011$auto$blifparse.cc:397:parse_blif$1750069/Y` (0.293938 pF, 4.205165 ns stage delay). The worst fast hold path reaches Ethernet RX SRAM bank6 A_ADDR[5] through added buffers46/25/39. The full native log was reconstructed byte-exact from the completed hosted job and checked against its saved SHA256; both raw paths are retained in `docs/evidence/cloud-protected-load-results-20261016.json`.

Independent RC annotation **38834269406** completed: all 113,606 SPEF nets match native IDs/names; 1,065 reported drivers comprise 302 no-sink plus 763 disconnected, with zero loaded unannotated drivers. This is not interface/qualifiedRC/SRAM/signoff acceptance. Full endpoint comparison **38834263964** and geometry/antenna **38834266592** were dispatched with exact source summary/manifest hashes. Inspect their current states before starting followups.

Corrected Sparse0.5ps full tree run **38834025040** is live after controls38833953558 passed. Prior38810158966 failed publication, with no retained component report; old fine0.25ps38810163678 still runs and may hit the same publication bug. Do not duplicate it. Full serial PHY and final timing remain open. Work stays cloud-only; local workspace is empty.

## 2026-10-16 — Cloud publication failure diagnosed and corrected

Run 38810158966 (Sparse 0.5 ps) ended with failure solely in the publication step: its group `vbic-tree32-full-sparse-0.5` violates the existing strict publisher group syntax. The native step exited successfully, but its detailed component result and waveform were not published; do not infer gate acceptance. The job log records the 1,445,509,953-byte archive SHA256 `74afb596098d79b13245612425bc2c1c7390895839ca8a4418051502f022c759`; these bytes are not recoverable from a hash alone.

The workflow now encodes the decimal point as `p` in the release group only, with all four backend/step publication combinations checked before native execution. Original filenames, simulation inputs, acceptance gates and the strict publisher validator are unchanged. The step-comparison downloader uses the same release encoding. Push runs controls only. After controls pass, dispatch a replacement 0.5 ps run with the original Sparse source study and unchanged inputs; do not repeat the old source revision. The already-running 0.25 ps run uses the old workflow and may encounter the same publication failure; do not duplicate or interrupt it, inspect its terminal result first.

Other five jobs were still in progress at this check: 38830273683, 38824521607, 38822066992, 38813902351 and 38810163678. Local workspace remains empty. All computation and artifacts stay on GitHub. Full serial PHY and final timing remain open.

## 2026-10-16 — Candidate RC annotation diagnosis completed

The independent annotation run **38832826137**, native job **116755292822**, completed on the two-buffer candidate from run **38813118414**. Source commit: `aace2ad0375333cf86eaf5232bdc830e54a5a6b2`.

All **113,558 SPEF nets** matched their native ODB net IDs and exact escaped names. Of **1,065 unannotated drivers**, **302 have no sinks** and **763 are disconnected**. There are **zero loaded unannotated drivers**. All selected source hashes remained unchanged. The full receipt is `docs/evidence/cloud-two-buffer-annotation-results-20261016.json`; summary SHA256 is `f49d15621be8b38999efe2c6a0bfb599eb8e0771aa1c3b6e0c81de9887fc54ad`, manifest SHA256 is `3e7c37c111a6fc9ca6c237c10322cd8370b5bf3463b3fe24af43bf050576e381`, and archive SHA256 is `3fabe3f1d4b60228406f08251c9fe40a5c3de8c8aae5bf31fe56584562e8a6fc`.

**The candidate remains rejected.** Its independent endpoint comparison still shows new hold/setup violations, and its geometry audit still reports **634 antenna nets / 783 pins**. This annotation diagnosis does not establish complete functional interface coverage, qualified RC corners, SRAM characterization, full serial PHY integration, or final timing acceptance.

The reusable `candidate-annotation-cloud` workflow passed controls in run **38832681479** and a real native candidate measurement in **38832826137**. It supports the two-buffer, three-buffer, measured 50-buffer, and protected 50-buffer profiles. The original annotation audit keeps its original defaults; candidate mode derives the complete driver count from the native report instead of assuming that it remains 1,065.

For each newly completed physical candidate, verify its exact summary/manifest hashes, then run all three independent checks: endpoint timing, candidate geometry/antenna, and candidate RC annotation. Preserve all failures. Check the six existing native jobs in `docs/evidence/cloud-current-checkpoint-20261016.json` before starting anything; do not duplicate a live job. Full PHY and final setup/hold remain open. All execution is cloud-only, and the local project directory contains zero entries.

## Completed-candidate RC annotation diagnosis staged

Newcandidate-annotation-cloud uses exactsame2/3/50/protected50sourcepins andlogic/0DRV/freshRC provenancegates. ClassifiesALLnativeunannotateddriversfromarchivedfreshSTAagainstexactnativeODB/SPEF IDs+writerescapednames; no reverseescaping. Originalannotationhelperdefaultunchanged113791cells/113863nets/113556SPEFnets/1065drivers; source-verifiedECOmode supports2/3/50addedbuffers andtakesdrivercountfromstrictnativeheader, notassumed1065 (soaddedloadedfailurescannotbehidden). Everyloadedunannotateddriverretained, no coverageadoption. Controlsrunonpush; realcandidateonlydispatchafterterminalphysicalsourcepins. Sameprotectedrouteproofrequired forprotectedprofile. Other6nativejobsremainlive, cloudonly/localempty.

## Independent two-buffer candidate geometry complete; timing rejection unchanged

38831638119/job116751875921 source9f1b5fc03ace7a69c6b9569f20ee3ce0a9ba37ff COMPLETE onactualtwo-buffer38813118414.113793cells/113865nets,113558exportednets,3322143shapes:0continuityfailures,0crossnetsame-layercontacts. Nativeantenna634nets/783pins remain (baseline651/809). summarybcca031bfb05f6a176594fb14a2223a41bad394b2bfbc0883e785fb09fb70a99; partsf7513f21a958b7d90498202af6d60d8e2b0ce37cdb5780221467d3cbe3864dc5; archive61599afc7ce22ca6a4f7629ee056e90a8dae752368de65ac9886ef470f1a8cf8. NOTADOPTED:allendpointfast hold91->94/newtypicalhold andfastsetupregressions unchanged. NoPG/CUT/internalmacro/spacing/foundryDRC/transistorLVSclaim.

Originalcontactscreen38831097775 COMPLETE0 acrossall3323078shapes/113556nets. Candidategeometrycontrols38831504333 PASS andrealcandidateworkflowvalidated. Usecandidate-geometry-cloud forcompleted3/50/protected50 with exactsourcepins, alongsideallendpointtimingcomparison.6nativeECO/analogjobs freshlychecked; seejsonhandles/statuses, don'tduplicatelivejobs. FullserialPHY/finalsetupholdremainopen. Cloudonly; local0entries.

## Original contact screen COMPLETE0; candidate geometry workflow staged

38831097775/job116749810923 sourcea757f8a37a8b3bb9f059c0464ebd6e68c8c55925 COMPLETE: all3323078exportedshapes/113556nets/7metalayers,0crossnetareaoverlap/0boundarytouch. Exact84pairintegeroracle across3chunksizes/layers/ownerspassed. summary734aba3ffcced475256854fbfe90fad6a541e1890bedf7b7d5733eabd581bc71; fullreceipt cloud-routed-signal-contacts-20261016.json. NOTPG/CUT/internalmacro/spacing/foundryDRC/LVS; antenna651andfinaltimingstillopen.

Newcandidate-geometry-cloud controlsrunonpush, fullnativegeometryonlydispatchaftercompletedcandidatepins. Supports2/3/50/protected50 with exactsummary/parts, source/logic/inversion/0DRVgates; protectedcandidate additionallyrequiresunchanged113506wireproof+pinnedconversionreceipt. Nativeexport sizeconfiguredonly0/2/3/50, originaldefaultunchanged; all55NDR andnativewidth/lengthguardsretained. Newcandidate nativeplacement+antenna, exhaustivecontinuity/contactscreens preserveallfailures. Noadoption. Existing6ECO/analogjobscontinueunchanged/cloudonly.

## Independent signal-metal contact baseline staged

Existing6nativeECO/analogjobs were verifiedlive; no duplicateorinterruption. Newrouted-contacts-cloud restores exact38810969514geometry export (3323078shapes/113556nets) and checksall same-layerintersections betweendifferentnetrectangles, includingwire/patch/via-metal/LEFpins. Exactintegertouch/areaoverlap, no spacingtolerance; allpairsretained. PerlayerSTRtree queriesboundmemory; randomizedindependentintegeroracle+chunk/layer/ownercontrols required. This preparesindependentphysicalchecking of fixedroute/newbufferinteractions; nativeDRT0alone notsufficient. It isNOTPG/CUT/internalmacro/foundryspacing/ESD/transistorLVS orproductionacceptance. SourceShapely2.1.2STRtreedocs https://shapely.readthedocs.io/en/2.1.2/strtree.html . AllrunsonGitHub; localempty.

## Corrected protected50 repair LIVE after all alias controls PASS

38830273683/job116747226072 source5393c86a523555b688d98457d9b55e5b48b0a8c9 active in nativephysicalstep. Recipe/legacyprofiles, exactruntime, compilation andstrictaliasrestorer positive+7negativecontrols PASS. Completedfailedpredecessor38830085032/job116746617665 source0e3b6885d16f18c4d9c9d2b4c6bc66f59df7bb1b stoppedinfixture becauseorderedparts require.tar.gz.part0000; correctedfixturefilenameonly, then dispatchedafterterminalfailure. Original38829185736 aliasarchivefailure retained. Defaultstreamrestorerunchanged, noFSlinkscreated bynewrestorer; allsource/payloadhashesrequired. Nativefixedconversion38828562698 remainsCOMPLETE exactDEF/decodedshapeproof. Allendpointcomparator38829407756 controlsPASS/fullcomparisonpendingphysicalresult. Other50/3ECOandPLL/full32jobsremainlive. FullPHY/finalsetupholdnotclosed. Allworkcloudonly; local0entries.

## Protected physical run stopped during archive restore; corrected replacement staged

38829185736/job116743711129 FAILED beforephysicalediting: originalfixedcontrolarchive contains hardlinkalias entries created byos.link for independentshapeinputs; strictstreamreader rejectednonregularentry. The previousheader sayingactive was written acrossjobcompletion; this supersedesit. Failure29762c289c38bd81ebce069e0ffc3098fab0668c4b52727e7704f73ab80a114a andarchivee180123cebdeea44a9fd07ba7b89024d15cb16316e7326e2172c0b891b13c6cc retained. Newdedicatedrestorer verifieswholepinnedonepartarchiveandallpaths/types; directregularhardlinkreferents requireequalpinnedinventoryhash; writesonlyselectedregularbytes, nevercreateslinks. Defaultstreamrestorerunchanged; sevennegativecontrolsguardaliasrestoration. Ownprotectedworkflowpush startsreplacement. Fixedconversiongeometryproof38828562698 remainscomplete; comparatorcontrols38829407756 PASS. Fivepriorphysical/analogjobsunchanged. Localempty/cloudonly.

## Protected-route experiment running; allendpoint comparison controls passed

38829185736/job116743711129 source57f5ee9b3d0b8603e7e299b83a3bafce3bb8adc5 active after50target/legacyprofilechecks, native runtime andcontrollercompilationPASS. Physical50repairwith113506protectedfixedroutes executing; nofinalresultyet. Endpointcomparatorcontrols38829407756/job116744433096 source9aea6ddf7eb6be4544e121aa5da8a8b6284044a3 PASS; fullcomparisoncorrectlySKIPPEDonpush. Native fixedconversionproof38828562698 COMPLETE exactDEF/decodedgeometry. Otherunprotected50/3andPLL/full32jobsremainlive; don'tduplicate. Next inspectterminalphysicalcandidate, requireits protectedrouteproof/0DRV/freshRC beforeall22544endpointcomparison. FullserialPHY/finaltimingnotclosed. Cloudonly; local0entries.

## Protected50-load physical experiment LIVE; independent comparator extended

Protectedload38829185736 source57f5ee9b3d0b8603e7e299b83a3bafce3bb8adc5 islive. Same50measuredoutputs;113506originalfixedroutes kept; exactrawopcode/data wirehashesafterplacementandDRT, originalcells/pins/PG/NDR proof, logic/inversioncontrols,0DRVs/freshnominalRC mandatory. This is distinct fromunprotected50run38824521607 and3buffer38822066992, bothstilllive; no duplicates. Fixedconversion38828562698 COMPLETE exactfullDEFandindependentgeometryequality; detailedreceiptpinsallnativeproof. Independentendpointcomparator nowaccepts protected_load_batch andrequires exactprotectedrouteproofandpinnedconversionreceipt. Onlycontrolsrunonpush; dispatchactualcomparisonaftercompletedphysicalcandidatepinsavailable. Originalotheranalog38813902351/38810158966/38810163678 live. FullPHY/finaltimingremainopen, noadoption. Everythingcloudonly; local0entries.

## Encoded FIXED control COMPLETE;50-load repair with unchanged routes staged

38828562698/job116741694567 source9a88fcd9c4fded3ae7d46c071e083a04d749bb0e COMPLETE. All113556routes FIXED; full130481394byteDEF exactlyexpected (0differinglines) and independentlydecoded3M+shapeJSON byteidenticalSHA c9e0e1b926d817b1e52edc414d34fe09d4e27bd445d903b3a2e10e88cb99eb4c. Native113791cells/113863nets/PG/ports/NDR signaturesidentical. TwoidenticalNETS-onlyimports compensatepinnednativeunconditionalITermreversal, no tolerance/normalization. FixedODBf5fd7f871b585df0d76e42ba19c44c0eb51e25959003b707ed5ee95ce3cf0707; summary029d754af843cf83c4dfe6753e43ab0eec228d2d42db0e07f1a910bebcc73e75; parts6f583bfd284758af853b0049b7697a1c00ac2f739a06f0c94b8866c6fe4635c0; archive1f85dfaa662958cb84fea0acf94c0720f17e2130fe10286ffeb8e3323d64425a. NotECO/timing/PHYacceptance.

Newprotected_load_batch profile uses exactsame50measuredoutputs but preserves113506unchanged encodedFIXEDroutes. RestoreverifiedfixedODB; sameoriginalgeometry/positivebufferlogic/inversioncontrols;100selectednewguides; fullDRT0DRV required plus exacteveryprotectedwireopcode/datahashafterplacementandDRT, allcells/inputpins/PG/NDRunchanged. Freshall113606netRC/unchangedallcellcornerSTA mandatory. Independentallendpoint/geometry/antenna/RCqualification stillneededbeforeadoption. Existingunprotected50/3buffer andanalogjobsremainlive; this testsdistinctrouteprotectionhypothesis, no cancellation/duplication. Allworkcloudonly/localempty. Recordnewrunhandleafterownworkflowpush.

## Actual native reversal identified; compensate with two exact route-only imports

38827797297/job116739230740 source49ad36d9e83d5fc93122afa296f49618ec71b0ba stillFAIL despiteomittedconnections. PinneddefinNet::end570-589 alwaysreversesITerms because dbNetITermItr::orderReversed26-35 alwaysreturns true. This supersedes earlier tentative reconnectdiagnosis. TwoidenticalNETS-onlyFIXEDimports reversetwice, preservingoriginalnativeorderwithoutdisconnectingpins/changingdonttouch. ExactwholeDEFandrawdecodedshapeequalitygatesunchanged; newcloudnativeproofrequired. Everyfailedsource/archive retained in native-reversalreceipt. NoPHY/timingcompletionclaim.

## Preserve terminal ordering by omitting connections from route-only DEF patch

38827188779/job116737268953 source2d817ac4e197be9dd389b62edf2d095fdeb567b9 retainedFAIL:113556encodedFIXED/allcell/topology/PG/NDRnativehashesmatch but121325DEFlinechanges. First12differences exclusivelyreversed terminalenumeration (includingPGwildcards), same130481394DEFbytes; independentgeometryexports haveidenticalaggregatecountsbutdifferentorderedJSONhashes. NativeDEFreader reconnectsITerms andchangesiterationorder. Correction removesonlysyntacticallyverifiedconnectionclausesfromroute-onlyNETSpatch, preservingexistingterminalconnections/order; SAME exactfullDEF andindependentgeometrybyteequalgatesretained. No canonicalization/waiver. Newcloudrunrequired; no routeadoptionorfinaltimingclaim.

## Encoded FIXED conversion works but full DEF mismatch remains rejected

38826783231/job116735978820 sourcee38804ac22762791adb4a80ac3fcd252eeb33229 convertedall113556routes toencodedFIXED;113791cells,113863nets andPG/port/NDR native signaturesunchanged. ExactfullDEFmismatch FAILED, archive7359b2062d23d741539fe066532d79cb8d223763e757691e19f8719dd314d5cf retained. New diagnostic keeps exactequalitygate but emitsfirstdifferinglinesandrunsindependentshapesbeforefailure, to identify actualdifference. Do notadoptfixedrouteconversion untilgeometryproved. Existingfivejobsunchanged/cloudonly.

## Native fixed-route control: indentation parser corrected after retained failure

38826401425 failedbeforeconversion: nativeDEFnetentries have4spacesbefore dash, whilecontrolcountedcolumn0. Metadata-onlynegativecontrol passed; all113556originalroutesconfirmedencodedROUTED and1787710pathstarts. Changedonlycountparser to accept horizontalindentation, retainedexactNETScount and allgeometry/typegates. Nativefixture nowusesactualindent. Failurearchive0f1fe669123cc0c59672b2abe41bd77d26fa41d88a0fad5a74d01fff42605883 andsummary2603bd44843d998560558a51b1b02fffff6d00043e425441cdfa92f9542e86bd retained. Ownworkflowpathpush starts correctedcontrol; no adoptionyet. FiveexistingECO/analogjobsunchanged; allworkcloudonly.

## Native encoded FIXED control dispatched

Run38826401425/job116734768284 source4215feec880bd52af4fedc3e2c041ba6581ffe05 live. Preserve existing five physical/analog jobs; no duplicates. Native decoder/wholeDEF/geometry proof required before use; this is not a timing/PHY closure. Primary-source parser correction recorded in cloud-native-fixed-wire-parser-control-20261016.json. Local workspace remains empty.

## Encoded FIXED route preservation control staged in cloud

New fixed-wire-control-cloud workflow restores exact original113791-instance route (38788529905, ODB4ecf6f150c7288c43b99fb944bec72e5ad45f693234181ff47c1df7566957493). It converts only NETS ROUTED clauses to FIXED, using a NETS-only DEF with read_def -floorplan_initialize. Pinned OpenROAD INCREMENTAL mode does not register NETS callbacks (definReader.cpp1932-1943), so incremental mode must not be used. Native before/after decoder must see113556ROUTED->113556FIXED; metadata-only negative control must remain encodedROUTED. Exact fullDEF except intended classes, all nativecell/connectivity/PG/port/NDR signatures, and independent decoded shapes must remain identical. Failure is retained; no ECO or route adoption, no freshRC/timing/fullPHY claim. Subsequent repair may protect unchanged routes only after control passes, and still requires route/geometry/freshRC/allendpoint checks.

Existing50output38824521607,3buffer38822066992,PLL38813902351 andfull32Sparse38810158966/38810163678 are live; no duplicates. All execution cloud-only; local project empty.

## Fifty-output physical batch live; all-profile comparator controls passed

Batch38824521607/job116728720146 sourceabd15b539ece968c7396d3137130ba0f67faddd4 islive. Exact50targetrecipe and legacy2/3profile contracts passed cloudstep; nativephysicalexperiment executing. Expected113841instances/113606guidednets, alloriginal113791cellsfixed; everytarget exactnativeconnectivity mustvalidate beforeadditions areadopted. All-profile independentcomparatorcontrols38824521597/job116728720053 PASS; actualbatch endpointcomparison NOTYETRUN. Existing3buffer38822066992,PLL38813902351,full32Sparse38810158966/38810163678 live; no duplicates.

Parallelprimarysource research: pinnedDRT supports encodedFIXED routes (Parser setsFixed fromwiredecoder; writerpreservesfixedwires; FlexDRusesINCRwhenfixednets). dbNet::setWireType changesmetadataonly, so it isnotvalid encoded-routeconversion. dbWireGraph omits patchrectangles, so naivegraphrewriteunsafe. Receiptcloud-native-fixed-wire-research-20261016.json pinsprimaryfiles. No fixed-wirealgorithm implemented orvalidatedyet. Futurecloudnativecontrols mustproveallprotectedshapes/pins/widths/vias/NDR/patches, thenactualroute/fullgeometryandfreshallnetRC; evenfixedclockgeometrycanhavecouplingdelaychanges. Existingfullreroutesunchanged.

Latestcompletedcandidate2remainsNOTADOPTED: independentcensussetup9601->9557,fasthold91->94,typicalhold0->1. FullserialPHY/mainchipfinaltimingremainopen. Everythingcloudonly; local0entries.

## Source-bound50-output physical load repair batch staged

New measured-load-eco-cloud profile measured_load_batch targets ALL50outputs in originalsource-logSHA-verified high-load receipt7f6572696f303fda18383f7d0def5c8e583c15b9cd7cf821dc4c7aa6170341de. Selection: originalreportednegative slowpaths, weakdrive1/2,cap>=.1pF,stage>=1ns; excludessequential/delay/clockmasters. This is not allnets coverage and not a timingacceptancelimit. Everyrawmeasurement recheckedagainst exactoriginalnative logbeforephysicalmutation. Native exactdriver/master/pin/fanout/signal/noNDR/noport guards must pass for all50; no selective omission. Original113791cells remainfixed; add50positivebuf16 cells, legalize additions1000x200um, geometry/input/PG/NDR proof and negativeinversioncontrol unchanged;100changed/newguides, complete113841cellroute0DRV, freshRC/allcorners required. Independent all22544endpoint comparator now supports batchprofile; no automaticadoption.

Preserve existinglive3buffer38822066992 and analog38813902351/38810158966/38810163678; do not duplicate them. Newbatch is a different source-bound hypothesis addressing remainingPCIe/Ethernet/core high-load bottlenecks instead of another single worst path. Originaltwo-buffer38813118414 remainsNOTADOPTED after fullcomparison38823446292: setup9601->9557 buthold91->94 andnewtypicalhold. Allworkcloudonly/localempty. Record newbatchandcontrol run handles afterown-pathpush.

## Two-buffer native route complete; independent allendpoint comparison rejects adoption

Two-buffer38813118414/job116691024892 COMPLETE0DRV, summary4c85988b67da484caef77960d0a8b71587e10255337ea92783b7fca11dd80cdb, partsmanifest252d118ba5ac9c5fb00156af6bbcd6dd836c29b718ad389f51fb6371efed013b, archive03c6e76d88fe44b586783bfc48b8f13999bb066565ede01ccf3847dfcec0f856. Fresh113558netSPEF2034f871b5be6cd47b2f26c1d80868236b5d1939228721332b5d93977b81aa91. Worstsetup improves-11.940513->-11.731633ns; worsthold-.151066->-.132041ns. NOTADOPTED.

Independent22544endpoint/135264row comparison38823446292/job116725381178 COMPLETE, summary1b267369d5035e3d4a27dafa4650e62a7f48e32849b0e5afde0f549a60eb5b16; archive781abb86ba8d9ed64324659acc1a7bc90292a0f1250493c6e1514f4279e47e6b. Slowsetup9601->9557; typicalsetup1285->1070; fastsetup53->59; fasthold91->94; typicalhold0->1. Nolostconstraints; manyendpointregressions. Geometry/antenna/annotationstillrequireindependentcandidatechecks beforeadoption. FullPHY/finaltimingnotclosed.

Actualworstremainingpath startsretrain_done, butdominant7.397814ns stageisnor3_1$1741541/Y driving0.541558pF (inputcontrolrootonly~0.76ns). Source-logSHA-verified scan found50original weak heavilyloaded outputs acrossreportednegativepaths, 43aftertwo-buffer route; detailedreceipt cloud-routed-high-load-targets-20261016.json retains everymeasuredline. This is a candidatehypothesis, not exhaustiveallnets nor nativeconnectivityapproval. Next consider batchrepairwithexactnativefanout/master/pin/signal/NDR checks and allsameproof/freshRC/endpointgates; don't blindlyinsertdelaycells on90setup-failingholdtargets.

Three-buffer expandedplacement38822066992/job116720743634 stilllive; PLL38813902351 andfull32Sparse38810158966/38810163678 stilllive. Do not duplicate. Fullcomparison workflowcontrols latest38823160385 passed; use it for completed3buffer too. Allworkcloudonly; local0entries.

## Comparison controls passed; preserve original archive inventory semantics

Registration38822999217/sourceee407ff552f0802aed6f9e13605e0f3329f78720 controlsjob116723794430 PASS; fullcomparisoncorrectlySKIPPED until completedphysicalsourcepins available. Refined selection uses frozenECOsummary's embeddedlogicreceipt because originaloutputs excludesALLbasenamesresult.json (includinglogic/result.json); never inventa nestedhash. Geometryproofselectedhash additionallymustmatchembeddedgeometry. Own-pathpush rerunscontrols for finalsource. FullnativeECOcomparison stillpending original38813118414/control38822066992; bothlive, no duplicates. No finaltiming/fullPHYclaim.

## Independent full-endpoint comparison staged for completed physical ECOs

New eco-endpoint-compare-cloud workflow controls validate orderedarchive integrity, completeidentitycoverage, regressions, newnegativepaths, and lostconstraints. Fullnativecomparison is manualdispatch ONLYafter a physicalECO has a complete0DRV/freshRC/STA report; inputs profile(two_buffer/control_three_buffer),run,summary_sha,parts_sha must be pinned. Restore allcandidateparts with completehashverification; exactcandidateSTA must equal originalfrozencontract with onlyODB/SPEFpaths changed. Independently rerun native22544endpoints/all135264corner-delay rows and compare each rise/fall/worst rawSI against38819589884. Report everyregression/constraintloss; no automaticadoption/signoff. Nativefullcomparison not yet run because physicaljobs stilllive. Allworkcloudonly. Observe control38822066992 andoriginal38813118414; no duplicate reroutes.

## Corrected placement candidate live; live log snapshots may be partial

Three-buffer expanded-placement run38822066992/job116720743634 source651cf62686a0d7ba5dff95039f7e3790e5167460 is active in nativephysicalexperiment aftercompilepass. Previous38821357967 terminalDPL-0036 buffer2 failure retained; wider1000x200um searchONLYforadditions, original113791cellsremainfixed. Originaltwo-buffer38813118414,PLL38813902351,full32Sparse38810158966/38810163678 remainlive. Do not duplicate.

LiveRESTjoblogs for bothphysicaljobs yielded onlyinitial~6.338MB baselineSTAchunk endingmid-report; that partialdownload doesNOTlocate currentnative stage or prove a stall. Analogjoblog404 isnotterminal. Poll knownrun/jobstate or finalrelease; neverrestartfromlogtruncation. Latestcompletedphysicaltimingstillsetup-11.940513ns/hold-.151066ns. FullPHY/qualifiedRC/finaltiming remainopen. Allworkcloudonly; local0entries.

## Three-buffer placement failure retained; expand only added-cell search

Three-buffer38821357967/job116718426829 failed nativeDPL-0036 on ONLYnewbuffer2 at input37806; originalroutedtiming replay matched exactly and preparationchecks passed. Summary30bea5780e81883382f63a4c3828a5c88355233dbdfbf351e6abf5ffe46b5725; archive968d1191a15bced2417668ddfb15076d87d470524b0135e158165d54711d15ab retained. PinnedOpendp.tcl:44-48 confirms max_displacement unitsmicrons; originalsearch100x20um. Corrected control_three_buffer search1000x200um appliesONLYto3additions; alloriginal113791cellsstillFIRM/exactgeometryaudited. Recordinitial/finalcoordinatesanddisplacementDBU for everynewbuffer. No timingthreshold,netrule,placementlegality orlogiccheckrelaxed. Defaulttwo_buffer profile retains100x20um. Newown-pathworkflowlaunch; observe before reuse. Originaltwo-buffer38813118414,PLL38813902351,full32Sparse38810158966/38810163678 live unchanged. Allcloudonly.

## Live handles after complete setup/hold diagnosis

Current corrected three-buffer physical run38821357967/job116718426829, source9a137967882c3e00a8cb6980ff84b300fdfaa3dc. Originaltwo-buffer38813118414/job116691024892 stilllive. Actual845patched1us38813902351/job116693663825 and full32Sparse38810158966/job116681265012,38810163678/job116681243193 live. No duplicates. Unsafeproxy-identity predecessor38821022638 is terminalCANCELLED; correctedvariant checks exactnative(instance,pin)tuple.

Completedcensus38819589884 andall546conflictreports38820661033 establish22544endpoints,91holdfailures and90ofthosealsofailsetup;68sharedworstslowpaths startpcie_retrain_done_i. Newthirdbuffer targets that common loadedroot, with fullreroute/freshRC/unchangedallcornerSTA gates; notadopted. Originalsetup-11.940513ns/hold-.151066ns remain latest completedphysicaltiming. Compare final2/3bufferresults, then repeat completeendpointcensus/geometry/antenna/annotation before anyacceptance. FullserialPHY andfinaltimingstillopen. SmallJSON/source/log inspection inRAM only; no localprojectfiles orCAD. Authoritative machinecheckpointupdatedwithcurrenthandles.

## Verified all91hold/setup conflict targets; physical candidate preparation hardened

Conflict38820661033/job116716178309 COMPLETE, sourcee11dd50fbffa0d797190906c4538795a2e34cb23; summaryaf4c313bfafbfa842d4cc071d37ec549e069823a98ed8ddd3afe722dc8ca21cf, archived849f5d0d0d20671862351984561487171358ab0dea9b72623ecc63b24a90ee2. All546corner-delay reports exactly match pinned float32 native rendering of rawSI; original source unchanged and baseline reproduced.91target topology is available directly in summary.hold_targets.68worstslowpaths startpcie_retrain_done_i; verified smallbuf2 drives0.424pF. Three-buffer profile is aligned to that common cause.

Initial three-buffer run38821022638/sourcee4733ef43ee48d048462479ece785b30f2bb0f43 cancellation explicitly requested before relying on its result: preparation used Python proxy equality for dbITerms, unsafe with unwrappeddbObject identity. Replaced with exact native(instance,pin) tuple and oneOUTPUT/allothersINPUT checks. No net or acceptance omitted. New own-path push runs correctedprofile with explicitprofile/count guards. Original two-buffer38813118414,PLL38813902351,full32Sparse38810158966/38810163678 remainindependent live jobs. Do not restart them. Everythingcloudonly; localempty.

## Separate three-buffer physical candidate for common PCIe control load

Source-bound native conflict reports from38820211190 show68of91negativeholdendpoints have worstslowsetup frompcie_retrain_done_i. Commoninput37806/X(buf2) drives3loads,0.424164891pF and1.093724251ns slew; its followingnor2 delay0.998621881ns. Do not blindly delay those90setup-failing endpoints. New control-load-eco-cloud uses explicitcontrol_three_buffer profile: retains originaltwo high-load buffers, adds onebuf16afterinput37806/X. All original113791cells/geometry,allinputpins,PG/NDR/SDC/libs protected; only three driver outputs reconnected through positivebuffers; exactoldfanouts2/2/4checked. Restrictedpositivecontraction+negativeinversion controls; only6native net guides replaced, allotherguidesbyteequal; full113794cellDRT0DRV gate thenfreshnominalRC/allsixcellcornerSTA. Original132globaloverflow,651antenna,qualifiedRC/SRAM/LVS/fullserialPHY remainopen. This is an independent physical candidate, notadopted; keep originaltwo-buffer38813118414 live for comparison. Refactor preservesdefaulttwo_buffer profile; existing nativejobs use frozencommits. Corrected exactfloat32 conflictverification38820661033 stilllive when prepared. Allnativework/artifactscloudonly.

## Conflict report representation corrected without loosening timing

Conflict38820211190/job116714687380 completed native546reports but gate rejected comparing float64 SI/ns against native float32 formatted report: raw2.9761593189903124e-10seconds -> native0.297615945ns. Pinned OpenSTA857316ff liberty/Units.cc:174-185 explicitly divides into float scaled_value, zeroes abs<1e-6, then printf digits. Corrected verifier reproduces that exact representation and requires EQUALITY for all546reported slacks, not a larger tolerance; original rawSI/slack signs/SDC remain unchanged. Failed run/results retained. New own-path workflow repeats native source-bound reports and final input hashes. Complete census38819589884 remains authoritative:90of91holdtargets alsofailsetup. Existing4longnativejobs unaffected.

## Verified actual-route census:90of91hold targets also violate setup

Native38819589884/job116712626062 completed, source02344a922a5c04c4e2230fe1f425a3b4670e4c83. Summary54a23354fc53eb4811b574a1c1bbd70aa413d83463e5165f240b8925c10e00ff; archive14883e2c8766210fddfaccb1d2a121a3e9a3bb308fd795029d5897a362bb636a.22544endpoints/135264corner-delay pairs; original geometry/RC/SDC/libs unchanged, exact vertex/path/raw-WNS coverage passed. Fast91hold; slow9601setup,typical1285setup,fast53setup.90negativeholdtargets already failsetup;1haspositivesetupallcorners. All91areinternalwithsingledriver; no missingsetupcorner. Do NOT blindly add91delaycells or claimfixingtheoneeligibleendpointcloseshold.1117hold/1072setup unconstrained endpoints remain explicitly open coverage questions.

New routed-hold-conflicts-cloud job restores exact original source plus verified91target topology in cloud, reproduces baseline and reports all546corner-delay target paths to identify shared slow/fast causes before physical mutation. Only measurements; no waivedconstraints. Record new run handle after own-path push. ExistingECO38813118414,PLL38813902351,full32Sparse38810158966/38810163678 live; no duplicates. Local0entries.

## Complete timing census observed; native identity adapter corrected

Run38818676027/job116709615619 retained as FAIL_OR_ERROR: summaryba78bccac23b513bded662295ab84524ca53b61f560f228666ba15bc389cffff, archive0e887ce4746650ff101fca753e810ef2fe5c579427924a9b9c1bd385aca4013c in cloud-results-38818676027-1-routed-endpoints. Complete census stage measured22544endpoints/135264corner-delay rows, fast91hold, slow9601setup/typical1285setup/fast53setup. All native coverage/WNS/reproduction checks passed before topology failed on STA-vs-ODB escaping of Ethernet SRAM instance g_bank[7].u_mem. Do not infer complete topology from this failed receipt. Corrected Tcl exports exact sta::sta_to_db_pin / sta::sta_to_db_port identities from pinned OpenROAD dcf36133 dbSta.i. Python requires one-to-one physical mapping; no stripping brackets/escapes or unresolved endpoint bypass. New own-path workflow replays full census/source checks and topology. Existing four long jobs unchanged. Everything remains cloud-only.

## Actual-route hold repair selection in progress

Original113791-cell routed nominalRC hold remains -0.151066ns. New routed-endpoints-cloud workflow replays source38809759501 byte-identical SDC/libs/SPEF, enumerates every native endpoint and all rise/fall min/max values at slow/typical/fast, verifies exact vertex/path coverage and original WNS, and exports every negative hold endpoint with setup headroom and native net topology. This is the prerequisite for explicit positive-delay placement without hiding setup regressions. No topology mutation, RC estimation, constraint relaxation, signoff or adoption. Reject incomplete/bidirectional coverage rather than truncate. Native execution and all results cloud-only; workspace remains empty. Existing physical ECO38813118414, PLL38813902351 and full32Sparse38810158966/38810163678 still live; do not duplicate. Check new own-path-triggered run before acting on its targets.

## Original-route annotation uncertainty resolved from native evidence

Annotation38815972613/job116700606177 complete: summary4cb6e74ce878f7bcd208b30afacf3edbb4062b9bea31fb380e153f90c334ea58. All1065unannotated drivers classified as302connected-without-sinks and763disconnected; ZERO loaded unannotated drivers. All113556SPEF nets match exact native ids and writer names. Original routedODB/SPEF/STA source unchanged. Receipt docs/evidence/cloud-route-annotation-classified-20261016.json. This resolves original-route annotation uncertainty only; repeat for new physical candidate and don't infer functional interface completeness or qualifiedRC/finalSTA acceptance.

Live handles verified: actual two-buffer ECO38813118414/job116691024892; patched actual845 full1us38813902351/job116693663825; originalSparse full32 .5ps38810158966/job116681265012 and .25ps38810163678/job116681243193. Do not duplicate. Full-wire38801162596 is complete componentPASS; mainchip baseline setup-11.940513ns/hold-0.151066ns and651antenna nets remain open. All work is cloud-only, local workspace0entries.

## Native annotation binding follow-up

Second classifier38815455579/job116698864598 failed because Python bindings omit inheriteddbObject.getId, after all five exact SPEF naming controls passed. Evidence remains in cloud-results-38815455579-1-route-annotation. Use exposed staticdbNet.getNet(block,id) from pinneddb.h to translate the actual SPEF net id, then require the same exact forward-escaped native name. This preserves both checks and does not waive any net. Own-path push launches corrected classifier. Other long native jobs remain live; no duplicates.

## Exact native SPEF name handling correction

Annotation38814839951/job116696793924 failed before classifying drivers: reverse-unescaping discarded literal bracket escapes in ODB names. Failed summary69adfcbf... and all source evidence retained. Pinned native extSpef.cpp writes net ids unchanged and preserves existing escapes; classifier now matches that exact net id AND native forward-escaped name. No loaded-net exception or parasitic modification. Own-workflow push launches one corrected diagnostic; inspect completion before claiming coverage.

Verified live: physical ECO38813118414, patched PLL full1us38813902351, full32Sparse38810158966/38810163678. Full-wire38801162596 complete componentPASS as recorded. Everything remains cloud-only.

## Completed full-wire component; actual annotation diagnosis launched

Full-wire38801162596/job116650255071 is COMPLETE, do not duplicate. Summaryc0e91d7ef51054fa07a79d06f407e96f7af3743c40259d6b99ddfee419baae0b: all original768samples/device/interface gates pass at .125/.0625ps through full34ns, same physical sources and limits. Min margins100.723619mV/100.725578mV, numerical comparison PASS. This is assembled4:1 only and margin above100mV is narrow. Full32 per-macro captures38810158966/38810163678 still live; actual32physical/x4 remains unproven. Detailed receipt pcie-vbic-full-wire-20261016.json.

Patched PLL full1us38813902351/job116693663825 is live on be12960e. Physical buffer repair38813118414/job116691024892 remains live. New route-annotation-cloud diagnoses all1065original unannotated drivers against exact original ODB/nominalSPEF; report categories preserve every loaded missing/failed binding as open, no waivers. Native diagnostic runs only in cloud. Local workspace remains empty.

## Patched native PLL full1us acquisition measurement prepared

New pll-vbic-acquisition-cloud restores exact original actual845 run38674687038 and requires paired-engine50ns evidence38805695818. Physical parent91364a..., all35 model/OSDI inputs, original34 probes, startup, KLU/.3125ps and full1us stay unchanged. Only proven native VBIC companion correction changes. Reproduce original acquisition rejection before the new run; apply frozen original800-900ns and900-1000ns100ppm/50ps/no-slip/control gates. No phase fit/window shift. Full raw stored in cloud ordered parts, including failure. Native progress logs report elapsed time/bytes every60seconds. Full845 safety, timestep/PVT/load/CDR/x4 still need proof regardless of this result. Own-path push starts one run; do not duplicate.

Corrected physical critical-load38813118414/job116691024892 is live on3b41d9e; original wire/full32 captures remain live. All execution and artifacts stay on GitHub; local workspace remains empty.

## Cloud-only continuation and corrected physical experiment entry point

Local workspace verified empty (0 entries), no local CAD/simulation processes. All source and results stay on GitHub. Existing full-wire38801162596 and originalSparse full32 runs38810158966/38810163678 remain active; do not duplicate.

Critical-load38812329280/job116688346427 was green but did NOT run the new ECO: its workflow accidentally invoked the old extraction controller. Its saved summary is FAIL_MISSING_REPORT, SHA256 a9785bbf7d09950e725587de53c0cc1735669c29288a8ba6e3c62d9765a2ff3b. No buffer repair or timing improvement occurred. Workflow now invokes/compiles the actual new controller and fails after evidence publication unless the source-bound complete physical report exists. The own-path push starts one corrected run; inspect it before claiming any repair.

Original geometry38810969514 summary3236d5446abdff3b8f8bab9731d38d1f850061d59a5058a37d2f940423b21936 verifies113556 signal nets/3323078 shapes, zero continuity failures and zero below-NDR-width segments. This excludes inter-net shorts, power, transistorLVS and spacing. Antenna651net/809pin failures and setup-11.940513ns/hold-0.151066ns remain open. Full serialPHY is not complete.

## Actual two-buffer PCIe critical-load repair launched in cloud

critical-load-eco-cloud is a source-bound physical candidate from actual routed extraction38809759501. It first reproduces original actual timing to1e-6ns, then adds two sg13g2_buf_16 cells after measureda22oi/nand4 outputs, keeping all113791originalcell placements/masters/inputpins/PG/55NDRs and physicalSDC unchanged. Only added cells are legalized. Original/modified netlists require positive buffer-contraction proof and inverter fault rejection. Four changed/new nets receive native GRT guides; every other original guide remains byte-identical. Full113793cell DRT then fresh nominalRC/three-cell-corner timing must be measured; original132globaloverflow and antenna/RCqualification/LVS remain open. Do not count this candidate as repaired until actual outputs pass. No original-source ODB or SPEF is mutated/reused after netlist change.

Independent original geometry38810969514 returnedsuccess; inspect its saved summary3236d544... before claiming continuity. Full32 Sparse0.5/0.25 and full-wire replay remain live, no duplicates. Everything executes on GitHub; local workspace stays empty.

## Exact latest cloud checkpoint and next physical repair

See docs/evidence/cloud-current-checkpoint-20261016.json for current run/job states. Native geometry follow-up38810969514/job116683788886 is queued/running; don't duplicate. Full32 originalSparse38810158966 and38810163678 remain active; wire38801162596 remains active. No new fullPHY or timing acceptance.

The saved actual timing report isolates PCIe setup critical-load targets: a22oi_1$1749936 cap0.207088pF/delay2.443390ns and nand4_1$1749937 cap0.428974pF/delay6.686792ns. Exact source/instance names in docs/evidence/cloud-routed-pcie-critical-loads-20261016.json. Repair is NOT yet applied. Next implement source-bound drive/buffering improvement, verify original functional/pin invariants, reroute and reextract; also classify1065unannotated drivers and repair651antenna nets. No clock/SDC/RC qualification waiver. Do not confuse native0DRVs with productionDRC/LVS/timing closure.

## 2026-10-16 measured routed timing and live full32 captures

Actual routed extraction38809759501/job116679719057 terminalSUCCESS as a measurement, NOT signoff. Fresh nominalSPEFb0411f... has113556nets and0per-net cap inconsistencies; slow setup-11.940513ns, typical-6.233346ns, fast-2.978773ns; fast hold-0.151066ns. Native annotation report has1065unannotated drivers (0partial); classify those before any coverage/closure claim. Worst slow setup $auto$ff.cc:337:slice$1171433 -> $auto$ff.cc:337:slice$1177036; retrain_done input paths also near-11.74ns. Receipt docs/evidence/cloud-mainchip-routed-nominal-rc-20261016.json. OriginalSDC/9libraries protected unchanged, nominalRC only. No stage passes final setup/hold.

Full32 originalSparse0.5ps38810158966/job116681265012 and0.25ps38810163678/job116681243193 live after controls passed. Sourcef4de0a9f6cdb873916671b3f1ec7e1cf60071e87; study38803757710 summarya52a... . KLU guard remains FAILED and KLU not adopted. Do not duplicate. Wire38801162596 still live. PLL paired50ns complete; long acquisition remains open.

Geometry38810141084/job116681014582 FAILED at unwrapped optional<Rect> bbox access. Failure retained in cloud-route-bbox-binding receipt. New verifier records bbox verification FALSE and checks independently exported segment/RECT geometry-length sum against native dbWire::getLength implementation. This is a limited diagnostic and must not be called complete layout shape equivalence/LVS. Native antenna651net/809pin violations remain. Subsequent job must be inspected before proceeding.

Local workspace was rechecked0entries. Existing8hour heartbeat already cloud-only and ACTIVE. All source edits/payloads/evidence remain GitHub; no local checkout/build/CAD/test runs.

## Latest measured native results and preserved original-backend continuation

32backend38803757710 is complete; all four native runs complete and inputs unchanged. Pristine/package agree exactly. Patched KLU is1.575986x faster (696.796s versus Sparse1098.141s) but differs2.5439587uV at v(xad_d0p.sink), FAILING the existing1nV backend-adoption guard. Do NOT adopt KLU or mark that guard passed. Full32 controller now allows a separate originalSparse-only full34ns measurement with identical original solver settings; KLU still requires unchanged1nV guard. This does not change original full768sample/device/interface or fullwave timestep gates. Receipt docs/evidence/pcie-tree32-backend-measured-20261016.json.

PLL38805695818 complete: pristine original50ns identical, patched50ns complete/clean, maximum engine effect0.412262mV. Full1us original800–900ns126.2157ppm acquisition failure is NOT resolved by this experiment. Receipt docs/evidence/pcie-pll-vbic-paired50-20261016.json. Full1us patched acquisition and timestep/safety/load/PVT proof remain needed.

Geometry38809417232 failed at another missing SWIG output typemap (getRect). Native651net/809pin antenna failures unchanged. Exact four RECT operands are now read directly from the native dbWire stream, with existing per-wire bbox guard; no patch shapes discarded. Failed capture retained. Newly launched routed-extraction-cloud uses exact route and nominalPDKRC; inspect its native run separately. Wire38801162596 remains live; never duplicate.

## Fresh extraction/STA follow-up of completed route

Prepared/launching routed-extraction-cloud on exact mainchip38788529905 routedODB4ecf6f... . It restores hash-bound original physicalSDC and all nine original libraries, fresh OpenRCX extraction using pinnedPDKc4b8b4e5 nominal rules ffda02... with librelane3.0.5 native flags, validates per-net SPEF cap conservation before reading it at slow/typical/fast cell corners. No stale/estimatedSPEF reuse. The PDK provides nominalRC only: this cannot close qualifiedRCmin/RCmax, fullSRAM characterization or production signoff. Original651antenna nets and132global overflow failure remain open. Corrected geometry38809417232 is live; original38808634187 binding error is terminal/preserved.

## Native antenna failures measured; pinned decoder correction

routed-geometry38808634187/job116675907550 FAILED after completed antenna measurement:651net/809pin violations. Exact failed capture/summary retained in docs/evidence/cloud-routed-antenna-initial-20261016.json. Geometry never ran: pinned dcf36133 Python does not expose dbWirePathItr/dbShape/dbITermShapeItr. Updated export uses supported dbWireDecoder and native transformed dbITerm.getGeometries, actual segment end extensions/via boxes/RECT patches, and checks each native wire bounding box. Corrected workflow launch is a verifier fix, no physical circuit change; do not mark geometric continuity passed before actual readback.

## 2026-10-16 complete native mainchip DRT; independent verification starts

38788529905/job116606725290 is now terminalSUCCESS, not live: native detailed-route DRVs0;113556wired nets;113791original instances and55NDR declarations preserved. Receipt docs/evidence/cloud-native-drt-complete-20261016.json pins permanent archive104854492bytes and routedODB4ecf6f... . Original global132overflow/NDR relaxation failure remains; this is not final acceptance. Do not rerun DRT. New routed-geometry-cloud restores this exact route for native antenna and actual metal/via/placedLEF-pin continuity screening. It excludes power/inter-net shorts, NDR spacing and transistorLVS; source is immutable. Qualified extracted STA remains next work.

Full32 comparison registration38807225461: native evidence restore fault controls and original stream/data tests passed; full-comparison skipped as intended because no full32 pair yet. Current wire38801162596, backend38803757710 and PLL38805695818 remain live. All work/cloud artifacts stay on GitHub, local workspace empty.

## Cloud-only continuation: exact PLL handle and prepared full32 comparison

PLL paired-engine38805695818/job116665834742/sourceb81fdfea7dec035e9d7bccda461b2fd51a6f1104 is live in native50ns step. Existing mainchip38788529905, wire38801162596 and backend38803757710 remain live; never duplicate. Local workspace is empty and no local native work is authorized.

Prepared tree32-step-compare-cloud runs integrity/parser controls on registration push ONLY. Full comparison must wait for successful full34ns0.5ps and0.25ps captures and requires both summary and ordered-part-manifest SHA256 values. It verifies every archive part and combined ordering before restoring complete native waveforms, checks identical physical/runtime/source/bit provenance, then uses original full-window step_metrics without changing thresholds or removing startup samples. Memory-mapped native readers retain every vector. This is still per-macroRC with imposed clocks/ideal intermacro wires, not a whole-tree or PHY pass.

## Actual845 PLL paired-engine follow-up

`pll-vbic-replay-cloud.yml` restores exact original actual84550ns source38672412524: parent91364a... unchanged, all32model files/3OSDIs, all495original probes, zero-sourceOP/102OFF commands, KLU and .3125ps preserved. Pristine source engine must reproduce original packaged waveform under the original1mV/1ps comparison plus a whole0–50ns1mV bound before patched50ns. Patch only simulatorQbcx companion expression; no physical loop, source, RC, pump/filter or acceptance-window change. Preserve full native captures via ordered hash-verified parts. This independent test measures whether the engine correction affects the clock circuit; it CANNOT close original800–900ns126.2157ppm acquisition failure or full845 safety. Full1us100ppm/50ps/slip/VCTRL gates, actual clock loading, PVT/CDR/x4 integration remain required.

Existing wire38801162596, corrected32backend38803757710 and mainchip38788529905 remain live; do not duplicate. All execution is GitHub-hosted and local workspace remains empty.

## Current live handles and verified full32 capture preparation

- Mainchip38788529905/job116606725290: native geometry/NDR+DRT step live. Never duplicate.
- Wire38801162596/job116650255071/source175d801b53b53c939dcf72088216a0ede7521553: native matched-endpoint+full-wire step live. Original1nV runtime controls and full34ns engineering/numerical gates unchanged.
- Corrected32:1 backend38803757710/job116659178611/sourcee90497f89e33fe6db9f1962b14d6d9ed3ced52df: native source/runtime step live. Readback and original observation controls passed. Previous38800540477 is terminal failure, NOT live; exact original waves/error retained in docs/evidence/pcie-tree32-readback-failure-20261015.json.
- Full32 preparation38803757497/job116659177471: controller syntax and exact payload roundtrip+6negative archive controls passed. Full-native correctly skipped on push. Receipt: docs/evidence/pcie-full32-archive-controls-20261015.json. Do not dispatch full simulations until actual backend proof passes; then pass study_run+summarySHA with matching current controller hash. Large native files remain complete, split only as hash-verified transport parts.

Current turn is progress: full32 runtime-gated capture path implemented and tested; native readback defect fixed and corrected study launched. Full serialPHY, actual whole-chip routing and final extracted setup/hold remain OPEN. Local workspace rechecked empty; all execution/artifacts stay on GitHub.

## 32:1 readback error corrected; original failed native captures retained

Backend38800540477/job116648093878 FAILED before patched cases. Packaged/pristine each returned0 after395/387s, but `option > file` produced empty files and emitted two normal headings into the log. Diagnostic scanner correctly refused its unscoped error/stepping words. Receipt: docs/evidence/pcie-tree32-readback-failure-20261015.json. Preserve both original raw captures and failed report; do not claim runtime agreement from them.

New backend source uses explicit native option markers, verifies actual numeric/matrix/method readback, and exempts only the two known labels INSIDE the verified block. Seven negative controls retain outside labels, real inside warnings, changed/missing options and malformed scopes. Own-workflow push starts one corrected study; prior study is terminal. Full32 workflow now requires the successful study run+SHA and exact current backend-controller hash, not the failed oldrun. Full32 simulations remain unlaunched until measured proof passes. Full32 registration38802993109 passed archive integrity controls and controller syntax only; native full job skipped as intended.

Wire38801162596/job116650255071 and mainchip38788529905/job116606725290 remain live; never duplicate. All execution/evidence remain cloud-only.

## Prepared gated full32 native replay and lossless large-evidence transport

`vbic-tree32-full-cloud.yml` runs only controller/archive integrity controls on its registration push. Full simulations require manual dispatch with the hash of passing study38800540477, backend choice, and0.5/0.25ps TMAX. The controller independently requires source-pinned pristine/packaged and patched Sparse/KLU agreement before restoring the exact original32:1 macro-RC inputs and running full34ns/all768original samples/devices/interfaces. Native clocks and intermacro wiring still retain the recorded ideal assumptions; no PHY/physical signoff claim. Do not dispatch before the actual measured study gates pass.

Full waveforms are archived as ordered1GiB parts with per-part and whole-archive SHA256; no waveform decimation. Hosted controls verify exact payload roundtrip and reject corrupt/missing/reordered/path-traversal manifests. This avoids the2GiB-per-release-asset limit without losing native samples. Current wire38801162596, backend38800540477 and mainchip38788529905 are live; never duplicate. Cloud-only policy remains.

## Exact live cloud handles after matched-endpoint correction

- Wire38801162596 / job116650255071 / source175d801b53b53c939dcf72088216a0ede7521553: native matched-endpoint provenance/full-wire step confirmed in progress. Never duplicate. Prior38799068525 remains a failed endpoint-control attempt; its3.26226nV final-sample difference is preserved.
-32:1 backend38800540477 / job116648093878 / source09e6e23d6f6c6b041ef6eb0589c96b5910e984c2: native source/runtime study confirmed in progress. Original near-memory-limit full capture remains a failure; streaming retains all probes. Inspect actual option equality/native vectors before speed or adoption claims.
- Mainchip38788529905 / job116606725290 remains live in geometry/NDR+DRT step. No duplicate. Original global-route132overflow failure remains open independently.

All execution and native evidence are on GitHub; local workspace rechecked empty. Current turn is progress: source-bound32:1 experiment implemented/launched and wire endpoint-control defect isolated/repaired/launched. FullPHY/routedchip/final setup-hold remain OPEN.

## Wire provenance endpoint failure preserved; matched-duration replay required

Wire38799068525/job116643041356 FAILED before any patched simulation. Pristine native capture completed, but its final1.2ns sample differs by3.26226nV from the interpolated original34ns packaged capture (1nV guard). Receipt: docs/evidence/pcie-vbic-wire-endpoint-20261015.json. Do not call it a physical pass or ignore the failed guard.

Controller now first runs the SAME packaged binary at identical1.2ns TSTOP. Retain its entire comparison to the original full capture; require original native times/values to match until within two native steps of the endpoint. Then require pristine versus packaged identical-duration captures to pass the unchanged1nV guard before patched full34ns cases. No original engineering threshold or full-wave window changed. Dispatch one corrected wire job only; previous job is terminal.

Independent32:1 source/runtime/backend study38800540477 was queued at last check; source09e6e23d6f6c6b041ef6eb0589c96b5910e984c2. Mainchip38788529905/job116606725290 remains live, never duplicate. Full goal remains OPEN; all work stays cloud-only.

## 2026-10-15 larger frozen-tree computational follow-up

Extracted four-input wire run38799068525/job116643041356 remains live at sourcec0d82b1fcf65c5dca421bde3345ffa221b7fa452; mainchip38788529905/job116606725290 remains live. Never duplicate either.

New vbic-tree32-backend-cloud runs an independent source-pinned runtime/cost diagnosis on the exact original32:1 physical-macro tree from38496981217 (source31d4d70464ed0c395ca9c4564e81e101fee849da). That old run passed electrical gates but retained a native near-memory-limit warning; its full waveform is hash-verified and remains preserved. New binary raw capture retains every original probe. Packaged/pristine startup must agree before patched Sparse/KLU4ns comparison. The already-built pinned ngspice47 engine has KLU enabled by default (configure.ac at a80f6e3e confirms); no rebuild/optimizer/model change is needed. Official manual section12.9 motivates measuring matrix cost, not assuming speedup. Compare identical original solver numbers and all native vectors; no full34ns/PVT/whole-tree physical acceptance from this study. Original intermacro wires remain ideal and are recorded as a limitation. All execution/evidence stay on GitHub.

## 2026-10-15 full compact waveform passes; extracted-wire replay next

Full-window38796689216/job116634823910 SUCCESS at sourced14078e2aefda63d06d03fbea9b128fe8b66d71a. Original input hashes unchanged; pristine controls pass. Both patched34ns captures pass all original768bit samples,62HBT64MOS and interface gates. Minimum original margin232.890mV; whole-wave step maximum8.06616uV; margin difference0.640554uV; edge difference0.281fs; all original energy gates pass. Receipt: docs/evidence/pcie-vbic-full-window-20261015.json. This closes this compact numerical experiment only, NOT fullPHY.

Prepared wire workflow's manual dispatch returned404 because it was not yet registered on the default branch; no job started. Add an own-path push trigger with the now-verified compact summarySHA fallback, retaining runtime/summary/gate validation before wire simulation. Find its exact new run by source SHA/name; never duplicate. Source regression38797659530/job116638188484 passed600tests and preserved original failed-capture controls at source3c288ba7a0b6bc842ab2031cd6f0d0471cdb661e. Mainchip38788529905/job116606725290 remains live. All work/evidence remain GitHub-hosted, local checkout empty.

## Prepared extracted-wire follow-up — dispatch only after actual compact pass

`vbic-full-wire-cloud.yml` is manual-only. It requires the SHA256 of run38796689216's published compact summary and independently checks its source/runtime hashes, pristine controls, unchanged input receipt, original engineering gates and full-wave numerical gate. No wire job is dispatched while compact is pending. The unchanged original wire archive is run38763917040 wire/hot_low_eighth_step, strict profile; pristine startup must reproduce its original raw capture before patched full34ns at0.125/0.0625ps. Original device/bit/interface/whole-wave/edge/energy gates retained. All work remains cloud-only. Mainchip38788529905 remains live and must not be duplicated.

## Current exact cloud handles — full-window runtime validation

- Full-window compact:38796689216/job116634823910, sourced14078e2aefda63d06d03fbea9b128fe8b66d71a. Dependencies/parser controls passed; native replay running. Review original34ns engineering and all numerical gates before next physical-wire replay.
- Mainchip failed-guide DRT:38788529905/job116606725290 remains live; never duplicate.
- Coupled prefix38795024358 failed only its final sha(str) check after all5native cases completed. Original failure retained; corrected Path conversion is in the full-window source.
- Local workspace empty, no native CAD processes and no project-named top-level/tmp or~/.cache entries on recheck. All work/results remain GitHub-hosted. Full goal remains OPEN.

## 2026-10-15 paired coupled runtime result and full-window continuation

Run38795024358 completed all5native simulations and pristine controls reproduce packaged captures. Patched startup step differences are0.7671085uV and0.4873155uV, vs pristine8906.847uV. Final protected-input assertion failed because sha received str rather than Path; original failed outcome retained in docs/evidence/pcie-vbic-coupled-replay-20261015.json. Fix only the path type. New vbic-full-window-cloud.yml repeats pristine controls, checks original sources at completion, and runs the patched unchanged compact circuit for the full34ns at0.125/0.0625ps. All original768samples, devices, interfaces, whole-wave1mV, edge and energy limits stay unchanged. No acceptance from prefix alone.

Mainchip38788529905/job116606725290 remains live; never duplicate. All execution and evidence stay on GitHub; local workspace empty. FullPHY, routed mainchip and final extracted setup/hold remain OPEN.

## 2026-10-15 native companion counterexample supports coupled replay

Synthetic companion run38793936101 completed. All8patched cases retain DC current to<5e-16A. Packaged/pristine QCO0 controls agree exactly; all4activeQCO cases in each original binary fail to complete. Inspect native error logs before interpreting those failures; the summary's false drift-observed field means missing completed drift measurement, not a pass. Receipt: `docs/evidence/pcie-vbic-companion-20261015.json`.

Hosted `vbic-coupled-replay-cloud.yml` restores the exact3binaries and original synthetic reports, checks their hashes and original failure diagnostics, then restores the unchanged62HBT/64MOS coupled tree. The pristine source build must reproduce both packaged startup captures to1nV before patched runs at0.125/0.0625/0.03125ps. All original PDK/source/device/solver/zeroOP/OFF flags and complete vectors remain fixed. One expression in the simulator changed; no model parameter or physical source did. Full34ns, independentPVT, physical integration and final chip timing remain OPEN.

Mainchip38788529905 remains live; no duplicate dispatch. All computation and evidence stay on GitHub.

## Exact active handles: native companion counterexample

- VBIC companion38793936101 / job116625309760 / source0045ccd17a9b9b28e11a5fb2b4bb3d438d24d123: packaged native cases executed; pristine same-version build confirmed live. Inspect reports and QCO0 controls before any claim. Investigation: `docs/vbic-transient-companion-investigation-20261015.md`.
- Mainchip38788529905 / job116606725290: still live. No duplicate dispatch.
- Newton study38791998396 completed but failed to close mismatch;1e-10 aborts preserved. Shared-controller regression38792102745 passed600tests. Exact receipt: `docs/evidence/pcie-newton-accuracy-20261015.json`.

All three original completion requirements remain OPEN, and all execution/results remain cloud-only.

## 2026-10-15 specific native VBIC companion-equation hypothesis

Newton-accuracy38791998396 also rejects tolerance tightening as a fix:1e-8 retains8.9068487mV mismatch;1e-10 aborts at1.25fs in both steps. Shared-controller regression38792102745 passed600tests. Stop repeating tolerance tightening.

Pinned ngspice47 source a80f6e3e95d51534905b1f23410a951802666656, vbicload.c SHA256ae2fca22ca7178bce26f31b4e433307945cafa9d8661d55007eed8fc096ff866, sets gbcx=geq and cbcx=integratedchargecurrent at886-887, then stamps gbcx into the matrix but stamps -cbcx/+cbcx without subtracting gbcx*Vbcx at1095-1100. Adjacent overlap-capacitor stamps explicitly subtract G*V. This is a concrete potential timestep-dependent artificial conductance, not yet a demonstrated fix in this circuit.

New hosted `vbic-companion-cloud.yml` tests constant-bias synthetic NPN/PNP at two timesteps with QCO=0 negative controls. It compares exact packaged binary, freshly compiled pristine same-version source, and an otherwise identical build with ONLY `cbcx = type*(cqbcx - gbcx*Vbcx)`. Preserve all sources/binaries/build flags/decks/logs and failures. No IHP model parameter or source changed; no runtime adoption or PHY signoff until actual coupled/full34ns/PVT/physical evidence passes. Missing transient cross-charge Jacobian terms are a separate observation, not changed by this one-expression test.

Mainchip38788529905 remains live. All work is GitHub-hosted.

## Active exact handles after waveform diagnosis

- Mainchip diagnostic: run38788529905, job116606725290, source266c8972cbcff17846df739de757f97f35d8fb31. Still in progress at last authoritative check; do not duplicate or infer completion from elapsed time.
- Nonlinear-accuracy study: run38791998396, job116618638101, sourceb130698c85d61794ddbc9a4ed3261aebd52cda36. Native paired simulations in progress.
- Shared-controller regression: run38792102745, job116619002862, same source. Confirm terminal outcome before claiming validation.
- Read-only waveform diagnosis38791022510 completed and is pinned in `docs/evidence/pcie-startup-wave-diagnosis-20261015.json`. Charge bracket38789786404 is rejected as a fix and pinned separately.

All sources, execution and results are cloud-only. Full PHY, complete physical chip routing and final extracted setup/hold remain OPEN.

## 2026-10-15 observed startup trajectories; nonlinear accuracy isolation

Read-only waveform diagnosis38791022510 completed. Original coarse/fine differences reproduce exactly, first exceeding1mV at xtree.n_i50 around0.505841ns. Native supply/data drives differ only at floating-point roundoff. The plotted peak regions show smoothly separated startup trajectories; the1mV whole-wave failure is retained. No evidence here proves a PDK defect or permits discarding startup.

A new `newton_accuracy` hosted study changes only reltol/abstol/vntol (1e-8/1e-15/1e-10 and1e-10/1e-17/1e-12), with original baseline controls at both TMAX0.125/0.0625ps. Keep integration trap/order2, trtol1, itl4=100, minbreak1e-18, chgtol1e-14, all sources/devices and original comparison limits. Native option readback and changed-value negative controls are mandatory. This tests nonlinear iteration acceptance separately from the already-rejected charge refinement. Every abort is preserved; no candidate is adopted merely because the workflow succeeds.

Mainchip38788529905 remains live. All work stays cloud-only and all three full-goal requirements remain OPEN.

## 2026-10-15 coupled charge bracket rejects charge tolerance as fix

Run38789786404 completed diagnosis: default and1e-16 both retain~8.90685mV coarse/fine voltage difference. At0.0625ps, successive charge1e-16/1e-18/1e-19 changes are below0.6uV, while1e-18/1e-19 coarse cases abort in xtree.xd0006. Original-charge startup prefix reproduces original full capture. Thus intermediate charge tightening is not a fix; keep all aborts and failed1mV comparison.

A hosted read-only analysis (`startup-wave-diagnosis-cloud.yml`) now restores the existing hash-pinned bracket archive, reproduces the exact worst difference, locates first native divergence and plots native samples around four relevant nodes. No new simulation, source smoothing or acceptance-window change. Use the observed waveform shape to choose the next causal hypothesis, not another blind tighter-tolerance run.

Mainchip38788529905 remains live; do not duplicate or treat its original failed global gate as passed. Local workspace remains empty.

## 2026-10-15 probe readback complete; coupled charge-tolerance bracket

Internal-probe run38789110926 completed. Every native timepoint and all17original vectors exactly reproduce run38787043126 in all4cases. Tight-charge failures remain near0.726ns; last accepted steps shrink to~2.05e-19/4.18e-19s, finite qbe/qbc and internal junction voltages vary smoothly across the last samples while dynamic currents fluctuate. These are accepted samples only, not the rejected Newton state; no model defect or successful convergence is claimed. Exact evidence: `docs/evidence/pcie-vbic-internal-probes-20261015.json`.

Next hosted `charge_bracket` keeps the original coupled transistor circuit and examines chgtol1e-16,1e-18,1e-19 between original1e-14 and already-failed1e-20, each at TMAX0.125/0.0625ps with fixed originalTSTEP. Original-charge captures remain paired controls. Native failures are retained independently so one abort cannot hide the remaining bracket. No source, device, startup window, original1mV comparison limit or full34ns/PVT/physical gate is relaxed. Prefix comparisons are diagnostic only.

Mainchip failed-guide detailed-route run38788529905 remains authoritative live work; do not duplicate. All work stays GitHub-hosted.

## 2026-10-15 internal VBIC probes; exact reference replay required

Full-chip failed-guide DRT run38788529905 (source266c8972cbcff17846df739de757f97f35d8fb31) is live; inspect its authoritative status before any dispatch. The original global-route failure remains unchanged.

A separate small hosted playback diagnosis adds native internal vbe/vbc, gm/go and four additional junction capacitances. It preserves the same frozen circuit, PWL, source corner, tolerances and steps. All four prior full/aborted recordings from run38787043126 are restored with archive and per-wave hashes. Every original timepoint and all17original vectors must be exactly equal, with no interpolation. Complete and partial captures retain their final32native samples, final5ps ranges and distance to original PWL knots. These probes may locate a charge/voltage transition but cannot by themselves establish model defects, full-circuit convergence or PHY acceptance.

## 2026-10-15 exact failed-guide full-chip detailed-route diagnosis

A new hosted-only diagnostic uses the preserved run38448901835 placement (113791 instances, 132 global overflow) and original saved guides. It does not rerun FastRoute or waive its failed gate. Before routing, native readback must preserve exact cell/master/placement, pin connectivity, boundary geometry and per-net NDR width/spacing/hard-spacing declarations; native fault controls remove an NDR, disconnect a pin and move a cell. The complete guide file must match native loaded guide counts per net.

Only after those checks does native detailed routing run with original database technology, default full iteration schedule and 2 threads. It retains native DRC/coverage and output ODB/DEF; after routing, the same logical/placement/NDR invariant is checked. Native DRV counts and wire existence are diagnostic evidence only: independent connectivity, geometric NDR, full DRC/LVS/antenna, qualified extraction and final original timing remain required. Full serial PHY remains separate and OPEN.

Workflow `.github/workflows/failed-guide-drt-cloud.yml` runs on the scoped push. Do not duplicate while live. Source scripts and runtime/guide/source hashes are retained; all computation stays on GitHub.

## 2026-10-15 cloud-only handoff verified; isolated VBIC result retained

Local workspace `/home/hasanmelih/Documents/ChatGPT/nnsoc` has zero entries, no native CAD processes were observed, and no project-named entries were present in `/tmp` or `~/.cache`. Original user documents and unrelated files are preserved. Retirement receipt asset 636387277 was downloaded into memory and SHA256-verified as `23f8d33591444bb1d22d18a8668142de3c52e906b4dddfbf98118b614d78bcbd`, status `COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE`. All source edits, CAD, simulations, tests and retained artifacts remain on GitHub; do not recreate a local checkout.

Hosted diagnostic 38787043126 completed and published a valid report after the JSON repair. Two original-charge cases complete; both 1e-20 charge-tolerance cases abort near 0.726ns in the isolated VBIC. Green workflow means diagnosis/reporting completed, not engineering acceptance. Exact source-bound result is `docs/evidence/pcie-vbic-playback-20261015.json`. Do not repeat this same experiment unchanged.

Next: inspect native charge/current continuity around the isolated abort and compare original coupled failure without weakening source, startup, bit or PVT gates. Mainchip 38731744914 is terminal (6h limit, 21 native NDR relaxations); preserve its failed route evidence and inspect exact guides/ODB before a new routing hypothesis. Full serial PHY, mainchip detailed routing and final extracted setup/hold remain OPEN.

## 2026-10-15 isolated VBIC diagnostic reporting repair

All execution remains GitHub-hosted; the local project directory is empty.
Run 38786338230 completed the two original-charge playback cases and retained two tight-charge native failures, but summary serialization failed on a NumPy boolean. The archived logs/waves remain in release `cloud-results-38786338230-1-tx-vbic-playback` (archive SHA256 `adcbda6f93db5ca047e9ea24e61357a312d069c6b9ea6aa35e6dc528eb606834`). Its fallback summary incorrectly says failure before playback; the native job log disproves that label.

The capture completion flag now explicitly uses a Python boolean, with hosted controls checking actual complete and partial capture JSON serialization. The fallback label now states missing summary without guessing execution stage. One fresh hosted diagnostic run will verify reporting end to end. Physics, source voltages, original solver tolerances and acceptance gates are unchanged; no PHY completion is claimed.

## 2026-10-15 — exact VBIC terminal playback prepared on hosted runner

ALL CLOUD; full goal OPEN; local workspace empty.

New `tx-vbic-playback-cloud` scoped push starts a bounded diagnosis of the actual failing `xtree.xd0002` (Nx6 npn13g2, original125C/hbt_wcs). It restores exact compact strict source38763917040, preserves every original native terminal sample before1.2ns with17-digit binary64 roundtrip, and interpolates only the explicit final1.2ns endpoint. Collector/base/emitter/substrate playback is common across all four cases: TMAX0.125/0.0625ps, chgtol1e-14/1e-20C. Same original model/geometry/corner/OFF startup and source runtime; no model substitution or changed full-circuit oracle.

It saves all terminal currents, native internal charges/capacitances and thermal-node voltage. All cases continue independently after native failure, retaining partial outputs and diagnostics. A green workflow is execution only; inspect `all_simulations_complete`, individual errors and comparison metrics. PWL playback introduces slope knots and removes feedback, so no physical/full-wave acceptance is possible from this isolated circuit. The next conclusion must distinguish model-local sensitivity from feedback/hidden-state effects.

Mainchip38731744914 is terminal6h timeout with21NDR relaxations. Its process guard has600hosted passing tests; no expensive route restarted. Inspect exact saved guides/ODB and clock congestion before a new route hypothesis; preserve all original rule and timing gates.

## 2026-10-15 — NDR fail-fast validated; no active mainchip route

ALL CLOUD. Local workspace empty. Full goal OPEN; prior turn is concrete progress, not an external blockage.

Source **b2c31bbb90e0ba23ced139ceb05868a274797c43** validated by **38783522114 /116589542268 SUCCESS600tests**. New NDR rejection actually kills launched descendants; healthy global-route output and unrelated phases survive. Original gate self-tests and all startup diagnostic/encoding controls also passed. No expensive native route was restarted.

Read `docs/native-vbic-and-route-findings-20261015.md` before continuing. Mainchip38731744914 is TERMINAL6h timeout with21NDR relaxations, not running. Charge study38782025812 is TERMINALnative VBIC abort; two baselines complete, tight-charge capture incomplete, fourthcase absent. Both receipts and raw failure archives are pinned. Model audit establishes VBIClevel9, TD0; distinguish subcircuit selft from unset modelSELFT. No claim of a simulator/model bug yet.

Next available work: isolate the specifically failing VBIC device with exact frozen model/geometry/corner and original terminal playback to test charge/current continuity; retain original full-wave oracle and all failures. Separately inspect saved complete failed guides/ODB and clock congestion before selecting a new physical routing experiment. Do not re-run rejected upper_metals/upper_three unchanged or finer full-wave simulations without new evidence.

## 2026-10-15 — mainchip timeout is terminal; native charge study exposes VBIC failure

ALL CLOUD. Full goal OPEN. No live mainchip route remains; do not describe the old handle as running.

Mainchip **38731744914 /116410943697** TERMINAL cancelled at6h. GitHub annotation explicitly says maximum execution time6h0m0s. The publisher preserved the138,996,116-byte archive and335,777-byte partial JSON. Receipt `docs/evidence/pcie-mainchip-upper-three-timeout-20261015.json`. Native log has21GRT0273NDR relaxations; first12:38:23UTC (clk_i/PCIe/ETH), then repeated iteration resets. Final global route and extracted timing are not complete. Partial JSON still says pending and is not a live-process signal.

Controller now stops NEW global-route trials immediately on native NDR relaxation, preserving rejection JSON/log/Tcl and killing the entire launched process group. It retains pre-route checkpoints and source constraints. Three real hosted subprocess tests cover rejected descendants, healthy routing and unrelated phases. Source-validation workflow push runs these before reuse. Do not replay upper_metals or upper_three unchanged; their constraint failures are established. Next mainchip hypothesis must address placement/clock congestion using saved exact state, not disable NDR or claim a guide pass.

Charge experiment **38782025812 /116584407140** restored source successfully and completed both baseline prefixes. Native chgtol1e-20C then aborts around0.54333ns atxtree.xd0002:npn13g2_nx_vbic; returncode0 did NOT mean a successful transient. Receipt `docs/evidence/pcie-timestep-charge-abort-20261015.json` preserves the native diagnostic and incomplete capture. Fourth case never ran. Do not adopt this charge tolerance or rerun full34ns.

The exact frozen source/native model audit proves active HBT model is VBIC, not HICUM. Native RTH/CTH are nonzero. Earlier exploratory HICUM source reading is not evidence about this circuit. Frozen model text and native parameters are included in the charge receipt with source SHA and lossless encoding. Inspect ngspice47 VBIC load/truncation/thermal/excess-phase code against these exact settings. No bypass or model change has been made. All original physical/device/bit/numerical gates remain unchanged.

## 2026-10-15 — repair byte-preserving model audit before charge study

ALL CLOUD; full goal OPEN. Native source/capture hashes restored successfully in38781466652, but the new source-text audit stopped BEFORE any simulation on a non-UTF8 micro-sign byte0xb5. This is a controller preflight failure, not device behavior. Receipt `docs/evidence/pcie-charge-model-audit-failure-20261015.json` retains its exact error and zero cases.

`model_source_record` now records UTF8 or lossless Latin1 with byte-for-byte roundtrip and SHA validation. ASCII, Latin1-micro and UTF8-micro controls cover this actual failure. No model bytes are rewritten, decoded text is only diagnostic evidence. Frozen HBT/resistor sources and first baseline native model parameter dump will be included in the summary, enabling RAM-only source inspection without local artifact downloads. Scoped workflow push retries charge_tolerance once; record the new run and inspect native charge readback/convergence before any full-wave retry.

Mainchip38731744914 remains live as last verified. Preserve it; it approaches its hosted6h limit around18:03UTC. Terminal timeout is not routing success. Inspect retained NDR/overflow/partial reports before another run.

## 2026-10-15 — source-bound charge tolerance and frozen model audit prepared

ALL CLOUD. Full PHY/mainchip detailed routing/final timing OPEN. Local workspace remains empty.

Three completed startup diagnostics ruled out TSTEP and matrix backend; finer TMAX and Gear2 did not converge. Native option readback shows charge tolerance still1e-14C despite strict Newton tolerances. New hosted `charge_tolerance` study tests that distinct numerical hypothesis at fixed original circuit/model inputs: baseline and chgtol1e-20C, each atTMAX0.125/0.0625ps, fixedTSTEP0.125ps, trap/Sparse. It retains all original flags/solver settings/zeroOP and native raw rows. Actual native charge-tolerance readback is required, with missing/duplicate/wrong-value controls. Both short baselines must still reproduce original full capture prefix; no full-wave or physical acceptance.

The same hosted restore also preserves the exact hash-bound HBT/resistor source text and native `showmod` output for parameter investigation. No device/model/geometry changes or bypass mutation are implemented. This avoids reasoning from a different PDK revision or assuming which model switches are active. Scoped workflow push starts the diagnostic once; record its run ID and inspect original source model/case outputs on completion.

Mainchip38731744914 /116410943697 remains live as last checked; preserve it. On terminal state inspect native NDR, overflow and timing with manualGRT0273screen for this older controller. No detailed routing/extracted signoff inferred from global guides.

## 2026-10-15 — native matrix backend ruled out; all three startup studies complete

ALL CLOUD. Local workspace remains empty. Full serialPCIePHY, detailed mainchip routing and final extracted setup/hold remain OPEN. Prior turn made concrete progress through three completed hosted diagnostics and source-bound receipts; this is not an external blocker.

Matrix study **38780011601 /116577469224** COMPLETE: KLU native availability, actual per-case backend readback, all62OFF flags, original circuit/model hashes, solver settings and zero operating point verified. Four complete native prefixes preserved. Receipt `docs/evidence/pcie-timestep-matrix-solver-20261015.json`. Sparse/KLU voltage differences are only2.21823e-13V at0.125ps and3.39395e-13V at0.0625ps. Both retain the same8.906847247mV TMAX difference. Therefore backend choice does not explain the discrepancy. Do not repeat this study or adopt KLU as a convergence fix.

Earlier factorial38777870655 ruled out TSTEP (37.6368nV); refinement38778734039 worsened trap discrepancies8.9068->9.8918->12.2343mV and Gear2 remained8.3171mV. All original0–34ns failures remain. No shifted startup/window/gate, no physical acceptance. Shortened baseline reproduces original prefix exactly through1.1ns.

Next investigate the frozen device/model transient evaluation and bypass/charge handling rather than another blind finer full-wave run. Native47 option readback has chgtol1e-14C, Sparse1.3 baseline, no conductance shunt. Exploratory source read of ngspice47 HICUM2 shows bypass disabled under selfheating and a CKTterr charge list; this does not yet establish which model settings are active or a bug. Verify frozen model parameters and actual option readback before any new hypothesis. A labelled isolated component diagnostic can identify the source without changing full-circuit acceptance. No bypass/model change implemented yet.

Mainchip **38731744914 /116410943697** remains in_progress as live-verified when this checkpoint was written; started12:03UTC. Preserve it. On terminal completion inspect complete native NDR/overflow/STA and failure artifacts. Its older controller needs manual GRT0273 screen. Global guides never close detailed metal or final extracted timing. Do not duplicate healthy jobs.

## 2026-10-15 — finer trap and Gear2 do not converge; matrix backend diagnosis prepared

ALL CLOUD, local workspace empty. Full goal OPEN.

Refinement **38778734039 /116573062910** completed all six1.2ns native captures with verified model hashes, options,62OFF flags and zero operating point. Baseline prefix exactly reproduces original through1.1ns. Receipt `docs/evidence/pcie-timestep-refinement-20261015.json`. Trap successive maximum voltage differences WORSEN:8.906847247mV (0.125->0.0625ps),9.891831193mV (0.0625->0.03125ps),12.234292598mV (0.03125->0.015625ps). Gear2 coarse/fine difference8.317086327mV; cross-method differences3.251660917/3.841691824mV. Neither finer TMAX nor Gear2 repairs this. Do NOT run expensive full-wave versions merely from these failed prefixes.

Actual native option readback identifies Sparse1.3 matrix backend. Next bounded hosted `matrix_solver` study compares Sparse and KLU at fixedTSTEP0.125ps and TMAX0.125/0.0625ps, original circuit/models/flags/tolerances. Scoped workflow push starts once. Native KLU availability preflight must pass; each real case must show intended backend in native option output. This tests a numerical hypothesis, not a proven root cause or acceptance. Preserve all failed captures. Original complete34ns gates remain required.

Mainchip38731744914 remains live as last verified; retain it. Detailed metal/extracted timing and full serialPHY are not complete.

## 2026-10-15 — TSTEP hypothesis ruled out; TMAX refinement prepared

ALL CLOUD. Full serial PHY, detailed mainchip routing and final extracted setup/hold remain OPEN. Local workspace remains empty.

Hosted factorial **38777870655 /116570107593** completed all four native captures, exact source/circuit hashes,62OFF flags, solver readback, zero operating point and six negative controls. Receipt `docs/evidence/pcie-timestep-factorial-20261015.json`. The1.2ns prefix matches the original full capture exactly through1.1ns (zero voltage difference). Changing TSTEP alone gives only37.6368nV. Changing TMAX alone reproduces8.906847247mV atv(mr),0.595716ns. Therefore TSTEP is not the significant cause; original convergence failure remains.

New hosted `tx-step-factorial-cloud` source prepares study `refinement` (automatic scoped push). FixedTSTEP0.125ps; trap TMAX0.125/0.0625/0.03125/0.015625ps plus Gear2 TMAX0.125/0.0625ps. Same source capture/models/options/minbreak except explicitly recorded integration method and TMAX. Same1.2ns diagnostic only, no full34ns acceptance; preserve every raw row and failure. Inspect native option/flag readback, baseline prefix reproduction, successive-step and cross-method differences before selecting a full-wave rerun. Do not repeat old factorial.

Mainchip38731744914 /116410943697 still live as last verified. Preserve it and inspect terminal NDR/overflow/STA evidence. Do not infer detailed routing or final timing from global guides.

## 2026-10-15 — signed HBT readback complete; cloud-only checkpoint

All execution and evidence remain in GitHub. Local workspace is empty. Full goal remains OPEN.

Signed-polarity diagnosis **38776558304 /116565617226** completed successfully. All62HBT native terminal observations, full original capture/hash readback, original engineering review and four corrupt-input controls passed. Receipt pinned under `placement_variants.compact_return_strap.bias_candidates.native_res_tc.compact_cold_hbt_polarity_diagnosis`. Original source run38767312141, compact cold_high_hbt_wcs, native_res_tc. Forward-VBE heuristic failures remain; signed observations do not grant qualified SOA or physical acceptance. No need to rerun this diagnosis.

Strict comparison38774749514 FAILED: compact8.906847253mV and wire8.111543842mV versus1mV. Preserve full startup and all original gates. Investigate separate TSTEP/TMAX dependence before another long run; not yet implemented. All six joint-sizing cases38773059353 are pinned; candidate rejected because all three wire cases fail. Probe counts read from actual `hbt_devices`/`mos_devices` fields:62/64.

Mainchip38731744914 remains live as last verified. Read its terminal native NDR/overflow/STA before deciding next route. Do not duplicate/cancel healthy jobs. Global route does not close detailed routing or extracted final setup/hold.

## 2026-10-15 — strict convergence still fails; sizing study fully rejected; signed HBT diagnosis running

ALL CLOUD. Local workspace is empty; keep all source, native execution, artifacts and resume state in GitHub. Full serial PHY, detailed mainchip routing and final extracted setup/hold remain OPEN.

Strict full-wave comparison **38774749514** completed execution successfully but FAILED its original numerical gate. Both source-bound captures and comparison are pinned, including all peak witnesses. Compact maximum voltage difference remains **8.906847253mV** against1mV. Tight nonlinear tolerances did not repair startup discrepancy. Do not rerun those four complete captures or remove startup. Next investigate explicit TSTEP versus TMAX: current `tran step stop 0 step` changes both; this is a hypothesis, not an established cause. A bounded diagnostic must preserve sources/model/options and isolate the two parameters before another long full-wave run.

Joint sizing study **38773059353** is COMPLETE with all SIX cases in the same candidate study. Three compact cases pass original electrical gates, but ALL THREE distributed-wire cases fail: hot_low has28wrong-sign samples and negative output margin; hotRES has576interface-margin failures and six data HBT low-VCE failures; coldHBT has two selector low-VCE failures. Candidate remains REJECTED and its changed device geometry is not represented by old metal. No adoption or physical acceptance.

Signed HBT source validation **38775537520 /116562080343** passed597tests and polarity controls. Source **f969704bf6bf80ca6adce302367cd13250a58bf9** retains original absolute-VBE screen while measuring forward/reverse junction polarities separately. Official BVEBO process measurement is reverse emitter-base; a positive1.023V VBE is not itself evidence of reverse breakdown. Public monitor targets are not qualified SOA. See `docs/hbt-operating-limit-provenance-20261015.md`. No existing screen waived and no device safety acceptance claimed.

Hosted original compact cold-HBT diagnosis **38776558304** is running on that source. Inspect its complete62-HBT signed observations, original review readback and negative controls, then pin its receipt. No new native simulation is required for this analysis.

Mainchip **38731744914 /116410943697** remains live as last checked. Preserve it; inspect terminal native NDR/overflow/STA evidence. Global routing is not detailed metal or final extracted timing. Do not duplicate a live run.

## 2026-10-15 — all strict fine captures complete; joint sizing rejected by hot wire

ALL CLOUD. Strict solver study **38763917040** is COMPLETE with four pinned native captures. The last wire 0.0625ps case passes original component gates at **100.722432816mV** output margin; no diagnostics. This is NOT yet numerical convergence proof. Next dispatch exactly one hosted `step_comparison`, placement `compact_edge_supply`, solver `breakpoint_tight_trap`, step_pair `fine`. Compare every original voltage/sample/edge/energy gate and preserve earlier default and breakpoint-only failures.

Joint sizing **38773059353 / data8_select10** is REJECTED for adoption. Its wire hot_low has **28 wrong-sign output samples**, 128 below100mV samples, minimum margin **-9.604110343mV** at unchanged0.3UI. Final interface has1161below150mV samples, CMmin1.784219876V; three data HBT VCE minima are below0.4V (worst0.397838551V). This failure and all three compact passes are pinned in the SAME candidate loaded_study (four cases so far). Remaining wire hotRES/coldHBT jobs are still running; let them finish and preserve results, but do not generate/adopt candidate layout from compact passes.

The larger final input loading damages bandwidth and shifts the voltage problem. Next physical/circuit hypothesis must address stage-drive and stack headroom jointly; do not repeat this exact rejected sizing or relax source-bit sampling. Original V10 remains the source-bound physical reference with its own unresolved corner failures.

Mainchip **38731744914 /116410943697** remains live. Current source-code inspection confirmed FastRoute soft-NDR modifies route edge cost and DRT independently reads database NDRs; no acceptance gate or constraint was changed. Global guidance alone is never final metal/DRC/STA evidence. Local workspace remains empty.

## 2026-10-15 — first joint-sizing native compact results pass; wire results pending

ALL CLOUD; full PHY and final chip timing remain OPEN. Study **38773059353** (`data8_select10`, fixed TC feed) has initial native results pinned under the candidate's own `loaded_studies` record. Append future cases to this SAME study.

The compact cold-HBT case now passes all original electrical gates: all twelve previous data-HBT VBE violations are absent, output margin **255.873662589mV**. Final interface CMmax **2.049776663087V**, only 0.223337mV below its 2.05V bound; do not infer robust PVT coverage. Compact hot_low also passes with output margin **186.396133923mV** and no HBT/MOS failure. The remaining source-bound cases must decide whether increased loading is acceptable. No layout integration or extracted candidate acceptance is claimed.

Wire jobs retain their existing handles from the prior checkpoint; do not duplicate. Changed devices still use original metal as a diagnostic control and `component_screen_passed=false` by construction. Require successful original-gate sensitivity evidence before new matching physical layout/extraction, and all independent corners/numerical/fault checks before acceptance.

Strict fine-step wire job **116522064672** and mainchip job **116410943697** remain running as last verified; preserve them. Local workspace verified zero entries.

## 2026-10-15 — joint headroom candidate is running in six hosted native cases

All work remains in GitHub; the local workspace is empty. Full serial PHY, mainchip detailed routing and final extracted setup/hold remain OPEN.

Source validation **38772760436 / 116552566371** passed **597 tests**, including exact 16-device sizing changes and rejection of missing, duplicate, wrong-model, wrong-Nx, duplicate-Nx and unknown-profile inputs. This validates the implementation, not the candidate circuit.

Native study **38773059353**, source **1e67372eaf1105c0b48fe2f54943695c2b3563f5**, is now running: `headroom_corners`, `compact_return_strap`, `native_res_tc`, `data8_select10`, default solver. Do not dispatch again. Jobs:
- compact hot_low: 116553595814
- compact hot_low_res_bcs: 116553595825
- compact cold_high_hbt_wcs: 116553595969
- wire hot_low: 116553595994
- wire hot_low_res_bcs: 116553596016
- wire cold_high_hbt_wcs: 116553595595

Publisher release groups append `-data8-select10`. Store successes AND failures under `placement_variants.compact_return_strap.sizing_candidates.data8_select10.loaded_studies`. Evaluate `diagnostic_screen_passed` and full original review: `component_screen_passed` is intentionally false because the changed device geometry does not yet have matching layout/RC. Actual candidate parameters are twelve final data Nx8 and four selectors Nx10; tails/reference and all R/C remain unchanged. New physical generation, DRC/LVS and extracted corner verification are still mandatory if it improves all diagnostic gates. Earlier V11/data-only failures remain evidence.

The compact cold VBE analysis **38771786806** is COMPLETE and pinned. It located real data-transition peaks rather than a removable startup transient. Original 1V bound stays unchanged.

Strict numerical study **38763917040** still has wire 0.0625ps job **116522064672** running; other three source-bound cases are pinned. Append its terminal receipt to the same study, then run hosted `step_comparison`, `compact_edge_supply`, `breakpoint_tight_trap`, `fine`. No convergence claim until all original full-wave gates pass.

Mainchip **38731744914 / 116410943697** remains running. Preserve the job and inspect native NDR relaxation, overflow and actual final reports when terminal. Its global route cannot stand in for detailed routing or extracted final STA.

## 2026-10-15 — cold VBE failure is a real data-transition peak; joint sizing candidate prepared

ALL CLOUD; fullgoal OPEN. Nativecompactdiagnosis38771786806 PASS exactoriginalreadback, notcircuitacceptance. Twelve finalNx3 data HBTVBE peaks occur after2ns in actualdata transitions: worst1.023395260872V at3.27075ns,2.230071699649mA/emitter, base2.157906922V/emitter1.134511661V. Otherbankpeaks2.39575ns,3.39625ns,7.02075ns. Startup-window removal would not fix this. Complete evidence under newground.bias_candidates.native_res_tc.compact_cold_hbt_diagnosis.

Source997977262e643a88b50c37f0189f76d4f703a88c prepares bounded `assembled_sizing=data8_select10`/`study=headroom_corners`: dataNx3->8 andselectorsNx6->10 together, allotherdevices/metal/bitsequence/gates unchanged. Candidate canonicalV12 source saved for futurematchingphysicalgeneration. This is distinctly NOT existing V11 data-only sizing. Oldphysicalmetal is explicitly marked mismatchingcandidategeometry, and component_screen_passed forcedfalse; only diagnostic_screen_passed canpass. Every original source/mutateddeck is hash-bound. Six corruptsource tests plus exact16devicechange test added.

Validation38772760436 isLIVE. AfterPASS inspect logs then dispatch tx-tree-assembled-wave-cloud once: studyheadroom_corners,placementcompact_return_strap,pre_biasnative_res_tc,assembled_sizingdata8_select10,solverdefault. Sixcases=compact/wire byhot_low/hot_low_res_bcs/cold_high_hbt_wcs. Keepresults undersizing_candidates, notphysicalvariant acceptedstudies. If anygatefails retain it; noautomaticadoption.

Strictfinewire0.0625ps38763917040/116522064672 and mainchip38731744914/116410943697 remainlive aslastchecked. Do notduplicate. Whenstrictpaircompletepin4thcase andrun fullstrictfinecomparison. Localempty; noCAD/tests/artifacts writtenlocally.

## 2026-10-15 — compact VBE event diagnosis running; frozen HBT sources verified

ALL CLOUD. Source audit38771062868/job116546679607 PASS,197frozenfiles verified; receipt `docs/evidence/pcie-hbt-geometry-source-20261015.json`. Exact npn13G2PCell has Nx1..10,le0.9um,we0.07um; avoid arbitrary emitter-length change. Current V10 dataNx3/selectorsNx6/tailsNx8. Historical Nx4..6 experiments and actualV8 geometry already failed hotcases; inspect earlierrecords before selecting newgeometry.

New analyzer sourceff6fb0fee1444f1a764c4735e2c7bb35cd04d630 adds exact `mode=compact` diagnosis, retains originalfullwave gates and skips inappropriate distributed-wire inference. Hosted validation38771602581/116548545517 SUCCESS590tests plus5missing/duplicate/wrongbias/wrongsolver/faultsource controls. No altered threshold, phase, oracle or transient.

Native analysis38771786806/job116549186902 LIVE: wave_diagnosis,compact_return_strap,cold_high_hbt_wcs,native_res_tc,modecompact. Inspect exact maxVBE events to determine startup versus data transition before changing physical transistor sizing. Uses original38767312141 compactcapture, no SPICE rerun. Release group has `-compact` suffix. Source scope must be compact and all original review fields match exactly. Pin full event evidence on completion; retain wire failures.

Strictfine38763917040 wire0.0625ps116522064672 andmainchip38731744914/116410943697 remainLIVE. No duplicate/restart. Appendfinalfinecase then hostedstrictpairedstepcomparison before anynumericalpass. FullPHY/mainchipdetailedroute/extractedsetuphold OPEN.

## 2026-10-15 — TC corner results and exact interface failures pinned

ALL CLOUD; full PHY, mainchip route and final setup/hold remain OPEN. Local workspace stays empty.

TC candidate run38767312141 is complete: all8 original compact/wire cases pinned without dropping failures. Wire cold resistor corner now passes: CMmax2.048618029V, outputmargin262.449760347mV. Wire hot resistor corner still fails CMmin1.789821675V and tail HBT VCE0.393495720/0.391323273V. Compact cold resistor CM and cold HBT VBE failures persist. Feed layout/RC remains unintegrated; candidate NOT adopted.

Interface diagnosis38769063249 (sourcec904a7...) verifies exactoriginal6912physical final interface samples. Originalbias hotres has1539below1.8V CM samples; minimum1.784024457V at bit41, phase0.3UI,7.1625ns, physicalt053_b/t046_b. Signedmarginthere249.614mV. No wrongsign or below150mVinterface sample. Complete original capture readback and injected witness controls passed; new `interface_failure_diagnosis` supplements original ground diagnosis.

Strictnumeric run38763917040: compactpair andwire0.125ps complete/componentPASS; samepartialstudy now3cases. Wire0.0625ps job116522064672 remainslive aslastchecked. Appenditwhencomplete then dispatch hostedstep_comparison, profilecompact_edge_supply,solverbreakpoint_tight_trap,step_pairfine. Prior startupvoltagefailure remainsopen untilcompletepairedcomparison.

Mainchip38731744914 job116410943697 stilllive aslastchecked. Preserve actualNDR; inspectGRT-0273 beforeacceptance. No detailroute/finalSTA claim.

## 2026-10-15 — newground TC ordinarycorners PASS; exact interface witness analysis LIVE

UTC 2026-10-15T16:28:49.144119+00:00. ALL CLOUD; goalOPEN. TCnativefeed remains schematic, notphysicalintegration.

**38765529919 newgroundnative_res_tc temperature_voltage COMPLETE4cases**: wirehotmargin**101.179299331mV**, finalCM1.811236808..1.851114723V, all62HBT64MOS/interfacesPASS, no diagnostics; wirecoldmargin265.199365834mV,finalCM1.987401859..2.024985750V. Only1.179mVoveroutputlimit; not robustfullPHYacceptance. SAMEbiascandidate study nowcomplete. **Nominal38767316386 COMPLETE2cases**, receiptsadded undernewvariant.bias_candidates.native_res_tc.loaded_studies.

**TC independentfailingcorners38767312141 source12b3d1847d2713cbc9e96555099788b64092ab2e** LIVEwirejobs: hotHBT116533783556,coldRES116533783939,hotRES116533784096,coldHBT116533784247. Fourcompactreceiptsnowpinned: coldRES CMmax2.054162684VFAIL; coldHBT CMmax2.045853876Vnowwithinlimitbut12dataHBTVBE up to1.023395261VstillFAIL. Hotcompactpass. Appendwireterminalresults to SAMEpartialstudy, preserveallfailures. Noadoption/physicalfeedclaim.

**Interface diagnostic sourcec904a7f2c65ea94582875823077b6279fdf75f4e** adds `interface_sample_witnesses`: actualbit/index/phase/time andp/nphysicalterminal pair atminimumsignedmargin/minimumCM/maximumCM, exactnativebrackets/neighborsandclock/biascontext, first12failedpairspluscompletecounts. Reconstructs exactoriginal6912final/768CMOSsamplereviews, nooracle/phase/window/thresholdchange. Cloudvalidation**38768007863/116536177949 SUCCESS590tests**, plusinjectedupper/lower/wrongsignsourcewitnessandmissingcoveragecontrols.

**38769063249** wave_diagnosis compact_return_strap/hot_low_res_bcs/native_res/default isLIVE, sourcec904a7... . It reads existingfailednativecapture, doesnot rerunsimulation. Inspect `interface_sample_witnesses` and deriveactual commonmode-failure timing/bit/physicalnet beforebias/geometrychanges. Keep previousgrounddiagnosis38763079513; newreceiptshouldbeadditionalinterface diagnosis ratherthan erasepriorproof.

Strictsolverrun38763917040 oldedge/breakpoint_tight_trap:2compactcapturesPASS,pinned;2wirecaptures116522064672/116522064809LIVE. Oncecompleteappendthenfullhostedstep_comparison withstrictprofile/finepair. Previous8.9/8.1mVstartupfailure stillnotclosed. Mainchip38731744914/116410943697LIVE;6hourlimit~18:03UTC. NoNDRwaiver/detailroute/finalSTAclaim. Localempty.

## 2026-10-15 — strictcompact pair complete; actualnewground hotmargin106.98mV

UTC 2026-10-15T16:12:19.681290+00:00. ALL CLOUD. Goal OPEN, authoritative newmeasurements pinned.

**38763917040 breakpoint_tight_trap**: BOTHcompact0.125/0.0625ps complete/PASS, samefull34ns/originalgates. New0.0625ps546310rows,232.890245390mVmargin, no diagnostics. SAMEpartialstudy now2cases. Wire0.125ps116522064809 and0.0625ps116522064672 remainLIVE; oncecomplete append and run fullstep_comparison(profilecompact_edge_supply,solverbreakpoint_tight_trap,step_pairfine). No extrapolatedconvergence from closeoutputmargin.

**38764229637 newground native_res temperature_voltage** now COMPLETE4cases/PASS. Newlypinnedwirehot:106.977256367mVmargin, finalinputCM1.802968707..1.843718782V, finalinputmargin172.591974618mV, all62HBT64MOSpass. Nativecoldwire265.267858545mVmargin. Ordinarytemperaturepass doesnotcloseindependenthotres/coldresfailures.

**38765529919 newground native_res_tc temperature_voltage**: compacthot/cold complete/PASS,pinned underbias_candidates.native_res_tc.loaded_studies SAMEpartialrecord. Wirehot116527620549 andwirecold116527620239 LIVE. Retain fixed feedgeometry andalloriginalgates; candidatefeedphysicalintegration absent. Need comparewirehotmargin against106.977mVbaseline: oldedgeTC had95.66mVfailure; do notassumecombinedcandidatepass. Ifpassesordinarycorners, stillneedsindependentfailingcorners/MOS/fault/numericalfullreadback.

Read-only headroomcheck: newgroundhotres finalclockHBTVCEminxd0001=0.406333221V,xd0003=0.406117596V, whiletail6/7 are0.392685020/0.390512435V. Simplyraisingclockcommonmode couldmovefailureintoclocktransistors; no suchchange made. Wholeloadeddesignneedscombinedcurrent/headroomandcommonmodecorrection, notthresholdrelaxation. Evidence originalhotres38760726764 summary retainsalldevicevalues.

Mainchip38731744914/116410943697 live aslastchecked. Noadditionalmainchiprunsstarted; waitcurrentrun, inspectnativeGRT-0273 andallactualtiming beforeanyacceptance. FullPHY/mainchipdetailroute/finaltiming notclosed. Localworkspaceempty.

## 2026-10-15 — strict firstcompact PASS; ground temperature control and TC candidate LIVE

UTC 2026-10-15T16:06:01.127969+00:00. ALL CLOUD; localempty. Concreteprogress: strictcompletedcapture andtemperaturecontrols nowpinned, new nativeTCtrial dispatched.

**38763917040 strictfine**, compact_edge_supply/breakpoint_tight_trap/sourcea7882b...: compact0.125ps116522064741 COMPLETE,274826unmodifiedrows to34ns,232.890381538mVoriginaloutputmargin,62HBT64MOS/interfacesPASS, no diagnostics; all strictnativeoptions/minbreakreadbackverified. Partialloaded_study created with1case; append remainingcompact0.0625ps116522064101 andwire0.0625ps116522064672/wire0.125ps116522064809 when terminal. No convergenceacceptance until fullpairedhostedcomparison; oldstartupFAIL retained.

**38764229637 newgroundtemperature/native_res/default/sourcea7882b...**: compacthot/cold andwirecold complete/PASS,pinned3cases inpartialstudy. Wirecoldmargin265.267858545mV,finalCM1.995138534..2.031777366V. **Wirehot116523140140 remainsLIVE**; appendreceiptwhencomplete. This ordinarytemperaturestudy doesnotcloseknownhotres/coldresfailures.

**38765529919 newgroundtemperature/native_res_tc/default**, sourceba6404a7fca61de707411334f2017cd704fb9449, LIVE: compacthot116527619969,wirecold116527620239,compactcold116527620372,wirehot116527620549. Existingfixedgeometry feed100um/1umRsil+16.5um/2umRppd, noPVTretuning/idealclamp. OriginalRCmodel/gates retained. Newvariant.bias_candidates.native_res_tc initialized withactive_trial andemptyloaded_studies; append allsuccesses/failures HERE, notbaselinevariant studies. Compare newgroundhotmarginwithsameconditionnative_res oncebothcomplete; oldedgeTCfailedhotmargin95.66mV andhotresCM/VCEstillfail. Feedlayout/RCintegrationunproven; do notadoptfromonecorner. Completealloriginalindependent/MOS/fault/numericalrequirementsbeforeacceptance.

ReasonforTCretest: actualnewground changedtailcurrentandheadroom, so oldTC marginfailure doesnotpredictcombinedcandidate. Do not blindlywidentheground; exactold/newbiasinteraction alreadyrecorded. CurrentnativecoldHBTwirepasses butcompactcoldHBT/VBEfailsretained. Mainchip38731744914/116410943697 continues; inspecteffectiveNDR GRT-0273 atterminal. FullPHY/mainchipdetailroute/finaltimingOPEN.

## 2026-10-15 — strict solver LIVE; newground full corner results and bias interaction preserved

UTC 2026-10-15T15:57:39.759849+00:00. ALL CLOUD. Implemented **breakpoint_tight_trap** sourcea7882b4620a1600ade8020a452d4a28e25f0b7f8: exactexisting tighttrap opts(methodtrap/maxord2/reltol1e-6/abstol1e-13/vntol1e-8/trtol1/itl4=100)plusminbreak1e-18. Everyoption andnative minbreakreadback required; originalphysics/stimulus/windows/limitsunchanged. Validation **38763516085/116520675995 SUCCESS590tests** pluspeakwitnesscontrols.

**38763917040 strict fullfine captures** sourcea7882b..., compact_edge_supply/native_res/breakpoint_tight_trap: compact0.0625ps116522064101; wire0.0625ps116522064672; compact0.125ps116522064741; wire0.125ps116522064809. All4actualsolverpreflightsPASS; all4capturesLIVE. Pinnewstudy oncecomplete, then hostedstep_comparison solverbreakpoint_tight_trap/step_pairfine. Preserveoldstartupfailures; do notexclude0..1nswindow. No nativewaveacceptance yet.

**Newground38760726764 COMPLETE8cases**; bothcoldwire receipts appended. WirecoldresFAIL CMmax2.053656336217V, margin262.458267942mV; wirecoldhbtPASS margin235.661349271mV, CM1.980368625..2.022497707V, noHBT/MOSfail. Compactcoldfailuresretained. WirehotresFAIL CMmin1.784024457V andtailVCE0.392685020/0.390512435V. Groundprofile notadopted.

**Ground diagnosis38763079513 COMPLETE**, source1220055a..., exactfailednewwirearchive/output/reviewreadback preserved. Receipt nowvariant.ground_path_diagnosis, exactcomparison invariantseparatenativetimes undervariant.measured_return_strap_comparison. E6 oldminimumat2.38675ns vsnew2.38725ns: cannot claim exactsame sample. E7 bothat2.38725ns, emitter67.0548→55.4189mV, collector458.5265→445.9313mV, currentperemitter0.659695→0.732030mA. Thuslowergroundvoltage didnotrestoreVCE duecollector/currentinteraction. E6similardirection atitsseparate extrema. NewshortestpathboundsE6=13.439735576ohm/E7=15.768369676ohm areNOTeffectiveR. Medianfinalfeed1.040634837mA vsold1.036876374mA. Do notblindlywidenthegroundagain; bias/current/cornerrepair needsoriginalfullgates.

**38764229637 temperature_voltage**, sourcea7882b..., compact_return_strap/native_res/default, LIVE. Obtain actualnewgroundhot_low/cold_high margins before choosingbiasrepair. Existingfixednative_res_tc candidate improvedoldcoldcommonmode butfailedoldhotmargin; combiningwithnewgrounduntested. Preservealloriginalqualificationrequirements.

Mainchip upper_three38731744914/116410943697 live;6hourhostlimit~18:03UTC. ScreenfinalGRT-0273beforeacceptance. FullserialGen3x4/mainchipdetailroute/finalextractedsetuphold remainsOPEN. Localempty.

## 2026-10-15 — returnstrap does NOT fix hotres; numerical peak is early startup

UTC 2026-10-15T15:44:51.352571+00:00. ALL CLOUD. New measured evidence preserved, no acceptance gate changes.

New **compact_return_strap** nominal wire38760721744/116510975999 COMPLETE: componentPASS, minmargin241.303595309mV, finalCM1.899492141..1.937652154V, all62HBT64MOSpass, zero diagnostics. Study nowcomplete2cases. Hotwire38760726764 cases pinned into SAMEpartialstudy:
- hot_low_res_bcs116510995555 remains **FAIL**: margin133.097640691mVpasses, finalCMmin**1.784024457099V**fails1.8Vfloor; xd0006VCEmin**0.392685020224V**, xd0007**0.390512435002V**fail0.4Vfloor. Slightly worse than oldedgegeometry0.393965736/0.391471681V. Real groundstrap is NOT adopted as successfulrepair, despite nativephysicalRCpass. Need exact emitter/collector currents/voltages and nativepath comparison before more geometry.
- hot_low_hbt_bcs116510995390 componentPASS, margin222.040388714mV, CM1.808307639..1.844095203V.
- coldwire jobs116510995594/116510995729 remainLIVE lastcheck. Append their terminal receipts; preserve compactcoldfailures alreadypinned.
Next dispatch wave_diagnosis compact_return_strap/conditionhot_low_res_bcs/native_res/default. It reads exact failednewwirecapture and computes actual groundpaths for comparison with old ground_path_diagnosis38751904886; no alteredRsubstitution or acceptance.

**Peak diagnostic38761402814/116513324545 COMPLETE**, source2b43250..., full4sourcecapturesreadback and allnativeoutput/review matches. Failure unchanged: compactv(mr)**8.906956733mV at0.595785ns**, wirev(xtree.t007_b)**8.111490836mV at0.714410ns**. Compactmr above1mV from0.512285..0.788410ns; wiret007b from0.586410..0.917660ns. Originalnative neighbors show sustainedstartupoffset, not just isolated interpolationpoint. Other internalpeaknodes around0.686..0.689ns. Fullwitnesses pinned in newtimestep_comparisonsreceipt. Do NOT discardstartupwindow. Nextnumericalcandidate: combine existing tight_trap tolerances with verified minbreak1e-18; earlier tighttraponly failedPWLbreakpoints whereas minbreakalone fixesendtime butnotstartupconvergence. This combinedprofile is NOTyet implemented. Add actualnative optionreadback/invariancechecks and cloudtests before fullpairedcaptures; preservealloldfailures.

Mainchip upper_three38731744914/116410943697 still running; no detailedroute/extractedtiming or fullPHYclaim. GoalOPEN; localempty.

## 2026-10-15 — original cold failures preserved; new wire trials and peak diagnosis LIVE

UTC 2026-10-15T15:41:04.425761+00:00. ALL CLOUD. Diagnostic source2b43250da0da0c3453fa128ca6519c2b4725c4f4 now reports exact maximum-error native time/index/value, native neighbors, fine interpolation bracket and full-window violation span. All original limits/windows unchanged. Validation38760959809/116511783482 SUCCESS:588tests,1positive/5negative comparison controls, injected peak time/value recovered.

**38761402814/116513324545** source-bound readback/comparison of oldcompact_edge_supply fourfine captures is LIVE. No repeated native transient. Inspect maximum_difference_witnesses for v(mr)/v(xtree.t007_b), preserve8.907/8.111mVFAIL. Tighttrap/Gear withoutminbreak previouslyfailed PWLbreakpoints; combining tighter tolerances with verifiedminbreak is a possible next tested profile, not implemented yet. Do not relax1mVgate.

Newreturnstrap sourceaa05c3ea44b87e733b978a76a7a8d6ef0f717c89 native studies:
-38760721744 nominal: compact116510976096 complete/PASS, wire116510975999 LIVE.
-38760726764 failing_corners: fourcompact cases complete, receipts now in SAMEpartialstudy. Coldres finalCMmax2.062747320702VFAIL; coldhbt CMmax2.056969639746V and12HBTmaxVBEup to1.023386990617VFAIL. Groundmetal changes do not affect compact control. Wire hot_hbt116510995390/hot_res116510995555/cold_hbt116510995594/cold_res116510995729 LIVE. Append nextresults to existingstudies; do not duplicate. Full independent/MOS/tempvoltage/fault/numerical qualification remains required.

Mainchip upper_three38731744914/116410943697 live; screen finalnativeGRT-0273 for effective NDRdowngrades. Localworkspace empty. Full serialGen3x4, mainchipdetailroute, finalextractedsetuphold remainOPEN.

## 2026-10-15 — numerical FAIL preserved; new actual ground model ready for native corner trials

UTC 2026-10-15T15:28:50.529382+00:00. ALL CLOUD. Comparison38758906733 COMPLETE, source7cf000..., all4original source archives/native hashes and reviews independently matched. Original electrical gates pass, sample margin/edges/energy convergence pass, but **all-voltage1mVgate FAIL**: compactv(mr)8.906956733mV; wirev(xtree.t007_b)8.111490836mV. Original0.125/0.0625ps captures preserved; no tolerances/window/phase waiver. Receipt appended to timestep_comparisons. Next add exact maximum-error time and native neighbor witnesses to diagnose numerical root before further simulator changes.

New returnstrap composition38758988798 COMPLETE:162models(57HBT24rppd81contacts),11936R7863C,41native conductors/22ports, no intermacro ideal alias/duplicateRC;6composition corruption controls rejected. Source extraction full archive/hash verified by hosted composition. Fresh composition receipt now compact_return_strap.verified_composition; archive publisher hash pinned for next capture full readback. Next native studies nominal and failing_corners on compact_return_strap with original native_res bias. Other all-corner/MOS/fault/timestep requirements retained; this is NOT full serialPHY or mainchip acceptance.

Mainchip upper_three38731744914 remains live, no final timing. Local workspace empty. Full goal OPEN.

## 2026-10-15 — cloud continuation handles after native RC and four fine captures

Checked UTC 2026-10-15T15:23:27.295590+00:00. Progress: authoritative receipts committed7cf000d11deab20e56d1edc87c9799acd1fa69de for all4fine captures and actual newreturnstrap11936R7863C extraction. No local files.

- **38758906733 /116504637764**: hosted `step_comparison`, compact_edge_supply, breakpoint_1as, fine. IN_PROGRESS in native source-bound comparison. All4source archives are pinned; this job verifies full native outputs and original reviews, exact contracts/model/bench equality except timestep, then all original voltage/sample/edge/energy convergence limits. Do not assume PASS from individual captures. Read published `cloud-results-38758906733-1-tree-assembly-4-step-comparison-compact-edge-supply` summary when terminal and pin all failures as well as passes.
- **38758988798**: hosted `composition`, compact_return_strap, source7cf000d11deab20e56d1edc87c9799acd1fa69de. Pending behind comparison by shared workflow concurrency; no job assigned yet. Do not duplicate/cancel. Physical162device proof and extraction receipt already pinned. When complete inspect composition controls, exact native topology, all output hashes, then pin `verified_composition` in variant before dispatching new native loaded wave studies. Start nominal plus original failing corners to expose regressions; retain full original independent/MOS/temperature/fault/numerical qualification requirements.
- **38731744914 /116410943697**: actual mainchip upper_three global routing still IN_PROGRESS, native route step. No terminal timing result. Older controller lacks nativeNDRscreen; manually inspect final native log for GRT-0273 before any acceptance. Original NDR rules cannot be silently downgraded. Detailed routing and extracted final STA still required.

Oldwire0.0625ps final result100.729365286434mV minimum at original768samples,545541rows to34ns,62HBT64MOSallpass. Only0.729365mV over100mVlimit; not proof of robust fullPHY. New returnstrap's electrical behavior is untested. Full serial Gen3x4/fourlanes, actual mainchip integration, final timing and all prior production scope remain OPEN.

## 2026-10-15 — all4fine captures complete; new ground native RC passes

UTC 2026-10-15T15:16:31.546477+00:00. ALL CLOUD. Source-bound receipts updated. Old compact_edge_supply fine run38750168595 now COMPLETE with4cases; final wire0.0625ps has545541rows to34ns, minimum margin100.729365286434mV, all original62HBT64MOS/interface gates pass, zero diagnostics. Summary644244334, archive644242621, publisherSHAdc6797cbff225651a65ad29af7a86e03b556521e2b443af365a27e1a3d6600ad. No numerical convergence claim until hosted pairwise comparison. Next step_comparison: compact_edge_supply/breakpoint_1as/fine.

New compact_return_strap extraction38758132775 source2fb52e511ad39fff4bbdb025bb85c311fe6c2648 passed original graph/ownership/Cconservation and13native corruption controls. Actual11936R/7863C,162devices/22ports/41conductors/322probes. Summary644251994, archive644251725, SHA81cc6546dd641b5eedae697b8ca0fa2f6ea6c475314fa71da7dc625d931d7d7f. Receipt pinned. Physical archive verified by hosted extractor; this extraction archive publisher hash pinned and full readback required by next hosted composition. Next composition compact_return_strap then all original electrical gates/corners including preserved failures. No qualified substrate/RF/EM/fullPHY or mainchip acceptance.

Mainchip upper_three38731744914/116410943697 remains live. Preserve runtime; inspect effectiveNDR GRT-0273 before route acceptance. Full serial PHY/mainchip route/final timing goal OPEN.

## 2026-10-15 — actual return-strap native DRC/LVS passed; next fresh cloud extraction

Checkpoint UTC 2026-10-15T15:11:18.585028+00:00. ALL CLOUD; local workspace verified empty. Native physical **38756076217** source8c6ce7b61ed5e8f96fcf02ce44fea5eb3ed03424 completed: **560categoryDRC zero**, hierarchical and flat **162deviceLVS match**, all5physical fault controls reject. New ground geometry receipt pinned in compact_return_strap. Summary644218630 hash8e1f2d5a525668bfcf1e4a2b3db5a14c137a939c0bcaa813e59529f05bbf8151 independently read back; archive644218282 publisherSHAa8aaf072fc63b78c34f939a8a35e0d2211a66ad1f6ad65f4217b7635f733714e,1364744bytes. Full archive/native output hash readback delegated to next hosted extraction. Source validation38756082156 SUCCESS.

Next dispatch stage=extraction, placement_profile=compact_return_strap on tx-tree-assembly-cloud; then pin native results and run composition/all original corner waves. No electrical improvement or completePHY claim. Existing source child geometry retained. Physical PASS does not close previously failing cold/hot common-mode/VBE/VCE cases.

Other live jobs last checked: wire0.0625ps **38750168595/116474190331** in_progress;3other fine cases passed. Pin fourth result into SAME partial study then hosted step_comparison(profilecompact_edge_supply,solverbreakpoint_1as,step_pairfine). Mainchip upper_three **38731744914/116410943697** still in_progress; inspect GRT-0273 native NDR downgrades before any route acceptance. Do not duplicate live runs. FullPHY/mainchip detailroute/extracted timing remains OPEN.

## 2026-10-15 — first actual wire fine-step capture PASS; real ground-strap layout candidate running native physical proof

Latest checkpoint UTC 2026-10-15T15:02:29.821784+00:00. ALL CLOUD. Local workspace empty. Goal still OPEN; concrete progress this turn.

**38750168595 wire0.125ps** job116474190686 now completed **PASS original component gates** with unchanged physical162-device core/11913R7851C, original62HBT64MOS loaded test, unchanged768bit samples. Source77c438..., solverbreakpoint_1as. Full273541rows to34ns, no diagnostics, outputmin**100.723546529051mV**, all interfaces/devices pass. Summary644183787, archive644182135, SHA9ae6ae2b1489172fb9ed5643be12175cb9b0573220739a0dd9f7b4d95320846d, elapsed1685.273s. Only0.723547mV margin above original100mV: do NOT infer robust all-corner/fullPHY qualification. Receipt appended to partial loaded_studies38750168595 (now3cases). **Wire0.0625ps116474190331 remains IN_PROGRESS**; other two compactcases alreadyPASS. Do not restart. Once fourth capture completes and is pinned, launch hosted step_comparison with placementcompact_edge_supply, solverbreakpoint_1as, step_pairfine. Full native archive/readback and numerical convergence remain pending.

### Ground geometry investigation and real candidate

Read-only source provenance run**38753589265** source61484bc7ac109273d26126dc2e849be45171a3ba completed. Actual GDS/native LVS geometry query **38754724396** sourceb7e8178f11465610218f17c78d0783836dba0b69 completed; source receipt in basevariant.native_ground_geometry_query and newvariant.source_geometry_query. Every original composition export hash checked; all native-net metal unions independently equal source GDS; original E anchors probe nativeAVSS onMetal2. Magic `.ext` explicitly has scale1000/1/0.5: native coordinates use5nm units; resistor values convert1:1toohms. Authoritative format https://opencircuitdesign.com/magic/manpages/ext_manpage.html . No raw-resistance substitution.

Actual query established: lower emitter atabsolute~806.875,320.23um has **clock sp onTopMetal2**; upper emitter327.435um lies just belowclock sn328.24um. Therefore no lower landing may connect toTopMetal2. Existing AVSS is onMetal2/3/4/5 atboth contacts; TopMetal1 corridor x804.875..808.875 is clear of other nets, with substrate stripes atx799.58..801.22 andx818.78+. Existing TopMetal2 AVSS plane occupies y502.24..534.24, allowing a top connection at518.24um. Source origin translation56/76um retained.

New **compact_return_strap** profile implemented **8c6ce7b61ed5e8f96fcf02ce44fea5eb3ed03424** across assembly/extraction/composition/nativecapture/analyzer/workflows and evidence. Same edge-supply placement, four276.015umdata routes, same36umM5supply and frozen child transistor drawing geometry. Additional parent-only **4umTopMetal1 vertical ground strap** at pretranslationx750.875 fromy244.230 to442.24, lower nativevia_stack Metal2→TopMetal1 at244.230/251.435 (8×1lower vias;2×2TopVia1), upper2×2TopVia2 atAVSS plane. No lowerTopMetal2 connection. Three native via stacks, zero newactive devices/ports. Changes are UNVERIFIED until native gates; new coupling may hurt clock/data margin and must be re-extracted/tested, including every existing corner failure.

**Native physical38756076217**, job116494755155, source8c6ce7..., is IN_PROGRESS (actual generation/DRC/LVS). DO NOT assume pass. Source validation **38756082156** queued as last checked. Inspect physical result; if DRC/LVS/fault controls pass, pin physical receipt in newvariant.verified_hierarchical_assembly using same schema asbase, then run extraction/composition and required original+corner native captures for this new profile. If failed, preserve original output and correct geometry; never bypass gates. Existing methods keep full560categoryDRC, hierarchical+flat162deviceLVS and actual fault controls. No mainchip integration or fullPHY claim.

Mainchip upper_three38731744914/116410943697 still live; first upper_metals timed out with31NDRdowngrades, evidence below. New effective-NDR gate is sourcevalidated; older livejob requires manual final-log screen. Finaldetailroute/extractedSTA, real32:1/fourlane, PLL/CDR/RX/PCS/LTSSM/pads/ESD and all production qualification remain open.

## 2026-10-15 — BOTH compact fine-step transistor captures pass; ground bottlenecks identified; two wire captures LIVE

Latest checkpoint UTC 2026-10-15T14:37:18.353542+00:00. ALL CLOUD. Goal remains OPEN. No local files or native work.

Native run**38750168595** source77c438072812a2020a02ef8fd257eee408cc9c4f, `breakpoint_1as`, now has **both compact0.125ps and0.0625ps COMPLETE/PASS** original engineering gates. New0.0625ps case: 545541 full rows to34ns, min original output margin232.898411741997mV, zero diagnostics, all original62HBT64MOS/interfaces pass, actual minbreak1e-18 readback. Summary644140203, archive644138595. Both source summaries and publisher hashes are pinned in the SAME partially completed variant.loaded_studies record; full hosted capture/readback and numerical comparison still pending. **Two wire jobs116474190686 (0.125ps) and116474190331 (0.0625ps) remain live**; do not restart. Once both terminal, pin them (including any failures). Only complete four-case studies may enter hosted stage`step_comparison`, placementcompact_edge_supply, solverbreakpoint_1as, step_pairfine. Profile support already added2d259223..., validation38751396985 **588passed**. Do not assume paired voltage convergence from standalone component screens.

**Ground path diagnosis38751904886 COMPLETED**, sourcee5d83038bf128d6fc88a891cb9f2bf58979a963f; summary644132920, archive644132170. Exact original wirehot_low_res_bcs review and full original source-capture hash readback pass; all original electrical FAILURES remain. Receipt and detailed paths now variant.ground_path_diagnosis. No ground geometry repair yet.
- Actual failing final emitter **T006_E** shortest resistor path upper bound12.310757376ohm,40segments. Largest raw resistors: **R9666=3.02941ohm** (`P_avss.n294`–`P_avss.n291`), shared **R9622=1.99561ohm** (`P_avss.n175`–`P_avss.n212`), **R9619=1.1ohm** (`P_avss.n295`–`P_avss.n267`).
- **T007_E** upper bound15.017284076ohm,37segments. **R9676=3.02897ohm** (`P_avss.n233`–`P_avss.n234`), sameR9622, **R9563=1.83131ohm** (`P_avss.n259`–`P_avss.n296`), **R9564=1.27451ohm**, **R9620=1.13954ohm**, **R9606=1.02362ohm**. Shared upstream~.55ohm segmentsR8772/R9091/R9430/R9444 also retained.
These are exact native lumped R names and path bounds, NOT effective resistance or solved EM/current. NEXT physical repair work: map these raw resistor nodes to actual metal/via coordinates/layers before widening or adding real parallel ground straps/vias. The verified extraction/composition archives include `wire96/rc03/` native extraction data and generator scripts; investigate their native node geometry on hosted runner (no large local archive downloads). Existing analyzer restores only selected composition geometry files, not all rc03 node metadata. `run_cloud_tx_tree_extraction.py` produces rc03 via frozenrun-rc01.py; `run_cloud_tx_tree_composition.py` adaptscompose49.py. Native graph binding/ownership/capacitance conservation and DRC/LVS must be rerun for real layout repair. Keep untouched child device shapes unless a separately verified child revision is needed. Cold HBT VBE and common-mode failures must still be addressed; improved ground may affect bias and cannot be accepted by a single hot corner.

Mainchip upper_metals38703550233 is terminal6h timeout plus31NDRdowngrades, preserved below; upper_three38731744914 is still running. Do not claim global/detailed route or final timing. Native NDR gate fixd7c207... verified in cloud. Full32:1/fourlane, PLL/CDR/RX/PCS/LTSSM/padESD/qualifiedRC/fullchip timing and physical verification remain required. Previous turn classified PROGRESS, no blocked condition.

## 2026-10-15 — FIRST FULL TRANSISTOR FINE-STEP CAPTURE PASSES; remaining three and ground diagnosis LIVE

Checkpoint UTC 2026-10-15T14:32:51.456585+00:00. Supersedes pending first-case wording below. ALL CLOUD; local workspace empty. Full goal still OPEN.

**38750168595 compact0.125ps** (job116474189843) completed successfully with the same original transistor circuit and original electrical gates. Source77c438072812a2020a02ef8fd257eee408cc9c4f, profilebreakpoint_1as. **273541 strictly increasing full native rows through34ns**, no diagnostics, all62HBT/64MOS/interface gates pass; original768bit samples min232.895896992mV, zero wrong-sign/below100mV. Actual native option/circuit-minbreak readback passes. Summary asset644118170, archive644117483, publisher archiveSHAd28e4837d6531f486b6b962316226e7fd3afb6111ae0583ac25f52ebd66dfb29. Full large archive hosted readback/numerical convergence still pending; do not claim full PHY or wire success. Receipt added as the FIRST case of partial loaded_studies run38750168595. When other cases complete, UPSERT them into that same study, don't duplicate it.

Other three jobs remain IN_PROGRESS in native capture: compact0.0625ps116474190719, wire0.125ps116474190686, wire0.0625ps116474190331. Do not restart. **2d25922344de8fa7215b9cbd2b9dc81ddf8dd605** enables `breakpoint_1as` in hosted step_comparison and extends the actual physics/stimulus invariance test to it. Hosted validation **38751396985**, job116478429496: **588 passed**, plus NDR1positive/3negative, CUGR1positive/10negative and clock-layer3positive/24negative controls. All source work pushed.

**Ground/bias path diagnosis38751904886**, job116480188030, source**e5d83038bf128d6fc88a891cb9f2bf58979a963f**, is LIVE on hosted runner. Uses original actual wirehot_low_res_bcs/native_res failed corner with exact archive/review. Analyzer now records each source-to-contact resistor path and the12 largest segments with exact exported native R names/values, validating parallel-conductance combination. This should locate the real geometry causing~65–67mV emitter ground rise; NOT an effectiveR/IR/EM claim. Inspect AVSS E terminals device6/7 (T006_E/T007_E) and map dominant native resistors back to geometry before a real DRC/LVS/re-extracted repair. No physical ground change yet.

Mainchip upper_metals38703550233 is terminal time-limit failure with31 native NDR downgrades; permanent evidence below. Upper_three38731744914 remains live, older controller, so manually enforce native NDR rejection on its final log. New gate prevents accepting native NDR fallback. Full detailed route/final extracted timing and serialPHY/PLL/CDR/RX/pads all remain open. Continue all work in cloud.

## 2026-10-15 — native duplicate-time cause isolated; full transistor fix trial LIVE; first clock-layer route timed out

Latest checkpoint UTC 2026-10-15T14:24:20.220555+00:00. Latest user instruction ALL CLOUD supersedes stale goal wording asking local. Local workspace remains empty; no local CAD/tests/checkout/artifact files. All native work runs on hosted Actions. Full serial Gen3x4 PHY, mainchip PCIe/Ethernet detailed routing and final setup/hold still OPEN. This turn made concrete progress, not blocked or achieved.

### PHY numerical failure: new authoritative evidence

Original failed captures38736928007 compact0.125/0.0625ps were fully downloaded and hash-verified ON HOSTED RUNNER, including every native output. Actual last points are **30.37499999999999ns** and **15.374999999999997ns**, each exactly one binary64 ULP before a PWL source knot. Unchanged original source PWL blocks were extracted byte-for-byte into an explicitly diagnostic linear RC reduction. This reduced circuit reached34ns but emitted **14** / **129** nonincreasing (zero-delta) time steps; the first duplicate occurs at EXACTLY the same time as the transistor failure. Strict full-wave reader correctly rejects these records. This is no physical-pass waiver.

Adding only **minbreak=1e-18** (one attosecond) to this linear control retains exact PWL source bytes, .tran settings and original reltol1e-4/abstol1e-12. Both reductions then reach34ns with **zero duplicated/reversed times** and pass the unchanged full binary reader. This supports a native breakpoint-resolution cause; it does NOT yet prove the full transistor circuit repaired or electrically accepted.

- First diagnostic **38747893120**, source5dfd86372851b03b8fcb119d40c74e001d463ee6, retained as FAILURE because the strict reader rejected duplicates and originally aborted diagnosis early. All18 transport tests passed. This was then fixed to RECORD that rejection and continue the diagnostic, never weaken the reader.
- Complete diagnostic **38748473714**, job116468271983, source22584f18dc79762e04c2de04e0b48c0629df0828, SUCCESS execution with both original failures and both numerical controls retained. Both small diagnostic archives have separately verified full archive SHA, embedded summary and every exported output. Receipts and full reports in variant.breakpoint_diagnoses. Original large transistor archives separately fully verified on hosted runner; reduced raw arrays are summarized with hashes, not republished as physical evidence.
- Native ngspice47 source confirms traninit.c setsdelmin=1e-11*maxStep; XSPICE dctran.c usesminBreak=10*delmin by default, and vsrcacct.c computes nearby PWL breakpoints in binary64. Exact source references: https://github.com/imr/ngspice/blob/ngspice-47/src/spicelib/analysis/traninit.c ; https://github.com/imr/ngspice/blob/ngspice-47/src/spicelib/analysis/dctran.c ; https://github.com/imr/ngspice/blob/ngspice-47/src/spicelib/devices/vsrc/vsrcacct.c ; https://github.com/imr/ngspice/blob/ngspice-47/src/spicelib/analysis/cktsopt.c . No simulator binary patched; pinned Debian47 executable unchanged.

**Full native trial38750168595** source**77c438072812a2020a02ef8fd257eee408cc9c4f**, solver_profile`breakpoint_1as`, original compact_edge_supply core/native_res bias, four cases compact/wire×0.125/0.0625ps, currently IN_PROGRESS in full transistor capture. Jobs116474189843/116474190331/116474190686/116474190719. All four reached long capture after passing hosted tests and actual native solver preflight. New profile keeps original tolerance values; `.options minbreak=1e-18` only. After analysis native `option` and circuit `$minbreak` variable readback are required; missing/changed/duplicate values reject. Circuit-variable readback is distinct from internal CKT state, whose breakpoint behavior was separately demonstrated above. No new stimulus phase, bit oracle, capacitance, model, window or safety gate. DO NOT duplicate these live captures. Inspect completed summaries, archive receipts and original engineering gates; only COMPLETE captures may enter numerical comparison. If they pass, add source-bound fine0.125/0.0625 comparison for this profile and retain all-vector1mV/edge/energy bounds and original device screens. Actual resistor/HBT corner failures and rejected TCfeed remain open independently.

Source validation38750174821 succeeded for77c438; native NDR gate validation38750531880 succeeded ford7c207f2e66ed1d5fb801daf872f5f0a6028f80e. Read terminal logs for exact test count. Prior22584validation38748478833 succeeded. No local tests.

### Mainchip routing: terminal first trial, second still live

**38703550233** upper_metals, source d3a3cec31e13cbf877158b5a6861689f13ae38a3, job116317277037, is now **CANCELLED BY HOSTED SIX-HOUR LIMIT**, not success. Check annotation explicitly says maximum6h exceeded. Native global router was still doing extra iteration53/100 in its latest loop when killed. Crucially, there were **31 unique GRT-0273 warnings disabling NDR demand**, beginning before further loop resets. Thus retained CTS dbNet NDR declarations were insufficient to prove effective routing-demand constraints. Do not treat this as acceptable routing even if a later relaxed result looks clean.

Permanent native output archive **644074391**,138998423bytes, SHA**4b1422c57b708633fc7d2764fc575130d4fcdc87ca2d8e00a09aa99d6f6153c8**, at https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38703550233-1-route-local_optimize_buffers/newer-postcts-placement-local_optimize_buffers-38703550233-1.tar.gz . Publisher checksum pinned; full archive readback not yet performed. Summary **644075104**,335792bytes,SHA**ef39b28c72682564d18492c4a566dc7b435bb95bb51ef074e1d6f957421ba30e**. Its last saved status says global route pending because the native process was killed; authoritative terminal job/annotation supersedes that stale report status. Global-route.log is preserved in the archive. No completed guide or post-route timing claimed.

Frozen OpenROAD source explains prolonged looping: `applySoftNDR` sets selected nets' edge demand to1 then resets the iteration counter. See https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/grt/src/fastroute/src/FastRoute.cpp#L1714 . **31 disabled nets:** clk_i, clknet_0_clk_bus, clknet_0_clk_i, clknet_0_clk_i_regs, clknet_0_clk_npu, clknet_0_eth_rx_clk_i, clknet_0_eth_rx_clk_i_regs, clknet_0_eth_tx_clk_i, clknet_0_eth_tx_clk_i_regs, clknet_0_pcie_clk_i, clknet_0_u_ibex.clk, clknet_1_0_0_clk_i_regs, clknet_1_1_0_clk_i_regs, clknet_2_0_0_clk_npu, clknet_2_0_0_pcie_clk_i, clknet_2_0_0_u_ibex.clk, clknet_2_1_0_clk_npu, clknet_2_1_0_pcie_clk_i, clknet_2_1_0_u_ibex.clk, clknet_2_2_0_clk_npu, clknet_2_2_0_pcie_clk_i, clknet_2_2_0_u_ibex.clk, clknet_2_3_0_clk_npu, clknet_2_3_0_pcie_clk_i, clknet_2_3_0_u_ibex.clk, delaynet_0_eth_rx_clk_i, delaynet_0_eth_tx_clk_i, delaynet_50_clk_i, eth_rx_clk_i, eth_tx_clk_i, pcie_clk_i.

Controller fix **d7c207f2e66ed1d5fb801daf872f5f0a6028f80e** now records native NDR downgrades on completion/failure and rejects a supposedly complete route if any occur. It does not suppress warnings, change geometry/capacity, or weaken clock rules. Hosted self-test verifies one positive/three negative NDR cases plus existing CUGR and clock-layer controls. This gate is not itself a physical repair. Next physical routing decision must inspect actual congested clock nets and buffer coordinates rather than run unchanged six-hour loops or waive NDR.

**38731744914 upper_three**, job116410943697, source486396eb95aac2c4dc9ab055ebfb996a884132f2, remains live. Do not cancel/restart on observation timeout. It uses the older controller, so explicitly inspect final native log for GRT-0273 before acceptance. Same placement hash660692b3e59756186bb017a62823999db593fa9d77b6e4181be9625fa7bfb707. Detailed routing, real extracted RC/STA, DRC/LVS and full PHY integration remain required. All earlier corner, PLL acquisition, pad/ESD and production gaps remain active below.

## 2026-10-15 — ALL CLOUD; tight native methods fail; exact corner diagnosis preserved

Latest checkpoint UTC: 2026-10-15T13:52:38.339509+00:00. Supersedes older LIVE labels below. User instruction: ALL CLOUD and clean local. Workspace `/home/hasanmelih/Documents/ChatGPT/nnsoc` verified EMPTY. No local checkout/CAD/tests/artifact files; API orchestration and small source/result reads are RAM-only. Never use `gh run view --log-failed`, which creates local cache files. Existing cloud-only eight-hour monitor remains in effect. Full serial Gen3 x4 PHY, routed mainchip and final setup/hold are still OPEN; this is progress, not achieved or blocked.

### Current handles and preserved evidence

- Mainchip **38703550233** (job116317277037, upper_metals) and **38731744914** (job116410943697, upper_three) both verified IN_PROGRESS at this checkpoint. Do not duplicate or cancel healthy work. They end at globalroute/estimated timing, NOT detailroute/signoff. Their pre-route snapshots643179081/643745801 have identical source inputs, placement repair and all six STA reports. Exact moved ODB SHA660692b3e59756186bb017a62823999db593fa9d77b6e4181be9625fa7bfb707;113791instances,1505selected buffers,960moved,zero data flops moved. Preserve SDC/NDR/capacity/zero-overflow gates. First workflow has 360min hosted limit from08:08UTC; inspect terminal artifacts if it expires.
- Tight numerical **38740901931** (trap) and **38740907328** (gear2), sourcecc13ec34e524104f3ac803b1023923ba916fc973, now BOTH COMPLETED FAILURE: all eight compact/wire captures abort. Actual native solver option readback passed in all eight. 0.125ps fails at30.375ns;0.0625ps fails at15.375ns, same as original default run38736928007. These are incomplete captures, never valid accepted studies or inputs for paired convergence comparison. All eight summary hashes, permanent archive publisher hashes and original native-output hashes are now pinned under variant.tight_numerical_results. Large archive readback has NOT been separately performed; do it on a hosted runner if needed. Keep failed records intact.
- The repeated native failure times are a diagnostic clue, NOT proven cause. Need source/version-bound ngspice breakpoint/delmin investigation while preserving original input stimulus, phases, bits, tolerances and windows. No patched simulator, shifted PWL edges or waived gates adopted.
- Solver option display contains two harmless labels with `error`/`stepping` words. Controller fix **a56bbe8de80ecfabfc5a58208b1c14cf02d40495** exempts ONLY those two exact labels INSIDE a fully verified unique option block; every actual warning/error remains. Raw failed records unchanged. Source validation **38745949504**, job116459519253, completed SUCCESS against exact a56bbe8: **584 passed**; both diagnostic-classifier tests retain real failures and reject malformed option blocks. Previous validation **38743987861** verified **582 passed** against402ed48fb4d7664ce6981d51b46734d742c931f0. No local tests.

### Corner repair evidence and next physical work

- Fixed native TC feed candidate (100um/1um Rsil plus16.5um/2um Rppd) **REJECTED**, all12 cases and receipts in bias_candidates.native_res_tc; runs38736943635/38736959438. Actual wire cold resistor corner now passes CMmax2.048726164V, but ordinary hot output falls to95.662679512mV below unchanged100mV; hot resistor corner still fails CMmin1.791249201V and final HBT VCE minima0.394780701/0.392285755V. Compact cold HBT VBE still1.023395V. Feed physical layout/RC not integrated; don't promote it.
- Prestage current/rail-binding review omission for native_res_tc fixed1833464213ce9b417c85cf1f1f61b99caef82c09. Source-bound native corner diagnoses **38742001287** (TC) and **38742006449** (original), source1a04a9b078ae277b39779940905eb4aaeaf783cd, both completed; receipts in variant.corner_diagnoses. Original waveform reviews exactly reproduced, failed HBT extrema/neighbor rows preserved; selected source archive readback only, explicitly scoped.
- Original hot resistor corner prestage median currents0.599020/0.596741mA; TC0.572036/0.569894mA. Final bias nearly unchanged1.03688mA. Original offending final emitters rise65.557/67.055mV and collectors459.523/458.526mV; TC barely improves them. Actual ground terminal path upper bounds11.691/12.311/15.017ohm are NOT effective resistance or EM proof. Investigate real ground/return geometry and bias matching, require native DRC/LVS/re-extraction and all corner/current/device gates. Do not ideal-short RC or claim repair from path bounds. No new ground/clock geometry implemented yet.
- Preflight parser failures38740055336/38740061733 retained permanently at releasecloud-tight-solver-preflight-rejection-20261015 asset643949898, SHA bfa06a3f3e2dcf1ebdfa28232cac32930e7bd7f3ce6e7ad5efe94b460945e43f, all eight job logs read back. They failed before transistor capture, correctedcc13ec34. All receipts/corner outcomes committed288dcd5820cdf0b2271d68838e50fa0a80cbe8f7.

Do not narrow the goal to4:1: full32:1/fourlane physical serializer, actual PLL/CDR/RX/PCS/LTSSM, pad/ESD, qualified RC, detailed mainchip routing and extracted final setup/hold remain required. Original PLL800–900ns acquisition126.2157ppm failure remains; later-window success cannot replace it. Continue in cloud with exact sources and native evidence.

## 2026-10-15 — full expanded capture readback now COMPLETE

Hosted diagnosis **38737128747** completed: summary **643860135** proves exact archives, embedded summaries and every native output hash for **all50** original+expanded edge-supply cases. The original hot review was reproduced unchanged. All four engineering corner failures and six intended faulty-circuit failures remain failures; this is evidence integrity, not all-corner acceptance. Receipts updated in tree4evidence.expanded_hosted_readback and all50case readback statuses. Fine-step38736928007 andTC candidate38736943635/38736959438 remain verified LIVE. Current source/test/candidate/routing continuation below remains applicable. ALL CLOUD; local workspace verified empty.

## 2026-10-15 — native convergence failure retained; finer captures and fixed TC feed now running in cloud

Latest turn is PROGRESS: actual paired readback completed, numerical failure retained, fixed physical-device feed candidate implemented,572 hosted tests passed, native jobs live. User override remains ALL CLOUD. Empty local workspace and cleanup receipt643812374 remain verified; no local test/CAD/artifact files. Do not mark full serial Gen3x4/mainchip/finalSTA complete or blocked.

### Current handles (verified LIVE, do not duplicate)

All following analog runs use implementation **fda41b234ff6388d913060411f031345ad610bdb**, profile`compact_edge_supply`:
- **38736928007** `hot_low_fine_steps`, pre_bias`native_res`:4jobs running native compact/wire at **0.125ps and0.0625ps**. Original0..34ns,256bits, all original electrical gates. Actual wire captures can take much longer than baseline0.5ps. Do not restart on elapsed observation time.
- **38736943635** `failing_corners`, pre_bias`native_res_tc`:4compact completed,4wire actively running. Compact hot_res_bcs andhot_hbt_bcs PASS; compact cold_res_wcs still CMmax**2.054162684V** (improved from2.062747321V but >2.05), compact cold_hbt_wcs CM nowPASS max2.045853876V but twelve final HBT VBE still fail up to**1.023395261V**. Keep all failures; do not waive compact control or infer actual wire result.
- **38736959438** `temperature_voltage`, pre_bias`native_res_tc`:compact hot/cold PASS;2actualwire jobs running.
- **38737128747**, job116429171818, `wave_diagnosis`: RUNNING full hosted archive/embedded-summary/all-native-output readback for ALL50 baseline edge-supply cases (6original+44expanded). Original gate reviews/failures preserved. This runs sourcefda41b... before pending candidate receipts and does NOT validate a TC feed layout.
- Mainchip **38703550233** upper_metals and **38731744914** upper_three both still IN_PROGRESS in native globalrouting. Their pre-route snapshots643179081/643745801 were read and independently compared: identical source_inputs, placement_repair, and six timing reports; exact movedODB SHA**660692b3e59756186bb017a62823999db593fa9d77b6e4181be9625fa7bfb707**,113791instances,960of1505selectedbuffers moved. Only clock layer profile differs. Neither implies completed detailroute or extracted STA.

### Actual timestep comparison outcome

Corrected **38735749704** completed successfully as execution, source57fcd6648731ba8605eee1705edb5f20abe9c844, summary **643824320**. It verified both actual compact/wire archives and model hashes and exactly reproduced all original native reviews. Same circuit inputs, generated benches/contracts differ ONLY integration timestep. Synthetic1positive5negative controls PASS. **Numerical screen FAILS**: some full-capture voltage deltas exceed fixed1mV. Compact max5.040244mV atmr; wire4.708498mV atxtree.t007_b (xd0007base), mr4.497195mV. Original768sample-margin deltas compact39.877751uV/wire54.749257uV PASS100uV bound, original crossing counts64rising64falling equal, wiremaxedge3.047499fsPASS100fs, sourceenergyboundsPASS1%. Do not change bounds or count standalone original gate passes as numerical convergence. Exact report/receipt in variant.timestep_comparisons, commit **7d4d40848ea9459c2155c851d96b20d86027a34b**. This motivates new0.125/0.0625 captures above.

Source now supports `tx-tree-assembly-cloud` stage`step_comparison`, input **step_pair=fine** for0.125/0.0625 (defaultoriginal remains0.5/0.25). After BOTH modes publish BOTH new conditions, pin them to baseline variant.loaded_studies with pre_bias`native_res`, then dispatch fine comparison once. Same-condition candidate bias studies MUST NOT be inserted into baseline loaded_studies; keep separate. Comparison removes only restored working wave.raw after independently verifying original archives and recording original native output hashes; original source releases retain all raw data. This avoids republishing several gigabytes of duplicate raw captures in one oversized Release asset. No raw source is deleted or clipped. Fine comparison NOT dispatched yet.

### Fixed native TC prestage feed candidate

Added native_res_tc to existing`tx_pre_bias_res_v1.inc`, mux controller and assembled-wave workflow, preserving original native_res subckt. Two series real native resistors fromAVDD toexistingreference: **Rsil100um/1um +Rppd16.5um/2um**, fixed at every PVT (sheet estimate2845ohm versus2860baseline). Based on published IHP3100ppm/K Rsil versus170ppm/K Rppd; exact frozen native models determine actual result. No output feedback, idealclamp, per-corner retune, changedcoregeometry/RC, alteredclockphase or sourcebit/gate changes. Increasing positive TC aims to reduce hot referencecurrent and increase cold current, raising hot and lowering cold outputcommonmode. Added feed layout/contact-current/RC not yet integrated/qualified; native62HBT64MOS original screens remain. Source bound summary.pre_bias_tc_scope explicitly states limitations.

New hosted regression **572passed**, verified completed job116428545209. Tests preserve identical originalbits/clocks/observations and require actualdisable_pre_b_bias fault wiring; original566 tests also retained. TC candidate receipts are **separate** under variant.bias_candidates.native_res_tc; partial6compact receipts committed **ba0527dd4dca6115ec3ed616e29c4ef505128355**. Next inspect actualwire PVT results before refining physical feed; record rejected candidates, then perform actual feed layout/native DRC/LVS/RC and larger32:1/four-lane integration when electrically sound. Do not infer fullPHY from this4:1screen.

Source documentation for resistor hypothesis: https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/02_process_control_params.html#rsil-specs and #rppd-specs, read in this turn. Original PLL acquisition failure and all production constraints below remain open. Current continuation has useful native computation underway; no genuine blocker.

Checkpoint UTC: 2026-10-15T12:52:51.196986+00:00

## 2026-10-15 — cloud-only cleanup verified; expanded corner failures retained; paired timestep comparison LIVE

This supersedes the older LIVE handles below. Latest user instruction is **all work in cloud, clean local**. Workspace `/home/hasanmelih/Documents/ChatGPT/nnsoc` is empty. No local CAD processes, clones, test execution or downloaded design archives. Use GitHub API for source edits and small summaries in RAM; full captures are verified on hosted runners. Never use `gh run view --log-failed` because it writes local cache. Original user documents and unrelated caches are preserved. The active 8-hour heartbeat is already cloud-only. Full serial Gen3 x4, mainchip detailed routing and final setup/hold remain OPEN.

### Local residue cleanup actually completed

Found 46 old `/tmp/tx-mux4-*.summary.json` files (2,594,488 bytes). Archived them in RAM, uploaded, read back the archive and verified every original member SHA256, then removed exactly those 46 files. Release `cloud-local-residue-retirement-20261015`: archive asset **643812226**, 460072 bytes, SHA256 **d951d3b69a4055397a0a9796c5059ee8f0bf528b000963177dee12fce692a056**; removal receipt **643812374**. Prior 114 NSSOC log caches already retired with independently verified receipt **642730081**. Remaining inspected GH log archives did not identify NSSOC and were left untouched. No blanket deletion of user data or other projects. GitHub binary upload via stdin with gh failed Content-Length before deletion; urllib with an explicit length succeeded, and all verification preceded unlink.

### Completed actual edge-supply waveform evidence

Source **370ff637ed78f18f04562f875b8d0ae354d11869**; `compact_edge_supply` actual 162-device native core, 11913R/7851C. Nominal **38727922711** and hot/cold **38727906690** all six cases PASS original component gates. Actual wire hot minimum **100.6804731531521mV** against unchanged100mV (only0.680473mV headroom), zero wrong-sign/below-threshold samples, all final interfaces/62HBT64MOS pass. Nominal227.645762mV, cold264.340451mV. Full six archive/embedded-summary/every-native-output readback and exact review reproduction PASS hosted diagnosis **38729628248**, summary **643697070**, archive643696587. All receipts under `placement_variants.compact_edge_supply` in tree4 evidence. Main doc160 updated. This is a4:1component, NOT full32:1/four-lane physicalPHY.

Expanded runs all executed source **649b2c19d0aa7a6564b0a1587214923dbc70dbb1**, now complete. Receipts for all44 expanded cases committed **a6beddd2ef8c3e3a5cb23f12d746e2105d9554d6**. Summary+publisher archive hashes pinned; expanded full archive readbacks still pending unless later separately proven.
- **38729645022 physical_faults**: six actual faulty cases all fail intended waveform gates; retained as negative controls.
- **38729653636 mos_corners**: all12 compact/wire cases PASS component screens.
- **38729648640 independent_corners**:24cases, **four engineering failures**, despite Actions success. Compact cold_high_res_wcs and cold_high_hbt_wcs fail final common mode; latter also final HBT whole-transient VBE up to1.023387V. Actual **wire cold_high_res_wcs** final CMmax **2.0537657137706975V** >2.05. Actual **wire hot_low_res_bcs** final CMmin **1.7854723607002319V** <1.8 plus xtree.xd0006 VCEmin0.393965736V and xd0007 **0.391471681V** <0.4. Both wire output margins pass (257.894022mV and127.179731mV respectively), which does not waive device/interface failures. Other20cases pass. Do not mark all-corner accepted; next electrical repair must address actual bias/headroom across both extremes with real physical devices/RC, retain original gates and source bits.
- **38729658172 hot_low_quarter_step**: compact and wire PASS. This is **0.25ps versus baseline0.5ps**, not0.125ps. Wire original768sample minimum100.714322744mV, final interface175.190932mV, no failed HBT/MOS. Standalone passing gates is not a completed convergence comparison.

### New source-bound timestep comparison (do not duplicate)

Controller `scripts/analyze_cloud_assembled_wave.py --compare-timestep`, workflow `tx-tree-assembly-cloud.yml`, stage`step_comparison`, profile`compact_edge_supply`. Added in **648d1eae6b5c0b4b20f6e26336ba8d5271b00518**. Hosted full raw archive and model hashes, native reviews reproduced exactly, all native vectors, original768sample margins, same-ordinal zero crossings and full source energies compared without fitted phase/latency. Additional numerical transport bounds1mV/allvoltage,.1mV/samplemargin,.1ps/edge,1%/energy; these are NOT PCIe acceptance and never replace original100mV/150mV/device gates. Synthetic1positive+5negative controls passed in first run.

First **38735292322** FAILED after proving original compact contracts/benches equal except actual timestep: generic input hash comparison incorrectly included those same generated bench/contract files whose hashes necessarily change with timestep. Summary **643812831**, archive643812299 retained. Source inputs were inspected: ONLY original bench/contract hashes differ in both compact and wire pairs. Fix **57fcd6648731ba8605eee1705edb5f20abe9c844** verifies their original input hash against archived output hash, keeps explicit normalized-content equality, and compares every remaining circuit/model input unchanged. Corrected hosted run **38735749704** is LIVE; inspect terminal summary before claiming convergence. Do not rerun native waves unnecessarily. After comparison, full expanded capture readback may use wave_diagnosis, which verifies all pinned cases; that stage replays baselinehot review only and does not turn corner failures into passes.

### Actual mainchip routing remains live

- **38703550233**, job116317277037, source d3a3cec31e13cbf877158b5a6861689f13ae38a3, clock`upper_metals` TopMetal1–TopMetal2. Started08:08UTC. Pre-route snapshot643179081. Still running native replay/globalroute as checked12:33UTC.
- **38731744914**, job116410943697, source **486396eb95aac2c4dc9ab055ebfb996a884132f2**, clock`upper_three` Metal5–TopMetal2. Started12:03UTC. New pre-route snapshot **643745801** published; native running as checked12:33UTC. New clock-profile controller preflight passed (3positive/24negative controls implemented). This is a controlled layer-choice comparison, not a duplicated identical job.
Both preserve local_optimize_buffers/hold2/seed13/FastRoute, original geometry, signalMetal2–TopMetal2, NDR/SDC/capacity/zerooverflow. Do not cancel healthy jobs. These controllers end at globalrouting and estimated timing, NOT completed detailedroute/signoff STA. Running logs API404 is not job failure; CUA disabled in this session. Need inspect final globalroute guides/overflow/STA, then actual detailroute/extraction/finalsetuphold on the exact accepted database.

PLL acquisition remains OPEN: original800–900ns window126.2157ppmFAIL; later900–1000ns84.0102ppm cannot substitute. Source-bound cycle observations added in **b231eecf2dc6742d70a25e47ad605f72add1d156**, no new PLL repair candidate/run. Physical source details and outstanding full PHY/ESD/RF/production constraints remain below. This is progress, not completed goal or blocked goal.

Checkpoint UTC: 2026-10-15T12:36:32.776614+00:00

## 2026-10-15 — measured supply coupling regression repaired physically; edge-supply native waves LIVE; ALL CLOUD

This is the latest checkpoint. Current goal turn is PROGRESS: source-bound failure diagnosis, full hosted capture readback, a new physical supply layout, native DRC/LVS, fresh RC and162-device composition all completed. Full serial Gen3x4/mainchip/finalSTA remain OPEN. Latest user override is ALL CLOUD; ignore stale goal phrase saying local. Local workspace remains empty. No local CAD/tests/clones/artifacts. API source edits and small evidence reads in RAM only; heavy waveform archive readback now executes on hosted runner. Never use `gh run view --log-failed` (creates local caches).

### Live handles, source370ff637ed78f18f04562f875b8d0ae354d11869 — do not duplicate

Profile **compact_edge_supply**:
- **38727906690** temperature_voltage. Native wirehot job**116398210861**, wirecold**116398210495**, compacthot116398210890 and compactcold116398210926. Wirehot/cold verified IN_PROGRESS in native full-wave step; no electrical result yet.
- **38727922711** nominal. Native wirejob**116398262301**, compact116398262532. Wire verified IN_PROGRESS in native full-wave step.
- Mainchip **38703550233**, job**116317277037**, source d3a3cec31e13cbf877158b5a6861689f13ae38a3: still verified IN_PROGRESS in exact newer postCTS/replay/routing. No duplicate, no final route/STA claim. Existing upper_metals clock restriction only; original132overflowplacement/SDC/NDR/capacity gates retained.

### Preceding closer geometry FAILED actual hot test — retained

**compact_m5_supply** cases in tree4evidence. Actual runs38722317700 and38722321392 are terminal. All six source summaries pinned; all six full archives, embedded summaries and every native output hash independently read back ON HOSTED RUNNER in diagnosis38725816163.
- Wirehot summary**643563687**, archive643563120: **TEN** original0.3UI samples below100mV, min**94.47861369886845mV**. No wrong-sign samples. Do not adopt candidate or shift gates.
- Wirecold summary**643548266** passes min264.085455mV; nominal643562343 passes min228.082931mV. All compact controls pass. These passes do not override hot failure.
- Source is29948e0caea687b748f329dccb6ad48c115326b6. Loaded receipts committed5212b2e5c1f94506103a02e789ee5e287b83475d; hosted readback proof recorded inccfe951baf0b754753166a90dfca425654d4a56c. A slow local RAM-only archive transfer was intentionally stopped before any receipt write; no native/cloud run was cancelled and no incomplete transfer claimed verified.

### Actual diagnostic evidence explains next physical choice

`scripts/analyze_cloud_assembled_wave.py` now groups each exported mutual/ground C by independently recovered native conductor and reports actual public-supply-to-device resistor path upper bounds. 41conductors,300metalterminal witnesses, unique native identities, publicrail binding and an actual corrupted-native-label control are checked. Path bounds are NOT effectiveR/solvedvoltage/EM/RF. Original waveform review must exactly match every original signal/interface/HBT/MOS gate; no changed oracle. `verify_study_captures()` verifies all selected raw captures on hosted runner; no local large archives needed.
- **compact_vertical diagnosis38724619146**, source1f2a8020a5598024b036ddb397927d12a002813a, summary**643590898**, archive643590540. Original two hot failures preserved. Total intermacro C ap/an/bp/bn =156.862583/169.534029/165.494220/171.525752fF; AVDD coupling =10.534100/9.904650/6.590710/7.526480fF.
- **compact_m5_supply diagnosis38725816163**, source6f8e917ace91953522bc366834f265383d1a467f, summary**643614542**, archive643614201. Original ten failures preserved. Total C =173.540885/183.477234/197.301561/204.636567fF; AVDD coupling =41.923000/39.989102/58.027199/58.829398fF. R path bounds improved only~0.22ohm; bias currents nearly unchanged. Wide M5 below the data corridor increased coupling despite shorter paths. This is evidence for moving the supply stripe, not a claim that the next circuit passes.
- Full receipts/failed samples/C groups/supply paths/readbacks stored under each variant.wave_diagnosis in **docs/evidence/pcie-tree4-assembly-input-20261015.json**. Source validation38724633921 and latest**38726437411 PASS**; latest job116393352584 explicitly reports**566 passed**. No new tracked file paths, licence path inventory unchanged.

### compact_edge_supply physical implementation and proof

Implementation **ccfe951baf0b754753166a90dfca425654d4a56c**. Fourth profile added consistently in assembly/extraction/composition/loaded-wave/diagnosis controllers and both workflows. Same frozen children and placement as M5: preB y330, finalx470/y112, four data paths276.015um, TM1datax378/390/402/414w4. Supply moved out of data corridor: **M5x418..454w36**, parallel **TM1x422..426w4**, native4x4upper via arrays at**x424**. SUB moved toTM1x358w4, finalAVSSx450w32. All child drawing regions independently XOR0; no device/sourceclock/current/bit/gate changes. EM/RF/substrate qualification remains false.
- Physical **38726423931 PASS**, sourceccfe951..., summary**643627210**, archive**643627003**(1214113B). Exact archive/embeddedsummary/layout hashes read back. Native560categoryDRCzero, hierarchical AND flat162deviceLVS, all five actual wrongfinger/missingHBT/intermacroopen/railshort/offgrid controls rejected. Receipt commit**4c10dbefb77ab1f7e31796ab46bf5b4afb036717**.
- Extraction **38726858271 PASS**, source4c10dbef..., summary**643638526**, archive**643638225**(7942669B). Actual **11913R/7851C**,41conductors/42electricalnets/322probes/462intrinsicterminals. All13actual raw-corruption controls and complete R/C matrix/geometry/ownership conservation pass. Archive/embeddedsummary/every native capture output read back. Receipt commit**d3b9c64f8fb7398ed2ebe460c3c63056289f8bb6**.
- Composition **38727463991 PASS**, sourced3b9c64f..., summary**643648040**, archive**643647863**(9521958B). All162models (57HBT24rppd81ptap),11913R7851C, six composition fault controls,41native metalnets and all12finalphysicalbase probes pass. Archive/embeddedsummary/every exported output hash read back. Receipt commit**370ff637ed78f18f04562f875b8d0ae354d11869**. Compact modelSHA b0a7f4ad150eed1a8f9e6d8ed1b34dd3be27d73e8b0ee756bdcd7ad78fa45c6c; wireSHA6e85c60f734ecf36866ed67dbf8fed58c1c706f75fdec7110a4b4aacc1ca525a. No ideal intermacro aliases or duplicated childRC.

NEXT: inspect actual completed edge-supply waveform summaries from live runs above. Pin all six metadata/publisher hashes into variant.loaded_studies, then run hosted wave_diagnosis for this profile: it replays exact original gates and performs full archive/embeddedsummary/native-output readback for ALL six. Do not transfer huge wave archives locally. Diagnosis accepts a zero-failure list too; useful for proving actual C improvement without changing acceptance. If nominal/hot/cold all pass, run actual physical_faults, independent HBT/resistor/MOS corners and hotquarterstep on this same geometry; retain failures. If hot fails, use actual C/interface/native safety diagnosis before new geometry/device changes. Full32:1/fourlane serialization and real clock integration remain necessary after this4:1component.

PLL remains original actual845 1us acquisition failure: 800–900ns126.2157ppm exceeds100ppm, later900–1000ns84.0102ppm cannot replace original window. No new PLL repair run. Source/archive/physicalpump details below. Mainchip finalSTA, full PHY/PLL/CDR/RX/PCS/LTSSM, analogpad/ESD/substrate/RF qualification and full-chip production gates remain OPEN; do not narrow goal or mark achieved/blocked.

Checkpoint UTC: 2026-10-15T11:33:34.620005+00:00

## 2026-10-15 — closer physical tree with Metal5 supply verified; loaded native runs active; ALL CLOUD

This entry supersedes the older live handles and compact_vertical pending status below. Latest user instruction remains ALL CLOUD and clean local. Local workspace `/home/hasanmelih/Documents/ChatGPT/nnsoc` is empty; no local CAD/tests/clones or artifact downloads. Read/edit source and archive bytes in RAM with GitHub API; execute native work only on hosted Actions. Never use `gh run view --log-failed` (writes local log caches). Cache retirement receipt asset642730081 confirms114 archived/read-back caches removed, unrelated projects untouched. Do not follow stale goal text saying local work. Full PHY, mainchip routing and final STA remain OPEN.

### Live handles — do not duplicate

Wave source **29948e0caea687b748f329dccb6ad48c115326b6**, profile **compact_m5_supply**:
- **38722317700** temperature_voltage. Actual wirehot job116379636395 and wirecold116379636535 verified running native transient. Compacthot summary643541102 and compactcold643538608 both component_screen_passed=true; this does NOT imply wired acceptance.
- **38722321392** nominal. Actual wire job116379647704 verified running native transient. Matched compact summary643541381 component_screen_passed=true.
- Mainchip **38703550233**, job116317277037, still running exact newer postCTS/replay and routing with upper_metals clock profile. Source d3a3cec31e13cbf877158b5a6861689f13ae38a3. No final timing result or detailed-route completion claim.
- Source validation **38722204953 PASS**, source5e85dad9ba0c4e8491fc49cbfa849a994e235466; prior validation38719797719 also PASS. Four source-control test suites contain566 tests as previously verified; no local test execution.

### Actual compact_vertical hot waveform still FAILED; preserved

Results now stored in `docs/evidence/pcie-tree4-assembly-input-20261015.json` under placement_variants.compact_vertical.loaded_studies, committed599657b1b3f93465b923eff20bb76007a8b61592. Run38718506788 wirehot summary643482801 has TWO samples below100mV, minimum98.97576930167817mV at0.3UI, no wrong sign. All6912 final physical input observations and62HBT64MOS safety screens pass; native diagnostics clean. Wirecold643480631 passes min264.671094mV. Nominal38718511203 wire643472709 passes min228.022664mV. All three compact controls pass. `loaded_all_corners_accepted=false`; never waive these failures or shift original gates.

### Source-bound failed-wave diagnosis implemented and executed

New `scripts/analyze_cloud_assembled_wave.py`; tx-tree-assembly-cloud stage `wave_diagnosis`. Reads pinned original hot wire capture, replays unchanged review, resolves real intrinsic base probes and real graph paths. No resimulation, altered source phase, or acceptance thresholds. Baseline diagnosis **38719793513**, source917c791ea946a6f600f4af83804e3d7d9e902cac, summary643488030/archive643487588. Exact receipt is tree4evidence.baseline_wave_diagnosis. Three baseline failures are falling bits on Bbranch:203,231,239. Worst bit203 has clock zero7.785413ps, mux zero25.208136ps, TX zero31.534817ps and100mV crossing37.610274ps versus fixed original sample37.5ps. Other crossings37.501219/37.541823ps. Actual four intermacro external capacitances160.562380/173.233724/168.609822/174.641345fF and resistor-path upper bounds about24.67–25.32ohm. Explicitly not effective resistance or RF qualification. Diagnosis success does not mean circuit acceptance.

### New compact_m5_supply physical candidate

Implemented in593a21c2b7778428b0b13c98460d66cfa9e07809. Source-bound adapters in assembly, extraction, composition, mux controller and both workflows accept baseline|compact_vertical|compact_m5_supply. PreA m90(353.985,0), preB m90(353.985,330), finalr0(470,112), before origin translation. Four TM1 data channels x378/390/402/414, width4um; each actual path276.015um. AVDD Metal5 stripe x358..454 (width96um), native Metal5→TopMetal2 via stacks4x4 atx366 for all three children. SUB TM1x466w4, finalAVSS TM1x444w32. Native frozen child drawing regions independently XOR0; parent intentionally changed. No model/current/clock/source-bit/gate adjustment. EM NOT QUALIFIED.

All receipts under placement_variants.compact_m5_supply in tree4evidence:
- Physical **38720750223 PASS**, source593a21c..., summary643505216/archive643504914. Native560categoryDRC zero, hierarchical AND flat162-device LVS, five actual malformed physical controls pass. Archive/embedded summary/output hashes read back. Receipt commit0b9c6f1f0a564b9c72ca21b5eed455fd4c636ebc.
- Extraction **38721369690 PASS**, source0b9c6f1..., summary643516176/archive643515990. Actual **11842R/7826C**,41metalconductors42electricalnets322geometryanchors462intrinsicterminals,13raw corruption controls, exact graph/RC/matrix conservation. No substrateR/RF/fullPEX qualification. Receipt commit5e85dad9ba0c4e8491fc49cbfa849a994e235466.
- Composition **38721828655 PASS**, source5e85dad9..., summary643526264/archive643526052 (9464692B), archiveSHA06f01969a92c29333f6c32c53ed6f8b81558001fed49cd543fca45d81b2218d1. All162 native devices,11842R7826C, six actual composition faults, all41native conductor nets, all12physical final input bases proven. Full readback/output hashes recorded in29948e0caea687b748f329dccb6ad48c115326b6. CompactSHA b0a7f4ad150eed1a8f9e6d8ed1b34dd3be27d73e8b0ee756bdcd7ad78fa45c6c; wireSHA299b3d22b5c6ba403bbbcf4cc810e7060a8911b4308c1aa0235056def9156a94. Never substitute prior baseline/vertical RC or duplicate childRC. No ideal internal alias.

NEXT: inspect actual complete summaries and archive hashes from38722317700/38722321392. If hot still fails, retain evidence and diagnose source-bound raw with fixed original sample phase and gates. If nominal/hot/cold all pass, dispatch physical_faults plus independent HBT/resistor/MOS corners and hot quarter-step for exact compact_m5_supply geometry; do not infer full acceptance from three conditions. Then actual larger serialization integration remains. Keep mainchip live run unduplicated; inspect terminal artifacts when available.

PLL still original800–900ns acquisition failure: actual8451us38674687038/review38705186021 has126.2157ppm >100ppm;900–1000ns84.0102ppm later passes but cannot replace original window. Physical pump/filter repair not yet selected. See older exact source/archive details below. Full32:1/fourlane PHY, PLL/CDR, RX/PCS/LTSSM, analog pads/ESD, qualified substrate/RF extraction, detailed mainchip route and setup/hold still OPEN. This turn made physical and diagnostic progress; do not mark goal complete or blocked.

Checkpoint UTC: 2026-10-15T10:50:59.594449+00:00

## 2026-10-15 — actual whole-tree loaded waves exposed hot failure; shorter real layout now in native waves; CLOUD ONLY

Latest user instruction is ALL CLOUD, local workspace empty. No local CAD/tests/clones/artifacts. RAM/API orchestration only; never `gh run view --log-failed` because it writes caches. Current goal turn is PROGRESS, not blocked: source-bound162-device composition, whole-core loaded wave evidence, actual physical placement repair and fresh native extraction/composition completed. Full32:1/fourlane serialPHY, actualPLL/CDR/safety/RF/ESD, mainchip detailed routing and finalSTA remain open. Do not narrow goal to4:1 or mark complete.

### Immediate live handles — do not duplicate

Source **65a454ff4d1b98bf6f4a774c2613622651d735a5**:
- **38718506788** actual `compact_vertical` assembled-core temperature_voltage: wirehot job**116366986582**, wirecold**116366986237** verifiedIN_PROGRESS in native transient. Compactcold completedSUCCESS execution; compacthot publishing. Need inspect actual summary acceptance, never infer from green Actions.
- **38718511203** same placement nominal matched control: wirejob**116367000226** verifiedIN_PROGRESS native transient; compact publishing/completing.
- **38703550233** MAINCHIP upper_metals routing, job**116317277037**, still verifiedIN_PROGRESS in native replay/routing. Source d3a3cec31e13cbf877158b5a6861689f13ae38a3. Exact older132overflowplacement; signalMetal2–TopMetal2, clockTopMetal1–TopMetal2; original zerooverflow/SDC/NDR/capacity. No duplicate and no finalSTA claim.

### Full-core composition and loaded-wave pipeline are implemented and proven

`scripts/run_cloud_tx_tree_composition.py` binds every native device/model/terminal to actual complete-core RC and independently recovers native schematic connectivity by collapsing only real R edges. Six actual output corruption controls reject; no ideal intermacro alias, no childRC duplication. Exact sources in **docs/evidence/pcie-tree4-assembly-input-20261015.json** (`verified_composition`, history and `placement_variants`).
- Initial baselinecomposition38713029536 (source45a44c2c), summary643366682, archive643366508, all162devices/11907R7847C/41conductors/300metalterminals/162unmodeledbody/22publicpins PASS. Archive and every output hash read back.
- Added native geometric interface binding, run**38714265875**, source393a8e69588ce74247d93358c9316305543a54bb; summary**643389563**, archive**643389409**, exact complete receipt inJSON. Frozen GDS/LVS `probe_net` at both real intermacro endpoints proves4distinctnative nets. Every final HBT base in final macro bbox bound (3perinput,12total). Compact probes ap=n_24/an=n_25/bp=n_26/bn=n_27; wired12anchors are source-proven in`wire96/tree-interface-probes.json`. NEVER add ideal ap/an/bp/bn public aliases.
- `run_cloud_tx_mux4.py --assembled-core compact|wire --assembled-placement baseline|compact_vertical` restores exact composition/extraction receipt for chosen placement, instantiates core ONCE +actualTX/fronts/bias (62HBT64MOS), original external source bits/clocks/startup/0.3,0.5,0.7UI/100mV unchanged. All9parallel positive/negative physical input base pairs checked per originalsample (6912interface samples), same150mV/commonmode gates. PublicCMOS interface768samples. No ideal intermediate aliases, no old three-macro instances.
- `interface_screen` rejects missing/empty/mixed-arity/aliased physical observations and demands complete original-phase coverage. New controls detect ONE failed parallel base even if the others pass. Hosted source validation**38715849025** and latest**38718236730 PASS**; **566tests** on former confirmed in actualjob log. Latest tests source d47306d2350c84d74af1bb6b1f2ce8f44dfb8bfd includes placement adapter. `LICENSES.md` refreshed from hostedcandidate38714864209 in25d38ea8; later commits only existingfiles, counts unchanged.

### Baseline assembled layout real-wire HOT FAILED — retained, not waived

All12cases under `loaded_studies` in tree4evidence JSON, each permanent summary/archive/hash:
- **38714860001** nominal compact+wire: PASS. Wire summary**643415517**, archive643415231; 69541rows,768originalsamples, min**228.006355mV**, final12base6912samples min211.601714mV;62HBT64MOSpass, no diagnostics.
- **38715509083** temp/supply: compacthot/cold PASS; wirecold summary**643425179** PASS min264.636648mV. **Wirehot summary643427378/archive643426992 FAIL:3samples below100mV, min98.46779434589426mV at0.3UI**. All6912final interface observations pass (min171.547234mV), allHBT/MOSsafety pass, clean diagnostics,69541rows. DO NOT relabel overall asPASS or move threshold/samplephase. Original individually-extracted/ideal-intermacro hot102.226mV does not apply to this full geometry.
- **38715513445** all6actualswap_pre_a_select/swap_leaf_select/disable_pre_b_bias compact+wire faults correctlyreject originalbits. Wired below100mV counts192/195/289; compact200/205/350. No native diagnostics. This is fault-control success, not healthy-circuit acceptance.

### Physical repair under test: compact_vertical, all four actual links now356.015um

`run_cloud_tx_tree_assembly.py --placement-profile compact_vertical`: only preB y400→330 and final y150→112; allchildGDSdevices/wires frozen and independently XOR-checked per drawinglayer before parent assembly. Four links394.015/388.015→**356.015** each. No circuit/current/clock/oracle change. Parent geometry intentionally differs: `exact_flat_geometry_preserved=false`; `frozen_child_drawing_regions_equal=true`. Baseline still requires exact originalflatXOR0. The alternate profile is explicitly named and source-pinned throughout extraction/composition/wave restoration, so no inheritedbaselineRC is accepted.
- Physical **38717337624 PASS**, source6bae58510c464c05b357736f853bb20c80fd940d, summary**643443993**, archive**643443803**: native560categoryDRC0, hierarchical+flat162LVS,5realphysicalfaults. `placement_variants.compact_vertical.verified_hierarchical_assembly`.
- Fresh RC **38717882380 PASS**, source5c9e9e0ba4e71b06b9a4808fe1780bd7e4a4df09, summary**643451397**, archive**643451252**: still11907R7847C, but NEWvalues/geometry.41conductors42electricalnets322anchors462terminals, all13nativecorruptioncontrols andfullC/Rgraphconservation pass. `verified_extraction` undervariant. Originalscope excludes substrateR/RF/fullPEX.
- Composition **38718138429 PASS**, source d47306d2350c84d74af1bb6b1f2ce8f44dfb8bfd, summary**643456082**, archive**643455893**/9446529bytes: full archive/embeddedsummary/everyexportedmodel+interfacehash verified. All162models/actualRC/topology/6faultcontrols/12physicalinputbases pass. `verified_composition` undervariant, pinned65a454ff. Actual electrical repair still UNPROVEN pending livewave runs above.

NEXT: inspect completed newnominal/hot/cold actualsummaries; retain failedcases. If allpass, run physicalfaults plus independentHBT/resistor/MOS corners and hotquarterstep on this exact assembled geometry; then expand physical serialization toward full32:1/fourlanes, not idealmacroconnections. If hotstillfails, diagnose actual source-bound failed samples/RC before further placement/driver changes. One possible geometric route to investigate (not implemented/proven): move avdd trunk toMetal5 in the intermacro channel, preserving nativevia stacks and original powerwidth, to free TopMetal1space and bring finalmacro closer inX; requires freshDRC/LVS/RC and waves. No arbitrary parasitic reduction or model-only acceptance.

### PLL remains actual acquisition failure, not a missing run

Actual8451us38674687038 complete; review38705186021 rejects original800–900ns frequency126.2157ppm vs100ppm, later900–1000ns84.0102ppm passes. Do not extend/shift window. All provenance inpcie-actual845-one-us-acquisition-rejection-20261015.json. No livePLL transient.
Source inspection this turn confirmed originalbench (asset634832275/batch000002, SHA6021e860...) has **no external loopfilter/clampedVCTRL**; only output50fF loads and actualparentinstance. Actualparent archive**642423511**, run38672085461, SHAff8837... contains pump30 with nativefiltercap `X_xpump_xd0001 ... cap_cmim w=10u l=10u`, rlo47um andrhi140um, currentbiasR80um. Repo generator`hw/soc/flow/make_pcie_pump_filter13_rhi140_v1.py` andsource`pll_pump_filter_hv_rhi140_v1.spice` exist. A real acquisition repair needs physical pump/filter geometry and freshRC; no capacitor or bias candidate was chosen or run inthisturn. Sharedintrinsicbulk/RF/full845safety/PVT remainunqualified.

Checkpoint UTC: 2026-10-15T10:16:07.537968+00:00

## 2026-10-15 — actual162-device whole-tree composition PASS; cloud only

Source45a44c2cf06628cc04c89da90b57bc64bd6e78e6, hosted composition38713029536 passed. Full readback of archive643366508 and embedded summary643366682 verified every exported model hash. `verified_composition` added to`docs/evidence/pcie-tree4-assembly-input-20261015.json`.162native devices,11907R7847C preserved exactly;6actual model/connection/RC corruption controls rejected. Independent resistor-only component collapse recovers all41native metal nets,300intrinsic metal terminals,162body/well terminals and22publicports. No ideal intermacro alias or childRC doublecounting. Native loaded transient NOT yet accepted. Next bind final input observations to actual physical HBT base terminals and run unchanged original-bit loaded bench against compact and full assembledRC.

Independent corner run38703553931 now terminal24/24published. Lastwirecold_high_hbt_wcs summary643319518 passes its component screens; earlier compact and resistorWCS failures remain. All-corner acceptance staysFALSE. Source inventory candidate from hosted38713077170 applied with exactSHA and same source path set. Mainchip38703550233 still verifiedlive; no duplicate.

## 2026-10-15 — ACTUAL4:1core assembled and nativeRC PASS; PLL original1us acquisition FAIL; cloud only

Latest user execution override is **CLOUD ONLY**, not the stale local-work phrase in the goal. Workspace `/home/hasanmelih/Documents/ChatGPT/nnsoc` empty. No local CAD/tests/clones/artifacts. Use GitHub API/RAM for sources and summaries; hosted Actions for all native work. Never `gh run view --log-failed` (local cache). Do not mark fullPHY/mainchip/finalSTA complete.

### Actual intermacro physical integration now exists for the three-macro4:1CML core

New controller `scripts/run_cloud_tx_tree_assembly.py`, workflow`tx-tree-assembly-cloud.yml` (`stage=physical|extraction`). Two exact cascade158 direct+tight child GDS, one exact V10 direct+tight child GDS. Source bindings and all permanent receipts in **`docs/evidence/pcie-tree4-assembly-input-20261015.json`**. Actual4differential data wires and sharedavdd/avss/sub metals;22external ports;162devices=57HBT+24rppd+81ptap.4:1core ONLY: CMOS frontends, loaded TX, clock/bias generation,32:1/four lanes, mainchip and qualification are still open.

-Flat physical **38707284903 PASS**, source252f356634ea410cea29e383a5e7d798d4015cac; summary643256294 SHA6fab9171550c956573ea3d8970e829480c8e55fce04dd6af56c7dfb11e1cfae3. Archive643256074/3518050bytes SHA86bf43e977fc140d1db880d380b810b36d9a4d9f7fa39757a8d26131b5695979. Native560categoryDRC0; both162/162transistor/contactLVS;5fault controls correctly reject (finger count, missingHBT, real intermacroopen, actualrailshort, offgrid). GDSa1e52df63ae8d8a1381f7804c8d74399b6e302a39e3be2f5cfd65f68d47921ae. Cellbbox940.785x799.24um. Data pair route lengths394.015/394.015 and388.015/388.015um; no electrical acceptance inferred.
-Hierarchical physical **38708389329 PASS**, source9de9d651957f5d8588adfa0f138f307d4f78061b; summary643283087. ArchiveSHAae83d275bddf1ccbebbb5ed15e43e3fab8bdaa23001261ed70f0b905a926217d. Same full gates again; every physical layer's merged region XOR against the exact accepted flatGDS is empty. Preserve native PCell hierarchy for unambiguous device-terminal anchoring. Generator records `origin_translation_um`; placement/routes metadata otherwise start before that shift, fault-cut and publicport coordinates after shift.
-Initial failures preserved:38705893904 parsed2terminalptap as3terminalR, stopped generation.38706630710 erased all labels and destroyed nativeHBT identification, causing1002CntB.h1 markers. Corrected by removing ONLY36macroTM2public labels/pins, preserving nativePCell identifiers. No rule/waiver changed. Failed summaries643227826/643240858.

### Fresh complete physical tree RC is verified, not just child RC concatenation

**38709725650 PASS**, source**dcde9dab0f14b0c5782be48bf2805f9804545134**. `scripts/run_cloud_tx_tree_extraction.py` adapts the frozen standalone native methods to exact independently measured full-tree scope. All162devices and462intrinsic terminals accounted; **41metal conductors,42electrical nets inclbulk,322geometry probes,300metal terminals,162unmodeledbody/well terminals**. Native source graph exported **11907R/7847C**. Exact resistor edge/value multiset, geometry ownership, every ground/mutualC attachment, full42x42collapsedC conservation, all13real raw-corruption controls PASS. All843port-short warnings are same-conductor aliases; no intrinsic alias edges used to hide opens. SubstrateR=false, fullPEX=false, RF/point distribution qualification=false.

Summary**643306585**, archive**643306326**/7856526bytes SHA**ea456af2ea37f29503f1f42bf559f30a9dd9a474938cea89c2f9d5d9ca708a0c**. Full archive readback verifies embedded extraction result and every native capture output. Receipt/audit/controls stored under`verified_extraction` in tree4assemblyinput. Prior38709136819 raw native extraction succeeded but audit rejected remaining17/18standalone cardinalities; native GDS/LVS independently proved41/42. Fixed ALL node, ownership, port, retirement, branch and matrix cardinalities explicitly, retained all tolerances and negative controls. Failed summary643293456 remains permanent.

**NEXT PRIORITY PHY ACTION:** Compose this actual162device tree and11907R7847C graph into nativeSPICE, preserve exact native transistor/terminal bindings and prove schematic graph/RC preservation; then run unchanged loaded original-bit waveform gates. Never sum old childRC with whole-treeRC (double counting). Existing standalone `run_cloud_tx_layout_composition.py` is54device-specific and needs a separate full-tree adapter, NOT false54device receipts. Frozen `binding96/export01.py`, `build-devices01.py`, `wire96/compose49.py`, `check-compose98.py` in known composition/extraction archives are reusable after strict scope adaptation. Full-tree outputs have22publicports; internalap/an/bp/bn are not public pins. Bench final-interface probes must bind actual native terminal/boundary reference points with source geometry proof, not reintroduce ideal intermacro aliases. Existing `run_cloud_tx_mux4.py tree_plan(4)` connects preA d0/d2→a,preB d1/d3→b, final a/b→m; map allactual62HBT+64MOS once front/TX/clockbias are included. Keep original external source bits,0.3/0.5/0.7UI,100mV, all-device limits and fault controls. Actualphysical4tree passing alone is not32:1/four-lane/fullPHY acceptance.

### Robustness results for the prior individually extracted (ideal intermacro) V10 direct+tight test

Source d3a3cec31e13cbf877158b5a6861689f13ae38a3. Existing6nominal/hot/cold matched cases pass; hotwire102.226266mV vsprevious83.938999mV/52bad. Additional evidence appended to`pcie-v10-tight-direct-supply-loaded-pass-20261015.json`:
-38703557182 all12MOS matched cases terminalPASS.
-38703561202 both hot_low_quarter_step casesPASS: actualmaxstep.25ps,137541rows; wire102.261064mV. Summary643202906; compact643186921. No phase/oracle change.
-38703564758 all6actual fault cases correctlyREJECTED (swap selectors or disablebias), complete native captures. Not healthy-circuitpasses.
-38703553931 independent corners **23/24published as of snapshot, last case stilllive**. Cold/high resistorWCS compact andwire fail final-interface common-mode (compact2.04199–2.06276V). Cold/high HBTWCS compact fails common-mode and12finalHBTlimits (VBEup to1.02336V,Ic/emitterup to2.23944mA). LastwireHBTWCS pending; do not rerun. All-corner acceptance isFALSE even though originalnominal/hot/cold passes. Fix actual bias/device/interface circuit and regenerate affected physical models before adoption; do not relax gates.

### Actual845PLL1us ended; ORIGINAL acquisition gate is rejected

Native38674687038 terminalSUCCESS as execution, not acceptance. Exact native3201212rows,35columns,1us complete with clean prefix. Review**38705186021** actualreviewjob completed and preserved **FAIL_ACTUAL845_ORIGINAL_ONE_US_ACQUISITION_GATES_NOT_PHY_ACCEPTANCE**. Summary643226866 SHA69ced95223e3da0ded17f2d64a3ab1aead3dcadb6f42e3e3512273f0cf506a35; native summary643202921 SHA9dfa7f360da5bc7ee8023230cf3ec1bb2da976e65db5ae33f4cd735d8637ad54; nativearchive643200631/1318040150bytes SHAe9056bf3eda2384204a9cfdc7b34c4725f15c0221389cb9dc937d176d2097dee. Evidence`pcie-actual845-one-us-acquisition-rejection-20261015.json`.
-800–900ns frequency100012621.5737Hz =126.2157ppm FAILoriginal100ppm. Phase span11.35798ps PASS.
-900–1000ns frequency100008401.0213Hz =84.0102ppm PASS; phasespan7.56028ps PASS.
-No slips, originalVCTRLwindow PASS; unchanged actual50ns prefix passes1mV/1ps (observed maxvoltage1.25uV, edgeerrors0). Sustained passing rolling window begins860ns; do not shift/extend original800–900ns acceptance window.
-Need real loop acquisition repair, then fresh physical/source-bound validation; no full-device safety/PVT acceptance from35selectedprobes. `run_cloud_pll865_snapshot.py restore_actual_pfd_parent` pins actual845composition38672085461, SHA91364a351fad4d376e6d168d85af6f63ff4076bfecd5af83192492bc514073fc. No newPLL transient running now; do not duplicate completed1us. Original PLL loop capacitor/device provenance still needs inspection before choosing physical change.

The review workflow also had a separate staleLICENSES.md count failure. Fixed using exact hosted generated candidate, not local generator. `cloud-migration-checks`38708393186 (none/native regression) subsequentlyPASS. Added extraction script then refreshed count again from hosted audit38709140864, source8d3488997652f5d297caec747483ff5385edb2ec; applied2470574 after same trackedpathset verified. Current later commits modify existing files only; do not let new source additions stale inventory again.

### MAINCHIP still live

**38703550233**, source**d3a3cec31e13cbf877158b5a6861689f13ae38a3**, job116317277037 verifiedIN_PROGRESS in native replay/routing. Exact132overflow placement, local_optimize_buffers,Ethernethold2,seed13,fast_route,clockprofileupper_metals. SignalsMetal2–TopMetal2, clocksTopMetal1–TopMetal2; native range readback, unchanged real capacity/SDC/CTS/NDR andzerooverflow gate. Wait for actual terminal result; no duplicate. Previous targeted193preCTS trial failed188overflow. Finalsetup/hold and detailed routing/extraction remain open.

Checkpoint UTC: 2026-10-15T09:10:22.105364+00:00

## 2026-10-15 — CLOUD ONLY; direct-supply hot failure repaired at component scope; controlled routing and process tests LIVE

Latest user instruction remains **all work in cloud, leave no local project files**. Local workspace `/home/hasanmelih/Documents/ChatGPT/nnsoc` is empty; no local OpenROAD/ngspice/KLayout/netgen/Yosys process. API/source/summary orchestration uses RAM only; all CAD/tests/artifacts are on GitHub-hosted runners and permanent Releases. Previous cloud handoff and log-cache retirement receipts remain authoritative. Never restore local CAD or use `gh run view --log-failed` (writes local cache).

**New V10 direct-supply component screens PASS**, source197c58c17c7867023c78355c851859422cc567e3. Composition38700550087 passed54devices/4080R/2683C, receipt `pcie-final-v10-tight-direct-supply-composition-20261015.json`; new final profile`v10_kelvin_low_ports_loads_shunts_series_direct_tight`, prestage`cascade158_kelvin_supply_direct_tight`. Runs38701140868nominal and38701144359temperature_voltage: all6matched compact/wire cases pass original768samples at0.3/0.5/0.7UI,100mV and all-device limits,69541rows,zeroOP,clean diagnostics. Hot wire improved52bad/83.938999mV to **0bad/102.226266mV**. Headroomonly2.226266mV: not robust all-corner acceptance. Summary643141554 SHAdfcb6df1b275f4703ab4ba48ddbe3a15e94adf40ea335928e0fc2a9910bcc891. Exact six-case summaries/hashes:`docs/evidence/pcie-v10-tight-direct-supply-loaded-pass-20261015.json`.

**Original32 full streamed wire38679319167 now TERMINAL PASS**, notlive. Runtime13818.38s; all69541native rows,604HBT/512MOS,768originalsamples,minimum235.353307mV,clean diagnostics. Earlier max-data warning is absent with complete binary capture. Summary643135282, result/outputs/hashes in`docs/evidence/pcie-32-streamed-wire-nominal-20261015.json`. Its ORIGINAL interior-pin profile is different from the new tight direct-supply candidate. No cross-profile adoption. External ideal clocks/intermacro connections, missing assembled tree GDS/fullPEX/ESD/jitter/BER remain. **FullPHY still OPEN.**

**LIVE new component robustness studies**, all source**d3a3cec31e13cbf877158b5a6861689f13ae38a3**, streams4, matched compact/wire, same new direct+tight profile, binary/native_res/stiff65; no gate/timing adjustment:
-38703553931 independent_corners (12process/temperature combinations).
-38703557182 mos_corners (6MOS combinations).
-38703561202 hot_low_quarter_step (time-step convergence at limiting corner).
-38703564758 physical_faults (3actual faults must be rejected, not counted as healthy passes).
Inspect actual `component_screen_passed`, original signal margins, all-device gates, diagnostics and complete capture; workflowSUCCESS alone is not electrical acceptance. Do not duplicate these runs.

**LIVE mainchip upper-clock-layer comparison38703550233**, source**d3a3cec31e13cbf877158b5a6861689f13ae38a3**, job116317277037. Hosted syntax and self-tests PASSED; native replay in progress. Exact existing132overflow placement (local_optimize_buffers, Ethernethold2,seed13) hash checked before routing; fast_route,macrobaseline,critical0. New explicit `clock_routing_profile=upper_metals` restricts clocks toTopMetal1–TopMetal2; signals remainMetal2–TopMetal2, all capacity adjustment/SDC/CTS/NDR and strictzerooverflow retained. Frozen OpenROADdcf36133 source confirms actual API in`src/odb/src/swig/tcl/odb.tcl:608-645`; native getters independently read back clock/signal ranges. Profile rejects mismatched placement/seed/solver/halo/priority etc via12negativecontrols; baseline unchanged. Existing prects193candidate FAILED188overflow; no closure claimed. Top-metal RC is technologyLEF default, still unqualified; routed timing/detailed routing/extraction required after successful GRT. Do not duplicate route.

**Still live actual845PLL1us38674687038**, source762c629d8e5124541fa40790348aad95b1a1c5b1, job116225492444. After terminalSUCCESS dispatch existing`actual_parent_acquisition_review_d2` through cloud-migration-checks.yml, then inspect unchanged100ppm/50ps/no-slip/VCTRL gates and exact first50nsprefix. Do not start review early or repeat transient. Failure/timeout must be preserved, never relabeled as qualified PHY.

Latest API snapshot UTC: 2026-10-15T08:11:34.865841+00:00
-38703550233: in_progress, conclusion=None; sourced3a3cec31e13cbf877158b5a6861689f13ae38a3.
-38703553931: queued, conclusion=None; sourced3a3cec31e13cbf877158b5a6861689f13ae38a3.
-38703557182: queued, conclusion=None; sourced3a3cec31e13cbf877158b5a6861689f13ae38a3.
-38703561202: in_progress, conclusion=None; sourced3a3cec31e13cbf877158b5a6861689f13ae38a3.
-38703564758: queued, conclusion=None; sourced3a3cec31e13cbf877158b5a6861689f13ae38a3.
-38674687038: in_progress, conclusion=None; source762c629d8e5124541fa40790348aad95b1a1c5b1.

Full serialGen3x4PHY, assembled physical tree/mainchiprouting and finalsetup/hold remain OPEN. These component improvements are not production signoff.

## 2026-10-15 — waveform regression diagnosed; V10 direct supply composition LIVE; mainchip188 remains

**Shifted output electrical candidate REJECTED**:38695637067/38695640569 terminal. All compact and wire nominal/cold pass. Hot wire **64/768bad,min76.338729mV** vs unshifted tight52/83.938999mV. Hot summary643012045 SHA689ef15afa57c23ac28a179d227156e3ede4435a55f80968e892f058658e34cb. Evidence:`pcie-output-passive-shift-loaded-rejection-20261015.json`. No adoption.

**Actual full binary waveform diagnosis passed**: tight_hot38697912670 summary643042413; shifted_outputs_hot38697916136 summary643042150. Analyzer now strictly supports original native/wave.raw plus legacywave.dat.gz; header/entire payload/hash/vector identity protected.32tests pass (nonuniform-time stats, reordered binary vectors, truncated payload, old/mismatched inputs). Failed initial archive-reader attempts38697369939/38697373766 are preserved; no native rerun or waveform edits. Bindings:`pcie-boundary-hot-diagnosis-input-20261015.json`; results/hashes:`pcie-boundary-hot-wave-diagnosis-20261015.json`.

Finding: bit0 mean source-to100mV **37.9020->38.4208ps**, bit1 **34.0341->33.2649ps**, physical mp/mn mean imbalance22.68->29.35mV. Compact controls coincide; final data collectors still lose120–145mV versuscompact. OutputC reduction alone worsens asymmetry. Next candidate targets real load-supply route, NOT gates/phase/current/device dimensions.

**V10 direct supply native physical PASS38698673205**, source8ff1cc1782edf6cbeb3537d3a45bf6c0143c3d43. Original UNshifted tight V10 + existing actual direct resistor landing-to-TM1 straps.560categoryDRC0markers,both54/54LVS,5fault controls pass. Summary643063294 SHAdaff88f2cc2c6e25bdb6d8bd8715cb1f4272d068067a2d9d8614ce0a335437cc. Physical evidence:`pcie-v10-tight-direct-supply-layout-20261015.json`. V8 direct version had failed originalhot; no acceptance inherited.

**FreshRC38699732467 PASS**:54devices,4080R/2683C,all13controls and exact native graph/C/ownership. Summary643086160 SHA823a3766ac9161598117928edb2489a0535ce68d0f0699fe250fb9516c2401e1; archive6300668bytes SHA705b7b89c98b103d96e2648bb03265b9e71312c27ce113e707ae05534ed7ff9d. Explicit54body/well,substrateR/RF/fullPEX limits unchanged. Evidence:`pcie-v10-tight-direct-supply-rc-20261015.json`.

**LIVE composition38700550087**, source**c96936c8bae942bf082fa3039a43621a1806bf4e**, circuitfinal_drive_v10, variant`critical_buses_kelvin_low_ports_loads_shunts_series_direct`, boundarynearest_pair_tight,compose_only=true. Exact new variant receipt is pinned independently in composition-input. Next inspect native54device/4080R/2683C result and archive hashes; create distinct V10 direct+tight final profile/receipt, retain prestagecascade158_kelvin_supply_direct_tight, then unchanged nominal+hot/cold4stream matched compact/wire binary screens. No V10 direct electrical profile exists yet.

**MAINCHIP193 ROUTE TERMINAL FAILED38683404082**, notlive:188overflow(M2=1,M3=18,M4=14,M5=142,TM1=12,TM2=1), improvedsame-flow222butnotzero; all1216cluster366 and olderdifferentplacement132 alsofailed. Exactsummary643038055 SHA91038fd08cd3142e5ac5c12508d9fe25486a731cfceac8ccb0b25a13385a2a3f; archive145076855bytes SHA487601b11e94e64facf6e9803d6e2bfd4882befbfa5f546f17d8b4e08b43b485.193scopeverified,1216measured,original97722cells retained. Placement-estimated slowsetup-3.136906ns/fasthold-0.625263ns; NOT routedSTA. Evidence:`pcie-packet-cluster-targeted-rejection-20261015.json`.

**Exact native congestion diagnosis38699508468 PASS** source028370798ff5605142ad94482d410946d08e3e46. Summary643080697 (~4.27MB); read ONLY needed fields.109markers/sum188,988uniquenets:268packetdata,80staging,35Ethernet,20clock,585other. Namegroupsnotcausal. Pin/bbox transforms and immutablefailedODB checked. Evidence:`pcie-packet193-congestion-diagnosis-20261015.json`. Next analyze remaining marker/channel geometry to choose real repair; do not repeat finishedroute or treat congestion reduction asclosure. Native failedODBhash2c761b94b811ef82810abd6a37b9936754e1d69ba8b85e2151cead517d5dd5f0; reportbadf99c790db14ef4adf8dc79da066c194e407f9f1ed317b3f757e55cf5e8c93.

Cloud durability fixed: `restore_cloud_boundary_failure.py` restores exact oldfailedZIP/proof from permanentassets642644297/642644376, no expiry-prone Actions artifact/run API. Hosted38696603319PASS with60bindingtests andbyte-exactproof; result643013513. Evidence:`cloud-permanent-boundary-failure-restore-20261015.json`. Failed artifacts/claims unchanged.

Stilllive: original32completewire38679319167/job116240001143 and actual845PLL1us38674687038/job116225492444. After PLL terminalSUCCESS dispatch existing actual_parent_acquisition_review_d2 (do not startearly). No duplicates. FullserialPHY/mainchiproute/finalSTA OPEN. Allcloud/localworkspaceempty.

## 2026-10-15 — repaired shifted-output model loaded screens LIVE

**FreshRC38694566613 PASS**, summary642967705 SHA5701f7d3157ab35d299765b23bbbaab43c4bc1f7a74e61348a64b360614feea2; archive6295768bytes SHAc8caae9782333240493c9e4c5102ba50229ce952e8af4350826e97486eb4d88e.54devices,4018R/2649C,17conductors/112probes,all13real corruption controls; exact native Rgraph/C values and geometry ownership conserved. Explicit54body/well/substrateR/RF/fullPEX limitations unchanged. Record:`docs/evidence/pcie-output-passive-shift-rc-20261015.json`.

**Composition38694954036 PASS**, sourceba1e1f2044e12e1abccd3ee9853a30732d1342cd, summary642983811 SHA369755e1dde6ecf8eb8413be68ec6d5c77fcf765acfb9fb9e87475e76b996741. Archive6675412bytes SHA771c407db5eeee9fa0fdfd4c53042979bb3c06ca81da05f1b915f5f63a1c710c. Full archive readback verified embedded resultJSON and both SPICE outputs. New exact receipt:`docs/evidence/pcie-final-v10-tight-left-outputs-composition-20261015.json`; wire20d4e7b18ac3198d3300ec5ac6a2b8764ea1569bb893fd42811e59233be7a7eb; compact88ef39f86774c3a8da6b10d6a2983dfd9e8fea0b356dfc76e18c731f9b41c661. Compact ordering changes are not an electrical pass; unchanged source circuit already passed strict layout LVS.

**Loaded simulations LIVE**, source**5dbc28504fbcfc9412d47a583484daef49d537df**:
- Nominal **38695637067**: compact116291452115; wire116291452407.
- Temperature/voltage **38695640569**: cold compact116291463659; hot compact116291463929; hot wire116291464044; cold wire116291464081.
- streams4; prestagecascade158_kelvin_supply_direct_tight (same proven receipt); matched final profile`v10_kelvin_low_ports_loads_shunts_series_left_outputs`; stiff65,native_res,binary. All768samples/0.3,0.5,0.7UI/100mV/device limits unchanged.
- Source audit38695644545PASS. Prior audit38695191029 proved **60passed/465deselected**, crossing physical policy and actual old/new variant bindings with valid hashes. Same-policy old geometry is rejected.
- Push38695637295skipped by existing guard, no duplicate transient.

Inspect all6 actual summaries/capture completeness, not just workflow verdict. Previous unshifted tight hotFAIL52samples/83.938999mV remains authoritative until this new physically verified variant is electrically proven. No new geometry adopted yet. Native attached-capacitance sums from exact RC: outputs21.61007/18.237282fF ->19.10986/15.708092fF; these are physical attachment sums, not timing or effective coupling predictions.

Long mainchip19338683404082, original32fullwire38679319167, actual845PLL1us38674687038 verified live this turn. Both oldchecks38633437805/38633422995 also live on GitHub-hostedubuntu24.04, NOT local; no unverified cancellation. PLL completion requires existing actual_parent_acquisition_review_d2. FullPHY/mainchiproute/finalSTA remain open. Allcloud; localworkspaceempty.

## 2026-10-15 — actual shifted output layout LVS repaired; fresh extraction live

**38694073224 PASS** (source2a7438fed513171d62645e6d633d8ab4551af193): native560-category DRC0markers; hierarchical+flat54/54 transistor LVS with no extraction diagnostics; all5actual physical fault controls rejected correctly. This closes the new avss/sub short in this macro only, NOT mainchip or fullPHY LVS/acceptance. Final output passives moved38.4um left; row24 ground escapes externally at-19.2; row23 retains149.6. Original circuit dimensions/models unchanged.

Exact physical record `docs/evidence/pcie-output-passive-shift-layout-20261015.json`; summary642958509 SHA1b9d8765e923eeae70bee8fa3de932a046276b2397ca24aa786c4a2ad3ba346a; archive399364bytes SHA8d8ffbab8eadc8e3fa35b6165f0d9bed12a129cc019e4978aa4bbd0faee23548. Source audit38694076042 alsoPASS.

**Fresh extraction38694566613 IN_PROGRESS**, source**de076c2d82f8f2afe204393baa8368ccc4f8a3a0**. circuitfinal_drive_v10; variant`critical_buses_kelvin_low_ports_loads_shunts_series_left_outputs`; boundarynearest_pair_tight. Separate exact variant key added under `boundary_tight_variants` in extraction-input. Existing tight sources retained. Extraction and composition workflows now accept this explicit variant (71004a8).

Next: inspect exact nativeRC topology/C conservation/13controls; ifPASS bind NEW variant key in composition-input and compose_only via tx-layout-waveform-cloud. Then add distinct final shifted-output profile+receipt in mux4/tree workflow. Keep prestage existing tight receipt. Run unchanged4-stream nominal+hot/cold matched compact/wire; preserve any failure. Tight predecessor hot FAIL52/83.938999mV remains until new electrically proven result. No shifted electrical profile or composition receipt exists yet.

Rejected intermediate native38692269967 avss|sub short and generator-only38693022160/38693631444 failures are all preserved with dedicated evidence. Generator guard changes retain8um supply-riser centre exclusion on either side and permit positive-width pins already exactly at macro boundary. No native DRC/LVS rule weakened. Intermediate c533ed111.2/-3.6 ground proposal never ran.

Long mainchip19338683404082, original32fullwire38679319167 and actual845PLL1us38674687038 rechecked live at this checkpoint. No duplicates. PLL terminalSUCCESS requires actual_parent_acquisition_review_d2. FullserialPHY, complete mainchip routing and finalSTA remain OPEN. Allwork cloud-only; local workspace empty.

## 2026-10-15 — output-passive shift real LVS short diagnosed and repaired

Original placement run**38692269967 FAILED**: native560-category DRC0markers but transistor LVS merges **avss|sub**. All54 devices/source reference preserved; physical acceptance denied and no extraction dispatched. Permanent failed summary642918281 SHAab27a69c0bc899ed9c589bb9745bf29943ecf71da4262e7c04401177b06ec7d2; archive642918062 SHAd8b73b2bc53e9f922b7646dbc971e74ebcdeddc6225a738792a1b542810b1adf. Failure details: `docs/evidence/pcie-output-passive-shift-lvs-rejection-20261015.json`.

Cause: moving row24 to x15.6 also moves its substrate escape to34.8 (=x+19.2), exactly the old explicit avss lane. **Source c007fda6e7f3e19c2cb0a83a0f6438cf4a0b3cdc** keeps row23's proven avss lane149.6 and moves row24 avss lane to-19.2, outside the wide avdd riser atx-10. Actual conductor rebuilt from native pins; no logical shorts waived, no models/taps removed. Intermediate c533ed proposal111.2/-3.6 was never dispatched and is superseded.

**New native physical run38693022160**, **source audit38693025410** (queued at last read). Same finalV10, variantcritical_buses_kelvin_low_ports_loads_shunts_series_left_outputs, boundarynearest_pair_tight. Inspect actual native560-category DRC, both54/54LVS, all5fault controls before binding extraction. Neither shifted geometry has electrical acceptance or a receipt/profile yet. FullPHY/mainchip/STA stay open.

Tight predecessor hot rejection52samples/83.938999mV remains authoritative. Previous physical layout receipt tables must NOT be overwritten by unverified shifted geometry. Once physical gates pass, add independent variant key and workflow extraction/composition choices, then freshRC/loaded waves.

Long mainchip19338683404082, original32wire38679319167 and actual845PLL38674687038 were verified live this turn; no reruns. Cloud-only, no local design/test files.

## 2026-10-15 — tight hot REJECTED; real output-passive placement trial

**Tight allcorners electrical results are terminal and reviewed:**38690816164/38690819319. Nominal wire minimum219.359807mV and cold wire263.601867mV pass. All compact controls pass. **Hot wire FAILS52/768samples, minimum83.938999mV** (previous nearest59/79.622008mV). No failed devices/diagnostics; all captures69541rows. Never adopt this geometry as electrically qualified. Full six-source evidence and hashes: `docs/evidence/pcie-tight-boundary-loaded-rejection-20261015.json`. Hot summary642898461, SHAe8f0a760ea24b3d2542577517b2e5e3f8d4c822090e5674f8c204229f00732fa.

Capacitance comparison is separately recorded in `docs/evidence/pcie-tight-boundary-capacitance-comparison-20261015.json`: real native attachment sum falls1.7545fF for each output; this is NOT an effective switching-load/delay model or acceptance.

New physical source **481cf09352d2949802382dfd47f835a5d2b8706e** adds opt-in variant `critical_buses_kelvin_low_ports_loads_shunts_series_left_outputs`, exact finalV10 + nearest_pair_tight only. Translates actual generator resistor rows23/24/25/26 by[-38.4,0]um; all device models/dimensions, schematic and route widths remain unchanged; affected wiring regenerated from real new coordinates. Physical geometry may fail; no acceptance assumed.

**New native physical run38692269967** (tx-layout-repair-cloud), **source audit38692273367**. Inspect actual DRC560categories, hierarchical/flat54/54LVS, all five real fault controls. On physical PASS, add exact source receipt under existing `boundary_tight_variants` with the NEW variant key and add that variant to extraction/waveform workflow choices; old tight geometry must remain pinned independently. Then fresh extraction/composition/loaded original gates. No new extraction receipt/profile exists yet. Publication group remains layout-boundary-tight-final_drive_v10; runID distinguishes it.

Three long runs verified live this turn: mainchip193 route38683404082; original32 fullwire38679319167; actual845 PLL1us38674687038. No duplicate dispatch. PLL successful completion still requires existing actual_parent_acquisition_review_d2. FullPHY/mainchip route/finalSTA remain open; cloud-only and empty local workspace.

## 2026-10-15 — tight models bound; unchanged loaded screens running

Source **01ca948f183b67ee573b5aa7ff33c415eadc4b71**. Real tight-boundary extraction38689805645/38689808641 passed original54-device,17-conductor,112-probe/100-metal-terminal audit and all13 corruption controls. RC: cascade3871R/2592C; final4018R/2648C. Exact records: `docs/evidence/pcie-tight-boundary-rc-20261015.json`. All54 body/well terminal limitations, substrateR=false, fullPEX=false, RFdistribution=false remain explicit.

Fresh composition38690296309/38690299339 passed with exact matching54devices and RC counts. Permanent archive readback verified embedded result JSON and both SPICE hashes. Dedicated tight receipts: `docs/evidence/pcie-cascade158-tight-composition-20261015.json`, `docs/evidence/pcie-final-v10-tight-composition-20261015.json`. No electrical adoption yet.

**LIVE loaded studies**, source01ca948f:
- Nominal **38690816164**: compact job116276049677; wire job116276049846.
- Temperature/voltage **38690819319**: cold wire116276070657; cold compact116276070856; hot compact116276070927; hot wire116276070947.
- Inputs: streams4; prestagecascade158_kelvin_supply_direct_tight; matched finalv10_kelvin_low_ports_loads_shunts_series_tight; stiff65 clock; native_res; complete binary capture. All original768samples/0.3,0.5,0.7UI/100mV/device limits unchanged.
- Source audit **38690822801 PASS**. Previous extended binding audit38690425520 verified **15 passed/465 deselected**, including stale left/nearest receipts rejected against tight policy.
- Push-trigger38690696681 skipped by workflow's own guard; no duplicate native simulation.

Next: inspect all six actual electrical summaries and original full-wave coverage, preserve any failure, do not infer electrical acceptance from job success. Nearest predecessor hot failed59samples/min79.622008mV. Only expand physical tree qualification when the new real metal passes unchanged gates. FullPHY, intermacro routing, substrate/RF/ESD and mainchip final route/STA are still open.

Long jobs confirmed live before this chain: mainchip193 route38683404082; original32 full-wire38679319167; actual845 PLL1us38674687038. No reruns. PLL terminal-success triggers existing actual_parent_acquisition_review_d2. Cloud-only; local workspace empty.

## 2026-10-15 — both tight boundary macros physically pass; fresh RC started

Source `9ef1b6b520414af7fdc2542d97d1fedbfc3e4c9f` binds **separate `boundary_tight_variants`** receipts. Original left/nearest receipts are unchanged; exact policy guard includes `nearest_pair_tight`.

Both physical runs38689140829/38689143416 passed native560-category DRC with0markers, hierarchical+flat54/54-device LVS with no extraction diagnostics, and all five real fault controls. Exact archive and summary hashes and measurements are committed in `docs/evidence/pcie-tight-boundary-layout-20261015.json`. This is macro physical evidence, not electrical or fullPHY acceptance.

Fresh cloud extraction: cascade158 **38689805645**; finalV10 **38689808641**. Source audit **38689811421**. On successful completion, inspect actual extraction summaries (topology, R/C conservation, fault controls, explicit substrate limitations); bind these exact archives under `boundary_tight_variants` in composition-input JSON; then dispatch tx-layout-waveform-cloud with compose_only=true and nearest_pair_tight for each macro. Add distinct tight profiles/receipt files for loaded tree and run unchanged nominal+hot/cold four-stream screens before considering32-stream or any adoption. Never inherit nearest geometry acceptance: its hot wire FAILED59samples/79.622008mV.

Rechecked live long native jobs: mainchip193 route38683404082/job116252752695; complete32wire38679319167/job116240001143; actual845 PLL1us38674687038/job116225492444. Do not duplicate. When PLL completes successfully, run existing actual_parent_acquisition_review_d2. All work cloud-only; local workspace remains empty.

## 2026-10-15 — tight perimeter runs dispatched (cloud only)

Source `cc8a85336ef041b4be881765260a583333df5c25`:
- Cascade158 physical DRC/LVS/fault controls: **38689140829**, job116270766622.
- FinalV10 physical DRC/LVS/fault controls: **38689143416**, job116270774267.
- Hosted source audit / existing eight boundary-binding rejection tests: **38689145804**, job116270782686.

All three started successfully; no result accepted yet. Tight policy needs separate fresh extraction and composition bindings only after physical gates pass. Do not substitute existing nearest/left receipts. Existing long-running mainchip,32-stream and PLL jobs remain unchanged. Latest electrical failure and exact summary hashes follow below.

## 2026-10-15 — nearest-edge electrical rejection; cloud-only continuation

All work remains cloud-only; local workspace is empty. Permanent retirement receipt: release asset 636387277; supplemental log-cache retirement receipt: 642730081.

Nearest-edge runs 38687665533 / 38687675615 are complete. Compact nominal/hot/cold and wire nominal/cold pass their component gates. **Wire hot fails: 59/768 samples below 100mV; minimum 79.622008mV. Do not adopt this geometry or call PHY complete.** All exact source-summary hashes and capture coverage are in `docs/evidence/pcie-nearest-boundary-loaded-rejection-20261015.json`.

New opt-in `nearest_pair_tight` experiment removes only the 20um optional perimeter margin from real public metal extensions. Existing left/nearest profiles remain unchanged. Needs its own native DRC/LVS/fault controls, fresh RC, exact binding receipts and unchanged loaded-wave gates before any adoption. No new electrical profile exists yet.

Still active at this checkpoint: targeted193 mainchip route 38683404082; complete original32 wire capture 38679319167; actual845 PLL 1us 38674687038. No duplicate runs. After terminal PLL success, dispatch `actual_parent_acquisition_review_d2` as documented below. Mainchip final routing/timing and complete serial PHY remain open.

<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# NSSOC cloud continuation — 13 October 2026

## Latest cloud-only checkpoint — 14 October 2026

### Newest state — supersedes every older live statement below

2026-10-15T05:37:00.276361+00:00 — Actual nearest-edge loaded studies DISPATCHED: nominal38687665533 and hot/cold38687675615, both exact source195e045815f621ea9139b021054b835ae59245cf. streams4,physical_profile=cascade158_kelvin_supply_direct_nearest,physical_final=matched,physical_final_profile=v10_kelvin_low_ports_loads_shunts_series_nearest,clock_reference=stiff65,pre_bias=native_res,capture_transport=binary. Inspect allsix compact/wire x nominal/hot_low/cold_high component_screen_passed/full-device/interfaces/complete raw/original768samples/diagnostics before acceptance. If hot margin still fails, retain evidence and diagnose final-stage output/select routes; do not alter100mV or sample phase. Both nearest DRC/LVS/RC/compositions already proved and pinned in receipts below. This remains macro-loaded electrical study with ideal intermacro connections, not assembledtree GDS or fullPHY. Original32wire38679319167,PLL1us38674687038 andmainchiproute38683404082 freshly confirmedIN_PROGRESS; no duplicate. Cloud-only, fullgoalsOPEN.
Latest nearest-run snapshot: {"38687665533":{"status":"in_progress","conclusion":null,"head_sha":"195e045815f621ea9139b021054b835ae59245cf","html_url":"https://github.com/Melihakbulut221/nssoc/actions/runs/38687665533"},"38687675615":{"status":"in_progress","conclusion":null,"head_sha":"195e045815f621ea9139b021054b835ae59245cf","html_url":"https://github.com/Melihakbulut221/nssoc/actions/runs/38687675615"}}

Nearest-edge native composition38687126255(cascade158) and38687137631(V10),sourcee13385914fd95f34695aeeb77d15765edf13da11, both TERMINAL SUCCESS:54exactdevices,3871R/2592C and4018R/2648C. New source-bound profiles cascade158_kelvin_supply_direct_nearest and v10_kelvin_low_ports_loads_shunts_series_nearest have explicit nearest_pair receipt guards. Hostedbinding controls38686879945 passed8/8. Next dispatch tx-tree-physical-cloud streams4,study nominal andtemperature_voltage,these two nearest profiles,physical_final=matched,stiff65,native_res,binary. Preserve unchanged complete capture/sourcebits/100mV/device gates; no adoption yet.

Both crossed old/left-boundary studies38684711897/38684722524 now terminal and reviewed; full8case proof pcie-boundary-crossed-isolation-20261015.json. Boundary final with originalprestage fails64hot samples/min73.900497mV. Boundaryprestage with originalfinal passes/min102.765242mV. Additional margin regression implicates final boundarymetal; nearest geometry requires fresh electrical proof. Original32wire38679319167,PLL1us38674687038,mainchiproute38683404082 remain pending; preserve handles. Cloud-only; fullgoalsOPEN.

Nearest-pair native RC38686441891(cascade158) and38686449272(V10),source7336c71b, are TERMINAL SUCCESS and reviewed. Exact3871R/2592C and4018R/2648C;54devices,17conductors,112probes,no disconnectedprobes,allnative R/C/ownership/13corruptioncontrols pass. FullPEX/substrate/RF remainsunqualified. New receipts in boundary_nearest_variants of pcie-tx-cloud-composition-input-20261013.json; fullproof pcie-mux-nearest-boundary-rc-20261015.json. Next dispatch tx-layout-waveform-cloud.yml samecircuit/variant,boundary_pins=true,boundary_policy=nearest_pair,compose_only=true; then add explicit nearest profiles and run unchanged loaded nativebit/device gates. Wrong-edge receipt guard and8meaningful binding controls under hostedvalidation38686879945. Original-final versus boundary-final isolation38684711897 hot_wire FAILED64samples/min73.900497mV; secondcross38684722524 hot_wire remains pending. Original full32wire,PLL1us andmainchiproute remainactive. Cloud-only; fullgoalsOPEN.

2026-10-15T05:24:26.349220+00:00 — Nearest-edge fresh RC DISPATCHED: cascade15838686441891 and V1038686449272, source7336c71b3e261bfee3699e4e418efccc3e653132. Both use original circuit/variant,boundary_pins=true,boundary_policy=nearest_pair; keep exact handles. Physical source38685490747/38685502717 already PASSED original560-categoryDRC,54/54hier+flatLVS andallfive faults. Pin displacement reduced1788->1453.54um(cascade),1624.8->1294.755um(V10). New RC, policy-bound composition and original loadedbit/device gates still required; not electrically adopted.

Cloud source audit38686193086/sourcea54537ace1a9af33cba25014fceed6538683a6ff PASSED:70workflow YAMLs differ semantically only in storage-tag exclusion cloud-migration-* -> cloud-*; all other triggers/jobs/permissions unchanged; three native controllers compile. Permanent result642772543 SHAeed863ba01a033e320d6360729e4d9b1bb0cdf3755fbcc446560abb583aa114c. All70 unintended storage-tag runs are now terminal; no cancelled job remains active. Original manual closures were preserved. Crossed isolation38684711897 and38684722524 have completed compact controls and four wire jobs running at latest poll; inspect electrical summaries, not only Actions status. Original32wire38679319167, route38683404082 and PLL38674687038 remain live/pending. FullPHY/mainchiproute/finalsetuphold remainOPEN. All execution and evidence stay cloud-only.

Nearest-pair actual physical trials38685490747(cascade158) and38685502717(V10),source9abea439, are TERMINAL SUCCESS and independently reviewed: both560DRC categories/0markers,54/54hierarchical+flatLVS,no extraction diagnostics,allfive real faults rejected,unchanged schematic hashes. Actual12 public pins reach left/right edges with each differential pair retained on one side;total pin displacement reduced. Exact native receipts now in boundary_nearest_variants of pcie-tx-cloud-extraction-input-20261013.json; fullproof pcie-mux-nearest-boundary-layout-20261015.json. Next dispatch tx-layout-extraction-cloud.yml for samecircuit/variant,boundary_pins=true,boundary_policy=nearest_pair; no electrical adoption before freshRC/composition/original loadedbit/device gates. Crossed all-left isolation and original main jobs remain live. Source-policy audit38686193086 is separate. Cloud-only; allthree finalgoalsOPEN.

Cloud queue correction: retirement tag cloud-local-log-cache-retirement-20261015/source13d8cfc3 unexpectedly triggered70 old push workflows;50 nonterminal runs were selectively cancelled with all source handles retained in cloud-cache-tag-run-cancellation-20261015.json. Original manual PHY38679319167,PLL38674687038,route38683404082,crossed38684711897/38684722524 andnearest-layout38685490747/38685502717 were NOT cancelled. Broadening only70 storage-tag exclusions from cloud-migration-* to cloud-*; exact hosted readback must verify all other triggers/jobs/permissions remain identical, then compile three updated native controllers. Commit uses skip-ci solely to avoid automatically launching all70 edited experimental workflows; dispatch cloud-source-validation.yml explicitly for bounded validation. Native physical/electrical acceptance remains governed by original dedicated jobs.

Nearest-pair physical trials dispatched: cascade15838685490747 and V1038685502717, both exact source9abea4390d045dae5987513f81e0f27cad6a07b3, boundary_pins=true,boundary_policy=nearest_pair and original circuit/variant. These are NOT passed yet. Extraction/composition now carry explicit boundary_pin_policy and separate boundary_nearest_variants receipt tables. Old left-pin receipts cannot satisfy nearest_pair, including prepared same-job sources. Populate new exact receipts ONLY after native physical/RC acceptance, then dispatch with matching boundary_policy. No native extraction dispatch until receipts exist. Original left recipes remain unchanged and usable for control. All execution remains hosted; fullPHY/mainchiproute/finalSTA remainOPEN.

Prepared opt-in boundary_policy=nearest_pair for both exact cascade158/direct-supply and V10/low-ports-loads-shunts-series macros. Current all-left clock pins shift about204/242um; new generator selects left/right by minimum pair-total pin displacement, keeps differential pairs on one side and original local devices/metal/vias intact. Actual native generator asserts12 unique public ports, both bounding edges and reduced total displacement. Original left policy remains available byte-for-byte in generated geometry. No electrical adoption: run native560-category DRC, hier/flat54-device LVS and allfive fault controls, then fresh policy-bound RC/composition/full original loaded waveform gates. Crossed isolation38684711897/38684722524 and other original livejobs remain unchanged. All operations cloud-only. FullPHY/mainchiproute/finalSTA remainOPEN.

2026-10-15T05:04:06.958906+00:00 — Cloud-only continuation:

- Crossed boundary geometry isolation dispatched from b5e5eef858192bd578da6992af038936b54e7d1b. Run38684711897 uses original cascade158 pre-stage and boundary V10 final; run38684722524 uses boundary cascade158 pre-stage and original V10 final. Both use streams4,temperature_voltage,matched compact/wire,stiff65,native_res,complete binary capture. All original bit/phase/device thresholds unchanged. Inspect actual hot_low electrical summaries to localize the64-sample boundary regression before changing physical geometry. Green workflow alone is insufficient.
- Do not rerun healthy original32wire38679319167, actual845 PLL1us38674687038 or diagnosed193 packet-route38683404082. Native outcomes still pending in the snapshot below. After PLL terminalSUCCESS dispatch prepared actual_parent_acquisition_review_d2.
- Cleanup completed: workspace empty; all114 positively identified older project gh log-cache copies archived and verified in cloud before deletion. No local CAD runs or project scratch. Source and evidence edits stay on GitHub. FullserialPHY, routedmainchip and finalsetup/hold remain OPEN.

Latest run snapshot: {"38684711897":{"status":"queued","conclusion":null,"head_sha":"b5e5eef858192bd578da6992af038936b54e7d1b","html_url":"https://github.com/Melihakbulut221/nssoc/actions/runs/38684711897"},"38684722524":{"status":"queued","conclusion":null,"head_sha":"b5e5eef858192bd578da6992af038936b54e7d1b","html_url":"https://github.com/Melihakbulut221/nssoc/actions/runs/38684722524"},"38683404082":{"status":"in_progress","conclusion":null,"head_sha":"76c6abf20c047977a8b7cd7191a9c3d24d77b2dc","html_url":"https://github.com/Melihakbulut221/nssoc/actions/runs/38683404082"},"38679319167":{"status":"in_progress","conclusion":null,"head_sha":"09c6d7b56d2576174bcdf899cdd3766b60750364","html_url":"https://github.com/Melihakbulut221/nssoc/actions/runs/38679319167"},"38674687038":{"status":"in_progress","conclusion":null,"head_sha":"762c629d8e5124541fa40790348aad95b1a1c5b1","html_url":"https://github.com/Melihakbulut221/nssoc/actions/runs/38674687038"}}

Boundary PVT38682890173 is TERMINAL, REVIEWED and NOT ELECTRICALLY ACCEPTED: hot_low physical_wire fails64/768 samples at0.3UI; min72.616394mV below unchanged100mV. All device/interface checks and native diagnostics pass. Compact hot/cold and wire cold pass. Exact receipts and phase metrics in docs/evidence/pcie-boundary-tree-pvt-rejection-20261015.json. Next isolate original/boundary prestage versus final geometry with crossed profiles, preserving identical source bits, sample phases and limits; do not proceed as if boundary tree PVT passed. Original32wire38679319167, PLL1us38674687038 and diagnosed193 packet-route38683404082 remain pending at last poll; no duplicates. FullPHY/routing/finalSTA remain OPEN.

Cloud-only cleanup verified again: workspace empty, no local native CAD processes or matching /tmp and /dev/shm project scratch.114 older NSSOC gh log-cache ZIPs(8698739bytes) preserved in cloud archive642729726 SHA6b81f9a1ea21bf84d6a6f8f7cd91246083ff335ff40ae4cece0dbfae1e4ad1dc; all members read back and hashed before local removal. Receipt642730081. Two additional disposable recent caches were removed after verifying source runs38675957139/38676515641 remain hosted. Unrelated project caches preserved. Continue through GitHub-hosted execution and in-memory API edits; do not recreate local checkout or download native artifacts locally.

Corrected diagnosed-only packet-placement trial NOW LIVE38683404082/source76c6abf20c047977a8b7cd7191a9c3d24d77b2dc. Inputs prects_grt,packet_clusters=true,seed13,hold_depth0,fast_route. Must report cluster_scope diagnosed_193_only,193constrained packet drivers,all1216nets measured,unchanged native circuit/CTS graph and original strict route/STA gates. Previous all1216cluster trial38676325412 is TERMINAL FAILED366overflow and must not be adopted or re-polled as live. Boundary PVT38682890173 has terminalsuccessful compact jobs116251166023/116251166054; both real-wire jobs116251165625/116251165969 remain IN_PROGRESS as last observed. Need inspect actual summaries for electrical acceptance; green Actions alone is insufficient. Original full32wire38679319167 and PLL1us38674687038 also remain pending; keep exact handles. Cloud-only; fullPHY/mainchiproute/finalsetuphold remainOPEN.

Mainchip packet-cluster trial38676325412/source d2e5500f is TERMINAL FAILED andNOT ADOPTED: alloriginal terminals/CTS graph preserved, but globalroute366overflow(M2=7,M3=124,M4=60,M5=155,TM1=13,TM2=7), worse than222fresh unclustered and132older baseline. Freshplacement slowsetup-3.203514ns,fasthold-0.633695ns (not final extractedSTA). AllpacketHPWL289461->31050um,193diagnosed subset82472->5506um, yet broader congestion regressed. Summary642688125 SHAc4afbae56bc48cb7b415203939322ae081cc6a57ee87da03f4cb85a67caa711b;archive642687617 SHAd1ea671f531f8a869d593cb8f10b48e4db61898401339334792a421054f76f97. Preserved rejection pcie-packet-cluster-all-rejection-20261015.json.

Found and corrected guidance scope: prepare_packet_clusters iterated all1216packet drivers despite diagnosed193source selection. New code clusters ONLY exact193diagnosed drivers and eligible direct sinks, verifies no other packet driver is constrained, but retains every circuit object andall1216-net independent measurement. OriginalpreCTS,0.45density,GRT-driven placement,CTS policy,SDC,zero-overflowgate unchanged. Corrected trial not yet dispatched; use newer-postcts-cloud placement_profile=prects_grt,packet_clusters=true,routing_seed=13,ethernet_hold_depth=0,router_solver=fast_route. Do not confuse failed oldrun with a livejob. Boundary hot/cold38682890173,original32wire38679319167 andPLL1us38674687038 remain separatelylive as last observed. Cloud-only; goalsremainOPEN.

Boundary4:1 loaded nominal38682032573/source d793174f86896bc45d1cec68c4356e7751452382 is TERMINAL SUCCESS for both exact compact and real-wire models. All768unchanged original samples pass: compact min280.128mV, wire212.323mV; failed HBT/MOS none, all interfaces pass,diagnostics empty,69541complete0..34ns rows. Wire439.014s; summary642686458 SHA4e1895a3ec0cbc6cd49de802f7938c36f51ac90ad4c7427cb46d5f10d5004f78,archive642686051 SHA41ef94b04934b2784feac1a1120bbfafe64fd0c40fd3147c460f1a1ae98f683c. Complete receipt pcie-boundary-tree-nominal-20261015.json. No fitted phases or relaxed100mV/device limits.

Boundary loaded hot/cold PVT NOW DISPATCHED38682890173/source 6c3a2ebbbd63ff47f6e0ba4643b175ee03d65471: streams4,study temperature_voltage,physical_profile cascade158_kelvin_supply_direct_boundary,physical_final matched,final profile v10_kelvin_low_ports_loads_shunts_series_boundary,stiff65,native_res,binary complete capture. Requires allfour compact/wire x hot_low/cold_high cases. This is NOT assembled-tree routing, fullPHY, RF/substrate/ESD or chip timing acceptance. Next consume exact cases; only then choose actual intermacro wiring and fresh parent RC/waveform work. Original full32 binary38679319167 wire, PLL1us38674687038 and packet-route38676325412 each freshly polled {"38679319167": "in_progress", "38674687038": "in_progress", "38676325412": "completed"}. Preserve these handles, never duplicate healthy jobs. All work/cloud evidence stays hosted; local workspace empty; fullserialPHY/mainchiproute/finalsetuphold remainOPEN.

Original-geometry full32 binary38679319167 compact job116240000960 is TERMINAL SUCCESS:1253.728s,69541complete rows1449columns,604HBT512MOS,all768original samples pass,min279.845832mV,zero wrong/below100mV samples,all device/interface gates pass anddiagnostics empty. Summary642653591 SHAb0b3edd02cb30d16d6ebe64396868164b5faedbf6f09b16cc4c85d639d2312f2,archive642652691 SHAe540b22f8b7233f713554b7936f50db62a21596affc4d46e4a00d55016e7e457. Full receipt pcie-32-streamed-compact-nominal-20261015.json. Parasitic wire job116240001143 remains IN_PROGRESS; do not declare memory-warning repair or full32wire acceptance until actual clean wire result. Boundary4:1 nominal38682032573 compact also passed(component screen,min280.128mV); wire still live at last readback. Original and new boundary geometries are distinct. PLL38674687038 and chiproute38676325412 remain live. FullPHY/mainchiproute/finalsetuphold remainOPEN; all cloud-only.

Boundary-pin loaded nominal study38682032573/source d793174f86896bc45d1cec68c4356e7751452382 DISPATCHED: streams4, physical_profile cascade158_kelvin_supply_direct_boundary, physical_final matched, final profile v10_kelvin_low_ports_loads_shunts_series_boundary,stiff65,native_res,binary complete capture. Review both compact/wire native original256-bit/768-sample/full-device gates; no electrical adoption yet. If clean, run loaded hot/cold using same exact geometry and original thresholds before assembled-tree routing. Boundary physical DRC/LVS, fresh RC and native composition are complete and separately pinned below. Long original-geometry full32 binary38679319167, PLL1us38674687038 and packet-route38676325412 re-polled IN_PROGRESS; keep exact handles. After PLL terminalSUCCESS use prepared actual_parent_acquisition_review_d2; consume route congestion/STA from actual terminal reports. Full serialPHY, routedmainchip and finalsetup/hold remain OPEN. Local workspace remains empty; two transient gh log-cache files created by log viewing were removed, all project execution and retained evidence stay hosted.

Boundary native composition38681643271(cascade158) and38681651961(V10),source81c72cabe, are TERMINAL SUCCESS. Exact new54-device macro models and fresh RC pinned in pcie-cascade158-boundary-composition-20261015.json and pcie-final-v10-boundary-composition-20261015.json. Cascade3871R/2603C,wireSHA671cb02f8041b1ffeb8ec43c7085345a484058fd7c6719a45667dd6a5de91025; V104018R/2663C,wireSHA2692c7397405018c4fadfde7ad7abf5fbbcebcaa0fb313637a7e5bc7255a083e. Added exact boundary profiles and sourceflag guard; hosted tests reject validly hashed old/missing boundary geometry. Next run tx-tree-physical-cloud streams4,study nominal,physical_profile=cascade158_kelvin_supply_direct_boundary,physical_final=matched,physical_final_profile=v10_kelvin_low_ports_loads_shunts_series_boundary,clock_reference=stiff65,pre_bias=native_res,capture_transport=binary. Require unchanged all original bit/device gates; then loaded hot/cold. Do not call passing subblock physical/RC checks assembled tree or fullPHY closure. All cloud-only.

Fresh boundary-pin RC38681282542(cascade158) and38681293062(V10), source d872fd1838cba53ea97ba56cea2742a752da5248, are TERMINAL SUCCESS: actual3871R/2603C and4018R/2663C, respectively;54devices,17conductors,112geometry probes,zero disconnected probes; exact native R/C graph andall13actual corruption controls pass. FullPEX/substrate/RF qualification remains false. Immutable receipts/audits in docs/evidence/pcie-mux-boundary-rc-20261015.json. Native device/RC composition now supports boundary_pins=true with separate exact receipts and positive sourceflag guard. Dispatch tx-layout-waveform-cloud.yml for both original circuit/variant values, compose_only=true,boundary_pins=true; then review composed counts/hashes and run original loaded waveforms. New boundary geometries are not electrically adopted or assembled tree/fullPHY acceptance. Existing full32 original-geometry38679319167, PLL1us38674687038 and chip packet-route38676325412 remain separate; never restart healthy jobs. Cloud-only.

Boundary-pin corrected native trials38680600467(cascade158) and38680608797(V10), both source9e3323fd, are TERMINAL SUCCESS. Each has12 real public pins at x=0 macro boundary, unchanged schematic,560 DRC categories/zero markers,hierarchical andflat54/54-device LVS/no extraction diagnostics andallfive real faults rejected. Exact receipts/native gates in docs/evidence/pcie-mux-boundary-layout-20261015.json. Cascade summary642645428 SHA288b5c88a0626f46beea4cf3162b70b6f6c3a4fdcbc76436542fe71813713545, archive642645257 SHA1e4c2124b35a691a708e27d52d191bf91bb081e3066f3af025516337a2af7c2d. V10 summary642647876 SHA29ad642558ac980f2c831937b0cfe443ccc73f01d64b559aefa0f020c7d00307,archive642647771 SHA43f1073b689e1662db79bfd383c9a16d9659ac29c2b5db29118258a48e159041. Original failed V10 artifact permanently preserved as642644297/929624b1906214472f59794d7ce78e6f27798881d1dbfe3e1f06337104ce089a; proof642644376. Added boundary_pins opt-in extraction, exact separate pinned boundary_variants receipts and positive sourceflag check prevent reuse of old geometry. Dispatch fresh extraction for both samecircuit/variant plus boundary_pins=true; then bind actual devices/RC and original loaded waveforms before adoption. Intermacro tree routing, PHY and final chip timing remain OPEN. All execution/artifacts cloud-only.

Boundary-pin first trials38680041596 and38680055040/sourceaf836358 TERMINAL FAILED before DRC/LVS: new loop variable metal shadowed the generator metal() function. Rename only that local variable. Final-stage publication also exceeded80-character group limit; shorten new boundary groups to layout-boundary-{circuit}. Original final failure artifact11947829260 SHA929624b1906214472f59794d7ce78e6f27798881d1dbfe3e1f06337104ce089a is pinned for hosted permanent recovery before the corrected final trial. Preserve these failures; no geometry/physical acceptance. Original native PHY/route jobs remain separate and healthy as last observed.

Prepared real macro boundary-pin extension for exact cascade158/direct-supply and V10/low-ports-loads-shunts-series layouts. Existing LEFs put all12 public TM2 pins inside fully obstructed macro boundaries. New opt-in boundary_pins extends only those actual TM2 conductors to a common left boundary and regenerates pin shapes/labels/LEF. Original devices, local wires and vias remain; unchanged560-category DRC, hierarchical/flat54-device LVS and allfive reference/geometry faults decide acceptance. New RC and loaded waves are mandatory before electrical use. This is a prerequisite to actual intermacro routing, not fulltree/fullPHY closure. Not yet dispatched at this checkpoint. Current full32 binary38679319167, PLL1us38674687038 and packet-route38676325412 verified live; do not restart. Cloud-only, local workspace remains empty.


2026-10-15 cloud-only verification: local workspace has zero entries; no matching project scratch in /tmp or /dev/shm and no native CAD processes. Retirement receipt636387277 is COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE with all nine hosted archive-member proofs PASS. Do not restore a local checkout or run local CAD/tests.

Serializer same-circuit transport controls38677947291/source3381e29ac1f946bf5bf08aae4c37d3bd8e8e7755 are now TERMINAL SUCCESS for BOTH compact and physical-wire. Each compared all69541 time rows; compact166vectors, wire322vectors; no interpolation, fitted phase or omitted vectors, identical physical gate decisions and diagnostics empty. Compact summary642586262 SHA c88c4e0b13c768a3bc71dd5a53670c955ffcea19ef9bcb78b32d32e0d7522cd7. Wire summary642597494 SHA66d7f3197868eea4a3b2dda383fab130277b8f181a6b2ef219361959bdffaf6e; wire archive642596925/387194144bytes/SHAa0f56f758279e22cc44e3a44fc45cf5d5ca130f4868a3d5a8ba65be21b13f2bd. Both component_screen_passed=true; this is transport control, NOT fullPHY acceptance.

Following both controls, full32 nominal complete binary capture DISPATCHED: run38679319167/source09c6d7b56d2576174bcdf899cdd3766b60750364. tx-tree-physical-cloud.yml streams32,study nominal,physical_profile cascade158_kelvin_supply_direct,physical_final matched,physical_final_profile v10_kelvin_low_ports_loads_shunts_series,clock_reference stiff65,pre_bias native_res,capture_transport binary. Preserve all original probes/limits; no warning waiver. Consume both compact/wire native results and immutable summaries before acceptance. Do not duplicate. PLL original1us38674687038 and packet-cluster routing38676325412 remain IN_PROGRESS at this verification. After PLL terminalSUCCESS dispatch actual_parent_acquisition_review_d2; after route terminal inspect congestion/equivalence/timing. Full serialPHY, mainchip routing and finalsetup/hold remain OPEN.

Live same-circuit serializer transport control38677947291/source3381e29ac1f946bf5bf08aae4c37d3bd8e8e7755: compact job116235726705 native step03:48:39Z, wire job116235726902 native step03:46:26Z, both IN_PROGRESS as last observed. Both passed source-bit/fullcapture/publication/newstream-parser unit checks. This runs legacy then streamed capture on each exact4:1 compact/wire circuit and requires all native samples and physical gate decisions to match without interpolation/phase fit. Do not repeat or dispatch full32 until both transport proofs are terminalPASS. Then use tx-tree-physical-cloud.yml capture_transport=binary,streams=32,study=nominal,physical_profile=cascade158_kelvin_supply_direct,physical_final=matched,physical_final_profile=v10_kelvin_low_ports_loads_shunts_series,clock_reference=stiff65,pre_bias=native_res. Original full32 wire38496981217 is NOT accepted: all engineering checks passed but max-data memory warning remains in preserved evidence. New full32 must complete cleanly with all original probes/limits; additional PVT/physical intermacro wiring/PLL-CDR/fullPHY gates remain. Other live handles remain PLL1us38674687038 and packet-placement38676325412. Both were authoritatively re-polled IN_PROGRESS this turn. No local CAD/files; all operations cloud-only. FullPHY/mainchiproute/finalsetuphold remainOPEN.

Full32 physical-wire nominal38496981217 retains all engineering gates PASS (604HBT512MOS,768unchanged bit samples,min235.353mV,zero wrong signs) but component_screen_passed=false because native max-data memory warning. Added opt-in complete binary raw transport using the identical .tran parameters, sources, saves, startup flags and native models. Memory-mapped strict reader retains every original voltage/current probe and complete time row; no thinning/interpolation/phase fit or warning waiver. New capture_transport=control runs original wrdata and streamed4:1 same-circuit captures then compares ALL samples at fixed decimal-format bounds before a full32 binary rerun. Negative controls reject payload/vector/time corruption. Not yet executed at this checkpoint. PLL1us38674687038 and packet-placement38676325412 remain live; no restart. FullPHY/route/finalSTA remainOPEN; cloud-only.

Latest cloud-only live handles: actual845 original1us capture38674687038/source762c629d8e5124541fa40790348aad95b1a1c5b1/job116225492444 remains IN_PROGRESS; corrected packet-cone placement/CTS/route38676325412/source d2e5500f48fcba567d7d0d5089c69f16593b0c99/job116230651836 remains IN_PROGRESS in native controller (started2026-10-15T03:28:06Z). Do not restart healthy jobs. Review refactor regression38676594253/source3292e603 TERMINAL SUCCESS: exact prior50ns source/raw/235-terminal review still passes, zero reset-masked or missing output windows. Result642538625/690898bytes/SHA c78e0a42a7646bb29cb12518551d8ddb900904becb5e289d653ffa3335507776. Common checks38676515641 terminalSUCCESS:71migration tests+473serializer/cloudcapture tests, original acquisition negative controls and source/licence checks. These are not fullPHY/signoff evidence. After38674687038 terminalSUCCESS, dispatch actual_parent_acquisition_review_d2 (already implemented) against its pinned immutable source; do not launch it early beyond45min source-wait budget. Consume exact packet-route result/geometry/timing before adoption; preparation guard now33actual cells, every logical/physical/timing gate unchanged. Earlier38675957139 terminalfailed census guard preserved. FullserialPHY/routedmainchip/finalsetuphold remainOPEN. Local project stays empty; no CAD or artifact restoration locally.

Prepared independent actual_parent_acquisition_review_d2 stage for exact live capture38674687038/source762c629d8e5124541fa40790348aad95b1a1c5b1. Dispatch only after terminal nativeSUCCESS; review launches no simulator. Requires exact source/run1, release/archive digests, actual845 parent reconstruction, original35 model/runtime inputs, exact34-probe circuit/startup/.3125ps deck, zeroOP, complete1us raw and independently recomputed unchanged actual50 prefix. Reuses frozen100ppm/50ps/no-slip/VCTRL acquisition gates and controls; reports actual UP/DOWN/reset windows and cycle measurements. No full-device safety, PVT/CDR/jitter/PHY/mainchip acceptance. Corrected packet-cluster trial38676325412/source d2e5500f is dispatched; earlier38675957139 terminal preparation failure preserved. All execution/storage stays cloud-only.

Packet trial38675957139/source766001ea is TERMINAL FAILED BEFORE PLACEMENT: native exact1216-net/193-congested-driver checks passed, connected first-level cone inventory had min3/max33cells and exceeded the speculative32cell preparation guard. This guard is an optimizer-size bound, not a DRC/timing/equivalence requirement. Bind it to actual33-cell census; retain every member and all source/CTS/routing/STA gates. Failure summary642524962/41054bytes/SHAbc6cde8f57f8905b0690ff08e1f652dad2c71489c4207c8d139de8bdff66d1e1; archive642524742/101009304bytes/SHA099da1181137efdafd6c90b47dc85d557f35052b25240a8a9fc65730e5eb504c. No placement result or acceptance. Actual845 acquisition38674687038 remains separately running as last observed. Cloud-only.

Prepared a targeted mainchip placement trial while actual845 acquisition38674687038 remains live. Native preCTS inventory has1216 receive_ownership packet flip-flops;132overflow diagnosis identifies193 of their output nets in congestion markers. New --packet-clusters / packet_clusters workflow option binds those193 original output drivers and forms disjoint small connected first-level packet read cones from exact preCTS database. Native GPL placement_cluster_cmd receives exact dbInst objects, avoiding wildcard names. Requires every group2..32cells and unchanged source circuit; same0.45 GRT-driven placement, original CTS policy, all-terminal equivalence, original SDC and strict zero-overflow routing remain. Measures endpoint HPWL without calling it routing/STA acceptance. No new placement dispatched or accepted at this checkpoint; fullPHY/routing/setuphold remainOPEN; cloud-only.

2026-10-15 verified cloud-only handoff: local /home/hasanmelih/Documents/ChatGPT/nnsoc has zero entries, no matching project scratch in /tmp or /dev/shm and no local CAD processes. Final retirement receipt636387277 remains COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE, with hosted archive-member verification. Actual845 original1us acquisition IS NOW LIVE: run38674687038/source762c629d8e5124541fa40790348aad95b1a1c5b1/job116225492444; native step started2026-10-15T03:08:55Z, last observed in_progress. Common checks completed success. Monitor this exact run; do not duplicate/restart a healthy computation. Consume its immutable release summary/archive after terminal completion; require full1us coverage and unchanged first50ns control before separate lock and safety review. No long-capture result accepted yet. Full serialPHY, mainchip routing and finalsetup/hold remain OPEN. All source, simulation, CAD and retained artifacts stay on GitHub-hosted infrastructure.

Actual845 native50 run38672412524 and independent raw/source review38673633192 are TERMINAL SUCCESS for finite capture/review scope. Native1003.714907947s,160072complete rows496columns,zero-sourceOP exactly0V,no execution diagnostics. All8 observed PFD clock edges unmasked and output responses present. Native summary642469457/792012bytes/SHA1d0e5874f38e796ba3391d575b70a2bb370e0a9e5500013a161b6212016393b5; archive642468819/563519069bytes/SHAfe8d9619f48add85c9819c86cf3f86a2efefeef9e26beec862e7ad995cb17752; raw635182699bytes/SHAd7b7b81a0ed4c34bbaf3a51321943bf5734c43e4d23a819d045d065d180cfd43. Review642472279/690520bytes/SHA9289b0d21c73efc89ef0b9acac30e43ef6212d66780f5d9bf2bccfefea599003. Measured PFD maxima|Vgs|2.617292V,|Vgd|2.591362V,|Vds|2.822054V; these are measurements, not foundry reliability acceptance. Added actual_parent_acquisition_d2 fresh original1us mode: same845 source,8648 wire records,32models/3OSDIs/startup/.3125ps/tolerances, original24+9 PFD logic+sharedbulk=34selected vectors. Gates on verified finite review, preserves full raw, compares unchanged first50ns against reviewed raw under existing1mV/1ps method bounds without phase fitting. Native budget20800s before6h runner limit; measured linear estimate20074s is not guarantee. All-device safety is NOT claimed by selected probes. Long capture not yet dispatched. FullPHY/mainchip routing/finalSTA remainOPEN, cloud-only.

Actual-parent review is now a hosted dependent stage: it polls only fixed source38672412524/head8220cbf898d97d311b5438f2f799385d7aef7af7/attempt1 at60s intervals and proceeds only after terminalSUCCESS. A45-minute review wait cap leaves archive-review time within the60-minute job limit; expiry does not cancel/restart native capture or accept partial data. Native capture remains live as last observed. Dispatch actual_parent_review_d2 once; do not duplicate either healthy job. Review verifies raw/source/model/terminal results and observed PFD response windows. FullPHY/routing/finalSTA remainOPEN; no local files.

Prepared actual_parent_review_d2 for the still-live capture38672412524/source8220cbf898d97d311b5438f2f799385d7aef7af7. Review requires terminal SUCCESS, exact source/run attempt and SHA-bound release assets before reading raw. Reconstructs the exact accepted845 parent and deck, original35 model/runtime inputs, all235 terminal differences, every recorded vector's rise/fall/min/max and reset masks. Adds observed reference->DOWN and feedback->UP response windows using fixed1.25V logic observation; already-high outputs are recorded, no fabricated lock/PVT/safety threshold. Do not dispatch until native capture is terminal successful. FullserialPHY/mainchip routing/finalSTA stillOPEN; cloud-only.

LIVE actual-parent native50 continuation:38672412524, source8220cbf898d97d311b5438f2f799385d7aef7af7, job116218353728 (pll-snapshot actual_parent_d2_rc), last observed IN_PROGRESS in native-capture step started2026-10-15T02:43:15Z. No result/acceptance yet; monitor same handle, do not restart from observation timeout. Capture uses accepted actual845 composition38672085461, explicit845 subcircuit and recomputed235-device terminal probes with common bulk at a_count_vss. Native32models/3OSDIs, originalstartup/zeroOP, .3125ps maxstep and tolerances preserved. After terminal capture consume cloud-results-38672412524-1-pll-pfd-actual_parent_d2_rc summary/archive, verify parent SHA91364a351fad4d376e6d168d85af6f63ff4076bfecd5af83192492bc514073fc, complete50ns raw coverage/diagnostics, actual clock/reset behavior and measured235 terminal stresses. All earlier graph runs terminal;38672085461 is the accepted exact graph/control result. Full845 safety/1us acquisition, substrate/RF/PVT, fullserialPHY, mainchip routing and finalSTA remainOPEN. Cloud-only; no local project files created.

Actual845 composition38672085461 TERMINAL PASS: complete3906-vertex/5474-edge bijection with17 fixed public ports, all845 native devices, ten physical macro ownership classes, source-proven9648-record native alias translation,8PFD child planes and82 unchanged parent anchors. All6 actual graph faults and7 component/RC corruptions rejected. Solver0.01699688s; same circuit SHA91364a351fad4d376e6d168d85af6f63ff4076bfecd5af83192492bc514073fc. Summary642423642/287518bytes/SHA22cae097bdb7c2a3fa77abaad4ebeff772fb08c1769c1e4fc10664f90f1e6f35; archive642423511/11295468bytes/SHAff8837dce9298abd8cb649eceb5b86dcd8e48454d7175002096b4b5b80a4205b. Added actual_parent_wave_d2/actual_parent_d2_rc to restore only this pinned accepted composition, explicitly instantiate845 subcircuit, regenerate all235 actual PFD terminal probes after shared intrinsic bulk binding and run50ns original32models/3OSDIs/startup/.3125ps/tolerances. Capture also records235 terminal voltage differences; no invented reliability/lock acceptance. Native actual-parent capture not yet dispatched. FullserialPHY, qualified substrate/RF, full845 safety/PVT, mainchip routing/finalSTA remainOPEN; cloud-only.

BLISS38671625931 produced exact3906-vertex/5474-edge/845-device bijection in0.016222392s, independently checked all labels/edges/inverse;129-vertex symmetric positive and nonisomorphic/wrong-color controls passed. Overall run FAILED because reset_bypass fault used obsolete canonical a_count_reset_b, so added a dangling wire instead of mutating actual counter_reset_b. Preserve summary642415315/285692bytes/SHAe54ca91ecbddf10abe13c9babe3904dd1d0d75cf9a27367d20889344c6f3d2d1; archive642415063/11294715bytes/SHAf076b1c84d5fc82a3a9976ffdcff76967a4fa56c1a12abd24d114521ff0079fc. Corrected fault through source-proven alias dictionary and require both endpoints already exist on separate measured metal components before short injection. Rerun all6 graph and7 component controls before accepting composition. Earlier macro-owned VF2++38632663091 also terminal cancelled by explicit6h annotation; summary642406167/85138bytes/SHA36dbb8c1e7c4e1c1fd4845cc3c9f1f5d894e6b76fb4d6073cf2ee33701df7971; archive642405999/11266889bytes/SHAd35646c0ef1c790917d27ac4068aae08265a0177b7476b904e3b7c7df9ee3f93. FullPHY/routing/finalSTA stillOPEN.

2026-10-15: both previous exact-graph runs are now terminal CANCELLED at hosted six-hour job deadline, not accepted:38631335585 and38632663091. No manual restart/cancellation. First preserved result642384794/84940bytes/SHAcc56ac01c5d5f0d8ef4458ef3000185fbbc30a46b41884147a7ad9964c384dde, archive642384551/11267062bytes/SHA553027705695200d84df26c97d223f8ce815267c4b8ac3f88ceca4c7f55ac885. It proves exact9648-record bijective source alias translation and corrected324/324 intrinsic nets with all324 net signatures matched (3906 graph vertices each); no complete bijection was produced. Replaced only exponential VF2++ search with pinned igraph0.11.9 BLISS; retains all macro/model/geometry/terminal/public-port labels and independently rechecks every returned label, edge, vertex and inverse mapping. Added symmetric positive and equal-degree nonisomorphic/wrong-color controls. Physical graph/RC gates are not relaxed. New cloud dispatch required; fullPHY/mainchip routing/finalSTA remainOPEN.

LIVE HANDLES (do not infer failure from observation time): general composition38631335585/sourcef01b815fa7edfbb3056eed2edb01145043832b6e/job116083446385 and stricter physical-macro-owned composition38632663091/sourceadb67efda60521b56cf1230388bd043d4a22103c/job116087929177 are both IN_PROGRESS in the composition step as last observed. No new native waveform has been dispatched. Next: consume exact result/archives; only after PASS_ACTUAL845_PARENT_COMPONENTS_REFERENCE_PLANES_AND_EXACT_INTRINSIC_GRAPH_NOT_ELECTRICAL_ACCEPTANCE and all6 graph/7 component faults, pin the resulting actual parent845.spice and launch actual-parent (not old frozen fixture) native capture with original32models/3OSDIs/startup/.3125ps/tolerances. Public subcircuit changes nssoc_parent865_wire_v1->nssoc_parent845_wire_v1; update testbench instance explicitly while retaining original18-port order. Recompute all235 PFD terminal voltage probes after common-bulk binding; old private xpfd.n_1 probe is absent, use actual a_count_vss. Full-device safety/1us acquisition/PVT and qualified substrate/RF remain separate gates. If graph search remains expensive, use all25 physically proved parent logical conductor identities (83 anchors), not only17 public names, as additional fixed interface labels; require one-to-one physical conductor/alias mapping, never merge disconnected nets or weaken equality. Local project stays empty; all execution/data cloud-only.

Run38631335585/sourcef01b815fa7edfbb3056eed2edb01145043832b6e/job116083446385 remains IN_PROGRESS in composition as last observed, not failed and not restarted. Added a separate stricter graph proof using actual ten-macro ownership from native physical parent: same845-device geometry, all terminal roles, fixed17 public pins and wire preservation remain mandatory; devices cannot permute across physically distinct macros. This should reduce symmetry search without weakening equality. A new comparison may run alongside the original; retain both outcomes. No electrical/native waveform launch until exact composition accepted. Cloud-only/local-empty policy continues.

Diagnostic38630092629 rejected composition: intrinsic geometry/model census845 matches;316 net signatures match, but8 expected internal nets split into16 actual nets (324 expected versus332 actual). AllPFD8planes pass. Summary641533963/173069bytes/SHAa7a2c77d9ab3200a0b6917a1da28d22a2dcf920e250c40811104c5463237ceeb; archive641533777/11152370bytes/SHAc12bb0d380c82e3e9b51de83a4e18021a577d158278c5703e4204f3fe401cc4c. Suspected cause: existing native865 fixture uses diagnostic aliases bp,bn,qp2,qn2,clk,count,countb,counter_reset_b,releaseb while replacement parent RC uses canonical A_* physical anchors. Added strict full-record proof against original canonical model29 parent865 source SHA802c93c1a4ebf492133a2873f04c3f3e898323166d630328bb3864a18bfbe31a. Require same9648 record IDs/parameters/wire values and bijective node-only translation across all records before applying aliases to fresh parent RC. No invented wire/zero-ohm bypass or relaxed graph check. This correction awaits cloud execution; fullPHY/routing/final timing remain OPEN.

Actual845 composition38629414547 terminal FAILED exact intrinsic graph node count. All845 model/geometry census and all8 actual PFD reference planes passed;610 other devices/remaining macro RC unchanged. No electrical simulation or acceptance. Failure summary641525193/83920bytes/SHAb9bfaf7100a46f93e97cbfdfc3eb076e21421695f62a2d167c43bc550307737d; archive641524983/10993881bytes/SHA2924aff6c03b626052692a7fc3fe7a923d0a3f4b3e17d9152bb6d6bfcf2e0024. Added exact unmatched-net diagnostics without weakening the comparison, to locate actual remaining topology/body discrepancy. Prior38628841198 was cancelled while still queued because its reader used wrong cap_cmim arity; no native capture was interrupted. Current next action: rerun composition diagnostics, fix identified connectivity/source representation only with physical proof. Full PHY/routing/final timing remain OPEN; cloud-only.

Run38627542372 TERMINAL PASS: fresh parent RC at exact original child planes,98R242C,25components83probes, all native R values and point/mutual capacitances preserved,8 actual corruptions rejected. Summary641488381/82087bytes/SHA908ab5606c70576588cc74fb376cc9daa67b34bf4dd0ea10ca9c2cc519fbb0dc; archive641488135/10655669bytes/SHAbd8cea7f0532921ee4566d6b8b8e7dc4ebe2b132b62e3ea088b8a68d9839ff09. Fresh wire netlist SHA532a9c30daca2554f7aaa97dcac7c9fac7db25f3755ea4749d9841ddcb5f0cf6. Added cloud parent_compose_d2: restore exact native845 reference, original865 source and new235 PFD; verify eight child physical planes, bind intrinsic PFD bulk only at existing ideal common reference, replace old parent RC, prove unchanged610 devices/remaining macro wires and exact845 intrinsic graph with17 fixed pins plus actual fault controls. This composition is not yet executed or accepted. Full serial PHY/mainchip routing/final timing remain OPEN. All durable files and execution are cloud-only.

Cloud-only continuation dispatched: run 38627542372, request d2-parent-exact-planes-rc-20261014, immutable source e9af58aa6ee849cbe4f18c9467c5f1d6fd0ae61f, native job 116070434777. Last observed IN_PROGRESS; monitor this same handle before any restart. It extracts/audits fresh parent RC at the verified original child reference planes from successful run38626309896. Syntax compilation of the exact remote controller passed without local files. Local /home/hasanmelih/Documents/ChatGPT/nnsoc is empty; no matching project scratch in /tmp or /dev/shm and no local CAD process observed. All CAD/tests/result archives remain on GitHub-hosted runners. On completion retain exact summary/archive hashes; only after native RC and eight corruption controls pass, proceed to full actual845 composition/body/reference-plane proof and electrical capture. Serial PHY, mainchip routing and final setup/hold remain OPEN.

Verified cloud run 38626309896 PASS: actual845 parent has 25 wire components and 83 anchors; 82 original anchors preserved, only moved A_pfd_reset changed; all five reset-release child reference planes exactly match the archived child RC model (VDD/VSS x=0.390 um). Two physical/logical corruption controls rejected. Summary asset 641472564 SHA256 608b16457b8d9500d13a7b60011aa018af1c25369093b10bb50f057679b5684d; archive asset 641472366 (4612750 bytes) SHA256 8ffebb42b9a959ed9c6c18ed9813873c4e92a4c3c2080945e366e677680e1e2a. Updated parent_rc_d2 to this exact capsule with explicit plane-proof checks. Next: fresh cloud RC/raw audit, then actual845 composition and electrical verification. Earlier 38624211966 RC remains evidence for its different planes and is not composable here. Full serial PHY, mainchip routing and final timing remain OPEN. Local workspace remains empty; all CAD execution and durable project data stay in GitHub.

- Recovery38624930704 terminal FAILED only final optional assertion No original composition recovered;614sources were restored and checksum-verified. Preserve23,052,321byte summary641442176 SHAe3482fbcaccf9315236b5b47451e1bb0488ca054dc5e3f9299795f03f8ff227e. It contains the needed original parent83anchor record SHA5b126d7155fd56110f0ed4444c50f0a999ce0f68c20b2e7993afa180769c39b1 and release rebound child anchor record SHA0aaa81bacda8b3a843f469d34a585bf1741bf26e78170e7457fe760a266052e4.
- Found real source-plane discrepancy before composition: original release108 child model VDD/VSS are localx0.390um, while the automatic overlap selector chose0.535um. Changed exporter to prefer exact archived reference points for every unchanged macro, requiring them inside each actual pin and on real parent metal; no arbitrary zero-ohm bridge. Require82/83parent anchors identical to original (only PFD reset moved), and all5release planes exactly match rebound child model. Fresh native binding and RC rerun are required; prior98R242C remains valid only for its own0.535um planes.

- Fresh parent nativeRC38624211966 TERMINAL PASS:25conductors/83probes,98R242C, all native R edge/value records and per-point/mutualC attachments exact, no isolated probes, all83grid deltas0. Eight actual raw/anchor corruption controls rejected. Summary641424496/79361bytes/SHAf8877528a5fd89af965ba82fb7be8b9575158c634bca5161f3ee764a9da28d28; archive641424125/8511159bytes/SHA8c170797c9a1172126803c31a6bc05656ebe37c76dd9fdeae5638ed0e22bbec3. wires.spice14871bytes/SHAee3a3ff8124707c5c8fa80dd2b49c28a56d51cc6c6367049c3bcfdf97e7b35e7.
- Composition must prove reference-plane matches, especially counter VDD/VSS atplacedx2580.390um and release VDD/VSS atx2580.535um. Added archived reset/release/rhi140/PBUF10 model/anchor recovery; no connecting distinct physical positions by an invented zero-ohm shortcut. Parent freshRC is unqualified metal extraction, not RF/substrate qualification or electrical/PHY acceptance.

- Parent-wire binding38623406807 TERMINAL PASS:25actual conductors,83anchors (66macro+17public), all parent-only metal/via polygons bound to native845-device LVS; reset-open and wrong logical reset mapping rejected. Source summary641409182/55459bytes/SHA7d2b48d8abe17db8e4b8243f9ed10de36ddcf1de7862c0cde7e53ba90ad1d512; archive641409027/2465615bytes/SHA001843bd6a160f987a7e8d55351a4e6cd75f07845b6684886ec93241ca4ef241. Physical wires GDS06ecd9616f23ba7d2e76d28293720494d10ba73a9c9c7cdd72fe262ff0133afb.
- Added fresh parent-only Magic extraction from that exact source with pinned runtime/raw parser; adapted recovered parent audit only for verified25conductor/83anchor census and hosted paths. All native R values/topology, individual pointC/mutual attachments, collapsedC and source ownership remain required. Eight actual raw/anchor corruptions must fail. No old parent RC reused and no electrical acceptance claimed.

- Current live native continuation: parent-wire binding38623406807, source6a7227840f2d191dff713fb743a7a64bc2b5b9ac, job116056406564. Native runtime preparation confirmed in progress. Uses actual pin/parent-wire overlap for release power anchor. Do not restart from an observation timeout. All earlier D2/parent physical runs are terminal.
- Last completed engineering result remains actual845-device PLL parent physical PASS38622111375 (560DRC categories; hierarchical9Match; flat845/845; two real faults rejected). Next: consume38623406807; if binding passes, extract fresh parent-only Magic RC, audit native R multiset/each pointC/mutual attachment against physical conductor ownership, retain raw fault controls, then compose D2child RC with actual parent and explicit shared substrate reference. Full serial PHY, RF/substrate qualification, acquisition/PVT and mainchip routing/finalSTA remain OPEN. All computation and archives stay on hosted runners; local project remains empty.

- Parent-wire export38622802741 TERMINAL failed at A_release_VDD anchor: declared pin center is not on parent-only wire geometry, although native parent DRC/LVS passed. No RC extraction ran. Retained summary641398468 SHAfc39bb1a79ace5e96c6b0e922f078f4d1868d6872592f331b1a1125e1e5cd43b and archive641398233 SHAe4a2daa15c55249fe80c2b4ff13f32bb966c18df17c6967e0f7f2f63030b9a61.
- Fixed read-only anchor selection: preserve usable preferred points, otherwise require actual intersection of declared macro pin rectangle with native parent metal; choose native5nm-grid point inside intersection, bind to both parent-only and full845-device native net. Record each moved reference point and require child-model reference-plane rebinding before RC composition. No geometry or connectivity edits, no nearby-point guessing, no relaxed LVS.

- Actual D2 PLL parent review38622111375 TERMINAL PASS. SameGDS560-category DRC preserved; new hierarchical9Match and flat845/845LVS passed with strict17parent-pin readback. Reset-open and wrong-width faults rejected; hierarchical port reader1positive+4negative controls passed. Summary641387744/171863bytes/SHA aabb9a94912402ca8ed27443fe8b380989d7724dd44d1e106140ab7e59e05f8b; archive641387561/2426976bytes/SHA7456fa988f5fd399a03e23d570ad3a11ade32f4ec7a101a7200aab382d9345fb. First wrapper failure38621210521 remains preserved.
- This is now actual replaced PLL parent geometry, not the earlier frozen electrical fixture. It does not establish fresh parent RC, electrical acquisition, full PHY or mainchip timing. Added native parent-only wire exporter: exclude all ten child macro geometries, bind every remaining metal/via component, macro pin and public pin to actual845-device flat LVS; reject removed reset bridge and wrong logical reset mapping. Dynamic component census comes from all actual declared parent/macro nets, not old753hardcoded24.

- Actual parent integration38621210521 completed native physical work:560-category DRC PASS; hierarchical LVS9Match including235-device PFD and845-device parent; flat LVS845/845PASS; actual reset-open and wrong-width faults rejected. Overall wrapper FAILED solely because standalone extracted_ports() rejects multiple .subckt headers. Failure retained: summary641372647 SHA36211fa13eaedc0fa1b6f662d9d7ff5e52403c371f297aa7192b6ab1b70a2d6f; archive641372470 SHA6ceb0027c22cb56116f7ac1f7ab53e85b94fcfcf37de346dd28e1eb381fc141a.
- Fixed parent port reader selects exactly the named parent from unique subcircuit headers, retains duplicate/missing/continuation rejection; one hierarchical positive and four malformed controls. Prepared saved-state review: no geometry regeneration, reuse exactGDS DRC and rerun strict LVS/actual fault checks with corrected reader. Native parent GDS2259e98c77af6c4385248025a60b7af332fe656c52094c33ef18c5d7692a4ee0; flat331ade3dfd49caf0af25c76d1bdf3004f7337dbf28d0755db527820e7241de8a; reference6de9c745fa2911ce732d1f772b28ac8147b476690d97152266c3554bd02d800d. Parent RC and electrical qualification still open.

- Actual D2 parent integration prepared from immutable interface capsule38619621840. Replaces PFD102 child with PFD94D2 using collision-free imported child names, preserves seven pins/all other child cells, adds one real0.6um-wide Metal5 reset bridge atx200.7..201.3,y1283.53..1440.93um. Restores the old parent's ninth BULK reference port without changing the existing parent node mapping; strict native LVS must prove substrate connectivity. New845device parent must pass560-category DRC, hierarchical and polygon-identical flat LVS; actual missing-reset bridge and wrong-width faults must fail. No claimed physical success before native results, no local files or tools.

- All native handles from this checkpoint are TERMINAL: D2 waveform38616009542 and independent review38619029764 succeeded for their stated finite-fixture scopes; D2 LEF38617744218 passed; parent interface38619621840 passed read-only inventory; fresh-CTS route38598795406 failed222overflow and diagnosis38618268577 completed. Do not poll or restart these as live jobs.
- D2 independent terminal review: result641332469,688943bytes,SHA ddbe9bfc61e50f93dd339e37241f39f5b1fdfe501ef0575e464c4334b0d07945. Exact source reconstruction and all235terminal review passed; max|Vgs|2.6180595V,|Vgd|2.5907854V,|Vds|2.8224231V,largesttapdrop0.03382789V. These are measured values, not device reliability/PVT qualification.
- Actual parent interface38619621840 source dd0c2fc3: summary641343786/179917bytes/SHA ee6fa848a5a5b34e150b300f7865b43c5d39846c72873d6b1909688222c1071b; archive641343598/255244bytes/SHA a84187f9fb911e8dc181d1ea38af394db0df5ec898ed4570e8fd6aa3203d82fc. Archive retains exact parent23 GDS/reference/result and exact D2 GDS/LEF/reference under hw/soc/out/cloud-pfd-layout/{parent,layout}; use this small verified capsule instead of downloading batch000001 again.
- Physical integration finding: original PFD is nssoc_pfd102_layout_v1 at r0(200,100), old654x1384.03um versus D2 654x1240.03um. Seven physical port positions match. Only reset moves from localy1340.63 to1183.83um (placed1440.63 to1283.83um); parent reset route must be reconnected and freshly checked. Parent Xpfd maps ref->fb,fb->ref,reset->reset,up/down unchanged,vdd->div_avdd,vss->avss,sub->sub,BULK->avss. Preserve intentional clock polarity and prove shared substrate binding from new native extraction. No parent replacement or new parent RC has occurred yet.
- Next engineering work: actual parent GDS child replacement with collision-free child names, reconnect moved reset, update reference without changing other devices, strict parent DRC/flat+hier LVS and fresh wire/body extraction. Then electrical capture using actual new parent; do not promote frozen fixture to parent acceptance. Mainchip routing222overflow and final timing remain open. Cloud-only operation and local cleanup remain in force.

- D2 native run38616009542 TERMINAL capture success: 50ns,160072rows,496columns,985.85s, no native diagnostics, original startup/OSDI/models/.3125ps retained. All four reference and four feedback edges after12ns have clearb>1.25V; DOWN responses occur at15.215,25.240,35.231,45.224ns. Previous24ns missed response absent in this finite nominal fixture. VCTRLmax0.593526V; no lock/PVT/full-PHY acceptance. Source summary641321586 SHA2295758b7673f6a640682a349494a0d43f100c7df22e9bb384964f154476360b; archive641320746 SHA3e26bdede22f9023cff3baaee219c391e04d87e1158b95d85d4955cf2603e292.
- Independent D2 source/waveform/terminal review38619029764 live (source068d23e7). Fresh-CTS diagnosis38618268577 COMPLETE:122native markers,total222overflow, geometry and all congested endpoints bound; four Ethernet SRAM hotspots persist. Diagnosis summary641320687 SHAcd819ccc22a235732f03084433fe448b1f13dd741d58e84502339b672c76078b.
- Added hosted exact parent23 GDS/reference versus D2 GDS interface inventory, prior to any actual parent replacement/shared-bulk/RC work. Pin locations and body interface must come from native data, not from the electrical fixture.

- Completed D2 native LEF run38617744218 PASS: exact eight pins/outline/use/direction/seven obstruction layers plus missing-pin and blocked-pin actual faults; summary641310743 SHA c5a556c4d7ecc54422e27da990c6493eabba10bb1d36184e254e9e759c169014, archive641310447 SHA9c91dde4eb98d1cca7671efb4776dfb370948a70eeb44beb5083166de509a7b5. This is macro interface evidence only.
- Live native handles: D2 waveform38616009542 (sourcee0bd3db2); read-only fresh-CTS congestion diagnosis38618268577 (source294ea6f0). Added independent D2 waveform review, to dispatch only after exact native completion; no repeated native simulation. Old run38598795406 remains failed222overflow.
- Cloud-only cleanup rechecked: local project directory0entries, no project scratch in /tmp or /dev/shm, no local OpenROAD/ngspice/KLayout/Magic/Netgen/Yosys process. All new source commits and results remain on GitHub.

- D2 native LEF check38617744218 dispatched from d76daf7ee30196bad6cec93c66adc5e5f86a709b. D2 native waveform38616009542 remains live. Mainchip route38598795406 is TERMINAL, not running; added a read-only native diagnosis profile for its exact failed ODB and congestion report before choosing another physical change. Fresh-CTS placement-estimated slow setup -2.876039ns and fast hold -0.624604ns are failures, not final extracted timing. No unchanged reroute launched.

- Cloud-only continuation: D2 PFD native run38616009542 remains in progress. Added exact D2 GDS/LEF native interface verification using completed physical run38614342619; checks retain all eight pins, outline, use/direction, seven obstruction layers and two actual missing/blocked-pin negative controls. No local files or CAD runs.
- Fresh-CTS mainchip route38598795406 completed with failure: actual FastRoute overflow222 (M2=1,M3=31,M4=26,M5=153,TM1=7,TM2=4), source9d904ed0. This is worse than earlier132; rejected, not final routing/timing closure. All logs and partial state retained in release cloud-results-38598795406-1-route-prects_grt.

**Newest live handles — doubled-drive native capture and mainchip route only.**
PFD native38616009542/job116031150471 (aoi4_d2_rc), sourcee0bd3db29bd0bcc3b840da4e0334419bff5c128a,
observedin_progress at requested-native-capture step. Commonchecks116031150251
completedPASS. Preserve exact run; no observation-timeout restart. Compare
full50ns native reset recovery against failed originalaoi4_rc38610259816,
then inspect all235terminal waveforms and full-device/PVT/acquisition needs.

Earlier original native38610259816, terminalreview38613111364, parentmethod
recovery38612960848, D2physical38614342619 andD2RC38615210714 are ALL terminal.
No earlierPFD job remainslive. Their source/failure/pass evidence retained.
Route38598795406/job115972338767 remainslive in exactpostCTS routing.
FullserialPHY/newparentlayout/routedmainchip/finalsetuphold remainOPEN.
All workcloud-only; no local workspace artifacts or CADprocesses.


**Doubled-drive PFD freshRC38615210714 PASS; actual native capture prepared.**
New235device layout yields715R1177C (not old716R1178C),53conductors/431anchors;
all8binding+13rawRC+6composition faults passed with preservednativepoints.
Summary641264393 SHA1df255b18e5fed6df0c3ad4470dcd0e6afd339727d9cfd2e0b4c0fbf6f23a82d;
archive641264152/6788161bytes SHA1d3eb4cf985251b4c5eac6e451ce720b713c5758a6ed4edea28688907efeb86b.
MacroSHAa0ace2729326fd774bb40e8c60bcb7a817cada4036308a9b6bb0a4ebf347248c.

Use pll_pfd_stage=physical_wave_d2 for actual845device fixture with freshD2RC,
original610otherdevices/nonPFD RC, exactmodels/OSDI/startup/.3125ps/50ns.
Unique94MOS topology against shared D2generator, reversibleterminaltranslation,
all235device terminalvoltages and resetmaskevents required. No waveform/lock
or newparentlayout acceptance inferred from DRC/LVS/RC pass. Originalaoi4_rc
source38610259816 and its failedreset behavior remain preserved. Newparent
physical/commonbulk reassembly stillrequired; mainchiproute38598795406 live.
Allworkcloud-only; fullserialPHY/routedmainchip/finalsetuphold remainOPEN.


**Doubled-drive actual PFD94 layout38614342619 PASS; freshRC prepared.**
560DRC categories/zero markers, hierarchical+flat235deviceLVS and allfive
actual physical/reference faults passed. Same94MOS topology with88DFF W*2,
AOI6 unchanged. GDS0451b81b8f73a8f1c4e2923e5f50d26cf3c09ad2c3a77ebd0f08acc864e1e08a;
LEF6a94d26e4a0803f80d661b116d5df91a76b1887ee763375664f28961d5a9d89e.
Summary641251925 SHA35841da91016821cb48937bc408bff5d70357b221da42b2ea36ef3cf2aa2ab20;
archive641251736 SHA9e3de73d250ba223b093f44c55e91c1e7327f8487c8d185b96f2350104e45210.

Run pll_pfd_stage=rc_d2 to bind actualnew235device GDS/LVS and extract itsown
new metalRC with unchanged8binding/13rawRC/6composition faults. Geometry
census/top/hash pinned; R/C counts derive from new extraction, never copied.
Then source-bound native84550ns with newRC and fullterminal review before1us.
Originalaoi4_rc still has proven reset/clock recovery failure; do notadopt it.

Parent recovery641221741 contains152sources; latestparent865 actualparent23
GDS/commonbulk source confirmed via parent18.py/reference23.py/review28.py/
compose29.py. NewPFD parentreassembly/routing/PEX stillrequired. Mainchip
route38598795406 live; allworkcloud-only/fullPHY/finaltimingOPEN.


**Actual PFD23550ns capture/review complete; reset recovery still fails functionally.**
38610259816 nativecompleted1030.661s,496columns/160072rows/50ns, cleanlog/zeroOP.
Summary641219321 SHA34666b2ef60d9421127d85b3e976b2babd932ca18750fc6aee9688af4ffb67eb;
archive641217928/561331928bytes SHA2b8f86a69d6b35f810f5f364a009a4b273a245b6436c5f7f647ce996d55b4c5b.
Independent physical_review38613111364 PASS as source/measurement validation,
result641223184 SHAab51598adb8a20ee5cee3b228cf7611d48715508837658e89c58f4cbf4f1533f.
All94MOS differences/141finite tap drops checked; maximum|Vgs|2.65153V,
|Vgd|2.67173V,|Vds|2.79213V, largesttapdrop33.728mV. No safety/PVT claim.

Actual clearb returns23.826ns, only0.190ns before internalfb rising24.016ns;
DOWN masterMQ does not rise again until31.184ns. Missing24ns output response
leavesUP asserted until nextDOWN event; nextreset36.679-40.070ns masks the
feedback edge37.084ns. Original physical candidate not adopted or locked.
Prepare pll_pfd_stage=layout_d2: same94MOS topology/235devices, double widths
of88DFF MOS only; AOI6 unchanged. FreshGDS560DRC/strictLVS/fivefaults required,
then freshRC andnativewave; no oldgeometryRC/wave reused as acceptance.

Parent source recovery38612960848 PASS. Full source inventory is in
result641221741/1464733bytes SHAa7b9bdce63bd51971e7295f571f557cbf5b1ae40df80b8529b3ad8c6ee0c1e49.
Latest actualparent865 geometry exists inpcie-feedback-pbuf10-20261012/parent23;
inspect parent18.py/reference23.py/parent-review28.py/compose29.py before new
PFD parent reassembly. Route38598795406 retainedlive; allcloud-only/fullgoalsOPEN.


**Parent physical integration source recovery prepared alongside live native capture.**
Native38610259816 and route38598795406 are still authoritative livehandles.
New physical-terminal review controls passed commoncheck38611528535; dispatch
physical_review only after original native success. Quantitative terminal
review alone cannot close full845device safety or actual parent geometry.

Use pll_pfd_stage=parent_methods to recover source-bound original PLL753 parent
physical generator/review/input manifests and latestparent865/PBUF10 composition
methods. Record actual archived GDS/LEF/circuit inventory without executing
archived code. Known review12.py/inputs01.json hashes must match historical
physical evidence. This resolves how to recompose newPFD and commonbulk in the
actual parent, rather than mistaking the frozen electrical fixture for layout.
AllCAD/source recovery/evidence remaincloud-only; fullgoalsOPEN.


**Physical PFD full-terminal waveform review prepared while native jobs run.**
After38610259816 terminates successfully, dispatch pll_pfd_stage=physical_review.
It restores that exact source9e56ae04 capture,35model/OSDI bytes, reconstructs
845device fixture from immutable parent/PFD macro, verifies originalstartup/
.3125ps/50ns deck and every terminal voltage. Reports Vgs/Vgd/Vds/Vbs/Vbd for
all94MOS and exact finite-contact voltage drops/derivedR-current for141taps.
Nine actual malformed-evidence controls plus analytic positive case required.
Independently recomputes resetmask events and extrema from rawwaveform.
This is quantitative diagnosis, not full845device safety/PVT/RF qualification;
no invented limits or PHY acceptance. Do not dispatch before nativecomplete,
restart simulation, or replace live route38598795406. Allworkcloud-only.


**Live cloud-native continuation handles — retain exact runs.**
Physical PFD candidate capture38610259816 on9e56ae047a0e36725bac42daa4868c092c2da261,
job116011470430 (aoi4_rc), observedin_progress at requested-native-capture step.
Common selftests/SPDX/inventory/REUSE/regression job116011469688 completedPASS.
Read terminal capture and actual full235device terminal voltages/reset recovery
before any electrical acceptance. Do not restart on observation timeout.

Route38598795406/job115972338767 remainsin_progress in exactpostCTS route step;
source9d904ed0 and savedfreshCTS5b18b060 retained. Inspect all original-terminal/
supply fault proofs, truezerooverflow and originalcorner timing when terminal.
PFD componentRC review38609444130 is completePASS, not fullPHY/mainchipsignoff.
No local durable files/CAD. This turn changed circuit-analysis implementation,
completed actual nativeRC and27faultcontrols, and dispatched the next native
simulation. FullserialPHY/routedmainchip/finalsetup-hold remainOPEN.


**PFD235 saved nativeRC review38609444130 PASS; electrical fixture screen prepared.**
Exact235devices/716R1178C,53metal conductors,431anchors with8binding+13rawRC+
6composition faults allpass. No native extraction rerun. Summary641161303
SHA2f4bade844a8f5182f5cc1c4b5c75ce4c4ce753d6dbdc062c20da7548e875a82;
archive641161060 SHA40f43ab7116303ab57a7431c7f2814045a4c1d35a42a1aedef2989626c9abedc.
Composed macroSHA4231a31db0b6e39bad5ba4266159a56ed3e780d8508c6bcdbb9e74cb43203f38.

Use pll_pfd_stage=physical_wave for actual PFD model in unchanged parent
fixture:845native devices,610non-PFD devices/allotherRC byte-identical,
original models/OSDIs/.3125ps/startup and50ns. Reversible nine-port translation,
exact94MOS topology naming and every235device terminal voltage recorded.
This is an electrical fixture, not recomposed parent physical/sharedbulk
integration. All-device safety/original1us/PVT/RF/substrate and PHY gates open.
Route38598795406 remains live; allcloud-only, no local durable artifacts.


**Actual PFD235 extraction completed; review original saved bytes next.**
38608812756 passed235device binding/eight faults,658terminal physical ownership,
new53conductor graph,716R1178C native extraction and per-point/collapsedC audit.
Raw fault harness failed selecting a non-bridge: actual exported R graph is a
forest. Correct control selects a real two-anchor bridge, removes exactly one
R, proves both real terminals isolated, requires the original open rejection.
No rawR/C/gate change. Use pll_pfd_stage=rc_review on exact savedarchive641150842
SHAddc9539a72d8b9f40f3c544c4e2ad09536c0440062944b28d582d4a17a578704;
do not rerun native extraction. Summary641151072 SHA617c3b3eb02d7256c1aecd62091f0546d49f6553f2b9857292645bc04defbeaf.
After13rawfaults/sixcompositionfaults, evaluate newRC in nativePLL. FullPHY,
routing/finaltiming remainOPEN; route38598795406 retained; allcloud-only.


**PFD235 RC38608389008 stopped safely before native execution.**
Strict source adaptation expected renamed diagnostic Complete235 but the
original literal is Complete255; corrected exact match without changing any
device/graph/electrical gate. Failedsummary641143185 SHA9a9af91dbdd1a490aa90815712f1d5ee50245de32dcbb5330d944b4175d8d6ac retained.
Rerun pll_pfd_stage=rc on corrected source; no native extraction duplicated.
Route38598795406 remains original live handle; all work cloud-only.


**New PFD235 native binding and actual geometry RC prepared.**
Use pll_pfd_stage=rc to restore exact physical38604234902 GDS/LVS, verified
recovered methods641099130, pinned PDK/models and native Magic runtime.
Export235 actual devices (94MOS/141contacts), bind658 native terminals with
423metal/235body references plus8ports. Conductor/R/C counts derive from
actual new geometry; never reuse original255-device parasitics. Require8binding,
13rawRC and6composition faults, exact wire graph and per-point capacitance.
No waveform, RF/substrate extraction qualification, acquisition or PHY claim.
Route38598795406 remains live; all native work and persistent files on GitHub.


**PFD extraction/binding source recovery38606020769 terminalPASS.**
448migration manifests searched;15exact source/anchor/device records recovered
without executing archived code. Summary641099130/640488bytes SHA
61c7bcbd29f8defec1a8565b0f0e1e110591474f9a5d42e5d077c33df543acf1.
Contains build_devices01.py/export01.py/check_binding01.py/binding-controls01.py,
anchors01.py/locate01.py/probe01.py/run-rc01.py/run-pipeline01.py/audit-rc01.py/
mutations02.py/compose01.py/check-compose01.py and originaldevices/anchorsJSON.
Next inspect these bound sources, adapt to actual235device AOI94layout and run
fresh physicalRC with original corruption/terminal-ownership checks. Never
reuse old255deviceRC as newgeometry. Onlyroute38598795406 remains live from
this chain; all completed native captures/physical/LEF failures and passes
retained. FullPHY/mainchiprouting/finaltiming OPEN; allworkcloud-only.


**Cloud continuation 2026-10-14T17:23:18.930165+00:00; exact source-recovery handle38606020769.**
Source329cf12816831d9005773513afdb9bae99537dc3; observedcompleted/success.
Use pll_pfd_stage=methods. EarlierdispatchHTTP422duplicateenv was corrected
before run creation; no earliermethodrun exists. Recover exact oldsource
methods, then adapt binding/anchors/RC to actual235device GDS5eba5849.

Completed: native paired38602623171, physical38604234902, LEF38605102553.
LEFsummary641086027 SHA c154e26374fe13e7333dc60bc443e4303f6f69cc3002f9ac2df4ccca0b00a7b0;
archive641085838 SHA0fe41f4e5469ae15fe794a8cc28830e501ce7db79cade521e8e0addb0511a024.
All8pins/outline/use/direction/obstruction checks and missing/blockedpin
controls PASS. No physicalRC/electrical/PHY/mainchip acceptance yet.

Retain route38598795406 observedin_progress/None; no
observation-timeout restart. This and previous turn made concrete progress.
Full serialPHY/routedmainchip/finalsetup-hold remainOPEN; allcloud-only.


**Matched native50ns comparison terminalPASS as screening, not acceptance.**
38602623171 completed both profiles cleanly withzero-sourceOP. Baseline102MOS
clearb low about1.665ns; AOI94MOS about0.936ns. Both schematic profiles avoid
clock-edge masking; absence ofPFD RC in BOTH demonstrates original parasitics
are material. Do not attribute all improvement solely to AOI topology. AOI
UPpeak2.0098V and internalMQpeak2.8461V require actual full-device validation.
Baseline summary641079126 SHA87e516e30930d875838283a7e35c4ad15fa1a698728ab3a0eec377e88f415610;
AOI summary641067985 SHAfc8e3522968f1d437b24b29851f34ddecbb1aef2421c6d3dd823f7316944e7f1.
Paired captures retained. LEF38605102553 completedsuccess; inspect result.

Next RC work uses pll_pfd_stage=methods to recover original source-bound
PFD255 native binding/anchor/extraction/composition methods from verified
migration manifests on GitHub. Reads/hashes selected originals only; no
execution or PEX qualification. Adapt to actual235device94MOS layout only
after source review, preserving every actual terminal and rawRC fault gates.
Routing38598795406 remains handle; allfullgoalsOPEN/cloud-only.


**PFD workflow selectors consolidated; no lost native job.**
LEF dispatch on a6bfa3d9 was rejectedHTTP422 because workflow_dispatch exceeded
GitHub25-input limit; no run was created. Four new PFD booleans now become
one pll_pfd_stage choice: topology/schematic/layout/lef (defaultnone). Use
pll_pfd_stage=lef for exact saved38604234902 interface verification. Existing
live38602623171 and38598795406 keep their original source/inputs and must not
be restarted. Original electrical/physical gates unchanged. Allcloud-only.


**PFD94 physical gates PASS; exact LEF native readback prepared.**
Run38604234902 onae8659729d0ba0c7394d28318ed13b5a42459f57 passed560DRC
categories/zero markers, hierarchical and flat235/235deviceLVS without
extraction diagnostics. Allfive physical/reference faults rejected.
Summary641068432/175711bytes SHA52a1ace9ab76efa62dbd9dcb1f8298a2931d778399b4d065988bbe426d4696e6.
Archive641068170/639953bytes SHA869b6c076124a4773bf9a047309d49f41d0465db18456603d5c7e7e837d9b953.
GDS5eba584933e1308a1266e6bb94f8a4f3c54b545b03a7ee5010884875c16accf6;
LEF00e00d8794e9aa98c162c804f41cd23aec1986031d1136219a799675ea5d7bea.
Native pll_pfd_lef=true restores exact saved layout and reads all8pins, outline,
directions/use and obstructions in OpenROAD; missing/blockedpin controls must
reject. No DRC rerun needed, no mainchip/RC/electrical acceptance. Paired
schematic38602623171 androuting38598795406 still retained cloud-only.


**First actual PFD94 geometry rejected; local tie placement repaired.**
38603616210 terminalFAIL at nativeDRC:560categories,oneLU.b marker in
nmosHV$3. Native rule requires all N+active within20um of PWell tie; marker
spans localy12.319-16um. Existing below-device substrate contact misses upper
portion of widened16um NMOS. Move only the two aoi4 wideNMOS existing ties
to device mid-height; same94MOS/94substrate/47wellcontacts and original88DFF
geometry. No deck/threshold waiver. Rerun pll_pfd_layout on repaired source.
Preserve failedsummary641054841 SHA78b0a86d432a2007a2286d1260592a5eddd8de37bd4e1fd5638a8eea6aa78f8f
andarchive641054578 SHAe57531ec02ba98f77633e3dba92190d64ffec1511c3ddf52c46895d7c5f3c11c.
Pairednative38602623171 androute38598795406 remain live/cloud-only.


**Actual AOI reset PFD layout/verification prepared on hosted runner.**
Generator now has explicitaoi4 profile:94original-schematic MOS,94substrate
and47well contacts, topnssoc_pfd94_aoi4_layout_v1. Same AOI transistor list
is shared with native simulation; first88DFFdevices unchanged. Physical gate
requires source-record equality,235actualdevices,560nativeDRC categories,
flat/hierarchical transistor LVS and existing wrong-width/missing-well/open/
rail-short/offgrid controls. No deck/acceptance waiver. New pll_pfd_layout
input restores exact197PDK/deck files and pinned AppImage on GitHub.
This is a physical candidate; new RC/fullnative/PVT/1us acceptance still open.
Paired schematic38602623171 and route38598795406 retained; no local files.


**Live native comparison38602623171; retain exact cloud handles.**
Sourcefaebb437ef2a3cc7010b46202ae731f7e76d4f59; observed2026-10-14T16:59:44.325223+00:00:
paired baseline_schematic/aoi4 jobs in_progress/None.
Native MOS counts are712/704 respectively, with610other instances and all
non-PFD RC unchanged. Both are schematic PFD screens lacking physicalPFD
RC/bodycontacts; no adoption. Check actual captures/controls and compare reset
recovery before new GDS/DRC/LVS/RC work. Original1us acquisition/PVT/safety
and fullPHY gates still required. Topology evidence641014025 confirmed.

Routing38598795406 observedin_progress/None. Do not
duplicate either handle. This and previous goal turn made source/native
evidence progress; no completion or blocker. Work remains cloud-only.


**PFD reset masking measured; matched static-CMOS redesign screen prepared.**
Topology diagnosis38601440241 oncad979e3 PASS. Result641014025/563238bytes
SHA46c256ba5cbfcca28f303ce6f02d862cd3f35af0566e43b4ddd816051587bca5.
Exact102MOS/771metalR topology names: clearb active about22.8-29.8ns, covering
next reference24ns and feedback27ns edges. Both outputs respond every20ns
in this startup capture; this is not proof of late1us causal closure.

New pll_pfd_candidate=true runs two matched schematic50ns native captures:
baseline102MOS and94MOS with original88DFFdevices plus6MOS static AOI reset
(clearb=NOT(reset OR(up AND down))). All8static input states and6wrong-gate
controls required. Both replace original255device/771R1256C PFD only; every
other610device and non-PFD RC line stays exact. Both lack PFD physicalRC/taps,
so any improvement requires real GDS/DRC/LVS/newRC and original1us/PVT/safety
validation before adoption. Original full-wire failures remain authoritative.
Routing38598795406 retained; cloud-only/fullPHY/routing/finaltiming OPEN.


**Full PFD terminal coverage PASS; schematic naming diagnosis prepared.**
38600813474 on426d78cf passed with every102MOS D/G/S probe included. Result
641004212/1054133bytes SHA
fef204c48418fbf8242d9dbf739f9d06ce6cac1c2b38a6412c1ff55dc181f164.
New pll_pfd_topology workflow input maps this immutable capture onto original
102MOS schematic through exact anchored D/G/S/model/W/L graph correspondence.
Only for naming: extracted metal resistors are collapsed in mapping, never in
simulation. Full RC waveform unchanged; body/tap LVS/qualifiedPEX/acquisition
not claimed. Require unique internal-net mapping and full transistor multiset;
wrong gate/size/missing device/port short must reject. Routing38598795406 live.


**PFD internal-node diagnostic coverage correction prepared.**
Successful full50 review38599049135 preserved exact raw capture and pump
observations, but its xpfd.n_ selection only covered well nodes, not the MOS
drain/gate/source probes xpfd.t*. Full raw capture contains these terminals.
Reader now requires every102actualPFD MOS D/G/S vector, retains all PFD
voltages and reports both rising/falling edges. Missing terminal/duplicate/
wrong-device-count controls must reject. Re-run only full50 diagnostic on
this corrected source; no new native simulation or altered gate. Use actual
reset/latch terminals to investigate alternating output before circuit change.
Routing38598795406 remains live; retain exact handle/cloud-only execution.


**Cloud-only checkpoint — 2026-10-14T16:41:49.948312+00:00.**
Local NSSOC workspace and NSSOC paths in /tmp and /dev/shm are empty; no
local CAD/simulation process. Remote retirement receipt636387277 SHA
23f8d33591444bb1d22d18a8668142de3c52e906b4dddfbf98118b614d78bcbd
confirms hosted archive readback before deletion. Source/CAD/tests/artifacts
stay on GitHub. Preserve original user Downloads and unrelated files.

**PLL full50 diagnosis38599049135 completed successfully, not lock acceptance.**
Sourcefae8ae84c0fb0178e8e22496b400130a60020286; result640970260/326153bytes SHA
f4043124ae4d3d07d6a72b121b06e522510edb2f2ed8a15f9fb0779164478a83.
Exact2438columns/160072rows, raw/payload/FIFO trailer and native device-current
aliases verified. Original parent/circuit/native off flags/OSDI match1us source.
Internal PFD/pump startup records are available; no new simulation, no late1us
internal causal proof and original rolling acquisition gate still fails.

**Routing handle38598795406: in_progress/None.**
Source9d904ed0e49ed9bdc00e767adb724d29ab6818ba; resumes saved freshCTS5b18b060
without rerunning placement/CTS. Inspect native original-terminal/supply and
dummy-output negative controls before timing/routing acceptance. Earlier
38596343019 and38597967217 are terminal verifier failures, preserved.
Keep this exact handle, do not duplicate on observation timeout.
Full serial PHY, routed mainchip and final setup/hold remain OPEN.



**Full50 payload/trailer verified; preserve native device-current aliases.**
38598305939 terminalFAIL after original compressed/raw/payload hashes and
exact FIFO trailer verification, at raw-name vs canonical-vector equality.
Original header1648_01.py maps native i(@device[param])/v(@device[param])
wrappers to original @device[param] names;487of2438columns use this form.
Reader now binds exact ordered source-vector bijection, with missing/reordered/
wrong-device/duplicate aliases rejected by4negativecontrols. No raw edits,
column omissions or electrical-gate changes. Rerun pll_full50_diagnosis on
this corrected source. Saved CTS proof/routing38598795406 is the live routing
handle; retain it. Full PHY/routedmainchip/finalsetup-hold OPEN/cloud-only.


**Native CTS dummy-load type distinguished from functional clock buffers.**
Resume38597967217 terminalFAIL at clkload427 master whitelist, before routing.
Frozen native TritonCTS.cpp:2430-2437 intentionally chooses inverter dummy
loads, and2525-2528 connects their input only. Verifier now permits only
clkload-named single-input/single-output standard buf/inv cells with output
strictly unconnected; functional clock buffers retain exact non-inverting
whitelist and single-driver proof. Every input root and supply still checked.
New actual dummy-output-to-signal connection negative must reject alongside
actual original-terminal and inserted-supply disconnect controls. Reuse exact
saved fresh-CTS5b18b060; no new placement/CTS simulation or acceptance waiver.
PLL corrected FIFO readback38598305939 on730962af remains handle.


**Full50 original FIFO format identified; no waveform corruption or gate waiver.**
PLL diagnosis38597592170 terminalFAIL at payload hash comparison after full
compressed/rawSHA checks passed. Original capture engine_parent753.py:408,460
requires headerNo.Points=0 and exact ASCII160072 trailer after2438-wide binary
rows. New reader incorrectly hashed that native trailer into payload digest.
Corrected parser hashes exactlyrows*columns*8 bytes and independently requires
exact trailer/no extra bytes; header remains0 and original raw/payload hashes
must both match. Added1positive/5negative trailer/truncation controls. Rerun
pll_full50_diagnosis once on corrected source; no simulator or data mutation.
Fresh CTS saved-database proof/routing38597967217 onb0d9e2f5 remains the routing
handle; original38596343019 terminalFAIL is preserved. Full goalsOPEN/cloud-only.


**Fresh placement/CTS completed; verifier stopped before timing/routing.**
38596343019 terminalFAIL, summary640931131 SHA4315605ee0a05f234000ad04cbe37393215657f87e6613b0db894885f0187bae.
Placement exact connectivityPASS:97661cells/12453dataflops moved; source97722.
Fresh CTSODB5b18b0607c41a9605c7252648849b21483c6a349460e995b41a16f37de0dd809
saved in archive640930633 SHAaab7e72e2cc2d2e2f434c08dfd84e509ba8eee22b9933e408d36f1bed4a4d4f8.
Failure checks SWIG ITerm wrappers with==; corrected to exact instance/MTerm
identity, still requires exactly one driver. Explicit disconnected-output
added CTS dummy loads are counted; every original terminal and inserted supply
must still validate, with actual terminal/supply disconnect negative controls.
Prepared resume_fresh_cts=true with prects_grt/seed13/hold0: resumes these exact
three saved databases, does not rerun native placement/CTS. Inspect actual
proof before any timing or routing acceptance. Full goalsOPEN/cloud-only.
PLL full50 diagnosis38597592170 dispatched on4bec64e0; retain same handle.


**Current-parent full-node PLL waveform located; hosted diagnosis prepared.**
Use PBUF10 native86520261012 full50ns, not older20261011 reset865 capture.
Finite parentSHA b7c2b8f7328c14ff15a5798c7aaec0629104ea7ec9252d2594d3dd9db168ff48
matches original1us exactly; bench circuit body differs only50ns/1us stop,
with identical native off flags and OSDI loads. Full waveform is migration
batch000008: six separately gzipped transport parts, each decoded in order
into originalwave.raw.gz SHA7eb021ef4143f8b9c7e706d212f8058512db654a9d86ac6d6ae38133f0f89a5e.
Prepared cloud-migration-checks pll_full50_diagnosis=true restores/hashes it
on hosted runner, verifies full2438-column160072-row header/payload, then
records internal PFD nodes and pump voltage/current statistics per cycle.
This is startup diagnosis, not late1us causal proof or acquisition acceptance.
Retain active fresh placement/CTS38596343019; no native restart or local files.


**Live corrected fresh-placement/CTS handle:38596343019.**
Sourceb81af7396d907284a63cec47306a5f905694b1de; jobs115963950590.
Current API state:in_progress/None. Preserve this handle and
inspect syntax, native placement/CTS graph plus supply proofs, original all-corner
STA and final zero-overflow route result. Do not restart on observation timeout.
Earlier38596031286 is terminalcancelled after corrected-input decision;
preCTS recovery38594940366 is terminalPASS with exact source/geometry records.
Current turn made native/source progress; no product completion or blocker.
Cloud-only/full serial PHY/routed mainchip/finalsetup-hold OPEN.


**Fresh CTS supply invariant added before physical execution.**
Initial prects_grt run38596031286/job115962883096 was cancelled during native
runtime preparation to add explicit global_connect and verification of every
inserted buffer POWER/GROUND pin against original supply domains. Both actual
signal-terminal and inserted-supply disconnect negative controls must reject.
Inspect cancellation terminal state before dispatching the revised source;
this is a corrected-input trial, not a timeout restart. No layout accepted.


**Pre-CTS lineage recovered; GRT-driven placement plus fresh CTS prepared.**
38594940366/job115959121361 PASS, summary640896159/9514534bytes SHA
817d6b0e4839f52630caa9630c18cfbff23cca80dcd380229d692da13204e493,
archive640895727/33604849bytes SHA
ffe047106a1a2de8af638c0cad4651fc41c7895eb88b78e8a204726100ec4086.
Native stages:79195preplacement,97722preCTS,113771postCTS; all20macros,
boundary geometry/die/core identical. Recovery is not circuit/timing acceptance.

Newer-postcts-cloud profileprects_grt uses exact97722-cell preCTS source,
moves sequential and combinational cells with native GRT-guided placement,
density0.45, unchanged routing capacities and clocks; regenerates CTS with
original buffer/sink-clustering/half-NDR policy. Require exact placement
connectivity, all original terminals preserved modulo inserted transparent
CTS buffers and an actual disconnect negative control, then all-corner STA
and zero-overflow global routing. Old hold2 ECO is not presumed valid after
new CTS. Dispatch once with placement_profile=prects_grt, routing_seed=13,
ethernet_hold_depth=0 and other options baseline/fast_route/critical0.
Full goals remainOPEN/cloud-only; no local files or CAD.


**Prepared source-bound pre-CTS recovery for a new placement/CTS repair.**
October12 physical19 archives13-16 contain the actual preplacement ODB518b889c,
preCTS ODB4739da22 and original postCTS ODBe4e04605. New congestion probe
source_profile=prects_inventory restores exact manifests/member hashes on
GitHub, audits native macro/boundary/die geometry and records source flow,
CTS/global-placement config plus actual PCIe/Ethernet data-flop endpoints.
No source geometry/constraint mutation or adoption. Dispatch once, inspect
complete bound metadata before preparing new placement and fresh CTS.
All three full goals OPEN; cloud-only policy supersedes older local instructions.


**Cloud-only recheck and terminal CUGR result — 14 October 2026.**
Run38591636770/job115947747389 is completed FAILURE, not live.
Native input repair PASS: exactly three empty declarations removed, all real
net terminals, instances, positions and boundary geometry preserved. Cleaned
ODB SHA21f82df4522be6353b1103f1a7923794fa50d9d87d04be8c31b38ca3fdea6cbb.
The independent route gate rejects CUGR nets still overflow; do not adopt or
rerun this identical input. Summary640851603 SHA
8132273cd7de6605cb585e95996b5a6ab48e6b5fb6e3c0157251d8885d979b4c,
archive640850855/242265502bytes SHA
9ba259eaf582ccb47678278d7d2eda1242cbb3ae2ba981d6d6400a5280c7e9b9.
No known native job from these trials remains live. Older live/dispatch
instructions below are historical and superseded by this paragraph.

Next physical work: inspect the current pre-CTS placement/floorplanning flow
and source-bound Ethernet SRAM channel/PCIe endpoint congestion before a new
geometry candidate. Do not reuse the stale September checkpoint. Independently
investigate source-bound PLL PFD/pump alternating-cycle behavior; verify old
full50ns source identity on a hosted runner before any reuse.

Workspace /home/hasanmelih/Documents/ChatGPT/nnsoc rechecked empty, including
hidden entries; no native CAD/simulation process observed. Cloud retirement
receipt636387277 was re-read and confirms verified remote archive readback.
Original user-supplied Downloads documents remain preserved. All execution,
source changes and durable engineering artifacts stay on GitHub; do not
recreate a local checkout or run local CAD/tests. Full serial PHY, routed
mainchip and final setup/hold remain OPEN; migration is not product closure.


**Live repaired-input routing handle38591636770/job115947747389.**
Source2a5e8a5abd98e49d3dec6ca23e71a01d200c3908, CUGR with explicit
cugr_empty_net_cleanup=true and exact originalseed13/buffer-placement/hold2.
Latest observation: native route step in progress. Preserve handle; do not
confuse this new input with terminal firstCUGR38589002753 or duplicate it.
Inspect native cugr-input-proof (all retained nets/pins/masters/positions and
boundary geometry unchanged) and complete route/STA results before acceptance.
Cardinality probe38590905780 is terminal and now recorded in structured evidence:
3empty,302single-terminal,113556two-or-more-terminal non-PG nets. Only the exact
three empty/no-wire/no-guide declarations may disappear; every actualterminal
remains. No timing/capacity waiver, no sourceODB overwrite, no adoption.
Previous goal turn and this turn make concrete source/native-evidence progress;
fullserialPHY/routedmainchip/finalsetup-hold remainOPEN and work stayscloud-only.


**Exact zero-terminal input repair prepared from native inventory.**
Probe38590905780 summary640823931/3861412bytes SHA
f1d71b542a4e46f5475ee77bd4e4b7f58c5c05f6aad91e1f0151d7400c68b5b8
is terminalPASS. It found3zero-terminal and302single-terminal non-PG nets;
the remaining113556 have2+terminals. CUGR originally tried all113861.
Native input cleanup now requires exactbaselineODB660692b3..., exactinventory
and only the3named zero-terminal/no-wire/no-guide declarations. It rejects
can_rx_i as a negative control; all302single-terminal nets, every cell/master/
position/status and retained net/terminal/boundary geometry must remain exact.
Source ODB is never modified; separate cugr-input.odb and full proof are saved.

Dispatch newer-postcts-cloud once with router_solver=cugr,
cugr_empty_net_cleanup=true, placement_profile=local_optimize_buffers,
ethernet_hold_depth=2, macro_routing_profile=baseline, routing_seed=13,
critical_nets_percentage=0, grid_profile=baseline. Require native invariants,
original all-corner timing and independent CUGR zero-overflow/coverage gates.
No adopted layout, no skipped actual signal, no constraint change. Previous
failedCUGR38589002753 retained. FullPHY/routedmainchip/finaltiming OPEN/cloud-only.


**Live continuation handle: terminal-cardinality diagnosis38590905780.**
Sourcec2ba59b4ec1394a336196ebbfcd905a3c2a477bd, source_profile=seed13_buffers.
Retain this read-only native job; it was dispatched after the terminal CUGR
failure and therefore supersedes the older no-live-job statement below.
It preserves sourcefailedODB connectivity and does not reroute/delete nets.
Inspect signal_net_terminal_inventory in its immutable summary before changing
the router input or native engine. PLL cycle diagnosis640800063 is terminal;
full sourcebound PFD/pump investigation remains next independent circuit work.
Cloud-only/fullPHY/routedmainchip/finalsetup-hold OPEN; no blocker or completion.


**CUGR terminal native exception; PLL cycle evidence identifies next circuit investigation.**
38589002753/job115938555226 failed at CUGR stage1 pattern routing with
vector::reserve. Source/placement invariants and1positive/10negative result
controls passed; no routed candidate or adoption. Summary640802953 preserves
failure inputs. Frozen PatternRoute::constructSteinerTree hasdegree1 handling,
but no degree0 guard before reserve(2*degree-2). This is a hypothesis, not yet
confirmed inputcause. New read-only native signal-net cardinality inventory in
probe_cloud_newer_congestion.py counts every non-PG net/terminal and reports
zero/one-terminal nets without deleting or excluding them. Dispatch probe
source_profile=seed13_buffers once on this source; identical sourceplacement
and connectivity underlie failed CUGR. Never silently skip an actual signal.

PLL cycle diagnosis38589545075 summary640800063/836777bytes SHA
02d9495f9c3b5b4f3f0d113e777712dd9f20ef162ebcc5f04768946b07bc5b66
passes hosted controls/common regressions, original acquisition remainsfalse.
Lastfeedback periods alternate9.993761ns/10.005040ns with80VCOedges each.
UPduty alternatesabout0.651/0; DOWNabout0.837/0.099; VCTRLcyclemeanabout
0.508/0.559V. These are descriptive source-bound observations, not causalproof.
Exactoriginalbench/parent865 netlist text is preserved in that same summary.
Next isolate PFDreset/pump modulation before another physical circuit candidate.
No existing job from this turn remains live; do not restart terminal captures.
All full product goalsOPEN/cloud-only. This turn changed authoritative source,
completed native controls/diagnosis and rejected a new actualsolver trial.


**Native solver run retained; original-wave PLL cycle diagnosis prepared.**
CUGR candidate38589002753/job115938555226 onfeba4ccf is queued, not failed.
Retain handle; no duplicate. Exact placement and independent zero-overflow
controls are mandatory; experimental engine success never means signoff.

Prepared cloud-migration-checks pll_acquisition_diagnosis=true: reuses exact
completed1us rawcapture38507479646 with all existing source/model/hash checks
and frozen original acquisition criteria. Adds descriptive per-feedback-cycle
clock edge counts, VCTRL ripple, UP/DOWN voltage means/duty, plus exact bound
bench/parent netlists. No new native simulation or acceptance change. Ramp/
constant-pulse positive and nonfinite/reversed-edge negative controls run first.
Dispatch once; use original cycle records to identify alternating-period/loop
settling causes before selecting a real circuit change. Full goalsOPEN/cloud-only.


**Next physical candidate: exact-placement native3D solver comparison.**
Marker diagnosis640359444 confirms persistent Ethernet SRAM4/5 region congestion;
large combinational spread did not fix it (138vs132overflow). Frozen OpenROAD
CUGR source applies original dbTechLayer adjustments and native obstructions.
Prepared router_solver=cugr on exactbaseline132overflow placement:
placement_profile=local_optimize_buffers, ethernet_hold_depth=2,
macro_routing_profile=baseline, routing_seed=13, critical_nets_percentage=0.
Do not combine this with new placement or relaxed capacity/SDC/RC. Native CUGR
is explicitly experimental; original report controls require zero overflowing
nets, zero wire overflow, nonnegative floating minresource and original113556
routed nets. Missing/rounded fractional deficits must reject;10negativecontrols.
Dispatch newer-postcts-cloud once with those inputs. Even a passing guide screen
requires detailed routing, independent connectivity/DRC and extracted timing.
No adoption or production claim. Previous goal turn made concrete progress by
completing original PLL lock review and exact congestion diagnosis; no blocker.
All full product goals remainOPEN and execution remainscloud-only.


**Heartbeat final checkpoint: congestion diagnosis terminal, no old live jobs.**
38566051147/job115858892640 PASS native geometry diagnosis and orientation tests.
Summary640359444 SHA c3978c991f6e2e2e84d14c91b4693325deb432857b6da17e8410a5975f2526da
binds exact failedODB fb2e0306e85818041f49bc6032bb9e38e167ef21e293492769717113370157d5
and congestionreport e91b84dcb03d3699977b124d3e698cf5f2ae224abcf30b7d953fadcab253e0f7.
100 native markers account for138overflow; every reported net is associated
with native endpoints and geometry. Archive640359163/19342818bytes preserves
original inputs/diagnosis. This is not routing closure. Use complete native
marker/net/macro records to design next repair, preserving existing OBS/capacity.

All explicitly listed older PLL, hot, timing and route jobs are now terminal.
PLL lock review remainsREJECTED (rolling100ppm windows); short-prestage hot
remainsREJECTED (CM/bitmargin and four HBT bounds); directACK unplaced setup
improves but slowCPUhold regresses. No candidate adopted. Three full goalsOPEN.
Latest structurednext_actions supersede older dispatch/wait instructions. Next
scheduled work is diagnosis-driven repair, not polling these completed runs.
Cloud-only execution and verified local retirement remain in force.


**14 October heartbeat follow-up: original PLL review terminal REJECTED.**
38565392744/job115856656627 completed source-bound original-gate review;
summary640347167 SHA4684318385d1ac7e9a7855a7a24b73853865e482e2a0a783bf2a8656c830485b.
Full capture verified3201212rows/25columns and complete1us; no new simulation.
Final800-900ns and900-1000ns windows pass, but intervening rolling windows
still fail100ppm: e.g.890-990ns feedback100013197.84012932Hz. Sustained
passing suffix starts900ns, violating the original start-at/before800ns gate.
Original positive/frequency/phase/missing-edge/control-voltage and truncated/
nonfinite controls pass. Acquisition, all-device safety and fullPHY remainfalse.
Next diagnose alternating periods/control ripple and settling using exact raw;
do not fit phase, waive rolling windows or restart the unchanged capture.
Full review persisted in cloud-closure-continuation evidence.

Congestion diagnosis38566051147/job115858892640 launched on2f29eb41528d71322e5a92ad26ca8690c12c5c0e,
source_profile=routability_data, exactfailed138overflowODB. This is a read-only
native geometry diagnosis, not another global route. Retain handle, review
marker/net/macro associations before selecting a repair. Previous hot rejection,
directACK mixed timing result and all full product gates remain unchanged/open.


**14 October12:35UTC heartbeat: all previous captures now terminal; next reviews.**
PLL38507479646 completed original1us continuous865device capture, summary639850959
and521359148byte archive639850421 (SHA59470c85beab31acc7ca76c4a908a24db5be5b74d358668f2e50d016548e3af6).
Prepared original-gate review38565392744 dispatched once; do not rerun native.
Capture completion is not lock, complete safety or fullPHY acceptance.

Direct ACK pair38526942261 completed: baseline639584274 slowPCIe-1.046260ns,
candidate639588788-0.980501ns; fastPCIehold unchanged-0.109062ns. SlowCPUhold
worsens-0.444253to-0.542557ns. Full original phase/path/control receipts retained
in ACK evidence; no adoption, still unplaced only. No final timing closure.

Short-prestage/direct-final hot38527211035 completed but BOTH REJECTED.
hot639594835 bitmin0.088065717V/31below100mV, finalCMmin1.794040920V;
hotres639596919 bitmin0.112378810V passesbits, finalCMmin1.782591361V fails,
and four finalHBT VCE lower bounds fail (minimum0.396485640V). No waiver or
adoption. Full summaries and hashes in the short-prestage composition receipt.

Route38511490580 remains terminaloverflow138. Prepared congestion sourceprofile
routability_data binds permanentarchive639573076, publishedsummary639573452 and
exactfailedODB/congestion hashes; dispatch probe once, then diagnose actual
markers before a new route. No healthy long job was stopped or duplicated.
Authoritative localretirement636387277 was re-read: COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE.
All work remains cloud-only; fullPHY/routedmainchip/finalsetup-hold OPEN.


**Cloud-only checkpoint, 14 October 2026: terminal route failure and live jobs.**
Local workspace `/home/hasanmelih/Documents/ChatGPT/nnsoc` remains empty,
including hidden entries. No local source/CAD/test/artifact files were created.
Retirement proof asset636387277 remains the cloud handoff record.

- Mainchip route38511490580/job115680796118 is now terminal FAILURE, not live.
  Original sourceec864e8484c146ea204d46ce6aa2f284ca4b73f7. GRT-0116:
  total overflow138 (Metal3:17, Metal4:19, Metal5:93, TopMetal1:8,
  TopMetal2:1); total routing resource usage19.51%, routed nets113556.
  This candidate does not improve original overflow132. Detailed routing and
  final routed timing are NOT complete. Preserve failed partial state; diagnose
  localized congestion before another geometry trial, do not blindly restart.
  Permanent archive639573076,197322362bytes,
  SHA3824566424b5f94dd3586be49981bd4238c8d01cd3cc9440cb63e70bd2c0d275;
  summary639573452,17021763bytes,
  SHA928272bfe863c02df5e90c600563d0f191aefa3b79b92596a4a2d3f8eb7fefc6.
  Release tagcloud-results-38511490580-1-route-routability_data.
- Hosted common validation38527212907 on0289caff PASS, including updated
  tracked inventory22579. This verifies regressions, not engineering closure.
- Direct ACK pair38526942261 on520fd0a90cb325388d52e73a14e3e8b824fd5c96:
  baselinejob115729422349 completed success; candidate115729422079 still
  mapping/screening. Preserve handle; inspect both original corner reports
  and combined controls before any decision. No candidate adoption yet.
- Short-prestage/direct-final hot study38527211035 on0289caff:
  hot_low115730282870 and hot_low_res_bcs115730283229 passed preparation
  and are in original-bit/electrical screening. Do not duplicate or infer PASS.
- Original continuous PLL38507479646/job115668187421 remains in progress.
  After capture success only, run the prepared source-bound acquisition review;
  capture completion itself is not lock or PHY acceptance.

All full serial PHY, routed mainchip and final setup/hold goals remain OPEN.
Future edits, simulation, CAD and durable evidence stay on GitHub. Older live
statements below are historical; the explicit statuses above supersede them.

**Source-bound short-output prestage composition PASS; new hot pair prepared.**
38526689071 summary639566149 binds54devices/3848R/2554C. Native wireSHA
69f91103491cb38a90e2daadb0655e60bfc93dde150ac1f9804e0151f0903bb8;
compact179199ae7f8245e24760570f3c507d61cdc3b13b5907c7d6ed9d03897ffadef6.
New studyv8_feedback_tc_short_pre_hot combines these actual prestage wires with
already bound direct-supply V8 final layout, original TC/nativeclock/sourcebits
and every original hot_low/hot_low_res_bcs gate. No device or RC mutation.
Expanded old-circuit AND wrong-geometry hashed archive controls run first.
Dispatch hot study once; only native result determines acceptance. Full PVT and
32:1 still required if these two hot cases pass. New receipt increases inventory
to22579/4223inline/18356path/docs1509; LICENSES.md updated in same commit.

Hosted common regressions38526686053 on240ba459 passed including inventory;
prior red runs retained as inventory failure. Direct ACK paired mapping was
dispatched on520fd0a9; retain latestmatching handle, no duplicate. Original
PLL38507479646/route38511490580 remain live handles. Full goalsOPEN/cloud-only.


**Proved direct ACK commit ready for paired native timing.**
New studyadvert_dedicated_ack_commit compares dedicated-only against
physical_idle_credit_dedicated_ack_commit. It requires original proof639541970
SHA64683e3cc9eea66a81e8cf2195089c32c80a95c5158778c1817a75e6d3984799,
all21source hashes and existing dedicatedFC all-state proof. Additional combined
buffered/replay positives and invalid-ACK guard negative run before mapping.
Rejected ACK-window candidate is excluded. Dispatch once on this source after
confirming hosted inventory/regressions run on240ba459; no constraints changed.
Prestage short-output composition was dispatched on240ba459. Find and retain
newest corresponding Actions handle, then bind composition before new waves.
Original PLL38507479646/route38511490580 remain handles. All goalsOPEN/cloud-only.


**Direct ACK commit proof PASS; prestage native RC PASS.**
38525456371 ACK job115724648567 summary639541970 passes all-input enable
identity, full replay equivalence and baseline11/candidate11 port tests; invalid
ACK guard negative rejected formally and2of7port tests fail as expected/no skips.
Candidate replaySHAa26f36608154ca66a365129284d74b03d627acddfe90811a52e2c30d928a568c.
Workflow was red only because sibling tracked-path inventory still had22577;
new evidence makes22578/4223inline/18355path/docs1508. LICENSES.md updated;
dispatch empty cloud-migration-checks once to recheck every original test.
No timing adoption. Next pair direct-ACK+dedicatedFC against dedicated-only,
with exact proof source and combined port controls before native mapping.

Prestage extraction38525671945 PASS original RC graph/13fault controls;
source archive now in composition input. Dispatch tx-layout-waveform-cloud
cascade158/critical_buses_kelvin_supply_direct_low_outputs compose_only=true.
Then source-bind combined newprestage+directV8 hot/cold waves; retain every
prior failed native result. Original route38511490580/PLL38507479646 retain
handles; cloud-only/full goalsOPEN. Real proof/physical progress, no blocker.


**Prestage short outputs: native physical PASS, exact extraction prepared.**
38524919925 summary639530448:560DRC categories/zero markers, strict LVS and
physical fault controls PASS. Archive639530335382687bytes SHA4c5d0246ed2f2aed89b9bde38bf13f46b28efff5a446fa3d823fcfd05594a6f9
is now bound in extraction input. Dispatch extraction for cascade158 and
critical_buses_kelvin_supply_direct_low_outputs once. Native devices/values
unchanged; electrical common-mode/bit repair not yet demonstrated.
Direct ACK commit proof was dispatched on1249b410, find newest workflow_dispatch
cloud-migration-checks and retain its handle. Combined-window rejected timing
summaries639525435/639521132 and full reported phases now saved in ACK evidence.
Original PLL38507479646/route38511490580 remain active handles/full goalsOPEN.
Cloud-only, no local CAD/tests/artifacts; this turn makes physical and proven
source-bound digital diagnosis progress without discarding failed candidates.


**Combined ACK-window timing rejected; direct register enable proof prepared.**
38524042217 completed: dedicated-only639525435 slowPCIe-1.046260ns versus
combined639521132-1.082708ns; fastPCIe hold unchanged-0.109062ns. Combined
buffered5/replay7 positives and wrong-page rejection passed, but timing did not.
No adoption. New direct_commit replay variant changes only the acknowledged
sequence register: same reset/link priority, write on allowed ACK handshake
including equal duplicate values. Original retirement/head/count/timer/NAK
logic remains unchanged. Removing the redundant delta!=0 enable is a hypothesis;
all-input identity/full output equivalence and complete port controls must pass.
Wrong-guard candidate intentionally accepts invalid ACK sequence and must fail.
Dispatch cloud-migration-checks ack_direct_commit=true once; map only after proof.
Do not combine the rejected ACK-window rewrite into this independent candidate.

Prestage short-output physical38524919925 completed success; read/bind full
physical receipt then extract original native RC. No waveform acceptance yet.
Original route38511490580/PLL38507479646 remain handles. All full goalsOPEN,
cloud-only. Earlier timing/analog failures remain preserved, not waived.


**Actual direct-supply hot study terminal: improvement, both cases rejected.**
38523202992 hot summary639508462 bitmin0.095224545V (13sub100mV early samples),
final-input diffmin0.151252448V and CMmin1.788243586V; hotres639507457 bitmin
0.118692802V PASSbits, diffmin0.155516545V, CMmin1.773661833V FAILinterface.
All HBT/MOS gates pass, no candidate adoption. Full original summaries/hashes
stored in direct-supply composition receipt. The review's final interface is
ap/an/bp/bn: PRESTAGE outputs, not final-mux op/on. Next physical candidate
cascade158/critical_buses_kelvin_supply_direct_low_outputs preserves all54devices,
shortens op/on buses and aligns/moves actual shunt/series resistors, keeping
native direct-supply geometry and every original threshold. Dispatch physical
layout once; require original DRC/LVS/faults then nativeRC/waves. No R rescaling.

Combined dedicated+ACK-window mapping38524042217 on9313190a is active:
baseline115720101470/candidate115720101724. Exact endpoint proof639490865 now in
structured ACK evidence. Fresh joint buffered/replay positive and wrong-page
negative ports precede mapping. Preserve run; do not start another timing trial
until reports identify the remaining limiting path. Original route38511490580
and PLL38507479646 retain handles. All full goalsOPEN/cloud-only.


**New limiting timing endpoint exactly bound; combined proof-preserving candidate.**
PreABC trace38522829842 summary639490865 PASS reproduces original pre_map.v
byte-for-byte (df4bc9fd42b4b5a2fd35b4a08f621501e6b7208809f738fc504d1b3535f058a4).
Three limiting registers1176743/45/48 bind through actual generic inverters to
u_pcie.acknowledged_sequence_o bits1/3/6. Original startpoint is ACK sequence bit0.
Thus after dedicatedFC commit, replay ACK-window classification is the limiting
cone. Prepared profilephysical_idle_credit_dedicated_window combines exact
source-bound dedicated advertiser proof with prior all-input CW2..5 ACK-window
identity/full replay equivalence, changing disjoint modules only. New combined
buffered5/replay7 positive port tests and wrong-page replay control precede
mapping. Compare against dedicated-only, original clocks/all corners retained.
Dispatch pcie-ack-cloud-mapping studyadvert_dedicated_window once; no adoption
or closure claim before original reports. Exact source and failure proof retained.
Hot actual-layout38523202992, PLL38507479646, route38511490580 retain handles.
All full goalsOPEN/cloud-only. Previous turn: concrete geometry/RC/composition
progress; current turn moves from exact endpoint proof to a combined candidate.


**Live original-gate electrical verification of the new actual layout.**
38523202992 on28162773 studyv8_feedback_tc_direct_hot:
hot_low job115717442756 and hot_low_res_bcs115717442977 in_progress. First job
passed hosted graph/source-bit/publication and expanded wrong-geometry/circuit
controls before native simulation. Keep both handles; no candidate acceptance.
Physical38521214968, extraction38521648860/recovery38522280250 and composition
38522827216 are terminal and source-bound in the new direct-supply receipt.
Do not rerun any of them. Full hot outputs determine next physical action;
a hot pass would still require full original PVT/loads/faults and32:1 integration.

Exact original-prefix digital provenance38522829842/job115716239787 remains
in_progress. Read its original premapped-byte-equality and register bindings
before changing replay RTL. Native PLL38507479646/job115668187421 and mainchip
route38511490580/job115680796118 freshly confirmed live; preserve their handles.
PLL review is prepared but must wait capture completion. Local workspace again
confirmed empty. Turn classification: progress (real new layout/RC/composition,
publication recovery without rerun, original-gate hot simulation started) and
verified waits. No genuine blocker; full serial PHY/routed chip/final STA OPEN.


**Direct-supply V8 device/RC composition PASS; original hot screens prepared.**
38522827216 on691dc727 summary639482876 binds54devices/4083R/2673C; archive
6394826726690446bytes SHA413ad0c3edbc2cc68689312e3bbe6d9e2a5689f9b7bed496cd50d34bd5401c47.
New source-bound receipt pcie-final-v8-kelvin-low-ports-loads-shunts-series-direct-
composition-20261014.json preserves physical/extraction/recovery provenance.
Native hot study=v8_feedback_tc_direct_hot runs hot_low/hot_low_res_bcs with
actualnewRC, unchanged cascade158 prestages/TC feedback/native clock/bits/gates,
no Nx/R mutation. Expanded wrong-circuit/geometry archive controls run first.
Dispatch once; electrical acceptance remains unproven until complete wave review.
Do not rerun original compact/hot captures. If hot passes, extend original full
PVT/fault/load scopes before any adoption. This commit adds one evidence file;
older inventory totals predate it and must not be described as current totals.
Digital prefix trace38522829842 on691dc727 active. Original PLL38507479646 and
mainchip route38511490580 retain handles; no local artifacts/full goalsOPEN.


**Direct-supply native RC recovered and ready for exact device composition.**
Recovery38522280250 PASS; original extraction summary639469687 retained with
4083R/2673C and13raw-fault controls PASS. Recovery receipt639469765 verifies
original failed-publication run/artifact bytes; no native rerun. Source archive
639469443,6309420bytes,SHAbd4c6c6750d8247eb636bb4ec741733c0ce17e83641c18496c50e89b4640ef09
is now bound in composition input. Dispatch tx-layout-waveform-cloud with
final_drive_v8/critical_buses_kelvin_low_ports_loads_shunts_series_direct and
compose_only=true. Only after verified composition bind original hot/cold
loaded-tree simulation. Substrate/RF extraction qualification remains OPEN.

Exact digital trace_dedicated_preabc prepared: restore original candidate
archive and runtime, execute unchanged synthesis prefix up to original ABC,
require pre_map.v byte equality and protected-input hashes, then trace actual
inverters to public register aliases. This avoids inferring RTL bits from
optimized names. Dispatch once; no timing constraint or hardware mutation.
Native PLL38507479646/mainchip route38511490580 keep original handles.
All full goalsOPEN/cloud-only. This turn has actual passing new geometry/RC
and preserves the publication failure and recovery evidence.


**Direct-supply native extraction passed; publication-only failure recovery.**
38521648860/job115712481875 completed native extraction and all13raw corruption
controls PASS; Actions artifact11873244348 preserves516files/7118011zipbytes,
SHAb0243b497deb490258f86b6f7ef26d07d6fe29247e345dae5aacb9837a549e46.
Only permanent publication failed: extract group exceeds80characters. Shortened
that one variant's group; prepared recover_direct_extraction=true to verify
exact original run/source/step verdict/zipSHA/all layout output hashes and
publish original evidence. No native rerun. Dispatch recovery once; only after
published receipt bind composition. Preserve original failed run.
Digital provenance38521650812 summary639453860 contains exact source/recipe;
original candidate synthesislog639454282 and pre_map.v inventory are available
for exact register binding. No RTL-bit inference from generated FF names.
Cloud-only/full goalsOPEN; original PLL38507479646/route38511490580 remain live.


**New actual V8 direct-load supply layout passes native physical gates.**
38521214968 on88399e38 summary639446885:560DRC categories/zero markers,
strict hierarchical+flat LVS and original physical fault controls PASS.
All54devices preserved. Archive639446743 SHA42369bd4fe6b1abc0846bf2a85ea33411518fd508c178b065c958a5a97c7293c,
401366bytes, now source-bound in extraction input. Dispatch native extraction
for final_drive_v8/critical_buses_kelvin_low_ports_loads_shunts_series_direct
once. No electrical or fullPHY acceptance; original hot/cold gates still required.

Digital polarity readback38521217396 result639444756 completed but the three
limiting replay-register Qs have no surviving public alias through inv/buf
cells. Do not infer an RTL bit. Expanded readback now preserves exact archived
replay candidate source, synthesis recipe/inventory and original synthesis log
for a bound provenance diagnosis, no remapping. Dispatch trace_dedicated_endpoints
once on this source. Current route38511490580/PLL38507479646 retain handles;
cloud-only, all full goalsOPEN. Prior failed electrical studies remain intact.


**Actual final-load supply repair prepared from matched native evidence.**
Hot TC paired analysis38520023196: clock-to-MUX median9.489683ps compact versus
17.522559ps actual wire; source-to100mV max27.716935 versus39.218292ps. Final
data collector time-means fall123-146mV and tail emitters rise33-35mV. Compact
hot passes, wire fails. New V8 low_ports_loads_shunts_series_direct preserves
all54devices and existing geometry, adding direct actual resistor-supply landing
TM1 routes into the existing low TM2 feed. This is a physical hypothesis, not
an accepted fix. Dispatch tx-layout-repair-cloud with that variant/profile
final_drive_v8 once. Require original560DRC/strictLVS/fault controls before
fresh RC and original hot/cold electrical gates. No RC rescaling/threshold waiver.

Dedicated endpoint readback now follows exact mapped library inv/buf edges to
recover original RTL aliases behind Yosys flip_bits, retaining polarity and
complete cell paths. Dispatch trace_dedicated_endpoints once on this source;
no synthesis rerun. Existing route38511490580/PLL38507479646 remain live and
must not be duplicated. Previous goal turn: verified wait plus persisted
terminal evidence; this turn makes new source/geometry progress. Cloud-only,
empty local workspace, all three full product goals OPEN.


**Cloud-only execution and local retirement reverified.** Local workspace
`/home/hasanmelih/Documents/ChatGPT/nnsoc` has zero entries, including hidden
files. No local checkout, CAD run, simulation or test artifacts were created.
Retirement asset636387277 records nine archive batches, each with hosted
PASS_EVERY_REMOTE_ARCHIVE_MEMBER proof, and the final inventory. Source changes,
CAD, simulation, tests and durable results remain on GitHub. Continue cloud-only.

**Both paired hot TC waveform analyses are now terminal success:**
- Run 38520023196, summary asset 639420551, study v8_tc_hot, SHA256 `8d3585334599ba614e93ff53a70079c55b36950ce782005f2389e9f85e575e75`.
- Run 38520032724, summary asset 639420603, study v8_tc_hot_res_bcs, SHA256 `f57022cab578f067549a7a58c5937c7c3ea0e8694a1bf0fd6c7dfa4a16ddbf64`.
These statuses mean source-bound analysis completed, not PHY acceptance.
Next inspect the preserved per-device terminal drops, feed currents and stage
transitions before choosing an actual metal-layout repair. Keep original
compact/wire cases and engineering limits; do not repeat the native captures.
Dedicated endpoint trace38519890192 also completed (asset639416287): the new
limiting startpoint maps to `u_pcie.flow.packets.ack_sequence` bit0; endpoints
still need exact inversion/net binding before the next RTL candidate. Dedicated
mapping38519026139 improves slow PCIe setup to -1.046260ns, but fast PCIe hold
remains -0.109062ns; unplaced screen only, no physical adoption.

Existing PLL38507479646 and route38511490580 were freshly verified in_progress;
retain both handles and do not duplicate them. Dispatch the prepared PLL
acquisition review only after the original capture completes successfully.
Full serial PHY, routed main chip and final setup/hold remain OPEN. This update
records cloud handoff and terminal readbacks; it does not claim product closure.



**Both exact hot compact TC controls PASS; paired waveform diagnosis ready.**
38519483522 hot639412001: bitmin0.222802747V, finalCMmin1.848810921V;
hotres639411953: bitmin0.239085055V, finalCMmin1.836530301V; all original
engineering gates/pass/no numerical warnings. Same actual Nx4 device/native
feedback geometry as failed wire38517527891. Thus metal RC is the differentiator
for this pair; do not retune bias blindly or relax thresholds. Both compact
summary SHA/result bindings added under actual_geometry_followup.hot_compact_controls.
Dispatch hosted diagnosis v8_tc_hot and v8_tc_hot_res_bcs once. Their tests and
lossless raw verification precede actual physical-time node/current/delay
comparison. No SPICE rerun. Dedicated endpoint trace38519890192 is active;
PLL38507479646/route38511490580 retain handles. All goalsOPEN/cloud-only.


**Dedicated commit timing improves limiting PCIe path, closure still OPEN.**
38519026139 completed. Candidate639409787 slowPCIe-1.046260ns versus baseline
639407422 -1.101756ns; fastPCIe hold unchanged-0.109062ns. SlowCPU setup remains
positive but declines1.251946->0.520503ns; no physical adoption. Crucially worst
PCIe path now register1167360->1176745/43/48 instead of link_up->sent_data.
Prepared hosted trace_dedicated_endpoints restores exact two immutable archives
and binds BOTH all reported PCIe startpoints and endpoints to original mapped
RTL net aliases; input ports explicitly distinguished. Dispatch once; no STA
rerun or fuzzy endpoint matching. Compact hot TC controls38519483522 still
active; read-only paired analysis awaits source-bound summary publication.
Original route/PLL existing handles retained. All goalsOPEN/cloud-only.


**Causal TC-feedback hot controls38519483522 active; readback prepared.**
Only exact actualV8 hot_low/hot_low_res_bcs compact models run. Existing wire
38517527891 captures retained. Prepared tx-physical-tree-diagnosis studies
v8_tc_hot / v8_tc_hot_res_bcs require source-bound compact entries under
actual_geometry_followup.hot_compact_controls after native publication. Do not
dispatch readback until both summaries pinned. Selector requires exact two run
IDs/corner/bias/clock/54device profiles and equal source/oracle hashes; full raw
byte verification and physical-time voltage/current/stage-delay reductions on
hosted runner. Added foreign corner/geometry/bias controls. Diagnosis workflow
now manual-only to avoid rerunning an unrelated old default on source push.
Dedicated timing38519026139/PLL38507479646/route38511490580 remain live handles.
Cloud-only/full goalsOPEN; no candidate acceptance from preparation or tests.


**Paired hot compact controls prepared for causal physical diagnosis.**
ActualV8 wired TCfeedback38517527891 failed bothhotcases while bothcoldcompact
passed. No same-hot compact captures exist for this exact feedback geometry;
without them DC/bias and metalRC penalties cannot be separated. New study
v8_feedback_tc_compact_hot runs onlyhot_low/hot_low_res_bcs using exactV8
compact model, sameall54devices/feedback/native clocks/sourcebits/limits and
no Nx or artificialR mutation. Pair with existing wire639381366/639379188;
then run read-only full-wave actual-node/current/stage-delay analysis in cloud.
Do not rerun existing wire or cold cases. Dedicated timing38519026139,
PLL38507479646 and route38511490580 remain current livehandles/fullgoalsOPEN.


**Corrected dedicated-commit proof PASS; paired timing38519026139 dispatched.**
38518875447 summary639394358 passes3all-state proofs(refresh128/0/1), both
wrong-owner/wrong-data counterexamples, baseline5/candidate5positive port tests
and5expected negative failures, no skips. Original preparation failure remains
639387011. Corrected parent declaration has samelogic; exact source/candidate
hashes saved in ACK evidence. Mapping onac549474 reruns proof and source bindings,
then original all-corner reports, no timing exceptions. No timing/adoption claim.
All actualNx4 TC cases38517527891 terminal2coldPASS/2hotFAIL, allHBT boundsPASS;
no need rerun that rejected study. See latest structured receipts for actual
hot bit/CM/differential failures. Route38511490580 and PLL38507479646 retain
existing handles. Full goalsOPEN; cloud-only. Turn classification: progress
(measured rejections, direct internal commit path, fixed Icarus preparation,
complete proof+ports and new paired native timing dispatch), no genuine blocker.


**Dedicated-commit preparation failure fixed, prior failure retained.**
38518563421 summary639387011: all3formal cases and2negative proofs passed,
but candidate Icarus elaboration rejected selected_ready declared after its
new port connection; no candidate port-test pass claimed. Move that existing
wire declaration before advertiser instance, and explicitly preserve it in
extracted formal region. No logic or threshold change. Port preparation errors
now retain the actual simulator tail before missing-XML assertion. Rerun the
same dedicated study once on corrected source; map only after all port tests.
ActualNx4 TC results all4terminal: cold2PASS, hot639381366FAILbit0.075877689V,
CMmin1.787411677V/diffmin0.148238710V; hotres639379188FAILbit0.098371279V,
CMmin1.773306078V. All actual HBTs pass; no diagnostics. Matching actualgeometry
improves hot margins/removes old selector failures, but not enough: no adoption.
Route38511490580/PLL38507479646 remain retained; cloud-only/full goalsOPEN.


**Bank-EOP mapping rejected; dedicated internal commit port prepared.**
38517610171 completed. Baseline639376752 slowPCIe-1.101756ns;
candidate639375563 slowPCIe-1.391512ns, fastPCIehold both-0.109062ns.
Formal equality did not remove the structural arbitration fan-in to the credit
bank enable; direct-EOP OR still retains chosen's input cone. New
variant=dedicated_commit gives only sent header/data bank updates an internal
commit_ready_i bound directly to selected_ready; original tx_ready_i handshake
and all other state remain unchanged. Joint ownership/all-state proof required,
not assumed; same wrong-owner/corrupt-data controls and original port tests.
Dispatch cloud-migration-checks advert_dedicated_commit=true once, then paired
mapping study=advert_dedicated_commit only on proofPASS. No constraints waived.
ActualNx4 coldcases639363894/639364278PASS; hot jobs38517527891 still active at
last check. PLL38507479646/route38511490580 retain currenthandles. All goalsOPEN,
cloud-only, no local artifacts. Previous turn verified wait then new terminal
slacks changed next action; this source repair continues real closure work.


**Direct EOP proof PASS; mapping38517610171 active.** Proof38517360412 summary
639356884 passes3all-state induction/2counterexamples/10positive ports; no skips.
No mapping/adoption claim yet. Do not rerun proved candidate or rejected bank-only
trial. Actual native Nx4 TCfeedback study38517527891 source1087cab6 is active,
using V8 layout's own4021R/2638C and device geometry, no Nx substitution. Four
independent corners; previous mixed-V11geometry run38516411596 fully terminal,
2coldPASS/2hotFAIL and retained in structured receipts. No feedback candidate
accepted. Full exact source/results/hashes saved in ACK and V11 evidence docs.
PLL38507479646 and route38511490580 freshly verified in_progress. All local
workspace contents remain retired; calculations/test/layout in cloud only.
This turn progressed via measured rejections, proved direct-EOP repair and
actual-layout followup dispatch; no genuine blocker. All full goalsOPEN.


**Direct EOP proof live38517360412/job115699056790** on1087cab6. Three all-state
proofs and both original negative controls required before paired mapping.
**TC feedback mixed-model sensitivity terminal:** all4cases complete; cold HBT
639337663/coldres639337673 PASS, hot639352416 FAIL(bit0.061058441V,64sub100mV,
finalCMmin1.784874467V, finaldiffmin0.147553398V), hotres639352027 FAIL(bit
0.084393708V,28sub100mV,CMmin1.770927243V,4selectorVCEfail,min0.398006589V).
No candidate adopted. Do not describe cold-only success as closure.
Actual V8 Nx4 layout RC comparison study=v8_feedback_tc_physical dispatched
once on1087cab6: find newest matching Actions handle. Purpose is to replace the
V11 geometry/device-mutation approximation with real matching Nx4 geometry;
this is diagnostic continuation of a failed candidate, not acceptance. Feed
layout/contact/assembledRC remain open. Keep every original bit/electrical gate.
Bank-only mapping terminalreject assets639343644/639343787 unchanged. Preserve
original route38511490580/PLL38507479646; cloud-only/full goalsOPEN.


**Bank-only commit timing rejected; direct EOP path prepared.** Paired mapping
38516179454 terminal: baseline639343787/candidate639343644. SlowPCIe setup
-1.101756 -> -1.171506ns; fastPCIe hold unchanged-0.109062ns. Candidate not
adopted despite CPU setup improvement. Original worst path has28combostages
fromlink_up through packet selection into sent_data. New bank_eop combines
separate-bank update with advert_ready=selected_ready&&(advert_eop||
(local_reset&&!chosen)). At activeEOP, existing ownership invariant must be
proved jointly, not assumed; SOP arbitration unchanged. Require all-state3
proofs/2corrupt controls/10positiveports before mapping. Prepared workflow
advert_bank_eop=true then study=advert_bank_eop. No relaxed SDCS or latency.
Analog38516411596 two coldcasesPASS; hotpending. ActualV8 TC followup prepared
but not dispatched. Route/PLL existinghandles remain; cloud-only/full goalsOPEN.


**Actual Nx4 layout source located; avoid redundant generation.** Existing V8
low_ports_loads_shunts_series composition38492591399 already contains exact
Nx4data/Nx6selectors/all other same devices, with54native devices,
4021R/2638C, wireSHA6153ffd201d601c05f663279e7489307d2bec63a55755713b6730ff99b1f94ac.
560DRC/strictLVS/fault checks are preserved in its source-bound receipt. This is
not the V11-sized geometry with edited devices. Prepared study
v8_feedback_tc_physical uses that existing actual layout RC and new native
TCfeedback, diagnostic-final-nx=0/no mutation. Four original independent corner
conditions; feed itself still lacks layout/RC/contact qualification. Dispatch
once after current v11_feedback_tc results justify it; no new layout rerun.
Current TC cold_HBT summary639337663 and cold_res summary639337673 PASS all
original electrical gates, finalCMmax2.028879602/2.036255106V. Hot cases pending.
Bank-commit mapping38516179454/PLL38507479646/route38511490580 retain live handles.
Full goalsOPEN, cloud-only. Study names in future release groups now explicit.


**Live exact followups — no duplicate dispatch:** bank-commit mapping38516179454
on94fddbcb, jobs115695382300(candidate)/115695382415(baseline), in progress.
Native fixed-temperature-feedback study38516411596 onddf1dad1:
hot_low115696109323, hot_low_res_bcs115696109823,
cold_high_hbt_wcs115696109657, cold_high_res_wcs115696119210. Four native
cases, no artificialR and no thresholds changed; geometry is a schematic
candidate, not adopted layout. Every job runs source-bit/graph controls before
SPICE. Original PLL38507479646 and route38511490580 confirmed live; do not
restart. Structured proof/result bindings and next_actions updated. Local
workspace verified empty. This turn progress: new proven digital candidate,
paired timing dispatch, process-sourced analog compensation implementation
and four hosted native dispatches. Full goals OPEN; no genuine blocker.


**Bank-commit proof PASS and paired mapping active38516179454.** Proof38515965607
summary639323020 passes3all-state induction/2counterexample controls/10positive
ports; FCcandidate0674e68fb0e83f20cdfbaf6ed87e8eb885040a245caa24f69c946c4e414185c4.
No timing/adoption claim. Wait paired native phases, preserve constraints.
**Native feedback temperature compensation prepared:** study=v11_feedback_tc
uses fixed Nx4 and physical actualR/C (no artificial-R change), hot_low and
hot_low_res_bcs wired; cold_high_hbt_wcs and cold_high_res_wcs compact. Only
prestage feedback switches to100um/1um Rsil +26.5um/2um Rppd per output branch,
original feedback remains available. Source: IHP Rsil3100ppm/K, Rppd170ppm/K
process targets; hypothesis reduces hot current without raising cold CM.
Native frozen PDK models/unchanged source bits and all existing gates decide.
Feed layout/RC/contact current qualification not yet implemented; no physical
acceptance even if schematic passes. Dispatch once after hosted graph checks.
PLL38507479646 and route38511490580 retained; cloud-only/full goalsOPEN.


**Direct per-bank credit commit candidate prepared.** Rejected static case mux
is not adopted. New bank_commit starts from exact original physical21-file
idle/credit baseline and moves only committed header/data slices into three
separate reset processes with direct active/ready/EOP/class enables. Original
link reset priority/storage/latency/parent arbitration/SDC unchanged. Require
all-state region induction(refresh128/0/1), wrong-owner/wrong-commit controls,
and ten positive buffered port tests before paired mapping. Dispatch
cloud-migration-checks advert_bank_commit=true once, then map advert_bank_commit
only if proof passes. New mapping profile preserves all corners, original log
phase metrics and candidate post-run hashes. Route38511490580/PLL38507479646
still verified live. No other study rerun; cloud-only/full goalsOPEN.


**Hosted review controls verified PASS.** Run38515404789/job115692961239 on
21a533c97ccfb0c06eff97fa2e2f5f3b581fa77a passed snapshot4fault controls,
acquisition frequency/phase/missing-edge/voltage faults and truncated/nonfinite
rejection, with positive locked-wave control. Other hosted regressions71+352PASS;
license/SPDX/inventory checksPASS. No local tests or artifacts. Original
PLL38507479646 and route38511490580 freshly verified in_progress; retain handles.
Next dispatch pll_acquisition_review=true only when original PLL run completes
successfully; do not rerun native. Completed serializer diagnostics/electrical
results and warning recorded in5224c996. Previous turn classification: progress
(source implementation, hosted validation, new terminal electrical evidence).
Full PHY/routed main chip/final setup-hold remain OPEN, no genuine blocker.


**Original PLL acceptance review prepared, not yet dispatched.** Existing
38507479646 native1us capture remains live. New cloud-migration-checks input
pll_acquisition_review reviews only that exact source444e78eb/run attempt1 after
successful completion. Restores exact published archive, original source deck,
parent, all35model/OSDI bytes, native log and complete raw payload. Reuses frozen
original100ppm/50ps/no-slip/VCTRL pure functions with locked/frequency/phase/missing
edge/voltage/truncation/nonfinite controls. No new simulation or fitted phase.
Cloud push self-tests must pass before dispatch; wait original capture completion.
32:1wire38496981217 summary639289318 has nominal electrical gates PASS, but a
native max-data-size warning keeps component_screen_passed=false. Preserve this
warning; not fullPHY acceptance. Nx4 internal-R summary639293994 improves bit
margin to0.101510901V but finalCMmin1.780957413V fails; all-R639281758 bit0.168537233V
also fails finalCMmin1.780405857V. Output-R639290449 bit0.068951690V fails. No
physical candidate adopted. All goalsOPEN; empty local workspace/cloud-only.


**Cloud-only handoff reverified; static-commit timing candidate rejected.**
Hosted readback38514837826 completed; result639294592 preserves every original
corner/group and exact mapped RTL endpoints. Baseline/candidate slow PCIe setup
-1.101756/-1.180261ns; fast PCIe hold unchanged -0.109062ns. Fewer cells
(79578/78976) did not improve the limiting setup corner. No adoption.
The 32:1 wire run38496981217 completed execution; electrical acceptance still
requires its published review. Combined Nx4 diagnosis38513890541 all-R and
output-R cases completed but both fail original engineering gates (summaries
639281758/639290449); internal-R case remains pending. Artificial R is never
physical acceptance. Route38511490580 and PLL1us38507479646 remain on their
existing active handles. Do not rerun completed studies or active native jobs.
Retirement636387277 again reports COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE;
local project directory was directly verified empty. No local artifacts created.
All full goals OPEN. Continue source-bound repairs and acceptance checks in cloud.


**Static-commit native mapping results published:**38513559584 baseline79578
cells(summary639278022), static candidate78976(summary639278671). Original report
hashes and archives pinned in new read_static_reports study; run this hosted
readback once to compare all6corner/type groups and bind critical RTL endpoints.
Do not infer timing success from602fewer cells. Future mapping controller now
includes all original reported phases in its result, bound to native log hash,
so follow-ups need not restore archives solely for slack readback. Current jobs
not changed/rerun. Remaining route/PLL/serializer diagnostics preserve live
handles; all full goalsOPEN/cloud-only.


**Exact active handles, source verification complete:** paired static-commit
mapping38513559584 on0dd9c255 has baselinejob115687234616 and candidate115687234836
live. Formal38513261561 already passed3induction/2negative/10positiveports; await
actualslacks before adoption. Combined Nx4 final-R diagnosis38513890541 dispatched
ondf2404db withall/internal/outputs classes. Compact and wire BOTH receive same
source-bound12data Nx4 transform before metal ownership validation; no relaxed
model/parameter checks. Every result remains nonphysicalacceptance. Compare
against original Nx4hotwire639239046; retain allC/upstreamRC/originalbitgates.
Do not rerun original sizing38511840985 (all8terminal,4coldPASS4hotFAIL).
Route38511490580,PLL1us38507479646 andoriginal32:1wire38496981217 allverifiedlive.
All code/evidence pushed; no local files. Next: inspect mappedslacks, causalRC
results and exact route terminalstate. All full goals remain OPEN.


**Static credit commit proof PASS / paired mapping38513559584 dispatched:**
proof38513261561 summary639256379 passes three all-state region proofs(refresh
128/0/1), wrong-grant and corrupt-commit counterexamples,10positive ports and
5expectednegative failures. Parent hash unchanged459d69dd, candidateFC91d54c37.
Mapping baseline/physical_idle_credit_static on0dd9c255 is active; do not adopt
before actualtiming. Area study38511840985 all8terminal: fourcoldcompactPASS,
fourhotwireFAIL, allHBTboundsPASS. Nx4 is least bad hot bitmargin0.063875817V,
64sub100mV samples, finalCMmin1.777817100V. No sizing candidate accepted. All
summary hashes/reviews retained in V11 receipt. Next diagnostic prepared:
tx-interconnect-diagnostic-cloud study=v11_nx4_wire_rc compares artificial1percent
all/internal/output final metalR, retaining allC/upstreamRC and originalbits.
Always diagnostic; never use substitutedR as physicalfix. Dispatch once to
identify whether real final geometry repair can address remaining hot failure.
Route38511490580,PLL38507479646 and32:1wire38496981217 retain existing live handles.
Cloud-only; fullPHY/routedmainchip/finaltimingOPEN.


**Static-commit proof dispatched38513261561** on8a51acdd; do not duplicate.
Paired map option advert_static_commit prepared, but dispatch only after proof:
physical_idle_credit vs physical_idle_credit_static, exact21sourcebindings,
unchanged SDC/corners/runtime. Mapping reruns fullregion proof including corrupted
commit control; every candidate source SHA rechecked after native synthesis/STA.
Callable proof main now takes explicit argv so embedding does not parse the
mapping --profile argument. No existing live work changed. Other native handles
in previous checkpoint remain active; all full goalsOPEN/cloud-only.


**Exact timing trace identifies the next RTL repair:**38512839026 PASS, summary
639244698 binds actual worst baseline register to advertiser.sent_data_o and
rejected candidate to sent_data_o/header_o, preserving mapped JSON source hashes.
New run_cloud_advert_control.py --variant static_commit replaces dynamic class
slice writes with three explicit fixed slices under unchanged accepted-EOP
/reset/link priority. Parent RTL/ready/valid unchanged (not rejected factoring).
Require full-region all-state induction refresh128/0/1, wrong-grant AND corrupted
committed-data counterexamples, plus full buffered port tests. No candidate
adoption/timing claim. Dispatch cloud-migration-checks advert_static_commit=true;
map only after native proof evidence. Existing route38511490580, sizing38511840985,
PLL38507479646 and32:1wire38496981217 remain live; no duplicate dispatch. All goals
OPEN/cloud-only. Trace and archived failed candidates retained.


**Timing critical endpoint tracing prepared:** readback logs show worst unplaced
PCIe setup starts at pcie_link_up_i, then a long combinational path. Baseline
endpoint$auto$ff.cc:337:slice$1165056; rejected control endpoint$auto$ff.cc:337:slice$1678497.
Before another RTL trial, new pcie-ack-cloud-mapping study=trace_control_endpoints
restores SHA-pinned paired archives, binds every reported PCIe endpoint exactly
to original mapped JSON/master/connections/RTL aliases, rejects missing matches,
and preserves source attributes. No synthesis/STA rerun or false-path exception.
Dispatch once. Nx4 andNx6 coldHBT compact summaries639230237/639236749 also pass
original gates; hotwire and unchangedNx8 controls still pending/live. Do not
select a sizing candidate yet. Route38511490580,PLL38507479646 and32:1wire38496981217
remain live; all computations cloud-only and goalsOPEN.


**Native placement checkpoint available, routing still live:**38511490580
pre-route summary639222493 passed exact connectivity/master/fixed-cell/pin
geometry checks and both fault controls.74988combinational cells selected,
73075moved, zero dataflops moved; all20 Ethernet hold cells retained/fixed.
Three-corner placement estimates completed (slowPCIe setup-1.887568ns,
fastPCIe hold-0.065139ns; CPUfast hold-0.055513ns); these are NOT routedSTA.
Candidate ODB9852cb580aa0930e8813569678121b5600bb1b78ecd4d51ce35572449acbf8b8.
Wait same native globalroute job115680796118. First sizing resultNx5 coldHBT
compact38511840985 summary639226840 passes original electrical gates at fixed
feedback32um (minimum bitmargin0.256630731V, finalCMmax2.043107421V, allHBTbounds
pass); diagnostic ONLY, altered emitter geometry has no new layout/RC. Other
seven cases still live/queued. Do not select from this one cold result.
Authoritative retirementasset636387277 reread: COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE.
Closure-continuation JSON next_actions refreshed to these actual handles;
older physical results retained as history. PLL38507479646 and32:1wire38496981217
still verified live. All full goalsOPEN; no local files/CAD/tests created.


**Dispatched cloud handles; do not duplicate:** routability_data38511490580,
job115680796118, sourceec864e8484c146ea204d46ce6aa2f284ca4b73f7 reached native
postCTS replay/placement/route step; syntax/runtime preparation PASS. Serializer
area study38511840985, source43fb19cc63765c28a4a90e2474789dfe1f59cc74:
Nx4/hot_low job115681875537 passed hosted graph/originalbit/device-area fault
checks and entered native transient. Remaining7cases queued at latest check;
maxparallel4, do not infer failure from parent queued status. New Nx4/5/6 and
unchangedNx8 control are ALWAYS sizing diagnostics, not accepted extracted
layouts. Review original bits, CM, all-device VBE/VCE/current across both
corners; only then decide physical geometry rebuild. Current fixed feedback32um
must also receive actual layout/RC before acceptance. PLL1us38507479646 and
full32:1wire38496981217 confirmed live this turn. All full goalsOPEN. Prior
turn made progress (new source-bound placement+sizing implementations, hosted
checks and native dispatch); no genuine blocker and no restart authorization
inferred from observation timeouts. No local project files produced.


**Active routing and bounded serializer sizing study:** routing38511490580
sourceec864e84 dispatched once with routability_data/hold2/seed13/baselineOBS;
check its exact handle. New tx-interconnect-diagnostic-cloud study=v11_data_area
compares data HBT Nx4/5/6 against unchangedNx8 control, fixed feedback32um,
cold_high_hbt_wcs compact and hot_low wire (8cases). This tests device-area
tradeoff before spending on new geometry. Exact12data devices only, every
other transistor/R/C untouched, original sourcebits/phase/device limits kept;
contract emitter counts follow actual modified device model. Fault tests reject
missing/duplicate/wrong-Nx/wrong-model targets. Sizing results are ALWAYS
notphysicalacceptance: changed devices require fresh layout/LVS/RC/PVT.
Dispatch this study once. Existing PLL38507479646 and32:1wire38496981217 still
live. All work cloud-only; all full goals OPEN.


**Next concrete routing repair prepared: routability_data** in newer-postcts-cloud.
Restores exact seed13baseline132overflow run38448901835 placement and its native
probe38471402795 (SHA-bound). GPL skip_initial_place+routability_driven density0.55
spreads original combinational data cells; no timing-driven resize. All sequential
cells, clock-connected cells, macros, boundarypins, and20proven Ethernet hold ECO
cells remain fixed. Exact all-instance/master/net checks, pin geometry, fixed
placement and two fault controls precede three-corner STA and fresh zero-overflow
routing seed13/capacityperturb0/normalmacroOBS. Never adopt from placement alone.
Dispatch newer-postcts-cloud placement_profile=routability_data,
ethernet_hold_depth=2,routing_seed=13,macro_routing_profile=baseline. Push no longer
starts duplicate legacy route. Runtime semantics checked against exact OpenROAD
dcf36133 sources replace.tcl/replace.cpp/placerBase.cpp/Replace.h, not assumed
from current documentation. Prior rejected halo155overflow/controlsetupregression
remain preserved. Existing PLL38507479646 and32:1wire38496981217 verified live.
Cloud-only; local workspace empty; all full goalsOPEN.


**Readback publication CLOSED, design closure still OPEN:** corrected hosted
read_control_reports38510653124 PASS including permanent read-back-verified
publication. Summary639191271, original baseline log639191336 and candidate
log639191430 retained; six-corner/type reports and all groups pinned in ACK
receipt. Control factoring candidate rejected for slow PCIe setup regression
(-1.101756ns baseline, -1.463237ns candidate), no fast hold improvement. Do not
repeat map or readback. Exact halo congestion diagnosis38509934192 also done;
next routing repair should address its native145markers/155overflow using
summary639175302 and actual endpoint/pin/OBS data. V11 lowinputR diagnosis
38508878110 rejected; do not substitute synthetic R. Existing PLL1us38507479646
and V10 full32:1wire38496981217 remain live as last verified. Local workspace
rechecked completely empty. All source, computations and artifacts on GitHub.


**Terminal cloud readbacks:** congestion38509934192 PASS exact diagnosis only:
145markers/155overflow,1095congested nets bound to actual endpoints; exact
four Ethernet SRAM pin/OBS geometries retained. Summary639175302/archive639175114
pinned in halo1 failure receipt; no route closure. Control report38510367472
native readbackPASS; candidate REJECTED: PCIe slowsetup -1.101756ns -> -1.463237ns,
fasthold unchanged -0.109062ns. Do not adopt smaller-cell candidate. All groups
and original logs retained in artifact11869582286. Permanent upload failed
because runner default Python lacks hashlib.file_digest; explicitly pin3.12
and redispatch read_control_reports ONLY (no synthesis rerun). Pending next
repair should use original retained route and timed baseline, not these rejected
candidates. PLL38507479646 / original32:1wire38496981217 retain live handles.
All computations cloud-only, local directory empty, all three full goalsOPEN.


**Cloud-only continuation:** workspace remains empty. Exact halo1 congestion
probe38509934192 dispatched onbc43f91e; do not duplicate. Main route stays
rejected with155overflow. Control mapping38509087565 is terminal: baseline79578
cells, candidate79555, but no adoption or timing claim. New mapping study
read_control_reports restores both SHA-bound original reports on hosted runner,
parses all reported groups and compares all three corners without resynthesis.
Dispatch this readback once. V11 input-R sensitivity38508878110 terminal FAIL
original gates despite artificial1percent final inputR: bit margin0.020459546V,
97sub100mV samples, six dataVCE failures, minimum0.374675481V. It cannot replace
real RC/geometry. Summary639166681 and exact metrics pinned in V11 receipt.
PLL1us38507479646 and original32:1wire38496981217 still live at latest check.
FullserialPHY, routedmainchip and finalsetup/hold remain OPEN.

**Mainchip route38490952579 is now TERMINAL FAIL, not live:** halo1/seed13
finished native73/100 with GRT-0230 non-improvement then GRT-0116 congestion;
155totaloverflow (M2=1,M3=14,M4=22,M5=104,TM1=11,TM2=3). Not a timeout.
Compared with seed13 baseline132overflow this halo candidate is rejected.
Exact summary639128927,archive639128646 (162878296bytes), failure ODB/guide/log
and congestion hashes retained under halo1_terminal in seed13 failure receipt.
Next action: dispatch newer-congestion-probe-cloud source_profile=
halo1_seed13_buffers, which restores exact failed ODB/report and resolves every
marker/endpoints/macro pins before another repair. Do not rerun same route,
inflate capacity, remove OBS or waive overflow. No detailed routing acceptance.
Timing control mapping38509087565 and V11inputR38508878110 are live; PLL1us
38507479646 and original32:1wire38496981217 retain existing live handles.
Other analog cases indexed in V11 receipt; all full goals remainOPEN/cloud-only.


**Verified new timing proof; native comparison is now dispatched:** control
factoring38508286832 PASS three full-state region induction cases(refresh128/0/1)
and10positive ports; wrong-grant control rejected in formal and all5port tests.
Summary639147659/archive639147458 pinned in ack-window evidence document.
Paired mapping38509087565 dispatched on149746ab: physical_idle_credit versus
physical_idle_credit_control, unchanged clocks/corners. Candidate not adopted;
need actual metrics before any physical ECO. Do not confuse with rejected EOP.
Metal38508868002 finished both actual graph+geometry diagnoses: cascade158
summary639149467 and V11summary639149461; concise measurements pinned in V11
receipt. Final data input paths~8.5..8.9ohm; internal worstpairs15.49..18.65ohm.
Prestage output-to-device~8..9.5ohm, internal worstpairs~23.79ohm. These are
DC diagnosis only. Actual geometry-bound files/negative controls preserved.
V11 artificial inputR diagnostic38508878110 still running at last check;
never adopt its synthetic lowR as a physical fix. Combine with real hotwire
failure38507486510 to choose new geometry/device repair. V11feedback32um
38507831996 has3/4compactPASS; coldresCMmax2.052879127V still fails2.05V.
Latest available actual waveform summaries indexed in V11 receipt; other
wire cases remain live until their exact jobs say terminal.
PLL1us38507479646,mainchiproute38490952579,original32:1wire38496981217 continue
on their existing handles. All cloud-only; local empty. FullPHY/mainchiproute/
finalsetup-hold remain OPEN; this turn made source/proof/diagnostic progress.


**Cloud diagnostics dispatched and guarded timing mapping prepared:** V11 actual
metal/geometry diagnosis38508868002 and artificial input-R sensitivity38508878110
are dispatched on1e74f55c; do not duplicate. Source-bound actual hotwire failure
38507486510 remains baseline, not overwritten by sensitivity results.
Advertiser control proof38508286832 has reached native formal/port checks.
New pcie-ack-cloud-mapping study=advert_control compares physical_idle_credit
with ONLY the reset/valid/ready factoring; no ACK-window/EOP refinement. It
reruns complete region proof, negative control and buffered tests and checks
all21 physical source hashes before replacing exactly parent+FC RTL. Dispatch
mapping only after reviewing38508286832 result. Original SDC/corners unchanged;
no synthesized/placed/routed success asserted. Existing analog/PLL/route jobs
retain handles in preceding checkpoints; all cloud-only and all goalsOPEN.


**V11 hot-wire rejection drives physical diagnosis:** real hot_low wire result
639132211 from38507486510 FAILS: originalbit margin0.011488287V, final interface
margin0.133128903V/64sub150mV samples, CMmin1.78408764V, sixdata VCE failures
(min0.374674096V). Cold_high wire639137215 passes (margin0.250125171V).
Never adopt V11 from nominal/compact passes. V11feedback32um compact results:
3/4PASS; coldresCMmax2.052879127V still fails2.05V. Wire cases remain active.
Next hosted diagnostics prepared: tx-metal-resistance-cloud profiles=
v11_loaded_tree,bind_geometry=true (exact cascade158 and V11 original graphs),
and tx-interconnect-diagnostic-cloud study=v11_hot_low_inputs,cases=mutations_only.
The latter artificially reduces ONLY final input metal R, retains all devices,
C, actual upstreamRC and original sourcebit/device gates. ALWAYS diagnostic,
component_screen_passed=false: never a replacement for real layout or PVT.
Compare against actual hot_low wire38507486510 to locate geometry to repair.
New timing proof38508286832 advertised-control remains queued at last check;
source/license jobPASS. Existing1usPLL38507479646,route38490952579,32:1wire
38496981217 retain live handles. All hosted, local empty, all goalsOPEN.


**Independent setup-path candidate prepared:** run_cloud_advert_control.py uses
exact21-file physical idle/credit source, without earlier rejected EOP-ready
rewrite. Remove internal ready reset gate, tie advertiser link high beneath
unchanged actual local_reset, and drive advertiser valid from reset-cleared
active state. No new latency, timer/state/clock/constraint change. Full-region
SAT induction on all storage/output, arbitrary reset/link/clock, refresh128/0/1,
complete buffered ports and wrong-grant counterexample required. This is an
UNPROVEN candidate; dispatch migration workflow advert_control=true, then map
only if proof passes. Do not adopt or reuse earlier reset/EOP timing results.
Analog combination38507831996 first coldHBT compact result639126842 PASSES
all original bit/device/interface gates (margin0.2560095V,CMmax2.04145454V).
Other paired corners and physicalwire still active; no broad acceptance.
Existing V11 baseline,1us PLL38507479646,route38490952579 and32:1wire38496981217
retain their handles. All computations/evidence cloud-only; all full goalsOPEN.


**Latest actual native progress and exact live handles:** source444e78eb.
PLL exact continuous1us capture38507479646/job115668187421 is running actual
native code; sibling source/license checks PASS. Do not repeat snapshot failure
38503868241 or restart this acquisition while its job exists/live.
V11 corrected native nominal38507129843, PVT38507486510 and failing-corners
38507494960 are running.355 hosted source/capture/receipt tests passed. Available
summaries/hashes retained in V11 receipt loaded_screen_partial_20261014.
Compact nominal passes (minimum originalbit margin0.280521955V); hot_low passes.
Compact cold_high_hbt_wcs now passes ALL transistor limits (V10 had12VBE fails),
but CMmax2.063234901V fails2.05V. ColdresCMmax2.076627404V also fails. HotHBT
compact12data VCE fail, worst0.394913256V below0.4V. No waived margins.
Combination experiment38507831996 dispatched on444e78eb: same exact V11 RC,
4streams,matched compact/wire,failing_corners,cascade158,stiff65,pre_bias=
output_feedback (fixed32um). This targets cold CM and hotdataVCE; selector
headroom/whole-device/originalbit checks must still pass. Feedback circuit
itself has no assembled layout/RC; do not call this fullphysical integration.
OriginalV10 full32:1wire38496981217 and mainchiphalo1route38490952579 remain
live at last observation. Check exact handles next; do not duplicate.
Critical-route publication fix38506144487 succeeded in all6 publication steps;
oldvariant RCfault failures remain recorded separately from archive transport.
All work/output stored on GitHub, local workspace empty. FullserialPHY,
assembledmainchiprouting and finalsetup/hold remain OPEN.


**Exact1us native865 cloud continuation prepared:** cross-process snapshot run
38503868241 segfaulted on snload/restore (-11); immutable failure summary639099695
and archive639099391 are pinned in parent865_snapshot_failure_20261014. No
snapshot is accepted or used. New pll_acquisition=true option in migration
workflow runs exact historical1us deck fresh from timezero, selected24probes,
original models/OSDIs/circuit/rails/startup/.3125ps/KLU/tolerances. Native output
streams to acquisition.raw;20800s safety deadline leaves time to preserve
incomplete evidence before6h hosted ceiling. Measured50ns runtime994s implies
~19888s for1us, an estimate not a promise. Complete capture still requires
fixed lock/slip/phase review and all-device safety/PVT; no inferred acceptance.
Dispatch once with pll_acquisition=true after source checks. Corrected V11
nominal38507129843 already reached native after tests; initial missing-counts
failures retained. Other initial corner runs may finish with same harness
failure; confirm terminal before replacing. Route38490952579 and original
32:1wire38496981217 retain handles. Local remains empty; three goalsOPEN.


**V11 harness repair / PLL snapshot terminal failure:** V11 initial loaded runs
38506756540/38506767529/38506778818 stop before native simulation: receipt lacked
counts. Added exact counts from immutable native composition (54devices,
4023R,2640C), plus supported-receipt schema integration control. Original failed
runs retained. Dispatch corrected nominal first; inspect hosted schema tests
and actual native start before repeating other corners.
PLL snapshot38503868241 is TERMINAL: continuous50ns and same-process resume50ns
finished in994/987s with complete25-column captures, but fresh-process restore
segfaulted(return -11). Snapshot NOT validated. Summary639099695,archive639099391
retain full failure; no cross-process acquisition chaining allowed. Reduced
selected-probe output took~20s/ns on hosted runner; assess exact1us native run
against hosted6h ceiling without changing sources/step/tolerances/lock gates.
32:1wire38496981217 and mainchiproute38490952579 remain live. All cloud-only.


**V11 composed native device/RC is ready for loaded simulation:**38506404916
passed binding on6be7d443. Summary639089844,archive639089513; immutable receipt
pcie-final-v11-kelvin-low-ports-loads-shunts-series-composition-20261014.json.
Added exact v11_kelvin_low_ports_loads_shunts_series profile to loaded-tree
runner/workflow and mismatched-archive/emitter-count controls. Dispatch matched
4stream nominal,temperature_voltage and failing_corners using cascade158
kelvin_supply_direct,clock_reference=stiff65,pre_bias=native_res first. This
isolates new final devices from the rejected feedback topology; do not accept
without actual original-bit/whole-device waveforms. No old RC scaling.
Feedback32um38505258788 TERMINAL: all8 actual summaries/hashes retained in V10
receipt output_feedback_32um_rejection_20261014. Candidate rejected: hot wire
CM and selector VCE failures plus cold compact VBE and cold wire selectorVCE.
Publication repair38506144487 now stores results in per-run releases; older
baseline topmetal/critical variants fail RC fault controls, not asset limit.
PLL38503868241,32:1wire38496981217,mainchiproute38490952579 retain live handles.
All work hosted; local empty; fullPHY,mainchiprouting,finalsetup/hold OPEN.


**V11 actual RC passed and is now bound for native composition:** hosted run
38506058339 passed real graph validation and 13 corruption controls. Exact
archive639080897 and summary639081033 are recorded with SHA256 in composition
input under final_drive_v11. This is unqualified wire-only RC, not RFPEX or
waveform acceptance. Dispatch tx-layout-waveform-cloud.yml compose_only=true
with final_drive_v11 / critical_buses_kelvin_low_ports_loads_shunts_series.
After native device binding passes, pin its archive into loaded-tree source;
never reuse V10 device/RC data for V11. PLL38503868241,32:1wire38496981217,
mainchiproute38490952579 and feedback32um38505258788 retain their handles.
Cloud result publication fix is under hosted validation in38506144487.
No local project files; full PHY/routing/final timing all remain OPEN.


**Cloud-only handoff verified:** local NSSOC workspace is empty. V11 fresh RC
run 38506058339 dispatched on 6fec8f05f0ed5c67684471e4585fdece32c6f510,
profile final_drive_v11 / critical_buses_kelvin_low_ports_loads_shunts_series.
Do not duplicate. Verify extraction and all fault controls before composition.
PLL snapshot 38503868241, feedback32um 38505258788, full32:1 wire 38496981217,
and main-chip routing 38490952579 still have active native jobs.
Automatic legacy critical-route run 38505551015 hit GitHub release's 1000-asset
limit during publication to cloud-migration-20261012-000. This is an archive
failure, not proof of electrical acceptance. Switch that workflow to existing
source-bound per-run/group publisher; retain full transient artifact fallback.
The old failed run and its available composition artifacts remain preserved;
its failed native-wave publication must not be claimed permanently archived.
Fresh push-triggered run verifies the changed publication path on hosted runners.
All simulations, tests and persistent project artifacts stay on GitHub.
Full serial PHY, assembled routing and final setup/hold remain OPEN.


**V11 physical result verified and bound for fresh extraction:**38505016479 on
16ff1e202cf713dc4b50c12126c241109013377e passed actual native geometry gates:
560DRC categories/0markers; strict hierarchical+flat54-device LVS;5intentional
finger/device/open/short/grid faults rejected. Summary639060800,archive639060607
393975bytes SHA6143b74d12cedffdc9ac399470ffb52f0d23f4b845862a8fa9a90c23e6164274.
This is only the V11finalstage block, NOT wholechip, electricalspeed, RFPEX or
PHY acceptance. Exact receipt now inpcie-tx-cloud-extraction-input-20261013.json
underfinal_drive_v11/critical_buses_kelvin_low_ports_loads_shunts_series.
Dispatch tx-layout-extraction-cloud.yml for that exactprofile/variant; verify
actual native RC and13fault controls before binding to devices and waves.
32um feedback experiment38505258788 is already dispatched on2aabe087; do not
repeat it. PLL snapshot38503868241,32:1wire38496981217 and mainchiproute
38490952579 retain live handles. Localworkspace remains empty; all goalsOPEN.


**Newest measured feedback decision and live physical build:**26um feedback
38503692385 is TERMINAL:8cases,2pass/6FAIL. All summaries/output hashes retained
underoutput_feedback_26um_rejection_20261014 in V10series receipt. ColdresWCS
CMpasses compact+wire; hotreswire CMmin1.745891842V and selectorheadroom fail.
ColdHBTcompact VBE still1.022290686V; coldHBTwire4selector VCE fail~.3685V.
Reject26um. Candidate feed now uses two32um/2um native resistors (was26um),
reducing actual reference current to recover output commonmode. No limits,
oracle, sample phase, source rails, transistor or extractedRC changed in
this bias experiment. This does NOT claim the separate coldVBE issue solved.
Dispatch the same8failing-corner matched4:1 study once with this source;
original26um capture remains authoritative at its pinned c6d595fe commit.
SeparateV11 Nx8 data-bank physical build38505016479 is queued/running on
16ff1e202cf713dc4b50c12126c241109013377e. Do not duplicate or use oldV10 RC.
PLL snapshot38503868241, full32:1wire38496981217 and chiproute38490952579
remain original active handles. Everything cloud; three end goalsOPEN.


**Next actual physical repair candidate:** V11 changes ONLY12final data HBTs
Nx3 toNx8; fourselectors stayNx6, reference/tails/resistors and27bodytaps
unchanged. ColdWCS compact VBE remained1.02229V after26um feedback lowered
input commonmode by~60mV, pointing to data-bank current density rather than
only input CM. V11 is a hypothesis, not acceptance; added capacitance may
worsen original8GT/s margin. Build fresh critical_buses_kelvin_low_ports_loads_shunts_series
layout with circuit_profile=final_drive_v11; require all unchanged native
DRC, strict54-device LVS, source equivalence and faults BEFORE freshRC/waves.
Never resize oldV10 RC and call it extractedV11. Added two strict source and
body-contact tests. V10and feedback26um rejections remain preserved.
Cloud source/license check38504338355 passed after .inc inventory correction;
feedback source/capture suite241tests passed. PLL38503868241 remains running
native snapshot experiment;32:1wire38496981217 and chiproute38490952579 retain
handles. Feedback38503692385 lastwire controls remain active; do not duplicate.
FullserialPHY,assembledrouting and finaltiming stillOPEN; cloud-only.


**Verified live native experiment and complete TX rejection receipt:** corrected
PLL snapshot38503868241 onab08fd71f265faca35a31c0c754516559b0b6581 has reached
actual native continuous/restore comparison step(job115656774245). Do NOT
restart or duplicate; source-check job115656773931 failed only inventory:
new .inc file is path-covered by spdx_check, not inline-classified. Inventory
corrected to22573total,4220inline,18353path. Hosted comparison selftests passed.
TX baseline38496978055 now has all24 final summaries and hashes recorded under
completed_independent_corner_screen_20261014 in V10series composition receipt:
19pass/5electricalFAIL; waveform completion is not broadPVT acceptance.
Feedback26um candidate38503692385 compact coldresWCS now passes CM
[1.980536,2.001422]V; coldHBT WCS CMpasses but twelveVBE failures remain.
Two hot compact cases now fall below1.8V. Wire cases are still in progress.
Do not adopt this candidate; examine completed paired results before choosing
next feed geometry or final transistor current-density correction.
Original32:1wire38496981217 and mainchiproute38490952579 remain live.
Everything hosted; no local files or CAD; all three end goals remainOPEN.


**Dispatch update and diagnosed harness correction:** output-feedback candidate
38503692385 dispatched on c6d595fedca1c151de20fe0d866c17320fe4e05b; inspect tests
then eight actual compact/wire failing-corner controls. Do not duplicate.
PLL snapshot38503239727 terminatedFAIL before any transient: reusable circuit
original title was parsed as a capacitor when included. Native log retained
in archive639010147(SHAe8bbd909b1cae489079bb8fe61b4dc3d96c49a9cf630185d179a28fc68c22afc).
Source/model/finite-input pins and four comparison corruption controls passed;
this is a harness error, not snapshot-compatibility evidence. Original title
now comment-prefixed, consistent with upstream ngspice snapshot example.
Only title syntax changed; no electrical controls removed. Corrected snapshot
requires one hosted dispatch; native simulation was not previously started.


**Current concrete continuation:** native PLL snapshot experiment38503239727
dispatched on83e3270e035f886479d475a665280bce84b55979. Keep its handle; inspect
native evidence before assuming snapshot/KLU/OSDI compatibility. No local run.
TX independent38496978055 is TERMINAL:24cases,19engineeringPASS,5FAIL despite
workflowgreen. ColdresWCS CM fails in bothcompact andwire; coldHBT WCS compact
also has12VBE failures. HotresBCS wire CMmin1.799833864V fails1.8V. HotHBTBCS
wire has6VCE minima below.4V(worst.388441772V). Bits pass in allfive failures.
A new output_feedback prestage feed uses two real26um/2um rppd resistors from
actual stage outputs into its original HBT reference. Hypothesis: increase
negative common-mode feedback instead of waiving PVT bounds. No ideal current,
clamp, phase change, transistor deletion or changed limits. Existing19HBT stage
and actual extractedRC retained. Added source/connection/fault controls.
Feed itself has NOT been laid out; candidate screens are not finallayout proof.
Use tx-tree-physical-cloud.yml study=failing_corners streams=4
physical_profile=cascade158_kelvin_supply_direct
physical_final_profile=v10_kelvin_low_ports_loads_shunts_series
physical_final=matched clock_reference=stiff65 pre_bias=output_feedback.
First inspect hosted tests; any failure remains a rejection. Remaining mainchip
38490952579 and32:1wire38496981217 still live at last observed checkpoint.
All three full-goal scopes remainOPEN; continue only on hosted runners.


**New hosted PLL continuation method under test:** run_cloud_pll865_snapshot.py
restores the exact native07 1us circuit, all32 original IHP model files and
three exact OSDIs, and original ngspice47 executable. No circuit, source,
startup, timestep or electrical-limit changes. The ngspice manual documents
snsave/snload across processes but warns against XSPICE devices; actual865
compatibility remains UNPROVEN until the native experiment passes.
Hosted workflow inputpll_snapshot=true compares continuous0-50ns with a
25ns checkpoint, same-process resume and fresh-process restore to50ns.
All24 original selected probes, no fitted phase; fixed1mV waveform/1psedge
method limits and four corruption controls. This is only restart-method
validation, never1us lock/full-device safety/PVT/PHY acceptance. Both original
failed readers and prefix diagnosis remain preserved. Do not dispatch full
segmented acquisition before reviewing actual native waveforms and snapshot
proof; do not assume snsave works with KLU/OSDI from documentation alone.
Native budget19000s leaves publication time before hosted6h hard ceiling.
Run only on GitHub; localworkspace remains empty. Existing TX38496978055,
32:1wire38496981217 and chiproute38490952579 retain their handles.


**Latest verified cloud outcome:** PLL prefix38501501029 onb2242dc77f4ba386cf16582deba163393d5c06e3
completed diagnosis and hosted source/license checks successfully. Summary
638969192,archive638969080; exact full summary pinned in
pcie-pll753-parent-rounded-credit-20261010.json underparent865_cloud_prefix_20261014.
748851 complete rows end233.92609375ns;40 trailing bytes excluded with hash,
never padded. Five corruption controls plus explicit partial-row controlPASS.
Feedback median frequency falls100.206270MHz(25-50ns) to100.068033MHz
(200-230ns); last short-window error~680ppm, not100ppm lock. VCTRL lastwindow
0.427578..0.593801V. Missing800-1000ns windows, phase/slip criteria and full
1us safety remain OPEN. Next PLL work: exact source-bound hosted native865
acquisition with valid runtime/resource plan, not another prefix acceptance
or redundantKLU change. Base finite50ns proof remains separate.
TX independent run38496978055 additionally fails hot_low_res_bcs physical_wire:
final CMmin1.799833864V<1.8V, although bits/devices pass. Exact summary638961839
now retained in V10series receipt; don't waive the small violation. Remaining
independent wire cases,32:1wire38496981217 and chiproute38490952579 stilllive
at this checkpoint. Preserve these original handles before any next dispatch.
Local cleanup complete as recorded below, all computation hosted. Fullserial
PHY,assembledchiprouting,finalsetup/hold all remain OPEN.


**Newest cloud-only cleanup and diagnostic checkpoint:** four legacy LVS `.cir`
files outside the checkout in its parent were archived, fetched back and
byte-for-byte verified, then ONLY those exact unchanged files removed.
Release cloud-migration-final-checkout-20261013 holds
parent-lvs-leftovers-20261014.tar.gz(asset638960993,14788bytes,
SHA12ab296f0bd74fae6bb559982b43421ccd30e9f7dfd69e8200e92da499199080)
and receipt638961046. Workspace empty; no local ngspice/OpenROAD/Yosys/KLayout/
Magic/Netgen process. Existing 8hour heartbeat already enforces cloud-only.
Corrected split-archive PLL run38501008048 reached waveform decoding but
FAILED strict complete-row gate: historical cancellation truncated final row.
Do not erase this failure or use partial data for acquisition acceptance.
Reader now has explicit interrupted-diagnostic-only mode: excludes incomplete
final row with byte count and hash, preserves original capture and strict
normal decoding. Added control proves no padded/fabricated row. All five
original corruption controls remain. Next hosted dispatch must inspect this
partial prefix; absent800-1000ns acquisition and whole-wave safety remainOPEN.
Independent cold TX failures and original active route/tree handles below
remain authoritative; no new circuit acceptance or completed layout claim.


**Latest correction and failures (14 October):** hosted PLL prefix38500020789
FAILED at archive member lookup, before waveform analysis. Archive002 contains
native07 bench/control/logs; wave.raw is in archive003(asset634833900,
121865817bytes,SHA867100a4e8844477ae6003fa84bb7c10801099afb335b8dd3d1b56a6a99450fb).
Both archive/member hashes remain required; reader now explicitly loads both.
Failed receipt638933688 is retained. A corrected hosted dispatch is needed;
never treat this data-location failure as a circuit result.
Independent TX38496978055 has two compact electrical FAILURES:
cold_high_res_wcs final CMmax2.062756V>2.05V;
cold_high_hbt_wcs CMmax2.056945V>2.05V and twelve HBT Vbe>1V
(max1.023357V). Original limits unchanged; exact summaries638905051/638908223
are preserved in the V10series receipt. Base6/6 and hot halfstep remain only
narrow successes; full independent PVT has NOT passed. Continue existing wire
cases and full32:1nominal38496981217; do not duplicate jobs. Full32compact
summary638926257 passed component screen only. Mainchip38490952579 still
running at this checkpoint. Local workspace verified empty; no local CAD.
FullserialPHY, chiprouting and finalsetup/hold remain OPEN.


**Current live readback and numerical evidence:** PLL865prefix diagnostic
38500020789 dispatched on c5e1df33127620ce8d3f54b4f4ca07ed63885ed9.
It runs ONLY on GitHub; five corruption controls before exact native prefix
analysis. Source/license tests run in the same workflow; push check38499990970
has the same source. Read its final summary before claiming any diagnosis.
Hot0.25ps TX38496975171 completed BOTHcasesPASS: compact232.880883552mV,
wire103.821631612mV versus original.5ps232.866874337/103.786226760mV.
Original768bit samples, device/interface gates, no diagnostics. Differences
are worst-margin comparisons, NOT whole-wave convergence/PHY acceptance.
Exact summaries638864869/638899224 and archive/raw hashes are appended as
`hot_half_maxstep_control` to the V10series composition receipt.
IndependentHBT/resistor38496978055 and full32:1nominal38496981217 retain their
original handles. Main-chip halo38490952579 also remains native-running.
Do not duplicate these jobs; inspect native engineering results individually.
All three full-goal scopes remain OPEN; local workspace remains empty.


**Verified latest PLL resume point and hosted diagnostic:**865PBUF10 finite50ns
native01 PASS, independent functional/electrical PASS, zero-source startup and
clean diagnostics. Immutable batch007(asset634874106,669884bytes,
SHAe59ca7de8b8f79a200b226fc7f817bc6eee415ebc563cb811ad5c0be1ae832c6).
Finite capture took5041.802s locally. native04 acquisition failed RAM floor;
native07 is terminalCANCELLED by parentSIGTERM,returncode-15,not currentlylive.
Native07 log reaches233.927ns only;1us final800-1000ns criteria are unobserved.
All exact native07 bytes are batch002(asset634832275,141989022bytes,
SHA6021e860444f74adae386a07f85254169bb6e75ab03fd981dff8cc52c098f6ce).
Bench already usesKLU, reltol1e-4/abstol1e-12, maxstep.3125ps; never add a
newKLU trial or silently coarsen timestep. Current raw149771119bytes pinned
SHA7c1f37bd9e29e794f2a33c67fe5efaa3f0c021bc907484d1d7efa60521d25ba8.
New `read_cloud_pll_acquisition_prefix.py` diagnoses this exact saved prefix
ON GITHUB, with five corruption controls, full archive/member hashes and
explicitly missing final acquisition windows. Dispatch existing workflow
cloud-migration-checks.yml withpll_prefix_readback=true. No new nativePLL
simulation yet. Inspect frequency/VCTRL direction before expensive replay.
FullserialPHY,assembledchiprouting,finalsetuphold remainOPEN;cloud-only.


**PLL continuation correction:**744/753 terminal readback below is HISTORICAL.
Later physical853(reset96) and865(PBUF10) descendants exist. Do NOT roll back
to compact753. The latest migration roots to inspect are
pcie-acquisition-resource-recovery-20261012,pcie-parent865-acquisition-20261011,
pcie-pbuf10-native865-20261012,pcie-pbuf10-acquisition-20261012. The migration
snapshot explicitly stopped acquisition retry01 on12October for cloud-only
handoff. Find its terminal/partial capture and input manifests before hosted
replay; old process/unit names are not live handles.
Gate source asset632607200(8611bytes,SHA54901cd0d7aa00a98fb0d6a95e2516a2e7781368d61acc80da0597fe63c89fa2)
requires independent finite865 pass before a1us diagnostic at.3125ps; no
external VCTRL clamp. Acquisition criteria: final800-900/900-1000ns windows,
100ppm,50ps phase range,no ordinal slips,VCTRL.4..1.5V. Selected24probes alone
cannot qualify all-device safety/PVT or fullPHY. Preserve the failed-source
negative gate. No new PLL simulation dispatched in this readback.


**Newest authoritative findings:** slow-corner mapping38496628841 completed;
79055cells, PCIe slow setup-0.991351ns versus-0.991500baseline (only0.149ps),
fast hold-0.109062ns unchanged. Not adopted. Full corners/critical path pinned
in `abc_slow_corner_completed_screen` ofpcie-ack-window-proof-and-screen-20261014.json.
Actual endpoint is advertiser.refresh[0], FF1304820; further blindABC sweeps
are not justified. Inspect full ready/arbiter/reset cone before the next ECO.
**PLL historical-state correction:**744native05 was finitePASS;753native03
was finiteFAIL, with a separate limited phase-window review. Newer compact
parent753native02 ALSO FAILED electrical and functional/phase checks. None is
running. Exact terminal records, raw hashes and independent reviews recovered
from migration batch259(asset635605533,68.8MB),316(asset635797234,1.46MB), and
744records628261905 are in `cloud_terminal_readback_20261014` of the existing
PLL753evidence receipt. Repair from compact753native02, not the older pending
snapshot or the unchanged wide parent. No PLL lock/fullPHY acceptance.
Native TX hot0.25ps38496975171: compact has passed, wired stilllive at lastread.
Independent corners38496978055 and32tree38496981217 retain original handles.
Main-chip halo38490952579 remains native-running; release summary638701652 is
an INTERMEDIATE placement/STA checkpoint, NOT a terminal route result.
All work stays cloud-only. FullserialPHY/main-chiproute/finalsetuphold OPEN.


**Current dispatch handles (do not restart queued/live jobs):**
- 38496975171: V10 4:1 hot-low compact/wire at0.25ps maxstep; compare against
  original hot-low0.5ps summaries638812939/638828378, same bit oracle/phases.
- 38496978055: V10 4:1 independent HBT/resistor and mixed PVT corners,24cases,
  at most4parallel. Every engineering gate still applies.
- 38496981217: V10 full32:1 compact/wire nominal, actual30prestage macros.
  All three run on31d4d70464ed0c395ca9c4564e81e101fee849da, same
  cascade158_kelvin_supply_direct / v10_kelvin_low_ports_loads_shunts_series /
  stiff65 / matched physical. Read terminal native captures, not workflow color.
- 38496983888: source/license/capture checks for31d4d704.
- 38496628841: paired typical/slow ABC mapping on96b1ee51; native preparation
  has started. OriginalD4000,32joint controls,all3STA corners.
- 38490952579: main-chip halo1 native routing remains running, original source.
V10six-case base measurements: compact/wire nominal280.128025493/234.097230665mV;
hot232.866874337/103.786226760mV; cold273.459379164/263.748860088mV.
All6pass original768samples/device/interface/diagnostics. Narrow hot margin
requires the above numerical/process checks before any acceptance expansion.
Unchanged schematic divider14 nine-job push38496930380 was cancelled after
inspecting its exact workflow; it does not exercise the new physical V10.
Legacy schematic/native study jobs now require explicit dispatch; standard CI
and all explicit physical/timing jobs remain enabled. No local artifacts.
FullserialGen3x4 PHY, assembled main-chip routing and finalsetup/hold OPEN.


**Newest PHY result:** V10series loaded38495318320/38495321089 completed all6
component cases successfully. Hot extracted-wire minimum103.786226760mV,
0wrong-sign/0below100mV among768original samples; all native device/interface
and diagnostic gates pass. Six captures/asset hashes are appended as
`loaded_temperature_voltage_screen` to the V10series composition receipt.
This does NOT close fullPHY: intermacro wiring/clocks still ideal, no fullx4.
Dispatch next: `hot_low_quarter_step`4:1 numerical control, independent process
corners4:1, and nominal32:1 with identical V10/cascade158/stiff65 settings.
Study workflows require explicit dispatch to avoid unrelated default push jobs;
physical study parallelism capped4. DefaultACK push38496573724 was cancelled
after verifying its baseline/ack jobs; desired slow-corner mapping38496628841
is separate. Sourcechecks38496631571 on96b1ee51.
Main-chip halo38490952579 remains live. All full-goal scopes remain OPEN.


**Newest synthesis finding:** ABC study38494637444 completed with no improvement:
79065cells and all6corner group minima identical, slowPCIe setup-0.991500ns,
fastPCIe hold-0.109062ns. Native trace proves D2000 was applied; its network
is combinational. Full native records/hashes are preserved as
`abc_delay_completed_screen` inpcie-ack-window-proof-and-screen-20261014.json.
Next paired study `abc_slow_corner` maps the SAME proved best RTL with the
pinned slow standard-cell Liberty, D4000, original FF mapping and constraints;
all3STA corners and32joint controls remain. Pending dispatch, not adoption.
V10loaded38495318320/38495321089: all3compact jobs completed; all3wire jobs live.
Main-chip halo38490952579 remains live. Continue cloud-only, no local files.
Full serial PHY, main-chip routing and final setup/hold remain OPEN.


**Latest advancement:** V10extraction38494852996 passed4017R/2636C and13faults;
composition38495079171 passed native54device binding. Receipt:
`docs/evidence/pcie-final-v10-kelvin-low-ports-loads-shunts-series-composition-20261013.json`.
**Loaded V10 hot/cold38495318320 and nominal38495321089 are now running** on
`84a5222afc769c035eec46335df3f8b74256dcb2`; streams4, matchedphysical,
`v10_kelvin_low_ports_loads_shunts_series`, cascade158direct, stiff65.
Source/license/capture checks38495323612 run on the same source.
Do not repeat extraction/composition or infer loaded acceptance from them.
ABC4000/2000study38494637444 remains running (jobs115627512925/115627513061).
Main-chip halo38490952579 remains running on its original source. All three
full-goal scopes remain OPEN. Continue cloud-only; local workspace stays empty.


- V8series loaded38492859554/38492856902 completed all6:5pass, hotwire fails50
  early samples, minimum88.993072473mV versus100mV. All devices/interfaces pass.
  Receipt `docs/evidence/pcie-v8-series-loaded-rejection-20261014.json` retains
  all6 captures and the next V10 trial. Do not repeat unchanged V8series.
- **V10 Nx3 data-bank plus same improved series geometry:** physical38494057637
  on05a0a4c8 passed560-category zero-marker DRC, strict hierarchical/flat54device
  LVS and5faults. **Extraction38494852996 is live**, source
  `1fc2599ffdbbb10714071d9b511d963e92168420`; profilefinal_drive_v10, variant
  `critical_buses_kelvin_low_ports_loads_shunts_series`. Summary638777925 and
  archive638777738 are pinned inpcie-tx-cloud-extraction-input-20261013.json.
  V10 needs its own fresh RC, composition and all6loaded cases; do not reuseV8.
- Reset-dominance38493229154 passed fullregion induction and32joint ports but
  PCIe slow setup worsened-0.991500 to-1.260820ns;79984cells. Rejected. Evidence
  `reset_dominance_completed_screen` inpcie-ack-window-proof-and-screen-20261014.json.
- **ABC synthesis-target study38494637444 is live**, source
  `0d16d91b36f0d57adc65f393a78e71149072bb47`: same best proved EOP/window RTL,
  target-D4000 versus-D2000ps. Native help and original/modified exact command
  are captured. No -dff/retime, changed clock period, relaxed SDC or adopted logic.
  Profilesphysical_idle_credit_window_eop andphysical_idle_credit_window_eop_d2000.
  Source/license checks38494640061 passed. Inspect both paired outputs.
- **Main-chip halo38490952579 remains live**; inspect same handle, never restart
  because a poll takes too long. Parameters and source below remain authoritative.
- PLL broader scope was revisited: docs/evidence/pcie-pll753-parent-rounded-credit-20261010.json
  proves parent753DRC/LVS/faults and parent86R/317C, not loaded lock or fullPEX.
  Old delivery627947280 (26692374bytes, SHA9bd534fc389506982c6d05f3fd5a94175e8e5a3dd8c9dae00648aca459d0f4b3)
  was read inRAM. Its historical running statements are NOT current process proof.
  Latest migrated753/744 terminal evidence must be located before cloud replay;
  no new PLL job was dispatched and no PLL completion is claimed.


This section supersedes older running/pending statements below. The local
workspace is empty. No local checkout, CAD, tests or artifacts; metadata/source
edits stay in RAM and native work runs on GitHub. Final retirement backup:
`cloud-migration-final-checkout-20261013`. Never force-push or retry uncertain
mutations before reading the branch ref. Latest engineering source:
`895fc9a44b85c1a8ae3451f0fdfb28b1ec58d73f`.

### Live runs to inspect before dispatching anything again

- **38490952579 main-chip macro halo**, source
  `a011880cdadc7f4c22cf077383382880528b1f14`, job115615743460.
  Native replay/routing is in progress. `local_optimize_buffers`, GMIIhold2,
  seed13, critical0, guideoffset0, halo1; exact baseline placement hash enforced.
  Native `set_macro_extension 1` enlarges actual macro OBS. Same original layer
  derates, SDC, cells and zero-overflow gate. No detailed routing/STA acceptance.
- **38492859554 nominal** and **38492856902 hot/cold PHY**, source
  `a1d1ae9707cf567b638951cdabc3f54087014a85`.
  All3compact jobs completed; three extracted-wire jobs remain running.
  Profile `v8_kelvin_low_ports_loads_shunts_series`, prestage
  `cascade158_kelvin_supply_direct`, stiff65, streams4, matchedcompact/wire.
  Read allsix engineering summaries; a green workflow does not mean acceptance.
- **38493229154 reset-dominance proof and paired digital map**, source895fc9a4.
  Baseline `physical_idle_credit_window_eop`, candidate
  `physical_idle_credit_window_reset`; jobs115623078791/115623079002 live.
  Candidate ties only advertiser.link_up_i high beneath unchanged actual
  asynchronous local_reset=rst_ni&&link_up_i&&!retrain_done_i. All other link
  connections, original FC state, EOP candidate, latency and SDC preserved.
  `run_cloud_advert_reset.py` requires full-region state/output induction with
  arbitrary reset/link/clock traces, wrong-owner counterexample, full public
  port controls before native paired mapping. Never assume proof/timing passes.
- **38493231713 source/license/capture checks**, source895fc9a4, running.
  Earlier source checks38492861940 and38492081693 passed.

### Fresh physical evidence

Series-output candidate moves only R25/R26 fromy=-50 toy=-18um on combined
loads/shunts geometry. Physical38491698578 passed zero-marker560-category DRC,
strict hierarchical/flat54device LVS and5actual faults. Extraction38492320653
passed native4021R/2638C graph/capacitance checks and all13negative controls.
Composition38492591399 passed exact native device/wire binding. Receipt:
`docs/evidence/pcie-final-v8-kelvin-low-ports-loads-shunts-series-composition-20261013.json`.
Summary638734981 SHA3f7c9eff40f67dd43f7d16be4b6f92730ae6fb5c2cf6e90d9aacb386a10b7192;
archive638734847 SHA7d23c3d62afd75a822f007b6b4fb0a4179c11659bac4da3f26afc8477f2c976b.
Do not reuse prior geometry RC or call physical pass an electrical pass.

Prior combined loads/shunts run38489754238/38489752340 passed5/6: hotwire had
50early samples below100mV, minimum88.309416767mV; allHBT/MOS/interface gates
passed. Diagnosis38491313386 proved clock-to-MUX median17.390ps versus9.491ps
compact; source-to100mV maximum38.278ps misses original37.5ps early sample.
These exact records and subsequent physical/RC receipts are retained in
`docs/evidence/pcie-v8-loads-shunts-loaded-rejection-20261014.json`.
Next after a genuine6/6pass: independent native device/process corners,
numerical step agreement/fault controls, full32:1 and actual clock/intermacro
layout. Do not change bit oracle, sample phases or electrical thresholds.

### Rejected digital and route hypotheses

- Non-SOP owner38488788552 passed exact proofs/ports but setup worsened
  -0.991500 to-1.261001ns; rejected.
- Factored EOP38492079062 passed3region inductions, wrong-owner counterexample
  and32joint public-port tests but setup worsened-0.991500 to-1.015753ns;
  cells79065 to79564. Rejected. Fast PCIe hold unchanged-0.109062ns.
  Allcorner evidence, hashes and candidate identities for both studies and
  earlier rejected FC refresh/snapshot trials are in
  `docs/evidence/pcie-ack-window-proof-and-screen-20261014.json`.
  Best unplaced baseline is still `physical_idle_credit_window_eop`.
- Half-grid38472175339 failed with identical seed13placement/congestion hashes
  (132overflow). Exact OpenROADdcf36133 source uses grid_origin only when
  saving guides, not routing partition creation. False shift claim withdrawn;
  nonzero choices removed. Never repeat half_x/half_y. Receipt/correction:
  `half_grid_rejected_followup` in
  `docs/evidence/cloud-seed13-buffers-route-failure-20261014.json`.

Full serial Gen3x4 PHY, assembled PCIe/Ethernet main-chip routing, final
setup/hold and production acceptance remain OPEN. Ideal clock/intermacro
segments, schematic TX driver and unqualified RF/substrate extraction are
explicit gaps; passing a4:1 component does not close them.

## Controlling request and scope

The user requires **cloud-only execution**. The local workspace is empty.
Do not clone the repository locally, restore local CAD, run local tests, or
retain local artifacts. Use GitHub API metadata/source edits in memory and
GitHub-hosted runners for all native work. Repository: `Melihakbulut221/nssoc`,
branch `codex/complete-open-work`. Never force-push or blind-retry a mutation.
On uncertain publication, inspect the remote ref before proceeding.

**Full serial PCIe Gen3 x4 PHY, assembled main-chip PCIe/Ethernet route and
final setup/hold remain OPEN.** Compact/4:1 component gates do not prove a
32:1/x4 PHY, actual PLL/CDR clocking, ESD, qualified RF/substrate PEX, or chip
production acceptance. Main-chip packet-interface work is a separate scope.

The previous long continuation log is preserved unchanged at
https://github.com/Melihakbulut221/nssoc/blob/a45de762a05b9625fe9308aac90805544988c81d/CLOUD_RESUME.md
and all immutable results/failures remain in Git history and release assets.
This concise checkpoint supersedes stale running/pending statements there.

## Active physical candidates: inspect these runs before dispatch

| Work | Exact source / runs | Verified boundary and next action |
| --- | --- | --- |
| Short selector buses on unchanged v8 | Physical38452058065, extraction38453131275, composition38453569616 | All native physical/RC/composition gates passed. Loaded nominal38454523127 andhot/cold38454526301 completed ona45de762a05b9625fe9308aac90805544988c81d. Fiveof six engineering screens pass; hotwire fails128early samples, minimum20.841388mV. Allsix retained inpcie-final-v8-low-selects-loaded-tree-20261013.json. Native paired diagnosis is next; no adoption. |
| Nx3 data-bank v10, original low-critical buses | Nominal38452808927, hot/cold38452812892 on7f95123097589d5edb304e9c0cdde52720a8ac2b | 6captures retained; complete=true; failed cases=[('hot_low', 'physical_wire')]. Check exact receipt before adopting anything. |
| Main-chip alternative net ordering | 38448901835 on c19fc8b4c72e4db8ad20d6132ad73153f1ef856b | Latest live readback: in_progress/None. Seed13, capacity perturbation0, exact135-overflow buffer placement. Preserve native result; detailed routing/extraction/final STA still required. |
| Bounded-save32:1 nominal | 38441895491 on26e3692a27cb4aea7faa877b8df3388ddc06024d | Latest readback: in_progress/None. Compact passed; extracted-wire companion must complete. Do not restart a live job after observation timeout. |

Source/model/geometry/original-bit/license checks38454282998 PASSED before
launching the short-selector loaded runs. Earlier v10 binding checks
38452484468 and receipt checks38453573552 also PASSED.

## Exact analog evidence and unchanged limits

Both current4:1 candidates use `cascade158_kelvin_supply_direct` prestage,
`stiff65` native clock common-mode reference/feed and matched compact/wire.
Original256source bits,768samples at0.3/0.5/0.7UI, output100mV, interfaces150mV
and1.8..2.05V common-mode remain fixed. All native HBT/MOS limits, zero-start
OFF flags and simulator diagnostics remain gating. No phase-fitting or RC
scaling. Differential clocks/intermacro connections still have ideal parts.

- **v8 low-selects** changes only actual sp/sn TM2 buses to y32/40um. Native
  physical passed560DRC categories/zero markers, strict54-device hierarchical
  andflat LVS andfive actual physical/reference fault controls. FreshRC passed
  all13corruption controls. Composition has54devices/4043R/2661C.
  `docs/evidence/pcie-final-v8-kelvin-low-selects-composition-20261013.json`
  binds archive6675045bytes/SHAf591bc98448db872b00d8d0b7c2c2f7aa27625908e265f7431a98008dc10a3b6
  andsummaryasset638003525/SHA91b3d4ce252c81e4c28b06b081d8ba10e05a3f91106ec3211a7d9ffdb9e84d14.
  Do not substitute old low-criticalRC. Profile: `v8_kelvin_low_selects`.
- **v10** changes only twelve data HBTs toNx3; four selectorsNx6, two tailsNx8
  andreferenceNx1 remain. Physical38450309882/extraction38450839520/composition
  38451600151 passed native gates with54devices/4041R/2659C. Profile:
  `v10_kelvin_low_critical`; distinct composition receipt and
  `docs/evidence/pcie-final-v10-loaded-tree-20261013.json` preserve all completed
  captures. Threecompact andnominal/cold wire gates passed; consult hot result.
- **v9 rejected:** Nx2data improved hotwire minimum17.694to41.723mV but still
  failed110early samples. Coldcompact also failed12HBT VBE/current limits
  (maximum1.021886V/3.676749mA). Allsix captures remain in
  `docs/evidence/pcie-final-v9-loaded-tree-20261013.json`; no selective adoption.
- **Native delay diagnosis38451366659 passed:** summaryasset637967168 SHA
  024328b471f0d1ee06476f080849621df84af4d17bd1c1a593f620d9393058c6. All128changing
  bit events unambiguous. Compact/wire clock-toMUX-zero median8.606881/19.656687ps;
  MUX-toTX-zero5.956289/6.178540ps. Source-to100mV median26.362079/39.053899ps,
  wiremax41.441851ps versusfirstsample37.5ps. This motivated selector routing;
  it does not already prove the new geometry works. Hot pair receipt:
  `docs/evidence/pcie-final-v9-hot-loaded-tree-20261013.json`.

If short selectors pass, expand unchanged independent HBT/resistor/MOS corners,
quarter-step numerical agreement and actual physical faults, then full32:1
andphysical clock/tree integration. If they fail, preserve/read exact events
before selecting another geometry. Do not combine sizing/geometry changes
without measuring their separate effects and then retesting the combination.

## Main-chip route and timing evidence

The seed13 trial must reproduce placement SHA
660692b3e59756186bb017a62823999db593fa9d77b6e4181be9625fa7bfb707.
Pre-route asset637931919/SHA8db957ba8f6b07fd0cc12e31df23d0f6925306f3b7c96310ab9ff646676f7a7e
reproduces that exact placement and prior timing. Estimated slow setup is
still negative (PCIe -1.275681ns, system -0.589711ns); fast hold also negative
(PCIe -0.065767ns, system -0.054434ns). These are pre-route estimates, not
signoff. Same cells, SDC, PDK RC/capacity adjustment andzero-overflow gate.

Previous priority30 run38420407838 is terminal GRT-0116 failure, not live:
153layer overflow (M3=21,M4=16,M5=107,TM1=7,TM2=2). It was native max-overflow
attempt termination, not elapsed timeout. Failure receipt:
`docs/evidence/cloud-critical30-buffers-route-failure-20261013.json`.
Diagnosis38443872244 has113markers/155summed marker overflow/933nets; marker
andlayer totals are different native reports. Asset637840399. Prior same
buffer placement had135overflow; broad endpoint move produced420 andwas
rejected. Do not repeat unchanged rejected candidates or waive physical gates.

## 32:1 capture, publication and local retirement

Original32run38440472079 failed wire allocation (42.522GB reported). Oversized
save-command risk was fixed with bounded128-vector commands; its contribution
to that original failure still needs actualnative-log verification. Do not
assert causality from the memory warning alone. Corrected32run38441895491
compact has604native OFF flags,69541wave rows, complete original engineering
gates andzero diagnostics. Exact summaryasset637874261/SHA
 e9423a26a42909dfeb088124e76e072f7701fcc6f37c617dd9c8eadd381739d8 is bound by
`docs/evidence/pcie-bounded-save32-compact-20261013.json`. Wire remains separate.

All native artifacts are retained in immutable GitHub releases, including
failed cases; never label workflow success as electrical acceptance. Migration
finished with `COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE`; do not
redo retirement or restore local CAD. The8hour cloud-only automation remains
the continuation mechanism. No full goal completion or production approval.


## Latest cloud-only follow-up

The empty local workspace and absence of local CAD processes were rechecked.
Low-selects hot wire has zero wrong-sign samples but128below100mV at0.3UI;
later0.5/0.7UI samples and all HBT/MOS limits pass. Shorter selector buses alone
do not close the amplitude failure. Preserve the compact/wire pair in
pcie-final-v8-low-selects-hot-loaded-tree-20261013.json; diagnosis workflow
study v8_low_selects_hot reads exact original archived waves with unchanged
bit oracle and thresholds.

cloud-migration-checks.yml with timing_readback=true restores the archived complete native STA
log/Tcl from run38371498733, verifying archive size/hash and both member hashes.
It publishes a small full-path log for setup/hold inspection while seed13
routing continues. It does not rerun STA or claim routed timing closure.

The new standalone readback workflow was not registered on the default branch
(dispatch404, no native run started). The readback job now uses the existing
registered cloud-migration-checks.yml workflow with timing_readback=true.
Low-selector native diagnosis38457021311 completed successfully on873a6350ca13c5d98981214033bc5b0af33d0add.


Native short-selector diagnosis38457021311 PASSED. Summaryasset638065261, SHA
acf780035a06b3be15e51beca4f7b9fa4360edf8f0d85a9d3a8926ccc0d64465;
all128 changing-bit events are unambiguous. Exact delay statistics(ps):
{"physical_compact": {"clock_to_mux_zero_ps": {"maximum": 9.581434892876144, "median": 9.491111200654228}, "mux_to_tx_zero_ps": {"maximum": 6.09829029383962, "median": 5.97122009132631}, "source_to_output_100mv_ps": {"maximum": 27.4264716742218, "median": 27.179796408673198}}, "physical_wire": {"clock_to_mux_zero_ps": {"maximum": 22.614831331883618, "median": 21.050944335681756}, "mux_to_tx_zero_ps": {"maximum": 6.513847561199617, "median": 6.17929948213888}, "source_to_output_100mv_ps": {"maximum": 42.797680763914016, "median": 40.40026853520598}}}

Timing readback38457177829 restored and verified both original files, then
failed because the caller selected PHASE markers instead of actual CORNER
markers. Failure retained. Corrected caller uses CORNER and requires allsix
slow/typical/fast min/max phases. Raw fullSTA log remainsasset638067970
SHA80055c3fb2022a1366d03f8a010d0c671fe603c57b3ca6ca64350b5a44668374.
It includes one unconstrained endpoint and SRAM slew violations. PCIe worst
setup contains a long logic chain; PCIe worst hold has justINV+O21AI.
These are placement estimates; no constraint relaxation or closure.


## Verified latest timing readback

Corrected run38457514399 onbad1063138a4233ffca9b64b7c1e0f577558176a PASSED
both source/license/model checks and exact archived timing readback. Optional
archive-migration job was not requested and is skipped. Summaryasset638073464
SHAe759439142daa150c9d12cbd8cc67cda55850f61afb81375b8b30619cdb9566d;
complete original logasset638073598, SHA
80055c3fb2022a1366d03f8a010d0c671fe603c57b3ca6ca64350b5a44668374.
Allsix corners reproduce old placement estimates; slowmax -1.275681ns,
fastmin -0.065767ns. Next inspect the full critical paths and bind synthesized
cell names to actual RTL/netlist before selecting an ECO. PCIe setup includes
six consecutive AND2 stages near its endpoint; hold includes INV+O21AI. The
unconstrained endpoint and SRAM slew violations must also be resolved without
weakening constraints. No new timing/layout acceptance.

Main route38448901835 and32:1wire38441895491 remain in progress at last readback;
do not duplicate them. Authoritative cloud-migration-final-checkout-20261013
retirement-progress.json was reread and digest verified: status
COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE. Local directory remains
empty. The existing8hour automation is ACTIVE and explicitly cloud-only.


Next cloud timing readback also restores the exact placementODB and runs native
OpenDB on the same pinned runtime to bind every reported timing cell to its
actual master, placed bbox, pin nets and full incident-net endpoint census.
The STA report and ODB hashes must remain unchanged. This gives RTL-facing
net names before any ECO choice; no cell, clock or constraint is modified.


## Native credit carry mapping and next candidate

Native readback38459016095 onb1d25755562e391f27f934f237a8d339221c5faa
PASSED all505reported cell/master bindings and complete incident-net census.
Nativecells asset638101934,2051537bytes,
SHA135e57abe41fc3323988677b4a81eac8f2a1e560be296ddfb84fcbce8ea7897f.
Exact original ODB/STA hashes remain unchanged. Prior failed readers
38458086604/38458327263/38458689640 remain in releases: escaping/import
and rendered array spelling errors were reader failures, not chip failures.

Worst setup: credit_data_consumed_o[29] to credit_header_consumed_o[23].
Worst hold: replay next_store_sequence_plus_one[11] to next_store_sequence[11].
Setup suffix is six AND2s then NAND2 passing the late credit enable through
previous carries. All seven original output nets must remain equivalent.

run_cloud_credit_prefix.py keeps those seven gates/outputs; inserts balanced
AND prefixes of seven early data inputs and applies the unchanged late enable
at each original gate. Actual Liberty SAT proves all seven outputs for all256
assignments of eight cutpoints. Replacing final NAND byAND must fail proof.
Existing instances are temporarily FIRM for added-cell legalization; audit
requires exact original geometry, all non-target pins, boundary nets and power
geometry, then restores statuses. Same archived3corner STA/SDC/libraries.
No candidate adoption, route, final hold or fullPHY closure is claimed.

Launch existing cloud-migration-checks.yml with credit_prefix_eco=true.
All native work is hosted. Do not launch full routing until measurements exist.


Credit-prefix candidate dispatched as run38460825316 on
9588d4421d7d574edfd7f5e687b72431f7628b8b. Latest authoritative status: completed/success.
Job115515232477 runs native proof/geometry/STA; source checks already passed.
Keep this exact handle; do not start another candidate or rerun on a polling
timeout. Read result.json in release cloud-results-38460825316-1-credit-prefix-eco
when published. Check all7output SAT proof and actual wrong-gate negative
control, exact retained geometry/power audit, allcorner/group deltas and all
remaining violations before any adoption. No accepted timing gain yet.


## Completed credit-prefix screen: real proof, timing still open

Run38460825316 PASSED its native work and controls. Exact full receipt:
docs/evidence/cloud-credit-prefix-screen-20261013.json. Summaryasset638141166
SHAa0413b69f0d2b827eedf1f74950bfd30e02cf004cb411eb7544c9553175b8b31;
archive638140287,201763214bytes. CandidateODB
SHAdc4d9bcaf7ca617b31ece0c7504a591d41ddff0e5558821e2a6cb7815940d074.
14new AND gates,113791retained instances with exact original geometry/power.
Actual Liberty SAT proves allseven original outputs at all256cutpoint inputs;
actual final NAND-toAND negative control fails as required.

Worst slow PCIe setup changes only -1.275681to-1.275034ns. No reported group
worst slack regresses; fast PCIe hold remains-0.065767ns, CPUhold-0.054434ns.
The previous header-consumed[23] endpoint drops out of the topthree paths, but
its exact new slack has NOT been explicitly measured. Do not infer its closure.
The next worst paths bind to credit_data_consumed_o[18] -> replay read_pos[2]
and[1]. A third new endpoint1165551 is not in the prior505cell binding.

Next: preserve all failures and inspect the newly critical control paths.
Potential RTL change to evaluate: clear read_pos whenever replay is idle,
instead of waiting for credit-grant/start. That can remove credit-grant timing
from the reset-to-zero cone but changes invalid-cycle output values; it needs
transaction-level equivalence and complete reset/ACK/replay/backpressure tests
plus fresh native mapping/timing. It is a proposal, NOT implemented/adopted.
Do not repeat the single-header ECO as though it closes all credit/control
paths; whole-chip setup/hold, routing and fullserialPHY remain open.


## Isolated replay idle-clear evaluation

run_cloud_replay_idle.py creates a cloud-only source overlay. Production RTL
is unchanged. It clears read_pos while !sending, removing its two start/grant
reset assignments. The proposed observation contract compares all control,
handshake and credit outputs every cycle; tx_data/SOP/EOP only while tx_valid.
Independent wrappers apply that mask; actual internal tx_eop feedback remains
unchanged. clk2fflogic preserves explicit clocks and asynchronous reset.

The full baseline/candidate replay and reliable-packet scoreboards run with
zero skipped tests. A real wrong-idle-index candidate must fail both sequential
proof and actual replay scoreboards. Any incomplete proof is retained as FAIL.
This does not prove mapping, timing, full parameter coverage or fullchip PHY.
Workflow: cloud-migration-checks.yml input replay_idle=true. Do not promote
the overlay or repeat existing native layout jobs before reading these results.


Replay idle-clear run38462752171 is active on5a29ee88c0e88b6aa8fcab7a43ff0566d984deba.
Do not promote overlay before reading sequential proof and all actual ports.
The native metal-DC workflow now accepts final_low_selects, restoring the exact
v8low-selects composition to identify remaining physical conductor resistance.
This is a read-only DC diagnosis, not loaded acceptance or altered RC.


## Cloud-only cleanup and authoritative continuation refresh

The latest instruction remains cloud-only. On 2026-10-13 the main workspace
was verified empty and no local CAD process was running. Two older checkouts
of this same repository (Documents/nssoc-public and Documents/nssoc), plus six
specific generated CAD temporary files outside the workspace, were archived
in memory, uploaded, downloaded, and SHA-256 verified before deletion.
All 2783 regular files were rehashed locally before deletion; 82721707 logical
bytes were removed. No local archive or checkout was created. Other repositories
and the user's original Downloads documents are outside this cleanup scope.

Permanent backup in release cloud-migration-final-checkout-20261013:
- asset638208020, legacy-nssoc-and-cad-residue-20261013.tar.gz
- 44933911 bytes; SHA256
  9fa1750273df0519c0e90f4cd14482bae75754056d18609bcc4777353ab0e203
- cleanup-manifest.json inside the archive binds every retained file/path/hash.

Replay idle-clear run38462752171 completed with a harness failure, not a pass.
The corrected run38463387304 on c2df40e58c2d0a7ad5c9eb9e9d51e099b4c4f4d4
passed its observable sequential equivalence and complete port controls.
Summaryasset638181971,59757 bytes,SHA256
96858095d6bb10040b8b40ac528d9b45f742bb97048fb4021524ad3777d5e2f3;
status PASS_OBSERVABLE_REPLAY_EQUIVALENCE_AND_COMPLETE_PORT_CONTROLS_NOT_TIMING.
Production RTL is unchanged. This result does not establish mapping or timing.
Next bind the exact proved candidate and baseline to a native whole-chip mapping
recipe; verify frozen capsule replay bytes before using any older synthesis
capsule. Do not present an older full-chip baseline as current physical evidence.

Metal DC run38463066637 completed with
PASS_SOURCE_BOUND_METAL_DC_DIAGNOSIS_NOT_ACCEPTANCE.
Summaryasset638172478,339654 bytes,SHA256
68c5d1276b3df10a6d8396be2d2b7eb4f95672cb456e7de8e6516199681b2ffd.
Use native resistor-to-geometry binding before selecting further metal changes;
this read-only diagnosis does not close the hot loaded-wire amplitude failure.

Main-chip route38448901835 and bounded-save32 wire38441895491 were rechecked:
both are still in progress. Preserve these handles and do not duplicate them.
The eight-hour automation remains ACTIVE and already requires cloud-only work.
Full serial PHY, main-chip routing and final setup/hold remain OPEN.


## Physical replay proof and paired full-chip mapping

The physical replay source differs materially from canonical RTL: it contains
registered byte prefetch, registered metadata and the successor address.
Run38465877636 on a1c6064078350d4834a9f933535e63e00bfbb372 passed1850/1850
observable equivalence points,11 baseline and11 candidate port tests, zero
skips. Actual wrong-idle-index mutation failed formal(2unproven) andall7ports.
Summaryasset638224436,SHA554699985261db8de530b8eb1aeb0846deded73a7a506abf5616788da8f681d9.
Sourceca334ee560f34a0d7484467d8a09ccbe7fc7b2113360f4bee7308f39bbac8e85,
candidate1bfa8971728d65ec2cfad2337d083298d7bcec8e56ce1fe4dc19f38fbcaa2edc.
Canonical proof is a separate result; neither proves mapped or routed timing.

The old ACK capsule uses WAKE1 top and registered credit-offer RTL, differing
from actual current physical19. New physical_baseline/physical_idle mapping
profiles restore the real RX-return-metadata map10 recipe and bind every read
source hash. Original top b782a7f... andcredit ba8adb6... must be used.
The original map-result10 retained a KeyError audit failure despite synthesis
returncode0. Its separately pinned map-audit14 is the corrected mapping audit,
bound by physical-result19; do not relabel the earlier failed audit.
Only the proved replay source changes in physical_idle. These are fresh paired
whole-chip synthesis/unplaced screens, not old-placement or final timing proof.
Use registered pcie-ack-cloud-mapping.yml with study=replay_idle. Preserve all
success/failure receipts and do not adopt without measurements.


Paired physical-source mapping dispatched as38466891418 on
9044757dcf8b34281f8e22228a76c79c296ce870. Actual live jobs:
115535880904 physical_idle;115535881391 physical_baseline. Both in progress.
Keep these handles; do not duplicate on observation timeout. Each restores
the same source-bound map10 recipe, same20SRAMs, five clocks and3corner
unplaced screen. New releases use cloud-results-38466891418-1-ack-map-PROFILE
with summary JSON plus full archive. Read actual status/errors before adoption.
The baseline proof run38465877636 and source/license checks both passed.
Main route38448901835 and32wire38441895491 remain live at this readback.
All work continues cloud-only; the local workspace remains empty.


## Measured paired mapping and physical-metal follow-up (14 October local time)

Run38466891418 completed both physical profiles. Sources restored correctly:
original map-audit14 status PASS_MAPPED_RETURN_METADATA_NATIVE_TIEZERO_AND_CLOCK_AUDIT.
Both contain16dual-port ETH SRAMs and4main SRAMs. No physical adoption.
Baseline79195mapped cells;idle79851(+656). Native unplaced slow PCIe setup
-1.240848 -> -1.147148ns (93.700ps improvement), but slow CPU setup margin
1.125990 ->0.251289ns. Typical RXhold -0.360791 ->-0.368361ns; fast RXhold
-0.347760 ->-0.351201ns. Fast PCIe hold remains-0.109062ns. Other negative
hold groups remain; this is unplaced before clock-tree/physical ECOs, not
a regression comparison against the currently routed placement. Do not adopt
or infer closure from the passing workflow. Candidate worst slow PCIe path
starts at pcie_link_up_i, ends at FF1165499; map to actual RTL before next ECO.
Baseline summary638249417 SHA817df9e748bbe9fe7a25180421feaae58840df41ba1d2a0cdf04fe700b9b46a4;
archive638249192,16809418bytes,SHA3d13294ba8abeb24721e289af6a14e3e41b26006060787f825e0e6b59057bec3.
Candidate summary638251056 SHAaccb288b74cf7c53529440c55bb7695d9e4e7038be6026764b417b22fc0ae372;
archive638250779,16909757bytes,checksumasset638250939. Native screen logs
SHAfe86ca5a5a4f179f8e8fe08fa830d663fae00c0a61fd64f2035a676ba3e01ee5
andfeab9c60c6ff59366e208508ffe00523773d5ec70aa30c5f5fb2ee5fffdd9ff8.

Native geometry binding38467961171 on9eb8abc869311b03d49a26ace606fd3157bf0cca PASSED.
Summaryasset638255303,797500bytes,SHA
6e769267cce4651d5428dd2d519045d7b87bfadd5b0411cc27c1226f07ad34aa.
All4043native resistors bind to unchanged composed wire graph; dominant edge
endpoints bind to native Magic coordinates and actual overlapping paint.
Scale5anchor-DBU/raw-unit;max terminal quantization2DBU. Actual shifted-port
and1percent-resistor-corruption controls rejected. Endpoint paint is NOT
proof of a unique layer or a straight physical edge. Max terminal-pair R:
ea/eb15.564287ohm,tail11.179695ohm,qn17.571188ohm,qp17.395588ohm.

Next physical candidate critical_buses_kelvin_low_selects_m3 onfinal_drive_v8
inherits exact low-selects geometry and increases only qn/qp/ea/eb M3 access
width0.6to1.0um. Tail already1.0um; all54devices and other routing unchanged.
Requires actual560category DRC,strictLVS,fivephysical faults, freshRC and
original loaded PVT. No RC scaling or acceptance claimed.


Native layout candidate dispatched38468734943 on
be7cc6a116619e8f9525f87a0af57cc045f385be; live job115542012002.
The earlier dispatch returned422 before any run because the new input was not
yet published; this is the sole actual native run, not a duplicate. Read the
layout-final_drive_v8-critical_buses_kelvin_low_selects_m3 release when done.
If native layout passes, bind its exact archive in extraction input before
freshRC/composition/loaded tests. No result yet; do not reuse low-selects RC.

Candidate mapping archive638250779 SHA256
3b639453fc6b011703961c444b8a06e6f7823714d9b22db331017d3bcf8f53eb.
Actual mapped FF1165499 hasQ u_pcie.credit_data_limit_o[2],D40788,Q14152;
its input path starts at pcie_link_up_i with0.8ns input delay, passes roughly
24logic/buffer stages and reachesD near4.725657ns against3.578509nsrequired.
Input link_up has one immediate buffer sink, so this is not simply an unbuffered
port fanout. The credit update/consume validation cone is the next RTL target.
Before repeating a static per-class credit-write optimization, inspect prior
pcie-fc-static-commit-20261012 results: its earlier formal proof exists, while
older published receipts still described mapping work as active. Preserve
source/profile separation and all earlier failed audits.


Layout38468734943 completed PASS_REAL_LAYOUT_DRC_LVS_FAULTS_REQUIRES_NATIVE_EXTRACTION_AND_WAVEFORMS:
560DRC categories/zero markers,strict hierarchical/flat54device LVS andnative
fault controls passed. Summary638274567 SHA
86294df2695187b9548944e791d62d87c07b8038d682d9c8542db3fd38d58764.
Archive638274392,394008bytes,SHA
f10c0dea2b1b85c4f042442d0d0bfb434933e8a7fd8dd0be4a1f21c2a8360fd6.
Exact geometry is now pinned in pcie-tx-cloud-extraction-input-20261013.json
under final_drive_v8 /critical_buses_kelvin_low_selects_m3. Next extraction
uses that profile; there is still no new RC/electrical or fullPHY acceptance.

Fresh extraction38469474319 is live on05ee0349c8555b86032d7758beeb8143af96e8f9.
Do not duplicate it. Read extract-final_drive_v8-critical_buses_kelvin_low_selects_m3
release; require full nativeRC graph and13fault controls before composition.
Local workspace remains empty; all CAD/tests execute on hosted runners.


Extraction38469474319 PASSED actual graph/13fault controls on the widerM3
geometry:4331R,2817C,54native devices,17conductors,112geometry probes.
Summary638284870 SHA04b5ad7021d5072fcd7ab5b69ebd9c8f52798aaf1b7daa286c17cbc3920caa8f;
archive638284559,6297265bytes,SHA
347b6944f05e7bcbc938b606818b376c4623febd4d2eb36e21a5f1447fdc0f45.
This exact extraction is now pinned for composition underfinal_drive_v8 /
critical_buses_kelvin_low_selects_m3. Native body/substrateR andRF qualification
remain outside this metal model. No loaded amplitude or fullPHY acceptance.


Composition38470027901 PASSED with54devices/4331R/2817C.
Receipt pcie-final-v8-kelvin-low-selects-m3-composition-20261013.json binds
summary638291781 SHA0bae6871c5dc048e441321b13c9de9e16e46b0565f5c7ee72f8a43539d6324dc
andarchive638291662,6700897bytes,SHA
29d0952fd201fb376ec30f851b0fa04241fe72a7e6e78bdb6cd8d0d0f5608eab.
New loaded profile v8_kelvin_low_selects_m3 uses this exact composition.
Run matched compact/wire4:1 trees with cascade158_kelvin_supply_direct and
stiff65, nominal plushot_low/cold_high, original256bits/768samples and
all unchanged native device/diagnostic limits. No acceptance until allwaves
are actually reviewed. Main32wire38441895491 androute38448901835 remain separate.


## Authoritative cloud continuation, 14 October

Main-chip seed13 run38448901835 is terminal: actual GRT-0116,132 total
overflow (M3=5,M4=20,M5=97,TM1=6,TM2=4). Not a timeout. Exact original
buffer placement SHA660692b3... retained; seed13 changes only net order.
Full failed native ODB, guide and congestion report preserved in receipt
cloud-seed13-buffers-route-failure-20261014.json. Do not rerun blindly.
Next inspect every marker/endpoint with registered congestion workflow
source_profile=seed13_buffers before choosing a physical correction.

WiderM3 loaded4:1 runs on661cb6c49e69e96524afd0d437e2ee7392c8896c:
- nominal38471108761, matched compact/wire;
- hot/cold38471122722, matched compact/wire;
- source/license/restore checks38471139570.
Exact v8_kelvin_low_selects_m3, cascade158_kelvin_supply_direct, stiff65.
Keep these handles and original acceptance thresholds; no wave results yet.
Older32wire38441895491 remains live at this readback, no duplicate.
All work is cloud-only. Local workspace verified empty and no CAD processes.
FullserialPHY, main-chip route and finalsetup/hold all remain OPEN.


## Late credit update verdict candidate

Source-bound congestion probe38471402795 andchecks38471414652 completed
successfully; inspect native diagnosis release before further routing.

New hosted run_cloud_credit_late_verdict.py restores exact ba8adb6... credit
RTL from physical_idle mapping archive638250779 (SHA3b639453...).
Only the joint header/data update verdict is factored:
(A || consume*B)*(C || consume*D) becomes
A*C || consume*((A||B)*(C||D)). Keeps early joint verdicts before late consume.
Static bank writes, every clock/reset and port behavior remain the same by
construction, but formal proof and complete tests are REQUIRED, not assumed.

Workflow cloud-migration-checks.yml inputcredit_late_verdict=true runs direct
physical-source equivalence, both baseline/candidate against frozen serial
reference, all port tests for both, and actual complemented-verdict negative
formal/port controls. All outputs compared; no validity masking in this proof.
No production RTL edits, physical adoption or timing claim. If positive
evidence passes, bind exact candidate into a paired native full-chip mapping
and compare all clockgroups/corners, not only the target PCIe setup.

WiderM3 wire jobs38471108761/38471122722 remain active at last readback;
compact jobs ended but electrical summary still requires review.


## Native132overflow diagnosis and controlled grid comparison

Native probe38471402795 passed:105actual markers sum132overflow, all
7.2um square gcells. Summaryasset638313529 SHA ca29ac20363e4f419ee3577dbd91085e48b541f91ca8d89f48e4bae72d46f01b.
Metal5 final layer overflow97; marker report uses layer '-' and must not
be relabeled as a unique metal layer. SRAM-region hotspots remain.

Next registered newer-postcts-cloud inputgrid_profile=half_xy,
routing_seed=13,placement_profile=local_optimize_buffers,ethernet_hold_depth=2,
macro_routing_profile=baseline,critical_nets_percentage=0.
Only grid origin changes3.6um peraxis relative to terminal seed13 run.
Exact same placement SHA660692b3..., SDC, LEF OBS, RC and reduction settings.
New native per-edge capacities follow shiftedpartition; no artificial increase.
Every baseline diagnosis marker and savedODB/report hash is bound first.
Requires zero globaloverflow, detailedrouting and actual extracted STA later.
OpenROAD documents grid_origin units as DBU:
https://openroad.readthedocs.io/en/latest/main/src/grt/README.html

Credit verdict proof/control run38471835755 is active onea1a231d...;
source/licensechecks already passed. Do not duplicate or adopt prematurely.
WiderM3 compact nominal/cold/hot all component_screen_passed=true,
minimum original-oracle margins281.361/272.648/229.882mV respectively.
Three physical_wire captures stillrunning; no newphysicalacceptance.


## Proved credit verdict and next paired mapping

Run38471835755 on ea1a231dc4cc2d7bf8cc806a98d7913638fdb231 PASSED:
direct physical-source2361/2361points; baseline andcandidate each285/285
against frozen serial reference;5/5baseline and5/5candidate porttests,zero skips.
Real complemented-verdict mutant fails3formalpoints andall5porttests.
Summaryasset638322232 SHA 658337c2e7cb3455e29a88248a8d738489013b4848925e7688dfc0c49a3cda35;archive638321969,208341bytes.
Exact candidateSHA7fc31891f0ae48a8df5247b6df72388ff12cf2603de9f9dc9654b30a0256d38a.
No timing improvement claimed from equivalence proof.

Existing pcie-ack-cloud-mapping workflow study=credit_verdict compares
physical_idle versusphysical_idle_credit. Both use exact actualphysical
map10recipe plus previouslyproved replayidle; onlycreditjointverdict differs.
Proof hash and actual complete positive/negative controls pinned before synthesis.
Review all3corner/5clock results,cellcount,SRAMs andendpoint cones. No adoption.

Main-chip half_xy seed13 route38472175339 on45a0dd0a... is active.
Do not restart on observationtimeouts. Allrunlogs/failures remain hosted.


## WiderM3 loaded result: rejected, all six captures reviewed

Both38471108761 and38471122722 completed. Five of six component screens
pass; hot physicalwire fails128of768samples at0.3UI,minimum16.686602mV
against unchanged100mVlimit. Later0.5/0.7phases pass; allHBT/MOS/interfaces
pass anddiagnostics empty. Actions success means simulation finished only.
Previouslowselects hot20.841388mV alsofailed: widerM3 is not the closure fix.
Full per-case immutable summary/archive hashes are in
pcie-v8-wider-m3-loaded-rejection-20261014.json. Keep every failed capture.
Next analog choice needs to reduce real mux settling delay without phase
fitting orRCscaling. WiderM3 alone is disproved; inspect shorter actual
terminal/interconnect geometry and loadedclock path before another change.

Creditpaired native mapping38472422176 ondb5369c1d... is active; compare
physical_idle tophysical_idle_credit, not olderphysical/postCTS timing.
Main-chip halfgrid route38472175339 andold32wire38441895491 remain live
at lastreadback. No duplicatejobs. Allwork stays hosted; localfolderempty.

Earlier staticFC experiment metadata readback completed from archive
634829840 SHA213a563d... entirely inRAM. decision13/rejection14 show
soc_pcie_fc_tx staticadvertisement writes regressedPCIeslowsetup219.546ps;
rejected andnotadopted. It is a differentmodule from current
soc_pcie_credit_tx peercreditverdict factoring; do not repeat orconflate.


## Shorter vertical HBT bank candidate

All widerM3 loadedcases reviewed and rejected for hot16.686602mV early
margin; do not treat completed Actions as electricalpass. Next profile
critical_buses_kelvin_low_selects_rows onfinal_drive_v8 restores original
lowselects widths, same54devices andallresistor positions, horizontal38.4um
bankpitch. Only verticalHBT rowpitch14to7.2um changes; pairedsubstrate taps
follow their devices. This shortens verticalroutes withoutthe widerM3 change.
No acceptance assumed: actual560categoryDRC,strictLVS,fivephysicalfaults
then freshnativeRC/composition/originalloadedPVT allrequired. Keep anyfails.

Existing jobs: pairedcreditmap38472422176, halfgridroute38472175339,
32wire38441895491 andlatestsourcechecks38472705185 wereconfirmedlive.
Do not duplicate them. Allwork remains cloud-only andlocalworkspaceempty.


Shortrow layout38473056743 on6bba98b5ade3a86cc3b214464fc3cc9682dc83a3
PASSED actual560categoryDRC/0markers,strict hierarchicalandflat54device
LVS andallfiveactualfaultcontrols. Summary638346326 SHA
0fccdbf22b4c1dac693a9191e1a563b5cd9a0c8d7aa7470ef9ad4098035eb4b9;archive638346125,393868bytes,SHA
402f298041bf5ff608b99c61a6ddd45061593b2f28adcbcd2b3ea1c196f116cc.
The exact new geometry is pinned for nativeextraction underfinal_drive_v8 /
critical_buses_kelvin_low_selects_rows. Freshgraph/13faultcontrols thencompositionand
originalloadedPVT stillrequired. No oldRC reused.
Pairedcreditmapbaseline completed;candidate remainslive atlastreadback.


Shortrow extraction38473550498 PASSED nativegraphand13rawfaultcontrols:
54devices,4047R,2663C,17conductors,112geometryprobes.
Summary638353146SHA2a90508c7bdce213f8e914e59f586a5af35a4f8f80ac018624555c01255af6f7;
archive638352934,6291650bytes,SHA9cdc769b9563ef69ad53230faef41667aa8736133ffa6211071872f1d66d42b8.
Exact extraction nowboundforcomposition; qualifiedsubstrate/RFPEXstillopen.

Creditpairedmapping38472422176 completed: physical_idle79851cells versus
physical_idle_credit79578cells. Both20SRAMs andsameoriginalclocklimits.
FreshunplacedslowPCIe -1.147148to-1.101756ns (45.392psbetter);CPUslow
0.251289to1.251946ns. FastholdPCIeunchanged-0.109062ns;RXfasthold
-0.351201to-0.352538ns (1.337psworse). Othernegativeholdgroupsremain.
No physicaladoption orfinaltimingclosure; inspectcriticalendpoint before
furtherRTL orphysicalrepair. BaselinelogSHAfeab9c60c6ff59366e208508ffe00523773d5ec70aa30c5f5fb2ee5fffdd9ff8;
candidatelogSHA935b57971096ec5778a08ccc802f07a93a3ff04cac3731eb571df3db8a8dbcfc.
Baselinearchive638343458 SHA01f84410750b738a588590740a383c966d88f191c9e1fe657392baebf7857a20;
candidatearchive638346608 SHAed43f52d14422ffb15c450350b5b697b61031ff50cee16d1e051a3e4374aa2be.
Summaryassets638343730/638346820 preservecompletecurrentnativechecks.


## Short-row composition passed; original loaded PVT next

Composition38473990143 one22dce0403... PASSED54native devices/4047R/2663C.
Summary638361292 SHAb278f40d11c45ae4b6ead5b8180d11dfac640f133a748fa798f563d1160fdca2;
archive638361053,6679358bytes,SHA
c9b1decbdc1a9802561933283299d27c48b8c5e097b418b29af7cc46868feaa0.
New v8_kelvin_low_selects_rows profile binds this exact composition.
Run matchedcompact/wire4:1 trees withcascade158_kelvin_supply_direct,stiff65,
nominalandhot/cold, alloriginal256bits/768samples/native devicegates.
No analogacceptance untilactualwavesreviewed.

Pairedcreditmap criticalpath nowmoved toadvertisement transmitter:
link_up input -> FF1165056 Q=u_pcie.advertiser.sent_data_o[4].
Actual source soc_pcie_fc_tx SHA599755ec5824cdea24379dbac7de7eff20cb5dd738cc4f4fd2767c8ddf73b904
inmetadata-late-select candidate02, differentfromcanonical6b5e82a0... .
Arrival4.669152ns/required3.567396ns atslow. PriorstaticFC bankwrite
experimentregressed219.546ps andmustnotberepeatedblindly. Inspectactual
acceptedEOP/ready arbitration cone. Anychange mustretain EOPcommitsemantics
andbackpressure, includecompletepositiveandactualnegativecontrols.


Loadedshortrow runsdispatched onf7829dfe3fdc77c771667b9acd984b123d7dc466:
nominal38474355636;hot/cold38474364222;sourcechecks38474375229.
Keep exacthandles. Sameoriginalgates andmatchedcompact/wire4:1profile.
Mainhalfgridroute38472175339 and32wire38441895491 remainseparate.

Nextdigital diagnosis (proposal only, NOT implemented): physicalbufferedflow
sourceSHA459d69ddaf287004099f91edf1d0c57d35fd324edf4fa9838cb994d398dd2509
already has registeredTXegress. Do not insert a duplicate stage blindly.
Arbiter chosen=locked?owner:flow_valid&&(!advert_valid||prefer_flow);
advert_ready=local_reset&&!chosen&&selected_ready. Late flow_valid from
creditlogic reaches FCacceptedEOPsent_data update. For a reachable valid
advertisement EOP (index5), firstbyte must already have acquiredadvertiser
lock; investigate/prove invariant advert_valid&&advert_eop -> locked&&!owner.
If proved with actualadvertiserandactualarbiter underarbitraryflowrequests,
reset/linkdrop/backpressure, EOPready may use the establishedowner directly,
removing unsensitizable flow-choice logic through an RTL refinement.
No falsepath/clockexception. Must retainactual acceptedEOP commitsemantics,
completebuffered/FC portscoreboards and realbad-owner negativecontrols;
fullobservable sequentialequivalence required before mappedcomparison.
Current exactFCsource is599755ec... in frozenACKcapsule; canonicaldiffers.


## Full32:1 native-macroRC nominal study completed

Old32wire run38441895491 is now TERMINAL/SUCCESS: 13877.539s native
transient,69541rows,604nativeOFFflags,allcomponentengineeringgates PASS.
All768originaloracle samples pass;minoutput158.150641mV,zero wrongsigns
andzero below100mV. Allinterfacelimits/allHBT/allMOSpass,diagnosticsempty.
Summary638367450 SHA5ecfa6f1b20e11cbcdfd9903405b00f5cb6b6cbdf9de05e41afb6864411a3e57;
archive638365881,2136119128bytes,SHA
4f5479f8be043bfa476d88ebc486ee0ceb8db29018959eb61fdc887e5f84aae5.
Fullreceiptpcie-32-native-wire-nominal-20261014.json. Do not duplicate.

Scope remains30cascade14 kelvin_supply_feed macros plusv8lowcritical final.
Intermacro connectionsanddifferentialclockphases areideal; noassembledtree
GDS/PEX,PLL/CDR,jitterBER/RFsubstrate/ESD/fullx4orchipacceptance. This is
real32:1nominalmacroRC progress, notclosure. Currentnewshortrow4:1PVT
38474355636/38474364222 remainsactive andusesdifferentcascade158prestage.
Latestchecks38474375229 passed. Mainhalfgridroute38472175339 remainsactive.
