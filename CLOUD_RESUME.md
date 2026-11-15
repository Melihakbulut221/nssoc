## Native select checks runner repaired; corrected run live

43741684472 FAILED before DRC execution. Artifact14172970266 SHA81ffc4ff74638a29fecc892dbe1c82e1af5125da8b570f140c2cab9e84e058ae verified RAM: drc/run.log contains AppRun cannot write uid_map: Operation not permitted; exit127. This is Ubuntu24.04 native runtime launch failure, NOT measured DRC/LVS result. Geometry/source checks passed before launch. Workflow runner changed ONLY ubuntu24.04->22.04 (same runtime as ongoing timing jobs). Commit1d2f582c16c0226bb8cebd3e7c23e72137fcd226, corrected run43741997075 confirmed IN_PROGRESS. No rule/threshold/guard changes, no repeat of unchanged failed job.

43741495046 NOR sizing native allcorner step still confirmed IN_PROGRESS. Previous turn launched physical checks; this turn diagnosed authenticated runtime failure and dispatched repaired environment. Objective active, no completion claim.

Read-only RTL investigation: current measured link_dllp->retry.timer path reaches timer reset on tx_valid_o && tx_ready_i && tx_eop_o && (tx_replay_o ? tx_first : !timer_running), soc_pcie_replay_tx.v lines522-523. Original source explicitly starts timer on last transmitted byte. Any future pipeline must preserve that semantics and ACK/training/replay priorities; do not add a simple one-cycle delay and claim equivalence. No RTL change made. Whole-root Git recursive tree timing/combined is TRUNCATED (~44813entries); use contents subdirectories or subtree SHAs for complete source searches.

## Native select-width2 checks dispatched; timing NOR trial confirmed running

New run43741684472/head d522bb6902e891ae5787c982cf2bc81fba56f6d4, branch codex/select-width2-native-checks confirmed IN_PROGRESS. scripts/check_select_width_candidate.py asserts exact four2umrppd/sixcore/sixsubstrate geometry and invokes existing unmodified check_pcie_cdr_feedforward_v1.run with explicit candidate TOP nssoc_cdr_select_feedforward_layout_v1_rwidth2_candidate, KINDselect,12devices. Workflow regenerates original baseline and candidate with full geometry replay, prepares pinned LibreLane3.0.5 SHA d6a349ec and unmodified IHP decks5e6d592 using lock verifiers. Runs all560 DRC categories, deep+flat12device transistor LVS and five faults: wrongresistor/missingcap/open/short/offgrid. All prior acceptance conditions retained. Artifact select-width2-native-checks-RUN contains native reports and candidate proof. Await actual results; no DRC/LVS pass claimed. No experimental workflow merged.

Timing43741495046 confirmed IN_PROGRESS in native sizing/allcorner measurement step. Do not restart.

Separate214delay lineage compact43741316572 SUCCESS now inspected; artifact14171584884 SHA4f3068937f20e91a0d0edd42d7cd2db0d5865086e7793b3959541a162cc3a1a9 verified RAM. ODB0338ee8b0c84289d3ac83f67c0d2033a00d033548e83e92154bebd655a36eae8,setup2154/0/0,slowWS-1.77885ns,hold0/0/7 withfastWS-.0299224ns,slew36/6/3cap0. NOT preferable to current346delay holdzero43fc; retain as separate experiment only.

Previous goal turn made concrete timing/physical generation progress. This turn adds native physical qualification execution and verifies live timing work. Full objective remains active/unclosed.

## 2026-11-15: RX-EOP hold-clean result verified; physical passive width candidate generated

GitHub push/admin permission verified. No persistent local checkout or CAD files created.

Current best: producer 43740394021/a21affd587931ff1b2aa84f891184f2ef485bd7b SUCCESS. Native artifact14172790245 SHA3da87458d6ad89a431c1de0853161ae0332a9d6cf19bbd5db3ba18b43157dfe6; derived14172641068 SHAe11d6e5f0eed80f02facb6cbcb718d0bf17f30a2fcaae50583c2985db3f04aee. Compact43741306361/2453d6a1f99717b10b43de2626b5579a5d2b5bb1 SUCCESS authenticates full derived archive and nine state/min/max members. Compact14172575935 SHA59ad57e0e8b5a41685983df900469eb482fef8a56426340d5491ddf8afc90b5e verified RAM. ODB43fc6b1318b92727bf8803950125686246bd55698015069d98b3247fdabde230. Setup2152/0/0, WS-1.78198/+.0185629/+.965397ns; hold0/0/0, WS+.222705/+.143183/+.00520262ns; slew36/6/3 cap0. No routed final acceptance. Improvement only2setupviolations and5.43psWNS. First worst is link_dllp FF164080->FF326881; NOR739727/739732 stilloriginal nor2_1/nor3_1 with .679290/.727554ns delays.

NEXT LIVE: 43741495046, codex/rx-margin-eop-nor-sizing/head493dd486a1cbc72cd7039c18066c671bc04c6cea. Worker size_rx_dllp_nor_gates.py restores exact43fc/source43739336608 with all archive/member/ODB/path guards. Two NORs _1->_2, retains346delays, bothbypasses, all previous buffer sizing; fresh allcorner timing and incidence/legalization checks. Experimental workflow NOT merged. Do not reuse old214delay metrics as current. Separate214delayRX-EOP43739796751 SUCCESS; compact43741316572/50f60d28aac7ba2f3803eea7c72bad9b4dcae97a SUCCESS but contents not yet inspected.

PHY: original passive source acquisition43740622508 SUCCESS, artifact14171769619 SHA56d5473fc33b95f28a320fc5b31bac9d07ad9989662f66335023a55b723f42e2 RAMverified. Physical width trial43740930024 failed missing hw/soc/out parent directory, not circuit failure. Fixed parent mkdir only, commit2652f89745b64537aec999dd2a940b8da69034c7 on codex/select-passive-width2-geometry. Corrected43741230042 SUCCESS. Artifact14172009186 SHA966be16d9a352088b1318fdee08a850e9f61687259c13dead1408a56bc31d948 RAMverified. Baseline original GDS layer-by-layer merged region XOR empty, same bbox/top/DBU, identical schematic and LEF. Candidate changes four select rppd widths1u->2u, lengths6u/8.6u unchanged, MIM4.8u unchanged, six substrate contacts and all ports/bbox preserved. Files scripts/generate_select_width_candidate.py and hw/soc/flow/make_pcie_cdr_feedforward_width_trial.py. Uses frozen original generator and authentic pinned PDK. All acceptance flags false. NEXT: candidate standalone transistor LVS/DRC, fresh RC, loaded current/timing, then actual650 geometry integration; do not substitute circuit parameters under stale RC identity. No fullPHY/layout acceptance.

Full production objective remains open, including setup, slew, full serial PHY/PLL, routed signoff, SRAM internal LVS/Liberty/RC and foundry acceptance. Do not merge experimental cloud-evidence-summary.yml.

## Passive select physical-source acquisition running; RX-EOP trials remain live
New scripts/acquire_select_passive_source.py on codex/select-passive-source-acquisition restores original selectmacro's5actualsourcefiles (GDS,LEF,layoutresult,schematic,rootresult) entirelycloud. Binds configSHA, originalproducer41547492718/headf1248c7a,release432088543/tag,asset703588571 SHA516d5105c2819cf5419ee47f32702937e04c27c9aa8e38ba7776b4fd83eb6844 and every archived member size/hash fromcomplete_members. Rejectspath/nonregular/duplicate/missingmembers. Exportsjust5sources+acquisitionreceipt; deletesonlyown verifiedtemporarytar,notoriginalrelease. No mutatedgeometry/acceptance.
Initial43740586848/head9a8750c5d842600385cf8572b370d1170b1f89ad mistakenlyexpected6selectedfiles; sourcecatalogliveinspectionshows5. Correctedexactcensus onhead6e6b9e41a75b8202f7c542f08d46e502feda6856, actualASTchecks passed; dispatched43740622508, verifiedQUEUED. InitialjobstillIN_PROGRESSlastpollbutwillhitcensusassert; donotacceptinitialhead/no needrerunidentical. Followcorrectedrun43740622508. Receipt newline ASTcheckedactualnewline,notliteralbackslash-n.
Nextinspect authentic layout/result.json andschematic.cir toprepareconsistentpassivecellregeneration fromnativePDKgeometry; current650nonMOSsourceidentitypreserved butchangedpassiveswillrequirefreshLVS/RC. Noanalogparameterchangeimplementedyet.

43740394021 current346delayRX-EOPsizing and43739796751 separate214delay+NORRX-EOPsizing bothverifiedIN_PROGRESS,lastpoll. No restart. Currentverifiedbestc515 setup2154/0/0,hold0/0/0,slew36/6/3,notfinalrouting. Previousgoalturnconcretecurrentimprovement+trial;currentturn physicalsourceacquisitioncode+verifiedwait. Fullgoalactive.

## Current holdzero commit-read sizing verified; RX-EOP sizing now applied to this source
43739336608/0eb8c912 SUCCESS. Native14171338738 metadataSHA08140ac22b4777533d7c8d62e647c6630065509f705f306f53e02bbf2fd6490e,size384818755B;derived14172156500 metadataSHA9cc11856df03d66a453e7eb5fb43f24049213fc277a3a8aa780b5b146d56267f,size17995323B.
Compact43740169951/head4054271dfce6cbe31d55f4ec51bcf4baf8133d83 SUCCESS authenticatesfulloriginalderived+9globalmembers. Compact14171438698 fullZIP SHA08597357ddc533ab5dfadd883026170c6f8120145bab37687a3e7de0eb865733 verifiedRAM. ActualcandidateODBc515137540ce7cfa486980a7fad69fb88948df270595770b9ce0afd150cbc61c,state run/4-nssoc-sizedfast/state_out.json: setup2154/0/0 (was2170),WS-1.78741/+.0185629/+.965397ns;hold0/0/0,WS+.222705/+.143165/+.00518863ns;slew36/6/3cap0. 346delays,bothbitbypasses,linkup/staging/readcopy sizes retained;noNOR. Thisisnewbestcurrentholdzero,notroutedclosure.
VerifiedactualfirstslowmaxRX-EOPpath contains sixsamebufferoriginalmasters3452buf2,3451buf4,3450buf2,3449buf2,2700buf1,2021buf1; smallRCdifferencefromolderNORlineage:2700delay.256613ns,2021.307369ns. No mixedmetrics.
Dispatched43740394021/heada21affd587931ff1b2aa84f891184f2ef485bd7b,codex/new-rx-margin-eop-sizing,verifiedin_progress. Worker scripts/size_rx_margin_eop_buffers.py binds exact43739336608/0eb/native14171338738/08140ac2 andderived14172156500/9cc11856,ODBc515/source43738187241. Applies3452:2->4,3451:4->8,3450:2->4,3449:2->4,2700:1->4,2021:1->4. Exactpath/master/incidence/port/censusguards,legalization,freshallcornerSTA,verifieddownloadcleanup;ASTpassed. Currentglobalholdzero mustbeconfirmedafterECO. ExperimentalworkflowNOTmerged. Separateold214delay+NORRX-EOP43739796751 stillliveatprecedingpoll.

PHYphysicalsourcepreparation investigated: originalreleaseasset703588571 native-fresh-rc.tar.gz SHA516d5105c2819cf5419ee47f32702937e04c27c9aa8e38ba7776b4fd83eb6844 includes binding/inputs/parent/inputs/rc_select/layout/{schematic.cir,result.json,nssoc_cdr_select_feedforward_layout_v1.gds,*.lef} andparentrc_select/result.json. Exactpermemberhashes/releaseproducer in scripts/cdr-mos650-geometry-inputs.json; nofilesdownloadedlocally. Existing cdr_mos650_geometry.py restoresparent500 andsplitsMOS then cdr_mos650_identity.py buildsall650references; changingpassivesrequiresindependentreferenceandfreshgeometry/RC, not merelychangegateassembler. No newanalogcircuittrialclaimedthisturn.

Previousturnverifiedwait;currentturnconcretevalidatedcurrentsetupreductionandnewRX-EOPtrial. Goalactive/fullproductionobjectiveunchanged.

## Commit-read sizing verified improves setup count; corrected D-source PHY delay measured

Compact43739572073/d0a30a581c9ca7a33fd664fe41a68cb08738221c SUCCESS; fullcompact14171477906 SHA913a64c36c2fccd4e2b2d151f43f8185e55f642d2e64d5c1b34ed6d0b2c5e047 verifiedRAM. Sourcefullarchive14172090238/8c36d891 and9state/min/maxmemberhashesauthenticatedincloud. Actualcandidate43738428141/4b17798 ODB e314031cf534e3e34c1a56d44e2582917e33dff938ca70c022e99aefa1c14763: setup2156/0/0 (was2172),worst-1.78632/+.0185629/+.965397ns,hold0/0/7baseline,WSfast-.0299224;slew36/6/3cap0. Separate214delay+NORlineage,notcurrent346delayholdzero.
Newworstoutput_activeFF175709->FF176720 throughRX-EOPdistribution. Authenticatedfirstpath: fanout3452buf2(.325922ns),3451buf4(.420541),3450buf2(.370699),3449buf2(.369285),2700buf1(.255907),2021buf1(.307361).
Newbranchcodex/new-rx-eop-sizing/head8f7445f1cb158bff162c76e14966c960b9c41501 dispatched thisturn. scripts/size_rx_eop_buffers.py binds43738428141/4b177/native14171374015/394cb307 andderived14172090238/8c36d891,exacte314/source43737191650. Sixnativebufferchoices3452:2->4,3451:4->8,3450:2->4,3449:2->4,2700:1->4,2021:1->4. Exactfirstpath/master/instanceincidence/port/census guards,legalization,fresh3cornerSTA,verifiedZIPcleanupretained. ASTpassed; notacceptance. CheckrunIDbybranch. Current346delaycommit-read43739336608 stillverifiedIN_PROGRESS.

CorrectedPHY43739539843/edc742b0 SUCCESS. Fullartifact14171736938 ZIP SHA3f068f923e7fc90dee43d24765c6944ad0f93195c7175e810ce4140465de3a28 verifiedRAM. Nativeactual650contractguardDQP->USP/DQN->USNpassed. Dsampler->driverbase median79.9829/80.2552ps,53unmatchedof127crossings. Driverbase->outputmedian33.5526/32.6781ps. Dsampler->outputmedian117.7346/121.9114ps,69/70unmatchedof127;max234.629/233.823ps. Allstatisticsmatchedsubset, boundedbynextsourceedgeor2UI; no claimunmatchedmeanspulsephysicallymissing. This supersedesB-reference177psasdriverlatency. Ddiff-.300224..+.294893V,base-.11131..+.11455V,output-.22015..+.23421V. Sourceexactfailedfull256bitcapture; no acceptancechange.
Nextanalogrepair canfocusactualDQP/DQN->USP/USNpassivelevelshifterandbase loading, notBclockedlatency/polarity. VerifiedparentSE_D0/D3rppd6um/1um,D1/D4rppd8.6um/1um,SE_D2/D5MIM4.8x4.8um. Needconsistentphysicalgeometry/source/newRC ifaltered; do notcallSPICE-onlyparameterchangeintegratedlayout. DriverbaseattenuationanddelayobservedbutchangingRorCtradeoffsrequireactualsimulation. CurrentmatchingRCassemblystrictgeometryguards mustremain.

Currentturn freshmeasuredsetupimprovement+sixbuffertrial+correctedPHYcausalmeasurement. Fullgoalactive,wholeproductunclosed.

## IMPORTANT correction: select propagation source is D sampler, not B; corrected diagnostic live

Physicalparent mapping docs/evidence/cdr-clock-access-domain-parent-map.json inspected oned63d854. SE_D0/D3 resistors6um/1um connect DQP->USP and DQN->USN; SE_D1/D4 8.6um/1um toAVSS; SE_D2/D5 MIM4.8x4.8um likewiseDQP/DQN->USP/USN. Actual selectdriver isafterclockedDsampler, not directlyB. Therefore preceding43738966004 Bselect176.97/176.60ps includesclockedsamplerlatency and MUSTNOTbeclaimedpurelevelshifterdelay or usedaloneasgroundsforanalogdriverresize. Priorfinalresponse's177ps ismeasurementbutitsdriverinterpretationoverbroad; userinformedthisturn. A/Csourcepathsnotchanged.
Dispatched43739539843/headedc742b0e84aed38896462a83abda1b84f583416,codex/reduced-input650-corrected-propagation,verifiedIN_PROGRESS. Changesonlyselectchainreference toactual xpd.dqp/dqn. Adds nativephysical650contractguard forexactoneDQP-USP andDQN-USN resistor plusrequiredDaliases; existingraw/sourcehash,originalsamplingcounts,actualtransistorbaseIDs andcrossingwindowguards unchanged. ASTpassed. Readcorrectedlevel-shifter-propagation.json before anycircuitchange. Do notcountunchangedfailingcaptureaspassingPHY.

Separate214delay+NOR threebuffertrial43738428141/4b17798be9fb38d258afea042c42221abc10812d SUCCESS. Derived14172090238 metadataSHA8c36d89171eee704b50cfa18d6b387c0878982e5349a7883a431e139ae5b09c7,size17967752B;native14171374015 metadataSHA394cb3078d24d756eeab0d1582a020cf90db30be5e17de5c2f8090203d7e0545,size384715776B. NumericalresultNOTYETverified.
Dispatched43739572073/headd0a30a581c9ca7a33fd664fe41a68cb08738221c,codex/new-rx-commit-read-compact,verifiedIN_PROGRESS. Reuses exactproducer/head/attempt1/fullZIPsha/memberhashsummaryfor9state/max/minmembersandfirst5paths. ASTpassed. Readbeforechoosingnexttrial.
Current346delay/noNOR threebuffertrial43739336608/0eb8c912 verifiedstillIN_PROGRESS. No restart; actualcurrentbest9f6530setup2170,hold0allcorners aspreviouslyverified.
Thisturncorrectedcausalinterpretationfromauthoritativephysicalconnectivity,dispatchesguardedcorrectmeasurementandcompletedtimingevidenceextraction. Fullgoalactive; no finaltiming/fullPHY/productionclosureclaim.

## Combined bit5 improves WNS and retains holdzero; current commit-read sizing dispatched

Compact43739027505/7422fdf1008aa9f48139d0e742e73fb695bf790f SUCCESS. Fullcompact14170994814 ZIP SHAc0555ec384c5482f623f41b97370819e715d324da15999765e0abfdf67223061 verifiedRAM; cloudauthenticatesoriginal14171158875/0c216396 and9consumedcornermembers. Actualcandidate43738187241/fc2b2e ODB9f6530faa761014a873f18049b28840b43644701f3b3778471b528588d363c52,state run/4-nssoc-sharedfast/state_out.json.
Setup2170/0/0,worst-1.78917/+.0185629/+.965397ns (was-1.815202); hold0/0/0,worst+.222705/+.143165/+.00518863ns; slew36/6/3cap0. Improvement26ps,no countreduction. Notroutedclosure. Bothbit4/5bypasses,346delays,linkup/staging retained; noNORsizing.
Authenticatedfirstslowmaxpath matchescommit_copies[5].read_copy andexact3buffers8443buf1(.581666ns),ABC734931748784buf1(.772734ns),7468buf1(.945489ns). This requalifiesactualcurrentpath, independent ofolderNORcandidate.
Dispatched43739336608/head0eb8c9127c6621346e9df8572d2120d13547a913,codex/new-rx-margin-commit-read-sizing,verifiedQUEUED. Worker scripts/size_rx_margin_commit_read_buffers.py binds exact43738187241/fc2b/native14171581554/1b62cfdb andderived14171158875/0c216396,ODB9f6530,report.source_run43735491108. Applies8443buf1->4,ABC748784buf1->4,7468buf1->8 withsourcepath/master/incidence/ports/censusguards,legalization,freshallcornerSTA andverifiedZIPcleanup. ASTpassed. NoNORmerging;346existingdelaysunchanged. Separateolder214delay+NORcommit-readtrial43738428141 stillliveatprecedingpoll. Donotmixlineages.

PHYpropagation43738966004/8ea9e300 SUCCESS. Fullartifact14171945613 ZIP SHA01e35605a158e38a0e557a2bbe72d5a4545293e15a99b14c79f3f454b5ad73ef verifiedRAM. Sourceboundexactnativewave andlogicalbaseIDs preserved. Sampler->driverbase medianA71.94ps,C86.10ps,Bselect0/1 158.25/158.50ps amongmatchededges. Driverbase->outputmediansA47.76,C46.65,Bselect33.55/32.68ps. Sampler->outputmediansA116.71ps,C138.33ps,Bselect176.97/176.60ps. Matchingboundedbynextsourceedgeor2UI; missingcountsA62/129,C77/129,Bselect96/129and97/129, so mediansarematchedsubsetnot universal fixedlatency. Inputdriverbase Bdiffonly-111.31..+114.55mV vs sampler-397.12..+381.94mV. Missingareunmatchedwindows,notautomaticphysicalmissingpulseproof. Strong evidence toinspectBselectlevelshiftchain beforestaticXORpolarity changes. Fullbits/settle/voltagegatesremainFAIL.
Readactual650modelassembler confirmsstrictidentity/geometry/currentRCbinding. scripts/cdr_mos650_geometry.py acquirespinnedreleasedparentlayoutand generates200MOS from50origins preservingtotalwidth; scripts/derive_cdr_mos650_physical.py adapts650DRC/deep/flatLVSchecker. Do notmutatecompiledparameterswhileclaimingmatchingRC. Next locate BQP/BQN->USP/USN levelshifter MOS/resistorgeometry and regeneratephysicalcandidate consistently ifchanged; current smallsignal delay measurementaloneisnotrepair.
Currentturn concretecombinedtiming evidence+newcurrenttrial andPHYlocalization; goalactive,fullscopeunclosed.

## Combined bit5 native run completed; compact evidence and PHY propagation analysis live
43738187241/fc2b2e1640ae110c2afbf2e54893ba0cd00ed688 SUCCESS. Native14171581554 metadataSHA1b62cfdb160641918facedf0c67ca68313ef8942f5afec1bc93f3ce4c1219bb9,size384835004B. Derived14171158875 metadataSHA0c2163969a74cddd262e1afc5c4ea9b489828698d5007e79b2800794f1d059df,size18003461B. Numericalresultnotyetinspected; do notinferholdzeroorclosurefromjobsuccess.
Dispatched43739027505/head7422fdf1008aa9f48139d0e742e73fb695bf790f,codex/new-rx-margin-bit5-bypass-compact, verifiedIN_PROGRESS. Reusedsummary authenticatesexactproducer/head/attempt1,fulloriginalderivedZIPsha and9globalstate/max/minmemberhashes; first5pathseach. ASTpassed. NextreadcompactSHA/cornermetrics before combiningfurtherresizes. Currentcommit-readbuffers43738428141 verifiedstillIN_PROGRESS; no native restart.

PHYexactconnectivity inspection identifies drivers:273B=uap/274B=uan outputsadn/adp;294B=ucp/297B=ucn outputscdn/cdp;295B=usp/299B=usn outputss0n/s0p;296B=usp/298B=usn outputss1n/s1p. Verifiedagainstactual124HBTcontractandbinding, not guessednetnames.
Dispatched43738966004/head8ea9e300e7b62d4a794d0f3e68bdfafeea25eee2,codex/reduced-input650-level-propagation,verifiedIN_PROGRESS. Extendsalreadyverifiedreadonlydiagnosis withlevel-shifter-propagation.json: fourchains Adata,Cdata,Bselect0,Bselect1; sampler->actualdriverbase,driverbase->output,sampler->output same-directionzero crossings. Eachmatchlimitedbynextsourceedgeor2UI, missing/multiple explicit; interpolatedcrossingtime withnative rowidentity, perstage min/median/max plusdiffamplitude. ExactlogicalB->nativeIDguard. No sourcewave/circuit/stimuli/acceptance mutation; no newnativeSPICErun. Originalsamplingcounts/hash reproduction retained. ASTpassed. Readresult tochoosephysicaldriverrepair without mistakingtransientinputcoverage forstaticXORdefect.

Previousgoalturn newsettledtruth evidence, currentturn newsource-boundpropagationanalysis andcompletedphysicalcandidate/verifiedwait. Fullgoalactive; setup/holdfinalroute/fullserialPHY/productionunproven.

## Actual comparator settled-input diagnostic authenticated; physical trials still live

43738464847/0c847e12a7242bf4a492e43b5adfb46b779b4cbd SUCCESS; fullcompactartifact14171263093 SHA bcc83af234c800a2951456a2c36de209d98a6cea4436b0acd2d7b8996c5aecf4 verifiedRAM. Diagnostic actual-comparator-settled-truth.json inspected. It reuses source-bound failedphysicalwave, not a newpassingPHY.
At realinputminimum25mV andcontinuous125ps: Xall4truthcombinations have0wrongsignrows but unequalinputs01/10 reachonly72.777/60.057mV(max), all637/462rowsbelow100mV. At50mV/125ps X01/10 have66/37native rows,correctsignbutmax71.169/59.661mV,stillbelowgate. At100mV/125ps only00/11represented. Yunequalinputs01/10 areabsent evenat50mV/0duration; at25mV/62.5ps only00/11represented. Thus no fullsettledXORtruthcoverage/no staticconnection-bug proof. Inference: upstream levelshifter/sampler pulse overlap and propagation plus insufficient output amplitude matter; inspect delaythroughaq/bq/cq->ad/cd/s0/s1before speculativepolarityfix. No samplewindows/gateschanged. Native rowcountsnot independentbits; original full256bitmeasurementstillFAIL.
This corrects overbroad interpretation of prior sampler-output truth: actual comparator inputs are distinct level-shifted signals. Next physicalrepair mustpreserveactualgeometry/RC consistency; do notpatch extractedtransistorparameters and claimlayoutmatch.

43738187241 combined346delaybit5 bypass and43738428141 commit-read3buffers verifiedIN_PROGRESS in nativephysical steps. Do notrestart onobserverwait. Canonical43727638507 SoCformal job132852961996 nowSUCCESS,pilotformalSUCCESS; actualproofartifactsnotyetcontentverified inthisturn. SoCartifact14171163422/e9e12802d793e5c2d449b367fc5833afdd57e6f345afd6c9abaad3130fcfd06e andpilot14170965253/e3bcd15441b5c47d062e7afce56c1e629b71bc238099ee138bfd4ba8f2902057 metadataonly. Mainchecksjob132852962017 stilllive;oldRTLfailedanchor remainshistorical.
Currentturn newdiagnostic evidence changesnextanalogaction plusverifiedwaits;prior turnconcretephysicaltrial. Fullgoalactive;production/fullserialPHY/finaltimingnotclosed.

## DLLP sizing measured; next commit-read buffer trial and comparator-input diagnosis running

Compact43738086147/d05fcb9779fd29e32d18c5df3a4479fd707b7b77 SUCCESS. Compact14171122652 fullZIP SHA44b4831e66f993a9bb3adc52a388d1a2349b355388d14450ee0dbca83c94f92e independentlyverifiedRAM. Authenticates originalderived14170414642/b6b0be57 andall9state/max/minmembers in cloud.
NORcandidate43737191650/787beb nowODB0b4369a966874923d23d1befad4081dd7744c9e14eb60dbe5707d300ce487940: setup2172/0/0,worst-1.78917/+.0185629/+.965397ns;hold0/0/7baseline,slew36/6/3cap0. Sourcehad2171setup,WS-1.790514; thus WNSimproves~1.34ps butcount+1, NOTaccepted/NOTmerged. Separate214-delaylineage.
NewworstFF551964commit_copies[5].read_copy->FF365477read_bank[5]r2slot[2].near_q[7]. Buffer8443buf1 delay.581666ns,ABC734931748784buf1 delay.772734ns,7468buf1 delay.945489ns. Strongload/slew on chain; firstclocktoQ.725387ns/inv748093.578078ns alsoexplicit. No finalrouteclaim.
Dispatched43738428141/head4b17798be9fb38d258afea042c42221abc10812d, codex/new-rx-commit-read-sizing, verifiedIN_PROGRESS. Worker scripts/size_rx_commit_read_buffers.py binds exactNORproducer/native14170896911/55fa8653 andderived14170414642/b6b0be57/ODB0b4369. Firstpath/masterguard; resizes8443buf1->4,ABC748784buf1->4,7468buf1->8. Exactnativeincidence/port/census checks, legalization,freshallcornerSTA; ownverifiedZIPcleanup retained. ASTpassed. Thisexploratorybranch retainsNOR+bothbypasses and7baselineholds; cannotmixwith346delaycandidate.
Current346delay bit5bypass43738187241/fc2b2e remains verifiedIN_PROGRESS.

PHY artifact14170738655/052f64a0 inspected native124HBT topology and98resistorgeometry. Actualcomparator Xdatausesadp/adn,selects0p/s0n; Yusescdp/cdn,s1p/s1n. These are level-shifted/transistor-base inputs, NOT identical to prior diagnostic sampler aq/bq/cq truth. Therefore priorwrongtruth doesnotbyitselfprove staticXORdefect. Selectbases~1.1..1.30V, topdata~1.67..2.05V; actualbranchsettling/current needsmeasurement. No unverifiedcircuitfix.
Dispatched43738464847/head0c847e12a7242bf4a492e43b5adfb46b779b4cbd,codex/reduced-input650-settled-truth, verifiedQUEUED. Extendsauthenticatedreadonly43737724460script to compare actualdata/select port differences againstoutput. Continuous stable-sign andminimuminput-magnitude windows thresholds25/50/100mV, duration0/.25/.5/1UI; outputs native rowcounts, min/maxsignedoutput, wrongsign/under100mV and actual selectHBTmodelcurrents foreachtruthcombination. Diagnosticwindows donotrelax originalsampleacceptance; originalsamplingcounts/hash reproduction stillrequired. Native rowcounts explicitlynot independentbittests. Reads exactalreadycapturedraw/no newsimulation,no layoutmutation. ASTpassed. Nextreadactual-comparator-settled-truth.jsonbeforeselectingbias/load/speed repair.
Allworkcloud,noexperimentworkflowmerge. Previousturnconcretecombinedrepair/diagnosis;currentturn newmeasuredcriticalpath andcontrolledtrial plusmoreprecisePHYlocalization. Fullgoalactive,finaltiming/fullserialPHY/mainchip andproduction stillopen.

## Current346-delay bit5 qualified and combined bypass dispatched; PHY failure localized

Measurement43737070576/4ddcac924bb5c48dea6bc76e746a85fcf0e75e31 SUCCESS; native14170927600 metadataSHA609df83722b9b4e2804422e8939236237f520ea198b0072c6dc2c9c56e077bb2; derived14170927529 metadataSHA3346f35767eef22c9914831a492b508b2fef56e053e0dab7b28f2e51d54252d1. Direct RAM observer download timedout120s, no CADrestart. Compact43737984408/6b79fd328f0ec656cc05bcd3d16b3e708ccbb459 SUCCESS authenticatesfulloriginalarchive and24 consumedmembers. Compact14171057697 fullZIP SHA6a0755d8fa1f588af85a017c26955ec0dfa6bfd212f6ed3f566f13585e4bb69a verifiedRAM; rawreports inspected.
ActualunchangedODBbb7a8554565670dc9918249ecd4fc625dd41b9aacec6da5d8305f88a954ad18c. TopologyFF175605/Q->head_last[5]->hold32105/A, outputnet32105 exactly805444/A retained and738686/B critical. Sharedmin .809978902/.412984222/.192794502ns; XORmin1.530964971/.868574798/.490187138ns. XORsetup-1.815202236/+.299670964/+1.499096632ns. Globalsetup2170/0/0 hold0/0/0 unchanged.

Dispatched43738187241/headfc2b2e1640ae110c2afbf2e54893ba0cd00ed688, codex/new-rx-margin-headlast5-bypass, verifiedin_progress. scripts/trial_rx_margin_headlast5_bypass.py bindsphysical43735491108/7b1/native14170478794/28158aac andderived14170063336/581d6036, actualbb7a; independentlyauthenticatesmeasurement43737070576/4dd/14170927529/3346f357. Same1.5/.8/.48nsqualification, sourcepath/master/port/census/FIRMfixedplacement guards. OnlyXOR738686/B bypasses32105,805444/Aretainsdelay; all346delays,bit4bypass,linkup/stagingretained. NativeallcornerSTA pending; no changedclocks/gates. ThreeownverifiedZIPcopiescleanupretained. ASTpassed. ExperimentalworkflowNOTmerged.

DLLPNOR43737191650/787beb429b87825d01fbccf4115b11f5c397894e SUCCESS. Native14170896911 metadataSHA55fa8653c27e7bffcc4b7d2003eac8417cdcc01797ef083af740761ef16a82d4; derived14170414642 metadataSHAb6b0be574b3929da44fa1c9b4139a0353bd37bc57dcbe4df15327522e9982fb1. NumericaloutcomeNOTYETinspected. Compact43738086147/headd05fcb9779fd29e32d18c5df3a4479fd707b7b77, codex/new-rx-dllp-nor-compact verifiedIN_PROGRESS; authenticatesfullarchive+all9state/max/minmembers, first5paths. Readbeforecombining.

PHYdiagnosis43737724460/832b70f SUCCESS. Fullsmallartifact14170738655 ZIP SHA052f64a053a1d502bbe68442800f669afb546355814e6bd85ac430032227edf5 verifiedRAM. Read-onlyauthenticatesoriginal3.47GBarchiveandrawc19b... in cloud; originalsamplinggates/counts reproduced. All32clockbase probes show0missingcrossings, nativecrossings21.09..24.22pslate. Original10ohm prebuffer sourcepeak4.13445/3.87495mA (old5.48/5.33mA), yet samplingA/B/C/Dwrong129/80/88/104; below100mV129/154/144/145. ComparatorX/Ywrong404/21, below100mV707/601. Phase17.9578mV<30mV. Observedstable-input comparatortruth alsofails: X10wrong91/124,X01wrong24/32,Y10wrong57/59,Y01wrong2/2; do notblamesolelyidealbitsorclock. NotquasiDCproof, transientinputs maystillmatter. VI ownsignedcurrent51.534uApasses but outputfollower3.114mA/emitterfailsaspreviouslyrecorded. Needinspectactual-hbt-topology-context.json / actual-resistor-topology.json and failedsamples toidentifycomparatorbranchbias/loadbeforecontrolledcircuittrial; do notrelaxacceptance. No fullPHYclosure.

Previousgoalturnconcretefailureanalysis+worker; currentturnfreshmeasuredcombinedrepair+localizedPHYfailure. Goalactive; fullscopeunchanged.

## Reduced-input failure localization dispatched
43737724460/head832b70f87a8b4d8c370b1a62a12a4e49575ed1c5 on codex/reduced-input650-failure-diagnosis verified IN_PROGRESS. Reuses authenticated read-only localize_buffered650_failure.py, binds exact failed producer43727364585/ed63d854, native14170009078/b12f0418e94da9228f4aa349f0b99af3a6aa11d682fbcfa7b4ca9dcce02172ff and rawc19b5649b288d2024a9c6932bd2750051cb270f52a02751fdf6c1e645e8c61cb. Full archive hash, unchanged report, exact physical contract hash/650devices, raw hash and original sampling counts rechecked. Computes prebuffer source demand, native clock-base crossings, comparator observed-input truth and device headroom; no simulation rerun, modified acceptance or circuit. AST verified before dispatch. Experimentalworkflow not merged. All native work stays cloud.
Next: inspect this diagnostic and ongoing timing43737070576/43737191650. Combine bit5 bypass only after fresh current346-delay margins pass. PHY rejection and current setup/hold metrics documented below. Goal active; this turn new authenticated failure analysis and targeted cloud worker.

## Current recovery: timing candidates verified; reduced-input PHY rejected
GitHub owner authentication and push/admin permission reverified. No local persistent source or CAD artifacts.

Compact43736726551/caf7ed23 succeeded; full compact ZIP14169599566 SHA2291971ef16cd95789c4bdd7a18cdc3989303129afd83d14b36c14af7541b53f authenticated in preceding work. Current346-delay candidate43735491108/7b1b49fd has ODBbb7a8554565670dc9918249ecd4fc625dd41b9aacec6da5d8305f88a954ad18c: setup2170/0/0, worst -1.8152/+.0185629/+.965397ns; hold0/0/0 with +.222705/+.143165/+.00518863ns; slew36/6/3,cap0. Not routed timing closure.
Separate214-delay bit5 bypass43735708592/81d677 has ODBdce5dd831c7f08a37dc2fb915b33e78d4d16506c970e17ab62ebe1ce06dfe4a5: setup2171/0/0,worst-1.790514ns;hold0/0/7 unchanged baseline. Cannot mix those results with current346-delay holdzero source.
Recovered live run43737070576/head4ddcac924bb5c48dea6bc76e746a85fcf0e75e31,codex/new-rx-margin-headlast5-measure. Read-only requalification of bit5 hold32105/XOR738686/B on exactbb7a before combining bypass.
Recovered live run43737191650/head787beb429b87825d01fbccf4115b11f5c397894e,codex/new-rx-dllp-nor-sizing. Independent214-delay source trial sizes DLLP critical739727 NOR2_1->2 and739732 NOR3_1->2; original measured gate delays .679290/.727554ns. No fabricated NAND3_2; source-bound native guards/all-corner STA pending.

PHY43727364585/ed63d854 completed FAILURE. Full derivedZIP14170726509 SHAca3d1c881a890addc50131a891b34d62421b20daee717f4a79f4737fd9aa0f65 (272165B) authenticated RAM; native14170009078 metadataSHAb12f0418e94da9228f4aa349f0b99af3a6aa11d682fbcfa7b4ca9dcce02172ff remains cloud. Simulator return0,stderr0,5965.80686seconds; functional/electrical assertion correctly rejects. Reduced input/cascode driver does not close loaded timing: three positive outputfollowers xfp0..2 peak3.114435mA per emitter fail device screen. VI signed51.53398uA now passes its own gate; this does not fix sampler/comparator errors. Sources unchanged; fullPHYaccepted false. Need diagnostic measurement of archived raw wave and input/output edge displacement before next controlled circuit change; do not restart identical simulation, relax thresholds or integrate rejecteddriver.
Canonical43727638507: pilotformal nowSUCCESS, socformal/checks stilllive, oldRTLanchor failure remains historical (separatefixalreadyintegrated). Full serial PHY/mainchip routing/final timing and production qualification remain open.

Reduced-input scalar evidence (long sample arrays omitted):

{
  "comparisons": {
    "x": {
      "below_100mv_samples": 707,
      "maximum_clock_to_valid_s": 1.189062500003487e-10,
      "minimum_signed_margin_v": -0.13239314722754594,
      "passed": false,
      "samples": 765,
      "wrong_sign_samples": 404
    },
    "y": {
      "below_100mv_samples": 601,
      "maximum_clock_to_valid_s": 1.189062500003487e-10,
      "minimum_signed_margin_v": -0.008959137071276572,
      "passed": false,
      "samples": 765,
      "wrong_sign_samples": 21
    }
  },
  "diagnostics": [],
  "status": "REJECTED_WHOLE_MIM_ACTUAL650_LOADED",
  "vi": {
    "actual_filter_connection": true,
    "bias_passed": true,
    "closed_loop": false,
    "mean_output_difference_v": 0.014402748599263035,
    "mean_signed_current_a": 5.153398179351501e-05,
    "minimum_active_tail_current_a": {
      "xtx": 0.00025273275229434144,
      "xty": 0.00024926459577271216
    },
    "passed": true,
    "phase_limits": {
      "constant_maximum_abs_current_a": 5e-06,
      "constant_maximum_abs_voltage_v": 0.002,
      "minimum_signed_current_a": 5e-05,
      "minimum_signed_voltage_v": 0.005
    },
    "phase_passed": true,
    "real_input_loading": true
  }
}

## Both new timing candidates completed; authenticated compact comparison running

43735491108/7b1b49fd31f792e97f259b2aaf03a1b08ccf24bb SUCCESS (current346delay staging sizing). Native14170478794 metadataSHA28158aac7871cf83ca7cd888a9dccab5f6c15b31916d89345d56e55d8b190368 size384779107B;derived14170063336 metadataSHA581d6036b40dc4ff3f96f43072c922b983fbeaee813fe6ae9d40dbcaee7d6970 size17976085B.

43735708592/81d677c715cc29465403ed38bc7b9fbb1a736928 SUCCESS (bit5bypass on214delaylineage). Native14170990285 metadataSHA84ce1a208c21ac4c34e744960b266d0be8c6405f92983fbcb3c23252ace2ecdf size384754019B;derived14170865589 metadataSHA36f5fcc727690f6cfd5e0c0a9e020631a6766603b754692fdf1c4f3034996537 size17986946B. Numbersnotyetinspected. Archivecleanup reducesnativeoutput from~3.3GB to~385MB; originalsourceartifactsremaincloud. Needverifyresultremovedcopies/nozipoutputs receipt too, notsizealone.

Dispatched43736726551/headcaf7ed23b7379cef41a412644e7f106191f664d6,codex/two-timing-candidates-compact,verifiedIN_PROGRESS. scripts/summarize_two_timing_candidates.py authenticatesbothexactsuccessfulproducerheads/attempt1,fullarchivehashes,all3states+globalmin/max+18branchreportspercandidate, assertsremoveddownloadcopiesexpected2/3 andnoneinoutputsmanifest. Exportsrawbranchreports,first5globalpaths,scalarresult+archive receipts/cornermetrics. ASTpassed. Nextreadsmallartifact, verifySHA, compareactualsetup/hold beforecombiningbit5repaironnew346delaycandidate. No fullCADrerun forsummary. PHY43727364585 stillverifiedlive. Currentturnprogress; fullgoalactive.

## Bit5 shared-delay topology qualified; one-pin bypass trial running

Compact43735445777/340052fbd61f9a7499bd93a3380d7251c58f1a28 SUCCESS; compact14170177896 fullZIP SHA918a08d0e6fe7e0542c02381b0a49bbdfbe5a4443cc38b70958620a4a4b17f4c (42070B) verifiedRAM. Cloudscript authenticatesphysicalmeasurement43734364727/e7b5 andfulloriginalderived14170515411/1306de38..., all24consumedmembers. Rawreports inspected. SourceODBunchanged20b515. Bit5hold32105A/X minslow/typ/fast+.809978902/+.412984222/+.192794502ns; criticalXOR738686/B min+1.530964971/+.868574798/+.490187138ns andsetup-1.814112902/+.300249159/+1.499502540ns. NativeactualsourceFF175605/Q->head_last[5]->hold32105/A; outputnet32105 exactly805444/A and738686/B. No reusebit4counterpart.

Dispatched43735708592/head81d677c715cc29465403ed38bc7b9fbb1a736928,codex/new-rx-headlast5-bypass, verifiedIN_PROGRESS. Worker scripts/trial_rx_headlast5_bypass.py restoresqualifiedphysical20b515 from43732602282/5df33083 native14169149260/126524463 andderived14168919765/3d20a73; independentlyauthenticatesmeasurement43734364727/e7b5/14170515411/1306de38. Sameconservativeminbounds1.5/.8/.48ns, exactfirstcriticalpath and3targets. SharedECO updatedtohold32105, critical738686/B, retained805444/A, sourceFF175605; nativeexactmaster/incidence/census/port andFIRM-coordinate/orientation/statusrestoreguards retained. BranchSTAconnectivitypointsat32105. Onlyonecriticalpinbypassed; oldbit4bypass/linkup/staging retained. No clocks/gatesrelaxed. Sourceis214delaylineage with7baselinefastviolations, not346delayholdzero; mustrevalidatebeforelatercombination.

Workerclosesauthenticatedsourcearchives then removesonlyownedderived.zip/native.zip/measurement.zip downloadcopies afterallreads; sourcearchiveID/hashreceiptsretained, originalcloudartifactsuntouched. ASTpassed andgeneratedECOsourceinspected; nativepending. This preventsrecursivearchivegrowth. Current346delaystaging43735491108 andactual650PHY43727364585 bothverifiedIN_PROGRESS. Fullgoalactive; currentturnprogress.

## Combined link-up sizing verified holdzero; staging combination and compact bit5 evidence running

Compact43735267852/d5c15f6 SUCCESS: authenticatedproducer43734156396/c355ce32, fullarchive14170027132/e2bec5be2990748b61abef5f730157e365436899bf3ec7cb3c1cbd80f4649e8e and9consumedstate/max/minmembers in cloud. Compact14170282396 ZIP SHAdc0e4c00d8a528aae9887769bb37a7989375ccef5fa01a0a47fd4dfc500f0506 (26310B) verifiedRAM. ActualcombinedcandidateODB9a62ad626e30fb613f673cb2c018a591efd999956b7f04da98ef7ffa919f5694,state run/4-nssoc-sizedfast/state_out.json. Setup2171/0/0 WS-1.82121/+.0185629/+.965397ns;hold0/0/0 WS+.222705/+.143165/+.00518863ns;slew36/6/3cap0. Globalsetupcount improves2232->2171withoutnegativeholds. SlowmaxmemberSHA1f2da23bb83e924d74b58396b4cf64e7381328aff034058bfef3b93d93a2b0d0 showsactualworststaging[2][6],fanout8282buf1 .893393ns. Notfinalrouting/PHYacceptance.

Dispatched43735491108/head7b1b49fd31f792e97f259b2aaf03a1b08ccf24bb,codex/new-rx-margin-staging; verifiedIN_PROGRESS. Worker scripts/size_rx_margin_staging_buffer.py binds successful43734156396/c355,exactnative14169464149/809a043a0526406a48311f334b9c1090b4f00ef21405e0e5d81d6f1da45b7243 andderived14170027132/e2bec5b, source9a62/source_run43733131689. Firstcriticalpath/masterguard thenfanout8282buf1->8. Existing346delays,bypass,linkupupsizes retained;allcornerfreshSTArequired. ASTpassed.

Thisworker nowclosesverifiedsafe/native ZipFiles afterallsource extractionandcriticalreportreads, unlinksONLYownedOUT/derived.zip andOUT/native.zip copies, recordsIDs/hashes andremovednames inresult; originalGitHubartifacts untouched. Removes recursivearchivegrowth fromfutureoutputmanifest. Fullarchive/memberverification retained. Nozipreadsafterclose (state/config readfromextractedsource). Native executionwillverifycleanup compatibility; notyetclaimedruntimePASS. Allother source/placement/incidence protections unchanged.

Bit5compact43735445777/head340052fbd61f9a7499bd93a3380d7251c58f1a28,codex/new-rx-headlast5-compact IN_PROGRESS. Worker scripts/summarize_headlast5_timing.py binds43734364727/e7b5,derived14170515411/1306de38b43f8669b7473ee8d10821e2fb7497b2b33d9c875e000d73d330a4f4; verifies3state+18branch+3nativeconnectivity members andexportsrawsmallreports, notjustaggregate. Nextreadactualbit5counterpartandminmarginsbeforebypass. PHY43727364585 verifiedstilllive. Fullgoalactive; currentturnconcretecombinedrepairprogress.

## Combined link-up and bit5 measurement completed; compact evidence extraction pending

43734156396/c355ce32 SUCCESS. Derived14170027132 metadataSHAe2bec5be2990748b61abef5f730157e365436899bf3ec7cb3c1cbd80f4649e8e,17965364B; native14169464149 metadataSHA809a043a0526406a48311f334b9c1090b4f00ef21405e0e5d81d6f1da45b7243,3308507903B. RAMderiveddownload timedout120s, no numericalresultverifiedyet. Do not infer goodtimingfromjobsuccess. Dispatchedcompactcloudsummary43735267852/headd5c15f6b5a335d0396c795425301c4d6b9abc2f8 oncodex/new-rx-margin-linkup-compact; verifiedIN_PROGRESS. scripts/summarize_margin_linkup_timing.py reuses testedsummarylogic, binds exactproducer/head/archiveSHA, verifiesall9 state/max/min memberhashes, exportsunqualifiedcornermetrics+first5paths/report. No nativeCADrestart. Readandhashcompactartifactwhencomplete.

Bit5read-only43734364727/e7b5fc83 SUCCESS alsojustcompleted. Derived14170515411 metadataSHA1306de38b43f8669b7473ee8d10821e2fb7497b2b33d9c875e000d73d330a4f4,17971262B; native14169537694 metadataSHA42cae187ed4642f3cb735b6c199605c3be4353a04f75016606465f7d2102e7f6,3235350234B. Contentsnotyetinspected; nextauthenticatebit5 min/max andactualotherloadbeforeanybypass. Source20b515 (214delaylineage), needsrevalidationonlatest346delayifcombining.

Identifiedarchivegrowthmechanism in sizingworker: downloadsOUT/derived.zip andOUT/native.zip retained throughfinally outputsmanifest, thenuploadedagaininsidecurrentnativearchive. Originalproducer artifacts remainGitHub; futureworker can closeverifiedZipFiles andremoveONLYtheseownedtemporarydownloadcopies afterallsourceextraction/reportreads, beforeoutputsmanifest. RecordtheirIDs/hashes inresult. ThiscleanupNOTIMPLEMENTEDYET; preservefullreport/source/memberverification andneverdeleteoriginalcloudartifacts. Canreducefuturemultigigabyte recursivearchivegrowth. Currentnative3.3GB, increasestransfer/storagepressure.

PHY43727364585 verifiedstillIN_PROGRESS. Prior turnverifiedwait, thisturnprogress bycompletedworkers andcompactevidencejob. Fullgoalactive.

## Next head-last bit5 critical shared delay measurement dispatched

Dispatched43734364727/heade7b5fc83d56799bb537e14a809c0df7eff83ffa1 on codex/new-rx-headlast5-measure, verifiedIN_PROGRESS. Worker scripts/measure_rx_headlast5_hold.py binds exactsuccessful43732602282/5df33083, fullnative14169149260/1265244633edb539233ba7ff37b05747d0f089ca390244f861aff01d7905512b andderived14168919765/3d20a73ee8ff0155d1c7becc56ad6d47a09e0abe77cf1c876476b9fcaa399fb1, candidate20b515. Guardfirstcriticalhead_last[5] path includeshold32105/X andABC734931738686/B. Exactly3targets hold32105/A,X,XOR738686/B. BranchSTAconnectivity nowexplicitlyreads hold32105, notoldbit4hold33182; nativeholdmasterguard andallcornerthroughmin/maxreports, unchangedODBassert. Read-onlymeasurement, no bypass or changedcell. ASTpassed. Exactloadcensus andshortmargins mustbeinspectedbeforerepair; cannotreusebit4counterpart805438 orFF175604.

Combined346delay+linkup43734156396/c355ce32 stillnativeexecuting. Actual650PHY43727364585 stillnativeexecuting at16:14UTC; around74minutes sincejobstart, notterminated/restarted. Canonical43727638507 formalsweeps/mainchecks alsostilllive; oldRTLfailedanchor alreadyfixedintegratione348e901 withseparateactualvalidatorPASS. Fullgoalactive; latestturnconcretemeasurementtrial, previousprogress. FullserialPHY/routing/finaltiming andproductionacceptance remainopen.

## Actual346-delay bypass retains hold0; link-up combination running; staging evidence authenticated in cloud

43733131689/8dda53af23853b6a7c690ddb7c626335ac057415 SUCCESS. Derived14169446886 fullZIP SHA6fcda2f25738fca4f4171a034cd309e25759c83bf3ad8a0bc85a2350bec3fe1c (17942605B) andallcornerstatehashesverified inRAM. Native14169129926 SHA42a5585b651ec6952696e81329b3ed2e97384ace3d07837bf5e10cfacea5361f (2913769900B) stayscloud. ActualcombinedODBac6995b02a658fa478c370a14bd1aabbf9c374447304b91717e77e7f22b46066, state run/4-nssoc-sharedfast/state_out.json. Setup2232/0/0 WS-1.83518/+.0185629/+.965397ns;hold0/0/0 WS+.222705/+.143165/+.00518852ns;slew36/6/3cap0. Thus measuredsharedbypass retainscurrentholdmargin, notfinalrouteclosure.

Dispatched43734156396/headc355ce32bcaf9c730dbd81bbeed99a9b4155d4a7,codex/new-rx-margin-linkup, verifiedIN_PROGRESS. Worker scripts/size_rx_margin_linkup_buffers.py restores exactac6995/source43729972900/measurement43732030174 archives andvalidatesactualfirstlinkupcriticalpath/threeoriginalmasters. Appliesfanout9351buf4->8,9344/2394buf1->4 on346delayholdzero source;allcornerglobalSTArequired. ASTpassed; outcome pending. Experimentalworkflow notmerged.

Stagingtrial43732602282/5df33083 SUCCESS. Native14169149260 SHA1265244633edb539233ba7ff37b05747d0f089ca390244f861aff01d7905512b (2867773282B). Derived14168919765 SHA3d20a73ee8ff0155d1c7becc56ad6d47a09e0abe77cf1c876476b9fcaa399fb1 (17972445B) twiceRAMdownloadtimedout120s; no nativejob restarted. Instead cloudsummary43734014244/3ee8cb19a47fa30c5fcca67cc02c1c8040c6640c SUCCESS authenticatesexactproducer/archive andall9 consumedstate/min/maxmembers. Compact14169980675 ZIP SHAe9b61587f80d595b669a57b89390919d8892ebab2a77d23ce3da76bbbc72f9dc (29151B) independentlyverified inRAM. Containsfirst5max/minpathspercorner andunqualifiedglobalmetrics, fulloriginalmemberhashes. This is verifiedcloudextraction, not directfullartifactRAMverification.

StagingODB20b515f13489500f122ad2d5a23255aa9e902af2f413e8cc4d6284a53ea6a4dd: setup2171/0/0 WS-1.81411/+.0185629/+.965397;hold0/0/7 WS+.222705/+.0846121/-.0299224;slew36/6/3cap0. Separate214delaylineage. SlowmaxSHA8c724d12286d0e7985d93697d55a44c241fb2c9ba57eb98d3a85e53dc809cf93. Newworst FF175605 head_last[5]->FF176720: hold32105(.679773ns) ->XORABC734931738686/B->equalitylogic->rx_eopbufferchain3452buf2(.325922),3451buf4(.420541),3450buf2(.370699),3449buf2(.369285),2700buf1(.255907),2021buf1(.307361). Nextinvestigation canmeasurehold32105 actualtopology/shortbranchmargins beforeanybypass; do notreusebit4branchcensus. Needlatercombinequalifiedstagingresize onlatestholdzero candidate, notmixmetrics.

PHY43727364585 verifiedstillIN_PROGRESS. Currentturn progress: authenticatedcombinedholdzero, dispatchedlinkupsizing, resolvedartifactobservationstallwithcompactcloudsummary. Fullgoalactive.

## Current346-delay shared branch measured; actual combined setup/hold trial running

Read-only43732030174/b70c4888f5c912b072f7b594a11339c5de8f4c78 SUCCESS. Derived14169073173 ZIP SHA2db2f422baccc23754034e68c2cb2138b1128ee6d69650819f13c2b4710044f6 (17940212B) authenticated in RAM; all3state,18branch min/max and3nativeconnectivity memberhashes verified. CandidateODB unchangedc887b622caf91307037b00e780ec73b52bfc4b8ab9700ba9c919625959876e09. Native14169048627 SHA570508ed85470ba13617bbc0408fb02710fed01224b9c62ef7983723c9ccca9e (2869586767B) stayscloud.

Sharedhold33182 input/output minslow/typ/fast+.818965912/+.418567866/+.196297929ns; criticalXOR738684/B min+1.529207230/+.864189625/+.483826339ns. XORsetup-1.844499707/+.283951968/+1.492695570ns. Nativecensus stillFF175604/Q->head_last[4]->hold33182/A; outputnet33182 exactly805438/A and738684/B. This revalidates topology/margins on actual346delay source, not old214delay source.

Dispatched43733131689/head8dda53af23853b6a7c690ddb7c626335ac057415, codex/new-rx-margin-shared-bypass; verifiedIN_PROGRESS onlyaftermeasurementproducerSUCCESS. Worker scripts/trial_rx_margin_shared_bypass.py restores exactc887 physicalproducer43729972900/a8333ff(native14168212861/f825619,derived14168124662/cb76b7) and independentlyauthenticates newmeasurement43732030174/14169073173. Requires125newdelays onsource43728240498 and originalmeasuredworstpath; unchangedminimumqualification1.5/.8/.48ns. Reuses provenonepinECO: ONLYcriticalXOR bypasseshold33182,otherloadkeepsdelay; allmasters,pins,nets,ports,coordinates,orientation,status invariant,temporaryFIRM topreventmirroring. All346delays retained. Freshglobal3corner+branchSTA; anynewholdviolation rejectsacceptance. No finaltiming/fullPHY acceptance asserted. ASTpassed; outcome pending.

Stagingbuffertrial43732602282 and actual650PHY43727364585 stillliveatlastpoll; no restart. Prior turnverifiedwait; currentturn concretecombinedtrial fromfreshmeasurements. Fullgoalactive.

## Link-up sizing reduces setup count; staging buffer trial dispatched

43731420109/3668f06febc8b96cc69d600061916f70b991f08b SUCCESS. Derived14168957702 ZIP SHA70de0599a4928d614f38d52172f690d9044458e32ab23771460a44ccffd8ba48 (17954453B) authenticated in RAM, all3cornerstates+slowmax/fastmin memberhashes verified. Native14169002716 SHAa06f4957dd597c88d259c5b50d05557ce3b7ced223fa3cdc2d3a81b06d7c7bae (2473256781B) stayscloud. CandidateODB2bbca33cd4b0711000abd1fa79f8fdd63a2d514ba232901115057a3d4f5d8174, state run/4-nssoc-sizedfast/state_out.json. From0ec7: setup2233->2172slow,typ/fast0;WS-1.82121/+.0185629/+.965397ns. Hold0/0/7 WS+.222705/+.0846121/-.0299224ns unchanged; slew36/6/3,cap0. This is214delay lineage, NOT346delay holdzero candidate; no mixedmetrics.

New slowworst FF174864 staging[2][6]->commit_copies[3].write_copy[2].copy FF551964: inverterABC734931760715inv1 delay.483504ns/slew.554038ns; fanout8282buf1 delay.893393ns/slew.899302ns/load.142386pF; lastAND760785and2_1 delay.817843ns/slew.986777ns,endpointsetup.502300ns. Next controlled trial targets one exactnative buffer8282 buf1->8; drivinginverterload andhold mayworsen, so freshallcornerSTArequired. No speculativeassumption accepted.

Dispatched43732602282/head5df33083a6fda309563213ab9438026116f5660c on codex/new-rx-staging-buffer-trial; verifiedIN_PROGRESS. scripts/size_rx_staging_buffer.py binds exact2bbca archives/head/producer and authenticates firstcritical stagingpath/master; sourceproducer43730133822. Reuses guardedinstance/master/incidence/port sizing with legalization, unchangedclocks/derating; freshallcornerglobal+branchSTA. ASTpassed, nativepending. Experimentalworkflow notmerged.

Currentholdmargin sharedmeasurement43732030174 and actual650PHY43727364585 verifiedstillIN_PROGRESS. Prior twoturns verifiedwaits; thisturn newresultanalysis and concretetrial. Fullgoalactive; fullserialPHY/mainchip routing/finaltiming/production remainopen.

## Current PCIe mutation anchors validated and integrated

43731932691/head765cd2ef3310ba09bfc5192ff2e6ef1811e28e5c SUCCESS. Artifact14169006896 ZIP SHAc43efa3878de95bb64b9a059b1a817ab6bedd39a9506c49a74c7e981ef4ec6cc (252176B) authenticated in RAM, each16 XML/log memberhash and actualJUnit counts checked. Regs andstream eachthreebaseline6pass=36positivecases; all10mutants produce functional assertion failures with0skips. Regsmutants counts5/1,5/1,5/1,5/1,0/6;stream5/1,5/1,5/1,4/2,4/2 (pass/fail). Mutant failures expected, not productfailures. Actualtestgates unchanged.

Integrated only scripts/check_pcie_tlp_controls.py two stale mutationanchor fixes after verifying all6 RTL/test/makefiles and parser identical betweentestedhead andintegrationparent. No productRTL or experimentalworkflow merged. Canonical43727638507 remains historically failed atoldmutantanchor, not retroactively green; its otherformalsweeps/checks live. Wholecanonical rerun may follow terminal result ifneeded, avoid cancellingliveproofs. Scopedvalidator proves repaired controls, not fullPHY/layout acceptance.

Live physical jobs precedingpoll:43731420109 linkupbuffers nativeexecution;43732030174 currentholdmargin sharedbranch read-onlymeasurement runtimepreparation;43727364585 full256bitactual650PHY nativeexecution. Fullgoal remainsactive; latestturnconcretevalidatedfix integration. Continue native workers and combine only sourcebound measurements.

## Hold-margin result improves minimum slack; current RTL mutant anchors repaired in cloud trial

43729972900/a8333ff19420d8bb90a59bc370ebe04119373f0c SUCCESS. Derived14168124662 ZIP SHAcb76b7d2da9b89c4a3c4ea3b0eea2137f740998a6af88ae354ce30eff1d1cb3f (24424597B) authenticated in RAM, all3cornerstate hashes verified. First observer download timed out120s; retried artifact only, never nativejob. Native14168212861 SHAf82561949e8cc731bee14e2963bb141f7787b55198b952a8a3c235cb74f98bf7 (2497180075B) stayscloud. CandidateODB c887b622caf91307037b00e780ec73b52bfc4b8ab9700ba9c919625959876e09; state run/4-nssoc-holdfast/state_out.json. Added125delays to221existing=346total.130reportedsub50pspaths,125selected,5unsafe/unmeasured paths explicitunselected. Global setup2232/0/0 WS-1.8445/+.0185629/+.965397ns;hold0/0/0 WS+.222705/+.143165/+.00518852ns;slew36/6/3cap0. Fast minimum improved.415ps->5.18852ps, still not50ps reserve or routedclosure. Unselected source paths endpoints176732,181450,181451,328847,176723; do not waive.

Dispatched read-only43732030174/b70c4888f5c912b072f7b594a11339c5de8f4c78, codex/new-rx-margin-shared-measure, verifiedIN_PROGRESS. scripts/measure_rx_margin_shared_hold.py binds exactc887 archives,125insertions/source43728240498, originalcritical head_last/hold33182/XOR path, clocks/derating and unchangedODB. Measures sharedholdA/X andcriticalXOR738684/B allcorners with nativeconnectivity before combining successful bypass on current346delay candidate. No source mutation or final acceptance. Linkupbuffer43731420109 and PHY43727364585 remainlive.

Canonical43727638507 RTL job132852962019 FAILED after1263passed/0failed/17skipped cocotb summary, at extraPCIemutantguard. Authenticatedartifact14169190557 SHAf8b13b84011a05a3980b6300f0bc36acf84eab08c7cbbcc4e28d55dc54d5e673 (6896499B): three realregs baselines each6pass/no skips, then error Mutation location drifted:zero_length_count. Registered descriptor decode changed mutation anchors; byte_strobes anchor also stale. No productRTL failure inferred from this specific guard error; fullCI remainsFAIL.

Fix765cd2ef3310ba09bfc5192ff2e6ef1811e28e5c on codex/current-pcie-mutation-anchors changes two oldmutationanchors to currentd_tag/d_low_addr andd_has_data/d_first_be while preserving injected wrongcount4 andwrongstrobes0xf. PythonAST and all10exact-one mutationlocations checked againstcurrentRTL. Native validator43731932691 IN_PROGRESS uses actualthreebaselines+fivemutants forbothregs/stream, unchanged sixcases/no skip andfunctionalAssertionError gates. Do not integrateuntil actualPASS. Experimentworkflow mustnotmerge. Allnativeworkcloud; no localpersistentfiles. Fullgoalactive, thisturnprogress.

## Canonical formal-and-boot actual outputs verified; physical workers remain live

Canonical43727638507 at7e046d88dcede61b92f2a96601fa40004ce24bb7: formal-and-boot job132852962069 SUCCESS. Artifact14169060521 fullZIP SHAcc6904852ee16ee220f120ff0e45fc74aa49090ead8abbc819e1bc643b1834d2,678927B independently verified in RAM. Inspected23 positive formal status files PASS (register file contract/equivalence, APB bridge, busstat,NPU), three intentional registerfile mutants FAIL, crashcocotb actual1pass/no skips. Boot none/entry0/length0 logs each actual28checks,zero failmask,RESULT PASS and TBPASS; invalid entry/length reject first image and boot fallback. Geometry real21properties0failed, odd-entry/cross-slot mutants rejected. Ethernet CPU GMII packet loopback+IRQ mask0 RESULT PASS/TBPASS. ExternalIRQ positive mask0,negative mask0x100, bothfourassertions/twosleepwakes. These are scoped RTL/formal evidence, not mapped-gate boot, fullserial PHY, CDC/physical or production approval. Intentional mutant JUnit skipped assertions are not positive tests; no aggregate false pass claimed. Other canonical RTL/checks/formalsweeps still live at preceding poll; nativeboot explicitly skipped.

Revalidated43731420109 (three linkupbuffer trial),43729972900 (holdmargin),43727364585 (reducedinputPHY): allIN_PROGRESS. No restart. Previous turn concrete new trial+checkpoint; this turn authenticated new functional evidence plus verified waits. Continue exact-worker polling and inspect all-corner/native electrical results when terminal.

Upstream SRAM dependency rechecked read-only: IHP-Open-PDK main e73adb4045731ddec21634146d536380057f6a26 vs c6562037497437ce6bc689e633e5b45abf9bbccb has identical git blob SHAs for all eight256x32/512x32 single/dualport GDS/CDL files. PR https://github.com/IHP-GmbH/IHP-Open-PDK/pull/1121 remains OPEN/unmerged, updated2026-11-02. No new raw SRAM geometry/reference fix in those published files; do not infer a full upstream LVS solution or relax resistance geometry matching. Fullscope remains active, not blocked while physical jobs run.

## Shared-delay bypass verified; new link-up critical path trial running

43730133822/3128bb965af5b1e7bf0b952a5f8ff34ed229304d SUCCESS. Derived14167899580 ZIP SHA618ec07ad0d95da348ec31b9177449c2aabe4b1529e069f24a3ea790e0f8fa0d authenticated in RAM, all three corner state/max/branch2 min/max member hashes verified. Native14168810819 SHAcfadd1b622c10d4fa1205ac3c08dd0bdc477cfbbbbf0a3779e5a21476e71c0d6 remains cloud (2078934562 bytes). CandidateODB0ec7b38eb8bf9f2ff7d4f81e486c5dd6fd430ae66b66cb19aee27494bb2955fd.

Global setup slow/typ/fast2233/0/0, WS-1.83518/+.0185629/+.965397ns; hold0/0/7, WS+.222705/+.0846121/-.0299224ns; slew36/6/3, cap0. Seven hold violations are original source7c850 baseline, not a regression from separate holdzero candidate. Exact XOR branch setup improves from-1.844506860 to-1.191524267ns; its hold margins remain+.963624775/+.501893103/+.239953503ns. Source placement/orientation protection completed successfully. Not final timing acceptance.

New worst path is link_up FF365865 through fanout9351(buf4, .466012ns),9344(buf1,.454507ns), r2_handshake distribution and2394(buf1,.286274ns). Dispatched43731420109/head3668f06febc8b96cc69d600061916f70b991f08b on codex/new-rx-linkup-buffer-trial, verifiedIN_PROGRESS. Worker scripts/size_rx_linkup_buffers.py restores exact successful0ec7 with full archive/member/source guards, validates first worst path and three original masters, sizes9351 buf4->8 and9344/2394 buf1->4. Original sizing flow retains incidence and instance guards with placement legalization; fresh allcorner global+three branchSTA judges effects. ASTpassed, native pending. No clock/derating or gate relaxation. Uses214delay lineage; do not mix its metrics with221delay/margin branch. Experimental workflow not merged.

Owner auth verified Melihakbulut221 with push/admin true. Existing margin43729972900 and PHY43727364585 remainIN_PROGRESS; canonical43727638507 was live at preceding poll. No local persistent source/artifacts. Fullgoal active: final routing/extractedRC/setuphold, fullserialPHY/mainchip integration and production acceptance remain open. Next authenticate margin/PHY outcomes, combine only after exact-source revalidation; do not restart live jobs.

## Shared-delay trial rejected unintended cell mirroring; fixed without weakening guard

43729430502/da246d6 FAILED before STA, not a measured timing rejection. Derived14168002386 fullZIP SHA24c20b43fdc4c5f82e61fa5e8e02048a1a63e2de63fcd8979f37e25b5f41455f verified in RAM. Native log confirmed exact one-pin bypass guard completed, then inherited detailed_placement mirrored78245 instances despite0translation displacement; final orientation guard correctly raised Unexpected placement change. No candidate adopted. Failednative14168155850 SHA3cf11bbd3a56c61a48498e2882ce4927e492beb8db998303c3ac135ec66841f7 remainscloud.

Fix3128bb965af5b1e7bf0b952a5f8ff34ed229304d: use already-proven hold repair policy to temporarily mark originalPLACED instancesFIRM, preventing optimizer mirroring; finalguard still requires identical coordinates/orientation, then restores and verifies originalplacementstatus beforewrite_views. Master/pin/net/portcensus, exactmeasuredsource and original clocks/derating remainunchanged. PythonASTchecked. Retried native **43730133822** on codex/new-rx-shared-hold-bypass; verifiedIN_PROGRESS. This supersedes failedrun43729430502, not a restart of a livejob. No timingoutcome yet.

Low-margin repair43729972900/a8333ff and reduced-inputPHY43727364585/ed63d85 alsoverifiedIN_PROGRESS. Canonical43727638507 formal-and-boot progressed to doublefault/APBcocotb; no fullCI/physicalcompletionclaimed. Fullgoalactive; thisturnprogress from diagnosed terminalfailure and concretefix.

## Combined221-delay setup candidate retains hold0; measured low-margin improvement dispatched

Combined43728240498/headb2ddf379726944957839e4e3755cc72e199df230 SUCCESS. Derived14167074480 fullZIP SHAfa6cb6d69d33622f36ac4a2bbbb3e7293629ae7c72f40b5abfd84c6f4aaf0b0c and all3state/minreport memberSHAs verified. CandidateODB **e975526a22a251cb830e24112eec64de5748754fc83000e441f7d2290f3ba9d4**. Native14167987249 SHAb484dcac548516118ba1fe04e485174d3057616dfb244b381da0f41c6472c99e,2090044530B cloud.221existingholdcells and10totalbufferupsizes retained. Setup slow/typ/fast2233/0/0,WS-1.8445/+.0185629/+.965397ns. Hold0/0/0,WS+.222705/+.0917479/+.000415001ns. Slew36/6/3,cap0. This is actual combined candidate, not mixed child metrics.

Fast report contains many sub50ps paths: firstFF326830->FF165873 .415ps; FF166553 self.444ps; commitreadcopy2->FF176722 .943ps; other self-feedback and PCIe inputboundary paths. Zero violations alone is fragile. Native lowmargin trial **43729972900 /a8333ff19420d8bb90a59bc370ebe04119373f0c**, codex/new-rx-hold-margin, dispatched after producerSUCCESS. Worker scripts/repair_rx_hold_margin.py binds exactnewE975 archives; reads all564current allcornerthroughreports; parsesTHIScandidate's min.rpt, selects only0<=slack<50ps, asserts everypathgroupreport reaches>=50ps (no hidden truncatedtail). Uses only actuallymeasuredinputs, at least1ns setup reserve per newdelay, exactnativepin/master/incidence/fixedplacement guards and unique nssoc_rx_margin_hold_ prefix. Records unavailable/unsafe paths explicitly; doesnot silently waive. Existing221delays preserved.50ps is experimental reserve target, NOT relaxed acceptancegate; clocks/derating unchanged. PythonAST and regexpositivecontrols verified; native outcome pending. Multipleinsertions may interact, so freshglobal3cornerSTA decides.

Sharedcriticalbranch bypass43729430502 and reduced-inputPHY43727364585 remainlive. CanonicalCI43727638507 CPU GigabitEthernetpacket/interrupt, externalIRQ/WFI, UARTreceive/corruptbyte stepsSUCCESS; wholeSoCstall/crashregression running atlastpoll. These are jobstep outcomes, not yetcompletefullCI or physicalacceptance. Fullgoalactive.

## Shared hold topology measured; one critical branch bypass trial dispatched

Read-only43728682416/eef0e9 completedSUCCESS. Derived14167916383 fullZIP SHA95064582717f0411bfffb7d0b5af8e348151d13229c6d148300a2eb587acb243 and all consumed connectivity/branch memberSHAs independently verified. ODBunchanged7c850. Native14167896528 SHA02aa3e9921773457522aea228212d041742af035ea8963f9d9d0bd1606865552 stayscloud.

Actual topology: sourceFF175604/Q ->head_last[4]->hold33182/A; hold33182/X net33182 feeds exactly ABC734931 805438/A and738684/B (XOR). Noexternalports. Shared minimumhold slow/typ/fast .818965912/.418567866/.196297929ns; XORbranch minhold1.529207230/.864189625/.483826339ns. XORbranch setup-1.844506860/+.283945322/+1.492688656ns. Fast criticalbranch minpath reachesFF160523, existinghold33182 rise delay.261416018ns. Removing this delay from XOR branch MAY leave margin but arithmetic is not proof: changedloading/C2Q/otherbranchdelay must be remeasured. Keep delay on805438/A.

New native trial **43729430502 /da246d69694c00290813080bc88b8fbd795bbcbd**, branchcodex/new-rx-shared-hold-bypass, dispatched only after successfulread-only producer. scripts/trial_rx_shared_hold_branch.py authenticates exactmeasurement14167916383/9506458 and minholdbounds1.5/.8/.48ns; restores originalqualified7c850 native/derived43726840782. New ack_chip_shared_hold_flow.py resolves two STA pins to native DB pins, checks noninverting delaymaster, XORmaster, exact2loads,originalsourceFF,net/portcensus; reconnects ONLY738684/B tohold33182 inputnet.805438/A remains ondelayoutput. Everyotherpin/master/net/port and originalplacement must remainidentical. No cell deletion, no clockrelaxation, no generalresizer. Freshglobal+through3cornerSTA. PythonAST passed and generated Tcl source inspected. Outcome pending.

This trial source has214delays and7unrelatedfastviolations, not latest221delay candidate. Successful ECO must later be combined on verified latestsource and allcornerSTA repeated. Do not claim current hold0 measurement applies to this separate trial. Combined221+fivebuffer43728240498 and PHY43727364585 remainlive. Fullgoalactive.

## Shared head-last hold delay targeted for measurement before any removal

Read authenticated derived14167680049 again (fullSHA506044747cf8aba10888ab14ff07402a354c6ce3253b23fabebb98e0f4829b9b), verified maxreportSHA41c9edcd4d8a9150f5948e4e9ed11be67c035e797640ceb75279851cafb76967 on candidate7c850. Worst slow path FF175604(head_last[4])->FF176720 contains **hold33182 delay0.692288ns**, then XOR738684/B, equality/control logic, rx_eop fanout3452(buf2)/3451(buf4)/3450(buf2)/3449(buf2), later2700/2021(buf1). Slack-1.844507ns. Holdcell output has fanout2; cannot remove it without checking both short paths. Second path link_upFF365865->read_bank[3].r2_slot[2].lane_copy includes fanout9351buf4/9344buf1 and r2_handshake3180/3179/3178/3177buf4, plus2394buf1. No stale ABC735174 identifiers.

Dispatched **43728682416 /eef0e9f4331428d63d7eb81084b4cea4b6777556**, branchcodex/new-rx-headlast-hold-measure. Worker scripts/measure_rx_shared_hold.py restores qualified combined214delay candidate7c850 from43726840782/a164, derived14167680049/5060447 and native14167575764/f488cebdfee2a13d71bd9c27d5725864500ed7df565735d0c270ea66d4edc9d4. Fullarchive/member guards. Exactly3 targets:hold33182/A,hold33182/X,andABC734931 XOR738684/B. Freshallcornerthrough-min/max reports, actualnative net/load census for A/X, assert ODBunchanged. The connectivity report's final master field is a native object handle, not master name; instance/pin/I/O/netnames remain explicit. ASTpassed; native pending. This is read-only investigation of whether shared delay can be moved to only the short branch, NOT permission to bypass blindly. Source is7c850 (214delays), NOT latest221delay combined candidate; any ECO on newer source needs revalidation.

Licensing followup e6591833c420dffbd5c22a76bc71e1ffe92dfedc adds refreshed NOTICES path to existing prepared-source component-license override in REUSE.toml, preserving upstream licensing instead of generic docs annotation. TOML parsed and exactone expectedrule verified. CanonicalCI43727638507 runs earlier7e046d8, so does not cover this path-only annotation change; no executable source change. Current221delay+fivebuffer43728240498 and reduced-inputPHY43727364585 verified live. Fullgoal active; prior turn progress, current turn progress plus verified waits.

## New RX candidate achieves postCTS hold0/0/0; final routed closure NOT established

Native43727102369/headce2c27eed959fbcd9ff893cc0f945d94edd24185 completedSUCCESS. Derived14166884065 fullZIP SHAa46aa0f60322cdb1aa0884afe2bd432a6bd8aa3cad4a0d2f1614671d428b7301 and each3corner stateSHA independently verified. CandidateODB **fd91b14417dae22edf59097e7d36dc284882e303e02f3e145ea2a37bc2909634**, source441ff;7new delays/7selected targets,214existing preserved (221total added). Native14167435762 SHA9cbf9ede3c62d4411859b48885ab9dc7a000e66b4bbf8278ae371fd0e0f831cb,1683637984B remainscloud. Sourceunchangedtrue,return0.

Slow/typ/fast hold counts **0/0/0**, WS **+.222705/+.0917479/+.000415001ns**. The worst fast margin is ONLY0.415001ps, not robust final-route acceptance. Setup unchanged **2276/0/0**, WS **-1.86168/+.0185629/+.965397ns**. Slew36/6/3,cap0. All original clocks20/4/8/8ns,derating5percent preserved. This is newRX physical candidate, unlike old mapped735174 histories. Final routing/extractedRC/fullPHY still open.

Independent214delay+fivebuffer combined43726840782/heada164dab measured: candidate7c850577a9c39f4e72383169ce0faa63c07422786ffbc6e5b8570d041b04d95f. Derived14167680049 fullZIP SHA506044747cf8aba10888ab14ff07402a354c6ce3253b23fabebb98e0f4829b9b and percornerstateSHAs verified. Setup2233/0/0,WS-1.84451/+.0185629/+.965397ns;hold0/0/7,WS+.222705/+.0846121/-.0299224ns;slew36/6/3cap0. Thus fivebuffer sizing helps43setup violations without fixing7holds; do not mix its metrics with fd91.

Dispatched actual combined221delay+fivebuffer trial **43728240498 /b2ddf379726944957839e4e3755cc72e199df230**, branchcodex/new-rx-holdzero-quarantine. Worker scripts/size_rx_holdzero_quarantine.py restores exact successfulfd91 producer/native/derived with fullhashes; requires physicalsource43720921041,measurement43725515099,7selected/no unresolved;564targets. Applies measured quarantine fanout9519/9492/9485/2680/2194 buf1->4 with firstcriticalpath andnativeincidence guards, thenfresh3cornerSTA. All221hold cells preserved. New state may worsen tinyhold margin after legalization; outcome pending, not assumedzero. ASTpassed.

CanonicalCI43727638507 now pythonqualitySUCCESS,memoryparitySUCCESS; mainchecks,RTL,formalpilot/soc,formal-and-boot stilllive. Formal-and-boot advanced beyond preparedguards to real-codec contracts, so original dependencyblock cleared in canonicaljob. Nativebootexplicitlyskipped byrequestinputfalse, not a bootpass. PHY43727364585 stilllive in full256bit native step. Fullobjectiveactive.

## Canonical integration CI running on refreshed prepared sources

Integration commit7e046d88dcede61b92f2a96601fa40004ce24bb7 includes authenticated metadata/notice, fixture and no-skip Ibex boundary test, plus scoped evidence receipt. Explicit canonical checks run43727638507 is IN_PROGRESS with full_interfaces=true and native_boot=false. This is the actual integration run, not the experimental validator. Long native mapped boot remains a separate unresolved issue; no claim of boot/timing/fullPHY acceptance.

Physical repair43727102369/job132851331678, combined sizing43726840782/job132850520498 and reduced-input PHY43727364585/job132852147581 all verified IN_PROGRESS in their native execution steps. No restart or cancellation. Wait for exact outcomes; then authenticate output hashes and compare all-corner setup/hold/electrical metrics before combining or selecting layout. Full objective active.

## Current prepared source replay and no-skip compatibility checks integrated

Authenticated43726998790/headfec7a01 passed6base+6full tests and stalehashnegative refusal, no skips. Artifact14166482651 fullZIP SHAb2a65a3e73087e2f81dceb5c48892b19689590bd01dc106adaf82b489341434c and every memberSHA verified; actualJUnit6+6success/negativeerror inspected. Integrated new metadata+notice, fixture pointer, Ibex entry test using prepared_sources instead of skipped missing ROOT/gen file, and receipt. Compared integration source transforms to all metadatahashes and exact expected test/fixture diff. Only unused pytest import removed relative to testedhead (already cleaned on f27f41c). No experimental workflow or physics change included. Canonical checks dispatch with full interfaces follows this commit; not yet fullCI acceptance. Native timing43727102369,43726840782 and PHY43727364585 remain separate live workers. Full goal active.

## Reduced-input clock driver candidate dispatched against unchanged full actual650 load

Progress this turn: derived a circuit trial from actual measured device currents, committed source and exact source manifest, and dispatched native transient43727364585/headed63d8541533f9823beb2321eddba32c00625843 on codex/current650-reduced-input-clock. Last observed IN_PROGRESS. Source is9709f80 loaded-circuit branch plus exactly12 input/cascode Nx4->2 changes, preserving30HBT instances,7ideal resistors, tail/reference/output circuitry, clock/data polarity and real physical650 load. Total buffer emitters117->93; source parser checks exact Nx by role and exact total. Branch gate and all changed source hashes updated; no old evidence rewritten. Full helper prefix before run_loaded (stimulus, original measure_wave, reader, electrical gates) byte-identical to9709f80; AST parsed.

Justification verified from actual failed43717632809 derived14165465911 fullSHA192c9bc0f4a75abf5defb1d548ee1784e869023303764fc8dd1072be3ec6eae6: input pair max model Ic/emitter~0.634mA, cascode~0.610mA, output follower~2.970mA near unchanged3mA gate. Thus shrink only input/cascode devices to test reduced capacitance/delay, not output devices. Doubling current-density estimate is NOT native acceptance; all voltages/currents and functional gates must be remeasured. Observed23-26ps clockbase delay may contribute to failures, not proven sole cause. Original256bits,18.75ps late offset,8GHz,10ohm sources,150fF/50fF loads,37.5ps sampler deadline,100mV/30mV gates remain unchanged. No clock-edge compensation or tolerance relaxation. Docs/cdr-reduced-input-clock-trial.md explains hypothesis and limitations. New driver remains pre-layout with ideal sizing resistors; fullPHY and production remain open.

Latest verified live handles: sevenhold43727102369/job132851331678 executing repair step; combined quarantine/214hold43726840782/job132850520498 executing sizing+allcornerSTA; preparedguards43726998790/job132851006935 executing test driver. Do not restart live workers. Await actual evidence before selecting/combining further candidates or integrating preparedsourcefixture. Previous turn was progress, this turn progress; full goal remains active, no blocker.

## Seven residual hold paths now have measured safe repair inputs; native trials live

Previous turn made progress: authenticated publication and restored cloud capacity. Current residual measurement43725515099/headadfa6e SUCCESS. Derived14166341678 fullZIP SHAcb5383123492ae6fc8baf6aefe55a86445d06f8deb6d53ea88acedf07021de37 verified in RAM;564 input targets, source441ff, untouchedsource=true. Native14166881413 SHAca5925a3fbd078637e4194002adbfd86beaf86c143a7ce3cf3e8f7a3916770f1 remains cloud. Subsequent local RAM re-download timed out; native job was NOT restarted. Instead compact cloud summary43726902731/head4640b6434b206f558078292971f9d8e319f6ee90 succeeded, authenticating fullZIP plus every consumed report member. Derived14167026008 SHAdbf057d3e7faa98bc560a1c3681d45c0ad4dc13a8224b78014b635a90ca43413 independently verified.

All seven negative paths have intermediate input setup margins >=1ns. Last eligible input selected by existing conservative policy (all ABC734931):773242/A(2.980288ns),783117/C(1.943596ns),807931/B(2.059344ns),807923/B1(1.746518ns),779157/A2(1.369031ns),769806/A2(1.844618ns),807890/A2(2.719357ns). Several downstream endpoint setup margins are NEGATIVE, hence do not add delays blindly at endpoints.

Native repair43727102369/headce2c27eed959fbcd9ff893cc0f945d94edd24185 on codex/new-rx-seven-residual-hold is IN_PROGRESS. Worker scripts/repair_rx_seven_residual_hold.py binds exact read-only measurement43725515099, then independently binds physical producer43720921041/head15c and its native792adf5/derived54b5559. Restores exact441ff, preserves214 existing delays, selects exactly7 negative paths/no unselected, adds7 delays with unique nssoc_rx_residual_hold_ prefix (avoids old names), retains1ns margin-per-delay rule, native pin/master/incidence/placement guards and fresh3corner global+564branch STA. AST passed; outcome pending. No timing acceptance yet.

Independent combined candidate43726840782/heada164dabeb173f8d9419b564c82001cb441c36c64 on codex/new-rx-combined-quarantine-hold IN_PROGRESS. Worker scripts/size_rx_combined_quarantine.py restores441ff with214 delays and resizes quarantine buffers9519/9492/9485/2680/2194 buf1->4, with same first-worst-path/master/incidence guards. This combines PREVIOUS214-delay repair and five-buffer setup trial, NOT the newest7 additional delays. Must measure and later combine final successful candidates, never add counts from separate trials.

Corrected PHY diagnosis43725858840/headc73ef842 SUCCESS; derived14166527169 SHA0be03e3f5ecae1a1f86cdfd5549eefdb0d6a7ca93ff7b9a1f26020a6ff230788 verified. Receipt artifact_sha256 now correctly b29c348bce77354de4c311334900a17e12607cbe0238d65065cd7d5efc1feee0. Originalsamplecounts reproduced, phase14.566706mV<30mV and sampler/XOR wrong signs persist. No activeHBT VCE<.4V, source10ohm peaks5.484523/5.329001mA. Clockbasecrossings~23-26ps afteroriginaledge,0missing. Observed truth table diagnosticonly. FullPHY remainsFAILED, need actual circuit improvement, not shifted sampling gates.

Prepared validator43726529947 FAILED correctly on5pass1skip in base. Artifact14167145555 fullSHA068638c0a773717f0428079046e18cb547fc171a21f9b864769abdc78d347d73 verified: register_file_external_entry_contract looked at ROOT/hw/soc/gen instead of authenticated prepared_sources fixture. Fixed test to use fixture/gen/ibex_top.v with requiredfileassert, no skip. Rerun43726998790/headfec7a01dafeea2b6e61bb9d9e1bb1eedf6a20641 IN_PROGRESS. Branch currentf27f41ca57c879bcdafef056401758e062a27760 differs only removal of nowunused pytest import (not in runninghead). Still requires12actualpositiveguards and stalehashnegative refusal. Integration must include this test fix, fixture/newmetadata/notice/receipt only afterPASS; no experimentalworkflow. Fullgoal active, all native/sourcework cloud.

## Publication authenticated; actual prepared-source guards dispatched

Publication43725915316/head374b0cc6dd4548c9f7f3d79d0a22985c65a5d695 attempt1 SUCCESS. Derived14166183251 full ZIP SHA17cf79cbe44ae4472126b2310e4b944463fd822dfb2fa8593661b16527db1f89 authenticated in RAM. Result PUBLISHED_AND_REDOWNLOADED_HASH_VERIFIED_NOT_YET_CI_INTEGRATED; metadata SHA1ee40532bf8e71d56d9c79d64d3929d7f4158ce7ee67eec3f337250264c908eb verified; archive08e629ada48eb210c3dc32a964b8e10864844d7e8b8f2a697862e23ba4d9a4b4,203844B. Release446127809 retains original producer589540 and38-file replay; not physical acceptance.

Dispatched ready validator 43726529947 at exact efa2587c4848f4eb7772e405ea8de232ae6c399d on codex/prepared-source-current-guards after verifying publication and absence of duplicate dispatch. Requires12 actual positive base/full structural guards plus stale-hash negative refusal. Do not integrate new fixture/metadata/notice until PASS. Native residual43725515099 and corrected PHY diagnosis43725858840 remain live at last observation. Goal active.

## Owner access verified; unintended release-tag queue cleared

User confirmed access restoration. Active gh account Melihakbulut221; API confirms push/admin/maintain true. Found evidence tag prepared-sources-20261115-43716663208 unintentionally triggered legacy push workflows because cloud-* tag exclusion does not match this tag. Cancelled 66 nonterminal runs, restricted to event=push, this exact tag and source589540e861dbd006d98f1de7622c0079ebd921ad; every cancel API returned success. This does not cancel workflow_dispatch native residual measurement/publication/diagnosis. Future evidence tags must respect workflow filters; no historical tag/source rewritten. Freed capacity let publication and corrected PHY diagnosis start.

Formal run43710889358 is now terminal FAILURE overall, but both formal stages SUCCESS. SoC artifact14166023682 full ZIP SHA024a84795402c3f72e4e50bce6d6441e53c3389bca5b67540b8cec84a306499d verified in RAM; result head386adc72f170ef69d298ce817a5e11de14b071a7, passed=true, selected_stage=soc, sources_unchanged=true, tasks dictionary116 entries, exclusions dictionary6 entries, complete_sweep=false. Do not equate dictionary counts to pass/exclusion counts without inspecting contents. Pilot evidence was already verified. Other CI failures remain; no physical timing/fullPHY acceptance follows from formal success.

Latest live observations: {"43725515099": ["in_progress", null], "43725915316": ["completed", "success"], "43725858840": ["in_progress", null]}. Residual all-input branch measurement remains the next prerequisite to safely fixing seven remaining fast hold violations on candidate441ff. Ready prepared-source validator efa2587c remains undispatched until publication success and artifact authentication. Corrected PHY diagnosis uses c73ef842. All native/source work cloud; no local files created. Full goal remains active.

## Buffered PHY diagnosis measured clock delay; report hash shadow fixed

Diagnostic43725443962/head150a0ef SUCCESS; artifact14165713461 SHA78c6acc34efacab1a022c2e437270fbed0e4a9743e4d4d0ab79128c0534c0d4b authenticated. FullfailednativeZIP/raw verified byworker, originalsamplecounts reproduced, no activeHBT VCE violations. Source10ohm peakcurrent beforebuffer5.484523/5.329001mA versus originaldirect~26mA. Native localclockbase crossings23-26ps afterexternaledge,0missing over248events/device; noninterpolatedrows. Delay may contribute tosamplingfailure; notproofsolecause. Same-time observedinput truth table remainsdiagnostic, notlogicinversionproof.

Found inheritedlocalizer variable shadow: archive digest variableexpected overwritten byclockpolarity, so oldsummary artifact_sha256=-1. ActualZIPcomparison beforeoverwrite usedcorrectSHA, so rawverificationexecuted, butreceiptfieldINVALID. Fixeddistinctarchive_sha256 plusfinalassertagainstAPIdigest, commitc73ef842de49f0ba8f9b4e7d26332000737975b9. Read-only corrected rerun **43725858840**, statusqueued. No native transient rerun, no acceptancegateschanged.

## Source release created with owner API; assets still cloud-verified

Pretaggedrun43725663204 FAILEDHTTP403 fromActionstoken despiteContents:write; artifact14165578868 SHA0818374395eb3b991416df2d8a66458bca7c58258c93340a8fed0adba084cd91. Exacttagalreadyverified. OwnerAPI successfullycreated release **446127809**, tagprepared-sources-20261115-43716663208,target589540e861dbd006d98f1de7622c0079ebd921ad,make_latestfalse. No localsource/nativefiles. Cloudworkerunchanged nowuploads/re-downloads/hashchecks assets intoexistingrelease: run **43725915316**, source374b, latestqueued/None.

Readyvalidator **efa2587c4848f4eb7772e405ea8de232ae6c399d** binds exactrun43725915316/head374b/attempt1. NOTDISPATCHED untilpublicationSUCCESSandverifiedderivedmetadata. Residualholdmeasurement43725515099 remainsinprogressatlastpoll; SoCformal43710889358 stilllive. Fullgoalactive.

## Publication retry after owner access: HTTP504 and exact tag preparation

Owner-dispatched43725447427/head374b FAILED with HTTP504 at releasecreate; log confirmsContents:write. This is distinctfromprevious403 underwrongaccount. Checkedrelease/tag afterterminalfailure: both404, so no ambiguouscompletedpublication. Created intendedimmutable tag prepared-sources-20261115-43716663208 pointingEXACT589540e861dbd006d98f1de7622c0079ebd921ad usingrestoredownerauth; no existingtagoverwritten. Redispatched unchangedpublicationworker as **43725663204** withpreexistingexacttag. Lateststatusin_progress/None.

Readyvalidator now **95e204352fc36ff8c0fa8e55d56b61826b046fc8**, exactproducerbinding43725663204/374b/attempt1 andallhash/negativecontrolsretained. NOTDISPATCHEDuntilpublicationSUCCESS. NativePHYdiagnostic43725443962/head150a0ef and residualholdmeasurement43725515099/headadfa6e areIN_PROGRESS atlastpoll. Goalactive; restoredpush/admintrue. Next: evaluatebothnativeoutputs andpublishsuccess->validator.

## Access restored; current physical results and next cloud jobs

The user restored access. `gh auth status` showed both accounts; switched the active saved account from mel11h to Melihakbulut221. Repository API now confirms push/admin true. The goal is active. No credentials were printed or copied.

Both new RX trials completed successfully as experiments, NOT timing acceptance. Full derived ZIP SHA and per-corner state hashes independently verified:

- Hold run43720921041/head15c0195: source0451 -> candidate441ff0490eb3239ba9011e1b5e08e99f7f8304a600e30ec38dc4806d10525e3e. Added214 delays on209 inputs. Hold slow/typ/fast counts0/0/7, worst slack+.222705/+.0846121/-.0299224ns. Setup2276/0/0, worst-1.86168/+.0185629/+.965397ns. Slew36/6/3,cap0. Derived14165417399 SHA54b555903714ceebf5648e9319743013f0fbf4cd0027fcf7d80571e8f45dd8e8; native14166012274 SHA792adf5a25ee7fb8f331aa19c208a0991a3d89c5620dde157acd36e9b84a973e. State run/4-nssoc-holdfast/state_out.json.
- Quarantine sizing run43721847063/headb8089c8: source0451 -> candidate3ce326baddbae3fd57e15e40688213342dd1127c0cbf799c302689a4170efeef. Setup2233/0/0, worst-1.84451ns slow; hold unchanged1/2/210. Derived14165917559 SHA6b8bf8a9726d0ae9a1c0fb7b7fc1663ba87ad0f5031b2bbb5c48b9bf214cac86. This candidate is SEPARATE from hold repair; no combined acceptance. Worst now head_last[4]->rx_eop, including existing hold33182 delay.692288ns, then fanout3452/3451/3450/3449. Other critical paths link_up->r2_handshake and staging->commit (fanout8282 buf1 .893393ns delay). Do not remove hold cells blindly.

Residual fast-hold endpoints:161171(-.029922ns),165885(-.024214),176732(-.008744),176731(-.004994),163157(-.002434),159806(-.001611),176723(-.001221). Existing measured endpoint setup is negative on several paths. Intermediate measured807934/A1 has.505898ns,760121/A has.380026ns,807891/B1 only.042615ns; none qualifies under prior1ns-per-delay rule. Many other intermediate inputs have no existing branch report, motivating the next native read-only measurement.

Actual-load PHY run43717632809/head9709 FAILURE is an electrical rejection, not simulator crash: simulatorreturn0,3496.141s,stderr0,diagnostics[],sourcesunchanged. Derived14165465911 SHA192c9bc0f4a75abf5defb1d548ee1784e869023303764fc8dd1072be3ec6eae6 verified; native14164934308 SHAb29c348bce77354de4c311334900a17e12607cbe0238d65065cd7d5efc1feee0 remainscloud. Originaldevices_passedtrue and added30HBT buffer screenPASS(minactiveVCE.4356596V), but A/B/C/Dwrong129/95/98/153of765;below100mV129/173/144/161. Asettling60.53125ps,B/C/D118.90625ps versus unchanged37.5psgate. X/Ywrong414/123,below100mV695/554. Phase14.566706mV<30mV; VI40.125356uA<50uA. Buffer7idealR and physical650 not fullPHY acceptance.

Publication43722855425 FAILED HTTP403 Resource not accessible by integration; artifact14166005175 SHA05818aa35e231c93947468da76f496dac59ba1c07a89619270d7d039b16aa8df verified. Earlier43717961699 failedHTTP502. Retried only after owner access restored; same source and idempotent no-clobber publication rules.

New jobs:
- codex/publish-prepared-source-refresh: run **43725447427**, head **374b0cc6dd4548c9f7f3d79d0a22985c65a5d695**, last observed completed/failure.
- codex/buffered650-failure-localization: run **43725443962**, head **150a0ef2ae2f47ac3683a03ac5573d7d3c85427e**, last observed in_progress/None.
- codex/new-rx-residual-hold-branches: run **43725515099**, head **adfa6e152dcf8560ed6cc5839682376c8a9d0633**, last observed in_progress/None.

Prepared validator head **2d51320c9f01871f66214d10b92e5d28d4bbe853** now binds exact publication43725447427/head374b/attempt1, unchanged hashes/refusal tests. NOT DISPATCHED until publicationSUCCESS. Buffered localization worker uses exact failednative+raw SHA8fa0dedff6a0519ea6fabb3f60adee47348bbf681447579e73537e89d3a8a8d6, all original sample gates; source-current calculation correctly uses prebufferclk_inp/clk_inn, notcp/cn. Residual hold worker measures EVERY input on all reportedsub50ps paths and top10setup/corner, exact7negativefast-source check, no placement changes. All workcloud; no finalroute/fullPHY/production acceptance.

## Publication terminal HTTP502 retried; compact setup audit independently confirms target

Publication43717961699 FAILED, artifact14164694678 SHA40ecd6989a9f5c810762093c3e9643798663c10438d90bb7b45b7eabcfc153ee verified. Actual joblog132823493627: GitHubHTTP502 at gh release create, AFTER authenticated replay/tar checks. API release lookup confirmed404/no partialrelease. Redispatched SAME source374b0cc6dd4548c9f7f3d79d0a22985c65a5d695 as **43722855425** (newrunattempt1), no source/gatechange and no successfulproducerrestart. Existingpublicationworker is idempotent and verifies anyexistingrelease/assets instead ofclobbering.

Ready validator branch **codex/prepared-source-current-guards** now **4dcf5754febe69d8425066145fb62f4a541f565d**, onlyexact producer run/name binding43717961699->43722855425 changed, head374b/attempt1/fullartifactSHA/metadata/tar/stalehash guards preserved; ASTpassed. STILL NOT DISPATCHED untilretrypublicationSUCCESS.

Compactsetup audit43718375160 SUCCESS; artifact14165156570 SHA19206dc13cdf17b007d6496b00afc22dfa98e86ae842919fecdd2df9ce81b585 verified. Source0451/reportSHA782725f8b6efdcf06b464bb5976fccb02c5f65e89c27dc32d9502d18950aca41. Parsed1004reportednegativepaths (NOTall2276violations): quarantine reset293,ownershiplink_up242,retryreset186,creditsreset51; othercounters/data pathsremain. Worst-1.861761ns withsamefanout9519/9492/9485. Confirmsalreadydispatchedfivecelltrial43721847063; noduplicateCADrunneeded. FullPHY/finaltimingstillopen.

## Pilot artifact verified; freed runners started pending work

RAM observer79341 finishedEXIT0: full artifact14165410093 ZIP SHA0c7fe43f verified, exactrun/head bound, result **54pilot tasks PASS,0exclusions**, allsource_state clean,sources_unchangedtrue, selected_stagepilot,complete_sweepfalse,makeexit0,5078.022s. Not fullSoC proof or fullCI pass.

Duplicate43710151473 nowCOMPLETED/CANCELLED. Capacityrelease effective: publication**43717961699 IN_PROGRESS**, compactsetup audit**43718375160 IN_PROGRESS**. Hold43720921041 andquarantinesizing43721847063 stillqueued atlatestpoll. Continuepublication->readyvalidator9c6 dispatch onlyaftersuccess, thenfixtureintegration; inspectsetupauditcompactoutput. ActualPHY43717632809 remainsindependent. Fullgoalactive.

## Redundant formal workers identified by actual input comparison and cancelled

Compared heads386adc72f170ef69d298ce817a5e11de14b071a7 and185526ac2e0dda69118962290e3288c1f13546f7. Formal directories formal(25entries),hw/rtl(10),hw/soc/formal(66) byte/blob-identical. Read all37SBY configs; all77declared tracked file inputs matched exact blobs; no executable config references changedrx_credit/soc_top/interfaces. Sole generated dependency ibex_register_file_ff.v: identical Makefile preparation recipe, tools.soc.mk/upstreampins/tools.mk, sv2v_ibex.sh(7db85aa5),ibex_fault_port.py(082086cc). check_formal_sweep/source_state, policy, peripheral/regfile/scrub helpers,requirements,checks.yml identical. This is scoped formal-model equivalence, NOT equivalent full newRX RTL.

During final preflight, retained43710889358 pilotjob132813745103 completedSUCCESS while socjob132813745437 remainedlive. Newer43710151473 had ONLY duplicatepilot/socformaljobs live; allotherjobs completed (including failing generic checks). Cancel requested for43710151473 ONLY after this verification; all nativephysical/analog jobs untouched and earlierformal retained. This supersedes older checkpoint instruction to retain43710151473, based on newly examined actual formal input closure. Do not label cancelled CI green or reuseold proof as fullnewRX integration acceptance.

Pilot artifact **14165410093 /0c7fe43f2a8c2afe088fcd86c965ab185dc5eaaa945103c0429bd2a20e11823c**,2433562B; RAM observer **79341** authenticating archive+result at checkpoint time. If stillrunning, poll samehandle. No localfilespersisted. Remaining main native jobs43717632809(actual650PHY),43717961699(publication),43718375160(setupaudit),43720921041(hold),43721847063(quarantinesetup); recheck after capacityrelease. Fullgoalactive.

## Actual remaining worst setup path recovered; five quarantine-path buffer trial dispatched

Signed HTTP Range ZIP read succeeded after whole-archive observer12332 ended143. Range observer19775 EXIT0, verified member SHA against producer result and source ODB0451f211 on API-bound artifact14162873930/e97aedd4. Whole archive digest had been verified earlier; NOT rehashed during range read. No local files persisted. Compact cloud audit43718375160 preserved (not cancelled).

Actual worst slow path FF343559 ->FF163168, PCIe250MHz, slack **-1.861761ns**. Launch net **u_pcie.flow.packets.endpoint.endpoint.receive_packet.quarantine.rst_ni**. After rebuffer23773 buf16, three buf1 cells fanout9519/9492/9485 contribute .337619/.387044/.376394ns; downstream nand4_1 736012 delay.700016ns, inv1 736013 .446701ns, further logic and fanout2680/2194 buf1. This is a different remaining reset branch after previous five-cell upsizing, not evidence that previous cell IDs are reusable across builds.

New native **43721847063 /b8089c88b9668b83a356f298ac419f0d7293567c**, branch **codex/new-rx-quarantine-path-sizing**, dispatched. Worker scripts/size_rx_quarantine_path.py restores exact43715930015 sized native14163265585/82f96ab5 and derived14162873930/e97aedd4. Verifies full archives, individual members, source0451 and first max path contains exact quarantine net/allfive buf1 cells before native mutation. Five choices **fanout9519,9492,9485,2680,2194 buf1->buf4**. Previous five upsizes retained. Same-incidence/master/port census guards, detailedplacement/check, all600 branch reports and fresh3corner globalSTA. Timing20/4/8/8ns and5percent derating unchanged. AST passed only; native outcome pending. Artifacts retain **ack-rx-reset-sized-derived/native-RUN** names. Source branch created at final skip-ci commit to avoid redundant generic ancestor CI.

Parallel hold trial43720921041 also starts from0451 but is a separate candidate; do NOT claim both ECOs combined without a subsequent actual combined candidate and fresh STA. Actual650clockbuffer43717632809 still running; publication43717961699 and setupaudit43718375160 queued at latest poll. Full objective active and incomplete.

## PCIe root admission integrated; new RX sized hold repair dispatched

Verified root run **43719347506 /89e0e5e749dc2383c06289a34640f7a8dc6f93e9** SUCCESS. Full derived artifact14163703883 digest93a4351dd4da082fcf1b5c1a87f53b3073a0e2f7a6f8e3ded4dcdd9240480fe2 and all121 indexed outputs authenticated. All88 XML testcases have finite positive simulation duration, no skipped/error/failure: shared25, epoch30, Gen12 33. Source controls129 refusals. Exact62 protected current sources checked before integration. Integration **163f6563fed1555a04d42ab84c0ab77b0a5bc3b3** contains only checker, root manifest, reviewed-context document and evidence receipt; NO experimental workflow. Standalone passes do not validate changed top-level reset semantics or complete serial PHY.

New branch **codex/new-rx-sized-hold-repair**, head **15c019517c9807b26bd39e875d5359b0ea48dbf8**, dispatched native workflow. Native run **43720921041**, job132832514757, confirmed QUEUED with no runner assigned. Duplicate branch-creation generic run43720915366 at inherited base797c was cancelled only after checking checks.yml, exact head, queued status and no running jobs; native candidate retained. Worker scripts/repair_rx_sized_hold.py authenticates reset-sized producer43715930015/head797c, derived14162873930/e97aedd4 and native14163265585/82f96ab5. Source ODB0451f211. Uses ONLY all600 actual branch measurements from this sized source, all corners/all path groups; chooses final measured input with >=1ns setup reserve per delay (2 delays if hold<-0.15ns). Unselected paths retained explicitly. Previous oldRX cell IDs NOT reused. Proven native STA-to-DB unique pin/master/incidence/port/placement guards preserved; target/cell census computed from qualified rows. Fresh all-corner global and branch STA after ECO. No positive native result yet. Artifacts new-rx-sized-hold-derived/native-RUN. Python AST passed; dedicated dispatch, generic duplicate push CI skipped.

Actual650 clock-buffer experiment43717632809 remains running; publication43717961699 and compact setup audit43718375160 queued at latest observation. Prepared validator9c6c62e on codex/prepared-source-current-guards is STILL NOT DISPATCHED: first require publication success. Root admission fix complete, prepared guard fixture integration and full canonical CI still pending. Full serial PHY, routing/extracted timing and production gates remain OPEN. All native execution/artifacts cloud only.

## Current prepared source structural validation implemented, waiting for publication before dispatch

Branch **codex/prepared-source-current-guards**, head **9c6c62e72b4c244800e676b7187726f7a79193a6**, created. **NOT DISPATCHED** because publication43717961699stillqueued. Worker **scripts/cloud_check_current_prepared_sources.py** requires publicationrun43717961699/head374b/success/attempt1, uniqueartifactmetadata/fullZIPdigest, publishedproducer589/43716663208, exacttar08e629 andallcurrenttransformhashes. MaterializesonlyNEWmetadata/notice intoephemeralcheckout; sw/tests/conftest.py singlepathchange toprepared-sources-current-20261115.json. Nohistoricalrecordmodified.

Nativeworkflow pins existingOSSCAD2026-08-04/setupaction andrequirements. Runs EXACTsixMakefile soc-prepared-guards tests for BOTHbase/full profiles, requires6actualtestcases/exit0/noerror/failure/skip each. Then mutatesONLYnewmetadata'sEthernettransformhashbacktoold1a3a..., requiresactualpytestfixtureERROR withspecificDependencytransformchangedmessage, finallyrestoresbyteexactgoodmetadata. Tracksallsourcehashes/gitdiff; source/proofscopeexplicitlystructuralelaboration(memoryblackbox), NOTmappedgateboot orserialintegration. PythonASTpassed; zero nativepassesclaimedyet. Futureartifact **current-prepared-guards-RUN** includesvalidatednewmetadata/notice/12positiveJunit/negativeJunit/result forreview; afterPASSmergeonlyfixture/newreceipt/notice intointegration, leaveexperimentalworkflowout. Commit[skipci]andno dispatchuntilproducerready avoids redundantqueue.

Latestlive: **43719347506rootcontext88-testregression nowIN_PROGRESS**; **43717632809actualloadedPHY IN_PROGRESS**; **43717961699publication QUEUED**, **43718375160setupreportaudit QUEUED**. Fullgoalactive, no finalacceptance. Thisturnprogress: concretepreparedguards/negativecontrolimplementation withdependencygating plusverifiedlivework.

## Actual PCIe root regression pin drift audited; explicit context refresh candidate dispatched

Retainedgeneric43710889358 RTLjob**132813745298** completedFAILURE. Actual log shows check_pcie_guarded_root.py pins abort on docs/pcie-training-epoch-ingress-20261031.md, thenfourguardedmodulesreportedUNREACHED. Not a provenRTLfunctional failure. AuditedALL61protectedfiles onintegration5814810: EXACTLYtwo pre-existingdrifts: document96b7e565...->9cfc53b6...; soc_top.v b782a7fb...->2695f631.... Allother59matched. Oldbytes atde7bd7ba0aaf661ed49433f0e181543c215f2ced authenticatedbyoldSHA beforediff. Documentcorrectshistoricalexecuted110tests; topchanges includeCORE_BT_ALU,dedicatedpcie_sys_rst_nresetleaf,registeredlink/training/retrain. These AREsemanticchanges; notcalledcommentonly/equivalent.

**43719347506 /89e0e5e749dc2383c06289a34640f7a8dc6f93e9**, branch **codex/pcie-root-context-refresh**, QUEUED. Newrootmanifest admits EXACTtwo current-contextdeltas inlegacyepochmap plus originalnettype/workflowdeltas; legacy manifestsunchanged. Checker observed-delta set extended toEXACTtwo reviewedpaths, nofreewhitelist. Pinsupdatedforcheckeritselfandnewprotected **docs/pcie-root-context-refresh-20261115.md** withcompleteunifieddiff. Allscopeflagsremainfalse inclmainchip_serial_integration. Source/refusalmutants retained and dedicatedEXISTINGroottemplatecopiedbyte-identical; workflowapproved_sourceexact89. Expectedactual25shared+30epoch+33Gen12tests=88, plusallsource/XMLrefusals. ASTpassed, resultsnotyetknown. DoNOTmergetointegrationuntilactualtestsverified; standalonepasswouldNOTprovechangedtopresetsemantics/fullPHY. Experimentalcommit[skip ci]avoids anotherduplicatefullRTLqueue; explicitnative88-testworkflowdispatched. Mainchecks.ymlunchanged.

Queuecleanup: duplicategeneric**43711852327**cancelled afterconfirmingdiff386adc->01fdcontainsONLYmeasure_ack_chip_hold_margin.py andexperimentworkflow,bothpythonqualitypassed; retainedolder43710889358plusnewRXgeneralregression43710151473. ActualnativePHY43717632809 remainsIN_PROGRESS; publication43717961699 andsetup-audit43718375160 queuedatlastpoll. Fullgoalactive/open, allcomputecloud.

## Queued duplicate generic checks removed; no native test cancelled

Cancelled six not-started/pending genericpush checks **43718376793,43717963405,43717631576,43717555311,43715932009,43716131763**. Before each cancellation verified owned experimentbranch, checks.yml/eventpush, statusqueued/pending, NOjobin_progress, andexactcommitfiles restricted toscripts/pnr/experimentworkflow/docs (noRTL/testsuite/mainCIworkflowchanges). Dedicatednativeworkflows andactualRTL-changing regressions retained. This avoidsrepeatfullunchangedRTL suites on pureanalysis/nativeworker changes; doesNOTclaimgenericCIpassed or removefutureintegrationtests. Existingknownpreparedsource/mappedbootfailuresremainopen.

Latestlivepoll **43717632809 IN_PROGRESS**, **43717961699 QUEUED**, **43718375160 QUEUED**. No nativeproducer restarted orcancelled. Previousgoalturn=progress(queuecleanupwithactualcancelresponses)+verifiedwait; noimpasse/fullgoalnotmet.

## Remaining setup report analysis moved to cloud after observer-only download timeouts

LocalRAM observer68834 exhausted180s on SAME24MBderived14162873930 after prior120stimeout43270. Bothobserverhandles finished; no localartifactpersisted and successfulphysicalproducer43715930015 wasNOTrestarted. OriginalwholeZIPpreviouslyauthenticated andsetup2276/hold1/2/210 remainverified.

**43718375160 /a026fdb2ce7ff954c743294fe626d3c94f64b462**, branch **codex/new-rx-reset-critical-audit**, QUEUED atlastpoll. New **scripts/cloud_audit_reset_critical.py** authenticates43715930015/head797c/attempt1/success, exactderived14162873930/e97aedd4 andcandidate0451f211. Reads/SHAlocks existingrun/2-nssoc-sizedslow/max.rpt, noCADrerun/mutation. Emits compactJSON with20worstpaths,launch-net census,initialbufferchains,firstfullpath,and100resetpaths. Artifact **new-rx-reset-critical-audit-RUN**, result.json only. ASTpassed. Useactualreportedchainsfornexttargetselection; fullreportpathcounts are reportcoverage, not magically allpaths.

Nativeactual650clockbuffer43717632809 remains IN_PROGRESS atlastlivepoll. Preparedsourcepublication43717961699 QUEUED. No terminal failure observed for either, no redundantrestarts. Thisturnprogress: executable cloud-side existingreport audit toavoid repeatedobserverdownloadstalls; goalfullscope unchanged/active.

## Current replay publication dispatched; actual-load PHY worker live

**43717961699 /374b0cc6dd4548c9f7f3d79d0a22985c65a5d695**, **codex/publish-prepared-source-refresh**, queued. Worker scripts/cloud_publish_prepared_sources.py restores native14162773969 with exact19e58df digest and producer43716663208/head589/success/attempt1; authenticates originalmetadata768a29 andtar08e629/notice, verifies38tar members. Publishes NEW tag **prepared-sources-20261115-43716663208** targeting589540, no overwrite/clobber. Downloads bothpublishedassets again viaauthenticatedAPI and verifiesfullhash+size before producingnewmetadata release_assets. Artifacts **prepared-source-publication-derived-RUN** containnewmetadata/notice/result. Hostedworkflow contentswriteonlyforthisauthorizedrepositoryevidencepublication. PythonASTpassed. Publicationnotyetobserved; fixturechange andunchanged elaborationtests stillpending. Do notclaimCIclosedbeforeactualtest.

Actual-loadedPHY **43717632809/9709f80dfe3dcf1abeae5da770ee2ea7abdb1c5a** rechecked IN_PROGRESS at "Assemble all five partition bases and execute whole256bit loaded nominal late case". Sourceclosure restoration/setup completed; actualelectricalresult pending. No finalPHYclaim.

Setup-derived reread observer43270timedout120s; successful native43715930015 preserved. Retry SAMEartifact14162873930 in RAM session**68834** stillreading atlastpoll, timeout180s. It will printfirst5slowmaxpaths' first23linesafterlaunchQ toidentifynewresetbranches. Observationfailureisnotnativefailure/restart. Sourcecandidate0451f211/2276setup unchangedverifiedpreviously. Fullgoalactive.

## Valid-Nx buffer six screens completed; actual650 loaded integration experiment dispatched

**43716130683/0d5f38e9ce08fec744306a847b94437988f1aa1e SUCCESS**. Derived **14162368221 /ab3955f802c820a666c19bebc52417c9c7ef91fa47e794f52348fd26d8d3a13f** verified, native **14162637999 /97851568e6bfccbc54f9fb923dc3560acc803c3a6bd2ed558929577964308bcf** cloud. Six direct/buffer100/250/500fF native traces complete, no diagnostics abort. Buffer37.5ps minimum signed output253.370/250.681/242.759mV,0wrong/0below100mV of510each. Buffercrossings6.433..6.474/7.766..7.815/9.758..9.855ps; no missing/multiple. Input peak~5.5mA, versus direct500fF18.967mA. Buffer500fF10ps samples ALLbelow100mV (not blanket high-speed pass). Native minactiveVCE .42846/.43360/.43617V, maxallVCE1.46693/1.47036/1.47358V; maxmodelic/emitter1.1556/1.4940/1.9079mA. Modelic not fullterminalSOA. Receipt docs/evidence/cdr-valid-nx-buffer-screen-20261115.json. Ideal sizingR/lumpedloads/typicalonly, no physicalbuffer or fullPHY acceptance.

**43717632809 /9709f80dfe3dcf1abeae5da770ee2ea7abdb1c5a**, branch **codex/current650-cascode-clock-loaded**, DISPATCHED. Base30d598 original actual650 fullcomposition; new helper **scripts/cdr_mos650_clock_buffer_loaded.py** copies frozenhelper with exact unchanged prefix (clock/stimuli/parsers/measure_wave gates), alters run_loaded only to insert same30HBT+7idealR fragment as subcktXclock between original10ohm RCP/RCN and physicalmodelcp/cn. Actual650geometry/models/loads/256bits/nominal_late/.3125psstep/34.25nsstop unchanged. Adds buffer nodeV/current captures andOFFreadback (154HBTtotal), samefullcapture parser/zeroOP/diagnosticgates, separate bufferVCE>=.4absVCE/VBE<=1.6/modelicperemitter<=3mA screen (notterminalSOA). Allphysical650electricalmeasurements remain original. AlladdedbufferprimitiveNx1or4,aggregate117,actualfrozenmodeldomain guarded. Workerownedbranchchanged and every changed/new sourcepin updated. Initial09a1011/43717553529 cancelled WHILEQUEUED because copiedworkflowpin stale; corrected9709updatesworkflowhash too, no native producer interrupted. Artifacts **buffer-loaded650-derived/native** rootpaired650-full-composition. This is real-load exploratorydriverintegration, NOTphysicalbuffer/layout/PHYsignoff. Fullmodels/gates notweakened.

## NewRX branch measurement and reset-sizing results

Read-only **43715682174/70ddf8596c404fed3d6741fb4a90dd87bf151ba0 SUCCESS**. Derived **14163130668 /3e2e87478b2bea0683a65389062763bc62433cdcb0dfbb1d4e797c2904ec0af8**, native **14162519493 /8cd195d4f1c1bb2811460077e0737a29befb46b89142acb423ed347445d9b3f0**. Actual600targets223paths source815b689e, allbranchreporthashes verified in RAM. Same measured guard latestpin setup>=countns, count2ifhold<-.15else1 selects **209uniqueinputs/214DLY**, minimumsetup1.394064188ns; ONEunselectedfastpath startflatten u_pcie.receive_ownership.commit_copies[2].read_copy.FF551964 ->FF176723; measuredpins ABC734931...760121/A buf1,807891/B1 o21ai1,endpointD. Do not silentlydrop orclaimallcovered. This selection belongs BASE815b, not resizedcandidatebelow; no holdECOdispatchedyet.

Reset-sizing **43715930015/797c06051cde73076629381ed79fe8d0c5e6452f SUCCESS**. Derived **14162873930 /e97aedd4ac08772ae08e9648dd0915f2e09cf78b90c59d6961d04e26a7003964** authenticated, native **14163265585 /82f96ab53a4bdbe4b8bcbff4edcda480ce886e37628ab26da7872da90a77215f**. Candidate **0451f211acbac6b2b29a14b9b19d4b5beb1eb23c96cbb10d4a76c9f4fdf15cb7**,state run/4-nssoc-sizedfast/state_out.json. Setup**2276/0/0** vs2382/0/0,WS-1.86176/+.0185629/+.965397ns. HoldUNCHANGED1/2/210,WS-.121472/-.185617/-.201013; slew36/6/3cap0. Five exactbufferchanges plus detailedplacement/checkpassed, but worstslowonly2.64psgain; inspectnewworstresetpaths before next sizing. CurrentRAM-derivedread session43270 downloading sameartifact toinspecttop10paths; observationdelay isnotnativefailure. No finalrouteacceptance.

## Current prepared-source replay finished; publication and fixture integration still pending

**43716663208/589540e861dbd006d98f1de7622c0079ebd921ad SUCCESS**. Derived **14163155706 /9a2945466f60a19777a3d4133f78eeb676ae019b52ba2d2f1aaaeb3a99314dfb** authenticated; native **14162773969 /19e58df2882a35c686342d2f1938ff061424f2917885c6ddb1adefb3a72ac809** cloud.38filesbyte-replayed, sourcesunchanged. Newtar prepared-sources-current-20261115.tar.gz203844B SHA**08e629ada48eb210c3dc32a964b8e10864844d7e8b8f2a697862e23ba4d9a4b4**; metadataSHA**768a29aebfade4d3fde252644dbaa99b2f876aeb4bafc5d816730fb726fec3ff**. Nativearchivehas package/metadata,tar,NOTICES. Needcloudpublication toNEW immutableRelease (historicalnotreplaced), addrelease_assets shape {release_tag,assets:[{name,bytes,sha256,url}]} toNEWmetadata, then update sw/tests/conftest.py fixturepath and rununchanged structural/elaborationguards. NOTdoneyet; guardmustremainfailclosed.

Queuecleanup43709881841cancelled afterconfirming newer43710889358sametestedRTL/workflow/tests, diffONLYexperimentworkflow,repairflow,newrepairworker, bothpythonqualitypassed. Newerregressionretained. This releasedcapacity; sourcejobandanalogbegan. Fullgoalactive/allcomputecloud.

## Current prepared-source regeneration dispatched without weakening integration guards

**43716663208 /589540e861dbd006d98f1de7622c0079ebd921ad**, branch **codex/prepared-source-replay-refresh**, queued at last poll. Worker **scripts/cloud_refresh_prepared_sources.py**, temporary cloud-evidence-summary workflow. Uses make soc-rtl-prepare SOC_INTERFACE_PROFILE=full with pinned upstreams/sv2v, then independent fresh sv2v replay and base/full interface generation in scratch root pointing to clean pinned ext. Existing scripts/collect_prepared_sources.py compares all generated .v and four interface bundle files byte-for-byte, creates NEW package prepared-sources-current-20261115.{json,tar.gz} plusNOTICES, leaving historical20260926record untouched. Additional tar verification checks exact membership,no unsafe paths,all lengths/SHA and equality to actual generated source; alltrackedfilehashes/gitdiff guarded. PythonASTpassed. Artifact names prepared-source-refresh-derived/native-RUN. No release publishing or fixture expectedhash changes yet; must inspect actual newreceipt then publish authenticated package and run unchanged structural/elaboration guards before integration.

Nativepriority jobs revalidated: newRX branch43715682174 and reset-sizing43715930015 IN_PROGRESS; valid-Nx clock-buffer43716130683 QUEUED, notfailed/restarted. Lastturnprogress: executable cloud regeneration/verification implementation anddispatch addressing the independentlyconfirmed integration guard failure. FullPHY/finaltiming/productionobjective stillopen. No local source/CAD persisted.

## Additional integration guard failure confirmed while native timing jobs continue

General CI43710889358/job132813745683 and43709881841/job132813779486 both failed formal-and-boot at "Prepared upstream compatibility and whole-SoC elaboration". Actual job logs show prepared_sources fixture rejects outdated transform snapshot before elaboration (1passed5errors); native-boot dependency skipped. This does not invalidate independently source-restored native timing measurements, but no green full integration CI claim is allowed.

The current timing/combined transform drift against docs/evidence/prepared-sources-eth-mbist-20260926.json was checked directly:

{
  "hw/soc/flow/adapt_eth_mbist.py": {
    "recorded": "1a3a9a0a734eb41d5886d05a08592b8062c58de074a9d086be9f76097489e576",
    "current": "6a2c0c1edf87d1673bea63519ed170b4f54c8e905dd5393afb20fc8231ea1508"
  }
}

Correct follow-up is regenerate/replay current prepared dependencies via scripts/collect_prepared_sources.py, preserving historical evidence, update fixture to new authenticated release metadata only after byte-identical independent Ibex/base/full interface replays. Do NOT merely edit expected transform hashes or remove stale-source guard. Relevant fixture sw/tests/conftest.py; generation script compares soc/gen/*.v with independent sv2v replay and four base/full interface bundle files; metadata/notice/tar immutable output. This is a source-snapshot CI issue, not the separate mapped gate-boot failure.

Native priority jobs43715682174 (newRX branches) and43715930015 (newRX reset sizing) rechecked IN_PROGRESS; valid-Nx PHY43716130683 queued. No producer restarted because waiting. Full goal active; pending exact-result evaluation remains next.

## Old RX margin repair complete; new RX setup/hold native experiments running

**43714299681/8b72c3e96e93a3cc38902e5649f5493d2c900ca0 SUCCESS**. Derived **14162840855 /d8e43d4cf1f86d452b9231d72b6ead705a7324d4d7b0fc1a84ca762cca372bd3**, native **14162482681 /20409cbb2268c1f157e008b6811d7199ad6753cc252e6b01a5a6a353b4c90384** (1.72GB cloud only). Candidate ODB **9626a02146f01a57b32b85c035c384370ee3cb3a5edf5bedf31b99143653e754**, state run/4-nssoc-holdfast/state_out.json. Derived ZIP plus all3state/max/min hashes verified. Hold0/0/0,WS+.288109/+.136266/+.00457756ns; setup2716/25/0,WS-2.24368/-.351183/+.755945ns. Slew16/4/3,cap0. Fast reported sub50pspaths157 -> **27** (4264reportedpaths percorner); othercorners0. Not50psreserveclosure, notfinaltiming. Actual141additionalDLY stage preserves old271; candidate remains OLD RX2a345, do not transplant IDs or claim NEW RX holds closed. Receipt docs/evidence/ack-chip-margin-repair-result-20261115.json.

NewRX readonly43715682174 and reset-size43715930015 both verified IN_PROGRESS at native measurement/ECO steps. Current native setup target reset-distribution fanout buffers; no result yet. Only superseded generic ancestor checks43712092757/head185526 cancelled after verifying diff solely workflow and postCTSworker and currentefa6 native43712102946success. Currenthead/nativework retained.

## Valid-Nx analog repeat encountered a model-comment decoder issue; fixed without changing model bytes

43715582272/45997e9 FAILED BEFORE any simulation: defaultUTF8 reader rejected0xb5 micro symbol in authenticated model comment. Derived **14162107110 /84f021badda1732db397ea1e331b2ad9dc34042b53ab16ec150571015cc60674** verified; native14162741153 /9064aab72196ffa069c20221857f76e9a02b852d93fe107cb9a04ace3a91218e retained. This does NOT refute the transistor-domain repair or qualify anything electrically.

Fixed only model preflight reading to read_bytes().decode('latin-1') (lossless byte-to-codepoint inspection, no file rewrite). **43716130683 /0d5f38e9ce08fec744306a847b94437988f1aa1e**, codex/cdr-cascode-clock-buffer-screen, QUEUED atlastpoll. Circuit30validNxdevices, allmodels/solver/sources/envelopes unchanged. ASTpassed. Need actual six nativecase results; repeat no new circuitguess. FullPHY/fullchip/production objective stillactiveandunmet. Allcomputecloud.

## New RX reset-distribution sizing experiment dispatched with placement legalization

**43715930015 /797c06051cde73076629381ed79fe8d0c5e6452f**, branch **codex/ack-rx-reset-tree-sizing**, queued at last poll. Parent70ddf859 newRX branch-measurement code; exact producer43712102946/efa6, native14162267126/4bbf12a0, derived14162406038/7d95470d, ODB815b689e unchanged source. Scripts **scripts/size_ack_rx_reset_tree.py**, **hw/soc/pnr/ack_chip_reset_sizing_flow.py**. Uses newRX restore and native branchSTA, no oldABC735174 mapping IDs.

Measured slow worst reset path has fanout9410(buf1 -> buf8),9409(buf2 -> buf8),9384/9379/9378(buf1 -> buf4). Exact five native masters all preflight before mutations; instance census, other masters, all pin incidence and chip port incidence checked. Then **detailed_placement and check_placement -verbose** before independent three-corner global/branch STA. No ideal clocks, constraint changes or broad repair. All edits AST-validated. Experimental candidate, not accepted; hold worsening/global setup impact must be measured, not inferred from buffer strength. Artifacts **ack-rx-reset-sized-derived/native-RUN**, rootack-chip-branches, final run/4-nssoc-sizedfast/state_out.json.

Read-only newRX branch measurement43715682174 now IN_PROGRESS per repository active-run list. OldRX margin repair43714299681 stillIN_PROGRESS. Analog valid-Nx repeat43715582272 stillQUEUED, no results. Latest turn progress: concrete new measured-path repair implementation/dispatched; no completion claim. Full PHY/route/final timing/product objective unchanged.

## New RX chip postCTS measured: typical/fast setup zero; slow reset-distribution path now worst

**43712102946 /efa6c5d0b26093d77f10a8f3bc241daaf7162a9c SUCCESS**. Derived **14162406038 /7d95470db280223dc05896e0c8fe1af40908bfa4b4175b5b58bf6f843de377cd**, native **14162267126 /4bbf12a0ec0f0da173eb37c82ebc3626647d9b3986900aa43b23f6609e6ff035** (437MB cloud only). Derived ZIP and all after state/max/min file hashes independently verified. ODB **815b689e59c10173047bf123cf5078b16f1b491e52925150558161130b104e54**, repaired_state run/5-openroad-resizertimingpostcts/state_out.json. Setup slow/typ/fast **2382/0/0**, WS **-1.8644/+.0185629/+.965397ns**. Hold **1/2/210**, WS **-.121472/-.185617/-.201013ns**. Slew36/6/3,cap0,fanout1361. Receipt docs/evidence/ack-rx-dllp-postcts-result-20261115.json. PostCTS estimate only, not final routing or fullPHY/boot acceptance.

Worst slow path now FF365863 -> FF365770, pcie_clk_i; startnet u_pcie.receive_ownership.commit_copies[0].read_copy.rst_ni. New mapper **ABC734931**. Reset distribution fanout9410 buf1 (slew.805787ns,delay.656286), fanout9409 buf2(delay.536851), fanout9384 buf1(.439843), fanout9379 buf1(.322197), fanout9378 buf1(.329506), followed by NAND/NOR logic. Potential buffer sizing/tree repair must be checked for hold impact and exact current native identities; do not assume oldRX EOP worst path or reuse ABC735174 IDs.

Read-only three-corner input-branch measurement **43715682174 /70ddf8596c404fed3d6741fb4a90dd87bf151ba0**, branch **codex/ack-rx-dllp-chip-branch-measurement**, QUEUED at last poll. Parent efa6, imports its NEW source restore and exact postCTS result IDs/digests/ODB above; copied proven measure_ack_chip_branches.py and ack_chip_branches_flow.py with new producer pins. Actual negative hold paths plus top10 setup paths, no physical mutation; native input resolution exact. Artifacts ack-rx-dllp-chip-branches-derived/native. Need results before measured hold ECO selection. OldRX marginrepair43714299681 still native IN_PROGRESS.

## Clock-buffer real model-domain defect corrected; native repeat pending

Supply-referenced bias run43715256618/head1f868 failed again at68.2973ps. Derived14161932806 SHAcbf7d732319f77a0c8d244180da9010a7106812f615541cd95b371d6f70d3549 verified; native14162900286 SHA6b254e53a0d4df35599ece4b66066a7bc51b5120e19e9a9b869f58c267ac1d0a cloud. Bias hypothesis did NOT fix startup.

Found concrete invalid extrapolation in experimental topology: regular IHP npn13G2 specifies Nx1..10; candidate used12/16. Model Csub=2.30e-14-1.50e-15*Nx gives NEGATIVE1fF atNx16. This is our invalid instance sizing, not a claimed process-model defect. Corrected each12 to3parallelNx4, each16 to4parallelNx4, referenceNx1 retained: **30native instances**, same aggregate emitter count but changed individual parasitic/thermal networks, so remeasure. No model clipping/thermal disable/tolerance relaxation. Cloud preflight reads actual authenticated model, checks domain/formula and positiveCsub for everyinstance before running. Docs on experiment branch: docs/cdr-clock-buffer-emitter-domain-20261115.md.

**43715582272 /45997e9bb9693d4bdec1afe0d69a153a6f6196e9**, codex/cdr-cascode-clock-buffer-screen, QUEUED at last poll. Existing frozen clocks,load cases,solver,maxstep,source10ohm preserved; Rref3200 retained. All30OFFflags andV/ic captured. PythonAST passed. Await realresults; full650/PVT/realpassives/layout/PEX/SOA/PHY integration still open. No fullPHY/production claim. Allcompute cloud; goal active.

## Native clock-buffer startup rejection investigated; supply-referenced bias candidate running

Run **43713326015 /9d2c5d9d360d9ac3d79aa321eeea985ebcb040ec** failed electrically/numerically. Derived artifact **14162305555**, SHA256 **34559d8fa8c5830869cb3a1032c1d173fd2561f2c153b9d939c22136db063b7d**, independently authenticated in RAM. Native artifact14162230681 SHAa606b3864707412807a389e4b0cdfddbd0e6e4703b1571ca85c9410b3aaa2cd5 retained cloud. Three direct capacitive controls completed, but buffer-100ff aborted at68.2974ps with temperature-limiter NaN / timestep-too-small on q.xtn.qnpn13g2 (234rows). Native exit0 was correctly rejected by diagnostic gate. No buffered electrical acceptance.

Next **43715256618 /1f868237e8bd04110fa9a03b5918db70b8ef01b0**, same codex/cdr-cascode-clock-buffer-screen branch. Replaces ideal externally forced IREF ramp with ideal sizing resistor Rref avdd bias3200. Bias naturally follows supply; initial hypothesis avoids reference bias forced above a low rising rail, NOT proven root cause. All10device sizes,clock/supply ramps,loads,source10ohm,models,solver tolerances,maxstep and diagnostics preserved. ASTpassed; inspect six native measurements before any promotion. Reference doc on experiment branch: docs/cdr-clock-buffer-startup-rejection-20261115.md. Real resistor geometry/full650load/PVT/PEX/PHY integration still required.

NewRX fullchip postCTS **43712102946** and oldRX hold-margin repair **43714299681** verified IN_PROGRESS native steps. No accepted results yet. Do not mix oldmapper735174 ECO IDs into newRX865/91e322mapped chip.

Queue cleanup: canceled only superseded push checks after verifying exact checks.yml/event/ancestor and source diff scope (scripts/workflow/pnr/docs), never live native work. Earlier43711845849,43710460966,43710146086,43709879902; latest43714289380 and43712994885. Current-head tests/native producers retained.43713327233 already completed when checked. Source and CAD remain cloud-only; full goal active and unmet.

## Sub50ps margin measurements verified; 141-input experiment dispatched, five paths explicitly unresolved

43711850416/01fd5593f442a7adaa70c83173035cd074a87fcf completedSUCCESS. Derived14161562880 SHA**bedcfb0dd51ffc34e2fbbc0bcd6860937515f11e678fbfe771b0b217cca4a0d2**, native14161433414 SHAc8a3cd143da8883329567e3b5554059a18870353074dd30bde7659563ac243ff. FirstRAM-only24.9MBdownload hit180stimeout; retrycompleted, no nativejobrerun. Source9a1633unchanged/returncode0,574targets,157fastsub50pspaths,allbranchreportsusedforselectionhashverified. Latestinputwith>=1nssetup produces**141distinctinputs covering152paths**, minselectedsetup**1.052330732ns**. FivepathsendpointsFF181448,365799,155696,159982,160400 lackeligiblemeasuredinputs. Theirbestmeasuredsetupreserves .977135718/.583467484/-.141730636/.151265666/.774344623ns; donotcallthoseunsafeingeneral, onlyineligibleforthisconservative1nsDLYguard. Fullsetupandholdjointrepair remainsneeded. Receipt docs/evidence/ack-chip-margin-selection-20261115.json.

**43714299681/8b72c3e96e93a3cc38902e5649f5493d2c900ca0**, codex/ack-chip-measured-margin-repair, DISPATCHED. Worker scripts/repair_ack_chip_margin.py, nativeflowack_chip_hold_repair_flow.py. Authenticatessamecurrent9a1633source/native14160612913 thenexactmeasurementartifact14161562880/run43711850416/head01fd; exacttargets/pathmatch andselectedreporthashes. Selects141sinks, oneDLYeach, preservesall271oldDLY. ASSERTexactfiveunselectedendpoints andcoverage152of157; writesunselected_paths andunselected_reason. No silentcoverageclaim orweakened1nsguard. Nativeprefixnssoc_ack_margin_* avoidsoldcellcollisions, alloriginalplacements/ports/otherincidenceguarded. Freshthreecorner574branch/globalSTA afterECO. Artifacts **ack-chip-margin-repair-derived/native-RUN**. PythonASTpassed; actualnewholdreserve/setupimpactnotyetknown. OldsourceIDsnottransferredtonewRXchip.

43712102946 newRXpostCTS stillIN_PROGRESSnativebefore/afterSTA+repair. Clockbuffercorrectedrun43713326015/9d2c5d9d360d9ac3d79aa321eeea985ebcb040ec remainsQUEUEDatlastpoll; no newSPICEresults. FullPHY/fullchipfinaltiming/productiongoalunachievedandactive. Allcomputecloud.

## Clock-buffer first native launch path fixed; corrected experiment live

Initial43713082943/87e2568c155bd4b818f626b3155132883e5fae4f FAILED before anytransient: direct-100ff command exited1 because cornerHBT.lib pathmissedone models/level. Authenticatedderived14160409803 SHAe75062509efc182a861aba863f457bb095337be13ae9201a6a1e9d50966f478a containsstderr/failure/runtimeacquisition; native14161451631 SHA34fc8292cab44a497ae9d0e530832446375bda9e504254561175ed2082cc1fb8. Runtime acquisitionselectedlistproves actualmember source/model-sources/models/models/cornerHBT.lib. No electricalpass/failure inferred fromlaunchpatherror.

**43713326015/9d2c5d9d360d9ac3d79aa321eeea985ebcb040ec**, samecodex/cdr-cascode-clock-buffer-screen, DISPATCHED. Only corrected .lib path to models/models/cornerHBT.lib relativetomodel-sources and addedis_filepreflightbeforeSPICE. Nativeengine/modelpins/circuit/sizes/clock/sourceR/loadcases/solver/timing/envelopeobservations unchanged. Inspectderived/nativeartifactsbeforeanyfull650integration. Source87 design documentationremainsdescriptive butcurrentexecutorhead9d2. Allclock-bufferresults remainexploratory and unaccepted untilfullphysical/full-load gates; no realrppd/layoutimplementedbythisexperiment.

43711850416 marginSTA and43712102946 freshRXpostCTSconfirmedIN_PROGRESS atlastpoll. No reruns ofhealthyCAD. NewRXCTSsource92371b remainscompletedimmutable. Fullgoalactive andunachieved.

## Fresh RX CTS complete; transistor clock-buffer development experiment launched

43710149740/185526ac2e0dda69118962290e3288c1f13546f7 completedSUCCESS. Authenticatedderived14161257474 SHA3c60bf1b82f58aa92f86a9ac2f6b0bd133d9c4dc24053a847b14e5ee36b6efe0; native14161681305 SHA473e93bedc7f7b5090577153d244c1b380d37e8554f9477db27af970a692a064. ActualCTSODB**92371b1b21268ba97e109a6650683f1e9512612d06133d03295101d8c71a2d98**,state run/27-openroad-cts/state_out.json,native771.875s. Sourcebinding43709259323/2dc,63files,newnetlist91e322 andJSONd5c1verified. Receipt docs/evidence/ack-rx-dllp-chip-cts-20261115.json. AccumulatedCTSmetricsincludeinheritedearlierstagevalues (e.g.hugeoldcornerWS); doNOTcomparethemwitholdrepaired2718/25counts. IndependentpostCTS43712102946/efa6clearsmetricsanddoesfresh3cornersbefore/afterrepair; itis live. Marginmeasurement43711850416 also live atlastpoll.

**43713082943/87e2568c155bd4b818f626b3155132883e5fae4f**, codex/cdr-cascode-clock-buffer-screen, DISPATCHED. Newphysical-direction development: ten nativeHBT differential/cascode/emitter-follower/current-mirror topology,6idealsizingresistors,original10ohmclocksource andfull8GHz34.25ns waveform. Direct/buffered100/250/500fFperleg screens(6cases), originalmodelruntime andgenerator hashpinned, allnew10HBTstartupflagsreadback/nativeVs/ic captured. Moredetails docs/cdr-cascode-clock-buffer-candidate-20261115.md. Worker scripts/screen_cdr_clock_buffer.py, netlist scripts/cdr_cascode_clock_buffer_candidate.inc. PythonASTpassed, nativeoutcomepending. Artifacts cdr-clock-buffer-derived/native. This isinitialtopology sizing, NOTnativepassives/layout/fullactual650load/integration; accepted/fullPHYalwaysfalse. No old650inputs/models altered. IdealR/C/ground andmodelic limitations explicit. Actualfull650/PLLfailuresremainuntilrealnewphysicalcircuitpassesunchangedfullgates. Needreviewcandidateall10HBTenvelopes beforefurtherload/physicaldevelopment; do notpromoteontopologyrunstatusalone.

No persistentlocalfiles/CAD/nativewave downloads. Fullproductscope stillopen, goalactive.

## Hosted queue released by cancelling only verified documentation-only checks

43711850416 margin measurement and43712102946 newRX postCTS nowIN_PROGRESS(checkoutconfirmed), previouslyqueued. Mainplacement43710149740 stillnativefloorplan/CTS, untouched. Investigationfound17runningrepojobs includingfourgenericRTL/formal/checks jobs fordocumentation-onlycommitcb4510. Verifiedrun/event/branch/head, singleparent andexactchangedfilesBEFOREcancellation:43710003003 cb4510 changedONLY docs/evidence/ack-chip-267-delay-result-20261115.json;43711985847 1a559297 changedONLY CLOUD_RESUME.md. Cancelrequests bothconfirmedCOMPLETED/CANCELLED. No source-changing tests/nativeCAD/producers cancelled. Bothqueuednativeworkflowsstartedimmediatelyafterward. Futureevidence/checkpoint-onlycommits use[skip ci] toavoidunnecessarygeneralCADregressionqueue; actualsource andexplicitnativejobs keepallguards/tests.

Previousgoalturnwasprogress(preparedanddispatchedsource-boundpostCTS). Thisturnremovesverifiedqueuecontention; no newtiming/PHYpass claimed. Fullobjectiveunchanged, allcomputecloud. Next inspect43711850416 current9a1633 sub50psheadroom; inspect43710149740/43712102946 newRX physicalresults andcompareallcorners. Physical/ECO IDs mustremainboundtotheirownnetlists.

## Exact new RX chip post-CTS continuation dispatched

**43712102946/efa6c5d0b26093d77f10a8f3bc241daaf7162a9c**, codex/ack-rx-dllp-mainchip-postcts. Parent185526 freshplacementbranch; physicaldependencies corrpre_banked_flow.py/corrpre_postcts_flow.py/interface_flow.py/check_timing_derate.tcl compared byte-identical topreviousde22 flow. scripts/cloud_predecode_postcts.py adapted ONLY producerbinding to43710149740/head185, exactnewmappednetlist91e322 andJSONd5c1/sourcebuild43709259323/head2dc/63files. RequiresCTSproducerattempt1success thenuniqueartifactnames ack-rx-dllp-chip-placement-derived/native withmetadatahead/run/digest plus allnativefileSHA andactualstateODBhash. NewODB/artifactIDsareobservedafterpublication, neverguessed orreusedfromoldCTS. Wait<=5400s, no nativeCTS restart. ThreefreshcornerSTA before/after electrical+BankedTimingRepair, propagatedclocks,20/4/8/8ns5%constraints, inheritedmetricscleared. Actualrepairresult remainsunaccepted untilallrequirementsverified. Artifacts **ack-rx-dllp-chip-postcts-derived/native-RUN**. PythonASTpassed; nativepending. This givesfreshRXcandidate timingneededbeforedecidingwhetherDLLPcomparisonhelpsfullchip.

43710149740 stillnativeplacement/CTS atlastpoll. 43711850416/01fd5593f442a7adaa70c83173035cd074a87fcf sub50psholdmeasurement queued(hostedrunner), no failure/restart. Old271-delaycandidate remainszero holdcounts buttinyfastmargin; source9a1633mustnotmixwithnewmapped91e322. LastactualfullPHYread-onlyevidence remainsloaded650failure andPLLcurrentdiagnosis; no analogcircuitrepaircompletedinthisturn.

This checkpoint is documentation-only; skip genericpush CI toavoidusingrunnercapacityforanotherunchanged-CAD receiptupdate. Experimental source/workflow commits andexplicitnativeworkflowdispatches remainchecked. No hardwaretestgateweakened. Fullgoalstillactive, allCADcloud.

## Three-corner hold counts zero; fresh RX chip synthesis complete and physical flow active

**43710888222/386adc72f170ef69d298ce817a5e11de14b071a7** completedSUCCESS. Derived14160404103 SHAa95289e0de482a8a0f6e9a39d79dca1f28ed9e36cc1e3d4f04ac68de917ac291; native14160612913 SHA4fd7159bf3acab4d34eb0f426c45c2dd1459e80810d185347161c6f9afbb2e95. Allthreecorner metricfilehashesverified. CandidateODB **9a163c3124826ca5bdbb12fab75e8808a6064d18d1b099ed489c865d359c65cd**, sourcee2b564. Four selected upstream nativeDLYs successfullyadded; original267preserved. Holdcounts**0/0/0**, WSslow/typ/fast **+.278192/+.127707/+.000100031ns**. Setupunchanged2718/25/0 andWS-2.2579/-.351183/+.755945. Slew16/4/3,cap0. ZEROCOUNTS ARE NOT FINALCLOSURE:fastreserve0.100031ps, original4264minpaths/corner include157fastpaths<50ps(others0). Receipt docs/evidence/ack-chip-zero-hold-result-20261115.json. Notrouted, no mappedboot/fullPHYacceptance.

**43711850416/01fd5593f442a7adaa70c83173035cd074a87fcf**, codex/ack-chip-hold-margin-measurement dispatched. Read-onlycurrent9a1633 restore, scripts/measure_ack_chip_hold_margin.py, exactly157sub50psfastpaths plus top10setuppaths/corner. Requiresallreportedgroups reach>=50ps beforeassuming low-marginreportcoverage; pin aliases/nativeSTA guard preserved. Actualinputbranchsetup/minmargins neededbeforeanymoreDLYinsertion. Artifactsack-chip-margin-derived/native. First133branchreports ofpreviousrepairwerenotcoverageofthese157newpaths, so doNOTreuseascompleteheadroomproof.

**43709259323/2dcbd7f9cedd8c9a70ee60b0adbc1cb5e2c96fd2** completedSUCCESS, actualRTLboot/replayregressions/synthesis/mappinggatespassed. Mappingartifact **14161006222** SHA**b1ac28abbf662ee303ec408590d1a71ce6d77b201c5dfd360828e1b992dd80f9**, verified. Native **14161235501** SHA**1602eefebdaa0e4ea4f9cbfbce400926883bd6ff355be596bd56d08fd883aa11**,9.56MBstayscloud. Replayregressions14160543858 SHAfff57130fbf2cba90a7dc261682ccb89061e43ce1f9c41dadb3ad86657b4f99a. Newcells116214,20SRAM(16dual+4single),26registeredwritebits,cachedEOP, ACKprefix+DLLPlast enabled. Netlist**91e32262883da381ceae0617233d65f81766fce63050987b4b2341ac38df57aa**, mappedJSON**d5c1d6c8762679297d7b75db7b0dc1f14db17758f2bf645e863b6df0df618715**,63sourceoutputs. RX865/ACKf563verified. Receipt docs/evidence/ack-rx-dllp-mainchip-mapping-20261115.json. NOTmappedgatebootorfullPHYacceptance.

**43710149740/185526ac2e0dda69118962290e3288c1f13546f7** successfullypassedexactsource restoration and nowRUNNINGnativefloorplan/placement/CTS. FuturepostCTS requiresactualnewODB/reportidentity; nevercopyABC735174/ECOIDsfromoldchip. Sourcefull20/4/8/8ns5%constraintsunchanged. FullserialPHY/route/setup/SRAMRC/productiongoalstillOPEN. Allcomputecloud; no localpersistentfiles.

## Residual branch selection independently verified; repair still running

RAM-only re-read of derived14160212631 succeeded afterthefirst90s timeout. ZIP SHA14457999 verified; sourcee2b564, sourcesunchanged/returncode0, targets andeachcandidatebranchreporthashverified. Localobserver session19879 nowfinishedsuccessfully. FourendpointD setupslacks are NEGATIVE(-.245302,-2.161812,-2.066339,-.797046ns), so doNOTadddelayatendpoint. Selectedearlierinputs ofmapperABC735174: 769640/B NOR4 setup1.186635733ns/hold-.040262904;779327/B2 A22OI setup2.775292873/hold-.006655676;779204/B2 A22OI setup2.816184282/hold-.005996537;772855/A0 MUX2 setup2.928442240/hold-.001284195. Eachsetupminimumacross3cornersandallreturnedgroups. Exactlyfourdistinctchoices, oneadditionalDLYeach. Receipt docs/evidence/ack-chip-four-residual-selection-20261115.json. NativeECO43710888222/386adc72f170ef69d298ce817a5e11de14b071a7 confirmedliveafterselection. Waitactualfreshallcornerresults; nozero-holdclaimyet. Fullscopeunchanged.

## Residual measurement complete; authenticated four-path repair dispatched

**43709880012/8ecd5371a47ec0dfbba719e203a15a0fa02c7a17** completedSUCCESS. Derivedartifact14160212631 metadataSHA14457999d8492281e9087dd953c45be7ba1d90e9d711252fae4dd868df289e54,size19382957; native14160252700 SHAa133c1cb295de1f95a918a4f9132a90fa0394f9ebee4ed3ced48aecc4716298d. Nativecomputationnotrestarted. Independent RAM-only deriveddownload hit90sobservationtimeout; second180srequest inprogress atcheckpoint, session19879. This is downloadobservationnotnativefailure; reportcontents/marginsnotyetindependentlyreviewedlocally.

**43710888222/386adc72f170ef69d298ce817a5e11de14b071a7**, codex/ack-chip-four-residual-hold-repair, NOW DISPATCHED. Samepreparedphase2workerplusliteralexpectedartifact14160212631/SHA14457999 gate andQUALIFIED_FOUR_RESIDUAL_CHOICES print before anyECO. Run/head/attempt/successbinding, archiveSHAandallselectedbranchreportSHA, sourcee2b564, targets/paths equality, exactly4distinctsinks and>=1ns allcornersetupheadroom allmustpass BEFORE physical changes. Nativepin/master/unique-driver/oldincidence/placementguard retained. FournewDLYidentitycells onlyifguards pass, thenfreshallcorner branch/globalSTA. No claimthatselectedmarginsorzero-holdhavepasseduntilactualresult. Newheaddoesnotmodifyclock/derating/holdmarginlimits. Artifactack-chip-residual-repair-derived/native. Existing267-delaycandidateunchanged; experimentnotpromoted.

43709259323 exactRX+ACKchip stillinprogress firmwareRTL/synthesis;43710149740 freshplacement/CTSstillwaitingonthisexactproducer. FullserialPHY/routedchip/finaltiming/productionnotcomplete. No localpersistentfiles created.

## Residual repair prepared; authoritative workflow identity corrected

The actual residual measurement is workflow_dispatch **43709880012/8ecd5371a47ec0dfbba719e203a15a0fa02c7a17**, NOT43709881841(the latter is generic push checks). At11:45UTC job132798925785 running native residual measurement since11:39:34; not stalled/pending. Always filterevent=workflow_dispatch and head SHA when discovering continuation runIDs. Updated preceding checkpoint reference accordingly. Producer43709259323 nowpassed replayregressions, running freshRTLboot/wholechipsynthesis. Placement43710149740 correctly waiting on exactproducer.

Prepared **codex/ack-chip-four-residual-hold-repair /e6eda8e830ff42b123cb7e2ee39bfbe1a6f857d9**, NOT DISPATCHED. Worker scripts/repair_ack_chip_residual.py and hw/soc/pnr/ack_chip_hold_repair_flow.py. Parentactualmeasurement8ecd; authenticates267-delay e2b564 source+native14160125922, parsesexact4residualholdpaths andtop10setup paths. Requirescurrentmeasurement43709880012 attempt1/head8ecd success; findsuniqueack-chip-residual-derived-43709880012 artifact, checksdigest and nativebranchreporthashes, exactsourceODB/targets/pathmatch. Selectslatestinputperpath with>=1ns actualallcornersetupheadroom, exactly4distinctsinks, oneadditionalnativeDLYeach. Uses nativeSTA->physicalpin API anduniquealiases; preservesallold267cells/placements/incidence/ports; newcellsnamednssoc_ack_residual_* toavoidcollision. Freshallcorner branch/globalmeasurement; nofinalacceptance. PythonASTpassed, nativevalidationpending. Inspectmeasurementreport first, then dispatch .github/workflows/cloud-evidence-summary.yml onthisbranch. Ifheadroomguardfails, selectfromactualbranchmargins withoutweakeningclock/uncertaintyconstraints. Artifactsack-chip-residual-repair-derived/native. No actualextraECOexecutedyet.

## Hold254->4 verified; fresh RX chip physical continuation gated and live

43708228938/4c2f65da2aae34d7e3116ba8edcca84a9c93e21f succeeded. Authenticated derived14160105837 SHA207970d03d9c52d70508cc18513a5d083cf4e018a5e0292b9cda9d48177776aa, native14160125922 SHA8fd442bb947cde2c8e355f7a22eb818179aa2b1361d8c9800c6e600ffe499355. CandidateODB e2b5649189b950d742c363bc5e3c36f41e299bf0130843384c4a5e5b142c939d. 267delay cells,254sinks, source97f316. Hold slow/typ/fast0/0/4; WS+.278192/+.0799065/-.0402629ns. Setup2718/25/0, WS-2.2579/-.351183/+.755945. Not routed/final accepted. Receipt docs/evidence/ack-chip-267-delay-result-20261115.json.

**43709880012/8ecd5371a47ec0dfbba719e203a15a0fa02c7a17**, codex/ack-chip-residual-hold-measurement dispatched. Read-only three-corner measurements on actuale2b564, parses4remaining negativehold paths andtop10setup paths; authenticate entire267-delay native bundle; remap source state paths into ack-hold-source, retainoriginal778proof artifacts. Worker scripts/measure_ack_chip_residual.py; artifacts ack-chip-residual-derived/native. Native measurement confirmed live(job132798925785,stepstarted11:39:34UTC) at11:45UTC. Inspect current branch margins before selecting extra delays. Residualendpoints FF163338,163143,162982,160687; worst40.263ps. Do notguesssetupheadroom.

**43709259323/2dcbd7f9cedd8c9a70ee60b0adbc1cb5e2c96fd2** RX+ACK mainchipbuild remains live, replayregressions atlastpoll. **43710149740/185526ac2e0dda69118962290e3288c1f13546f7**, codex/ack-rx-dllp-mainchip-placement dispatched with exactproducer-success gate. Restorer waits43709259323 attempt1/head2dc for<=9000s; failclosed onnon-success. Requires exactnewRX865,ACKf563,allmappingflags,20SRAM/16dual,26registeredbits,cachedEOP. Authenticatesactualpublished artifactnames/digests, allnativefileSHA, sourcehashes, nooldnetlist IDs reused. Freshplacement+CTS preserves20/4/8/8ns and5% derating. Source-binding records newpublished artifact identities; no guessedcellcount or oldmappinghash. Physicalsource branch inheritsactual2dc inputs. Workers restore_predecode_chip_boot.py/cloud_predecode_chip_placement.py, artifacts ack-rx-dllp-chip-placement-derived/native. Gate boot, routing and finalsignoff remainseparate.

43708501996/ee9a693879374f500074f147f832e873d15825e4 allstatusinputs bypass completed; derived14160281037 SHAad1b69cbf957c4b33a2f13babe36704d37f8951454999bba4e144e4989c60825. Native14159858140 SHAef7194cf7c9480b34b940b367de8fe5c9e2e90b2a524417b0555c8afcb56c462, ODB6af8965b2e9794e54e6afc67298d751eaec29441cdbf029dfba490c794746369. Setup2721/24/0; WS-2.2579/-.0308553/+1.12765. Holdunchanged1/17/254. Typicalimprovementbut2additional slowviolations vsoriginal, NOTpromoted. Receipt docs/evidence/ack-chip-all-status-input-result-20261115.json. Nevercombinewithholdwithoutnewmeasurement.

43708067466/1a2db89a1a11c0f311694f97d9ed8dcf1dcda104 actualPLLcurrent analysis completedSUCCESS. Derived14160086150 SHAcabf1ee08500685802f907e4c11a4e8f1a1dcb0e0645f9579177bf393686b6dd, native14160225775 SHA6c999716e0c68f5bbd6920d084e38985393ed536356b57d7ca9165d260c7692e. 28terminalcurrents,132nativecolumns,419392rows,26historicalanomalywindows. MaxabsoluteKCLresidual1.073887e-15A,maxnormalized2.693133e-11. Physicalterminalcurrent differsfromprimitiveic; no safety/acquisition/fullPHY acceptance. In26anomalywindows minimumVCE tail391=.433686V,392=.889920,393=.828861,394=.694360,395=.803340,396=.805699,400=.697650. Do notinferalltime safety fromthese windows. Receipt docs/evidence/pll-terminal-current-diagnostics-20261115.json. Next analogdesign must address unresolvedclockdrive/loaded650/PLLacquisition, notrelax gates.

All work cloud, no persistentlocalfiles created. FullserialGen3x4/mainchiproute/finalsetuphold/productionstillOPEN.

## RX full traffic qualified; actual next mainchip build dispatched

43707359187/d7719ea5449f3c61102f9a633692beaa19aa66be bothjobsSUCCESS. Trafficjob132791216392 artifact14159124888 SHA782de6a69e9796a879db0f2ce1cc52bcb092f9862abdda0ab854c04bb9d2ad36: exactRX865d687a272faf4a5077f79af21ace3b4afbe5085b640dd20f3512c8a43ff7d5, eight300kcycle positives andeightactualcomparison-inversion mutationrejections. All16nativecase log hashes verified. Formalartifact14158424919 andtwofullmoduleproofs/twomutants alreadyverified. Receipt docs/evidence/rx-dllp-full-traffic-20261115.json. No mappedboot/routing/timing/fullPHY claimfromthis.

**43709259323/2dcbd7f9cedd8c9a70ee60b0adbc1cb5e2c96fd2**, codex/ack-rx-dllp-mainchip-build, NOW DISPATCHED afterbothproof/traffic gates. Sourceandconfigurationdetailsinpreviouscheckpoint unchanged. NewnativefirmwareRTLboot+wholechipsynthesis20SRAMs; nativeartifact ack-rx-dllp-mainchip-source-native-RUN, mapping ack-rx-dllp-mainchip-mapping-RUN. Exactlegacy+newRXandACKqualificationrequired beforeCAD; correctedACKmappingverifierfromeedc4f retained. Whenactualbuildpasses, bindnewmappedsource/outputs andusefreshplacement/CTS/allcorners. Do NOTapplyold97f316buffer/holdECO cellIDs tonewmapper. Need measure shiftedDLLPlength paths aswellasindexcriticalpath.

43708228938 exact-STA-to-physical-pin holdrepair,43708501996 allstatus-ANDinputbypass,43708067466 PLLboundaryanalysis allremainliveatlastpoll. No previousnativeproducerrestarted or gateweakened. Completeproductscope stillopen.

## RX full-module formal passed; exact next-chip build prepared but not dispatched

43707359187/d7719ea5449f3c61102f9a633692beaa19aa66be formaljob132791216269 succeeded. Artifact14158424919 SHA8b258dba14526dcea5c9efc26f1c875f661ddabc5a0a87e2882ded4836ff8daf; allfourlogSHAverified. Positive(dw4,slots1),(dw8,slots2)fullmoduleequivalenceproven; actualDLLPcompareinversionmutantsbothrejected. Existingequal-resetcopycontractonly. Trafficjob132791216392 stilllive; no wholechip qualification claim. Receipt docs/evidence/rx-dllp-full-formal-20261115.json.

Prepared **codex/ack-rx-dllp-mainchip-build /2dcbd7f9cedd8c9a70ee60b0adbc1cb5e2c96fd2**, NOTdispatched untiltrafficpasses. ParentexactACKchip56f97b8744d2dcd92821a79a7dd63168aacefa9c. RXsource865d687a272faf4a5077f79af21ace3b4afbe5085b640dd20f3512c8a43ff7d5 copiedexactfromqualifiedcandidate; outsideoneDLLPconditional span matchesold2a345byte-for-byte. SameoldACKreplayf563source and alloriginalcore/Ethernet/SRAM/otherPCIedefines. AddedSOC_PCIE_RX_DLLP_LAST_COMPARE tobothRTL/synthesisknobvalidation andconfigurationreceipt. MapperusescorrectedACKsource/census logicfromeedc4f64900475d70dd5785a6f5d72276748d4b6, explicitnewRXhashanddefinegates, unchanged20SRAMcensus. Qualificationgateauthenticatesold2a345cursor formal+traffic AND new865fullformal+trafficwithexactrun/head/job/artifact/log/casecounts; verifieslegacy sourceoutsideconditionalunchanged. NewbuildcannotreuseoldRXapprovalasnewapproval. Newworkflowartifacts ack-rx-dllp-mainchip-source-native/mapping/replay-regressions. Initialin-memorygateprototypehadPythonelse16syntaxerrorbeforeANYcloudmutation; correctedactualpreparedfiles astparsed. Nativebash/pytest/RTLboot/synthesis checksstillpending actualdispatch. Futuremappedidentitieswillchange; old97f316 ECOtargetsMUSTNOTbe reusedblindly.

## All status-AND input ancestry experiment live

**43708501996/ee9a693879374f500074f147f832e873d15825e4**, codex/ack-chip-status-input-bypass. Exactoriginal97f316 restored again (not18c51successor). Examine ABC735174...761075 AND4inputsA/B/C/D, followonlyunique internaldrivers whosemasters are authenticbuf1/2/4/8/16identitycells, stopatfirstnonbuffer; noDLYbypass,noinversions,noexternalports, bounded32levels. Reconnectonlythese1..4sinks toancestralnets, preserveallothermasters/incidence/counts. PinnednativefunctionaldefinitionsverifiedforALLfivebufstrengths. Nativeplanreportstatus-bypass-plan.rpt recordsold/newnetsandactualchains. Measureall778targets/global3corners. Artifactack-chip-status-inputs-derived/native; finalstate run/4-nssoc-sizedfast. NoacceptanceuntilactualsetupANDholdreportsreviewed.

## PLL native publication complete; actual current analysis running

43703613123/90c1662b6d2597d85fdd171ff3e91deaf4825e7f nowcompletedSUCCESS. Nativeartifact **14158584796**,16234712683bytes,SHA **b81ffadd164a3b81d2550041276fb33300746d0735f93c86e7c6c6d5b21b45f9**, stayscloud. Derived14159376096 unchanged. Reconstruction43708067466/1a2db89a1a11c0f311694f97d9ed8dcf1dcda104 active, notanothertransient. Hold43708228938/4c2f65da2aae34d7e3116ba8edcca84a9c93e21f stillactive atlastpoll. FullPHY/production/finaltiming remainsopen.

## PLL130ns noninvasive current capture passed; reconstruction queued

43703613123/90c1662b6d2597d85fdd171ff3e91deaf4825e7f nativecommand finished and derivedresultPASS130NS_ORIGINAL131_BIT_PREFIX_WITH110_CURRENT_CHARGE_QUERIES. Derived14159376096 SHA7c41c46d59205b5ea01d3536c4ce1952bb6d7216ffba699f3a5e067daa0ea49e. Actual419392rows5216cols, raw37ca78285805c3cbf8538c75223501cbdfcfc30013ee2d8f19892b56b8b62cf2, original131columns first416191rows(strictlybefore130ns)bitidentical;onebitmutantrejected;sourceunchanged. 131nsendpointguard, not1usacquisition orfull5106equivalence. Native17GBartifactupload stillliveatlastpoll; donotrestartsimulation. Receipt docs/evidence/pll-130ns-current-prefix-result-20261115.json.

**43708067466/1a2db89a1a11c0f311694f97d9ed8dcf1dcda104**, codex/pll-actual-boundary-currents, live. Worker analyze_pll_boundary_currents.py waitsactualproducerpublication up to90min (45secpoll), thenrequiresoriginalrun/head/conclusionsuccess anduniquenativeartifact beforeauthenticatedcloudonlydownload. FreesonlyunusedSDKsonephemeralhost; requiresZIP+rawspace. VerifiesnativeZIPdigest/rawSHA/header419392x5216,exact21boundary/54passiveorientationrecords from43700489696. Reconstructs28C/B/E/Sports for391/392/393/394/395/396/400; preservesnativeicseparately; KCLresidualsreportedNOTassertedsafe. Original26anomalyintervals andeventbracketingrowsauthenticated. Retainsallnative110queries+21terminalVs+time and28reconstructedcurrents incompactNPZ(about0.5GB), allnativecloud. Artifacts pll-boundary-current-derived/native-RUN; reviewdiagnostics beforeclaimingcompleteportsemantics/safety. No newnative transient.

## PCIe status branch trial measured, not final timing

43706430499/b57d33515715591c62adc9ba328f65920db21b04 PASSmeasurement. Derived14158494071 SHA6c849803759fbf88816a5d92c318bd4b359c4c167a1cdbba02edbb78f97d7bcd;native14159226547 SHA4eea09045654812514fb8d6ff5c5908b53423bf581bfb862b06b3eae4e421979. Candidate18c51ccf43c67eb40ee96f067240242ed87d02c0baa65c4101be619fc792c8b0. Original97f316 source, oneAND4/D movedbefore3buffers, allotherincidenceunchanged. GlobalsetupWS slow/typ/fast -2.2579/-.256646/+.77169ns;count2720/25/0 (oneadditional slowviolation); hold1/17/254 unchanged. Statusportitself slow-2.000434vs-2.235730,typ-.256646vs-.351183,fast+.771690vs+.755945. NewworstportstartFF343800, otherinputs nowlimiting; minportmargin2.550/1.652/1.148ns unchanged. Receipt docs/evidence/ack-chip-status-branch-result-20261115.json. Notpromoted; measureotherAND4inputs beforeassumingonepathrepairsolveswholeport.

## Hold native pin binding correction

43707520309/5680fc203d49785f1d33444d6e4b403a09bd5500 failedpreflight forflattenedtarget228; no ECO started. Stringescapenormalization againstODBinstance names wasinsufficient. Derived14159730356 SHAba68820dfd69c1a2712fddc41ab8d6876caf859ce73bca32263e8b299d613551;native14159027569 SHAc8bd3537ac0ced401f32b5901f0e5d5a54018fa066b50b152184ca5206bb9709.

Current **43708228938/4c2f65da2aae34d7e3116ba8edcca84a9c93e21f**, sameholdbranch. Enumeratesget_pins/get_full_name withsameexactSTAlookup provenby778measurement, requiresuniqueobjectthen usesnative sta::sta_to_db_pin toobtain dbITermdirectly. Runtimecommandexistence/INPUTrole/expectedmasterrequired, preflightsall254beforemutation. Original267delays/headroom/portnets/placementguards unchanged. This usesdocumented nativebridge (OpenROAD src/dbSta/src/dbSta.i sta_to_db_pin), avoidsguessingphysicalnames. Await actualresult.

FullRXqualification43707359187/d7719ea5449f3c61102f9a633692beaa19aa66be remainslive formaljob132791216269 andtraffic132791216392. No newRXintegrated oroldphysical ECO reusedonfuturemappedIDs.

## RX per-input path benefit proven in isolated STA; full qualification live

43707089634/6d133f9b1448c51c5e6be0bb6222c4901232cf49 PASS, artifact14159455175 SHA7aa06454c17ac458a95d60939776d15386be8c20c779902e27b8b91dc34862bf. Receipt docs/evidence/rx-dllp-per-input-sta-20261115.json. At CW6 (default MAX_TLP_DWORDS8 givesCAP38,CW6), output_index[0] arrival slow .965329->.606977ns,typ .603685->.378606,fast .395824->.252304. Slow worstlength-input .920053->1.238326ns (regression). AtCW8 index0 saves.388092ns butlengthalso slower. Overallisolatedcone-worse result didnot imply everyinputworse; candidate may help actualindex-start criticalpath. This isNOTchipgain; mustmeasurelengthpathsafterintegration.

Fullmodule qualification **43707359187/d7719ea5449f3c61102f9a633692beaa19aa66be**, branch codex/rx-dllp-full-qualification. ExactRXsource865d687a272faf4a5077f79af21ace3b4afbe5085b640dd20f3512c8a43ff7d5 unchanged. Formalcommonflags READ2,RESET_COPIES,COMMIT_COPIES,CURSOR_LOCAL_RESET,LOCAL_LANE_NEXT inboth modules; gateadds ONLY DLLP_LAST_COMPARE. Existingequalresetcopycontract appliedboth, allotherinputs unconstrained. Parameters(dw4,slots1),(dw8,slots2), actualconditionalcompare inverted innegativecontrol. Trafficeightseeds x300k, completer/requester andsmallerparam, sameactualcomparison mutant; baseline defaultRTL. Addedmacro toshellwhitelist; nativevvp failurecode preserved evenifPASStext, rejectsFATAL/ERROR/MISMATCH. Workers qualify_rx_dllp_full_formal.py/qualify_rx_dllp_full_traffic.py. Twoartifacts rx-dllp-full-formal/traffic-RUN. No newRTLmainchipintegration orapprovalreuse untiltheseactualresultsverified.

## Hold physical-name preflight correction

43707023571/79757815ebec75ca9e46f43a1ba1b5d1a357134d passed inputporttarget166, then failedbeforecandidatepublication attarget228 flattenedreadbankand3input. Actualsourcepin '$flatten' prefix hasfourreportbackslashes; priorPythononcecollapse stilldidnotmatchODB. Derived14158792441 SHA7f98443cec0cdaf9e3d8d87f2cebe4c0857e9eeb003d6b7935026dc07a4efadf; native14159520343 SHAa4688665972631adc7f52234b492861d2c989cb49147bcefb058b01d566ecebd. No partialECO promoted.

Current **43707520309/5680fc203d49785f1d33444d6e4b403a09bd5500**, sameholdbranch. Nativehelper tests literal reportname andsuccessive doublebackslashcollapse against findInst; requires EXACTLYONEphysicalmatch, sameexpectedmaster/inputpin. PreflightsALL254targetnames BEFOREanymutation, thenusesresolvedinstance. Keeps original267delays, measuredallcornerheadroom, exact1inputportor1internaldriverguards and allotherincidence/externalportnets/placements. No wildcardmatching oromittedtargets. Await actualresult.

Statusbranch43706430499/b57d33515715591c62adc9ba328f65920db21b04 andPLL130ns43703613123/90c1662b6d2597d85fdd171ff3e91deaf4825e7f remainlive. Scope remains fullPHY/mainchip/routing/allcornerfinaltiming/production; diagnostic passes arenotacceptance.

## Hold repair controller fixes and additional PHY diagnosis

Original hold run43706172494/227ee398324dbf6d4ea65d95e8a5e8fe0e911b6f failed BEFORE native flow: Python tuples in path pins compared to JSON lists. Both serialized254path/778target bindings were verified exactly equal. Derived14158830365 SHA95b9909f0df192c3ebc23bd39009ca3dd3bcd9a2828d3694c42d183cadda6a0b; native14158302929 SHAb917e048addd96a4241ca305a0cf9131c7cfb6a62139968df6b359a8191ba592. Normalize only representation via json.loads(json.dumps(paths)).

Fix434a5bf773310bcfd41bd99fa917be3e0848838e run43706586173 then failedduringECO beforepublishedcandidate at target166 hold23910/A. This actualtarget has sole INPUT driver pcie_rx_dllp_i, notinternalITermdriver; setupheadroom2.055521ns,hold-.026290ns. Derived14159200221 SHA62bf836e1019e2efacd2dab4d44605fdb5e6ad8520fa2c37865a8037daab08cf;native14158198952 SHAec169f6944310c1c461c4043b18469232ffbeb2c846ba516ef453cacebeef46c. Partialin-memoryECO is NOTacceptedcandidate.

Current **43707023571/79757815ebec75ca9e46f43a1ba1b5d1a357134d**, sameholdbranch, restarts exactoriginal97f316. Insertion permits either1nativeoutputdriver/noBTerm or1INPUT BTerm matching observedsource/nointernaldrivers. Everyexternalportnet saved andrequiredunchanged; no ambiguity, clock/IOconstraintchange oroutputportexception. Original254targets/267delays and allsetupguards unchanged. Awaitnativepostrepairmeasurement.

PHY43706669496/62fd47ca9e384e99c2c4144428302b7cce26fc86 read-onlyPASS, artifact14159060181 SHAc42530ff809b620026df7039ffc6f1d7d5bac771a54b659c3c3468ce2d3a4d61. FrozenidealPWL and original10ohm series sources reconstruct CP/CN peakcurrent26.393/26.194mA and RMS11.244/11.089mA, maxdrop263.929/261.937mV. Actualsampler-input vscomparator same-time tables include wrongsigns evenwheninputmagnitudes>=100mV, BUT propagation/settling history notcontrolled; cannotclaimisolatedXORBooleanerror/inversion. Keeporiginalbitphasegate. Receipt docs/evidence/current650-drive-truth-20261115.json. Nextusephysicaltopology and quantifiedclockdrive todesign changes, not idealizeinputimpedanceorremoveoutputloads.

RX DLLP comparator prioralgebra candidatehadworseoverallcone butactualcriticalstartis output_index[0], so measureseparateinputpaths beforediscardingpotentialcarry-relocation. Newisolated workflowbranch codex/rx-dllp-input-path-measurement retains14widthproofs/mutants/pinnedPDK/18mappedcones, addsperinputOpenSTA reports withbuf2driver10fFload/virtual10nsclock. FirsttreeAPItimeoutmadeNOref/dispatch; contentsAPIretry produced93c4980cecd223131c186ee5780d1bac1b8b0e95 run43706905555. Failedonunsupported-group_path_count inUbuntuOpenSTA2.0.17; artifact14158599331 SHAea46013b1e071a261d2b28e06b4301afc385a4ce294c6427dacef847cc9bbd8a. Removedonlyunsupportedoption (singleoutput/groupdefault). Current **43707089634/6d133f9b1448c51c5e6be0bb6222c4901232cf49**. No newRXRTL integrated. Source865d687a272faf4a5077f79af21ace3b4afbe5085b640dd20f3512c8a43ff7d5. Outputout-rx-dllp-compare/per-input-sta.json; artifactrx-dllp-input-paths-RUN. ThisOpenSTAisolatedmeasurementNOTchipOpenROADsignoff.

Status-branch43706430499 andPLL130ns43703613123 remainliveatlastpoll. FullPHY,mainchipintegration/routing/finaltiming stillopen.

## Actual new-chip hold repair and status-branch setup experiment dispatched

Readonly778target run43704514831/1733c2ce4e780c0fef02e3c32cd38cb26f63384f completed successfully. Derived14158067560 SHA bdb1030257c058024fb03a5acbffa39b57d934b31851bb01f573d43f799e908d; native14158322169 SHA5ef517a5be5a0afda15fb4e7e9a222d442d1144539c7d7c1293bd4c64ad9cff1. Exact97f316ODB unchanged. Each branch report can contain multiple path groups; take minimum across ALL returned slacks, not only first path.

Hold repair **43706172494/227ee398324dbf6d4ea65d95e8a5e8fe0e911b6f** live, codex/ack-chip-measured-hold-repair. Restores exact original97f316 (NOT seven-buffer successor). Reproduces/authenticates complete778 reports, selects latest safe input on each negativehold path. All254unique targets have >=1ns allcorner setup headroom per proposed delay;13worsthold<-150ps use2delay,241use1 =>267 sg13g2_dlygate4sd3_1. No uncovered reportedpath. Native flow guardsmasters, one driver, noBTerms, exacttargetchanges/counts, otherincidence and originalplacements. Reports all778targets+globalfresh3corners. Scripts repair_ack_chip_hold.py and ack_chip_hold_repair_flow.py. Artifacts ack-chip-hold-derived/native; candidate run/4-nssoc-holdfast/state_out.json. Await result before claimingzero hold; new violations can emerge.

Seven-buffer experiment43704930454/3cd426a6244a9cfa423f36af5afe1be52711c8cd completed. Derived14158209200 SHA7a5479f1e9a7285f435d94e41776332133062a1913098fdcab7651267576ca15; native14158234215 SHA0aab5da123a3be174a30d1e0e4da4650e98fedd61882cee8c6f6ea31be06d97d. CandidateODB c4d3fff0f3967cfcfdd6d208d4ca1effaf377362dc7b18d9f089725c9fd0469a. SlowWS -2.23573ns vs-2.2579, slowTNS-2963.36vs-2980.9, setupcounts unchanged2719/25/0;holdunchanged1/17/254;cap0,slew16/4/3. Smallgain, NOTsignoff or selectedintegration. Receipt docs/evidence/ack-chip-seven-buffer-result-20261115.json.

New setup trial **43706430499/b57d33515715591c62adc9ba328f65920db21b04**, codex/ack-chip-status-branch-bypass. On original97f316, move only ABC735174...761075/D (and4_2) from fanout6459/X to ABC735174...749641/X (and2_2). Guards actualthreebuf4 chain: fanout7544 ->ABC761074 ->fanout6459; independently authenticates pinnedIHPbuf4 X=A definition. Preserves allotherpinincidence/cellmasters. This removes3bufstages ONLY for statusANDinput; doesnotremovebuffersorchangeotherloads/gates. FullSTA may reveal increasedupstreamload orholdregression; awaitmeasurement. Worker repair_ack_chip_status_branch.py/ack_chip_status_branch_flow.py; artifacts ack-chip-status-derived/native. Internal flowIDs stillSizedSlow/Typical/Fast; finalrun/4-nssoc-sizedfast/state_out.json. Parenthassevenexperimentfilesbutnewworker restoresoriginal97f316, doesNOTapplysevenresize.

## Actual PHY stage mapping identifies clock switch headroom

43705887967/0ff49d674e0fe0dbf076763ccd4c88036bc438da read-only diagnosticPASS. Artifact14158622153 SHAa5ff9e5ccebeebf014e162ae5510ebe9a34f8377f1b315bf37af76f30a5d73b3. Exactcontract6095d786d9ba65d967c7029b0753ef8f4316dcfb463a5aacb801565a90d5fad1 matchednativearchive. HBT211/212 are both CN-driven Dsampler master sampling switches: B=cn,C=sd_m_se,E=sd_m_te,Nx2, legacy61/62.32clock-base observations cross15.156..17.656ps afterideal sourceedge withnomissingcrossing across248cycles. These are localbase-relative-to-source-commonmode crossings, not directdifferentialpair propagation nor fullPHYqualification. Receipt docs/evidence/current650-stage-clock-map-20261115.json. Artifact has124HBTlogical/physicalvoltagecontexts and98resistorlogicalbindings fornextcircuitdesign. FullPHYstillfailsoriginalsample/phase/headroomgates.

PLL130ns43703613123 stilllive. No duplicate native transient or uncontrolled sourcechange. Allworkcloud, no CAD/source artifactsleftlocal.

## Current650 read-only failure localization completed

43705504612 / c7f2e37792525b4ad45abb1474dec6299ea7576e PASS_DIAGNOSTIC only. Artifact14157553316 SHA98dd50bc56b195de5f1c90dc5fec0d47bf9efd202d34340c236d5e622391d36e. Exact original failed native waveform and all six original sample failure counts reproduced; circuit acceptance remains false. Receipt docs/evidence/current650-loaded-localization-20261115.json.

Sampler A129/B128/D128 below100mV observations occur ONLY at0.3UI (37.5ps) after sampleedge. C128 at0.3UI plus16 at0.9UI; X and Y failures span all measured phases. A failures only source transitions; B/C/D include unchanged previous/current data, so cannot attribute all failure to input-transition settling. Detailed perbit previous/current data, physical data/select differentials and sourceclock context retained in artifact sampling-localization.json. Native HBT211/212 both worstVCE at20.81421875ns, row68871; .396984/.395426V,325/658violatingrows. This diagnoses headroom, not fullterminalcurrent equivalence or complete rootcause. Do not relax37.5ps/100mV/.4V/30mV gates or change expectedbit alignment to pass.

Next analog task: map failing HBT pair and sampler data/select paths back to current650 physical graph, quantify clock/input/output settling delay before choosing circuit change; keep widened clock-only geometry experiment rejected. Timing newchip778reports, seven-buffer sizing, and PLL130ns capture are still active atlastpoll. FullPHY/finaltiming stillopen.

## Current650 loaded case rejected; native failure localization and new-chip sizing live

Actual loaded producer 43697553951 / 30d59883a29c0c64f5855884a26aeb39783900ae completed native simulation (return 0, no diagnostics, sources unchanged) but FAILED electrical gates. This is not an observation timeout. Derived artifact 14157917034 SHA4f428b30a1a757556c425e5abddf4a3cf1ad1ca1af4d4e68ad486d69632bd854; native 14158082074 SHA1f6167012365bc7bffcc85bad084d0824021ec6d1c963d1dc3a5537f22b114c3 (3.45GB, stays cloud). Exact receipt docs/evidence/current650-loaded-rejection-20261115.json.

Phase18.4019mV <30mV. Sampler A/B/C/D wrong-sign32/0/64/76 out of765 each; X/Y384/20. A/B settling50.156/47.031ps >37.5ps. HBT211/212 minimumVCE .396984/.395426V <.4V. VI passed53.098uA/15.040mV. Current clock-metal geometry did NOT resolve electrical failures; no fullPHY or mainchip acceptance. Native raw113490rows1752cols SHAfb95656a71a54217d4b7215571b5d8ac48513d0f17fd8736dd526b744125aa3a.

Read-only localization **43705504612 / c7f2e37792525b4ad45abb1474dec6299ea7576e**, branch codex/current650-loaded-failure-localization. Restores authenticated native only in cloud; reproduces original six sampler/comparison counts exactly; records failure sample bit transitions, data/select/clock context and native lowVCE timestamps. No circuit or gate changes, no new native transient. Worker scripts/localize_loaded650_failure.py; artifact loaded650-localization-RUN. Await actual result before choosing next analog change.

New-chip sizing **43704930454 / 3cd426a6244a9cfa423f36af5afe1be52711c8cd**, branch codex/ack-chip-seven-buffer-sizing, still live. Uses exact97f316 postCTS sourceODB. Replaces fanout3516/3514/3513 buf4->buf8, fanout2832/2411 and ABC735174...760989/760990 buf1->buf4; guards original masters, complete instance census and all pin-net incidence. SevenBufferECO followed by three fresh778targetSTA reports; output ack-chip-branches; artifact ack-chip-sized-derived/native. NewODB and fresh final state run/4-nssoc-sizedfast/state_out.json required. Setup AND hold must be compared before promotion; no final acceptance.

Read-only unsized778target run43704514831 /1733c2ce4e780c0fef02e3c32cd38cb26f63384f and PLL131ns capture/130ns exactprefix43703613123 /90c1662b6d2597d85fdd171ff3e91deaf4825e7f remain in progress. No duplicate producer launched. Original clocks/derating and electrical gates preserved; fullPHY, mainchip routing and finaltiming remain open.

## NewACK branch measurement controller repairs; RX compare experiment remains isolated

Original43703506723/de5f493d025a1768cde3e9320532960592d9bdc7 failed BEFORE STA: missing ack-chip-branches/run directory. Addedmkdir in8b68c8aff1482db7bb692b3d93e63f1085e05d63, rerun43703972790 then reached nativeSTA but failed on escaped flattenedpin $flatten\\u_pcie.receive_ownership.read_bank[2].pick_copy.../A. Actual778targets selected. Derivedfailedartifact14157836594 SHAdf85a1de02e5657f9c24c877b4a5c133cdcf89a7b1af5d55d7f55e6470cfcba5; native14158116058 SHAeda0e6881cfff81fe4852714c1ef6f1a346e9e0ff9cf465503d0a2ce5c5b9fab. No changedphysicalcandidate produced.

**43704514831/1733c2ce4e780c0fef02e3c32cd38cb26f63384f** live codex/ack-chip-measured-branches. Flow now enumerates actual STA pins/ports with get_full_name and exact dictionary lookup; accepts unique raw/report-unescaped alias, rejects missing/ambiguousname. Avoids get_pins wildcard escape interpretation. Still exact97f316ODB, readonly778pin/port allcorner reports. Previouspartialreports not finalcomplete measurement; awaitthisrun.

New critical RX path includes out_eop_o expression output_index+1==CW'(dllp_length). Experimentalbranch codex/rx-dllp-last-compare replaces only enabled SOC_PCIE_RX_DLLP_LAST_COMPARE expression with index==lengthminusone, preserving originalexpressionforCW<3. Initial54690368aff39b373ff4eebc8b018a9c72f00043 run43703924946 failedCW2formal. Diagnostic5b2ce124ad7c39856572784a575903c9edb37684 run43704073170 showedONLYCW2mismatch;CW3..32passed. Artifact14157906036 SHA4105ced6f9f6f899e41f175de8d6d233d8d66678db870f88102c39a9507fe200. Corrected narrowwidthfallback in3d1dab9f15cf10faa433fc6f95aaa9b7a40ae968, run43704240375 passed14widths(1,2,3,4,5,6,7,8,9,10,12,16,24,32) andzero-wrap mutants forwidth>3. Artifact14158340555 SHA3bbf7f8b726e032c5aa6ce75b71c39e41c7ae2194644f6047f7fa9d14e9a0417.

However isolatedmappedEOPcone slow/typ/fast ps forCW6 original889.17/559.80/367.85 vs candidate1014.82/644.47/424.78; CW8 and10also worse worstconedelay. NO mainchipintegration orfullmodulequalification initiated. Possible per-input path shift is not yet measured; do not infer actualchipgain from algebra. Existing actualnewchip remains unchanged. Useful regression scripts: priorqualifiedRX fullmoduleformal/8seedtraffic in7b3d47cd6bd0666f035f6c231f5edefb705ca1c6 scripts/qualify_rx_cursor_formal.py andqualify_rx_cursor_traffic.py; check_pcie_rx_read_ahead.sh whitelist needsnewmacro if laterqualified. All require actualnewsourcebinding, not old2a345hash approval.

LongloadedPHY43697553951 and PLL130ns43703613123 remainlive atlastpoll. No nativeprocess restarted due observationtimeout. FullPHY/finaltiming stillopen.

## Fresh ACK mainchip postCTS measured, branch-margin diagnosis live

**43700966904/de22dcaec98353379bd970648f0b97a59b767246 completed** and authenticated native-derived reports inspected. Native14157198878 SHA9d6c9e73416ec8783b2e3ae558c409266f3733f6e4864bd4368d85ee8842feb9;derived14156558964 SHA43c92ec5528353be0ae288cc813e405d47d351c1ca21195d0e60d03d1f979850. New repairedODB97f3161d2f6c36a062f9db94cad37d175282b981a8b4060306f6f6c32d0ff6e9, run/5-openroad-resizertimingpostcts/state_out.json. After slow/typ/fast:setup2719/25/0,WS-2.2579/-.351183/+.755945ns,TNS-2980.9/-.680359/0; hold1/17/254,WS-.19365/-.242284/-.248552ns;slow/typ internalhold0,fastinternal214. Slew16/4/3,cap0. Sourcesunchanged, allclocks/5percentderate unchanged, notrouted/boot/fullPHYacceptance. Receipt docs/evidence/ack-prefix-new-chip-postcts-20261115.json.

Criticalslowpath now FF175663(output_index[0]) through rx_eop_i to receive_ownership.read_bank[2].pick_copy.FF551884, rather than old ACK arithmetic. Worstholdpcie_training_i->FF183590(-.248552ns); Ethernetoutputeth_txd_o[4](-.218474ns),[1](-.215055ns). Do not reuse old735036 cellIDs; newmapper735174 and flattened hierarchy differ. Newchip improves worstsetup andtypcount but slowsetupcount/TNS increases; not yet selected as finalwinner.

**43703506723/de5f493d025a1768cde3e9320532960592d9bdc7**, codex/ack-chip-measured-branches, live read-only3corner measurements on actual97f316 ODB. Restores actualnewCTS andpostCTSchain. Selects first/last2data-input alternatives for allreportednegativeholdpaths, allinputsontop10violatingsetuppathspercorner, andnegativeoutputports. Captures max/min report for eachactualpin/port, unchangedODB. Worker scripts/measure_ack_chip_branches.py;flow ack_chip_branches_flow.py;output ack-chip-branches;artifacts ack-chip-branches-derived/native. Use exact measuredheadroom to choose nextECO, no speculativeblanketdelays.

## PLL observer4ns prefix proven; actual130ns diagnostic live

**43702980812/5a68451b6301db6e955474c024d8ae413b7fae90 PASS**, actual4.1ns13138row5216column capture, original0–4ns12817rows/131columns bitidentical, one-bitmutant rejected, originalsourcesunchanged. Raw0eb5046de9f36998382634a74e4e5838eb58010e35c7320c8b41aefdf6a3e292. Derived14157024254 SHA011ec6005e17b3ccc36505cdb9d3f041b43c4123af16f37b0a6bb5a2a6f4ac61;native14157099181 SHAea287977bd08b8be795aec577b3857830fe9e945f34e19334b5199309afb068d. Previous4ns-terminal-row failure retained; comparison criterion not weakened, endpoint movedoutsideit. This qualifies short sharedprefix only, NOT fullPLL/currentsemantics/safety/acquisition.

**43703613123/90c1662b6d2597d85fdd171ff3e91deaf4825e7f**, codex/pll-current-prefix130ns live. Authenticates successfulshortpilot before preparation. Original845+4PLL/102OFF/solver/model/loads, extra110queries; separate131nsendpoint, exactallold131columns/times strictlybefore130ns required. Native current131ns.raw expected~17GB stayscloud. Worker scripts/pll_current_prefix130ns.py; output/artifacts pll-current-prefix130ns-derived/native. Maxnative300min/workflow355min. No acceptance ifprefixdiverges; nointerpolation orretiming. On pass reconstruct actualC/B/E from54nativepassiveboundarycurrentrecords andsubstratefromRsub/Csub, inspect sevenfirstlatchdevices391/392/393/394/395/396/400 during26anomalies76–117ns plusstartup1.84ns. Existing aggregate/currentqueries mustnotbe mislabeledcompleteports withoutthisphysicalboundaryanalysis. Full1usacquisition andfullPHYremainopen. Loadedcurrent65043697553951 stilllive atlastpoll.

## PLL difference localized to terminal step; exact4ns guard trial

43702605947/3b440a880d833eb3ff5da5e46622781390660996 completed read-only localization. Artifact14157450696 SHA9090b865805a825f541df9f928852cf4dd47358b568c0504f915c4cb2946eec4. Exactly127differingvalues in127columns, ALL atrow12816 (last row before4ns). First12816rows/131columns bit-identical. Reference time3.999843750000193e-9 vs diagnostic3.999765625000096e-9 (78.125fs earlier). Endpoint timestep adjustment is a hypothesis, not proven cause. Original4ns gate stays rejected.

**43702980812/5a68451b6301db6e955474c024d8ae413b7fae90**, codex/pll-current-prefix-guard live: identical0–4ns bitcomparison12817rows, but simulate4.1ns to keep endpoint effects beyond comparison window. Nothing is interpolated/excluded/tolerance-relaxed. Worker scripts/pll_current_prefix_guard.py; native current4p1ns.raw; artifacts pll-current-prefix-guard-derived/native. Await actual gate. Original1us acquisition remains unaccepted. If pass, consider analogous131ns capture for exact0–130ns comparison before original latch76–117ns diagnosis; do not shorten comparison window to hide differences.

ACK full-delta equivalence43702510353/bf9174bec693aa4b9cb4363753719bd94205ba4f PASS: twoall24bit equivalences,4mutantsrejected,6x300ktrafficpasses;artifact14156274320 SHAb4e6aad27adf822a80a9da265669756a8840da21192d8ac996b4296a25248c3d. Still REJECTED forintegration due prior measured timing regression.

Additional isolated borrow topology comparison43703055528/b9f6f8dc7e2ded60f4e9353b2097048e3830ab21 PASSmeasurement only, artifact14156839492 SHAc0bf1a459296ab45725aec8cfbd53bb7fade41ec54f664ce293c253cd93bb567. Allfourfull-delta expressions formallyequivalent over2^24pairs. All share stale-prefix classifier and exact loads/libs. Slow/typ/fastps: original2151.22/1370.64/905.56; group3 2275.13/1453.50/957.20; flatborrow2369.79/1515.75/1012.73; prefix-tree2467.71/1575.42/1042.69. Keep existing stale-only candidate; none of these experiments merits mainchip synthesis. NativepostCTS43700966904 and loadedPHY43697553951 stilllive at lastpoll.

## Full ACK delta candidate rejected on isolated mapped timing

43702685646/cdcb36214815b0941002e06b9b780a7a22068636 completed; artifact14157435974 SHA7d1bf70ca7793584a1626c397c25dac2fcb1773128495083238391ca0056fa05 authenticated and result inspected. ABC slow/typ/fast ps: original2593.46/1664.38/1095.69; stale-only2151.22/1370.64/905.56; full-delta3bit-group candidate2275.13/1453.50/957.20. Full-delta area910.7154 slow versus850.9158 stale-only. Thus do NOT promote this full-delta variant into mainchip; it regresses allcorners versus ongoing stale-only chip. Its independent equivalence/traffic43702510353 was still running; preserve result as diagnostic, never claim mapped timing acceptance from equivalence. The full-delta source remains isolated experimental branch only. Mainchip43700966904 and loadedPHY43697553951, read-onlyPLL difference43702605947 remain in progress at latest observation.

## PLL prefix rejection retained; full ACK delta alternative under qualification

**43702129953/b6e44d8a8bb58ab639dcef52d1d4de3cfe7347ba FAILED** at exact131column prefix comparison after actual4ns native run. Original cache authenticated,12817rows strictlybefore4ns; reference prefixSHA f2a359fbedc10eebf8b0e8af8392a2e9bc0331bbd4bf844e3169435930d2f5d8. Do NOT relax equality or proceed130ns. Derived14156672470 SHA e89789a3f6beb52bb722a651fd0b019195f3983f7e7ae8af06b8d691459154d2; native14156199159 SHA 8cdd9bf7d0e92a3c59d0b141f5ab288326cb30a6cfea55a6e54cbadb2f6d83b8. The method has not proved noninvasiveness.

Read-only diagnosis **43702605947/3b440a880d833eb3ff5da5e46622781390660996**, codex/pll-current-prefix-difference, authenticates existing failed native capture and oldcache, reports first differing sample, per-columncounts/errors, and time-bit equality. NO simulation rerun. Await result before designing baseline4ns/no-extra-observer control if required. Original full acquisition remains failed.

Exact oldsetupmax report still traverses ACK sequence subtraction (source FF160646 ack_sequence[3], hold32906, arithmetic chain to FF164200). New ongoingACKchip43700966904 only optimizes stale classification; do not presume full closure. Additional optional RTL macro **SOC_PCIE_ACK_DELTA_PREFIX** computes all12delta bits with parallel3bit-group borrows, unchanged capture/handshake/latency. Experiment branch codex/pcie-ack-delta-prefix **bf9174bec693aa4b9cb4363753719bd94205ba4f**, qualification **43702510353**: all2^24 full-delta and stale equivalence,4mutants,6x300k fullreplaytraffic usingactual CRC/EOP/etc commondefines. Pending; not mapped/mainchip accepted.

Isolated identical-load3corner mapping comparison **43702685646/cdcb36214815b0941002e06b9b780a7a22068636**, codex/pcie-ack-delta-mapped, compares original/stale-only/full-delta shared delta+allowed+stale cone. PinnedPDK c4b8b4e, buf2driver10fF eachoutput. Worker scripts/measure_ack_delta_prefix.py. This is only ABC combinational timing, no routing/sequential/fullPHY proof. Do not integrate until qualification and measured benefit reviewed; fresh synthesis identities required for any eventual chip candidate.

## New measured hold result and PLL transient pilot

43701339119/6b9880503b0c5b9f3eea7f37afaf650c82f56070 completed. Candidate269cb4335730057ef617b10aa07eced703e1ae03dcfe56ae25d7d80f7fc16154, run/4-nssoc-combinedafterfast/state_out.json. All34targets>=50ps,35addedcells, hold0/0/0; globalfastminimum20.7873ps still below50ps. Setupslow2457/typ98/fast0; worst-2.71877/-.389342/+.683008ns; slew27/3/0cap0. No routed/final acceptance. Authenticated report and artifact bindings saved in docs/evidence/rx-lane-post174-repair-result-20261115.json. Historical selected_targets120 in producer is old lineage; actual measured_targets34 and new_cells35.

Native passive RC fixture43701736489/82f41e26ade16885ddf11649b1bb77049a603d83 PASS:2011rows7variables, maxRerror1.735e-18A,C-ramp1.089e-14A,C-hold0,KCL5.766e-15A; wrongsign/missingcap mutants rejected. Derived14157285577 SHA f75bae364a9f005177bf0fa6fd6341a45281cbf351b0c590b203567898fc4c1d; native14157380344 SHA df76b5571788a7956fee9a963b99c4c61c2638fee2fb9990848e5b11dcdeff26. Not PLL acquisition/full-current qualification.

Pilot 43702129953/b6e44d8a8bb58ab639dcef52d1d4de3cfe7347ba, codex/pll-current-prefix4ns, status in_progress at checkpoint. Actual845+4PLL, authenticated original131-column cache,110current/charge observations,5216expectedcolumns, all1694voltagevectors. Separate deck changes only1us->4ns endpoint; original protected unchanged. Bit-exact shared times/131values strictlybefore4ns required, one-bit mutant rejected. No long130ns dispatch until this pilot passes. Artifacts pll-current-prefix4ns-derived/native; worker scripts/pll_current_prefix4ns.py. All sources/captures cloud-only.

## Resumed live cloud work, 2026-11-15

All CAD and source changes remain cloud-only. Direct recheck confirms these native jobs are in progress; do not restart them or claim final acceptance:
- Post174 follow-up **43701339119 /6b9880503b0c5b9f3eea7f37afaf650c82f56070**, branch codex/rx-lane-post174-repair. Actual3b0afb ODB,34targets/35cells,31DLY+4small buffers; ABC736135/B uses two buffers. Exact original incidence/master/placement census guarded. Source reviewed after dispatch. Output combined-post174-repair-trial.
- Fresh ACK chip postCTS **43700966904 /de22dcaec98353379bd970648f0b97a59b767246**, codex/pcie-ack-prefix-postcts. Uses new CTS ODBc23108497dbbeeb5a71317688ced49f465ff24a9ae7c8fe3393d2d63287c8e3a from43699512862/2f3a58a584c3a5417bd5922a42cf994be7e90c32. Original20/4/8/8ns and5percent derating; fresh3corner metrics before/after native electrical/setup/hold repair; no old cell IDs. CTS placement is not routing or final timing acceptance.
- Loaded current650 PHY **43697553951 /30d59883a29c0c64f5855884a26aeb39783900ae** still executing complete256bit nominal_late case. No electrical acceptance yet.

Post174 read-only measurement43700042818/d1b65dacd823d2a09e6d11164640227c46fa26cb passed:35paths137pins. Derived14156406361 SHA5871ebb877266cdea737e3b77a5e8f4cd0472617f8c726be55396b0374d3a3e1. 31latest safe inputs cover32paths; only three previously thin branches remain. This measured result supplies the follow-up above, not an assumption of global50ps closure.

Native passive-current preflight43700761986/10d074aa1772113b01b07123b26a6a7ef58c836c passed OP accessor/coverage only:110queries,1694original voltage vectors retained,5215variables,3negative controls. Derived14156083787 SHA9419b6d4c39d1ce263ca2eb4571d8c7e061cd738f2d8ec0d30ae65901a7c320e; native14156317561 SHA0b6171402b3ce8b781f6404e8fa44c05375ea35a51f2d87a65c4c0c4b0f4d0a4. NOT dynamic current qualification or PLL acquisition.

Dispatched separate analytical RC transient fixture at **82f41e26ade16885ddf11649b1bb77049a603d83**, codex/pll-passive-dynamic-fixture (run 43701736489). Same frozen patched engine103134... and native Docker image restored. Checks actual signed resistor/capacitor currents against analytical ramp/hold and KCL, plus wrong-orientation/missing-capacitor negative controls. Does not alter/simulate PLL DUT. On pass, proceed to trajectory-preserving actual PLL capture; do not equate fixture pass with full nonlinear terminal-current validation. Worker scripts/pll_passive_dynamic_fixture.py; output pll-passive-dynamic-fixture.

Observed supplemental boot43691795620/91a4dea0322172b853b0450d153ebaefd380ee6f FAILED after4000096cycles, checks0 and no FW_PASS. Native log captures late PCc0000982/instruction0000006f and PCc0000984/instructionfe010113, cause3f, mtvecc000090X. Root cause unresolved; investigate exact ROM/address mapping and early trace before another unchanged4Mcycle run. Artifact14156540920 SHA8a9d21d6010b78eb1e2ac474fb76356d9d18e9de2eed3bc21a522f948eb02f2d. Zero-delay supplemental model is not SDF/native boot signoff.

## Six-cell result and noninvasive PLL terminal-current work

Six-cell experiment **43699804844 /efec998407e318e3c6c051e9cbb9a40dbae86bab completed**, derived14155659500 SHA2a8f8b655afd09a18f6b039b30f9276992aac7ceb58434e5063d659d07ce59d6; native14155669542 SHAbc6dc608a346202bd8e9bb38956fbf3d07391c5f5f79a492e06fce94a5d81f94. Candidate2a7edf718083509d71e2e773ac3e25f4fba058f5b366a55b7914070d477d3d81;state run/4-nssoc-combinedafterfast/state_out.json. Setup counts2458/98/0 and worstslacks unchanged. Five targets exceed50ps:ABC767397/A287.590ps,780629/A290.496ps,770542/A275.277ps,772540/B73.165ps,772710/B83.327ps. ABC736135/B only45.54246ps with620.401084ps worstsetup; an additional small buffer needs actual measurement. Do not mark all six accepted. This is on254b1e baseline, NOT combined with174 repair. Receipt docs/evidence/rx-lane-six-buffer-result-20261115.json. Await35-path measurements on3b0afb before combined selection.

PLL topology **43700489696 /ec300f1e8cfa04b84ce0e12d819f56551757590c PASS readback**: all21selected C/B/E nodes have unique attached HBT, no other device cards, complete54passive incidence records. Exact composedmodel02210e5fe8dce4c0fbda06de98d5651b5a894e6ad2d9b2f3e7bb83acf671b258. Derived14156446419 SHA90ae28c3fc79198c1594944707f6e3f47936ff64086328732e139111cd3bf54c; native14156546114 SHA44e348751cb8a4b3da7449c79e2336cc4b1c1729a29fbd7f8a75c747ff1d867f. This enables a proposed exact terminal-current observation from negative signed sum of EXISTING metal resistor/capacitor currents. Seven substrate terminals additionally use original internal Rsub/Csub currents with opposite sign (S1->BN). No ideal sensor/shunt or model change. Dynamic orientation/KCL and capture must still be qualified; topology alone is not electrical proof.

**Live43700761986 /10d074aa1772113b01b07123b26a6a7ef58c836c**, codex/pll-passive-current-preflight, extends exact-engine OP observer to these native R/C queries and seven Rsub/Csub pairs. Uses `save all` plus queries, verifies every original1694 voltage vector in actual native header, correct current/charge types, and3negative coverage controls (missing passive,wrong unit,missing original voltage). Original sources/102OFF retained. Scope remains OP accessor+coverage, NOT dynamic terminal-current/PLL/fullPHY acceptance. Output pll-passive-current-preflight; native original case archive retained separately.

## Actual174 repair result and new35-path measurement

**43698884172 /8efcfa852e866f4a0db100f3c5bda36a9e260c6d completed and artifacts inspected.** CandidateODB3b0afb4c09cd12fea658ad96bf4958385b4ef6270f03f619752b25b0decde780; state run/4-nssoc-combinedafterfast/state_out.json. Derived14156430096 SHA098fdc23f1ca7bd164862758d12bab3331282ef8176c83f5cee84c62d67868db; native14155663198 SHA5bbb8f2d04216d0e2284e2c576b6b04779d4c9c382b49445059daa7e2b0350b2. Native archive is RUN CONTENTS and must restore under ROOT/combined-nearzero-repair/run to retain absolute state paths. Sources unchanged,174target+boundary margins>=50ps,globalhold0/0/0. Slow/typ/fastsetup2458/98/0,WS-2.71877/-.389342/+.683008ns unchanged; slew27/3/0,cap0unchanged. Globalfastholdminimum improves .000544009->.00741174ns, NOT global50ps closure. SlowTNS-2722.2->-2722ns;typTNS unchanged.

Actual same-global-report scan finds35paths/35distinct endpoints below50ps, down from189. This is limited to reported paths, not an exhaustive path census. WorstnewpathFF326753->FF1658357.412ps; other short paths emerge after shared loading changes. See docs/evidence/rx-lane-174-hold-margin-result-20261115.json for all35exactstarts/endpoints and metrics. Never assume174selected margins prove every path repaired.

**Live43700042818 /d1b65dacd823d2a09e6d11164640227c46fa26cb**, codex/rx-lane-post174-margin: authenticates actual3b0afb candidate, every restored native file and source min reports; selects ALL data-input alternatives on those35paths; reads all3corners+40boundaryports without modifyingODB. Output combined-post174-margin-trial; artifacts rx-lane-combined-post174-margin-derived/native. Use resulting actual setup headroom for next repair, not old254b1e margins. Independent six-cell candidate43699804844 is still measured on old254b1e, so eventual combined use requires remeasurement.

## Six-path native buffer experiment live; PLL query limits confirmed

**43699804844 /efec998407e318e3c6c051e9cbb9a40dbae86bab**, branch codex/rx-lane-six-margin-repair, evaluates all six excluded near-zero paths on unchanged254b1e baseline. Actual measured23-pin/all-corner artifact14154434169 is authenticated. Inserts sg13g2_dlygate4sd3_1 at ABC767397/A,ABC780629/A,ABC770542/A (setup>2.6ns); inserts smaller native sg13g2_buf_1 at ABC736135/B,ABC772540/B,ABC772710/B (setup0.7068/0.4147/0.4431ns). Both native Verilog buf(X,A) identities authenticated. Original instance masters/incidence/locations/orientations guarded, six new cells/nets only. The .4ns small-buffer selection screen is an experimental headroom guard, NOT a relaxed final setup/hold gate. Keep all original clocks/derating. Measure full global and target STA; this is not an accepted repair until actual results and eventual combined candidate are checked. Output combined-six-repair, artifact rx-lane-combined-six-repair-derived/native. Pre-CAD source/output contract retained to prevent prior publication-path mistake.

PLL source/native OP inspection additionally established: exact frozen model has nonzero cbeo=8e-16*(Nx*.25)^.975 and cbco=2.36e-15*(Nx*.25). vbicask's ic/ib/ie/is combine stored internal states; vbicload adds some charge derivatives but treats outer qbeo/qbco separately. Therefore these native queries are NOT qualified complete macro-terminal currents or conduction-only currents. Actual seven native show readbacks have area=1,m=1,OFF=1; some unrelated show-all fields (dtemp/internal node aliases) return unsupported-query error7/NAN. The42 requested current/charge outputs themselves are finite and typed. Do not report all show-all fields valid or substitute Nx multiplication. Next dynamic instrumentation must handle omitted branch currents and verify original voltage capture; no guessed shunts, model tweaks, or electrical acceptance.

## ACK mapping accepted as an experimental input; fresh physical implementation dispatched

Recovery **43699207988 /eedc4f64900475d70dd5785a6f5d72276748d4b6 PASS**, actual mapping report inspected:116356cells,20SRAM(16dual-port256x16+4single-port2048x64),ACK prefix/CRC select/RX optimizations and one EOP cache register verified. 60 original failed-producer native files unchanged;63 authenticated outputs including3 newly generated origin/lowering records. Native14156046025 SHA0673859fcc942f17f6c21acca0eeb65fe19be554115fa9277c09494a903ab8c1; mapping14155786846 SHA38311da36470a6e321ba9942d56b8fa924b011140d84eba9d37394a801aa9a00. MappedJSONa2705107c499532247633c1441af5b770d1ad5cf6991f0ebf7824390699b0254; netlist5ba01f27e98ee65c9ac6e9e30d0d1cd754e7c2b275efab7a70249ec3e35daca4. This validates mapped structure, NOT mapped boot/final timing/fullPHY.

**Live placement/CTS43699512862 /2f3a58a584c3a5417bd5922a42cf994be7e90c32**, branch codex/pcie-ack-prefix-placement. Uses actual recovered63-file input, exact immutable artifact IDs/digests, source hashes,20SRAM and116356cell census, original20/4/8/8ns clocks with5percent derating. Same proven old placement flow retargeted to actual new source; no old ODB/cell IDs reused. New gate-level boot remains separate and unaccepted. Output root hw/soc/out/cloud-predecode-chip-placement; artifacts ack-prefix-chip-placement-derived/native. Next use fresh CTS ODB for all-corner timing diagnosis and routing, never copy old cell selections.

## ACK mainchip mapping recovery, 2026-11-15

Original build **43696515079 /56f97b8744d2dcd92821a79a7dd63168aacefa9c terminal FAILED** after synthesis: check_predecode_mainchip_mapping.py still required old replay sourcea5891101... instead of formally/traffic-qualified ACK sourcef5634cd4.... It also omitted ACK_STALE_PREFIX from the exact enabled macro census. Native synthesis retained, not lost. Native artifact14155771240 SHA579b44b07e51c09207bc7c6d3f1e5182502737d91d8eabc0f06307a6d586aa4b (build.tgz); proof-gates artifact14155776313 SHA0d949776b606699a6c01caac8d588a33bdff8ced1c513271b54dbbf29d31247e; replay-regressions14155751386 SHA438ede4961cf72257cfb8d34014df0fc3feba6c07500618f24767abb1637c7fe. Mapping artifact originally has only RX/ACK proof gates, no mapping.json; do not claim old failed run passed.

**Live recovery43699207988 /eedc4f64900475d70dd5785a6f5d72276748d4b6**, branch codex/pcie-ack-prefix-mapping-recovery, restores those exact authenticated artifacts, checks new source and enabled ACK macro against Yosys synthesis input and ACK qualification, retains CRC/EOP/RX/predecode/SRAM checks. Re-runs only lowering/mapping validation, NOT synthesis. All original restored native files must remain byte unchanged. Report distinguishes synthesis_producer43696515079 from current validator source/run. Workflow preserves recovered native output and mapping evidence; old replay regression remains bound by original artifact. Original prepared script ran RTL firmware boot then synthesis before stale assertion; mapped boot and physical timing remain separate and unproven.

Next consume recovery result, then use its actual new mapped netlist/identities for a fresh chip implementation. Never transplant old254b1e cell IDs. Hold repair43698884172, observed CVCboot43691795620, loaded PHY43697553951 remain live at last direct poll.

## Exact PLL native OP accessor result

**43698755531 /636f4a54a66c0ecc01c8a3fe799565e16fa553b7 passed bounded accessor existence.** Derived14155955561 SHA57f41cc165d88dfc1dc52bb22ddea1033d91c16035d55f1770fa48df30eb09bd; native14155920694 SHAf602f0c42a06bc7f7b27e9ac41fd0fbcc21eb78c69fda0f4c6761e971ec65c6f. Actual engine/model/image restored, all102OFF flags read back, original inputs unchanged,42 finite queries. Native OP header has28current/14charge variables. See docs/evidence/pll-current-native-op-20261115.json.

CRITICAL next-capture requirement: this OP-only wrapper's extra `save` produces exactly42 variables, not the original voltage vectors. This is valid only for query-existence preflight. A future dynamic wrapper must explicitly preserve the original save set plus new queries and verify actual native full-column/header coverage and common131-column/time prefix. Do not infer original observation preservation from source-byte preservation. OP zero values do not prove scaling, transient semantics or complete macro-terminal KCL. Native query/model readback logs remain available; qualify Nx/m and query equations before130ns diagnostic, retain original1us acquisition requirements.

## 2026-11-15: repair publication fix, six-path results, actual PLL accessor probe

- **43697752210 /c5affedb31cd1b2e02d8234d073525a3be94f571 is terminal FAILURE.** Native ECO+STA command succeeded, but both uploads found no files: workflow collected combined-nearzero-repair-trial while actual driver wrote combined-nearzero-repair. No artifacts means NO verified timing improvement, no successor ODB. Corrected ONLY publication paths and added pre-CAD output-contract guard. **Replacement live43698884172 /8efcfa852e866f4a0db100f3c5bda36a9e260c6d**, same branch codex/rx-lane-nearzero-repair, unchanged native experiment. This is a genuine failed publication retry, not restart from observation timeout.
- Six-path read-only run **43697869651 /162c746d4cd214aee03ce421f1dd56d3438330f2 passed**. Exact original254b1e ODB unchanged,23 distinct inputs. Derived14154434169 SHA19fee53f2e944cb53eb569aecc4a71eb7b58a411188b2fdd177827362800e91f; native14154893429 SHA4b8db6cd649eb9192897672e6a8c14710cf03617ea36c9cad62cc7afc79dcb5a. Three newly found intermediate pins have >2.6ns worst setup: ABC767397/A (nand4_1)2.721625805ns; ABC780629/A (nand2_1)2.653504133ns; ABC770542/A (nor2b_1)2.619621515ns. ABC prefix is $abc$735036$auto$blifparse.cc:397:parse_blif$. These cover endpoints FF181416,FF164048,FF159945 respectively (FF prefix $auto$ff.cc:337:slice$).
- Remaining three best options are ABC736135/B(nand2_1),setup0.706844389ns,hold path13.418ps to FF181413; ABC772540/B(nor2_1),setup0.414730936ns,hold36.024ps to FF160489; ABC772710/B(nand2_1),setup0.44306916ns,hold47.568ps to FF160521. Need actual smaller-delay cell experiment and fresh complete setup/hold; no blanket large delay or relaxed final gate. All these measurements belong to the unchanged baseline; recheck after174 repair before combining.
- **Live PLL native accessor probe43698755531 /636f4a54a66c0ecc01c8a3fe799565e16fa553b7**, codex/pll-current-native-preflight. Restores frozen original engine103134f..., exact native Docker image/models/prepared845-device circuit; retains102OFF/solver/loads/source bytes. Separate OP-only wrapper adds42 actual leaf queries (ic,ib,ie,is,qbe,qbc for7devices), no run/tran command, saves native logs and binary OP. Validates existence only; units/scaling/dynamic current semantics, common131-column130ns diagnostic, original1us PLL acquisition and fullPHY remain OPEN. Source readback43698421351 verified in docs/evidence/pll-current-source-readback-20261115.json. Model Q child uses m=1 and internalS1 throughRsub/Csub toBN, so do not multiply queries by Nx or relabel intrinsicis as macroBN current.

## PLL source preflight resumed, 2026-11-15

**43698421351 / f0f1ee210be80c08d15ff52a38b11af74eaac8d2**, branch codex/pll-current-source-preflight, performs hosted exact source readback only. Restores original preparation39920519407 (summary63c6b8d...,parts92a85e...) and frozen HBT modelae9288..., seven actual first-master device records391/392/393/394/395/396/400, original deck/terminal contract, and pinned ngspice VBIC source. No circuit/solver/stimulus change, no transient, no current-query qualification claim. Native model/source payload remains cloud. Consume readback.json to resolve actual leaf/parameter/scaling/branch topology, then qualify accessors with exact original engine before130ns unchanged-circuit diagnostic. The proposal atd05b2bf1756194d1dd5e8f8fb816044a9a1e9a14 remains source-only; its old authorization flag is historical, user has since authorized full PHY work. Preserve all startup/OFF/load/safety gates and common131-column trajectory comparison; full1us acquisition is still required. Existing raw capture has no individual HBT currents; do not infer conduction-only or complete macro-terminal currents from unqualified queries.

Additional live read-only run **43697869651 /162c746d4cd214aee03ce421f1dd56d3438330f2**, branch codex/rx-lane-six-path-alternatives: every data input on the six excluded paths, unchanged254b1e baseline, all three corners. Re-measure on the repaired ODB before applying subsequent changes; combined effects are not established.

## 2026-11-15: fresh RC composition and measured hold-margin repair dispatched

Production readiness, full serial Gen3 x4 PHY, integrated routed mainchip and final setup/hold remain OPEN. All native work remains hosted; no local CAD or artifacts. Do not merge experimental workflows into timing/combined.

- Fresh metal RC **43696429827 / 51f8af2cb8cf867e7fc15233096e2d31df9a12c0** passed: 28414 R, 18356 C, two extraction orders and fault controls. Native14154956301 SHA217c4e367210a1f7de27b8820b5497c787bef1e89ad57104b56f23e60200c705; derived14154482289 SHAbdd6243a89b1394e46ed8fd948f1dd6842e40b88459b6c467a9db4b5b41cbc4f.
- Fresh gate mesh **43696757962 / e6fb3b967a732baca602b2323f79c81027a90703** passed four native mesh resolutions. Native14154901883 SHAd48c05270beda1f01a2466ee01e7e8039ffba12d67b2a4af8647f7f805c2e62f; derived14155021465 SHA8b309be64accf34a9bd6442edb3f167aba224835bfd777c160c5b27eb1fd228c.
- Fresh gate reduction **43697011992 / 385dcedd4c42a5353c5fd930e5e882c94e7378c7** independently checked: 503 native executions,250 port networks,2 fault controls, nominal_R_network_port_reduction_qualified true. Native14155092029 SHAce0ba53fab63b8a952d9d0c8f6a5542f9b5cc95cfaf946ef0c4f591d9c240d80; derived14154732668 SHAa59051eea20ed2a9bec8a4fcc47b74071396bc9466bb717568d393a79cecd50e. Material corners, full PEX/electrical/full PHY acceptance remain false.
- **LIVE loaded composition43697553951 / 30d59883a29c0c64f5855884a26aeb39783900ae**, branch codex/current650-clock-full-composition. Exact fresh6023cf16271d3d49307b3967b056b4b11bfaa5534254dc89ba60f3dc21b6f82a GDS chain; both assembler and acquisition census guards updated to measured28414/18356. Original256bit nominal_late stimulus, load, solver, device and electrical gates unchanged. Old historical metal retained only for explicitly named comparison, not composed model. Consume result before claiming clock-geometry improvement.
- Near-zero measurement **43696332872 / c5681cc5d85a5d67adc81465a21835aeb94b534a** passed without changing ODB254b1e467fbdd6a94ce274a2c58a32168ff145b99cb54b4cb60faeab80ac5d33. 189 reported paths,507 alternative pins,3042 branch reports. Derived14154788203 SHAd4126f65abc2210d7664a1d769fe65291fc1ef1a01c2c4084e79b6f5a86eb729; native14154334768 SHA20ea10f376ae8e0e966094d9fd6f0a6bffaa227c322e974cfc8c7a7157b740a6. See docs/evidence/rx-lane-nearzero-measured-plan-20261115.json.
- **LIVE repair43697752210 / c5affedb31cd1b2e02d8234d073525a3be94f571**, branch codex/rx-lane-nearzero-repair.174 distinct measured branches cover183 paths, all with >=1ns worst setup in all3corners. Six paths excluded, not waived. One native noninverting delay per selected branch; exact unchanged baseline, original master/incidence/placement guards; fresh all-corner/global/boundary reports. Overlapping paths may accumulate delay; do not accept before comparing ALL results. No final routing or fullPHY claim.
- Still track ACK mainchip43696515079 /56f97b8744d2dcd92821a79a7dd63168aacefa9c and observed boot43691795620 /91a4dea0322172b853b0450d153ebaefd380ee6f. New synthesis IDs must not reuse old ODB cell selections.

Next: consume repair and loaded results; handle six remaining margins with measured path alternatives; consume ACK synthesis and rebuild placement/CTS with fresh identities; diagnose boot observer; continue serial PHY/integration and full release blockers. Preserve failed measurements, never relax clocks or acceptance gates.

---

## 2026-11-15 — current-source ACK chip build, full near-zero margin batch, and fresh clock RC active

The full production goal remains active. No final chip/PHY acceptance. All native CAD and source work stays in GitHub; only small derived reports are processed in local RAM.

### Active jobs (confirmed via API)

1. **43696515079 / 56f97b8744d2dcd92821a79a7dd63168aacefa9c**, `codex/pcie-ack-prefix-mainchip`: new whole-chip firmware/RTL preparation and synthesis, retaining the exact b2e5... build options and20 SRAMs, plus opt-in SOC_PCIE_ACK_STALE_PREFIX. New gate `scripts/require_ack_prefix_qualification.py` authenticates the exact new RTL and six-switch qualification before CAD. Both sim_soc.sh and syn_soc_top.sh propagate the new flag; preparation manifest records it. Existing native-model, scrub, firmware, CRC-select and RX proofs remain. This is a NEW candidate; never transplant old ODB cell IDs after synthesis. Preserve current combined ODB as baseline. Native artifact names ack-prefix-mainchip-source-native / mapping / replay-regressions. Flow still packet-boundary PCIe, NOT full serial PHY integration.
2. **43696332872 / c5681cc5d85a5d67adc81465a21835aeb94b534a**, `codex/rx-lane-combined-nearzero`: read-only margin batch on exact combined ODB254b1e... . Actual fast min.rpt from43695359714 contains189 distinct endpoints with hold<50ps; not just worst CPU path. Includes Ethernet SRAM input path at0.871ps and PCIe/CPU flops. Driver authenticates that report and enumerates first and last two data-input pins on each path. Measures max/min through each distinct option at all3corners plus40boundaryports. Uses group_path_count1 (worst per clock group) to avoid huge redundant reports; same worst-margin semantics. Source scripts/run_combined_nearzero_trial.py andhw/soc/pnr/combined_nearzero_flow.py. Expected189 recorded paths; do not claim exhaustive more-than-report-limit census. If source-pin parser fails, inspect actual path type rather than guessing. Next choose actual setup>=1ns alternatives, then insert native identity delays and remeasure all corners. Delay at finalD is NOT automatically safe.
3. **43696429827 / 51f8af2cb8cf867e7fc15233096e2d31df9a12c0**, `codex/current650-clock-metal-rc`: fresh distributed metal/MIM-aware RC on qualified clock GDS6023cf... with both native extraction orders and unchanged numerical methods. Source controls/full artifact hashes protected. Earlier43696088748 failed because helper cdr_mos650_mim_support.py still asserted old0e7b GDS. Inspected all pinned Python sources: only that helper retained the obsolete guard. Updated it to exact physically qualified6023 GDS and updated manifest; no numerical equation/rule changed. Failed run native14154795784 SHA77c53e771ca249a7fd04ff62278e0c7c4bbb216316ef1c6e000b7190fe248996, derived14154263779 SHA20120a60cbc31fdac2158d842b806dd01c0795bf74e59ec8e160e8554ea8280f. Successor must pass before gate mesh/reduction/loaded test.
4. **43691795620 /91a4dea0322172b853b0450d153ebaefd380ee6f**, observed CVC boot: last seen running, original4Mcycles plus read-only PC/mcause; do not restart. Its model scope remains supplemental functional, not native/SDF acceptance.

### Proven new evidence

**Clock terminal anchors43695818962 /8fc405e96adafb355d85e6da401df25b6ac22bfc passed.** 650devices,2046terminals,1428physical anchors,200gatecontacts, current6023 GDS, oldRC not reused. Native14153663756 SHA023d640ad7979b6a1bc3d87e0e96afe02737e7a8aef3b25fa805f955dfeccf68; derived14153204757 SHAe9233feee1c10354794dc7646b73b8fe9247113e3a1c070a8d0295d7c42e208f. Receipt current650-clock-terminals-qualified-20261115.json includes provenance proof. Initial43695646721 stopped at obsolete old-GDS provenance guard. Fixed by RESTORING authenticated old0e7b graph-native predecessor and independently proving BOTH packed->upper(M3/M4/M5) and upper->clock(M3/M4/M5/TM1/TM2) additions. Original geometry/child material/annotations/hierarchy preserved; current via incidence andmacro bbox unchanged. No blind guard removal or replacement-only shortcut. Current metal input config binds these exact anchors and graph43695470421.

**Six-pin combined headroom43695359714 /5e29b46e34c21a0fca6396aac7eeaac4aefd662b passed, ODB unchanged254b1e...** Receipt rx-lane-combined-six-pin-headroom-20261115.json. Native14154184576 SHA9da06d3874891bdc6ad4975badf86814a3f15d5101a2d95cc7fb6f25273a07ac; derived14154109878 SHAda7d3c4c994905fac903adce282b6efdebbc9d78412071da4234801f5f3d03cd. WorstCPU FF176887/Q -> NAND811030/B -> O21AI811031/B1 -> MUX811032/A0 -> FF176920/D: slowsetup through first3 inputs18.8663/17.5919/14.1293ns; finalD only0.614557ns. All share fast hold0.000544009ns. First branch is safe measured alternative, finalD blanket-delay could hurt setup. ACK FF160646/Q->FF164200/D slowsetup-2.718770504ns, typical-.258043826ns, fast+1.148584604ns; unchanged actual worst. Current wholecombined setup2458/98/0 and hold0/0/0 remain placementRC only.

**Critical source correction before ACK integration:** timing/combined replay RTL lacks CRC_SELECT and EOP_CACHE optimizations present in actual synthesis b2e5e004... . Initial isolated ACK experiment used that older main-branch source. DO NOT replace actual chip source wholesale with it. Ported ONLY the prefix block+one capture RHS onto b2e5... and verified removing those exact edits restores original bytes SHAa5891101ff12672cf6da0fa5da09c638e44fc7a5d4fc94b445535e7b00834d45.
Current qualified RTL SHA**f5634cd4692abde4aa576aa11e392c4ef5c2787a35962aeec0ac444340ec4c7a**, producer **43696035080 /13ce1bfba1a3238f8b08415c55df4f2bdec5d8a9**, branchcodex/pcie-ack-stale-current-mainchip-qualify. All24bit combinational proof+2expected mutants and6x300k fullreplay output comparisons PASS. Both reference/candidate enabled INBANK,AHEAD,RESET_COPIES,WRITE_PREDECODE,EOP_CACHE,CRC_SELECT; onlycandidate adds ACK prefix. Reference reset-copy port explicitly driven equal to original reset; candidate same existing bench support. No other bench coverage removed. Artifact14154810806 SHA9d104d50fd232005f67e1431051c650ff4a919adfcbcfa083709ba3455a47ed6; receiptpcie-ack-prefix-current-mainchip-qualification-20261115.json. Mapped isolated ACK cone17% gain still hypothesis for chip gain; NEW synthesis/physical qualification required.

Next consume active jobs, preserve exact artifacts, and advance fresh RC/gate mesh/reduction/original loaded test plus real mainchip timing. Full serialGen3x4, analog loaded closure, mainchip route, final setup/hold and production remain open.

## 2026-11-15 — fresh clock graph verified; terminal extraction dispatched

Freshgraph43695470421/d58ae1163bf3ba50206437c5c17cf63e299414a9 PASSED and derivedresultinspected:650devices,2046terminals,25ports,113actualconductorcomponents, exactGDS6023cf16271d3d49307b3967b056b4b11bfaa5534254dc89ba60f3dc21b6f82a; sourcephysical43695046876; old_RC_reusedfalse,wire_rc_extractedfalse. Native14154355704 SHAa7c6e05d6c251e025359cfd0170596bb55c9eb6b2625b35c253f35fec8ebfe29; derived14154183456 SHA864aa69a2c72e061126c25841f46abfc17d4d2422a4e6a8b6fcdd5b604f8026a. Graph113componentsalone isnotRC/extractedtiming.
Newterminalanchorsbranchcodex/current650-clock-terminal-anchors, heade8144cd4f5c97a498af43ac7b91aa90b358f3c7b. Exactada333... provenmethods, newgraphsource/native+derived/GDShashesandbranchguard; fullfilepinsupdated; originalpackedbaselineusedonlyprovenance, neverascurrentgeometry. NativeartifactmissingERROR. Mustvalidatefreshactualgatecontacts/terminals, thennextmetal/gatemesh/reduction/loadedtest.
{'run': 43695646721, 'head': 'e8144cd4f5c97a498af43ac7b91aa90b358f3c7b', 'status': 'in_progress', 'conclusion': None}

Combined-margin43695359714/5e29b46e34c21a0fca6396aac7eeaac4aefd662b andobservedboot43691795620/91a4dea0322172b853b0450d153ebaefd380ee6f remainliveatlastpoll. Do not restart. PhysicalPASSreceipt+ACKmapped~17%gainreceipt committed54870852a40df26d398fa13cd6c08021a1d95bd1; fullproductgoalunchanged.

## 2026-11-15 — actual clock650 full physical PASS; fresh extraction and combined headroom active

**Clock650 physical43695046876 /7c253a13438932af701b33f6c9d6c76f2ddfa6b5 PASSED.** Exact new GDS6023cf16271d3d49307b3967b056b4b11bfaa5534254dc89ba60f3dc21b6f82a (1691454bytes). ALL560DRCcategories,0markers; deepLVS+flatLVS PASS; all13faultsREJECTED_EXPECTED_FAULT includingoffgrid. This closes the clock-metal candidate physical failures52->5->0, NOT loaded electrical/fullPHY/mainchip timing. Qualification explicitlynew_RC_executed:false,electrical_accepted:false,full_phy_accepted:false,final_timing_complete:false. No rules weakened.
Native14154400256 SHAc79134cba9fcd33d749903b93d9a71b940771c3da7266ad4b1ed4ff051600248; derived14153864178 SHA2c5ae31956dcf1b5465388a1189c6c90ce7c52d4ba6ee54e10b9e0a72a0067ce; physical/result.json SHAdb747240d81efb032f205a3285c4dcf71c2e78a79ad4d7d3892ec4422a95303f,physical-qualification.json SHAc362845ed704bb5a0455bab08719ced5872d12a03adf8eb0bec68f811b1a23fc. DRCreportSHA65323bd352a208ac709ce75e782faf3b6dd9291cce44ddb14ee15e01d5e919b0. Fullreceiptcurrent650-clock-physical-qualified-20261115.json committed here.

**LIVE fresh graph43695470421 /d58ae1163bf3ba50206437c5c17cf63e299414a9**, branchcodex/current650-clock-wire-graph. Exact oldproven17297fd... graphmethods, nowbindnewphysicalrun/head/archive/report/GDS andnewbranchguard; pinsupdated atomically; nativeartifactmissingERROR. Source scripts/extract_cdr650_paired_wire_graph.py, manifest scripts/cdr650-paired-wire-pins.json. Requires16physicalphasespass,650devices/2046terminals/25ports, independentnativeLVSownership. No oldRC reused. Nextaftergraph: freshanchors(templateada33327319b35ec53eea1b3cba17a30060b8c00),metal(templatea81e8c3d4f38a9f836e710dce22085e6de39b97c),gatemesh(template6706e6c00e9d63aa4ff11c082c41ed06923a755a),reduction(templatea0f8e83e27889b7ad8fa28993c452a8884714aaa),thenoriginalfrozenloadedtest. Obtainexactnewartifacts eachstage. Physicalpass alone not an electrical or CDR lock pass.

**ACK mapped comparison43695254919 /13ad3945cb34ebb8d6bf569ddcd711a9c67cc24d PASSED measurement.** ExactqualifiedRTL447e2208...; source scripts/measure_ack_stale_prefix.py, branchcodex/pcie-ack-stale-mapped. PinnedIHPc4b8b4..., jointdelta[11:0]+allowed+stalecone (27inputs,14outputs), actualsharedlogic, DEPTH4sent_count3bits, samebuf2driver/10fFoutputload, ABCno wireload. Native ABCdelay ref->prefix: slow2593.46->2151.22ps,typ1664.38->1370.64ps,fast1095.69->905.56ps (~17%gain). Area slow780.192->850.9158um2 (+9%); gates69->81. This is unmapped-RC-free combinational estimate, NOT 0.44ns improvement to actualmainchip guaranteed and NOT currentsetupclosure. Mappednetlists+librarieshashes inartifact14153918915 SHAf95449ccad4592241865597fd2db2d702b9332578d5ab57d236aca31214e995e; receiptpcie-ack-stale-prefix-mapped-20261115.json. Candidate stillopt-inexperiment only; fullcapturetiming/reset unchanged. Need actualwholecone/mainchipintegration withfreshproof/physicalchain beforeenabling. No oldFFIDs to be assumed valid afterresynthesis.

**LIVE combined headroom43695359714 /5e29b46e34c21a0fca6396aac7eeaac4aefd662b**, codex/rx-lane-combined-margin. Read-only authenticatedcombinedODB254b1e...; sixpins NAND811030/B,O21AI811031/B1,MUX811032/A0,FF176920/D,FF164200/D,FF160646/Q; actual3cornersmax/min throughreports+40boundaryports+globalmetrics. Preserves clocks20/4/8/8ns,5%derate,propagatedclocks, assertsODBbytesunchanged. Source scripts/run_combined_margin_trial.py andhw/soc/pnr/combined_margin_flow.py. Restoresfullsetupchainandexactcombinednativebeforemeasurement; outputcombined-margin-trial/run, derivedartifactrequired. BeforeanyextraCPUholddelay chooseactualpositiveheadroom; currentglobalfastonly+.54ps. NeedseeactualACKcriticalpaths/load beforeadoptingRTLchange. Sourcepriorreceiptcombinedhold remains2458/98/0setupand0/0/0hold,placementRConly.

Observedboot43691795620/91a4dea0322172b853b0450d153ebaefd380ee6f stillactiveatlastpoll; don'trestart. Fullproductiongoalactive,fullserialGen3x4/mainchiproute/finalsetup+hold/otherreleasegatesremainopen. AllCAD/native/sourceworkcloud; no localartifacts.

## 2026-11-15 — same-ODB combined hold zero; ACK full traffic passes; reduced TM2 physical active

**Combined43693300169/9ebc5aaeec99b2303b6c3e74439370a2588b94d8 measured successfully.** Exact same candidateODB254b1e467fbdd6a94ce274a2c58a32168ff145b99cb54b4cb60faeab80ac5d33 has setup2458/98/0 slow/typ/fast withWS-2.71877/-.389342/+.683008ns; hold0/0/0,WS+.126711/+.0902471/+.000544009ns. Slew27/3/0,cap0. No globalsetupcountregression vsbestsetupinput; selected123pins+40boundaryports>=50ps. GlobalCPUholdmin stillonly.54ps. This is placementRC, NOT routedfinalclosure. Fullreceipt rx-lane-combined-setup-hold-20261115.json. Native14153798487 SHAa74a0c46411f4f015f804a53ea1e5aae636a4d5a01c471e5c1b276863e8d6ea6; derived14154072583 SHA1dffb409ed2343c1e386a81ed97216b4faca4851d15bcf5b6e33f0af621fbf23. RestoreROOT/combined-hold-trial/run, state run/6-nssoc-remainingholdeco/state_out.json; precedingsetupchain mustremainavailableforabsolute paths. Next improveactualsetupcriticalcone andCPUholdmargin withfresh headroom, then route/extractedSTA/currentphysical. Do not claimfinaltiming.

**ACK prefix43694619569/fb6f18b80192f9830eca6d150ba4e949860d95b4 PASSED** formalall24binaryinputs+2rejectedmutants AND6x300kcyclefullreplaycosim acrossdepth2/4,timeouts128/256/1024. Everyoutputequal, originalcoveragegates met, mismatches0;1.8Mcycles. Artifact14154310067 SHA3735f2f2eac49e17aad5ef221b8a6b878d6cf3e3116547e1c43a58e7448ec713; receiptpcie-ack-stale-prefix-traffic-20261115.json. Candidate remainsopt-in onexperimentbranch; NOT activated in currentmainchip, NOT mappedtiming/four-stateexhaustive proof. Next mapexactSG13comparison/wholecone to demonstrate delaygain beforemerging/newwholechipbuild. Avoid invalidatingworkingECOchainblindly.

**Actual5TM2markers extracted43694781509/30c39b00a62491f981879dc23ee1a4a3889d9a49** artifact14154280743 SHA71e5189e05819522f10c9c99a3043ee53dfd00562734d72327bda471e5b1ad56; receiptcurrent650-clock-tm2-markers-20261115.json includesactualXML. All5edge-pairgaps2.8um: topcell y476.43/473.63,x440.658..522.342;top y1018.69/1015.89,x0..957.142;top y1342.32/1339.52,x440.658..957.142;pd_child_sampler y195.63/198.43,x246.863..464.652;pd_child_sampler_cd samey,x566.863..784.652. ChildcoordinatesareLOCAL; don'tapplyasglobalboxeswithouttransforms. Diagnosticfirst43694670264 failedPython3.10file_digest; successor24.04passed, noCADrestart.

**Reduced TM2 generation43694925469/36c3cc0fadf9c59e05884b06dc286570f65eee4a PASSED**, TM2growth1um instead3um, still5umforeignclearance; sameopening/bbox/originalgeometry/via guards. Native14153639079 SHAb418d18b4c92c0d45f10f1f73559a69f45a616c4b59fe746429de966dd5483f2; derived14153658828 SHAa5018968e07b1ab1b3b30473f417ffb72de3ab961b57a3df60f42cf79dce0a1f. ExactGDSinboundphysicalcfg. Newphysicalrun/head below bindsactualcandidateandhashmanifest, unchangedfullchecker. AwaitfullDRC/LVS/faultresults beforefreshRC. Do not assumeminwidth/spacingpass.

{'latest_physical_run': 43695046876, 'head': '7c253a13438932af701b33f6c9d6c76f2ddfa6b5', 'status': 'in_progress', 'conclusion': None}

Observedboot43691795620/91a4dea0322172b853b0450d153ebaefd380ee6f stillinprogressatlastpoll. No restart. FullserialPHY/mainchipintegration/route/finaltiming/productionremainopen; activefullgoalunchanged.

## 2026-11-15 — clock DRC reduced52->5, ACK comparator formal passes; traffic and marker diagnosis active

Physical43694128865/eb1308d99a2b830160c419bab34162e27500ccd6 terminalFAILURE: newGDSaeaf8e4fcc33d06f7198d2a837a8b2cd13c9b902e5083ca9ceff4759e755e9b7 has ONLY5 TM2.bR markers; all priorM3/TM1/TM2minwidth failures eliminated.560categories. Deep+flatLVS pass; fullfaultclosure notclaimed. Derived14154250558 SHA6b0f6d94dbb038d2ce1e34b5c46e906656b5d549f6f3411a8bfa2258cf66a28b; native14153712794 SHA30b6baa51a98f6f9fa6a2920e5224c7287d57ec348d1fa9118f0b55980f80d38. DRC report2970b7ecb3d877357b4ea6172ef7378b8402c06ad28c343e4f2ee66ceb304c76. Full derived physical receipt committed with this checkpoint.
LIVE marker diagnostic43694670264/821b17c7d4076aa668378d8406a71e78fb69c6ad, codex/current650-clock-tm2-markers. scripts/read_clock_tm2_markers.py downloads exactfailednative cloud-only, extracts reportXML items+categories tosmallJSON. Inspect actual5markers before next geometry edit; intra-owned-conductor narrow gaps may triggerlongwide5umspacing despiteforeign-clearance5um. Do not waive rules. Native GDS remains cloud.

New setup RTL candidate in separate codex/pcie-ack-stale-prefix, NOT enabled/merged into mainchip. Actual soc_pcie_replay_tx.v adds opt-in SOC_PCIE_ACK_STALE_PREFIX, 3/3/3/2bit group borrow for low11bit subtraction and highbit xor; stale iff resultingMSB AND lowerbitsdifferent. ACK captureedge/reset/ack_delta_q/allowance unchanged. Initialformal43694422342/e5d97e810dc40069cf76216589eecd0c3d6d37d3 PASSED all2^24 binarypairs, rejectedmutants(removehalf-distanceexclude,removeborrow), bothRTL modesIcaruscompile. Artifact14153377331 SHA88faf5ac758b1481b041ec22a6865f09c1e5081cbb9d415f0c752e4b30d7a646; RTL SHA447e2208baf1e158561e29332178adce5687ab574f465b109b433ca1a95652de. Receiptpcie-ack-stale-prefix-formal-20261115.json. This is not arbitraryX/Z, fullmoduletraffic or timingproof.
LIVE extendedqualification43694619569/fb6f18b80192f9830eca6d150ba4e949860d95b4: sameformal+mutants AND existing unchanged tb_pcie_replay_ahead fulloutputeverycyclecosim, sixconfigs(4x38x256seed1,2,4;4x38x1024seed3;2x22x128seed5,6),300kcycles each, originalcoveragegates. subprocessreturnANDPASSmarkerANDnoFATAL/MISMATCH enforced. Sourcequalify_ack_stale_prefix.py. Beforeintegration need mappedSG13timinggain and fullsystemqualification; activating RTL requires new synthesis/physicalchain, oldDB IDs cannot be transplanted. Do not abort currentcombinedtiming candidate.

Combined43693300169/9ebc5aaeec99b2303b6c3e74439370a2588b94d8 and observedboot43691795620/91a4dea0322172b853b0450d153ebaefd380ee6f still live; exactexistingjobs, no restart. Fullgoal remainsactive; serialGen3x4/integration/finalroute/timing/production unclosed.

## 2026-11-15 — width-filtered clock candidate dispatched to full physical checks

Most recent live physical run: **43694128865**, head **eb1308d99a2b830160c419bab34162e27500ccd6**, branch codex/current650-clock-metal-physical. Same frozen full560 DRC/deep+flat650 LVS/fault checker, no waived rules. At checkpoint source-controls passed and native tool acquisition in progress.

Generation **43693981547/e2779c919b770c4c89d9b83190154052151cf406 passed**. New GDS **aeaf8e4fcc33d06f7198d2a837a8b2cd13c9b902e5083ca9ceff4759e755e9b7**; native artifact14153486599 SHA c669d3ab01dbff33bb3b30aa4b54d3f3ce724c293d839edac9570e16fbc203e2; derived14153028432 SHA f6bbf6b5b9f15348f2ed9651c27692473b258c4103b5fcabc0427640e46fca54. Proof clock-metal-widening-proof.json authenticated RAM-only; original geometry, macro bbox and via incidence retained, all5metal layers changed. Bound cfg and physical hash manifest atomically updated. DRC success remains unknown until native result.

Combined timing43693300169/9ebc5aaeec99b2303b6c3e74439370a2588b94d8 and observedboot43691795620/91a4dea0322172b853b0450d153ebaefd380ee6f still active. Do not restart. Separate zero-hold candidate near-zero fast path identified from authenticated derived14153535376/min.rpt: Ibex prefetch FIFO FF176887(Q rdata_q[72]) -> NAND811030/B -> O21AI811031/B1 -> MUX811032/A0 -> FF176920/D, clockgroupclk_i through gatedu_ibex.clk. Worst margin +.000544009ns is CPU path, not selectedPCIe target. Await same combinedODB metrics; measure its actual setup headroom before any further delay. Full prefixes as existing scripts; no blindly reusing old selected-pin margins.

Next fresh RC template inspected, NOT dispatched: scripts/extract_cdr650_paired_wire_graph.py at17297fd48eb45504f19c15f517c7ba69fdd017af (old graph43680974890). If current fullphysical passes, clone to new experimentbranch, bind exact newphysicalrun/head/nativearchive/report/GDS hashes, update branch guard and scripts/cdr650-paired-wire-pins.json. It authenticates full16phase result,650device/2046terminal/25port census, actualLVS ownership and unchangedoriginal probe with only50->200NMOS adaptation. Never bypass physical status or reuse oldRC. Then fresh anchors/metal/gatemesh/reduction/loaded frozen electrical.

## 2026-11-15 — combined timing candidate active; bounded clock geometry LVS passes, DRC repair active

This entry supersedes older active handles below. No full PHY, routed timing or production acceptance. Cloud-only source/native execution retained.

- LIVE combined setup+hold: run 43693300169, head 9ebc5aaeec99b2303b6c3e74439370a2588b94d8, branch codex/rx-lane-combined-setup-hold. Restores best setup ODB d2c53ac45dc6f60418d2b1ef5dc27222826f8d91bddd128907e3fb09ff977ebd and measures all selected margins BEFORE applying 203 delay cells. Requires actual setup margin >=1ns for 123 selected pins plus40 boundary ports at all3corners. No arithmetic merger of separate proofs. Native combined-hold-trial/run; scripts/run_combined_hold_trial.py, hw/soc/pnr/combined_hold_flow.py and combined_{boundary,selective,remaining}_hold.py. Consume same-ODB after reports then route/extract/qualify.
- Separate hold candidate 43692165051 / 4d5ae68d0e85c980d36181029db8a72e2e63961a measured hold0/0/0 slow/typ/fast, worst +.126711/+.0902471/+.000544009ns. Last margin is only .54ps, NOT robust final closure. Setup2752/730/0 unchanged. ODB ee99e9949c205a3c6853b9d65201e1b2baec3be22bcf12350c5f63711bfb1059; native14152604859 SHA b2104fd0d6f657cd7fe4b2460fee09ab45daa494806271302b0f4e08526b1969; derived14153535376 SHA d3abc9d16412128a9157ee33cd2bedbb61183d5d873a9d5607b75c66d66e812a. Receipt rx-lane-remaining-hold-20261115.json.
- Best separate setup candidate43691893753 / 8993198b17ea0a4f3fa76211ee82141208f98b89 measured setup2458/98/0, worst -2.71977/-.389342/+.683008ns, hold4/25/163. Native14153077350 SHA1e50fd1359572512c930ab780350b160c463498840667793ae97471c5120ad3c; derived14152692973 SHAac6398c0738207b4fb3805f95c166f1e335a48e16bbfa1a602a4b545289ed562. Reset-branch-trial/run/4-nssoc-resetbrancheco/state_out.json; exact ODB above. Receipt rx-lane-reset-branch-20261115.json. Both receipts committed ae6466ffe53140f40a57183ecc092d346a156d1a.
- LIVE observed boot43691795620 / 91a4dea0322172b853b0450d153ebaefd380ee6f. No restart. Original4Mcycle gates plus read-only PC/mcause observer. Prior DUT86/101 warning investigated: all15 omitted ports are OUTPUTS, no missing input; not a proven root cause. Native/SDF qualification still false.

PHY clock history:
1. Unbounded9ccd... candidate43692375532 rejected by physical43692558291 before DRC: nonzero LEF origin. No full physical pass.
2. Bounded candidate43692801237 / 1eef48c53ab0cffcef532e77bad1054a1d8a1e81 GDS94850042c86cd02166bc562ec81f16252e3ddcf43b8adf84f7ab4a053fe670e9, originalbbox[0,0,2316600,4715480] retained. Native14153185709 SHA fddddd56f043756b4fdd8708e6508a5eca0f4a15374359addde6a1c5a9cbe468; derived14153091217 SHA0c5427c0fbab77a0d3db284f71b5f666a7a76f40ef79a1bfaf9c8403c4a68db5.
3. Full physical43692962126 /842c0f2f13887815641989170ff1fdf1aab62bf5 FAILED DRC52, deep and flat LVS PASS. Counts M3.a2,TM1.a32,TM2.a12,TM2.bR6;560categories. Native14153241062 SHA375dd5879a6ebce1b015a13c0434906db54783ba91fad8fdd6d69f6df51b5203; derived14153276012 SHAf0b01acc435060c7fd944eeb57fde5841fcefa387ff76f3186e23c1e809c3893. DRC reportSHA0548e9b64258b237b631ef6bc2e424336de6812857d232a87048bce5e9fec80a. Do not claim all fault controls passed; 12 expected rejects observed.
4. LIVE geometry repair43693981547 / e2779c919b770c4c89d9b83190154052151cf406, codex/current650-clock-metal-candidate. Pinned IHP c4b8b4... official BEOL rules verified: Mn width .2um,TM1 1.64um,TM2 2um; TM2 long parallel wide lines require5umspace. Generator now clips macro extent, increasesTM2clearance to5um, morphologically opens expanded conductor at minwidth/2 then intersects allowed patch, preserving ALL original geometry and original via incidence. This is a candidate, not presumed DRC clean. Poll generation, bind fresh artifact/proof/GDS to physical branch and full unchanged checker. Need independent fresh RC and loaded electrical after physical pass; never reuse previous-GDS RC.

Physical successor procedure: update scripts/cdr650-clock-physical-input.json with exact newrun/source/native/proof/GDShashes on codex/current650-clock-metal-physical; update corresponding entry bytes/SHA256/git_blob_sha1(if present) in scripts/cdr-wire-shortcuts-physical-pins.json atomically. Frozen checker30c4586b... unchanged. Dispatch workflow cloud-evidence-summary.yml once, do not merge experimental workflow to integration. Independent worker verifies predecessor0e7b..., exact five metal layers, original geometry,25labels,via incidence andbbox. Full650 loaded predecessor electrical failure and physical/mainchip integration gaps remain.

## 2026-11-15 — last3 hold repair dispatched; actual clock-metal GDS generated and native physical validation queued

Active full-product goal unchanged; no production/fullPHY/timing acceptance. Previous turn progressed: same-ODB branch headroom verified, three actual identity-delay ECOs implemented, real clock-metal geometry generated with preservation proof and full unchanged native DRC/LVS/fault workflow dispatched. Native artifacts remain cloud; local source/geometry not persisted.

**Exact active handles (last API confirmed):**
1. 43692165051 / 4d5ae68d0e85c980d36181029db8a72e2e63961a, codex/rx-lane-remaining-three-hold-repair. Native3corner run inprogress. Scripts run_remaining_hold_trial.py / remaining_hold_flow.py. Exact120-holdODB962722... plus one native sg13g2_dlygate4sd3_1 per3selected input pins. Original placements/masters/incidence retained; direct unique source connectivity validated. Selectedpin and40boundary margins plus ALL10oldshortpath pins and global3corners measured. Source headroom artifact authenticated before any mutation; all3setup margins >=1ns. Native path remaining-hold-trial/run/, missing archive ERROR. No final acceptance if execution green.
2. 43691893753 / 8993198b17ea0a4f3fa76211ee82141208f98b89 reset branch setup repair, stillnativeSTAinprogress. Exactoutputsuccessor3cea...; distinct SETUP chain, not hold chain.
3. 43691795620 / 91a4dea0322172b853b0450d153ebaefd380ee6f observed CVC boot, now actual wholechip simulationstepinprogress. Same4Mcycles/invariants, read-onlyPC/exception observer; no need restart or new unobservedboot.
4. 43692558291 / 86ac8a17ff9d65ba07d5e7a506a20ff0a4c6746a, codex/current650-clock-metal-physical, QUEUED. Full frozen checker30c4586b... DRC/deepflatLVS/faults on newclockGDS below. No checker/gate weakened. Newprotectedclockconfig+workflow/worker included in hashclosure; unchanged older predecessor acquisitions still independentlyverified before appending clock successor. Poll thisexactrun.

**Remaining headroom evidence complete:** 43691367680/d322dcdad7844ec794a47252e9d9fcebc3b89ca9. Derived14152613116 SHA8fb6a5f3e443a53d20889a6a0332358f43277ad1a90c671301ff2646908d1a26; native14152418876 SHA38510567748008acb44e03bd96f3b8746b5e38d323178443765c3c3598dcf466. ODBunchanged9627224813c5ce11cf43ffc3758d9f5f3b47802081ce587911e0944ccb0445f8. Actual10pins60branchreports+240boundaryreports, all3corners. Receipt docs/evidence/rx-lane-remaining-headroom-20261115.json.
Safe delayedbranches chosen:
- INV738189/Y sg13g2_inv_1 -> O21AI771053/A1 sg13g2_o21ai_1, slowsetup2.969167709ns, fasthold-.03202194ns.
- NAND770028/Y sg13g2_nand2b_1 -> O21AI770030/A2 sg13g2_o21ai_1, slowsetup2.230125666ns, fasthold-.023924308ns.
- BUF749466/X sg13g2_buf_1 -> NAND770358/A sg13g2_nand3_1, slowsetup2.473076105ns, fasthold-.000323519ns.
All ABCprefix $abc$735036$auto$blifparse.cc:397:parse_blif$. These are later branch inputs; first-load or finalD chosen blindly wouldhurtsetup (e.g FF159887/D slow-.668528795, FF160215/D+.092090786). Do NOT insertdelay atfinalD/commonfirstinputs. New3holdscript uses unchanged nativeidentitycellfunctioncheck+sameODBsetupgate+protectedplacement.

**Actual PHY clock metal candidate generated successfully:** 43692375532/2a9f213ab2168e9a5b4895338b813b884dffdbaf, codex/current650-clock-metal-candidate. NewGDS9ccd4298c9a8cab902dcd708f9d47d9c55430ea1702b8c8e1c0e00abab33ec8f; predecessor0e7b4d8da7e6de4bda98ea0a83d6dbb5ea78c73c89a60d5724ba44401c1a24c0.
Native14152833480 SHAd2b51f0339111e3112511e06245d2dd86c51a92ee7691f584e78b08c2721f40b, solecandidate.gds. Derived14152549172 SHA4a0352ce7ed823533169e4b28dbc9d4e7f03af82a24df3e73e503d1134664ae2; membersclock-geometry.json / clock-metal-widening-proof.json. Receipt current650-clock-geometry-20261115.json. Actual CP/CNcomponents16/17 seeded nativeHBT211/B and216/B on currentauthenticatedanchors. Traces connected conductor through actualvias; widens onlyM3(30)+M4(50)+M5(67)+TM1(126)+TM2(134). Originalallgeometry/hierarchy/25labels/via incidence preserved; serializedregionequalverified. Adds10component/layerpatches. Growth.3/.6/.6/2/3um,clearance.6/.6/.6/2/3um. This is genuinegeometrychange, NOT numericalRCscaling or devicechange. Electricalimprovementunproven: additionalCmayoffsetlowerR. FullDRC/LVS queued, then MUST fresh graph/anchors/metal/gatemesh/reduction and original frozen loadedtest; never reuse previousRC or assume clock widening closes samplerVCE/phase/eye. FullclosedloopPHY remainsopen.
Generator source scripts/widen_current650_clock_geometry.py; inputscurrentgraphnative14148043395/8bf417..., currentanchorsderived14148053860/dd1a...; selectedGDS exacthash. Newphysical source scripts/cloud_cdr_wire_shortcuts_physical.py appends clockcandidate admission AFTER existingM3+uppernativegeometryguards. New scripts/cdr650-clock-physical-input.json binds source/run/artifacts/hash. Independently compares old/newregions allowedexact5metals, nooriginalgeometryremoval, noadditionalvia incidence, texts25identical; frozen650schematic/checker untouched. All priorcheckerfaultcontrols remain. If nativefail, inspectactualviolations; do not weakenchecks.

Two receipts above committed afd3c972dfaebee312f011c75ac896714b4fcad1 on timing/combined. No workflowmerged. Nextconsume3holdandreset3 setupresults; globalsetup/hold/electrical mayregress despite localmarginflags. Once bothscopesuccessful, combine actualECOs onONEcandidateODB and remeasure/reroute/qualifycurrentphysical. Current pipelinestillplacementRC, not routedfinaltiming.

## 2026-11-15 — preserved hold120; output setup gain; dominant reset repair and boot diagnosis active

Continue full production-ready NSSOC goal unchanged. All source/native execution remains cloud. Mainchip packet interface still NOT full serial Gen3 x4 integration. No final closure flags promoted. Previous turn made measured/preserved progress; no genuine blocker.

**LIVE confirmed handles:**
- 43691893753 / 8993198b17ea0a4f3fa76211ee82141208f98b89, codex/rx-lane-reset-branch-setup. Three buf4 dedicated branches from exact output-branch successor3cea359...; actual DB proves identity-only original chains depths5/2/5, original placements/masters/incidence protected. Reset behavior/clock constraints unchanged. Source scripts run_reset_branch_trial.py/reset_branch_flow.py; native path reset-branch-trial/run/, missing archive ERROR. Poll exact handle.
- 43691367680 / d322dcdad7844ec794a47252e9d9fcebc3b89ca9, codex/rx-lane-remaining-three-headroom. Read-only exact preserved120 holdODB962722...; derive every gate-input/endpointD pin on remaining3 fast negative paths, measure all3corners through each plus40boundary ports. Will select later branch-specific delay insertion using actual positive setup margin.
- 43691795620 / 91a4dea0322172b853b0450d153ebaefd380ee6f, codex/rx-lane-cvc-observed-boot. Fresh supplemental original4Mcycle gate boot with read-only companion top module observer; unchanged netlist/firmware/bench/SRAM/standard-cell qualification. Logs PC/instruction/mcause/mtvec/dataaddr/req every1000cycles after1.2M. Scope still derived standard-cell FUNCTIONAL only, native/SDF false. Do not restart.

**Hold120 repeat fully preserved:** 43690493434 / d6671978da578bc7fe8840c4c9ca6053b667aaee PASSED, identicalODB9627224813c5ce11cf43ffc3758d9f5f3b47802081ce587911e0944ccb0445f8 and same measures as firstunpreservedrun. Native14152826262 SHA72c2789cc116cad1500b6fe75595a24e2b6101483908a73db3a31be3a8bae1a9; derived14152756388 SHA25615ebb6be631cae972991f6c4d65d4d3cf01c5ee6d8dbd13ca10568b0e26f1. State run/1-nssoc-selectiveholdeco/state_out.json; restore under ROOT/selective-hold-trial/run. Full receipt rx-lane-selective-hold-preserved-20261115.json commit54898e038a4f7acd682f3f615e99d7a851877cd7. Both selected_margin_50ps/boundary_margin_50ps true. Global hold0/0/3 slow/typ/fast, WS+.126711/+.0783771/-.0320219ns; setup2752/730/0 unchanged. This remains separate HOLD chain, not setup successor.

**Output setup candidate PASSED measurement, not closure:** 43690386874/a244e33ea53a1d5b80464d3f248c6ee01971e64e, exact three identity branches. Sourceonebranch34a186..., newODB3cea359235759956213066e4c0c37de2aa62ae19044f20b812e240dba3f28dc3. State run/4-nssoc-outputbrancheco/state_out.json, restore ROOT/output-branch-trial/run. Native14151958934 SHAfd8c35d4c9fc724ef2bad06b4b335b4749bf0fe108fbbf60011f027cef136940; derived14152013712 SHA8014a9f65613e24fc1d161a31248e2fe4ead85bec51b10c29b7317817405b6d8. Targetpcie_initialized_o slow setup-2.826776743 -> -2.244403839ns; typical-.829167426 -> -.389341891; fast+.337455630 ->+.683007658. Targethold minfast+1.233639002ns. Global setup slow2489(-2.76546),typ277(-.389342),fast0(+.683008). Global hold4/25/163 unchanged. Slew27/3/0, cap0. Receipt rx-lane-output-branch-20261115.json committed481489ecc4a82d407ca1444752bf90e141a47d2a. Do not confuse target gain with global closure.

**Dominant setup cause mapped and next repair implemented:** authenticated original onebranch slowmax report1005negative reported paths (PCIe1000limit,CPU3,async2; NOT full2491endpointcensus). FF343483519paths = u_pcie.flow.packets.endpoint.endpoint.receive_packet.quarantine.rst_ni; FF343481236 = u_pcie.flow.packets.retry.rst_ni. Exact mappedJSONSHA6cbaa20bd3b0e911dcf66c4160a2130f18c1e0293ec57864d65341e052ca8eda; mappingrun43691158844/head583ec347946dc9cfcdae148a2af2117cd9964007,artifact14151664094 SHA896341182e3f634232e3377b2618e9291faa0e46b963dfd3cbb755fdf9a4fea9. Receipt rx-lane-dominant-setup-source-map-20261115.json.
Planrun43691622193/head74f07cc3e9b39008b41796cd407ddeb57c5794e6 artifact14152682344 SHA5769886a10ffcdd677827ec5969af588949b58dcb936a7d0be201e46cf634d35, receipt rx-lane-reset-branch-plans-20261115.json commitc9bb1129ff44f212de94d75fd0afd76c606faf97:
FF343481/Q dfrbpq2 -> AND739577/B and2_1 via fanout9652/9651/9642/9639/9638 (236paths).
FF343483/Q dfrbpq2 -> INV736012/A inv2 via fanout9610/9583 (441paths).
SameFF -> NAND736127/A nand4_1 via fanout9610/9527/9508/9482/9478 (78paths).
Prefixes FF $auto$ff.cc:337:slice$, ABC $abc$735036$auto$blifparse.cc:397:parse_blif$. Newlive repair validates all chains in actual successorODB, preserves inversion/logic and drives only sink pin through new buf4. No reset suppression/false paths.

**Whole-chip CVC boot terminal FAILURE:** 43681966595/4d0e9c12b692fe6297989ce1b62834cc0cada86a, artifact14152836241 SHA0d909e3bc3ed901f373cf648a2f7779d052cb30bba5999c2d59bf730304a9b2a. 16cell374784tracequalification passed; compile26.4sec. Run7019.45sec return0 BUT native $fatal and boot gatesFAILED; fourmillioncycles completed, not host timeout. UART436bytes; primaryimage rejectedcause5 asexpectedfallback, backupimage read/copy/verify completed, then prints0x00000000 and no success. At4000096cycles checks0/fails0/code0/magic0, watchdog1/0/0,flashviolations0. This is not functionalpass. Receipt rx-lane-cvc-functional-boot-rejected-20261115.json commite6cdb34167cabfb0c17ff62479181b5c852ef6fc. CVC compile warnings: DUT86/101 explicitports, monitor outputintegerbusy_cycles/done_cycle treatedwidth1vs32; investigate semantics but not assumed rootcause. SRAM qualification43682680141 remains independent, not replayed by originalboot.
Boot signal mapping43691579642/ccd15255c53c119934a7c83c3455b82e13660af0 artifact14152652315 SHA689b6a9fd984aebdce32f7bc95e67efc8f4e82c71db3d112341053845126dd27, receipt rx-lane-boot-signal-map-20261115.json. Exact flattened32bit u_ibex.u_ibex_core.exs_id_pc_id/exs_id_instr_rdata_alu_id;7bit cs_registers_i.mcause_q;32bit cs_registers_i.csr_mtvec_o;bus_data_addr32/req1. Observer uses escaped whole identifiers under tb_logicrom_gl.dut, read-only additional module. All28originalfirmware/PCIe/MBIST gates retained.

**PHY physical diagnosis:** topology43690670697/7fc709fc8fd8a2344fbce63080d34fdaa93834a4 artifact14152690287 SHAf4c395ccfd68376f160f038c04e0081a3ff1f6cc48c8d2cd73e3c92229826c02. Receipt shared650-failed-source-topology-20261115.json commitecf3f2fe9be2a80a3409fbe4d1a9473c92700ffc includes all650 source/physical bindings. UnsafeHBT211/212 are samplerD master clock steering pair: B=cn,C=sd_m_se,E=sd_m_te,S=bulk,Nx2,origin61/62,loadedXD0061/62. Not randomunknownmacro.
Saved-lag diagnosis43691010476/c46e85cc261565f0df63e154c98fd0cee7678d23 artifact14152661476 SHAba38165c6fcfa7137729406d09baa768a28ac2e6148a469b6cd483ee2f5dfd47, receipt shared650-saved-lag-diagnosis-20261115.json commitf744173e9897b9578b6fe0be9af49734262b52b1. Samewave, no new transient. Samplers A/B/C/D late.75UI unshifted all247testedcorrect but ORIGINAL.3UI electricalgate stillFAIL; never waive/move acceptance. X no clean bitlag in-4..+4: unshifted125wrong/247, best+2still83wrong, so not simplewhole-bitlatencyfix. Yconstant expected zero fornominal_late, shiftcomparison not meaningful independentdata;5wrong/195weakof247. Clockpair211base waveform phase0~1.1575V,.25~1.3724,.5~1.4257; VCEminaroundphase.5~.3847V. Need actual analogclockdistribution/load/workingpoint redesign with original externalstimulus and gates; fullPHY and gateextrinsic/substrate/PVTremainopen. No new full650run launched unchanged.

Next: consume remaining-headroom, choose branch-specific safe delay repairs; consume resetbranchglobalallcorner notjusttarget. Combine finalsuccessfulsetup+hold onONEODB and qualifyrouted/physical. Consume observedboot to identifyPC/trapandfixactualcause. Native artifacts staycloud; local RAM reports only. Do not dumpfullresultdict (400KB tooltruncation); writefullreceipt directlyGitHub thenprintselectedscalars. GitHub archive transienttimeout90sec isn't producerfailure; retrydownloadsameID/cachebuster only.

## 2026-11-15 — hold120 measured; preservation corrected; PHY saved-wave diagnosis

Continue the active full-product goal, not just these scoped trials. Everything native/source/CAD stays cloud; local cwd remains empty. No acceptance/production flags were promoted. Mainchip still packet-boundary PCIe, NOT integrated full serial Gen3 x4 PHY.

**Exact LIVE handles (do not duplicate):**
- 43690493434 / d6671978da578bc7fe8840c4c9ca6053b667aaee, codex/rx-lane-selected-short-hold-repair: repeats exact120-delay repair because first run's workflow used wrong native upload path. Now selective-hold-trial/run/ and missing native archive is an error.
- 43690386874 / a244e33ea53a1d5b80464d3f248c6ee01971e64e, codex/rx-lane-output-branch-setup: exact one-branch-hold successor; three dedicated buf4 branches on pcie_initialized_o path. Traverses actual original DB, permits only noninverting buffer chains (depth3/7/0); other original incidences/masters/placements retained. Three-corner before/after output and global STA. Not yet measured.
- 43690670697 / 7fc709fc8fd8a2344fbce63080d34fdaa93834a4, codex/shared650-failed-source-topology: queued read-only native contract topology mapping, source-to-layout identity of failed HBT211/212 and all650 records. No new transient.
- 43681966595 / 4d0e9c12b692fe6297989ce1b62834cc0cada86a: supplemental CVC whole-chip functional boot still running. Not native SDF/signoff; keep previously documented model qualification scope.

**Completed one-branch hold repair:** 43688957642 / 14db852f55f5a10b6a1de9c46267a9c3d6a07ce0 passed execution and targeted margin. FF326833/D min fast -0.010532353 -> +0.238576278ns; slow/typ min+.970938146/+.494271070; setup minslow2.186722755ns. Global setup2491/277/0 unchanged; fast hold164->163, global slow/typ4/25 unchanged. NewODB34a18678010315f75b7d4efd4bf39656f228d50a3133e337afb471302e934dda, state run/4-nssoc-onebranchholdeco/state_out.json; native14151119606 SHAfc2f5eae25f6938a3f50c108dd8b37d1b0ade94e655d4c014d779e96226abea7, derived14151584150 SHAb7eb5e15f8c7a68f70628197517297a92e0c2f241cd9bf896c56a98d5be1cc1b. Full receipt docs/evidence/rx-lane-one-branch-hold-20261115.json committed50d8393d8a2ec3bf5f6d695e25c58c0d680ab0c3.

**Completed120 hold repair but NATIVE NOT PRESERVED:** 43689570775 / b2a1b4014987cc6d87d1b45b409ce18ff4bf2712 passed measurement: all120 selected branches and40 boundary ports >=50ps in all3corners. Global hold slow/typ/fast0/0/3, WS+.126711/+.0783771/-.0320219ns. Setup2752/730/0 and worst-2.91509/-.829167/+.337456 unchanged. Source is boundary-hold candidate, separate from setup chain. ODB hash9627224813c5ce11cf43ffc3758d9f5f3b47802081ce587911e0944ccb0445f8 was measured but artifact absent due workflow typo selective-hold/run/; do NOT use as available continuation. New producer above will provide its own exact ODB/hash/archive. Derived14152410866 SHA99178273ba3342a351fd7e02c1f2ffb165e214ea052f87950b7699c857d4e123, full receipt rx-lane-selective-hold-unpreserved-20261115.json.

**Remaining3 fast hold paths:** FF160215/Q -> inverter738189/A/Y -> o21ai771053/A1/Y -> sameFF/D (-.032022ns). FF159728/Q -> nand2b770028/A_N/Y -> o21ai770030/A2/Y -> sameFF/D(-.023924ns). FF159728/Q -> firstload749466/A -> FF159887/D (-.000323519ns; inspect full path for later pins). ABCprefix $abc$735036$auto$blifparse.cc:397:parse_blif$, FFprefix $auto$ff.cc:337:slice$. First-load setup margins-1.000985/+.541972/-.024723ns respectively prevent blanket delay there. NEXT: measure later branch-specific pins771053/A1,770030/A2 and appropriate third-path pin on newly preserved120ODB, all corners before adding delay. Keep output40 port guards. Then combine successful setup+hold ECOs on ONE exactODB, remeasure, route and qualify independently. Never add proof numbers across branches.

**PHY full650 terminal failure recovered:** 43682293907/cf0a6547b53e7dd3b5961bd92bfcd74347cde78f failed electrical acceptance after simulator return0, diagnostics[],5236.924sec. Native14151930537 SHA1df16dedf119d2511bb1bbddf0881cc258db82bb9251f6015b61ec08c43b1423 stays cloud (~3.23GB); derived14151372439 SHAe4f73f8e9cfa6544455ddb87c479e91300962c6785ec34515efc615e2cfeddab. Fullreceipt shared650-upper-loaded-rejected-20261115.json exists. V/I nowPASS:53.471082uA,15.137884mV; phase18.576874mV FAIL30mV gate. Do NOT repeat unchanged transient or lower sampling/voltage gates.

**Saved-wave diagnosis43690199272/7e72ca8af74c22afab2b51bd22c39399b76ffcac PASSED:** artifact14151778970 SHAcf0d4b1250b6bd08ddfdc45eaa2bdc3864dd5d21122e517ea1b15ed94f80ca7f; receipt shared650-saved-wave-diagnosis-20261115.json. Full original raw hash/rows verified without new simulation. A/B need47.34375/42.65625ps to100mV, exceeding37.5ps gate. C/D weak130/128 samples; wrong10/31. X wrong392/765, Y20/765. C weak even at.9UI for2bits. Do NOT fix by moving readout phases. HBT211/212 VCEmin.383937926/.382331329V below.4V; minimum at20.81359375ns, collectors~.8834V,emitters~.5V. Remaining HBT screens pass. Physical source topology job above maps causes to real circuit. Stage-tail currents .001642..005251A (not lack of bias). Need actual analog redesign/load reduction; not full closed-loopPHY. Frozen external8GHz,256bit,originalloads unchanged. Contract native SHAef839c27e19bf819aa6894f2b99774b2202f6d7694c434f39a64ea9798cd8b86,1514075bytes.

Receipts for120hold andwave diagnosis committed71f3b153abe18a2addac571307d7f2c3e53f74cd. Experimental workflows remain on branches; do not merge into integration. Artifact downloads can90sec-timeout: cache-bust ?read=time.time_ns(), retry DOWNLOAD only. GitHub contents creation requires PUT (POST404); use git tree/commit + nonforce refPATCH for atomic multi-file receipts. Never print full large measurement dictionaries.

## 2026-11-15 continuation: 120 safe short branches selected from measured headroom
- Branchheadroom43688204095/headb3b454d06bdf4b958beeb1ec81acf750c2e3c80b SUCCESS, readonlyODB041148... unchanged. Derived14151417762 SHA256 45be2e9740d76eaedf39fd645e2fc03e8d0df761e84a481eae901c3863899668, all included member hashes verified on retry (first download timed out before mutation). Native14151293101 SHA256 7e80442fcdf3559693351b7f43879af3c0488459f0928784935db5f05fddf2f4. 738 branch and240 boundary reports. Full receipt docs/evidence/rx-lane-branch-headroom-20261115.json, commit91d7eb8320a0cd72b2aa90b268d404e0a06781db.
- Of123 branches,120 have min allcorner setup>=2.721937656ns. Three unsafe first-load pins: ABC735036/parse_blif738189/A slowsetup-1.000985146ns,fasthold-.03202194ns; parse_blif749466/A slowsetup-.024723336,fasthold-.000323519; parse_blif770028/A_N slowsetup+.541971803,fasthold-.023924308. Full exact instance names in receipt. These are NOT waived; do not add the same delay at their first-load pin blindly. Next investigate later branch-specific inputs along their short paths that avoid shared setup-critical cones, with actual through-pin setup measurements.
- Selectivehold43689570775/headb2a1b4014987cc6d87d1b45b409ce18ff4bf2712, branch codex/rx-lane-selected-short-hold-repair, confirmed in_progress. Exact boundaryhold43687226105/ODB041148... + exact completed headroom receipt authenticated. Asserts all738 report member hashes, target123 identities,3setupvalues perpin; selects120 with minsetup>=1ns (actualminimum2.7219), retains3 excluded targets with measured deficits. Adds1 native dlygate4sd3_1 ONLY perselectedfirst-load pin, verifying original source/master/pin/one-driver incidence; +120cells/+120nets, original locations/orientations preserved with FIRM/status restore. Remeasures all123branches/40ports/global3corners. result selected_margin_50ps and boundary_margin_50ps are independent evidence, accepted=false. All3 excluded branches remain open. Scripts selective_hold_flow.py/run_selective_hold_trial.py; artifacts rx-lane-selective-hold-derived/native.
- New setup-candidate short-hold repair43688957642/head14db852f55f5a10b6a1de9c46267a9c3d6a07ce0 remains outstanding on separate critical-loada4c18... candidate; never mix its proof with original hold-source041148... without combined remeasurement. CVCboot43681966595 and PHY43682293907 remain outstanding. Fullproduct closure still OPEN.

## 2026-11-15 continuation: guarded repair of newly introduced short branch running
- New one-branch43688957642/head14db852f55f5a10b6a1de9c46267a9c3d6a07ce0, branch codex/rx-lane-new-short-hold-repair, confirmed in_progress. Exact critical candidate43687918155/ODBa4c18bef... restored through all CTS/postCTS/five/bulk/critical archives with hashes. Flow measures FF326833/D max/min at all3corners BEFORE mutation, requires each setup>=1.0ns, then adds exactly1 native dlygate4sd3_1 only between nssoc_link2_load_stage/X and this D pin. Exact source/master, one-driver, pin incidence, cell/net +1 census; original cells FIRM during legalization, exact locations/orientations/status restoration. Measures3globalcorners plus same target after, records12 before/after target reports and50ps post margin flag. No result/closure assumed. Scripts one_branch_flow.py/run_one_branch_trial.py; artifacts rx-lane-one-branch-derived/native. Compile checked before dispatch.
- Branchheadroom43688204095, CVCboot43681966595 and loadedPHY43682293907 remain live at last check, not restarted. Need actual123branch/738reports before deciding old hold-candidate branch delays. These remain separate candidates; combine only with fresh exact-source measurements.
- Setup next investigation remains pcie_initialized_o buffer-chain latency (details below). Possible physical identity-preserving branch shortcuts: FF310786/Q to NAND749598/B currently through3noninverting buffers; NAND749598/Y to NOR761173/A through7noninverting buffers; NOR761173/Y to output301/A direct high-cap wire. A future experiment must prove upstream unique-driver chain consists ONLY of native noninverting buffers, preserve other loads, add dedicated branch stages and check all original incidence/placement plus global/port timing. This is NOT implemented or dispatched yet. Do not bypass actual logic, waive external-output timing, or assume it will pass.
- Full serialPHY/routed finaltiming/production still OPEN. Cloud-only execution/source persists, integration receipts on timing/combined; experimental workflow branches never merged.

## 2026-11-15 continuation: three-load setup gain includes one new hold violation
- Critical-load43687918155/headcbab9f4ea80d64416b82f74ffdf9f6506eaf395a SUCCESS, not accepted. Derived14151645842 SHA256 403109626190df03fae6ddf30de9991a48e0263594b68aab198c8dae05a18b7c and all included hashes verified. Native14151148148 SHA256 29cdc353d13b860be8033677e1b99448dbd8a7788c4c87336316023db66bfee9. ODBa4c18befb2a2bba68b351e0d8e2397174a9fac36a32765372c34108b1ba648c1, state run/1-nssoc-criticalloadeco/state_out.json. Receipt docs/evidence/rx-lane-critical-load-20261115.json, commit371da0de2ea5cf7baefad93d95e3cd0d362368c4.
- Slow setupWS -2.82678ns (R2R-2.76546), count2491; typ count310->277, WS-.829167/R2R-.330453; fast0/+.337456. Slew27/3/0 cap0 unchanged. BUT fast hold count163->164 (R2R123->124), WSstill-.128417. Slow/typ holds4/25 unchanged. Do not promote as nonregressive.
- Authenticated oldbulk/newcritical fast min report comparison found new negative path FF164048/Q -> nssoc_link2_load_stage/A/X -> FF326833/D, slack-.010532ns. Old report did not include this pair; do not invent its positive before margin. Stage output fanout7, cap.207109pF; this is a branch-specific new short path, not reason to add delay to all seven loads. Next measure setup headroom at FF326833/D and trial a native identity delay ONLY on that sink, with original incidence/placement protection and allcorner global+target checks.
- Current worst slow setup now output pcie_initialized_o from FF310786/Q (credits.rst_ni): fanout9719/9697/9694 -> NAND749598/B/Y -> rebuffer23797 -> ABC749701 -> fanout6496 -> ABC761170 -> fanout5553 -> ABC761171 -> fanout4833 -> NOR761173/A/Y -> output301/A/X -> port. Arrival5.776777ns, required2.95ns. NOR761173/Y cap.081869pF/slew.910980ns/delay.755831ns. Much delay is a noninverting buffer chain. Future option: verify native DB chain and source/load incidence, then dedicated branch buffering rather than indefinitely upsizing one worst path. Not implemented/dispatched yet; do not bypass any logic or alter clock constraints.
- Branch-headroom43688204095 still confirmed in_progress; CVCboot43681966595 and PHY43682293907 remain outstanding. Boundary-hold source041148... remains separate from setup candidatea4c18..., requiring exact combined-source remeasurement later. All full product gates remain OPEN.

## 2026-11-15 continuation: boundary hold targets pass, remaining123 branches measured next
- Boundaryhold43687226105/headbe6bcaff0adfd2b82d9addc94dff3fa592d73411 SUCCESS. Derived14151266033 SHA256 a302206994c7d36c5c4b434753f279e39fa179a669d83df04427c6c12ec5d67b and all included members verified. Native14151216414 SHA256 0bc6d45ae804f69c1fab2a7118d8ff9f30a18060b6a523e3789e118dca15a708. ODB041148ea5b9550a31c6ad2a804f0c192702a928dd114dde00aaa6bad835015e7, state run/1-nssoc-boundaryholdeco/state_out.json. All240 targeted max/min reports pass50ps, actual minimum166.517913ps. Full receipt docs/evidence/rx-lane-boundary-hold-20261115.json, commit63d4939fc17a7640ee399590df0b33dfc7db86c5.
- ORIGINALpostCTS source global hold slow4->0/WS+.0723328ns, typ25->2/WS-.0569229ns, fast163->123/WS-.128417ns. Setup WS/count and slew/cap unchanged (-2.91509/-.829167/+.337456,2752/730/0; slew27/3/0 cap0). This closes selected boundaries only, not all hold or routed timing. NOT the bulk/setup successor, do not merge evidence by assumption.
- Exact fast remaining123 paths inspected:46 self-feedback,123 unique first-load pins; others include FF164046/Q->FF326831/D direct, FF164050/Q->FF326835/D direct, FF376629/Q->hold24028/A feeding Ethernet SRAM bank2 enable, and short logic branches. New read-only43688204095/headb3b454d06bdf4b958beeb1ec81acf750c2e3c80b, branch codex/rx-lane-short-branch-headroom, confirmed in_progress. Restores exact hold source, derives123 source/first-load pairs from authenticated fast min.rpt, requires uniqueness/census. Measures738 through-pin setup/hold reports plus previous240 boundary reports and global three corners. Asserts ODB unchanged, repair_executed=false. Needed before branch-local delay ECO to avoid harming shared setup-critical paths. Scripts branch_headroom_flow.py/run_branch_headroom_trial.py; artifacts rx-lane-branch-headroom-derived/native.
- Critical-load43687918155/headcbab9f4ea80d64416b82f74ffdf9f6506eaf395a, branch codex/rx-lane-three-critical-loads, confirmed live. Exact BULK source43686936440/ODB891a32b... restored through CTS/postCTS/five/bulk member-hash chain. Adds3 identity buffer stages: FF164048/Q(7loads)->buf4, XOR739610/X(8loads)->buf2, NAND739624/Y(1load)->buf2. Checks exact source masters/pins/load census, only16sink rewires, adds3cells/3nets, original instances/positions/orientations unchanged with FIRM legalization/status restoration. Three global corners, no assumed gain. Scripts critical_load_flow.py/run_critical_load_trial.py; artifacts rx-lane-critical-load-derived/native. This is not boundary hold successor; eventual combined candidate needs fresh exact checks.
- CVCboot43681966595 and loadedPHY43682293907 re-polled still live. Do not duplicate/restart. Full serialPHY/routed finaltiming/manufacturing acceptance remains OPEN.

## 2026-11-15 continuation: 102-buffer setup improvement authenticated
- Bulk43686936440/head7bb39994a5c5f6514f7c5c04bededcce4d3da29b SUCCESS. Derived14151092505 SHA256 a6c277eb4a18afcd6a2b885d82682cade29ffdc94ecdf5c71ba2848872b34f44 and all included members verified. Native14151355146 SHA256 3ce3acc14505a075a653f0ba34244e3607775d0d9293f22cef12f7abd5207454 stays cloud. CandidateODB891a32b71b5b1bac5f29a02c0cbea7bd3853da5f26d6ecc356de7b086074a507, state run/1-nssoc-bulkbuffereco/state_out.json. Full receipt docs/evidence/rx-lane-bulk-sizing-20261115.json, commit69953f9303af4152c19272f296611c35bdd46118.
- Against its FIVE-buffer baseline: slow setupcount2643->2491, WS-2.88577->-2.87997ns; typical707->310, WS unchanged-.829167ns, R2RWS-.43522ns; fast0/+.337456ns. All holdWS/count unchanged-.298512/-.328194/-.322873 and4/25/163; slew27/3/0,cap0. Improved engineering candidate, still far from closure; placement RC only.
- Current slow max path changed to FF164048/Q = u_pcie.flow.packets.link_data[2], fanout7,cap.203140pF,slew1.272171ns,cell delay1.150456ns; XOR739610/X fanout8,cap.062533pF,slew.770453ns,delay1.086503ns; NAND739624/Y fanout1 drives wire4382/A buf8,cap.072567pF,slew1.319272ns,delay1.145560ns. EndpointFF164359. Bulk did not include the separately measured NAND load stage. Candidate next action: on exact bulk ODB, insert native identity stages at these three measured loads, verify actual driver/master/sink census and every allowed incidence change, preserve original placement, then three global corners. This is a proposal, NOT dispatched yet. Do not guess FF/XOR sinks or transfer old IO margins.
- Boundary hold43687226105 remains confirmed live; CVCboot43681966595 and PHY43682293907 remain live. Next inspect hold result (all240 target margins + global metrics) and continue on exact chosen DB. Any combination of bulk/loaded/hold changes requires remeasurement on one common candidate; workflows stay experimental, full serial PHY/routed timing/production OPEN.

## 2026-11-15 continuation: measured load stage complete, boundary hold ECO live
- Loaded driver43686390703/head3a0eca76fc6da5fe80b9fbf53e4f6a1faa1e65a7 SUCCESS. Derived14151076685 SHA256 0eaa5db784d72f1334cd42c6b12a054799cbbb514cf3027a3fd1c44e29c5de3d and all included members verified. Native14150583695 SHA256 25d94ea1e315bb80a32a81c6d0e0b46837fd5ce8d25337e9f008af8ce77f52c5. CandidateODB85aa1a5a9df637148d12ae94c1019ce5812f75e8ffc4e5adab25980ed74fe2b7, state run/1-nssoc-loadeddrivereco/state_out.json. Receipt docs/evidence/rx-lane-loaded-driver-20261115.json, committeded44a01f0410b7177d1625777dfef73f10ff63c0.
- Slow/typ/fast setupWS -2.87256/-.829167/+.337456ns, counts2643/674/0. Compared five-buffer counts2643/707/0. HoldWS/counts unchanged-.298512/-.328194/-.322873 and4/25/163; slew27/3/0,cap0. Engineering improvement only; no full closure.
- Boundaryhold43687226105/headbe6bcaff0adfd2b82d9addc94dff3fa592d73411, branch codex/rx-lane-boundary-hold-repair, confirmed in_progress. Exact ORIGINAL postCTS43682771828/ODB9b80811b... and same40 measured ports. Adds2 native dlygate4sd3_1 identity cells per port=80cells/80nets. INPUT: preserve external BTerm/net, move original input loads to delayed net. OUTPUT: preserve driver/internal load net, move only output BTerm to delayed net. Explicit before/after incidence and census checks, original cells temporarily FIRM during native legalization, exact original locations/orientations verified and placement statuses restored before writing. Native delay Verilog hash/function guard; original clock budgets and derates. Repeats240 targeted reports +all three global corners and records all_boundary_margins_50ps. Passing job alone not acceptance, result accepted=false. Scripts boundary_hold_flow.py/run_boundary_hold_trial.py, artifacts rx-lane-boundary-hold-derived/native.
- Bulk102-sizing43686936440 remains live, source FIVE-buffer successor; hold candidate starts originalpostCTS and loaded-driver candidate is another source. DO NOT silently combine timing evidence: eventual combined ECO needs exact restored DB and allcorner remeasurement. CVCboot43681966595 and PHY43682293907 still live; next consume all outputs and continue current-source R2R hold/setup fixes, routing/full serial integration. Full product still OPEN.

## 2026-11-15 continuation: 240 boundary reports verified, measured bulk sizing active
- Read-only boundary43686092687/headd2be8b515ce4182f6c1cfd5a126cc48f690bf3a9 SUCCESS. Derived14150292373 SHA256 439c3384d8e85c82239521693ee44350382cf82ed99c4bf7a983bd0a305bda45 and all included output hashes verified; native14151080522 SHA256 3f75962a03ccecbba0cf4d5be5bd9b1722fb0464be919099a8533b760d71de87 remains cloud. 240 reports, exact unchanged original postCTSODB9b80811b..., repair_executed=false. Full receipt and perport six-value summary docs/evidence/rx-lane-boundary-headroom-20261115.json, commit409cf33831daa08f3a55d6e47f68ad4025bb09d7.
- All40 selected ports have fast hold violations, but ALL have positive setup margin in every corner. Minimum setup1.978538513ns slow pcie_function_id_i[6]. training slow/typ/fast setup2.73060751/2.92852807/3.014322996ns, hold-.298511654/-.328194022/-.322873294ns. Ethernet worst fast hold-.248081446 at eth_txd_o[1], slow setup3.669423342ns. Thus target identity-delay ECO is supported by measured headroom, not an assumption; afterward require all240 setup/hold reports plus global metrics. Two native dlygate4sd3_1 cells per port are a candidate, not an established fix. Preserve all old incidence except explicit input-load/output-port branch rewiring; retain port clocks, original placement and SRAM/clock geometry; check50ps margin. Do not inherit these margins after other ECOs without remeasurement.
- Bulk sizing43686936440/head7bb39994a5c5f6514f7c5c04bededcce4d3da29b, branch codex/rx-lane-measured-bulk-sizing, confirmed in_progress. Exact FIVE-buffer successor43685594561/ODB613df4f... restored with all native member hashes and initial original CTS/postCTS dependencies. Derives102 unique non-clock buffers from authenticated negative slow max.rpt: fanout/ABC named, buf1/2/4, output cap>=.03pF and slew>=.3ns. Maps strengths1->4,2->8,4->16, asserts102 exact masters, unchanged instance/net counts and all incidence, verifies native identity functions. Three global corners after native legalization/fresh placement RC. Candidate not accepted; can improve setup or worsen hold and must be evaluated. Scripts run_bulk_buffer_trial.py/bulk_buffer_flow.py; artifacts rx-lane-bulk-buffer-derived/native. Source-only Python compile passed before dispatch.
- Loaded driver43686390703 remains live independently (originalpostCTS+9sizes+1buf2 NAND-load stage), not same baseline as bulk. CVCboot43681966595 and loadedPHY43682293907 still live. Do not duplicate runs or merge experimental workflows. Next consume actual results, implement measured boundary delay trial on an exact chosen baseline, and validate combined candidate before routing. Full product closure remains OPEN.

## 2026-11-15 continuation: five-buffer gain measured, next loaded driver trial
- Five-buffer43685594561/heade96a0f224c2d1e89d4a7b4398a1695a6239b6f23 SUCCESS. Derived14150651901 SHA256 9d8bc3997b63a084357b525af386bd003e240ad246489c112978c0b244f333b9 and all included members verified. Native14150412445 SHA256 086a5f3b6e6370c406e779a994e733ea5191419be0e0539aab94357d15d7f613. ODB613df4f452611b2779d5772d6e65f405ea93c509ce385e575cb43a2fb84f8a16, state run/1-nssoc-fivebuffereco/state_out.json. Full result retained in docs/evidence/rx-lane-five-buffer-sizing-20261115.json, commitf7e8cd4f04dd30e4ae163d922502e961dc3b509b.
- Slow setup -2.91509 -> -2.88577ns, count2752->2643; typical count730->707, WS remains-.829167ns. Fast setup unchanged+.337456/0. All hold WS/count and slew/cap counts unchanged at shown precision: holds4/25/163, slew27/3/0,cap0. This improves setup but is not closure. Current worst slow path now link_data[0]/FF164046 -> fanout8720 buf2,7591 buf1 -> NAND4_1 739624 driving wire4382 buf8 -> fanout3418/2618 -> FF164359. NAND output slew1.319ns and delay1.14556ns; available library has NAND4 only strength1, so cannot assume a nonexistent larger gate.
- Next experiment43686390703/head3a0eca76fc6da5fe80b9fbf53e4f6a1faa1e65a7, branch codex/rx-lane-loaded-driver-sizing, confirmed in_progress. Exact repaired baseline43682771828 again; reapplies prior5 measured resizes, adds8720 buf2->buf8 and7591/3418/2618 buf1->buf4, inserts native identity buf2 between exact NAND739624/Y and wire4382/A to reduce weak-gate input loading. Validates original two-terminal net topology, nine exact master changes and only one allowed incidence change; verifies all four native buffer model functions. Native legalization and all-corner global measurements; no changed clocks/derates/exceptions, no assumed gain. loaded_driver_flow.py/run_loaded_driver_trial.py, artifacts rx-lane-loaded-driver-derived/native.
- Boundary headroom43686092687 remains in_progress; it measures original postCTS baseline, not sized successor, so do not transfer endpoint margins blindly to later modified databases. Wait for actual40port/240report outputs before delay ECO decisions. CVCboot43681966595 and loadedPHY43682293907 remain outstanding. Full serial PHY, extracted routed timing and production acceptance OPEN.

## 2026-11-15 continuation: measure boundary headroom before hold ECO
- Current repaired min reports authenticated against derived14150425741: all4 slow holds are pcie_training_i and pcie_function_id_i[3],[13],[9]. Typical25; fast163 includes Ethernet outputs and123 register-to-register violations. Adding delay without measuring each corresponding setup path could worsen setup, so inspect both first.
- Read-only boundary run43686092687/headd2be8b515ce4182f6c1cfd5a126cc48f690bf3a9, branch codex/rx-lane-boundary-headroom, dispatched/queued. Exact current postCTS43682771828/ODB9b80811b..., source and every archive member authenticated. Three independent corner processes, 30 PCIe input ports and10 Ethernet output ports, max/min perport =240 required reports with actual path assertions. Original clocks/derates, NO repair. Requires final ODB identical to source; result repair_executed=false. Derived/native artifacts rx-lane-target-io. Scripts run_target_io_trial.py and target_io_flow.py. The driver retains a harmless old top docstring from its template; operative scope and ODB guards explicitly read-only.
- Five-buffer sizing43685594561 remains confirmed in_progress; do not restart. CVCboot43681966595 and PHY43682293907 remain outstanding. Next inspect actual outputs: only promote sizing with global all-corner impact evaluated, use exact boundary headroom before targeted delay insertion, retain original verification criteria. Product closure not achieved.

## 2026-11-15 continuation: current repair complete, targeted sizing live
- PostCTS43682771828/head486f80761d93074926fcfbfa2bac02b42aba9835 SUCCESS but timing NOT closed. Derived14150425741 SHA256 5a51bcb461b07af9822d4408ce2b5d4955e5c88bf619a1e5c720adcb3b64f643 and all included member hashes verified. Native14150655431 SHA256 33ed1d35db904f9f4184d6348e6076f9762c4d154a1c87a6da801c5c12bcaa2f remains cloud. RepairedODB9b80811bdaeb646b09207f83f33eda68a8f59273374001548a19996b92b36fce, state run/5-openroad-resizertimingpostcts/state_out.json. Receipt docs/evidence/rx-local-lane-postcts-20261115.json.
- Slow/typ/fast setup after -2.91509/-0.829167/+0.337456ns, counts2752/730/0. Hold -0.298512/-0.328194/-0.322873ns, counts4/25/163; slew27/3/0,cap0. Before fast hold14169, now163; slow setup -7.25265 now-2.91509. Placement RC only. Worst slow resetFF365787 -> five weak fanout buffers -> stage_write_at[33] D FF365715. Worst fast hold pcie_training_i -> FF183556. Do not treat green workflow as closure.
- Targeted experiment43685594561/heade96a0f224c2d1e89d4a7b4398a1695a6239b6f23, branch codex/rx-lane-five-buffer-sizing, confirmed running native trial. Restore exact current CTS+postCTS artifacts and every member hash; only fanout9423/9422/9421/9411/9409 buf1->buf4. Check original native buffer functions and unchanged pin incidence, legalize via native step, measure three global corners with original clocks/derates. No broad repair or assumed gain. Scripts run_five_buffer_trial.py and five_buffer_flow.py. Native/derived rx-lane-five-buffer artifacts.
- SupplementalCVCboot43681966595 and full650loadedPHY43682293907 remain live, not restarted. Next consume targeted and electrical outputs; compare all setup/hold/electrical metrics, continue routing and full integration. Entire product goal remains open.
- A repeated derived-artifact download timed out before any receipt mutation; first download and all hashes had already verified. Recorded the observed metrics directly; no native archives or checkout stored locally.

## 2026-11-15 continuation: current CTS baseline authenticated
- Read-only baseline43684347348/headb4e1bbd18752d30477150708708dc1cf052d3ffe SUCCESS. Derived14150050716 SHA256 a35d7e9273814bcfe35fc52c71b94bd01da403a81c97695ace1626b4aff14871 and every included output member authenticated. Native14150035761 SHA256 58ef5daa54f12005d91dc27292a0432ff3026c1a9213285c7183fab8eabb6bc1 remains cloud-only. Receipt docs/evidence/rx-local-lane-cts-baseline-20261115.json retains full result and critical-path census.
- Same unchanged CTS ODB d9915115add6829533fc17b2d5a70aac055d9255a7106bb7a3528fb5e3dbc53e. BEFORE repair slow/typ/fast setup WS -7.25265/-3.42718/-1.31988ns, counts3282/1468/339; hold WS -1.64545/-1.15705/-0.872643ns, counts528/1019/14169. Placement RC only. Worst slow path reset FF343483 -> weak buffer/handshake logic -> r2_pick_d[5] -> read_bank[2].pick_copy. Worst fast hold pcie_rx_valid_i -> FF173065/D. Multiple undersized buffer stages visible. These are pre-repair metrics, not regression comparison with an older repaired netlist.
- Actual all-corner repair43682771828, supplemental CVC boot43681966595 and full650 loadedPHY43682293907 remain live at this check. Do not restart them. Compare repair output against this exact baseline before targeted ECO/RTL changes. All product gates remain open until exact-source evidence establishes them.

## 2026-11-15 continuation: expose baseline timing while repair runs
- Exact fresh CTS read-only baseline dispatched 43684347348 / b4e1bbd18752d30477150708708dc1cf052d3ffe, branch codex/rx-local-lane-cts-baseline. Based postCTS486f807..., same authenticated CTS43681407524/new netlist, original clocks/corners/derates. Flow contains ONLY three BankedBefore measurement steps, no repair; final script asserts original ODB unchanged and records repair_executed=false. Artifacts rx-local-lane-cts-baseline-derived/native. Purpose: obtain current critical paths before long all-corner repair43682771828 ends; do not mistake baseline for repaired timing.
- Main repair43682771828, supplemental CVC chip boot43681966595 and full650 PHY transient43682293907 all re-polled live, not restarted. REST job log endpoints return404 while running, not evidence of stopped jobs. BrowserOS public GitHub page requires sign-in for logs; no authentication change attempted, temporary task tab closed.
- Next inspect baseline per-corner max/min reports and target actual current critical path, then compare with actual repair output. Full closure remains unproven and goal active.

## 2026-11-15 continuation: measured shared-metal resistance improvement
- Independent comparison 43683369026 / 21e0b505b64304331fa975cf7d7e8dda649ec6bc SUCCESS; artifact 14149726345 SHA256 11b3a1a05047373f8feb10d37479dfb883d28a9bfeb5f450b60f407a8ae8423e independently verified. Receipt docs/evidence/shared650-upper-metal-resistance-20261115.json includes full results, methods hashes and producer bindings.
- 168 same-endpoint passive conductor comparisons across C/E terminals of 277,280,281,286,301,304,305,310: new/old R ratios 0.641811183913082 to 0.87075324480824, hence 12.9247% to35.8189% lower. Example T277_E toT292_E 85.3762->54.7954ohm; T281_E toT162_D 131.97535->107.57695ohm. New RC differs authentically: old wires SHA686f1fa6c5f8410b2eaeb922963cfe57e8a57b438d1675334720119d0e8812c8, new215d277a3ba6fcced185f370c8515db4056954445e8bce762f945c3bb1a49acc.
- This is isolated passive metal resistance, not loaded amplitude/eye/bit correctness, intrinsic gate RC or full PEX signoff. Frozen full650 loaded test43682293907 remains live to decide electrical performance. Do not mark PHY closed from resistance alone.
- CTS43681407524 passed as recorded below; fresh postCTS43682771828 and CVC boot43681966595 remain live. All full-chip routing, final timing and full serial PHY requirements remain active/incomplete.

## 2026-11-15 continuation: exact lane-next CTS complete
- CTS 43681407524 / 88666de4aafead504019fb71481d1e38d7b8581d SUCCESS. Native artifact 14149545683 SHA256 4c1ab2dd97530657f013f16db7e33044e432db65a055bc5e0a3291e533ce5790; derived 14148897485 SHA256 bf83b20b47b1be23a427f4d363d09598c5a019dd5d4e97885b787764ac53e09e independently verified. result.json SHA256 f36eccd20b7dc09004e4b4dff5c68be4f05347f062ac9f527b3e42beab0a2a37. CTS ODB d9915115add6829533fc17b2d5a70aac055d9255a7106bb7a3528fb5e3dbc53e, state run/27-openroad-cts/state_out.json. Physical implementation elapsed 510.216sec, protected sources unchanged. Exact new mapping ec21ef3b... / 6cbaa20b... authenticated. Placement/CTS only; no route or timing acceptance.
- Do not interpret the mixed accumulated CTS metric dictionary as clean final per-corner timing. PostCTS 43682771828 clears inherited metrics and runs separate all-corner measurement/repair; it was re-polled live after CTS completion.
- Independent passive resistance comparison 43683369026 / 21e0b505b64304331fa975cf7d7e8dda649ec6bc, branch codex/shared650-resistance-comparison. Same diagnostic method as full composition; authenticated old/new native RC source artifacts. Runs independently to expose resistance effect before long transient ends. First attempt 43683295435 failed before downloading because workflow environment key was malformed; corrected GH_TOKEN variable name, numerical method unchanged. Long full650 43682293907 not restarted or modified.
- CVC chip boot 43681966595 remains live. No unobserved boot/PHY/timing success claimed. Next inspect numerical resistance report, actual boot outcome and exact new three-corner postCTS reports.

## 2026-11-15 continuation: new synthesis complete, SRAM simulator traces qualified
- Lane-next synthesis 43680923081 / b2e5e00493c2770f69f2ef37ac07d7010c9a8a74 SUCCESS. 116050 cells, 16 Ethernet 2P SRAM + 4 system 1P SRAM. Source native artifact 14149016224 SHA256 c1ea5a1f15feed9ca77c2b7073c3f63e901eb7844369902e1c5cbfdc89ce02fc. Mapping artifact 14148916459 SHA256 b00e8b7d71cc8a59a93c36e5ccb0d1010c616613055963bb762d763f7a6dcd51 verified. 63 mapped outputs. Netlist ec21ef3b50e5242565dbedf65c5a3232cba091d47faa3ab59e90717861131610; mappedJSON 6cbaa20bd3b0e911dcf66c4160a2130f18c1e0293ec57864d65341e052ca8eda. LOCAL_LANE_NEXT true. Not gate boot, CTS, route or STA acceptance.
- CTS 43681407524 is now actually placing new chip. CVC whole-chip boot 43681966595 is now in supplemental boot compile/run stage, not waiting for synthesis.
- PostCTS 43682771828 / 486f80761d93074926fcfbfa2bac02b42aba9835, branch codex/rx-local-lane-chip-postcts: dispatched, waits for exact successful CTS 43681407524/head88666de..., downloads exact named artifacts and verifies all member hashes, requires new mapped netlist above. Same interface_flow.py and check_timing_derate.tcl as prior banked flow verified byte-identical before creating branch. Three independent corner processes before/after repair; same 20/4/8/8ns clock constraints, propagated clocks, 5% derates. No routed/signoff claim. Old ODB/old hold evidence not used.
- Original SRAM FUNCTIONAL comparison 43682680141 / 9184ef61ce9b21d265117cb48aad71ff61bc2873 SUCCESS. Artifact 14149550703 sha256:f70e5f27cc72f2ceae944ed9d38f42f7e056d9ecadf2f1dd8513c100fdb8e106; result SHA256 2f844fb8258058e098f9cb7656161abe58b7088c6ac320514ea15ee0f16b2ff0; every compile/run log hash verified. Both actual 2048x64 1P and 256x16 2P wrappers (all five original model files unchanged). Full address write/read checks, four-state BIST/MEN/WEN/REN combinations, masked X/Z data, unknown addresses, sequential cross-port reads; CVC and Icarus traces identical, inverted A_DIN mutant rejected for each. Scope is directed functional comparison, NOT exhaustive memory-state/collision proof, analog SRAM Liberty/RC or native timing/SDF. Receipt docs/evidence/cvc-sram-functional-qualification-20261115.json.
- Running CVC chip boot predates this new SRAM gate; do not silently claim it consumed SRAM qualification. Next revision must explicitly bind/replay this gate before promotion beyond supplemental functional evidence.
- PHY full650 43682293907 remains live; new shared-metal effective resistance and frozen loaded test pending. Full product goal remains active/incomplete.

## 2026-11-15 continuation: new full650 electrical composition started
- Gate reduction 43681872344 / a0f8e83e27889b7ad8fa28993c452a8884714aaa PASSED. Native artifact 14149015728 SHA256 17c578b57dc780933d8b34e3f47a2c4280692cff922c6ad02e53d054e64d4cd6; derived 14148925763 SHA256 79bb3a11b2eb22eba2a35d89ee2bde4d452c18be1af0ee1f6140d8c4451681a2 independently verified. 250 port networks, 503 native simulator executions, 2 fault controls. Nominal resistor-network port reduction only; not full PEX/electrical acceptance.
- Full composition 43682293907 / cf0a6547b53e7dd3b5961bd92bfcd74347cde78f, branch codex/shared650-upper-full-composition, status in_progress. Strict new geometry/anchor/identity, new metal RC 43681301520, new gate reduction 43681872344. Frozen nominal_late external8GHz 256-bit test and all original electrical thresholds preserved.
- Before transient, new scripts/cdr_shared_resistance.py compares isolated passive-network DC effective resistance for C/E terminals of devices 277,280,281,286,301,304,305,310 to every physical anchor on the same conductor. Uses full resistor graph, sparse nodal solve with residual <1e-7, exact native labels and same endpoint inventories, analytical series/parallel controls. Reads old metal 43655950942 ONLY for comparison; actual composed simulation uses NEW metal. Report shared-metal-effective-resistance.json records all values and ratios, no assumed improvement and no acceptance claim. Results pending. Capacitors/intrinsic devices/gate R are intentionally absent from this diagnostic, present in full simulation as before.
- Mainchip synthesis 43680923081 re-polled live; CTS 43681407524 and CVC boot 43681966595 are both live, waiting on exact successful synthesis. Do not restart based on waiting. Next consume current actual artifacts/timing, not old source evidence.
- Full serial PHY, routed mainchip setup/hold and production acceptance remain OPEN. All execution/source changes cloud-only.

## 2026-11-15 continuation: gate reduction and exact chip functional boot dispatched
- Gate mesh 43681657324 / 6706e6c00e9d63aa4ff11c082c41ed06923a755a PASSED; derived artifact 14148691161 SHA256 cc1fbc40008751c9a106bbf92a91fd8f40e55731519905caaae4f6c43d578004 verified, native artifact 14148995276 SHA256 5f26d8c34c008dc59d992820c9b5f10c953b45aebe54d0e804066530e44c1a49. 200 MOS, four mesh resolutions. Not full PEX/electrical/PHY acceptance.
- Gate reduction running 43681872344 / a0f8e83e27889b7ad8fa28993c452a8884714aaa, branch codex/shared650-upper-gate-reduction. Current paired_current() copied from exact new mesh source; new mesh archives and exact GDS hash. Expect 250 networks, 503 native executions and two fault controls. After it passes, adapt full-composition template 5af3482a5382ec42f3d66694eea9f4f7c5887c2a with new paired_current(), NEW metal RC 43681301520 and actual new reduction artifact IDs/digests. Check shared-terminal resistance and run unchanged frozen 256-bit nominal_late criteria. Prior failure unchanged until actual new simulation.
- Supplemental CVC chip boot running 43681966595 / 4d0e9c12b692fe6297989ce1b62834cc0cada86a, branch codex/rx-local-lane-cvc-functional-boot. Based exact CTS source, waits for qualified synthesis 43680923081. Builds pinned unmodified CVC, reruns reset/data/X/mutation probes and all16cell qualification, uses original sim_logic_boot_gl.py --prepare-only, 4M cycles, packet-async + system-ethernet MBIST. New scripts/run_cvc_functional_chip_boot.py authenticates inputs and exact derived model b1280e76..., preserves original firmware/testbench, calls original boot_checks requiring all28 firmware checks + PCIe + MBIST. 14400sec runtime, actual compile/run and hashes retained. Original standard-cell library unchanged; only derived CVC model aliases delayed pins and excludes specify. Native gate/SDF/STA acceptance remains false; SRAM simulator equivalence and simultaneous-edge qualification remain separate.
- Synthesis 43680923081 and dependent CTS 43681407524 re-polled live, not restarted. New synthesis still pending; no setup/hold improvements claimed from incomplete run.
- Next: consume actual fresh synthesis mapping then CTS, run new postCTS all-corner timing; inspect actual CVC compile/boot evidence; continue new PHY electrical composition. All full-product completion requirements remain active and incomplete.

## 2026-11-15 continuation: fresh upper-metal RC and qualified functional simulator
- Latest graph 43680974890 / 17297fd48eb45504f19c15f517c7ba69fdd017af passed. Native 14148043395 SHA256 8bf417abc9ce9c1b030c02bd749d4f72c15134d3e86d7bfd59e2307ff1ec259b; derived 14148128097 SHA256 1b9b54eb2a11922da14262574c75a12b63fa6872ca667e29335d824648f05381.
- Fresh anchors 43681114908 / ada33327319b35ec53eea1b3cba17a30060b8c00 passed: 650 devices, 2046 terminals, 1428 anchors, 200 gate contacts. Native 14148427588 SHA256 6cebc4e20550ae05d2841f6c7d9dcb71e70ac5feab67dae08b7fe25dc6069e2b; derived 14148053860 SHA256 dd1a823739509bffac9a9296223908e5bbdca2a92377d638b1cf26feba3da2a3. Provenance verifies exact GDS, unchanged child geometry/annotations, additions only on M3/M4/M5 against original packed predecessor.
- Fresh upper-metal RC 43681301520 / a81e8c3d4f38a9f836e710dce22085e6de39b97c passed. Native 14148810524 SHA256 ee54cfd52b54b7ce963449a839280b0f31a68ddb152aa2b95dee061cd5f6434d; derived 14148765623 SHA256 856c6667b3f0d848a412669dfc439d0349218b160816a29332b44bd1e5aaa743. 28634 R, 18488 C, 7 MIM; both native orders identical, 13 wire + 9 MIM fault controls EACH order passed. Substrate/gate-poly full PEX and electrical acceptance remain false. First draft 43681274222 explicitly cancelled because identity artifact incorrectly pointed to anchors; corrected source uses separate graph identity artifact.
- Gate mesh RUNNING 43681657324 / 6706e6c00e9d63aa4ff11c082c41ed06923a755a, branch codex/shared650-upper-gate-mesh. Restores new physical GDS and new anchor/identity artifacts, SHA-bound. Next gate reduction and full650 loaded composition must use NEW metal RC above. Compare actual shared-net resistance before expensive loaded simulation; do not reuse M3-only electrical failure as new result.
- Lane-next synthesis 43680923081 / b2e5e00493c2770f69f2ef37ac07d7010c9a8a74 passed replay regressions and entered actual firmware/synthesis at 05:33:27 UTC. Pending result. Dependent CTS 43681407524 / 88666de4aafead504019fb71481d1e38d7b8581d, branch codex/rx-local-lane-chip-cts, waits for EXACT successful synthesis run/attempt/head, then authenticates source/mapping artifacts and every manifest output. It only implements placement/CTS, no boot/routing/signoff acceptance. No old netlist hashes or hold proof reused. On completion start fresh postCTS and all-corner measurements.
- CVC final cell qualification PASSED 43681457439 / 417631425fe12d0f0eb8b58b8014888d4f9ab424. Artifact 14147809768 SHA256 49a6a5c6f701ea3217219abd3c6a64843f477da5648f4f5150ad88952932dde4; cvc-cell-qualification/result.json SHA256 47fac2c78ed4af926dedbf83202c073766920239484b99791fa8631cdf1b98d0; all per-cell compile/run log hashes independently verified. 16 affected cells, 374784 reference trace rows, zero mismatches; D inversion mutant gives 524 mismatches. Derived library SHA256 b1280e76c1e322681066805af26b7405d93cae36b58de079045c85342b5b101f. Original PDK bytes unchanged.
- CVC scope STRICTLY derived zero-delay functional simulation: NSSOC_CVC_ZERO_DELAY enables explicit delayed-pin aliases and excludes specify sections (CVC rejects some ifnone edge paths even with +nospecify). Icarus original/derived reference retain specify sections. Bench serializes initialization/context pin transitions. This does NOT prove arbitrary simultaneous transitions, SRAM model compatibility, original native timing/SDF, full-chip gate boot or signoff. Earlier CVC failures remain recorded. Next implement strictly authenticated functional-only whole-chip boot wrapper using existing boot_checks and same PCIe packet-async/system-Ethernet MBIST gates; do not waive native boot requirement.
- No local source/CAD artifacts; all mutations on experimental GitHub branches, only continuation docs on timing/combined. Full serial Gen3 x4, routed mainchip setup/hold and production acceptance remain OPEN.

## 2026-11-15 continuation: upper-metal physical pass and fresh lane mapping
- Upper-metal physical run 43680484913, source 97150588f7cf9df96d32f61f32dd63ec4aa5c7e3: PASS. Derived artifact 14148078022 SHA256 11e1bbcf8883a46584ad10a12f96fba12c5179db1e6b6214662405bf66653ba5 verified in memory; physical/result.json SHA256 68a6405d61dd59aecb4c70aa399801fc3435c74860dedaf20b0ae614f7abf1a2. Native artifact 14148172598 SHA256 8325673484fce71cbbd9d2103e910d0e33810f2357cfc3e47db1d3cb3df5acc4 remains cloud-only. GDS 0e7b4d8da7e6de4bda98ea0a83d6dbb5ea78c73c89a60d5724ba44401c1a24c0. 560 DRC categories / zero markers, deep/flat LVS and fault controls passed. This is the 650-device CDR component, NOT full serial PHY or electrical acceptance.
- Fresh graph dispatched 43680974890, branch codex/shared650-upper-wire-graph, head 17297fd48eb45504f19c15f517c7ba69fdd017af. Restores exact new physical result and native artifact; no old geometry or RC substitution. Next anchors, metal RC and loaded electrical test.
- Lane-next synthesis 43679206297 failed ONLY at stale RX RTL hash assertion in check_predecode_mainchip_mapping.py, after synthesis. Both source hash assertions updated to qualified 2a345ba4082873f73fd8f308880a1f8d29651e24c12bbeaf9ac20b8f4082636e; explicit LOCAL_LANE_NEXT synthesis flag assertion added. Fresh full rerun 43680923081, branch codex/rx-local-lane-mainchip-synthesis, head b2e5e00493c2770f69f2ef37ac07d7010c9a8a74. Await actual mapping then fresh CTS/timing; do not inherit old netlist hold closure.
- CVC comparison 43680498124 failed: original Icarus vs CVC differs on sg13g2_dfrbp_1. Qualification bench changed multiple pins simultaneously while setting each context. Next diagnostic serializes each initialization/context pin transition with settling time, retaining all four-state contexts, all transition tests and negative control. Run 43681005264, branch codex/cvc-four-state-cell-qualification, head 54be3ed0e5c93953eed05e8b4295bbb32342a6a5. This does NOT waive the prior failure or establish arbitrary simultaneous-edge equivalence, native timing/SDF or chip acceptance.
- All execution remains GitHub-hosted; no local checkout or CAD artifacts created. Full PHY, routed mainchip setup/hold and production acceptance remain OPEN.

## Exact-semantics RX qualification PASS; fresh synthesis, upper-metal PHY and boot acceleration active — 2026-11-15

RX qualification43659882138/head7b3d47cd6bd0666f035f6c231f5edefb705ca1c6 PASSED: two full-module proofs+two formal mutations, eight300000-cycle traffic positives+eight mutations. RTL SHA2a345ba4082873f73fd8f308880a1f8d29651e24c12bbeaf9ac20b8f4082636e. Safeformal14139263805/dc706988935291203256217b6a5b998308dc5221fbb945af8ec0de7f033e15c5; safetraffic14140620761/61a03dadf61ee06baf66d73902cd5f29f375795ad057939e0b63c18486c0394f. Every result/log hash verified. Receipt rx-local-lane-mux-qualification-20261115.json. New gated synthesis43679206297/headc803c5c16a1defa5819448f804ebfcbc55af5ba4 on codex/rx-local-lane-mainchip-synthesis live, last in replay regressions. Exact qualification gate/define mapping; next fresh CTS/STA/native boot. Old hold-zero does not transfer.

Earlier RX-bank native boot43653859525 FAILED timeout19000s, artifact14146774814/a0f70b780a8396799538c69548aa59e028da95b2e2278bb98016c93168dbcd44. Native cell and compile passed;1.45Mcycles firmware starts,1.58Mcycles reached at wall limit. No boot acceptance, no inference of functional deadlock. Receipt rx-bank-native-boot-timeout-20261115.json. Do not rerun same expensive bound blindly.

WidenedM3 full650 electrical43657193496 FAILED actual frozen loaded gate, native return0 and diagnostics[]. Safe14140668784/597e5eaf0f3f1898bdcf51803450b299191ae5d5d67faf9d923dece6d1c43a43; native14140418589/3e15a7fe209b7324590f86b0848548d06047afe741dab7a898050f40f7d01f24, wave487fc0405a04ed0923ef1f48322a085a9db990e0259991e3246bd1e28c66ffd8. Original weak/wrong counts essentially unchanged; phase15.7984mV<30mV, VI46.9957uA<50uA. Receipt packed650-shared-widening-loaded-rejected-20261115.json. No acceptance relaxation.

New actual via-connected shared-net M4/M5 widening generator43679621675/head33b31b1de07150a96371636da46dbf0b4b9502e9 SUCCESS. GDS0e7b4d8da7e6de4bda98ea0a83d6dbb5ea78c73c89a60d5724ba44401c1a24c0, predecessor f93aa... . Onlylayers50/67 additions; originalgeometry/allvia incidence retained. Safe14148110652/e34dcbcda19e5f4674529286e9bdc123544286334c71c3b5b4cae0d2f10ae464; native14148040883/0816ff427334631d8024228670d543bc5d66efe8e1556677c9c8ce411ec599c6. Receipt packed650-shared-upper-widening-20261115.json. Fullphysical43679880662/head7eb77f81d326938394034792978eba56d14e2c75 on codex/packed650-shared-upper-physical live. Authenticates full priorM3 chain then exactupper successor; unchanged full560DRC/deepflat650LVS/fault gates. Next onlyafterPASS freshgraph/anchors/metalRC and actualsharedR before full loaded; do not reuse priorGDSproof.

Boot acceleration: original CVC compiler preflight43679446314/headf1348efb1d834f7a702b798f1f6ebd7b3fa682d8 failed actual nativecell (unsupported delayed timing pins), artifact14148210151. Also initialXbench injection missed because indentation; fixed with explicit assertion. Do NOT call CVC native-compatible. New derived-functional alias probe43679929283/head6449f0b850b748205aabe369b59a10626a4115b7 on codex/native-cvc-functional-alias-probe live. Separate generated model explicitly aliases ONLY exactpinned zero-delay $setuphold/$recrem delayedpins; originalPDK bytes retained. No SDF/timing/native-library acceptance. Probe crosschecks reset/data/X against originalIcarus and mutations. Ifpasses, qualify all16affectedcell types with exhaustivefourstate transitions before any wholechip use; never waiver. Compiler sourcecambridgehackers/open-src-cvc@1c5e043ec33ef6f1fdbf38565501c944893a83cf, license read, sourceunmodified.

Full serial PHY/closed-loop/PVT/qualifiedPEX, routed all-corner setuphold and production approval remain open. Work cloud-only; local workspace remains empty.

## Independent local cursor rejected; exact-semantics mux distribution qualification running — 2026-11-15

Current run43659882138/head7b3d47cd6bd0666f035f6c231f5edefb705ca1c6 on codex/rx-local-lane-next-qualification. Revised candidate retains master r2_lane and original synchronous reset-free copy register; only distributes the identical next-state mux inside keep_hierarchy. No independent cursor or changed reset semantics. Formal and eight300000-cycle traffic/mutation matrix running; acceptance pending. Default RTL remains unchanged without SOC_PCIE_RX_LOCAL_LANE_NEXT.

Previous run43659495266 failed before RTL execution because allowlist lacked new define and workflow was traffic-only; both adapter issues fixed. Run43659632740/head da44f20d6af407cdfdd5e353ce36536067dccde7 then failed full internal-state equivalence (384 unproven cells at dw4/s1) for independent local cursor with asynchronous reset. Authenticated rejection receipt rx-independent-lane-rejected-20261115.json. Do not waive unproven points or use this source. Its traffic job may still finish independently. Gated synthesis43659835754/head31bdc6eff5b9eaf0668808471344128a790fb553 was explicitly cancelled after proof failure, before CAD acceptance; do not resume this old source.

If new exact-semantics candidate qualifies, adapt gated synthesis branch to new RTL/head/run/jobs/hash, retaining log/digest checks. Build adapter already adds new define to synthesis and simulation allowlists and provenance mapping, with READ2 dependency; shell syntax checked. Replace outdated independent-cursor docs. Only then fresh native boot/CTS/STA, no old hold-zero transfer. WidenedPHY43657193496 and earliernewbankboot43653859525 remain live. Full serial PHY/routed timing/production remain open.

## Local lane next-state qualification dispatched — 2026-11-15

Run43659495266/head0b748a19699b473833a8808a145a5644c0ea9a21 on codex/rx-local-lane-next-qualification, based exact new-bank postCTS source c536109095cf62d8efcbde4ba9dc144e2e66fb89. Experimental SOC_PCIE_RX_LOCAL_LANE_NEXT replaces both staged-group and bank-group shared-D lane copies with local rotate/hold/restart logic in keep_hierarchy modules. Same asynchronous master reset covers pulses between clock edges. Original lane-copy implementation remains default; no clock changes or added pipeline stages. Full-module proof at dw4/s1 and dw8/s2, eight300000-cycle traffic cases, and existing ready-inversion negative controls run in cloud. NOT accepted pending actual outputs. First Git tree request timed out before branch creation; retried using affected-directory tree construction, then dispatched only once. No local files created.

NEXT inspect qualification artifacts and source hashes. If proof fails investigate actual failing equivalence, never weaken contract. If passing, map exact candidate with new define and establish fresh CTS/three-corner timing; do not copy old hold-zero evidence. New-bank nativeboot43653859525 and widened full650 electrical43657193496 still in progress. Existing full production goal remains open.

## Old-netlist placement hold zero verified; new RX-bank setup remains open — 2026-11-15

Final ECO43658104828/headbe37a6115e72e3571f78e4b5f839ba6672dcd90d and impact43658254135/head76f420cb751e986b3caff9e07330aba6c9f997f3 completed. All1584 target reports independently hash-checked and >=50ps. All three corners now zero hold violations with no setup/slew/cap regression. Fast worst hold +0.00019551ns (0.19551ps): very small placement-only margin, NOT routed signoff. Candidate ODB ca285517ffd5a36e3d7d2cd67d972e12c4371c0e47fb4cfb60116a3826899c01. Native14139565346 SHA9905b4d1b4774c8682fccd455eb047f70dbd20b1ca5f8e3b0f2bc2aa323f0226. Derived14138049695 and comparison14138388800 authenticated. See rx-final-short-hold-{eco,impact}-20261115.json. Setup remains -3.11156/-0.703858/+0.46195ns. No proof transfer to new RTL.

New RX-bank postCTS43656292239/headc536109095cf62d8efcbde4ba9dc144e2e66fb89 also complete. Derived14138143942 authenticated; receipt rx-bank-postcts-20261115.json. New ODB5ef26433964b06465a5f992471d47cc043c819a279de65f4538bcbf766d75089, native14138749599 SHAa1feb912816f6ffb13ff40798199073bd03ec7bb53fa85a2e9bbd04390775081. Slow/typ/fast setup WS -2.20198/-0.190781/+0.841564ns, counts2587/1/0; hold counts13/16/212. Critical reset-qualified handshake -> r2_pick_first_d -> r2_lane_d -> lane_copy D path. Next investigate local lane next-state computation with full-module formal and traffic gates before any mapping; retain reset and cycle semantics. New-bank boot43653859525 and widened full650 loaded43657193496 still live at last check; do not duplicate. Full serial PHY, extracted routing timing and production approval remain open.

## Final short-branch global impact dispatched — 2026-11-15

Impact43658254135/head76f420cb751e986b3caff9e07330aba6c9f997f3 on codex/rx-final-short-hold-impact awaits exactECO43658104828/headbe37a6115e72e3571f78e4b5f839ba6672dcd90d. Compares against verifiedlatefeedbackbaseline43656972871/native14138618413/76ac393d.../ODB1af420... . Existing all-corner setup/hold/slew/cap metricsandpropagatedclockchecksunchanged. No closureclaimed beforeactualtargeted+globalresults. Producer43658104828 stilllive atlastcheck.

NewbankpostCTS43656292239, independentnativeboot43653859525, widenedPHYfull650loaded43657193496 allstilllive withno completedresults. Do notduplicateorrestart. Next inspect finals; ifholdzero confirmallcornersandsetupnonregression, then continue setup/routing closure withouttransferring oldnetlistproof to newbankRTL. FullserialPHY/qualifiedPEX/PVT/productionremainopen.

## Globalhold3->1 verified; last measured short branch repair launched — 2026-11-15

Lateimpact43657092967/head38fb30e3c725cbdb44069357a69a24398ccae12c SUCCESS. Authenticatedsafe14138693271 SHA945d582f1e142c54521a3b762ad1261c89b634f8189196b4980da6d1152f25ed. NOregressions,targetedtrue. Fasthold3->1,WS/TNS-.00158362ns; setupunchanged. TypWS+.0940192->+.10981ns. Receipt rx-late-feedback-hold-impact-20261115.json. ExactacceptedengineeringODB1af420...; stillplacementRC, setupstillnegative, notsignoff.

Thirdbranch43657463628/head12669ba4c370c5eae2712a94f29ff5dda4e74552 completed6reports verifiedhashes. Derived14138177986 SHA6750609871aa84657f8f54eb1e4a655eb0b35a519bd5ed8a357517f57d045c9d. THROUGH778838/B2 slowsetup+2.871114016ns/hold+.362137884,typ+3.206366777/+.133547068,fast+3.392246246/-.001583622ns. Receipt rx-third-hold-branch-timing-20261115.json.

NewECO43658104828/headbe37a6115e72e3571f78e4b5f839ba6672dcd90d queued on codex/rx-final-short-hold-eco. RestorelateECO43656972871/native14138618413 SHA76ac393d782d6a18705c3d0061684facacba82502b7f6cea2d9ed45f3a8533c9 andODB1af420bd624b8448914f643aaa5a32589220bce31f87c7eb939b14a183c1a67d. Add2identitydelays onlysink778838/B2 fromFF165926/Q, preserveoriginalplacement/statuses/incidence. Measure1584reports=264targets*3corners*max/min includingallpreviouspins;50psgate. No passyet. NEXT dispatchwholechipimpact based38fb30... with producer43658104828/headbe37..., baseline43656972871/native14138618413/76ac.../ODB1af420..., prefixrx-final-short-hold-eco. Mustverifytargeted+globalandactualremainingholdcount beforeclaimclosure. PHYloaded43657193496/newbankpostCTS43656292239 remainpending.

## Two late feedback ECO targeted checks PASS; global impact pending — 2026-11-15

ECO43656972871/head83c740023a5b95f390c0d3923a6c5cafd398fbb0 produced all1578reports; everyreporthash independentlyverified and all>=50ps. Originalplacement/statuses/incidencepreserved,4nativeidentitydelays added on2laterfeedbackbranches. CandidateODB1af420bd624b8448914f643aaa5a32589220bce31f87c7eb939b14a183c1a67d. Native14138618413 SHA76ac393d782d6a18705c3d0061684facacba82502b7f6cea2d9ed45f3a8533c9; safe14139131529 SHA20f6d222cbf7f513c6abe2a41930805ca04552d2eee2c705fdda43ae914f1902. Receipt rx-late-feedback-hold-eco-20261115.json. TargetedPASS only; do notassertglobalholdcountyet.

Impact43657092967 stillnoartifactatlastcheck; wait actualcomparison againstbcc33...baseline. Thirdbranchmeasurement43657463628 stilllive,noartifact. Afterbothready, ifthirdbranchsetupmarginallows, useexactnew1af420...ODB fornextselectiveECO then remeasurealltargets andglobal; confirm noimpactregressionfirst. FullPHYloaded43657193496/newbankpostCTS43656292239 stillpending.

## Third residual hold identified; exact-branch setup measurement dispatched — 2026-11-15

Census43657314385/head4717859f79270dbdd22a1307003a310219f703d6 SUCCESS on codex/rx-three-residual-hold-census. Derived14138996569 SHA707333dec883f46332e1dcc6ee8c8731462e1e9d5d1dd25a9b6bbcfae8bb7e58 reads exact107repairODBbcc33... . Threefastnegativeendpoints:FF160423 -.020237ns andFF160725 -.012739ns (currentlatefeedbackECOtargets), plusFF162884 fromFF165926 -.001584ns. Thirdpath:165926/Q ->778838/B2(a22oi)->778838/Y ->778840/A2(o21ai)->778840/Y ->162884/D. Endpointslowsetup-2.765825ns, so blanketDdelayunsafe; measureactualshortbranch.

Readonly43657463628/head12669ba4c370c5eae2712a94f29ff5dda4e74552 queued on codex/rx-third-hold-branch-timing:6reports3cornersmax/min THROUGH $abc$734844$auto$blifparse.cc:397:parse_blif$778838/B2. Restores107repairrun43655839647/native14138157525/ee48d106.../ODBbcc33... . Nodelayyet. Ifmarginspermit, addtargetedrepaironlyafterlateECOresult then remeasurecombinedalltargets/globalimpact. Two-branchlateECOwillnotdirectlymodifythisthirdsink; sourceFF165926alsofeedsalreadyrepairedbanches, so actualnewcandidateglobalcheckstillneeded.

FullPHYloaded43657193496, lateECO43656972871/impact43657092967, newbankpostCTS43656292239 alllive atlastpoll. No successinferred. Keepfullproductiongoalactive.

## Widened gate reduction verified; fresh full650 loaded case dispatched — 2026-11-15

Reduction43656724764/head273fc4523ce4534b909d935f72296595575ce3ac SUCCESS. Authenticatedsafe14139110010 SHA82d9f0dd0500d462c3c759c2d39134bda6c2e948b4a7be1ac6fb64297c249a8f; native14138466871 SHAc2b2a9a471c6a619d331341c653600b00b94d8d9357c3cc4091cdf50913b485c.250networks503nativeexecutions2faultcontrols; nominalRportreductiononly. Source75nmmesh74660407bytes SHAa9f431888484de7883ff3a6cc9cd2b15286368214ecc25620ee52689205adcf8. Receipt packed650-shared-widening-gate-reduction-20261115.json. ExtrinsicpolyC/materialcornerqualification/fullnonlinearintegration remainfalse.

Fullcomposition43657193496/head5af3482a5382ec42f3d66694eea9f4f7c5887c2a queued atlastcheck on codex/shared650-widened-full-composition. ExactnewGDS/currentanchors/identity, freshmetalRC43655950942 native14138785042/dbba... safe14137894183/7dae..., newreduction43656724764 native14138466871/c2b... safe14139110010/82d... . Assemblesallfivepartitions, then unchangedGATE_PARTITION1 LOADED_CASEnominal_late256bits originalfrozengates/UI/step/stop andfull650devices. Original oldfailedwaveNOTreused. Needactualelectricalresult; no passclaimed. FullPHYclosedloop/PVT stilloutsidecurrenttestscope.

Latefeedbackwholechipimpact43657092967/head38fb30e3c725cbdb44069357a69a24398ccae12c live on codex/rx-late-feedback-hold-impact; awaits exactproducer43656972871 and comparesbcc33... residualbaseline. Candidate43656972871 andnewbankpostCTS43656292239 stilllive. AfterlateECOglobalcheck identifythirdfast hold viaactualnewmin.rpt/census; prior107repairhad3fastviolations, not2. Keepallremainingproductionrequirementsopen.

## Residual hold repair verified109->3; two late feedback repair launched — 2026-11-15

ECO43655839647/head08d99bb8bc95db8629648202c37e7a17c8121840 complete. ALL1566targetreports hashesverified and >=50ps; originalplacement/statuses/incidencepreserved. CandidateODB bcc33fa1a7c936d1e97ebea796a918fb86835307d4238f8d0a8deaaf2f61c407. Native14138157525 SHAee48d106b424c4557f87a774411cc2465496cbd116b149c69c9ae5a19cd6b8fe; derived14139075159 SHA91e40fb04509749b2487cb693e8486a2eae1b571d375f8e8652e2122d84e2511. Receipt rx-residual-short-hold-eco-20261115.json.

Wholechipimpact43655889301 SUCCESS; safe14137569320 SHA154e07160c16909548384e94a5f1da7790c40249ecc31f2dcb9aa7f68ef4b047. NOregressions, targetedtrue; fast hold109->3,WS-.0528166->-.0202371ns,TNS-3.11025->-.0345596ns. Setupunchanged. TypWS+.0476559->+.0940192ns. Receipt rx-residual-short-hold-impact-20261115.json. PlacementRConly NOTsignoff. Thirdfastendpoint remains toidentify; do notclaimonlytwoholds.

Latebranchmeasurement43656054797 SUCCESS;12reporthashesverified. Safe14138301042 SHA9f98fd3e026e6580d8d1314c1eb3777caf3e684a21c7a26b82cb48c95c3c4895; slowsetup isolated772052/A=+2.918188334ns,772804/A1=+2.928355217ns; fast hold-.020237146/-.012738810ns. Receipt rx-two-feedback-late-branch-timing-20261115.json.

Newtwo-branchECO43656972871/head83c740023a5b95f390c0d3923a6c5cafd398fbb0 live on codex/rx-late-feedback-hold-eco. Restoresverified107repairODB bcc33... then4nativeidentitydelays: sink772052/A from737260/X, sink772804/A1 from761429/Y. Fixedalloriginalplacement/statusrestore retained. Measures1578reports inclall261previoustargets+2latepins,50psgate. No passyet. NEXT dispatchwholechipcomparator based9aa1f0... replacingproducerwith43656972871 andbaselinewith43655839647/native14138157525/ee48.../ODBbcc33... . Targetboolean unchangedall_previous_and_residual_setup_hold_margin_50ps_passed. Inspect residualthirdhold fromlatestcandidatewholechip min.rpt/census beforeadditionalECO.

PHYreduction43656724764 andnewbankpostCTS43656292239 stillpending atlastcheck; goalnotcomplete.

## Widened gate mesh complete; native port reduction launched — 2026-11-15

Mesh43656489981/headb102cbfba2f92a61931ff4933e044cf2e6d0a918 SUCCESS. Authenticatedderived14139035003 SHA82727a08dace09c13efdaf97a64d50c639532308d12225491e35323f5402ea8e; native14138596148 SHAd141a35ef2b83ff433b0cfed7fcc4b52cb7db4af6d2de1e91b7ab28f24b85747. Fouranalyticreferences+fouractualmeshDC/currentconservation passed,50groups200gates200contacts. Refinementrelativechanges .00343038/.0217839/.00429767; nonuniform nonlinearconvergence NOTqualified. Nominalmaterial only. Receipt packed650-shared-widening-gate-mesh-20261115.json.

Reduction43656724764/head273fc4523ce4534b909d935f72296595575ce3ac queued atlastcheck, branchcodex/shared650-widened-gate-reduction. Uses exactnewgeometry/currentanchors/identity acquisition copied fromverifiedmeshsource; newmesh75nm native+safe digests. Existing250portnetworks(50groups*1/2/4/8/16partitions),503nativeDC/AC/noiseexecutions andfaultcontrols retained. No reductionpassyet. Next freshfull650composition with currentmetalRC43655950942 and frozenloaded test; old electricalfailurestillopen.

Timing107branchECO43655839647+impact43655889301, later2branchmeasurement43656054797, newbankpostCTS43656292239 remain live, no retries. Do not infer success from lackofartifacts. FullPHY/finaltiming/productiongoal stillactive.

## Current widened PHY gate/contact mesh launched — 2026-11-15

Gate mesh43656489981/headb102cbfba2f92a61931ff4933e044cf2e6d0a918 live on codex/shared650-widened-gate-mesh. Fresh actual GDS1640350bytes SHA f93aa21dc645e4396b8e230114ec36656399e35bed94a1095e58fc3b62e009fe from authenticatedgenerator43654184010/native14137186920, currentanchors43655485838/derived14138025358, currentidentity43655245035/derived14136829675. Sourceclosurepins refreshed. Existing actual200contacts/200MOS/50groups,600/300/150/75nm mesh,analytic70ohm rectangle and native currentconservationchecks unchanged. Material7ohm/square and15ohm/contact remain nominal, NOT PVT/signoffqualified. No currentmeshpassclaimed yet. Next inspect output then fresh portreduction/full650composition with newmetalRC43655950942 and frozen loaded transient; do not reuse oldgeometry acceptance.

At lastcheck107holdECO43655839647 and latebranchmeasurement43656054797 stillhave noartifacts and arelive; impact43655889301 waits exactproducer. NewbankpostCTS43656292239 also live. Existing provenmetalRCreceipt below; fullPHY/electrical/finaltiming/productionremainopen.

## Fresh widened metalRC PASS; new RX-bank postCTS repair launched — 2026-11-15

RC43655950942/headae914da1b8791477927d34ac8c8b50c060d2921a SUCCESS. Derived14137894183 SHA7dae990a1588017ff8d273dbb276a83134cbad90c9ae6690dde0bc7e5598aa13 independentlyauthenticated; native14138785042 SHAdbbaaa2f8d2dfeb5267bc08165541dd2587d74c9eb34f6010183513bd5ab2ae8 stayscloud. Fresh28634R18488C,7nativeMIM, bothnativeorders equal,13wire+9MIMfaults perorder. Receipt packed650-shared-widening-metal-rc-20261115.json. Counts equaloldgeometry do NOT implyequalvalues or benefit. Next freshgate/contact RC/full650composition on exactnewGDS and compare sharednetR/C then frozenloaded electrical tests. No electrical/fullPEX/fullPHY acceptance; substrateR/materialPVT stillopen.

NewRXbank postCTS43656292239/headc536109095cf62d8efcbde4ba9dc144e2e66fb89 live on codex/rx-bank-chip-postcts. Based exactnewRTLbranch37635e..., restores mapping43651528850 and completedCTSjob132627989572 of43653859525. Native14136884328/d97e80b... andsafe14137827409/cbe6f... exactCTSODB041e9a... . Verifiesnewnetlistff7ab... and20macros; old metricsdiscarded, original20/4/8/8ns and5%derates/propagatedclocks preserved. Existingelectrical+timingrepair flow with3cornerbefore/after checks. Bootindependentpending. Newnetlistresults cannotreuseoldercursorECOproof.

Older107residualholdECO43655839647, impact43655889301, twolatebranchmeasurement43656054797 allstilllive atlastcheck. Do notduplicate. No newholdclosureyet.

## Two setup-sensitive feedback paths: measure after fanout split — 2026-11-15

Current107branchECO43655839647 and impact43655889301 remain live; newPHY RC43655950942/headae914da1b8791477927d34ac8c8b50c060d2921a also live. No restart or acceptance claims.

Inspected exact native max/min reports from residualmeasurement43654879592. Excludedindex9 sourceFF160423(update_h_infinite) drives commonbuf737260; fastfeedback then takes772052/A->772053/B1->sameFF/D, while worstslowsetup takesfanout8646 and longcreditlogic toFF343661. Excludedindex11 sourceFF160725(ack_encoder.index[1]) drives commoninv761429; fastfeedback takes772804/A1->sameFF/D; worstslowsetup instead takes772693/A and longencoderlogic toFF160709. Thus delayingcommonfirstsink penalizesunrelatedsetup; investigate later isolatedbranches.

Readonly measurement43656054797/head45e1293cb0ad8ac9380de465f85759854592821e live on codex/rx-two-feedback-late-branch-timing. Exactunchanged combinedODB4f937eac...;12reports=2laterthroughpins*3corners*max/min. Targets $abc$734844$auto$blifparse.cc:397:parse_blif$772052/A (source737260/X) and $abc$734844$auto$blifparse.cc:397:parse_blif$772804/A1 (source761429/Y). Targetmanifest hw/soc/pnr/rx-two-feedback-late-targets.json. NoECOyet. If actualmarginspermit, repairthese on exact accepted107repaircandidate onlyaftertargeted+globalresults; current measurementbaselineexcludespending107repair, so remeasureallaftercombinedECO. Do notclaim2holdsclosedorsetupfixed.

##107-branch repair and whole-chip impact launched; MIM source guard corrected — 2026-11-15

Residual ECO43655839647/head08d99bb8bc95db8629648202c37e7a17c8121840 live on codex/rx-residual-short-hold-eco. Exact combinedODB4f937eac... restored from14137831182/1d8aa6f... . Adds214identitydelaycells only107 selected firstsink branches; indices9/11excluded from measured109list. Existingallplacements frozen/restored; originalmasters/incidence retained except exactsinks. Reports1566=3corners*2types*(40IO+111oldfeedback+3SRAM+107newbranches); 50ps targetedgate. Selectionmanifest rx-residual-eco-selection.json. No pass yet.

Whole-chip comparator dispatched on codex/rx-residual-short-hold-impact head9aa1f0b5831693257e9cda78bea99e377f10824b; awaits exact43655839647 and compares against combined109-hold baseline. Inspect actualtargeted result and globalregressions beforeacceptance. Existing setupviolationsremainopen.

PHY RC43655635850 FAILED before actualMIMextraction: cdr_mos650_mim_support.py line17 still pinned oldpackedGDSecae... . Allnewanchor acquisitionpassed. Updated singleexactGDSguard to verifiedf93aa... and refreshed sourcepins; unchangednumericalmethods/geometricchecks/faultgates. Successor dispatched with source ae914da1b8791477927d34ac8c8b50c060d2921a on codex/shared650-widened-metal-rc. No RC/electricalpassyet. Previousfailurederived14137970823 contains precise-actual-mim-geometry.stderr. Awaitnewactualresult.

## Widened PHY RC running;107 residual short branches selected from measured margins — 2026-11-15

Anchors43655485838/head2df206f2f4b66cd6bb9bd6a7529c9eeedea37298 SUCCESS:1428physicalanchors200gatecontacts2046terminals. Derived14138025358 SHA9edacef48d4e10df6e857dcff5e424b6e1e18ba8c7b72f158e88fa3ef4ab88c2; native14137404512 SHAfec8e0124d6d69e54ba765c1aa5b333eb32d7b33742324a9bb847dfc7b76f5e3. Fresh metal RC43655635850/heade0e7a5deb1257ffd31c89f3adf11e00be96226bb live on codex/shared650-widened-metal-rc. Authenticates exact new anchors/GDSf93aa..., all frozen numerical methods and both native orders/13wire+9MIMfaults each unchanged. No oldRC reused; wait for actual result, then new gate/full composition and frozen loaded test. Electrical/PHY acceptance still false.

Residual branch timing43654879592/head984477f89e1b72623d4bbcfa7832fd1617bf598a produced654 reports; derived14137813488 SHAbd70c3155b057557aa49282c0ff9af7cab0b349bea01df73b6eed8282516b327. ALL654 report hashes independently verified. Receipt docs/evidence/rx-residual-branch-timing-20261115.json.107of109 firstsink THROUGH branches have slowsetup>=1.940916419ns. EXCLUDE indices9(slowsetup-.476986915ns)and11(+.318118870ns); these are the two previouslyexcludedfeedbackpaths. Do not confuse newindices with oldfeedbackindices4/13. Next: selective2identitydelays per107branches on EXACT combined ODB4f937eac... using existingfixedplacement/status restoration, previous40IO+111feedback+3SRAM targets retained plus107new throughpins, rerun all3cornermax/min and globalimpact. Manifest hw/soc/pnr/rx-residual-branch-targets.json on source984477... maps source_pin/through_pin/endpoint_pin. No newdelayrepair dispatched yet; no residualholdclosure claimed.

## Fresh widened PHY graph verified; current terminal anchors dispatched — 2026-11-15

Graph43655245035/head0a3f9c8527c9aa7244bb1e97fc68ea85801d0b7e SUCCESS. Independently authenticated derived14136829675 SHA f7b62b079a2f8359ffcbdda903498567d7f082969e71cd4632733d364d0edee2:650devices2046terminals25ports113components on exact newGDSf93aa21d..., old_RC_reused=false. Native14136809573 SHA c312cea831aadfa66456abd3b732620cb82322599dfbad572592fdb5ff115bb6 stays cloud.

Next terminal anchors run43655485838/head2df206f2f4b66cd6bb9bd6a7529c9eeedea37298, branchcodex/shared650-widened-terminal-anchors, queued at lastcheck. Authenticates new graph artifacts/GDS/LVS, retains authenticated original packed predecessor for band provenance, independently checks exact newGDS, unchanged hierarchy/annotations/all retained children/non-M3 material and nonempty addition-only M3. Runs existing current-native anchor probes and fault controls unchanged. Needs actual outcome; no anchors/RC success claimed. If passes, adapt fresh metal RC to exact new anchors source, then frozen loaded electrical test. Do not reuse former RC.

Residual109 timing43654879592 still live (not restarted). Boot43653859525 remains separate; prior CTS receipt is not timing acceptance. All production closure scope remains open.

## Widened PHY physical PASS; new bank CTS complete; fresh graph launched — 2026-11-15

Verified physical run43654646137/head96e48b1938c13d6b875177e561e2499efd9338c6 SUCCESS: GDS f93aa21dc645e4396b8e230114ec36656399e35bed94a1095e58fc3b62e009fe, full560DRC zero markers, deep/flat650-device LVS and fault controls. Derived14137064874 SHA036daf19913f59ab61cb48427a2f9df61c6eb08122e2d3222ef4b3e22eae9771; native14137283857 SHA9be73184f06ad6186d50216ee9a4245fcccbafdfddd5052ceee5a8da37027ff4. Physical receipt docs/evidence/packed650-shared-widening-physical-20261115.json. Electrical/fullPHY/qualifiedPEX/finaltiming remain false.

Fresh conductor graph dispatched on codex/shared650-widened-wire-graph head0a3f9c8527c9aa7244bb1e97fc68ea85801d0b7e. Restores exact new physical archive, independently verifies full16-phase physical report SHA94d5fd7fdcd5f4bac673fcaddfb3e3069615fdea9071cfe01383dce70a750d37 and all native LVS bindings, then extracts actual new geometry. Old RC is NOT reused. Next: inspect graph then fresh anchors/metal RC and frozen loaded electrical tests; no benefit claimed before measurement.

New RX-bank CTS job of43653859525/head37635e0231e164dd2ba68d4b7397feceb91d569d COMPLETE; independent boot remains running. Derived14137827409 SHAcbe6f6921b81d781904bc594f3ac741986803fb2d27bb6cbc638680cc1f471e9; native14136884328 SHAd97e80b9340d239cc7775488a8ca971aa819482b96fb1c40892e5c17106ae94c; CTS ODB041e9a211b843cc07a90ddbabde1fb2484d4c0c1858c216c82c3f8e12964359c. Receipt rx-bank-chip-cts-20261115.json. Raw CTS metrics show very large setup/slew violations (slow setup ~-207million ns); NOT usable signoff or evidence of improvement. Needs existing electrical postCTS repair flow on exact new netlist and fresh RC/propagated-clock STA. Do not transfer old-source ECO acceptance.

Residual109 through-branch timing run43654879592/head984477f89e1b72623d4bbcfa7832fd1617bf598a confirmed running on codex/rx-residual-branch-timing. Uses exact combined ODB4f937eac... and654 actual targeted reports. Original census43654670959 safe14136858838 SHA34498b01b87909b6ed24c8ef616685d012f690c65de615e16a4cb9dbd69e0951: only2self-feedback of109, all109firstsinkpins unique, endpointslowsetup missing38/109 due capped reports. Next choose safe THROUGH setup margins before selective delay; no blanket terminalD delay. Existing hold109/setupnegative remain open.

## Combined internal repair verified:109 fast hold endpoints remain — 2026-11-15

Combined43653684598/head49d8a9aa95863bc35fb87a448583b8c77f6b4896 SUCCESS; all924targetedreports hashesverified and >=50ps. Previous40IOs+3SRAMA_MEN+111feedbackthroughpins retained, originalplacement/statuses preserved. ODB4f937eac00ff3936e6f6ed874db0af68cd92bd15ce9c31500a19c3b89db215d1; native14137831182 SHA1d8aa6f46257d545a933e33c0e764207a5ab26f42c00db75bcfc7e76dd38186a; safe14137771426 SHA60413cb246884b9b0fea20d73f5ef51306611885adc97ca26af257fe65747f3f.

Wholechip43653893556/head7017ab4224d6ec1cdc822d9d2b83722afd37dfe2 SUCCESS; safe14137641826 SHA42001e2588fc0ebc711ed7b5266c7fad425247941888e25af6f2312d272bbc8e. NOregressionsagainstSRAMbaseline. Fast hold227->109,WS-.0600474->-.0528166ns,TNS-7.4964->-3.11025ns. Slow/typicalholdremain0;typWS+.0476559ns. SetupWSunchanged-3.11156/-.703858/+.46195ns; TNSslow-3633.15->-3633.07,typ-195.907->-195.879ns. Receipts docs/evidence/rx-combined-internal-hold-{eco,impact}-20261115.json. PlacementRCscope only, notrouting/signoff.

Newresidualcensus43654670959/head42af61d9fda658447f725cd349bbb3836ed329ff, branchcodex/rx-combined-residual-hold. Reads exactnewnative+ODB and extracts109remainingholdpaths andknownendpointsetup; missingcappedpathsremainunknown. Inspect beforetargetednextrepair. NewRTLbankCTS/independentboot43653859525 remainsdistinctsourceandliveatlastcheck.

First widenedPHYphysical43654392314/head6784dbea... failedBEFOREnativeDRC inprepare_layout KeyErrorports. ActualnewGDSindependentgeometryand25textcomparisonpassed, but generationreceiptlackedconsumerportsfield. Correctedsource96e48b1938c13d6b875177e561e2499efd9338c6 retainsoldpackedproof portsONLYafterexacttop25labels/positions compareandrecordsprovenance. Sourcepins refreshed. Newphysical43654646137 branchcodex/packed650-shared-widening-physical live. GDSf93aa21d... unchanged. Do not classifyfirstfailureasactualDRCviolationorclaimphysicalpass. Frozen560DRC/deepflatLVS/faultgatesunchanged.

## Shared M3 physical candidate generated; full physical verification launched — 2026-11-15

Generator43654184010/headc765e2c7548d3e9a57c591b058a0b768208e2dff SUCCESS. NewGDSf93aa21dc645e4396b8e230114ec36656399e35bed94a1095e58fc3b62e009fe; native14137186920 SHA343b6f236d8d61683488dba3590727bbe5220c6c973da8af49fc89b6161bfd29. Proof14137047543 SHAef9a8bd5eea68273acc104e4f2a301b72106e9b400edc9c7d0c1042b812f6291. Tencomponents75/76/78/80/81/100/101/102/103/104, onlyM3added, alloriginalgeometry/toplabels/hierarchy preserved; via2/3 incidence unchanged, serializedregionsanddeletedpatchcontrol passed. Receipt docs/evidence/packed650-shared-widening-20261115.json. NativephysicalandelectricalacceptanceFALSE.

Physicalrun43654392314/head6784dbea92d889c19cc9d82b446575c55bcda45d, branchcodex/packed650-shared-widening-physical. Adapts established full560DRC/deep+flat650LVS/13fault checker WITHOUTchangingchecker/gates. Restores independentlyauthenticated original650schematic andpackedpredecessor, then authenticatesnewproducer/archives/GDS and independently verifies onlyM3addition/nooriginalremoval/top25labels/noextravia-incidence. Sourceclosure pins updated for script/workflow/currentcandidateconfig. Samepinnedruntime/per-executablehostedpolicy. Sourcecontrols gate thenactualphysical. FullfreshRCneededafterpassing; M3landingwideningmaynotaddressdominantlongrouting resistance, do notclaimIRimprovementuntilactualnewextraction. ConsidertracingfullsharedconductoracrossM3/M4etc ifdominantRremains, not arbitrarilychanging numericalresistors.

Combineddigital43653684598+impact43653893556 still live atlastcheck. NewbankCTS/boot43653859525 also live, no duplicatejobs. Allnativeworkcloudonly.

## PHY widening generator correction; current cloud jobs — 2026-11-15

Firstwidening43654034145/head77c6d895... FAILED at Existingmetalclippedcomponent75 beforewritingcandidate. Conservative.6umexclusion had clipped existing metal atoldspacing. Corrected sourcec765e2c7548d3e9a57c591b058a0b768208e2dff only appliesobstacleclearancetoNEWpatch and unionsunchangedoriginalmetal; doesnotwaivevia/netguards. Newpatch also clippedawayfrompreviousnewpatcheswithsame.6umspacing. Preservesexactoriginaltoplevelhierarchy/publictextlabels now (removedwrapper), recordsoriginalflattenedregionsbeforeinsertion andchecks serializeddifferenceonlyM3addition. New run43654184010 branchcodex/packed650-shared-widening. Awaitactualcandidate andthenfullphysicalverification; noacceptedlayoutyet.

RXbank CTS43653859525: candidatejob132627989572 liveNativefloorplanplacementCTS; independentbootjob132627989732 liveNativebootcompleteMBIST/firmware atlastcheck. Exactnewnetlist116097cells/20SRAM. Combinedinternalhold43653684598 job132627464946 live freshnativeSTA; impact43653893556 waitsproducer. Do notduplicatejobs; no combinedsignoffyet.

## Fixed feedback nonregressive; combined repair and new RTL CTS launched — 2026-11-15

Fixedfeedback43652982531/head11890797d11a032989772232d9308036a9388841 SUCCESS. All906reports authenticated/targeted>=50ps, originalcoords/orientationpreserved,statusesrestored. ODBf455e6f2ee80705a99f63edcfe539b58ff150c849fbe133030b97d7232d683a5; native14137301176 SHAa4092e336b653fa182f6f301fe9997f4a219de8896a04550ff0068598361161a; safe14136659596 SHA414ac92909c2c43eb221ca19df0fc76193c59b1e3f5761b67d7801198d410161. Impact43653022011/head9b8523bdad119cc8914d264c7870c79a67086f90 SUCCESS; safe14136923347 SHA538d7d40060224257a59afd333f9818ba411339e57959e37ea391bddde61fa4e. NOregressions. Fast hold230->112; slowTNS-3633.15->-3633.07,typ-195.907->-195.879ns. Receipts rx-feedback-fixed-hold-{eco,impact}-20261115.json.

Combinedinternalcandidate43653684598/head49d8a9aa95863bc35fb87a448583b8c77f6b4896, branchcodex/rx-combined-internal-hold-eco restores verifiedSRAMODB24b20bf... fromnative14136452503/41788e3a..., then adds same222feedbackdelays with alloldplacementsfixed/restored. Remeasures924reports:40IO+111throughfeedback+3SRAMA_MENpins,3corners,max/min. Need check alltargeted andglobal. Impact43653893556/head7017ab4224d6ec1cdc822d9d2b83722afd37dfe2, branchcodex/rx-combined-internal-hold-impact compares exactSRAMbaseline. No combinedpass yet.

NewbankRTLmainchip43651528850/head790a01e745ffa2a6b4b6db8e23a569749ddf06f5 SUCCESS. Mapping116097cells20SRAM63outputs; mapping14137116552 SHA05bdb7b2d6345c7010ea5ededb39aaa8c2cfc319ae05849a23d60914de31ad1e; native14136672988 SHAdcd55025a9b50aa0e0a949cf7515f3f02057fbcdce2fea229bb84afa0b2b8145. Netlistff7ab0c7c6b49770176105b8ff6fde1f07ba9c0cb08607e486549e2ebf714852; mappedJSON80ed8dd97816eeffb6bbd20a9552c507572bd8fe22d31e194cb4e315e396190d. ActualRXRTL6e873669... sourcehash, formal/trafficqualification preserved; mappedbootfalse. Receipt rx-bank-mainchip-mapping-20261115.json. Newphysical+independentnativeIcarusboot43653859525/head37635e0231e164dd2ba68d4b7397feceb91d569d, branchcodex/rx-bank-chip-cts. Restores/authenticatesall63files+allsourceinputs; original20/4/8/8ns/derates5% and20SRAM. Newmappedsource means oldECOtimingNOTtransferable. Track physicalcandidatejob andbootjob independently.

PHYgeometry43653771394/headb4c9dbacf4aad443036a51176e80da5549aa66ee SUCCESS; safe14137715411 SHA50023f405647f1587311a16a79627d87e4abdeff033e0a94f2d78d5540bd8218. ActualGDSdbu=.001um;108terminalanchors across10sharedcomponents. Same-layerlandings+nearbygeometrydiagnostic. Newphysicalcandidategenerator43654034145/head77c6d895db3f053ea5cfbd387571783555152408, branchcodex/packed650-shared-widening. Traverses actualM1/Via1/M2/Via2 toexistingconnectedM3polygons for10nets; growsM3by.6um whileclippingotherM3andforeignVia2/Via3 with.6umclearance; assertsownershipdisjoint andexactvia-incidence, preservesalloldgeometry, checksserializedregionsanddeletedpatchcontrol. Addsgeometryonly; needsnativeDRC/LVS/freshRC/frozenloadedtests. NoPHYpass. Currentgenerator uses wrappercell aroundoriginaltop, inspect port propagation fordeepLVS or preserve originaltop hierarchy in successor if needed. NativeGDSstayscloudonly.

## Comparator shared-metal resistance measured — 2026-11-15

SharedRC43653233927/head63712eb12c3564b26b5d388f249c497cb67f65a1 SUCCESS. Safe14137345574 SHA5a6bf4771186a69e12de69b0ff3e66631505954194f31cfdfe55c56f6b61bc3f; receipt docs/evidence/packed650-shared-net-rc-20261115.json. Exact priorpacked650model/wave sources preserved, no circuit changes.26nets:16interfaces+10internalcomparator nets. Sharednets explicitly use canonicalC/Ereference, NOTunique driver. X/Y symmetric metal: net40 reference lowerC -> upperE54.376..71.976ohm; net51 -> upperE57.016..79.896ohm; net62 interlowerE57.432..66.232ohm; outputcollector nets42/46 ~25..35ohm. Sharednets externalmetalC200..289fF. This supports investigating local shared-emitter/collector routing IR, consistent withactualterminalvoltage differences; NOT proof ofsolefailurecause or fullPEXqualification.

Next physical PHY work should inspect and reduce these actual local connections, preservingdevices/logicalnetincidence then rerunDRC/LVS/freshRC/frozenloadedtest. Originalpackedgenerator scripts/generate_paired650_packed_buffers.py atdbe212de5ae00036284f104d45742db443186f51 only moveswholebands and globaltrunks; internalsharedmetal unchanged bypacking. Do not resimulate unchangedcircuit or replace physicalR numerically as a purportedlayoutfix.

Useful exactcloud artifacts: packedGDSnative14131740193 SHA89585c334b2ae7f06b21e6851babe72ec11b5d1b4e0bee675c79090129193057 (candidate.gds SHAecae8ae8e49beea391b1d2575da6f5ac9ea01180550ae65fc786ddc6fd9ee193). Anchor native14132315920 SHA9040ef35d8eef59e932254e24c67950872be6050b644eccb0c01fe744a375e95; derived14131807306 SHAe5a2c6cbe1134e92f812b6abfe5d77bed5e797a7f4d8a3cbe6af9cf7c6af0cf4 contains terminal-anchors.json/unique-anchors.json/device-locations.json withcurrentpackedcoords. SharedXnet40 component75: device277E [1296375,2689692]metal10,278E[1326375,2689692],285E[1536375,2689692]; lower286C[1568225,2690940]metal8,287C[1598225,2690940]. Need read GDSactualDBU, don'tguessunits. Net51component76,tail62component78. FullmetalRCnative14132266869 SHA2c1771da6336f13c20583b40c1e602287ec63c60046b0c4daf1b2240c52e85f0. Keep native geometry cloudonly. Current-topologyreceipt is1.47MB: GitHubcontentsbase64 may beempty atthissize, use git/blob or authenticatedderivedartifact instead.

Digitalfixed-placement43652982531/audit43653022011 andbankmainchip43651528850 remain live at lastcheck. Do not duplicate/restart. ExistingclosedSRAMandunacceptedfeedbackresultsbelowremainexactsource-bound.

## Feedback hold improvement has setup regression; fixed-placement successor running — 2026-11-15

Feedback43651662225/headf389138917f81319a765ae1c0a59f4beda1a9f86 SUCCESS as execution; all906targeted reports authenticated and >=50ps. ODB46e684aa81b429420313e41b6372f09e29f448c8f9be1d4803cf5604a15ab2ca; safe14136622550 SHAa1784c16754a8ea28416fd352929711ce1fa569b2e1aa485a98fd7911dbc70d7; native14136149219 SHA6bef830f51894a5c7b4e91bf39c2b5b296fa0ec9c683a8aa23316d94b3c76bee. Wholechip43651746400 safe14136538142 SHA8b69418c9271daa0e40444944689a330bc20037f9b757902f3a13b113beb8744 found fast hold230->113 BUT slowsetupTNS-3633.15->-3633.89ns, typical-195.907->-195.949ns. Do not claim nonregressive or combine withSRAMECO yet. Both receipts rx-feedback-hold-{eco,impact}-20261115.json published.

Pathdiagnosis43652775879/head566df7bd44b755c7558286b3d65ba6ec8aa862fd SUCCESS; safe14136891101 SHAf2ee4b2d4b9462039fc998dee5e7cdbb25a3414d9bdefcd578f8445f9bc5a76a.887slow endpoint changes, worst additional-.016299ns atslice161655 from resetFF343468. Existing non-feedback-path wirecaps changed atbuf735888/fanout3848 etc, consistent with collateral legalization movement. Capped reports have missing endpoints; recorded, not treated as pass. Receipt rx-feedback-path-diagnosis-20261115.json keeps worst20percorner/fullpaths and residualcounts; complete diagnostic remains artifact.

Successor43652982531/head11890797d11a032989772232d9308036a9388841, branchcodex/rx-feedback-fixed-hold-eco: same111branch selection and222cells, same combinedIO baseline. Temporarily makes all original PLACED cells FIRM during legalizer; before write_views asserts ALLoriginalcoordinates/orientation unchanged and restores original statuses. PinnedOpenDB dbTypes.h explicitly defines FIRM asfixed. This is a hypothesis test, not accepted. Audit43653022011/head9b8523bdad119cc8914d264c7870c79a67086f90, branchcodex/rx-feedback-fixed-hold-impact waits exactproducer and compares originalcombinedIO metrics. If passes, combine with verifiedSRAMcandidate24b20bf... and rerun allpins+globalmetrics. Never transplant acceptance acrossODB.

PHYcurrenttopology43652502092/head3105aaa9a4a7529e90998726f90d8cd13e7e9d68 SUCCESS; safe14136617917 SHAdfb875af0f06d89181b52d37c4ba7d9f46d376ecb3350c8a58674a9591b001e1. Read originalfailedwave, reproducedallacceptancecounts, emitted650devicebindings/124HBTcurrent+voltage/16MOSstagecurrent groups. No new simulation or changed gates. Receipt packed650-current-topology-20261115.json. xd211/212 are samplerDmasterclock devices CN->SD_M_SE/SD_M_TE, not comparator. ComparatorX same-logical emitter terminals show unequal physical voltages (~25mV for some upper devices; shared lowercollector vs upperemitter tensmV), sourceADP/N Nx2 drives sixNx4baseinstances. Need distinguish wireIR/driverloading/switching before circuit/layout correction; original failure stillOPEN.

Mainchip43651528850/head790a01e745ffa2a6b4b6db8e23a569749ddf06f5 still pending at lastcheck. SRAMrepair proven nonregressive below remains separate. All native work in cloud.

## SRAM hold repair verified; remaining227 internal PCIe paths — 2026-11-15

Producer43651534065/heada77bed0723b12a73e8481c61b1214fa10edb41e2 SUCCESS. All258targeted report hashes independently verified; all40IOs+3SRAMA_MEN max/min3corners >=50ps. CandidateODB24b20bf3db1652ce562a1acebe43305ce79939d97e79a8cf3cafa2af302f0314; native14136452503 SHA41788e3ae61a6140c1bf8eba55e51c7c867c974777fee6965915a00e274de0ea. Derived14136238268 SHAd16716b02db5bb7eeaa9f3ebf30c1648e494486bd44c0c7e03ece7eeffebfe43.

Impact43651726319/head96cc07e4a22acdeb389304cd1516ca53b4c99f9f SUCCESS; safe14135684713 SHAa53116870ef5a1397b7aaf0aeac32bb730cb77142726f8911de9a2c42dcffff3. No metric regressions. Fast hold230->227,WS-.163726->-.0600474ns; typicalWS+.0124991->+.0345766ns; slowWS+.122274ns unchanged. Setup unchanged slow-3.11156/typ-.703858/fast+.46195ns. Receipts rx-sram-men-hold-{eco,impact}-20261115.json. This remains placementRC; no routed/signoff claim.

Independent feedback candidate43651662225/headf389138917f81319a765ae1c0a59f4beda1a9f86 and impact43651746400/head75dde1fefe21c2366166429e6dd4da68dac1054f still pending at last check. Baseline for feedback excludes newSRAMECO; merge only after candidate+global evidence then rerun combined. Mainchip790a01e... run43651528850 continues separately. Feedback measurement receipt docs/evidence/rx-feedback-branch-timing-20261115.json now published and all678report hashes verified. PHY unresolved scope unchanged below.

## Resumed: source guards fixed, selective feedback repair launched — 2026-11-15

Previous SRAM43650954563 FAILED before ECO (Wrong SRAM target). New source a77bed0723b12a73e8481c61b1214fa10edb41e2, run43651534065, resolves escaped OpenDB instance names with exact unique canonical-name and master guards. No pass claimed; inspect result and global impact. Physical baseline remains exact combinedIO ODBde8647caef5c3d38121edeb9d102f53e5406f77371ca161d254459aad58075ca.

Previous mainchip43646859306 passed qualification/replay but FAILED mapping verification because checker retained OLD RX RTL SHA c16d14... . New source790a01e745ffa2a6b4b6db8e23a569749ddf06f5/run43651528850 binds checker to actual formally qualified6e873669... and cross-checks qualification receipt. Fresh complete workflow dispatched; no new mapping/physical success claimed.

Feedback measurement43650299177 SUCCESS; safe14136175946 SHA0ace6b564979b7a796caa25ebc172ad4f6566ec90e7d6709620b7233d5d42af3. All678report hashes verified. All113 branches have negative fast hold (worst-.060047414ns). Slowsetup index4=-.476986915,index13=+.318118870ns; exclude BOTH. Remaining111 have >=2.363167048ns slowsetup. Selective candidate run43651662225/headf389138917f81319a765ae1c0a59f4beda1a9f86, branchcodex/rx-feedback-hold-eco inserts222identitydelaycells only on these111first feedback sink branches. Exact sourceQ and original pin incidence checked;40original IOs +111through-pins remeasured at3corners906reports. Uses SAME combinedIO baseline, not pending SRAM candidate. Do NOT treat independent ECO results as merged. Selection manifest hw/soc/pnr/rx-feedback-eco-selection.json on candidate branch. Need native targeted and wholechip metrics before acceptance.

Wholechip impact workflows being dispatched on codex/rx-sram-men-hold-impact and codex/rx-feedback-hold-impact, each bound to exact producer and combinedIO baseline. Inspect producer failure if impact fails; never weaken assertions or count upload success as timing success. Native data stays cloud-only.

PHY: packed650 loaded failure and transfer/headroom evidence unchanged; no new circuit correction accepted. Full PHY, routed mainchip, final allcorner timing and production qualification remain OPEN.

## All endpoint measurements complete; SRAM-enable ECO launched — 2026-11-15

EndpointSTA43650042619/head17e8f11d049bc4e4820d36304dad94980d9d6598 SUCCESS. Safe14136086263 SHAb0953c2d6bcaed5f74ecfdd64c3c6ec89263eca394aba719e7021a140b7eb965; native14135754127 SHA4a1e045fa6386b8f46c2173096d7a25790e17db2e84a2e0370710c8d58f90e87. All1380actual pin reports authenticated.221of230pins have NEGATIVE slowsetup; only3have>.8ns. Thus do NOT blanketdelay FF/D. ExactSRAMA_MEN slowsetup bank1+15.578088760,bank2+15.878623009,bank3+15.958136559ns (earlier instance-level worstsetup1.8ns was another macro pin). Receipt docs/evidence/rx-internal-endpoint-timing-20261115.json.

SRAMcandidate run43650954563, source801c3483d3421ce5a8f84dbf75c1bd101822e17d, branch codex/rx-sram-men-hold-eco. ExactcombinedIOODB de8647ca... via native14135173417/31bfe99bd985d6edfd9246d21c511edf2d17f17371d091158bf9299c909f824b. Adds2nativeidentitydelaycells per SRAM A_MENbank1/2/3 (6total), preserving alloriginalmasters/incidenceexceptthese3sinkpins; validates exactRM_IHPSG13_2P_256x16_c2_bm_bist masters. Re-measures40IOs+3SRAMpins at3corners,max/min258reports; indices40/41/42SRAMbank1/2/3. Needs globalimpactcomparison afterrun; not yetaccepted. FeedbackbranchSTA43650299177 remainspendingatlastcheck.

PHYtransfer43650709490/head981128901a00539bd851826cbf20fca88241237c SUCCESS; safe14134909226 SHA09e27055faf39590b13df3de50649e88b64a25a354fe8cc704823814cd09ae4b. Full receipt docs/evidence/packed650-input-transfer-20261115.json. At.6UI AD/CDcommonmode~1.83/1.82V, select0/1~1.187/1.186V; manyselectsamplesweak. Xdata/select bins still weak even with stronginputs; do not inferpolarityswap or retimeexpectedvectors. Need inspect actual comparator topology/headroom and choose next circuit/layoutchange (drivers seehighload, sampleoutputssettlelate). Currentgeometry alonepackingdidnotfixPHY. Exactfailednative retained inclallvectors. No analogcandidate accepted.

## Packed PHY diagnostics complete; transfer/headroom follow-up — 2026-11-15

Wave43650439557/head53702608c38ff76b405ce0b847334de0d5ce2573 SUCCESS; artifact14135194717 SHAb3f53858b2ec551b5e366819f2a3f77a0ea7640e1178f7a49b0e5bc5c8004f0f. Reproduced all original failure counts exactly before diagnostic bins. A/Bweak129/128 at.3UI become0at.4UI; C/Drequire~.5UI for >=100mV, Cstill2weak at.9UI. Xwrong125-135of255throughall diagnostic phases 0..0.9 UI; simply shifting samplingdoesnotfixX. Yweak219-225of255throughphasebins. Original frozen sampling remains failed; diagnostic bins are NOT acceptance changes.

DriverRC43650497998/head5aaed37cd0868f171c3f5fdd712af348cf7476a7 SUCCESS; artifact14136091128 SHA0bfdae44aae003cf8775795d4efdb05e638912669fc8bc39bc44f2ffa3ace568. Packed externalmetalC aqp/aqn495/546fF,cqp/cqn656/715fF,dqp/dqn646/703fF,adp/adn465/494fF. Metal-only maximumfirstmoments C25.4/35.9ps,AD25.7/30.3ps. Finite driver/device loading notincluded, so not fullsettling estimates. ActualADPdriver274nx2 drives6HBTbaseinstances nx4 plus rppd load; refer fullphysicaldevicebindings rather than inferinversion. Receipts docs/evidence/packed650-wave-diagnosis-20261115.json and packed650-drive-rc-20261115.json.

Follow-up transfer/headroom run43650709490, source981128901a00539bd851826cbf20fca88241237c, branchcodex/packed650-input-transfer. Same exactwave/source, expanded diagnostic perinputcommonmode, explicittruthcombinationbins, allnativeHBTsampledVCE/VBE. Reuses previously implemented helper at e5a8c892582b46d744ea4307d59ece4401a666e4 but retains packedsourceacquisition. No acceptance/data/polarity/phase modifications. Next choose concrete circuit/layout change based on actualinputtransferandheadroom; do not rerun unchangedfullPHY.

## Exact packed PHY waveform and driver diagnostics launched — 2026-11-15

Wave diagnostic run43650439557, source53702608c38ff76b405ce0b847334de0d5ce2573, branch codex/packed650-loaded-diagnosis. Adapted existing diagnosed-paired helper from9a814be2f84742f020e7c38ffd6e9a128c3e2daa; exact fresh packedrun43642783223/head15a63339b7a18be32652b2d481c863bd8936c208, safe14135338555/53940fed9591cbafab85792525eacc8f44fa3a41200874d57cea1b0a4a0fcfb2, native14135837525/fdee30ae9abd5a38d685b819d7cb3fc84840a3fab2cbef0f4aa8ded130997c0c. Authenticates rawbbd4390a3ecd4b3e15ecce9ccd34c5adb03c2eed1ad68f8853b34badcde1e9b6 and reader against protected source, reads all vectors, reproduces original acceptance counts before diagnostic phase bins. Native stays cloud-only; no resimulation or acceptance changes.

DriverRC run43650497998, source5aaed37cd0868f171c3f5fdd712af348cf7476a7, branch codex/packed650-drive-rc. Exact same packednative, contractef839c27e19bf819aa6894f2b99774b2202f6d7694c434f39a64ea9798cd8b86, modeldd2922e9bfecfbf085ff093099c43568c399df7e3c199063333aa7f7db1c4fbb. Computes actual16interface-conductor metalR/externalC firstmoments, checks650devices/28634R/18488C. Explicitly excludes intrinsic device/MIM load and finite driver resistance; do not mistake metalonlydelay for total signalsettling. Use both diagnostics to choose next circuit/layout fix. Helpers are on experiment branches (not timing/combined scripts); avoid404 by using exact refs.

Digital runs43646859306(mainchip),43650042619(endpointSTA),43650299177(feedbackSTA) remain live at lastcheck. No duplicate jobs started.

## Packed PHY failed actual electrical gates; feedback timing launched — 2026-11-15

PackedPHY43642783223/head15a63339b7a18be32652b2d481c863bd8936c208 TERMINALFAILURE. Native simulator completed return0 in4841.458s, diagnostics[], but original acceptance gates rejected. Safe14135338555 SHA53940fed9591cbafab85792525eacc8f44fa3a41200874d57cea1b0a4a0fcfb2; native14135837525 SHAfdee30ae9abd5a38d685b819d7cb3fc84840a3fab2cbef0f4aa8ded130997c0c (2.20GB cloud-only); rawSHAbbd4390a3ecd4b3e15ecce9ccd34c5adb03c2eed1ad68f8853b34badcde1e9b6. Sampler weakA/B/C/D129/128/130/128 of765;wrong0/0/10/31. ComparatorX/Yweak737/671,wrong384/52. Phase+.015770747V below+.03V; VIcurrent46.916uA below50uA, outputdifference13.3906mV above5mV. HBTxd0211/212minVCE.3838906/.3822837V below.4; MOSscreensallpassed. Packing helped some values but did NOT solve loadedPHY. Receipt docs/evidence/packed650-full-loaded-failure-20261115.json. Next PHY action: adapt existing diagnose_paired650_loaded.py and driveRC diagnostic to exactnewproducer/wave/model; diagnose drivers and latch timing from native wave. Do not rerun same candidate or loosen sampling/gates; do not label fullPHY accepted.

Internal timing continuation: new run 43650299177, sourcea07066b22af54900d82f7e1adfb42a51e6054597, branch codex/rx-feedback-branch-timing. Measures ALL max/minpaths THROUGH113unique first feedback gate pins, threecorners678reports, exact combinedIOODB de8647ca...; noECO. Manifest hw/soc/pnr/rx-feedback-branch-targets.json records sourceQ, throughpin, endpointD from actualnegativepath. Unlike -to D-only evidence, this isolates feedbackbranch while considering all downstream endpoints; no -from restriction. Endpointmeasurement43650042619 still independent. Await margins then split only proven-safe branches; blanketDdelayunsafe due121knownnegativeendpointsetups. RXbankmainchip43646859306 remains live at last check.

## Internal endpoint timing and branch diagnosis — 2026-11-15

Read-only run 43650042619, source17e8f11d049bc4e4820d36304dad94980d9d6598, branch codex/rx-internal-endpoint-timing. Restores combined-IOODB de8647caef5c3d38121edeb9d102f53e5406f77371ca161d254459aad58075ca; all230actual endpoint pins from authenticated census,227FF/D plus TXFIFO SRAMbanks1/2/3 A_MEN (NOT arbitrary SRAM data pins). Eachpin explicit -to setup/hold threecorners,1380reports required; noECO. Source manifest hw/soc/pnr/rx-internal-hold-targets.json pins exactcensus14134799084/SHA395a053dbc2c7809a2b33b4c8a9339310b2be89e5a2c103289d4c1ace6ff3f2c.

Critical new diagnosis:121of136known slow setup endpoint worst paths ALREADYnegative (worst-2.889165ns atslice163028), so blanketD-pin hold buffers would worsen setup.113of230fast worstpaths are self-feedbackFFQ->localmux/gates->sameFFD; all113have unique first feedback gate input (76A0,27A,10A1). Next safe candidate: measure allcorner max/min THROUGH each exact first feedback sink, then insert delay only on safe short branch, protecting long alternate input paths. Need actual through-branch setup evidence before mutation. Remaining117nonselfinclude3SRAMA_MEN and shared/control paths; inspect separately. Existing endpointSTA still useful but negative endpointsetup does not prove feedbackbranch unsafe or safe. No new internalrepair claimed.

## Residual hold census complete — 2026-11-15

Run43649796906/head2cf06c24822c96d805c9c6a7bd1a4229b043404d SUCCESS. Safe14134799084 SHA395a053dbc2c7809a2b33b4c8a9339310b2be89e5a2c103289d4c1ace6ff3f2c. Exact combinedODB de8647ca... has230remaining fast hold endpoints:227pcie_clk_i,3clk_i.97endpoint setup pairs absent in capped max report; need targeted -to actualdata pins for these before ECO. Worst Ethernet TX FIFO SRAM bank2 fromFFslice376654, fast-.163726ns; endpointworst slowsetup+1.846647ns. Bank3 fromslice376655 fast-.126689, slowsetup+1.859098. Next worstPCIe FFslice164433 self-feedbackQ->nand2->o21ai->D fast-.060047ns; setup absent. Full negative minpath text is in census.json, so derive actualterminal (especiallySRAM) from data-arrival section, not just instanceendpoint. Consider fast-corner-aware internal hold repair but do not regress slowsetup or waive clocks. New RXbankRTL physicalcandidate is still separate and source-bound.

## Combined I/O repair PASS; slow/typical hold zero — 2026-11-15

Producer43648980039/head95929ee677c79d9bab52f47c28f684eedb91795a completed SUCCESS. CandidateODBde8647caef5c3d38121edeb9d102f53e5406f77371ca161d254459aad58075ca; native14135173417 SHA31bfe99bd985d6edfd9246d21c511edf2d17f17371d091158bf9299c909f824b. Safe14135452833 SHA1748d71661772a2e02b2d0c10a0b0db0e85b871bdf8f8291b9fc4c2448979939. All240targeted reports authenticated, all40IOsetup/holdchecks >=50ps. Worst setup slow/typ/fast +.725850523/+1.675288439/+2.164728642ns; worst hold +.666230619/+.278011858/+.089237399ns.

Wholechip43649093686/head50a0bede8a6cfcf6cefbf5efef2e2971da05fb2f SUCCESS, safe14134844911 SHAb46a915fba9927d5174b07515b5c686168d1cae4f062fab1cb46312a53c7b8e4. No detected regressions against Ethernet-repaired baseline. HOLD COUNTS slow0/typ0/fast230, worst+.122274/+.0124991/-.163726ns. Setup unchanged2631/635/0, WS-3.11156/-.703858/+.46195ns. Receipts docs/evidence/rx-pcie-hold-eco-20261115.json and rx-pcie-hold-impact-20261115.json. This remains placementRC, NOT routed or production signoff.

Next residual internal hold census run 43649796906, source2cf06c24822c96d805c9c6a7bd1a4229b043404d, branch codex/rx-internal-hold-census. Authenticates exact combined candidate native/ODB; derives min/max endpoint pairing and full negative minpath text cloud-side. Inspect230remaining internal cones and missing setup margins before new repair. Separate RXbankRTLmainchip43646859306 and packedPHY43642783223 remain live at prior check.

## Combined PCIe ECO whole-chip audit queued — 2026-11-15

Run 43649093686, source50a0bede8a6cfcf6cefbf5efef2e2971da05fb2f, branch codex/rx-pcie-hold-impact. Waits for exact combined producer43648980039/head95929ee677c79d9bab52f47c28f684eedb91795a. Baseline authenticated native14134996872/e6893782d2385474b989299f52807ea4e4c11f4ffc06a6a366310fe3484d5832, ODB635f0e623eb202d845bde5a1f29f65466cf82f639dc2f7044aaabcac1451c203. All original allcorner metrics must remain present; checks propagated clocks and exact candidateODB duplicates. Records setup/hold count/slack/TNS regressions and40IOtargeted240check result separately. accepted staysfalse; production/routing still open. No fresh result yet.

## PCIe margins measured and combined I/O ECO launched — 2026-11-15

Measurement43648146822/head2a700b3a0965336cf1b09c224d98b3c2ba3a0b01 completed SUCCESS. All174native targeted report hashes verified from safe14135141187 SHAcd5e5e588cca03ddaef8d87d60d033cba2c0704fc5919272ba5cde9764e5b85d. All29inputs have positive allcorner setup, minimum2.073814869ns (function_id[3],slow); fastest hold worst-.194897100ns DLLP. Receipt docs/evidence/rx-pcie-input-timing-20261115.json. Exact measured baseline was training-only ODBdce675..., distinct from Ethernet ECO.

New candidate run 43648980039, source95929ee677c79d9bab52f47c28f684eedb91795a, branch codex/rx-pcie-hold-eco. Restores exact Ethernet-repaired native14134996872/SHAe6893782d2385474b989299f52807ea4e4c11f4ffc06a6a366310fe3484d5832 and ODB635f0e623eb202d845bde5a1f29f65466cf82f639dc2f7044aaabcac1451c203. Adds two identity-delay cells per29PCIeinputs (58total), preserving all original masters, port nets and incidences except the29firstsink connections; requires each original input one sink. Keeps previous training2+Ethernet20cells. Fresh detailedplacement/RC and allcornerSTA. Reports240targeted checks for40IOs: indices0:28PCIeports same as measurement;29training;30:37ethdata[0:7];38tx_en;39tx_er. Revalidates prior repairs, not just new inputs. No timing constraints relaxed. Must inspect targeted margins AND global metrics; no acceptance claim yet.

## Ethernet whole-chip comparison complete — 2026-11-15

43648249331/head084413ccae9d3bbc31a9fb3152bd57dedd35bdac SUCCESS; safe14135221490 SHA0a70dc71e4d47fb692cb040ea050ce2cd6d568ad9c80e86e0a20d6b58d2decb3. No detected metric regressions versus RX training-ECO baseline. Fast hold count269->259; worst-.227691->-.194897ns. Slow/typical hold2/28 unchanged; setup2631/635/0 and WS-3.11156/-.703858/+.46195 unchanged. Targeted Ethernet60checks passed. Receipt docs/evidence/rx-ethernet-hold-impact-20261115.json. This validates the twenty-cell Ethernet ECO only at placementRC scope; still not routed/production signoff. CandidateODB635f0e623eb202d845bde5a1f29f65466cf82f639dc2f7044aaabcac1451c203 is next combined physical baseline if continuing this source. PCIe input measurement43648146822 uses earlier training-only baseline: do not blindly transplant its path margins as new-ODB evidence. Can use them to propose an ECO but rerun exact final all-corner timing.

## Ethernet ten-output hold repair targeted PASS — 2026-11-15

Run43648005592/headf58d9ada2b6441b33ea8c27ff693e7a1e6c525f6 completed SUCCESS. All60targeted outputs/corners/setup-hold checks >=50ps. Worst hold slow/typical/fast +1.611442327/+.725703955/+.242022291ns; worst setup +2.147369862/+3.322887897/+3.968505621ns. CandidateODB635f0e623eb202d845bde5a1f29f65466cf82f639dc2f7044aaabcac1451c203. Safe14135181374 SHAa42354f2b51531f3e4bd645dccbc35776eaed567ead072579d830765440f7149; native14134996872 SHAe6893782d2385474b989299f52807ea4e4c11f4ffc06a6a366310fe3484d5832. Receipt docs/evidence/rx-ethernet-hold-eco-20261115.json. Source trainingECOunchanged, twentyidentitydelaycells only; actual io reports in native archive (safe has result hashes but report upload glob was old training glob).

Wholechip comparison43648249331 still pending at check; inspect its outcome BEFORE treating ECO as nonregressive. Targeted PASS does not close remaining setup, internal hold, routing or production signoff. PCIe targeted input run43648146822 still live; preserve its distinct baseline when using results. RXbankmainchip43646859306 and packedPHY43642783223 continue.

## RX bank traffic PASS, full RTL qualification complete — 2026-11-15

Traffic43646430563/job132605179099/head a5084f973055411c1891033fadf040b9055c9dfd completed SUCCESS. Exact RTL6e8736695b6fe059716fd90b5b8d969ca80a326f6c3a4705325bb5b7ec8831c0: eight300000cycle reference cases passed and eight ready-inversion mutations rejected. Artifact14135230618 SHA256f7b4174d19a9a4957ee989856c404cea9c93b2d2d3e16f27f36a04d1338f86bf; all16case logs authenticated and actual PASS/MISMATCH messages independently inspected. Receipt docs/evidence/rx-bank-local-traffic-20261115.json. Combined with formal14133878061/92b362a146853ab4680bbf46fd134d0970701524521077d286383fe57bff6918, exact new bank source now has both intended RTL qualification gates. This is NOT physical signoff or proof of setup improvement.

Next monitor conditional mainchip build43646859306/head05ad63a01140ff0fa8a2b75c78bbc5031a51b420; its dependency gate may now advance. Do not launch duplicate build. Then authenticate fresh mapping/native outputs and run source-bound placement/CTS/repair plus separate mapped boot. Existing PHY43642783223, EthernetECO43648005592/impact43648249331, PCIeinputs43648146822 continue independently.

## Ethernet whole-chip impact gate queued — 2026-11-15

Run 43648249331, source084413ccae9d3bbc31a9fb3152bd57dedd35bdac, branch codex/rx-ethernet-hold-impact. Waits for exact producer43648005592/headf58d9ada2b6441b33ea8c27ff693e7a1e6c525f6 success, then authenticates native/derived artifacts. Baseline is exact earlier RX training-ECO native14134159392/SHA92d72fe95c41b068bc255e7f9f7a3b0e7abaa415990ec57e948ccc246e7b2e26 and ODBdce675ce9aab6a7833fcb55ded416540b392affb065521ef53e3ce9d33d1d54c. Reads all-three-corner native metrics before/after, checks propagated clocks, matching candidate ODB copies, source identity, and every prior metric present. Records regressions and targeted Ethernet60-margin result separately; accepted remains false. No native archive downloaded locally.

## Targeted PCIe input setup evidence launched — 2026-11-15

Run 43648146822, source2a700b3a0965336cf1b09c224d98b3c2ba3a0b01, branch codex/rx-pcie-input-timing. Read-only restored RX training-ECO ODB dce675ce9aab6a7833fcb55ded416540b392affb065521ef53e3ce9d33d1d54c. No Ethernet or additional PCIe delay ECO in this run. Measures all29remaining PCIe input ports: dllp,error,eop,sop,data[0:7],valid,function_id[0:15], in that index order. Each receives explicit -from get_ports max/min at all3corners,174reports required; missing report/path fails. Report itself includes NSSOC_TARGET_PORT for reliable mapping. Original source/constraints protected. Derived artifact rx-pcie-input-timing-derived-* includes io-*.rpt; native output separate cloud-only. Await actual margins before repairing these inputs. Ethernet run43648005592 remains separate candidate from the same baseline; do not combine unverified results.

## Ethernet output hold ECO launched after full census — 2026-11-15

Census43647795434/heada6ec1164d5d9a7d8b5f680a25945d5355a64e687 completed. Artifact14133908959 SHA23328da860436b88901e552f79f6b6d6b1d9e8953f2b8a8001bc6e343e36470f. 269 violating endpoint union, 39 I/O endpoints; 126 endpoints (including PCIe inputs) lack setup endpoint matches in capped native max reports. DO NOT assume missing setup is positive: use targeted STA before touching PCIe. Receipt docs/evidence/rx-eco-hold-census-20261115.json. Ethernet10outputs all have three-corner setup evidence, minimum3.420857ns (slowbit7). Fast hold worst-.227691ns.

New physical experiment run 43648005592, source f58d9ada2b6441b33ea8c27ff693e7a1e6c525f6, branch codex/rx-ethernet-hold-eco. Restores exact training-ECO ODB dce675ce9aab6a7833fcb55ded416540b392affb065521ef53e3ce9d33d1d54c via authenticated native14134159392. Adds two sg13g2_dlygate4sd3_1 per Ethernet data bit[0:7],tx_en,tx_er (20total); preserves original output port nets, original masters and all incidence except ten output-driver connections. Native detailed placement then propagated three-corner STA and60targeted max/min reports. No clock/constraint changes. Derived upload retains result/native.log but original workflow report glob still training-*.rpt; actual io-*.rpt are in native archive and must be inspected cloud-side if needed. Not yet accepted; requires targeted margins and wholechip comparison before further promotion. No PCIe input change without targeted setup evidence.

## Remaining hold paths identified — 2026-11-15

Derived job43647574845 completed success, source f67516a6169da71b3841057daee9b8ce73c1b603; artifact14134294466 SHA25602cf38a2a13692d1f7ffa7dae7ebdb401228e055300f05b9f04dda30f03b45f8. Reads exact RX ECO native archive cloud-side; first three paths per actual min report retained. Slow worst pcie_rx_dllp_i->FFslice173055 -.014111ns; next pcie_rx_error_i->slice173056 -.000558; eop_i->slice173057 +.003425. Typical same ports -.156492/-.148541/-.145831. Fast worst is Ethernet output: FFslice371202->eth_txd_o[2] -.227691; slice371204->eth_txd_o[4] -.227516; slice170336->eth_tx_en_o -.226977. DLLP first sink hold23697/A; Ethernet bit2 ends hold23858/X driving output (priorhold23857 andoutput97). Next action: obtain paired all-corner setup margins and full violation census from existing native max/min reports before adding any delays. Do not apply repair based on min reports alone or conflate these with prospective RX-bank RTL candidate.

## RX physical input repair measured — 2026-11-15

ECO43646555578/head6a87c130412d272c700214201820da450f693fad completed successfully. Derived14133708950 SHA30f64d9adeecb122e49fdd218bc144870e6c93f6f7bb5f9985120233a2f5f8b5; native14134159392 SHA92d72fe95c41b068bc255e7f9f7a3b0e7abaa415990ec57e948ccc246e7b2e26. CandidateODB dce675ce9aab6a7833fcb55ded416540b392affb065521ef53e3ce9d33d1d54c. Input hold slow/typ/fast +.661808610/+.275306463/+.087556742 ns; setup +1.604881644/+2.232374668/+2.557558775 ns. Targeted50ps margin passed all six checks.

Wholechip impact43647032009/headac826ac70b0e7b38da19c967ce17f8744c5d7a5c completed. Safe14133763882 SHA7dc117cff52bea357c4ff48def96734c6ea81670a08eef32c6783c5506d61494. Holdcounts3->2,29->28,270->269; remaining wholechip holdWS -.0141112/-.156492/-.227691 ns. Setupcounts unchanged2631/635/0 and WS-3.11156/-.703858/+.46195 ns. SlowsetupTNS worsened -.01ns (-3633.29->-3633.30), explicitly preserved regression. Not wholechip acceptance, not routed closure. Receipts docs/evidence/rx-training-hold-eco-20261115.json and rx-training-hold-impact-20261115.json.

Next derived remaining hold paths run 43647574845, source f67516a6169da71b3841057daee9b8ce73c1b603, branch codex/rx-eco-hold-paths. Native archive remains cloud-only. Read returned actual min-path start/endpoints before next targeted repair. RX bank traffic43646430563 and conditional build43646859306 remain independent; packedPHY43642783223 still pending at last poll.

## RX bank formal PASS — 2026-11-15

Formal job132604800997/run43646311455 completed SUCCESS. Exact RTL6e8736695b6fe059716fd90b5b8d969ca80a326f6c3a4705325bb5b7ec8831c0: both full-module proofs (4DW1slot,8DW2slots) passed under equal-reset-copy contract, both ready-inversion mutations rejected. Artifact14133878061 SHA25692b362a146853ab4680bbf46fd134d0970701524521077d286383fe57bff6918; four actual logs independently checked against their hashes and proof/unproven messages. Receipt docs/evidence/rx-bank-local-formal-20261115.json. First run overall failure is only pre-simulation traffic harness allowlist error; corrected traffic43646430563 still running at check. Conditional build43646859306 must continue waiting for its exact traffic job. No physical acceptance yet.

## RX full-chip ECO comparison queued — 2026-11-15

Run 43647032009, source ac826ac70b0e7b38da19c967ce17f8744c5d7a5c, branch codex/rx-training-hold-impact. Waits (bounded45min) for exact RX ECO43646555578/head6a87c130412d272c700214201820da450f693fad to complete successfully, then authenticates fresh native and derived artifacts by exact producer IDs/head and GitHub SHA256 digests. Compares all available original all-path metrics in slow/typical/fast against exact original RX postCTS result14133259949/f508cef6faf940e32aea7ab50f8ac83e8ce158e2bd3789c86c46633c6ed29c9b. Requires original ODB identity, both native output ODB hashes equal candidate report, propagated clocks, every original metric present. Reports target pass separately and all regressions explicitly even if targeted50ps margin fails. accepted stays false: placement-only, not routed signoff. No fresh timing acceptance yet.

## Conditional RX bank whole-chip build — 2026-11-15

Run 43646859306, source 05ad63a01140ff0fa8a2b75c78bbc5031a51b420, branch codex/rx-bank-mainchip. This is a queued dependency-gated build, NOT a passed qualification or timing result. Before native CAD, require_rx_cursor_qualification.py waits for exact formal job132604800997/run43646311455/head d93e575991c560ec910925eee630f6555af26d81 and traffic job132605179099/run43646430563/head a5084f973055411c1891033fadf040b9055c9dfd. Each wait is bounded 45min; failure or unresolved deadline stops before CAD. Verifies completed-success jobs, exact source hash, complete case/mutation counts, each producer artifact run/head and GitHub SHA256 digest, and every case log against its reported hash. The old candidate's static formal artifact ID is intentionally replaced by new immutable producer run/head/job bindings; fresh artifact hashes will be recorded once published. No substitution of old proof allowed.

Then unchanged firmware/native-cell preflight, replay regression and full synthesis with twenty SRAMs execute, using original clock/architecture selectors. Native and mapping artifacts named rx-bank-mainchip-*. Native mapped boot and physical timing remain separate required gates. Do not merge the experimental workflow. Prior runs remain running, not canceled or restarted.

## RX input diagnosis and bank harness correction — 2026-11-15

Completed diagnostic run 43645678166, source 950a045c064f8b77b28f8cd4e89b6f7cb93af70e, artifact 14134236381 SHA256 21188dbe10d102293be8f744d404e9e9e76ee314caa1bc4055347dc01f6e6ade. Exact RX repaired ODB unchanged. Slow/typical/fast input setup margins +2.859017372/+3.015025139/+3.079114914 ns, hold -0.429313272/-0.417217821/-0.387760997 ns. Actual first sink hold23727/A, endpoint slice183541. These are placement RC, not routed signoff.

Dispatched source-specific two-delay ECO run 43646555578, commit 6a87c130412d272c700214201820da450f693fad, branch codex/rx-training-hold-eco. Reuses protected two-native-delay-cell method on exact RX database with original sink hold23727, verifies all original incidences and masters and preserves constraints. No passing result yet; inspect targeted six margins AND whole-chip metrics before adoption.

RX bank experiment 43646311455: formal job 132604800997 remains live. Traffic job failed BEFORE RTL simulation: inherited shell harness disallowed SOC_PCIE_RX_CURSOR_LOCAL_RESET. Corrected only allowlist (ef8d55353921691776a776a604de0ffab12a2975); workflow traffic-only head a5084f973055411c1891033fadf040b9055c9dfd, rerun 43646430563/job132605179099 live. RTL hash remains 6e8736695b6fe059716fd90b5b8d969ca80a326f6c3a4705325bb5b7ec8831c0. Bind future proof/traffic qualification to each exact job/head/hash, not overall first-run color. Do not promote before both pass including mutations.

Packed PHY run 43642783223/job132593819470 remains in progress. No restart or new acceptance claim.

## RX bank local-handshake experiment — 2026-11-15 continuation

Not signoff. The RX critical-cone diagnostic run 43645631518 identified the current worst slow setup endpoint as bank_byte[0][4], FF slice176645, from soc_pcie_rx_credit.v bank register update. Startpoint slice343468 is the reset-copy driver. Worst slack remains -3.111556 ns. Diagnostic safe artifact 14133831439 SHA256 91aa435f74fa67aa5d0a0d4f5335f25648de9d8e4edef8374edf186e9a8a931b.

New isolated experiment: codex/rx-bank-local-handshake, commit d93e575991c560ec910925eee630f6555af26d81. RTL SHA256 6e8736695b6fe059716fd90b5b8d969ca80a326f6c3a4705325bb5b7ec8831c0. For READ2, bank update/restart now use r2_handshake, matching the cursor's optional local reset tree under the unchanged equal-reset-copy contract. Default behavior is preserved. Full-module formal cases and eight traffic cases, including ready-inversion negative controls, dispatched via cloud-evidence-summary.yml. No physical improvement claimed; inspect both jobs before any synthesis promotion. Do not merge the experiment workflow.

Still live at this check: packed PHY composition 43642783223, RX training input timing 43645678166, CRC and RX physical/boot runs 43638590941 and 43641707777 (physical jobs completed previously; boot remains separate). All edits/execution remain cloud-side; no local CAD artifacts.

## 2026-11-15 — RX postCTS mixed timing result; exact next diagnostics live

RX postCTS43643048434/sourcedb35595f13bc3eb63890086789b93e252fbb4cb6 completed execution (1500.23s), NOT timing closure. After repair slow setup2631/WS-3.111556ns,hold3/WS-0.429313ns; typical setup635/WS-0.703858ns,hold29/WS-0.417218ns; fast setup0/WS+0.461950ns,hold270/WS-0.387761ns. Register-to-register hold0 slow/typ,230 fast/WS-0.163726. Slew26/5/2,cap0,fanout1348. Compared CRC-only: worst slow setup improves223ps but setup/hold counts regress; candidate not accepted. Exact repaired ODB3f0dea28cbacdfb5c3fdaff22abc9191cc589437c9a2fda4740e7ba5063d87bd. Safe14133259949 SHAf508cef6faf940e32aea7ab50f8ac83e8ce158e2bd3789c86c46633c6ed29c9b; native14133777129 SHA238cba66b6541bffa2407278ced7d453c64286bc5515a1d6e01939781f6f0c98. Receipt `docs/evidence/rx-cursor-postcts-20261115.json`.

Worst slow PCIe path starts reset FFslice343468 (quarantine.rst_ni alias), six fanout buffers, gates and long fanout tree, ends FFslice176645. New mapping/cone diagnostic **43645631518**, sourced1137c413b4809b8005a99d04a39858d7f275450, branch `codex/rx-cursor-critical-cone`; binds group endpoints AND every cell in worst PCIe setup cone to exact RX mapped JSON0924c5a8d60ff347f9d3673f09cdf53736c69fc9159de63391a52f483c2b1e2a. Do not infer source from net aliases alone.

Worst fast RX input hold remains pcie_training_i ->slice183541. NEW exact RX input setup/hold diagnostic **43645678166**, source950a045c064f8b77b28f8cd4e89b6f7cb93af70e, branch `codex/rx-training-input-timing`; restores RX CTS+repaired outputs and all hashes, unchanged constraints, measures six targeted paths before transferring the successful CRC-only two-delay ECO. Endpoint/source buffers may differ; inspect its own report first.

CRC two-delay wholechip impact audit43645375159 initially failed because archive has two DB copies (step and final), not one. Corrected audit43645500909/source910750ca23438de87aae533e793ae8529001ce4f authenticates BOTH exact paths and both candidate hashes; SUCCESS. Safe14133936596 SHAf3b0a993f0c876b286d3c0d426fcfe64a138705d5176efd9d90d9e3a968d198b. Slow hold1->0,WS+0.101977ns; typical17->16,WS-0.0756001;fast221->220,WS-0.226722. Setup counts/worst slack unchanged, but slow total setup TNS -3878.11->-3878.22ns is an explicit regression. Receipt `docs/evidence/crc-training-hold-impact-20261115.json`. Do not silently call allchip improvement/closure.

Packed full loaded43642783223/job132593819470 remains independently live. No full serialPHY/route/production signoff; all native work cloud-only.

## 2026-11-15 — actual training hold ECO closes targeted input in all corners

Run43644585495/sourcedea0de872cdbf0fa716d68b597033ac2ab23534f completed SUCCESS. Two native delay cells added, exact original incidence checked, legalized and freshly measured. Training input hold slow/typ/fast **+0.684289992/+0.317939460/+0.149620548ns**; setup **+1.618731022/+2.211832285/+2.521901369ns**. All six exceed50ps. This is a genuine source-specific physical input fix, NOT allchip closure. Exact candidate ODB8f1f22fc156621e4d96872f8eaa9134b11315d5a3a358226767facc57fe5358c. Source DB unchanged. Safe14134275067 SHAb84f9d66b6b988be6e0b8857ce4037c97752eaa39af00e0556085ed99c95517c; native14133434311 SHAb08e5099e538625c4cf30f58e231f62618c58aa6c962cf99f87417d4acfd8b5b. Receipt `docs/evidence/crc-training-hold-eco-20261115.json`.

NEW impact audit **43645375159**, source **f655c3580acff971385968a163b1ef02dd719b02**, branch `codex/crc-training-hold-impact`. Reads authenticated actual native candidate ODB/STA reports in cloud, compares every before/after corner metric against original CRC repaired run43639975405, explicitly reports count/slack/TNS regressions. Requires exact output ODB hash and all propagated clocks. No fresh timing result invented from ideal estimates; uses actual completed independent STA. On result inspect remaining violations and any regressions before adoption. Preserve native ECO for later route/equivalence; apply to newer RX only after identifying its own actual input endpoint and margins.

RX postCTS43643048434 and full packed loaded43642783223 still live. Full goal remains open; cloud-only native work.

## 2026-11-15 — training input setup headroom measured; physical hold ECO live

Diagnostic43643718087/heade54adacc0ae714b27c1449930cabe9dd3d3708e9 completed SUCCESS. Exact CRC repaired ODB unchanged. Targeted pcie_training_i setup slack slow/typ/fast **+2.872979641/+2.994712114/+3.046618223ns**; hold **-0.389348686/-0.360046655/-0.325918019ns**. Each of6reports contains one actual path. Safe14132724018 SHA6488ef8e34e5031740b5b719bc8300c5d0b5eec8439a6f74cfee13f7b1c5d9c1. Receipt `docs/evidence/crc-training-input-timing-20261115.json`. This is source-specific placement RC, not routed signoff.

NEW physical candidate **43644585495**, source **dea0de872cdbf0fa716d68b597033ac2ab23534f**, branch `codex/crc-training-hold-eco`. Adds two native sg13g2_dlygate4sd3_1 cells immediately before original hold23699/A, preserving original training port/net. Asserts original single-sink incidence, exact +2cell/+2net census and every original cell/master/pin connection except the one reconnected input. Native PDK model c4b8.../stdcell Verilog SHA28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4 verified: cell is buf(X,A), so no Boolean or cycle change. Then native legalization, updated placement RC and three fresh independent corner measurements. Require at least50ps input setup/hold margin; keep accepted=false for fullchip. Original clocks/uncertainty/input delays unchanged, no broad repair_design invocation. Native output retained for wholechip metrics/equivalence/route follow-up. Do not adopt candidate merely on native execution success or transfer it directly to newer RX source without own measurement.

RX timing43643048434 and packed loaded43642783223 remain independent in-progress jobs. Goal remains open; all native work cloud-only.

## 2026-11-15 — input timing diagnostic CLI directory fixed

Targeted diagnostic43643389576/sourcec8b49701b0800591dc951187b56ef5cb954d54ef failed before STA: LibreLane requires the --force-run-dir directory to exist. Actual CTS/postCTS source authentication and extraction had succeeded; CLI rejected missing input-timing/run. Added explicit mkdir before subprocess (same pattern as existing native repair driver). No physical design, input constraints or acceptance change.

NEW diagnostic **43643718087**, source **e54adacc0ae714b27c1449930cabe9dd3d3708e9**, same `codex/crc-training-input-timing` branch. Inspect exact six targeted setup/hold reports and source invariance before any delay ECO. Previous failed run supplies no timing evidence. RX postCTS43643048434/job132594638172 and full packed loaded43642783223/job132593819470 confirmed in progress this turn; no restart. Full goal still open, native work cloud-only.

## 2026-11-15 — targeted training-input setup/hold diagnosis dispatched

NEW read-only diagnostic **43643389576**, source **c8b49701b0800591dc951187b56ef5cb954d54ef**, branch `codex/crc-training-input-timing`. Restores authenticated CRC CTS and complete repaired postCTS43639975405 outputs, requires repaired ODB568dfa2f110b6813d316087b6249340bedd4c831b95bf13d6224014b49c6afb1, then runs three separate native corner STA processes with explicit `report_checks -from [get_ports pcie_training_i]` for max/min. Original clocks, derates, input delays and physical database remain unchanged; source hashes verified after execution. Each of six targeted reports must contain actual paths. This measures setup headroom before a possible hold delay ECO; it does not itself modify cells or fix timing. Do not infer setup headroom from missing paths in the truncated standard report.

Flow `hw/soc/pnr/input_timing_flow.py` extends existing guarded SingleCornerSTA, appending reports after native corner.tcl write_libs (upstream LibreLane3.0.5 source checked). Worker `scripts/measure_crc_training_input.py`. Experimental workflow must not merge. If execution fails, diagnose exact stage; no acceptance waived. A successful diagnostic is only for exact CRC candidate, not automatic proof for newer RX source.

RX corrected postCTS43643048434/job132594638172 and packed loaded43642783223/job132593819470 are independently live from current checks. Full goal remains open; cloud-only native work.

## 2026-11-15 — RX postCTS input-address mismatch corrected; fresh run live

Initial RX postCTS43642916374/source219de71d65ac179920bd8eba0505dc9f00738032 FAILED before CAD execution. Its workflow still downloaded CRC source14131535375 and mapping14130736810 while the restore helper correctly required RX hashes. Source authentication rejected the mismatch. No timing result from that run exists. Corrected only the two artifact addresses to RX14132027737/14131928219; no identity check or timing gate removed. NEW run **43643048434**, source **db35595f13bc3eb63890086789b93e252fbb4cb6**, same `codex/rx-cursor-chip-postcts` branch, job132594638172. This supersedes the earlier live handle. It still consumes exact RX CTS43641707777/job132590504077 and retains all clocks/derates/repair settings.

Packed full-loaded43642783223/job132593819470 confirmed live in composition/transient step. Do not restart either job merely because no intermediate artifact is available.

Additional CRC report inspection: worst hold at all3corners is pcie_training_i ->slice183526, with two inserted delay cells; residual slow/typ/fast -0.389349/-0.360047/-0.325918ns. Standard max.rpt contains NO training input paths, because report is truncated to other worse paths; this is not evidence of available setup margin. Before any targeted extra delay ECO, explicitly measure this input setup/hold in all3corners on the exact new RX repaired database. Preserve external delay and clock uncertainty constraints. Existing repair used max_buffer_percent50 and max_iterations1000; its log reports unable to repair all hold checks and186 inserted hold buffers, not proof that the total buffer limit was reached.

Full goal remains open. All native work stays in cloud.

## 2026-11-15 — RX CTS complete; exact new three-corner repair executing

RX physical job132590504077 in43641707777 completed SUCCESS, source62db42e598ccca15b5d51f202b2c5b52ab33b976. Same twenty SRAMs,356 authenticated outputfiles,596.51s, protected inputs unchanged. CTSODB2d7f284e5a22dcaced71be4bcf1956f5d6d00373653d6a0217c1b4c694271b69. Safe14132319537 SHAf68456d7af8c3cc649cee632a11bce69723b7a948bd8247050284156adca7c86; native14133215435 SHA88a6068cd6374965d52e0a72f6b77466fd3a0fcd7f80d1a0aaf8438afa9ed314. Full receipt `docs/evidence/rx-cursor-chip-cts-20261115.json`. Independent native gateboot remains pending, not inherited from another source.

NEW RX postCTS run **43642916374**, source **219de71d65ac179920bd8eba0505dc9f00738032**, branch `codex/rx-cursor-chip-postcts`. Restores exact completed physical job and all hashes; requires exact new CTSODB,20macros, unchanged clocks/5%derates; discards inherited metrics. Original three independent before/after STA corners and electrical/setup100/hold1000 repair retained. Compare actual RX results against CRC-only43639975405 only after this completes; CRC had slow2548setup/-3.3349ns and fast221hold/-0.325918ns. Never lower clock or waive I/O hold to claim closure.

Packed full loaded simulation **43642783223**/source15a63339b7a18be32652b2d481c863bd8936c208 is the other active successor. Check exact composition, full256-bit native transient and original acceptance gates. Full serial PHY, routed mainchip timing, qualified PEX and production qualification remain open. All native work cloud-only; experimental workflow not merged.

## 2026-11-15 — all503 packed reduction controls passed; actual loaded circuit dispatched

Reduction43642333530/head761de4f6abe134f6a8cc06a53beab086a015af52 completed SUCCESS:503 actual native simulator executions,250 port networks across50groups andfive partitions, two negative controls. All200 physical contacts and intrinsic gates bound to current geometry. DC/AC/power/noise checks retain original tolerances. This qualifies nominal resistance-network port reduction only, not temperature/corners, gate extrinsic capacitance or whole nonlinear circuit. Safe14132572167 SHA4c029817080e8f4972e206d1b0b94971f738c7d4e2c14e92e5603c0ec830f297; native14132791321 SHA969027fae7d4700685e4cacc4cf3ee4c23fc472ad4bff5c4f6a6825f7f2ff4b1. Receipt `docs/evidence/packed650-gate-reduction-20261115.json`.

NEW full composition/loaded run **43642783223**, source **15a63339b7a18be32652b2d481c863bd8936c208**, branch `codex/packed650-full-composition`. Authenticates exact new geometry, current2046 terminals, metal RC43641595711 and reduction43642333530; builds allfive partitions then runs original256-bit nominal_late n1 test. `cdr_mos650_full650.py` and `cdr_mos650_full650_loaded.py` unchanged from original failed paired case73b781...; no moved observation windows, inverted expected data, removed loads or changed SOA. All nominal material/model limitations still apply. No fullPHY claim. Inspect assembly, actual transient diagnostics and original gates after completion before broader refinement/PVT/closed-loop validation.

RX physical43641707777/job132590504077 completed placement/CTS computation in596.51s and is uploading native output. Safe14132319537 SHAf68456d7af8c3cc649cee632a11bce69723b7a948bd8247050284156adca7c86 confirms356 outputfiles, unchanged sources, CTSODB2d7f284e5a22dcaced71be4bcf1956f5d6d00373653d6a0217c1b4c694271b69. Wait for completed physical job and native artifact, then start own before/after postCTS repair from exact62db42e598ccca15b5d51f202b2c5b52ab33b976 source; no CRC timing proof reuse. Independent actual gateboot job132590504308 remains live. All native files cloud-only.

## 2026-11-15 — packed gate mesh passed; full native reduction controls live

Packed mesh43642048336/head05178c10479e149d76fddbfd00dff121999bce86 completed SUCCESS: fifty physical groups,200 contacts/gates, four actual-mesh DC and four analytic70ohm references passed at600/300/150/75nm mesh pitch. Finest refinement changes diagnostic gate averages by0.4298%; this is not whole loaded intrinsic convergence. Material values remain nominal/unqualified. Safe14132687034 SHA82f1c0a49e6963af7b3064a7e2f7ee7ea3b45a9c4c168a353c51ccbd8ab5ca20; native14132771588 SHA95b16196dc6d95fbefe5f436c81bb3dd0bc39f8ca0c2e68d9fe3ad96b9a0377a. Receipt `docs/evidence/packed650-gate-mesh-20261115.json`.

NEW reduction run **43642333530**, source **761de4f6abe134f6a8cc06a53beab086a015af52**, branch `codex/packed650-gate-reduction`. Uses exact new mesh plus new geometry/anchors/identity; original503 native DC/AC/power/noise/fault executions across50 groups and five partition bases remain unchanged. No old geometry mesh accepted. After success create source-bound full composition using new metal RC43641595711 and this reduction, then rerun unchanged loaded256-bit transient. Old composition reference source73b781d77b169a4c270bb635197540d3c8f96a9c/run43626358999 failed acceptance; preserve failure and use only its methods. RX mainchip43641707777 placement/CTS+gateboot still independent; CRC postCTS failed timing as recorded below. All native work remains cloud-only.

## 2026-11-15 — CRC postCTS measured, still fails; packed gate mesh live

CRC postCTS43639975405/headb6dfa2a1429d837d7f4d5e479897cf95dac06f87 completed native execution, NOT timing acceptance. After1199.21s repair: slow setup2548/WS-3.334900ns,hold1/WS-0.389349ns; typical setup602/WS-0.775369ns,hold17/WS-0.360047ns; fast setup0/WS+0.471704ns,hold221/WS-0.325918ns. Slow/typical register-to-register hold is clear, but all I/O paths remain mandatory. Slew13/7/0,cap0;fanout1377 remains. Same original clocks/derates, placement-estimated RC only. Repaired ODB568dfa2f110b6813d316087b6249340bedd4c831b95bf13d6224014b49c6afb1. Safe14132078627 SHA0ed233f5323f5cd384752bb90205d8ecfe989da42d936701151ea37183815c01; native14131978922 SHAf6dff8733fb34fdc4d9e5bb58a73a61390c8341ecaf7edbd0980a0cbdb4a8021. Receipt `docs/evidence/crc-select-mainchip-postcts-20261115.json` includes actual worst paths and measurements.

Worst slow path still starts reset-distribution FF $auto$ff.cc:337:slice$343453 (aliased endpoint.receive_packet.quarantine.rst_ni), traverses five fanout buffers then receive-ownership logic/lane_d[7], ends receive_ownership.r2_staged_group[1].lane_copy slice551876. This is the cone targeted by ongoing RX local-reset candidate43641707777; inspect its own postCTS results before adopting. Worst fast/typical hold starts pcie_training_i, ending slice183526 through two delay cells; keep input timing constraints intact. Do not call this chip closed because native execution succeeded.

NEW packed physical gate-mesh run **43642048336**, source **05178c10479e149d76fddbfd00dff121999bce86**, branch `codex/packed650-gate-mesh`, job132591553484. It rereads exact ecae8a... GDS, fresh anchor artifacts14131807306 and native identities14132415076, validates all200 gate contacts/50 physical groups, and runs four mesh resolutions plus analytic/current conservation references. Original physical equations/material assumptions unchanged; nominal material values are not signoff-qualified. On success adapt old reduction source0308a08571969e629fb567c811414edb925a0dbc to this exact new mesh producer plus new geometry/anchors/identity; run all503 DC/AC/power/noise/fault checks, then full composition with fresh packed metal RC43641595711. RX CTS and independent native boot43641707777 currently live; no old candidate acceptance reuse.

## 2026-11-15 — fresh packed numeric RC passed both orders and all fault controls

Corrected run **43641595711**, source **a82ae4f177962c6eeca9a1a678d7423274ddb313**, completed SUCCESS. Actual new packed geometry produces28634 resistors and18488 capacitors,650 devices/2046 terminals,1428 point references/200 gate contacts. Both native orders agree exactly, including1022 coupling records. Each order rejects13 wire and9 MIM faults. Seven intrinsic MIM cards remain separated from wire C. This establishes this extraction stage only: full qualified PEX, electrical acceptance and full PHY remain FALSE.

Safe14131868918 SHA256 `8d3141a5cee58b57df009381dfd5b141ed465a698f3d0c22ec6db8542492fc14`; native14132266869 SHA256 `2c1771da6336f13c20583b40c1e602287ec63c60046b0c4daf1b2240c52e85f0` (cloud only). Receipt `docs/evidence/packed650-fresh-metal-rc-20261115.json`.

NEXT: rebuild gate-contact network binding/reduction/composition against these exact new source artifacts, then unchanged loaded256-bit transient. Old paired pipeline reference runs43625413974 (gate mesh),43625754764 (503 DC/AC/power/noise checks) and43626358999 (failed loaded transient) are methodology only, not reusable new geometry acceptance. Keep all original windows/expected bits/loads/device SOA gates. RX+CRC exact placement/CTS+boot43641707777 and CRC-only postCTS43639975405 are independent live handles; inspect completed jobs before source-specific successor stages. No native data local, no experimental workflow merge.

## 2026-11-15 — RX mainchip mapped; exact CTS/boot live; packed RC identity fixed

RX+CRC build **43638771489**, source **e92350d314fd8c04c9c06f2aa7d198f02b000cd1**, completed SUCCESS. 115390 cells, twenty SRAMs,26 replay predecode bits, one source-derived EOP FF; RX local-reset and CRC-select flags confirmed. Exact formal/traffic qualification gate passed. Mapping safe14131928219 SHA716388bae108cddc07099c7dc0de28e058a9c0f888f6cb2b04c5a0fd75baa334; native14132027737 SHA5b92b8ded91a9d8b2d0042457d09f8473dd99064cb7a509644c08d47fe6f1586. Receipt `docs/evidence/rx-cursor-mainchip-mapping-20261115.json` contains full mapping and qualification. This is not gate-level boot or physical acceptance.

NEW exact RX+CRC physical/boot run **43641707777**, source **62db42e598ccca15b5d51f202b2c5b52ab33b976**, branch `codex/rx-cursor-chip-physical-boot`. Placement/CTS job132590504077 and independent Icarus native boot job132590504308. Restore requires completed successful producer, all63 output hashes, current RTL/input hashes, both RX/CRC flags and fresh source netlist3bc7451e1700daa7ffa8ff2b834c4aed64f2e013d2060deba30d3b7b124b53b4. Same original clocks, derates, native models and all MBIST/firmware gates. On CTS completion create source-bound before/after three-corner repair, without inheriting CRC-only results.

Packed metal RC43641038903 FAILED before numerical extraction: `cdr_mos650_mim_support.py` still asserted the old paired GDS hash285760..., correctly rejecting the new packed ecae8a... geometry. Fixed that one exact identity to the independently DRC/LVS-validated packed geometry and updated source-closure hash; no geometry or acceptance changes. NEW run **43641595711**, head **a82ae4f177962c6eeca9a1a678d7423274ddb313**, same `codex/packed650-fresh-metal-rc` branch. Source controls passed, native extraction currently live. Failure receipt `docs/evidence/packed650-metal-rc-stale-identity-20261115.json`. Inspect both native orders and raw-fault controls before accepting RC; then rebuild exact new gate network/composition and unchanged loaded transient.

CRC-only postCTS43639975405/job132585189822 still in native repair; CRC gateboot43638590941 independent. Old Verilator run43620739672/job132525630570 did not reach SoC compilation: native-cell simulator compatibility preflight failed both seeds. Safe14123713097 SHAab629997a3df10119605ed18a08aefadd1fdd90f6e637314df10aac56f56f419 confirms this, not a mainchip functional failure. Actual Icarus boot remains separate. Full serial PHY, routed timing and production qualification remain OPEN. All native work stays in cloud; do not merge experimental workflows.

## 2026-11-15 — all packed terminal/contact bindings passed; fresh metal RC executing

Terminal/contact run **43640767232**, source **b0ab692823d8aaf2c401674cac2f6c3c91f5db95**, completed SUCCESS. All650 devices and2046 terminals are accounted for, with1428 physical point references and200 gate contacts. Source pin provenance checked actual primitive material/annotations and actual packed band transforms. Numeric RC has not yet been accepted. Safe14131807306 SHA256 `e5a2c6cbe1134e92f812b6abfe5d77bed5e797a7f4d8a3cbe6af9cf7c6af0cf4`; native14132315920 SHA256 `9040ef35d8eef59e932254e24c67950872be6050b644eccb0c01fe744a375e95` (cloud only). Receipt: `docs/evidence/packed650-terminal-anchors-20261115.json`.

NEW fresh metal RC run **43641038903**, source **8372a48986258a93441a79fc2ea9b52f8a36a577**, branch `codex/packed650-fresh-metal-rc`. Explicitly dispatched with execute=true and approved_source equal to that exact source. It restores the new accepted anchor artifacts and new native identity artifact14132415076; authenticates actual GDS `ecae8ae8e49beea391b1d2575da6f5ac9ea01180550ae65fc786ddc6fd9ee193`; requires113 conductors/114 electrical nets and all actual source-bound terminal inputs. Original numeric extraction/audit/control methods run with both native orders and MIM-aware geometry. Old paired RC is not substituted. Source closure pins and exact branch checks were updated; physical and electrical acceptance thresholds were not changed.

Next inspect its complete native/derived outputs, RC invariants and raw-fault controls. Then produce gate-network binding/composition for this exact new geometry and run the original loaded256-bit transient without moving windows, inverting expected data, removing loads or changing device SOA gates. Full qualified PEX, serial PHY and mainchip timing remain open. CRC postCTS43639975405, RX+CRC build43638771489 and CRC gateboot43638590941 remain independent live handles from the last check; revalidate before acting.

## 2026-11-15 — packed native conductor graph passed; terminal/contact extraction live

Run **43640446032**, source **4a72ade2fe5f938f1a1438c08c35b6f9c38c2f95**, completed SUCCESS. Fresh native identities and actual metal/via graph have650 devices,2046 terminals,25 external ports and113 conductor components. Actual geometry was not changed and no component was merged merely by net label. Exact GDS remains `ecae8ae8e49beea391b1d2575da6f5ac9ea01180550ae65fc786ddc6fd9ee193`. This is connectivity extraction, not numeric RC or electrical acceptance.

Safe artifact14132415076 SHA256 `4969908bb9422d864bb5ff3d17a2e61928a6f3f2a3f267904819a160f1159c59`; native14131638321 SHA256 `2b3fb4f7f941846e2a2f69953e5be309129e8e5f1870252b3ce822e3ffb62dad` (cloud only). Receipt `docs/evidence/packed650-wire-graph-20261115.json` preserves the report and hashes of exact graph/identity members.

NEW terminal/contact run **43640767232**, source **b0ab692823d8aaf2c401674cac2f6c3c91f5db95**, branch `codex/packed650-terminal-anchors`. It authenticates the new conductor producer and its archives, the actual packed generation archives, exact GDS/LVS database, complete primitive material and annotations, and actual whole-band transforms. `cdr650_paired_pin_provenance.py` was explicitly rebound to the new GDS, rather than leaving its old hard-coded hash or bypassing source pin provenance. All original terminal-material probes and fault controls remain. No old numeric RC reuse. On completion require every2046 terminal,1428 physical point references and200 gate contacts before fresh metal RC extraction and electrical recomposition.

CRC postCTS43639975405 and RX+CRC firmware/synthesis43638771489 remain live, with CRC gateboot43638590941 independent. Full goal remains open. All native source/CAD work stays in cloud.

## 2026-11-15 — complete packed PHY physical suite passed; fresh extraction started

Corrected physical run **43640075616**, source **1d7d44c9907c071bf801dcb1347d46750cccd97e**, completed SUCCESS. All16 actual phases completed: full560-category native DRC has **zero markers**; deep and flat LVS each match **650 layout /650 schematic devices**; all13 native physical/schematic fault cases were rejected. This supersedes the partial interrupted run43639600962; no missing phase was waived. The seven memory-monitor controls also passed. This is physical verification of the standalone packed CDR/phase-detector candidate, NOT full PCIe PHY or whole-chip manufacturing approval.

Exact packed GDS `ecae8ae8e49beea391b1d2575da6f5ac9ea01180550ae65fc786ddc6fd9ee193`. Safe artifact14131278779 SHA256 `943f8a26ec6a54c963edc0fdd7d0a6547a26a436dca526682a3316be9dc9c412`. Native artifact14131118894 SHA256 `a0c94feff983952e7696aa231b9bb3aa83248d391c8933ca5a5d4649fdb8c50b` (cloud only). Exact native physical report SHA256 `83dfc99b6aa0ad8384891f7aa90be9cbfc34955dcae7cfd94d74e59fb809c5c6`. Receipt: `docs/evidence/paired650-packed-physical-20261115.json`.

NEW native identity/conductor extraction run **43640446032**, source **4a72ade2fe5f938f1a1438c08c35b6f9c38c2f95**, branch `codex/packed650-wire-graph`. It requires the completed successful physical producer, exact archive and physical-report hashes, all16 phase outcomes, exact new GDS, all layout/LVS inputs and650-device identity. Then it extracts actual metal/via connectivity without merging by net label or substituting old geometry. Runtime source closure is pinned. Next require its2046 terminals and25 ports, then rebuild terminal anchors and fresh metal RC for this GDS before recomposition and unchanged whole-loaded electrical tests. Old paired RC must not be reused merely because topology is the same.

CRC postCTS43639975405/job132585189822 remains in actual three-corner electrical/setup/hold repair. RX+CRC43638771489/job132581372827 remains in actual firmware RTL boot/synthesis. CRC gateboot43638590941/job132580818711 remains live. The older and new sources stay distinct; no inherited functional/timing acceptance. Full serial PHY, chip timing and manufacturing qualification remain open.

## 2026-11-14 — CRC CTS complete, fresh STA/repair live; packed PHY monitor failure corrected

CRC physical job132580818864 inrun43638590941 completed successfully in673.118s. Exact source85356cc286bea6cd6f53492a17c3182b037ec795, twenty macros and356 output files. CTS ODB SHA256 `6deaba84600e5bd9ef0a59028a6fce1b00fea8e9f87f968a997487220c14dcaa`, state `run/27-openroad-cts/state_out.json`. Safe14130768482 SHA256 `a7a3a9c5193d18850814bc9833b52eee358a234c216421e682cd06210c5152a1`; native14131641568 SHA256 `8db0f7647c3fa75371fa3741ece0a4334775ddeb8998d8b7fa069b9239787c03` (cloud only). Receipt `docs/evidence/crc-select-chip-cts-20261114.json`.

NEW postCTS run **43639975405**, source **b6dfa2a1429d837d7f4d5e479897cf95dac06f87**, branch `codex/crc-select-chip-postcts`, job132585189822. Restores that exact completed physical job and all file hashes, discards inherited metrics, then independently measures slow/typical/fast corners before and after native electrical/setup100/hold1000 repair. Original clocks, constraints and5% derates unchanged. It is executing actual native repair. Gate boot43638590941/job132580818711 remains independent and live. RX+CRC43638771489 has advanced into fresh firmware RTL boot and complete synthesis after its replay regressions.

Packed PHY run **43639600962** is terminal FAILURE from its process monitor, not a native geometry mismatch. Actual DRC passed all560 categories with zero markers; actual deep and flat650 LVS passed; five negative fault cases were rejected before interruption. Remaining fault cases were not completed. The monitor observed a transient missing live VmRSS, then logging/scheduling consumed279ms against its100ms total window. It terminated the checker at59.176s with `memory_sample_unavailable`. Safe14131760761 SHA256 `7bf7dfe14274338204dca446a7eb6ab4492441c9f500770025a949390a8fd6c0`; native14131104745 SHA256 `b7dd54fbd4cd820fd5aa4a189edb6a052e335b4cac0067fc29521ef0066ef5cd`. Partial receipt `docs/evidence/paired650-packed-monitor-interruption-20261114.json`. Do not mark the full suite passed or reuse its missing phases.

NEW corrected physical run **43640075616**, source **1d7d44c9907c071bf801dcb1347d46750cccd97e**, same branch `codex/paired650-packed-physical`. Historical evidence modules remain unchanged. New `scripts/physical_memory_sampler.py` retains three attempts,20ms retry interval, fresh counters, PID/starttime checking and rejection of persistent missing counters; only the total bounded snapshot window is now1s. The10GiB RSS limit,2GiB free-memory minimum, native command time limits and every physical acceptance gate remain unchanged. Runtime module selects the exact new sampler SHA256 `36721c1b98c0481e5c91568888634e8becdb1678f33a50fcf0c9f69c93f49d6a`; source closure pins updated.

Seven deterministic monitor controls passed, including reproduction of the original100ms failure, successful fresh retry after279ms, persistent missing counter rejection, total deadline enforcement, PID reuse and malformed-unit rejection. Controls artifact14131965533 SHA256 `f7cfae24d053e0b5a461c0ec2c54663453051aaab7c6c5dd9cebf696df94246f`. Source-controls job132585500637 passed; native job132585576183 is the next required full run. Only after that succeeds start fresh graph extraction. Reusable graph extractor: `scripts/extract_cdr650_paired_wire_graph.py` and pins/workflow atsourcee0a87989915cb7d65a20176de33649859f013393; update its exact physical run/head/native artifact/report hash/GDS hash and closure pins to the new accepted source, never bypass these bindings. New packed GDS remains `ecae8ae8e49beea391b1d2575da6f5ac9ea01180550ae65fc786ddc6fd9ee193`.

All native files remain in cloud. Full PHY, routed chip timing and manufacturing qualification remain open.

## 2026-11-14 — packed PHY geometry generated; full native physical validation live

The measured AD/CD/selector loading now has a physical candidate, not only another diagnostic. Generation run **43639421390**, source **dbe212de5ae00036284f104d45742db443186f51**, branch `codex/paired650-packed-buffers`, completed successfully. It keeps the first six sampler/clock bands fixed and packs the later ten complete buffer/comparator bands with a16um gap measured between actual occupied regions (all material layers, child bounds and parent labels). No primitive resizing or local wiring edits. All37 global TM1 trunks are rebuilt with exact via incidence retained; serialized geometry and real deletion mutations were checked.

Actual total SIGNAL trunk length decreases **25676.76um ->23738.76um**, a1938um/about7.55% reduction versus the actual previous paired candidate. No individual signal trunk becomes longer. Upper occupied extent decreases329.4um, but supplies retain their original outside endpoints, so this is not a claim that total chip bbox shrank. No RC or timing improvement has yet been demonstrated.

New GDS SHA256 `ecae8ae8e49beea391b1d2575da6f5ac9ea01180550ae65fc786ddc6fd9ee193`; original source geometry `c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c`; paired comparison `285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514`.
- Native artifact14131740193 SHA256 `89585c334b2ae7f06b21e6851babe72ec11b5d1b4e0bee675c79090129193057` (cloud only).
- Proof artifact14130989352 SHA256 `590ee5edefb5e0de9a0997fc8d92a06513e601670b045fbb8e0a2d4187e9de98`.
- Receipt: `docs/evidence/paired650-packed-generation-20261114.json`; design note: `docs/paired650-packed-buffers-20261114.md`.

NEW full physical run **43639600962**, source **63db8effa6600507bb540a19011d17a284536f73**, branch `codex/paired650-packed-physical`. Derived from previously successful native physical source8274b540...; changes only exact branch/runtime admission, candidate input pins, additional packing provenance assertions and source-closure hashes. Original full560 DRC, deep/flat650 LVS and fault gates remain unchanged. Independent650 reference schematic is unchanged. This job must finish before building new exact geometry/anchor/metal RC and rerunning original loaded electrical gates. Do not transfer the old paired DRC/LVS/RC acceptance to the packed candidate.

Mainchip CRC run43638590941 still executes placement/CTS and independent actual native gate boot; RX+CRC build43638771489 is still running its fresh replay positive/mutation regressions. Both were confirmed live. They are separate sources. Full serial PHY, chip setup/hold and manufacturing acceptance remain open; all native work stays in cloud.

## 2026-11-14 — RX traffic passed; qualified RX+CRC mainchip build now live

RX traffic job **132576149016** inrun **43637085427**, source **c5becaa11a0274839f798a47890dd021fb78d0cf**, completed successfully. Eight original-reference 300000-cycle tests passed and eight ready-inversion mutations were rejected. Safe artifact14130976590, SHA256 `8058a0fd3fdfbb1beef7f95138bb1e061d8ce4df94364b274105f28a403b6c51`. Exact RX RTL hash remains `c16d14cb42d27d261ec7aca5a303f9c3b63e24da6ce651b1a504fe3e56f658ec`. Receipt: `docs/evidence/rx-cursor-traffic-20261114.json`. The overall run is red because of the INITIAL formal hierarchy-harness error; the separate corrected formal run43637249034 passed both proofs and both mutations. Both exact results are required.

After inspecting all16 traffic outcomes, dispatched prepared source **e92350d314fd8c04c9c06f2aa7d198f02b000cd1**, branch `codex/rx-cursor-mainchip`, run **43638771489**. This supersedes the earlier "not dispatched" note below. It independently requires exact completed formal/traffic jobs and authenticated artifacts, then performs fresh CRC regressions, actual firmware RTL boot and complete synthesis with the RX cursor distribution flag. No physical closure claim yet.

CRC-only physical/boot run43638590941 has passed exact source restoration and is actively executing: placement/CTS job132580818864; native Icarus boot job132580818711. These remain independent from the RX+CRC build. Original EOP/older boot sources are also separate and must not supply acceptance for these candidates. Next inspect actual new CTS result for a fresh source-bound postCTS repair, and RX build mapping before scheduling its physical comparison. Analog drive/RC result and next repair sources are in the entry below. All native execution remains in cloud.

## 2026-11-14 — CRC mainchip mapping passed; new exact-source CTS and boot started

CRC mainchip run **43635824821**, source **9339dd6eeda8cf65383c7dc606e0cc752c1d6432**, completed successfully. Four regression variants each contain six seeds: twelve positive tests and twelve semantic mutation rejections. Mapping has **115737 cells**, sixteen Ethernet SRAMs and four system SRAMs, all 26 replay write-predecode bits, and one source-matched EOP cache register at lines326–338. The checker derives that origin from actual lowered RTL. This proves mapping, not gate boot or physical timing. Receipt: `docs/evidence/crc-select-mainchip-mapping-20261114.json`.

Exact new outputs:
- Native artifact14131535375, SHA256 `b92718e6281f3c11a16b9154ba6de8fc661e60e9846c3001f61af1ec1308fac4` (cloud only).
- Mapping artifact14130736810, SHA256 `bd7755567790c904749b467dcd72d3faa59756e24dcf360726d5188fc32382a9`.
- Regression artifact14130731781, SHA256 `075259cf52cf499867e3898866074e6a3b16d65811be99628850e6c948217db5`.
- Netlist SHA256 `2a10c2131d5089eb84171f759817f843d887026ed9e4fe882d84b17fb945672c`; mapped JSON `a06ddb567dd79109b083f2dce786ab9bf2f0aadf1983a57d1ff27e8a8a5a7082`.
- Firmware SHA256 `ab7440619ca719358e6598b0cf291a268c8ccf13357b50ef3a89cbe583e71801`; 63 output files authenticated.

NEW physical/boot run **43638590941**, source **85356cc286bea6cd6f53492a17c3182b037ec795**, branch `codex/crc-select-chip-physical-boot`. It restores only the exact new artifacts, checks the successful source producer and every output/input hash, then runs placement/CTS and a separate actual native Icarus boot with all system/Ethernet MBIST and firmware gates. Original clocks, derates, models and constraints remain unchanged. Do not transfer older EOP timing/boot evidence. Old EOP boot43632152541 remains independent. Experiment workflow must not merge.

RX cursor formal proof remains passed. Traffic job132576149016 inrun43637085427 is still live. The next RX fullchip source **e92350d314fd8c04c9c06f2aa7d198f02b000cd1** on `codex/rx-cursor-mainchip` is prepared but **not dispatched**: inspect all eight positive/eight mutation traffic results first. Its workflow independently enforces both formal and traffic artifacts before any synthesis. This RX candidate includes the CRC change but has no own mapped or physical result yet.

## 2026-11-14 — actual PHY interface topology and metal loading measured

Diagnostic run **43638218885**, source **373c6bc3ae24fc2a40d720ce199aedaeb1d87411**, completed successfully. Safe artifact14131037408, SHA256 `9bfe8a3a975523cccd7592ef23e2f29de3b63362f96a8dd1fa40cba2068e1546`; receipt `docs/evidence/paired650-drive-rc-20261114.json`. It reads the actual failed circuit's authenticated contract and model in cloud and solves its native metal resistor networks. It does not modify the circuit or claim qualified extraction.

ADP/ADN external metal capacitance is **467/496fF**, with effective metal resistance from collector to the most distant HBT terminal **124.7/132.7ohm**. CDP/CDN:381/407fF,123.5/131.5ohm. S0P/S0N:241/231fF,119.4/105.4ohm; S1P/S1N:230/219fF,119.0/105.0ohm. Metal-only first moments with all other conductors clamped reach25.8/30.4ps for AD and19.7/23.2ps for CD. These omit intrinsic device/MIM capacitance and finite driver resistance; they are NOT measured full-path propagation delays or proof that the actual timing gate passes.

Actual ADP driver is HBT275 (Nx2), base `uan`, collector `adp`, emitter `da_tail`. ADP drives six Nx4 XOR HBT bases and rppd386 (length1.8um,width8um, between `da_load` and `adp`). Actual S0P driver is HBT298 (Nx2), base `usn`, collector `s0p`, emitter `s0_tail`; it drives two Nx6 HBT bases and rppd398 with the same geometry. This provides concrete loading/topology for the next repair. Simply enlarging the driver without checking its fixed tail current will not necessarily improve speed. Next inspect upstream UAP/UAN/UCP/UCN/USP/USN transfer and dominant physical metal segments before choosing geometry/bias edits; preserve the full loaded acceptance and device SOA checks. Do not substitute a polarity inversion or a later observation window.

Full serial PHY, routed all-corner chip timing and manufacturing acceptance remain open. All native CAD/source execution stays in cloud; local workspace remains empty.

## 2026-11-14 — qualification-gated RX wholechip source ready; actual driver/metal RC solve live

Prepared but NOT DISPATCHED codex/rx-cursor-mainchip/sourcee92350d314fd8c04c9c06f2aa7d198f02b000cd1. Built from CRCmainchip9339... with exact formally proven RX RTL c16d14cb42d27d261ec7aca5a303f9c3b63e24da6ce651b1a504fe3e56f658ec. Adds validated default-off SOC_PCIE_RX_CURSOR_LOCAL_RESET to bothsim/syn drivers; rejects unlessREAD2andRESET_COPIESareenabled. Configuration recordsflag; mappingchecker requiresflagandexactRXhash inaddition to priorCRC/EOP/predecode/20SRAM checks. Noexistingnativeprooftransferred. New require_rx_cursor_qualification.py checks exact successfulformaljob43637249034 and exacttrafficjobqualify(traffic) in43637085427, hashesarchives, exactRTLhash, all2positive/2mutationformal and8positive/8mutationtrafficresults. Overalloldtrafficrunformalharnessfailureisnotignored as success: separatecorrectedformal proofrequired. WorkflowrunsfreshCRCregressions andwholechipfirmwareRTL/synthesis onlyAFTERgatespass. Thus dispatch this workflow only after trafficartifact isavailableandinspected. Do not merge experimentworkfloworclaimphysicalclosure.

NEW driver/topology/RCdiagnosis43638218885/source373c6bc3ae24fc2a40d720ce199aedaeb1d87411 on codex/paired650-drive-rc. Reads exact nativefailedPHYarchive14129601477 ONLYincloud, authenticatescomposition-n1 contractSHA b456d6d7ac87b13ec801ec2eb593510c8b8aa103c429845cfccc045314cd7d6e andmodelSHA719c86b15cd58713b0ca7c49ec9005d5c30b8a0496d116c337c62ef897f42c82. For16sampler/interfaceconductors identifies actualphysicaldriverandlogicalattacheddevices, traversesactual28634metalR/18488Cgraph, solves groundedconductance matrixforeffectiveRtoHBTterminals andfirstmomentwithexternalconductorsclamped. Intrinsicdevice/MIMcapacitanceandfinitedriverRareNOTincluded; thisisdiagnosis,notPEX/bandwidth/signoff. Intendedtospecifywhichbuffer/wiretolayoutrepairfollowingmeasuredweakAD/CD/S0/S1. Noresimulationoracceptancechange.

RXtraffic43637085427/job132576149016 andCRCmainchip43635824821 remainlive; EOPgateboot43632152541/job132560946622 also confirmedlive. Keep exacthandles; norestartforobservationlatency. Fullmanufacturinggoalopen.

## 2026-11-14 — actual PHY transfer evidence locates weak/delayed comparator drive

Read-only exact-wave diagnosis43637557930/sourcee5a8c892582b46d744ea4307d59ece4401a666e4 completedSUCCESS. Original sampler/comparator acceptance metrics all reproduced; no new transient, layout or acceptance. Safe14130676643 SHA25681169240776686fcdc6db148a0a65c854f6efef027d7a50300fc14575d3cce95. Full derived receipt docs/evidence/paired650-input-transfer-20261114.json.

At diagnostic0.6UI, AD/CD inputs have66/77 of255 samples with abs(diff)<100mV; S0/S1 have157/160. Data commonmodes1.829/1.819V, selector1.187/1.185V. At0.9UI S0/S1 each167weak. These input100mV counts are diagnostic, not an added/replacement acceptance gate. AD's strongest sampled sign relation is B/C lag0 (208/255), CD's B/C lag-1 (198/254); selectors similarly favor previous samples. This suggests slow interface transfer but is NOT proof of topology, an allowed retiming, or permission to change expected vectors.

Actual X grouped by AD/S0 at0.6UI: equal-sign00/11 with both inputsstrong have36/37samples, outputmeans-.06217/-.09515V. Opposite-sign01 hasonly3strong pairs and10hasnone; cannot claim a complete static XOR truth-table test from this PRBS waveform. Y's opposite-sign inputbins havezero strong pairs. No HBT fallsbelow.4V at sampled0.6or0.9UI, but original ALL-TIME active VCE failures remain and are not waived. Next analog action: inspect exact physical buffer/selector connectivity plus extracted RC and current/bias before choosing a drive/route repair; do not simply invert output or move observation windows. Generator source for current paired geometry is scripts/audit_cdr_native_cap_records.py at0d90e18e09678eb1733123d97f41942dace720b3 (run43621748603); it moves wholephysicalbands and rebuilds37TM1trunks, preserves local devices. Current model composed via scripts/cdr_mos650_gate_ac.py at73b781d77b169a4c270bb635197540d3c8f96a9c; protectedactualnativezip14129601477 remainscloudonly.

RX cursor formal passes as recorded below; trafficjob132576149016/run43637085427 confirmedlive from20:22:16Z. CRCmainchip43635824821 firmware/synthesisstep confirmedlive from20:20:04Z. No restarts. Fullchiptiming/PHY/manufacturingobjective notclosed.

## 2026-11-14 — RX cursor formal qualification passed; actual PHY transfer diagnosis dispatched

Formal-only corrected run43637249034/source2eed5ba2ffa16553d9bdaa79856eceb4e3519139 completedSUCCESS. Actual full-module state/output equivalence passes 4DW/1slot and8DW/2slots with mapped memories and fully flattened helper modules. Both ready-inversion semantic mutations rejected. Proof explicitly binds the existing parent contract rst_copy_ni == rst_ni; no other input assumptions. Exact RX RTL SHA256c16d14cb42d27d261ec7aca5a303f9c3b63e24da6ce651b1a504fe3e56f658ec. Safe14129599973 SHA256dfc322a1d49550d5b4df1b30beb294d9bc3c343eb26bcd3c7209536e1a711223. Receipt docs/evidence/rx-cursor-formal-20261114.json. Independent traffic job132576149016 inrun43637085427 remainsLIVE; overalloldrunwillfailbecauseinitialformalharnessfailed, so inspecttrafficjobandartifact separately. No physical acceptance or mainchip integration yet.

NEW actual-wave input-transfer diagnosis run43637557930/sourcee5a8c892582b46d744ea4307d59ece4401a666e4 on codex/paired650-input-transfer. Extends authenticated existing waveform reader from9a814be...; reproduces original acceptance first, then reports AD/CD/S0/S1 differential/commonmode, same/opposite sign relation to all four samplers at integer lags -1/0/+1, all input-combination bins for X/Y against both data and selector candidates, and all124native HBT sampled VCE/VBE. Empty input bins remainexplicitn=0. These are diagnostics, not assumptions about topology or authority to retime expectations, invert polarity, relax windows or accept the failedPHY. Original1.59GBwave stayscloudonly; no new transient or layout. Inspect transfer and native headroom before selecting actual comparator/bias/geometry repair.

CRC_SELECT wholechip43635824821/source9339... remainsinfirmwareRTL/synthesis. EOPonlyandoldpredecodegateboot jobs remainindependent. Next actionable gates: finish exactRXtrafficqualification then source-boundphysicalcomparison; inspect newPHYtransferreport tochooseactualanalogchange. Fullmanufacturingobjectiveopen.

## 2026-11-14 — RX formal harness flattening repaired; traffic unchanged

First candidate run43637085427/sourcec5becaa11a0274839f798a47890dd021fb78d0cf formal job failed with "No SAT model available for cell r2_staged_group[0].lane_copy_gate". It was a hierarchy-lowering error, not semantic acceptance or rejection. Initial helper keep_hierarchy clearing happened before parameter elaboration, leaving opaque derived modules. Safe formal artifact14130815318 SHA256287a6c568d7aad7f7c39f063210ee2c6ebed77e24e7d318cef6427af8f194e55 preserves failure.

Formal-only correction source2eed5ba2ffa16553d9bdaa79856eceb4e3519139 on same codex/rx-cursor-reset-local branch, run43637249034: prep/elaborate first, clear both module and instance keep_hierarchy, flatten, explicitly assert no soc_pcie helper cells remain, then memory mapping and equivalence. RTL bytes unchanged. Original traffic job43637085427 continues, not rerun. New formal result pending; do not count first run as semantic mutation rejection. CRC fullchip43635824821 remains in actual firmware RTL/synthesis. No physical closure claim or source/layout substitution.

## 2026-11-14 — RX reset distribution candidate dispatched after exact critical-path mapping

Critical-path extraction43636364178/source48341d59fa054aae5edb5264267903f050b2367a completedSUCCESS. Safe14130253110 SHA256bc1198c8973dc6f1e8400253546f0239eb9816c54c585c3de7e6259941691f38. Receipt docs/evidence/eop-chip-critical-paths-20261114.json records exact original mapped aliases and reported group metrics. Slow PCIe worst -3.316962ns starts at parent up_rx reset copy (soc_pcie_buffered_flow_packets.v:79-86), passes six serial fanout buffers and handshake logic, ends at receive_ownership.r2_lane_d[9] copy. This is not a CPU data path despite the mapped constant's dcsr_q alias. Slow CPU worst +.837359ns in this EOP-only postCTS state; fast CPU hold still negative. Group counts capped1000, not total violations. No false-path waiver.

NEW experiment codex/rx-cursor-reset-local/sourcec5becaa11a0274839f798a47890dd021fb78d0cf, run43637085427. Default-off SOC_PCIE_RX_CURSOR_LOCAL_RESET uses the already-existing rst_copy_ni to qualify only READ2 cursor/pick handshake. External valid/reset contract unchanged; requires existing equal-reset-copy contract and RESET_COPIES. Does not remove reset qualification or add latency. Full actual-module formal qualification explicitly ties the reset copies in both versions, with two parameter sizes and semantic ready-inversion mutation controls. Eight-seed300000cycle original reference/copy tests and eight mutations run independently. Runner failures now propagate. Proof/traffic results pending; no mapped/physical benefit claim. Not enabled in mainchip drivers or integrated RTL. Experiment workflow must never merge.

Existing CRC_SELECT mainchip43635824821 has advanced past replay positive/mutation regressions into fresh firmware RTL boot and wholechip synthesis; do not restart. EOP gateboot43632152541 and olderpredecodeIcarus43620739672 remain live; oldVerilatorboot failed independently. These source variants must remain distinct. FullPHY, routing, all-corner timing and manufacturing acceptance remain open. Next: inspect new formal/traffic outcome; only after passing qualify source-bound physical comparison, then decide adoption. Keep all source/CAD execution in cloud; local workspace remains empty.

## 2026-11-14 — fresh EOP mainchip postCTS measured; receive ownership is now worst, closure still open

Actual source-bound postCTS43633451595 completed native electrical/setup100/hold1000 plus independent slow/typ/fast measurements in1490.496s. Old inherited metrics were discarded. Repaired ODB befeb52d35e17b1580296a09347ecee07783cd9a0dd503c5150ebddef718b174; state run/5-openroad-resizertimingpostcts/state_out.json. No timing acceptance: original20/4/8/8ns clocks and5%derates unchanged.

Before -> after: slow setup WS -8.35744 -> -3.31696ns, count2440 ->2587; slow hold462 ->0, finalWS+.0453129ns. Typical setup1019 ->793, WS-.735139ns; hold949 ->1, WS-.0910532ns (register-onlyhold+.024274ns). Fast setup275 ->0, WS+.823744ns; hold14025 ->224, WS-.220928ns (r2rWS-.096726ns). Slow slew156 ->26; typical slew16 ->11; fastslew0; capacitance0 inallthreecorners. Improving worst slack does not mean every violation count improves.

Worst finalslow start $auto$ff.cc:337:slice$365445 -> receive_ownership.r2_staged_group[1].lane_copy, worsttypical toreceive_ownership.read_bank[2].r2_slot[1].lane_copy. Fast worstholdeth_txd_o[2]; typical worstholdpcie_training_i. These are EOP-only source results, not the new CRC_SELECT candidate. Cloud detailed-path group/mapped-alias extraction handles:
[
  {
    "id": 43636364178,
    "head_sha": "48341d59fa054aae5edb5264267903f050b2367a",
    "status": "in_progress",
    "conclusion": null
  }
]
It checks the original fullchip mappedJSON SHA1c03ec19a0f8afc2384d92f8974be6cce48ff189e7e1a06e138a69f8754dd8f9 from original failedproducer43630345267 plus independent successfulvalidation43631950511, and maps worst endpoints perclockgroup to exactRTL. OriginalmappedmastersmustnotbeconfusedwithpostECOsizedmasters. Inspect this before choosing another RTL/clock/data distribution repair.

Safe postCTS14129917895 SHA2f7429aa34519372129c4a272e381799bfee5a37aefc5b07495b9901e493110b; native14130177227 SHA62b0a8fcfb281c3a6abc3fcf140b66fc75a017e1c7f7d30cb931ed88bc8ecd93 cloudonly. Slim43636062884 safe14130091813 SHA4087507dc7b282fd4d4f97981798dc293e51b9a74cea239076fed60292a8dea0. Receipt docs/evidence/eop-mainchip-postcts-20261114.json.

CRC_SELECT fullchip build43635824821/source9339dd6eeda8cf65383c7dc606e0cc752c1d6432 is live in replay positive/mutation regressions. Do not restart. EOP-only actualboot43632152541 still independent; oldpredecodeboot43620739672 lastconfirmedlive. LoadedPHY43626358999 is terminalrejected, itswaveformdiagnosis43635472153 completed; nextactualanalogworkmustaddress samplerlatency and comparatortransfer, notrerun unchangedn1or relaxgates. Fullmanufacturinggoalremainsopen.

## 2026-11-14 — CRC-select block has positive all-path margins; mainchip build dispatched; loaded PHY diagnosis retained

CRC physical run43635053634/source6a2065c74105bfc60d4d500cf42f34cb4aeb7c5e completed successfully. Equal-area, identical constraints and optimization budget comparison: EOP-only baseline all-path slow setup -0.047070794 ns / fast hold -0.012820662 ns; EOP+CRC_SELECT candidate +0.018597124 ns / +0.001171230 ns. Candidate typical setup+1.111926794, fast setup+1.739200354; slow hold+.086899199, typical hold+.032137737 ns. 1675 paths per report, 24reports/candidate. Candidate mapped cells5940 vs5870 (+70). The worst candidate slow path moved to ack_sequence_i[1] -> _10129_/D. This is useful isolated ideal-clock/estimated-RC evidence, not robust routed/chip closure; it does not reach requested +50ps/+25ps optimization margins. Receipt docs/evidence/replay-crc-select-placement-20261114.json. Native14129877036 SHAb11a7273499ec4f192ed47086b16251c88191a2b34544993585448d838af1195 remains cloudonly.

NEWmainchip run43635824821/source9339dd6eeda8cf65383c7dc606e0cc752c1d6432 on codex/crc-select-mainchip: begins with six-seed 300000cycle positive regressions for CRCalone and allphysicaloptions plus six-seed semantic CRC-bit mutations for each. Source is restored in finally and wholechip synthesis is gated by all expected results. Then original complete firmware RTL boot and20SRAM mapping. EOP source origin checker now derives the unique $adff source from actual lowered candidate RTL and requires exact matching unique mapped PCIe-clocked flop, not obsolete hard-coded line spans. Exact CRC source hash and synthesis flags, all26writepredecodebits, all20macros remain required. New validated default-off flag wired into bothsim/syn drivers; configuration report recordsallthree replay knobs. Experiment code/workflow not yet integrated into timing/combined; mainchip boot/layout must be rerun for this source if mapping succeeds.

EOP-only postCTS43633451595/source2c515a0bfb946ef244cc9e94e2f6af8a7e22e2fe is now COMPLETE SUCCESS (execution only). Safe14129917895 SHA2f7429aa34519372129c4a272e381799bfee5a37aefc5b07495b9901e493110b,31MB; native14130177227 SHA62b0a8fcfb281c3a6abc3fcf140b66fc75a017e1c7f7d30cb931ed88bc8ecd93,433MB. Cloud slim extraction handles:
[
  {
    "id": 43636062884,
    "head_sha": "659c666e8997e3d7fdd0fbe6b8a1da9424efc02c",
    "status": "completed",
    "conclusion": "success"
  }
]
Read the fresh before/after metrics before deciding the next physical continuation. Do not transfer them to CRC_SELECT source.

Loaded PHY waveform diagnosis43635472153/source9a814be2f84742f020e7c38ffd6e9a128c3e2daa completedSUCCESS. Exact original1.59GB/113490x1752 waveform and original reader hashes checked, original sampler/comparator acceptance counts reproduced. At0.6UI allA/B/C/D samples have >100mV correct margins, but the REQUIRED0.3UI gate fails and C has one weak sample at0.9UI. X/Y remain badly degraded across0.6–0.9UI; forX, both expectedbitclasses have negative average differential (roughly -29to-36mV), so this is not resolved by merely examining a later sampler point. This does NOT authorize changing observation windows. Next analog diagnosis should inspect actual comparator input transfer/alignment and operating points on this exact waveform before a new geometry/bias trial. Safe14129158800 SHAacc3de7c8d6b4cb8f8800f11f383b72a85b0a27c278ea6d70f135b9b84de3caf; receipt docs/evidence/paired650-wave-diagnosis-20261114.json. Prior full loaded case remainsREJECTED; no fullPHYclaim.

## 2026-11-14 — paired650 actual loaded transient finished and rejected; diagnose preserved waveform

Run 43626358999/source73b781d77b169a4c270bb635197540d3c8f96a9c is now terminal FAILURE, not live. Native ngspice returned 0 after 5497.373 s, with zero collected diagnostics and unchanged protected sources. The original electrical/data gates rejected the actual 256-bit nominal_late, partition1 case. Five partition bases were assembled, but only n1 nominal_late was simulated; no PVT/refinement/full-PHY closure.

A/B/C/D samplers respectively have 129/128/129/128 samples below 100 mV; wrong-sign samples 0/0/24/31. X has 385 wrong-sign and 742 weak samples; Y has 60 wrong-sign and 676 weak samples. Phase mean +0.01508648 V fails the unchanged +0.03 V minimum. Actual VI current +45.082 uA fails the +50 uA gate despite VI voltage +12.912 mV passing its +5 mV gate. HBT xpd.xd0211 and xd0212 have minimum active VCE .383943/.382336 V, below .4 V; 200 MOS terminal checks pass and minimum stage tail current is 1.51348 mA. Do not change expected bits, observation windows, margins or SOA gates to force a pass.

Safe artifact14129935844 SHA2561120b7b95099d7bd4c966b4a5f2bc39b663f18d1ec9ddcc11a3fa29a87ab5f1d; native14129601477 SHA2560c2aad0a0e0c78ec3dab1be1f9b4e96a57ff9ab41da2df54bba053818c01eee9,2195843371bytes cloudonly. Complete raw waveform 1590734653bytes,113490rows,1752columns, SHA256eb082c14050301a3e7daff0d0f8e284e4d9a0b2b69683a68b078680c3a25e55a. Summary, command, failure and source member hashes: docs/evidence/paired650-full-loaded-rejection-20261114.json.

New codex/paired650-loaded-diagnosis reads the existing native archive ONLY in cloud, extracts/hash-verifies the one raw waveform, uses the original source-hash-verified strict reader, reproduces all original sampler/comparator weak/wrong/minimum metrics, and emits diagnostic phase and expected-bit bins. No resimulation or acceptance-window change. This will distinguish slow settling from a comparator polarity/amplitude issue before another layout/device trial. Current diagnostic handles:

[
  {
    "id": 43635472153,
    "head_sha": "9a814be2f84742f020e7c38ffd6e9a128c3e2daa",
    "status": "in_progress",
    "conclusion": null
  }
]

CRC-select physical comparison43635053634 and EOP-only mainchip postCTS43633451595 / actualboot43632152541 remain separate live jobs. Full goal open.

## 2026-11-14 — CRC input-select RTL candidate proven; physical comparison live

Following rejected OR4 resize, new optional SOC_PCIE_REPLAY_CRC_SELECT moves SOP selection after separate initial/continuing CRC networks and separately computed upper-residue comparisons. Original input CRC state, accepted-byte enable, reset, polynomial, residue, latency and packet decisions stay unchanged. This targets the SOP-to-CRC-comparison input cone rather than blindly increasing drive strength. Source candidate 90b31c2acdbd1170b4b4aa0e74f26e9bcaff789e on codex/replay-crc-select; RTL SHA256 a5891101ff12672cf6da0fa5da09c638e44fc7a5d4fc94b445535e7b00834d45. Default OFF, not integrated into timing/combined or running EOP mainchip.

Formal run 43634922779 completed SUCCESS. Four full real-module equivalence proofs (2x22 and 4x38 in default and all-physical-option builds) passed with mapped memories, no blackboxes; four semantic CRC-bit mutation controls were rejected with unproven equivalence, not parser/tool errors. Physical options include EOP_CACHE, WRITE_PREDECODE, AHEAD, INBANK, RESET_COPIES. Safe 14130076059 SHA256 d29084a051eea2370c1bc85f557d648249022df73bfa604ef3bf907ed233e864. Receipt docs/evidence/replay-crc-select-formal-20261114.json.

Physical comparison 43635053634, branch codex/replay-crc-select-placement/source6a2065c74105bfc60d4d500cf42f34cb4aeb7c5e, dispatched ONLY after inspecting all eight formal outcomes. Mapper independently requires that exact successful formal head. Both baseline and candidate use EOP cache and all preceding physical flags; only CRC_SELECT differs. Same original 600x600um core, 4 ns ideal clock, I/O budget, uncertainty, 5% derates, frozen libraries and estimated layer RC. Both run placement/electrical repair then setup1200 with +50ps optimization margin and hold1000/maxbuffer40 with +25ps margin. 24 ALL-CONSTRAINED-PATH reports per candidate (no register-only filters), electrical reports, source-mapped single EOP flop checked in both. Comparison is not full-chip/routed signoff. Need inspect whether synthesis preserves benefit and any hold/area/electrical regressions. Experiment workflow must not merge.

This new RTL insertion shifts EOP always-block source line numbers. Existing hard-coded mainchip mapping checks MUST be adapted using the actual lowered cell origin if this candidate is later adopted; do not waive source binding or reuse older mainchip results. Current EOP-only mainchip 43633451595 / boot43632152541 and paired65043626358999 remain independent live runs.

## 2026-11-14 — completed old buf4 route/RCX evidence measured; no timing closure

Old candidate 43610680141 completed FAILURE. Authenticated cloud extraction 43634587365/source7a491f528275fc218813700fc1e7901de27d3d45 passed; safe artifact 14129084546 SHA256 97532361b0a04c5774b4c4514bd29ca66b9738ba1b8d80fbbe02c3bf0707709f. Full receipt docs/evidence/buf4-routed-measurements-20261114.json includes all slim evidence and source report hashes.

Fresh nominal OpenRCX plus three-library-corner STA: slow setup 451 violations, worst -1.1162431295 ns; slow hold 0. Typical setup 0, hold 2 with worst -0.0343659555 ns. Fast setup 0, hold 112 with worst -0.1328672765 ns. Aggregate worst slew count 584, capacitance count 106. Router DRC 0, fresh antenna 368 nets / 413 pins. The source SDC and acceptance gates were unchanged. This is NOT qualified RC min/max: one nominal SPEF (583e5df3456e3a59e1a84582ac8cdda57006749cb496c3cfb07d476cb6423c0a), 158097 nets, zero capacitance-conservation inconsistencies within that limited audit.

Worst slow old-RTL PCIe path is retry.write_valid -> retry.bytes[25][4], not the new predecode/EOP source; CPU remains -0.576229 ns and Ethernet TX -0.021050 ns in slow group reports. Therefore do not transfer or optimize old source as though it were the live new EOP fullchip. New postCTS 43633451595, new actual gateboot 43632152541, paired650 transient 43626358999 remain the next live handles. Source-specific isolated OR4 ECO was rejected (previous entry); candidate integration and full product signoff remain open.

## 2026-11-14 — single OR4 upsize rejected; saved guarded candidate retained

Measured run 43634351297 / source 4d5a209adcb35c83075e3df0cad9d6ab77367d4c succeeded as an experiment. Exact control reproduced all six all-path STA values and the ODB hash. The sole _06640_ OR4_1 -> OR4_2 replacement worsened slow setup from -0.022251979 to -0.063389517 ns; typical setup 1.089151502 -> 1.060272336 ns; fast setup 1.733969331 -> 1.715619087 ns. Hold stayed +0.025209585 ns at fast. This ECO is REJECTED and not integrated.

Native legalization moved no cells. The changed stage delay itself increased from 0.417097926 to 0.460538507 ns at its actual load; larger drive is not automatically faster. All three Liberty pin functions/directions were checked equal. Electrical report still contains fanout violations; this experiment cannot support block signoff even if timing had passed. Exact guarded control ODB 8870b2b02e3e1b5e2c690459c348f002b8b56e32362b560492099a748a734c0e is retained. Safe 14129550921 SHA256 64e7d99949213b9fb79bcd537e41a9389e234917730945256ada560cfa004010; native 14129202107 SHA256 a9936362bf29911581b9a1fd3578203ccf8e67b740fc548b4fc14dfe5a9e1272. Receipt docs/evidence/eop-input-or4-eco-20261114.json. Do not merge the experiment workflow or the rejected change.

Old-RTL buf4 route 43610680141 has now finished with overall FAILURE. Its actual detailed route reached zero router DRC after iteration 7, but fresh antenna check reports 368 violating nets / 413 pins (separate route metric 305). Original clocks and timing/antenna acceptance remain mandatory. Routed STA safe artifact 14129471164 SHA256 4e9033aca2d5d1a3cdbf4d9624f2a462f8a1c93ded31e641de5f44a1483bc19b is about 29.6 MB; cloud-only slim extraction 43634587365/source7a491f528275fc218813700fc1e7901de27d3d45 on codex/buf4-routed-results is live. It reads the finished report, it does not rerun routing. Inspect extracted metrics next; never transfer this old RTL evidence to the new EOP chip.

Priority remains new EOP full-chip postCTS 43633451595, new gate boot 43632152541, and paired650 loaded transient 43626358999. They remain live. The small isolated ECO is not a substitute for full-chip optimization. No new native data downloaded locally.

## 2026-11-14 — targeted input-path OR4 ECO dispatched from guarded saved database

Run 43634351297, branch codex/eop-input-or4-eco, source 4d5a209adcb35c83075e3df0cad9d6ab77367d4c. Native log of the preceding guarded repair explicitly said it could not repair all setup violations despite its final endpoint counter being zero. Cache remaining worst path is in_sop_i -> _09986_/D, slow setup -0.022251979 ns. Its _06640_/X sg13g2_or4_1 stage contributes 0.417097926 ns. Frozen IHP library includes sg13g2_or4_2.

The experiment restores exact guarded_hold.odb from authenticated native artifact 14129275553 and compares untouched control against ONE equivalent master change (_06640_, or4_1 -> or4_2). All three frozen Liberty files must have identical pin directions and Boolean functions for these masters. It does not change RTL, constraints, clock, I/O loads, library timing tables or RC models. Both cases run native OpenROAD, legality check, fresh placement RC and all-constrained-path min/max STA in three corners. Control must reproduce previous six all-path slacks within 2 fs. Candidate legalizes after resizing. Electrical violation report and native final ODB/netlist are retained. Sources and databases remain in cloud; experiment workflow must not merge into integration.

Inspect actual ECO result before accepting or extending it. All acceptance/full-chip/PHY claims remain false. Mainchip fresh postCTS 43633451595 and boot 43632152541 are independent live jobs; avoid duplicate launches. Evidence ledger for previous guarded result is docs/evidence/eop-block-guarded-repair-20261114.json.

## 2026-11-14 — guarded block repair measured: hold improved, input setup still open

Run 43633349306 / source 470ff1618470f9c2875aa6b021db85591e1e8c0c completed successfully as an execution, not timing acceptance. Both original DB readbacks matched. Positive optimization margins (setup 50 ps, hold 25 ps) left the original 4 ns clock, I/O budgets, libraries, derates and zero-slack acceptance unchanged.

Cache all-constrained-path final setup: slow -0.022251979 ns, typical +1.089151502 ns, fast +1.733969331 ns. Final hold: slow +0.178296044 ns, typical +0.087623879 ns, fast +0.025209585 ns. Register-only slow setup is +0.050769 ns, which does NOT close the input path. Baseline all-path slow setup remains -0.190607980 ns, fast hold +0.020921515 ns. These are ideal-clock isolated-block estimates, not routed chip signoff.

Authenticated safe artifact 14129230698 SHA256 9772aa9f3b23a62bbaa900a028fec6417812e3890dffef89968d8a419b8bf3b9; native artifact 14129275553 SHA256 b9b6166a75a2889ee88f952abaf8b9e00f2fb151f4654d4dd9a0ceab290551c4 remains cloud-only. Full receipt: docs/evidence/eop-block-guarded-repair-20261114.json.

Next: inspect remaining input path and native optimization log before choosing another ECO. Full-chip EOP postCTS run 43633451595 remains live, exact source 2c515a0bfb946ef244cc9e94e2f6af8a7e22e2fe. New full-chip boot job 132560946622 remains live. Old buf4 run 43610680141 has completed routing and advanced to nominal OpenRCX / three-corner STA; do not transfer its result to new EOP RTL. Paired650 full transient 43626358999 and old predecode boot 43620739672 also remain live. No duplicate runs or acceptance relaxation.

## 2026-11-14 — fresh EOP mainchip CTS completed; postCTS repair dispatched; independent block audit found input violation

Mainphysicaljob132560946246 ofrun43632152541/sourcea763617997b618370792779deb37ab711e79774a COMPLETEDSUCCESS (664.236s). IndependentIcarusbootjob132560946622 stilllive, sooverallruninprogress. Actual20macroplacement/CTS, protectedsourcesunchanged. CTSODB55a060b56ff638d3d859c78f514cb949f8b5a573bbe0e32dd82cf80b68d66ec4 at run/27-openroad-cts/state_out.json. Safe14128368896 SHAcb4b0de4d03e1d7d071ea36950c466708bc20a31f99828529244533c5a07c1af; native14129335105 SHA1b13027b0c4d4d3c5c8c5c30fc7dd106e0be90e163ca6fdaa8b38ac7fbecbd06,302421624bytes cloudonly,356hash-boundfiles. Fullreceipt docs/evidence/eop-chip-placement-cts-20261114.json. InheritedCTSmetrics areNOTfreshpostCTSSTA.

FreshpostCTS branchcodex/eop-chip-postcts usesauthenticatedcompletedphysicalJOB (notoverallrunconclusion,becausebootindependent), exactproducerhead/attempt1 andnative/safepins. Restoresoriginal60mappedfiles viaqualifiedreport14128104943 andsamefourprotectedsourcehashes. Discardsinheritedmetrics. Separatesbefore/after slow/typ/fastSTA, propagatedclocks, original20/4/8/8nsand5percentderating, existingelectrical/setup100/hold1000repair. Nochangingcheckerlimits, nooldbootproof. KeepfullPHY/finaltimingfalse. Experimentalworkflownotmerge.

Independentblockall-path audit43633057865/source1609e8efff5523fdb3b19cc717437d8ddee7c61b PASSEDexecution butFOUNDtimingviolation. SameexactrepairedODB, nooptimization, regmeasurementsmatch. Cacheall-constrained slowsetup-.037968963ns,typ+1.088527799,fast+1.719216108; minslow+.089274243,typ+.032396004,fast+.000090150. Worstslow startsin_sop_i andends_09986_/D. Baselineinputslow-.198555619ns. ThuspreviouspositiveREG-ONLYresultisNOTblockclosure. Safe14128722987 SHA9a2f4224ab32af7665c16e1ca8f6a5cfcf69e16369e067323e280b9524579611; receipt eop-block-all-path-audit-20261114.json. Unconstrainedresetpaths/electrical/CTS/routedqualificationstillopen.

Nextblockbranchcodex/eop-block-guarded-repair/source470ff1618470f9c2875aa6b021db85591e1e8c0c usesexactcontinued_holdODB andaddspositiveoptimizationguards: setupmargin .05ns; holdmargin .025ns withsetupmargin .05ns; setup600/hold1000/maxbuffer40. Originalclock/IObudgets andacceptance0unchanged. Independentallpathreports afterlegalization, 24reports/candidate, before-regmeasurementsmustmatch. PinnedOpenROADdcf361... Resizer.tcl primarysource confirmsmarginoptions; doesNOTsupportnewer -path_group so thatoptionNOTused. No falsepaths/allow_setup_violations. Needinspectreportedallpaths, notgreenworkflowalone.

Newrun handles:

[
  {
    "id": 43633349306,
    "head_sha": "470ff1618470f9c2875aa6b021db85591e1e8c0c",
    "status": "in_progress",
    "conclusion": null
  },
  {
    "id": 43633451595,
    "head_sha": "2c515a0bfb946ef244cc9e94e2f6af8a7e22e2fe",
    "status": "in_progress",
    "conclusion": null
  }
]

## 2026-11-14 — resumed block register timing positive for cache; independent I/O audit dispatched

Run43632711029/source871de823044485fbe7cb7484d930016550c23a94 PASSEDactualsavedDB continuation. Bothresumed six-corner/mode register-path measurements exactlyreproducepreviousstagewithin2fs beforeoptimization. No synthesis/globalplacement restart. Additionalsetup600thenhold1000/40percent, original4nsidealclock+5percentderates/libraries/layerRC unchanged.

Cacheaftercontinuedhold reportedregister-to-register: slowsetup+.001099ns,typicalsetup+1.395881,fastsetup+2.176728; slowhold+.319269,typicalhold+.119948,fasthold+.000090ns. Addedsetup26resizes17buffers20pinswaps/removed2buffers, then8holdbuffers. Margins1.099ps/.09ps areextremelythin, NOTrobustroutedtiming orfullchipclosure. Baseline registerslowsetup still-.009184ns,fasthold+.000130ns. Native resizerbaselineall-pathWNSalso showed-.155ns despitezero endpointcounterinitslastrow: do nottreat resizerintegercounterasallpathpass.

The existingreports restrict -from all_registers clockpins/-to dat apins. Therefore no all-I/O/blocksignoff claim. Independentconstrained-all-path audit dispatchedon codex/eop-block-all-paths/source1609e8efff5523fdb3b19cc717437d8ddee7c61b,run43633057865. Loadsactualcontinued_holdODB; reproducesoriginalregistermeasurements, then removesonlyregisterendpointfilters fromreport_checks with10000paths/group and9digits atslow/typ/fast. No furtheroptimization. Mustinspectinput/outputworstpaths; unconstrainedreset/clock/physicalcoverage remain outsidethisidealclockblockscreen. Allacceptanceflagsfalse.

Safe14128054256 SHA33d20efb90b41337cc6624e64a3e97fe85c589b7c067e7c4d5770c03c32085cb; native14128074215 SHA2ef9df86ee0b3c2863d8c06ecf474cbdb750f6f765711b416c03e00407304c7a cloudonly. Fullreceipt docs/evidence/eop-block-resumed-repair-20261114.json. Newfullchip43632152541 bothnativeCTS/gateboot stillrunning; nooldpasses transferred. Fullmanufacturinggoalopen.

## 2026-11-14 — exact repaired replay DB continuation dispatched while mainchip CTS runs

Currentblockcontinuation43632711029/source871de823044485fbe7cb7484d930016550c23a94, branchcodex/eop-block-resume-repair. Unlikeearlierpairedscreens, it restoresactualbaseline/cache hold_repair.odb from600iteration43631139914 native14128122304 SHAa997c6d23fe7c5af22a5887830141297f09a3e253da12f86ca2dfde47ff68ae6. Safe14127987571 SHA73154f72f8b9f946118c4fdbea2207a61a1a44167a69d4de1bf64f6cf3ffba39 bindsoriginal measurements. No resynthesis/globalplacement restart.

scripts/continue_eop_block_repair.py authenticatesproducerhead/archive metadata/hash andstrictzip paths. LoadsODB withsameoriginalnativeTcl clock/library/load/RCprefix, removesonlyfreshfloorplan/tracks/pin/globalplacement initialization. Original4ns/5percentderates andallLiberties unchanged. Reportsresumed_before then600additionalsetupiterations andhold1000/maxbuffer40 withlegalization/estimatedRCaftereach. All18reports/candidate required; resumed_before sixcorner/mode worstslacks mustmatch originalhold_repair within0.000002ns. Noacceptanceorphysicalequivalencewaiver. Fullnetlist/layout filesonlycloudartifact; expected eop-block-continuation-derived/native-RUN. If mismatch/failureinspectexactoutput ratherthanrelax tolerance.

Mainchip43632152541/sourcea763617997b618370792779deb37ab711e79774a confirmed bothjobsinprogress: candidate132560946246 innativeplacementCTS; boot132560946622 infullIcarusMBIST+firmware. Both exactsource restorationsteps passed. Existingloaded65043626358999/oldgateboot43620739672/oldbuf4route43610680141 also confirmedliveearlierthisturn. No duplicatesorcancelations. Fullgoalopen; nextusecompletednativeCTSforfreshallcornerpostCTSmeasurement,not inheritedmetrics.

## 2026-11-14 — exact EOP-cache mainchip revalidated; placement/CTS and gateboot dispatched

Originalproducer43630345267/sourcebdd7cc588490425ff98c4718ea8986ecc06a128a finished RTLfirmware andsynthesis butFAILEDpostcheck: cachedcellsource usesabsolute /home/runner/work/nssoc/nssoc/... whilecheckerexpectedrelativepath. Diagnosis43631823524/source638a04f294270b7970b02976bdf76eb4492d255d on preservednative14128012721 SHAd32dd9bb9e0cc1d25f34e29cfbec4bb71908bef7bcaaa577327719602dcd3570 provedactualsingle $auto$ff.cc:337:slice$164145 sg13g2_dfrbpq_1, source310.5-322.8. RTLfirmware28checks passed,failmask0; synthesis115746cells/18845flops,20SRAM. Originalfailedrun remainsfailed, notrewrittenaspass.

Revalidation43631950511/sourcea238c421772e0f1ccd8a8e4ef64e7d5aad1cb894 PASSEDwithoutresynthesis: authenticatedwholearchiveandall60files, correctedonlysourcepathnormalization, requiredoneactualcachedflopclockedpcie_clk_i,26writepredecodebits,16Ethernet+4systemmacros. Safe14128104943 SHA58963d3e81c870b90af23181ebb2fb313a995920cc33affc6cb303082b2b0898. Nativeproducerhead staysbdd7...; validationhead separatelyrecorded. Reportconfiguration isvalidationenvironment; originalproducerconfigurationandrecipesremainintheauthenticated60files, notall originalprepareexportsareinvalidationenv.

ExactnewNL187c813203c0b2a3327eea877da77e697e1abc29efcbf7f83d5beecb86fe012d; mappedJSON1c03ec19a0f8afc2384d92f8974be6cce48ff189e7e1a06e138a69f8754dd8f9; FWab7440619ca719358e6598b0cf291a268c8ccf13357b50ef3a89cbe583e71801. Validatedsourceinputfilesinreceiptmustmatchonrestore.

NEWcombinedphysical/boot branchcodex/eop-chip-physical-boot/sourcea763617997b618370792779deb37ab711e79774a: exact60filehashrestorefromoriginalnativeplusqualifiedmapping; nooldnativeproofreuse. Independentjobs: originalPacketInterfaces floorplan->CTS 20macros/original20/4/8/8ns+5percentderates; andIcarus originaluntouchednativePDK 2Mcycles/19000s gateboot withsystem+EthernetMBIST/all28firmwarechecks. Verilatorsupplemental is notrerunbecauseuntouchedcellincompatibilityalreadyproven; noVerilatorpassclaimed. Bothcandidateaccepted/fullPHY/finaltimingfalse. Sameoutputpathcloud-predecode-chip-placement preservedforrunnerrelativepathcompatibility, butartifactnames EOP-cache. Experimentalworkflownevermerge.

Current combined run: 43632152541 (head/status verified atcheckpoint).

600iterationblockrun43631139914 PASSEDexecution48reports, stillNOTclosed. Afterholdlegalization baseline slowsetup-.338381/fast hold-.009951ns;cache slowsetup-.216959/fast hold-.017249ns. Cachetypicalsetup+1.271659,fas tsetup+2.120494ns. Native14128122304 SHAa997c6d23fe7c5af22a5887830141297f09a3e253da12f86ca2dfde47ff68ae6. Fullreceipts/pathscommitted. Residualcache slowpathonehot[1]->_ahead bank0bit5 throughbuf1/buf2selecttree;fastholdreplay_first->transmit_slice.spare_data[0]. Pathsdiagnosis43631707241 usesoriginalmappedaliasesforregisteridentity; mastertypesinactualtimingreportoverrideoriginalpreECOaliascelltype (someflopsresizedto_2). Do notconfusealiaseswithpostECOmasters. Setupstillstoppedat600with100endpointsbeforelegalization; no blindnewtriallaunchedwhilemainchipstarts.

Fullgoal remainsopen. Existingoldgateboot43620739672/oldbuf4route43610680141/newloaded65043626358999 were lastconfirmedlive; useoriginalhandles. Nextchecknewfullchipjobs, thenfreshpostCTSrepair/extractedrouting/ownLVS andexactnewgateboot. Allnativefilescloudonly.

## 2026-11-14 — paired setup/hold repair completed, residual violations retained

Run43630824750/source8161dd822bd24533d78825f3f176d3ef26116c2a PASSED nativeexecution and48requiredreports (24/candidate), NOTtimingacceptance. Holdbufferbudget40 permittedbothcases tofinish. Baseline1291holdbuffers/cache1299 (+15.8/+15.9percentarea duringholdstage); alloriginalconstraints unchanged. Freshafterlegalization:

- Baseline setup-only slow-1.220659ns; afterhold slowsetup-1.305586,fasthold-.009951ns.
- Cache setup-only slow-1.054706ns; afterhold slowsetup-1.123962,fasthold-.017249ns. Typicalsetup+.684403,hold+.095383; fastsetup+1.771932; slowhold+.284414.
- Both stillviolate original4ns/5percentderated ideal-clock blockscreen. Holdrepair addsdelayandworsensslowsetup. Noallow_setup_violations; nofalsepath changes. These are NOT routed/mainchip metrics.

Fullsourceboundreceipt docs/evidence/eop-cache-setup100-hold40-20261114.json. Safe14127978185 SHA f7414f5e30a18140ce712ba46f35b9f2e4021c8689c380b36ac488f18e423de6; native14128008179 SHA0f8f92b95ad8deeac73f86bc4687f739ec90b29b86c35fa6c5a8cf36158bac66 stayscloudonly.

Native logs showsetupstoppedat100iterationswhileimproving, notconverged: baseline86resizes14buffers/378violatingendpoints,cache96resizes6buffers/381violatingendpoints. Nextcodex/eop-cache-setup600 extendsONLYsmallisolatedpaired setupsearch to600, keepshold1000/40percent andeveryoriginalconstraint. Fullchipsearchlimitsunchanged. Discovercurrentrun frombranch; neverrerunlivehandle. Mainchip43630345267 remainsrunning separately; noacceptednewsource yet. FullPHY/productiongoalstillopen.

## 2026-11-14 — isolated native hold repair hit buffer budget; same constraints continuation dispatched

43630531400/sourceacb583e43098fc4f1b58aa7422f67a6c5493ef0c FAILED during baseline hold repair, beforecachecandidate. Native baseline setup resized86cells, inserted14buffers, swapped8pins andimprovedreportedWNS around-2.882->-1.219ns beforelegalization. Exact6corner/mode postlegalization reports are recorded in docs/evidence/eop-cache-repair-buffer-budget-20261114.json. Hold inserted1267buffers (+15.5percentarea) and stoppedRSZ-0060 Max buffer count reached. This is NOT successfulholdclosure orcompletepairedcomparison. Native14128102442 andsafe14127483579 retainpartialstage; no outputs discarded locally becauseeverythinghosted.

Currentcontinuation43630824750/source8161dd822bd24533d78825f3f176d3ef26116c2a, samecodex/eop-cache-timing-repair branch. Uses -max_buffer_percent40 forhold instead ofdefault20; setup100/hold1000iterations unchanged. OpenROADprimary README explicitlydefines this as maximuminsertedbufferpercentage, notslackthreshold. Same4ns/5percentderates/inputoutput/area/libraryconstraintsforbothcandidates. No allow_setup_violations switch. Nativeplacement/legalization/all3corner measurementsrequiredafterrepair. Flagsaccepted=false persist; morebuffersmayregresssetup/area/routing andmustbemeasured.

Fresh mainchip43630345267 confirmedliveatthischeckpoint in firmwareRTL+fullsynthesisstep; no newboot/placement startedbeforeexactsourceavailable. ExistingloadedPHY43626358999, oldpredecodegateboot43620739672 andoldbuf4route43610680141 were lastconfirmedlive; continue originalhandles, no duplicate. Goalactive/incomplete.

## 2026-11-14 — EOP-cache behavioral qualification PASSED; paired physical gain measured

Simulation43629411055/source00113c97cc04fc41551e45e1efa9c0499aa2bc17 PASSED12positive300k-cycle runs (cachealone6/allphysicaloptions6), original output/storage/coverage checks intact; all12compiledwrong+2increment controls rejected. Exact source e478d785... unchanged/restored. Formal43629312391 already passed2physical-option sizes. Full receipts now in docs/evidence/replay-eop-cache-qualification-20261114.json.

Physical43629920068/sourced25b831d07ae9f3444fec0b78656bcd5c02bee37 completed, NOTclosed. Actualcachedstate isone sg13g2_dfrbpq_1, source soc_pcie_replay_tx.v:310.5-322.8, loweredQ andmappedcellbothbound. Baseline5895cells/cache5870. Same600umcore/4nsidealclock/5percentderates/IHPlibraries/layerRC: afterelectricalrepair slowsetup-2.881974 -> -2.486284ns (395.690psbetter), typical-.367894 -> -.142452, fastsetup+1.067601 -> +1.279902. Fasthold-.048063 -> -.064218ns (16.155psworse). NoCTS/routed/fullchipacceptance. Previous isolatedwritepredecode results had different preprocessing; compare onlycurrentpaired baseline/cache.

Nativealiasdiagnosis43630223798/sourceb424163331ae07b47deba73c58a2ab6ceca89079 passed. Oldcriticalread_pos[1]->replay_read_onehot[62]. Newcriticalreplay_read_onehot[33]->read_replay_bank[0].ahead[5]; 0.15-0.19pFloads and0.8-1.2nsbuf1stages dominate distribution, comparatorno longerworst. Fastholdendsnext_store_sequence[0]. Safe/native IDs+SHA/fullpathreceipts retained in evidenceJSON; native14127781771 remains cloudonly.

Fresh mainchip43630345267/sourcebdd7cc588490425ff98c4718ea8986ecc06a128a uses new default-off EOP_CACHE forwarded by both sim_soc.sh and syn_soc_top.sh. Preservesallprioroptions20SRAM/firmwarechecks. Checker binds exactnewRTL, onecachedsourceflop and26writepredecodebits. Newcandidate; gateboot/postCTS/routing/RCX/DRC/LVS stillrequired. Do notinheritoldpasses or cancel liveoldgateboot.

Next blockrepair sourceacb583e43098fc4f1b58aa7422f67a6c5493ef0c/codex/eop-cache-timing-repair extends identicalpairedscreen with native setup100iterations andhold1000iterations, legalization andall3cornerreports aftereach;24reports/candidate mandatory. Acceptanceconstraintsunchanged. First dispatch preparation hitGitHub git/trees422timeout beforebranchcreation; authoritativeabsencechecked andtreecreationretried, nowdispatched. Not a CADfailure. No experimentalworkflows/candidateRTL merged intointegration yet.

Current new handles:

[
  {
    "id": 43630345267,
    "head_sha": "bdd7cc588490425ff98c4718ea8986ecc06a128a",
    "status": "in_progress",
    "conclusion": null
  },
  {
    "id": 43630531400,
    "head_sha": "acb583e43098fc4f1b58aa7422f67a6c5493ef0c",
    "status": "in_progress",
    "conclusion": null
  }
]

## 2026-11-14 — EOP-cache physical screen current handle and alias diagnosis

Current physical trial43629920068/source d25b831d07ae9f3444fec0b78656bcd5c02bee37 on codex/replay-eop-cache-placement. First43629515583 failed at missing replay_eop_q alias; second43629722934/source9ba674777abc814c6691cf2f077178d928943d58 proved both replay_eop_q/core_eop names optimized away (only external EOP names retained), then failed the alias guard. These are mapping-validator failures before placement, not measured timing failures. Original candidate RTL unchanged e478d785... and clock constraints unchanged.

Current mapper emits pre-synthesis lowered JSON after proc, identifies the unique $adff Q driving replay_eop_q, and follows its exact src range to exactly one sg13g2_df mapped cell. No keep attributes, no aliases manufactured, no bypass of cached-state survival check. Both baseline and candidate use the same added lowering step. Entire native artifacts remain hosted. Only after state-survival check passes can placement and before/after electrical-repair reports execute. Do not reuse first two failed handles.

Simulation43629411055/source00113c97cc04fc41551e45e1efa9c0499aa2bc17 remains separate:12positive300kcycles plus12compiled wrong-increment controls. Actual formal43629312391 already passed bothphysical-option sizes. No candidate integration or fullchip timing closure claimed. Next inspect complete actual simulation report; inspect physical report or exact mapping assertion if it fails. Then target wholechip implementation if candidate measurements justify it, preserving all originalclock/hold/inputoutput constraints and verifying actual gateboot/routing/RCX/LVS for newnetlist.

Live snapshot at this checkpoint:

[
  {
    "id": 43629920068,
    "head_sha": "d25b831d07ae9f3444fec0b78656bcd5c02bee37",
    "status": "in_progress",
    "conclusion": null
  },
  {
    "id": 43629411055,
    "head_sha": "00113c97cc04fc41551e45e1efa9c0499aa2bc17",
    "status": "in_progress",
    "conclusion": null
  },
  {
    "id": 43626358999,
    "head_sha": "73b781d77b169a4c270bb635197540d3c8f96a9c",
    "status": "in_progress",
    "conclusion": null
  },
  {
    "id": 43620739672,
    "head_sha": "98281a5792ac15ed28f5ecd001b0cff462e95f99",
    "status": "in_progress",
    "conclusion": null
  },
  {
    "id": 43610680141,
    "head_sha": "d42836ac2566de769473973bb15625e27f788f8d",
    "status": "in_progress",
    "conclusion": null
  }
]

## 2026-11-14 — replay EOP-cache candidate implemented; full RTL equivalence PASSED

Actual new mapped JSON diagnosis43629195905/source023bc757bd46e6130afa1092e0dc927137a0d76d proves worst slow setup goes retry.read_pos[1] -> replay_read_onehot[33], not byte storage. Exact source mapping532a165624564dcc0f1b1bd7904e697b244afcdadde7d289b2bd9fb07e01d59a. Fast hold endpoint slice365153 is functionID bit5, confirmed. Safe14126803650 SHA f75ba0cdd33c84f0879670b13e2e04ad378cd3ba2d1d4cb277073f8ac786e378. Do not infer endpoint names from nearby old candidates.

Implemented default-off SOC_PCIE_REPLAY_EOP_CACHE on experimental branchcodex/replay-eop-cache/source3d813a0c4273f1f1864267d8c04c0b632b4bb004. Caches read_pos==send_last with same reset/send-start/cursor-update behavior; no extra stream latency. Reset bothoperands0 => cached1; linkloss holds; accepted nonlast increments BW-bitcursor; sendstart compares length==1. The aim is removing equality logic from high-fanout replay cursor control. Other critical paths may replace it; no timing benefit claimed yet.

Full actual module/memory sequential equivalence43629312391 PASSED both2x22 and4x38, with write-predecode/AHEAD/INBANK/RESET_COPIES common. SourceRTL SHA e478d785013174a7a7ce63b6fcbd8aa609736e65e292748eb8c0311e453f69e8; safe14127810063 SHA00f02a7949b2659a356c56b617166b31ab7770bea85e6bdfd52b2861102f4519. Original OSS2026-08-04, async2sync/induction; not analogreset or physical timing proof. Receipt docs/evidence/replay-eop-cache-functional-20261114.json includes exact mapped aliases and both proofs.

Actual simulation43629411055/source00113c97cc04fc41551e45e1efa9c0499aa2bc17 running: EOPcachealone and allphysicaloptions, six300k-cycle seeds each, with all original coverage/storage/output checks. Both configurations also compile wrong+2cursorincrement and require all6realMISMATCH verdicts; vvp failure no longer masked. Sources restored after mutation; no expected stream changed. Follow this handle before integration.

Same-area native mapping/placement dispatched on codex/replay-eop-cache-placement (source/run discover branch). Uses same600x600um,4nsidealclock,5percentderating, identicalIHPcorners/RC; baseline includeswritepredecode and differs only cacheflag. All original reports remain; estimated/block timing cannot certify whole chip. Experimental workflows must not merge. Candidate RTL currently NOT integrated into timing/combined, pending simulation and physical evidence.

Existing actual650loaded43626358999, wholechipboot43620739672 andoldbuf4route43610680141 confirmedlive this turn; not restarted. Fullproductiongoal active and incomplete.

## 2026-11-14 — full critical-path diagnosis completed

Cloud extraction43628894510/source2fcec5a42f0e16aee066a9c0540fcf07b7e2e85b PASSED; safe14127227743 SHA f1458a2f1fd146a582b8a4b26cae978b71ec18a3d32f64b4467688903a6366f9. Full worst paths per group committed in docs/evidence/predecode-postcts-critical-groups-20261114.json. Report limited to1000paths/group: do NOT mistake reported violating count for full STA endpoint count.

New candidate slow setup worst PCIe -3.164052ns (1000/1000 reported negative), CPU-.665779 (40reported), async-.293908 (50reported). Ethernet TX+.110500 and RX+1.242997 at placement estimate, not routed closure. Worst PCIe starts retry.read_pos[1]/slice163666 and ends slice163909/D through read decode, highfanout buffers and final mux. Actual dataarrival8.478067ns versus required5.314015ns. Large weakbuffer780064 adds1.013977ns; decoder gates and hold39356 also contribute. Need map destination via exact mappedJSON and inspect read-decode topology before redesign. Strengthening one buffer alone cannot substantiate 3.164ns closure; must compare measured threecorner effects without deleting hold protection or relaxing clocks.

Fast hold groups: PCIe238 reported,EthGTX10,CPU2,EthRX1 (total251); worst functionID input-.496129ns,Ethoutput-.236079,CPU-.152594,EthRX-.010314. Repair must cover real external input/output timing too, not just register paths. Full report includes exact source/destination/gates. OldRTL route result remains separate and rejected. Native boot43620739672, newloaded65043626358999 and oldbuf4route43610680141 were inprogress at last check. Continue those handles; no new compute duplicate launched.

## 2026-11-14 — completed postCTS and routed results; permanent evidence verified

Fresh predecode postCTS43625119515/source63a2a8fbed52f0765a46cd5f5cbacff5cf773623 completed native repair, NOT timing closure. Fresh before->after: slow setup WS -8.04621->-3.16405ns, count2611->2761; hold526->3 (WS-.698812). Typical setup826->451,WS-.985106; hold1036->25. Fast setup271->0,WS+.292031; hold14266->251,WS-.496129. Original20/4/8/8ns,5percent derating preserved. RepairedODB36872bcd4a4548e1a155dca4292947526b7217a165049e311ab6ec2754718440. Native14126623378 SHA c3a38efc51b1919a2c8c477078e7ab90c22514b9f764f2a2faeb24160ebab7d5 remains cloudonly. Boot/equivalence/routing/extractedSTA and own LVS remain required.

Worst observed new slow path starts u_pcie.flow.packets.retry.read_pos[1], includes hold39356 and heavily loaded sg13g2_buf_1 ($abc$734260$auto$blifparse.cc:397:parse_blif$780064: .203877pF,1.280644ns slew,1.013977ns delay). Need full path/endpoint and per-group coverage before choosing targeted physical repair; do not remove hold buffers blindly. Fast worst hold is pcie_function_id_i[5] to slice365153/D (-.496129ns) with two delay cells and propagated capture clock. No false paths or relaxed input/clock constraints authorized as workaround.

OldRTL exact-jumper run43614100441/sourceb83bc3a3f204bf9a2833c89fd632ae9308a58b56 completed route successfully but FAILED timing/electrical/antenna acceptance. DRT errors0 is not full DRC. Antenna178nets/191pins (other-scope metric143), vs prior377/424. Fresh nominalRC: slow610setup,WS-1.02523104ns,hold0; typical setup0/hold7; fast setup0/hold118,WS-.118013824ns. Slow reported setupgroups PCIe582,CPU25,EthTX1,async2. Fast hold PCIe114,CPU2,EthRX2. Slew570/cap102/fanout1477 remain. Do not merge/adopt as closed. These are oldRTL results, not predecode candidate closure.

Authenticated slim reports43628260289/safe14127078135 SHA eb4e5b9a3aa08bf225c81ae22bf6ed6e52fd33c5d262c17698c1505f951b5ed3 are now committed as docs/evidence/postcts-jumper-*.json. Original large safe archives need not download locally. Follow-up cloud-only full critical-path/per-group extraction dispatched on codex/postcts-critical-path-groups source2fcec5a42f0e16aee066a9c0540fcf07b7e2e85b. Numerical source/report inputs unchanged; experimental workflow must not merge.

Permanent intermediate PHY preservation43628177807/source88fe59545ee0379fced9b28f15a682606fa44f20 PASSED. Independently read back all15 archive assets SHA/size/state and exact16-asset release set; prerelease445511108 remains explicitly NOT production approval. Manifest and full receipt committed in docs/evidence/paired650-{archive-index,preservation}-20261114.json. Release tag cloud-paired650-evidence-88fe59545ee0379fced9b28f15a682606fa44f20. Earlier43627949773 failed before uploading due tag permission; current reserved-tag workflow succeeded. Native content stays hosted. Future loaders need manifest fallback when Actions artifacts expire.

Last live checks: actual new650 full loaded simulation43626358999, exact new gateboot43620739672, oldRTL buf4route43610680141. Do not duplicate. Full serialPHY, newchip closure and production approval remain false.

## 2026-11-14 — actual wire-load comparison PASSED, mixed physical tradeoffs measured

Diagnostic43627389964/sourced4569fbeb75818b37d41b7ba8fcacbe84eab5acb completed. Safe14126747208 SHAc874d25604a057d33f796e44d3cacd56ac97aa0a8259e6aee49d5edf93f13976. Full source-bound results (12semanticnets,allHBTterminalbindings,allDCpairs) in docs/evidence/cdr650-paired-wire-load-comparison-20261114.json. Whole native files remain cloudonly. Sparse DCresidual/reciprocity and3analytic controls passed.

**Measured groundC fF old->new:** adp246.379->148.995;adn248.238->150.811;cdp207.690->153.798;cdn213.092->159.162. BoundarycouplingC remains substantial:adp320.142->318.3037;adn347.0928->345.3431;cdp237.2183->227.3175;cdn257.7002->247.8894. Max driverC-to-receiverB wire-onlyDC R ohm:adp130.6389->124.7297;adn138.6359->132.7267;cdp126.7609->123.5025;cdn134.7579->131.4995.

**Regressions must remain visible:** aqpground181.100->196.196;aqn206.264->221.361; cqp314.273->367.941;cqn286.199->339.873fF; theircouplingalsoincreases. s0p/s0n ground+4.92/+4.83fF, s1p/s1nunchanged. Thus actualpairingreducesA/Cdata-bufferwireload butincreasessampleroutputload. Do notadoptongeometryorcaponly. Pendingfull65043626358999 mustcheckA/CsamplerwaveformsaswellasX/YandoriginalSOA. Ifnewwavefails, usethesequantitative tradeoffs in nextlayout/circuit decision. NevergroundallcouplingC andcalliteffectiveload; theseareseparateboundaryentries, notdynamicdelay orfullRFPEX.

Newfull65043626358999 andpostCTS43625119515 were stillin_progress atpriorcheck. No duplicate launched; no acceptanceflags changed.

## 2026-11-14 — targeted native wire-load comparison dispatched during full650 transient

Actual full650 composition/loaded run43626358999/source73b781d77b169a4c270bb635197540d3c8f96a9c and postCTS repair43625119515/source63a2a8fbed52f0765a46cd5f5cbacff5cf773623 still live; original boot43620739672/routes43614100441/43610680141 also live. Do not restart them. GitHub REST job-log endpoint returns404 while live; BrowserOS neo is logged out and cannot reveal live logs. Browser task tab was closed. No browser auth is needed for existing API/finished artifact workflow.

New diagnostic branchcodex/cdr650-paired-wire-load-compare/sourced4569fbeb75818b37d41b7ba8fcacbe84eab5acb compares actualold/new metal networks. All native content stays hosted. Uses originalfullcomposition input pins for old metal41728568165 andidentity41712243960; newnative14125201998 andidentity14125295448. Resolves semanticnet names through nativeLVS originalsource-terminal mapping, nevernativeID equality. Targets adp/adn/cdp/cdn/s0p/s0n/s1p/s1n/aqp/aqn/cqp/cqn. Checks650device/2046terminal/1428physicalpoint/113conductor ownership, exactR28634/C18476old vs18488new/MIM7. Reports boundary groundC, boundary couplingC and internalC separately. Open-circuit wire-only DC resistance computed by sparse nodal solve between actual HBT collector andbase contact anchors, with residual/reciprocity and3analytic series/parallel/dangling-branch controls. This is NOT effective capacitive load, RF PEX, gate delay or loadeddevice acceptance; flags remainfalse. Result should explain whether targetedroutingactuallyreducesload, notreplacefulltransient.

{"id": 43627389964, "head_sha": "d4569fbeb75818b37d41b7ba8fcacbe84eab5acb", "status": "completed", "conclusion": "success"}

Expected safe paired650-wire-load-derived-RUN/result.json only. No newnative archive published because exact inputsalreadyimmutable. Source script scripts/compare_paired650_wire_load.py ondiagnosticbranch. If analysisfails inspectactualassertion; no weakenedclosure or semanticgroup assumptions.

Current integration audit also confirmed training_epoch_control/typed ingress are externalPMA bundledmailbox/record transport, notfullLTSSM. No newRTL changed orserialintegrationaccepted. Continueactualanalog/electrical andchipclosure while preservingthisfullgoal gap.

## 2026-11-14 — new gate port reduction PASSED; actual new full650 composition dispatched

Run43625754764/source0308a08571969e629fb567c811414edb925a0dbc PASSED503native simulator executions,250port networks (50groups × partitions1/2/4/8/16), fullDC/AC/power/thermal-noise comparisons. Both actual noiseless-conductance and wrong-resistance controls rejected; original numerical tolerances unchanged. New75nm mesh SHA45154a042c59c9264af38e89b8e99cd8d38387f934ee3172b2cc8d110092d7e4,74637551bytes. Safe14125119960 SHAb49bb48108f0a6499016092c5ccfd83795bd25af1b88773fbcc55d22ff8d258f; native14125304132 SHA60749878a9146a9115289993ba0b3227ba3952678a3e2a0200ed0eb6e33476c1,217053309bytes,CLOUD ONLY. Receipt docs/evidence/cdr650-paired-gate-reduction-20261114.json retains full250network proof andfault/tolerance/thermal/currentidentity records. Nominal R-network port reduction only: calibrated material/PVT/polyC/fullPHY remain false.

**Next actual full650 circuit:** branchcodex/cdr650-paired-full-composition/source73b781d77b169a4c270bb635197540d3c8f96a9c. Original factory9bba58288772dd2bee9dab142e391d0616737973, newpaired_current actualidentity/geometry, newmetal43623877135 andnewreduction43625754764. All selected matrices/fragments checked against qualified250network report. NEWmetal wires.spice exactSHA c155530d8f6688ddee3a11258cd5c2de0578e6b0d086a253323ee7e5eea9011a,2020502bytes; anchors08 taken from sameauthenticatednative. Assembler onlychanges expectedC18476->18488 and reportedcontractC; actualR28634/MIM7/650devices/2046terminals/1428physicalpoints remain strict. Source MOSfixture regenerated fromactualnewnative identity/geometric gates, not copiedoldIDs. Frozen originalcanonical500 binding supplies nonMOSparameters only, neveroldRC. Original intrinsicRFmodel gate-resistance partition and all otherparameters preserved. No rejectednx1/bias/sizing whatif applied.

Workflow assembles all5partition bases then runs original full256bit nominal_late withn=1. Originalloaded stimulus, waveform, device SOA anddiagnostic gates unchanged. Need inspect any mismatch, startupwarning or waveformfailure; nofullPHYpass inferred. Safe expected paired650-full-composition-derived-RUN, native paired650-full-composition-native-RUN. Native file lists are saved if acquisition fails. Preceding1df98ade... preparationdoc is historical, notsuccess. Experimentalworkflow nevermerge intointegration.

[{"id": 43626358999, "head_sha": "73b781d77b169a4c270bb635197540d3c8f96a9c", "status": "in_progress", "conclusion": null}]

PostCTS repair43625119515 still running at priorinspection; continueoriginalhandle. OldRTLroutes andactualIcarusboot remain independent. Fullgoal active/incomplete.

## 2026-11-14 — fresh actual paired650 gate resistance mesh PASSED

Run43625413974/sourcebc78aa9667a0915c7dc31b244b714a1d2166a362 completed successfully on new actual GDS285760...:50groups,200intrinsicgate areas,200realcontacts, four600/300/150/75nm grids,4native analytic70ohm checks and4fullmesh current-return checks passed. Actual metal/poly/contact enclosure and SalBlock/pSD exclusion reread; original numerical mesh method unchanged.150to75nm maximum uniform-injection average change0.004297672003824132 (0.4298percent), NOT full nonlinear convergence or PVT qualification.

Safe14124829951 SHA15c92cb7f9ca584c69e116dfa957abd2612f25f8efc5cc3cfea933538ccd88fc; native14125203854 SHA0485478594d39baa2bec3e3b769b4cf3b33ad1c19a95bce5bd50b6ed2e9ccba8,87016922bytes,CLOUD ONLY. Native root native/mesh-75/{mesh.json,gate-poly-resistors.cir}. Receipt docs/evidence/cdr650-paired-gate-mesh-20261114.json preserves all four nativecheck/mesh reports. This generates nominal gateR only; polyC, calibrated material corners, fullintrinsic/metalcomposition and fullPHY remain false.

Next noise-preserving reduction is dispatched on branchcodex/cdr650-paired-gate-reduction. Original reduction characterize() body unchanged except authenticated NEWmesh acquisition and NEWnative200device fixture. All50groups × five partitions1/2/4/8/16,503nativeDC/AC/power/noise executions including2faultcontrols remain mandatory; no cuts to original tolerances. Follow handle below, do not reuse old reduction matrices. Outputs expected paired650-gate-reduction-derived-RUN/native-RUN. Original header --controls mode still refers historicalfixture; workflow invokes --extract with new actual readback and sourceclosure checks.

[{"id": 43625754764, "head_sha": "0308a08571969e629fb567c811414edb925a0dbc", "status": "in_progress", "conclusion": null}]

PostCTS repair43625119515 remains running separately. Fullmanufacturinggoal incomplete; no originalroute/boot restart.

## 2026-11-14 — fresh postCTS repair running; new physical gate-mesh extraction dispatched

**PostCTS:** first43624906428/sourcea425eb5b862feeda83ed86f455b621d2f140fb4f failed before CAD because scripts/restore_predecode_chip_boot.py was absent from integration base. Added exact tested helper from placementa3a79275..., verified all4original mapped-source input hashes against candidate branch before dispatch. Current source63a2a8fbed52f0765a46cd5f5cbacff5cf773623/run43625119515: exact mapped-source restoration and pinned runtime preparation passed; native three-corner before/after STA plus electrical/setup/hold repair confirmed in_progress. Continue this handle, not43624906428. Original clocks/derating unchanged, boot/equivalence/routedRCX remain separate.

**Fresh paired650 gate mesh:** branchcodex/cdr650-paired-gate-mesh/sourcebc78aa9667a0915c7dc31b244b714a1d2166a362. Adapted original qualified mesh producer41721107217/source6fc562599fdc527bf95c0ef92332e87a4efd26e6. Numerical characterize() body byte-identical except both exact GDS pins changed to new285760.../1627742bytes. Acquires new actual candidateGDS native14124521775, terminal geometry safe14124672969, native identity safe14125295448; binds producer IDs, heads, success and archiveSHA. Every actual polygon/contact and200MOS dimensions/ownership reread. Original four pitches600/300/150/75nm, analytic70ohm checks, full200gate current-return conservation retained. Frozen nominal7ohm/square and15ohm/contact are still only nominal published material values, NOT calibrated signoff corners or temperature. Intrinsic model/runtime unchanged. Must not claim polyC/material/fullPEX/loadedPHY qualification from this resistance-network diagnostic.

First mesh43625347253/source0ba45c... failed pip because version parser truncated0.30.4.post1 to0.30.4.; corrected exact original version and workflow pin, no numerical acceptance change. Current snapshot below. Expected safe paired650-gate-mesh-derived-RUN and native paired650-gate-mesh-native-RUN. All native content stays hosted. Next after gate mesh: original noise-preserving port reduction producer41725473326/source8d7874d8c9740725ed1e4cd8c3631ec1c81bc2e6, then full composition factory41733225660/source9bba58288772dd2bee9dab142e391d0616737973 using NEW metalRC43623877135 and NEW gate mesh/IDs. These original factories are reference only; never import old native geometry/RC or rejectednx1 whatif. Original frozen waveform/retimedD/SOA gates remain.

[{"id": 43625119515, "head_sha": "63a2a8fbed52f0765a46cd5f5cbacff5cf773623", "status": "in_progress", "conclusion": null}, {"id": 43625413974, "head_sha": "bc78aa9667a0915c7dc31b244b714a1d2166a362", "status": "in_progress", "conclusion": null}]

Full chip manufacturing goal remains incomplete. Original oldRTL route43614100441/43610680141 and boot43620739672 were live this turn, not restarted. Experimental cloud-evidence-summary.yml workflows must not merge into timing/combined.

## 2026-11-14 — correction: inherited metrics were NOT post-CTS timing; fresh repair dispatched

Authenticated stage diagnosis run43624756918/source078cba2d9f1e0476c3a62bb0e96c934855a2ba68 PASSED. Safe artifact14125851871 SHAbd8bea1955083690d7d32561049a24bb05018103008e11f0771505244432831f contains original-hash-checked metrics plus independently hashed first240-line report excerpts. The prior CTS snapshot mixed stale inherited metrics: slow -207199132.342ns and typical -127533037.097ns originated in step04 STAPrePNR, fast -71.779ns in step23 STAMidPNR BEFORE repair24 and CTS27. Step27 or_metrics_out.json contains NO timing metrics. Do not cite any of those as measured post-CTS timing. PrePNR worst path goes from rst_sys_n (5327loads,24.787149pF,153.759842ns slew) through row_bm to SRAM A_BM; report shows213590672ns terminal slew and -207199008ns library setup. These are diagnostic pre-placement/model extrapolation symptoms, not validated current chip timing; fresh per-corner measurement is required.

Fresh postCTS driver scripts/cloud_predecode_postcts.py is on branchcodex/predecode-postcts-repair/sourcea425eb5b862feeda83ed86f455b621d2f140fb4f. Exact source native14124619734/safe14125635095, all file hashes and CTS ODBfc440027... verified on hosted runner. Restores original mapped source separately, discards inherited metrics, separately measures three corners before/after guarded electrical and setup/hold repair using existing CorrpreBankedPostCTS. Original 20/4/8/8ns clocks and5percent derating retained. functional_boot_accepted=false, accepted=false, finaltiming=false remain explicit; no historical boot proof reused. Experimental workflow MUST NOT merge into integration. This is candidate repair, not routed timing, equivalence, serial PHY, or production approval.

{"id": 43624906428, "head_sha": "a425eb5b862feeda83ed86f455b621d2f140fb4f", "status": "in_progress", "conclusion": null}

Native files remain cloud only; no local source/native downloads. Follow current repair handle; also original boot43620739672 and original routes43614100441/43610680141 still in_progress at inspection. PHY next remains fresh gate-poly RC/composition on actual paired650 geometry, then unchanged loaded electrical gates. Full goal incomplete.

## 2026-11-14 — actual paired650 metal/MIM RC PASSED both native orders

Run43623877135/sourceca7922a41bb122ec714a23cd2ca5b7ea63d197ba completed successfully. New actual GDS285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514 yielded28634resistors,18488capacitors and7separate intrinsic MIM devices. Both native extraction orders produce identical complete R/C/device records; original13raw wire +9MIM identity fault cases rejected in EACH order. Actual650devices,2046terminals,1428anchors,200gatecontacts remained bound. No oldRC reused/scaled. Numerical methods, qualified Magic binary, raw conservation checks unchanged; MIM masks/access points derived from actual new GDS/native identities.

Safe14125052605 SHA26bccc7db4231b610aa780e128fea159424bafdf5b3cc32da3a3a4474f0d506c. Native14125201998 SHA1443428cee3752ae7c9b14aa65d01e614520ca5547e79abf8e406ff3c56617fb (386133458bytes), CLOUD ONLY. Native archive includes mos650-metal-rc/native/mim-precise/wire/rc03/{wires.spice,pump_wires.ext,pump_wires.res.ext} and precise_reversed, plus complete restored paired-terminal-anchors. Receipt docs/evidence/cdr650-paired-metal-mim-rc-20261114.json retains original full result and both complete variant reports.

**Next PHY work:** fresh gate-poly access RC on new geometry/anchors, proper MIM/metal/poly/full650 intrinsic composition, then unchanged loaded electrical checks. Do not call this full RF PEX or full PHY/electrical acceptance: gate_poly_RC_extracted=false,full_loaded_composition_executed=false,substrate_r_modeled=false,full_pex_qualified=false remain explicit. Use actual native650 device parameters and new native IDs; do NOT carry forward rejected nx1 transistor what-if or old RC. Keep frozen retimed-D selector semantics/windows and original transistor SOA gates.

**Newchip CTS diagnosis:** dispatched branchcodex/predecode-cts-path-diagnostics/source3c21f988de3987aec473c2f2ee74a620a688eab0 to select source-hash-checked run/27-openroad-cts text reports from native14124619734, without downloading native files locally. Current run snapshot below. Read worstpaths/clock/slew reports and repair the exact newcandidate; huge placement/CTS delay values are NOT timing acceptance. Actual GDS/ODB assets remain hosted.

[{"id": 43624148622, "head_sha": "3c21f988de3987aec473c2f2ee74a620a688eab0", "status": "completed", "conclusion": "success"}]

## 2026-11-14 — new full-chip predecode CTS completed, timing NOT accepted

Run43622573415/sourcea3a79275ea42940b3c319c7c15cab2ae75f15109 completed placement/CTS in537.19s, returncode0, all protected inputs unchanged. Actual20SRAMs and141520instances, CTS ODB SHAfc4400278ce81212ca7b30bf2d02aa7356f23e512336020e201e98839cd9beab, state run/27-openroad-cts/state_out.json. This means physical stage completion only. functional_boot_accepted=false, accepted=false, final_timing_complete=false remain explicit.

**Timing is severe and requires diagnosis/repair:** fast setup WNS-71.779ns,12777hold violations WNS-0.601382ns,14250setup violations; slow setup WNS approximately-207199132ns andtypical-127533037ns (extreme extrapolated/delay values, cause NOT established). Clockskew metrics around310-320ns;11479maxslew violations/338maxcap worst counts. These are placement-estimate CTS reports, NOT extracted routed timing. Do not compare them as an apples-to-apples regression against the heavily repaired/routed oldRTL baseline. Do not route or adopt this candidate blindly, and do not hide enormous values. Next chip action: read actual per-corner CTS worstpaths/clock reports from saved native archive on hosted runner, identify extreme load/slew/cell/table/constraint cause, then coherent postCTS electrical and timing repair with original constraints. Existing scripts/cloud_replay_crc_postcts.py shows the native repair sequence but its oldboot-proven handoff pins cannot be reused for this pendingboot candidate.

Safe14125635095 SHA27634a4fc273d1dfa52c6bb72cbfde2b50e8f7c3bf15fb5ff73cf31dbad72ace. Native14124619734 SHA244a660873d74ae73e2913c1cd96546817d6a3e0474045a662ea566246adaac5 (301323113bytes), cloud only. Full receipt docs/evidence/predecode-chip-cts-20261114.json preserves metrics, protected inputs, commands and all output hashes. Native archive holds prepared/config.json,physical.sdc,run/... including CTS reports andODB. Never download native archive locally. Use slim derived text report job if needed. Exact newnetlist4b17ff9e... is restored separately from mappedsource43618915765; original60hash binding still valid.

Fresh PHY metal/MIM RC43623877135/sourceca7922a41bb122ec714a23cd2ca5b7ea63d197ba remains live; native newanchors43623472892 alreadypassed. Icarus boot43620739672 andoriginal oldRTLroutes43614100441/43610680141 remain separate pending qualifications. Fullproductiongoal active/incomplete.

## 2026-11-14 — fresh RC current handle after exact geometry pin correction

Follow **43623877135**, sourceca7922a41bb122ec714a23cd2ca5b7ea63d197ba, branchcodex/cdr650-paired-fresh-metal-rc; confirmed in_progress. Previous43623675068/source81c9464b91d9d5b618b604104e97c06212adb3b6 is terminal failure, NOT live. All current source acquisition/anchor hashes/native integer MIM dimensions passed, then support.generate() correctly rejected a stale hardcoded baseline GDS SHA c3351820... before actual native R/C. Replaced that sole source-identity constant with exact newly DRC/LVS-qualified candidate285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514 and rebound source manifest. No geometry, numerical method, circuit assumption, threshold or acceptance check was relaxed. New explicit dispatch uses approved_source=ca7922a41bb122ec714a23cd2ca5b7ea63d197ba. Do not restart a live run.

First failed safe14124782932/7408ea38f69ed1d24d56d716ed0598f17d6004f609bd55064843d2b06442717a; native14125425563/7b4c90bc5b25c23527834e49d32f323ca5f1f96bb3a854f2c442ba1cd2a75efe cloud only. New expected safe paired650-metal-rc-derived-43623877135/native paired650-metal-rc-native-43623877135. Two native orders and13wire+9MIM faults each remain required, followed by new gate-poly/MIM composition and unchanged electrical tests; no new R/C result yet.

Previous actual paired650 DRC/LVS and terminal-anchor successes remain valid for their exact hashes. Fullproductiongoal active, no local files.

## 2026-11-14 — paired650 all terminal anchors PASSED; fresh MIM-aware RC live

Run43623472892/source54a4766e9256d2cd0a3f93f5441ca5d1c238c7ce PASSED actual current650 device-location, terminal anchor, gate-poly-group, contact and dedup workers. 2046terminals,1428distinct physical anchors,200actual gate contacts across50groups, separate intrinsic MOS gates preserved. All source material reread from actual serialized new GDS and L2N; current native-owner probes passed. Ten original actual binding corruptions rejected (lost terminal, parameter, duplicate instance, wrong native owner, missing anchor/group/contact, duplicate contact, gate ideal collapse, wrong group association).

Physical macro relocation proved explicitly: original40 topinstances ->16macros with24topvias flattened into conserved parent geometry; exact declared transforms, full child material and local annotations checked. Wrong translation and missing macro controls rejected. Full old hierarchy equality is correctly FALSE; per-primitive pin identity and explicit relocation proof replace that obsolete invariant. Old qualified primitive local pin drawings hash-bound and checked against unchanged intrinsic geometry, never old global coordinates/native IDs. Firstrun43623331177/sourcee4c109726edb2da17e4b436c21a128072edca351 failed after successful relocation checks due missing FLAGS import; fixed one import and reboundsourcehash before newrun. No geometry or acceptance gate change.

Safe14124672969 SHAa3e3b980b8d03f8ef38d854b414649a40496711d532f4824957184fc9082c199. Native14124873759 SHA0bf3857c86266eb8628545faea5b3a2794b80abaa6f06a09d7c8d1f9c785f422, cloud only. Receipt docs/evidence/cdr650-paired-terminal-anchors-20261114.json. Native archive root contains selected/ and view/; all actual new anchor files under view/wire/. Corresponding fresh flat identity remains graph-safe14125295448/d8376d4009da54acbe52569fd119add9f07f4f13d8120ebc65bd5fa193c899ac; its LVSDB digest must match restored selected/physical/lvs_flat/result.lvsdb.

**LIVE actual fresh metal/MIM RC:** [43623675068](https://github.com/Melihakbulut221/nssoc/actions/runs/43623675068), source81c9464b91d9d5b618b604104e97c06212adb3b6, branchcodex/cdr650-paired-fresh-metal-rc. Source-controls passed, native-metal-rc running. Adapted original1b40bf2db3844d6281c467022b248a2871ced6df factory, unchanged frozen numerical methods, original qualified Magic runtime, explicit seven MIM devices, two native capacitance enumeration orders,13raw wire faults +9MIM identity faults EACH. Only acquisition/source path/producer binding changed to new paired650 archive. Restores original absolute paired-terminal-anchors paths so anchor input hashes remain checked. New cfg paired_view replaces obsolete view producer spec; all materialized source files rehashed before/after. MIM geometry helper now explicitly targets paired-terminal-anchors/native/view. No old R/C used or scaled. No relaxed electrical gates.

Safe expected paired650-metal-rc-derived-43623675068; native paired650-metal-rc-native-43623675068, all native stays cloud. Status still requires full composition, gate-poly RC, and unchanged loaded electrical tests even if metal stage passes. Do not call this qualified full RF PEX. Preserve original component113/net114/650device/2046terminal/1428anchor/200contact counts.

Newchip placement43622573415, Icarus boot43620739672, exactjumper route43614100441 andbuf4route43610680141 remain their original live handles. No duplicates or local files. Manufacturing objective remains active/incomplete.

## 2026-11-14 — new paired650 native identities and fresh conductor graph PASSED

Run43622884786/sourcee0a87989915cb7d65a20176de33649859f013393 completed successfully. New GDS285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514 independently binds650 devices,2046 terminals,25 ports against original schematic identities;15 actual identity corruptions rejected for EACH deep/flat readback. Fresh complete metal/via graph has113 conductor components and114 native electrical nets; every component's material belongs wholly to one native LVS net, no native metal-net split or union-by-label shortcut. This is NOT extracted R/C yet.

Safe14125295448/d8376d4009da54acbe52569fd119add9f07f4f13d8120ebc65bd5fa193c899ac. Native14125325353/b29785a0ad74a923e6c250f564a3f57da8d876e58992d57b5800e18ab4176b47 (215800722bytes), cloud only; contains selected exact new layout/LVS databases and native/view/wire/native05/wires.gds,wires.l2n,result.json. Original physical archive also preserved inside. Full graph/control receipt docs/evidence/cdr650-paired-wire-graph-20261114.json.

Next actual extraction work: qualify primitive pin provenance after declared macro translation and top-via flattening, run locate01.py/current650 gate anchors/dedup, validate all1428 physical anchors including200 gate contacts with current native xrefs. Oldsource_pins() full hierarchy/annotation equality cannot be reused unchanged because actualmacro transforms/public pins moved and24top via instances were flattened into conserved overlay geometry. Preserve per-primitive material/pin identity; verify explicit baseline->candidate transformations and use current native IDs/coordinates. Then run fresh metalRC/poly/MIM composition and unchanged electrical gates. No oldRC or oldanchors accepted as newextraction.

Newmainchipplacement43622573415/sourcea3a79275ea42940b3c319c7c15cab2ae75f15109 remains live at native floorplan/placement/CTS. Boot43620739672 and originalroutes43614100441/43610680141 remain separate pending qualifications. Fullproductiongoal active/incomplete.

## 2026-11-14 — new paired650 layout PASSED native DRC/LVS; fresh graph and new chip placement live

**Completed physical qualification:** [43622190993](https://github.com/Melihakbulut221/nssoc/actions/runs/43622190993), source8274b540b6223e6a9bd2c7aa7b3d2c5046b09a7f. Actual candidate GDS285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514 (1627742bytes) passed560-category DRC with0markers, deep+flat LVS with650devices each (124HBT,200MOS,98rppd,7MIM,221tap), and all13 actual fault cases rejected. Frozen checker SHA30c4586b... unchanged. Complete physical report SHA7fec2657806b39de1cf96815f469787aa66934e7b7f004755cbbbb071ac654bf. NewLEF SHA02f6b1ad6a9f3b4f52281e5330f9f22d95fe71c524d90d3da4973316e5a55741; independent reference21d730545b983930eacf733ba77a7593df52e253987991724de9594fe136bbfb unchanged. Actual25 pin boxes regenerated; footprint2316.6x4715.48um. Native lifecycle clean, no surviving child processes.

Safe14125115411 SHA0d9b23019c89ab327ef3a296437a1bd61c180491954d09274c225814a69dc674. Native14124657803 SHA bf981a5887f0fd69167f41e1ce6b8065662202d1fe9f8b2de201df210eb408ec (217602539bytes) contains full new physical outputs/caches at hw/soc/out/cloud-cdr-wire-shortcuts-physical/...; cloud only. DeepLVSDB a660b051307cf53822a5d84be53c3d73bce70448d6fafbf8e5b4f3ad8b4abbca; flat ec58d3df5a7a815b1b992d1c4f8fe7f2e99dc3436b138a18e99ed76f1f0f0a16. Full receipt docs/evidence/cdr650-paired-native-physical-20261114.json. This is the CDR block's exact physical pass, NOT serialPHY completion, newRC/electrical acceptance or main-chip signoff.

**LIVE fresh topology extraction:** [43622884786](https://github.com/Melihakbulut221/nssoc/actions/runs/43622884786), sourcee0a87989915cb7d65a20176de33649859f013393, branchcodex/cdr650-paired-wire-graph. Authenticates new physical run/native archive and every selected layout/LVSDB/decklog input; executes original independent650-device/2046-terminal/25-port native identity comparisons and fault controls. Then runs original exact geometric metal/via graph extraction with only declared650 census adaptation. Requires every component wholly owned by one actual native net, no split metal networks, complete terminal coverage. No old geometry/RC reused. Safe paired650-wire-derived-RUN, native paired650-wire-native-RUN. This extracts fresh wire graph only; source pin/terminal anchors and actual R/C still follow. Original wire pipeline source f3aece4ae3b048df220cb51277d74fcd026940ed in scripts/cdr_mos650_wires.py requires hierarchy/annotations identity with old pin geometry, which must be adapted explicitly to relocated bands and flattened top-level vias, not simply bypassed. Use native xref identities for new device/terminal ownership; do not carry old native IDs or old coordinates blindly.

**LIVE full-chip new predecode placement/CTS:** [43622573415](https://github.com/Melihakbulut221/nssoc/actions/runs/43622573415), sourcea3a79275ea42940b3c319c7c15cab2ae75f15109, branchcodex/predecode-chip-placement. Exact60-file mappedbuild43618915765 restored through tested source-binding helper; netlist4b17ff9e9dac2452c60fc3a1e1860e775cdce2015589bb020b7530ab83314997 andmappedJSON532a165624564dcc0f1b1bd7904e697b244afcdadde7d289b2bd9fb07e01d59a. New script cloud_predecode_chip_placement.py uses existing20SRAM/four-clock floorplan and original constraint/CTS flow. This is explicitly NON-ADOPTED physical candidate work while boot43620739672 remains pending, not the old boot-proven handoff and not inherited acceptance. Requires separate successful newboot before adoption. Safe predecode-chip-placement-derived-RUN; native predecode-chip-placement-native-RUN. Latest poll has entered actual native floorplan/placement/CTS, runtime preparation and source restoration passed. Future need newroute/RCX/LVS, no oldODB reuse.

Original boot43620739672 and route43614100441/43610680141 remain their original handles. Manufacturing objective remains active/incomplete. No local native/source files.

## 2026-11-14 — paired650 full native physical qualification LIVE

Run [43622190993](https://github.com/Melihakbulut221/nssoc/actions/runs/43622190993), source `8274b540b6223e6a9bd2c7aa7b3d2c5046b09a7f`, branch `codex/cdr650-paired-native-physical`. Source-controls job132530121821 PASSED; native-physical132530193052 started. Follow this exact handle. No native physical verdict yet.

The experiment adapts the earlier physical factory from b3d9d1d284b1e8464d5359e7e21991aef21a787c without changing the frozen native checker SHA30c4586b86167ad775af14b5568152820a802037150bdfd282e7ba0843a1555f,560 DRC categories, deep+flat650-device LVS,13 fault controls, qualified launcher/supervisor/resource limits. All source closure hashes rebound. The original baseline_candidate() still authenticates the complete old650 generation archive and independently rebuilds the original reference; new candidate() additionally authenticates run43621748603/source0d90e18e09678eb1733123d97f41942dace720b3 and both native/proof artifact digests. source.gds must byte-match the independently restored650 baseline. Candidate hash285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514. Original650 schematic copied unchanged and hash-checked.

prepare_layout() now reads actual25 TopMetal2 pin boxes/labels from the serialized new GDS, checks all names and proof coordinates, regenerates LEF pins AND obstructions with original use/direction, and supplies moved coordinates to frozen checker metadata/fault generation. Original old LEF is not used as candidate coordinates. Candidate admission and final native record are bound to scripts/cdr650-paired-physical-input.json. No previous physical verdict transferred. Experiment workflow is NOT merged to timing/combined; only promote tested controller when appropriate.

Outputs: paired650-physical-derived-43622190993 contains safe derived reports; paired650-physical-native-43622190993 contains all native output/caches, cloud only. Earlier controls artifact includes schematic sources; do not download it locally. The new workflow uses artifacts rather than old release-reservation/publish steps; source/runtime controls, native verdicts, diagnostic preservation remain intact. It does not perform new RC or electrical transient verification; these follow only on exact physical pass.

Verified live at dispatch followup: boot43620739672 Icarus (approximately16min), route43614100441 exact jumpers (89min), route43610680141 buf4 (127min). Original handles unchanged. Supplemental Verilator incompatibility is already diagnosed and not waived. Full-chip timing, full serial PHY and manufacturing readiness remain open. All native work stays on hosted runners; no local source/CAD files.

## 2026-11-14 — actual paired CDR layout generated; native qualification is next

**New physical candidate:** run [43621748603](https://github.com/Melihakbulut221/nssoc/actions/runs/43621748603), source `0d90e18e09678eb1733123d97f41942dace720b3`, branch `codex/cdr650-paired-band-layout`. Generation and serialized geometry checks passed. Candidate GDS SHA256 `285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514`; source `c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c`. Preserves 16 primitive macro hierarchies and all later local overlays, including gate contacts; rebuilds 37 actual global TM1 trunks. Every old/new via incidence checked; no new same-metal contacts or overlapping distinct trunks permitted. Removing a real trunk or native contacts is rejected by serialized-geometry controls. Public pins move with bands. This is **NOT native LVS/DRC, fresh RC, electrical acceptance, full PHY or chip integration**.

Safe artifact14124466665 SHA726986be12be609ba674d4622b6011b30d3392a2ff70e6e69578a552984705ce. Native14124521775 SHA84bbb918af34605e7c6f14598fc68e7d5bb811a3d32d6c22bb294c0a51623ac6 contains candidate.gds/source.gds, cloud only. Generator promoted byte-identically as scripts/generate_cdr650_paired_bands.py (tested experiment path scripts/audit_cdr_native_cap_records.py); inputs metal.tgz releaseasset707281704/09c2185efebbdb7e60c0457d62c175d98d7bffca35e60bfe7c3f179f62ebbfb6 and geometry.tgz asset706980601/d8bd9f7463e7941e4f0319c5d01c47f217366cd213d83c68b9f6fdc6d256bc36. No experimental workflow merged. Receipt docs/evidence/cdr650-paired-layout-20261114.json. Total trunk length39385.2->39493.2um; targeted shortening is not a total capacitance/timing claim.

Preceding intersection audit43621581186/sourcefd516803e5e742ca87a4e6a51fd08ddeec1c61f7 safe14124267180/78ed5dc774b2a09bda0b65dbf8af673b5f09c510ecea5b018e043d457d64ed9b identified all37trunks with actual TopVia2 contacts and zero remaining band-crossing polygons. The prior four crossings were late shortcuts atx953..961.2um, outside overly conservative earlier953.6um filter but inside realmacro boundary993.6um. No crossings were sliced or waived.

**Next physical work:** validate this exact GDS against independent unchanged650 reference using frozen full560-category DRC/deep+flat LVS/13 fault controls, then new RC and unchanged electrical gates. Existing factory source `b3d9d1d284b1e8464d5359e7e21991aef21a787c`, scripts/cloud_cdr_wire_shortcuts_physical.py, derives exactchecker SHA30c4586b86167ad775af14b5568152820a802037150bdfd282e7ba0843a1555f via checker_text(). Original factory is branch/source/asset pinned and CANNOT simply run unchanged on newcandidate. Prepare new explicit source binding and regenerate LEF/metadata from actual25moved pin geometries; do not keep old pin coordinates. Source physical reference schematic SHA21d730545b983930eacf733ba77a7593df52e253987991724de9594fe136bbfb in original650 geometry lineage; verify actual archive bytes before use. Factory uses pinned AppImage d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466 and unchanged native checks. Do not transfer previous physical pass.

**Native cell diagnosis:** run43621515746/source9a80c7aad2f033f3b8b3a25527c08f7d334f1f21 completed diagnostic collection. Safe14123229761/64e69eb08a195f3782e573f84623554383e3ac239304257c29b2b7dac8e56f1f. Untouched IHP model passes Icarus; Verilator seed1 fails asynchronous reset reassertion at66ns, seed29 positive-edge capture at55ns; compiler reports unsupported specify constructs. Diagnostic success is NOT Verilator compatibility. Strict compatibility gate retained, no altered models or bypass. Actual chip Icarus boot43620739672 continues; native-cell diagnostic script and receipt retained. Existing routes43614100441/43610680141 also continue. Joint traffic43617762343 already passed and promoted in dcba4e028997c7ba7426bb071b3a2cc9998690d6. All native work stays cloud; manufacturing goal active/incomplete.

## 2026-11-14 — joint predecode traffic PASSED; native boot and routes remain live

Verified run43617762343/source df8c47d62027a3b5fd378f459ef8cb7208b9b712: inferred and vendor FIFO variants each PASS,2 tests/0failed/0skipped, actual SRAM instances0/16, asynchronous PCIe, source/runtime hashes unchanged. Actual Ibex + PCIe packets + GMII traffic and FIFO POR MBIST; NOT serial PHY, full mapped chip boot, layout or timing. Safe14122964087 SHA43e94a25337983a1b542e329a840a681afab3fcc33125f77e42af39570b2b868. Only tested checker define whitelist promoted; no experiment workflow. Complete reports docs/evidence/predecode-joint-traffic-20261114.json.

Boot43620739672 Icarus remains live. Supplemental Verilator FAILED native-cell compatibility before whole-chip compile (both seeds1/29 failed, untouched IHP library SHA28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4). Safe14123713097/ab629997a3df10119605ed18a08aefadd1fdd90f6e637314df10aac56f56f419. Do not waive compatibility or call this a chip functional failure/pass. Existing diagnostic collection omitted nested cell logs; next focused cloud probe must preserve these. Icarus continues unchanged. Routes43614100441/43610680141 remain live; no duplicates.

Band feasibility43620938275/source6f4e11caa345f0d4e064c68ae0f2dfb0d8b298e9 completed. Safe14123109182/1085d139c5ec3aa0f472059bb6820614085bad42bc96e6ebc54d978963c47346. After 33 conservatively identified TM1 trunks, four remaining TM1 crossings at x953..961.2um block a naive whole-band move. These are left of macro boundary993.6um, but geometry alone does not establish electrical ownership; inspect their actual via/metal intersections before rebuilding. Full receipt docs/evidence/cdr-current-band-feasibility-20261114.json. No new geometry or timing acceptance; full manufacturing goal remains incomplete.

## 2026-11-14 — fresh predecode main-chip synthesis PASSED; mapped boot live

Run43618915765/sourceb900da8cc1d57b8b2ce80416b6742c36239afd63 PASSED fresh firmware RTL preparation, strict native preparation tests, synthesis, and actual mapped-select audit. 114952cells,26 realclocked selection bits(10write_group+16write_low),20SRAMmacros(16Ethernet256x16 +4system2048x64). Candidate SHA4b17ff9e9dac2452c60fc3a1e1860e775cdce2015589bb020b7530ab83314997; mappedJSON532a165624564dcc0f1b1bd7904e697b244afcdadde7d289b2bd9fb07e01d59a; firmwareab7440619ca719358e6598b0cf291a268c8ccf13357b50ef3a89cbe583e71801. Safe14123429089/f11becfb6e2ab79646a58d29285409fc1dc1c6d30acf1501836e5a424dc3f695; native14123718652/c6848d124c65c6aae6af7ee70deb7b516d0a06e91886a0d4945ea12ce4645615 (build.tgz,60hash-bound files). Native stayscloud. Tested syn_soc_top.sh/sim_soc.sh opt-in define forwarding plus prepare_predecode_mainchip.sh and check_predecode_mainchip_mapping.py integrated byte-identically; experimentalworkflow excluded. Defaultoff behaviorunchanged. Receipt docs/evidence/predecode-mainchip-mapping-20261114.json.

LIVE gateboot43620739672/source98281a5792ac15ed28f5ecd001b0cff462e95f99, codex/predecode-chip-native-boot. Restores exact60sourcefiles/hash, samepinnedPDK and OSS2026-08-04. Two separate jobs: nativeIcarus4state and supplementalVerilator2randomseeds. Full20SRAM POR MBIST plus28firmwarechecks, asyncpacketidle profile,2Mcycles,19000s simulatorbound/355minhostedjob. Fourstate may hit known hostedlimit; don't waive gates or callVerilator a4state substitute. No remapping or bootprooftransfer. Safes predecode-chip-boot-iverilog-43620739672 and predecode-chip-boot-verilator-43620739672; inspect terminal verdicts and sourceunchanged before claimingboot. Fulljointtraffic43617762343 still pending separately. Oldroutes43614100441/43610680141 stilloriginaloldRTL.

CDR completegraph planning43620299436/dbed4fa2675efea02e15f17d732822e29a8e049b passed after first43620183298 failed ONLYrailidentitylookup (fixed to explicitdetail.public_port, not guessedlabels). Safe14123208037/2c40ce1637f98cd27103d6bae831299ab79ac4b0e91188053bfb4eec4f1ae782. Unconstrainedweightedplan REJECTED for adoption: shortensdata1050.52um butlengthensCdivider->buffer inputs1355.15um. NoGDSmodified.

Pairedplan43620553452/source0e2361ad89a4afd8593dd608387efde21a11624a PASSED40320exhaustive backendunitpermutations. Safe14122963884/7b6b52f81bf4b08aea51d4b5b6658a07df3afc52987af252432c7c6ae8a171e4. All1428anchorsassigned:1403to16currentmacros,25explicitpublicports; exact3supplycomponents. Fixesfirst6frontendtransforms, externalpins; preservesdivider/bufferpairs(6,7),(9,10), protectednets66/67/75/76 HPWLnotincreased. Candidateorder[3,0,1,2,4,5,8,6,7,12,11,9,10,13,14,15]. DataHPWL2044.62->994.10um and1804.62->754.10um; selectors+35.6um; otherupstream/outputnets stillincrease(up to799.89um). Weightedproxy118064.513->113320.583. NOTtiming/routeacceptance; fullnetdeltas retained docs/evidence/cdr-paired-placement-plan-20261114.json.

LIVE physicalband feasibility 43620938275 branchcodex/cdr-current-band-feasibility. Uses exactcurrent650GDS; subtracts immutablechildgeometry and classifies known-width TM1 rectanglesleftofmacros as candidateverticaltrunks; reports everyremainingband-crossingconductor before movinganything. This decideswhether old scripts/generate_cdr_retime_band_reorder.py strategy canpreservelateroverlays. Thatoldhelper is for484devices and mustNOTrun unchanged; it rebuildstrunksandmovespublicpins, unlike currentplanning'sfixedpins. Current650 includes150top-levelcontacts andmanylocalmetal/viaoverlays; allmustbeconserved. Sourcegenerationtrace nextusecomplete scripts git subtree, not truncatedrootrecursive/contents1000listing. FullgoalACTIVE; no native/localassets.

## 2026-11-14 — current650 macro boundaries recovered for actual floorplan repair

Macro audit43619786675/sourceae37a42977e99dc57ef648736b89f1893207c0c0 PASSED; safe14123722696 SHAa570289fa65af522ad286ce4e11f03a415f4ef076ee61c3944a70c0d1b8d202c. Exact GDS top has40directinstances:16functional macros plus24via stacks (not40functionalblocks). All first16 macros X=993.6um in a single long vertical stack. A data buffer ordinal7 Y2286.41um, Cdata ordinal10 Y3062.30um, selector0ordinal11 Y3336.93um, XOR0ordinal12 Y3611.56um, selector1ordinal13 Y3916.19um, XOR1ordinal14 Y4190.82um. Data macro406x194.63um, selector466x194.63um, XOR826x224.63um. Macros themselves untouched; source devices remain actual650. Top route shapes and24via stacks include later physical changes; merely changing instance transforms would break connections and is NOT an implementation. Native pin labels on direct children absent, so use actual terminal anchors/net ownership to rebuild interconnect, not guessed friendly labels. Receipt docs/evidence/cdr-current-macro-boundaries-20261114.json.

Current650 generation source from physical-candidate manifest: run41709759119/source087721d42112ed108543d2da053ee6d0e2f20a9c, release433163953, tagcloud-results-41709759119-1-cdr-mos650-gate-metallization. Verification41710162510/sourceb3d9d1d284b1e8464d5359e7e21991aef21a787c. This geometry has200MOS/124HBT/98rppd/7MIM/221tap, later gate-metal straps and source/drain via relocations. Old394/484 generators cannot replace it wholesale. Next actual design work: derive complete macro terminal/net graph from source anchors/L2N, compact data/select/XOR placement while accounting for upstream sampler paths, rebuild top routing, then exact unchanged circuit LVS/DRC/newRC/electrical gates. Currentmillimeterdistance evidence changes direction away from blind transistor sizing sweeps. No new PHY native job currently live after these completed audits.

Other original live handles unchanged at latest verifiedpoll:43618915765 firmware RTLboot/full20SRAMsynthesis,43617762343 actualjointtraffic/MBIST,43614100441 exactjumperDRT,43610680141buf4DRT. No localfiles or duplicatejobs. Productiongoalactive/incomplete.

## 2026-11-14 — actual CDR placement spans measured; compact macro audit live

Physical-span audit43619538391/source693c1d9c878ba3b9bce355c30e6e04c01f11169c PASSED. Safe14123666468 SHA6d822df59c2da0152245a473f9ec10af16701057682466a33b57d5ac5c54a0d9. Exact current650 GDS c3351820... read with pinnedKLayout0.30.4.post1: DBU0.001um, top2316.6x4715.48um. Data driver->six XOR base Manhattan LOWER BOUNDS adp1474.62–1804.62um/adn1594.62–2044.62um; commonverticalspan1322.77um. Selector driver->two bases605.95–725.95um. No physical change yet; not routed length or proven timing causality. Receipt docs/evidence/cdr-buffer-physical-spans-20261114.json. This justifies compact macro placement/rerouting investigation; adding parallel wires alone leaves oldcapacitance. Preserve upstream sampler/divider loading and all device/net identities, then fullnativeDRC/LVS and regeneratedRC/frozen electrical gates.

LIVE macro-boundary audit 43619786675/sourceae37a42977e99dc57ef648736b89f1893207c0c0 branchcodex/cdr-compact-macro-boundaries. Same exactnativeGDS/anchors; adds topinstance transforms/bboxes/pinlabels, no geometrychanges. Safe cdr-native-cap-records-43619786675. Follow originalhandle, do not rerun prior span audit. Source generator reconnaissance: main scripts/cdr_retimed_*_parent_plan.py describe OLD394/484device hierarchical sources; do NOT treat as current650. Currentphysicalrun41710162510/sourceb3d9d1d284b1e8464d5359e7e21991aef21a787c/codex/cdr-mos650-gate-metal-physical has exact650 reference and physicalchecker, scripts/cdr-wire-physical-candidate.json identifies its generator. To rebuild, use currentGDS hierarchy and that current650 generation provenance; oldprimitivegenerators alone would discardlaterchanges. RecursiveGit tree maytruncate (huge docs); use contents directory endpoints for focusedsource discovery.

Verified live now: newmainchipsource43618915765 (firmware RTL boot/full synthesis), joint43617762343 (traffic/POR MBIST), exactjumpers43614100441 andbuf4route43610680141. Nochanges/restarts to ongoingjobs. Fullproductiongoalactive; nothing native written locally.

## 2026-11-14 — native capacitor provenance confirmed; source build progressing

Native capacitor record audit43619048065/source5e5ae228678377ff602befb779077c6a52946ee4 PASSED. Safe14123805673 SHA75d60093cff9cf9f5e0f8dc64f34441eb31db8af1336eb9a36419b6e076622ac. Exact metalRC archive707281704/09c2185e... read only on runner. Original Magic pump_wires.res.ext contains T382_rppd_2.n0 cap131020.2109375aF and T383_rppd_2.n0 cap146790.359375aF, matching composed C8237/C8243; not newly introduced by nx1 trial. Original .ext identifies T382 resistor terminal, Q275 collector and six XOR bases on same conductor; T383 similarly Q273 plus six bases. Res.ext preserves distributed branches (e.g T382.n0->Q275_C27.453ohm; T382.n1->n053.3457ohm; T382.n0->T38240.4117ohm). This supports investigating actual routed topology/load, but is NOT qualified high-frequency PEX or proof the physical capacitance model is correct. Do not scale C or alter valid frozen checks. New receipt docs/evidence/cdr-native-cap-records-20261114.json retains bounded actual native records and four terminal anchors. Next trace full same-conductor geometry/driver-to-load distances and consider a compact physical buffer/XOR arrangement with fresh RC, unchanged LVS/DRC gates.

Fresh predecode main-chip build43618915765 has passed source/tool preparation and is running Fresh firmware RTL boot and complete chip synthesis with twenty SRAMs. Joint43617762343 still actual concurrent traffic/FIFO POR MBIST. Source modifications remain experiment-only until native checks pass. Existing exactjumper and buf4 DRTs still run at their original handles. Snapshot: {"43618915765": {"status": "in_progress", "conclusion": null, "head_sha": "b900da8cc1d57b8b2ce80416b6742c36239afd63"}, "43617762343": {"status": "in_progress", "conclusion": null, "head_sha": "df8c47d62027a3b5fd378f459ef8cb7208b9b712"}, "43614100441": {"status": "in_progress", "conclusion": null, "head_sha": "b83bc3a3f204bf9a2833c89fd632ae9308a58b56"}, "43610680141": {"status": "in_progress", "conclusion": null, "head_sha": "d42836ac2566de769473973bb15625e27f788f8d"}}. No duplicate runs or local native files. Full goal remains active/incomplete.

## 2026-11-14 — measured predecode write-path improvement; fresh main-chip synthesis live

Integration ff1e70cc1faf92b4c77837d71be814139b55104a records exact tested placement/path helpers and receipts. Placement43616617171/source df75847d635b3c53b895ea3b1c62c3f20d83f091 plus saved-ODB write-path readback43617173813/source8ca0209c777e4e84405b3b7be172b8c3b7755f9e: same constraints/placement-estimate RC, slow targeted write setup after electrical repair improves -0.883149ns -> +0.131997ns; targeted fast hold +0.269111 -> +0.182012ns. ALL-path slow setup remains -2.344590ns and fast hold -0.059318ns. Isolated block, no CTS/route/signoff. Never claim full-chip timing closure. Safe placement14121799888/0c05fde1f4ec73ff467ba17781565fe950d3163f826f246a697a2d7b6ef6c16c; native14122337899/d55d22b5617fb2d693985c1cf2dec9616dbbb1f50a0f555ee9d640844eca1611 cloud only; safe readback14122254324/ef8d0590ee9ea3a3b3ac6fcb7b3ae49ede5e56c13bed793b046be827a6c78611. See docs/evidence/replay-write-predecode-placement-20261114.json.

LIVE joint CPU/PCIe/GMII test43617762343/source df8c47d62027a3b5fd378f459ef8cb7208b9b712, branch codex/replay-write-predecode-joint: inferred then vendor16FIFO SRAMs, asynchronous PCIe, all C10 peripheral defines plus WRITE_PREDECODE. Require each two tests/no skip/errors and exact 0/16 actual SRAM instances. Pending; do not merge whitelist change before results. Safe replay-predecode-joint-43617762343; native input archive stays cloud.

LIVE fresh full-chip source build43618915765/source b900da8cc1d57b8b2ce80416b6742c36239afd63, branch codex/predecode-mainchip-source. Missing WRITE_PREDECODE forwarding in syn_soc_top.sh/sim_soc.sh patched ONLY on experiment branch; one addition to existing strict0/1 define loops, default unchanged. New prepare_predecode_mainchip.sh preserves existing MBIST boot preparation through firmware RTL boot and synthesis, deliberately stops before lengthy mapped boot; check_predecode_mainchip_mapping.py requires actual26 registered select bits(10group+16low),20SRAMs incl16Ethernet and exact RTL SHA374722073fc503a85970748d79daad12fd360fb1edeb58b76250ddf3b967eb35. C10 peripheral flags, execute/PMP stage, RF CHKDEFER/PREDECODE, MEM_RDREG2, prefixadder, full interface. This is a NEW netlist, not old boot/physical evidence. Next requires actual native gate boot/proofs then coherent placement/CTS/route/RCX/LVS. Original full4state MEM_RDREG2 MBIST boot may exceed hosted6h; do not omit MBIST or claim a2state substitute proves4state. Keep preparation native artifact predecode-mainchip-source-native-43618915765; safe mapping summary predecode-mainchip-mapping-43618915765. Do NOT merge experimental workflow replacement.

PHY correction, superseding earlier window question: direct passive-divider-only input binding43617454925/source a7d15d20d2606b605146daf69d54a9e3d3efdc22 proves BOTH s0/s1 XOR selectors derive from RETIMED D, not raw B. D retains expected previous-bit sign at .6/.75/.9UI. No basis to change frozen checker windows/expected bits. Safe14121769540/8bc073a79e1a3dc0e8c18345bb2c0573c19af682a55fe02ec19716282de8c06f. Clock/load audit43616487827/source9935e4a991472d2bdcfcd87eb84a7f7fa795760f traced32physical clock bases, expanded50 passive subcircuits:18476C/28984wireR. Incident explicitC adp0.566521pF/adn0.595331pF/s0p0.234530pF, includes coupling; NOT grounded effective load/qualified RFPEX. Dominant C8237=131.0202fF to wire_cref, C8243=146.7904fF to wire_cref, differential C238=107.741fF. See docs/evidence/cdr-buffer-loading-and-retimed-selector-20261114.json. Nx1 trial still REJECTED unchanged.

Read-only geometry provenance43618600239/source b49e1d61d2901e513026f8036c3ca0bb670f6c18 PASSED; safe14123580366/4f7cfe1084a89aadbf769ced05d75dceb40c0f524c8430d4c7a5e125452dc97f. Exact GDS is c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c (legacy filename nssoc_cdr_pd500_resistor_v59.gds, actual650 devices). Source metalRC producer41728568165/1b40bf2db3844d6281c467022b248a2871ced6df, asset707281704 SHA09c2185efebbdb7e60c0457d62c175d98d7bffca35e60bfe7c3f179f62ebbfb6. Native wires.spice637a79590e87a3e11866ec822afb6096c3dc7d626d23acd0235389af8bfd0e3c. LIVE native capacitor record audit 43619048065/source5e5ae228678377ff602befb779077c6a52946ee4 branch codex/cdr-native-cap-records; restores metal archive only on hosted runner, traces T382/T383/T397/T398 resistor terminals into Magic .ext/anchors. Safe cdr-native-cap-records-43619048065. Next determine actual geometry/model behind dominant caps, then physical layout/driver change and regeneratedRC. Parameter-only previous what-ifs did not regenerate layout; do not arbitrarily scale C.

Existing original route handles unchanged and live: exact-jumper DRT43614100441/sourceb83bc3a3f204bf9a2833c89fd632ae9308a58b56; buf4reroute43610680141/sourced42836ac2566de769473973bb15625e27f788f8d. No duplicate/restart. Both oldRTL, neither tests newpredecode. Follow final antenna/DRC then fresh3cornerSTA; older LVS cannot transfer. All native work/cloud artifacts remain on GitHub; local workspace untouched. Full production goal ACTIVE and incomplete.

## 2026-11-14 — tested predecode integrated; nx1 PHY rejected and diagnosed

Integration313e85443f23d48b85d24b2bf10f3afccaf32efb contains byte-identical tested predecode RTL, co-simulation script/bench, source/SAT guards, actual full-RTL proof helper (physical read/reset options), and mapping helper. SOC_PCIE_REPLAY_WRITE_PREDECODE is DEFAULT OFF. Experimental workflow NOT merged. No source/native files written locally.

Stronger test43614166666/source5634da5c513f0ef0ed76df2d68155e8f6d760132 PASSED:12x300000cycles with every actual byte enable AND every stored byte compared,6 actual compiled wrong-select faults detected,19 independent tests no skips/errors/failures. Safe14121404592 SHA25dc8ac9590fe4bd175fc7eae9021ca6232c51e691ebd28c717e1a24d4f340b6. Default fullRTL proof43613750120 and physical-option fullRTL proof43614451027 both passed2x22/4x38; physicalsafe14120689834 SHA848b82d0db03127c7c18d7337afa9462d6d64251533753ccf8c34bc4e68437f8. Mapping43615106119/source141207b93d0ba17d402a427a64ca0543db6d8a96 PASSED, safe14121384406 SHAee910e980e9760ddec1d19f5b56b79f0edabb87a35d11176c737a6b6b339ca12. Isolatedcellcounts5900->5898,flops1605->1622; this says NOTHING conclusive about routed delay/hold. Firstmapping43614858489 onlyreporterfailed on two zero-port $scopeinfo records; strict empty-connectivity metadata classification fixed, unknown hardware stillrejected. See docs/replay-write-predecode-20261114.md and receipts. Next: actual physical candidate with newdefine; current running native routes still OLD RTL and cannot measure this newcandidate. Do not blindly apply old route/LVS pass tochangednetlist.

PHY43603972722 now TERMINAL FAILURE: simexit0/7004.41s, X385wrong/717below100mV of765 unchanged versusnx2; Y1wrong/588below, samplerA65/C148/D96below, Bpass. Devicesfailed XD0292/XD0293. This nx1 variant is rejected; don't restart same sweep. Safe14121124635 SHAd497b09e264004bba0c90f78ddb26c5853206a3d4855445549518344691e53dc. Native14121577984 SHAd5e62c25486ba447781a5e4cdc12c00b303e890fb3cb51de1c8cdf77f32d1615 stayscloudonly. divider-whatif artifact containsNPZ, do NOTdownloadlocally.

Read-onlydiagnosis43615016719/source059c7cde174f8b8496909493294ab1156c66f9cd PASSED exactfrozengatereproduction. Safe14122285145 SHAd961cd8d420b0b7c091b1c44b380340f3db7521de3512b02c91a6d792023b557. XD0292/293 unchangednx6 failACTIVEminimumVCE .380924/.379038V vs .4V gate at5.833/5.830ns, NOTcurrentdensity orstartuppeak: alltimeabsVCE .741/.746V,VBE .831/.833V,current/emitter .335/.353mA withinlimits. A sampler sign correct at.75UI transitiongroups, downstreamA interface stilllate/wrong: 01 median+.0561V vs sampler-.2357V;10 median-.0148V vs sampler+.2168V. SmallerXORload didnotrepairthe upstreambuffer. Fullreceipt docs/evidence/cdr-xor1-rejected-20261114.json. Do not relaxfrozengates. Before anotherbias/widthsweep, investigate actual sampler/buffer settling and clock/observation-window alignment; clock generator flips again .5UI after rising, whereas XORchecks use .6/.75/.9UI afterrising. This is a contract-audit QUESTION, not a demonstrated checker bug or permission tochange thresholds/expectedbits. Actualphysicalclock/retiming topology mustresolve it.

Native routing continues at original handles: exactjumper-guides43614100441 (699jumpers/473guide nets, noGRTregeneration; thenfreshRCX/3cornerSTA) and buf4trial43610680141. Snapshot: {"43614100441": {"status": "in_progress", "conclusion": null, "head_sha": "b83bc3a3f204bf9a2833c89fd632ae9308a58b56"}, "43610680141": {"status": "in_progress", "conclusion": null, "head_sha": "d42836ac2566de769473973bb15625e27f788f8d"}}. NeithernewRTLcandidate norfullserialPHY is integrated into those old-RTL physicalruns. Full product goal remainsopen.

## 2026-11-14 — predecode functional qualification passed; exact-jumper DRT live

Full actual replay RTL equivalence PASSED run43613750120/source1d665b21afbe869f46d4befa832c6b76197e5610 using pinned OSS CAD Suite2026-08-04, configurations2x22 and4x38. Earlier43613576934 failed only old Ubuntu Yosys parser on existing sized-cast syntax. Safe14121491806 authenticated, both complete native proof logs/hash/verdicts checked. Simrun43613400964/sourcef95fe2d305c3a64f234376218ccaeaebebe1b284 PASSED:12 all-output co-simulation cases,3.6millioncycles,zero mismatches, plus19 independent cocotb tests across4suites,zero skips/errors/failures. Receipt docs/evidence/replay-write-predecode-functional-20261114.json. RTL remains experiment-only and default-off. This is NOT measured timing closure.

Stronger validation43614166666/source5634da5c513f0ef0ed76df2d68155e8f6d760132 (codex/replay-write-predecode) now additionally compares every actual memory write strobe and every stored byte, including malformed frames; restores baseline source SHAfff6a0d3abb6b3f3a468baef8312b357efb7b591d3733cd92f3dda3345c34c63 by reversing only opt-in changes; compiles actual wrong-low-select mutation and requires specific strobe mismatch in all6seeds. Same candidate RTL SHA374722073fc503a85970748d79daad12fd360fb1edeb58b76250ddf3b967eb35. Do not merge experiment workflow. Preserve source/helper/tests only after controls pass.

PreDRTscreen43612029407 PASSED,699reportedjumpers across iterations,473 changedguide nets outof158097,159934cells/354ports and allinstancegeometry/connectivity unchanged. Safe14120604011/native14120788686 pinned in docs/evidence/pre-drt-jumper-screen-20261114.json. Not finalantennaacceptance.

Continue exactguides via live43614100441/sourceb83bc3a3f204bf9a2833c89fd632ae9308a58b56, branchcodex/exact-jumper-guides-drt. Restore authenticated guides.tgz (SHA69172352eb82e92a998843405c2db5ade521c96654e85fd9ff1fe1785e93b510), renameoldroute tojumper-source, explicitlytake after-jumpers.odb and read_guides after-jumpers.guide in pinnednativeDRT; NO GRTpass. BindexactODB/guide/SDC/netlistSHAs in jumper-input-proof.json. Original16DRTiters/0postDRTrepairloops, no constraint/gate relaxation. DRTthenCheckAntennas and freshRCX/3cornerSTA withallzeroacceptance. Safe route-pre_drt_jumpers-43614100441/routed-sta-pre_drt_jumpers-43614100441; native routed-db-pre_drt_jumpers-43614100441 and pre-drt-jumpers-rcx-native-43614100441 cloudonly.

Other live original jobs: buf4reroute43610680141, PHY43603972722; no restart. Fullgoalstillopen.

## 2026-11-14 — registered replay write predecode candidate in cloud qualification

Existing source/checkpoint e259ba0bb7b255d238aba602fcb405fc10e4bae7 recovered after continuation. No native assets or source checkout written locally. Current diode baseline receipt/six worst paths were successfully committed; do not rerun it.

New candidate run [43613400964](https://github.com/Melihakbulut221/nssoc/actions/runs/43613400964), branch codex/replay-write-predecode, source f95fe2d305c3a64f234376218ccaeaebebe1b284. Only experiment branch changes RTL: default-off SOC_PCIE_REPLAY_WRITE_PREDECODE registers 16 low address choices and ceil(DEPTH*MAX_BYTES/16) qualified high groups. Each of the original five write_valid assignments has its corresponding group assignment immediately following under the define; no duplicated acceptance predicate, no extra pipeline cycle. Same write_data flop; memory update uses high[group] && low[offset]. Reset/link-clear group assignments mirror original write_valid clears. Default build retains original code. Do not assume timing benefit before synthesis/placement/route/RCX/STA.

Qualification includes six-size Boolean factorization SAT with six deliberate wrong-low-address counterexamples; those are NOT full sequential equivalence. It also runs the original six-seed 300000-cycle all-output replay co-simulation twice (predecode alone and with read-ahead/in-bank/reset copies), and four independent cocotb suites (replay/reliable/flow/buffered-flow), rejecting failed/skipped/missing tests. Safe artifact replay-write-predecode-43613400964. First SAT step succeeded; actual co-simulation currently running, all results pending.

Separate full actual-RTL sequential proof [43613576934](https://github.com/Melihakbulut221/nssoc/actions/runs/43613576934), branch codex/replay-write-predecode-formal, source 8a7190db46a6ae0a5e413f293cbc64ac7dd73980. Real default/candidate builds, flattened modules, memory_map, async2sync, equiv_make/simple/induct(seq4), equiv_status -assert, configurations DEPTH2/MAX22 and DEPTH4/MAX38. No blackboxed memory or manually recreated state machine. Each native proof bounded1200s to diagnose non-convergence; timeout is not acceptance. Safe artifact replay-write-predecode-equivalence-43613576934. Formal not yet proven. Preserve exact default source binding and inspect failures before promoting RTL; no experiment workflow merge.

Existing independent jobs unchanged: pre-DRT jumper screen43612029407, buf4 reroute43610680141, PHY43603972722 all still in progress at latest poll. Follow original handles; active job status alone does not prove internal progress. Full goal remains open, including coherent new-route LVS, actual all-corner timing/electrical/antenna closure and full serial PHY integration.

## 2026-11-14 — baseline RCX/STA completed; distributed write-enable bottleneck persists

Run43591198141 nowcompletedFAILURE due actualacceptanceviolations, NOTtoolcrash. NativeRCX+3cornerSTA5m53s successful. SafeSTA14120119428 SHA65a0b3c26fc315e23ee1396d3fda00d3748c1d14d824b8dba5723e0eee8f5b8e (29.4MB). Cloudslice43612497640/source8940e666340465899db4bf9ddd2d1fa5cf641aac PASSED; smallsafe14120707100 containsfullsummary and6completeworstpaths; preferthis overrepeatedlargearchivedownloads. Receipt docs/evidence/diode-legalized-routed-sta-20261114.json.

Slow:539setup,WNS-1.074318442ns,0hold; setupgroupsPCIe510/CPU26/async2/EthTX1. Typ0setup,8hold,WNS-0.033812398ns(PCIe). Fast0setup,115hold,WNS-0.110754686ns (PCIe111/CPU2/EthRX2). Capviolationsslow101/typ104/fast111; slew567/241/126; fanout1477allcorners. RouterDRC0,antenna377nets424pins. Original4nsPCIeclockunchanged; nominalRCnotqualifiedRCcorners.

Latestslowworst write_valid->$auto$ff.cc:337:slice$570168(retry.bytes[25][5]): sourceQ0.638662ns,place35302buf1 .376415, NAND3_1 $abc$720139$auto$blifparse.cc:397:parse_blif$810545 delay1.356738ns at.117590pF/1.594826nsslew, place31537buf1 delay.977058ns at.164274pF/.849530nsslew, NOR2 .295619, place28884buf2 .420569, mux .364190; arrival6.017402ns. No holdpads. Criticalbranchchangedfrompreviousplace31551. Currentbuf4reroute43610680141 testsolderbranchonly; letfinish but doNOTassume onebufferclosesdistributedwrite-enabletree.

PotentialnextRTLhypothesis afterreviewingpriorvariants: predecode capture_address into registered16-waylowselect and registeredqualifiedhigh-addressgroups (ceil(storebytes/16),10for152bytes). Samewrite-data register andsameone-cyclecapture->storewrite; eachbyteenablegroup_q[index/16]&low_q[index%16] ratherthan globalwrite_valid+binarydecodeafterflop. Needexactcapture-validpredicate matching bothoriginalwrite_valid<=1 branches, sameasyncreset/linkclear, and formalper-byte strobeequivalence plusexistingreplay/fullpacketregressions BEFOREanynativecandidate. This is NOTimplemented orvalidated; do notclaimlatency/functional/timingpass. Inspectcurrentrtl pcie/soc_pcie_replay_tx.v and docs/combined-timing.md priorwritepaths. Avoidblindlyaddinglatency.

Otherjobs: preDRTjumpers43612029407, buf4reroute43610680141, PHY43603972722 remainliveatlatestpoll. Nojobsrestarted. Fullgoalopen.

## 2026-11-14 — pre-DRT jumper screen live, not a final antenna result

Follow43612029407/source408d751279f3ec57f9ee3a2b6601fd059aaa7b99 oncodex/pre-drt-jumper-screen. Basedbaseline2bb475... withunchangeddiodelegalizedODB/SDC/config. RunsONLYGlobalRouting, then native repair_antennas sg13g2_antennanp -jumper_only -iterations3 withoriginalratio_margin/congestionpolicy BEFORE detailedrouting. Explicitgrt::have_routestrue/have_detailed_routesfalse guards. Nativecheck_placement, before/afterODB+guides, independentwholechipinstance/master/location/orientation/status/pin/net/topport equality and canonicalper-netguidegeometry comparison. Requires actualGRT-0302 InsertedN jumpers (N>0) and changedguidenets; no-effectcasefails ratherthan launchinglongDRT. Noaddeddiodesallowed. 2400sflow/65minjob; noRCX/STA/detailedroute inthisscreen.

OfficialexactOpenROADdcf36133 GlobalRouter.cpp repairAntennas only invokesjumperInsertion when !haveDetailedRoutes(nets_to_repair). LibreLane3.0.5 common/grt.tcl onlyglobal_route/write_guide (noantenna repair), so priorbaseline didnotapplythispreDRTstep. OldpostDRT-jumpercall wasno-op and isnotrepeated. This is a hypothesis to reduceactual377remainingnets, notguaranteedclosure.

Artifacts: route-pre_drt_jumpers-43612029407 safelogs/JSON/proofs; guides-db-pre_drt_jumpers-43612029407 nativecloudonly, innerguides.tgz includes exactstate andentireGRTstep withbefore/afterODB/guides. Ifpassescontinue DRTfromthese EXACTmodifiedguides (doNOTregenerateGRTandlosejumpers), thencheckrealantenna/DRC andfreshRC/STA. FullchipLVS remainsownnewgeometryrequirement. Noexperimentworkflowmerged.

Otherlive snapshot: {"43591198141": {"status": "in_progress", "conclusion": null}, "43610680141": {"status": "in_progress", "conclusion": null}, "43603972722": {"status": "in_progress", "conclusion": null}}. Baseline43591198141 nowRCX/STAafterDRC0but377antenna-netfailedroute; buf4trial43610680141 independentlyrouting; PHY43603972722 simulating.

## 2026-11-14 — baseline routed, antenna improved but FAILED; RCX/STA live

Run43591198141 routejob132436088101 COMPLETEDSUCCESS. Routing3h56m26s, finalrouterDRC0 atiteration5, wirelength11001517. Strict antenna result377violatingnets/424pins (route__antenna_violation__count303); previousroute565nets/656pins. Improvement is NOTzeroacceptance. StandardunsupportedLEF58warnings remain; routerDRC0notfoundryDRC. Parentworkflowoverallnotterminal: RCX/STAjob132497306850 started. Follow samehandlefor3cornerresults; do notrerunrouting.

Safe14119918415 SHAd5d20e5af32453218931ada6aec41e14d4551fe3d14d3907f831be01b1031114 containsroute.log,stateouts,routed-state.json,proofs. Native14119848983 SHA3c9346bd008313c5f50f85e6f4798935bb01c487131fa0d802502c37707e3e60, innerrouted.tgz stayscloudonly. Receipt docs/evidence/diode-legalized-route-20261114.json withexactviews/metrics. No full-chipGDS/LVS pass transferred tothisroute.

Next antennarepair must targetthis completedroute/currentGRTguides and exact377-netreport. EarlierpostDRTjumper-onlyrepair wasno-op: OpenROADjumpers belong beforeDRT. Inspectexistingantennaflowhelper beforetryingpreDRTjumper/diode strategy; avoidrepeatingfailedpostroutecall or silentlyaccepting remainingviolations. Existingbuf4trial43610680141 continuesindependently, PHY43603972722 stilllive. Fullscope remainsopen.

## 2026-11-14 — exact three-corner buffer Boolean equivalence PASSED

Run43611046213/source19ac096b9594e6854399ff2c2554e97b59224715 PASSED all3positiveSATproofs and3actualinversioncounterexamples. Models hash-match frozenimplementationpackage822dab... inputcontract: fast547c5fb3ef0eabe0362de7fb361ff736f6791987996b4b1af39b70deb569a72e; slowed1cff6e4d66d89d200e94c2213b8926a71c451218ca2df9b1157c98460e4b1d; typ968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4. RealYosysread_liberty/flatten/check/SAT, no-libblackboxes. Safe14119783596 SHA260c7f413529e9acc3eb84dedcaedae3eef2f788689b9d4cf555df00278395d9. Allsixloghashes/verdictsrechecked. Tested scripts/qualify_retry_buffer_liberty.py retainedbyteidentically, experimentworkflowexcluded. Receipt docs/evidence/retry-buffer-liberty-equivalence-20261114.json.

Together with nativeplacement/connectivityproof43610473965, selectedbuf1->buf4candidate preserves Boolean behavior and existingconnections. It is NOT a timingpass: livebuf4reroute43610680141 must regeneratewireRC and measureallcorners/hold/electrical/antenna. Originalbaseline43591198141 and PHY43603972722 stillinprogress atlatestpoll. Noadditionalcandidate launched; followcurrenthandles.

## 2026-11-14 — exact buffer Liberty SAT qualification live

Follow43611046213/source19ac096b9594e6854399ff2c2554e97b59224715 oncodex/retry-buffer-liberty-equivalence. scripts/qualify_retry_buffer_liberty.py verifies originalimplementationpackage822dab.../releaseasset663146895, readsinputcontractwithoutrestoringnativefileslocally, fetchespublicIHPc4b8...Gitblobs forstandardfast/slow/typLiberty and requires eachSHA256 equal everymatchingfrozenpackageinput. Typical additionally968b0cfd... . RuntimeAppImaged6a349.../ubuntu22samepinned.

ActualYosys read_liberty (NOT-libblackboxes), flattenedtwo-cellcombinationalmiter and SAT provebuf1==buf4 for eachcorner. Separate inverterreplacement must produceactualSATproof failure, not genericparsererror. 3positive+3negativecases. Safeartifactretry-buffer-equivalence-43611046213 containsresultJSONandnativeYosyslogs; models/miter/nativework remaincloudonly. This is functionequivalence, not timing/physicalapproval. If frozenpublichash differs inspect ratherthan acceptingunboundmodel. No helpersmergeduntilpassed.

Livejob snapshot: retrybuf4reroute43610680141/job132494855003 in Rebuildroutingfromverifiedretrydriversizing; baseline43591198141/job132436088101 in Rebuildroutingfromverifiedfourdiodelegalization; PHY43603972722/job132474510071 in frozengatesimulation. Nojobsrestarted. Existingbuf4placement/connectivitypassed aspreviouscheckpoint; fullgoalstillopen.

## 2026-11-14 — buf4 placement/connectivity PASSED; coherent reroute live

Qualification43610473965/sourced0c1713733ef76d7ad8d601eac41d2a5e656227f PASSED on unchanged savedcandidate from43609939062. Nativecheck_placementrepeatedsuccess; all159933nontargetinstances and ALLnetconnections/354ports identical. Onlyplace31551 masterbuf1->buf4, X2617440->2615520DBU,Y1704780unchanged,R180->MX selectedrowreflection; statusPLACEDandA/X/VDD/VSSnets unchanged. Originalverifier was too strict about selectedorientation; diagnostic43610218581 provedexactdelta beforeexplicitqualification. No othergeometryallowed. Safe14120510154 SHA7118d141ef31cca85c805e615c7768d5a183f89da8da78316acbf11fa8854a52; native14120090635/d67191c...; candidateODB972d9676... . Receipt docs/evidence/retry-driver-buf4-placement-20261114.json. PlacementONLY, no timing/routingacceptance.

Follow newreroute43610680141/sourced42836ac2566de769473973bb15625e27f788f8d, branchcodex/retry-buf4-reroute (based frozenbaseline2bb475...). Originalroute43591198141 and PHY43603972722 remainliveuntouched. Newprepare_antenna_resume binds exactcandidateODB+nativearchive and makes exactlyone reversiblebuf1->buf4declaration change forplace31551 in BOTHindependentnl/pnl; allotherreferencecharactersretained and before/afterhashesrecorded. GRTvalidatesbuf4reference and expectedODB/SDC; allsignalroutesrebuilt,powerspecialpreserved. Same19200sroutinglimit355minjob, then19800sRCX/threecornerSTA, zeroalltiming/electrical/antenna/DRCgatesunchanged. No RTL/clocks/constraints edits. Addedcloud-onlyRCXnativearchive for coherentfollowup aftermeasurement.

Artifacts: route-retry_buf4-43610680141 safe, routed-db-retry_buf4-43610680141 nativecloudonly; routed-sta-retry_buf4-43610680141 safe; retry-buf4-rcx-native-43610680141 nativecloudonly. Ifinputregex/sourceguardfails inspect ratherthan weakeningchecks. Once measured compare againstbaseline; upsize can worsenupload/hold and is notguaranteedimprovement. Need pinnedLibertypositive-buffer equivalence alongside physicalsourceproof beforefinalacceptance. Testedplacementhelpers remainonexperimentbranch; experimentalrouteworkflow notmerged. FullserialPHY/newlayoutLVS/finaltiming/production stillopen.

## 2026-11-14 — buf4 native placement passed; selected-instance delta diagnosis pending

Run43609939062/sourcef8b704e002e5ccff680059459fba0ec4cf21c429: standaloneOpenDBswap passed; detailedplacement passed and159933othercells fixed, selecteddriver displacement1.9um, check_placementpassed. Finalverifier rejected selectedplace31551 attribute mismatch (currently permits onlymaster/location change; orientation/status stillstrict). All-net connectivity and alltopports comparisons alreadypassed before thatassert. Do not assume whichfielddiffers untildiagnostic.

Native14120090635 SHAd67191c33b2015eb39b097946904044e564990b12fddcd0c6d88f643d9ada340, innerretry-buf4-native.tgz. SourceODB c9deaebb...; candidate native/buf4-legalized-unrouted.odb SHA972d9676e2f3af51fda24b2411048b60383e9dfffdb92cd8550a9caf9c53e0b9. Safe14120075645 SHA2ca7cb3965d7dc1562c2928908b63f0b559dd06462250a6ba95902a34f2b4930. Candidate NOTaccepted and NOtimingclaim.

Follow diagnostic43610218581/sourcec35979b8f0efd150ea6f0ff4ed551088f1478121, samebranchcodex/retry-driver-buf4-placement. Restores ONLYoriginal+candidateODB from pinnednativearchive in cloud; does not rerun/editplacement. Updatedverifier writes derived/native-delta.json before originalstrictassert. Inspect actualselectedchange; preserve allnonselectedgeometry, everypin/net/topport and placementstatus. If selectedorientationchanged, determine legitimate legalizedroworientation and explicitlydocument permittedselectedtransform rather than suppressing unexpecteddiffs. No nativefiles local.

Also checked officialLibreLane3.0.5 source: GlobalRouting.outputs=[ODB,DEF], so it does NOT update nl/pnl. Futurecandidate needs matchingbuf4in independentlogical/poweredreference. WriteViews can emit freshviews, or exactsingle-master replacement in originalnl/pnl with inversehash guard and nativeconnectivityproof; do not pair oldbuf1reference withbuf4layout. Primarysource librelane/steps/openroad.py classGlobalRouting and scripts/openroad/common/io.tcl write_views. Originalbaseline43591198141/PHY43603972722 remainlive at priorpoll.

## 2026-11-14 — native sizing callback fix; next integration must regenerate netlists

Retry43609730238 reachedOpenROAD but swapMaster on STA-attachedODB withoutLiberty crashed (signal11 sta::ConcreteCell::portCount/equivCellsArcs/dbStaCbk). Derived14119308393 proves nativefailure; no successfulplacement. The chosen geometry mutation has not yet been validated.

Follow43609939062/sourcef8b704e002e5ccff680059459fba0ec4cf21c429 oncodex/retry-driver-buf4-placement. New scripts/prepare_retry_driver_buf4.py creates independent odb.dbDatabase, validates exacttarget/net/pin schema and allinstance signatures, swaps onlymaster1->4 and writesbuf4-unplaced.odb. Then pinnedOpenROAD Tcl reads thatcandidate, locksother159933cells, legalizesselectedtarget, restoresstatuses, check_placement. FinalindependentPython compares allinstances/allnets/ports to originalsource. This avoids STAcallbacks for geometry-only step; it does NOT substitute for actual Liberty timing.

If successful, next route adaptation must preserve coherent nl/pnl/ODB: existing prepare_antenna_resume.py takes pre-sizing recoveredroute nl/pnl, which cannot silently accompany changedmasterODB. Generate fresh logical+poweredVerilog from resizedODB (or require nativeGRT returns matchingupdatedviews) and verify targetmaster/net connectivity before reusing full-reference generation. The known routeflow resets signals only and retains powerspecialwires; bind itsODBhash to actualnewartifact, regenerate routing+RC, preserve originalSDC1fab1c6a... andallcorners. Do not reuse oldtransistorreference or claim frozenRC timingacceptance. Baseline43591198141 and PHY43603972722 stilllive; unchanged.

## 2026-11-14 — retry driver screen infrastructure fix

Firstplacement43609541720 failed BEFORE nativeCAD: Ubuntu24 AppRun cannotwriteuid_map(Operationnotpermitted), returncode127. SourceODBhash verified unchanged; no placement/electrical outcome. Safe14119618668; native14119434428cloudonly. Do not interpret as designfailure.

Follow replacement43609730238/sourceb1bfdc7664b8b6ba02e5ca77c31bda68e9955948 oncodex/retry-driver-buf4-placement. Uses provenubuntu22AppImageenvironment; hostsha helper now explicit chunkedSHA256 forPython3.10 (samehash checks). ExactsameODB,buf1->buf4target,nativeTcl/independentconnectivityverifier,placementlimits and acceptance boundaries. Previousjobterminal; originalroute43591198141 and PHY43603972722 not restarted. Native outputs onlycloud.

## 2026-11-14 — exact overloaded replay driver placement experiment live

Follow43609541720/sourcea3487a2f42e87c3425db2573856838f7f77434af oncodex/retry-driver-buf4-placement. Targets ONLYplace31551 sg13g2_buf_1->sg13g2_buf_4 on verified159934-instance legalizedODB. Other159933instances LOCKED during detailed_placement, then exactoriginalstatusesrestored. max_displacement1000/1000, no legality waiver. Originaldriver/netnet31551, unique internal SIGNAL output, protection flags and pin-schema checked before swap. Native independent Python inventory compares ALL instance pinconnections, allnetmemberships, ports, nonselectedmaster/location/orientation/status and selectedorientation/status. Source/hash/runtime pinned. No simulationclock/SDC/RTL modifications.

Safe artifact retry-buf4-placement-derived-43609541720 containsresult/native-proofJSON. Native retry-buf4-placement-native-43609541720 stayscloudonly, innerretry-buf4-native.tgz. If pass, resultingout/native/buf4-legalized-unrouted.odb is NOT a routed or timing-accepted candidate; regenerate GRT/DRT and allcornerRC/STA before assessing benefit/hold regressions. Existingroute43591198141 remains untouched as independentbaseline. No testedhelpermerge until nativeexecutionpassed. If requestedmasterabsent/placementfails inspectactualreport, do not weaken invariants.

Source helpers: scripts/run_retry_driver_buf4_placement.py, scripts/retry_driver_buf4_placement.tcl, scripts/verify_retry_driver_buf4.py. Experimentalworkflow only. Parent evidence and rationale in immediatelypreceding checkpoint. Mainroute43591198141 and PHY43603972722 still IN_PROGRESS at dispatchsnapshot. Fullgoal notachieved.

## 2026-11-14 — concrete retry-store setup driver diagnosis

While live route43591198141 and PHY43603972722 continue, inspected actual prior routed STA safe artifact14111793410/run43579643337 (29,027,528-byte ZIP, derived reports only, RAM only). `nom_slow_1p08V_125C/max.head.rpt` worst path write_valid ($auto$ff.cc:337:slice$309577) to $auto$ff.cc:337:slice$569476 has slack-0.799543ns, arrival5.755142ns, required4.955600ns, original4ns PCIe clock.

Concrete data-path cells: sourceQ0.707018ns/0.095786pF; place35302 buf_1 delay0.407540; nand4_1 delay0.224774; place31551 buf_1 drives0.299358pF with1.540707ns slew and1.204865ns delay; next nor2_1 delay0.992989/slew0.747776; place29583 buf_8 delay0.361816; mux2_1 delay0.286367. NO dlygate hold pads on this path. Prior failure here is load/slew dominated, so do not blindly add RTL latency. Replay RTL already stages write_address/data/valid, and historical docs/combined-timing.md records prior write_valid sensitivity to placement.

Next actionable independent candidate: inspect same drivers in exact legalized sourceODB and evaluate targeted positive-buffer upsize/legalization (e.g. place31551) before another full physical run. Preserve all topology/clocks/constraints; measure allcorner hold as well as setup, and regenerate routes/RC after size/pin-geometry changes. Frozen-wire sizing is ONLY a hypothesis screen, never physical acceptance. Existing old helper scripts/cloud_route234_sizing_screen.py and prepare_route234_sizing_screen.py illustrate guarded native master replacement but bind a DIFFERENT old114025-instance design; do not run them unchanged. Current159934-instance legalizedODB is native14112212387/hashbe3f5242a66dbbc81708b43f83d707c58ccc07d944bc8fe8fc3c11a745013228, membernative/four-diode-legalized.odb hashc9deaebb26a07bf0909c249547156b1a1cb96401c8ccfa3748acff818131d959. Proven local legalization helper sourcef0c5230da39e88f6b8a30994015b7e09c911a8d3, scripts/diagnose_four_diode_legalization.py and .tcl. Inspect/adapt carefully; lock others and restore placement-status provenance. No sizing candidate launched yet.

Original route/PHY runs remain live; do not restart them. Latest documentation commit8d67402061277f4adac460b22ca96bbd682163ff adds current scoped LVS pass to README and marks CLAUDE_HANDOFF historical. Fullchip fault suite remains passed. Full serial integration/finaltiming/production unresolved.

## 2026-11-14 — full chip native fault suite PASSED

Suite43607561776/source0af445ae8447e48a7fbd1252f1693df19acc3bfb PASSED allfour controls in one identity-gated cloud job. Identity108Match+strictportstrue; signal_open107Match/1NoMatch; SRAMMOSwidth107Match/1NoMatch; port_name108Match but strictportsfalse. Alloriginal DB hashes unchanged. Safe14118697093 SHA3ae02f4c345b809785f8a03bef78e0fc299ea13a477855e216ec0a7d9edb6917. See docs/evidence/full-chip-native-fault-controls-20261114.json and docs/full-chip-native-fault-controls-20261114.md. Tested helper copied byte-identically to integration; experiment workflow NOT merged.

Signal fault disconnects NSCELL_0 SG13G2_NOR2_1.A fromNSNET_356. SRAM fault changes CELL<31>.N5 width0.30->0.45 in shared DPbitkit definition. Port fault changes CAN_RX_I netname only; topology stillmatches and portgate correctlyrejects. Stored SPICE case semantics restored per originalreader; no blackboxing/deviceexclusion/netequivalence/portwaiver.

Next: follow route43591198141 and PHY43603972722. Route success must feed its OWN coherent GDS, poweredVerilog/fulltransistorreference and LVS; do not transplant old GDS pass. Existing prepare_namespaced_chip_streamout.py and run_full_chip_transistor_lvs.py pin prior artifact/hashes and must be rebound explicitly after newroute artifacts exist. Native outputs stay cloud-only. Full serial PHY, finaltiming/qualifiedRC and manufacturing approval remain open.

Latest snapshot: {"43591198141": {"status": "in_progress", "conclusion": null, "head_sha": "2bb475a2d0a9c51cfa985a50d0239799deaddc45"}, "43603972722": {"status": "in_progress", "conclusion": null, "head_sha": "389d8b4f2e5782521d5bd779807dce3bb5029a10"}}

## 2026-11-14 — stored full-chip identity replay PASSED; full fault suite live

Identity43607296971/source1c3f8363705a03c0e9d254a44b47d85ef5f4bcc7 PASSED:108Match, native comparetrue, flag_missing_portstrue, original DB SHAunchanged,97.73s comparison. Restoring original SPICE reference.case_sensitive=False also makes original saved-xref port check pass (beforefalse/aftertrue), confirming serialization-semantics cause. Safe14119285571 SHAdb1e0fdcaaf6c86fae0ef605d0e5e4fbe4d7d60b0cf94f362dd233c38266de9c. Receipt docs/evidence/full-chip-stored-identity-20261114.json. No port waiver or source/netlist edits.

Follow complete fault suite43607561776/source0af445ae8447e48a7fbd1252f1693df19acc3bfb, branchcodex/full-chip-native-fault-controls. Single cloud job reruns identity FIRST, then signal_open, sram_mos_width, port_name sequentially. Each restores same original DB independently. Identity requires108Match and strict ports; signal/MOS require native comparefalse; port-name mutation requires comparetrue but strict portsfalse. Aggregate requires allfour exact cases and sameoriginalhash; no generic command failure counts. Safe artifact full-chip-native-fault-suite-43607561776 contains aggregate.json plus per-case result/port-inventory JSON. Native DB remainsrunneronly. Tested suite helper not yet merged; do not merge experimentalworkflow.

Once suite passes retain helper/evidence and move to new-route results. Route43591198141 and PHY43603972722 still live at snapshot. Full serial PHY/newroute allcorner timing/coherent newroute LVS/production approval remain open.

Snapshot: {"43591198141": {"status": "in_progress", "conclusion": null, "head_sha": "2bb475a2d0a9c51cfa985a50d0239799deaddc45"}, "43603972722": {"status": "in_progress", "conclusion": null, "head_sha": "389d8b4f2e5782521d5bd779807dce3bb5029a10"}, "43607561776": {"status": "in_progress", "conclusion": null, "head_sha": "0af445ae8447e48a7fbd1252f1693df19acc3bfb"}}

## 2026-11-14 — saved LVS replay loses SPICE case semantics; restoration under test

Diagnosis43606966719/sourceb90cfd743752d1cf92cfe74a296dc4a105e59970 completed: graph compare TRUE/108Match; port check FALSE even on original saved cross-reference before replay. Safe14119210172 port-inventory.json proves both deserialized netlists case_sensitive=True; 354pins each, only2exact-case matches (supplies) but all354match case-folded with no collisions. Layout ports lower-case, SPICE reference uppercase. This is not evidence of electrical mismatch in original accepted extraction.

Official KLayout v0.30.13 src/db/db/dbNetlistSpiceReader.cc line1325 explicitly netlist.set_case_sensitive(false) because SPICE is case-insensitive. New experiment restores reference.case_sensitive=False, retains layout sensitivity, unchanged port/net names, collision/count guards, strict flag_missing_ports, full device graphs and original DB SHA. No pin/net equivalences or missing-port waiver.

Follow identity-only43607296971/source1c3f8363705a03c0e9d254a44b47d85ef5f4bcc7 oncodex/full-chip-native-fault-controls. If identity passes run actual signal_open, sram_mos_width controls and add a port-name mutation to demonstrate port rejection remains effective. Aggregate acceptance must require identity pass and all negatives rejected. Experimental helpers not yet integrated. Native files stay cloud-only.

Route43591198141 and PHY43603972722 still IN_PROGRESS at latest API check. Goal remains active: full serial PHY, final coherent route/LVS/timing and production approval are not complete.

## 2026-11-14 — native graph identity matches; port replay still unresolved

Identity replay43606609559/sourcecceb261dfd98ace5aa3e741df1d3d83d4d05005a completed native compare TRUE with108Match in79.95s after clearing stale xref and explicit model correspondence. However flag_missing_ports returnedfalse: control remains FAILED, no negative-controls acceptance. Safe artifact14118413876 containsresult.json. Original DB hashunchanged.

Follow port-inventory diagnosis43606966719/sourceb90cfd743752d1cf92cfe74a296dc4a105e59970 oncodex/full-chip-native-fault-controls. It records original flag_missing_ports before recompilation, both netlists is_case_sensitive, and top pin/net names; then repeats same identity. Use derived port-inventory.json to diagnose serialization/case or actual port correspondence. Do not weaken port gate or claim full controls passed. Original native extraction engineering LVS acceptance is separate and unchanged. Routing43591198141 and PHY43603972722 were still active at latest check. All CAD/native work remains cloud-only.

## 2026-11-14 — full-chip fault-control replay diagnosis; identity retry live

Original engineering chip LVS pass remains scoped to its exact old GDS/reference. Additional full-chip stored-graph fault controls are NOT accepted yet: first replay43605811862 failed identity and reported duplicate circuit pairs; its negative-width rejection is not independent detection evidence. Signal-open selector also used Pin.name as a field; corrected callable accessors.

Structure inventory43606135790/source69394957314082bcecab05fc1d9e13afe214dc3e PASSED, safe artifact14118323405. Both tops158681subcircuits,0directdevices; layout model names lower-case and reference upper-case. Official KLayout0.30.13 source confirms LayoutVsSchematic.compare appends to existing cross-reference, and xref.clear is exposed. New helper clears only old comparison results and explicitly maps each reference model to its unique same-name case-insensitive layout class after exact Python class/parameter schema checks. No model exclusions, net/pin equivalences, or threshold changes.

Follow identity-only run43606609559/sourcecceb261dfd98ace5aa3e741df1d3d83d4d05005a, branchcodex/full-chip-native-fault-controls. Do not accept negative controls until unchanged identity succeeds. Original DB/artifact hashes remain frozen; native stays cloud only. Experimental helper/workflow NOT merged into integration. After identity success run signal_open and sram_mos_width, require aggregate identity plus both genuine rejections, then retain tested helper and evidence without experiment workflow.

Route43591198141 remains IN_PROGRESS in rebuild-routing step; PHY43603972722 remains IN_PROGRESS in frozen-gate simulation step. Preserve live handles, do not restart. Full PHY, new routed-chip LVS/timing and production approval remain open.

## 2026-11-14 — full chip engineering transistor LVS PASSED

Original run43602758557 completed native compare &&flag_missing_ports TRUE:108Match,zero extraction diagnostics,354topports,7456816recursive primitives on both sides. Both SRAM interiors included (DP70110/SP1211120). Original strict auditor rejected only our changed success wording ("INFO : Netlists match." instead of "INFO : Congratulations! Netlists match."). No electrical mismatch was reported.

Reaudit43605359900/source1999119e9a22d6e771be3583f09debf8be3106b8 PASSED after exact alternate-success recognition.40positive/negative verdict controls passed, preserving mismatch/warning/must-connect/empty/missing-verdict rejection. Native DB and original log hashes unchanged; no extraction rerun or log editing. Safe14117612941 SHA99a62ccc4f2d4ae190fc25883e9a81ae06fd2a3ccc93a7395614075c52bd4a34. Native14117582646 SHAfd250afa9a2c55ef266149c583d76256dd8dcdd9d5f043cfd892a7043e15979b,innerfull-chip-lvs-native.tgz: native/full-chip.lvsdb SHA3ddd851b8f0d80050bc97aabb6576836eb1d20ef41d0184c239f7840b479ca22. Native stayscloudonly.

Accepted scope is exact old packet-interface chip GDS c6c7df7f... with engineering SRAM CDL and independent reference523438b6... . This does NOT accept the live new diode-legalized route, serial PHY, padframe, final timing or foundry approval. No manufacturing claim. Fullchip LVS helpers and auditor fix retained in integration; experiment workflows not merged. See docs/evidence/full-chip-engineering-lvs-passed-20261114.json and docs/full-chip-engineering-lvs-20261114.md.

Next: follow route43591198141 (fresh route+RCX+allcornerSTA) and PHY43603972722. When new route finishes repeat coherent GDS/fullreference/LVS on its own logical+physical inputs; do not transfer this pass across route hashes. Also consider fullchip native connectivity fault controls using completed DB without re-extraction, retaining proven macro controls and strict no-blackbox boundary.

Live job snapshot: {"43603972722": {"status": "in_progress", "conclusion": null}, "43591198141": {"status": "in_progress", "conclusion": null}}

## 2026-11-14 — isolated XOR loading candidate launched

Run43603972722/job132474510071 (source389d8b4f2e5782521d5bd779807dce3bb5029a10, branchcodex/cdr-isolated-xor-load1) dispatched and restoring frozen native input. Variantbd10_lowz8_xor1_cdata3_sel15. Compared to completed43596398222, ONLY24XOR_DATA HBT nx2->1. Same C-pairnx3,selectbias1.5mA, all bench sources/solver, original extracted wires/RC unchanged. This is a nominal externally clocked circuit hypothesis, NOT new layout/RC or full PHY.

Exact reversible24-record source delta plus3negative controls run before simulation. C-pair and selectbias intermediate guards retained using constructed xor1 baselines; receipts explicitly label these baselines unsimulated. Actual candidate current-density binding includes24nx1 HBTs+2Cnx3 HBTs; original3mA/emitter and all data/device/phase thresholds unchanged. No integration helper merge until executed/validated.

Follow the same run to completion (17000s simulator timeout,330minjob). Safe result artifact cdr-xor-load1-result-only-bd10_lowz8_xor1_cdata3_sel15-43603972722 includes result,isolated-xor-load-change,candidate-current-density-binding and intermediate proofJSON. Native xor-load1-native-* stayscloudonly. Mixeddivider-whatif-* containswaveformNPZ: do notdownload locally. Priorphysicaldiag43603543533 has frozen gates reproduced and supports testing reduced input loading; it does not predict acceptance.

Full chip LVS43602758557 and diode-legalized routing43591198141 still live; preserve handles. Goal remains production-ready fullscope, not achieved.

Job snapshot: {"43603972722": {"status": "in_progress", "conclusion": null}, "43602758557": {"status": "in_progress", "conclusion": null}, "43591198141": {"status": "in_progress", "conclusion": null}}

## 2026-11-14 — PHY post-bias physical diagnosis passed

Diagnosis43603543533/source09ff87119d427d932731ccb8a78b706c358ebccd PASSED, actual gates exactly reproduced. Safe14116909437 SHA035d187ec392926c4d111594b96b2e5d7c84b0072b621ca8ae2702fbac25163b. Original43603401088 failed only absent import dependencies; exact proven cdr_mos650_full650_loaded.py and cdr_n1_divider_whatif.py were restored from d22e49cab14ddc4ed70a46492c9ea83d0509ac55 on experiment branch, without gate changes.

At0.75UI X transition groups01/10 have zero samples with both inputs>=100mV. Their A-buffer median output+59mV/-17mV is still wrong sign although A-sampler medians-236mV/+217mV are correct. A-buffer HBT273/275 median collector currents already switch (.602mA/1.977mA for01,1.973mA/.649mA for10) while collectors lag. X has zero wrong-sign relative to simultaneous XOR for strong-input samples but many below100mV; do not mistake this for full data success. Selector-current-only increase did not solve loading/settling.

Next justified candidate to consider: isolated XOR input HBT nx2->1 relative completed cdata3_sel15, all24 XOR_DATA devices only, no source/bias/load/solver/gate changes. This is a hypothesis from observed collector settling, not an accepted circuit. Check prior experiments before launch (known variant list includesxor2/xor3, notxor1). Current/emitter binding must reflectnx1, preserve3mA limit. Existing c_devices and selectbias isolation guards assume xor2 and must be updated with exact reversible24-record differences, not removed. Native waveform/RC stays cloud-only. Existing acbuf15/acbuf20 and collectorwidth12/16 variants already tried; do not blindly repeat.

Full chip LVS43602758557 and route43591198141 still live at latest poll; continue following actual handles. Full PHY/final timing/production unresolved.

## 2026-11-14 — isolated PHY select-bias trial rejected; physical diagnosis live

PHY43596398222 completed FAILURE of frozen data gates, simulatorRC0,4671.69s. Variantbd10_lowz8_xor2_cdata3_sel15: only ibs0/ibs1 bias1mA->1.5mA relativecdata3, model unchanged. Device/phase/VI gates pass but data fails. X385wrong-sign/717below100mV of765samples; Y0wrong-sign/580below100mV. SamplerA65,C148,D96 below100mV,Bpasses. No layout or PHY acceptance. Safe14116609449 SHA f02366f817e8128ef272a93accd09f6c1bc7968f538373969ffd2de8a32a3677. Native14116918270 SHA2f2dd3cffcadde6e7111065c3e5c79580ec245f5bffa14a54116cb66c6587868 (cloud only). Mixeddivider-whatif artifact containswaveform: do not download locally.

Follow diagnosisrun43603401088 (source85e8478623537af67a0642c7ed7cc109c37b86ac, codex/cdr-select-bias-physical-trace). Uses existing frozen-phase physical-path observer on completed native waveform, reproduces all original gates first, now also saves interface_truth_rows. It does not rerun/modify circuit or loosen gates. Inspect input-sign disagreements and strong-input XOR violations to select a justified next circuit change. Do not blindly increase bias or accept partial Y improvement. Full-chip LVS43602758557 and route43591198141 remain active at last poll.

## 2026-11-14 — every native reference pin connection verified

Run43603138368 PASSED (source b278e7a3281e2c6eb4031af5f51ab8aeb0d92a02). Actual frozen KLayout reader graph compared against independent powered-Verilog JSON and qualified CDL pin mapping: all158681native instances and816244pin connections match, zero mismatches. Wrong-signal-net and missing-pin controls rejected. Previous354top-pins/7456816primitive/DP70110/SP1211120counts also pass. No physical-layout LVS acceptance implied. Artifact14116878522 SHA cf4412a58b54b5693149db8f1519bc837796cb66e4e10d14924111f4c44248c1. Receipt docs/evidence/chip-native-reference-connectivity-20261114.json. Updated tested native reader helpers retained.

Next priority: follow live fullchip LVS43602758557, route43591198141 and PHY43596398222; do not restart live jobs. Inspect actual native/audit failures if they finish. Fullchip LVS extraction/comparison still active at latest poll. No new native archives downloaded locally; expected connectivity JSON generated and consumed only in cloud.

Job snapshot: {"43591198141": {"status": "in_progress", "conclusion": null}, "43596398222": {"status": "completed", "conclusion": "failure"}, "43602758557": {"status": "in_progress", "conclusion": null}}

## 2026-11-14 — full transistor chip LVS now live

Run43602758557/job132470857034, branche codex/chip-full-transistor-lvs, source e8f1b7d0782132fcb991182b4fde3c1aa147fa57. Frozen inputs restored and native comparer fault controls PASSED. Full chip extraction/comparison/strict audit step is IN_PROGRESS; do not restart due to observation timeout. Native timeout18000s/job355min. Check terminal result, then derived full-chip-transistor-lvs-derived-43602758557. Native DB/extracted circuit stay cloud only in full-chip-transistor-lvs-native-43602758557.

This uses exact assembled namespaced GDS c6c7df7f... (prior timing-failed route43579643337) and independent full transistor reference523438b6... . Both passing macro deck extraction prefixes are byte-identical; assembled comparison contains all six explicit hierarchy name pairs and nine flatten targets per SRAM namespace, with exact macro device/pin counts and full-side primitive conservation. No blackboxing, nil mapping, net equivalences, or missing-port waiver. max_branch_complexity2048 (same tested SP bound); strict flag_missing_ports and audit retained. Full-chip main primitive totals are measured, not forced equal ahead of native comparison, since physical-only cells require genuine comparison. Still no full serial PHY/final-route/production acceptance.

Reader/source collection run43602421955 PASSED, source67464a2464ffdb9cae864667a2070d073fce659d, derived artifact14116294182 SHAa5738706249770973fe0edb52578c5e04be8240c51c664b244a3f6c3a36eb8f5. Contains actual DP/SP deck source (safe text), native reader result. Main full LVS helpers remain experimental on run branch until execution validated; do not merge workflow.

Latest job snapshot: {"43591198141": {"status": "in_progress", "conclusion": null}, "43596398222": {"status": "in_progress", "conclusion": null}, "43602758557": {"status": "in_progress", "conclusion": null}}

## 2026-11-14 — native full reference reader passed

Run43602238038 (source017e930b9ffd9edd997a98b70e4a614dea3f3181) PASSED. Actual frozen KLayout0.30.13 and original passing DP macro reader read full independent reference: SOC_TOP 354pins,158681subcircuits,7456816recursive primitives, DP70110/SP1211120. No extraction/comparison was performed. Original full reference hash unchanged. Artifact14116517553 SHA71113a8ea0f126257e94d9c799e54ab621fdcaaab4064f9a5ff8d4186dd330b9. See docs/evidence/chip-native-reference-reader-20261114.json.

Next job 43602421955 source67464a2464ffdb9cae864667a2070d073fce659d on codex/chip-reference-native-reader repeats qualification while exposing ONLY source code of both proven macro decks (dp-lvs-deck-source.txt,sp-lvs-deck-source.txt) as derived artifacts. Native archives remain cloud-only. Read these sources to compose both SRAM transformations into full chip LVS without inherited macro-top-only assertions or losing any flattening/pair mapping. Current native reader helper intentionally exits BEFORE extraction; do not mistake it for full LVS. Full-chip extraction/comparison still needs launch. Route43591198141 and PHY43596398222 were still live at turn start.

## 2026-11-14 — independent full transistor reference emitted

Cloud run 43601779482 PASSED, source a8b0244721df1e6d994b30b094fcb3413b25d799. Full hierarchical CDL emitted from unchanged powered routed Verilog: 158681 instances, 354 top pins, 7456816 recursive primitive devices, 1140 qualified isolated clock-load outputs. All 158661 standard-cell supplies and 20 SRAM VDD/VDDARRAY/VSS supplies resolve exactly to VPWR/VGND. No internal constants or supply mismatch. Both SRAM primitive totals match prior native macro LVS (70110 DP,1211120 SP). Original eight empty corner/edge library definitions are preserved and listed; no logical instance is empty. Full source library records unchanged. Pin-order emission/readback passed, but native KLayout reference parse and physical chip LVS are NOT yet run.

Native artifact 14115684311 SHA256 894aa48ad4ee2c0f6e43724f1a88f20b278128e49d27b3584148759317c5c0b9 contains streamout-native.tgz. Reference path hw/soc/out/namespaced-streamout/pinmap-native/soc_top-full-transistor.cdl SHA256 523438b6014557b86ee7d438f95ddbfaabb76f390265283fcb844c233fcb8aa4. Full native data stays cloud-only. Derived artifact14116063825. Details in docs/evidence/chip-full-transistor-reference-20261114.json.

Next: native KLayout reader qualification, then full hierarchical LVS using exact assembled namespaced GDS artifact14116226453 (run43599532225), exact full reference above, and both verified macro deck transformations. Preserve primitive counts, top ports, strict unmatched-port rules, and no blackboxing. Consider reading/validating reference first to catch syntax/name/port treatment before heavy extraction. Full chip layout is still the prior failed-timing route, not final route; no full serial PHY acceptance. First reference runs43601292901/43601561542 failed only new Python parser assumptions (CDL slash delimiter and original empty corner definitions), corrected without modifying library bytes or circuit topology.

Current job snapshot: {"43591198141": {"status": "in_progress", "conclusion": null}, "43596398222": {"status": "in_progress", "conclusion": null}}

## 2026-11-14 — all 1140 open clock-load outputs qualified

Cloud run 43600938256 passed (source eb33eff08d22a924bec182547086dce9dafb187c). Frozen Liberty confirms all 1140 omitted scalar X/Y pins are outputs on exact clkload-number instances. Missing input/power, bus, width mismatch and unrelated-instance controls reject. Top ports have no constants or aliases. This is interface qualification, NOT full-chip LVS. See docs/evidence/chip-open-output-qualification-20261114.json.

Next: emit independent full transistor CDL from powered logical netlist with exact formal order, explicit isolated nodes only for qualified open outputs, and verified internal constant/supply mapping. Raw config VDD_PIN=VPWR/GND_PIN=VGND, VDD_NETS/GND_NETS null; do not guess supply nets from configuration. Inspect logical connectivity and map to declared top supply ports. Use complete standard-cell CDL plus namespaced SRAM CDL; no macro blackboxing. Native JSON and artifacts stay cloud-only. Main routing 43591198141 and PHY isolated-bias 43596398222 remain in progress at last check; do not restart. Integration streamout uses the previous failed timing route and is not final physical acceptance.

## Assembled SRAM geometry readback passed

Run **43600253157**, source `09ac3feea2471ed393055fdf55d84be9dca5b3f5`, verified all **311 SRAM library cells** in the actual assembled main-chip GDS. No missing or different cells; grid, shapes, labels and internal instance transforms/arrays match. The main-chip top contains exactly **16 DP and4 SP macro instances** as required. Safe artifact14116495410, SHA256 `28d31064048873cd2a8e3bb6676f1ff5938773b01642287ddf07a7e46819752c`.

This closes the namespaced SRAM geometry-transfer check for the prior CRC route, **not full-chip electrical LVS, DRC, timing or manufacturing acceptance**. The GDS direct-top instance count1,388,337 is structural and must not be equated to the powered-Verilog logical count158,681 without classifying helper/via/physical-only cells.

Next substantive task: qualify the1140 omitted clock-load outputs using authoritative cell directions, resolve top-port/constant/bus mapping, then build the independent full transistor schematic and compare it to this frozen GDS. Use the pinmap and streamout artifacts listed immediately below. Keep original gate failures visible and repeat final verification on the newer route once it completes.

Evidence: `docs/evidence/assembled-sram-geometry-passed-20261114.json`. Tested readback helper retained in integration.

## Main-chip GDS produced; independent powered-netlist interface inventory completed

### Verified streamout

Run **43599532225**, source `879fb01d6680375de93b18618705ebd38f58b97d`, completed successfully. The actual main-chip GDS with namespaced SRAM views is **138,694,064 bytes**, SHA256 `c6c7df7f7fe7d23c03847ffa49bb547423ff89b7dc9266a47effa495efea077d`. All LEF cells had corresponding GDS cells; original DEF/ODB/netlist/SDC hashes were unchanged. Safe artifact **14116226438**; native **14116226453**, SHA256 `bb1421b73653582fb56f11abedf90d66153e4d5919ef761a1d8a685b12d08d31`, contains `streamout-native.tgz`. Keep it in cloud.

This is an integration qualification using the prior completed CRC route43579643337, which failed antenna/timing gates. It is NOT final layout acceptance. The separate legalized-diode route43591198141 is still running.

Readback audit **43600253157**, source `09ac3feea2471ed393055fdf55d84be9dca5b3f5`, branch `codex/assembled-sram-geometry`, compares the actual assembled macro cells against all311 cells in the verified library, including shapes/labels/internal instance arrays/transforms and16DP+4SP multiplicities. Inspect the result before claiming lossless assembled geometry. Safe prefix `assembled-sram-geometry-derived-`.

### Independent full-CDL pin inventory

Run **43599635907**, source `c04f30d7696e1a3bb2550c5192ed65f125b351e1`, completed its diagnosis. It parsed the original **powered** logical netlist (`pnl`) into YosysJSON without synthesis/optimization, and checked **158,681 cell instances** against full standard-cell and namespaced SRAM CDL headers. **No unknown cell types** were found.

All reported interface issues are omitted X/Y output connections on clock-load examples: BUF_8=342,INV_2=259,INV_4=128,INV_1=330,INV_8=73,INV_16=7,BUF_4=1 (total1140). The report does NOT accept these automatically. Next verify directions using the pinned cell-library interface definitions, check every affected instance (not just first-five examples), and represent intentionally open outputs with unique isolated nodes only after that proof. Missing inputs/power/width errors must remain failures. Add meaningful negative controls for omitted input/power and wrong width.

Before emitting a full schematic, also verify top-port aliases/constants, source bus direction/index metadata, constant-net mapping and source pin ordering. Do not silently tie missing pins or use empty macro definitions. The old blackbox-only converter remains unsuitable. Native JSON is cloud-only in artifact **14115941190**, SHA256 `588c3deacaf4c5824500ba96da77cf85a486e0d122a770f62a94c6436e6a8fa3`; safe pinmap artifact **14115941182**. The streamout GDS contains physical-only cells as well; distinguish intentional physical cells from omissions when full transistor LVS is assembled.

Tested preparation, guarded streamout flow and diagnostic pinmap scripts are now retained in integration. Evidence: `docs/evidence/mainchip-namespaced-streamout-and-pinmap-20261114.json`. PHY43596398222 remains live; complete PHY, full-chip LVS, final timing and manufacturing approval remain open.

## Current checkpoint: fast exact restore verified; main-chip integration advancing

The previous turn made concrete progress. The archive bottleneck was measured and fixed; the coherent main-chip preparation now succeeds. Full-chip LVS and manufacturing approval remain **unproven**.

### Verified input restoration

Run **43598890723**, source `f1145703b7280773670ded41e46638fdaa906413`, verified all **5,030 files / 1,173,231,506 bytes** against the frozen contract, including disk readback hashes. Header scan took 3.33 s and sequential restore 5.89 s. The former lookup order caused 2,539 backward seeks in gzip. Manifest hash: `fe773024abb77b2c184be52ca26eb1028eba228e0a784cfdd78f4175e92f98d0`.

Only the two jobs still in input restoration, **43598072420 and43598415001**, were deliberately canceled after this proof; no routing or PHY calculation was canceled. Their replacements preserve all input hashes. The actual pinned AppImage replay then restored and verified all files in about11 s.

### Coherent main-chip inputs now prepared

Run **43599303587**, source `1d9748bf0bd6436e1bcaddd8a403f90cce6d71f3`, passed preparation. It binds **16 DP and4 SP SRAM instances** to the verified namespaced GDS files. Every other configuration field is unchanged. Archived logical views are `def,nl,odb,pnl,sdc`, and their hashes are in safe artifact **14115961267**. The prior `pdk_dir::` path failure was fixed by resolving the exact file through the pinned input contract; hash checks were retained.

This run stopped at the CLI because `--force-run-dir` requires an existing directory. The workflow now creates it. Current streamout run: **43599532225**, source `879fb01d6680375de93b18618705ebd38f58b97d`, branch `codex/namespaced-chip-streamout`. Inspect its actual terminal result before claiming GDS completion. Safe artifact prefix: `namespaced-chip-streamout-derived-`; native files stay cloud-only.

### Independent schematic interface inventory

Run **43599316243** successfully parsed the archived **powered Verilog netlist** with Yosys, without synthesis or optimization. Its first inventory stopped on a differing connection signature for `SG13G2_BUF_8` instance `clkload0`. This is not yet classified as an intended open output or a defect.

The observer now records every interface variant, its count/examples, and every missing/extra/width issue rather than stopping on the first difference. No unresolved pin is accepted or filled in. Current run: **43599635907**, source `c04f30d7696e1a3bb2550c5192ed65f125b351e1`, branch `codex/chip-full-cdl-pinmap`. Safe artifact prefix: `chip-full-cdl-pinmap-derived-`. Read `pinmap-inventory.json`; unknown cell types and ambiguous power/bus mappings must be resolved before emitting a full independent transistor schematic. The old `verilog_to_spice.py` remains blackbox-only and must not establish full LVS.

The streamout/pinmap work uses the **prior completed CRC route43579643337**, which failed timing/antenna acceptance, solely to qualify the integration process. Repeat on the final accepted candidate. Current legalized-diode route43591198141 and PHY select-bias simulation43596398222 remain separate running calculations.

Evidence: `docs/evidence/fast-restore-and-coherent-chip-preflight-20261114.json`. The tested sequential-restore helper is retained in integration; in-progress streamout/pinmap helpers remain on their experimental branches.

## Coherent main-chip streamout and independent full-CDL interface preparation live

NamespacedSRAM library itself passed bothmacroLVS+losslessmerge (below). Now streamoutqualification43598072420/source85d29262c1048e00e82621dba61af94a61090400,branchcodex/namespaced-chip-streamout. Usescompleted priorCRCjumperroute43579643337 native14111958544 SHA0c61942e79e1c94aceedd757e5d4cc298af6cbbe90480612c72bfed2fcbf18b0 (timing/antenna FAILED; qualificationonly). DoesNOTreplace/interfere withlive legalizeddiode43591198141. Restores exactPDK/design package663146895 SHA822dab7067d901fa79dabffffff784baf5c9965f0a5091eba67acdc48b9956f4 andnative library14114456981 SHA647008a959be8601aeb762f5ba238c7864ad0bcde0ef807f3e1dcae3324d8d25. ChangesONLY2MACROS.gds fields toproven dp.gds/sp.gds, verifiesoldmacrohashes, allotherconfigfieldsequal, retainsoriginalDEF/ODB/netlist/SDC views withhashes. Native KLayout.StreamOut insidepinnedLibreLane3.0.5AppImage. GuardchecksconfiguredmacroGDS hashes andalloriginalviewshashesbefore/after. Requiresactualoutput; skippedstepfails. Safe namespaced-chip-streamout-derived-*;nativenamespaced-chip-streamout-native-* stayscloud.

First43597457415/source89e0282141e7f471174810801bea2cb13655218c failedbeforedesignload:Ubuntu22Python3.10lackshashlib.file_digest. Fixedrestorecommand to usepinnedAppImagePython, notweakenhashchecks. Do notrepeathostPythonexecution. Currentrestore rehydratesallcontractinputs (notonlytools), then exactroutedarchive; monitor actualterminalresultsbeforeassuming success. Helpers scripts/prepare_namespaced_chip_streamout.py,hw/soc/pnr/namespaced_sram_streamout_flow.py areonexperimentbranch,notyetqualified/merged.

Independent pinmapinventory43598415001/source0d40c767d55ed8698afe0b16c1d31158043abccc,branchcodex/chip-full-cdl-pinmap uses sameexactfrozenrestoration. Yosysread_verilog+write_json ONLY, no synthesis/optimization; preferpnl else nl. ParsefullstandardcellCDL+namespacedSRAMCDLheaders, inventoryeverycelltypenamedportwidth/scalar/busbit/supplysuffix mapping,unknowncelltypes/missing/extraports visible. No empty macro definitions, no inferredmissingsupplies, noSPICEoutputorLVSpass yet. Explicit VDD!/VSS!/VDDARRAY! formalaliasesloggedonlyifnamednon!connectionexists. Nonzero-based/irregularbus interfaces flaggedforreview. Same-typeinstanceinterfacesmustagree. Safe chip-full-cdl-pinmap-derived-*; JSONnetlistandnativearchivescloudonly. Existinglegacyverilog_to_spice.py remainsblackbox-only andmustnotbeusedtojustifyfulltransistorLVS.

Next: inspect preflight/result/streamoutlogs andpinmapinventory; resolve genuineport/power/order issues beforewritingindependentfullschematic. StreamoutarchivecontainsnewGDS/config/state/library; sourcelogicalnetlistviewscanberecoveredfrompinnedpriorroutearchive. Repeat finalintegrationonnewcandidateoncecurrentroutecompletes. PHY43596398222selectbiasstillrunning; fullPHY/finaltiming/productionremainopen. Receipt docs/evidence/chip-streamout-pinmap-launch-20261114.json.

## Collision-free SRAM GDS/CDL library built from two strict native LVS passes

43596487748/source5a68106d6043c9ad3f8f644bb4eff6492b281b1e: DP26Match andSP25Match strictPASS,0extractiondiagnostics,originaltopportcontracts and recursiveprimitivecounts preserved. Namespaced GDS/CDL reversible proofs andGDSroundtripgeometry/instance checks passed. No new device/value/port/net waiver. Tested scripts namespace_sram_macro.py and replay_{dp,sp}_sram_namespaced.py retained in integration.

Bundle43596855175/source9b1da1411db02188f90c21dedcb51f36ca1db849 succeeded. 290uniqueCDLdefinitions,311uniqueGDS cells,allXcalls resolveuniquely within ownmacro library. Fullshape/instance/layout-grid equality before/aftermerge andGDSwrite/read,allreference-record equality. Tops unchanged RM_IHPSG13_2P_256x16_c2_bm_bist andRM_IHPSG13_1P_2048x64_c2_bm_bist. Safe14114083194 SHA79666c446a03f9c82b7a5357895439a71ee15f77642fd5352bbb8972c4e9df2a;native14114456981 SHA647008a959be8601aeb762f5ba238c7864ad0bcde0ef807f3e1dcae3324d8d25. Nativezip containsdp.gds,sp.gds,dp.cdl,sp.cdl,sram-namespaced.gds,sram-engineering.cdl,manifest.json. Keepcloudonly. MergedGDS SHAfb6925729c25f70eba48d6feb15daba92e586befe0bf12827e2cc2cc3f76b86a;mergedCDL SHA6a80a60991554f8f680249556192a24b4c3768bf843449927280c049b45eafd6.

NEXT integrate namespaced macroGDS paths into coherent mainchip streamout config, preserving originalmacroLEF/Liberty/timing/topinterfaces. Sourceconfig must be tied to exact routedcheckpoint; finalroute43591198141stillrunning. Main-chip independent schematic conversion must include FULL standard-cell andnamespaced SRAMCDL with explicit originalpinorders/power/busmapping. Existing hw/soc/pnr/lvs/verilog_to_spice.py is explicitly legacy macro-BLACKBOX and must NOT be reported as full transistor LVS. Need an independently sourced logicalnetlist, not GDS-extractedreference. Both full-chip LVS and finaltiming remainopen; individualmacropasses andlosslessbundle are necessarybutinsufficient.

PHY43596398222 isolatedselectbiasstillrunning; no newlayout/PHYacceptance. Nativebootpassed. Testedhelper build_namespaced_sram_library.py retained. Source-tree exploration: rootrecursiveGit tree isTRUNCATED; use subtreeSHAs for scripts,hw/soc/flow,pnr ratherthan assuming omitted filesabsent. Evidence docs/evidence/sram-namespaced-library-passed-20261114.json.

## SRAM namespace fix in native LVS; isolated PHY select-bias trial launched

Reference reachability43595961882 succeeded: both macro tops reach62CDLdefinitions,0unresolvedXinstances. ConflictingMET3RES is genuinely reachable:12DP and6SP direct definition references, widths.24/.26um. It cannot be discarded as unused.

Namespace candidate branchcodex/sram-namespaced-lvs uses NSDP_/NSSP_ prefixes for every internal GDS cell and CDL subcircuit, preserving actual macro top names/ports. Proves reversible complete CDL record substitution, rejects injected resistor-width change, and checks physical shapes/hierarchical instance transforms/arrays before rename and afterGDSwrite/read roundtrip. Every originalinputhash still checked before mutation. No values,nets,ports,models or acceptance thresholds changed. Both same macro strict LVS runs then compare renamed artifacts with original recursive counts and native port contracts.

Firstrun43596245592/source0fc26be6cd80b8a8a99a32a1ce1feee20d9ecaed: preservation proofs passed onboth, native compare stopped because Ruby %w flatten-cell lists retained old names. NOT LVS pass. Fixed exact %w[]/()/{} list mapping plus quoted operands and regression examples in5a68106d6043c9ad3f8f644bb4eff6492b281b1e. Retry43596487748 running, safe namespaced-{dp,sp}-derived-*; native namespaced-{dp,sp}-native-* cloudonly. Requireactualstrictpassboth before building common library/chip reference. Experimentalhelpers stay onbranchuntilnativeverification.

PHY43596398222/source2520c0d8ef6d0c3537d28e5a989048b39a8edfe6, branchcodex/cdr-select-bias-isolated. Singlevariantbd10_lowz8_xor2_cdata3_sel15. Relativemeasuredcdata3: ONLY ibs0,ibs1 references1mA->1.5mA; allphysicalmodelrecordsbyteidentical, allotherbenchlines(data,clock,load,solver)identical, fullfrozendevice/current/data/phasegates unchanged. Motivation verified B/D-to-select physicalpaths and weakselectswing; thisisacircuitwhat-if, NOTnewlayout/RC/completePHY. Safe cdr-select-bias-result-only-*; rawwave/nativecloudonly. Do notrestartwhilelive.

Legalizeddiodefullroute43591198141stillrunning; nativebootpassed; SP/DPengineeringmacroandfaultcontrols passed before namespace. Productionapproval/fullPHY/finaltiming/fullchipLVSremainopen. Receipt docs/evidence/sram-namespace-and-phy-select-launch-20261114.json.

## Shared SRAM geometry inspected; trace actual reference usage next

Geometry preflight43595848957/source13bfe72c6a5e26d81515d130a02dee3f59f08d05 completed. OriginalGDS hashes verified. Conflicting CDL RSC_IHPSG13_MET3RES hasDP width.24um vsSP.26um,length.6um; this named cell is absent from both originalGDS hierarchies. Many unused CDL library cells also absent; corrected observer after43595752035 failed on unusedAND2X4. Do not treat absent unused library definitions as extraction failure or infer electrical corruption from direct shape hash differences. Thirty shared present cell names have differing raw shape hashes (including labels/instance text); this is NOT an equivalence verdict.

Reachability preflight run43595961882,source196ce7b01d5858dd36dabeaa29d8b69b77bd36e0,branchcodex/sram-reference-library-preflight: resolve original CDL X references from each actual macro top; report whether conflictingMET3RES is reachable, reference counts and any unresolvedXinstances. Inspect before building merged chip library. If reachable, preserve both definitions with deterministic macro-specific namespaces and prove unchanged contents/connections; never silently first/last-definition-wins. If unreachable, prove it before excluding unused definitions. No full-chip LVS has passed yet.

SP andDP engineering comparisons andfullmacro fault controls passed; bootpassed; PHY connectivity mapped but electrical marginsfail; legalized-diode route43591198141stillin_progress. Evidence docs/evidence/sram-library-geometry-and-reachability-launch-20261114.json. All nativefilescloudonly.

## Full-chip integration preflight found a shared SRAM reference name conflict

43595567300/source088ee293f07db0611dbd4c6dac103bd4f63c8f11 completed. Exact passed DP/SP engineering CDL libraries each145subcircuits,42sharednames:41identicalcanonicaldefinitions,1different RSC_IHPSG13_MET3RES. Do NOT concatenate/include both with a first/last-definition-wins merge. Individual macro LVS pass does not prove a merged library is equivalent.

Physical shared-cell investigation run43595752035/source202afdd19f4ec20be6c6d02dcfe8e79b59b7fafa, branchcodex/sram-library-geometry-preflight. Restores both pinned passing native archives only on cloud, verifies originalGDS hashes, inventories direct GDS geometry of42sharedcellnames and exact differing reference records. Safe sram-library-geometry-preflight-*. Direct shape hashes include labels and are not electrical equivalence proof; inspect shape/type/parameter differences before choosing deterministic namespace separation and explicit LVS mappings. Full-chip LVS remains pending.

All SP/DP fullmacro sensitivity controls passed; bootpassed; route43591198141stilllive; fullPHY and finaltiming stillopen. Receipt docs/evidence/sram-library-conflict-preflight-20261114.json. Native files remain cloud-only.

## SP full-macro fault controls all passed; A/B physical paths established

43595161911/source da49561e5f322166feb371f7b5e6ee14d96da9fa completed SUCCESS all4controls. Identity25Match strictPASS. WidthR0.2u->.3u,layerR0metal2->metal3,andfirstMOSgateNT->NSSOC_INJECTED_OPEN_GATE each completed native compare and strictFAIL(24Match1NoMatch),as required. Not infrastructure rejection. Both SP and DP engineering macro comparisons now pass with full-macro fault sensitivity controls; original vendor references and full-chip/production qualification still not passed.

PHY43595197025 sourced22e49cab14ddc4ed70a46492c9ea83d0509ac55 completed. Including physical rppd links established A-sampler toadp/adn andB-sampler tos0p/s0n reachability,29and52traceddevices respectively. No unresolved traversal frontier. This is connectivity evidence only, includes feedback/bias, not proof of forward gain or timing. Fixed-phase native waveforms and gates reproduced unchanged; data/XOR margins still fail. Do not repeat HBT-only/NMOS-only observer attempts. Next candidate requires localized RC/settling evidence and unchanged full electrical/data gates, then actual new layout/parasitics.

Full-chip reference collision preflight run43595567300,source088ee293f07db0611dbd4c6dac103bd4f63c8f11,branchcodex/sram-reference-library-preflight. Checks shared SP/DP subcircuit names/definitions in exact passed reference artifacts before building a common chip reference. Safe sram-reference-library-preflight-* only. No circuit/geometry mutation, no full-chip acceptance. Legalized-diode route43591198141 remains running.

Receipt docs/evidence/sp-full-controls-and-phy-paths-20261114.json. Native evidence remains only in cloud. Do not merge experiment workflows.

## SP full engineering macro LVS passed; full macro fault controls running

Run43594788773 sourcef2caf1977cdea6d514b51e2f7aa99c57839d388e: strict audit PASS within comparison scope,25Match,0other,0extraction diagnostics,nativeRC0,auditRC0,124.616s. Both sides preserve1211120primitives and355nativeports before/after normalization. Evidence-backed INVX2/NAND2X2/CINVX4 flattening on both sides;2048 bounded search, original acceptance rules unchanged. Geometry unchanged. This is engineering reference with5resistor corrections, NOT original vendor reference/full chip/foundry approval.

Full SP identity and width/layer/open-gate controls run43595161911, sourceda49561e5f322166feb371f7b5e6ee14d96da9fa, branchcodex/sp-full-macro-controls. Each uses exact native original inputs before one explicit reference mutation,355pins/1211120primitives and strict audit. Do not accept infrastructure failure as fault rejection. Inspect all4actual control results before claiming sensitivity verified. Helpers and native inputs pinned; live runs must not be restarted.

PHY HBT+NMOS trace43594964200 completed but still reaches only final HBTS;98physical rppd devices were not traversed. Added labeled resistor reachability (without changing RC or measured waveforms) in source d22e49cab14ddc4ed70a46492c9ea83d0509ac55, run43595197025. Supply rails stop traversal. Inspect upstream routes before circuit changes. Frozen gates remain failed; no PHY acceptance.

Legalized-diode full route43591198141 still live, native boot43588310054 complete/pass. DPengineering macro and negative controls pass (below). Next full-chip integration LVS must use a consistent routed design and explicit engineering-reference qualification. Receipt docs/evidence/sp-engineering-macro-pass-controls-launch-20261114.json; all native files cloud-only.

## SP normalization trial launched; PHY observer fixed, upstream trace incomplete

SP inventory43594622132 verified exact direct-device and child differences: top layout has1824 additional NMOS and1824 additional PMOS; reference has768 additional INVX2,512 NAND2X2,32 CINVX4 instances, accounting exactly for the difference. Matrix both sides2048 NMOS+64columns,770pins; search messages require640/1024 above previous512 limit. No electrical equivalence inferred from inventory alone.

Next SP run43594788773, sourcef2caf1977cdea6d514b51e2f7aa99c57839d388e, branchcodex/sp-normalized-bound2048: flatten those3 evidenced cell types on BOTH sides, preserve1211120recursive primitives and355native ports, search2048 with original maxdepth and1800s native timeout. Native fault controls also changed to2048. Strict audit required; green diagnosis execution is not acceptance. Safe artifact sp-sram-hierarchy-bound2048-normalized-derived-*. Do not restart while live.

PHY observer43594550414/source4274eeb93e2a17c519cd189f0e754e01ce17437b succeeded after logical/native alias fix. Original gates reproduced. Paths reach terminal HBTs xd0275/xd0273 foradp/adn andxd0282/xd0281 fors0p/s0n; no sampler port reached in current four-level HBT-only trace. Therefore upstream buffer connectivity is still NOT established; extend traversal to actual device types/port mapping before sizing changes. Output/data margins remain failed, no full PHY acceptance. Tested observer source retained in integration; dependency scripts remain on experiment branch.

Boot43588310054 completed/pass (details below). Legalized-diode route43591198141 remains live. Receipt docs/evidence/sp-inventory-and-phy-observer-20261114.json contains both derived reports. Native CAD/waveforms stay cloud-only.

## 2026-11-14: native MBIST/boot complete; SP mismatch narrowed; PHY observer repaired

Boot run43588310054 completed with native_returncode=0, completed_boot=true, passed=true, sources_unchanged=true. Both system/Ethernet MBIST and packet-async PCIe idle boot profiles passed. Source1c0d103c64f040543106b2a3e9265fe580f4d289; original simulation3fd0fded2d874efa0109d8558a213380de1f36a7. No checkpoint continuation needed. This is not SDF timing, serial PCIe traffic or manufacturing acceptance.

SP run43593832917 completed diagnosis in77s; strict LVS FAILED:26Match and2NoMatch (matrix512x128 and top).1211120 primitive devices conserved on both sides;355 native ports. Do not mistake green diagnostic workflow for LVS pass. Read-only SP matrix/top native inventory run43594622132 source9024017cf28506bb0fd546495a47abf8d595ddb9 is running; its safe artifact is sp-matrix-top-derived-43594622132. Compare hierarchy/direct devices before any additional flattening. Native archive14113282480 SHA2c7f88ea31c2e515c84b4664a1f2d99bf5cf06da2c753077a16154c065430ddb remains cloud only.

PHY observer43593968180 failed at assert selected: connectivity tracing omitted logical-to-native binding aliases. Fixed in4274eeb93e2a17c519cd189f0e754e01ce17437b, retry43594550414 running. Inspect actual result before accepting the fix; frozen waveforms, device gates and sampling phases unchanged. No new circuit/layout acceptance.

Legalized-diode full route43591198141 remains in_progress. Do not restart. Fresh DRC/antenna and three-corner timing must still pass. DP engineering macro pass and fault controls remain recorded below; original vendor/full-chip/manufacturing approval remains open.

Receipt: docs/evidence/boot-complete-sp-mismatch-phy-retry-20261114.json. All CAD/native waveforms/checkpoints remain on GitHub; no local project artifacts created.

## SP full macro hierarchy replay and PHY physical buffer diagnosis live

SP43593832917/sourcec0f792bc59c418edaae2bb5f7dfd4bb082fd589b,branchcodex/sp-sram-hierarchy-bound512. Restores exactSPtimeoutnative14111284849 SHAdd437de8cfc8f81ffe504a5555608eebf3b6f3d401ce9cd4c49d87e362e4e58c. SPspecific32cell/column512/matrix512x128pairs,355nativeportnamesbeforealign,1211120primitiveconservation,ownprevioussixflattenboundaries,512boundedsearch+15controls. NO DP-onlyINVX2/NAND2X2/CINVX4extraflatten. Safe sp-sram-hierarchy-bound512-derived-*;nativecloudonly. Strictauditstillrequired,greenjobdiagnosisonly. Do notrestartwhilelive.

PHY43593968180/sourcec65ecf1b92d3c603caaad71d15b63e47ff99e852,branchcodex/cdr-xor-physical-path. Usesexactcdata3native14112762376,originalfrozenacceptancereproduced. Traceadp/adn/s0p/s0nviaactualnumericwiregraphandC/E-to-baseHBTpaths(upstreamsamplerportsreported). Collectsimultaneousphysicalterminalvoltages/currentsatfixed.6/.75/.9UIphases. No newcircuitvalues/simulationoracceptance. Safe cdr-xor-physical-path-derived-*;nativewaveformsstaycloud. Inspectactualconnectivitybeforeanotherbuffersizingchange.

Otherlive legalizeddiodefullroute43591198141,fullnativeboot43588310054. DPengineeringfullmacroand4fullcontrolsPASSED;originalvendor/SP/fullchip/foundryqualificationremainopen. Launchreceipt docs/evidence/sp-hierarchy-and-phy-path-launch-20261114.json.

## ENGINEERING DP macro identity and all three full-macro faults verified

43593348833/source411cb5d256664ff49086779b671cf347c3f60199 terminalsuccessALL4jobs. Nativeidentity26MatchstrictPASS;R0width.2u->.3u,R0metal2->metal3,MOSgateB_RWL->NSSOC_INJECTED_OPEN_GATEeachcompletednativecompareandstrictFAILwithNoMatch. Eachnegativehas3Skippedparents/1NoMatch/22Match;notinfrastructurefailure. Safeidentity14113615843 SHA423d0c9ee2a95b7b69b77806a436004e8e8c2dc08c56b8d6eed0a5001f58d87c; width14113655801 SHAc48a171cf08c068a8b5e9edfc90f2fb939bde1e30ed9868f34d4877c14392fac; layer14113416930 SHAee018c7011ebfe004347b59b6d9fe0a3c87f97d9670782b62702d22fea9ca68f; gate14113990021 SHA07601c536446e8181f2f4f0bd8c6f2c355f77d7764bb2212ff0418650e2f309f. FullrawnativearchiveIDs/hashesincase receipt. No localCADfiles.

Humanreport docs/sram-engineering-lvs-20261114.md; fullreceipt docs/evidence/dp-full-macro-controls-passed-20261114.json; tested mutationrunner scripts/replay_dp_sram_full_macro_controls.py retained (NSSOC_MUTATION identity/resistor_width/resistor_layer/mos_gate_open). ExperimentworkflowNOTintegrated.

NEXT SRAM: adapt proven nativepre-alignports+explicit32cell/column/matrixpairing+512boundedsearch to SP savedtimeoutinputs14111284849. Inventory43591995572 confirmsphysicalRM_IHPSG13_1P_BITKIT_16x2_SRAM/COLUMN_512/MATRIX_512x128 vsreferenceRM_IHPSG13_2048x64_c2_1P_BITKIT_16x2_SRAM/COLUMN_pcell_0/MATRIX_pcell_1; donotcopyDPperipheralthree-cellflattenwithoutSPevidence. SPtotal1211120primitives;referenceportcountfrominventory. KeepimmutableGDS/referencehashchecks. SPinputdeckbeforehash0bf61b1efb961298ed8cca8da9d214bdbc526310065ecabf2a72a9f66d6145e7, command25ff225b27e169e3b65557c38e640fec11dc3381fdfae2e3faea6ee1937bd8bb, engineeringCDL3ef741993177dccaf1be29e34561c2b6d13d4c20dc75b00d6ab72b0a4a972a7c. Originalvendor/fullchip/foundryqualificationstillopen.

NEXT PHY: frozeninterface43592773443 points to A/Bdata/selectbuffer settling/margins; verify actualphysicalconnectivity before new circuit values. Bothsizingvariantsfailed; no blanketauthorizationtoswapoutputpolarityorrelaxgates. Testedobserverretained.

LIVE: legalizeddiodefullroute43591198141; fullnativeboot43588310054. AllotheraboveDP/PHYdiagnosticrunscompleted. Continuefullgoal,notproductioncomplete.

## ENGINEERING DP FULL MACRO LVS PASSED; full-macro fault controls live

43593043558/sourcecb15ee8f57f1050e8c1b7c6fc2a9e986bf7afa3b terminalsuccess. Native12.999s,strictauditPASS withincomparison scope,26Match0other,0extractiondiagnostics,explicitdecksuccess. Native215ports/namecontract,70110primitiveconservationbothsidesand15nativecontrolsPASS. Onlysearchcapacity16->512changedafterobserved360requirement;acceptanceunchanged. Safe14113665237 SHA1a4bbe0da252e0df4bd7822df56589b8d3b7b14eb8690435fcb9bc24fac446bc;native14113411418 SHAbff8640c1efc79d3877f3ececa08d369d5c80bbc81556c13284e540566aa260e cloudonly. ThisisENGINEERINGcandidate(eightresistortokens changed earlier),NOToriginalvendorCDL/fullchip/foundryacceptance. Testedhelper scripts/replay_dp_sram_ports_bound512.py andscripts/check_lvs_ports_bound512.rb retained.

Full-macro controls currentrun43593348833/source411cb5d256664ff49086779b671cf347c3f60199,branchcodex/dp-sram-full-macro-controls. Fourcasesidentity,R0width.2u->.3u,R0metal2->metal3,firstbitcellMOSgateopen. Mutationsoccurafterimmutableoriginalinputhashchecks,proveonlyonefieldchange,allgatespreserved. Requireactualnativecomparisoncompletion;identitymustPASS,eachmutationmustNoMatch/strictauditFAIL. Infrastructureerrornotacceptednegativecontrol. Safe dp-sram-full-control-derived-CASE-*;nativecloudonly. Do notcallcontrolspasseduntilallfourverified.

Topdegreeobserver43593086693/source50e54f8b52e532eec9b1f56cbeb70db3cac09dc6 succeeded. Layout4648nets333empty/reference4395nets0empty;empty-netcountaloneisnotnet-equivalenceproof. No netswerepurged;successful512comparisondidnotrequiregraphdeletion.

PHYXORinterfaces43592773443/source4377f7749e83f687a03fa361191425b24f087f35 completedbothdiagnoses. Frozenoriginalgatesreproduced. BothvariantsXinputsdisagreeideal414/765;strong-input200sampleshave0wrongXpolaritybut135below100mV. Ystrong304,0wrongpolaritybut187below100mV. Namedinterfacehypothesesnotconnectivityproof;nexttraceA/Bbuffer-to-Xdata/selectphysicalpathsandsettling,no polarity/gatewaiver. Safe cdata14112694295 SHAbc52ce27071d570a6f6fd281085d129ca56d3c6c3b52473957fd9700ddd2f865; cslave14112414765 SHAa6769047b6737646822617c0b52f84380173b1f05b3f1275b88f449b91319947. Tested scripts/diagnose_cdr_xor_interfaces.py retained. Fullreceipt docs/evidence/dp-engineering-full-macro-pass-and-controls-20261114.json includesallfourreports.

Otherlive legalizeddiodefullroute43591198141,MBIST43588310054. PHYsim43584735530terminalFAILboth,SP43566292104terminaltimeout. Keepfullproductiongoalactive.

## DP native215ports and primitive conservation pass, stricttopstillfails; PHYbothsizingvariantsrejected

43592362942/source6fd9507ee7542aad7f6be29f2a0125bdd73bc9e2 terminalsuccessDIAGNOSIS,strictLVSFAIL. Native215ports/nameagreementpassed,before/after70110eachpassed,15controlsPASS. 25Match/1topNoMatch(threepreviouslymatchedstandardcelltypesnowflattenedbothsides,notlostprimitives). Native194.116s. Safe14113400577 SHAc6630e283d72401d4d1644b0772bb052f43176561d1dff08092d53074edcdcd0;native14112394415 SHAd9f0cd937bc43ab7550c22d672835d2092556f2f64aac10f0584d0ca945186bc;DB40bf9721db12569e03a51b411a211b8fb8c51fccad02f554578c127a0a8e346c. Newread-onlytopinventory43592863220/source76228b6fa935deafe61753c16cf87a9e6739166d,branchcodex/dp-normalized-top-inventory,safe dp-normalized-top-derived-*. Inspectremainingcount/searchlimitsbeforefurthercompare.

PHY43584735530 nowterminalFAILbothjobs. cdata3job132416701841:simRC0,device/phasePASS,dataFAIL;C148below100mV,min45.73mV(vscslave3C120,min56.63mV). X386wrongsign717below,Y1wrong581below;A65,D96belowunchanged. Safe14112882059 SHA8aab59e3437f6c4e6e4ec97448679d45a7b652af8f5a623bd5c63c9ec96f2610;native14112762376 SHA29605a3d0eda6de2a348d2619d5f009edb87594d9581883be105d03d1bd6449f cloudonly. Neitherintegrated.

NewPHYsaved-capturediagnostic43592773443/source4377f7749e83f687a03fa361191425b24f087f35,branchcodex/cdr-xor-interface-diagnosis. Bothnativecapturescloudonly,originalgatesreproducedthenfixed-phaseX/Ynameddata/selectinterfacevoltagesgroupedbyexpectedbits. No timingshift/newsimulationoracceptance. Safe cdr-xor-interfaces-derived-*. Strong-inputmaskdiagnosticonly,originalgatesunchanged. Combinedreceipt docs/evidence/dp-native-ports-preserved-and-cdr-sizing-rejected-20261114.json.

Otherlive: legalizeddiodefullroute43591198141,MBIST43588310054. Do notpollterminal43584735530/43592362942asrunning. Allnativeworkcloudonly.

## Native port timing of construction corrected; strict215 guard retained

43592200178/source90270dd18db42c1e2729eab9c8f7435db092ce66 terminalFAIL beforecomparison:primitive70110eachpreserved,butnativeTOP_LVL_PINSafteraligncreated273layoutpinsvs215reference. All215present,58extraarehierarchicallypromotedinternal$instance.signal labels. Guardcorrectlyrejected. Safe14112748023 SHAf1fe484adf71435cee249483707d1d4eff46a57efd50d9035d417778177687af;native14112852727 SHA32cad698b0ffd6f222eb91017a400c71987b13a6ebe9888794d9bbca56c76a5e cloudonly.

Currentrun43592362942/source6fd9507ee7542aad7f6be29f2a0125bdd73bc9e2,samebranchcodex/dp-sram-top-ports-normalized. Movebothnative make_top_level_pins calls BEFOREalign,unchangedalgorithm andenabledswitch. No manualpinremoval/selection,nonequivalentnetsaliased. Keepstrict215namecontract,3arraypairs,3additionalflattenedcells,70110conservationand15controls. Safe dp-sram-port-normalized-derived-*;checknativecompletion/strictauditbeforeclaim. Receipt docs/evidence/dp-sram-native-port-order-correction-20261114.json.

Otherlive legalizeddiodefullroute43591198141,PHYcdata3job132416701841,MBIST43588310054. Earlierrecordsbelow.

## DP missing native port construction and exact peripheral boundary imbalance diagnosed

Savedtopobserver43592070053/source2c9c9cf589dfb90792de8fa581fb02f0836ac645 succeedswithoutdetailedxreftraversal. Safe14112946292 SHAc3913d24e6a91b64022b33ca8eba7c3f3edbd34652e73ce77483b937ea0c6e95. Layout0pins/reference215;all215reference namesexistlayoutnamednets. Pinneddeckmake_top_level_pinsdisabledbyoriginaltop_lvl_pins=false. Threeboundaryimbalancesexactlyexplain1808directMOSdifference:referenceextra384INVX2,256NAND2X2,8CINVX4;layout904extraNMOS+904extraPMOS. No proofyetthattopmatches. Nativeobserverfirst43591834876failedreferencepropertyAPI;fixed43591936491/43592070053successful,noGCcrash.

Newrun43592200178/source90270dd18db42c1e2729eab9c8f7435db092ce66,branchcodex/dp-sram-top-ports-normalized. OriginalGDS/CDLunchanged. Nativeoptiontop_lvl_pins=true;allow_unmatched_ports=falseunchanged. Requireexact215portcount/nameagreement(nativecreatesallnamedports,no selectivecreation). FlattenINVX2,NAND2X2,CINVX4onbothsides;before/afterrecursive70110eachmandatory. Preserve3arraypairsand15controls;strictauditunchanged. Safe dp-sram-port-normalized-derived-* includes top-port-and-extra-flatten.json. Notaccepteduntilnativeverdict+auditpass;notvendor/manufacturingapproval.

SPtimeoutinventory43591995572/sourcecd6f627546800d52adf39f5f0a9e4ae3eb5d53ee succeeded. Safe14112383414 SHA1c400482b0983233974d8c711e7d380941c3275e45724d20809685d522c122f0. Lastdeckphasecomparison06:42:45; nofinalDB/extracted.cir. Physical16x2SRAM,column512,matrix512x128namesdifferreferencebutcountsstructurallycompatible. Do notblindrerun. Fullinventories/ports/logs docs/evidence/sram-native-ports-and-sp-phase-20261114.json;testedobserversretainedscripts.

Otherlive legalizeddiodefullroute43591198141,PHYcdata3in43584735530,MBIST43588310054.

## SRAM block, column and matrix now Match; top remains NoMatch

43591517998/source1acd3c5a4d647495111b274178c29f0440f49a68 terminalsuccessDIAGNOSIS, strictLVSFAIL. 28Match/1topNoMatch. Full448-device32cellblock,1792-devicecolumn,28928-devicematrix eachMatchwithallcontentscompared;top70110eachunchanged. 15nativecontrolspass. Native67.066s vs925.965s block-only; no looseningoflimitsoracceptance. Safe14113030357 SHA1e4a50e936c708c72ac10be5854b762084c12593dddc1e9809e4373c0b6e3bb7; native14113100183 SHA9bac7b5cb401e8b8fc28442197e3dba1cf3c2ce30cba523eae779d315c0c7848 cloudonly. Receipt docs/evidence/dp-sram-matrix-match-top-open-20261114.json.

Nextinspectremainingtopports/peripheralcounts/searchmessagesfromsavedDB; avoidpreviouscrashingfullxrefreader. Additionalcellnamepairs requireinputhierarchyevidenceandstrictcontentschecks; no waiver. Do notpoll43591517998aslive orrerununchanged. OriginalvendorCDLqualificationstillopen.

Live legalizeddiodefullrouting43591198141,PHYcdata3job132416701841 in43584735530(cslave3terminalFAIL),MBIST43588310054. SPtimeout43566292104terminal. Allnativeworkcloudonly.

## PHY cslave3 completed and rejected; cdata3 still live

43584735530/source842ab2012fae1904251fd1503024e5670de6ad8f job132416702005 terminalFAIL at frozen waveform/device acceptance gate. SimulatorRC0,devicesPASS,phasePASS,VIpass;data/waveformFAIL. Cbelow100mV120samples(min56.63mV),A65,D96;Xwrong386/below717,Ywrong1/below585. cslave3notintegrated;noPHYclosure. Safe14112233130 SHAce095c2ced48cd5b78a7f036e538f0737fae994ffa925c51ff89c76a0cb47d5e;native14112317745 SHAe75dfba4fbd10c671f23764bd580bb5225f2fd848357e0914fb316981c5a6ab2 cloudonly; mixed14112686651 includesNPZ,donotdownloadlocally. Receipt docs/evidence/cdr-cslave3-rejected-20261114.json. Same run'scdata3job132416701841 stilllive;waititsownresultbeforecandidatecomparison.

Otherlive: legalizeddiodefullrouting43591198141; DPmatrix/column43591517998; MBIST43588310054. Latest integration continues below.

## Remaining DP graph hits depth500; matrix/column correspondence trial live

Serialization-only43591354767/source8baf59cd680f086eb64e33db9a41f510b1f089e3 successful. Safe14112816221 SHA6a9a9182c84264cf102443c1007eb0e334825e7b357ef338f2a6c29cf16d411d. SavedblockpairedDB contains15231search-limitmessages:11520depth500exhaustions plus3711complexity16exhaustions(needsmax272). Thus topNoMatchnotproofallstructuralfaults. Blockitself448vs448devicesMatch. No acceptance.

Currenttrial43591517998/source1acd3c5a4d647495111b274178c29f0440f49a68,branchcodex/dp-sram-explicit-matrix-pairs. Keep32cellpair; add physicalCOLUMN_64->referenceCOLUMN_pcell_0 andphysicalMATRIX_64x32->referenceMATRIX_pcell_1. Verifiedoriginalinventorybothmatrices2048bitcells,16columns,2matrixinstances. Existenceguards,allprimitives/ports/dimensionscompared,15nativeidentity/faultcontrols,depth500/complexity16unchanged. No electricalequivalenceassumedfromnames. Safe dp-sram-matrix-paired-derived-*;nativecloudonly. Receipt docs/evidence/dp-sram-block-depth-and-matrix-launch-20261114.json.

Otherlive legalizeddiodefullroute43591198141,PHY43584735530,MBIST43588310054. SP43566292104 andDPblock43589897545 terminal;neverpollaslive. Earlierrecordsbelow.

## DP32-cell block matched; top unresolved. SP timed out, both terminal

43589897545/sourceea8eef24283b7af4bd4e627330b104fc395af579 completeddiagnosis925.96s,15nativecontrolspass. StrictauditFAIL:26Match(includesexplicit32-cellblock),1topNoMatch;70110recursiveprimitivesbothsides,0extractiondiagnostics. Safe14111923944 SHA1ad936dd8eb943439fa005211519128543cc1656e0fa82c9e15a1070b69c0199. Native14111429578 SHA95e9cf179b818929781a79cca4e5a089e2e04d51a724a0b01752ead2c057fc05; DB839fc525689e193b0dd1146188c274bb2dfcc58f470fe345a17e9044e0de14c5. Do notretryunchanged. Newserialization-onlydiagnostic43591354767/source8baf59cd680f086eb64e33db9a41f510b1f089e3,branchcodex/dp-sram-block-search-messages; safe dp-sram-block-search-messages-derived-*; noCADobjectloading/replay.

SP43566292104/sourcec226118b038f4180ce97452b9e469e873b37fd83 terminalFAIL:18000snativetimeout,novalidfinalLVSverdict. Safe14111334791 SHA74fa424a9b2b86c866bcd5c49ea833654177fbca545df1a08871105944028b65;native14111284849 SHAdd437de8cfc8f81ffe504a5555608eebf3b6f3d401ce9cd4c49d87e362e4e58c cloudonly. Nextinspectsavedphase/hierarchybeforeanyreplay; don'trestartblindly. Fullreceipt docs/evidence/sram-block-match-and-sp-timeout-20261114.json.

Otherlive: legalizeddiodeGRT/DRT43591198141,PHY43584735530,MBIST43588310054. Earlierrecordsbelow.

## Four failed diodes legalized; full routing continuation live

Run43590951082/sourcef0c5230da39e88f6b8a30994015b7e09c911a8d3 succeeded placement-only screen in29.27s. Fourdiodes ANTENNA_482/1342/457/458 movable;159930otherinstances fixed, allotherposition/orientation invariants passed,total159934unchanged. Originalplacementstatuses restored; native check_placement passed, no warnings/errors. No routing/antenna/timing claim. Safe14112471184 SHA3a29560701a518de1bd209909938697fb6f5989bfa5b4652fb125bd36e304122. Native14112212387 SHAbe3f5242a66dbbc81708b43f83d707c58ccc07d944bc8fe8fc3c11a745013228 cloudonly; verifiedfour-diode-legalized.odb SHAc9deaebb26a07bf0909c249547156b1a1cb96401c8ccfa3748acff818131d959. Testedhelpers now retained in scripts/diagnose_four_diode_legalization.py and.tcl.

Current route43591198141/source2bb475a2d0a9c51cfa985a50d0239799deaddc45,branchcodex/crc-legalized-diode-route. Restores exactverifiedplacement and originalSDC; clears only signaldbWires, retaining supply/specialwires, rebuilds GRT+DRT thenfreshCheckAntennas. DRTautomaticrepairloops0 for first fullrouteof alreadyinserteddiodes; strict finalantenna-zero and3cornertiming/electrical gates unchanged. Nativeinput/version/script hashes pinned. Safe route-crc_diode_legalized-* androuted-sta-crc_diode_legalized-*;nativecloudonly. Do not restartwhilelive. Receipt docs/evidence/crc-four-diode-legalized-route-launch-20261114.json.

Otherlive DPblock43589897545,SP43566292104,PHY43584735530,MBIST43588310054. PriorfailedCRCtimingandantennaevidencebelow remains valid for oldcandidateonly.

## CRC extracted STA rejected; captured diode failure now supports isolated legalization

43579643337 is terminalFAIL at strict acceptance. SafeSTA14111793410 SHA2b25292fffb06b73ac4d3f119c3a7c886edeefcaf7888c4c0ea0c58c4ad3f276. Slow569setup WNS-.799542677ns,1hold-.095417454; typ0setup9hold-.069170227; fast0setup122hold-.135881976. Slowviolations PCIe551,CPU15,async2,EthTX1. Fast holdPCIe115,CPU3,EthRX4. Cap96/103/108,slew550/227/119,fanout1363. Antenna565nets656pins stillopen despiteDRC0. NominalRC only, no production claim.

Diode capture43590389460/source9003dfcb3e85be38688357e0d9b823f46cd4d2f8 terminalFAIL as intentionally preserved. Runtime exactdcf36133... confirmed. DPLfails on ANTENNA_482/1342/457/458; native failed-stateODB and before/after statuses saved. Safe14112725149 SHA2769b547134d9c9b21793b3467bd198a9910031bf95fbaad5cd5cc212477cc7c; native14112241785 SHA5a745c683ff7e1adec765b3ef73ffb13ad21900f6e7567f5d7e9cdc663144176 cloudonly. No repeated originalroute needed.

Currentfour-diode trial43590951082/sourcef0c5230da39e88f6b8a30994015b7e09c911a8d3, branchcodex/crc-four-diode-legalization. Restore exactfailedDB, lock allothercells, only4diodes movable, detailed_placement-max_displacement1000x1000; allotherlocations/orientations mustunchanged, then restoreoriginalstatuses and requirecheck_placement. No subsequentroute yet; passingonlyplacementdoesnotcloseantenna/timing. Safe four-diode-derived-*;nativecloudonly. FullSTA+capture receipt docs/evidence/crc-routed-sta-and-four-diode-trial-20261114.json.

Live DPblock43589897545,SP43566292104,PHY43584735530,MBIST43588310054 remain separate. Do not pollterminalCRC43579643337 ordiode43590389460 as running.

## CRC jumper-only route finished but antenna repair failed; diode failure capture live

Run43579643337 route job132401417086 completed execution; fresh final check still565antenna nets/656pins, unchanged across5iterations. Routing DRC0 is not foundry DRC or antenna closure. Safe14111439322 SHA1e8a33fd24778a4212ad496f8a96a675d8cf28067e698d51ef4a5163997e2d85; native14111958544 SHA0c61942e79e1c94aceedd757e5d4cc298af6cbbe90480612c72bfed2fcbf18b0 cloudonly. DependentSTA job132432238364 is running; retain results for timing diagnosis but antenna gate already fails.

Source diagnosis: LibreLane3.0.5 pins OpenROADdcf36133...; GlobalRouter::repairAntennas calls jumperInsertion only if !haveDetailedRoutes, while jumper_only inhibits diode insertion. Explains ineffective post-DRT jumper-only loop; do not repeat. drt.tcl exact SHA matches runtime proof. Native version still to verify.

New diode diagnostic43590389460/source9003dfcb3e85be38688357e0d9b823f46cd4d2f8, branch codex/crc-diode-placement-diagnostic. Exact original checkpoint, no initial or subsequent detailed route. Capture repair_antennas -diode_only error, native DB and pre/post placement statuses; print runtime version. Intentionally non-accepting failure even on successful insertion; native archivecloudonly, safe route-crc_diode_diagnostic-*. Inspect actual failure before changing placement. Receipt docs/evidence/crc-jumper-ineffective-and-diode-diagnostic-20261114.json.

Still live: DP32cell43589897545,SP43566292104,PHY43584735530,MBIST43588310054. Earlier results below.

## Bitcell pairing rejected; parent 32-cell block test live

43589771694/source ef4dcd378344f01360ae663e53ca5ee2bdd2450e completed diagnosis in16.74s, native15/15 controls pass, strict LVSFAIL:25Match, bitcellNoMatch, topSkipped. Physical leaf6devices vs reference14; top recursive70110each unchanged. Explicit name mapping alone is insufficient. NativeDB14f60640f6a1a6fd60c75e265b2b360722ab294737a60fa45ab1fc0424d7b88b. Safe14111783729 SHA2cca92bd0da453cb30d8ae7639e03364e521ab0a4536f7a9dc837e8440ace385; native14112185339 stayscloud. No acceptance.

Current run43589897545/source ea8eef24283b7af4bd4e627330b104fc395af579, branch codex/dp-sram-explicit-block-pair, pairs only physical RM_IHPSG13_2P_BITKIT_16x2_SRAM to reference RM_IHPSG13_256x16_c2_2P_BITKIT_16x2_SRAM BEFORE align, to test parent boundary. Original GDS/CDL,strict checks,16 complexity bound and15 native controls unchanged. Not also pairing defective leaf. Safe dp-sram-block-paired-derived-*; nativecloudonly. See docs/evidence/dp-sram-bitcell-pair-rejected-20261114.json. Other live PHY43584735530,antenna43579643337,SP43566292104,MBIST43588310054.

## DP bitcell name mismatch verified; strict correspondence experiment live

Original GDS and engineered CDL hierarchy inventory43589227835 succeeded, safe14111637882 SHA320189ddd96027c6a03d6a848036f12410178b5f9cdd82ff4252b6d26769b3a4. Physical RM_IHPSG13_2P_BITKIT_CELL differs from reference RM_IHPSG13_256x16_c2_2P_BITKIT_CELL. Similar names alone do not prove equivalence. Pinned KLayout align flattens unmatched circuit names.

New run43589771694/source ef4dcd378344f01360ae663e53ca5ee2bdd2450e, branch codex/dp-sram-explicit-bitcell-pair, inserts exactly this one explicit cell pair BEFORE align with existence guards. Bounded16 and all original comparison controls retained; five extra native renamed-cell identity/width/open/missing/extra-device controls required. No nil mapping, blackboxes, net aliases, pin equivalence or waived checks. Safe dp-sram-bitcell-paired-derived-*; native archives cloud only. Do not integrate experiment workflow or claim LVS until strict audit succeeds. Full inventory/receipt in docs/evidence/dp-sram-prealign-hierarchy-20261114.json.

Other live runs unchanged: PHY43584735530; CRC antenna43579643337; SP LVS43566292104; MBIST continuation43588310054 from1.90Mcycles.

## SRAM search ambiguity confirmed independently; hierarchy inventory live

Run43588998602/source `ff22dfcd50ea2e51222dba28d98c08e16610138b` succeeded without loading CAD objects. Reads exact serialized DB SHA341e7da... only on cloud. Safe14111003774 SHA `abc6554fb3974ede597897234ff08275820dc7ef6102f3d3132a7ae068437a02`. 5752 exact embedded complexity-limit messages: most need32, some128/256, four need8192. Therefore bounded topNoMatch cannot alone distinguish structural defects from search exhaustion. Do not classify all mismatches as design errors.

Detailed native reader ALSO crashes in Ruby during DeepShapeStore destruction; not Python-only. Latest43588791834/source `dcee94349586376e569598b03de41f158d61bb56` staysFAIL, nativeRC6. Partial report preserved safe14111896618 SHA `52c360b1f7b6db6eb9ba63caded65ef3b85bfca3bfad2783e1b03eab04d2e7b2`; **not trustworthy acceptance evidence**, requires independent validation. Previous observer runs43587894664(API),43588102578/43588371410(Python GC),43588535934(Ruby) terminalfailure; do not poll/relaunch them. Report and failures in `docs/evidence/dp-sram-search-ambiguity-and-reader-failure-20261114.json`.

Live hierarchy inventory43589227835/source `e6682d1a15931a7c79a44423686f8a7f05eb1981`, branch `codex/dp-sram-prealign-hierarchy`. Reads original GDS cell names/instance counts and engineered CDL cell definitions in cloud; no LVS replay or correspondence assumption. Compare unmatched leaf names before considering explicit same_circuits; any mapping must retain full primitive and port checks, not blackbox/exclude cells.

Other live work: full native boot43588310054 from1.90Mcycles; PHY43584735530; CRC antenna43579643337; SP LVS43566292104. Earlier records below.

## Full native boot advanced to 1.90M cycles; next checkpoint continuation live

Parent43573697024/source `27c496c5649c284e5cc1494792ef103c7fd427c7` completed CHECKPOINT infrastructure successfully, **not boot acceptance**. Lastcycle1900000, UART450 bytes, flash6frames; firmware entered, tests1..5 print ok. completed_boot=false,passed=false, checkpoint_saved=true. Safe14110894168 SHA256 `93d10bd767f486fdc5718cec80d4de1cdd2c1fd453c805bda68e31874bdaf79d`. Native14111635745 SHA256 `4118593a84fc58be234b22d1fe177626dba8a2a6f973ff10e5effca36b9472a9`; tgzSHA `06e96554e91fd1b956b3c948419a02f7de81c8ba43f75df69e5d6014453d5875`, images-43573697024, logprefix16449bytes SHA `6fc8354e52debce6a7854615f17ef0cce200158d95a819638f58fa6535e85793`.

Live continuation [43588310054](https://github.com/Melihakbulut221/nssoc/actions/runs/43588310054), source `1c0d103c64f040543106b2a3e9265fe580f4d289`, branch `codex/full-native-boot-continuation-three`. Exact 1.90M checkpoint/runtime/parent/input guards retained, original3M bound and28 final checks unchanged. Do not replay older1.26Mcheckpoint. All native work stays cloud.

DP bounded mismatch diagnosis43587894664 failed on unavailable Net.id; corrected43588102578 hit native Python malloc abort (not an LVS result). Current instrumented diagnosis43588371410/source `4c3e36b2409301d094fd1ff57f2e776f22735405` reads saved DB only, with faulthandler/stage logging to locate binding abort; no new LVS extraction. Full bounded comparison result remains25Match/1topNoMatch. Other live PHY43584735530, antenna43579643337, SP43566292104.

## Bounded DP comparison completed in 87.68s: 25 Match, 1 top NoMatch

Run43587554414/source `d4a4f4f4468e56f354b87ce20748ca9945b2f1c9` completed DIAGNOSIS successfully, **LVS FAILED**. Native10/10 default/bounded identity and mutation controls passed. Exact70110 devices per side preserved; extraction diagnostics0. 25 child circuitsMatch, topNoMatch. Strict audit remainsFAIL. Safe14111580210 SHA256 `cc9d018c2ee7e6c3d4fff20edf534c8eaa2640a945f06c3eef1976cbcffcc9f0`. Native14111500413 SHA256 `31142082483dce4751f3abfe3af48cc1e76a48b4ce6f61ce9afbb6f29f5f3ced`; final DB SHA256 `341e7da0e6d9552c99f31d058d0250846321051badf48c099add4e60edebc2aa`. Native files stay cloud. Do not interpret green diagnostic job as LVS pass.

Live mismatch diagnosis43587894664/source `8d7ec27a32169f50002cc2fb253e5007c5ecf2cc`, branch `codex/dp-sram-bounded-mismatch`: read saved DB only in cloud, aggregate top net/device/subcircuit statuses and parameter differences. Safe `dp-sram-top-mismatch-derived-*`. No new extraction or graph edits. Other live jobs: PHY43584735530, antenna43579643337, SP43566292104, MBIST43573697024.

## DP bounded-comparison diagnostic launched

Run [43587554414](https://github.com/Melihakbulut221/nssoc/actions/runs/43587554414), source `d4a4f4f4468e56f354b87ce20748ca9945b2f1c9`, branch `codex/dp-sram-bounded-comparison`. Restores exact timeout archive only in cloud. Validates runtime/deck/reader/reference/input hashes. Only adds `max_branch_complexity(16)` in strict compare branch, leaving depth, device/port/dimension acceptance unchanged. Native default and bounded identity/fault controls run first. Bound exhaustion is failed_match in pinned KLayout source, not match. Native cap1800s for diagnosis; any unresolved graph remains failure. No full-chip/vendor/production claim. Safe `dp-sram-bounded-derived-*`; native artifacts cloud-only. Do not rerun old 43562021054.

Live alongside PHY sizing43584735530, CRC antenna43579643337, SP LVS43566292104, MBIST43573697024. Previous evidence below.

## DP engineering full-macro LVS timed out in comparison, not a mismatch verdict

Run 43562021054/source `70ebe8dca3b28d91a259f49bfee6b5b57c219f6e` is TERMINAL FAILURE. Native KLayout reached 18000-second timeout. Do not poll or blindly rerun it. Safe derived artifact 14110887368 SHA256 `f242d163ee68b57e2d873ec8b4104be8c9c30dc5ed2749102c964a318ece1195`. Native archive 14110867794 SHA256 `d0109ba41e2d146d25a90f7dcaeba2602b87168cbe9b0d01a175b57b1734658e` stays cloud-only.

Cloud log diagnosis 43587113786/source `1c2c0c3837f1c302a681a461ca1febed4ac80dc8` succeeded; safe artifact 14111100106 SHA256 `08511c7c8597c2a20a76df20a0b3048a90fade1858e6ead6334e0e746f1f48c5`. Last deck line: 05:48:26 UTC Starting SG13G2 LVS Comparison with flag_missing_ports, following derivation/extraction/alignment at 05:48:17..26. No final lvs.lvsdb/extracted.cir. Next inspect comparator matching behavior and strict negative controls; not geometry extraction or blind timeout extension. Existing six-cell flatten/count proof and engineered resistor candidate remain unqualified; no vendor/full-chip LVS pass. Full evidence in `docs/evidence/dp-sram-engineering-comparison-timeout-20261114.json`.

Still live: PHY sizing 43584735530 (two variants), CRC antenna 43579643337, SP LVS 43566292104, MBIST 43573697024. Earlier records below.

## C sampler phase diagnosis completed; two isolated circuit candidates live

New screen [43584735530](https://github.com/Melihakbulut221/nssoc/actions/runs/43584735530), source `842ab2012fae1904251fd1503024e5670de6ad8f`, branch `codex/cdr-c-slave-sizing`. Relative to `bd10_lowz8_xor2`, `cdata3` changes ONLY XD0255/XD0257 nx=4 to 3; `cslave3` additionally changes XD0253/XD0254. No bench, solver, acceptance, wiring-RC or layout changes. Candidate binding uses actual nx for current-density gates. Isolated-edit proof includes three negative controls. Do not integrate these circuit changes without results. Safe artifacts `cdr-c-sampler-result-only-*`; mixed NPZ and native artifacts stay cloud-only.

Phase diagnostic 43584493730 passed unchanged-gate reproduction. Verified artifact 14110140623 SHA256 `87e4c31c3a91c3df65895773196fde014965e0ec93ed9e25e80f0a2fde019298`; full report in `docs/evidence/cdr-c-sampler-phase-result-20261114.json`. For history 010, median C output at phase .5UI is 203.2mV, falling to 88.25mV at .875UI (all 32 bits below 100mV there). History 011 retains 147.97mV at .875UI. Early transition acquisition also fails. Simultaneous differential samples and physical clock-bank currents support acquisition/retention investigation; no closed-loop PHY claim. Frozen original gates are unmodified.

Other live work: CRC antenna 43579643337; SP LVS 43566292104; DP LVS 43562021054; MBIST 43573697024. Poll actual jobs, never restart on observation timeout. Prior records below.

## C sampler transistor diagnosis completed, PHY still rejected

Run 43584141378: both jobs passed diagnosis, reproduced original failing gates. Ten physically connected HBTs traced from C output, including feedback. Safe results and original full reports in `docs/evidence/cdr-c-sampler-path-result-20261114.json`. Load12/load16 both show history 010 minimum about 51.92mV and median about 93.3mV at frozen samples, below 100mV requirement; load change does not fix sampler. Script now retained; experiment workflow not merged. Next: analyze phase-resolved C master/slave acquisition and feedback currents before a circuit candidate; pooled node percentiles do not prove instantaneous differential gain. No new simulation/layout/PHY pass. Four previous long jobs remain separate; check their actual terminal results.

## C sampler original-bias path diagnosis launched

Run [43584141378](https://github.com/Melihakbulut221/nssoc/actions/runs/43584141378), source `413bd9793862cfd88281883d82ae8355f3ba811b`, branch `codex/cdr-c-sampler-original-bias-path`. Uses both rejected original-bias load12/load16 native captures on cloud runners only, replays original gates, then reports physical transistor voltages/currents by bit history. No acceptance or circuit changes. Inspect safe `cdr-sampler-c-path-derived-*` JSON on completion; do not download native archives locally. Do not merge experiment workflow.

Four existing jobs were still in progress without artifacts: CRC antenna resume 43579643337, SP LVS 43566292104, DP LVS 43562021054, MBIST 43573697024. Do not restart them. Prior checkpoint below remains applicable.

# CRC continuation handoff archive-name error fixed

43579396178 failed BEFORE native CAD: base archive SHA passed, but tar expected routed.tgz whereas actual freshCRCbase14100640319 contains handoff.tgz. Verified original parent workflowb1626c18095a9a9c7a06b3cb1bd508a4a0ba7f19 uses handoff.tgz. No repair result or changed design. Stop polling thisfailedrun.

Replacement43579643337 source288a68db7bd32fd3218eec5486165a2b4adeb48e, samebranchcodex/crc-jumper-checkpoint-resume, queued at latest dispatch check. Changed only base archive member name and failure archive preservation of recovered-route (so NL/PNL/input checkpoint references survive). ExactSHA/ODB/SDC/565antenna check, jumper-only method,5iterations, freshfinalCheckAntennas and dependent3cornerSTA unchanged. Await actual checkpoint restoration and native repair result. Native archive/content remainscloudonly. Other live43566292104,43562021054,43573697024. Fullgoalopen.

---

# Exact CRC DRT checkpoint recovered; jumper-only repair continuation active

Inventory43579197875 completed/success; safe14106639162 SHA2d74ec95899508f1e5ce5580c13e6c4c18570d9cc556552260675e1be608b651. Savedroute/3-openroad-detailedrouting/drt-run-0/soc_top.odb218660715bytes SHA9adefc224ed62b8e661cdf4c2ae009f4e9910e5e2c5b848156464eb0fdfca40c; SDCroute/1-openroad-detailedplacement/soc_top.sdc SHA1fab1c6a3d4777bca6c00e4008ea6546ef403b100a3bc480683172a0ba682511. State_in NL/PNL fromdetailedplacement. This is completed initialroute before failed diodeinsertion; no newroute pass claimed.

Continuation43579396178 source94b5fab106b45e94460f9ab382cd6b80b2e5ed23, branchcodex/crc-jumper-checkpoint-resume, verified in_progress. Restores freshCRCbase14100640319 SHAf724a289dc08812190d1aac64bfd1b4fafceeaca71c734ed578ca41d96a62f7c then failednative14107653261 SHAa401c73f139405396cf8afdb0e24e718c1334c09d8c49c3e4774d78e3440f64c. Moves oldroute to recovered-route before new force-run-dir, keeps NL/PNL refs valid. Exact ODB/SDC guards, stale metrics cleared, requires fresh565antenna nets before skipping initialDRT. Config changes only DRT_ANTENNA_REPAIR_JUMPER_ONLY=True/DRT_ANTENNA_REPAIR_DIODE_ONLY=False; original5repairiterations,DRT16,ratio10/clocks preserved. Uses supported pinnedupstreamdrt script guardd389d9e6...; no relaxed thresholds. Adds OpenROAD.CheckAntennas afterrepair to prevent stale finalcounts, thenRemoveRoutingObstructions. Dependent extractedSTA retains strict3cornerzero gates. Route355min/19200s,STA355min/19800s. Actual repair result pending.

Safe route-crc_jumper_resume-43579396178; native routed-db-crc_jumper_resume-43579396178 cloudonly; safeSTA routed-sta-crc_jumper_resume-43579396178. Failednative antenna-resume-incomplete-native-43579396178 cloudonly. Failure recovery may require original archive too, because recovered-route references are outside new route archive. Receipt docs/evidence/crc-jumper-recovery-launch-20261114.json. Source experiment only until tested. Stop pollinginventory43579197875 aslive.

Otherlive43566292104(SP),43562021054(DP),43573697024(MBIST). PHYnext: actual Csampler gain/data path after load-only screens failed. Fullgoalopen.

---

# Fresh CRC route failed diode legalization, checkpoint inventory launched; CDR settling diagnosis complete

43561900502 sourceb1626c18095a9a9c7a06b3cb1bd508a4a0ba7f19 terminal/failure, ROUTE_RC2 NOT timeout. Job132347238762 log: initial detailedrouting3h18m08s finishes DRC0; antenna565nets656pins; first repair_antennas fails DPL-0036 on ANTENNA_482,ANTENNA_1342,ANTENNA_457,ANTENNA_458. DependentSTA skipped. Native14107653261 SHAa401c73f139405396cf8afdb0e24e718c1334c09d8c49c3e4774d78e3440f64c stayscloud. Routeartifact14107820079 SHAd88db968c580a65be20a6f92f28f7f4511a23dfffb481103f8a6cf9f3c097a5a includesDRCgeometry, do notdownloadlocally.

New inventory43579197875 sourcedbadad3fb7fbbc40565e65496a6121f9de38d312, branchcodex/crc-route-recovery-inventory, queued at dispatch check. Same prior tested inventory adapted to route-incomplete.tgz; collects only paths/hash/size/state references/metrics, no native bytes locally. Safecrc-route-recovery-inventory-43579197875. Find exact saved drt-run-0 ODB, config/state refs; then diagnose diode legal placement or jumper repair using checkpoint. Do not repeat initial full route. Receipt docs/evidence/crc-route-diode-placement-failure-20261114.json. Stop polling43561900502 aslive.

CDRdiagnosis43579024949 sourceb562486df6d8c15994b355b877bfc80a648d77ac success; safe14107443996 SHA4d9a5206ab7aa3a5d05a7769241058bf3520d308ee87acd5986b2a105b97a895. Exact252interiorbits UI/16grid: neverstable>=100mV by117.1875ps A0/C64 in baseline,load12,load16 all; bufferA67→63/63,bufferC96→96/96. No acceptance threshold/window changes. Csampler history-sensitive margin remains; loads do not fix it. Testedscript integrated, result docs/evidence/cdr-acload-settling-result-20261114.json. Next PHYwork should inspect actual Cmaster/slave gain/data path instead of more load/current sweep. No fullPHY/layoutclaim.

Stilllive43566292104(SP),43562021054(DP),43573697024(MBIST), plusnewinventory43579197875. Fullgoalopen.

---

# Both original-bias collector-load CDR screens fail data; saved-sample diagnosis live

acload16 result from43571075470 verified: simulatorRC0/devicePASS/phasePASS/dataFAIL. X381wrong717below100mV, Y2wrong596below,765samples each. A/C/D lowmargin65/139/96 exactly same counts as acload12;Bpass. Lower collector resistance alone does not fix the data path. No new layout or closed-loop proof. Safe14107393490 SHAd335866dcf7c30ea6e7100f2ba2041b71d64692ee36bc3b3d197a5fa4896ae2e. Native14107159021 SHA5dbfa37bb7560c8b363f6edf179e098c4e2469281b797aba3d0486ebcc389dcc; mixed14106994265 SHAf8b37b573de8ec7608b800a71089896805462a387bd2c3f97cc371f1953ab17e, bothcloudonly. Raw8fb118e2e91346887be64ba06ebd3c9d31bd1b992fbb5adb2d8f8ec97d1a654a,113490points. Receipt docs/evidence/cdr-acload16-rejected-20261114.json.

Next43579024949 sourceb562486df6d8c15994b355b877bfc80a648d77ac, branchcodex/cdr-acload-settling, verified live. Same tested exactUI/16 conditional settling diagnostic adapted to baseline+xor2acload12/acload16 pinned mixed archives. No waveform realignment, threshold edits, new simulation/layout. Script scripts/diagnose_cdr_acload_settling.py onexperiment, safeartifactcdr-acload-settling-43579024949. Goal: distinguish unchanged sampler-margin from buffer-settling effects before another circuit candidate. Native/mixed archives staycloud. Await result before integrating script.

Other live43566292104(SP),43562021054(DP),43561900502(freshCRCroute),43573697024(MBIST). Fullgoalopen; RX6finalantenna0/0 independentlyproven but extractedSTA rejected as recorded below.

---

# RX6 final antenna independently0/0; routed timing rejected; CDR load12 data fails

43577454990 source7e10978a522ae51d0ccc3d251e1f04e7c089884a completed/success. Fresh read-only native antenna check0nets/0pins,0warnings/errors. ODBSHA3eaa76b381138c637770590f5e19bdedebedc9e658c854fe9b4bf109d31c03cd,SDCSHA5c65218b6106315c71d45c19eb61af09781607f0f438f2c7f99c4427884d24a4 unchanged. Old1/2was pre-finalrepair: do not repair this now-clean antenna candidate. Safe14107441301 SHA25849f1b1bffc545a7984b6e20aca9ec633dd49ca36023d35a795d616b77590d. Tested source copied to main. Receipt rx6-final-antenna-zero-20261114.json. Future routing must check antennas unconditionally after final repair; no report-only freshness assumption.

43569629324 terminal/failure. SafeSTA14107520603 SHA3e1a511d5f9560af0dae28a9ecf652d32ee3fb647eb0d5bc8e87fd0944148911 verified/read. Slow1327setup(-1.996737943ns),0hold;typ0setup,2hold(-.012410961ns);fast0setup,74hold(-.111859136ns). FastgroupsPCIe70/CPU4; EthRXhold0. SlowsetupPCIe754/CPU529/async41/EthTX3. Cap105/106/111,slew751/249/125,fanout1423each. Timingreject; freshCRC43561900502 remains priority separate netlist. Do not transplant old-instance ECO. RepeatSTAartifactdownload timedout180s before mutation; first successful SHAverified read supplied exact scalarreceipt docs/evidence/rx6-routed-timing-rejected-20261114.json. No simulator rerun needed.

CDR43571075470 acload12 completed/failure: simulatorRC0/devicePASS/phasePASS/dataFAIL; X381wrong717below100mV,Y1wrong588below,765samples each. A/C/Dlowmargin65/139/96,Bpass. Safe14107175734 SHAc7afa62bbf62281ed8aad8aff94c97bc16af769ceaedd21cff1815c422ca7501; fullresult docs/evidence/cdr-acload12-rejected-20261114.json. Native14107240670 SHAa4f8b266f11b0a48d7bda855c8a6d69933d6ea2933be82f2ec200a89925eb3d5 cloudonly, mixed14106494834 SHA7847a708ebe849dbb6219c58982ff24543d9094dd96e1b7872942f9e6ff22f71cloudonly. RawSHA7591486c78ad4f9e50e82c675417f047b04d8f71d781bb11ea1e4f0e5ca64444,113490points. acload16 stillpending atlastpoll.

Livehandles43571075470(partial),43566292104,43562021054,43561900502,43573697024. Stop polling43569629324/43577454990 aslive. Fullgoalopen; router/antenna checks are not foundry signoff or fullPHY.

---

# Antenna audit format-key bug corrected; final-archive-bound check live

43577172823 failed before OpenROAD measurement with KeyError:'SDC': deprecated DesignFormat.name returns lowercase format id, not enum identifier. Replacement uses explicit odb/sdc keys. Removed incorrect pre-route-SDC hash comparison: final views are bound to exact SHA-verified final routed archive14105679819; hash invariance of ODB/SDC before/after native check remains required. No layout/threshold changes; old SDC equality was not evaluated due KeyError, so no claim of measured hash mismatch.

Replacement43577454990 source7e10978a522ae51d0ccc3d251e1f04e7c089884a, branchcodex/rx6-final-antenna-audit, verified in_progress. Safe artifactrx6-final-antenna-derived-43577454990. Require native antenna__violating__nets/pins, no view replacements, input hashes unchanged. Stop polling failed43577172823/43576971725. Actual final antenna status still unknown; recorded1/2 may precede last repair. Other livehandles remain43571075470,43569629324,43566292104,43562021054,43561900502,43573697024. Fullgoalopen.

---

# Final antenna audit run-directory failure fixed; replacement live

43576971725 failed before any native antenna measurement: CLI --force-run-dir requires existing directory final-ant. Exact source/raw checkpoint unaffected. Job132393216711 confirms archive SHA passed; exit2 on missing run directory. Derived error artifact14106581453 SHAea306ba8840a83fef48235c6be98a926aee285e4f9cb7df743327b3cc8c805c7.

Workflow now mkdir -p out "$OUT/final-ant" before CLI. Replacement43577172823 sourcef2a0307ed1b5c51a6d5422e72b8aeed1c4143f59, samebranchcodex/rx6-final-antenna-audit, job132393847343 verified live preparing pinned tools/PDK. No design/limit/helper change. Await derivedrx6-final-antenna-derived-43577172823, require actual fresh native metrics and ODB/SDC hash invariance. Stop polling failed43576971725. Existing main RX6 stored1/2 remains potentially pre-final-repair and not proven final. Fullgoalopen.

---

# RX6 final antenna metric freshness unresolved; independent read-only audit launched

New evidence: pinned LibreLane3.0.5 drt.tcl loop is `while {$i <= $::env(DRT_ANTENNA_REPAIR_ITERS) && [log_cmd check_antennas]}`; it increments i after each repair/reroute, then writes views WITHOUT an unconditional final check. RX6 consumed all3iterations, so saved1net/2pins may describe the pre-final-repair database. Previous receipt accurately preserves stored metrics, but they DO NOT prove final remaining violations. Do not assert final antenna closure or final1/2 until fresh audit.

43576971725 source94ed5de217b4d811cc735db425c74fe49f6abf21, branchcodex/rx6-final-antenna-audit, verified in_progress. Uses exact final native14105679819 SHA623d7be7b8438522b6b0f81fdec45801006997892ec07953b4687ed88b53d85a; all native stays cloud. Clears old metrics, runs original OpenROAD.CheckAntennas only; no route/repair/threshold edits. ODB/SDC before-after hash invariance and no replacement views required, native antenna metrics required. Derived artifactrx6-final-antenna-derived-43576971725 contains reports/JSON/log only. Sourcehw/soc/pnr/final_rx6_antenna_audit_flow.py is on experiment until tested. First local source-validation attempt failed an enum-text formatting assertion before any mutation; final flow uses only verified ODB/SDC enums. No native local work.

RX6 routedSTA43569629324 remains independent/inprogress. FreshCRC43561900502,CDR43571075470,SRAMLVS43566292104/43562021054,MBIST43573697024 still require results. Fullgoalopen.

---

# RX6 hold candidate routed: router DRC0 but antenna1net/2pins remain; STA started

43569629324 source12101bb1da5f82420b08b363ef707d2d08e55933: routejob132370971009 completed/success. Exact final routed-state reports router DRC0, antenna1net/2pins (NOT antenna closure). Initial39 reproduced by NSSOC_RESUMED_PINNED_DRT_ANTENNA_39. 159731instances,20SRAM,1134antenna cells,0padcells. Ten unsupported LEF58_ENCLOSURE/noCUTCLASS warnings remain; router DRC0 is not foundry signoff.

Safe14106655609 SHA30023bc4368caf39a3327cd0097b1feed3dd4862fa1314dea3a3bafe64c56829. Native routedDB14105679819 SHA623d7be7b8438522b6b0f81fdec45801006997892ec07953b4687ed88b53d85a remains cloud-only. Same-run routedSTA132392278204 started; await exact extracted timing, then diagnose remaining antenna from this exact saved database. Do not restart initial route or transplant old ECO. FreshCRC43561900502 separate/still live. Other liveCDR43571075470,LVS43566292104/43562021054,MBIST43573697024. All acceptance gates unchanged; fullgoalopen.

Receipt:docs/evidence/rx6-route-residual-antenna-20261114.json.

---

# Extracted timing rejects older electrical candidate; misleading clock labels fixed separately

43567570194 completed/failure. Exact finalroute DRC0/antenna0/0 but threecornerSTA fails: slow1390setup(-1.989753ns),2hold(-.356828ns);typ0setup,4hold(-.212935ns);fast0setup,98hold(-.251383ns). Cap105/109/113,slew708/272/144,fanout1416each(slow/typ/fast). SafeSTA14106081080SHA`04c1539e64b73d7e9d53f03d4aac401b43545b721d70c85672ede06c67842f0b`. NominalSPEFsha0a343a9739393cfe0b759e96b21a74241a1a4a7c4c6d7ae3ed3ea547d08d266e,capconservationpasses;RCminmaxunqualified. Receipt:docs/evidence/electrical-routed-timing-rejected-20261114.json.

Worstsetup remainsPCIe fold_word27→crc7,CPUinstr→RF,asyncreset,EthTXb_func→bank1. WorstholdEthRXwq_data9→bank0, NOT earlierRX6address-only target. Prioritize freshCRC43561900502 and separateRX6candidate43569629324 results before any old-instanceECO. Do notcall this oldcandidate timingclosed or transfer its metrics to newRTL.

Clock header contradiction resolved in upstream3.0.5corner.tcl: `if is_propagated` erroneously sets `is_virtual` printvariable, so report showedVirtualyes/Propagatedno. Fixed printassignment only in guarded source, no STA clock/SDC/SPEF/delay/limit edits. Cloud43575282471 sourceacb25e2ffa9c7ce0d65fd0e194bb54cc758074cd passed4truthstates+missing/duplicateanchor rejection; originalbug reproduced in2states. Safe14105737685SHAf0e730850a10485954b0d56837eb1f02ed85ca7dda766c8dbd3b928cf2c1f0ab. Integrated source/test; existingruns unaffected. Receipt:docs/evidence/routed-clock-report-label-controls-20261114.json.

Sixlivehandles43571075470,43569629324,43566292104,43562021054,43561900502,43573697024. Stop polling43567570194 aslive. Fullgoalopen.

---

# Electrical candidate routed with zero router DRC/antenna; exact routed STA now running

43567570194 source`0b0afcacd36d6223e0fba6ce1ddbf18312c955e8`: routejob132364639141 completed/success. Pinnedresume reproduced28antenna nets31pins, then2/2, then0/0. Fresh finalmetrics route__drc_errors=0,antenna__violating__nets=0,pins=0,flowerrors=0. Confirmed stale metrics removed/config unchanged. Final159612instances,20SRAMmacros,1018antennacells. Routepass elapsed~1h19m. Safe14105204176SHA`54cad8e84c4e919fc471203c4a43ef1000d52e53d628fc629f6394ba4dd453c8`; native14105074398SHA`7704bd4afb10dab17e6d15b1abc7290d80ca0663b55af6193a0802a4620f123f` stayscloud.

Same-run dependent routed-stajob132384337030 verified in_progress restoring exact routedDB. Await3corner extracted STA: zero setup/hold/cap/slew/fanout gates unchanged,clocks20/4/8/8ns. No timing pass yet. TenDRT-0349warnings: router skips LEF58_ENCLOSURE withoutCUTCLASS on Cont/Via/TopVia layers. RouterDRC0 does not cover those rules or independent foundry/full-chipDRC. No padcells in this core candidate. This is older five-driver electricalcandidate, NOT freshCRC43561900502 orRX6hold43569629324; do not transplant evidence.

Receipt:docs/evidence/electrical-route-zero-antenna-result-20261114.json. Poll43567570194 STA plus43569629324,43561900502,CDR43571075470,LVS43566292104/43562021054,MBIST43573697024. Fullgoalopen.

---

# MBIST second restore PID collision fixed; same1.26M checkpoint retry active

43573337312 failed in CRIU restore; followup43573539211 collected exact native diagnostic: `criu/log.c:430 pidfile: Can't open .../restored.pid: File exists`, followed by Cannot write pidfile/Restoring FAILED. Original dump includes the previous restore PID file. No simulator error or boot completion. Safe14104814119SHA`fb27a96d108a0feff659ce84e77637199a1318b68506429523592786cd2e2b8f`. FullCRIUlog14105725472SHA`a03213b9615963aff1b3c67b25a1d29d3e7513db062230f9e09b6dbd9e75b961`cloudonly. First failure safe14104843822SHA`a3641939cdf17db5eb2d76620ac9ff4aa0efe807a7d87d0a89fb50280ddd2eab` lacks detailedCRIUlog.

Fixed43573697024 source`27c496c5649c284e5cc1494792ef103c7fd427c7`, branchcodex/full-native-boot-continuation-two, in_progress at restore/simulation step. New outputPID`restored-RUN_ID.pid` must not exist; old files retained. CRIU detailed errors now extracted into safe result, full log retained cloudonly. SAME original1.26Mcheckpoint/input/runtime/hash/image identity, original28gates and3Mcyclebound, no restartfromzero. Actual restore progress/boot acceptance still requires result, not inferred from live step. Script on experiment branch; copied to integration only as dedicated source snapshot to avoid replacing older entrypoint.

Receipt:docs/evidence/full-native-restore-pid-fix-20261114.json; snapshot:scripts/resume_full_native_boot_from1260k.py. Poll43573697024 instead of failed43573337312/43573539211. Otherlive43571075470,43569629324,43567570194,43566292104,43562021054,43561900502. Fullgoalopen.

---

# Full native MBIST advanced to1.26M cycles; next exact checkpoint continuation launched

43558722004 completed/success as checkpoint infrastructure ONLY: passed=false,completed_boot=false,checkpoint_saved=true,stage_status=checkpointed_pending_boot.10800.323s segment,last_progress_cycle1260000. Safe14105022987SHA`43f3463da142dde3d0e5e9ca57d0292a8bf67286479b00656d69a39d9fb479de`; native14104748996SHA`875955125fb62aa659076191cf87496b58209fd56059d2bc1f38f24cf3aac6cf`cloudonly. Innernext-checkpoint.tgzSHA`8f480f6170a83b41ed1be10ef15ac5beae08b3f77e635575274e6f1ad6632181`; prefix10534bytesSHA`a2b5e52f0f115f5c17249a7eea6528f2b50814d1be91992f5b7b66714f5223e5`; CRIUimage_directory`images-43558722004`. No boot acceptance; uart/flash still0 during observed MBIST phase.

Next43573337312 source`5f4612b7a1aa09f8fafb3a0ffc3548b8c82f84fa`, branch`codex/full-native-boot-continuation-two`, verified in_progress. Exact parent chain/status/source/cycle/hash guards, restore images-43558722004; runtime/kernel/mappedfiles unchanged required. Input next-checkpoint.tgz renamed parent-checkpoint.tgz after restore/unpack verification so unchanged input cannot be uploaded as a fresh output checkpoint. Original full3Mcyclebound and28bootchecks/system+EthernetMBIST retained. Original boot checker/preparer/lock compared with frozen parent and unchanged. Native restore not yet proven by completed result. Safe prefixfull-native-continuation-result-43573337312, nativefull-native-continuation-checkpoint-43573337312; allnative stayscloud.

Receipt:docs/evidence/full-native-1260k-continuation-20261114.json. PollnewMBIST43573337312 plusCDR43571075470,route43569629324/43567570194/43561900502,LVS43566292104/43562021054. OldMBIST43558722004 terminal, do notpollaslive. Fullgoalopen.

---

# Internal clock topology/measurement completed; no missing clock edges in observed candidate

43572236262 source`e260cf027733c35302e1ac375b0d10a80ec69a24` completed/success. Safe14103694704SHA`b96721f2fa7ef446cbcfde835258d25b10d8c7dde97a112e447b742cba8ca8b9`. Prior43571981658 failed solely because one-to-one pairing assumption rejected real parallel clock devices; corrected by all shared-emitter positive/negative branch combinations, not arbitrary matching. Source and report: scripts/diagnose_cdr_internal_clock.py; docs/evidence/cdr-internal-clock-result-20261114.json.

Native acbuf15 waveform and original failure gates reproduced. Connectivity-only wire-R collapse identifies16cp-driven+16cn-driven HBTs,32branch combinations,8master/slave MOS-tail banks. Actual captured base voltages retain full RC. All branches have258rising/257falling expected edges. C master/slave source-relative crossings roughly14.76..15.36ps, versus receiver port~11ps. This establishes measured internal clock arrival for this rejected candidate, not missing-edge causation, C sampler gain acceptance, jitter/PVT qualification, closed-loop PLL or final PHY. Keep original sample times/limits. C history-dependent amplitude problem remains; inspect data/latch/gain path next rather than assuming clocks absent. Await ongoing acload12/16 isolated load screen43571075470.

Other six handles43569629324,43567570194,43566292104,43562021054,43561900502,43558722004 active at last poll. Fullgoalopen.

---

# Corrected clock-capture diagnosis: physical cp/cn were saved

Clock audit43571554607 source`df70272f91e5819edc20421868e6ef7e0fdd4382` completed/success. Safe14104249669SHA`3030d7a5065d48fea1a0857aa4a081dbce2944a0b8e2118e73aab84b68d49329`. Exact full acbuf15 raw reproduces original failed data/device gates. Both v(cp),v(cn) exist. Prior notes saying clock vectors were absent were incorrect: clk/clock substring search missed cp/cn. Corrected both settling scripts to include contract-bound cp/cn aliases. Full diagnosis source and report preserved in scripts/diagnose_cdr_saved_clock.py and docs/evidence/cdr-saved-clock-port-result-20261114.json.

Receiver port crossings:258/258 rising,257/257 falling; rising source-relative10.987..11.662ps,falling10.889..11.207ps. Differentialrange-0.29949..+0.27762V, commonmode1.28353..1.29335V. These are receiver port voltages, NOT internal latch-clock timing, PLL recovery, jitter qualification or timing acceptance. Original stimulus-referenced sampler thresholds/windows remain unchanged; do not subtract observed delay to obtain a pass. Existing captured internal device-base voltages may permit further stage diagnosis without new simulation once actual topology identified.

New acload12/16screen43571075470 still live at last poll; other six43569629324,43567570194,43566292104,43562021054,43561900502,43558722004 also live. Fullgoalopen.

---

# Exact CDR failure recovered; independent collector-load screen running

Native diagnosis43570807730 completed/success: original sampler/comparison and device gates reproduced exactly from full raw. acbuf15 eight HBT violations are active minimumVce0.2186..0.3017V vs0.4V floor, NOT excessive current. acbuf20 lowers selectorVce to0.0734..0.1273V and adds buffer/tail headroom violations plus three startupVce peaks1.603..1.609V vs1.6V ceiling. Do not relax those bounds. C sampler low-margin samples occur only when bits[k-2]!=bits[k-1] in the diagnosed interior history; not a proven clock-topology explanation. No internal clock measurement inferred.

Safe artifacts14103968849SHA6552ec7b2f30e515ffd107678c5ac5545ec6ca4f2257377eec2743a6f9ca1389,14103859118SHA48a9d9ea9ee5f656dc539a2507b7af58e1f4da3e0a93447d24a10faaaae5bfab. Results and next-run receipt:docs/evidence/cdr-native-failure-result-and-load-screen-20261114.json. Tested diagnosis source preserved scripts/diagnose_cdr_native_failures.py; needs frozen helper source ec52087 for reproduction.

Next screen43571075470 source`7e7b32d746ef5b19e7ed72ac23af2368b8fea624`, branch`codex/cdr-ac-load-original-bias`, observedin_progress. Two variantsacload12/acload16 keep ALL originalbench/bias sources byte-identical and only change four A/C collector widths8u→12u/16u relative to xor2 baseline (bd10_lowz8_xor2). Native topology and fourline-only guards retained. Pure source patch checks passed before dispatch. Original device/data/phase gates unchanged. This separates collector-load reduction from harmful bias increase; lower swing is a risk requiring actual measurement. ExistingRC/externalclock means no newlayout/PHYpass. Safe resultprefix`cdr-ac-load-result-only-VARIANT-43571075470`; mixed/native archives cloudonly. Read result-only first.

Six other live handles43569629324,43567570194,43566292104,43562021054,43561900502,43558722004. Fullgoalopen.

---

# Full saved CDR device/history diagnosis launched

43570807730 source`ec52087e74b97d707236035938df178180f27378`, branch`codex/cdr-native-device-history-diagnosis`, verified in_progress. Two cloud jobs restore original full raw waveforms for rejected acbuf15/acbuf20; no simulator rerun. Exact archive/raw hashes, candidate nx=2 binding, unchanged gates must reproduce saved results. Reports exact failing HBT metric/time/terminal voltages and four-bit history at original sampler phases. Safe artifacts`cdr-native-failure-derived-VARIANT-43570807730`. Native archives remain cloud-only. Implementation on experiment branch; integrate only after successful result. Receipt:docs/evidence/cdr-native-failure-diagnosis-launch-20261114.json.

Six prior routing/LVS/MBIST jobs still live at latest poll. Full production goal remains open.

---

# CDR comparison completed: current-only buffer change is insufficient

Diagnostic43570390846 completed/success; safe14104122995 SHA`f5c99f1b5635a011c56874959815b8d09850b49e518d9c542b7e4ca5d77a40b4`. Result saved in docs/evidence/cdr-ac-buffer-settling-result-20261114.json. Diagnostic success is not a PHY pass.

Exact preserved grid after rising[k],252 interior bits: transition A-buffer failures67/127 baseline,63/127 for BOTH acbuf15/acbuf20 by final117.1875ps grid point; passing transitions still ~101.6..117.2ps. C sampler failures64/252 unchanged, C buffer96/252 baseline and1.5x,89/252 at2x. Original strict sample gates remain authoritative; these conditional grid counts are different windows, not replacements. Stronger buffer modestly improves latency but leaves dominant errors and introduces device-limit failures. Neither candidate accepted.

Next: diagnose C sampler history/clock relationship and XOR selector operating-point violations before another current sweep. Saved captures lack clock vectors: do not infer clock timing from data alone; use actual topology plus a targeted cloud capture if needed. Native archives stay cloud-only. Existing six timing/LVS/MBIST jobs were still active at last poll; retrieve their final evidence before claiming closure. Full goal remains open.

---

# CDR A/C buffer current screens rejected; saved-waveform comparison running

43562981217 completed/failure. Both acbuf15 and acbuf20 simulate successfully and pass phase, but fail data and device limits. X wrong-sign samples383/765 for BOTH; Y below100mV587/588 samples. Failing HBT counts8/14; sampler A/C/D remain failing. No PHY acceptance, no new layout. Do not repeat unchanged current increases.

Safe result-only14103877257SHA`f9e9332b631252c132227b877b48b7593d95af88317ae3ac7b482d4a0c5cd466` and14103871330SHA`b39fb2fa31b2e955c00f7380e9a8b0d429f7b59847bbc63c5be589df5dbfee61` verified. Full results: docs/evidence/cdr-ac-buffer-rejected-result-20261114.json.

Diagnostic43570390846 source`7b6db8cfb6c50edb9d6330aed231cc833976cd8a`, branch`codex/cdr-ac-buffer-settling-comparison`: exact UI/16 saved grid for original xor2 + acbuf15 + acbuf20. No threshold or sample alignment changes. Mixed NPZ archives remain cloud-only. Safe artifact`cdr-ac-buffer-settling-43570390846`. Inspect conditional transition settling before next circuit change; diagnostic success alone is not acceptance.

Other six runs freshly verified in progress: RX6resume43569629324, electricalresume43567570194, SP43566292104, DP43562021054, freshCRCroute43561900502, nativeMBIST43558722004. No numerical timing/LVS improvement inferred from live job status. Full goal remains open.

---

# RX6 hold checkpoint verified and split continuation launched

Inventory43569490025 completed/success. Safe14104151119SHA`0d974e1bec75005424ef7e0ac94b81bd52587b9234245dc5e07c2a989ae965bb`; candidate drt-run-1ODB221904411bytes,SHA`329e6ef42702320243b595ab56554d5fc3fd3c63e93ff452faad0a206df36c82`. SDCsame5c65218b6106315c71d45c19eb61af09781607f0f438f2c7f99c4427884d24a4 but path`rcx/1-nssoc-cut10jrx6holdthree/soc_top.sdc`. Native14103417683SHA`361ca0f3c8fad45e6c8a8a4b49e828804cb48df8835651acb49932222f6e1c31`cloudonly.

Resume43569629324 source`12101bb1da5f82420b08b363ef707d2d08e55933`, branch`codex/resume-rx6-hold-antenna-pass`, dispatched. Same exactruntimeDRTscriptguard/skipinitialfullroute approach as43567570194, but MUST reproduce39antenna nets for this specificholdcandidate. Clears inherited metrics, originalconfig/clockunchanged. Route and RCX/STA split jobs, original strict zero gates. Artifacts`route-cut10j_rx6_ant_resume-RUN`,`routed-db-cut10j_rx6_ant_resume-RUN`,`routed-sta-cut10j_rx6_ant_resume-RUN`; nativefailprefixantenna-resume-incomplete-native-RUN. Neither continuation yet validated as success.

Receipt:`docs/evidence/rx6-hold-checkpoint-resume-launch-20261114.json`. Poll7live handles:43569629324,43567570194,43566292104,43562021054,43561900502,43562981217,43558722004. Old43538031308/43541234973 terminalfailure. Fullgoalopen.

---

# Ethernet RX6 hold candidate also timed out; separate checkpoint inventory running

43541234973 completed/failure, nativeRCX_STA_RC=124 at330min. IntermediateDRC0 after first antenna repair;39nets/41pins remain, secondrepair82diodes cut off during pinaccess. No final timing, so hold benefit not yet verified. Safe14104080998SHA`79cf09302f5cc660a21d05d0ca5dd6c7105395790bfa498856426e4df88dbfb6`; native14103417683SHA`361ca0f3c8fad45e6c8a8a4b49e828804cb48df8835651acb49932222f6e1c31`cloudonly.

Inventory43569490025 source`0aebe4c70dbf6c5273f23f2c2d821ad5c33ea430`, branch`codex/rx6-hold-route-recovery-inventory`, safe prefix`rx6-hold-recovery-inventory-43569490025`. Inspect exact drt-run-1ODB and candidateSDC hashes; never use electrical-only candidate hashes for this variant. Reuse split-resume method only once native readiness/identity established. First electrical-only resume43567570194 still running; do not duplicate it.

Receipt:`docs/evidence/rx6-hold-route-timeout-recovery-20261114.json`. Otherlive SP43566292104,DP43562021054,newCRCroute43561900502,CDR43562981217,MBIST43558722004. Bothold43538031308/43541234973 terminal, no longerpollaslive. Fullgoalopen.

---

# Saved antenna checkpoint continuation launched with separate RCX/STA budget

43567570194 source`0b0afcacd36d6223e0fba6ce1ddbf18312c955e8`, branch`codex/resume-pinned-antenna-pass`, active. Restore original base14068260482 then nativecandidate14102387358. Exact drt-run-1ODB SHA6613e8102b7a4076f1748b75447ece150ccf86818c06dc89b50ca42cb2b92b7e, candidateSDC SHA5c65218b6106315c71d45c19eb61af09781607f0f438f2c7f99c4427884d24a4. Initial state onlyODB/SDC/NL/PNL, all stale metrics removed; config unchanged.

Flow`hw/soc/pnr/resume_pinned_antenna_flow.py`: exact runtimeDRTscript SHA`d389d9e6d75bbb82552321f689d92a2e0392684142c11ffabe59c757ece59461` guard. Omit initial full drt_run ONLY; fresh check_antennas must reproduce28net violations before continuing original3-passrepairloop. Native restore behavior still needs result, no pass claim. Route19200s then routed_handoff; dependent separateRCX/STA19800s,355min each. Strict3cornertiming/electrical+DRC+antenna gates unchanged. Native failure archives retained. Safe route report excludesDRCgeometry files. Artifacts:`route-cut10j_ant_resume-RUN`,`routed-db-cut10j_ant_resume-RUN`,`routed-sta-cut10j_ant_resume-RUN`; failednative`antenna-resume-incomplete-native-RUN`cloudonly.

Receipt:`docs/evidence/antenna-checkpoint-resume-launch-20261114.json`. StillactiveSP43566292104,DP43562021054,freshCRCroute43561900502,CDR43562981217,MBIST43558722004,oldholdroute43541234973. Prior43538031308 terminalfailure, do notpollaslive. Fullgoalopen.

---

# Route recovery checkpoint located; implement resumed antenna pass next

Inventory43567101492 completed/success. Safe14103305888SHA`9e8ece69660c7d0b8cb99aa997cbad3a143766c7843db23e7d8876a0a31da3e1`. Saved checkpoint `hw/soc/out/impl-probe/rcx/4-openroad-detailedrouting/drt-run-1/soc_top.odb`,221619313bytes,SHA`6613e8102b7a4076f1748b75447ece150ccf86818c06dc89b50ca42cb2b92b7e`, after first antenna pass (28nets/31pins remain; intermediateDRC0). Native archive14102387358SHA`3f7e4ca94925a33d730cfe47b1f4487434c05b76e4c6e10e847f04317d3898e6`. Presence/hash verified, native restore still untested.

NEXT: create split cloud recovery flow. Restore original base14068260482SHAcf6a83685c33cdf4083786f0ab136ef1ea2666b44476521228aed5eed73d0855 then candidate archive overlay to sameabsolute workspace. State ODB must bind drt-run-1; SDC at rcx/1-nssoc-cut10jfivedriverresize/soc_top.sdc SHA5c65218b6106315c71d45c19eb61af09781607f0f438f2c7f99c4427884d24a4. Old state has STALE inherited route/antenna metrics; clear/recompute, not acceptance. Upstream LibreLane3.0.5 `librelane/scripts/openroad/drt.tcl` inspected: drt_run writes eachODB, initial `drt_run $i {*}$drt_args` then incr i, whilecheck_antennas/repair_antennas/drt_run. Adapt runtime script with exact anchor guard to omit first full reroute from this checkpoint, then fresh antenna check/repair. Native restart behavior needs validation; no pass claim from files. Separate route handoff and RCX/STA (avoid330min combined budget). Existing freshCRCroute unaffected; do not use old instance ECOs there.

Receipt:`docs/evidence/five-driver-route-checkpoint-result-20261114.json`. Stilllive SP43566292104,DP43562021054,newroute43561900502,CDR43562981217,MBIST43558722004,oldholdroute43541234973. Full goal open.

---

# Old five-driver route timed out; cloud recovery inventory running

43538031308 completed/failure, nativeRCX_STA_RC=124 after19800s. Initial detailedroute4h06m;244antenna nets/261pins. First repair424diodes and intermediateDRC0, then28nets/31pins. Second repair44diodes started, cut off during pin access. NO final route or extracted STA. Derived14102821860 SHA256`30ce5dfb1e35baa00e3da190ccfb5f83b346e2f4b9d53f7c2d9b7e7d87d24585`; native14102387358 SHA256`3f7e4ca94925a33d730cfe47b1f4487434c05b76e4c6e10e847f04317d3898e6`192.8MB, cloud-only.

Recovery inventory43567101492 source`a3907ddf599b5533187995ea8de00b35c60ec7c7`, branch`codex/five-driver-route-recovery-inventory`: inspect archive filenames/hashes and state view paths in cloud. Safe artifact`five-driver-recovery-inventory-43567101492`. Do NOT assume intermediate routedODB exists merely because logs show completedDRT; inspect saved states first. Next recovery must split/checkpoint stage budget; do not repeat unchanged330min run. Do not transplant this oldcandidateECO into freshCRCnetlist.

Receipt:`docs/evidence/five-driver-route-timeout-recovery-20261114.json`. Other live runs:SP43566292104,DP43562021054,newCRCroute43561900502,CDR43562981217,MBIST43558722004,oldholdroute43541234973. Full product remains unqualified.

---

# SP fullmacro mismatch localized; six-boundary comparison running

43564996899 completed/failure, extractionRC0/auditRC1:24Match,6NoMatch,1Skipped top;0extraction diagnostics. Both sides1211120recursiveprimitives (817450MOS+393670R), unchanged original/candidate CDL inventory. Tested reader hash87a75b402b35d7306153a66089c0f0105b4e50c4816c7c553d97219af6c41519 bound to actual candidate. Safe14102840450 SHA256`8aba5c22b51a18a6f7942427d2cdba5e48a65a8981c9806d917d2fed89f68e29`; native14101844940SHA`48f06a811262a9ae15a99ce5fd53c9e31503f450e3f90eae69e3135fffd1f120` stays cloud-only. No LVS pass.

43566292104 source`c226118b038f4180ce97452b9e469e873b37fd83`, branch`codex/sp-sram-engineering-six-boundaries`: sameSPreference, flatten exactly observedCBUFX8,CINVX2,CINVX8,FILLCAP4,FILLCAP8,WLDRVX8 on both sides. Count must remain1211120 before/after EACH side. No geometry/CDL/net/body/port edits. This tests hierarchy representation, not an acceptance waiver. Native18000s/workflow350min. Derived prefix`sp-sram-engineering-reference-normalized-derived-sp-deep-43566292104`; native counterpart cloud-only. Receipt:`docs/evidence/sp-sram-fullmacro-boundaries-20261114.json`.

Other six runs remain active:DP43562021054,newroute43561900502,CDR43562981217,MBIST43558722004,oldroutes43541234973/43538031308. Full product goal remains active.

---

# Independent SP engineering reference fullmacro comparison running

43564996899 source`867aa31021be8d6fec40ebb5afe2d7bcdc85a354`, branch`codex/sp-sram-engineering-reference-v1`. Five explicitly reversible R statement edits only: bitcellR0/R1metal2,R2metal3 W0.2/L0.6; standaloneMET2RES/MET3RES eachW0.26 unchanged, only layer-model identity explicit. Original GDS/CDL immutable, terminal tokens unchanged. Strict reader, metal1 controls, ports/bodies unchanged. Full recursive original/candidate CDL inventory must agree before native run. Original SP hierarchy retained, NO DP six-cell flatten or70110 count assumption. Native18000s/workflow350min.

Safe result prefix`sp-sram-engineering-reference-v1-derived-sp-deep-43564996899`; native counterpart remains cloud-only. Bind actual candidate reader to tested87a75b402b35d7306153a66089c0f0105b4e50c4816c7c553d97219af6c41519 when result arrives. Successful engineering comparison is not vendor qualification or full-chip acceptance. Receipt:`docs/evidence/sp-sram-engineering-reference-launch-20261114.json`.

Continue DP43562021054, route43561900502, CDR43562981217, MBIST43558722004, oldroutes43541234973/43538031308. Goal active; full production not achieved.

---

# SP direct-pin recovery passed; original SRAM LVS remains failed

43564703460 completed/success source`daf24ca240958f2ed85099b48f72bb0b44904487`; safe14101134348 SHA256`9ef327edaad1aaa5c6d605e127c36c8fb658d464a9da3836cf6f47b5503314e2`. Native saved DB reused, no extraction rerun. One duplicate expanded net name confirmed in original layout; direct Net.each_pin avoids merging conductors by label. All three R have unique two-external-endpoint correspondence: R0/R1 -> res_metal2, R2 -> res_metal3; each W0.2/L0.6um versus original genericW0.26. Isolated body ports still absent in layout vs NW/PW reference; NEVER alias those. Tested script now on integration.

Next: use this independent SP map for a separately versioned engineering reference, preserving original GDS/CDL and strict fullmacro comparison. SP standalone MET3RES width is0.26 (NOT DP0.24); no SP fullmacro correction/acceptance yet. Determine exact SP primitive counts/hierarchy, do not transplant DP70110 assumption. Current DP engineering comparison43562021054 remains running. Receipt:`docs/evidence/sp-sram-direct-pin-result-20261114.json`.

Keep live route43561900502, CDR43562981217, MBIST43558722004 and oldroutes43541234973/43538031308. Full product remains unqualified.

---

# SP original bitcell LVS failed; saved-database endpoint recovery running

Run43563445727 completed/failure. Independent audit: one NoMatch,9primitives both sides,0extraction diagnostics. Three original generic R W0.26 vs extracted twoM2/oneM3 W0.2 (L0.6). Endpoint diagnosis stopped with AssertionError; expanded-name uniqueness assumption suspected. Duplicate VSS port labels observed; NEVER merge nets by those labels or alias body ports.

Recovery43564703460 source`daf24ca240958f2ed85099b48f72bb0b44904487`, branch`codex/sp-sram-direct-pin-diagnosis`, reads saved native14101208963 only in cloud. Uses actual netlist Net.each_pin/NetPinRef.pin directly, preserving duplicate names; no repeated extraction or reference edit. Await derived `sp-bitcell-endpoint-diagnosis-43564703460`; require native process exit0 and inspect mapping before using it. Original failure receipt:`docs/evidence/sp-sram-bitcell-failure-recovery-20261114.json`.

Other six live runs unchanged:43562021054,43561900502,43562981217,43558722004,43541234973,43538031308. Full PHY/timing/current full-chip production gates remain open.

---

# SP SRAM owner diagnosis passed; separate SP bitcell comparison running

**43563284302 completed/success**, source`b7adb2000f01d80a24532e8dc91ea2057d07fd4e`, safe14100549566 SHA256`f63436b55538ad4ac67d374ea10d12cc9c355bf3ba05c96441f0cebcf890d6a6`. Original SP reference393670genericLVSRES:393216in131072bitcells(3each),64MET2RES,384MET3RES,6metal1dummy. All original W0.26/L0.6um. Physical marker leaves show bitcell-typeM2/M3W0.2 and standaloneM2/M3W0.26. **SP standalone metal3 is0.26, not DP0.24**; independent SP mapping required. No whole-macro polygon expansion/topology/LVS acceptance. Receipt:`docs/evidence/sp-sram-resistor-owners-result-20261114.json`.

**43563445727**, source`60dd2a564467738d1fc55ef628bf751443896e2e`, branch`codex/sp-sram-original-bitcell`: original physicalRM_IHPSG13_1P_BITKIT_CELL vs originalCDLRM_IHPSG13_2048x64_c2_1P_BITKIT_CELL, explicit top-name translation only. ThreeR+sixMOS expected. Strict widths/classes/ports and no-merge correction; native1200s bound. Actual netlist endpoint mapping integrated (not xref display circuits), no body aliases. Do not call successful diagnosis LVS acceptance; inspect audit and mapping. Native artifacts cloud-only, derivedprefix`original-sp-sram-bitcell-derived-`.

Long runs remain active as before: newroute43561900502, DPcandidate43562021054, MBIST43558722004, oldroutes43541234973/43538031308, A/Cbuffer43562981217. Keep full serial PHY, qualified RC/Liberty, current full-chip verification and external manufacturing approval open.

---

# Current SP SRAM independently inventoried next; DP evidence is not transferable

**43563284302**, source`b7adb2000f01d80a24532e8dc91ea2057d07fd4e`, branch`codex/sp-sram-original-resistor-owners`: original **RM_IHPSG13_1P_2048x64_c2_bm_bist** GDS/CDL pins restored from package663146895 only in cloud. Script`scripts/diagnose_sp_sram_resistor_owners.py` enumerates original hierarchical generic resistor owners and physical marker-leaf dimensions. Full top polygon expansion intentionally omitted; no LVS/connection/production claim or source edits. Require no unresolved CDL child models. Receipt:`docs/evidence/sp-sram-resistor-owners-launch-20261114.json`.

Do not extend DP bitcell mapping or candidate43562021054 to the four SP macros without independent evidence. Continue the live freshroute43561900502, DPcandidate43562021054, MBIST43558722004, oldroutes43541234973/43538031308 and A/Cbuffers43562981217. No same-input reruns; no local native files. Full product goal remains active and unproven.

---

# Exact reader controls passed; targeted A/C buffer circuit screens running

**43562548073 completed/success**: all10actual-CDL CustomReader positive/layer/W/L/open controls passed, nativeRC0. Safe14100384146 SHA256`2d34f811c1557b044eaaec0436035555bf8466c21cfc6c2880436e01357ac62c`. Candidate reader SHA256`87a75b402b35d7306153a66089c0f0105b4e50c4816c7c553d97219af6c41519` must match actual engineering macro43562021054 result before binding. Receipt:`docs/evidence/sram-reference-reader-controls-result-20261114.json`.

**43562679420 completed/success**, source`10eba9d8c228d5146df70ba37e78b2fc5ccda8dd`, safe14100379062 SHA256`86c5edf695e8a93a773bb441c6d238ab897e70ef2dad1e6e113a7b98facca056`. Exact-grid A sampler stable100mV at39..47ps on transitions; bufferA67/127(xor2),73/127(xor3) transitions still not stable by117.1875ps, those stable reach109..117ps. No clock vectors saved; selector clock remains unmeasured here. Some C sampler late margins also fail. Sampled settling is not continuous/native acceptance. Receipt:`docs/evidence/cdr-buffer-settling-result-20261114.json`.

**43562981217**, source`27a6dc7c4ae918c7d8a3888701e5b2ae26e254f3`, branch`codex/cdr-ac-buffer-current-resistance`: two isolated screens on failedxor2 baseline. Only four A/C collector resistor widths8->12/16um and two ibda/ibdc reference bias1->1.5/2mA change. All other topology, actual multiplicity binding,3mA/emitter and original sampler/data/phase/device gates remain. NominalI*R preservation is a hypothesis. ExistingRC/externalclock retained forscreen only; no newlayout or closedloopclaim. Safe result-only artifact prefix`cdr-ac-buffer-result-only-`; mixed NPZ/native archives remain cloud-only. Receipt:`docs/evidence/cdr-ac-buffer-screen-launch-20261114.json`.

Scripts for successful reader/settling diagnoses are now on integration. Continue live routes43561900502/43541234973/43538031308, fullmacro43562021054, MBIST43558722004. Full production objective remains open.

---

# Reader qualification and CDR settling diagnostics launched

**43562548073**, source`5ce444217f111bad822c9cf44a17e0645b7cc1c9`, branch`codex/sram-reference-reader-controls`: actual CDL through exact candidate CustomReader, then native independent graph comparison. Ten positive/layer/W/L/open controls. When finished, bind reader_candidate_sha256 to engineering macro reader hash; do not treat isolated policy tests as whole-macro signoff. At observation native runtime install stage live.

**43562679420**, source`10eba9d8c228d5146df70ba37e78b2fc5ccda8dd`, branch`codex/cdr-buffer-settling-diagnosis`: frozen failed XOR2/3 native samples remain cloud-only; exactUI/16 phase grid quantifies A/C sampler-to-buffer settling by bit transition. No new simulation/layout/polarity/gate changes. Metric is stable signed100mV through last sampled phase, not continuous-time/PHY acceptance. Use to select concrete next circuit experiment; do not repeat blind XOR size sweeps.

Receipt:`docs/evidence/reader-cdr-settling-launch-20261114.json`. Five long runs43561900502,43562021054,43558722004,43541234973,43538031308 verified live this turn; continue exact polling. Full production objective remains open.

---

# Strict native resistor negative controls passed

**43562168662 completed/success**, source`425b317cbd0dc7c5e82fd31a3806febdcaaf087a`, safe14100796355 SHA256`4fa2c9ca950e00f7c564f7d27ca7c92884c1b03a2e370fa5c8927259440f41aa`. All10native verdicts checked: both metal2/metal3 positive graphs match; wrong layer/W/L/open each rejected. Native returncode0, exact fixed RES2 class SHA256`1f9d1328eb1af5a534ff68a5cbc263513e305ece27bb87b75ef4b9454f45236f`. Scope is comparator policy only, not full deck-reader/candidate-macro/signoff qualification. Script now on integration; receipt:`docs/evidence/sram-reference-resistor-controls-result-20261114.json`.

Fresh route43561900502 and engineering-reference macro43562021054 remain the active next tasks below; poll exact handles. Do not rerun comparator controls unchanged or infer full LVS closure.

---

# Fresh routed candidate and SRAM engineering reference now running

**43561900502**, source`b1626c18095a9a9c7a06b3cb1bd508a4a0ba7f19`, branch`codex/crc-order-fresh-antenna-route`: exact fresh CRC handoff14100640319 pinned, now native route stage. Legalize/global/detailed route with antenna repair5/5 and unchanged ratios, DRT16; dependent nominal extracted RC and standalone three-corner STA; strict zero timing/electrical/DRC/antenna gate. No old instance ECOs. Native data retained cloud-only.

**43562021054**, source`70ebe8dca3b28d91a259f49bfee6b5b57c219f6e`, branch`codex/sram-engineering-reference-v1`: strict full-DP-macro engineering-reference comparison. Script`scripts/run_sram_engineering_reference_v1.py`; eight R statements across three cells change only proven layer/W tokens, original CDL/GDS unchanged. Exact reversibility and unchanged terminal assertions; no body aliases, no ports/tolerance waiver. Candidate result explicitly separate from original vendor/current-chip acceptance. Original70110primitives preserved.

**43562168662**, source`425b317cbd0dc7c5e82fd31a3806febdcaaf087a`, branch`codex/sram-reference-resistor-controls`: exact Ruby RES2 strict layer/width/length/open native rejection controls. Inspect all10verdicts, not just green workflow; not full macro/deck-reader/signoff proof.

Receipt:`docs/evidence/fresh-route-sram-reference-launch-20261114.json`. New experimental workflows stay on experiment branches. Long MBIST43558722004 and old route candidates43541234973/43538031308 were verified live this turn. Poll exact handles; do not relaunch based on observation delays. Full serial PHY, current-chip LVS, final qualified timing/RC and manufacturing remain open.

---

# Fresh CRC deep repair completed: route the new pinned handoff next

**43550440744 completed/success**, exact source`ecbcf43200413fc63844bbd20a7532f87af54216`. Both deep setup and hold repair completed; native handoff **14100640319**, SHA256`f724a289dc08812190d1aac64bfd1b4fafceeaca71c734ed578ca41d96a62f7c`, retained7days, cloud-only. Derived report14100400861 SHA256`d4b77f873736fe69c70c665478c465e32a645bb80cc57d3a9ca8cd62b7a893c9` inspected; contains logs/reports/TCL/config/flop map, not native DB/netlist.

Same-candidate estimated PCIe worst setup improved **-1.123 -> -0.264ns**. Remaining reported slow CPU setup~-0.15ns, fast Ethernet RX hold~-0.02ns. These are **post-global-route estimated parasitics, not routed/extracted acceptance**, group table values rounded and not full violation counts. Receipt:`docs/evidence/crc-order-deep-repair-result-20261114.json`.

**Next physical action:** launch fresh antenna-aware detailed routing and extracted RC/all-corner STA from this exact handoff. Do not transplant old cut10j instance ECOs. Preserve antenna ratios; old3iterationsleft1violation, so evaluate additionaliterations. No downstream route has been launched for this handoff yet.

Latest SRAM endpoint diagnostic succeeded as documented below; original full LVS still fails, corrected engineering reference candidate not yet launched. MBIST43558722004 and old route candidates43541234973/43538031308 remain live. Full serial PHY and manufacturing objective remain open.

---

# SRAM bitcell endpoint correspondence proven; original LVS still fails

**43561481053 completed/success**, source`31c39226b470f7fd07d14f2788b0fbe74c2e4ec0`, safe14100646223 SHA256`5b740aa78dda74bad16c0ca0478f7d471c8e42a3ac1953af6967be6e60643cfb`. Read-only original DB: each of six resistor endpoints has two named external anchors, uniquely paired. **R0/R1/R3/R4 -> res_metal2; R2/R5 -> res_metal3; all L0.6 W0.2**, versus original generic LVSRES W0.26. Original schematic MOS bulk pins anchor PW/NW; isolated layout body nets lack external pin labels. Do not invent body aliases. Working script`scripts/diagnose_sram_bitcell_endpoints.py` now on integration; uses actual db.netlist/reference circuits, not xref display circuits.

Failed harness runs43561017033/43561129891/43561263620/43561370062 are terminal and rejected, including two cleanup aborts despite JSON output. Receipt:`docs/evidence/sram-bitcell-endpoint-mapping-20261114.json` contains sources/reasons. No need to rerun this diagnosis unchanged.

Next: versioned engineering reference candidate using proven layer/width mapping plus previously established standalone MET2RES/MET3RES ownership, strict full-macro comparison in well/tap context, wrong-width/layer/open controls. No geometry changes, no body aliases, no tolerance waiver; candidate correction is not vendor approval. **No corrected candidate has yet been launched or accepted.**

Continue exact live handles MBIST43558722004, CRC deep repair43550440744, old routes43541234973/43538031308. Native data stays cloud-only. Full PHY, final timing, current-chip LVS and manufacturing remain open.

---

# Original SRAM bitcell: strict mismatch localized; endpoint mapping launched

43559617022 completed/success as a diagnostic, **LVS audit FAIL/NoMatch**. Fourteen primitives on both sides. Six reference LVSRES L0.6 W0.26 versus extracted four metal2 and two metal3 L0.6 W0.2. Reference additionally has NW/PW ports absent as separate extracted ports. Eight MOS pairs are marked mismatch; dimensions alone must not be taken as topology proof. No extraction diagnostics. Safe14099104530 SHA256`76d38343e3a35e5d5ada715372d3e1c987fc7a6b7a9ae8bff1e72d313d6145ad`; native14099039829 SHA256`b99ccd77e73bcf774597d9a67c030a1a89f18ae0a154e97f512805c354c6a563` remains cloud-only.

Next read-only cloud diagnosis **43561017033**, source`6650b1c1b558b319be5fb4d7904ed1d48dcf19cd`, branch`codex/sram-bitcell-endpoint-diagnosis`: exact original DB SHA256`c367b0565c64b00eedd2510d465d9c0d9cba64a7c2f79e4c04b5a9389bd49598`, mapping by identical named external resistor terminals where unambiguous and MOS body-port inspection. No class/width/geometry/port edits. Inspect result before versioned candidate reference correction; do not guess R0..R5 layers or waive NW/PW. Evidence:`docs/evidence/sram-original-bitcell-result-20261114.json`.

Live MBIST43558722004, fresh CRC deep repair43550440744, older routes43541234973/43538031308. Final timing, full current-chip LVS and serial PHY remain unaccepted.

---

# Fresh CRC candidate: preliminary timing available; deep repair running

Run43550440744 source`ecbcf43200413fc63844bbd20a7532f87af54216` reached deep setup repair. Safe artifact14099407422 SHA256`479b5d7f13488c2ba6a271058f8732cc391a9b5076b5da00a580445d01fbdc3f` contains post-global-route estimated STA, not final routed acceptance. Worst traced PCIe path is packet_accepted_o -> receive_ownership.head_last[2], slack -1.123ns. Do not infer a final improvement against older extracted-route measurements. Evidence:`docs/evidence/crc-order-preliminary-timing-20261114.json`. Wait for exact fresh deep-repaired handoff before antenna-aware routing/RC/STA; old instance ECOs must not be transplanted.

Bitcell43559617022, MBIST43558722004 and older physical candidates43541234973/43538031308 remain live at observation. Full PHY, current SRAM/chip LVS and final timing remain open. Native artifacts remain cloud-only.

---

# Latest archived SRAM RC audit — conservation and independent MOS topology passed

**43560070099 completed/success**, source`526c35599625cbcb093f0617d4aed09976f2d807`, safe artifact14099668660 SHA256`8e6818c2766f129b50d07f56b03427bcfd93e2c3187ebd55a9f3960fcd1f3c46`. Archived alternative DP8TSRAMDP256x16:37076MOS,237334R,1215822C. After resistance-component projection,155342capacitance pairs:0missing,0extra,0changed within1e-23F+1e-5relative tolerance. Independent schematic topology proof:37076devices,10272nets,88ports, exact net bijection/MOS edge multiset without body aliases. Positive resistor count explicitly checked. Evidence:`docs/evidence/archived-sram-rc-independent-result-20261114.json`.

This closes the **scoped connectivity/conservation audit only**, not physical value/corner calibration, junction geometry, Liberty, current vendor SRAM/chip binding or manufacturing approval. Native RC netlist SHA256`57f426ae891d1551d3d8d752d1dec75dacb3887b403509699b8f8d1785e930ad` remains in native artifact14099637041 cloud-only. Do not rerun extraction unchanged; reuse pinned native result for subsequent calibrated simulation work. The large extractor report was never downloaded locally.

Original bitcell43559617022 and full native MBIST43558722004 remain the active targeted tasks. Other physical runs43550440744,43541234973,43538031308 need continued exact polling. No current-chip LVS/timing/PHY closure claimed.

---

# Latest RC result — archived alternative extraction completed; independent audit running

**43534692191 completed/success**, source`2b9714c3c9c9ffb6e47313c7b96d09f74435dd98`, after extra32GiB cloud swap. It extracted the **archived alternative DP8TSRAMDP256x16**, not a current-chip vendor SRAM. Do not poll it as live or transfer its result to current-chip signoff. Native14099637041 SHA256`d937d7733a8fb8ffebed9ee61b6923c5d66c75284ed33e549a3493e8eb2e3404` stays cloud-only; large report14099432476 has not been downloaded locally.

Independent audit **43560070099**, source`526c35599625cbcb093f0617d4aed09976f2d807`, branch`codex/sram-full-rc-independent-audit`, observed completed. Hash-pinned native RC, prior CC artifact14082854262 and independent schematic14069436539. Tests37076MOS identities/parameters/ordered terminals, no resistor shorts or split reference nets, anchored passive networks and pair capacitance conservation; then reruns independent CC MOS topology proof, no body aliases. Original GDS identity required on both. Native payloads stay cloud-only; output JSON only. Inspect actual resistor count is positive as well as conservation result before accepting any RC-network claim. Even a pass does not qualify values/corners, junction/metal calibration, Liberty, present-chip binding or manufacturing. Evidence:`docs/evidence/archived-sram-rc-extraction-audit-launch-20261114.json`.

Original bitcell43559617022 remains live; MBIST43558722004 live. Other physical runs43550440744,43541234973,43538031308 still require fresh polling. Old flat43529228292 and strict fullmacro43553707234 are terminal failures, not pending.

---

# Latest native task — bounded original bitcell comparison running; old flat job timed out

**43559617022**, source`b75511764c3b131039325a05a142b98b9271e971`, branch`codex/sram-original-bitcell-lvs`, job132340149751, is live in native comparison. Script`scripts/diagnose_original_sram_bitcell.py` restores pinned original package and KLayout, applies the independently tested resistor no-merge switch correction, enables strict reference LVSRES L/W comparison, and isolates original CDL bitcell with only its subcircuit top name translated to GDS RM_IHPSG13_2P_BITKIT_CELL. It asserts6resistors+8MOS reference primitives, preserves dimensions/connections and runs native extraction with port audit. No layer guesses, width edits or class collapse. Result emits device pairing class/parameter metadata and port names, no netlist. Successful workflow means diagnosis complete, not LVS acceptance. Native artifacts stay cloud-only.

**43529228292 is now terminal/failure in both children.** Flat child132242493732 timed out at18000s, with no completed LVS DB/verdict. Do not poll/restart it as live or call it a pass. Safe derived14099936774 SHA256`5d0d13bd234c2b42ab4db0a2c0cde7fb2a35d65fa656581580199095d2a60678`; native14100130986 remains cloud-only. Evidence:`docs/evidence/sram-original-flat-timeout-20261114.json`.

Live long MBIST43558722004. Other live CAD:43550440744,43541234973,43538031308,43534692191. Re-poll exact handles before interpreting. Full manufacturing-ready objective remains open.

---

# Latest physical ownership — GDS cell names located; isolate bit cell next

**43559302585 succeeded**, source`85e28d9a82d1b3d7933a82847a24261417448d6c`, safe artifact14099392016 SHA256`d172c8821e7f34cf0972a34571991e3601a25f165b39f15f2bba6bec18c024c3`. Physical resistor owner leaves: lvsres_db_0x0283509a=M2 .6x.2; lvsres_db_0x02834b9a=M3 .6x.2; lvsres_db_0x0400b71a=M2 .6x.26; lvsres_db_0x263f099a=M3 .6x.24; lvsres_db_0x04007e9a=M1 .6x.26. GDS bit-cell names include **RM_IHPSG13_2P_BITKIT_CELL** and **RM_IHPSG13_2P_BITKIT_CELL_SUB**, whereas CDL uses **RM_IHPSG13_256x16_c2_2P_BITKIT_CELL**. Evidence:`docs/evidence/sram-resistor-physical-owners-20261114.json`.

Next concrete task: bounded native extraction/comparison of the original bit cell with explicit top-name handling and strict ports/primitive inventory, to establish the six resistor instances' physical layer correspondence before a versioned reference correction. Do not guess which R0..R5 maps to metal2/metal3 from aggregate counts. Do not collapse all resistor classes, relax widths, or adopt a layout-derived reference as independent signoff. Original GDS/CDL stay frozen; diagnostic controls remain distinct from acceptance. Existing native artifact14099740595 supplies exact original inputs and runtime. No new native job launched for this bit-cell task yet.

Full MBIST43558722004 remains live, five CAD handles as below. All native data stays cloud-only.

---

# Latest resistor ownership — three reference cells explain the remaining inventory

**43559140090 succeeded**, source`b0748dea6d3932fe7673d28c135b9ac43254f5ca`, safe artifact14099766973 SHA256`d02d8725ea0f3681d302f31fac420fd7a9b9c426ff92655ca88472f28d6c8d1f`. Original CDL recursive24822resistors and every child model resolve. Owners: RM_IHPSG13_256x16_c2_2P_BITKIT_CELL has6 direct resistors R0..R5,24576total; RSC_IHPSG13_MET2RES has1,16total; RSC_IHPSG13_MET3RES has1,192total. All useW2.6e-7,L6e-7. Matching metal1 RSC_IHPSG13_CDLYX1_DUMMY has1,38total and exact original geometry. **The other three CDL cell names have no exact GDS cell match**, so aggregate counts must not be used to invent instance/layer correspondences. No source correction or LVS acceptance yet.

Expanded cloud ownership diagnostic **43559302585**, source`85e28d9a82d1b3d7933a82847a24261417448d6c`, same branch`codex/sram-resistor-reference-owners`, queued at latest check. Exports original GDS cell-name and direct resistor-marker ownership counts plus recursive dimension summaries, no coordinates or connectivity. Inspect this before choosing a strict source correction or bounded local topology experiment. Evidence:`docs/evidence/sram-resistor-reference-owners-20261114.json`.

Full native MBIST43558722004 and physical CAD runs retain their exact handles below; re-poll before interpreting. Do not mark the chip or SRAM LVS accepted from these diagnostic successes.

---

# Latest SRAM diagnosis — original marker dimensions now match extraction one-to-one

**43558886103 diagnostic succeeded**, source`ea631c8c991a6f0538bb21f71f05e686886df462`, safe artifact14099676514 SHA256`63ebc8a05e3c7c1cb233c3147e2310d635389970e47098a8f8d0c1ae7e1e0e7a`. With strict unmerged resistors, original geometry exactly matches extracted dimension/count inventories: metal2=16384(.6x.2)+16(.6x.26); metal3=8192(.6x.2)+192(.6x.24). Reference has24784 generic LVSRES(.6x.26) instead.38 metal1 LVSRES(.6x.26) and all MOS dimension/count distributions agree. **This is not topology or full LVS proof**; no reference/GDS edits made. Evidence:`docs/evidence/sram-unmerged-dimension-diagnosis-20261114.json`.

Next cloud diagnosis **43559140090**, source`b0748dea6d3932fe7673d28c135b9ac43254f5ca`, branch`codex/sram-resistor-reference-owners`, observed completed. Reads original pinned CDL/GDS from native artifact only in cloud, counts original resistor ownership recursively, and reports cell names/instance parameter metadata plus per-cell original geometry dimensions. Exports no connectivity/netlist/geometry coordinates. Require original hierarchical resistor count24822 and no unresolved child models; use ownership evidence before proposing any reference/geometry correction. No class collapse or dimension tolerance waiver.

Long full MBIST **43558722004** and five CAD jobs remain the live handles from prior section; refresh before acting.

---

# Latest SRAM result — merge fix preserves70110 devices; top LVS still fails

**43553707234 is terminal/failure**, source`c077726eb378897ef2bf2b2e10bb8c6333195111`; do not poll it as live or rerun unchanged. Strict switch correction produced the expected **70110 recursive devices on both sides**, unchanged by selective flatten. Final audit:25Match,1NoMatch(top), no extraction diagnostics. Counts alone do not prove connectivity. No tolerances/ports/geometry/reference were waived. Evidence:`docs/evidence/sram-strict-merge-result-20261114.json`.

Diagnostic **43558886103**, source`ea631c8c991a6f0538bb21f71f05e686886df462`, branch`codex/sram-strict-merge-top-diagnosis`, observed in_progress. Reads only the exact new native database in cloud (artifact14099740595 SHA256`815d7babfb54232f89de61f45a6b1b2bc181cfe2c7d2158d5e521c1eb62cf4c7`, DB`dc81844b99e5b7b73898e6e8acebc71677d2d3934707b07c272d550696e22f0d`), exports bounded mismatch and hierarchy inventories, compares original metal2/metal3 marker polygon dimensions one-to-one now that resistors are unmerged. A diagnostic pass is not LVS acceptance. Inspect remaining class/width/topology causes; do not collapse metal classes or waive widths.

Full native MBIST continuation **43558722004** remains the live long run from the preceding section. Other live CAD:43550440744,43541234973,43538031308,43529228292(flat child),43534692191. All native data remains cloud-only.

---

# Latest continuation — full native MBIST continuation is running

**43558722004**, source`7d118a79f0bdfab6aa60b5bccb1cdb9dd836e2b8`, branch`codex/full-native-boot-continuation`, observed **in_progress**. Script`scripts/resume_full_native_boot.py` restores the real full-chip process from pinned native artifact14099590587 (SHA256`e6bebcf73c67bed72610b3d903ca91bd4037e665564659d926b059cfefd1c393`) and result14099221726 (SHA256`d6286a1a89a173c7aa8ca2818d6e9043cea026a3c4b6d6a52afa6c6c5901dcec`). Original netlist, firmware, PDK models, 3million-cycle bound and all MBIST/28-check gates remain. This is not a start-from-scratch run or memory preload.

Prerequisites passed:43557919707 matches the **3 original log lines through20000cycles** after separate-runner restore; this is bounded output agreement, not exhaustive state equivalence or full MBIST. Corrected43558336660 normal native exit0+completion+trace passed, while SIGTERM exit0 and SIGKILL exit-9 were correctly rejected as incomplete. Complete derived evidence:`docs/evidence/full-native-checkpoint-qualified-continuation-20261114.json`.

Long segment runs for up to10800s of simulation. On actual process exit, require original boot_checks with actual waitpid exit code, all MBIST/PCIe/28-check banners, no fatal/error and unchanged sources. On segment time budget, save the entire process and emit **checkpointed_pending_boot**, `completed_boot=false`, `passed=false`, `checkpoint_saved=true`; a green workflow in this state is NOT boot completion. Derived artifact`full-native-continuation-result-43558722004` contains result and log; native artifact`full-native-continuation-checkpoint-43558722004` remains cloud-only.

If checkpointed: pin exact next artifact IDs/hashes and resume its image_directory (images-RUNID) with exact runtime/file identity. The next harness must accept the validated checkpoint_saved state instead of requiring passed=true, bind the new parent source/run, and use the new image_directory, preserving all final gates. Do not mistakenly restart from the old10000cycle checkpoint. Current native script is first-segment-specific and must be adapted with those pins for the next segment. If completed_boot=true, independently inspect final report/log and provenance before calling this scoped functional boot closed; no SDF, serial PHY, memory fault qualification or manufacturing acceptance follows.

Six physical CAD handles remain as in the re-polled snapshot. Continue exact live jobs; original43558139164 is terminal/failure (normal child passed, obsolete SIGTERM -15 expectation failed). Native data stays cloud-only.

---

# Latest correction — SIGTERM may return zero; completion evidence required

Exit-control run43558139164 SIGTERM child **failed** its assumed -15 expectation: the real restored VVP returned **0** after SIGTERM. Subreaper/waitpid worked; this is why exit0 alone is insufficient. The control failed closed, not a chip pass. Evidence: `docs/evidence/native-vvp-sigterm-zero-exit-20261114.json`, safe artifact14099185767 SHA256`6985e162d1562918fbeb5da4db5bc29d57f876287f188c9fe67e3a8ce499a26d`.

Corrected controls **43558336660**, source`292a3313f7c0fca20c3fa65cc5de910003083162`, branch`codex/native-checkpoint-exit-status`, dispatched/queued at observation: normal requires native exit0, completion marker AND identical full trace; SIGTERM/SIGKILL require missing completion and rejected simulation; SIGKILL additionally requires native -9. Do not replace this with an exit-code-only gate. Original full-chip boot_checks already requires MBIST/PCIe/28-check banners and no fatal messages; preserve those checks unchanged in long continuation.

**43557919707 full-chip prefix is still live** in dump stage. Require its successful restore/equality plus corrected exit controls before long native MBIST continuation. Previous normal exit-control child132335564397 was still live; do not cancel or mislabel it. All native payloads remain cloud-only; no manufacturing signoff.

---

# Latest continuation — native exit-status controls running

Full-chip prefix qualification **43557919707** is still live in dump stage; do not restart. A second prerequisite **43558139164**, source `241ecd5640abc2a2f4e83f139faf76924ff858f9`, branch `codex/native-checkpoint-exit-status`, tests actual restored native process exit collection. Python becomes a child subreaper, checks parent identity, and uses waitpid: normal native execution must exit0 with exact trace; forced SIGTERM must be observed as -15 and rejected as successful simulation. Both jobs remain pending at this observation. See `docs/evidence/native-checkpoint-exit-controls-launch-20261114.json`.

Next: inspect both exact run results. Only after the full-chip prefix and exit-status controls pass, start long continuation from the pinned real full-chip checkpoint, with strict runtime/CPU/mapped-file/source identity, full memory tests and original28-check firmware gates. Use actual native exit0 plus original boot_checks; a text PASS or successfully saved chunk alone is insufficient. Retain process images only in cloud. All six CAD handles in the previous snapshot were also confirmed live this turn.

---

# Latest checkpoint — pinned native IHP restore passed; full-chip prefix running

**43557409470 completed/success**, source `85aeb1e224eca0cf2d1f5008da9e8ed59e4d199d`. Pinned original OSS CAD suite ARM package and untouched native IHP flip-flop were used in the 50-million-cycle four-state/delayed-event comparison. All502 lines byte-identical, trace SHA256`c82f1f1fa067c864f09fbec3f5f30b61bdf42d2e74b7a003e95f3de84f85b6a3`. Strict CPU/runtime and mapped-file checks preserved. This is not full-chip MBIST or silicon acceptance. See `docs/evidence/native-ihp-checkpoint-result-20261114.json`.

**43557919707**, source `104cfcfbe16b589bf3ee5df1b51d0374c1d19eb2`, branch`codex/full-native-checkpoint-prefix`, observed **in_progress**. Script`scripts/check_full_native_checkpoint.py` downloads pinned original recovery artifact14097721346 only in cloud, reconstructs exact original testbench/firmware/netlist/models with input hashes and flags, recompiles using pinned ARM suite, and runs the unchanged full-chip workload. It compares first20000cycles uninterrupted against a process saved after10000cycles and restored on a separate runner. No preload/shortened MBIST/RTL mutation. This test deliberately stops after prefix comparison; do not mistake it for full MBIST/boot pass. If passed, qualify/use the preserved process checkpoint for multi-job continuation through the original final MBIST and28-check firmware gates, maintaining exact runtime/file identity. Process images/netlist/GDS/waveforms stay cloud-only.

Six CAD handles were re-polled in the evidence snapshot. Continue exact live handles, no blind reruns. Full serial PHY, final timing, current SRAM/chip LVS, qualified characterization/RC and manufacturing acceptance remain open.

---

# Latest continuation — native model controls pass on both architectures

Run **43557240046** at `8a4f8605f4e6ac501f111df5ccbb0ea868bdd514` passed x86 and ARM native flip-flop and mapped SCRUB positive/negative controls using pinned OSS CAD suite 2026-08-04. Untouched locked PDK sources verified. This is not SRAM or full MBIST completion. See `docs/evidence/native-ihp-architecture-controls-20261114.json` for complete derived results, artifact identities and fresh CAD status snapshot.

Next **43557409470** at `85aeb1e224eca0cf2d1f5008da9e8ed59e4d199d`, branch `codex/native-ihp-arm-checkpoint-proof`, observed in_progress: native IHP flip-flop added to the 50-million-cycle X/Z and delayed-event cross-runner checkpoint control, using the pinned original OSS suite ARM package. Checks every file mapped by the native VVP process before restore, exact kernel/runtime identity and strict CPU compatibility; requires full byte-identical output. No full-chip result yet. If passed, qualify real SRAM/full mapped workload before resumable MBIST deployment. Native artifacts stay cloud-only.

Six ongoing CAD handles were re-polled; read exact snapshot and refresh. No duplicated CAD jobs or waived signoff gates.

---

# Latest checkpoint — ARM restore equivalence passed; native model qualification launched

Run **43556397817** passed both dump and separate-runner restore with strict CPU/runtime checks. All 502 output lines of the 50-million-cycle four-state/delayed-event control match the uninterrupted baseline, SHA256 `972d25b21a2ed9247967e9597a35e0a48f04dfe4e7203a7c02fcae5ea39ad160`. This uses apt Icarus and does **not** establish native IHP/full MBIST acceptance. Evidence: `docs/evidence/native-vvp-arm-checkpoint-result-20261114.json`. Process images remain cloud-only.

Next workflow dispatched on `codex/native-arm-model-qualification`, source `8a4f8605f4e6ac501f111df5ccbb0ea868bdd514`: pinned original OSS CAD suite 2026-08-04 on ARM and x86, untouched model-lock preparation, native flip-flop compatibility plus mapped SCRUB positive and historical failing negative controls. Resolve exact run handle by branch/source, inspect both results, then qualify checkpoint equivalence on the real native workload before full MBIST. No simulator version relaxation or MBIST bypass.

Six CAD runs rechecked live:43553707234,43550440744,43541234973,43538031308,43529228292(flat child),43534692191. Their results remain pending.

---

# Latest checkpoint result — dump works, x86 cross-runner restore rejected

Run **43556082535** at source `0463c149ea3a7e50c1024d31532a064bc815ce1f` completed/failure. Native VVP dump and kernel preflight succeeded. Separate-runner restore failed the preserved strict CPU check: **unsupported xfeatures0xe0** on AMD EPYC7763. Exact runtime libraries and kernel matched. No output equivalence, full MBIST completion or chip acceptance. Do not use `--cpu-cap=none` or otherwise suppress this failure.

New capability probe **43556397817**, source `3f2c7fa6209ea5b4be64c2d6a969f8ee433455ee`, branch `codex/native-vvp-arm-checkpoint-proof`, observed **in_progress**. Only runner labels changed to supported `ubuntu-24.04-arm`; four-state delayed-event test and strict dump/restore validation remain. A success would still require original native model/simulator qualification before a real MBIST run; no architecture substitution has been accepted.

Evidence and earlier harness/build failures: `docs/evidence/native-vvp-x86-checkpoint-result-20261114.json`. Safe derived artifacts14098840762/14098940303 are authenticated there; process images remain cloud-only. Six physical CAD handles below still need exact polling.

---

# Latest experiment — native simulator process checkpoint across cloud jobs

Capability run **43555672343**, source `78e99d71c98793c35eeaabf0e764beaf786aa065`, branch `codex/native-vvp-cloud-checkpoint-proof`, observed **in_progress**. It builds official CRIU v4.3.1 at `3ce556b7e8291c1bfdca974962f6282d7802b69f` on the cloud runner. Initial43555513918 failed at apt because criu had no installation candidate; no capability test ran there.

Purpose: determine whether a complete VVP process, including pending events and four-state state, can be moved between GitHub jobs to overcome the20000s native MBIST timeout. A synthetic trace with X/Z, nonblocking updates and delayed events must be byte-identical to an uninterrupted run. Both dump and separate-runner restore must pass, with exact runtime/kernel identity and `--cpu-cap=all`. No weakened CPU checks, RAM-only preload, MBIST shortcut or chip acceptance. Even a successful small test still requires qualification on the exact native PDK workload.

Evidence/next steps: `docs/evidence/native-vvp-checkpoint-capability-launch-20261114.json`. Native checkpoint payloads remain in cloud. Do not download them locally. The six CAD handles below were re-polled; use the JSON snapshot then refresh before acting.

---

# Latest continuation — MBIST timeout and CDR transition-margin diagnosis

Observed 2026-11-14T04:08:40.137899+00:00. **MBIST/boot43516903518 is terminal/failure**, not live. Native vvp exited124 at20000.064s, with progress through1,530,000cycles; UART startup at~1,460,000 and six flash frames by~1,480,000. No native PASS. The RTL-preparation exit0/28checks belongs to a different run phase and does not close MBIST. Filtered cloud diagnosis43554935242 succeeded; see `docs/evidence/full-mbist-native-timeout-20261114.json`. Native recovery artifact14097721346 is pinned there and must remain cloud-only. Do not repeat the same timeout blindly; investigate runtime/MBIST startup and preserve full native model semantics and coverage in any acceleration.

**CDR conditional diagnosis43554632921 succeeded** (source39887bdeaa187c80e5340b5bb5bb23772784d19c), not electrical acceptance. In each XOR-load candidate, transition-group A sampler has0/381 below100mV at diagnostic phases, but buffer A has347/381(nx2) or349/381(nx3) below100mV; X has381/381. This prioritizes sampler-to-buffer level shifting/settling and actual selector timing over another XOR-area sweep. Corrected B expected bit accounts for the next falling edge; initial diagnosis43554431443 is superseded. Full original acceptance gates remain untouched. See `docs/evidence/cdr-xor-conditional-signals-20261114.json`. Next audit actual selector topology before inferring a polarity or test expectation fix.

Six native handles last observed live: strict SRAM merge fix43553707234, fresh CRC physical43550440744, five-driver hold/antenna43541234973, five-driver antenna43538031308, original DP flat43529228292, alternative SRAM RC43534692191. Re-poll exact handles. No manufacturing-ready claim.

---

# Latest correction — resistor merge switches verified; full macro running

Native controls **43553545114 passed all 16 cases**. Original Ruby RES2 merges serial and parallel pairs even with both requested switches off; the two-line correction honors all four switch combinations. Controls instantiate the actual Ruby class in native resistor graphs with boundary pins; no unsupported getter or Python imitation. Original harness failures 43553195656/43553342992 are terminal and superseded.

Full frozen DP SRAM candidate **43553707234**, source `c077726eb378897ef2bf2b2e10bb8c6333195111`, branch `codex/sram-strict-resistor-merge-fix`, is **in_progress** at this observation. It pins successful control artifact14096828657 SHA256 `b58b9142d77cb2f5b429ea23df5854b5e65f5bb19158561d635f9be9872214da`, verifies the original custom_devices source, and adds only the tested two-line switch correction. Existing strict W/L, ports and extraction checks remain unchanged. The new expected 70110 recursive-device guard is derived from 62046+8064 formerly merged pairs and must be verified by the run; it is not yet a measured macro result. Other vendor width/model/hierarchy issues remain open.

Result and provenance: `docs/evidence/sram-resistor-merge-switch-controls-20261114.json`. Reproducible control source is now `scripts/check_sram_resistor_merge_switches.py` on integration. Experimental workflow remains on its own branch. No native files or local checkout created.

Continue the six older live runs: fresh CRC physical43550440744, five-driver hold/antenna43541234973, five-driver antenna43538031308, original DP flat43529228292, alternative SRAM RC43534692191, MBIST/boot43516903518. Four-driver43528773096 is terminal/rejected, not live. Poll before acting.

---

# Latest terminal result — four-driver antenna candidate rejected

Run **43528773096** completed/failure: **DRC=0, antenna nets/pins=1/1**, slow setup **1367** (WNS -2.070215 ns, TNS -478.996881 ns), slow hold3, typical hold11, fast hold**82** (WNS -0.319650 ns). Electrical/fanout gates also fail. Evidence `docs/evidence/cut10j-four-driver-antenna-result-20261114.json`. Do not adopt this candidate or call it timing closure.

SRAM isolated Ruby control run **43553195656** failed before testing flags; captured subprocess stderr had been hidden by the harness. Diagnostic retry **43553342992**, source `1b412c55021425ec17be2601548e81bcb5c1f1d7`, branch `codex/sram-resistor-merge-switch-controls`, preserves native stdout/stderr in a derived JSON and was live at the latest check. Diagnose that failure before applying the proposed merge-switch correction. No pass yet.

---

# Latest investigation — original resistor geometry and ignored merge switches

Observed 2026-11-14T03:45:29.353822+00:00. Cloud geometry check **43552896584** independently confirms metal2/metal3 width differences in the frozen original SRAM GDS. Metal3 polygon count/dimensions match extraction; metal2 polygon count does not (16400 versus 8336 normalized devices), while width-binned total lengths agree. Failed direct-count test **43552738032** is preserved; aggregate agreement is not connectivity proof.

The exact frozen `RES2` class does **not** bind `supports_serial_combination`/`supports_parallel_combination` to requested switches. Thus prior `no_series_res=true` should not be interpreted as proof of no merge during `combine_devices`. Upstream PR1121 (still open, head `3df647ebe53439ae41d56a1e9c2b38003ba2124d`) contains a two-line fix and requires explicit metal-layer identity for LVSRES.

Isolated cloud controls **43553195656**, source `63876fda9e588ae2a7261f1ce85ee89b189c16ca`, branch `codex/sram-resistor-merge-switch-controls`, observed **completed**. These execute the original/fixed Ruby class for all four switch combinations, then native two-resistor serial/parallel controls (16 cases). If passed, integrate only the tested switch correction into an experimental macro flow, recompute unmerged primitive counts, and retain strict dimension/topology/port checks. The frozen GDS/CDL discrepancy remains separate. No class collapse, dimension waiver or physical acceptance.

Evidence: `docs/evidence/sram-original-geometry-and-merge-switches-20261114.json`. Existing native job statuses are pinned there; all seven other runs were re-polled in this continuation. Native files remain cloud-only.

---

# Latest result — hierarchy-expanded SRAM inventory

Cloud diagnostic [43552140757](https://github.com/Melihakbulut221/nssoc/actions/runs/43552140757) completed successfully at source `39512ef05cd88123d0e1d46554ce8067f3dd4414`. This supersedes the pending diagnostic below; it is **not** LVS acceptance.

Both full hierarchies contain **62,046** primitive devices. All MOS class/L/W/count distributions match exactly at 12-digit rounding. Inventory differences are restricted to metal resistor classes and widths: extracted metal2/metal3 include W=0.20/0.24 um while reference LVSRES uses W=0.26 um. Equal MOS inventory does not establish topology or supply connectivity. No GDS/CDL dimensions, tolerances, net aliases or acceptance gates were changed.

Evidence: `docs/evidence/sram-hierarchy-dimension-inventory-20261114.json` (artifact 14095939669, SHA256 `3a8436cfdfb54c22567d523850ff21a0574f8fd4e6225c64ed7a15bcedc147c4`). Next isolate model-reader identity and actual marker/reference mismatch before any source correction; require strict full LVS, negative controls and DRC for a candidate. Continue monitoring the exact active physical/MBIST/flat-LVS/RC handles below. No native data was downloaded to disk.

---

# Latest continuation — SRAM dimension diagnosis and rejected CDR screens

Observed 2026-11-14T03:32:49.878654+00:00. This section supersedes older live-status claims below.

- Current DP SRAM selective flatten run **43543201489 failed**: 25 Match, one top NoMatch; no Skipped, no extraction diagnostics. Hierarchy changes did not close LVS.
- Bounded top diagnosis **43551681909 succeeded** as a diagnostic, not LVS acceptance. Paired resistor samples show metal3 width **0.24 um versus reference 0.26 um**. Direct top inventories have different child boundaries and are not evidence of missing transistors. See `docs/evidence/sram-top-dimension-diagnosis-20261114.json`.
- Cloud hierarchy-expanded inventory diagnostic **43552140757**, source `39512ef05cd88123d0e1d46554ce8067f3dd4414`, branch `codex/sram-selective-flatten-top-diagnosis`, is completed at this observation. It reads the exact pinned selective-flatten database; no new extraction, net aliases, tolerance relaxation, or device omission. Inspect the resulting derived JSON before choosing a correction.
- CDR XOR nx=2 and nx=3 run **43542889935 failed electrical acceptance**. Both native simulations exited zero, device limits and phase passed, but X comparison has 386/392 wrong-sign samples and sampler A/C/D margins fail. No layout accepted. See `docs/evidence/cdr-xor-load-reduction-result-20261114.json`. Next diagnose data-path polarity/settling and sampler margins rather than repeat this load sweep.
- Fresh CRC physical **43550440744**, old-layout route candidates **43541234973 / 43538031308 / 43528773096**, DP flat LVS **43529228292**, alternative SRAM RC **43534692191**, full MBIST/boot **43516903518** were still in progress on this continuation. Poll exact handles; do not restart live jobs. Fresh CRC run remains probe-only and needs its own downstream detailed route/RC/STA after successful handoff.

All native artifacts remain in cloud. Full PHY, final timing, full current SRAM/chip LVS and manufacturing acceptance remain open.

---

# Latest continuation update — CRC proof and fresh physical candidate

This update supersedes the PCIe proof/live-run entries below. Other native jobs must still be re-polled by their exact handles. The full manufacturing-ready objective remains open; all native work stays in cloud.

- **CRC proof passed:** [43549353231](https://github.com/Melihakbulut221/nssoc/actions/runs/43549353231), source `0e86c8c8ec9db5838ae371821e6c047a6825d554`. Capacity 8: 551/551 points; capacity 32: 1351/1351, both directions. Proof-only semantic wire `fold_ordered_word=transmit_order(fold_word,fold_msb_first)` in the baseline provided 32 additional obligations, all proven. No assumed relation or output mask. Scope is Yosys async2sync/undef induction plus previously completed packet/reset simulations, not whole-chip or physical signoff. See `docs/evidence/pcie-crc-order-state-relation-result-20261114.json`.
- **Fault controls passed:** [43549920774](https://github.com/Melihakbulut221/nssoc/actions/runs/43549920774), source `81f6fec51e315d0bfa2b3188576715716dc9e857`. CRC bit and output bit corruption rejected in both directions (capacity 8); rc=1 and final unproven-equivalence assertion, no timeout acceptance. See `docs/evidence/pcie-crc-state-relation-negative-result-20261114.json`.
- **Fresh physical run LIVE:** [43550440744](https://github.com/Melihakbulut221/nssoc/actions/runs/43550440744), source `ecbcf43200413fc63844bbd20a7532f87af54216`, branch `codex/crc-order-fresh-physical`, job `132311448151`. Last observed CAD runtime setup. Uses exactly candidate RTL SHA256 `51aff3ebbbf80d251b4a3ebaa3c8da744d1c0e67fb3189f2cb947af1d15219ce`, all original cut10j knobs, fresh RTL simulation and synthesis through placement/CTS/global route and setup/hold repair. Emits a native `route-handoff-r_cut10j_td_d68-43550440744` artifact if successful. **This workflow contains only the probe job.** After completion, bind its exact handoff artifact/hash and run antenna-aware detailed routing, fresh RC extraction and all-corner STA. Never reuse old cut10j layout as evidence for new RTL. Existing fixed instance-name ECOs are from the old netlist and must not be blindly applied to this new synthesis.
- Candidate RTL remains **unmerged** in `timing/combined`; require fresh physical evaluation before adoption. Original failed proof runs 43543271489 (structural) and 43546370331 (deeper bitwise) are terminal timeouts, no longer live; their reports remain preserved.
- Initial physical dispatch at source `870322cd742c2ff872f39905eeaa5fb014aa30ac` was rejected HTTP422 because a header split matched the `pcie_jobs` input. No CAD job started. Corrected top-level split produced the live source above.

Still-live native handles at this update: SRAM selective flatten 43543201489; CDR actual-multiplicity XOR load screens 43542889935; old-layout hold/antenna candidate 43541234973; five-driver antenna 43538031308; four-driver antenna 43528773096; current DP flat LVS 43529228292 (deep child already failed); archived alternative SRAM RC 43534692191; native full MBIST/boot 43516903518. Re-poll before acting. No result here closes full PHY, current-chip LVS, final timing, qualified RC/Liberty, integrated pad/DFT, or production review.

---

# Cloud continuation — 2026-11-14

Observed at **2026-11-14T01:58:10.696260+00:00** on integration branch **`timing/combined`**.
Repository: https://github.com/Melihakbulut221/nssoc
This is a resume checkpoint, not a chip signoff. The manufacturing-ready goal remains open.
All source edits and native computations are in GitHub. Do not recreate a local CAD checkout or download native geometry, SPICE, netlists or waveforms. Read source and vetted derived summaries through API in RAM; filter mixed artifacts in cloud first.

## Resume these exact jobs

| Run | Scope | Observed status | Source |
|---|---|---|---|
| [43543201489](https://github.com/Melihakbulut221/nssoc/actions/runs/43543201489) | Current DP SRAM: six-cell symmetric hierarchy flattening | in_progress / pending | `220c52b2872ad4350d1308adf2b2d99b3802d9cc` |
| [43543271489](https://github.com/Melihakbulut221/nssoc/actions/runs/43543271489) | PCIe CRC retiming: forward structural plus sequential proof | in_progress / pending | `be7609b53929c286ee31537a333c226934b2d727` |
| [43542889935](https://github.com/Melihakbulut221/nssoc/actions/runs/43542889935) | CDR XOR input area nx=2/nx=3 with corrected current-density binding | in_progress / pending | `225363749ed24b5b9e452ab39af757376f21db00` |
| [43541234973](https://github.com/Melihakbulut221/nssoc/actions/runs/43541234973) | Five-driver plus isolated Ethernet RX bank6 A_ADDR6 hold ECO | in_progress / pending | `f83a2f29afc00626688942b2ce663a4b844eeb3c` |
| [43538031308](https://github.com/Melihakbulut221/nssoc/actions/runs/43538031308) | Five-driver plus antenna repair | in_progress / pending | `6c5d8de09c0fd88b0daa57e669b3b6fc2bf67bbb` |
| [43528773096](https://github.com/Melihakbulut221/nssoc/actions/runs/43528773096) | Four-driver plus antenna repair | in_progress / pending | `e8d24c8d92dbec192db84115d8c8110f82a1812c` |
| [43529228292](https://github.com/Melihakbulut221/nssoc/actions/runs/43529228292) | Current DP SRAM normalized deep/flat comparison; deep failed, flat pending | in_progress / pending | `13d88396f2be3a7823981be6ffe5e67df7b9ed32` |
| [43534692191](https://github.com/Melihakbulut221/nssoc/actions/runs/43534692191) | Archived alternative DP SRAM RC extraction with 32GiB swap | in_progress / pending | `2b9714c3c9c9ffb6e47313c7b96d09f74435dd98` |
| [43516903518](https://github.com/Melihakbulut221/nssoc/actions/runs/43516903518) | Full native system/Ethernet MBIST and firmware boot | in_progress / pending | `3fd0fded2d874efa0109d8558a213380de1f36a7` |

Poll exact handles again before acting; these observations will age. Do not restart a live run on observation timeout. Inspect failed steps and derived reports before retrying. No pending result in this table is a pass.

## Latest findings and next decisions

- **SRAM:** run 43541320172 passed the scoped metal1 model/width/length/A-Z-open controls, then failed the full current DP macro: 25 Match, 6 NoMatch, 1 Skipped; both sides 62,046 primitive devices. The isolated leaf still lacks physical VDD/VSS ports and is not full-LVS accepted. The next hierarchy test preserves all primitives and the strict final port/extraction audit. See [controlled result](docs/evidence/sram-metal1-controlled-macro-result-20261114.json) and [open-control diagnosis](docs/evidence/sram-metal1-open-control-diagnosis-20261114.json). Do not waive dimensions, supply opens, unmatched ports or extraction warnings to obtain a pass. The older full flat job is still a separate pending comparison.
- **Ethernet hold:** full reports from rejected four-driver run 43505737740 show RX bank6 `A_ADDR[6]` setup +5.231030 ns in slow corner and hold -0.427385 ns in fast corner. The new candidate inserts three noninverting delay cells only on that endpoint branch, with Liberty identity, power and contracted-connectivity checks, then fresh routing/RC/STA. The source name had to be resolved from escaped ODB hierarchy; prior parser/name failures are preserved. These old path margins do not predict acceptance of the new layout. See [budget](docs/evidence/ethernet-rx-hold-budget-investigation-20261114.json) and [candidate](docs/evidence/cut10j-rx6-hold3-antenna-launch-20261114.json).
- **PCIe CRC RTL:** candidate byte-order retiming remains **unmerged**. Packet simulations and mutation tests passed, but both full mutual proof attempts timed out at 1,800 s. The cleaned proof left 402/1,178 unproven cells at capacities 8/32 before induction; no completed counterexample or proof. The new structural method still requires every remaining equivalence cell proven. See [proof record](docs/evidence/pcie-crc-order-cleaned-proof-timeout-20261114.json). Require successful mutual proof, negative controls and fresh physical timing before accepting the RTL candidate.
- **CDR:** sampled diagnostics found late/weak A/C-buffer transitions and six `nx=4` XOR base loads on each `nx=2` buffer collector. Two circuit-screen variants reduce only 24 XOR device `nx` parameters. Initial run 43542698325 was cancelled because the legacy checker used original emitter multiplicity for current density. Replacement 43542889935 uses the actual candidate binding and unchanged 3 mA/emitter limit. Existing interconnect RC is retained only for screening; a good waveform would still require new layout/extraction, numerical agreement and full operating-condition checks. See [response](docs/evidence/cdr-lowz8-buffer-response-20261114.json) and [corrected screen](docs/evidence/cdr-lowz8-xor-load-reduction-launch-20261114.json).
- **RC:** the swap-extended extraction is for an **archived alternative** DP8TSRAMDP256x16, not either vendor SRAM in the current chip. Apply independent topology/RC audit if it completes; never transfer its result to the current macro or claim qualified min/max RC.
- **Native MBIST:** the current full run includes system and Ethernet memories plus firmware handover; PCIe is idle and there is no SDF. Do not call it serial PHY or routed-timing proof.

## Completion remains unproven

Keep the full scope in [product acceptance](docs/92-product-acceptance.md), [second audit](docs/96-second-audit-closure.md) and the README. Outstanding work includes final setup/hold/electrical closure on the same routed chip, full current SRAM and chip LVS, qualified SRAM characterization/Liberty and min/max RC, full serial Gen3 x4 PHY/control/clock integration, integrated padframe/DFT and physical verification, manufacturing review, and the required silicon/radiation qualification. Historical pilot/core passes and scoped diagnostics do not close these requirements.

The previous checkpoint is retained below as history; its live-run statements and dates are not current.

---

# Claude handoff — terminal status update, 2026-11-04

Read [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md) first for the detailed Turkish handover, exact sources, failures, measurements and next steps. Machine-readable selected evidence: [CLAUDE_HANDOFF_EVIDENCE.json](CLAUDE_HANDOFF_EVIDENCE.json).

At 2026-11-04 02:07 UTC, runs 41699812301, 41733225660, 41734419971 and corrected handoff 41739641054 were all completed/failure. No queued/in-progress runs were returned by the API. The old v360 live-status text below is historical.

- Route: supervisor memory-sample bounded-window failure; last successful RSS below limit. Route did not finish.
- Actual650 N1/N2: native transients exited zero; data/device/phase electrical gates failed.
- Handoff: original1691 scope correction passed its former failure point; DEF single-wire-clause parser now fails in prepare. Logical diode supplies passed; physical continuity unverified.
- Full serial PHY, completed mainchip routing, final timing and production acceptance remain open.

Documentation handoff only, not a new native experiment or v361 monitor rebuild. Native assets remain cloud-only. No CAD/simulation job dispatched for this handoff.

---

## Historical v360 checkpoint (preserved verbatim below)

# Cloud continuation — checkpoint v360

Updated: 2026-11-03T23:21:08.981491+00:00

## Native route-class restoration and diode-inclusive netlist handoff

New source50f1ebf8d1c940abff985f971aeae670eeb4a9ec on codex/mainchip-postroute-handoff implements actual original full-chip class restoration, diode logical-supply audit, physical netlist export, fresh-library read/link and complete instance/pin/boundary incidence comparison. The old zero-diode route12 adapter and original timing gates remain unchanged. Source controls41738123187 passed, including six rejection cases; their1190-byte artifact13280920159 was authenticated in RAM.

Native job41738314531/release433325391 is the first real execution. Its initial input is the existing completed route41440285882, which still has known physical violations. It is a qualification of the handoff implementation, not the new full64 result and not signoff. It invokes no new routing. The complete real netlist comparison must pass, then native diode/port mutations must be rejected. Native failure must be diagnosed without silently omitting diodes/physical cells.

Current full64 route41699812301 and actual650 N1/N2 runs41733225660/41734419971 retain their exact handles. If the handoff implementation passes, acquire the completed full64 output with exact source/asset/member pins and apply it there before fresh RC/original-clock timing. Do not use the old zero-diode netlist. Original global class restoration and actual physical diode PG connectivity are distinct; the new logical supply check does not establish metal continuity or LVS.

The restored PLL terminal map and distinction between failed RHI120 and olderPLL845 captures remain documented in docs/pcie-cdr-pll-connection-audit-20261104.md. Current650 benches still use an external clock and do not prove a recovered-clock loop.


Observed 2026-11-03T23:21:08.981491+00:00:
- 41699812301: in_progress/None
- 41733225660: in_progress/None
- 41734419971: in_progress/None
- 41738123187: completed/success
- 41738314531: in_progress/None


## History and execution
Previous actual route and failure handoff:
https://github.com/Melihakbulut221/nssoc/blob/1725fa8d43b6befeb966504d5aa5af8f1e9c69b0/CLOUD_RESUME.md
All earlier sources, complete reports and failed runs remain preserved.
All native CAD/geometry/runtime/electrical payloads stay cloud-only. The local
workspace is empty; source and derived-text API coordination uses RAM.
The8-hour monitor remains read-only with automatic_native_dispatch=false.
Poll existing exact handles; do not restart on observation timeouts.
Full serialPHY, completed mainchip routing and final setup/hold must all
pass real complete verification before the overall goal is complete.
