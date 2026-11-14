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
