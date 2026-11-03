# Cloud continuation — checkpoint v345

Updated: 2026-11-03T18:46:19.681320+00:00




## Current continuation: fresh650 metal/via RC passes; new bounded-region engine compiled and in actual-chip qualification

Actual650 fresh metal/via RC41693055344/sourcef4f7723f935b80fcd5ade5b7f159e82e7845d7ae on codex/cdr-mos650-metal-rc SUCCEEDED. It measured28449 resistors and18299 capacitors, retains1428 logical/1278 physical anchors, and passed all13 original raw native corruption controls. Complete raw topology/values/attachments were audited. Release433064135 preserves all native evidence. This closes metal/via extraction for this exact candidate, not gate-poly RC, MIM composition, electrical acceptance or full PEX.

Bounded-region engine build41688147573/source6cae8ce19c56bb597b9edab02c7d21b14b099eb2 SUCCEEDED. Actual full compile1803.211s; Tcl/Python interface checks passed; no terminal errors or OOM. New ELF108948904 bytes SHA256e12b1c70296c119c31ed5b1a7f739904d06b3c86cd703eebee25dbcc9c357431, all104 runtime dependencies unchanged. This is NOT a measured routing memory improvement.

Independent actual-chip qualification source controls41694933685 PASSED on source5518d9fa75b505848e2c6a5c7d1b4a0ca9c011af, branchcodex/mainchip-guide-tiled-roundtrip. Actual qualification41695305770/release433078096 dispatched on SAME exact source, retaining full143820nets/154480instances/1691protected clock records and original complete DRT/antenna comparison. Follow its authoritative snapshot below; no duplicate. If successful, bind its actual new ELF/qualification evidence into the original full64 routing workflow, run independent source controls and then one full route. Prior41552715162 remains a preserved11GiB guard failure; never relabel92referenceDRT or21antenna nets27violations as signoff.

Gate-model diagnostic41695546092/source12f87169a29887cbae7edb1def1dc91ddeb92819/release433079603 SUCCEEDED. Frozen ordinary MOS model is PSP103, RF alternative PSPNQS103 with explicit RF gate parameters; actual physical200MOS use rfmode0 and50 shared contact groups. One top contact feeding a long poly stem is not represented by current metal RC. Full actual model declarations and technology report preserved. Binary-decoding41694626851 and Latin1 annotation41695152558 failures remain failures in immutable releases and root logs.

NEXT PHY: inspect native gate AC characterization on codex/cdr-mos650-gate-ac (exact handle in snapshot/monitor), including each actual W/L/AS/AD/PS/PD tuple, both QS/RF modes, explicitpre_layout0, native model readback and complex impedance over1MHz-10GHz. This only informs physical distributed poly/contact composition; it does not accept full PHY. Resolve compact-model overlap, derive actual physical gate network, complete650 MIM/intrinsic composition and preserve original loaded headroom/phase/current/sampling gates.

All native data remains GitHub-only; local workspace empty. Existing8hour monitor remains read-only, automatic_native_dispatch=false. FullserialGen3x4, mainchip fullroute and finalsetup/hold remain unaccepted.

Observed 2026-11-03T18:46:19.681320+00:00:
- 41688147573: completed/success
- 41693055344: completed/success
- 41694626851: completed/failure
- 41694933685: completed/success
- 41695152558: completed/failure
- 41695305770: in_progress/None
- 41695546092: completed/success
- 41696724132: in_progress/None


## Current continuation: complete actual650 wire topology passes; retain physical identity under LVS permutations

Actual650 wire extraction41690238100/source9986cd07106b20805a74656ac5292e9a70b760e5 on codex/cdr-mos650-wires SUCCEEDED. Native-wires126106937185 generated113 geometrically connected metal/via components,114 electrical partitions, all650 unique physical device instances,2046 terminals and25 ports. All13 complete conductor/via layer unions match the input GDS after serialization; every anchor probes to its actual native LVS owner and wire component. There are1428 logical anchors,1278 exact distinct geometric points after deduplication; do not substitute historical500-layout counts. All5 actual corrupted-binding controls rejected.

The exact new GDS and both650 LVS databases were authenticated and rebound to the independent full200-MOS/450-other-device reference. Non-MOS source pins were recovered by exact drawing signatures from qualified prior source-pin records; actual new MOS units were regenerated with the pinned IHP PCell runtime and matched by complete primitive drawing before recovering annotations. Old500 wire RC was not reused. Current source, all native results and failures stay in release433047733, native-wires.tar.gz70422645 bytes SHA25625ea88486294dff3236a52fd41db2a57e6410c410d7a999c45e6f6b22e3d16e8. Receipt: docs/evidence/mos650-wires-41690238100-receipt.json.

Actual200 gate terminal/access-poly/contact geometries are retained, forming50 physical contact groups:8 groups of1 unit,34 of4,4 of6 and4 of8. This is not gate-poly RC. Shared metal contact anchors do not model resistance along the connecting poly. Fresh extraction must address this explicitly and establish compact-model overlap before electrical qualification.

NEW BINDING FINDING: the naive assertion that every physical gate group has one original schematic MOS ID was rejected.40 of50 groups contain multiple old schematic IDs even though their terminal owners are identical: the LVS matcher permutes electrically equivalent parallel units. Actual physical wrapper paths and unit ordinals are complete. Do NOT use old loaded_instance or schematic expanded names as unique physical wrapper identity. Bind new RC devices using CURRENT FLAT LVS native IDs, unique current physical paths and actual terminal/anchor geometry; keep schematic names only as semantic aliases. Full200-unit group evidence and the rejected assumption are preserved in docs/evidence/mos650-wires-41690238100-physical-gate-groups.json. This finding does not reject LVS equivalence or the physical650 candidate.

NEXT PHY: use release433047733 current view/native05 wires.gds,wires.l2n,graph,locations,anchors03/anchors08 and flat-native identity to derive complete fresh metal/via RC. Extend the model with actual gate-poly access resistance and avoid double-counting compact intrinsic parasitics. Preserve exact physical anchor aliases and current650 device order; do not rerun the old500->200 expansion. Full MIM/intrinsic composition, source-order controls and unchanged loaded electrical gates remain required. Substrate resistance/full foundry PEX are still unqualified; full serial Gen3x4 PLL/CDR/SERDES/PCS/LTSSM and mainchip integration remain open.

MAINCHIP: follow SAME engine41688147573/source6cae8ce19c56bb597b9edab02c7d21b14b099eb2, job126099852433, release433034713. Its source partition controls passed255 cases; complete build remains subject to the live snapshot below. Do not dispatch a duplicate or restart on observation timeout. Once the actual full build succeeds, qualify its new ELF/runtime on the complete chip and execute the original full64 routing and downstream physical/RC/all-corner setup/hold gates. The old single-worker route41552715162 remains a preserved memory failure; no identical rerun.

Native payloads remain cloud-only, local workspace empty,8hour monitor read-only with automatic_native_dispatch=false. FullPHY, fullchiprouting and finalsetup/hold are not accepted.

Observed 2026-11-03T18:10:41.417238+00:00:
- 41688147573: in_progress/None
- 41690238100: completed/success


## Current continuation: actual650 terminal identity passes; guide region memory repair in cloud build

Mainchip41552715162/source5ba879c94ed74747d7e30ae341dee1d045765150 is TERMINAL FAILURE, not active. The single-worker route ran4560.291882265 seconds and crossed the unchanged11534336 KiB process-group RSS guard at11793076 KiB; host available3367476 KiB, SIGTERM return-15, OOMKilled=false. It remained in20th guide iteration after90 percent, partial82 markers. Partial markers are not final DRC, and restoration/RC/STA were not reached. The complete82-member derived failure and release432114633 metadata are preserved in docs/evidence/mainchip-single-worker-41552715162-complete-failure.json. Do not rerun the identical candidate.

Pinned upstream guideTilesFlow merges intersecting same-direction guide boxes without a region-size cap. New candidate6cae8ce19c56bb597b9edab02c7d21b14b099eb2 on codex/mainchip-guide-tiled-engine partitions each merged worker rectangle into windows bounded by args.size times native GCell dimensions, with one-GCell overlap and exact full-union preservation. Original guide geometry, full64 strategy, search costs, single-worker limit, physical constraints and acceptance gates remain unchanged. Worker decomposition changes routing behavior and is not claimed equivalent. Exact failing-box size was not observed in the old log; new split telemetry makes this measurable.

Engine run41688147573/release433034713 passed source-controls126099301471: actual C++ partition helper255 coverage/boundary/integer-limit cases,6 invalid-bound refusals,4 independently detected coverage faults; original9 lifetime cases, engine7 positive45 refusal25 lifecycle and observer4 positive29 refusal controls retained. Follow SAME engine-build126099852433; no restart merely because observation times out. Full native compile status is in the current snapshot below. A successful build alone requires actual-chip qualification before one full64 routing attempt, followed by original restoration/full DRC/antenna/PG/LVS/fresh RC-Liberty/all-corner STA.

PHY identity41687582642/source d059ce861f55ee6c526a2e6f4f7beab7041fc562 on codex/cdr-mos650-identity SUCCEEDED. Both actual deep and flat LVS databases from physically qualified650 candidate41556278428 bind all650 devices,2046 actual terminal owners/geometries and25 public ports to the independent original schematic and explicit200-MOS plan. All15 corrupt-identity controls reject per mode. Complete physical650 parameters and explicit source/drain terminal permutations are retained. Release433031196 permanently contains the actual complete identity/native input evidence; docs/evidence/mos650-identity-41687582642-receipt.json binds every derived member and full release index.

NEXT PHY: use these actual650 native IDs/semantic mappings to implement complete physical geometry paths and conductor partitions, then fresh650 wire RC with explicit intrinsic-device parasitic coverage. Existing500-layout canonical compare assumes unchanged500 devices and cannot be qualified by changing counts. Do not reuse old500 RC or double-expand200 actual MOS. New electrical qualification must retain original loaded gates and failure history (61/62 headroom, phase/current/sampling), then full closed-loop serial Gen3x4 qualification and integration. Identity success is not fresh RC or electrical/PHY acceptance.

All native CAD/SPICE/GDS/ODB/ELF/raw/archive payloads remain GitHub-only. Local workspace remains empty. Existing8hour monitor remains read-only, automatic_native_dispatch=false. Full objective remains active; no fullPHY, routed-mainchip or finalsetup/hold acceptance.

Observed 2026-11-03T17:54:12.571556+00:00:
- 41505377046: completed/failure
- 41507901483: completed/failure
- 41552715162: completed/failure
- 41556278428: completed/success
- 41687582642: completed/success
- 41688147573: in_progress/None


## Current continuation: actual MOS650 gap repair physically tested; full native evidence preserved

First actual650candidate41554289328 produced a valid all34layer-roundtripped GDS but fullDRC41554860331 rejected oneLU.b marker. Independent diagnostic41555538547 then proved deep+flat650device LVS and12LVS fault rejections; offgrid was deliberately not qualified while baselineDRC failed. Exact marker: nssoc_model_range_123,polygon(0,-5;0,-3.33;0.98,-3.33;0.98,-5)um. All evidence preserved, no rule waiver.

Actualgaprepair324d50d9f2c4ba3cde823ff1c8602e95c0c25a82 oncodex/cdr-mos650-geometry shortened unit spacing1um->0.5um, reducing worst extension5um->2.5um while retaining totalW,all200MOS and450other devices,originaltopaccess and independent reference. Generation41555879992/release432130268 SUCCEEDED. NewGDS1019324bytes/SHA17bcc6f9e98f5346e92f7c770f4212a012ab1718ba78432fd609e280ff5e0541; all34layer roundtrip and original preservation guards passed. Independent reference remains35500bytes/SHA21d730545b983930eacf733ba77a7593df52e253987991724de9594fe136bbfb.

Newfullphysical41556278428/source852e610cd4873d7cfcd3b09d85f03c62b5151969 oncodex/cdr-mos650-physical/release432132372 was run on exact new GDS. Native checker30c4586b86167ad775af14b5568152820a802037150bdfd282e7ba0843a1555f retains every original phase body and all13fault intents, collects independent DRC/deepLVS/flatLVS failures, refuses acceptance for any failed/unqualified phase. No native count/rule/mismatch criterion was weakened.

ACTUAL TERMINAL RESULT: success; PASS_NATIVE_PDK_CDR_PD650_DRC_LVS_AND_FAULT_CONTROLS; full650physical macro accepted=True.
All phase statuses: {"drc": "PASS", "gain_gate_disconnected": "REJECTED_EXPECTED_FAULT", "gain_tail_width": "REJECTED_EXPECTED_FAULT", "lvs": "PASS", "lvs_flat": "PASS", "missing_gain_hbt": "REJECTED_EXPECTED_FAULT", "missing_hbt": "REJECTED_EXPECTED_FAULT", "offgrid": "REJECTED_EXPECTED_FAULT", "old_data_header_length": "REJECTED_EXPECTED_FAULT", "old_retime_width": "REJECTED_EXPECTED_FAULT", "old_sampler_input_width": "REJECTED_EXPECTED_FAULT", "q_open": "REJECTED_EXPECTED_FAULT", "rail_short": "REJECTED_EXPECTED_FAULT", "v59_old_length": "REJECTED_EXPECTED_FAULT", "wrong_finger_count": "REJECTED_EXPECTED_FAULT", "wrong_follower_polarity": "REJECTED_EXPECTED_FAULT"}.
All560DRCcategories ZERO markers; deep andflat650transistorLVS match, no extractiondiagnostics;200MOS/124HBT/98rppd/7MIM/221tap; all13actualfaults rejected. This closes the physical650 macro DRC/LVS gate for this exact candidate, not fullPHY or productionapproval.

NEXT PHY: follow docs/cdr-mos650-fresh-rc-continuation.md. Build actual650native identity/fullterminal/wirepartition view and fresh650RC, with explicit50->200unit mapping and450nonMOS invariants. Existingcanonical logic assumes500unchanged primitives and cannot just change constants. Expected2046terminals/1428anchors require actual extraction; never inject expected counts as observations. Existing500layoutRC26344R/16878C and rejectedfull650wave41549033741 cannot qualify this newgeometry. Avoid double-expansion ofalready200physicalMOS. Then original34.25ns/full650electricalgates including61/62headroom,phase/current/sampling; fullserialGen3x4/closedloopCDRPLL remains open.

MAINCHIP: follow SAME fullroute41552715162/source5ba879c94ed74747d7e30ae341dee1d045765150, native-routing125644268460, release432114633. Qualifiedsingle-workerengine41548861169 andindependentcontrols41552510648 passed. No duplicate/restart on observationtimeout. Fullroute restoration/fullDRC/antenna/PG/LVS/qualifiedRC-Liberty/allcornerSTA remain required. Fullmainchiprouting andfinalsetuphold not accepted.

Native CAD/SPICE/GDS/ODB/ELF/raw/archive payloads stay GitHub-only; localworkspaceempty. Existing8hourmonitor read-only,automatic_native_dispatch=false. Full product goal remains active.

Observed 2026-11-03T01:02:04.189543+00:00:
- 41552715162: in_progress/None
- 41554860331: completed/failure
- 41555538547: completed/failure
- 41555879992: completed/success
- 41556278428: completed/success

## Current continuation: actual MOS650 physical GDS generated; independent650 DRC/LVS dispatched; same full-chip route active

Generation41554289328/source0ff42781cc19177fd3c12d54eb005814d54b3373 SUCCEEDED oncodex/cdr-mos650-geometry/release432122255. Actual physical GDS1019324bytes/SHAaca57588cfd38a563bca6fbe1376622c276ec8db54a67bc39e06d40718e012a3. All42wide MOS replaced by192native model-range units plus8unchanged narrow originals;450other devices retained. Alloriginal shape/hierarchy/public annotation guards and macroextent passed. All34actual layer unions are exactly equal after native GDS write/re-read; no executable PCell/library context remains. This is real geometry generation, NOT native transistor extraction or physical acceptance.

Independent reference35500bytes/SHA21d730545b983930eacf733ba77a7593df52e253987991724de9594fe136bbfb derives from original schematic correspondence41435641296 and original200-unit electrical plan, not new candidate extraction. Expected census200MOS/124HBT/98rppd/7MIM/221tap =650. Derivedartifact13192844306 SHA032dc9512f6f615f748ccfaf77f5a1cef8187f330d4617cbbf282f0e37c658ee preserved completely with native archive index/release metadata; nativeGDS/reference/archive stay cloud-only.

Two real implementation failures preserved:41553480865 rejected optional layer display-name drift(Metal1.pin8/2 versus8/2); fixed by numeric GDS layer/datatype identity, no polygon waiver.41553925669 passed physical replacement/preservation guards but rejected GDS roundtrip8/2 because default PCell context regenerated internal annotations. Export now uses write_context_info=False and preserves complete all34layer roundtrip evidence, rather than suppressing mismatch. Alloriginal50PCell exact checks and documented marker-only differences retained.

Full physical verification source45c8b61e1d41bc9016b0fc387b092b84366b9d81 oncodex/cdr-mos650-physical, run41554860331/release432125037 DISPATCHED. Follow SAME run. It authenticates all actual generation archive members, reference provenance and physical GDS; full560-category DRC, deep andflat no-simplify650transistorLVS and all13original fault intents required. Complete derived checker SHA f8882ff123bf308d8273b40ff3dc06351abb010a3420878d8c226f2e894b787b. Exact adaptation changes expected MOS count50->200/total500->650 and original schematic case/unit names, with SC_GT0 firstunit8.890u; no DRC rule, mismatch criterion or fault removed. Actual650 independent reference is used to exercise all10schematic fault hooks in sourcecontrols. Three geometryfaults remain native. Post-publication receipt is outside sealedarchive and compared through independent asset metadata; every actual indexed file remains authenticated.

NEXT PHY: inspect actual41554860331 source/native outcomes, preserve any failure, fix actual rule or LVS causes. Only actual full physical success may qualify matching650geometry. Then derive complete650canonical terminal identity/new650RC and full650loadedwave from that exactcandidate. Never reuse old500layout RC to claim650physical correctness. Prior directmetal500layout/full650wave41549033741 REJECTED: only two specific HBT headroom gates passed;61/62headroom,phase/current/sampling remain failures. FullserialGen3x4/closedloopCDRPLL and mainchip integration unclosed.

MAINCHIP: follow SAME fullroute41552715162/source5ba879c94ed74747d7e30ae341dee1d045765150 oncodex/mainchip-guide-single-full64/release432114633, native-routing125644268460. Actual new single-worker engine qualified41548861169; independent full64controls41552510648 passed. Memory reduction and completed routing still unproved; no restart on observation timeout. Require actual fullroute restoration,fullDRC/antenna/PG/LVS/qualifiedRC-Liberty/allcornerSTA. No finalsetup/hold acceptance.

Native payloads/work remain GitHub-only, localworkspaceempty. Existing8hour monitor read-only, automatic_native_dispatch=false. Goal remains active and full scope unchanged.

Observed 2026-11-03T00:44:36.074387+00:00:
- 41552715162: in_progress/None
- 41553480865: completed/failure
- 41553925669: completed/failure
- 41554289328: completed/success
- 41554860331: in_progress/None

## Current continuation: single-worker actual chip qualified and full route active; real PHY wave rejected, two specific headroom gates improved

Actual chip qualification41548861169/source17d1961a0847f8045449e4bc6b7f42e5aa31e310 SUCCEEDED. Full143820nets/154480instances/1691clocks preserved, all104 runtime dependencies match, ODB/DEF identities unchanged; all3roundtrip/final-check/measure phases complete. Original92DRT markers,21antenna nets/27violations remain reference checks, NOT signoff. Native elapsed670.66695428s; ELF108936520bytes/SHA c9fa3fc955888a75801f77bee022b79748d884d32dde0d99645f0ca4c21ce6c1.

Full64 source5ba879c94ed74747d7e30ae341dee1d045765150 oncodex/mainchip-guide-single-full64 binds actual new qualification, fixture, producer, assets, ELF and all104dependencies. All22qualification fault controls,11original phase bodies,full original scope/resourceguards retained; all3nested manifests updated bottom-up. Independent sourcecontrols41552510648 SUCCEEDED. Actual fullroute41552715162/release432114633 is active: follow SAME native-routing125644268460, do not duplicate/restart on observation timeout. Sourcecontrols125644018582 already passed. Memory reduction and completed routing NOT yet proved. After returnedroute require fullDRC/antenna/PG/LVS/qualifiedRC-Liberty/allcornerSTA; no finalsetup/hold success yet.

Actual full650 loaded wave41549033741/source6194e2fc2108f7b38c378d387761cf7e79771edf completed native simulator return0 in638.233571068s and REJECTED electrical acceptance. Full34.25ns unchanged case produced113475rows/1302columns; raw1182001399bytes SHA6f37a25d4ba0d6c9e064b272c7c79a387836c72692234424acdef9dab773736d remains cloudonly. Original13binding+2equivalentunit+12expansion native checks and13admission/24partition/4projection/6identity source checks retained. Actual diagnostics empty and zero-sourceOPmaximum zero.

Compared with actual rejected16Via2 run41540256258, directmetal repair reduced all8 measured source-sink Reff by42.28-45.27percent (measurement41549188690 SUCCEEDED, all26344R and978anchors authenticated). Two SPECIFIC HBT minimum-active-Vce gates now pass0.4V: xd0115=.4116121765V,xd0116=.4097722545V. xd0061=.3773409555V andxd0062=.3757119282V still fail. Phase13.1871253mV<30mV, signedVI40.4484742uA<50uA; sampler timing/decision margins still fail. Do NOT translate two headroom conditions into device/fullPHY acceptance. Complete derived wave rejection and all network measurement assets preserved here.

Matching650 physical geometry remains OPEN: current freshRC26344R/16878C derives from500device layout, while loaded model expands50MOS to200units. Newactualgenerator oncodex/cdr-mos650-geometry replaces42wide MOS with192native model-range units plus8unchanged originals, preserving450other devices/25ports/macroextent. Independent reference comes from original schematic; no newextracted netlist used as reference. First41552100346 rejected original PCell reconstruction before candidate mutation. Complete50-device diagnostic41552637236 proves ONLY Metal1.pin(8/2) internal annotation differences: original absent/regenerated2rectangles; every fabrication polygon and other annotation matches. Both failures preserved.

Correctedsource39a079e0bc3d84b5c05628200d39c9bfc2e9fba4 (all5changed files readback verified) pins the exact full50 observed marker-only differences; any extra drift still rejects. Independent regenerated terminal markers must lie inside actual originalM1; only newlycreated internal annotations removed, alloriginal publicM1annotations/fabrication/hierarchy guards preserved. Actualgeneration41553480865/release432118222 dispatched. Follow SAME run. Candidate generation alone cannot close matching650geometry: require all560DRC,deep+flat650transistorLVS,meaningfulfaults,canonicalidentity,newactual650RC,newloadedbinding/fullwave.

AllnativeCAD/SPICE/GDS/ODB/raw/ELF and archives remain GitHub-only. Localworkspaceempty; onlysource/derivedtext APIs in RAM. Existing8hour monitor stays read-only with automatic_native_dispatch=false. Goal remains active; fullserialGen3x4,mainchipfinalrouting andfinalsetup/hold unclosed.

Observed 2026-11-03T00:33:06.129437+00:00:
- 41548861169: completed/success
- 41549033741: completed/failure
- 41549188690: completed/success
- 41552100346: completed/failure
- 41552510648: completed/success
- 41552637236: completed/failure
- 41552715162: in_progress/None
- 41553480865: completed/failure

## Current continuation: direct metal physical/canonical/RC passed; identical full650 wave and single-worker actual-chip qualification active

The actual upper-metal repair GDS0209d91c15d490631937f31aa12d2bbe68153f88a62e7be596fbc4eaae295dfa (1090004bytes) passed physical41545635890: all560 DRC categories,zero markers,deep/flat500-device transistor LVS and all13 physical fault controls. Canonical41546548106 passed143 source controls and full500 devices/1446 terminals/25 ports/978 anchors plus113x13=1469 layer-partition comparisons. Physical/canonical proof is preserved here; this is not fullPHY acceptance.

FreshRC41547492718/sourcef1248c7a3709d8112da98d25b9c3d67bf39c83fe succeeded with26344R/16878C/500devices and all11 numerical phase receipts. Model2125138bytes/SHA1988b375a1b290c1921c0a3cfd2cd5c82e54c2425103506e3995474c8c3ae89d; composition1018813bytes/SHA50c1ecc64299770eda8250a422f470031077ce69cf05e5a75e24136ac3fd5768. Actual port order returns toiry,yp,yn,irvx; never reuse previous RC or old positional ordering. Derivedartifact13190470112 SHA364f21f082b1043bac1672203836dd516394d88d52e5f84b724ba07440d8a614 authenticated. Native release432088543 archive703588571 stayscloud; completeindex703588573 SHA064e9866374789beed3d2a3f756a121348e0f8614a3dfc21ff470bd0fbc262bd.

Actual electrical comparison41549033741/source6194e2fc2108f7b38c378d387761cf7e79771edf oncodex/cdr-clock-metal-domain-loaded/release432096193 is dispatched. Ownsourcecontrols passed. Follow SAME loaded-wave125631947060 and preserve actual fullwave result. New correspondence transport changes73 terminal labels using both complete independent canonical identities and prior16Via2 LVS map; all six identity faults and original13 admission/24partition/4projection source controls retained. Original34.25ns full650 test/runtime/stimuli/preparation/measurement/limits unchanged. Actual13binding+2unit-spelling+12expansion checks still required in native preparation. Matching650geometry,closedloopCDRPLL,fullserialGen3x4 and electrical acceptance remain open. Compare every actual result against rejected41540256258, not a synthetic baseline.

Actual eight-path network comparison41549188690/source7bab158ff9fe67647e98fee5bc1d3c42b34f4732 oncodex/cdr-clock-metal-resistance/release432096898 is dispatched. Authenticate all current native archive members/all26344R and978 anchors, retain2.5ohm/reciprocity/KCL/energy/four refusals, measure eight upper-emitter/clock-collector Reff vs actual16Via2 network41541318521. Follow same job; diagnostics alone cannot close electrical gates.

Mainchip complete single-guide-worker engine build41542996185 succeeded: ELF108936520bytes/SHAc9fa3fc955888a75801f77bee022b79748d884d32dde0d99645f0ca4c21ce6c1,all3671 compile commands and all8 native smoke/build commands successful,104 runtime dependencies unchanged. Only liveguideworker limit2->1; memory reduction not measured yet. Source-controls41547846319 failed on two nested stale workflow pins before native execution; fullfailure preserved. Fix17d1961a0847f8045449e4bc6b7f42e5aa31e310 updates allthree manifest levels bottom-up, checks all entries and retains every original checker. New independent controls41548705055 succeeded.

Actualchip qualification41548861169/source17d1961a0847f8045449e4bc6b7f42e5aa31e310 oncodex/mainchip-guide-single-roundtrip/release432095403 is active at last check. Follow native-routing125631431607; despite job name this is roundtrip/final-check/measure only, not routing. Must preserve whole143820net/154480instance/1691clock scope,ODB/DEF snapshot identity,92DRT markers/21 antenna nets/27 violations and104runtime fingerprints. These are reference-equivalence checks, not signoff.

NEXT MAINCHIP: only after actual qualification success, bind actualnew reports/fixture/ELF/producer in a new full64 branch based302f9c30a847acd659a8c451bdce83707fce5d70. Retain all22 qualification fault controls,all11 original phase bodies,full original scope and guards; update nested manifests bottom-up. Obtain independent same-source controls before native route. Do not reuse two-worker qualification or restart the failed two-worker run41513663302. Route failed11GiBRSS after6800.616s and partial82markers were not finalDRC. After actual returned route require restoration/fullDRC/antenna/PG/LVS/qualifiedRC-Liberty/allcornerSTA. Finalsetup/hold has not passed.

Native work/payloads remain GitHub-only; local workspace empty. Existing8hour monitor remains read-only,automatic_native_dispatch=false. Product objective remains active; none of these stage successes proves fullserialPHY or finaltiming.

Observed 2026-11-02T23:57:54.743022+00:00:
- 41542996185: completed/success [('source-controls', []), ('engine-build', [])]
- 41545635890: completed/success [('source-controls', []), ('native-physical', [])]
- 41546548106: completed/success [('source-controls', []), ('native-canonical', [])]
- 41547492718: completed/success [('source-controls', []), ('native-rc', [])]
- 41547846319: completed/failure [('source-controls', []), ('native-routing', [])]
- 41548705055: completed/success [('source-controls', []), ('native-routing', [])]
- 41548861169: in_progress/None [('source-controls', []), ('native-routing', ['Authenticate new engine, roundtrip actual chip, compare full DRT and antenna'])]
- 41549033741: in_progress/None [('source-controls', []), ('loaded-wave', ['Authenticate direct clock metal RC and simulate all200 explicit model-range MOS units'])]
- 41549188690: queued/None [('compare', [])]

## Current continuation: actual direct clock metal candidate generated; full physical qualification and routing engine build active
The failed via-only650wave41540256258 remains rejected. No electrical gate closed from its1.62-1.94percent resistance reduction. Full previous measurement and comparison remain under docs/evidence/cloud-v337-domain-wave-41540256258/.
A real upper-metal repair is now implemented, not merely proposed. Run41545373835/source85b5462fa5155ba3b790d0e3552ac4c4a26d8e81 on codex/cdr-clock-direct-metal generated actual GDS1090004bytes/SHA0209d91c15d490631937f31aa12d2bbe68153f88a62e7be596fbc4eaae295dfa. Eight original HBT terminals form two distinct same-net connected TopMetal1 networks,4um route width,48Via3+48Via4+32TopVia1. M3 landings are completely inside original same-net metal; all other layers/devices retained. Both sets of tree-link lengths are110.605/470.745/310.245um; shared trunk metal is merged.10actual geometry controls and original resistance controls pass.
First generation41545004371/source97305d1bda256b06821d2121ee6c17274d9c7a36 rejected the entire candidate: all eight landings passed, but two collector links could not route around clipped obstacles. All evidence preserved. Revision uses complete obstacle polygons and admissible spanning links, with a regression for obstacles beyond the former100um window. No clearance or electrical limits loosened.
Native generation release432077856, tagcloud-results-41545373835-1-cdr-clock-direct-metal; complete-output-index703536532 SHA19a29ad02fb27636c5cd2e93d7862afdc51f905cbeb08ce4c0d4c3069aaf35ea; nativearchive703536439,61325990bytes SHA67d10a9c7fa82d9ebd0fb7f9092f0df73b2f16277855a86ebad0925dbf172352. Native payload stays cloud-only. Derivedartifact13189280736,272700bytes SHAe6b29dab098f380843b210c2f6f81f1397f6c9086e691d289e3a816f4ce612d8.
Full physical qualification41545635890/source014e51092c1de1521e17d1963e8095d5e8c6322a on codex/cdr-clock-metal-physical, release432079295/tagcloud-results-41545635890-1-cdr-wire-shortcuts-physical. Source-controls125620438847 passed. Nativephysical125620632632 last observed acquiring unchanged native tool. Independent validation reconstructs all declared geometry, checks every actual terminal/cut/enclosure, both native owners, every-layer foreign clearance and exact serialized delta. Then unchanged560DRC/deep-flat500deviceLVS13 must pass. Do not claim physical or electrical acceptance until actual results.
NEXT PHY: follow SAME physical run; preserve failures. If physical pass, update canonical producer to this GDS and actual prior16Via2 freshRC41537723922/sourcebd1fc5b2deed8a0ea153db91a362c983e6379254/release432038108 as reference. Verify all500devices/1446terminals/25ports/978anchors and every113partition x13layer union with declared metal additions, not old via-only assertions. Then fresh distributedRC and unchanged full650loaded-wave gates. Never reuse old RC or infer performance from geometry controls. Actual650matching layout, closedloopCDRPLL and fullserialGen3x4 still open.
Mainchip single-guide-worker engine41542996185/source62e6ac38e32493023dcda04bbb4cf5476e9d50f2/release432065531 remains building at last live poll; source-controls passed. Follow same build125612193523. New ELF/runtime must receive actualchip qualification before a new full64 route. Previousfull64 run41513663302 failed11GiBRSSguard after6800.616s; partial82internal markers is not finalDRC. Preserve original scope/limits; finalsetup/hold has not passed.
All native work is GitHub-hosted; localworkspaceempty.8hour read-only monitor automatic_native_dispatch=false unchanged. Full objective remains active.

Observed 2026-11-02T23:29:55.762757+00:00:
- 41545004371: completed/failure [('native-geometry', [])]
- 41545373835: completed/success [('native-geometry', [])]
- 41545635890: in_progress/None [('source-controls', []), ('native-physical', ['Verify actual new GDS with full native DRC deep flat LVS and faults'])]
- 41542996185: in_progress/None [('source-controls', []), ('engine-build', ['Build complete pinned engine under owned cgroup'])]

## Current continuation:16Via2 full650 wave rejected; one-worker routing engine building
Actual full650wave41540256258/source15feb7375e24de69d10377f1e52e8e07e3ef02c0 completed34.25ns with simulatorreturn0 after1175.928051441s. MeasurementREJECTED_WHOLE_MIM_PD650_LOADED is a real electrical rejection, not process/infrastructure failure.113475rows,1301vectors+time,124HBT currents,200MOS currents,977Vnodes,11savecommands retained. Raw1182001399bytes/SHA4d543b24922e80a186c5073092f4033ff9b8eccf0534120b6dd6f359d5a8041a remains in cloud. Actual13binding+2equivalent-unit+12expansion controls passed; source13admission/24partition/4projection/6identity controls passed. No native warnings in diagnostics; zero-sourceOP maximum0.
Phase13.179724361mV still below30mV (old13.179521608mV); VI40.422928501uA still below50uA (old40.422021823uA). All A/B/C/D maximum clock-to-valid times remain exactly47.03125/42.65625/118.90625/99.84375ps vs37.5ps gate. Wrong-sign samples remain0/0/3/34; below100mV129/128/129/128 of765. ComparatorX/Y wrong-sign counts remain387/44; this was also present in the previous wave, not a new regression.
Minimum activeVce61=.3545478598V,62=.3519561613V,115=.3811308016V,116=.3798059077V. Improvements are only.67056/.70965/1.58834/1.58760mV. Remaining deficits against.4V are45.452/48.044/18.869/20.194mV. Source/sink resistance measurement41541318521 found1.62-1.94percent improvement, consistent with limited headroom benefit; this repair does not close any failed electrical gate.
Retain rejected baseline41528163238 and new rejection. Full native release432050827 has4parts plusindex/parts; all raw/source/case outputs remain there. Authenticated derivedartifact13188180017,2016185bytes,SHA84ed30b96d741bd51133c1b93b7f5e4662bfe7b9944eb95815c7c195b864fc5b. Selected complete measurement/preparation/control/derivation/release reports and full per-stage baseline comparison preserved in docs/evidence/cloud-v337-domain-wave-41540256258/. Scope remains proposed650MOS partition over actual500device wireRC, not matching650physical geometry.
NEXT PHY ACTION: implement actual low-resistance metal/access repair; further identical via-only work is not sufficient. Use native fullgraph/coordinates in clock-access-resistance-41541318521/result.json. Investigate direct upper-metal same-net paths between E54/E56 and C61/C62, and translated E106/E108 to C115/C116, with realvia-stack landings and foreign-net keepouts on everylayer. This metalcandidate is NOT implemented yet. Require560DRC/deep+flatLVS13,completecanonicalidentity,freshRC and unchanged loaded gates. Also preserve independent phase/current/sampling failures; solving4HBT headroom alone cannot prove fullPHY.
Mainchipfull64 run41513663302 is terminalRSSfailure: route6800.616s,11832844KiB>11534336KiBguard,return-15, noOOM. Actualcompute ended22:28UTC; jobcontinueduploading. Partialiteration20/90percent82markers is NOTfinalDRC. Nativefailurecapsule431900029 stayscloud.
Single-guide-worker complete engine build41542996185/source62e6ac38e32493023dcda04bbb4cf5476e9d50f2, branchcodex/mainchip-guide-single-engine, release432065531. Ownsourcecontrols passed; actualengine-buildjob125612193523 active atlastdirectpoll. Only C++liveworkerlimit2->1 changed; strengthenednine-casefixture,7positive/45refusal/25lifecyclecontrols retained. Authenticate resultingnewELF/runtime, then repeat actualchip ODB/DEF/net/clock/DRC/antenna qualification before full64 route. Never reuse oldELF qualification fornewbinary. Same12GiBcgroup/11GiBRSSguard/2GiBavailablefloor; no scope reduction.
Actual650layout,closedloopCDRPLL,fullserialGen3x4PHY and finalmainchipsetup/hold remainopen. Cloud-only work; localworkspaceempty.8hourread-onlymonitor/automatic_native_dispatch=false unchanged.

Observed 2026-11-02T23:14:00.210773+00:00:
- 41540256258: completed/failure
- 41542996185: in_progress/None
- 41513663302: completed/failure

## Current continuation: full64 stopped at RSS guard; single-worker engine build dispatched
Mainchip41513663302/source302f9c30a847acd659a8c451bdce83707fce5d70 is TERMINAL FAILURE. Actual router ended2026-11-02T22:28:18Z after6800.61579865s withreturn-15 andsupervision_failure=maximum_group_rss. Observed11832844KiB >11534336KiB guard; available3317168KiB. Container OOMKilledfalse. This was NOT a timeout. Process receivedSIGTERM and no live children remained. The cloud job continued packaging/uploading after native compute stopped; earlier job-levelactive reports must not be read as proof of ongoing native computation.
Original64 route reached guides iteration20. Last internal progress was90percent with82markers vs92 atiteration19; route did NOT return, no completed route-restore/final-check/measure acceptance exists.82is not a final DRC result. Full failure artifact13185543898 (396593bytes,SHA68b8593758f2b9f28106e7953e3c05b983f67b944c5bae17246ebe392edb9261) is retained completely in docs/evidence/mainchip-guide-full64-41513663302-memory-failure.json. Native release431900029 preserved1589851937-byte archive in3parts plusindex/parts metadata. Never download those native parts locally.
Concrete fix source62e6ac38e32493023dcda04bbb4cf5476e9d50f2, branchcodex/mainchip-guide-single-engine: change only C++guide_worker_limit2->1 in existing qualified upstream FlexDR patch. New fullFlexDRSHA393bbfd15596cddfdbc3bb4d87a3055449596d5646945b89a4cc6526a32ac8b0. Exact source reversal and sole C++constant delta checked during source preparation. Originalguideboxes,IDs,searchargs,64schedule and resourceguards retained. Stronger compiled nine-case fixture must prove maxexactly1liveworker,allIDs in exact input traversal order, no leaks and zero/multi-box refusal. Preserve7positive/45refusal/25lifecycle build controls and DRTmessage-ID checks.
New complete engine build41542996185,release432065531/tagcloud-results-41542996185-1-mainchip-guide-batch-engine-build. Follow same run; do not duplicate. Controls precede complete native build. BUILD SUCCESS IS NOT ACTUAL CHIP QUALIFICATION. When built, authenticate binary/runtime/source receipt, then repeat fullactualchip ODB/DEF/net/clock/DRC/antenna qualification with thisnewbinary before full64 route. Priorenginequalification41506262574 cannot qualify the newELF. Final fullchipLVS/diodePG/globalclasses/qualifiedRC/Liberty/allcornerSTA remain open.
PHY comparison41540256258/source15feb7375e24de69d10377f1e52e8e07e3ef02c0 remains the same full650 electrical trial against actualfreshRC41537723922. Preserve/compare its actual electrical result to rejected41528163238. New8path network measurement41541318521 proves only1.61665-1.93600percent Reff improvement, leaving11.50867-12.11822ohm. If electrical gates reject, design actual wider/upper-metal same-net paths and localaccess reinforcement using saved nativecoordinates; do not repeat tiny via-only repairs or idealize R. Such metalcandidate is NOT implemented yet.
Actual650physical geometry,closedloopCDR/PLL,fullserialGen3x4PHY and finalmainchip setup/hold remain open. Cloud-only native work; localworkspaceempty.8hour read-only monitor/automatic_native_dispatch=false unchanged.

Observed 2026-11-02T23:10:14.769742+00:00:
- 41513663302: completed/failure
- 41542996185: in_progress/None
- 41540256258: in_progress/None

## Current continuation: measured16Via2 benefit is small; full650 wave still authoritative
Cloud resistance comparison41541318521/source09b163cb8a45f3682188586806044fc0e2fcd459 SUCCESS, release432056699. All3236 freshRC archive members authenticated; all26218 native/exported resistors agree,978 native anchors and coordinates verified. Eight full unit-injection networks passed KCL/energy,analytic2.5ohm,reciprocity and4fault controls. All ranked edges retain native coordinates.
Actual reductions are only1.61665%-1.93600% (0.18911-0.23924ohm). New Reff11.50867-12.11822ohm. T054_E->T061_C12.35746->12.11822; T054_E->T062_C12.34120->12.10261; T056_E->T061_C11.69778->11.50867; T056_E->T062_C12.22452->12.01794. Cgroup106/108->115/116 has identical values. This proves a small physical-network improvement, NOT electrical acceptance.
Important next design decision: repeated via-only work cannot reasonably be treated as sufficient closure. Use actual loaded comparison41540256258 against41528163238 to quantify headroom/delay; if rejected, target real low-resistance metal paths and local access rather than another identical via pass. r2794/r2792 dominate upper54 access; r2739/r2751 and r2801/r2809 dominate clockcollector localaccess; fullnetwork/path coordinates in result.json. Do not interpret matching resistor names across extractions as identical physical elements; compare full source/sink networks.
Candidate next approach (NOT implemented or accepted): direct wider upper-metal connections between same-net upperE54/56 and clockC61/62, and translated106/108->115/116. Investigate existing qualified via-stack geometry for M3-to-upper-metal transitions, foreign-net keepouts on every touched layer, all4 terminals pernet and serialized ownership. Any proposed strap needs real560DRC/deep+flatLVS13, canonical device/material identity, freshRC and identical loaded gates. Do not idealize resistance, relax voltage/delay limits or claim an unbuilt route.
Full650wave41540256258/source15feb7375e24de69d10377f1e52e8e07e3ef02c0 remains the same actual comparison with newRC41537723922. Own source controls passed13admission/24partition/4projection plus6identity faults; complete500device/1446terminal/25port identity transport confirmed35renumbered terminals. Native job125602509227 was active at last directpoll. Follow actual terminal result and preserve all outputs. Release432050827. Current500physical and proposed650simulation remain distinct.
Mainchip full64route41513663302 stays live; do not duplicate it. Fullchip DRC/antenna/diodePG/globalclasses/LVS and qualifiedRC/Liberty/allcornerSTA remain required afterroute. Actual650geometry,closedloopCDRPLL,fullserialPHY and final chip timing remain open.
Cloud-only work. Local workspace empty.8hour read-only monitor and automatic_native_dispatch=false unchanged.

Observed 2026-11-02T23:00:33.030900+00:00:
- 41541318521: completed/success
- 41540256258: in_progress/None
- 41513663302: in_progress/None

## Current continuation: actual16Via2 freshRC passed; full650 electrical comparison
FreshRC41537723922/sourcebd1fc5b2deed8a0ea153db91a362c983e6379254 completed successfully with500 devices,26218R and16796C. ModelSHAe99ea8c8b7edb51b0f8ce51f269e90460ce90d97fa7f8496540c7d11d806154a. All11 numerical phase receipts are retained. Complete native release432038108 remains in cloud. This is extraction qualification, not electrical or fullPHY acceptance.
New loaded comparison41540256258 oncodex/cdr-clock-access-domain-loaded, source15feb7375e24de69d10377f1e52e8e07e3ef02c0, reservedrelease432050827, tagcloud-results-41540256258-1-cdr-clock-access-domain-loaded. Follow this same run; do not dispatch a duplicate. Source controls precede native execution. It uses the original complete34.25ns/650device electrical trial with unchanged runtime, stimuli, prepare/measure methods and acceptance limits. Compare against rejected41528163238.
Preparation found35 changed terminal cluster/name labels and observed public orderiry,yn,yp,irvx. Existing physical500device primitives/positions are unchanged. Prior LVS correspondences are transported using independently extracted old/new500device identities and1446terminal ownership, complete physical transforms, a bijective net map and all25 named public-port partitions. Six deliberately corrupted identity inputs must be rejected by cloud controls, in addition to existing13admission,24partition,4projection and actual native13binding+2equivalent-unit+12expansion controls. New map is explicitly correspondence transport, NOT a newly generated native LVS pairing. Original map and failed baseline are preserved.
Physical41535701378 passed full560DRC with0markers and deep/flat500deviceLVS13. Canonical41537000719 passed all134source controls, all500device/1446terminal identities and113x13layer comparisons for exactly16newVia2. Actual650geometry/fullPHY/closedloopCDRPLL and finalmainchip timing remain open.
Mainchip full64route41513663302 remains the same job. After actual route completion require finalDRC/antenna/globalrouteclasses/diodePG/fullLVS and matchingqualifiedRC/Liberty/all-cornerSTA; route success alone cannot close timing.
All native work/payloads remain in GitHub. Local workspace empty. Existing8hour read-only monitor and automatic_native_dispatch=false unchanged.

Observed 2026-11-02T22:48:14.538133+00:00:
- 41537723922: completed/success
- 41540256258: in_progress/None
- 41513663302: in_progress/None

## Current continuation: actual16Via2 physical and canonical passes; freshRC dispatched

Physical41535701378/sourcee00b2df77c4337940ec7db32159dacc260eb91ab SUCCESS: GDS28eebb9f880648935a6368ada78a5e5666694ba98e073fbbac3f2e0c986339d6 (1079924bytes) passes all560 DRC categories with0markers,deep andflat500deviceLVS,and13 expected fault rejections. Original124HBT/50MOS/98rppd/7MIM/221ptap census retained. This is the analog500device candidate, NOT full-chip or650physical acceptance. Complete native release432027578; derivedartifact13183378339,353107bytes,SHA0073be71d2e29a31dfa12ecd6451d37eb5747faf3514d8a66717fd7228b7cd19. Full derived proof permanently preserved in docs/evidence/clock-access-physical-41535701378.json.

Canonical41537000719/source6aefe5e1cd95b24c9a7fb3bc0c073b57f344c717 SUCCESS. All134source controls passed,including11 new exact-cut/enclosure/spacing/ownership controls. All500device/1446terminal/25port/978anchor identities and238native nets preserved. All113partitions x13layers=1469 complete material comparisons passed. Exactly2changed partitions,layer29 only,288800nm2 each (8newVia2 each). Originalc0d420cd reference and actual28eebb9f candidate independently authenticated;78 current canonical files regenerated. Complete release432034343; artifact13183399167,1450095bytes,SHA13ccd860f80764b388fbdf26e6bee43f1cde715464292282d7143f010501fa31; full derived proof and qualification permanently preserved here.

Initial canonical41536737948/sourceebc7daf2d5c471fd1f81915c1914a09accc85fa4 failed SOURCE CONTROLS ONLY: KLayout Region does not accept a Region as constructor argument. Native job skipped. One fixture-copy line changed to supported Polygon[] constructor; no native material or acceptance predicate changed. Full failure artifact13183678137 retained in clock-access-canonical-control-failure-41536737948.json.

Important actual observed new semantic port order: avdd,avss,sub,ird,cn,cp,dn,dp,irb,ira,irc,ibda,ibdc,ibs0,irx,xp,xn,ibs1,iry,yn,yp,irvx,irvy,vin,vip. yp/yn ordering changed relative to original reference. Bind by actual verified named terminal identity; NEVER reuse old positional order. FreshRC configuration and host exact-order check now both use this actual observed order. Source preparation rejected old-order assumption before any commit or native execution; corrected from actual canonical evidence.

FreshRC41537723922/sourcebd1fc5b2deed8a0ea153db91a362c983e6379254 oncodex/cdr-clock-access-fresh-rc is the next authoritative job. Reservedrelease432038108/tagcloud-results-41537723922-1-cdr-wire-shortcuts-fresh-rc. All frozen numerical/runtime methods,13-command lifecycle,resource/cleanup checks retained. Actual78-file canonical inputs and new semantic order are pinned. Requires real new distributedwireRC and both preciseMIM orders; no original RC result is promoted.

After full freshRC success, authenticate all outputs and compare actual new resistance paths. Then derive model-range200MOS candidate from actual500 model/current physical identities and run unchanged full34.25ns/650device loaded gates. Original rejected650 run41528163238 is the comparison baseline. Check native IDs/terminal bindings rather than assuming prior integer/device or port order. 16via improvement is still UNPROVEN; dense existing collector via arrays and long paths may need actual metal reinforcement if gain insufficient. Actual650geometry/fullPHY/closedloopCDRPLL/final mainchip timing remain open.

Mainchip full64route41513663302 remains SAME job; follow actual outcome, do not restart while live. Final DRC/antenna/globalclasses/diodePG/fullLVS/matchingqualifiedRC/Liberty/all-cornerSTA remain required. Cloud-only native work; local workspace empty.8hour read-only monitor/automatic_native_dispatch=false unchanged.

Observed 2026-11-02T22:30:48.591198+00:00:
- 41535701378: completed/success
- 41536737948: completed/failure
- 41537000719: completed/success
- 41537723922: in_progress/None
- 41513663302: in_progress/None

## Current continuation: actual via candidate generated; full physical verification dispatched

Current collector-access generation41535065105/source381397901390b96a7609f6592918d685d104bfbd SUCCESS. Authenticated complete freshRC41439516945 including original current GDS c0d420cd, all26222 extracted/exported wire resistors, all978 extraction coordinates and13 original conductor unions. Eight full connected-network unit-injection solves pass analytic/reciprocity/refusal controls and energy/KCL checks. C/D upper-emitter to clock-collector effective resistance is11.6977815-12.3574617ohm. Every resistor's contribution and native coordinates are retained; these diagnostics do not constitute new transient results.

Generated actual GDS28eebb9f880648935a6368ada78a5e5666694ba98e073fbbac3f2e0c986339d6,1079924bytes, containing exactly16 extra190nm Via2 cuts:4 each at T054_E,T056_E,T106_E,T108_E. All are within existing same-net M2/M3 with50nm enclosure,240nm spacing and5nm grid. No devices or metal geometry changed. No additional cuts fit at clock collectors under the existing-metal-only search. Exact serialized via-only delta verified. Do not call the candidate a repair success or assume it closes20-49mV headroom deficits. It is still the original500device layout; actual independent650 MOS geometry is not implemented.

Full unchanged560DRC/deep+flat500device LVS13fault verification is41535701378/sourcee00b2df77c4337940ec7db32159dacc260eb91ab oncodex/cdr-clock-access-physical, reservedrelease432027578/tagcloud-results-41535701378-1-cdr-wire-shortcuts-physical. Native driver independently reconstructs16cuts from original candidate/archive/native net ownership before running the exact old checkerSHA3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66. All checker predicates, primitive counts and scoped runtime/resource controls retained. Follow SAME run, do not restart a live job.

Generation archive and original native inputs remain release432024316/tagcloud-results-41535065105-1-cdr-clock-collector-access. Derivedartifact13184480809 is288427bytes SHA8f074fbbf6599c5fa41b464b4b22cb7862e8daf447be462ff53ece82991a4689. Full9JSON outputs are permanently preserved in docs/evidence/clock-access-generation-41535065105.json. Native GDS/RC never downloaded locally.

After physical acceptance, run fresh distributedRC/MIM and compare full650 loaded gates with original41528163238. Preserve rejection if not improved. Resistance ranking also shows substantial clock-collector access and long interconnect contributions; investigate real metal reinforcement/upper-layer shortcuts if16vias have inadequate benefit. Existing clock-collector access already has dense Via1/Via2 rows, so merely repeating via-only generation is not justified. Do not substitute idealized resistance reductions for a physical correction.

Same full64mainchip41513663302 remains authoritative routing job. Final routing/DRC/antenna/fullLVS/diodePG and matching qualifiedRC/Liberty all-corner setup/hold remain open. FullserialGen3x4/closedloopCDRPLL/actual650layout and accepted PCIe/Ethernet chip integration remain OPEN. Cloud-only native execution, empty local workspace,8hour read-only monitor/automatic_native_dispatch=false unchanged.

Observed 2026-11-02T22:16:38.454760+00:00:
- 41535065105: completed/success
- 41535701378: in_progress/None
- 41513663302: in_progress/None

## Current continuation: complete actual650 diagnosis identifies access-wire headroom loss

Diagnosis41532494266/sourcef9a1713ad83a3ea11684c451034b008a82b640c2 SUCCESS. Authenticated the complete current650 native archive from41528163238, rederived the exact model/contract/partition, parsed the entire original34.25ns raw waveform and reproduced original scalar measurements. All9 JSON outputs, including the full13.87MB per-edge stage timings, are preserved without trimming under docs/evidence/cloud-v331-current-stage-41532494266/. This is diagnosis, not a new simulation or physical/electrical acceptance.

At the actual four failing master-clock HBT minima, measured dominant-upper-emitter to clock-collector wire drops are SC_M_CS0=72.998071mV, SC_M_CS1=72.514986mV, SD_M_CS0=53.868987mV and SD_M_CS1=54.729729mV. Corresponding deficits below0.4V are20.457540,21.781687,46.122702 and48.753489mV. Both upper branches and currents are retained. Signed voltage decomposition reproduces each measured Vce exactly. Local clock-edge delays are only a fewps; they do not by themselves explain47-119ps sampler output delays. No causal fix has been proven.

Next concrete physical investigation: inspect actual upper-emitter/clock-collector metal/via access for54/56->61/62 (net$44) and106/108->115/116 (net$598). Current GDS already contains48 Via2 cuts/M3 access repair at upper emitters T054_E,T056_E,T106_E,T108_E from producer41434944363/sourcef878816a24906f450d5ffa2f72b6b08ed6024e6a, release431366909. Actual physical qualification41435641296/source262ac9b4d9142be6235c68d279c67aac9b92e3a8/release431371522 and freshRC41439516945 are the correct basis. Remaining clock-collector access may be a bottleneck; quantify actual resistor paths and owned geometry before changing layout. Do not zero wire resistance or reuse idealized net connectivity as acceptance evidence. Need actual candidate GDS/fullDRC/deep+flatLVS/freshRC and repeated unchanged complete waveform gates.

Previous current650 trial remains electrically REJECTED: phase13.179522mV,VI40.422022uA,A/B/C/D max47.03125/42.65625/118.90625/99.84375ps; four HBT Vce failures. Full actual500 native mapping and50 MOS physical inventory41530232708 passed, but actual650-device geometry has not been generated. Independent MOS-unit active/contact/gate/tap geometry and its full physical checks remain open.

Same mainchip full64route41513663302 continues; do not restart an active run. Once complete, authenticate all route outputs, DRC/antenna, global net classes/diodePG, fullLVS, qualifiedRC/Liberty and final all-corner setup/hold. No full serialGen3x4 PHY or accepted final PCIe/Ethernet mainchip integration is claimed. Native work remains GitHub-only; local workspace empty. Monitor8hours/read-only/automatic_native_dispatch=false unchanged.

Observed 2026-11-02T22:05:12.240564+00:00:
- 41532494266: completed/success
- 41513663302: in_progress/None

## Current continuation: actual650 waveform rejected; complete current MOS geometry mapped

The current-parent200-unit MOS correction ran successfully through actual native binding, the full34.25ns simulation and measurement in41528163238/sourceef607670eaf619fbae377184fb2300a867f66ee6, but electrical gates REJECTED it. Engine0/826.288652164s,113475rows/1302columns,all200 MOS currents. Original13+2 and expanded12 binding controls passed. Phase13.179522mV,VI40.422022uA,A/B/C/D47.03125/42.65625/118.90625/99.84375ps,wrong0/0/3/34. Complete derived text,actual model-domain proof,measurement,preparation,native log and release/index/parts are preserved under docs/evidence/cloud-v330-domain-wave-41528163238/. Raw remains release431986396. Do not rerun this unchanged rejected trial or call it accepted.

Four failing HBTs61/62/115/116 are current schematic SD_M_CS0/1 and SC_M_CS0/1, the C/D master clock switchesNx2, not slave load devices. Exact native pair evidence is in cloud-v330-failed-master-clock-switches.json. Their master input pairs54/56/106/108 areNx4. Continue diagnosis from actual650 raw capture: local input common mode,clock-switch base/emitter,collector/emitter access drops and active-current times, together with sampler settling/hold and XOR/VI propagation. Do not substitute a guessed sizing or relaxed predicate. More detail: docs/cdr-current-domain-wave-and-physical-next.md.

Actual current physical inventory41530232708/source95a55018dc6998dcebc8418a275fe06abc0c6b14 SUCCESS. It authenticated GDS/flatLVS and all500 native identities/parameters/terminal owners, then mapped all50 MOS to unique real PCell enclosures and D/G/S/B shapes. Complete native-derived data is in cloud-v330-actual-geometry-41530232708.json and cloud-v330-current-mos-physical-locations.json; native release431997486. Initial41529608784 exact-top failure and full actual500 pairs remain preserved. Actual GDS has the matched main cell and one unreferenced rppd root; corrected named-top selection does not alter geometry or native LVS.

New650-device layout has NOT been generated. Use these measured current cells/pins to implement explicit units with real contact/tap/routing geometry,full DRC/deep+flatLVS,freshRC/MIM and rerun. Do not promote rejected electrical trial or transfer original500 physical pass. Full serialPHY/closedloopCDRPLL and accepted mainchip integration remain OPEN. Same full64route41513663302 continues; finalSTA is downstream of actual routed candidate/RC/Liberty/fullLVS/diodePG. Monitor8hours/read-only/automatic_native_dispatch=false. Local workspace empty; native work remains cloud-only.

Observed 2026-11-02T21:46:54.690635+00:00:
- 41529608784: completed/failure
- 41530232708: completed/success
- 41528163238: completed/failure
- 41513663302: in_progress/None

## Current continuation: actual current-parent650-device loaded run admitted and dispatched

Current source ef607670eaf619fbae377184fb2300a867f66ee6 on codex/cdr-current-domain-partition now connects the50-to200 independent MOS partition to original freshRC41439516945. Source controls41528032935 SUCCESS:24 partition faults,13 input/context faults and4 projection faults; complete artifact13180506987/7088bytes/SHAf7f617f65c285093acfab0b9e5bcd5b73818afdf23bcb666324f8cba8dd8f386 retained in docs/evidence/cloud-v329-domain-loaded-controls-41528032935.json. Exact7 changed-source files are retained in cloud-v329-domain-loaded-source.json. Candidate source has not replaced root execution.

Actual native run41528163238 was dispatched once at this source. Exact-source release431986396/tagcloud-results-41528163238-1-cdr-current-domain-partition reserved and verified. Follow this handle; do not restart it from observation delay. Host authenticates original500 parent/native runtime, checks the three model files against actual audited pins, derives650-device proposal with200 model-range MOS and unchanged98 resistors/all450 non-MOS/parent wireRC. It retains actual original13 binding refusals+2 equivalent-unit cases and12 expansion faults. All977 voltage/124HBT vectors remain;200 MOS currents give1301 vectors. Only required cardinalities and PD650 labels change; full original numerical gates and34.25ns waveform remain. Complete success/failure and native waves stay cloud-only. Actual preparation or electrical result must be inspected before any pass claim.

Parent,current-only,load-only and combined wide-MOS trials all remain electrically rejected; full evidence retained in v328. No500-device candidate promotion. A successful new provisional wave still requires actual independent-unit PCells,taps/routing,650-device deep+flatLVS/fullDRC,new complete wire/MIM extraction and rerun. Width membership alone is not full model/PVT/closedloop qualification. CompleteCDR/PLL,serialGen3x4 and physical integration remain OPEN.

Same mainchip full64route41513663302 remains the authoritative route job. Do not launch a replacement while live. Its endpoint measures DRC/antenna; original global-class restoration,diodePG,fullLVS and finalSTA acceptance remain downstream checks. Root88-test PCIe functional repair remains integrated. Monitor remains8hours/read-only/automatic_native_dispatch=false. All native computation and artifacts remain GitHub-only; local workspace empty.

Observed 2026-11-02T21:26:27.580482+00:00:
- 41528032935: completed/success
- 41528163238: in_progress/None
- 41513663302: in_progress/None

## Current continuation: isolated load trial rejected; current-parent model-domain correction now source-qualified

Load-only41521089374/source3e15debe2f1d0c165d5e964aee8bbac6ef79e712 completed actual34.25ns,113475rows/1152columns,engine return0 in1027.856699s and was electrically rejected. Phase11.576923mV<30mV,VI35.922831uA<50uA; A/B/C/D42.96875/38.90625/118.90625/50.15625ps all fail37.5ps. Wrong signs0/0/0/0 do not pass amplitude: below100mV counts114/64/160/128. Four HBT low-activeVce failures61/62/115/116 persist. Full non-source derived contents, raw-wave receipt, preparation/controls/model delta/native log, release index and parts manifest are permanently in docs/evidence/cloud-v328-load-only-41521089374/. Native raw/engine remain only in cloudrelease431945564. All four parent/current/load/combined wave results were independently reauthenticated and preserved in docs/evidence/cloud-v328-four-corner-electrical-comparison.json; all remain rejected.

Important current model gap was revalidated: actual runtime's three MOS library hashes match native audit41286495589;42 of50 current single-gate MOS exceed the declared0.15..10um range. Existing original stress checks or LVS do not qualify this model domain. Both old500-device physical handoff documents now explicitly retire promotion of rejected width/load proposals.

Next actual source is codex/cdr-current-domain-partition at9324e2da283540c6d4f1a1bec18641ccec30fefa. It applies only explicit50-to200 independent MOS partition to ORIGINAL current freshRC41439516945, preserving all98 resistors/all450 non-MOS records/parent wireRC/totalW/L/connections. It does not compound the old mixed20 resistor candidate. Initial controls41525549975 and strengthened controls41526131863 both succeeded. Complete strengthened artifact and source proof are retained.24 refusals include balanced11um/7um devices retaining total36um and consistent junctions, rejected specifically by the domain predicate. These controls did NOT execute an actual650-device model, transient or layout. Source branch code is not yet integrated into root execution.

Continue by adapting the actual current-parent loaded host using these explicit units, complete current native500 binding, original13 faults plus12 expanded-binding faults,200 currents and1301 full vectors; retain all original numerical gates. Do not reuse historical native cluster IDs or old mixed20 model hashes. Details and exact four-way metrics: docs/cdr-current-domain-next-native.md. Then actual650-device geometry/DRC/deep+flatLVS/freshRC/waves,closedloopCDR/PLL and full serialPHY/mainchip acceptance remain required.

Keep same full64route41513663302/source302f9c30a847acd659a8c451bdce83707fce5d70/release431900029 running. Its endpoint measures DRC/antenna, not finalSTA; it explicitly leaves original-global-class restoration/diodePG/fullLVS acceptance false. Authenticate final native capsule and required downstream audits before matchingRC/Liberty setup/hold. Root PCIe test dispatch repair remains integrated and88 actual positives41521879475 remain valid within their functional scope. Monitor stays8hours,read-only,automatic_native_dispatch=false. Full serialGen3x4 PHY, accepted mainchip PCIe/Ethernet route and final setup/hold remain OPEN. Local workspace empty; all native work/evidence cloud-only.

Observed 2026-11-02T21:14:49.130163+00:00:
- 41521089374: completed/failure
- 41525549975: completed/success
- 41526131863: completed/success
- 41513663302: in_progress/None

## Current continuation: actual88-test PCIe root repair integrated; analog and routing handles retained

Functional regression41521879475 at sourcea303cf8689479cb693b154c3f63cd7ae7505d93c succeeded. All17 XML invocations, source/method hashes and actual compile/simulation returns are authenticated:25 shared-front,30 training/epoch ingress and33 Gen12 CDC positive tests, no failed/error/skipped XML cases. The unchanged global discovery guard passed. Each filtered command explicitly reports1 separately owned native memory-parity module; this job does not claim memory-parity execution. Complete derived XML/logs/results are permanently in docs/evidence/cloud-v327-pcie-root-pass-41521879475.json.

The tested root-runner dispatch, guarded controller, exact canonical Gen12 source review, protected manifests and workflow template are now copied into the working root. Every61 protected dependency matches the tested source; original RTL, test bodies, original legacy checkers/provenance and current root generic workflow are unchanged. Root closure evidence is docs/evidence/cloud-v327-pcie-integration-closure.json. The canonical validation view checks exactly the two already-present nettype directives; actual compilation always uses the guarded root RTL. Earlier failed admission41518536751 and sparse-completeness41520194928 plus initial55-test pass41521054837 remain preserved. This is functional regression integration, not full serialPHY or physical/timing acceptance.

Continue actual isolated8-resistor load-only41521089374/source3e15debe2f1d0c165d5e964aee8bbac6ef79e712/release431945564. Independent controls41520836968 passed; actual original geometry binder and full frozen wave gates retained. Do not dispatch a replacement while this handle is live. Reject or qualify based on the full actual wave. Prior16-MOS current-only41514109475 was electrically rejected; all complete evidence is in v326.

The real archived native-rppd generator has been located and pinned for a possible physical follow-up, not executed. docs/cdr-slave-load-only-physical-handoff.md identifies how to preserve current collector/source/drain/ground geometry, use actual native PCell pins and net-owned bridges, prove exactly8 changes, retain complete deep/flat LVS and560-category DRC, regenerate full RC/MIM and rerun waves. Historical v58 input hashes and four-device generator cannot be relabelled as current8-device verification.

Continue same actual full64 mainchip route41513663302/source302f9c30a847acd659a8c451bdce83707fce5d70/release431900029. Qualified original input still carries92DRC and21antenna nets27records; final routed result and setup/hold remain unproven. Monitor remains8hours/read-only, overflow repaired; last observer41513825922 was explicitly bounded PARTIAL_OBSERVATION, not a whole-history all-green result. Full serialGen3x4 PHY, accepted mainchip PCIe/Ethernet route and final setup/hold remain OPEN. All native artifacts/work stay cloud-only and local workspace stays empty.

Observed 2026-11-02T20:50:28.727041+00:00:
- 41521879475: completed/success
- 41521089374: in_progress/None
- 41513663302: in_progress/None

## Current continuation: current-only PHY rejected; isolated load-only trial and root PCIe verification active

The16-MOS current-only41514109475/sourced8289b3f57f23b66288cd7851b03ca81bc4954b6 completed its actual34.25ns simulation: engine return0,894.319366s,113475rows/1152columns. It is electrically REJECTED, not a simulator failure. Phase15.796080mV<30mV,VI46.852669uA<50uA; A/B/C/D maximum metric45.78125/41.71875/51.40625/53.28125ps>37.5ps; wrong signs0/0/8/46. Five HBT active-Vce failures include newly failing71(SB_S_LN),0.390572V. Full measurement, every non-source derived text member, native log, prepared state, derivation, controls, native release index and parts manifest are permanently preserved under docs/evidence/cloud-v326-current-only-41514109475/. Raw wave and engine stay cloud-only in release431902569. No48um physical promotion.

Next isolated load-only source3e15debe2f1d0c165d5e964aee8bbac6ef79e712 on codex/cdr-slave-load-only-trial changes exactly8 slave rppd lengths2.6->1.9um from originalfreshRC41439516945, leaving all MOS geometry unchanged. Other492devices and full wireRC retained with exact whole-model/contract reversal. It completes the missing corner of parent/combined/current-only comparison; it may worsen amplitude and must meet the same full gates. Original geometry binder is direct and unmodified. Independent controls41520836968 passed and the complete artifact13177647354 is authenticated/preserved. Actual native run41521089374 dispatched once, exact-source release431945564 reserved. Follow this existing handle. See docs/cdr-slave-load-only-trial.md. No matching GDS/freshPEX or electrical acceptance yet.

Root PCIe regression repair is on codex/pcie-guarded-root-regression, current sourcec574444973148615ea91a192bbcd85d26ef73890. It has NOT yet been integrated into the working root. Initial admission41518536751 failed stale Gen12 source identity; a canonical read-only validation view retains the original exact checker/provenance while actual compilation uses guarded root RTL. Follow-up41520194928 passed source controls and all25 shared/30 epoch actual tests, but both shell runs failed unchanged global completeness because the focused sparse checkout lacked real separate-memory-parity discovery dependencies. All failed logs, XML, actual results and complete second derived artifact text are retained. Current source adds those2 protected dependencies without changing RTL/tests/skip lists/completeness logic. Focused verification41521054837 dispatched once. Inspect actual result before integration;55 Icarus positives do not prove complete serialPHY or chip integration.

Mainchip full64 native routing41513663302/source302f9c30a847acd659a8c451bdce83707fce5d70/release431900029 is the same existing job. Source controls and exact full-chip input qualification passed. Do not restart it from observation delay. Original qualified input remains92DRC(64short+28spacing),21antenna nets27records. This is not a final routed or final-timing pass.

Repaired8-hour observer41513825922 succeeded at loading all838inventory rows and all5 bounded shards from exactv325head. Its result is explicitly PARTIAL_OBSERVATION: active discovery/selectors complete; historical refresh reached the unchanged600GET/time bound and next-history cursor40125733778. Preserve bounded budget/rotation; no false all-history-green claim. Native dispatch remainsfalse. Current job statuses below supersede that older snapshot.

Superseded old build broadCI41460294346 is terminalcancelled; exact hardware/formal/build/general-workflow equivalence to successor41492788476 was verified, existing failures preserved. No CAD/SPICE cancelled. Full serialGen3x4 PHY, accepted mainchip PCIe/Ethernet routing and final setup/hold remain OPEN. All native work and artifacts remain GitHub-only; local workspace empty.

Observed 2026-11-02T20:41:29.090586+00:00:
- 41513663302: in_progress/None
- 41514109475: completed/failure
- 41513825922: completed/success
- 41518536751: completed/failure
- 41520194928: completed/failure
- 41521054837: completed/success
- 41520836968: completed/success
- 41521089374: in_progress/None
- 41460294346: completed/cancelled

## Current continuation: actual current-only electrical stage live; existing route and monitor handles retained

Follow the same dispatched jobs: full64 route41513663302/source302f9c30a847acd659a8c451bdce83707fce5d70/release431900029;16MOS current-only41514109475/sourced8289b3f57f23b66288cd7851b03ca81bc4954b6/release431902569; main live observer41513825922/source5f3814a3e0366b8ec310c9270494c01dd6b3e03c. Independent source controls and both native workflows' source-control jobs passed. At the latest direct observation, current-only loaded-wave job125513614933 is in its authenticate-parent-and-simulate step; no terminal electrical result is available yet. Full64 native-routing125512950978 and monitor observe125515511051 are queued. Do not infer a stopped job or launch replacements from queue delay.

One additional superseded general pushCI41496973308 was cancellation-requested and is now terminal cancelled. Its successor41507901483 remains enabled. Exact ancestor comparison shows only six docs/scripts/workflow files changed, no RTL. Existing old lint/RTL failures remain; cancellation never counts as a pass. Build-branch general CI41492788476 was NOT cancelled: a wider comparison was divergent and did not establish equivalent hardware.

The physical downstream dependency is now pinned in docs/cdr-current-only-physical-handoff.md and docs/evidence/cloud-v325-current-only-physical-handoff.json. Existing physical41435641296 and freshRC41439516945 prove the original36um geometry only. A useful48um electrical result requires actual16-device geometry plus matching schematic, full DRC/deep+flat LVS, new complete mapping/terminal identities, actual intrinsic dimensions and fresh wire/MIM extraction, then the unchanged full loaded-wave gates. Do not reuse parent GDS/RC hashes, assume native IDs survive extraction, or substitute provisional diffusion parameters for extracted ones. This inspection did not generate new layout.

All new job handles, exact-source reservations and complete independent controls are already preserved in v324. Complete rejected previous trial's stage data is preserved in v322. Monitor inventory has838rows in shards below64KiB, schedule remains8hours and automatic_native_dispatch=false. Full serialGen3x4 PHY, accepted mainchip PCIe/Ethernet route and final setup/hold remain OPEN. Native evidence and computation remain GitHub-only; local workspace stays empty.

Observed 2026-11-02T20:05:23.567245+00:00:
- 41513663302: queued/None
- 41514109475: in_progress/None
- 41513825922: queued/None
- 41496973308: completed/cancelled

## Current continuation: actual full64 routing and current-only full-wave experiment dispatched

Full64 native workflow41513663302 is dispatched ONCE at source302f9c30a847acd659a8c451bdce83707fce5d70, branchcodex/mainchip-guide-full64-route. Independent controls41512344559 SUCCESS; exact derived artifact13174561106,5959bytes SHAbfcca00bee1dba67ec6533b5eedf4bf5243145117a9d312ac326e04c4d550f90 authenticated and ALL11JSON members preserved here. All original source-control suites,22 actual-qualification refusals and unchanged11phase bodies passed. Native input control_run41512344559. Exact-source release431900029/tagcloud-results-41513663302-1-mainchip-bulk-postdrt-antenna reserved. Follow this handle; do not dispatch a replacement because it is queued or an observation times out. Actual route must still complete with original47/full64 protections, lower violations and later pass final timing. Prior qualified snapshot retains92DRC/21antenna nets27records; qualification is not completed routing.

PHY current-only native workflow41514109475 dispatched ONCE at sourced8289b3f57f23b66288cd7851b03ca81bc4954b6, branchcodex/cdr-slave-current-only-trial. Independent controls41512921089 SUCCESS, artifact13173972691,1594bytes SHAc29e36dbb70791b1f0b1f4c24cb7869781731f671c6829d7b085d03cc09ec4e3 authenticated and complete derived JSON/log preserved. Controls retain29definitions/5blocks/9frozen source files/13admission refusals,16primitive reversals/14bad cards,16geometry positives/5adapter refusals. Actual13native binding refusals+2unitcases+8actualgeometry faults must still pass before transient. Exact-source release431902569/tagcloud-results-41514109475-1-cdr-slave-current-only-trial reserved. Only16slave NMOS widths36->48um and associated provisional diffusion change; original eight collector resistors and other484devices/parentwireRC remain unchanged. No physical candidate has been accepted. Inspect full actual wave/measurement before proposing further changes; successful fixed-parentRC simulation alone needs matchingGDS/DRC/LVS/freshPEX and rerun.

Monitor repairv323 preserves all835historical records below64KiB per shard. Live main monitor41513825922 dispatched ONCE at5f3814a3e0366b8ec310c9270494c01dd6b3e03c with modeobserve/approved_source. Its main workflow reads exact current working-branch inventory. Follow existing handle and verify acquisition; do not claim a healthy monitor based only on repacking. The preceding41501146100 failure was inventory size, not missing main synchronization. New inventory includes both native handles and this observer; all prior failures remain.

Two superseded pushCI cancellation requests41498680552/41493899500 free hosted capacity; terminal outcomes are recorded below. No actual CAD/SPICE job was cancelled. Complete prior PHY stage diagnosis is permanently in docs/evidence/cloud-v322-slave-stage-41508059395, including full per-bit data and four failed HBTs.

Full serialGen3x4 PHY, accepted mainchip PCIe/Ethernet routing and final setup/hold remain OPEN. All native execution, archives, ODB/GDS and raw waves remain GitHub-only. Local workspace is empty. Continue from existing handles and preserve complete success/failure evidence; never mark goal complete based on controls or diagnostics.

Observed 2026-11-02T19:54:57.860752+00:00:
- 41513663302: queued/None
- 41514109475: queued/None
- 41513825922: queued/None
- 41512344559: completed/success
- 41512921089: completed/success
- 41498680552: completed/cancelled
- 41493899500: completed/cancelled

## Current continuation: monitor inventory overflow repaired without dropping history

The scheduled monitor41501146100 failed because an inventory shard exceeded its unchanged65536byte bound. The main workflow already loads the exact working-branch inventory; this was NOT a missing main synchronization problem. The previous v322 note named the failing guard but did not yet identify this cause.

All835 ordered records are now repacked into contiguous shards below60000bytes, with matching byte counts, Git blob IDs, per-shard SHA256 and unchanged combined ordered-row SHA256. No record, failure or job was removed; monitor source,8hour schedule,request bounds and automatic_native_dispatch=false remain unchanged. Run existing main cloud-progress-monitor.yml mode=observe with approved_source equal current main SHA to verify live acquisition. Do not claim successful observation until that job actually passes loading.

Two obsolete push CI runs41498680552 and41493899500 were cancellation-requested after verifying their branch source had advanced and intervening changes were only scripts/docs/.github. Existing lint/RTL failures remain; cancellation is not pass. Current-source tests and all actual CAD/SPICE jobs remain enabled.

Full64 independent source controls41512344559 succeeded at302f9c30a847acd659a8c451bdce83707fce5d70. Authenticate its derived controls and dispatch actual full64 once with control_run41512344559, then reserve exact-source release. Isolated16MOS current-only controls41512921089 remain their own handle. Complete PHY diagnosis and both candidate source snapshots are preserved in v322. No PHY, chip route or setup/hold acceptance is implied.

Observed 2026-11-02T19:50:16.034850+00:00:
- 41498680552: completed/cancelled
- 41493899500: completed/cancelled
- 41512344559: completed/success
- 41512921089: in_progress/None

## Current continuation: full64 route source and isolated16-MOS trial dispatched for controls; complete PHY stage diagnosis preserved

Actual new-engine full-chip roundtrip41506262574 remains passed: all143820nets154480instances1691protected clocks and ODB/DEF/material snapshots identical; fullDRT92 and21antenna nets/27records remain OPEN. The9.054GB check peak is not routing memory reduction or timing acceptance.

Full64 source302f9c30a847acd659a8c451bdce83707fce5d70 is published on codex/mainchip-guide-full64-route. It explicitly uses the new ELF and authenticates the complete successful actual-chip qualification archive/fixture before routing. Original11phase bodies, original47clear/protection/restore, full64 schedule, original resources/supervision/snapshots and oldELF protection stay intact. Independent execute=false source controls41512344559 is dispatched once. Native full64 has NOT been dispatched. After successful same-source controls, authenticate all controls, dispatch execute=true with control_run41512344559 once, and reserve exact-source empty release cloud-results-RUN-1-mainchip-bulk-postdrt-antenna. Do not restart queued/live handles. Source snapshot including all transitive pins is preserved here.

PHY stage diagnosis41508059395/sourcee6c78d53d05c724c2b4adc83f86aebd47d44d9f7 SUCCESS. Authenticated derived artifact13172382269,1777693bytes SHAabc5ae184c3cfe1e477901bd50afd6f95726a7eb660028edd7e31834b5fcba7d. ALL eight derived members are permanently preserved, including complete13872333byte per-bit stage JSON and1198670byte native device diagnosis. Original complete113475x1152 raw wave remained cloud-only. Controls8 malformed waves+3 stage cases+3 actual24-list cases passed; all old scalar delays reproduced. This is diagnosis of rejected41501239838, not new successful transient.

At C bit8, sampled slave output is28.415mV at0.3UI,120.445mV at0.4UI,173.372mV at0.5UI,99.105mV at0.9UI. It first exceeds100mV and then loses hold margin; do not report118.90625ps as a successful transition time. Eight C bit windows reach that original bounded metric. Clock crossing lag1.5625..4.6875ps remains small relative to sampled data transition failure. A/B/D maxima42.96875/38.90625/49.21875ps still exceed37.5ps. Four master clock HBTs61/62/115/116 retain lowVce failures. Underlying24device trial remains rejected with no matching physical layout.

New isolated electrical proposal source d8289b3f57f23b66288cd7851b03ca81bc4954b6 on codex/cdr-slave-current-only-trial changes only16slave tail MOS widths36->48um plus consistent proposed diffusion, deriving again from original freshRC41439516945. All collector resistors retain2.6um length, all other484devices and parent interconnect RC unchanged. This isolates increased current from prior combined load reduction that coincided with C droop; improvement is a hypothesis. Actual16MOS geometry binding, exact model reversal, all frozen numerical methods, all100mV/37.5ps/voltage/current gates and150fF loads remain. Independent execute=false controls41512921089 is dispatched once; native not dispatched. After SUCCESS, dispatch execute=true once and reserve exact-source release cloud-results-RUN-1-cdr-slave-current-only-trial. A passed provisional circuit still needs matching schematic/GDS/DRC/LVS/freshPEX and repeated loaded simulation.

Source-only branches use skip-ci for frozen-ancestor general push tests; independent source controls and native experiments remain mandatory. Existing broadCI41505377046/41507901483 and their failures remain recorded. Monitor41501146100 FAILED observe/main-inventory guard: it is not a healthy monitor or successful native repair. Root inventory now includes both new handles; main synchronization remains to investigate, and automatic_native_dispatch remainsfalse.

Everything native/heavy is cloud-only; local workspace empty. Full serialGen3x4 PHY, accepted chip PCIe/Ethernet routing, final setup/hold and production acceptance remain OPEN.

Observed 2026-11-02T19:46:50.689885+00:00:
- 41512344559: queued/None
- 41512921089: queued/None
- 41508059395: completed/success
- 41505377046: queued/None
- 41507901483: in_progress/None
- 41501146100: completed/failure

## Current continuation: actual new-engine full-chip qualification PASSED and authenticated

Native41506262574/source64a21283a014b802329e295d1136ae1ec645fee0 SUCCESS, host PASS_CLOUD_GUIDE_ENGINE_ACTUAL_CHIP_QUALIFICATION, inner PASS_GUIDE_ENGINE_ACTUAL_CHIP_QUALIFICATION, result PASS_ACTUAL_CHIP_ENGINE_ROUNDTRIP_AND_FULL_CHECKS. No terminal errors; every host/native command0; container exit0/noOOM, original source/runtime protected. Actual inner677.265687seconds, peak9054203904bytes under12GiB; this is snapshot/check memory, NOT routing RSS reduction.

ALL143820nets154480instances1691protected clocks and full material/wire snapshot remain byte-identical across old engine, new-engine load, write/reload and full DRT/antenna measurement. Full snapshot624857592bytes SHAbb626be69f89e559432104cec5404ef1831917b230c11db0c03dfc01e91ecba0; DEF186096898bytes SHA68fe1bb0329424c421d4c0a6bc0d20e444ca7ab43e425413ae95498e57990fd4; even ODB rewrite214392179bytes SHAe460c8d0751ad9d22042a2e133103e0853048110fb0b2747c04ced44eb284d4e equals input. Full DRT92=64short+28spacing and21antenna nets/27records exactly match old engine. No routing/repair occurred; no physical/timing/fullPHY acceptance.

Authenticated derived artifact13171308389 212137bytes SHA96cf31b611eecd8556ef76144e976f5edc64d7bfcf0319bd6e6d0f20aa114461; relevant complete derived records, supervision, actual command streams, result, container and permanent-publication records copied here. Release431857262 contains native archive314976709bytes SHA13cf17f6d75294cc2444013b5cfa321c50d676b29ac4975b87c257578c400bb3 (asset702897085), exact index702896826/parts702896941. Native archive was NOT downloaded locally. scripts/mainchip-guide-engine-qualified-inputs.json pins producer/allassets/fullindex/parts and selected qualification evidence for the next cloud-only full64 consumer. Actual captured fixture is docs/evidence/mainchip-guide-engine-qualification-fixture.json. Keep built-engine manifest unchanged; qualification is separate.

NEXT MAINCHIP: implement explicit new-engine full64 host/inner based on unchanged sourcef808321a65ca9197f10e75f2f59073d47095a718 scripts/cloud_mainchip_snapshot_reload.py and mainchip_snapshot_reload_inner.py, with original11phases, original47clear/protection/restore, all1691clocks, full64 schedule, route snapshots, original memory/supervision/cleanup. Authenticate complete successful qualification capsule and actual result/runtime/engine binding before execution; keep old ELF separately protected. Use new ELF /work/guide-engine/openroad explicitly, never silently overwrite c.ENGINE. Retain all original source tests and updated transitive manifests. Independent same-source controls and external release reservation required. No new full64 source/dispatch has been published yet; original source investigation is RAM only. Current original seed exact snapshot20 and selected47 plan remain pinned; no claimed internal router-state resume. New engine route must still actually complete, lower DRC/antenna, preserve full scope and pass eventual timing.

CURRENT PHY read-only stage diagnosis41508059395/sourcee6c78d53d05c724c2b4adc83f86aebd47d44d9f7, branchcodex/cdr-slave-drive-stage-timing. It uses actual proposed composition and full rejected41501239838 wave; parser/stage controls plus actual24-list fixture and3malformed-list refusals precede native archive acquisition. Prior41507270587 was cancelled while queued because source compared delta list to integer; do not restart it. Follow current handle and permanently preserve full derived stage/per-bit/clock results when terminal. Underlying24device trial remains electrically rejected, no matchingGDS/freshPEX: phase12.974mV, VI39.692uA, C worst metric118.90625ps, four lowVceHBTs. No new proposed geometry accepted.

Superseded push CI41504869013/source0423d948 and41507164455/sourcee9ebe92 were cancellation-requested to release hosted capacity; current-source push checks41505377046/41507901483 remain enabled. Existing failures preserved; cancellation never counts as pass. Historical41504869013 lint failure was missing default_nettype guards in soc_pcie_gen12_raw32_align.v. Current root already adds exactly the two guards and otherwise retains identical bytes (comparison+full log preserved here); no new RTL edit or whole-root lint pass claimed.

Everything native/heavy remains GitHub-only; workspace empty. Readonly8hour monitor automatic_native_dispatch=false. Full serialGen3x4 PHY, accepted mainchip PCIe/Ethernet route and final setup/hold remain OPEN. Qualification success is permission to test actual new routing, not production signoff.

Observed 2026-11-02T19:30:20.133310+00:00:
- 41506262574: completed/success
- 41508059395: completed/success
- 41504869013: completed/cancelled
- 41507164455: completed/cancelled
- 41505377046: queued/None
- 41507901483: in_progress/None

## Current continuation: actual-chip qualification and complete slave-drive stage diagnosis

The first stage reader41507270587/sourcee9ebe92ef4023990a0ad9a23c19eb4b604eaccc7 was CANCELLED while queued, before runner execution (classify job had no steps). Source review found the 24-element derivation delta list was compared to integer24. This is a source guard defect, not electrical failure. Corrected sourcee6c78d53 validates the actual list, unique exact24 native IDs and changed parameter records. Source controls now consume the authenticated real captured derivation fixture and refuse integer/missing/duplicate-device forms before archive acquisition. Old source, queued state and cancellation remain preserved. Corrected reader41508059395 was dispatched once; follow it, never restart cancelled41507270587.

CURRENT MAINCHIP NATIVE41506262574, source64a21283a014b802329e295d1136ae1ec645fee0, branchcodex/mainchip-guide-engine-roundtrip; reserved release431857262/tagcloud-results-41506262574-1-mainchip-bulk-postdrt-antenna. Independent controls41505439588 and same-run source-controls passed. Exact engine41493369685 versus recovered full chip41440285882; full143820net/154480instance/1691clock native snapshot and DEF before/after actual ODB rewrite, original fullDRT/antenna and post-check full-scope equality. Old ELF/runtime/source/supervision preserved. Follow this handle; no duplicate dispatch on polling delay. Terminal native PASS, all checks and full permanent capsule must be authenticated before full64 routing. Zero current route/repair calls and no convergence/memory-saving/timing acceptance merely from this qualification.

CURRENT PHY READ-ONLY DIAGNOSIS41508059395, sourcee6c78d53d05c724c2b4adc83f86aebd47d44d9f7, branchcodex/cdr-slave-drive-stage-timing. Authenticates the entire native archive from electrically rejected41501239838, all original1152columns/113475rows and scalar reproduction. Uses ACTUAL proposed composition native/provisional-bias-model/composition.json SHA071b2c83a130de7b1a0483735f4b8297cfe48657a8616fd95981e703a96e23cf, not old parent composition. Requires actual24device derivation, unchanged other476devices/full wireRC, exact trial composition/planes pins,8actual geometry faults,13original binding faults,2unit-equivalence cases and explicit false matching-layout/freshPEX/PHY flags. The original48HBT stage-role mapping and all parser/clock/per-bit algorithms remain byte-identical; all48HBT parameters/native terminals must match the independently LVS-derived roles. It measures master/slave data arrivals, local clock brackets and complete native delays/margins, reproduces all original gate scalars. It is diagnosis of an existing rejected waveform, not another transient or relaxed acceptance. Workflow first runs original frozen-wave parser and stage controls, then full cloud-only archive/wave analysis. Complete derived stage output must be authenticated and permanently preserved after terminal completion; native wave/archive must never be fetched locally.

PHY41501239838 is terminal ELECTRICALLY REJECTED, engine0, full capture preserved. Rootv317 contains complete measurements,8geometry controls,13binding refusals/2unit cases, source/derivation/runtime metadata, release431828783 pins. A/B/C/Dwrong0/0/0/0; delays42.96875/38.90625/118.90625/49.21875ps>37.5, phase12.974mV<30, VI39.692uA<50 and four HBT61/62/115/116 low activeVce remain. The read-only follow-up is specifically to isolate C's regression before deciding a new parameter change. Do not promote this24device trial into GDS/layout; no matching layout/freshRC.

Previous engine source-control stale transitive pin failure41504918363 is preserved; corrected controls41505439588 full10JSON evidence is rootv3181fab74aad99b173671a6133e9bce99667e475755. Historical push CI formal-and-boot lint failure on41504869013 is separately recorded; do not present narrow controls as all-CI success.

All native CAD/SPICE/raw waves/GDS/ODB/archives stay GitHub-only. Local workspace empty. Readonly8hour monitor remains automatic_native_dispatch=false. Full serialGen3x4 PHY, accepted mainchip PCIe/Ethernet route, final setup/hold and production approval remain OPEN.

Observed 2026-11-02T19:15:12.781416+00:00:
- 41508059395: queued/None
- 41507901483: pending/None
- 41506262574: in_progress/None
- 41507270587: completed/cancelled

## Current continuation: actual-chip qualification and complete slave-drive stage diagnosis

CURRENT MAINCHIP NATIVE41506262574, source64a21283a014b802329e295d1136ae1ec645fee0, branchcodex/mainchip-guide-engine-roundtrip; reserved release431857262/tagcloud-results-41506262574-1-mainchip-bulk-postdrt-antenna. Independent controls41505439588 and same-run source-controls passed. Exact engine41493369685 versus recovered full chip41440285882; full143820net/154480instance/1691clock native snapshot and DEF before/after actual ODB rewrite, original fullDRT/antenna and post-check full-scope equality. Old ELF/runtime/source/supervision preserved. Follow this handle; no duplicate dispatch on polling delay. Terminal native PASS, all checks and full permanent capsule must be authenticated before full64 routing. Zero current route/repair calls and no convergence/memory-saving/timing acceptance merely from this qualification.

CURRENT PHY READ-ONLY DIAGNOSIS41507270587, sourcee9ebe92ef4023990a0ad9a23c19eb4b604eaccc7, branchcodex/cdr-slave-drive-stage-timing. Authenticates the entire native archive from electrically rejected41501239838, all original1152columns/113475rows and scalar reproduction. Uses ACTUAL proposed composition native/provisional-bias-model/composition.json SHA071b2c83a130de7b1a0483735f4b8297cfe48657a8616fd95981e703a96e23cf, not old parent composition. Requires actual24device derivation, unchanged other476devices/full wireRC, exact trial composition/planes pins,8actual geometry faults,13original binding faults,2unit-equivalence cases and explicit false matching-layout/freshPEX/PHY flags. The original48HBT stage-role mapping and all parser/clock/per-bit algorithms remain byte-identical; all48HBT parameters/native terminals must match the independently LVS-derived roles. It measures master/slave data arrivals, local clock brackets and complete native delays/margins, reproduces all original gate scalars. It is diagnosis of an existing rejected waveform, not another transient or relaxed acceptance. Workflow first runs original frozen-wave parser and stage controls, then full cloud-only archive/wave analysis. Complete derived stage output must be authenticated and permanently preserved after terminal completion; native wave/archive must never be fetched locally.

PHY41501239838 is terminal ELECTRICALLY REJECTED, engine0, full capture preserved. Rootv317 contains complete measurements,8geometry controls,13binding refusals/2unit cases, source/derivation/runtime metadata, release431828783 pins. A/B/C/Dwrong0/0/0/0; delays42.96875/38.90625/118.90625/49.21875ps>37.5, phase12.974mV<30, VI39.692uA<50 and four HBT61/62/115/116 low activeVce remain. The read-only follow-up is specifically to isolate C's regression before deciding a new parameter change. Do not promote this24device trial into GDS/layout; no matching layout/freshRC.

Previous engine source-control stale transitive pin failure41504918363 is preserved; corrected controls41505439588 full10JSON evidence is rootv3181fab74aad99b173671a6133e9bce99667e475755. Historical push CI formal-and-boot lint failure on41504869013 is separately recorded; do not present narrow controls as all-CI success.

All native CAD/SPICE/raw waves/GDS/ODB/archives stay GitHub-only. Local workspace empty. Readonly8hour monitor remains automatic_native_dispatch=false. Full serialGen3x4 PHY, accepted mainchip PCIe/Ethernet route, final setup/hold and production approval remain OPEN.

Observed 2026-11-02T19:10:41.525746+00:00:
- 41507270587: queued/None
- 41507164455: queued/None
- 41506262574: in_progress/None

## Current continuation: actual-chip new-engine qualification dispatched after independent controls

CURRENT NATIVE HANDLE41506262574, exact source64a21283a014b802329e295d1136ae1ec645fee0, branchcodex/mainchip-guide-engine-roundtrip. Independent controls41505439588 SUCCESS at this exact source, native skipped in control run. Authenticated derived control artifact13170743240,5112bytes SHAcdd2449271644f8e13f9153c547a91b4d0b73d78f7de24c7fda63eb8a3b5ce65; all10JSON records permanently copied here. Eight original suites and new2positive complete archive transports/16hostile refusals passed. Previous stale-transitive-pin failure41504918363 and corrected pin cascade remain preserved in v317.

Native run41506262574 was dispatched once with execute=true/control_run=41505439588. Externally reserved release431857262/tagcloud-results-41506262574-1-mainchip-bulk-postdrt-antenna is bound directly to the exact tested source; it must preserve complete success/failure. Follow this specific handle; queued/in_progress or an observation timeout is NOT a reason to dispatch again. Actual job status recorded below. Qualification is NOT yet accepted merely because controls passed or the run started.

The run authenticates complete native engine41493369685 and restored-chip41440285882 archives inside GitHub. Exact new ELF separate from immutable original. Actual full143820nets/154480instances/1691clock snapshot and DEF must equal old reference, survive ODB write/reload, and remain equal after unchanged fullDRT/antenna Tcl; measured reports must equal old reference. Runtime, image, source, cgroup, supervision/cleanup and permanent output preservation checks remain enforced. Zero route/repair calls. Only an actual terminal PASS with full measurement and capsule evidence authorizes the next original full64 routing experiment. Source/config/docs are copied to rootv317; runnable workflow and transitive manifest closure live on the exact feature source above.

PHY41501239838 is TERMINAL/ELECTRICALLY REJECTED, not running. Rootv317cb2a34f40518b9fbad355f4789b72d0af3dd3d43 preserves its complete derived measurement/control/derivation/runtime result and release metadata. Actual native engine returned0; full113475x1152 waveform34.25ns preserved in release431828783. Native binding all8paired geometry faults plus original13refusals and2unit cases passed. A/B/C/D wrong signs0/0/0/0, but delays42.96875/38.90625/118.90625/49.21875ps exceed37.5; phase12.97409175mV<30; VI39.69184228uA<50. HBT61/62/115/116 remain below0.4V activeVce. Do not promote24device proposed geometry into layout; parent RC was held fixed and no matchingGDS/freshPEX exists. Next PHY work should use complete authenticated current/parent waves to isolate C timing/swing and remaining clock-tail headroom.

Push checks41504869013 and41505377046 are separately tracked; broad push CI is not identical to the specific independent source controls. Historical-base push job formal-and-boot in41504869013 reported whole-SoC lint failure; this is preserved in snapshots and is not hidden by successful qualification controls. Do not claim all CI passes.

All heavy/native work and archives remain GitHub-only; local workspace empty. Readonly8hour monitor remains automatic_native_dispatch=false. Full serialGen3x4 PHY, accepted mainchip PCIe/Ethernet route and final setup/hold remain OPEN. No physical/timing/production acceptance from source controls or engine build.

Observed 2026-11-02T19:04:56.217512+00:00:
- 41505439588: completed/success
- 41506262574: in_progress/None
- 41504869013: in_progress/None
- 41505377046: pending/None

## Current continuation: actual new-engine chip qualification implemented; slave drive trial electrically rejected

Guide engine qualification source64a21283a014b802329e295d1136ae1ec645fee0 on codex/mainchip-guide-engine-roundtrip implements whole-chip comparison with exact engine41493369685 and recovered reference41440285882. New ELF remains separate /work/guide-engine/openroad; old frozen engine/source/runtime/lifecycle preserved. Authenticates all engine and chip capsule members, including unselected files, exact producer/source/releases/asset IDs, full hashes, directory census and no symlinks/aliases. New native phases: full143820net/154480instance/1691clock old-engine snapshot+DEF equality, actual ODB write/reload equality, unchanged fullDRT/antenna Tcl and exact complete measurement comparison, full post-check snapshot equality. Zero routing or repair calls; no memory reduction, convergence, LVS, PHY or setup/hold acceptance claimed.

First source controls41504918363/source0423d9480918fd98e7ce94d709040ef8c5b50dae correctly refused stale transitive workflow pins in mainchip-full64-pins.json before native dispatch; full log preserved here. Corrected only cascading three pin manifests, retained all eight original control suites and added two positive archive transports plus sixteen malicious capsule refusals, original lifecycle/resource equality and explicit new ELF/runtime binding. Corrected independent controls41505439588 is current. Follow it, authenticate its artifact and only after success dispatch native execute=true with control_run=41505439588 at exact corrected source; externally reserve its unique release as prescribed by host. Do not rerun failed source controls or call a build pass full-chip qualification. Native qualification has not yet been dispatched at this checkpoint.

PHY41501239838/source4aeff85064492459822c36dcec869aae87f44be4 FINISHED and was ELECTRICALLY REJECTED. This is different from prior pre-transient binding failure41499547929: actual500-device geometry binding passed all8paired faults; original13binder refusals and2equivalent-unit cases passed; engine returned0 after1070.412seconds and produced full113475rows1152columns34.25ns waveform. Full raw1045823299bytes SHA2507f874be9fa67550e12262d7eb8a752bf75db96ccd68f72ba29f24ccbf748b remains GitHub-only. Sources unchanged. Derived artifact13170781492 1423785bytes SHAe7b64e17db437cc37d7dd1d28e22267fb7afa0e7da0d57e81a98bb2f7b8b765a authenticated; full measurement, geometry controls, derivation, engine, config, prepared state, publication and failure records copied here.

The24device trial reduced A/B/D worst delays to42.96875/38.90625/49.21875ps versus original45.78125/41.71875/54.53125; C worsened51.09375->118.90625ps, all exceed37.5ps. A/B/C/D wrong-sign counts0/0/0/0 (original0/0/2/34) but below100mV counts123/64/129/128of765 remain. X/Ywrong383/44 and below100mV741/680. Phase12.97409175mV<30mV, VI39.69184228uA<50uA; original14.325205mV and43.0512336uA. Four HBT61/62/115/116 minimum activeVce0.337347154/0.334221321/0.372771895/0.370736187V<0.4. No individual MOS terminal-voltage or MIM cap-voltage gate failures in this run. Do not mistake improved signs for acceptance. Release431828783 permanently preserves complete native output in four parts plus exact index/parts. Fixed-parent-RC geometry experiment only; no matching layout/freshPEX/fullPHY claim. Do not promote this trial into mainchip layout. Next PHY work must diagnose C timing/swing and remaining clock-tail headroom using authenticated complete waves; avoid inferring that lower collector resistance and higher MOS width solve all stages.

All native CAD/SPICE/raw waves/GDS/ODB/archives stay in GitHub. Local workspace remains empty. Monitor stays readonly every8hours with automatic_native_dispatch=false. Full serial Gen3x4 PHY, accepted mainchip PCIe/Ethernet routing and final setup/hold remain OPEN. Last retained mainchip92DRT/21antenna; no new routing/timing/production closure.

Observed 2026-11-02T19:00:25.681610+00:00:
- 41505439588: in_progress/None
- 41505377046: pending/None
- 41504918363: completed/failure
- 41504869013: in_progress/None
- 41501239838: completed/failure

## Current continuation: complete bounded-worker engine built and metadata authenticated

Corrected full OpenROAD build41493369685/source851db8f517c03cffd0afeb6527e281bd9353f5d2 SUCCESS. Full project compiled, Tcl/Python interface smoke tests and ldd completed. Host status PASS_COMPILED_ENGINE_INTERFACE_ONLY; inner PASS_COMPLETE_OPENROAD_BUILD_AND_INTERFACE_SMOKE_ONLY. No terminal errors. Inner2815.861seconds, host2901.347seconds; cgroup peak3712278528bytes, no OOM under12GiB. This is NOT actual-chip routing qualification.

Actual binary108936520bytes SHAef4b5d3cdfba609be0a57fbf1debc21ed94dff3b331255c6e9d194028e1bd224. Sourcebefore/sourceafter1492875bytes SHA8edcc701e021736baa64882de235a179e3a6e75677862eaf07c3550d1ebfbaa3 identical. DerivedFlexDR78757bytes SHA892a9771d911cf8ed350ffe4d42683b16561f3989f1e7c8302a02f8016328d9e. Full build configuration3671compilecommands, GUI/tests/LTOoff, Pythonon. Runtime104dependencies16940bytes SHA6651a9b0b0059ed4b6ebfa5cb016a2ce08c146196d357fa1283ebf57eb6619a0 is identical to the old qualified runtime. Container imageIDa958d3bee9c5261b26e221e1c1461c92f830f14293bc5050848653bd7ec8d185 matches original route image.

Release431773741/tagcloud-results-41493369685-1-mainchip-guide-batch-engine-build has14assets. Native archive40,899,271bytes SHA551cfed25c0a4b1aae6f6af748ead7167b41ea89d481c0db434f8c2c9d9bd6be, asset702752450. Native archive/binary were NOT downloaded locally. All13 directly published JSON metadata assets, release/tag metadata are authenticated by bytes/SHA and permanently copied here. scripts/mainchip-guide-engine-built-inputs.json records exact producer, all asset pins, complete output index, archive parts, binary, runtime and image for the next cloud-only consumer. It grants no physical/routing acceptance.

NEXT MAINCHIP IMPLEMENTATION: new no-route actual-chip qualification using recovered whole chip before any full64 routing. Original recovery source0990e2971dee0333598a59a033dfe4f1f1f4215b and frozen base7a0776718ec37a106b7dfde0cbd477c6a2a5522f retain acquisition/full-scope audit methods. Actual recovered41440285882/release431403455 contains reference restored native snapshot/DEF. Authenticate all producer archives and use new ELF in a separate explicit path while preserving old frozen engine/source checks; do not silently overwrite c.ENGINE. Runtime is byte-identical but still measure ldd again in new job. Compare full143820nets/154480instances and all1691protected clocks plus all wire geometry against actual old recovered reference; run full DRT/antenna. Original recovery measure() hardcodes selected47_routing_executed=True and cannot substantiate a new no-route claim; explicit new scope/result required. Only after this pass may new ELF run original full64 route. No new full64 or actual-chip qualification has been dispatched at this checkpoint.

PHY: corrected native slave-drive trial41501239838/source4aeff85064492459822c36dcec869aae87f44be4 remains current; release431828783/tagcloud-results-41501239838-1-cdr-slave-drive-trial. Actual status recorded below. Independent controls41500976761 passed24primitive roundtrips/14refusals,16geometry roundtrips/5refusals, original29definitions/5blocks/9files/13admission refusals. Require actual8geometry mutations plus13original binding refusals and2unit-equivalence cases before interpreting the waveform. Model changes remain24slave devices only, fixed parent interconnectRC, original stimulus/clock/150fFloads/gates. Never redispatch earlier pre-transient failure41499547929; it and both rejected bias trials are permanently preserved.

Rootv315c7432eefb3d3f0105aa61f9eecb3b45a6f571848 includes detailed geometry correction/previous failure; v3138df4bb006ef1a256ab7a0c3115b454aa75ef428a preserves full original-wave stage diagnosis41497066977 and balanced electrical rejection41494299114. Follow the actual live PHY handle, not old checkpoints' pre-dispatch instructions.

All native work/payloads remain GitHub-only; local workspace empty. Readonly8hour monitor automatic_native_dispatch=false. Full serial Gen3x4 PHY, accepted mainchip PCIe/Ethernet route and final setup/hold remain OPEN. Last retained route92DRT/21antenna; no timing/production closure claimed.

Observed at 2026-11-02T18:39:06.150165+00:00:
- 41493369685: completed/success
- 41501239838: in_progress/None

## Current continuation: exact proposed MOS binding corrected; new native trial dispatched

This v315 entry supersedes v314. Follow new native trial41501239838; never redispatch old terminal41499547929.

First slave drive attempt41499547929/source522ac9b2736a3445c839ac6dfcf25bf245ab78d1 FAILED BEFORE SIMULATION. All24 proposed primitive changes and whole-model/contract reversal completed. Frozen bind_native line37 then refused48um: it intentionally encodes the original width list/census and36um tail groups. No transient command, engine result or measurement was produced. This is a geometry-admission/setup failure, not an electrically rejected simulated circuit. Release431819162 permanently retains complete capsule; derived13167768061=1132986bytes SHA2da04151cc7b42011348c3e88e939c24947080dbbe0f853aca9bc695cfb74e18. Full failure trace,24device derivation and source controls are copied here.

CORRECTED SOURCE4aeff85064492459822c36dcec869aae87f44be4 on codex/cdr-slave-drive-trial, four changed files read back byte-exact. New scripts/cdr_slave_drive_binding.py requires exact16 selected slave MOS IDs, all proposed parameter tokens, original terminal clusters/names and actual card order. It reverses only those16 MOS geometries in a read-only memory copy, calls complete original bind_native for topology and all other geometry, then returns actual48um/diffusion parameters to frozen preparation/measurement. The simulator always reads the actual proposed candidate file. The reversed copy is neither written nor simulated. Original numerical source bodies, every preparation/measurement gate,all clock/stimulus/load values remain unchanged; no blanket48um acceptance was introduced.

Independent source-controls41500976761 SUCCESS. Artifact13167174740=1623bytes SHA0c6f3da3a6c37c525728c71589d72d6b80cea11250fb3f1addf53f40057a22e7. Original29definitions/5blocks/9files/13admission refusals and24primitive roundtrips/14card refusals retained. Added16geometry roundtrips/5paired-parameter,terminal,identity refusals passed. These are source-only controls; actual native binding is not claimed by them.

NEW NATIVE TRIAL41501239838/source4aeff85064492459822c36dcec869aae87f44be4; independently reserved release431828783/tagcloud-results-41501239838-1-cdr-slave-drive-trial points to exact source. Observe actual job state below. Before engine execution, actual full500 geometry binding must run8 extra paired card+contract faults (width,length,area,perimeter,ng,m,RFmode and an unselected master borrowing48um) and show the original binder alone refuses the new geometry. Original13binding refusals and2HBT equivalent-unit cases still run in actual preparation. Follow the same handle until terminal; do not restart on observation timeout.

Circuit proposal remains exactly24 devices from original freshRC41439516945: eight slave collector rppd loads L2.6->1.9um,W32; sixteen slave tail MOS W36->48um,L0.3,AD/AS16.32p,PD/PS96.68um. Other476devices and every parent interconnectR/C unchanged under byte-exact model/contract reversal. No previous failed input-bias modification is compounded. All150fF test loads and original electrical gates retained. Fixed parent interconnect RC is provisional: matching GDS,DRC/LVS,canonical terminals,newRC and repeated loaded simulation are required before any promotion.

Rootv3138df4bb006ef1a256ab7a0c3115b454aa75ef428a retains complete original-wave stage diagnosis41497066977 and balanced-bias electrical rejection41494299114, including full per-bit/crossing records and all failed HBT gates. These remain failures/diagnostics, not accepted PHY.

MAINCHIP current handle remains corrected engine build41493369685/source851db8f517c03cffd0afeb6527e281bd9353f5d2,release431773741. No fresh chip route has been measured. After success authenticate binary/runtime and run full143820net/154480instance no-route roundtrip, all-wire/protected1691clock comparison and full DRT/antenna before full64 route. Original image matches new build image exactly; old engine constants must not be silently overwritten. Old inherited measure() hardcodes selected47_routing_executed=True, so a new no-route qualification must not reuse that claim as current routing evidence. Last retained chip92DRT/21antenna; fullPG/LVS/freshRC/finalSTA still open.

All native work and payloads remain GitHub-only; workspace empty. Readonly8hour monitor retains automatic_native_dispatch=false. Full serial Gen3x4 PHY, accepted mainchip PCIe/Ethernet route and final setup/hold remain OPEN.

Observed at 2026-11-02T18:34:31.024143+00:00:
- 41499547929: completed/failure
- 41501239838: in_progress/None
- 41500976761: completed/success
- 41493369685: completed/success

## Current continuation: slave drive native trial dispatched after successful independent controls

This v314 entry supersedes v313's pre-dispatch instruction. DO NOT dispatch a second slave trial.

Native electrical trial41499547929/source522ac9b2736a3445c839ac6dfcf25bf245ab78d1 is now dispatched on codex/cdr-slave-drive-trial. Independently reserved release431819162, tagcloud-results-41499547929-1-cdr-slave-drive-trial points to the exact tested source. Observe its actual jobs below and follow this same handle until terminal; an observation timeout is not a stopped job.

Independent source-controls41498753635 SUCCESS, derived13167902243=1492bytes SHAb3ce0104b6e9e40f00e532fe5ee0bbd52855bf0aa19a3caba56261a28f21b5b7. All24 primitive roundtrips and14 card refusals passed alongside original29definitions/5blocks/9files/13admission refusals. Actual preparation still requires original13binding refusals and2unit-equivalence cases. This is source-control success, not electrical/physical acceptance.

The full500 original-parent-RC experiment changes only24 slave devices: eight load resistor L2.6->1.9um,W32; sixteen tail NMOS W36->48um,L0.3 with consistent provisional AD/AS16.32p and PD/PS96.68um. External clock, stimuli,150fF test load, voltage/current-density and final waveform gates remain original. Other476 devices and all parent interconnect R/C are byte-exact unchanged under whole-model/contract reversal. Failed bias experiments are not compounded. No matching geometry or new extraction is claimed.

v313 root8df4bb006ef1a256ab7a0c3115b454aa75ef428a permanently preserves full sampler-stage diagnosis41497066977 (including13,871,621byte per-bit/crossing JSON) and balanced-trial41494299114 failure/measurement/provenance. Full-wave stage diagnosis reproduced every original sampler delay, identified local clock-crossing delay1.5625..4.6875ps, and motivates this actual drive/load experiment. It did not itself improve delay.

Corrected engine build41493369685/source851db8f517c03cffd0afeb6527e281bd9353f5d2 remains the current routing-engine handle. On success authenticate binary/runtime then require fresh full143820net/154480instance no-route roundtrip, protected1691clock/all-wire scope comparison and full DRT/antenna before full64 routing. No new chip route or setup/hold closure is claimed. Last retained chip has92DRT and21antenna nets.

All native work/artifacts remain cloud-only. Full serial Gen3 x4 PHY, accepted mainchip PCIe/Ethernet routing and final setup/hold remain OPEN. Readonly8hour monitor stays automatic_native_dispatch=false. Next action: inspect these exact two native results, preserve complete failures, and promote no provisional parameter trial without matching GDS/DRC/LVS/freshRC/loaded verification.

Observed at 2026-11-02T18:23:05.739225+00:00:
- 41499547929: completed/failure
- 41498753635: completed/success
- 41493369685: in_progress/None

## Current continuation: full-wave stage diagnosis complete; balanced bias rejected; slave drive trial source published

All native CAD, SPICE, GDS/ODB, raw waves and native archives remain GitHub-only. Local source/API/derived text are RAM-only; workspace remains empty. Full serial PCIe Gen3 x4 PHY, accepted mainchip route and final setup/hold remain OPEN.

MAINCHIP: keep following corrected complete-engine build41493369685/source851db8f517c03cffd0afeb6527e281bd9353f5d2 on codex/mainchip-guide-batch-engine, release431773741. Its build status is recorded below; never restart on observation timeout. Two-worker lifetime patch is not yet qualified on a routed chip, and no new route/timing improvement is claimed. Current retained chip remains92DRT=64short+28spacing and21antenna nets; all1691protected clock wires were unchanged in recovery41440285882. After actual successful engine build and runtime authentication, require full143820net/154480instance/no-route roundtrip and original protected wire/clock comparison plus full DRT/antenna before full64 routing. Do not silently change old c.ENGINE or drop frozen-source/runtime checks.

BALANCED BIAS41494299114/source df723c791fec2621585c80fb56409d65b5811b44 completed and FAILED original electrical acceptance. Engine returned0, whole transient complete, sources unchanged; all native records sealed in release431779366. Derived13166113737=1409781bytes SHA904b21b197686f66d1911c758dabbbd14dbda350f9104c9040e05fae96d04ec4. Complete measurement, engine, derivation, publication and failure records are preserved here.

Balanced C critical Vce .421640/.420208V exceeds0.4V; D .389873/.386994V still fails. This does not mean all other device gates passed: the comparison JSON retains every failed HBT gate including all-time overvoltage. Phase14.590486mV<30mV still fails. A/B/C/D output maxima45.78125/41.71875/51.09375/54.21875ps exceed37.5ps; wrong signs0/0/1/33 and below100mV129/128/128/128of765. XOR comparisons also fail. This provisional fixed-parent-RC experiment is rejected and not promoted to geometry; the original and pull-up-only failure remain intact.

SAMPLER STAGE DIAGNOSIS41497066977/sourcef3bbcddef55b19194cce675f91a0bb265b577bce SUCCESS. Derived13166219492=1776044bytes SHA9464d8a319a1b733724f8cdacabe95bf3c79ce3141d9c15bb25d4a265b52189d. The full original native wave from41441047354 was authenticated and parsed in cloud. All48 master/slave data and selector HBTs were joined by actual full500 LVS mapping41450661063, native IDs, parameters and all terminal clusters. Every original per-bit sampler delay and original scalar measurement reproduced. All16 selector-pair local crossing comparisons had unique matches, no missing/ambiguous reference edges. Native clock-crossing delay bounds1.5625..4.6875ps. Full per-bit native samples/crossing brackets and source controls are retained here; no new transient/layout or changed acceptance gate.

Representative worst A/B/C edges already have correct-polarity master output and slave input while slave output is still old or below100mV. D also has a late upstream input. This supports testing slave drive/load response, not asserting a sole cause or claiming timing closure.

NEXT SOURCE522ac9b2736a3445c839ac6dfcf25bf245ab78d1, branchcodex/cdr-slave-drive-trial, six changed files read back byte-exact. Independent source-controls run41498753635; branch-creation checks41498680552 (actual parent sourcedf723c79; NOT a test of new source522ac9b2). Follow exact handles. Native trial has NOT yet been dispatched in this checkpoint: first verify actual source-control result24primitive roundtrips/14card refusals plus original29definitions/5blocks/9files/13admission refusals, then independently reserve exact-source release and dispatch execute=true once. Preserve run identity if visibility times out.

The next experiment starts from original authenticated collector Via2 freshRC41439516945, not either failed bias model. Eight slave load resistors SA/SB/SC/SD_S_RP/RN L2.6->1.9um,W32 unchanged; sixteen slave tail MOS SA/SB/SC/SD_S_T0..3 W36->48um,L0.3 unchanged. Provisional consistent AD/AS12.24p->16.32p and PD/PS72.68um->96.68um use parent0.34um diffusion extension. Exact target IDs/parameters/native terminals required. Whole-model and contract reversal prove all other476devices and every parent wireR/C card unchanged. No HBT/reference bias/master/input divider/stimulus/clock/150fF load/gate changes.

Sheet-only resistance ratio1.9/2.6 and nominal width/current48/36 give I*R ratio0.97436; nonlinear/device/contact/wire behavior may invalidate this hypothesis. Actual full waveform and voltage/current-density gates decide. This is a provisional parameter trial without matching GDS or recomputed wire parasitics. Even a numerical pass requires real schematic/GDS, DRC/LVS, canonical terminal mapping, freshRC and original loaded simulation before promotion. Closed-loop serial PHY/PVT/ESD/EM/integration/STA remain open.

Readonly8hour monitor keeps automatic_native_dispatch=false. Do not mistake successful diagnosis or source controls for accepted electrical/physical behavior.

Observed at 2026-11-02T18:19:49.824516+00:00:
- 41493369685: in_progress/None
- 41494299114: completed/failure
- 41497066977: completed/success
- 41498680552: in_progress/None
- 41498753635: completed/success

## Current continuation: compiler ID collision corrected; first bias trial rejected; balanced divider trial dispatched

All native CAD, SPICE, waveforms, GDS/ODB and native archives remain GitHub only. Local workspace empty. Full serial Gen3 x4 PHY, routed mainchip and final setup/hold remain OPEN.

MAINCHIP actual full build41453866417 FAILED after2063.7seconds at87%: upstream message scanner found DRT9999 twice (new FlexDR guard and existing TritonRoute.cpp). Compiler exit2, no OOM, cgroup peak3717890048bytes under12GiB limit. Original release431499827 preserved; no binary was qualified. The passing lifetime fixture did not cover cross-file message IDs.

Cloud diagnostic41460346322/sourceb36fa4700d78c2b8a5145db94603126887d13052 succeeded, authenticated entire failed archive and retained complete logs. Derived13147914267=77579bytes SHA56f4602691b66d161598bd4dd8962e8cb6392a755c6172813683edf9a2645c17. Its full selected text is stored here.

CORRECTION source851db8f517c03cffd0afeb6527e281bd9353f5d2: only new guard ID9999->10000, next free reported by actual scanner; worker accounting guard9998 unchanged. FlexDR derivedSHA892a9771d911cf8ed350ffe4d42683b16561f3989f1e7c8302a02f8016328d9e,78757bytes. Bounded two live workers, guides, geometry, cost and original full64 schedule unchanged. Source controls41492927619 SUCCESS: all old engine7positive/45refusal/25lifecycle and observer4positive/29refusal,9compiled lifetime cases retained. Exact pinned upstream find_messages.py now scans both actual derived C++files plus observer header; corrected version passes and prior duplicate-ID version is rejected. Whole actual DRT directory preflight is also required before compiler-container creation; original upstream build check remains enabled. Source-check three-file scope is not whole-engine qualification.

NEW COMPLETE ENGINE BUILD41493369685, same source851db8f5, branchcodex/mainchip-guide-batch-engine, release431773741/tagcloud-results-41493369685-1-mainchip-guide-batch-engine-build. Follow this exact handle; do not restart on observation timeout. After successful build/interfaces, qualify new binary on actual recovered chip and all protected clock/wire scopes before full64 routing. Current chip evidence remains92DRT (64short28spacing),21antenna nets,1691protected clocks unchanged. No new route/STA improvement has been measured.

PHY first provisional pull-up-only experiment41458294059/source4bc8aa4117cb603155e4d03bcd00c69c7d6ee943 is terminal REJECTED_WHOLE_MIM_PD500_LOADED. Native transient return0, sourcesunchanged=true, complete34.25ns/113475rows/1152columns raw1,045,823,299bytes SHA1370699f6fbd8523743afd942fceee845a82f4f014e08de075f199a71b1a971d. Full native release431531665 retains four parts and complete index. Derived13148519767=1409362bytes SHA1aaf64b5b67ca623db80c4a33f18271790ae0904b662c38b38575d7ae58dbf93; complete measurement and provenance copied here.

Compared with unchanged physical parent41441047354, four critical Vce values rose from(.342697,.339778,.370967,.369198)V to(.396086,.393141,.416315,.413390)V. C now passes0.4V for its two critical devices; D still fails. Phase14.18547mV<30mV and VI42.66045uA<50uA remain failures. Sampler A/B/C/D maximum clock-to-valid45.78125/41.71875/118.90625/54.21875ps, limit37.5ps; C previously51.09375ps worsened. Wrong signs0/0/0/33, below100mV129/128/128/128of765. Do not promote pull-up-only trial to physical layout or acceptance.

NEXT BALANCED TRIAL41494299114/source df723c791fec2621585c80fb56409d65b5811b44, branchcodex/cdr-sampler-balanced-bias-trial, release431779366/tagcloud-results-41494299114-1-cdr-sampler-balanced-bias-trial. Independent controls41493968467 SUCCESS, artifact13165312239=1338bytes SHAd383b888f1d9753f34c3ebb13aa3112ad7c4ccb9512e24a59a4e0de67840c640. Original29numerical definitions/5blocks/9files/13admission refusals plus6card refusals and both parameter shapes retained; actual13binding and2equivalent-unit controls still required.

This experiment starts from unchanged authenticated collector Via2 freshRC41439516945, not previous trial. Actual mapped pull-ups182/183/220/221 change L1.8->1.75um,W8 unchanged; pull-downs184/185/222/223 change L5->6um,W4 unchanged. First-order sheet-only normalized parallel resistance0.190677966->0.190909091 (+0.1212%); supply-divider fraction0.847457627->0.872727273. Hypothesis: raise common-mode while retaining differential load/gain, unlike previous14.49% normalized resistance drop. This estimate ignores contact/bias/capacitance effects and is not measured PDK resistance or expected success.

Both trials explicitly use fixed parent interconnect RC with modified primitive dimensions; matching_layout_verified=false and fresh_RC_for_modified_devices=false. New trial preserves other492devices, all interconnectRC, all original externalclock/stimuli/loads/gates/fullwaves and requires exact model/contract reversal. No new analog geometry generated. Even numerical success needs actual schematic/GDS regeneration, DRC/LVS, canonical matching, freshRC and original loaded verification; full-loop/PVT/ESD/EM/PCIe integration remain open.

Readonly8hour monitor keeps automatic_native_dispatch=false. Next: collect both current native results, diagnose actual failure/success, maintain same handles until terminal; never equate fixture/build or provisional circuit improvement with fullPHY/production/timing acceptance.

Observed at 2026-11-02T17:49:05.888877+00:00:
- 41453866417: completed/failure
- 41460346322: completed/success
- 41458294059: completed/failure
- 41492927619: completed/success
- 41493369685: in_progress/None
- 41493968467: completed/success
- 41494299114: in_progress/None

## Current continuation: real C/D input-bias experiment dispatched

Native CAD, SPICE, waveforms, GDS/ODB and native archives remain GitHub only. Local workspace empty. Full serial Gen3 x4 PHY, routed mainchip and final setup/hold remain OPEN.

NEW PROVISIONAL ELECTRICAL EXPERIMENT41458294059, source4bc8aa4117cb603155e4d03bcd00c69c7d6ee943, branchcodex/cdr-sampler-bias-trial, reserved release431531665/tagcloud-results-41458294059-1-cdr-sampler-bias-trial. Independent source-controls41458035010 SUCCESS; original29 definitions,5 executable blocks,9 numerical files,13 admission refusals retained; new six single-card fault refusals passed. Derived sourcecontrol artifact13148670349=1338bytes SHA f111f22ef817e376917147bebec40771909ca001a7ceec179cf8261e945db312, text preserved here.

Actual native correspondence41450661063 establishes SD_UP/UN = native182/183 and SC_UP/UN=220/221. These four rppd resistors pull AVDD to C/D input-gain collector nodes; length1.8um,width8um. A/B input circuits differ: there are NOT eight identical pull-ups. New trial changes only these four lengths to1.5um. Hypothesis: higher input common-mode improves clock-selector Vce; reduced differential gain is a risk. This is NOT an observed improvement.

Dedicated cloud helper authenticates successful mapping's complete derived ZIP and all500 Match records, then exact four full parameter/terminal mappings. It authenticates the unchanged full parent freshRC41439516945 and runtime, writes separate candidate model/composition files, checks exactly four reversible length-token changes and full composition reversal, preserves other496 primitive parameters and every interconnect R/C card. Parent files remain untouched. All original stimuli, external8GHz clock, loads,34.25ns full waves,13 actual binding controls,2 unit-equivalence controls and measurement gates are unchanged.

IMPORTANT: inherited interconnect RC is fixed parent RC and does NOT constitute matching extraction for changed resistor geometry. Every trial/configuration/provenance explicitly marks matching_layout_verified=false, fresh_RC_for_modified_devices=false, physical_acceptance=false, full_phy_accepted=false and final_timing_complete=false. Trial producer/source identify current trial, with authenticated parent provenance separate. Successful numerical results would still require schematic/GDS regeneration, DRC/LVS, canonical material, fresh RC, original loaded gates and full-loop/PVT/ESD/EM before integration. No new analog GDS has yet been generated. Original loaded41441047354 remains REJECTED (phase14.325mV,VI43.051uA,Vce.3398..3710V and delay41.72..54.53ps fail original limits).

MAINCHIP build41453866417/source5a82cbd4068411de19acc73605ebb64250b010fc remains the SAME engine build handle. Bounded guide-worker lifetime code and all original source controls passed, full engine compilation/native scope qualification and actual route effect must be established independently. Current actual recovered chip remains92DRT (64short+28spacing),21antenna nets;1691 protected clocks unchanged. No new route reduction or final setup/hold closure is claimed.

NEXT: follow both exact live handles without restarting on observation timeouts. For the trial, collect complete terminal measurement/raw-wave preservation and compare against parent with unchanged gates; if promising, implement real physical regeneration before acceptance. For engine, inspect full build and interface evidence, then qualify binary on actual checkpoint and protected clock/wire scopes before original full64 route. Keep fullPG/LVS/freshRC/3cornerSTA and full serial PHY obligations open.

Readonly8hour monitor retains automatic_native_dispatch=false. All source changes are already on the dedicated remote branch.

Observed at 2026-11-02T14:05:41.264544+00:00:
- 41453866417: in_progress/None
- 41458035010: completed/success
- 41458294059: in_progress/None

## Current continuation: bounded guide-worker engine build dispatched

Root v309 a91216f4c7c39e4b9ede5b4278bd421f81fd3c2f permanently preserved all completed guide and full500-device mapping observations and failures (inventory809,77files10,969,281bytes, every readback verified). Native work/payloads exclusively GitHub; local workspace empty. Full serial PHY, mainchip route and final setup/hold remain OPEN.

NEW REAL ENGINE BUILD41453866417, source5a82cbd4068411de19acc73605ebb64250b010fc, branchcodex/mainchip-guide-batch-engine, release431499827/tagcloud-results-41453866417-1-mainchip-guide-batch-engine-build. Independent same-sourcecontrols41453547634 SUCCESS. Do not restart if observation times out; follow this actual handle.

CHANGE: exact pinned OpenROADdcf36133a369abc8f3c5e5738cd4d82e4903c0e0 FlexDR.cpp originalSHA122e84ca0906d7e53d4e5f4c7216a72e55f085f1a62b0848df06fc9eafd2e3af -> derivedSHA1a9c208a7be43783dc5873bc07e1022c15847714ccdf8b1ddac68c2717af2361. Only guideTilesFlow worker lifetime section changes. It lazily creates at most2workers, executes each chunk, commits results and destroys those workers before creating more. One box per guide worker is asserted; total completed workers must match original count. Actual original guide selection/merging/boxes/independent batch grouping, costs, ripup/follow-guide parameters and full64 strategy remain unchanged. Commit timing within each independent batch changes; routing equivalence and RSS improvement are NOT assumed.

SOURCE CONTROLS: original engine7positive/45refusal/25lifecycle and original internal observer4positive/29refusal passed. New actual C++replacement body compiled with g++-std=c++20-O2-Wall-Wextra-Werror and executed under instrumented worker constructor/destructor and completion checks:7positive lifetime scenarios including empty/single/odd/multiple/nonmonotonic batches;2invalid box groups rejected. All <=2live workers and each worker completed/freed exactly once.3modified upstream source cases refused. Complete source reversal exact. These are source/fixture controls, not a complete engine or chip route qualification.

COMPILATION uses prior qualified build source26e2f28b735238bd69140dca9a0fc6d2bf29f197 with original observer derivation retained; fixed gitlinks/OpenSTA/ABC, immutableubuntu24.04-dev image,12GiB cgroup,2CPUs,no swap, native full project build and Tcl/Python interface checks. Exact source-before/after and source guard remain. All available failures and native engine archive published to the separately reserved release. No native data is downloaded locally. Complete build can qualify only compilation/interfaces, not clocks/routes/finaltiming. The next action is to collect its terminal evidence, qualify the new binary on actual recovered native data with original full-wire/clock/scope observations, then route and run full DRC/antenna; later PG/LVS/freshRC/3cornerSTA are still required.

KNOWN CHIP EVIDENCE: recovery41440285882 has92DRT(64short+28spacing),21antenna nets.1691protected clocks and nonselected wires unchanged. Completed native guide audit41449886129/source3bf8acec68f0a90ca008a94dff3f7f074f7b9717 measured96source nets/2593guides/325intersections,34selectedsources,61temporaryFIXEDsources,4clock sources. No new routing/violation reduction yet. Source audit corrected complete_DEF.accepted=false semantics without dropping any scope checks; Point-overload native closed intersection passed6native cases. Original failed audits41445399432/41447786520 retained.

KNOWN PHY EVIDENCE: full native mapping41450661063/source22baa225789b8ec1c9ce98437196af1e48fc2918 matched500LVS devices and all1446loaded terminal identities plus all500composition records. Critical61/62 areSD_M_CS0/1 and115/116 areSC_M_CS0/1 (Nx2 clock-selector HBTs, basesCN). Drivers54/56 and106/108 areSD/SC_M_DP/DN (Nx4 data pair). TailMOS3..6/32..35 areSD/SC_M_T0..T3(W36um,L0.3um). Symmetric parallel devices can exchange equivalent schematic pairing; no uniquephysical-name claim. Mapping failures41449736667/41450082352 retained.
Loaded41441047354 stillREJECTED: phase14.325mV<30mV,VI43.051uA<50uA,Vce.3398..37097V<.4,sampler41.72..54.53ps>37.5. Fullwave1,045,823,299bytes preserved. Native scope/DRC/LVS/RC successes are not fullPHY acceptance. Next electrical work must use actual source mapping and fullwave operating points for an explicit bias/device-size/collector-wire change, then real physical regeneration and unchanged loaded gates. No provisional parameter experiment or new analog geometry has yet been dispatched.

Readonly8hour monitor remains automatic_native_dispatch=false. Full closed-loopCDR/PLL/SERDES/PVT/ESD/EM and mainchip final acceptance remain open.

Observed at 2026-11-02T13:35:37.399898+00:00:
- 41453547634: completed/success
- 41453866417: in_progress/None

## Current continuation: guide audit and full PHY device correspondence completed

Root v308: a773002fb728e25c4c7d449b4de01c7344b9eec3, inventory802. Native CAD, geometry, simulation, waveform and archive payloads remain exclusively on GitHub. Local workspace remains empty. Full serial PCIe Gen3 x4 PHY, final mainchip routing and setup/hold are NOT complete.

MAINCHIP
Recovery41440285882 retains the actual routed iteration19: 92 DRT violations (64 shorts,28 metal spacing),21 antenna nets. All1691 protected clock wires and all nonselected wires unchanged;46 of47 selected wires changed. Original failed route41415994457 is still a failure. No new routing was performed this turn.

Initial guide audit41445399432/sourcecccc79890d45e1e9796ee096bfbc42b064f72160 failed before opening ODB. It incorrectly required complete_DEF.accepted=true. The original routing_delta function returns accepted=false even after all scoped DEF assertions pass; this is a production acceptance disclaimer. Corrected consumer independently checks native clock/other-wire booleans, protected DEF records/non-NETS bytes, exact46 changed owners within47 selection, native/DEF changed-set agreement and ordered-name SHA. It continues to require accepted=false and all final acceptance flags false. Real producer fixture plus22 refusal controls and9 coordinate/rectangle controls passed41447590694/sourceb3ea23076cc47c0f94c912eff85f853815a95692.

Actual audit41447786520 then passed scope but failed at embedded OpenROAD Rect.intersects(Rect) overload. No geometry or original gates were changed. Source3bf8acec68f0a90ca008a94dff3f7f074f7b9717 uses native Point containment in both rectangles for the common lower-left candidate point, preserving exact inclusive intersection and checking native coordinates and result types. Six native boundary/degenerate/disjoint cases pass. Independent source-controls41449620712 passed.

ACTUAL GUIDE AUDIT41449886129 SUCCESS; source3bf8acec68f0a90ca008a94dff3f7f074f7b9717; branchcodex/mainchip-route47-guide-audit; release431471737.
- Actual measuredODB214402279bytes SHA53b42f42c244af7416a78c0cc04cc897f99b114c892c6bc86ecc60affa3e05af.
- All92 markers,96 source nets,2593 guide records,325 marker-guide intersections.
-34 source nets in selected47;61 in temporary FIXED overlay;4 protected clock source nets.
- Largest intersecting guide475.2x7.2um (3421.44um2), from a fixed nonselected register-file net. Selected long guides include424.8x7.2um and410.4x7.2um.
- Full observation1012909bytes SHAd54abd172e41b3bd5d3a33243eec7fb86b3c48c24d38ab9e42ff470f6512be2b.
- Derivedartifact13144512570=275127bytes SHAab6bf3e7cd71b0223f2169a02da674fabd90cd12ec934642c7afafe991a320e5.
- current_route_calls=0,current_repair_calls=0,geometry_changed=false,memory_cause_proven=false,router_internal_guide_mapping_equivalence_proven=false. This is native diagnosis, not closure.

Exact upstreamdcf36133a369abc8f3c5e5738cd4d82e4903c0e0 source inspection:
FlexDR::guideTilesFlow builds workers from all intersecting original net guides, merges same-orientation intersections, constructs all workers before processing batches, and retains each batch's results until all its workers finish. Unlike optimizationFlow, it does not subdivide batches by BATCHSIZE. Flow switches to guides at <=100 violations unless ripupALL/INCR or max-spacing work. Current stored-guide observation is not proof of identical internal iteration20 guide order/batches.
NEXT MAINCHIP: implement/qualify bounded guide-worker allocation and completion batches in the pinned router while retaining original full64 schedule/costs/guide geometry and immutable wire/clock audits; do not repeat the unchanged 11GiB failure. Alternative single-step ALL-ripup forcing bounded optimization tiles was investigated in source but NOT implemented; it changes routing strategy. No engine patch/build/route trial has yet been dispatched.

PHY
Collector Via2 candidatec0d420 remains physically/canonically/RC qualified only at subblock scope. Actual loaded41441047354 remains REJECTED: phase14.325mV<30mV, signedVI43.051uA<50uA, Vce61/62/115/116=.342697/.339778/.370967/.369198V<.4; sampler delays41.72..54.53ps>37.5ps. Complete raw113475x1152,1,045,823,299bytes retained. Original external-clock nominal scenario; no closed-loop/fullPHY acceptance.

NEW FULL NATIVE DEVICE CORRESPONDENCE41450661063 SUCCESS, source22baa225789b8ec1c9ce98437196af1e48fc2918, branchcodex/cdr-collector-device-map.
Authenticate complete physical41435641296 release431371522 and exact flat LVSdatabase2760554bytes SHA9df6ea3e90bccaebe216834488154f680317934560ed99ad0b1a9be1ff22da37. Native KLayout reader0.30.4.post1; exact500 matching primitive pairs/bidirectional bijection and25ports. Cross-check all1446 native terminal IDs/model spellings/net names/clusters against actual freshRC41439516945 native planes244758bytes SHA380865a73b8be42afa07ef81a5fcd05e7110e570455ce857f772770e09b08048, and all500 actual loaded composition records1015133bytes SHAd775d58fcaaba7c6f4d5d06a51645839e0b0e4e853de5e6249f3156b1f9b27d5. Ten source-only refusal controls passed.
Derivedartifact13144567876=66389bytes SHA415215780ef60cd6bd971ccb782d1dfbe4430a67c2f5ae10a3f0d60c6bbcd9cb.
Preserved earlierfailures41449736667/source11d5d2b6a40b82a30dc5058c7814f68e19193324 (invalid redundant Net.id API) and41450082352/sourceda58d7d649e982cead0a7e419f79e5a069bb94ad (lowercased npn13G2 did not equal raw native model spelling). Correct reader uses net cluster_id/name/expanded_name and separately preserves raw/normalized model names. No identity comparison removed.

Actual source mappings:
61=SD_M_CS0;62=SD_M_CS1;115=SC_M_CS0;116=SC_M_CS1. All four clock-selected HBTs useNx2,le0.9um,we0.07um; basesCN, collectorsSD_M_SE/SC_M_SE, emittersSD_M_TE/SC_M_TE.
54=SD_M_DP;56=SD_M_DN;106=SC_M_DP;108=SC_M_DN. Data pair HBTs useNx4,le0.9um,we0.07um; basesSD_LP/LN orSC_LP/LN, common emittersSD_M_SE/SC_M_SE.
3..6=SD_M_T0..T3 and32..35=SC_M_T0..T3; eachNMOS W36um,L0.3um, gatesIRD/IRC,sourcesAVSS. Actual loaded source voltage includes extracted ground drop and is not ideal ground.
LVS can exchange equivalent parallel devices; pairs are a valid native correspondence, not a unique physical naming guarantee.

NEXT PHY: use this native source mapping with preserved fullwave operating points to design/simulate specific clock/data common-mode, device sizing or remaining collector-wire corrections. Data-input deviceNx4 -> higherNx would be a circuit change with added capacitance; not yet simulated, not a claimed fix. Any exploratory parameter simulation must be explicitly provisional because old RC/layout no longer qualifies modified primitive geometry. Actual final change must regenerate schematic/GDS, full DRC/LVS, canonical material, fresh RC and unchanged loaded gates before integration.
All full closed-loopCDR/PLL/SERDES, PVT/ESD/EM and mainchip PG/fullLVS/final3cornerSTA obligations remain open.

Readonly8hour monitor remains automatic_native_dispatch=false. No local native files or new local project files.

Observed at 2026-11-02T13:20:03.899552+00:00:
- 41445399432: completed/failure
- 41447590694: completed/success
- 41447786520: completed/failure
- 41449620712: completed/success
- 41449886129: completed/success
- 41449736667: completed/failure
- 41450082352: completed/failure
- 41450661063: completed/success

## Current continuation: actual recovered route92DRC; collector candidate electrically rejected; guide-memory diagnosis dispatched

Previous rootv307 ac5300c77500b098904cfd059221b94a25b11cdc/inventory799. Native work/payloads exclusivelyGitHub; localworkspace empty. Complete serialGen3x4PHY/mainchiproute/finalsetuphold remainOPEN.

MAINCHIP RECOVERY41440285882/source0990e2971dee0333598a59a033dfe4f1f1f4215b/release431403455 TERMINAL SUCCESS. Exactiteration19 recovered, originaltemporary47protection restored, all1691clocks/allnonselectedwires unchanged, completeDEF auditPASS.46of47selectedwires changed versusoriginal140marker input. Originalfailedroute41415994457 remainsFAIL; currentrecovery made0routecalls. Nativeinner650.6126seconds, zero terminalerrors. design_is_routed=1 does not meanDRCclean.

ACTUAL FULL DRT CHECK92markers=64Short+28MetalSpacing, allcategories below10000cap and complete serializedcensus. FullsignoffDRC=false. Report16461bytes SHA4d70f7bb24b4aaceb7e435b4a70b4670a20f5ad07a06e4398349e69d2000c59b; markerJSON118206bytes SHAa7cbb4ad472a6f0bf6a8e422eb439dab2e2685ad3ec63062c304af7f4d0bebb9. Antenna21nets with27reportedviolations. Some includePCIe receiveownership andholdbuffers. Originalglobalrouteclass restoration/diodePG/fullLVS/finalSTA stillrequired; recovery didnotclaimthem. Restoredcandidate214392179bytes SHAe460c8d0751ad9d22042a2e133103e0853048110fb0b2747c04ced44eb284d4e. MeasuredODB214402279bytes SHA53b42f42c244af7416a78c0cc04cc897f99b114c892c6bc86ecc60affa3e05af. Complete72member release sealed; single507337878bytepart. Derived13140238534=281462bytes SHA09dea7b60ec56de5ae36dadd3e40196d4dd639e1190f29524e4b99e0d374e1b6.

NEW GUIDE AUDIT41445399432/sourcecccc79890d45e1e9796ee096bfbc42b064f72160/branchcodex/mainchip-route47-guide-audit/release431439188. Independent same-sourcecontrols41444984360 PASS. Reuse unchangedengine/runtime/resources and originalfrozen source gates. Authenticateall72recoverynativemembers plusoriginalscopeinputs, select6currentfiles. Readactual92markerJSON/ODB/nativeguide records with exactliteralnames, nativeDBU/losslessDecimal coordinates and cross-check allrectangleintersections againstactualodb.Rect. Classify selected47/protected1691/temporaryFIXEDoverlay. Preserveallguides/intersections andrankedextents. NO routing/repair/write_db/write_def. No claim ofexactinternalfrNetguide equivalence, memorycause ornewmaterial. This diagnostic follows recoveredactualviolations tochoose a later boundedroute strategy; nounchangedmemoryfailing rerun.

COLLECTOR LOADED41441047354/sourceeb5eb3e34f248e77c26b573f4cfd52a1fdf585ae/release431408879 TERMINAL ELECTRICAL FAILURE. Nativeengineexit0, fulltransient=true/sourcesunchanged=true, statusREJECTED_WHOLE_MIM_PD500_LOADED. Phase14.325205048534979mV<30mV; signedVI43.05123360647242uA<50uA. HBT61/62/115/116minimumVce .34269694860107586/.33977774836005276/.3709673862509904/.3691976007675946V<.4. Versusparent41430498959 improve5.264/5.611/12.762/12.478mV, stillfail. SamplerA/B/C/D maxdelays45.78125/41.71875/51.09375/54.53125ps>37.5; wrongsign0/0/2/34; below100mV129/128/128/128 of765. ComparatorX/Ywrong387/44, below100mV726/652, delay118.90625ps remainfailures.

Fullraw1045823299bytes SHA6bb19cfd4db727ecc28b6564bf3a157470e09153d488626ffa1f5b7cf9e6ce7d=113475rows1152columns,34.25ns,0.3125psmaxstep unchanged. Measurement452909bytes SHAc16b5b66490b76de73f932f2df0d807527cb7b0eafa00139694795ec76b4d5b8. Derived13140423325=1375316bytes SHA91e990391786c5460d772e66963724841985ed4bc95689ad24f9677fade7e0e4. Completeindex701645061=25422bytes SHA881d6d759972190866998369cad80f7f016a49a96748b0734e586af304e59e55. All4nativearchiveparts andoriginalfailure preserved; never shortenwave orrelaxgates.

FULLWAVE DIAGNOSIS41443536765/source9911d8f5a6bae26a8864d858c3a21bc7b48808d0 SUCCESS. Entireparser/diagnosis unchangedfrom55fa84c2 exceptbranch+producer/index/parts. Allactualraw/scalars/margins/delays/signcounts reproduced andexactbadset61/62/115/116 retained. Derived13140329003=120423bytes SHA16ffa363ead36ea95ae97cc579780a274d8015bca56fccdf8949f22f40793c77.

Nativeoperatingminima now61:Vc.829382412,Ve.486685463,Vb1.420525401,Ic3.992023mA;62:Vc.828401554,Ve.488623806,Vb1.420592491,Ic3.912432mA. Drivers54/56E=.872704176/.888610480 atthoseminima; remainingpathdrops43.32..60.21mV.115:Vc.858448311,Ve.487480925,Vb1.424827861,Ic4.044968mA,drivers106/108E=.937624156/.889631044, drops79.18/31.18mV.116minimum movedto18.18671875ns:Vc.861016737,Ve.491819136,Vb1.427232995,Ic3.970839mA;drivers106/108E=.892858328/.937510976, drops31.84/76.49mV. TailMOSdrain/gate/sourcevoltages andallupperdriverC/B/E/Sterminals saved in compactderivedoperatingrecord. Remainingemitter-to-MOSdrops42.1..47.7mV. Needactualbias/geometry design investigation; no claim another smallVia changealonecloses phase/delay/fullPHY.

Passive41441842390 proved8collectorReff -11.26..13.49percent andother24unchanged. Allphysical/canonical/freshRC passes remainvalidonlywithin analogsubblockscope. Do notequate passivegainwithloadedacceptance. Readonly8hourmonitor automatic_native_dispatch=false. Followguideauditactualhandle; preserveallfailures/controls. FullclosedloopCDR/PLL/SERDES/PVT/ESD/EM andmainchiprouting/PG/LVS/3cornerSTA stillopen.

Observed at 2026-11-02T12:35:01.538130+00:00:
- 41441047354: completed/failure
- 41440285882: completed/success
- 41443536765: completed/success
- 41444984360: completed/success
- 41445399432: in_progress/None

## Current continuation: measured collector-path improvement; actual loaded and mainchip recovery still under observation

Rootv306 cb90ea54250cfa46dc7341be60095624a432f619/inventory798. Full serialGen3x4 PHY, mainchiprouting and finalsetuphold remain OPEN. Allnative work exclusivelyGitHub; localworkspace empty.

NEW RESISTANCE41441842390/sourced9bd6e108d890fcfbab5d77d85535a49d2092b88/branchcodex/cdr-collector-via2-resistance completedSUCCESS. Exactcurrentmodel fromfreshRC41439516945:500devices26222R16798C. Same26solver/7comparison/4partitioncontrols and32complete reciprocal network queries, actual114electrical partitions/500primitiveparameters/1446terminals preserved. Derived13140841659=2152067bytes SHA1fc0b6b2bff3d421cbf90411e2afcd5af57dc4b6e6568274d717e5b88d78ac07.

Originalnativecomparison reference is b9b9, notimmediateparent5e5ef394. Separate DERIVED incremental analysis authenticates parent41430503141/artifact13134345896 andcurrent41441842390/artifact13140841659, verifies sameoriginalreference/solver/all114partitions and joinsall32stable source/sinkterminal labels. All8collector Reff decrease1.4837932796803077..1.9273789820353926ohm =11.256570649473463..13.492477957780459percent. Remaining24paths (16emitter+8ground) exactlyunchanged. Currentcollector Reff11.697781516811677..12.357461712656765ohm. Rawresistance solver andcompleteoutputs remaincloud; derivedJSON/text only used for this comparison. Reproducibleanalysis andfull32rows saved with thischeckpoint. Do not infer actualoperating Vce, delay, phase/current or EM from passiveunitcurrent.

FreshRC41439516945 alreadyPASS and fullyarchivedv305, exactactualportorder15/16xp,xn. Loaded41441047354/sourceeb5eb3e34f248e77c26b573f4cfd52a1fdf585ae/release431408879 sourcecontrolsPASS and actualsamefullwave/gates running at lastobservation. Followsamehandle; authenticatenativeexit andcompletewave beforeanyclaim. Parent41430498959 rejection/1GBwave remainpreserved.

Mainchiprecovery41440285882/source0990e2971dee0333598a59a033dfe4f1f1f4215b/release431403455 sourcecontrolsPASS and original restoration/audit stage running at lastobservation. Originalfailedroute41415994457 remainsmemoryFAIL. Exactretained19ODB214392179bytes SHAa93e921ccd7abb164dbe2ff3f6a1a1c26777d707399cea7580d7c5d08ea11017 isrecoverysource, not internalrouterstate. Original1691clocks/allnonselectedwires/classes/DEF/fullDRC/antenna/read-onlyaudit required. No newroute calls and11GiBRSS/12GiBcgroup/2GiBhostreserve unchanged.

UPCOMING MAINCHIP DIAGNOSIS, not implemented nor accepted: exactOpenROADdcf36133 guideTilesFlow considers every marker source net with intersecting originalguides and merges intersecting same-direction boxes. Original getGuides reader authenticates each guideowner/box/layer/vialayer/congested/jumper/connected_to_term and rejects hiddenproperties. Once recovery producesactualfullDRC, mapmarker sources to nativeguideboxes and classifyFIXED/protected/selected owners. Determine whether oversized boxes derive from fixednets; do not assume. Temporary guidechanges or bounded batches would require explicit independentreversibility/scope/runtimequalification before routing; finalDRC and STA gates remainunchanged. Do notclear guides or shorten search merely to pass.

Originalphysical41435641296 andcanonical41438707959 success apply to analogsubblock only. FullclosedloopCDR/PLL/SERDES/serialPHY/PVT/ESD/EM, mainchiprouting/PG/LVS andfinal3cornerSTA remainopen. Readonly8hourmonitor automatic_native_dispatch=false. Preserve exactlivehandles andfullfailures; no duplicates on observationtimeout.

Observed at 2026-11-02T12:12:29.850129+00:00:
- 41441047354: in_progress/None
- 41440285882: in_progress/None
- 41441842390: completed/success

## Current continuation: actual collector fresh RC PASS and full loaded simulation dispatched

Supersedes v305 live-RC wording: collector freshRC41439516945/source710869eb13082f3c3dc488159bf167d937294454/release431398178 is TERMINAL SUCCESS. Actual500devices26222R16798C. Model2112906bytes SHAe388befe16436bf93ae3ab561f3d3ffb0d0403cabae887d0de3a142b41566001; composition1015133bytes SHAd775d58fcaaba7c6f4d5d06a51645839e0b0e4e853de5e6249f3156b1f9b27d5. Originalqualification3767bytes SHA28fd21a20be516c19d2b960d39269d8b416f93667abc3af1ae8ed7f4557e8e98. Actualportorder15/16xp,xn. Derived13137233875=8368693bytes SHA32d24c56caecd39e13534b6f4c381e71d168e34b0a11c2e1c53712914787ec9d, already fully and permanently archived in v305. All original numerical receipts unchanged.

NEW LOADED41441047354/sourceeb5eb3e34f248e77c26b573f4cfd52a1fdf585ae/branchcodex/cdr-collector-via2-loaded/release431408879. Actualnewcensus,portorder,model/composition and complete qualified archive bound. Host exactly reverses to8a73ba2c except declared currentmetadata and meaningful negative selector-order fixture. Negativeorder nowxn,xp; oldyp/ynnegative andR+=1 unchanged. All29frozendefinitions/5blocks/9files/43fdpreparation-measurement/stimuli/loads/fullraw/phase-current-Vce-sampler-comparator gates unchanged. Source-only fixture remains native_executed=false. Follow this exactrun, preserve allsuccess/failurewaveforms. RC success is not electrical acceptance.

MAINCHIP41415994457 terminalmemoryFAIL remains preserved; original full640route was not successful. Actualiteration19snapshot214392179bytes SHAa93e921ccd7abb164dbe2ff3f6a1a1c26777d707399cea7580d7c5d08ea11017 exists. Recovery41440285882/source0990e2971dee0333598a59a033dfe4f1f1f4215b/release431403455 is the active originalclass restoration, allclock/wire/opcode/DEFscope audit and fullDRC/antenna diagnostic. Independentcontrols41440092152 PASS; controls41439875813/41439959911negative-test exception mismatch failures retained. No newroute call or routerinternalstate resume claimed. Inspect real finalDRC and scope before selecting memory-bounded routing strategy. Frozen11GiBRSS/12GiBcgroup/2GiBhostreserve unchanged.

Physical41435641296 full560DRC0/deepflat500LVS13 andcanonical41438707959 all123controls/1469comparisons PASSED only for analogsubblock. Parent41430498959 loaded rejection and full1GBraw preserved. FullserialGen3x4PHY, closedloopCDR/PLL/SERDES/PVT/ESD/EM, finalmainchiprouting/LVS/PG and3corner setup/hold still OPEN. Do not infer completion from these intermediate passes.

Native CAD,simulation,waves and payloads stay exclusivelyGitHub. Local workspace empty. Readonly8hourmonitor automatic_native_dispatch=false. Current task continues via exact livehandles; no duplicate dispatch on observation timeout.

Observed at 2026-11-02T12:01:34.945790+00:00:
- 41439516945: completed/success
- 41440285882: in_progress/None
- 41441047354: in_progress/None

## Current continuation: collector Via2 canonical PASS, fresh RC live; saved mainchip iteration19 recovery

Previous checkpoint v304 fcee42478c0e7c8795ec65ca77aea76bc7441cdd has790inventory rows. Native CAD/GDS/ODB/SPICE/waves remain exclusively GitHub. Local workspace empty. Full serialGen3x4 PHY, mainchip routing and finalsetup/hold remain OPEN.

CORRECTION TO v304: mainchip41415994457/sourcef808321a is TERMINAL FAILURE, not live. Route elapsed5737.308s; supervisor maximum_group_rss, returncode-15. RSS11605680KiB exceeds11534336KiB(11GiB); available3664296KiB remains above2097152KiB floor.12GiBcgroup/swap0; no OOM kill. Iteration19 completed with92internal markers (28MetalSpacing+64Short); iteration20 guides tiles stopped near90percent. This is not finalDRC and no finalrouted checkpoint returned. Complete native release431237039 has100members,3archiveparts and snapshots0..19. Do not repeat same failing route unchanged.

SOURCE RESEARCH: exact engine OpenROADdcf36133a369abc8f3c5e5738cd4d82e4903c0e0, src/drt/src/dr/FlexDRFlow.cpp and FlexDR.cpp. Below100markers state machine can selectGUIDES. guideTilesFlow unions original guideboxes, creates explicit-sized workers and processes whole independent batches before clearing. The normal args.size optimization tiles do not bound these explicit guideboxes; reducing threads alone may retain completed workers in a batch. A safe bounded-batch/box repair needs new runtime qualification, not altered DRC acceptance. Snapshot support was ALREADY enabled in originalroute47 source. Actual19ODB214392179bytes SHAa93e921ccd7abb164dbe2ff3f6a1a1c26777d707399cea7580d7c5d08ea11017 is preserved. Reuse must first pass original complete scope/class/DRC audits; serializedODB is not internal router-search-state resume.

MAINCHIP RECOVERY41440285882/source0990e2971dee0333598a59a033dfe4f1f1f4215b/branchcodex/mainchip-route47-snapshot19-audit/release431403455. Independent same-source controls41440092152 PASS, oldsource-controls41439875813 and41439959911 FAILED only because new negative archive test expectedAssertionError instead of existingvalidatorValueError. Test corrected; actualvalidator/native gates unchanged. Native helper also explicitly inserts /work/tail-source/scripts before embedded imports. Both failures preserved.
Authenticate whole failedproducer capsule, all100members/all3parts, select7exact baseline/protection/scope/failure/snapshot records. Recompute original47selectednets against actual baseline and1691protected clocks. Restore original routeclasses, run unchanged complete native wire/opcode/DEF/scope/clockaudit, fullDRC/antenna and readonlymeasurement. No newroute call, no failure reclassified success.11GiBRSS/12GiBcgroup/2GiBhostreserve unchanged. Current candidate originalclass/PG/fullLVS/threecornerSTA and broader original828netscope restoration remain required after this diagnostic. Follow same live job; do not restart on observation timeout.

COLLECTOR GENERATOR41434944363/sourcef878816a SUCCESS. Actual c0d420cdbc31863bf21086e88c12f494779961225031c261d6b05fe07e7585a7 GDS1078900bytes: four HBT54/56/106/108 emitter accesses on two collector nets44/598,12newVia2 each,48total. OnlyVia2/M3 added1732800/12048600nm2; originalM2/devices unchanged. Fullwave diagnosis41433864856 of rejectedparent41430498959 showed30..94mV collector pathlosses, motivating this repair.

ACTUAL PHYSICAL41435641296/source262ac9b4d9142be6235c68d279c67aac9b92e3a8/release431371522 PASS.560DRC categories zero markers, deep andflat500primitive LVS match, all13intentionalfaults rejected. Derived13136427750=354889bytes SHA62f6d57cb094be6e1a1905762e5e58fdcd44a3045f6f1fc89a0480d868a4df48.

ACTUAL CANONICAL41438707959/source6ecc4bac9ac806babd879413cd6d7230e70b826d/release431392541 PASS.123controls=96unchangedprevious+27collectoridentity/offset/grid/guard/cut/spacing/enclosure mutations. All113partitions×13layers=1469comparisons. Exactlypartitions3/51 changedVia2/M3,24cutsperpartition,areas866400/6024300nm2each. All500devices1446terminals238native114electricalnets978anchors25ports and78canonicalfiles preserved. Native port order actualpositions15/16 reverted fromxn,xp toxp,xn; always bind actualneworder rather than assumingIDs unchanged. Derived13138450060=1449973bytes SHA137114c9609b4312005c8f518a2eed84330736f9f4597b757275fd0ecd6ff34b.

FRESH RC41439516945/source710869eb13082f3c3dc488159bf167d937294454/branchcodex/cdr-collector-via2-fresh-rc/release431398178. Host byte-for-byte reversible toa53fb2f3 after exactproducer/candidate/schema/status/branch/measuredport substitutions. Original13commandplan/658runtimefiles/11numericalreceipts/bothMIMorders and resource limits unchanged. Sourcecontrols PASS; native extraction live at dispatch observation. Require actual terminal qualification, measuredR/Ccounts and model/composition hashes; then same fullloadedgates. Loaded negative selector-order fixture must change to parentxn,xp because currentactualxp,xn. No waveform shortening/gates relaxed.

Parent drainM23loaded41430498959 remainsREJECTED: phase14.3184mV<30mV,VI43.0307uA<50uA,Vce.337433/.334166/.358205/.356719V<.4V,samplermaxdelays45.78125/41.71875/51.09375/54.53125ps>37.5ps,wrongsign0/0/2/34. All1045823299rawbytes SHA bf5572baba3665b925385cf257686b7fb8dbcb24371e9de65bef5196a53fddb3 preserved in original release. Physical/canonical/RC success is not electrical, EM/PVT, closedloopCDR/PLL/SERDES, fullPHY or finalmainchip timing acceptance.

Next: follow actual recovery and freshRC handles. On successfulRC, consume actualcensus/portorder in full unchangedloadedwave stage; use passive comparison only as diagnosis. On recovery completion, inspect realcompleteDRC and scopedelta before choosing memory-bounded reroute. No new mainchip reroute until recoverability is proven.8hourreadonlymonitor remains automatic_native_dispatch=false.

Observed at 2026-11-02T11:57:08.403779+00:00:
- 41415994457: completed/failure
- 41435641296: completed/success
- 41438707959: completed/success
- 41439516945: completed/success
- 41439875813: completed/failure
- 41439959911: completed/failure
- 41440092152: completed/success
- 41440285882: in_progress/None

## Current continuation: drain M2/M3 electrically rejected; actual collector-driver access repair

Previous rootv303=d2e0af7a0ac38f847b68ff1d34aa82391f62c84b/inventory788. NativeCAD/GDS/ODB/SPICE/waves exclusively GitHub; local workspace empty. FullserialGen3x4PHY/mainchiprouting/finalsetuphold remainOPEN.

DrainM23GDS5e5ef394 passed physical560DRC0/deepflatLVS13, canonical96controls/1469comparisons and freshRC41428920414 with500devices26218R16796C. Passive41430503141 found16emitterpaths27.46..28.97percent lower versus immediate9fef; other16 unchanged. Physicalmap41431599840/6a6b14ef actualPASS103controls/all26218native-exportedR/all978portsandownership/7documentedMIMrelocations/13nativeunions/50criticalresistors. Derived13134492431=482051bytes SHA23643f7a0a478045eb1c0424c1a0a04ed77036f5e38c6b5bdf134800275aad23.

ACTUAL LOADED41430498959/source8a73ba2c575c4e6b8accf1dff736d481e1e53606/release431336246 TERMINAL FAILURE: native engineexit0, transient_executed=true/sources_unchanged=true, statusREJECTED_WHOLE_MIM_PD500_LOADED, acceptedfalse. Phaseaverage14.318407882438447mV<30mV; signedVI43.03073211449151uA<50uA. HBT61/62/115/116 minimumVce .33743317402843276/.3341663079585235/.3582050227770855/.35671941943935614V<.4V. SamplerA/B/C/Ddelay45.78125/41.71875/51.09375/54.53125ps>37.5ps, wrongsign0/0/2/34, below100mV129/128/128/128 of765. ComparatorX/Ywrongsign387/44, below100mV726/652, delay118.90625ps. Passive improvement did NOT close operating gates; Cpairheadroom worsened about1.3mV.

Full raw1045823299bytes SHAbf5572baba3665b925385cf257686b7fb8dbcb24371e9de65bef5196a53fddb3=113475rows1152cols, complete unchanged waveform. Measurement452899bytes SHA0f9688d618642b517af3a7fc9a0d071389ed9e64a54bf8f570b0b5ec062e94af. Derivedartifact13135261689=1378192bytes SHA39b4db1199654c16cf7efa7ffa456eeab88f576b6bb4b84205f7515d23488373. Releaseindex701451273=25049bytes SHAc632b51aa343ef9d644439f6928e068f3d01125fef822f6de7db1a1db42b9653. Allnativeparts and originalfailure preserved.

FULLWAVE DIAGNOSIS41433864856/source55fa84c20b0cd4d8dfd074769cad9c3b6e8696e8/branchcodex/cdr-drain-m23-wave-diagnosis completedSUCCESS. Alloriginalparser/diagnosis body exactlyaaf92 except branchandactualproducer/indexpins; sameactualfailure-set61/62/115/116. Allfullwave native bytes/scalars/margins/delays/signcounts reproduced. Derived13136240451=120651bytes SHA7ff5ec8d0e66e6a3acbbc2a7a663acb3d3aff7389037bc9bd21a012c13221ad3.

Actual operatingminima:61Vc.823615534Ve.486182360Ic3.986517mA;62Vc.822283489Ve.488117181Ic3.906766mA;115Vc.845345470Ve.487140447Ic4.028430mA;116Vc.845657446Ve.488938027Ic3.953865mA. Collector driver54/56 losses47.56..68.02mV and106/108losses30.27..94.18mV. Emitter-to-MOSdrops42.04..47.49mV remain. Do not equate passive unit-current resistance improvement with operating headroom improvement.

NEW GENERATOR41434944363/sourcef878816a24906f450d5ffa2f72b6b08ed6024e6a/branchcodex/cdr-collector-via2-access/release431366909. Uses actual rejectedmeasurement and reproducedoperatingproof, exactcurrentGDS5e5ef394/fullRCarchive and103originalcontrols. Targets ONLY4collector-driver HBT54/56/106/108 Eterminals on2nativecollector nets; lowerselectorHBTs unchanged. Newfunctiongenerate_collector_via2_access added; alloriginalfunctionASTs except explicitmain dispatch unchanged. No8HBTdraft wasgenerated/dispatched.

Each proposedM3pad is x±1825nm,y[-650,+450]nm aroundactual5nm point (originalHBTanchor exactly2nmabove). Retain4oldVia2/site. Add12new190nmVia2/site (8atdy-480 withdx±1680/±1200/±720/±240,4atdy0 withdx±1680/±1200), total48. RequireALL48 admitted,50nmboth-metal enclosure,240nmold/newcutspacing,240nmforeignM3clearance,50nmadjacentforeignvias,ownedold/newM2points andoriginalM3attachment,all13unions. Onlylayers29/30 maychange; serializedexactdelta andoriginalmaterialreversal required. No nativegeometry/candidate success yet inferred from dispatch.

NEXT: follow samegenerator41434944363 actualterminal. If successful, readactualGDS/proofarea/cutmetadata and qualify full560DRC/deepflatLVS13 + independently reconstructedcanonicalall113partitions×13layers. Then freshRCwithactualnewcensus/order andunchangedfullloadedgates. If geometricadmission fails, preserveexactfailure and redesignwithcurrentnativeownership; do notlowercut/enclosure/spacing gates. Collector repair may notaloneclose allheadroom/phase/sampler failures; laterbias/architecture changes mayberequired. Nativephysical proof≠fullPHY.

Mainchip41415994457/f808321a65ca9197f10e75f2f59073d47095a718/release431237039 same live47netroute,11GiBRSS/12GiBnoswap/2GiBhostreserve. No duplicate on observationtimeout. Awaitcandidate then originalclass restoration/independentfullDRC/diodePG/connectivity/LVS/final3cornerSTA. FullclosedloopCDR/PLL/SERDES/serialGen3x4/PVT/ESD/EM remainopen. Readonly8hourmonitor automatic_native_dispatch=false. Complete derivedZIPs separatelyarchived withbyteforbyte readback; originalsealedproducerassetsets unchanged.

Observed at 2026-11-02T11:15:57.878327+00:00:
- 41415994457: in_progress/None
- 41430498959: completed/failure
- 41433864856: completed/success
- 41434944363: completed/success

## Current continuation: actual residual physical map while full loaded transient runs

Previous rootv302=fb7eba842810fe50397137b8d8aaacc8f20c0a9e/inventory787. All nativeCAD/GDS/ODB/SPICE/waves remain exclusively GitHub; local workspace empty. FullserialGen3x4PHY, mainchiproute and finalsetuphold remain OPEN.

Current candidateGDS5e5ef394 adds872Via2 at8drains plusM2/M3. Physical41427042946 passed full560DRC0/deepflat500LVS13faultrefusals. Canonical41428154889 passed96controls/1469net-layer comparisons, only emittercomponents18/62 changed. FreshRC41428920414/a53fb2f3/release431325407 actualPASS:500devices26218R16796C. Model2112612bytes SHAd9b1de9dfce3564af178bc0ec643b1f9e7b9bee13e04d6cb2fcce7da3c14042e;composition1015041bytes SHAbcdf63fc9053749ae23794cacc43b9069a988a2fad99885de9ab60a28957ee0a.

Loaded41430498959/source8a73ba2c575c4e6b8accf1dff736d481e1e53606/release431336246/branchcodex/cdr-drain-m23-loaded has passed unchanged sourcecontrols and is executing original full transient. All29frozendefinitions/5blocks9files/43fdpreparationmeasurement/stimuli/loads/phase-current-Vce-sampler-comparatorgates/fullraw unchanged. Actualneworderxn,xp at15/16;yp,yn at19/20; old-selector negative nowxp,xn. Census26218R16796C. Do not substitute passive/physical success for actualloaded gates.

Resistance41430503141/3d260104 completed SUCCESS. Rootv302 saved independently authenticated incremental comparison against immediate9fef sourceM2:16emitterpaths reduced5.285668..5.627096ohm/27.461296..28.970251percent; other16queries(8collector+8ground) unchanged within8.2e-12ohm. Original native reference b9b9 remains explicitly distinguished. All114partitions/500primitiveparameters/1446anchors checked. Passive unitcurrent is not actual operating current/voltage.

NEW read-only physical map41431599840/source6a6b14ef4cb48666ce4ada1d89ba3796075389b2/branchcodex/cdr-drain-m23-critical-access/release431344051. All103originalsourcecontrols passed. Derives from6e68a6c8 current-sourceM2map with only actualfreshRC/candidate/status/resistanceproducer metadata plus actual26218resistor census in inspect_critical_access. The truthful result field nowall26218native_exported_resistors_equal. All978nativeports/alloriginal-extractionownership/7documentedMIMrelocations/13conductorunions/fullRendpoints-values-multiplicity remain mandatory. AllotherfunctionASTs identical; actualmapping methods andcontrols unchanged. Acquires all complete nativearchive members with SHA256. This run changes no geometry and claims no electrical acceptance. Purpose: exact physical residual endpoint ownership for the next correction if the pending loaded transient still fails.

NEXT: follow same loaded41430498959 and map41431599840. Read complete actual measurement-result only after native output preserved. If rejected, preserve fullraw and derive unchanged fullwave diagnosis fromaaf92 after binding exactnewproducer/rawhash and checking actualfailedHBTset; no threshold relaxation. Combine actual operating voltagedrop/current with currentphysicalmap and32querysolutions before another geometry/bias change. Prior9fefloaded41422407076 remains rejected; its fullwave diagnoses collector30..93mV/emitter51..57mV losses and all failures remain archived.

Mainchip41415994457/f808321a65ca9197f10e75f2f59073d47095a718/release431237039 same live47netroute; no duplicate on observation timeout. 11GiBRSS/12GiBnoswap/2GiBhostreserve unchanged. Await candidate then originalclass restoration/independentfullDRC/diodePG/connectivity/LVS/final3cornerSTA. FullclosedloopCDR/PLL/SERDES/serialGen3x4/PVT/ESD/EM stillopen. Readonly8hourmonitor automatic_native_dispatch=false. DerivedZIPs preserved separately withbyteforbyte readback; sealednativeproducerassetsets unchanged.

Observed at 2026-11-02T10:49:31.719765+00:00:
- 41415994457: in_progress/None
- 41430498959: in_progress/None
- 41431599840: completed/success

## Verified incremental drain M2/M3 resistance result

Actual resistance run41430503141/source3d2601040c26b9e10443f674e6d2c211f8d14546 completed SUCCESS. Its original reference is b9b9; the new derived comparison independently authenticates BOTH sourceM2 run41423647133 and drainM23 run41430503141, both complete artifact ZIP digests and their identical original reference. All32 stable querylabels and exact source/sink terminal identities are bound before comparing actual after_ohm values.

Against IMMEDIATE sourceM2 predecessor9fef, all16 emitter-to-drain paths improved by5.285668407882763..5.6270956810249135ohm (27.461296408640123..28.970250552801946percent). Other16paths(8collector+8ground) maximum absolute delta8.196110456992756e-12ohm. Full114partitions/500primitive parameters/1446terminal identity checks passed in each original native comparison. This result proves targeted passive resistance reduction, NOT actual operating voltage/current, electrical acceptance, closed-loop CDR or fullPHY.

Machine-readable proof: docs/evidence/drain-m23-incremental-resistance-41430503141.json. Reproduction source uses only API/derivedJSON and no local native CAD: docs/evidence/drain-m23-incremental-resistance-analysis.py. Native current model was500devices26218R16796C, original sourceM2model500devices24530R15676C; the comparison preserves each actual census.

Loaded41430498959/source8a73ba2c575c4e6b8accf1dff736d481e1e53606/release431336246 is the next acceptance gate. Keep full rawwaves/actual failures and original thresholds. Mainchip41415994457 remains the same47net routing handle; never duplicate on observation timeout. FullserialPHY, mainchip routing, finalDRC/LVS/3cornerSTA remain open. All native work is GitHub-only.

Observed at 2026-11-02T10:44:00.227802+00:00:
- 41415994457: in_progress/None
- 41430498959: in_progress/None
- 41430503141: completed/success

## Current continuation: drain M2/M3 fresh RC PASS; full loaded transient and resistor analysis dispatched

Root v300=1ee6d1ee2978eeaa2c8bd04e529f496736446207, inventory785. Native CAD/GDS/ODB/SPICE/waves remain GitHub-only. Local workspace empty. Full serial Gen3 x4 PHY, mainchip routing and final setup/hold remain OPEN.

Actual GDS5e5ef394 (1075316bytes) adds872Via2/8drains and M2/M3. Full physical41427042946 passed560DRC0, deep/flat500primitiveLVS and13fault refusals. Canonical41428154889 passed96controls/1469partition-layer comparisons; only emitter components18/62 changed. Prior counter-sampling physical failure41426359185 is preserved; one unchanged retry succeeded.

FRESH RC41428920414/sourcea53fb2f3e56b1175172b4320a1ec443bb57773db/release431325407 completed SUCCESS. Actual500devices26218R16796C. Model2112612bytes SHAd9b1de9dfce3564af178bc0ec643b1f9e7b9bee13e04d6cb2fcce7da3c14042e;composition1015041bytes SHAbcdf63fc9053749ae23794cacc43b9069a988a2fad99885de9ab60a28957ee0a. Derived13133507423=8369726bytes SHAa6dde0d967d9c8f4f36bdff608e61e935eee71f1557672383f7bc3610ce7c60a. Originalqualification3767bytes SHAf7a940f37c5cfe20d190862074b73f0ff6cd839c8393b64d806adbb6102b4db0. Numerical PASS does not imply qualified PEX or electrical/PHY acceptance.

LOADED41430498959/source8a73ba2c575c4e6b8accf1dff736d481e1e53606/branchcodex/cdr-drain-m23-loaded/release431336246. Source controls passed; fullwave job follows. Exact producer/assets/allmembers/model/composition/current measured census and25ports+wire_cref bound. Semantic order nowxn,xp at15/16;yp,yn at19/20. Old-selector negative fixture nowxp,xn; old-port-order remainsyn,yp; counts negative remainsR+=1. Qualification fixtures explicitly native_executed=false/source_only_metadata_fixture=true. Host reverses exactly to e96ca21 except current metadata/census/order and meaningful negative fixture. All29frozen definitions/5blocks9files/43fdpreparation and measurement bodies/stimuli/loads/fullwave preservation/phase-current-Vce-sampler-comparator gates unchanged. Preparation-only workflow-title assertion initially stopped before mutations, corrected to actual dispatch-only YAML; no native failure.

RESISTANCE41430503141/source3d2601040c26b9e10443f674e6d2c211f8d14546/branchcodex/cdr-drain-m23-resistance. Unchanged32complete-network queries/reciprocal solves/26solver controls/7comparison controls/4partition controls. Reference remains ORIGINALb9b9 result41395210468, NOT immediate9fef. Current census26218R16796C; old reference census24530R15676C retained. Host exactly reversible to a11002 after metadata/currentcensus pins/status. Need all114partitions/1446anchors/500primitive parameters before semantic comparison. Unit-current resistance is not operating voltage/power. Initialdispatch HTTP500 was reconciled against exact branch/runlist; only one actual run exists. Do not replay source publishers.

Parent9fefloaded41422407076 remains REJECTED:phase14.3818mV<30,VI43.1925uA<50,HBTminVce.337377/.334107/.359545/.358041V<.4,sampler45.78125/41.71875/51.09375/54.53125ps>37.5,wrongsign0/0/2/34. Fullraw1045823299bytes SHAb1824920ca04941650b2cab231f00dc6a1b926becbed42e302a3dd882465ac69 stayscloudonly. SourceM2 fullwave diagnosis41424462139 reproduced all scalars:collectorloss30..93mV/emitter-to-MOS51..57mV motivated newdrainrepair. SourceM2 resistance41423647133 measured ground-25.51015ohm vsoriginalb9b9 without closing electrical gates.

NEXT: follow same loaded41430498959 and resistance41430503141 handles. Inspect complete actual scalar gates, preserve fullraw and failures. If rejected, derive fullwave diagnosis from aaf92 with actual newproducer and first verify actual failing HBT set; never soften gates to fit. Compare emitter resistance to both b9b9 and separately authenticated9fef by stable querylabels; do not confuse baselines. Full closed-loop CDR/PLL/SERDES/Gen3x4/PVT/ESD/EM remain open.

Mainchip41415994457/sourcef808321a65ca9197f10e75f2f59073d47095a718/release431237039 remains same live47netroute. 11GiBRSS inside12GiBno-swap plus2GiBhostreserve. Do not restart on observation timeout. Await candidate then originalclass restoration/independent fullDRC/diodePG/connectivity/LVS/final3cornerSTA. Read-only8hourmonitor automatic_native_dispatch=false. Permanent derivedZIP copies are separate from sealed native releases, with fullbyte readback.

Observed at 2026-11-02T10:41:16.218513+00:00:
- 41415994457: in_progress/None
- 41428920414: completed/success
- 41430498959: in_progress/None
- 41430503141: completed/success

## Current continuation: drainM23 complete canonical PASS and actual freshRC running

Previous verified rootv299=761d4fd9b65fcc3abeca09e52cd52de662197a24/784inventory. All nativeCAD/GDS/ODB/SPICE/waves exclusivelyGitHub; local workspace empty. FullserialPCIeGen3x4PHY/mainchiprouting/finalsetuphold remainOPEN.

NewdrainM23GDS1075316bytes SHA5e5ef3940bb0e410af8bbb92376e2c1cb60e3c520e37b65c7e675af41e58603f from41425901322/fe271530/release431305033 adds872Via2(109per8MOSdrain) andM2/M3only. Physical41427042946/source5b7b7532067870a402d5f1cd32610318652fe3cb/release431312532 actualPASS:560DRC0,deep/flat500primitiveLVS,13negativefaults allrejected. Firstidenticalsource41426359185 counter-sampling failure preserved; exactlyone unchangedretry succeeded.

FULLCANONICAL41428154889/source198797326d783aba9a57e46ce9ce690863387490/release431319979 SUCCESS. All96controls=73unchanged+23newdrainadversarial. All113completepartitions×13layers=1469actualcomparisons, onlycomponents18and62 changeM2/Via2/M3. Eachcomponentareas79200000/15739600/75550000nm2;total158400000/31479200/151100000. All872cuts independentlyreconstructed fromexactoriginalanchors with bothmetal50nmenclosure/old-new240nmspacing. Allothernet/layer material exact. Native500devices1446terminals238nets114electricalnets113components978logical/physicalanchors25ports and78canonicalfilesqualified.

Canonicalderived13131924709=1450817bytes SHA447e792cac27d9f0e9a228df3faf8e5f46c8efb66b8f313f3422ed46feae790f. Controls13132493994=1091bytes SHA7136276c9fa3d98e22adfa53e562e8ca7dfd1c8a866e1769b00eef1d0c452c77. Actualnewportorder = avdd,avss,sub,ird,cn,cp,dn,dp,irb,ira,irc,ibda,ibdc,ibs0,irx,xn,xp,ibs1,iry,yp,yn,irvx,irvy,vin,vip. Onlypositions15/16 changed fromparentxp,xn toxn,xp; namednetidentityexact.

NEW freshRC41428920414/sourcea53fb2f3e56b1175172b4320a1ec443bb57773db/branchcodex/cdr-drain-m23-fresh-rc/release431325407. Sourcecontrols passed andnative-rc isactive. Wholecanonicalartifact/current78files/completeproducerindexpins independentlyauthenticated. Bothnumericcfg and exacthostorder guard use measurednew25ports. Host exactlyreverses toqualifiedbbbd992fcc8806fcb9132d22d09cf42c5c3c234b after branch/schema/producer/candidate/status/actualorder substitutions. Numericalmethods,13commandplan,bothMIMorders,658runtimefiles,resource/lifecycleboundaries and11qualificationreceipts unchanged. This isactualnewRC; finalR/Ccounts/model/compositionhashes mustcome fromnewnativeoutput.

NEXT: awaitactualfreshRC41428920414PASS andauthenticateall11receipts/model/composition/newcounts. Derive loaded frome96ca21ed0c63dd0353cbd499be25c1b0ed22c75. Update exactcandidate/newproducer/nativeR/Ccounts and model/composition/interface = actual25ports +wire_cref. Keep29frozennumericaldefinitions/5blocks9files and43fdprepare/measure bodies. IMPORTANT current old-selector-port-order negativefixture setsxn,xp at15:17, whichisNOWVALID. Change onlythatmutation tooldparentxp,xn so itremainsrealnegative. old-port-order at19:21 remainsyn,yp and validnegative; Rcount+=1 unchanged. Source-onlyfixtures staynative_executed=false. Runactualunchangedfullwave phase/current/Vce/sampler/comparatorgates; nopassfromphysical/canonical/RC.

Parent9fefloaded41422407076 remainsREJECTED:phase14.3818mV<30,VI43.1925uA<50,HBTminVce.337377/.334107/.359545/.358041V<.4,samplerA/B/C/Ddelay45.78125/41.71875/51.09375/54.53125ps>37.5,wrongsign0/0/2/34,comparatorsfailed. Fullraw1045823299bytes SHAb1824920ca04941650b2cab231f00dc6a1b926becbed42e302a3dd882465ac69 stayscloudonly. Fullwave diagnosis41424462139 reproducesallscalars:collectorloss30..93mV/emitter-to-MOS51..57mV motivateactualdrainrepair. SourceM2groundpassive-25.51015ohm vsoriginalb9b9didnotcloseelectricgates. PVT/EM/closedloopCDR/fullserialPHY stillopen.

Mainchip41415994457/sourcef808321a65ca9197f10e75f2f59073d47095a718/release431237039 same live47netrouting,11GiBRSSinside12GiBnoswap/2GiBhostreserve. No duplicateonobservationtimeout. Eventuallyoriginalglobalclasses/independentDRC/diodePG/connectivity/LVS/final3cornerSTA. Readonly8hourmonitor automatic_native_dispatch=false. Complete derivedZIPs permanentlyarchivedseparately withbyteforbyte readbacks; sealednativeproducerassetsets unchanged.

Observed at 2026-11-02T10:31:55.880060+00:00:
- 41415994457: in_progress/None
- 41428154889: completed/success
- 41428920414: in_progress/None

## Current continuation: drainM23 full physical PASS; complete independent canonical proof executing

Previous fully verified rootv298=2b20e771ed0fd0935ea555b6b67c4d6cc695eee5/783inventory. NativeGDS/ODB/SPICE/waves andarchives exclusivelyGitHub;local workspace empty. FullserialPCIeGen3x4PHY/mainchiprouting/finalsetuphold remainOPEN.

Actual candidateGDS1075316bytes SHA5e5ef3940bb0e410af8bbb92376e2c1cb60e3c520e37b65c7e675af41e58603f fromgeneration41425901322/sourcefe2715306626db1367aca6dbf9637b1e06b35a20/release431305033:8MOSdrains3/4/5/6/32/33/34/35,M2+M3rectangles[x-150,y-200,x+1250,y+17800],872newVia2(109perdrain),only10/29/30areas158400000/31479200/151100000nm2. All103originalgeometrycontrols passed,all13unions/exactserialization/materialreversal preserved,no primitive/Via1change.

FULL PHYSICAL41427042946/source5b7b7532067870a402d5f1cd32610318652fe3cb/release431312532 SUCCESS. Actual560categoryDRC0markers,deep/flat500primitiveLVS PASS,all13faults REJECTED_EXPECTED_FAULT. All16steps checked. Same43source/contextcontrols and frozencheckerSHA3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66. Derived13132766774=354515bytes SHA30fb20281e48e53dced451e723a5b36b67027a9f6c3ec85494d394e57b96605f. Nativefallback13132702065 remainscloudonly. Earlier identicalsource41426359185 stopped onmissingcounter resampling afterfullDRCPASS; completefailedhistory retainedv298. Exactlyone retry, no relaxed supervisor or electrical/physical thresholds.

NEW completecanonical41428154889/source198797326d783aba9a57e46ce9ce690863387490/branchcodex/cdr-drain-m23-canonical/release431319979. Independently reauthenticate all3236currentreference freshRC41420011926 native members; GDS9fef07bc1018452bytes andL2N2005450bytes SHA1c354daa4898a789eb0f91e52ac2dc6797b6abfbf79f45530ff866d5b53a3261. Completepassedphysicalcapsule also authenticated. New independent drain_m23_variant/prove_material reconstruct exact8rectangles/872cuts on ORIGINAL two emitter partitions. Eachoriginalnativeanchor must match fullcanonicalreference exactly; devices3..6 use$159 and32..35 use$700. OriginalM1point andoriginalM2/M3lower+upperattachments required. Exact190nm cuts/bothmetal50nm enclosure/old-new240nmspacing independently evaluated. Each109cutgrid dx0/480/960,dy0..17280step480 excluding(0,0),(0,17280).

All113nativepartitions×13layers=1469material comparisons required; exactly6changedrows across2originalemitterpartitions/3layers;allothermaterial exact. Combinedcutcount436perpartition and totalarea perlayer pinned. Original500device1446terminal25port identities/anchors/transforms/sourcepinwitnessfaults and78canonicalfile census remain unchanged. All73oldsource/geometrycontrols preserved plus23newdrain mutations=96expectedcontrols, actual count must pass. Actualnative methods and supervisor boundaries unchanged; oldavss-onlywhitelist is not reused.

NEXT: follow41428154889. OnactualcanonicalPASS authenticate fullqualification/files and measured semanticportorder; derive freshRC fromqualifiedbbbd992fcc8806fcb9132d22d09cf42c5c3c234b (sourceM2 freshRC41420011926). Preserve entire13commandpipeline/11native receipts/bothMIMorders/658runtimefiles, measureactualnewR/Ccounts/model/composition. Then derive loaded frome96ca21ed0c63dd0353cbd499be25c1b0ed22c75 using actualnewmodel/ports; preserve29frozen numericaldefinitions,5blocks9files,43fdprepare/measure/fullstimuli/phase-current-Vce-sampler gates. Ensure old-port-order negative fixtures are actuallydifferent from newlymeasuredorder; never assume previousorder. NegativeR-count fixture+=1 stays. Sourcefixtures remainnative_executed=false. Do not infer electricacceptance fromphysical/canonical/RC.

Parent9fefloaded41422407076 isREJECTED with fullraw1045823299bytes SHAb1824920ca04941650b2cab231f00dc6a1b926becbed42e302a3dd882465ac69;phase14.3818mV/30,VI43.1925uA/50,HBTminVce.337377/.334107/.359545/.358041V/.4,samplerA/B/C/Ddelay45.78125/41.71875/51.09375/54.53125ps/37.5,wrongsign0/0/2/34,comparatorsalsofail. Fullwave diagnosis41424462139 reproducedallscalars;collectorlosses30..93mV/emitter-to-MOS51..57mV justifiedactualdrainrepair. Newground-only resistance-25.51015ohm (~56percent vsoriginalb9b9) didnotcloseelectricalgates. PVT/EM/closedloopCDR/fullserialPHY remainopen.

Mainchip41415994457/sourcef808321a65ca9197f10e75f2f59073d47095a718/release431237039 same live47net/64iteration/seed42/2thread/1691protectedclock native routing. No duplicateonobservationtimeout. Need eventualoriginalglobalclasses/independentDRC/diodePG/connectivity/LVS/final3cornerSTA. Readonly8hourmonitor automatic_native_dispatch=false. Separatecomplete derivedZIP archives/hierarchicalrootpublication/fullreadbacks; sealedproducerassets unchanged.

Observed at 2026-11-02T10:24:03.991418+00:00:
- 41415994457: in_progress/None
- 41427042946: completed/success
- 41428154889: in_progress/None

## Current continuation: actual drainM23 full DRC PASS; physical suite counter-sampling failure and exact-source retry

Previous rootv297=3edf3f984c470909742296cbca7394a1f63ca125/782inventory fully readback-verified. NativeCAD/GDS/ODB/SPICE/waves exclusivelyGitHub; local workspace empty. FullserialPCIeGen3x4PHY,mainchiprouting/finalsetuphold remainOPEN.

Generation41425901322/sourcefe2715306626db1367aca6dbf9637b1e06b35a20/release431305033 SUCCESS;103originalcontrols andall8realdrain geometricguards. ActualGDS1075316bytes SHA5e5ef3940bb0e410af8bbb92376e2c1cb60e3c520e37b65c7e675af41e58603f. AddedM2/Via2/M3 onlyareas158400000/31479200/151100000nm2,872new190nmVia2=109perdrain. SourceM2parent9fef07bc1018452bytes unchanged, same500primitives. Exactserializeddelta/originalmaterialreversal verified. Fullgeometry and operatingwave evidence recordedrootv296/v297.

Firstphysical41426359185/source5b7b7532067870a402d5f1cd32610318652fe3cb/release431308018 terminalFAILURE. All43source/contextcontrols passed. Actualfull560DRC process0/zero markers PASS, reportSHA65323bd352a208ac709ce75e782faf3b6dd9291cce44ddb14ee15e01d5e919b0. Complete13fault LVSsuite did NOT finish: at85.60125085seconds qualified supervisor terminated processgroup with memory_sample_unavailable, CounterError Missing-counter resampling window exhausted. Lastsuccessfulsample489404KiBgroupRSS and14982108KiBavailable, farinside10GiBRSS/2GiBreserve. This is not memory-capacity exhaustion, geometryDRC failure or accepted LVSsuite. Nativechecker/source/gates unchanged.

Failedderived13132670907=301000bytes SHA99e7eb505410a12b17fdaff7242a651db440ec8b98d8014764fa2f53d102d6c2. Complete native release index701315896=14697bytes SHAbcff77d2cb7b7d42625efcaa951c2984c0017956bb262ede8ab89edc6adf9c68;native701315895=3478583bytes SHA546e508f751d73f918d3f835fc4ff901d5e3c6102cf7ab015bb1688ee2865b29 stayscloud-only. Native fallback13132352526 also retained. Allfailed evidence and partialreports preserved.

ONE bounded exact-source retry41427042946/source5b7b7532067870a402d5f1cd32610318652fe3cb/branchcodex/cdr-drain-m23-physical/release431312532. The oldrun was authoritatively terminal and no samebranch job live before dispatch. Newrun attempt1, samecandidate/source/checker/control/limits; NOT restart because of an observationtimeout. No samplingguard disabled or threshold relaxed. Follow this exactrun. If sameinfraissue recurs, investigate qualified/proc counter sampler with preservedfailures and targeted race controls rather than loopblindretries.

After actualfullphysicalPASS, create NEW canonical exactdelta proof relative9fef07bc using current producer41420011926 (freshRC) and fullphysicalretry41427042946. Actualtwoemitterpartitions correspond8MOSdrainanchors, additionsonly10/29/30,872cutcenters. Independently reconstruct eachrectangle[x-150,y-200,x+1250,y+17800] and each109cutarray: dx0/480/960,dy0..17280step480 excludingexisting-conflict(0,0)and(0,17280), then actualbothmetal50nm andold/new240nm spacing checks. Preserve originalfull113partition13layer material comparisons and500primitive1446terminal identity. Keep all73oldcanonicalcontrols andaddnewdrainadversarialcontrols. Neverreuse avss-onlyM2/Via1/Via2 whitelist. Then actualfreshRC,measureactualportorder and unchangedloadedfullwave gates.

SourceM2loaded41422407076 remainsREJECTED:phase14.3818mV/30,VI43.1925uA/50,fourHBTminVce.337377/.334107/.359545/.358041V/.4,samplerA/B/C/Ddelay45.78125/41.71875/51.09375/54.53125ps/37.5,wrongsign0/0/2/34;comparatorsalsofailed. Fullraw1045823299bytes SHAb1824920ca04941650b2cab231f00dc6a1b926becbed42e302a3dd882465ac69 stayscloud-only. Fullwave diagnosis41424462139 reproducesallscalars; actualemitter-to-MOSdrops51..57mV andcollectorconnectiondrops30..93mV justifiednewdraincandidate. Physicalmap41424965941 passedall978port/24530R/13unionchecks. Groundpassive-25.51015ohm didnot closeelectricalgates. FullclosedloopCDR/PHY/PVT/EM notaccepted.

Mainchip41415994457/sourcef808321a65ca9197f10e75f2f59073d47095a718/release431237039 same live47netrouting. Follow samejob; eventualoriginalglobalclasses/independentDRC/diodePG/connectivity/LVS/final3cornerSTA. Readonly8hourmonitor automatic_native_dispatch=false. Separatepermanentevidence archives andhierarchicalrootpublication withallreadbacks; originalsealedproducerassets untouched.

Observed at 2026-11-02T10:15:19.689654+00:00:
- 41415994457: in_progress/None
- 41426359185: completed/failure
- 41427042946: in_progress/None

## Current continuation: actual drain M2/M3 candidate generated; full physical qualification dispatched

Previous verified rootv296=e153d93bb49f38c3d761d47c73d5bb77792503a5,780inventory. All nativeGDS/ODB/SPICE/wave archives exclusivelyGitHub; local workspace empty. FullserialPCIeGen3x4PHY,mainchiprouting andfinalsetup/hold remainOPEN.

Current sourceM2 parent9fef07bc passed full560DRC/deepflatLVS13/canonical1469comparisons/freshRC41420011926 but loaded41422407076 actuallyREJECTED with engineexit0 and full113475rows1152columns1045823299bytes rawSHAb1824920ca04941650b2cab231f00dc6a1b926becbed42e302a3dd882465ac69. Phase14.3818mV<30;VI43.1925uA<50;fourHBTminVce.337377/.334107/.359545/.358041V<.4. SamplerA/B/C/Ddelay45.78125/41.71875/51.09375/54.53125ps>37.5;wrongsign0/0/2/34. ComparatorX/Y alsofailed. All fullwaves and scalar failures preserved rootv296 and release431279993. No gates loosened.

Fullwave diagnosis41424462139/aaf92f61 SUCCESS exactlyreproduces all scalar measurements with originalparser/body. Actual emitter-to-MOSdrain drops51..57mV and collector same-net drops~30..93mV. Ground-only repair increasedcurrent, so next candidate targets signal drain access. Passive41423647133/a11002d proves8ground paths-25.51015ohm vs ORIGINALb9b9 (~56percent), not electricalclosure.

Actual physicalmap41424965941/source6e68a6c8fc0f641803af5f05f492c10a0d021b97/release431298692 SUCCESS: all103controls,978original/extractedanchor ownership/coordinate checks,13conductorunions and24530native-exportedresistor endpoints/value/multiplicity. Derived13130664324=476687bytes SHAc3084a8740b194cb4eca40cf3f29bfc4c963898f2fa67e4c2ee7e012629162cb. Current realdrains have narrowM2/M3 at(x,y) and originalupperattachment(x,y+17600nm);8actual originalM1drains preserved.

NEW generation41425901322/sourcefe2715306626db1367aca6dbf9637b1e06b35a20/branchcodex/cdr-drain-m23-reinforcement/release431305033 SUCCESS. All103original controls unchanged. GDS1075316bytes SHA5e5ef3940bb0e410af8bbb92376e2c1cb60e3c520e37b65c7e675af41e58603f. Originalinput9fef07bc1018452bytes;inputL2N2005450bytes SHA1c354daa4898a789eb0f91e52ac2dc6797b6abfbf79f45530ff866d5b53a3261. Derived13131907548=291402bytes SHA8d4f590d937513a006e97ffb315e70079c41198bdcd17c8ee1fd4cb42264b2b9;controls13130869316=1254bytes SHA95f3723d7b29d3741f1748a025b270e704010ac6493f3a40bc9580870e480ae7.

Added onlylayers10/29/30 (M2/Via2/M3) areas158400000/31479200/151100000nm2. For each8actualMOSdrain3/4/5/6/32/33/34/35, M2+M3 rectangle[x-150,y-200,x+1250,y+17800]nm. Via2 centers dx0/480/960,dy0..17280step480 admitted only exact190nm cut/50nm bothmetal enclosure/240nmexisting-new spacing. Actual109perdrain=872unique cuts; rejected originaloverlap/spacing positions retained. Every actualguard passed, full13nativeunions andserializeddelta verified, exact originalmaterial recovered afterreversal. No devices orVia1 changed. OriginalVia1-only failure staysrejected; that coveragegate was neverlowered. No physical/electrical acceptance fromgeneration.

NEW fullphysical41426359185/source5b7b7532067870a402d5f1cd32610318652fe3cb/branchcodex/cdr-drain-m23-physical/release431308018. Same frozenphysicalcheckerSHA3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66,full560DRC/deep-flat500primitiveLVS13,43original source/contextcontrols. Candidateauthentication exactGDS/areas/872cutcenters/8drainidentities/two actualnativeemitter nets/individualmetal andvia guards. Current schematic andLEF areindependently matched to41420011926. Nativechecker/verificationbodies unchanged exceptlabel.

NEXT: Follow actualphysical41426359185. Onfailure preserve allmarkers/native data and repairrealgeometry. OnPASS build NEW completecanonical delta proof relative current9fef07bc, with bothnativeemitterpartitions (actualdrain anchors), exactM2/Via2/M3 reconstruction ofall8rectangles/all872cuts, allother113partition/13layer material comparisons and500device1446terminal identity preservation. Do not reuse older source-ground-only canonicaldelta whitelist. Use actual measuredports and unchangedcanonical/nativequalification; then actualfreshRC and unchangedloaded fullwave gates. FullEM/currentdistribution/PVT/closedloopCDR/fullserialPHY remainopen.

Mainchip41415994457/sourcef808321a65ca9197f10e75f2f59073d47095a718/release431237039 continues same47net/64iteration/seed42/2thread/1691protectedclock routing with11GiBRSSinside12GiBnoswapcontainer and2GiBhostreserve. No duplicate on observationtimeout. Returnedroute requires originalglobalclasses,independentDRC,diodePG/connectivity/LVS andfinal3cornerSTA.

Checkpointpublisher now uses hierarchical changedtrees with source/nonforce guards and fullreadbacks. Derived completeZIP archives in separateevidence releases, sealednativeproducer assets untouched. Readonly8hourmonitor automatic_native_dispatch=false. Goalnotachieved.

Observed at 2026-11-02T10:10:54.852685+00:00:
- 41415994457: in_progress/None
- 41424965941: completed/success
- 41425901322: completed/success
- 41426359185: in_progress/None

## Current continuation: actual source M2 loaded rejection diagnosed; current physical access map

Previous rootv295=07ce5eb609b9a665e66dc76ab1a0f4b9d7b7ebbc/778inventory fully readback-verified. NativeCAD/GDS/ODB/SPICE/waves exclusivelyGitHub; local workspace empty. FullserialPCIeGen3x4PHY,mainchiprouting andfinalsetup/hold remain OPEN. The actual GDS9fef07bc passed full560DRC0/deep-flat500LVS13, canonical1469comparisons/73controls and freshRC41420011926; none proves electrical closure.

Loaded41422407076/sourcee96ca21ed0c63dd0353cbd499be25c1b0ed22c75/release431279993 completed FAILURE after actual native transient exit0 with unchanged electrical gates. Complete raw113475rows/1152columns/1045823299bytes SHAb1824920ca04941650b2cab231f00dc6a1b926becbed42e302a3dd882465ac69, all rows original/unmodified, maxstep.3125ps/end34.25ns. Derived13130843225=1367845bytes SHA82afe810a9b53a9cb09703d3c2f3c3c6fdb5a6e2871d2a803fe0611c1edfb0a5. Complete native release index701266971=24685bytes SHA9b6e7cb5a8b8dc0e1fd43511ea3fec64b635bfd228b16b36d9933749fac206ee; parts701268444=1031bytes SHA1547b41abb98c612ce2b8d891b72cee788ff4e6ae7579efee53c52bb3c8d0736. Native parts701267008/701267393/701267724/701268167 remain cloud-only. Initial negative-fixture failed41422125181 preserved separately inv295; no native execution in that source-control failure.

Actual phase14.3817746547mV<30;VI43.1924974678uA<50. HBT61/62/115/116 minimumVce0.3373770346/0.3341069023/0.3595448875/0.3580410229V<0.4. SamplerA/B/C/D maximumvalid45.78125/41.71875/51.09375/54.53125ps>37.5;wrong-sign0/0/2/34;below100mV129/128/128/128 of765. C/Dsign errors improved from15/48 in old4ccf but remainfailed. ComparatorX/Y wrongsign387/44 anddelay118.90625ps alsofailed. No threshold/stimulus/case/portname relaxation. External8GHztest is not closedloopCDR.

Fullwave diagnosis41424462139/sourceaaf92f61a67cd74c33c6c871baf88b2be038caed/branchcodex/cdr-source-m2-wave-diagnosis SUCCESS. Derived13131201670=120771bytes SHAc2b8c82d9ea3bd6174c345a9a0bdda5eaa0670e7eff0e8e7f8b54edc010d9bdf. Every original native archive member authenticated; fullwave parsed, every HBTminimum and sampler/comparator margin/delay/sign count reproduced. Parser controls and entire diagnosis body byte-identical to qualifieda36dd3 except branch/current inputbindings. Sameexact4HBTfailure-set guard preserved.

At61/62worstVce:collector0.82577/0.82448V,emitter0.48840/0.49037V,Ic3.915/3.834mA. ConnectedMOS3..6 drains0.4342..0.4374V,sources0.2731..0.2764V,gates0.9561V. Collector's same-net driving emitters54/56 are46.5..67.0mVhigher. At115/116worst:collector0.84866/0.84918,emitter0.48911/0.49114,Ic3.959/3.879mA. MOS32..35drains0.4343..0.4374,sources0.2785..0.2817,gates0.9630. Collector driving106/108 same-net drop29.7..92.6mV. Emitter-to-MOS drops51..57mV remain. Source-localground reduction increasedcurrent; do not assume further local ground changes automatically fixheadroom.

Qualified passive41423647133/a11002d current9fef against ORIGINALb9b9reference: all8sourceReff -25.51015ohm (~56percent), to19.7183..20.1611ohm. Other24queries unchanged within2.1e-11ohm. Full500devices1446anchors114partitions preserved. Residual source-local7.01435ohm andshared4.88213/1.35196ohm contributions do not equal operatingloss without actualcurrent. Nativecollector/emittercritical edges retained inall32scope.

Current read-only physicalmap41424965941/source6e68a6c8fc0f641803af5f05f492c10a0d021b97/branchcodex/cdr-source-m2-critical-access/release431298692. Uses actualcurrent freshRC41420011926 and current32query results41423647133. All103geometrycontrols unchanged; maps all978portcoordinates,documented7MIMrelocations,all24530native/exportedresistors and13nativeconductorunions. Only acquire_current metadata andinspect_critical_access producerconstants change; numerical/geometry bodies preserved. Await real native endpoint/owned/foreign material map before additional collector/emitter/groundlayout design. Keep existingVia1-only failure requiring4vias/everydrain; do not lowercoverage.

Mainchip41415994457/sourcef808321a65ca9197f10e75f2f59073d47095a718/release431237039 same live native47net routing. Follow exactjob, no timeout duplicates. Returncandidate requires originalglobalclasses,independentfullDRC,diodePG/connectivity/LVS,final3cornerSTA.

Root publishing uses hierarchical changedtrees after originalHTTP422, exactsource/nonforce ref guards and fullreadbacks. Derived ZIPs are permanently stored in separate evidence releases with digest/completebyte readback; never mutate sealed native producer assets. Readonly8hourmonitor automatic_native_dispatch=false. FullPHY/PVT/EM/production/mainchipfinaltiming remainOPEN.

Observed at 2026-11-02T10:00:38.265877+00:00:
- 41415994457: in_progress/None
- 41422407076: completed/failure
- 41424462139: completed/success
- 41424965941: completed/success

## Current continuation: source M2 reduces actual ground-path resistance; loaded and mainchip route active

Previous rootv294=1fd50238ec67ad4cce93775de4ef307959c9bfcc,775inventory is fully readback-verified. Full serial PCIe Gen3x4 PHY, mainchip routed integration and final setup/hold remain OPEN. All native GDS/ODB/SPICE/wave processing exclusively GitHub; local workspace empty.

SourceM2 GDS9fef07bc already passed full560DRC0markers/deep-flat500primitiveLVS13 in41417079679. Full canonical41419044277 passed73controls and1469 complete partition/layer comparisons. FreshRC41420011926/sourcebbbd992fcc8806fcb9132d22d09cf42c5c3c234b/release431264092 completed actual numerical pipeline including11native receipts. Model1981942bytes SHA60c292b827899ad2b222df6fd96a20a7265004832ada95fa80ebb87df5ebf0dc, composition974729bytes SHAeebbf88566d615a6cae7b9a1c7d03e8346bc52580eea8c72fc1fdb92b160f391. Complete500devices/24530R/15676C. Physical/canonical/RC acceptance is not electrical acceptance.

New loaded41422407076/sourcee96ca21ed0c63dd0353cbd499be25c1b0ed22c75/branchcodex/cdr-source-m2-loaded/release431279993 passed source-controls and started actual loaded transient. Retains29frozen numerical definitions,5blocks,9files,exact43fdprepare/measure,all stimuli/load/phase/current/Vce/sampler gates. Measured25port order is avdd,avss,sub,ird,cn,cp,dn,dp,irb,ira,irc,ibda,ibdc,ibs0,irx,xp,xn,ibs1,iry,yp,yn,irvx,irvy,vin,vip plus wire_cref in RC interface. Earlier41422125181/sourcee65a44db15798f7b7c72d205974b48e26de03002 failed ONLY the old-selector-port-order negative fixture: its xp,xn mutation had become valid. No native acquisition/transient occurred. Corrected fixture now uses previous xn,xp. No checker or numerical threshold relaxed. Failure logs and both attempts retained.

Actual passive comparison41423647133/sourcea11002d7924f6649598fbec223eb830ed64402af/branchcodex/cdr-source-m2-resistance SUCCESS. Derived13131285945=1502833bytes SHAb37f734198ded94349ef247bb9c1b052e89b460de9c0092fea95f424db8ab036. Same32full-network reciprocal solves,26solvercontrols,7comparisoncontrols,4whole-partitioncontrols. All500primitive parameters,1446terminal anchors,114complete electrical partitions preserved. Each of8MOS source paths reduced25.51015ohm versus ORIGINAL b9b9 horizontal-ground reference41395210468, from45.22849..45.67123 to19.71834..20.16108ohm (~55.86..56.40percent). Other24query deltas <=2.1e-11ohm. The current4ccf sourceM1 predecessor independently reduced0.6357ohm against same b9b9 reference; new comparison is explicitly not mislabeled as direct4ccf comparison. Unit-current edge power does not prove operating dissipation, EM, bias headroom or loaded acceptance. Ground improvement can increase selector current and worsen HBT Vce; await actual loaded results.

Mainchip41415994457/sourcef808321a65ca9197f10e75f2f59073d47095a718/release431237039 remains the same native47net/64iteration/seed42/2thread routing with1691protected clocks.11GiBRSS guard inside12GiBno-swap container and2GiBhost reserve. Do not duplicate on observation timeout. Returned candidate requires original global class restoration,independentDRC,diodePG/connectivity/LVS and final3cornerSTA.

Rootv294 initial single nested-path git/trees creation timed outHTTP422 beforecommit/refupdate. Fixed publication by building exact changed subtrees bottom-up. All33files/11597245bytes were readback-verified at1fd5023; no native job stopped. Complete derived archives permanently preserved in separate release431275466/tagcloud-derived-evidence-v294 with byte-for-byte readbacks. Sealed native producer release sets untouched. v295 uses the same safe publication and separate archive scheme.

Next: inspect actual loaded41422407076 terminal derived measurement result. If rejected, preserve entire nativewave in GitHub and bind unchanged fullwave diagnosis a36dd3a2613a365b608dc5d9b10c5a24b41d00ea to this exact new release/index/parts; reproduce every scalar before designing further ground/bias/signal changes. Follow original live mainchip job. Monitor remains read-only8hour automatic_native_dispatch=false. FullclosedloopCDR/SERDES/link,actualEM/PVT,fullchipsetuphold andproduction gates remain OPEN.

Observed at 2026-11-02T09:52:04.934587+00:00:
- 41415994457: in_progress/None
- 41422125181: completed/failure
- 41422407076: in_progress/None
- 41423647133: completed/success

## Current continuation: source M2 full canonical PASS; new actual RC extraction running

Previous verified rootv293=8c13f1e3d415f0ddcdc7e05026cb351a43f9ea70,774inventory. Full serialGen3x4PHY,completed mainchiprouting,finalsetup/hold remainOPEN. AllnativeCAD/GDS/ODB/model/waves exclusivelyGitHub. Localworkspace empty.

Actual sourceM2 canonical41419044277/sourcec0cb25a769f061912eab1274f4d17fe8964486bc/release431257808 PASSED. All73controls (58unchanged+15new M2/via adversarial); actual complete113conductorpartitions on13layers=1469comparisons. Onlyavss component14 layers10/19/29 add221876000/6931200/866400nm2. All othernet/layer material identical.500primitives,1446terminals,238native nets,114electrical nets,113wire components,978physical/logicalanchors,25publicports preserved. Every original/sourceM2 targetanchor, via enclosure/spacing/position and originalM1/M2/M3 connection independently verified. All78canonical files qualified. This is not RC/electrical acceptance.

Canonicalderived13129575704=1449986bytes SHA8f63e1f33ead15ebce37e1387e599e4aa5f74bd31c4f0c585354a8f98c1cd9b2; controls13128234918=938bytes SHA5cc8774fde9b0edb97dbe1d47f2543e7bf9bccd63ddecf83c744bf33c6935db9. Nativecanonical archive remains onlyGitHub. ActualsourceM2 GDS1018452bytes SHA9fef07bce22bce079cf82e3c7600932aa6adce49359838f6c72569fbde3ef61b already passed full560DRC0markers/deep-flatLVS13 in41417079679/source41d9c4a6d96d9e97b1b58dad84fda478f50b2ee0/release431244468.

NEW freshRC41420011926/sourcebbbd992fcc8806fcb9132d22d09cf42c5c3c234b/branchcodex/cdr-source-m2-fresh-rc/release431264092. Binds actualnew78canonicalfiles and qualification directly from wholeauthenticatedartifact, current500device/1446terminal identities. Nativeportorder changed at15/16 xn,xp->xp,xn and19/20 yn,yp->yp,yn. All25named net identities are independentlyunchanged. BOTH numericalcfg and exact host guard use measuredorder: avdd,avss,sub,ird,cn,cp,dn,dp,irb,ira,irc,ibda,ibdc,ibs0,irx,xp,xn,ibs1,iry,yp,yn,irvx,irvy,vin,vip. This is ordering metadata, not electricalsignalrenaming.

FreshRC host exactlyreverses to9750 previousqualifiedhost after onlybranch/schema/producer/candidate/status/actualportbindings. Alloriginalnumericalmethod bodies,13commandplan,preciseMIMorders,658runtimefiles,resources/lifecyclecontrols and11native receipts unchanged. Require actualnative PASS; newR/Ccounts andmodel/composition hashes must be measured. No copy ofoldmodel or source-only acceptance.

AfteractualfreshRCPASS, derive loaded from d1acc79777356767bdc61cffe96d7a8e7edc2409 using newactualcounts/model/composition/all11receipts and interface = actual25ports+[wire_cref]. Preserve29frozennumericaldefinitions/fiveblocks/ninefiles and exact43fdprepare/measure bodies. IMPORTANT old-port-order negative fixture currently writes yp,yn at19:21; newactualorder isyp,yn, so change mutation topreviousyn,yp to keep it a realnegative. Resistor-count negative already +=1 and should remain. Explicitmetadatafixtures remain native_executed=false/source_only_metadata_fixture=true. Groundbypass can changecurrent/bias and worsenHBT Vce; no electricalimprovement inferred.

Mainchip41415994457/sourcef808321a65ca9197f10e75f2f59073d47095a718/release431237039 confirmed inprogress. Same47net/64iterations/seed42/2threads/1691protectedclocks with11GiBRSS insideunchanged12GiBnoswapcgroup and2GiBhostreserve. Follow exactjob; eventualrealreturnedroute needs originalglobalclass restoration,diodePG/connectivity/LVS and final3cornerSTA. Allfailed predecessors remainpreserved.

Read-only8hourmonitor automatic_native_dispatch=false. No duplicate native dispatch on observationtimeouts. PVT/currentdistribution/EM,closedloopCDR/fullserialPHY andfinalmainchipSTA remainrequired.

Complete derived ZIPs are permanently archived separately in release 431275466 under cloud-derived-evidence-v294. Every original ZIP byte was read back and checked. Root tracks archive receipts and key qualification reports instead of expanding repetitive control fixtures. Original sealed native producer releases and all native jobs remain unchanged. The initial expanded publisher was stopped while creating unreferenced blobs, before any root ref change; no native computation was stopped.

Update: actual freshRC41420011926 completed SUCCESS; measured500devices/24530R/15676C. Model1981942bytes SHA60c292b827899ad2b222df6fd96a20a7265004832ada95fa80ebb87df5ebf0dc, composition974729bytes SHAeebbf88566d615a6cae7b9a1c7d03e8346bc52580eea8c72fc1fdb92b160f391. Loaded41422407076/sourcee96ca21ed0c63dd0353cbd499be25c1b0ed22c75/release431279993 has passed source-controls and its native loaded-wave job is live. Initial41422125181 failed only a stale negative fixture which had become valid; no native acquisition occurred in that failed run. The retry changes that fixture to previous xn,xp; no numerical thresholds changed. GitHub root tree creation previously timed out HTTP422 before commit/ref update. This publisher builds changed subtrees bottom-up and preserves source SHA checks. All native jobs remain untouched.

Observed at 2026-11-02T09:48:12.630690+00:00:
- 41415994457: in_progress/None
- 41419044277: completed/success
- 41420011926: completed/success

## Current continuation: source M2 physical PASS; current-reference full canonical proof running

Previous rootv292=f551337492ffd5bd0a20c709a7fbf682e031d3ab is fully readback verified (773inventory). Full serialGen3x4PHY,completedmainchiprouting,finalsetup/hold remainOPEN. NativeCAD/layout/model/waves onlyGitHub; localworkspace empty.

New sourceM2 GDS1018452bytes SHA9fef07bce22bce079cf82e3c7600932aa6adce49359838f6c72569fbde3ef61b from generation41416430071 passed actual fullphysical41417079679/source41d9c4a6d96d9e97b1b58dad84fda478f50b2ee0/release431244468. Actual560DRC categories0markers; deep/flat500primitiveLVS PASS; all13faults REJECTED_EXPECTED_FAULT. Physicalqualification explicitly electrical_accepted=false,new_RC_executed=false,full_phy_accepted=false,final_timing_complete=false. Derived13127274700=363167bytes SHA6dff1eb3a41f88efdbae32c83744df308ae9ef9c25b5485a9c048c18422a2426. Releaseindex701135347=20773bytes SHAa2fcb80ecbbc4237d6c5f32f7f981c4a3b1bad9ac3458a1dfd7ec214696adfb5; nativephysical701135346=6035043bytes SHAb8f416c017c9028b5503f65fb8acf2f51048a6f2104680f8710d88a001c6e086 remainscloudonly.

NEW canonical41419044277/sourcec0cb25a769f061912eab1274f4d17fe8964486bc/branchcodex/cdr-source-m2-canonical/release431257808. Independent sourcecontrols passed; native-canonical running. All58prior controls remain, plus15new independent sourceM2/via mutation cases. Reconstruct originalanchoredM2 column/landing and24Via1+3Via2 per source independently, require originalM1 landing,oldM2attachment,oldM3enclosure,190nm cut bounds,50nm bothmetal enclosure,240nm old/newcutspacing,all guard key sets/truevalues,all8actualoriginalanchors. Allcomplete conductorpartitions compared across ALL13layers. ONLYavss layers10/19/29 may add areas221876000/6931200/866400nm2; every othernet/layer must exactlymatch.

Reference choice resolved: use current4ccf1212 actualfreshRC41404030506/source9750f2c17a8cca7b5560a74097f04c04b769e5b1/release431157438 via existing simple acquire_reference schema in canonical PARENT. OriginalL2N1996982bytes SHA5bbfcd2257b1f287b0f7a919d3edccdaa56a668de0050f813a42c47eea0885e3 matches newgeneration input_l2n. Do not use olderb9b9reference or compare newL2Ntoold. Current complete_members file came directly from generation2671 sourceM2 input config; whole nativearchive/membervalidation retained. Canonical extraction/primitive/terminal/port/anchor/transform identity and originalfaultcontrols still native; counts must be actually measured.

If canonical passes, bind NEW actualcanonical qualification/viewfiles/portorder into freshRC source9750 baseline on newbranch, retain unchanged13command pipeline/all original numerical functions, execute all11actual qualification receipts. Do not assume nativeportorder or numerical R/Ccounts. Then bindactualnewfreshRC to unchangedloaded methods fromd1acc/43fd; previousloaded41405079602 remainsREJECTED. Groundbypass can changebias/current and worsenHBT headroom; no electricalimprovement claimed from physical/canonical. Actualvia currentdistribution/PVT/EM and fullclosedloopCDR/PHY stillrequired.

Mainchip41415994457/sourcef808321a65ca9197f10e75f2f59073d47095a718/release431237039 confirmedinprogress. Same actual47net/64iterations/seed42/2threads/1691protectedclocks route with validated11GiB RSS,unchanged12GiBnoswapcgroup/2GiBhostreserve. Follow exactjob. Require realreturnedcandidate,originalglobalclass restoration,diodePG/connectivity/LVS and final3cornerSTA. Previous10GiB failure41393730481 remainspreserved;92partialinternalmarkers is not completedDRC.

Read-only8hourmonitor remains automatic_native_dispatch=false. No duplicate dispatch on observationtimeout.

Observed at 2026-11-02T09:17:21.885031+00:00:
- 41415994457: in_progress/None
- 41419044277: in_progress/None

## Current continuation: actual source M2 bypass generated; full physical and mainchip route active

Previous verified rootv291=b7dada7de94a143af041c524c984f114fda91c88 preserved all failed/qualified memory-policy and M2-generation attempts. Native CAD/GDS/ODB/RC/waves exclusively GitHub; local workspace verified empty. Full serialGen3x4 PHY, completed mainchip routing and final setup/hold remain OPEN.

Actual sourceM2 bypass41416430071/source2671a5b64f65df0195b7a3e1e724735521609a5b/release431239884 PASSED103geometry controls and native generation. Candidate1018452bytes SHA9fef07bce22bce079cf82e3c7600932aa6adce49359838f6c72569fbde3ef61b. Exactly8source avss accesses,192Via1/24Via2, newM2 area221876000nm2,Via1area6931200nm2,Via2area866400nm2. All13input native unions,all actual owned metal/cut guards,exactserialized delta and originalmaterial reversal passed. No devices/parameters removed or changed. Generation is not fullDRC/LVS or electrical acceptance.

Derived13127433872=372610bytes SHA32d168ac55b07499e8142c95688f1e8b101298f510e272761327939cdc2df953; controls13128036797=1254bytes SHA3a4f053f8a9b007a5f64fe3cd46d409c308b8cc9170298b86e2410a920e5ac8c. Release index701115344=44711bytes SHA952bdd2be030fb0b5dfe8aea7da2d413139a8d24ae57e8a1349ca7138f4120ba; nativearchive701115342=438601bytes SHA374ab2efa102165da7048e8a658e4e8b831cbb7898077ad6c685187a7b69526f remainscloudonly.

NEW full physical41417079679/source41d9c4a6d96d9e97b1b58dad84fda478f50b2ee0/branchcodex/cdr-source-m2-physical/release431244468. Source controls passed; actual native verification started. It authenticates entire generation archive/memberindex,actualsourceidentities/declaredareas/216guardedcuts, and runs unchanged full560DRC/deep-flat500primitiveLVS/13faultchecker SHA3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66. Its inherited parent is used for unchanged schematic/LEF only; both independently compared against current41404030506 parent and match byte-for-byte. NewcandidateGDS alwaysused forphysical. Original43controls/contextguardcases unchanged. Follow exactjob; do not duplicate on observation timeout.

Mainchip41415994457/sourcef808321a65ca9197f10e75f2f59073d47095a718/release431237039 is the only new native47net route. Same64iterations/seed42/2threads/1691protectedclocks; explicit11GiB RSS within unchanged12GiB no-swap container and2GiB host reserve, both isolateddefault/global bound and unchanged-function checker validated by19newcontrols in independent41415631201. Previous41393730481 failed10GiBRSS after7021.574s; lastcompletediteration19internal92markers is partialnotfinalDRC. Currentroutehasnotyetprovidedcompletedphysical/timingacceptance.

Next: once newM2fullphysical reallypasses, derive new canonical per-partition M2/Via1/Via2 ownership from actual newGDS, newRC, unchangedloaded transient and actualbias/currentdistribution/PVT/EM. Ground bypass can change current and worsenheadroom; previousloaded41405079602 remainsREJECTED. No electrical improvement inferred. After mainchiprealreturnedroute, require originalglobalclasses,diodePG/connectivity/LVS and final3cornerSTA. Read-only8hourmonitor stays automatic_native_dispatch=false.

Observed at 2026-11-02T09:03:50.183260+00:00:
- 41415994457: in_progress/None
- 41417079679: completed/success

## Current continuation: bounded route retry and actual source-ground M2 bypass

Full serial PCIe Gen3x4 PHY, completed mainchip routing and final setup/hold remain OPEN. All native CAD/GDS/ODB/RC/waves remain GitHub-only. Local workspace empty. Prior verified rootv290=2aa3f2a110716dd059c9f60212e538fba4140a4a preserves mainchip41393730481 memory failure and Via1-only41412504017 zero-admission failure in full.

Mainchip route resource fix on codex/mainchip-route47-repair sourcef808321a65ca9197f10e75f2f59073d47095a718:
Original same64iteration/seed42/2thread route,47selectednets,1691protectedclocks,12GiB no-swap container and2GiB minimum available host memory retained. Only isolated supervisor RSS constant AND its supervised keyword default are changed10GiB->11GiB, leaving1GiB non-RSS cgroup reserve. Command evidence checker derived from authenticated14874bytes SHA059e3e4edde4a63997cc841728f02d5b6a2aaf77335cb7d1b8dba70ed7d2e321 by single reversible constant replacement; every function body AST-identical. DerivedSHA08b30b1fcb7319ca5a204bf94da2ce8a7f03ead5e17d310aa0baaf8fc17c9e84. No physical/electrical/time/output/PID/cleanup/identity threshold changes. Growth may still exceed available memory; no success guarantee.

Initial controls41415300286/source7cd3336db272810b86d756bf42e9ccd1d7ea9909 refused a stale nested workflow digest before native execution. Fix updated only nested full64/snapshot manifests and their transitive pins, not original control bodies. Independent same-source41415631201 PASSED original suites plus19new resource/exit-boundary/owned-keyword-default controls. Authenticatedartifact13127009267 includes route47-memory-controls/result.json. Production41415994457/release431237039 now owns this retry; follow this exact run, do not duplicate or infer success from control-only result. Full candidate output/original route-class restoration,PG/connectivity/LVS/final3cornerSTA still required.

PHY sourceM2 physical bypass experiment on codex/cdr-source-m2-bypass:
Input actual4ccf1212 GDS/current freshRC41404030506/actual32query41407813062. Prior Via1-only41412504017 tested existing overlaps but admittedZEROcuts at all28critical terminals. New geometry instead adds1400nmwideM2 columns from existing1500x4000nm sourceM1 patches to actual same-netM3 ground access17.6um below, a290nm landing to originalM2,24Via1+3Via2 per each of8sources. All216cuts190nm,480pitch,50nm bothmetal enclosure,240nm existing/newvia spacing. Require all13original native unions,actualavss ownership,240nm foreignM2 spacing,50nm foreignVia1/2 clearance,extent/grid,all8sourcearrays,exact serialized onlyM2/Via1/Via2 delta and reversal. No devices/parameters/originalmaterial removed. Original95geometry controls plus8newM2 guards.

First41416167847/sourcec59d1c25092d95e5ffab69be402b17a8ea7103a4 PASSED103controls and firstactual M2owned/foreigngeometry guards, then failed FileExistsError because partial progress reused an exclusive-write filename. Preserve failure, initial proposal and logs. Fix2671a5b64f65df0195b7a3e1e724735521609a5b uses unique per-source/per-cut progress files while retaining exclusive-write save and ALLgeometry guards unchanged. Retry41416430071/release431239884 follows this exact source. No generation or electrical acceptance assumed.

Ground bypass can change bias/current; previous small ground improvement slightly worsened HBT Vce. Require full560DRC,deep-flatLVS13,new canonical full partition proof,newRC,unchangedloaded phase/current/Vce/sampler gates,actualcurrentdistribution/PVT/EM and bias review. Priorloaded41405079602 remainsREJECTED despite physicallyclean block. No completeclosedloopPHY or finalmainchipSTA accepted.

Read-only8hour monitor stays automatic_native_dispatch=false. Each native job is explicitly dispatched only after checking source and terminal predecessor evidence.

Observed at 2026-11-02T08:56:22.982255+00:00:
- 41415300286: completed/failure
- 41415631201: completed/success
- 41415994457: in_progress/None
- 41416167847: completed/failure
- 41416430071: completed/success

## Current continuation: mainchip memory termination and Via1 coverage refusal

All native CAD/layout/model/waveform work remains GitHub-only. Local workspace verified empty. Full serial Gen3 x4 PHY, mainchip routing and final setup/hold remain OPEN.

Mainchip 41393730481/source 7cc6f94a7a685423533a25bc0d418e33764e8366 TERMINATED FAILURE. The actual 47-net route ran 7021.574 seconds then original RSS supervisor sent SIGTERM: measured 11218012 KiB exceeded 10485760 KiB (10 GiB); available host memory 4000064 KiB exceeded retained 2097152 KiB minimum. Container hard cap 12884901888 bytes (12 GiB), peak reached hard cap; memory.max events 6179 but all OOM counts zero. Prepare/freeze/reversal audits passed. Last completed router iteration19 reported 92 internal markers (28 MetalSpacing,64 Short); iteration20 reached 90 at90percent before termination. These are internal partial counts, NOT completed independent full DRC. No returned routed-fixed candidate, final route audit, restored full DRC/LVS or timing acceptance exists. Baseline independently measured140 remains historical, not a newly measured terminal result. Next repair: investigate snapshot-time memory peak and a bounded budget within unchanged12GiB container and2GiB host reserve; keep route64/seed42/2threads and all electrical/physical gates. Do not blindly rerun or claim snapshot as completed route.

Via1 generation41412504017/source0677daccbaca68d007e6b37c4509ef143fc43db2 TERMINATED FAILURE. Source-controls passed; native generation refused "at least four additional local same-net vias for each of eight actual MOS drains". Actual ownership assertion was NOT the failure. Existing overlap geometry did not yield all eight required drain coverages. No Via1 candidate accepted. Preserve failure and exact attempted script. Next inspect per-terminal coverage and existing same-net overlap capacity; implement a genuine metal-access repair if existing overlap is insufficient. Do not delete or lower coverage/spacing/ownership checks.

Earlier actual4ccf1212 GDS passed block560DRC/deep-flatLVS13 and canonical identity; freshRC41404030506 completed. Loaded41405079602 remains REJECTED: HBT minVce0.3362–0.3708V below0.4V, sampler max delays41.40625–55.15625ps above37.5ps. All32 actual resistor comparisons41407813062 show only0.6357ohm improvement in eight source-ground paths, other24unchanged. Full-wave41408975201 and geometry41408690630 completed successfully as diagnosis, not electrical acceptance. Next via/metal changes require fresh physical/canonical/RC/unchanged loaded gates.

Both terminal result artifacts, original failure messages, source job metadata and permanent release indexes are preserved with byte/digest validation. Native payloads remain exclusively in GitHub. Read-only8hour monitor remains automatic_native_dispatch=false.

Observed at 2026-11-02T08:41:28.983018+00:00:
- 41393730481: completed/failure
- 41412504017: completed/failure

## Current continuation: loaded source M1 candidate rejected; next larger ground-access repair under diagnosis

All native CAD/layout/model/waveform work remains GitHub-only. Local workspace empty. Full serial Gen3x4PHY, completed mainchip routing and final setup/hold remain OPEN.

Actual4ccf1212 sourceM1 GDS passed full physical41401709497, canonical41403441348 and freshRC41404030506. Loaded41405079602/source d1acc79777356767bdc61cffe96d7a8e7edc2409/release431163845 now FAILED electrical qualification after a real native transient: engine exit0,829.814seconds; full113475rows/1152columns retained with no decimation. Raw1045823299bytes SHA d1ef391296ccb274f54500bbd6c5bceec9172b13af89a637546b017217efd49b. Complete release index/parts and derived13123443651 (1368933bytes SHAdcf43aada2b7a63d9ce7b2374c6dd89cff7c5b1a65dd5b8368eb468c55f2161e) preserved. Native archive parts remain only in GitHub.

Actual new phase14.752861593mV<30mV; signedVI44.166729330uA<50uA. HBT61/62/115/116 minVce0.339030756/0.336205693/0.370825949/0.369569860V<0.4V. SamplerA/B/C/D max delays45.78125/41.40625/52.96875/55.15625ps>37.5ps. Wrong-signA/B/C/D0/0/15/48; below100mV129/128/128/128. Prior ground model41391065497 phase14.758390691mV/VI44.182149848uA, C delay53.28125ps and16wrong signs. Other effects are tiny and HBT minima slightly worsen. Do not accept this as electrical closure.

Qualified resistance41407813062/sourcefafb2d0be139a44b3c70b449dfc182c5b9f171b0 on codex/cdr-source-m1-resistance PASSED. All32same frozen full-network solves and reciprocity checks ran. All500composition primitive parameters/terminal anchors,1446terminals and114complete composed electrical partitions match. Unnamed extractor ordinals may change only with complete partition identity; all public names fixed. 26original network,7comparison and4whole-partition controls passed (original full-wave reader controls also retained). New source-to-ground resistances44.592789–45.035528ohm: each improved by ONLY0.6357ohm (~1.39–1.41percent); all24other query values unchanged. Derived13124003147=1501108bytes SHAeeaa76224b1aadb3ba6a9def4debfe6026ff4835154dd390fd9e088909472665. Unit-current sensitivity is not actual operating-current loss.

Preserve two diagnostic refusals:
41406550838/source19b28ebe5329b05e6948665aa3d3db7d60a79c18 stopped before acquisition because comparison negative test caught AssertionError while unchanged need()raises ValueError. Only expected exception fixed.
41406816137/sourcec141ddb5c9e0034890a5fd541a140c51ba240f24 passed controls and all32native network solves, then refused raw net-name equality ($700 became$699). Its complete pair outputs remain preserved. Final41407813062 authenticates prior actual compositionc863575e... from freshRC41389957475 and proves entire primitive/partition identity before comparisons, with rejection controls for actual connectivity, parameter and public-name changes. No numerical solver or electrical limit changed.

Current all-layer geometry survey41408690630/source41bc40b0bbfd5a4bda407b8c43b236247f2fb21d/release431188942 on codex/cdr-source-m1-ground-access PASSED. It uses current4ccf1212 GDS/current freshRC and the actual current32query sensitivity proof. All original85geometry controls,978port coordinates, both978anchor ownership sets,7MIM relocation witnesses,24530native/exported resistors and13native unions are retained. ground-access-corridors.json contains full source/shared avss endpoint corridors padded5um, all13layers' owned/foreign polygons and actual same-net M1/M2 and M2/M3 overlaps. No geometry changed; no via dimensions/enclosure/spacing/current-density approval claimed. Derived13124178828=447045bytes SHA36f8ec13b86715b0c7ae7ca6dda7b808e3f40de042e6fd975a9085d65346dc5b.

Full-wave diagnosis41408975201/sourcea36dd3a2613a365b608dc5d9b10c5a24b41d00ea on codex/cdr-source-m1-wave-diagnosis dispatched with every source file readback verified. It binds current failed41405079602 release/index/parts, authenticates whole native archive, reads all original raw rows and reproduces HBT/sampler scalar failures before reporting same-net terminal losses at actual HBT minima. All diagnosis bodies and frozen parser controls remain byte-identical to3007520; only branch/current input metadata changed. Follow this exact job; do not duplicate. Native data stays in GitHub.

Next engineering action: combine current geometry survey and actual operating voltage-loss diagnosis to select a larger source/shared-ground access repair. The4um local M1-only widening was insufficient; inspect remaining31.8888ohm source aggregate edges and shared accesses, potential same-net upper-metal/via connections and foreign geometry. Do not assign an aggregate resistor wholly to one metal layer or infer operating loss from unit-current rank. Any new via/metal design requires actual PDK spacing/enclosure/current-density checks, full560DRC/deep-flatLVS13, exact canonical identity, newRC and unchanged loaded gates. Consider circuit headroom/bias if operating losses show metal alone cannot resolve four HBT minima. Full closed-loop serialPHY and corners still required.

Mainchip41393730481/source7cc6f94a7a685423533a25bc0d418e33764e8366 remains the same owned47net reroute; original140DRC last terminal count. Originalglobalclasses,1691clocks, diodePG/connectivity/LVS and final3cornerSTA remain open. No observation-timeout restart.

Previous verified rootv288=cc9c5992735942cb9dc3f3210c899a8bae5a04f5. Inventory766. Read-only8hour monitor and automatic_native_dispatch=false preserved.

Observed at 2026-11-02T07:55:22.862502+00:00:
- 41405079602: completed/failure
- 41406550838: completed/failure
- 41406816137: completed/failure
- 41407813062: completed/success
- 41408690630: completed/success
- 41408975201: completed/success
- 41393730481: in_progress/None

## Current continuation: source M1 loaded source controls passed; actual production job identity verified

Current loaded41405079602/source d1acc79777356767bdc61cffe96d7a8e7edc2409 on codex/cdr-local-source-m1-loaded passed source controls: all29definitions,5executableblocks,9frozen files, complete unchanged prepare/measure bodies and negative previous-port-order/count fixtures. Authenticated control artifact13123375512 is1120bytes SHA8841f4c2bc9568e90d251f0a2cac1ecc1f7b17103f3418c9a20fbe5ab59780fe. Source controls explicitly report no native acquisition or transient; actual loaded execution remains a separate job.

GitHub reports the production job name loaded-wave, not native-loaded. Corrected that single monitor inventory entry using the actual current jobs response, preserving run/source/branch and inventory count761. No simulation or numerical source changed and no new workflow was dispatched for this metadata correction. Read-only8hour monitoring/automatic_native_dispatch=false unchanged.

Actual current GDS4ccf1212 passed physical41401709497, canonical41403441348 and freshRC41404030506. The complete new RC model1982076bytes SHAede72ee139584ccce88eec9f7a8b05c74ae1be6da49e32e1b16185b0846a66fc, composition and all11numerical receipts are preserved under current-terminal-41404030506/qualified in rootv287. All native material remains in cloud releases. Native loaded-wave measurements are not yet accepted; previous41391065497 remains rejected. Inspect current loaded41405079602, preserving full raw/failure release evidence and comparing unchanged HBT minVce, phase/signedVI and sampler margins/timing. Do not replace the model or relax gates.

Same mainchip41393730481/source7cc6f94a7a685423533a25bc0d418e33764e8366 remains the owned47net reroute; original140DRC is last terminal count. Original globalclasses,1691clocks, diodePG/connectivity/LVS and final3cornerSTA remain required. No duplicate on observation timeout.

Full serial Gen3x4PHY, completed mainchip routing and final setup/hold remain OPEN. Full previous continuation recipe is in v287. Previous all-file-readback-verified rootv287=cffeb34537dc7741c5efc45e60054e9f14f4b67f (32files/13501121bytes). Workspace empty; no local native payload.

Observed at 2026-11-02T07:19:58.243622+00:00:
- 41405079602: in_progress/None
- 41393730481: in_progress/None

## Current continuation: actual fresh RC qualified; frozen loaded transient dispatched

Native CAD/layout/model/waveform work remains GitHub-only; local workspace empty. Full serial Gen3 x4 PHY, completed mainchip routing and final setup/hold remain OPEN.

Actual eight-source M1 candidate4ccf1212d4b98046b1b56037bb1b76c53477777b08ee9cba5053c8e6323203e8 (1003860bytes) passed physical41401709497 (full560DRC zero markers, deep/flat500primitiveLVS,13faults) and canonical41403441348 (58controls, exact all13layer material identity and500device/1446terminal/25port/978anchor witnesses). Complete prior terminal evidence and generation refusals are preserved in rootv284/v285.

FreshRC41404030506/source9750f2c17a8cca7b5560a74097f04c04b769e5b1/release431157438 now PASSED actual new native extraction and all11original numerical receipts. Current census500devices/24530R/15676C. Model1982076bytes SHAede72ee139584ccce88eec9f7a8b05c74ae1be6da49e32e1b16185b0846a66fc; composition974729bytes SHAf2e6742baedc06eb6fc2beb17fc42553f0bef0b1c959289cdbbab7e5cf44d78d. Complete derived13122204344 is8350800bytes SHAc70fb2c804cff69265692e972fdd114e2a8a052cfab1bad7710b28b060ca41d7. Root preserves exact current/original qualification,11phase receipts and authenticated complete release index; all native output is permanently retained in GitHub. The previous28core/13current source controls are fully preserved in rootv286. None is electrical acceptance or qualifiedPEX.

Loaded41405079602/sourced1acc79777356767bdc61cffe96d7a8e7edc2409/release431163845/tagcloud-results-41405079602-1-cdr-wire-shortcuts-loaded is dispatched on codex/cdr-local-source-m1-loaded. Source published atomically and every file readback verified before dispatch; independent exact-source release reserved. Follow this same run. The current actual model, composition, whole native index, all11receipts, measured census and26node interface are bound before native execution.

New extractor ports19/20=yn/yp; actual25semantic names and identities unchanged. Loaded basis now uses measured order; negative fixture rejects previous yp/yn. Wrong-count fixture now increments measuredR, guaranteeing a real mismatch. Reversing only branch/producer/geometry/status/interface and these two metadata fixture changes reproduces previous host494a63a byte-for-byte. All29definitions,5executableblocks,9sourcefiles,13actual binding controls and complete prepare/measure methods from43fd3f71a289fef004aeb41cd2d0972d81f76f41 remain unchanged. Source-only qualification fixture retains native_executed=false/source_only_metadata_fixture=true; initial staging refusal on these additional existing fields happened before any mutation, and they were preserved explicitly.

Next: inspect loaded source controls and actual native preparation/transient/measurement. Preserve complete raw waves and failures in the release; download only authenticated derived text to local RAM. Compare actual HBT minVce, phase/signedVI, source ground rise and all sampler margin/timing results against rejected41391065497. No ideal-ground substitution, lighter load, altered waveform, threshold relaxation or old electrical success transferred. External8GHz nominal_late test remains distinct from closed-loop CDR/full serialPHY/corners.

Mainchip41393730481/source7cc6f94a7a685423533a25bc0d418e33764e8366 remains the single active47net reroute. Original140DRC remain last terminal measured count. Preserve original global classes/1691clocks, diodePG/connectivity/LVS and final3cornerSTA. No duplicate on timeout.

Previous fully verified rootv286=4f3099f7c8300b770e16874564c9b2b95fc3a67e (118files/20718849bytes). Inventory761; read-only8hour monitor and automatic_native_dispatch=false preserved.

Observed at 2026-11-02T07:17:00.933112+00:00:
- 41404030506: completed/success
- 41405079602: in_progress/None
- 41393730481: in_progress/None

## Current continuation: exact canonical qualification passed; actual fresh RC dispatched

All native CAD, layouts, extracted models and waveforms remain GitHub-only. Local workspace empty. Full serial Gen3 x4 PHY, mainchip routing and final setup/hold remain OPEN.

Candidate4ccf1212d4b98046b1b56037bb1b76c53477777b08ee9cba5053c8e6323203e8 (1003860bytes) passed physical41401709497: 560DRC categories with0markers, deep/flat500primitiveLVS and13faults. The full terminal evidence and generation refusals remain in rootv284/v285.

Canonical41403441348/source52b88fd735c40f3f40faced7e30051b788c9d01d/release431153587 now PASSED all58controls and actual native qualification. All13layers of all conductor partitions compared exactly; only avss M1 changed by48000000nm2 across8declared rectangles. All500devices,1446terminals,25ports,978anchors and hierarchy/transforms preserved. Canonical derived13122158804=1449837bytes SHA8b164ee8db89553b0727fa88f49b890d56876b91ee07428943b9720ede376d22; control13122002912=840bytes SHA67c0c42de571ccb600cb72fd3dd946705a51799d155293b94cb3d765ff21efba. Canonical archive700842961=3714835bytes SHAb39d2edf9c3dd5ebcc2ae7944199a34b86259a422581ad5501008e4dc391bf99; index700842958=22729bytes SHA293c76cb7eeeb43b8a8414f51c0744fc9a963f46ea045528e5a5208d7871e04d. Native archive remains cloud-only.

FreshRC41404030506/source9750f2c17a8cca7b5560a74097f04c04b769e5b1/release431157438/tagcloud-results-41404030506-1-cdr-wire-shortcuts-fresh-rc on codex/cdr-local-source-m1-fresh-rc was atomically published and every source file readback verified before dispatch. Source controls passed; actual wireRC/both preciseMIM orders/composition now running. Follow same run; do not duplicate on observation timeout. All original numerical methods,13command plan,11receipts,runtime658members and resource/lifecycle controls preserved.

The new canonical extractor assigned positions19/20 to yn/yp, whereas prior qualifiedRC basis had yp/yn. All25semantic names and complete native witnesses match; this is measured port ordering, not an electrical net swap. The staging publisher correctly refused a stale-order assertion before any mutation. Both current numerical config and exact host guard now bind actual order. Reversing only the reviewed branch/producer/geometry/status/order strings reproduces the original host byte-for-byte. No numerical method or threshold changed.

Next after complete actual freshRC success: acquire only authenticated derived text locally in RAM, read current q and original q, bind all11receipts and complete native index. Create codex/cdr-local-source-m1-loaded from494a63a4136813f6018c8cab027632ff02f54d0d with actual measured500device/R/C census, current model/composition pins and current26node interface. Update the negative old-port-order fixture to reject previous yp/yn and make wrong-count fixture increment measuredR; preserve all29definitions,5executableblocks,9sourcefiles,13bindingcontrols and exact complete prepare/measure bodies from43fd3f71a289fef004aeb41cd2d0972d81f76f41. No oldRC reused as new. Full loaded raw waves and failed outputs stay in GitHub. Previous41391065497 remains REJECTED for HBT minVce, phase/signedVI and sampler margin/timing; physical/RC success is not electrical acceptance.

Mainchip41393730481/source7cc6f94a7a685423533a25bc0d418e33764e8366 remains the single active47net reroute. Original140DRC are last measured count. Original globalclasses,1691clocks, diodePG/connectivity/LVS and3cornerSTA still required. Full PLL/CDR/SERDES/PCS integration is not complete.

Previous verified rootv285=38e0f0b34716369698c9ac68ad7d2d671e623b2f (187files/28743445bytes). Inventory760; read-only8hour monitor and automatic_native_dispatch=false preserved.

Observed at 2026-11-02T07:11:12.059993+00:00:
- 41403441348: completed/success
- 41404030506: in_progress/None
- 41393730481: in_progress/None

## Current continuation: source M1 physical qualification passed; exact native ownership running

All native CAD, layouts, extracted models and waveforms remain GitHub-only. The local workspace is empty. Full serial Gen3 x4 PHY, mainchip routing and final setup/hold remain OPEN.

Actual eight-source M1 candidate GDS is 1003860 bytes, SHA256 4ccf1212d4b98046b1b56037bb1b76c53477777b08ee9cba5053c8e6323203e8, generated by 41400908740/source880dce57683ccb79f38ea43f3014bb90151329e1. Only eight 1500nm by4000nm Metal1 rectangles (48um2 total) are added; no new devices or vias. Original source controls and all failed attempts are preserved in v284.

Physical41401709497/sourcea60c812f23d80ce7672a807f6392fa35cc440a32/release431142636 is now SUCCESS: 43controls; all560DRC categories with zero markers; deep/flat500primitiveLVS; 13expected fault rejections. The frozen checker SHA3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66 remains unchanged. Derived13121826335 is352456bytes SHAab2299c2bc5abf9e6436fa7f4e159b51717a52181bf8b0d49f53aaa873ca6360. Native archive700807528 is5988110bytes SHAe1f9f52b103f0cc7aba38af914c9c7aa36e2380c2f0157b0f0d80eb6e92a9e2d, retained only in GitHub.

Canonical41403441348/source52b88fd735c40f3f40faced7e30051b788c9d01d/release431153587 is independently reserved and dispatched on codex/cdr-local-source-m1-canonical. All published source files were read back byte-for-byte. It authenticates actual preceding b9b923 GDS/native graph from freshRC41389957475 and actual physical4ccf1212. It independently reconstructs eight new M1 rectangles from actual original source anchors and requires all13layers of every conductor partition to match exactly, with only avss M1 increasing by48000000nm2. All48original canonical controls remain, plus10new positive/adversarial source-M1 controls. Complete500device/1446terminal/25port/978anchor witnesses remain unchanged. Native results pending; no freshRC acceptance claimed.

Publisher staging initially refused because its AST unchanged-function list did not permit verify's intended status-string rename. Before publication, the actual verify function was inspected and an explicit AST assertion proved that the only change is the exact qualification status literal. No worker, resource, lifecycle, validation or stimulus changed for this correction. The inherited physical qualification label is not a geometry assertion: full16phase results and exact4ccf1212 digest are bound independently.

Next after canonical success: new native RC extraction and all original numerical checks; then unchanged full loaded transient. Previous loaded41391065497 remains REJECTED for HBT minVce, phase/signedVI and sampler margins/timing. No claim that physical M1 repair has yet improved those electrical measurements. Full serial PLL/CDR/SERDES/PCS and mainchip qualification remain required.

Follow the same mainchip41393730481/source7cc6f94a7a685423533a25bc0d418e33764e8366/release431098535. Actual47net reroute is still active; original140DRC remain last measured count. Do not duplicate it on observation timeout. Original global classes,1691clocks, diodePG/connectivity/LVS and3cornerSTA remain required.

Previous fully readback-verified rootv284=3c8f1dbc17cf0de0cd86af99ba2aec6ced16d163. Inventory759; read-only8hour monitor and automatic_native_dispatch=false preserved.

Observed at 2026-11-02T07:02:38.574099+00:00:
- 41401709497: completed/success
- 41403441348: completed/success
- 41393730481: in_progress/None

## Current continuation: eight-source M1 candidate generated; full native physical verification dispatched

All native CAD, model and waveform work remains GitHub-only. Full serial Gen3x4PHY, completed mainchip routing and final setup/hold remain OPEN. Local workspace is empty.

Actual generation41400908740/source880dce57683ccb79f38ea43f3014bb90151329e1/branchcodex/cdr-local-source-m1/release431137984 PASSED102controls and native8target admission. New candidate native/nssoc_cdr_pd500_local_source_m1.gds is1003860bytes SHA4ccf1212d4b98046b1b56037bb1b76c53477777b08ee9cba5053c8e6323203e8. Each source3,4,5,6,32,33,34,35 receives a4um-long,1.5um-left M1 reinforcement (6um2 per source; total48um2). Only layer8/0 is added; no device or via changes. Exact serialized full-layer delta and removal/roundtrip back to originalGDS passed. Derived13121530902 is249565bytes SHA30d79a9d8163b92c50f52add9220aff620f0f8ddf5ddb646cfa3cb929e03b87e. Electrical improvement is NOT measured and physical_acceptance remains false.

Full physical run41401158595/sourcee06a1fa008653e57f29a3ba4415711fd90c54498/branchcodex/cdr-local-source-m1-physical/release431139494 is independently reserved with tagcloud-results-41401158595-1-cdr-wire-shortcuts-physical. This first attempt failed before native geometry: inline policy admission still expected the previous horizontal-ground branch. Its complete job log and empty-output publication failure are preserved. Corrected run41401709497/sourcea60c812f23d80ce7672a807f6392fa35cc440a32/release431142636 on the same local-source-m1-physical branch changes only that expected branch literal and adds seven tests of the actual inline policy assertions. Follow41401709497, not the terminal41401158595; no duplicate. It authenticates complete generation archive and current candidate byte digest, then uses unchanged checker SHA3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66 for560DRC categories, deep/flat500primitiveLVS and13negative faults. Only candidate binding/proof/path changed relative to qualified physical sourcec40549f17f783ae3250139e63a9edee75721b219. Original schematic/LEF, all frozen checker/source/runtime/resource controls remain. Source was published atomically to a new branch with skip-ci, avoiding duplicate unrelated baseline RTL jobs while retaining explicitly dispatched physical source controls.

Three generation refusals are preserved in full derived metadata:
-41397981344/source6ef31b5bd00bd0eacc3e46983a13fe2b3e09ab4f:91controls passed; native original two-argument Region.sized(width/2,0) selected isotropic mode0 and grew Y. All8targets refused on span/left-only/spacing/shape guards; no GDS accepted.
-41399519731/source7694c28b3ab848acfa854b962f17a5bc1318b603:98controls passed including actual old-overload reproduction and all5width polygon comparisons. Explicit3argument horizontal sizing fixed Y. All8still refused because full36um source contour is not a constant290nm rectangle; added material reached65nm inside nominal left boundary and approached foreignM1.
-41399977249/sourcecac63a0e8834b3bb620a80e9c7d807c33745a084:102controls passed; none of20-36um source bands was an exact rectangle, so no width admitted. Do not infer nonrectangularity only at distant ends; the measured data only proves these tested full bands are nonrectangular. Actual map41397314520 shows4um local windows are exact290nm rectangles for all8sources. Adding16/12/8/4um search lengths admitted the4um candidate with ALL original605nm foreignM1,5nm foreignVia1, left-only, attachment, maximum-span and exact8target gates unchanged.

KLayout primary API documentation confirms sized(dx,dy,mode) differs from sized(d,mode): https://www.klayout.de/doc-qt5/code/class_Region.html . Current runtime0.30.4.post1 executed regression controls. IHP published M1 rules were researched (0.18um basic,0.22um qualified parallel run,0.6um wide-line case), but NO guard thresholds or fullDRC rules were changed. The generated candidate still passed the stricter605nm proposal guard.

Queue management: cancelled only old/initial-copy checks41397960768 and41396646262, then duplicated generic checks41397312674 on completed read-only diagnostic branch. The latter compare against06d603105065697e069dde1e6954a8605a535c5c proved exactly6changed diagnostic/doc/workflow files and no RTL changes; its actual native mapping41397314520 had passed. Current generation-head CI and all native jobs remained. Cancellation receipts, terminal run/jobs and pre-existing failed formal-and-boot logs are preserved under docs/evidence/cloud-ci-capacity-cleanup-20261102/. Those historical branches lack nettype directives in soc_pcie_gen12_raw32_align.v. Rootv283 already contains both directives; exact comparison proved those44bytes are the only difference. No new RTL patch or claim of full root lint pass was made.

Next: if corrected41401709497 passes full physical scope, bind actual current4ccf1212GDS to canonical native extraction (500devices,1446terminals,25ports,978anchors), prove only expected M1 delta against actual priorb9b923parent, then freshRC numerical validation and unchanged loaded waves. Use actual generator41400908740 and physical41401709497 release/indexes; do not reuse old RC as new. Existing electrical41391065497 remains REJECTED for fourHBTminVce, phase/signedVI and sampler margins/timing. Source-local M1 is only part of a32.5245ohm aggregate edge; improvement must be quantified, not assumed. Complete serial PLL/CDR/SERDES/PCS integration and full chip qualification remain required.

Mainchip41393730481/source7cc6f94a7a685423533a25bc0d418e33764e8366/release431098535 remains active. Source controls passed; actual47route/fullDRC/antenna results pending. Original140DRC are last terminal measured count. Preserve reversible class identity,1691clocks, originalglobalclass restoration, diodePG/fullconnectivity/LVS and final3cornerSTA. No duplicate or timeout-based restart.

Previous fully readback-verified rootv283=6de29461db911bec51ec4c4f7e7052d2b2acdf61. Inventory758, read-only8hour monitor, automatic_native_dispatch=false.

Observed at 2026-11-02T06:45:23.278169+00:00:
- 41397981344: completed/failure
- 41399519731: completed/failure
- 41399977249: completed/failure
- 41400908740: completed/success
- 41401158595: completed/failure
- 41401709497: in_progress/None
- 41393730481: in_progress/None

## Current continuation: native resistor physical mapping passed; measured local Metal1 candidate dispatched

All native work remains GitHub-only. Full serial Gen3x4PHY, final mainchip route and final setup/hold remain OPEN. Local workspace is empty.

Actual physical resistor mapping41397314520/source7b2a7efcedd829412cb18fd45d66179c071a3c79 PASSED. Derived13119862659 is406050bytes SHA52f13ce1c9b223d49367d75e928168e932f2eab61fb51992d847fc861f59a9f2. Full52critical-resistor coordinate/ownership map, all978port checks, all24530native/exportedR correspondence, all13native conductor union equalities and unchanged GDS proof are preserved under docs/evidence/current-terminal-41397314520/. This is diagnostic acceptance only.

Failed attempts41396652103/source02db0affab32b2f7d331c2e5f720ad38663d2c84 and41396958129/source9e2c0fa6b6b5df855d5d1d84293ac418ea3071d9 are preserved. The new reader initially selected pre-MIM anchors from binding/inputs/wire/anchors08.json. Its unchanged2nm coordinate gate correctly refused seven mismatches. Complete diagnostic proved971coordinates exact and seven MIM bottom reference differences (devices273-279). Correct actual references reside at mim/precise/wire/anchors08.json in the same authenticated freshRC archive. The seven documented bottom points are on actual Metal5 outside the intrinsic MIM mask; no RC or GDS was modified. Corrected reader requires exactly those documented seven changes, every other field equal, both original and extraction points on the same native-owned metal and all978extracted coordinates within original2nm/5nm-grid tolerance. All85original controls passed.

The dominant32.5245ohm source edges terminate on actual290nm-wide M1 strips. For example T003_S=[1884565,406030]nm and its opposite native resistor endpoint P_avss.n175=[1868095,388430]nm is on the actual M3/Via3/M4/Via4/M5 ground landing. T032_S=[1884565,1595550]nm has the symmetric structure. A resistor edge can aggregate multiple physical segments; this evidence does not assign its entire resistance to M1 or guarantee a repair effect.

Candidate generation41397981344/source6ef31b5bd00bd0eacc3e46983a13fe2b3e09ab4f/branchcodex/cdr-local-source-m1/release431121700 is dispatched with exact reserved tagcloud-results-41397981344-1-cdr-wire-tail-shortcuts. Follow this exact run. The native function generate_local_source_m1 in scripts/cloud_cdr_wire_tail_shortcuts.py proposes left-only M1 reinforcement of source3,4,5,6,32,33,34,35 within18um each side of the actual reference. It tries added widths1500,1200,900,600,300nm and requires all8targets to admit. Added material must be connected, inside originalbbox,605nm clear of foreignM1,5nm clear of foreignVia1 and avoid unclassified material. No device, via, contact, source stimulus or logical reference is changed. Original85controls plus6new positive/adversarial guard controls run before native execution. Candidate serialization must equal originalGDS plus precisely reported layer8/0 additions, and reversal must reproduce original material. Parent remains GDS1003348bytes SHAb9b92319590ecca1c9ce31dcf1cc31f4fdc1d468fc514585931671ed2f4fa492.

Next PHY action: inspect candidate local-source-m1-proposal.json and local-source-m1-generation-proof.json. If refused, diagnose exact foreign clearance or attachment evidence, never lower guards to force admission. If generated, run the original complete physical checker SHA3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66:560DRC categories, deep/flat500primitiveLVS and13faults. Reuse actual physical host at c40549f17f783ae3250139e63a9edee75721b219, update candidate source/release/index and proof selector to local-source-m1-generation-proof.json / native/nssoc_cdr_pd500_local_source_m1.gds, keep all frozen checker/source/runtime gates. New proof only layer8/0,8sources,no devices/no vias, mapped parentb9b923. Its original schematic/LEF remain frozen and byte-identical. Only after physical pass: canonical binding, freshRC and original loaded wave gates. Loaded41391065497 remains rejected for HBTminVce, phase/signedVI and sampler timings.

Mainchip41393730481/source7cc6f94a7a685423533a25bc0d418e33764e8366/release431098535 remains the exact native reroute job. Source controls passed; current native results pending. Preserve47scope identity/reversal,1691clocks, actualfullDRC/antenna, originalglobalclass restoration, diodePG/connectivity/LVS and final3cornerSTA. Original140DRC remain last measured count until new actual results prove otherwise. Do not duplicate or restart on observation timeout.

Previous fully verified rootv282=d927c2e5dca792040c63be0f33065caf244b74c7 (49files/18979465bytes). Inventory753; read-only8hour monitor and automatic_native_dispatch=false retained.

Observed at 2026-11-02T06:10:47.856857+00:00:
- 41396652103: completed/failure
- 41396958129: completed/failure
- 41397314520: completed/success
- 41397981344: queued/None
- 41393730481: in_progress/None

## Current continuation: actual resistance bottleneck measured; physical mapping dispatched

All native CAD, geometry, extracted models and waveforms remain GitHub-only. Local workspace is empty; local activity is source/API/text metadata coordination in RAM. Full serial Gen3 x4 PHY, final mainchip route and final setup/hold remain OPEN.

Actual selector resistance run 41395210468 / source 4a20c52579eddaa7f0a1f82f41cb6af8445b806c PASSED. Derived artifact13118444894 is1467909bytes SHA b3a4162dfd66ae6148a987f3d3ffb40d140d661fc35aa741ac9971be215dd7a6. All derived files, all32full pair solutions, controls and acquisition are preserved under docs/evidence/current-terminal-41395210468/. The original loaded electrical rejection is unchanged. Twenty-six network controls and original frozen wave-reader controls passed; actual500device cards and24530R/15676C were authenticated. Every full-network unit-current solve passed KCL, terminal balance, energy, reciprocity and passive maximum-principle checks. This passive R-only sensitivity calculation is not a transient or operating-power result.

The eight MOS source-to-public-avss paths measure45.22849-45.67123ohm. Each contains a terminal-local32.5245ohm branch accounting for71.2-71.9percent of its equivalent resistance. Actual resistor names: r24495(T003_S), r24476(T004_S), r24457(T005_S), r24438(T006_S), r22219(T032_S), r22200(T033_S), r22181(T034_S), r22162(T035_S). Shared4.88213ohm edges contribute about10.7percent. Selector emitter paths measure18.2452-20.4448ohm; collector paths13.1816-14.2848ohm. These findings identify local access as a stronger next target than another blind top-ground widening.

Native physical mapping run41396652103 / source02db0affab32b2f7d331c2e5f720ad38663d2c84 / branchcodex/cdr-critical-access / release431114381 is dispatched with independently reserved tagcloud-results-41396652103-1-cdr-wire-tail-shortcuts. Follow the exact live job; no duplicate. Source modifies scripts/cloud_cdr_wire_tail_shortcuts.py, adds scripts/cdr-critical-resistance-inputs.json and docs/cdr-critical-resistance-physical-map.md. Original85geometry controls and guard ASTs are unchanged. It binds the CURRENT freshRC41389957475/sourcefe2ccfc1529b0e7507a585d3d8078e9d60af368d and current1003348byte GDS SHA b9b92319590ecca1c9ce31dcf1cc31f4fdc1d468fc514585931671ed2f4fa492, not the old four-shortcut GDS. Full native archive61446034bytes SHAf79de017083fa7d867ffd15888242724487eab6f518a75e4bf0664fbcb8e5da9 stays in GitHub.

Mapping must validate all978port coordinates against GDS, all24530native/exported R values/endpoints/multiplicity, and all13conductor unions. It maps top3edges of each32query through the actual composition inverse and native component ownership, preserves rawrnode records and emits owned/foreign geometry at each endpoint. Do not interpret rnode type placeholder as a GDS layer. Read-only input and final GDS equality are required. No new geometry, RC, electrical acceptance, full PHY or timing acceptance is claimed.

Next: inspect actual critical-access-map.json once this job terminates. Select a real physical local connection repair only after its layer and native ownership are proven. Preserve devices and original schematic; require full560DRC/deep-flatLVS13, canonical binding, freshRC and unchanged loaded electrical gates on any revised candidate. Do not delete failed evidence or relax thresholds. Current loaded41391065497 still fails fourHBTminVce, phase/signedVI and sampler margins/delays.

Mainchip41393730481/source7cc6f94a7a685423533a25bc0d418e33764e8366/release431098535 remains the exact native job to follow. Source controls passed. Original140DRC remain the latest terminal measured count until its native outputs prove otherwise. ReversibleFIXED identity checks, preservation of1691clocks, actual47net reroute, fullDRC/antenna, originalglobalclass restoration, diodePG/connectivity/LVS and three-cornerSTA remain required. Do not restart the running job for an observation timeout.

Previous rootv281=28e298bcf0922c8fe17ffe2e2138b16ee7540515. Inventory now750; monitor remains read-only8hour with automatic_native_dispatch=false.

Observed at 2026-11-02T05:55:26.846178+00:00:
- 41395210468: completed/success
- 41396652103: in_progress/None
- 41393730481: in_progress/None

## Current continuation: full new-ground waveform diagnosis passed; repaired47native run active

All native payloads remain GitHub-only. Full serial Gen3x4PHY, completed mainchip route and final setup/hold remain OPEN.

Diagnosis41393728274/source3007520e9bbc6a4bfccb294cc6d8acee62bef30b PASSED on the complete actual rejected new-ground raw waveform. Authenticated derived13117589643 is121806bytes SHAecc1cf03991f96cfc127b3c2f7dc30a0f82a53a592a304e73b180be48f7c504e. All native archive members authenticated, all113475rows/1152columns parsed, all original HBT minima/sampler timing margins and wrong-sign counts reproduced. This is a diagnosis success, not electrical acceptance. Complete diagnosis and a compact same-net terminal-loss report are preserved under docs/evidence/current-terminal-41393728274/.

At the worst HBT61/62 instant, collector voltages are0.843651/0.842517V, emitter0.504539/0.506221V. Their same-net upstream HBT54/56 emitter terminals are0.882608/0.900478V. Corresponding MOS3-6 drains are0.458190-0.460962V and sources0.301482-0.303867V. For HBT115/116, collector0.874813/0.875292V and emitter0.503713/0.505443V; same-net HBT106/108 emitter terminals0.955791/0.900683V; MOS32-35 drains0.456755-0.459530V and sources0.306308-0.308648V. These are actual distinct distributed-net terminal voltages, not ideal node aliases. The ground rise decreased relative to previous0.324-0.331V observations but the four Vce minima worsened. Do not infer that another blind ground widening closes electrical timing.

Next PHY work: analyze the actual extracted resistance/current paths feeding these four selector nets before selecting further conductor or circuit changes. Current four shortcuts already connect T061_C-T056_E,T061_E-T005_D,T115_C-T108_E,T115_E-T034_D through M2/M3 with existingM1/Via1 access preserved; their same-net drops still remain. HBT106_E on the C collector net has the largest observed upstream difference, while its existing shortcut endpoint isHBT108_E. Evaluate the complete shared-net path and original access/via bottlenecks rather than assume a direct shortcut or wider top ground fixes all sampler/comparator delay. Any revised geometry must preserve real ownership, spacing/enclosure, devices, full560DRC/deep-flatLVS13, canonical binding, freshRC and unchanged loaded gates. Any circuit redesign must update its actual schematic/layout/LVS together. No ideal ground, lower gate, different stimulus or reused RC proof is allowed.

The actual source geometry helper is scripts/cloud_cdr_wire_tail_shortcuts.py at06d603105065697e069dde1e6954a8605a535c5c. Its acquire_current currently binds the old four-shortcut RC41352147913/GDS1c7d5617; a new candidate on ground GDSb9b923 must instead authenticate current freshRC41389957475/sourcefe2ccfc1529b0e7507a585d3d8078e9d60af368d and its full new canonical/native archive. Keep every prior failed geometry and electrical observation.

Mainchip repaired native41393730481/source7cc6f94a7a685423533a25bc0d418e33764e8366/release431098535 passed own source-controls and is observed active. Independent controls41393574410 passed all original checks and20new import-path regression controls. The earlier41391752608 failed before routing on the hosted-root path encoder, preserved with zero route/importcalls and noOOM. Follow the exact current job; no duplicate dispatch. Native identity/reversibleFIXED/47owner geometry/1691clocks/fullDRC/antenna results are still pending. Original140DRC remain the last measured count; original global-class restoration, diodePG/fullconnectivity/LVS and final three-cornerSTA remain mandatory.

Checkpointv280=8c0f0ccb3cfb4a04fe00a3af92ec3e0f55ccd505 was verified across131files/12036788bytes. Inventory748 and read-only8hour monitor remain; automatic_native_dispatch=false.

Observed at 2026-11-02T05:30:48.810766+00:00:
- 41393728274: completed/success
- 41393730481: in_progress/None

## Current continuation: loaded ground candidate rejected; native path bug repaired and new run launched

All native CAD, archives and full raw waves remain GitHub-only. Local workspace is empty. Full serial Gen3x4PHY, mainchip routing and final setup/hold remain OPEN.

Actual new-ground loaded41391065497/source494a63a4136813f6018c8cab027632ff02f54d0d/release431084851 is terminal FAILURE. The unchanged transient returned0 after1182.983702seconds and preserved all113475rows/1152columns,1045823299bytes SHA8e1246b7cb4d26f361538977af4507fad259c3e98eeb0f7f851157f5e295ec75. Electrical status REJECTED_WHOLE_MIM_PD500_LOADED: phase14.758390691mV versus30mV, signedVI44.182149848uA versus50uA, A/B/C/D maximum clock-to-valid45.78125/41.40625/53.28125/55.15625ps versus37.5ps; C/D wrong-sign samples16/48. HBT61/62/115/116 minimumVce0.339112537/0.336296287/0.371100560/0.369848838V versus0.4V. These four minima worsened from the previous four-shortcut candidate, while phase/VI improved modestly. No electrical acceptance follows from the passed macro physical and freshRC checks. Frozen stimuli/device limits/measurement bodies remain unchanged. Authenticated derived13117914409 is1372359bytes SHAdfba52f7ddf8c398da57a21bc7a5b5476ab761fc60bb36047ae1fe314c92116e; all original native parts remain release431084851.

New full-wave diagnosis41393728274/source3007520e9bbc6a4bfccb294cc6d8acee62bef30b uses the exact previous parser/diagnosis methods with only the producer configuration changed. It authenticates every complete native archive member, reads every original waveform sample, reproduces each failing-device scalar, measures connected native terminal voltage drops and groups sampler/comparator errors by bit transition. Follow its actual outcome before selecting another circuit/layout repair. It is diagnosis, not another transient or acceptance claim.

Mainchip41391752608/source4ac4c07b02172eb63b399648efc48279fa79dcb1/release431088470 failed in prepare BEFORE ANY class import or routing: frozen import_tcl called a hosted-root-only path encoder and rejected /work. Full native iteration20 roundtrip, original scoped delta and native report-name selection already passed. Routecalls0/importcalls0, elapsed444.352901seconds, peak6675869696bytes, allOOM counters0. Authenticated derived13118560094 is208526bytes SHAb7eaba5d8fa8213e769d589e3f29192bee2e7f672533effe5584ad57cc5a716c. Original140DRC remain; no route improvement is claimed. Complete235944940byte failure archive SHA6483d298b94861c7bb9ce7d7c47be234e491f8ecf85f9f3299c265813fc19567 remains cloud release431088470.

Source7cc6f94a7a685423533a25bc0d418e33764e8366 fixes only the owned-path import boundary. The original import function bytecode/defaults/closure is reused with an isolated namespace whose path encoder admits only canonical exact-owned paths and three declared stems. Original globals remain unchanged; both floorplan imports and all six Tcl commands remain exact. Additional20controls reproduce the actual historical rejection, cover each import sequence, and reject wrong-stage, foreign, injected and real symlink paths. All new and existing controls PASSED independent41393574410. Native41393730481/release431098535 is reserved at the exact source and dispatched using that control run. Follow the SAME handle; do not restart on observation timeout. All original native identity, reversible protection,47owner wire/guide checks,1691clocks, full DRC/antenna and resource controls remain.

After successful route observation, original global route-class restoration, diodePG/connectivity/fullLVS and final three-corner RC/STA remain mandatory. Frozen global restoration also needs authenticated original baseline/insertion snapshots, insertion plan and original classes; do not equate temporary47class restoration with original global restoration. Original producer41349316524 index contains all necessary inputs, including baseline-snapshot624649274bytes SHA93cd2b9336d37dab192cacb16781b6a85489c4b56b95ab978ff20686816c1138 and insertion-snapshot627376262bytes SHA501e93ae94d2a08477d59f14f8bee320412a0de83578ec1c6ad7a818878e772f. Keep these native structures cloud-only.

Checkpointv279 committed b768ae41969479809efed0d4012c3a4ee6427ce2 and all434files/96165608bytes were readback-verified. Its original coordinator attempt stopped before publication because the new8351097byte derivedRC package exceeded the metadata guard. Recovery admitted only the exact known artifactID/size/digest, preserving the native-payload exclusion and full readback checks. No native CAD ran locally.

Monitor remains read-only every8hours with automatic_native_dispatch=false.

Observed at 2026-11-02T05:25:08.405102+00:00:
- 41391065497: completed/failure
- 41391752608: completed/failure
- 41393574410: completed/success
- 41393730481: in_progress/None
- 41393728274: completed/success

## Current continuation: new ground RC passed; loaded waves and actual47net repair launched

All native CAD, archives and raw waves remain GitHub-only. Local workspace is empty. Full serial Gen3x4PHY, mainchip route and final setup/hold remain OPEN.

FreshRC41389957475/sourcefe2ccfc1529b0e7507a585d3d8078e9d60af368d/release431078750 PASSED actual numerical extraction for ground GDSb9b92319590ecca1c9ce31dcf1cc31f4fdc1d468fc514585931671ed2f4fa492. Authenticated derived artifact13117376512:8351097bytes SHA3942e7dac897fae1bcd9362024a6863031b37bee4c2da94d77f8e411a675126d. Actual model1982585bytes SHA0bfdbf74c8dd73b2234b771746785af57fade28f122af94b436096c27b2ff943; composition974729bytes SHAc863575e8fd2f6586d0436a8db2fc0c80061b3032c8f9633fc9d9777f18c1527. Counts500devices/24530R/15676C. Original full numerical qualification and all11receipts passed. FreshRC is not loaded electrical acceptance or foundry-qualifiedPEX.

Loaded run41391065497/source494a63a4136813f6018c8cab027632ff02f54d0d/release431084851 uses this actual new model. All original29loaded definitions/five executable blocks/nine source files, stimuli, complete prepare/measure bodies, actual semantic port order, raw-wave handling and device/electrical limits are unchanged. Same model census as previous candidate is measured, not assumed. Independently reserved release is bound to the exact source. Inspect live outcome before claiming improvement over failed41379770619. Full waves must remain in GitHub. The first coordinator preparation attempt failed before any branch mutation because the qualification fixture also has two explicit source-only metadata flags; the second preserved both flags and updated only q/oq inputs.

Mainchip source4ac4c07b02172eb63b399648efc48279fa79dcb1 on codex/mainchip-route47-repair passed independent controls41391622039, including20additional scope/identity/clock/PG/instance/terminal refusal controls and all existing controls. Actual native run41391752608/release431088470 was independently reserved and dispatched with control_run41391622039. Do not dispatch a duplicate while this handle is live.

The native flow repeats the complete original iteration20roundtrip/scope audit, resolves every literal source name in all140reports, and checks47ordinary selected ITerm-only nets. It constructs both metadata and encoded FIXED protection for all nonselected wires. Before deleting any selected route, the protection is reversed and the full native snapshot (including every original wire opcode/clock record) must exactly equal the input. Any failure stops before routing. Then only47wires are cleared, every guide is verified unchanged, and the same original64iteration engine/settings/layers/seed run on the authenticated seed. Per-iteration native snapshots and complete partial outputs are retained. This is a new scoped cycle, not internal-search-state continuation.

If routing returns, temporary47protection is reversed; every nonselected wire,1691clocks, complete native sections and wholeDEF are compared. Full original DRC/antenna checks then run read-only. A green observation job is not signoff: result reports actual remaining DRC/antenna, and original global route-class restoration, complete diodePG/connectivity/LVS and final three-cornerRC/STA remain required. All acceptance flags remain false. Original input iteration20 has140DRC until a newly measured result proves otherwise.

The owned native47pipeline uses the same frozen engine/container/runtime/resource limits;6floorplan_initialize imports across3class-import phases,7audit/preparation phases and one actual route invocation are explicitly counted. Original route budget14400seconds and all per-phase1200second/resource supervision are retained; hosted job budget360minutes. Preserve terminal refusals or checkpoints rather than treating elapsed observation as failure.

Prior ground generation/physical/canonical passes remain documented in v276-v278. Follow both exact live jobs, preserve results, then respond to measured electrical or route failures without weakening any gate. Monitor remains read-only every8hours with automatic_native_dispatch=false.

Observed runs at 2026-11-02T05:11:33.888930+00:00:
- 41389957475: completed/success
- 41391065497: in_progress/None
- 41391622039: completed/success
- 41391752608: in_progress/None

## Current continuation: ground physical and canonical PASSED; newly bound RC dispatched

All native CAD and archives remain GitHub-only. The local workspace is empty. Full serial Gen3x4PHY, mainchip routing and final setup/hold remain OPEN.

Actual all32ground branches at4.6um were generated in41388218990/source06d603105065697e069dde1e6954a8605a535c5c. GDS1003348bytes SHA b9b92319590ecca1c9ce31dcf1cc31f4fdc1d468fc514585931671ed2f4fa492 passed physical41388495424/sourcec40549f17f783ae3250139e63a9edee75721b219:560DRC categories/zero markers, deep-flat500primitive LVS,13expected fault rejections,16phases. This is a CDR macro result, not full-chip signoff.

Canonical41389419224/source944efffd8ed7c4c586f06d9a9028ee81f9d08420/release431075795 PASSED actual native execution. Authenticated derived artifact13117060205 is1449657bytes SHA9ef855ce02101fb12666265cfc4c48c027ee14cfeac86192222e59d7344bcb53. It preserves500devices,1446terminals,25ports,978anchors,238native nets,113wire components and114electrical nets. Exact comparison of every conductor partition on all13layers found only the declared avssTopMetal2addition:29916180000nm2. Native ground component14/canonical cluster24; all levels/ordinals/transforms remained equal. All78current-view files are bound. No bbox approximation of original nonrectangular polygons was used.

New actual RC job41389957475/sourcefe2ccfc1529b0e7507a585d3d8078e9d60af368d/release431078750 is independently reserved and dispatched. It binds the new78-file canonical view and observed semantic port order to unchanged full numerical methods,13command plan, both precise MIM orders and original runtime/lifecycle controls. Reused658-member runtime is not new RC evidence. Numerical definitions/validators and electrical limits were not relaxed. Exact current source-only control and native execution state are recorded below; poll the same run until terminal, never restart because observation time elapsed.

Observed unchanged semantic port order is avdd,avss,sub,ird,cn,cp,dn,dp,irb,ira,irc,ibda,ibdc,ibs0,irx,xn,xp,ibs1,iry,yp,yn,irvx,irvy,vin,vip. Do not infer it from historical numeric native port IDs. The new canonical qualification is separately pinned by whole artifact digest and exact member bytes in the RC source; no claim is made that the generated proof existed in its producer Git tree.

If freshRC passes, bind its actual composition/model/native outputs into the unchanged loaded-wave checker. Electrical reference remains the failed four-shortcut loaded41379770619 (ground rise0.324-0.331V and minimumHBT Vce0.3490/0.3463/0.3813/0.3801V below0.4V). Do not transfer its electrical result or its RC model to the new GDS. The new geometry must meet all original scalar/wave and device limits without altered stimuli or idealized ground.

Mainchip remains at qualified iteration20reload41385939588 with140reported DRC. Selection41388383192 verified47authorized nets touch all140records;7records also touch protected clocks and127touch68outside-scope names. Native identity of every report name and reversible FIXED protection for all nonselected wires remain prerequisites to actual47-net routing. Both encoded route classes and net metadata require verification. All1691clock records, native material/terminals, original class restoration, diodePG, complete DRC/antenna/LVS and final three-corner STA remain required.

Prior width10um/5um refusals, missing reservation41387369679, successful real spacing diagnosis41387922295 and all source controls are preserved. New4.6um geometry leaves2100nm in measured constrained corridors; original2005nm/5005nm predicates are unchanged. Monitor stays read-only every8hours with automatic_native_dispatch=false.

Observed runs at 2026-11-02T04:43:58.488950+00:00:
- 41389419224: completed/success
- 41389957475: in_progress/None

## Current continuation: ground candidate passed full physical verification

Native work remains GitHub-only and the local workspace is empty. Full serial Gen3x4PHY, mainchip routing and final setup/hold remain OPEN.

Physical run41388495424/sourcec40549f17f783ae3250139e63a9edee75721b219/release431070997 PASSED on actual all32ground-branch GDS b9b92319590ecca1c9ce31dcf1cc31f4fdc1d468fc514585931671ed2f4fa492 (1003348bytes). Authenticated derived artifact13116248869 is353420bytes SHA6749dd76a05bbf6da3bd27e05b7039f2800b5947f0986d53936b62713cb7e486. Actual result:560DRC categories, zero markers, deep and flat transistor LVS each500primitives (124npn13g2/50sg13_lv_nmos/98rppd/7cap_cmim/221ptap1), all13fault injections rejected as expected, all16phases completed. Full physical checker remains frozen SHA3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66. This is a CDR macro result, not full-chip LVS or fullPHY signoff. New RC and electrical acceptance are explicitly false.

Canonical run41389419224/source944efffd8ed7c4c586f06d9a9028ee81f9d08420/release431075795 is the next exact-source independently reserved native job. It authenticates this physically passed candidate and current four-path reference GDS1c7d56173b350c067df5db468b4099d7c5b8681e891d027b700737566c2c3b94 from freshRC41352147913/source6eace90ce68a61546f0268b3fd65b2b9b2b3840d/release430869108. It reconstructs every declared700nm positional widening from the actual original polygon (never bbox-only), verifies all13layers/all conductor partitions and requires exactly one changed avss/TopMetal2partition. Existing native identity/planes/recovered-pin checks and frozen methods remain. Inspect authoritative live state before assuming completion. If it passes, adapt freshRC to the new canonical output, then run the unchanged loaded-wave gates; do not reuse old RC as new geometry evidence.

Actual spacing diagnosis41387922295 proved failed5um proposals narrowed real gaps to1900nm. Geometry was redesigned to4600nm, leaving2100nm in the constrained6000nm-pitch corridors; no spacing threshold was relaxed. All85generation controls and all32branches passed41388218990. Prior failed candidates and the initial missing-reservation failure41387369679 remain permanently preserved in v275/v276.

Mainchip47-net selection41388383192 remains a verified plan only: all140report20violations touch47of828authorized signal nets;7also touch protected clocks,127touch68outside-scope names. All literal escaped names are preserved. Before actual rerouting, independently resolve every source name in native iteration20ODB, build and audit reversible FIXED protection for all nonselected wires, and preserve every original clock and material. The original frozen native helpers fixed_plan/metadata_only/import_tcl/fixed-audit show the required distinction between metadata and encoded path classes; changing metadata alone does not establish fixed geometry. All1691clocks must remain unchanged. Current iteration20 native reload/scope proof passed41385939588, but routing, original class restoration, diodePG, DRC/antenna, LVS and three-corner STA remain open.

Next actions: follow canonical41389419224 without observation-timeout restarts; preserve any terminal failure before redesign. After success, perform newly bound RC extraction and real loaded-wave checks. In parallel task planning, implement the47-net native identity/freeze/clear/route pipeline using actual qualified iteration20geometry, preserving original failure checkpoints and all final acceptance constraints. No full serialPHY or timing acceptance is claimed.

Monitor remains read-only every8hours; automatic_native_dispatch=false.

Observed runs at 2026-11-02T04:38:20.874842+00:00:
- 41388495424: completed/success
- 41389419224: in_progress/None

## Current continuation: all32ground branches generated; full physical verification running

Native CAD, archives and waveforms remain GitHub-only. The local workspace is empty. Full serial Gen3x4PHY, completed mainchip routing and final setup/hold remain OPEN.

Run41387922295/source88babaeadcbf90ec8aff7d4fc7885a106c653a1e/release431068062 completed the real native original-versus-added clearance diagnosis. All32original branches have zero overlap at1999/2000/2005nm. Fourteen failed5um variants create actual spacing loss: at6000nm line pitch, the original2800nm gap becomes1900nm after900nm symmetric addition. This disproves the unchanged-baseline false-positive hypothesis. Do not relax the2005nm/5005nm spacing predicates.

Run41388218990/source06d603105065697e069dde1e6954a8605a535c5c/release431069611 PASSED actual generation of all32branches at4600nm width,700nm symmetric addition (2100nm gap in measured constrained corridors), preserving the exact original spacing guards. It passed85source controls. Actual GDS1003348bytes SHA b9b92319590ecca1c9ce31dcf1cc31f4fdc1d468fc514585931671ed2f4fa492 adds only TopMetal2 and preserves all original material, devices, vias and public pad. Generation alone is not physical or electrical acceptance. Original physically qualified reference GDS1c7d56173b350c067df5db468b4099d7c5b8681e891d027b700737566c2c3b94 remains the last qualified reference until the new candidate passes every downstream gate.

Physical qualification41388495424/sourcec40549f17f783ae3250139e63a9edee75721b219/release431070997 executes the unchanged checker SHA3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66:560DRC categories, deep/flat500primitive LVS,13faults and all16phases. Inspect live outcome; never infer success from source controls or generation. Original schematic9f70d7af1f26aa07029c8b473e7596f27cd6a50e1dacae4ea16bfd4559fc9f13 and LEF1f595545113979fdeda5f663c3c03398e8dce75c3821c6c8d4c6b686f9673896 were independently matched to current freshRC source6eace manifest. Newly extracted RC and unchanged loaded electrical gates are still required after physical qualification.

Earlier diagnosis41387369679 failed before acquisition because its independently reserved release was not created within the wait period. Its85controls passed; it produced no actual geometry diagnosis. Preserve the failure and use41387922295, whose release was independently created and bound before native work, for actual measurements. Do not rerun a terminated job as attempt2 because first-attempt guards require a fresh dispatch. Always reserve the exact-source tag/release immediately after dispatch identification.

Mainchip literal report selection41388383192/source802088c5e961d43af4b3cb83db0e9da50ad22a8d PASSED11source controls and authenticated both original derived artifacts. All140iteration20violations touch47members of the original828-net routing scope:7records also touch protected clocks,127touch68outside-scope names,6involve only owned nets. Escaped names were preserved exactly. No clock is selected. Native ODB identity of all report sources and reversible FIXED protection for all nonselected wires must be verified before rerouting47signals. Selection is not routing repair. Snapshot20 full load/write/reload and original-scope preservation already passed41385939588 with154480instances143820nets1691protected clocks. Current route remains140reported violations; final timing is not accepted.

Next: follow the active exact physical run without restarting on elapsed observation; preserve terminal reports. If it passes, rebuild canonical connectivity/material ownership relative to current four-path GDS and then extract freshRC and run the unchanged loaded-wave checker. New ground canonical declarations must reconstruct each original owned branch plus its selected700nm positional addition, not approximate nonrectangular polygons by bounding boxes. Prove exact all13layer conductor partitions. Keep500devices/25ports/all canonical terminals and all original fault controls. For mainchip, implement native47-net identity and reversible protection, then actual bounded routing repair retaining all1691clocks and full final DRC/antenna/LVS/STA gates. No shortcut in these requirements.

Monitor remains read-only every8hours; automatic_native_dispatch=false.

Observed runs at 2026-11-02T04:30:57.119626+00:00:
- 41387369679: completed/failure
- 41387922295: completed/failure
- 41388218990: completed/success
- 41388383192: completed/success
- 41388495424: in_progress/None

## Current continuation: route iteration20 verified; ground clearance diagnosis

All native CAD remains GitHub-only. Full serial Gen3x4 PHY, complete mainchip routing and final setup/hold are OPEN.

Actual original router reports authenticated in run41385020793: iterations5/10/15/20/25 contain561/267/159/140/298 violations. Iteration20 has89shorts and51metal-spacing violations; it is the lowest of the five retained reports, not proof of a completed route. Run41385939588 independently loaded, wrote and reloaded iteration20 and verified preservation of154480instances,143820nets,1691protected clocks and original828-net allowed changes, with zero absent owned wires. It did not run routing repair, restore original signal classes, verify diodePG, close timing or accept physical signoff. The original iteration25 verification remains valid, but iteration20 is the preferred qualified next repair input.

Ground reinforcement runs are preserved, including failures:41385188402 source-controls caught an ambiguous KLayout sizing overload; explicit three-argument sizing fixed it.41385545130 rejected all32ten-micron candidates;41386007875 admitted5of32centered five-micron candidates;41386421055 admitted18of32using centered/upper/lower added-only positions with identical guards. No candidate GDS was generated. Do not claim18of32as a passing repair. The remaining14need actual layout redesign.

Current diagnosis41387369679/source88babaeadcbf90ec8aff7d4fc7885a106c653a1e reports whole/original/added-only clearances using actual native geometry. It preserves every existing guard and reports exact overlap areas and foreign bboxes at1999/2000/2005/5000/5005nm. Three independent geometry controls distinguish an unchanged exact2000nm baseline gap from new spacing loss. Inspect the live outcome before further width proposals. No weaker acceptance or synthetic input substitution is authorized.

Snapshot20 first attempt41385528741 failed source authentication because a newly pinned document was missing from explicit sparse-checkout lists. Fixed source6ea1056a421a5ba7ebe6bba23d549d552d3e18bf passed standalone controls41385666865 and native41385939588. These failures remain recorded.

Electrical reference is still loaded41379770619: local ground rise0.324-0.331V, phase13.5867mV<30mV and HBT minimumVce0.3490/0.3463/0.3813/0.3801V<0.4V. Current accepted physical geometry remains four-shortcut GDS1c7d56173b350c067df5db468b4099d7c5b8681e891d027b700737566c2c3b94; no later failed proposal replaces it. Any new actual GDS needs full560DRC, deep/flatLVS13, exact canonical binding, fresh RC and unchanged loaded-wave acceptance.

Next: inspect actual baseline-vs-added ground collisions; redesign only from native evidence. For mainchip, classify140report20violations against native net identity and original scoped owners, then implement a bounded actual repair with protected-clock/material checks. Loading an ODB does not restore the internal detailed-router search state. Keep full original three-corner timing constraints and all physical acceptance gates. Monitor remains read-only every8hours; automatic_native_dispatch=false.

Observed runs at 2026-11-02T04:16:38.712752+00:00:
- 41385020793: completed/success
- 41385188402: completed/failure
- 41385545130: completed/failure
- 41385528741: completed/failure
- 41385666865: completed/success
- 41385939588: completed/success
- 41386007875: completed/failure
- 41386421055: completed/failure
- 41387369679: in_progress/None

## Latest continuation: ground-access evidence and refused M5-spine candidate

Native work remains GitHub-only; local workspace is empty.

Current avss access run41383160648/source97af42119c0c0dfadfc6bf2a288271a22e1ff541/release431041644 PASSED actual read-only GDS/L2N inspection. Eight measured tail MOS source terminals T003/004/005/006/032/033/034/035_S all belong to canonical avss cluster24, extracted component14. The original conservative local M2 and M3 access guards admit none. There are101actual avss anchors. Sixteen canonical internal avss anchors lie on Metal5(layer67) at x994600nm; P_avss is on TopMetal2(layer134) at[1200,112000]. Metal5 is NOT TopMetal1(layer126).

Physical candidate generation41383764902/source73af4aa6900a5b16a21a522c6cc48732b754344e/release431045009 passed68source controls but FAILED before generating GDS: no continuous owned Metal5 strip spans all16canonical anchor heights. The one6000nm-wide vertical-spine proposal was refused by its ownership/continuity predicate. This is a disproven geometry assumption, not a completed power repair or DRC result. Preserve failure.json and ground-spine-proposal.json. Do not drop the predicate to force acceptance.

Follow-up41384121103/source50b25269bca8a20bb5bacabbbdcf04f99d2f47c2/release431046973 is the actual13-layer ground topology inspection. See exact observation rows below/checkpoint for terminal or active status. It reads the same current GDS1c7d56173b350c067df5db468b4099d7c5b8681e891d027b700737566c2c3b94 and wire L2Nd53282a6bbb79f5410dd55c42e13dcfc42e0840b0c014a684e2076420ba0c6d9. It reports original owned conductor bounds/areas and canonical anchor neighborhoods without geometry mutation. Use this result to locate the true inter-stage ground path before redesigning reinforcement.

Electrical reference remains actual failed loaded41379770619 and full-wave diagnosis41382407375: local tail-source ground rises0.324-0.331V, phase13.5867mV<30mV, four HBT minimumVce below.4V. No new layout has replaced the already physically validated four-shortcut GDS. Any new candidate must independently pass full560DRC, deep/flatLVS13, canonical binding, newly extracted RC and unchanged actual loaded gates.

Mainchip snapshot41381113212 passed full load/write/reload and original828-net scope preservation; routing, class restoration, diodePG, DRC/antenna and original three-corner RC/STA remain open. Snapshot iteration25 still has298reported routing violations. The exact retained per-iteration DRC reports exist only in the cloud native archive of41349316524: work/bulk-postdrt-antenna/fixed-routing.drc-{5,10,15,20,25}.rpt. Its derived ZIP omits them. Next diagnosis should authenticate the native archive on GitHub and classify these reports; never download that native archive locally. Pinned OpenROAD detailed_route includes initialization/track assignment; single_step_dr alone does not prove exact saved-search-state continuation.

Rootv273 already permanently preserves complete snapshot success, current electrical rejection and full-wave diagnosis. Full serial Gen3x4 PHY, mainchip route, final setup/hold and production approval remain OPEN. Monitor is read-only every8hours and automatic_native_dispatch=false.

Observed runs at 2026-11-02T03:40:12.578361+00:00:
- 41383160648: completed/success
- 41383764902: completed/failure
- 41384121103: completed/success

Current native topology completed; exact derived report retained.

## Latest continuation: actual snapshot reload passed; actual PHY wave rejected

All native work remains GitHub-only. No local native input, waveform, GDS, ODB, tool cache or project files are retained.

**Mainchip:** native run41381113212/source968ca55acade41e869ae66bb2280c799bd7e41e3/release431030641 passed the actual last partial-ODB load/write/reload and full original scoped-delta audit. Candidate and rewritten ODB are byte-identical:214432143bytes/bde736aeacee0fd7a476d5375ae9c30a7199c630fdae190934145dcc4d43e977. The full native snapshot covers154480instances,143820nets,1691protected clock records. Exactly828owned signal nets changed from the original cleared snapshot; no owned net remains without a wire; all nonowned structure/wiring remains exact. Independent52source controls passed in41380942856. This proves safe preservation of the partial database, NOT router-state resume equivalence or completed routing. Original26snapshots and elapsed-limit failure41349316524 remain preserved. Latest route iteration25 had298router violations; these are not setup/hold counts.

**Current PHY electrical rejection:** run41379770619/source16c1b1d7d5ab2cf88a884c9dd255da359eff6d2c completed the actual current24530R/15676C loaded transient with unchanged sources and simulator return0. All113475rows/1152columns were read. Data, phase and device predicates failed. Phase13.586716731mV<30mV; signed VI41.460608381uA<50uA. Four transistor minimumVce values:61=.349021977V,62=.346337364V,115=.381265704V,116=.380062961V against.4V. SamplerC22andD50wrong-sign samples remain. Do not confuse this electrical failure with initial descriptor-only failure41379434066.

**Current full-wave diagnosis:** run41382407375/source9154c6b9c4358b8e233df6b79a4ccb1365ebced3 passed the unchanged frozen reader and8refusal cases, authenticated all131native archive members, parsed the entire existing waveform and independently reproduced original scalar measurements. Failed-wave SHA5d4dd06eb3590e860d0528f30e548f8b436d41a90084de9719fb4f91cf6e42bd. At transistor61/62 minimumVce, connected tail MOS source avss is.32396-.32715V while substrate is.001061V. At115/116 minima, tail sources are.32782-.33095V, substrate.001063V. Related load-resistor avss is.27639/.28131V. These current-wave measurements justify investigating actual supply/ground routing, but do not by themselves prove a specific repair will pass. Current shortcuts leave emitter-net drops around42-46mV and collector paths24-78mV. Preserve all models and gates; use real native ownership for any metal reinforcement, then full DRC/LVS, canonical binding, new RC and loaded waves.

**Next mainchip action:** inspect pinned router source before choosing a snapshot continuation strategy. Pinned upstreamdcf36133a369abc8f3c5e5738cd4d82e4903c0e0 contains single_step_dr/step_dr; main detailed_route still performs initGuide/prep/track-assignment before routing. Therefore loading a passed snapshot does not alone prove continuation from iteration26. No new route has been dispatched in this checkpoint. Preserve exact scope, original wire classes, diodePG, matching netlist, full DRC/antenna and original3corner RC/STA acceptance requirements.

All four runs above are terminal. Full serial Gen3x4 PHY, mainchip route, final setup/hold and production approval remain open. Monitor remains read-only every8hours; automatic_native_dispatch=false.

## Latest continuation: corrected current RC loaded job active

Execution is GitHub-only. Local workspace remains empty; no native geometry/archive/wave payload is acquired locally.

Original freshRC41352147913/source6eace90ce68a61546f0268b3fd65b2b9b2b3840d/release430869108 passed the complete numerical pipeline on actual1c7d5617 GDS:500 devices,24530R,15676C,14 successful commands and11 receipts. Root checkpoint271 retains exact qualification and all failed mainchip snapshot metadata.

Initial loaded run41379434066/source754c3b690f95e7d835c20e322ceb7a4c6d5b2e86/release431020109 passed source controls but failed before RC asset download and before simulation: KeyError(name) in the frozen download_asset helper. This was a descriptor-schema defect, not a new electrical result. All actual failure/source-control/publication evidence remains preserved. Corrected source16c1b1d7d5ab2cf88a884c9dd255da359eff6d2c retains exactly the same source asset IDs/sizes/SHA256, adds the required explicit name, and adds missing-name/mismatched-name refusal controls.

Corrected loaded run41379770619/source16c1b1d7d5ab2cf88a884c9dd255da359eff6d2c/branchcodex/cdr-wire-tail-loaded/release431021893 is the sole continuation handle. Its source controls passed. It authenticates the complete current3236-member RC archive, uses actual semantic irx,xn,xp order and the original frozen simulator/model library. All nine numerical source files,29 definitions,five executable blocks,13 actual binding refusals/two equivalent-unit checks and nominal_late electrical/device/solver predicates remain unchanged. An additional stale-selector-order refusal is present. Do not claim wave acceptance until actual complete measurements pass. If failed, inspect and retain the new model's real waveforms; never reuse old model waves or relax thresholds.

Mainchip41349316524 remains a recorded elapsed_limit failure with26 actual hashed drt_iter0..25 ODB snapshots and no final route. No new mainchip native job has been started. Next: authenticate the complete738-member, four-part failed native release on GitHub, restore the original pinned engine/runtime via the existing frozen-prefix pipeline and qualify snapshot load/write/reload. The existing native.snapshot helper in scripts/mainchip_bulk_postdrt_antenna_native.py records every143820 net, instance/terminal/master/row, immutable material, protected clock DEF record and exact wire encoding; it can compare a before/after roundtrip. Its1691 protected-net assumption must be checked against the actual saved classification/protected scope; do not change the requirement merely to make a snapshot pass. Preserve its full returned snapshots and any mismatch. Then separately restore/check original classes,828-net routing scope, all nets/clocks,2702 diode PG contacts, DRC/antenna, matching154480-instance netlist and original three-corner RC/STA. Restarting a snapshot is not yet qualified and cannot be claimed equivalent to resuming router internal search state.

Full serial PHY, final chip physical/timing acceptance and production approval remain open. Monitor remains read-only every8hours; automatic native dispatch is false.

## Latest terminal evidence: current RC passed, mainchip route reached time limit

All work remains cloud-only; local source/API/derived-text coordination is RAM-only. No native archive is acquired locally.

Fresh RC41352147913/source6eace90ce68a61546f0268b3fd65b2b9b2b3840d/release430869108 completed successfully. Its original full numerical qualification contains500 devices,24530 distributed resistors and15676 capacitors,11 phase receipts and14 successful actual native commands. Candidate GDS1c7d56173b350c067df5db468b4099d7c5b8681e891d027b700737566c2c3b94 binds canonical41350835442 and actual25 semantic ports including irx,xn,xp. Model1981992bytes SHA256a4eb11d906874e61b77929a2acb20837b26e06d58ae3d6e274d0fa59d7354d37. This is fresh extraction, not loaded electrical acceptance or foundry-qualified PEX. Next: run original nominal_late loaded whole-MIM/device predicates, retaining all previous rejected waves, then expand electrical coverage only as actual results justify.

Mainchip41349316524/sourcea47bb1895ad12fdebddeb055dc5e3e9c414c04e0/release430851918 terminated with elapsed_limit at14400.702739005seconds and returncode-15/SIGTERM. Last sampled groupRSS8307808KiB and available6978188KiB did not hit the10485760/2097152KiB thresholds; cgroup OOM/kill counters were zero. Iteration25 completed with298 routing violations; iteration26 was halfway with294 when stopped. This is not a setup/hold count or a final DRC pass.

The exact stage proof contains26 actual drt_iter0.odb through drt_iter25.odb files, each hashed. No final route checkpoint exists, route_returned:false, snapshot_reload_qualified:false. The26 files are retained in the four-part native release and fallback artifact; their ability to reopen and preserve scope/nets/clocks/diode PG is unproven. Next: cloud-only authenticated snapshot reload and geometry/connectivity audit, then qualify routing continuation without treating a partial snapshot as success. Do not repeat the same complete-start route merely for an observation timeout.

Both above jobs are terminal, and neither should remain labeled active. Full serial PHY, mainchip physical acceptance and final three-corner setup/hold remain open.

## Latest cloud continuation: fresh RC launched

The actual four-path canonical graph passed in run41350835442/source360a01ea394943614b25895e6389221f2b0ca0ba/release430861219. The complete derived proof is retained at docs/evidence/mixed-canonical-terminal-41350835442 and root commit e81440f25b73d0a86e85ea80acbcd8e8971f19a5. It preserves500 primitives,1446 terminals,25 ports and978 anchors across the exact declared Metal2/Via2/Metal3 additions and all13 layers. Physical DRC/LVS/fault qualification passed separately in41349608125.

Fresh RC run41352147913/source6eace90ce68a61546f0268b3fd65b2b9b2b3840d/branchcodex/cdr-wire-tail-fresh-rc/release430869108 has been dispatched once. Canonical133-member archive,78-file current view and actual semantic pin order irx,xn,xp are bound. Original658-member runtime cache, numerical algorithms, corruption controls, command arguments and resource limits are retained;19 unchanged host function ASTs were compared. Six edited source/config/document files were read back exactly. Observe the existing handle, never duplicate merely because observation timed out. After successful fresh RC, bind and run the original loaded whole-MIM transient/device predicates on the current model. A fresh extraction is not an electrical or full-PHY acceptance.

Mainchip full64 snapshot route41349316524/sourcea47bb1895ad12fdebddeb055dc5e3e9c414c04e0/release430851918 remains the existing handle. After its actual terminal outcome, authenticate native snapshots/final output, qualify reload, classes, original scope/nets/clocks and diode PG, run DRC/antenna with the matching154480-instance netlist and fresh RC/original three-corner setup/hold. No route/timing pass is inferred from an active job.

All CAD and native archives remain on GitHub. Local workspace and project temp areas are empty and no local CAD is running. API/source/derived-text coordination is RAM-only. Full serial Gen3x4 PHY, final chip timing and production approval remain open. Eight-hour monitoring is read-only; automatic native dispatch remains false.

## Latest result: current four-path native geometry binding passed

Execution remains cloud-only: native GDS/ODB/L2N/SPICE/raw data and CAD execution stay on GitHub. The local task workspace and project temporary entries are empty; only source/API/derived-text coordination occurs in RAM.

Canonical run41350835442/source360a01ea394943614b25895e6389221f2b0ca0ba/release430861219 passed on the actual four-path GDS1c7d56173b350c067df5db468b4099d7c5b8681e891d027b700737566c2c3b94. All500 primitives,1446 terminals,25 public ports,978 anchors and all13-layer owner partitions passed the frozen identity checks. Current canonical view has78 files; the complete native archive has133 authenticated members. Original geometry is retained and the four declared Metal2/Via2/Metal3 additions are verified. Physical run41349608125 already passed560DRC categories with zero markers, deep/flat LVS and13 expected fault rejections.

Actual native port ordering now has irx,xn,xp rather than the preceding view's irx,xp,xn. Fresh RC and subsequent wave models must bind this actual semantic order; no stale positional mapping is acceptable. No new RC or loaded electrical result is claimed. Use the frozen full numerical fresh-RC pipeline with this exact qualified canonical archive and unchanged original runtime cache, then rerun original loaded predicates without relaxing limits.

Mainchip route41349316524/sourcea47bb1895ad12fdebddeb055dc5e3e9c414c04e0 remains the existing handle. Keep its actual iteration snapshots and final/failure evidence; do not duplicate. Snapshot reload, classes/connectivity/diode PG, DRC/antenna, matching netlist, fresh RC and original three-corner setup/hold still require actual proof. Full serial PHY and final timing are not complete.

Latest instruction: **her şeyi bulutta yap, lokalde bir şey bırakma temizle.**
It overrides the earlier local-execution wording in the active goal. All CAD, simulation, native archive/layout/waveform acquisition and numerical/geometric analysis run on GitHub. Local coordination uses source/API-derived text in RAM only. Never acquire native ODB/DEF/GDS/SPICE/raw archives locally, including RAM. The local workspace and project temp entries were verified empty, with no local CAD processes. Unrelated user files remain untouched.

## Latest result: full physical pass; current native graph and mainchip routing in progress

Execution remains cloud-only. All local task workspace/temp entries are empty and no local CAD process is running. Native GDS/ODB/L2N/SPICE/raw archives remain on GitHub; source/API/derived text coordination is RAM-only.

Physical run41349608125/source8203934d2a56cdcc8a2fa7754d76d2bf24330658/release430854100 completed successfully on the actual four-path GDS1001172bytes SHA2561c7d56173b350c067df5db468b4099d7c5b8681e891d027b700737566c2c3b94. The full original checker reported560 DRC categories, zero markers, deep and flat LVS pass with124HBT+50MOS+98resistors+7MIM+221taps=500 primitives and the25-port reference, plus13 REJECTED_EXPECTED_FAULT results. All16 native phases passed their required outcome. This proves physical equivalence and DRC within that CDR block's tested scope, not full serial PHY, mainchip LVS/timing or production readiness. Complete native output release assets remain in GitHub: native-physical.tar.gz5979956bytes SHA256bcdeb4489a4923540119f8d71c06224aa0a66f013e6d04e589ca6538fffb8528; index20773bytes SHA2565e44568d47ab16bf18465ffadea480554240204ae066704b1a42a2ee0eeb4611.

Fresh canonical run41350835442/source360a01ea394943614b25895e6389221f2b0ca0ba/branchcodex/cdr-wire-tail-canonical/release430861219 was dispatched. Its before-reference is the actual successful six-shortcut fresh-RC producer41339125361/sourcec6abc571734c0e3197ce1227e990b7b1420610da/release430788452, GDS244992e91350d3bcac15fd58c48cc5249ee615ffc21f30f539a0cbb6b42fc347. All3236 native members are authenticated on GitHub. The earlier pre-six-shortcut42ed reference and old six-M2-only material declaration cannot prove this new mixed-layer delta.

The new adapter independently reconstructs the exact Metal2/Via2/Metal3 additions for four original owner nets from the admitted bridge centers, two new Via2 cuts, original access boxes and complete route points. All original conductor partitions and all13 layers must satisfy exact material union with no deletion or undeclared material. Original500 primitives,1446 terminals,25 ports,978 logical anchors,160 planes/19 fault cases and frozen native identity/source-pin/parent-geometry/worker checks remain. Three new refusal cases cover wrong Via2 count, off-grid new routing and wrong connected endpoint. Source-controls have passed; consult actual run snapshot for native completion. No new RC or loaded transient has run yet. After genuine canonical qualification, derive fresh distributed RC and execute the original loaded electrical/device predicates without model substitution or relaxed limits.

Mainchip actual full64-with-snapshots run41349316524/sourcea47bb1895ad12fdebddeb055dc5e3e9c414c04e0/release430851918 remains monitored. Its independent31 source controls41349079496 and repeated controls passed. Snapshot-only Tcl instrumentation leaves original64 iterations, seed42, threads, clock/layer/resource constraints and supervision intact. Native snapshot reload, restored classes, scoped connectivity,2702 diode PG contacts, original nets/clocks, DRC/antenna, matching154480-instance diode-inclusive netlist, fresh RC and original three-corner setup/hold remain unproven. Preserve the existing live handle; no duplicate dispatch.

All rejected intermediate and previous loaded electrical failures remain retained. Full serial Gen3x4 PHY and final chip timing/production approval remain open. Monitor inventory718 runs; eight-hour monitoring remains read-only with automatic_native_dispatch:false. Prior monitorHTTP502 is not claimed resolved.

## Previous checkpoint v267: four mixed clock-selector paths generated; full physical checks and mainchip route running

Execution remains GitHub-only. Local workspace and project temporary files remain empty; native archives/GDS/ODB/L2N/SPICE/waves are never acquired locally. Source/API/derived-text coordination is RAM-only. This overrides stale local-execution wording in the active goal.

Native stack audit41348276461/sourcea5b632140452e3c2b28bff69521d98cdc0a1ccd7/release430845320 passed the original42 controls and authenticated the same actual six-shortcut parent. It proved that all four previously blocked M1 endpoints have same-component, enclosed existing Via1/Via2 paths to legal Metal3 landings. Original entire-Metal2 landing reuse was rejected by foreign-M2 clearance, not malformed cuts. The M2 emitter-side terminals instead admit direct Metal2 access and are blocked on direct Metal3. Thus mixed Metal2/Via2/Metal3 routing is based on actual geometry, not assumed layer connectivity.

Initial mixed generation41348741667/source748b5ab8c76603d8436aaf921f600e109d1eb7f7/release430848757 passed52 controls and generated only D_emitter/C_emitter. Its actual1000340-byte GDS SHA256f7782129bd7e3b6fff0ebdd5c6646eb765b175368ef2e9b78d348979ba1b9e88 and exact serialized delta/original-material reversal were preserved, while the run remained FAILED because both collectors were unrouted. Each collector had six admitted bridge options but all432 simple Metal3 routes failed actual foreign-material guards. This failed intermediate remains evidence, not a physical pass.

Obstacle-aware generation41349305622/source2c5de6a9a9c84f170a9272eed63b37156e6e6043/release430851849 succeeded. All60 controls passed: original42, ten mixed-layer guards and eight search refusal/geometry fixtures. Both collectors use an actual rectilinear obstacle graph on the5nm grid with conservative center clearances910nm around foreign Metal3 and310nm around foreign vias; the original complete final geometric guards are rechecked on the full assembled metal and cuts. Native searches expanded7901/7939 nodes and each collector path length is604235nm. Both emitter paths retained the direct candidate. All four paths are now generated: D_collector,D_emitter,C_collector,C_emitter. Actual GDS1001172bytes, SHA2561c7d56173b350c067df5db468b4099d7c5b8681e891d027b700737566c2c3b94. Only Metal2/Via2/Metal3 were added, with two new Via2 cuts per path; all original devices,M1,Via1 and preexisting material were retained. Actual serialized delta and exact original-material reversal passed.

Full physical verification41349608125/source8203934d2a56cdcc8a2fa7754d76d2bf24330658, branchcodex/cdr-wire-tail-physical, reservedrelease430854100, tests this exact new GDS. Frozen checker SHA2563ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66, all560 DRC categories, deep/flat500-device25-port LVS and13 injected faults remain unchanged. Parent reference schematic/LEF, PDK, AppImage and supervision limits are unchanged. Consult latest actual run snapshot; do not assume physical success from generator success. After a physical pass, obtain fresh canonical/material/terminal binding, distributed RC and the original loaded waveform/device predicates. No electrical/PHY acceptance exists yet. The previous rejected loaded result41341309504 remains authoritative until replaced by real new simulation.

Mainchip full64 snapshot sourcea47bb1895ad12fdebddeb055dc5e3e9c414c04e0, branchcodex/mainchip-full64-snapshots, passed independent controls41349079496:11 original stage tests,12 original native-preservation tests and8 new snapshot tests. Actual native run41349316524/release430851918 was then dispatched and repeats those controls before routing. Original full64/seed42/two threads/layers/clock constraints/resource checks/route budget remain. The sole Tcl delta enables the preexisting iteration snapshot branch, so progress can be published even if the route times out. The actual native run and snapshot readback/reload are not yet qualified; every snapshot is marked reload_verified:false. Original full64 run41323446729 failed on the four-hour elapsed limit, not OOM, with no returned final route. Do not repeat that old job or reuse stale postroute/STA pins. Upstream source confirms the snapshot path at OpenROADdcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/drt/src/dr/FlexDR.cpp; this is source evidence, not a native resume-equivalence claim.

For mainchip, once actual new bytes are available: reopen/audit them in the cloud, restore original classes using new pins, check scoped connectivity/2702 diode PG contacts/original nets and clocks/DRC/antenna, export matching154480-instance diode-inclusive netlist, generate fresh RC and run the original three-corner setup/hold constraints. Full serial PLL/CDR/SERDES/training/LTSSM/replay/credit/ESD and production approval remain open.

Inventory717 runs; existing eight-hour monitor is read-only and automatic_native_dispatch:false. Earlier monitorHTTP502 is not claimed repaired. Preserve the live jobs and inspect their existing handles before any follow-up dispatch.

## Previous checkpoint v266: cloud-only cleanup verified; terminal failures retained

All native CAD, layout, waveform and archive processing runs on GitHub. The local workspace and project-specific temporary entries are empty; no local CAD process is running. API/source/derived-text coordination uses RAM only.

Mainchip run 41323446729 (ff1c0e6163e0ba1537a075d50e940fafc9332c64) ended in failure. Its actual full-route-stage report identifies elapsed_limit at 14400.716919044 seconds, returncode -15, with SIGTERM cleanup. Docker OOMKilled is false. The last memory sentinel measured 9366512 KiB RSS and 5930368 KiB available, against the original 10485760 KiB group limit and 2097152 KiB availability floor. Thus the recorded termination was the four-hour route deadline, not an OOM. The log finished iteration 28 with 86 routing violations and reached iteration 29, 90 percent, with 85 violations before termination. These are partial router observations, not final DRC, a saved final route, or timing closure. The stage reports route_returned:false and an empty checkpoints object. Durable native release 430685443 and derived/native workspace artifact metadata are preserved. Inspect actual candidate-outputs.json before claiming any resumable post-route database. The next route change must address checkpoint/lifecycle/time budget within hosted limits, preserve original constraints and resource checks, and use actual saved byte pins. Do not repeat the identical four-hour job blindly or invoke old restoration against stale pins.

Three physical clock-selector shortcut attempts are retained:
- 41345681826 / 3a54dd452f99a892e8e9d7521c87e51fe933a431: original M1-only access refused an actual M2 terminal reference; 31 controls passed.
- 41346242975 / e56e07ea71fa7a0d1d58d02e4e670e9766e6184c: direct owned-M2 access admitted all four M2 sides; original M1 access admitted none; 38 controls passed.
- 41346732942 / 7210be7e9fae153c45ca7bfeb52fa9d21c35fd81: geometry-derived M1 search seeds retained all original guards, but all four M1 sides still failed; 42 controls passed. No route candidates were evaluated and no new GDS was generated. Representative collector sites failed foreign-M2 clearance and existing-via clearance; MOS-drain sites failed existing-via clearance. These bounded search failures do not prove no legal topology exists. Next inspect/reuse actual same-net existing via stacks and attached M2, proving ownership and original lower/upper enclosure, without relaxing foreign-material spacing or pretending a different pin is the original one. Only then consider another physical candidate.

Original loaded electrical failure remains: four HBT headroom violations, A/B delay, C/D wrong signs, X/Y and phase/V-I gates. Measured collector/emitter wire losses and local avss lift remain actionable evidence, not accepted fixes. Every new geometry requires strict DRC/LVS, canonical binding, fresh RC and unchanged loaded waveform tests. Full serial Gen3 x4 PHY, final mainchip setup/hold and production approval remain open.

Verified PCIe nettype repair and full-wave diagnosis from checkpoint v265 remain intact. Monitor inventory now includes 711 runs; eight-hour monitoring stays read-only, automatic_native_dispatch:false. The previously observed monitor HTTP502 is not claimed resolved. No new native run was dispatched during this terminal-evidence update.

## Previous checkpoint v265: full native wave diagnosis and PCIe nettype repair

All CAD, native acquisition and geometric/numerical execution remain on GitHub. Local workspace and task temporary files remain empty; API/source/derived text coordination stays in RAM.

Actual full-wave diagnosis 41344170319/source 12c97e1c3510fd96cd410ba1e9d62f2b760a009e passed eight frozen-reader refusal controls, authenticated every one of the 130 native capsule members, parsed the complete original 113475-row/1152-column waveform and reproduced the original device/margin/delay/wrong-sign measurements. It did not execute a new transient and did not accept the rejected PHY. Extended diagnosis 41345078765/source 11e7c3f4b33388da8c03d7d571cc405fd384db36 repeated this and measured actual same-net terminal voltage drops.

The four failed HBTs are cn-clock selector pairs 61/62 and 115/116. At the actual minimum-Vce times, D collector-to-connected input-pair emitter differences are 41.3/60.5 mV and C differences 27.3/79.8 mV; clock-selector emitters sit roughly 46.5–47.2 mV above connected MOS drains on the same extracted nets. The corresponding local bleed-resistor avss terminals are at 276/283 mV, whereas substrate is near 1.1 mV. These are measured distributed-wire drops, not ideal-node substitutions. They motivate physical interconnect improvements; they do not by themselves prove a fix or quantify every contribution across the whole trace. A/B transition settling, C/D wrong signs, X/Y and phase/V-I gates remain rejected.

New physical generation: run 41345681826/source 3a54dd452f99a892e8e9d7521c87e51fe933a431 on codex/cdr-wire-tail-shortcuts. Reserved tag cloud-results-41345681826-1-cdr-wire-tail-shortcuts. Targets are D collector T061_C–T056_E, D emitter T061_E–T005_D, C collector T115_C–T108_E and C emitter T115_E–T034_D. The baseline is the actual already-generated six-shortcut GDS, SHA256 244992e91350d3bcac15fd58c48cc5249ee615ffc21f30f539a0cbb6b42fc347, obtained from successful fresh RC 41339125361/release 430788452, all 3236 members authenticated. Current raw canonical anchors and L2N establish ownership; composition binds exact transistor IDs/terminals. Original eight geometry helper/control bodies are AST-identical and 31 original controls remain required. Generation proposes guarded 600 nm M2/Via1 routes, preserves original devices/M1 and all six earlier shortcuts, and serializes/reverses the exact new layer delta. Any partial or blocked attempt must remain failed and retained. It requires fresh strict DRC/LVS, canonical binding, RC and unchanged loaded electrical gates before acceptance. Do not repeat this existing dispatch blindly.

Separate actual CI failure repaired: hw/soc/rtl/pcie/soc_pcie_gen12_raw32_align.v lacked default_nettype guards. Only default_nettype none/wire lines were added; every original behavioral source byte remains. Source 95e0aa8795d7ec7a9d13f59e01d2a936d5ddc609, run 41344951300 passed native Icarus module compilation, original prepared-upstream/whole-SoC guards and original complete lint with the unchanged diagnostic ledger. This closes that nettype failure only; the ledger still retains existing warnings and the rest of formal/boot is not claimed complete. The verified RTL edit is imported here.

General checks 41344155576 was an exact-commit duplicate of 41343649094 (both b038f1e12b35b30d90b619392f74b6388004ae32). The less-progressed duplicate was cancelled to release hosted capacity; its formal-and-boot nettype failure and cancelled job states are preserved, not relabelled passes. The older checks run was left running. The dedicated waveform job subsequently acquired a runner and completed. This observation does not prove GitHub account quota settings. Future source-only experimental commits should avoid launching duplicate broad checks; all required dedicated tests still run at exact source.

Mainchip full64 41323446729/source ff1c0e6163e0ba1537a075d50e940fafc9332c64 remains independently monitored; consult the latest snapshot. Do not duplicate it based on observation or assumed deadlines. After actual terminal publication, authenticate current outputs, restore original classes with current byte pins (old restoration code hardcodes an obsolete candidate), audit connectivity/2702 diode PG contacts/original nets/DRC/antenna, export matching 154480-instance netlist, then fresh RC and original three-corner setup/hold. Full serial PHY, final mainchip timing and production approval remain open.

Monitor inventory: 709 tracked runs, eight-hour read-only, automatic_native_dispatch:false. Prior monitor HTTP502 remains unresolved. All derived proofs, failed logs and exact source copies are retained on GitHub.

## Previous checkpoint v264: loaded transient rejected; exact device classification completed

All CAD, simulations, native payload acquisition and numerical/geometric work remain on GitHub. Local workspace and project temporary files are empty; local coordination uses source/API/derived text in RAM only.

The actual six-shortcut fresh-RC loaded run 41341309504 (source e685588ec268543e351ce4e68c8008bf212058c8) completed its native engine normally in 748.264 seconds, return code 0. The unchanged electrical gates rejected it. Native waveform contains 113475 complete rows and 1152 columns, 1045823299 bytes, SHA256 b01865684d99a7aa07be345aed90d4ec2b745f929b8a1df2e5ea22c61c77c276. The full 130-member native capsule remains in release 430801948, tag cloud-results-41341309504-1-cdr-wire-shortcuts-loaded; four parts total 1054388621 bytes, archive SHA256 bd0c7813cf9708bf7c1989bcc8581a1f7226a31fb3870b5e8196b8f513d55180. Never download this capsule or waveform locally.

Terminal proof is imported from bd28e3e77f607c827713fb3295e41dce0858a4fc into docs/evidence/wire-loaded-terminal-41341309504. All 78 derived-file readbacks and 41 server-side source blob identities were verified. Receipt SHA256 38d8f6a4abff09ea97b615e762fb58f86ca66fbdae1c862988e753477b96968f. The original derived artifact omitted one hidden workflow source due to upload-artifact defaults; exact source recovery is explicitly recorded separately and matched to the native index. The original artifact was not changed. Future loaded uploads must include hidden files.

GitHub classifier run 41343651743/source b038f1e12b35b30d90b619392f74b6388004ae32 passed 11 rejection fixtures and reproduced every original scalar predicate from the exact authenticated rejected measurement. It performed no new transient and read no native waveform. Four HBTs alone fail the device safety predicate: xpd.xd0061/62 minimum active Vce 0.340654/0.341871 V and xpd.xd0115/116 0.376225/0.377426 V, below the unchanged 0.4 V gate. All 50 MOS checks, HBT/MOS/stage tail-current predicates and seven capacitor-voltage predicates passed. This diagnosis is not electrical acceptance.

All four samplers still fail margin/clock-to-valid; C/D have 25/54 wrong-sign samples. Comparisons X/Y have 386/43 wrong signs. Phase average is 13.573 mV against 30 mV, and V/I current is 41.426 uA against 50 uA. V/I bias passes. Do not relax these conditions or treat physical/RC qualification as functional PHY closure.

NEXT PHY: use the actual new waveform on GitHub to locate those four HBTs in the physical sampler stages, correlate clock/data/output transitions with collector-emitter headroom and wrong-sign comparisons, and make the next evidence-driven circuit/layout repair. Preserve the actual 500-device model and source identity; old width2/Nx8 experiments are not newly regenerated layout. A circuit/model experiment must remain explicitly experimental until new geometry, strict DRC/LVS, fresh RC and unchanged loaded gates pass.

Mainchip full64 run 41323446729/source ff1c0e6163e0ba1537a075d50e940fafc9332c64 remains independently observed. Read the latest checkpoint snapshot before any action; do not duplicate dispatch. After terminal publication, authenticate actual new routed/partial files and restore original classes on those new byte pins. Existing restoration source 05d336a1b1b681c9d96b71d464c5ea430835e438 hardcodes an older producer/candidate and cannot admit this new output unchanged. Then native connectivity, 2702 diode PG contacts, original-net preservation, DRC/antenna, matching 154480-instance/1351-diode netlist, fresh RC and unchanged three-corner setup/hold.

Full serial PLL/CDR/SERDES, training/LTSSM/replay/credits/lane/TX/serial top, final mainchip physical/timing and production approval remain open. Monitor inventory is 705 runs, eight-hour read-only, automatic_native_dispatch:false; prior HTTP502 monitor failure remains unresolved.

## Previous checkpoint v263: actual new RC loaded-wave host running on GitHub

The new41-file source closure is on codex/cdr-wire-shortcuts-loaded. Current sourcee685588ec268543e351ce4e68c8008bf212058c8, run41341309504, reserved release430801948/tag cloud-results-41341309504-1-cdr-wire-shortcuts-loaded. Source-controls passed and loaded-wave is active. Do not duplicate dispatch. Current phase combines authentic acquisition,real model binding/preparation,and actual transient/measurement; an active workflow step alone does not prove the engine has already started.

Host scripts/cloud_cdr_wire_shortcuts_loaded.py restores the actual new500-device/24474R/15640C model from freshRC41339125361 and authenticates all3236 archive members. It reuses the exact original loaded runtime/model library (120members/40selected) while preserving that historical pump run's electrical failure. No width2/Nx8 experimental device changes enter this actual physical500-device model.

All9frozen loaded source files,29definitions and5complete executable numerical blocks are unchanged. Current source controls include10 context/RC-proof refusals. Historical acquisition/admission/current_configuration functions are not invoked as current authority: only four named pure transport/engine helpers are isolated, and current verified inputs are provided to explicit cloned numerical function namespaces. Original prepare_case/measure_case code objects remain exact. Actual native projection comes from the frozen deck's original first3AST statements after full actual500-device model binding; old1151-vector counts are not assumed.

Preparation repeats all13 actual native binding faults and2equivalent-unit checks. The actual new semantic26-port interface retains iry,yp,yn and wire_cref. Full original sourcebits,125psUI/2nsstart/34.25nsstop/0.3125psstep,solver/backend,current/device/data/phase/V-I conditions remain. First scenario is nominal_late with external clock, not completePLL/CDR/allcorners/fullserialPHY. Engine keeps original1200s and16MiB log bounds with tokenless child cleanup. No acceptance limit was changed.

The initial run41341073013/source8e1795108084acea87c9ac054f1f87e466c7b346 failed Python parsing before any source control or native model acquisition. Missing whitespace between __code__ and and was corrected. Original full job log/run/jobs/emptyrelease/noartifact metadata is permanently preserved in6files under docs/evidence/wire-loaded-terminal-41341073013; sourcehead retained by its exact-source tag. Workflow now tees independent source-control logs, so a parser error cannot suppress all diagnostics. Empty original release430800531 remains distinct.

Current publication always attempts full success/failure native preservation after reservation. Actual output root cloud-wire-shortcuts-loaded, archive root wire-shortcuts-loaded, full indexed native.tar.gz.partNNNN plus parts.json and complete-output-index.json. Derived artifact wire-loaded-derived-RUN has only text; full native fallback wire-loaded-native-fallback-RUN stays on cloud. Never acquire native archive,model SPICE,raw OP/wave or CAD payload locally. Engine outcome is not known yet; inspect actual measurement-result/host-failure/engine-result and complete native publication before proceeding.

NEXT: observe current41341309504, collect full actual success or failure without weakening original gates. If electrical rejection occurs, use newly measured wave/device/phase evidence for the next concrete circuit/layout correction; do not substitute old outputs or source metadata for a real transient. If initial preparation fails, preserve proof and fix the actual failing current binding/transport. Do not relabel preparation,physical or RC qualification as full electrical success.

Rootv262 qualifiedRC proof remains475files/90999065bytes. Mainchip full64 run41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64 remains independently live; no restart based on observation. After actual termination use new output classes/pins/connectivity/PG/DRC/antenna, matching154480-instance/1351diode netlist,newRC and original three-corner setup/hold. FullserialPHY and finalSTA/production approval remain open.

All native work and acquisition stays on GitHub. Local workspace/temp remain empty; source/API/derived text only in RAM. Monitor704rows/8h/read-only automatic_native_dispatch:false,prior502 not declared resolved.

## Previous checkpoint v262: actual six-shortcut fresh RC numerically qualified

Run41339125361/sourcec6abc571734c0e3197ce1227e990b7b1420610da completed successfully.13 current-host controls,28 frozen-core controls and33 phase controls passed. All14 actual supervised commands returned0; all11 actual source/run-bound phase receipts validated. Both precise MIM input orders, original raw13/MIM5+9/composition21 controls and complete branch/capacitance ownership passed. Native lifecycle has primary_error null,heartbeat stopped,no remaining live process.

Actual new model:500 devices,24474R,15640C,1446terminals. Model mim/composition/pd500-mim-wire.spice is1976884bytes SHA2562d58e10cf840abf3648f89fa97d8124ba3cd7593f39f84de05d0992833b53c27. Composition973274bytes SHA256e1fe928d7cae252dd21d8cbd7d085500c1f991a3a3c9a8eae7eaa232479fddc5. Actual semantic interface is the current25-port order (iry,yp,yn) plus wire_cref. Never copy old positional yn,yp order.
This is newly computed RC from physically qualified GDS244992e91350d3bcac15fd58c48cc5249ee615ffc21f30f539a0cbb6b42fc347. Device geometry was not changed by width2/Nx8 screening and must not be silently combined with those trials. New R/C counts alone say nothing about electrical improvement.

Permanent release430788452/tag cloud-results-41339125361-1-cdr-wire-shortcuts-fresh-rc has complete-output-index.json asset699234264,609145bytes SHA256ea1dd295d64c3627d0f44b1cc25fc60a7bc9456bc451def188134e877163022e; native-fresh-rc.tar.gz asset699234263,61422387bytes SHA256a1820c15192ac63b4181931d38e3ee62d45fe1ffca5db08b47f6fe62b7fc60c0. Archive root wire-shortcuts-fresh-rc,3236 fully indexed members.
Complete475-file proof ccb1a3059fc6a434bb0a9fb325b17a06a570529f,90999065bytes,receipt453765586de3fc812fc1c27914c3fd16ed168fd98deac183cb89d721b3f2f991 under docs/evidence/wire-rc-terminal-41339125361. Original preflightfailure41338512381 remains separate.

NEXT: execute the actual new500-device distributed model under frozen loaded-wave/device/phase/V-I gates. Current source basis docs/evidence/wire-shortcuts-loaded-basis.json pins full3236-member RC capsule,new model/composition/planes,actual qualification/source/tag/release and original loaded numerical/runtime references. SOURCE PREPARATION ONLY: no new transient has started.

Reusable frozen loaded library at source43fd3f71a289fef004aeb41cd2d0972d81f76f41:
- scripts/cdr_via2_m3_loaded_core.py and scripts/cdr-via2-m3-loaded-core-catalog.json contain9 complete pinned source files,29definitions and5 executable blocks (scenario,prerequisites,binding,deck,measurement); historical_runtime_reference is not executable. Actual catalog original source84b8b591e10be32716947c8d6b079fd7a21ce18d. Keep numerical AST/body bytes unchanged.
- Original current_configuration is bound to old41251732540 and its exact old INPUTS_SHA. Do not invoke it as current authority or bypass checks. New explicit host must bind new RC producer and actual current context, and provide verified current configuration to isolated cloned frozen pure functions. Historical configs only supply immutable runtime/transport constants. Do not overwrite frozen old inputs or fake old receipts.
- prepare_case/measure_case/numerical_namespace/verify_current_inputs/verify_runtime/verify_projection can use independent namespaces whose current_configuration validates the actual new producer, new qualified model/composition/planes, current generated projection and actual exact interface. Keep every original measurement/body and unchanged models/runtime.
- bind_native validates all500 device cards/1446 terminals/26ports and topology-derived sampler/VI aliases. It is semantic-order aware: external nodes are constructed in contract interface order. No source edit is needed to handle yp/yn order.
- Generate the new projection ON CLOUD from actual newly restored model and composition using the frozen binder and the original deck prefix selecting nodes/vectors. Do not reuse old1151-vector or old15489-wire-map counts: those were measurements, not invariants. Declare actual native-card validation when it ran; source projection alone is not a wave result. Preserve and protect projection bytes for both preparation and measurement.
- Native preparation must repeat all13 actual binding rejection controls and equivalent-unit checks. Frozen scenario UI125ps,START2ns,STOP34.25ns,STEP0.3125ps; 125ps is8GT/s. Original core's first declared case nominal_late is not full PLL/CDR or full-corner closure. Preserve original sourcebits,solver/backend readbacks,data/current/device/phase/V-I gates.
- Original runtime config scripts/cdr-via2-m3-loaded-runtime-inputs.json binds pump39029337682/release415768966. Its historical electrical failure must remain failure while reusing only authenticated frozen engine/model bytes. Complete archive120members/40selected,patched-ngspice SHA103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509 and model-pin436914ae3ef1e1727b31e799317cfd92354cf00a00839527f49fcb079b9da1a6. Full acquisition and native parsing/wave work stays on GitHub.
- scripts/cloud_cdr_sampler_load.py has reusable isolated pure acquisition/restore/run_engine helpers. Never invoke its historical acquire/producer admission or simulation that selects old model or experimental candidate. Original engine limit1200s and log16MiB; preserve actual process exit/cleanup,all raw waveform/OP/deck/stdout/stderr and errors. Sourcecontrols and independently reserved exact-source release precede native execution.
- scripts/cdr-sampler-load-host-pins.json on the same source has37files. Use relevant unchanged source closure, archive original workflow separately or omit it from a new manifest, and pin the actual new current host/workflow independently. All29frozen defs/5executed blocks plus original runtime records must stay byte-exact.
Full new transient source/dispatch is still to be implemented, not asserted complete.

Mainchip full64 run41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64 remains live; do not duplicate. Route14400s/outer18000s deadlines are execution budgets, not observation limits. After terminal inspect actual classes/pins/connectivity/PG/DRC/antenna, export matching154480-instance/1351diode netlist, freshRC and unchanged three-corner setuphold (20/4/8/8ns,5percent derate). Old153130-instance route12 netlist cannot be reused.

All native CAD/simulation/acquisition/geometry/numerics stay on GitHub; no native payload download even to local RAM. Local source/API/derived text only in RAM; workspace and project temp empty. Monitor702rows/8h/read-only automatic_native_dispatch:false; previous monitor502 not declared healthy. Physical/canonical/nominalRC passes do not close fullserialPHY,foundryRCcorner qualification,mainchip timing or production approval.

## Previous checkpoint v261: current six-shortcut fresh RC dispatched on cloud

Physical run41335306847 and canonical run41336588343 passed on the actual six-shortcut GDS244992e91350d3bcac15fd58c48cc5249ee615ffc21f30f539a0cbb6b42fc347:560DRC categories zero markers,deep/flat500-device LVS and13 faults; native78-file view,500devices/1446terminals/25ports/978anchors,full113x13 material identity. These results are not electrical/fullPHY or final mainchip timing acceptance.

The current fresh RC host is scripts/cloud_cdr_wire_shortcuts_fresh_rc.py on codex/cdr-wire-shortcuts-fresh-rc. Current source c6abc571734c0e3197ce1227e990b7b1420610da protects2111 source/config files. Original numerical16sources/30definitions/9blocks remain byte-exact; current hosted admission and current11phase receipts bind actual78-file inputs, actual25-port order (iry,yp,yn),all raw13/MIM5+9/composition21/order controls. No old RC numerical result is reused as a new result. Original authenticated658-file runtime cache is restored and revalidated only on GitHub.

Initial run41338512381/source2c100541638c37b012447e41c50f3aba51e19e9b failed source preflight with KeyError bytes;1137 historical source pins contain sha256 only. No native input/extraction started. Full original traceback and7-file proof are preserved under docs/evidence/wire-rc-terminal-41338512381. The fix checks every declared SHA256, optional size and Git blob identity, with7 source-schema fixture tests and no weakened numerical acceptance. It also includes host-failure.json in future source-control artifacts.

Fixed run41339125361/sourcec6abc571734c0e3197ce1227e990b7b1420610da was independently dispatched once. Reserved exact-source release430788452/tag cloud-results-41339125361-1-cdr-wire-shortcuts-fresh-rc. Watch source-controls then native-rc; do not duplicate dispatch. Workflow native timeout360min; each actual command bounded1200sec with supervisor evidence. Runtime input/cache, native current view, extraction, all raw results and permanent complete archive remain cloud-only.

NEXT: collect actual terminal current RC evidence, preserving failures, then require actual original complete numerical qualification before unchanged loaded-wave/device/phase/V-I validation. New shortcut electrical improvement remains unmeasured. Nominal RC is not foundry corner RC or production signoff.

Mainchip full64 run41323446729 remains independently live on sourceff1c0e6163e0ba1537a075d50e940fafc9332c64; no duplicate restart. Its native process deadline14400s and outer18000s are separate from observation. After terminal inspect actual output classes/pins, native connectivity/PG/DRC/antenna, matching154480-instance netlist including1351diodes, newRC and unchanged3cornersetuphold. Oldroute12netlist153130instances is stale.

User latest instruction governs all work: everything on cloud, no project files/native payloads on local storage. Local workspace/temp are empty; only source/API/derived text is handled in RAM. Native archives/GDS/L2N/ODB/DEF/SPICE/raw must never be downloaded locally even into RAM. Monitor remains8h/read-only automatic_native_dispatch:false; prior502 not declared resolved. Full serialGen3x4PHY and final mainchip routing/timing remain open.

## Previous checkpoint v260: actual six-shortcut native view qualified; new RC basis frozen

Run41336588343/source2e42588a8ae03d6ef460c5cecf16943d715c5147 completed successfully.39 source controls and all eight actual native phases passed. The physically qualified GDS244992e91350d3bcac15fd58c48cc5249ee615ffc21f30f539a0cbb6b42fc347 now has a fresh78-file native view.
Full identity preserved:500 devices,1446 terminals,25 ports,978 anchors,238 native nets. All160 planes/19 plane faults,16 leaf placements/5 independent geometry controls, source-pin recovery and native witness controls passed. Complete113-conductor x13-layer material comparison has1469 rows; exactly six M2 rows changed. Added area38344150DBU2 for each A/C path and39784150DBU2 for each D path. No new vias, missing conductor material or foreign partition changes.
All eight supervised commands returned0; primary_error is null, heartbeat stopped and no live process remains. This is actual newly derived native geometry/connectivity evidence, not an inferred RC or wave improvement.

Full146-file proof7d09fd1cc02f50cafb0efe5e59b680982d17370f,20052852bytes,receipt5360d112ab9d8d38731c4c97c309b21d98ed34e04a93e1b11458cd779c9e437c is imported under docs/evidence/wire-canonical-terminal-41336588343.
Permanent release430771584/tag cloud-results-41336588343-1-cdr-wire-shortcuts-canonical:
complete-output-index.json asset699151389,22738bytes,SHA256280383a72f37276acc2e1026ef3795105a92d0e1d9c46de6e51c53fd0a67c40e;
native-canonical.tar.gz asset699151390,3548835bytes,SHA2562ef9a587865ba810d28fee2db13944cec7fcb5f62f446e3168f608389ee90137.
Archive root wire-shortcuts-canonical,133 members. Current view path view/candidate/ with78 members. Actual original runner root hw/soc/out/cloud-cdr-wire-shortcuts-canonical/view/candidate.
Derived artifact13095134941,1295843bytes,SHA25654fec302808159110070a160efdf90fb7b1d7d76793ba86b1f27f46ee2e64f78. Native archive was not acquired locally.

CRITICAL semantic port-order change: the new actual native order contains ... iry,yp,yn,irvx,irvy,vin,vip, whereas the old order had ... iry,yn,yp,... . Full public name/terminal/anchor identity matches; raw enumeration order is not a circuit change. New RC config and compact model/binding/stimulus must use the actual new semantic port order from native_identity.new_native_port_order, never retain the old positional interface. Source/device/anchor order must not be guessed.
docs/evidence/wire-shortcuts-fresh-rc-basis.json now binds the actual current78 files, full133-member native capsule, qualification/hash, source/release/tag, actual25-port order, and authenticated original runtime-cache inventory. It is SOURCE PREPARATION ONLY; native RC remains unexecuted.

NEXT REQUIRED NATIVE ACTION: adapt the frozen numerical RC core at9bf12d1e496f7d9192582175ab2fa714e3e8d41b to this actual newly qualified current view, with current-source hosted admission and an independent empty source-bound result release. Do not rerun or relabel old41251732540 outputs as new RC. The original numerical definitions can remain byte-exact:
- scripts/cdr_via2_m3_fresh_rc_core.py: current_view_proof validates configured root and all78 pins; prepare_current_view copies actual inputs into binding/wire-stage; binding_native_export/validate build500-device contact-oracle/model binding; derive_wire_methods runs the frozen extraction/audit methods.
- command_plan requires output ROOT/hw/soc/out/cloud-cdr-via2-m3-fresh-rc and original native entry path. It has13 commands after prepare:binding-export,binding-validate,wire-extract,wire-audit,then precise and precise_reversed MIM generation/extraction/finish/audit,then compose. Reusing the path on a fresh cloud runner is possible; the old producer/authority cannot be reused.
- scripts/cdr_via2_m3_fresh_rc_native.py pure helpers include current_packet,verify_runtime_cache,copy_cache,operate,validate_complete_files,source_pins,lifecycle/receipt validators. If extracting their definitions into a new explicit current host, preserve actual phase context, all11 terminal receipts, exact executed command streams, original raw13 corruption refusals, MIM5/9controls, composition21controls, whole branch/capacitance ownership and direct/reverse measured count/value equivalence. Do not execute old main/authorized/admission wrappers on the new producer.
- core.current_binding reads scripts/cdr-via2-m3-fresh-rc-namespace-inputs.json and CurrentBinding freshly rereads descriptor+summary on every stage. It must bind the current new source/run and actual new port order; no historical report authority.
- Original RC capsule41251732540/release430243359 already authenticates3091 members and contains658 runtime-inputs/ members totaling32215858bytes: frozen_layout197 files, model source and model-pins, baseline Magic, precise Magic and complete provenance. They can be restored on cloud from that exact fully authenticated capsule instead of fetching the same runtimes repeatedly. Record current restoration/hash checks and repeat original producer provenance validation; historical acquisition status is not current execution proof.
- verify_runtime_cache checks complete byte inventory for frozen_layout/models/magic, exact selected precise outputs and summary, all original MODEL_PINS under ROOT/pdk, and every frozen PDK runtime file. Copy runtime-inputs/models/models into ROOT/pdk/libs.tech/ngspice/models and original frozen_layout members into ROOT without overwriting different source. Precise and baseline Magic library hashes and AppImage/scoped AppArmor remain unchanged.
Then run native freshRC, preserve full success/failure proof, and only after complete numerical qualification execute unchanged loaded-wave/device/phase/V-I tests. NominalRC still does not constitute foundry RCmin/max or production signoff. Width2/Nx8 device screening is not regenerated accepted physical geometry.

Physical verification41335306847 remains a genuine separate pass (560DRC0markers,deep/flat500-device LVS13). Mainchip full64 run41323446729 remains independently live; no duplicate restart. After actual route termination verify classes/pins/PG/DRC/antenna, matching154480-instance netlist,newRC,and unchanged three-corner setup/hold.
Full serial Gen3 x4 PHY and final mainchip physical/timing closure remain open. Local workspace/project temp remain empty; all native CAD/acquisition/analysis is GitHub-only. Monitor inventory700/read-only automatic_native_dispatch:false remains; prior monitor502 has not been declared resolved.

## Previous checkpoint v259: six-shortcut GDS full physical verification passed; fresh native view running

Actual physical run41335306847/source50cb5767faef80336161ab7fa40de7d99dbf6243 completed successfully. All36 source controls passed. The exact999700-byte GDS SHA256244992e91350d3bcac15fd58c48cc5249ee615ffc21f30f539a0cbb6b42fc347 passed:
- Full560-category DRC:0 markers.
- Deep and flat strict native LVS:500 devices,25 ports;124npn13g2,50sg13_lv_nmos,98rppd,7cap_cmim,221ptap1.
- All13 actual reference/geometry fault injections rejected as expected.
- Qualified process supervision, complete command streams, no primary error, no remaining live process and stopped heartbeat.
Physical result.json82676bytes SHA25652356958a13e7690f7d4b3f3580380b36106c7c713adeb18d41e5e6786dcab9a.

Full133-file proof204093821b1edcba161625e9074291755157d69f (3329349bytes,receipt1e8bf4c872638102fbeec192dd38613b4bdd8141a91cd0a00cf1fbe3cf103fa5) is imported under docs/evidence/wire-physical-terminal-41335306847. All39 protected source files were copied server-side by Git blob identity; no native payload was acquired locally.
Permanent release430763614/tag cloud-results-41335306847-1-cdr-wire-shortcuts-physical:
complete-output-index.json asset699119950,20769bytes,SHA2560d1e51baea9ffbbb699fc131d3406d443178aa17bb6e861873e1c23979209226;
native-physical.tar.gz asset699119951,5970038bytes,SHA256b4b708083f11f67e57de36f30518f1e2a1782659ce8019e4b4c6ce5691723496.
The archive contains134 fully indexed members. Derived artifact13094398187,351397bytes,SHA25663dd05e83a7da9c9b43024a9ebc1720114a706eaeadd8e448b5e665bce5db5ef.

Next actual native view run41336588343/source2e42588a8ae03d6ef460c5cecf16943d715c5147,branch codex/cdr-wire-shortcuts-canonical,release430771584/tag cloud-results-41336588343-1-cdr-wire-shortcuts-canonical has been dispatched.39 source controls passed; native-canonical is live. Do not dispatch a duplicate after an observation timeout.
Source scripts/cloud_cdr_wire_shortcuts_canonical.py and54-file pins scripts/cdr-wire-shortcuts-canonical-pins.json authenticate old3091-member RC capsule and all134 new physical members on GitHub. All binding/inputs reference children are selected from original RC. The current physical layout and flatLVS files are byte-copied into native/ aliases; original records remain immutable.
Pure frozen projection/planes/recovery/identity definitions come from394b6e2c5e6fffbbc1a8d92fbdf41bd5d3a93356; historical hardcoded candidate authority is not used. New admission names the actual244992...GDS and successful physical run. The four original probe/location/anchor workers execute on the new view.
Qualification requires all160 planes/19 faults,16 independent leaf placements/5 controls, full500-device/1446-terminal/25-port/978-anchor identity, native witness faults and every actual conductor partition on all13 layers. Each layer must equal its old owned material plus exactly the six declared600nm M2 shortcut regions and existing landing boxes. New via count remains0. Per-target added area must match the authenticated generation record. No RC or wave result is inferred from this identity check.
Each of eight native phases uses original1200-second supervisor bounds and original2GiB free/10GiB RSS guards. Job180minutes. Publish all actual outputs to native-canonical.tar.gz/complete-output-index.json; derived artifacts named wire-canonical-derived-RUN.

NEXT: inspect run41336588343. Preserve exact current source, full logs, controls, derived outputs and complete permanent native index. If the canonical view genuinely qualifies, use its actual view/candidate78-member inventory and native graph/anchor records for new RC. The prior numerical methods at9bf12d1e496f7d9192582175ab2fa714e3e8d41b are scripts/cdr_via2_m3_fresh_rc_core.py, cdr_via2_m3_fresh_rc_native.py and cloud_cdr_via2_m3_fresh_rc.py. Their immutable numerical definitions/raw graph13-corruption checks/intrinsic MIM/direct+reverse order composition can be reused, but original producer/current_view pins and old execution admission cannot be relabelled. Build current-source runtime acquisition/host binding to the new actual canonical view and preserve original500/978/25 device/anchor/port gates. Native flow prepares actual bindings, extracts wireRC, audits all branch/capacitor ownership, performs both precise MIM orders, then composes full compact device+wire model. Only then rerun unchanged loaded-wave/device/phase/V-I acceptance.
Original nominal RC limitations remain; a numerical qualification is not foundry RC-corner or fullPEX signoff. Width2/Nx8 screening was not regenerated as accepted geometry and must not be silently combined.

Mainchip full64 run41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64 remains live at this snapshot. After completion, qualify actual restored classes/pins/PG/DRC/antenna and matching154480-instance diode-inclusive netlist, freshRC and unchanged three-corner setup/hold. No duplicate router is authorized solely by observation timeout.
Full serial Gen3 x4 PHY, final chip routing acceptance and final timing remain open. All CAD/native acquisition/analysis remains on GitHub; local project/temp are empty and local CAD processes absent. Monitor inventory700 remains read-only,automatic_native_dispatch:false; prior monitor HTTP502 is not marked resolved.

## Previous checkpoint v258: native full physical verification launched on cloud

The actual six-shortcut GDS remains the 999700-byte candidate SHA256 244992e91350d3bcac15fd58c48cc5249ee615ffc21f30f539a0cbb6b42fc347 generated by run41333497715/source2f7f6e673e0bac5052d82e7ffd7073b9685f962f. No physical or electrical acceptance is claimed yet.

New physical verification source: 50cb5767faef80336161ab7fa40de7d99dbf6243 on codex/cdr-wire-shortcuts-physical.
Actual dispatched run41335306847, independent release430763614/tag cloud-results-41335306847-1-cdr-wire-shortcuts-physical.
Source-controls passed; native-physical started. Consult the live API before assuming any terminal result or dispatching again.
Source manifest scripts/cdr-wire-shortcuts-physical-pins.json authenticates39 source/config files, including original seven SPICE libraries by both SHA256 and Git blob SHA1.
The candidate and original3091-member capsule are only acquired on GitHub. Fresh result.json binds the new GDS, unchanged original schematic/LEF, original25ports and actual current inputs.
The frozen checker bytes remain3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66: full560-category DRC, deep and flat500-device LVS and all13 fault controls.
The original pinned AppImage,197-file PDK runtime, scoped AppArmor policy and qualified process-group supervisor are reused. All actual command streams, memory guards and cleanup are preserved.
Native checker bound7200seconds; hosted job180minutes. Both success and failure outputs publish to native-physical.tar.gz plus complete-output-index.json. Fetch only derived artifact wire-physical-derived-41335306847 locally in RAM; native archives stay cloud-only.

Prior run41335113333/source9ec20efdfcbf55b6e7f0d3020bb2a275c95ad084/release430762483 failed BEFORE native execution. The source gate compared a bytes/SHA256 dictionary with enriched SPICE pin rows that also contained git_blob_sha1. All seven actual source Git blobs and sizes independently matched the expected metadata. The fix checks bytes/SHA256 and the additional Git blob identity separately; no source, device or acceptance criterion was weakened. Full original preflight failure/log/API receipts are preserved under docs/evidence/wire-physical-terminal-41335113333.

NEXT: read run41335306847. If complete, preserve its actual source/control/native-derived/full-log proof and authenticate its permanent complete-output index. A failed DRC/LVS must be repaired as an actual new candidate. After a genuine pass, create canonical native view and fresh RC for this exact GDS, then rerun unchanged loaded-wave/device/phase/V-I acceptance. Do not reuse original RC as the new shortcut result.
Mainchip run41323446729 remains independently tracked. After actual full64 route completion, qualify restored classes, physical pin connectivity, PG, DRC/antenna, matching154480-instance diode-inclusive netlist, fresh RC and unchanged three-corner setup/hold checks. Do not restart either job solely because an observation timed out.

All CAD/native acquisition/analysis remains on GitHub. Local workspace and project temporary directories are verified empty; no local CAD process runs. Local coordination uses only source/API/derived text in RAM. Unrelated personal files and application credentials are not deleted.
Full serial Gen3 x4 PHY, final mainchip routing acceptance and final timing remain open. The eight-hour monitor remains read-only with automatic_native_dispatch:false; prior HTTP502 monitor-health observation is not silently converted into success.

## Previous checkpoint v257: six real physical divider shortcuts generated on cloud

Actual native run41333497715/source2f7f6e673e0bac5052d82e7ffd7073b9685f962f succeeded after31 controls (19 unchanged wire/coordinate plus12 geometry tests). It authenticated all3091 original RC capsule members, loaded actual GDS42ed5bcd567518786b718248947771172e9f5cc419d0aaa8fc8c49d8cfa4e876 and wire L2N57abb9fe69e4fcc57a18ee8a61fbcfa04475ad3331581062fde41f2d6aa6fe3b, matched complete M1/Via1/M2/Via2 layer unions, and generated all six A_p,A_n,C_p,C_n,D_p,D_n shortcuts. No target remains unrouted within this six-net candidate.

Actual new native file: native/nssoc_cdr_pd500_wire_shortcuts.gds in archive root wire-shortcuts;999700bytes;SHA256244992e91350d3bcac15fd58c48cc5249ee615ffc21f30f539a0cbb6b42fc347.
Permanent release430752170/tag cloud-results-41333497715-1-cdr-wire-shortcuts:
- complete-output-index.json asset699061027,1894bytes,SHA256f0258c68ee4bf6608e5b926f420cdd259a8119f7f5ef0e78a111be7dd903f3f3.
- native-candidate.tar.gz asset699061028,348712bytes,SHA2560dec57eeac173fc9c9ec0ca76d1a6cd218e265605c8e143188d69bac71ba7e17.
The native archive was never acquired locally. Derived artifact13094222549,164182bytes,SHA256a5ae083a4e41009d348b7fddc440efd4e57cc2c72b870e44912404d09e598de9.

Only0.6um-wide Metal2 shortcuts were added. Each endpoint reused its actual original four-Via1 landing, after proving same-net M1/M2 ownership and50nm lower/upper enclosure of each190nm square cut. Existing Via2 cuts and all original vias remain. There are zero new Via1 shapes. All original device/M1 geometry remains unchanged. The serialized GDS contains exactly the declared layer-union additions; deleting inserted shapes restores all original layer material. Foreign-M2 clearance605nm, foreign-via avoidance, same-net ownership, continuous route and existing die boundary checks all passed. These static guards are NOT the full PDK DRC/LVS or electrical acceptance.

All six selected routes use the first Manhattan path:
A_p [1024100,2059690]->[1084100,2059690]->[1084100,2055530];
A_n [1204100,2059690]->[1264100,2059690]->[1264100,2055530];
C_p [1024100,2835580]->[1084100,2835580]->[1084100,2831420];
C_n [1204100,2835580]->[1264100,2835580]->[1264100,2831420];
D_p [1024100,2587350]->[1084100,2587350]->[1084100,2580790];
D_n [1204100,2587350]->[1264100,2587350]->[1264100,2580790].
Coordinates are original1nm GDS DBU. New M2 area38344150DBU2 per A/C route and39784150DBU2 per D route; via added area0.

Preserved actual unsuccessful predecessors:
41332615153/source7374d2201b6541f67c23e6f56dda8b0b78325eb1/release430746317 passed27 controls but selected a nonexistent mim/precise/wire/native05/wires.l2n path; no generation. Correct canonical input is binding/inputs/wire/native05/wires.l2n (and matching wires.gds). New source checks selected paths against pinned complete inventory before acquisition.
41332859047/source9fb67f1332fbc2e17e51d182461a176b40669e6e/release430747892 passed27 controls and native layer-union checks but found no new via sites in a small search; no candidate.
41333160166/source60464d2610e69ffbd040c35ee4d5abef7778487f/release430750188 passed29 controls and preserved every10um bounded access refusal. It revealed that existing four-via stacks already occupy the1.730um x0.300um M1 /1.730um x0.290um M2 terminals. The final source reuses these existing qualified same-net landings rather than duplicating cuts. No clearance or electrical threshold was relaxed.
All four complete source/log/result proofs are imported under docs/evidence/wire-shortcuts-terminal-RUN. Initial failures remain genuine failures; only the final generation succeeded.

NEXT REQUIRED PHYSICAL ACTION: authenticate the new candidate archive on GitHub; run original full560-category DRC, deep and flat500-device transistor LVS and13 actual fault controls on this exact new GDS. Preserve original schematic/ports and bind fresh candidate metadata/output hashes; do not relabel the previous GDS result.json as a new generation. Existing validated physical pipeline is scripts/cloud_cdr_via2_m3_physical_recheck.py at9bf12d1e496f7d9192582175ab2fa714e3e8d41b: derive_physical uses cloud_cdr500_resistor_v59_physical.physical_source(original,'cd_shunt') with four exact substitutions; checker SHA3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66. Original source hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py checks actual layout result inputs/outputs, immutable PDK revision5e6d592e4002946a4616f798c357f0f3c06cf3b6, all560categories, deep/flat primitive counts124HBT/50MOS/98R/7MIM/221ptap and13 fault controls. AppImage3.0.5 SHA d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466, pinned frozen runtime and scoped AppArmor launcher must be restored on cloud using actual current-source admission, not old producer authority.
Then create canonical native view/new wire extraction and fresh RC for the exact new GDS, run unchanged loaded-wave/device/phase/V-I gates. The new RC/electrical improvement is NOT yet measured. Width2/Nx8 device-geometry trials are still not regenerated accepted layouts. Supply-path repair and complete closed-loop/serialPHY remain open.

Mainchip full64 run41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64 remains active; do not restart or duplicate. After terminal publication qualify actual pins/classes/native connectivity, DRC/antenna and new diode-inclusive154480-instance netlist/RC/STA.

All CAD/native acquisition/analysis remains on GitHub; local source/API-derived coordination RAM only. Workspace and project temp remain empty. Eight-hour monitor inventory now697, read-only automatic_native_dispatch:false. Prior live monitor HTTP502 remains recorded. Full serial PHY, mainchip physical closure and final setup/hold remain unachieved.

## Previous checkpoint v256: original extracted wire bottlenecks and native coordinates mapped

Actual cloud run41331408334/source352b68e4d6a0f6fabbb18b850fff264e24fa0121 passed14 controls and mapped eleven physical-anchor pairs on the original RC graph. Its first coordinate reader handled EXT node records but omitted rnode records; most internal coordinate references were empty. Preserve this limitation and do not treat that first pass as complete geometry mapping. Proof0a1833238c5884607e6e2a703db8d0322b005886 at docs/evidence/wire-path-map-terminal-41331408334 contains all17 files (receipt3234ec6216d594cd6d2a5cf7605991c020df158516b141da3588da119a855e62).

Successor run41331683449/sourcef09bea650a2180b14efa651f3d648f9fdc3ba77e passed19 controls, including five additional coordinate parsing/refusal checks, and authenticated all3091 original native capsule members on GitHub. All24360 wire resistor cards match the original composed model through its exact node map. Every ranked edge endpoint now has actual rnode coordinates. Rnode numeric type is deliberately not interpreted as a metal. All original numerical calculations, original physical anchors and original source archive remain unchanged. Proof9676c2b87b2fcfc32a6e5981e78827883827506f at docs/evidence/wire-path-map-terminal-41331683449 contains17 files (receipt1d63cbd22390592f5be549d1c97012e88bb24cd76357f0f6c6fc28d77b01964e).

Measured effective resistance on original passive wire network:
- A series output T227_rppd_2 to shunt top T228_rppd_1:54.24519999999601ohm.
- A series output to buffer base T123_B:67.84909999998533ohm.
- A shunt top to buffer base:72.99409999998234ohm.
- C series output to shunt top:54.24519999999601ohm.
- D series output to shunt top:54.06919999999009ohm.
- AVDD to T124_C:42.62048764263007ohm.
- AVSS to T126_E/T129_E:21.13319100251308/21.18774570249786ohm.
- AVSS to shunt228/235/239:22.131607769626264/22.31409945376873/22.186162469739923ohm.

Important original edge identities:
A path R13592=24.5501ohm T273_mim_btm.n1--T227_rppd_2;
R13591=25.5151ohm T273_mim_btm.n2--T228_rppd_1;
R13590=4.18ohm between those internal nodes;
R13589=43.299ohm T123_B--T273_mim_btm.n1.
AVDD R18797=33.4312ohm P_avdd.n1103--T124_C and R18796=8.46587ohm P_avdd.n1102--P_avdd.n1103.
Ground126 R21114=13.5088ohm P_avss.n1959--T126_E and R21110=6.16703ohm P_avss.n1956--P_avss.n1960.
These are electrical network sensitivities to one-ampere DC test injections, not operating-current estimates, AC transfer, physical resistor footprints, proven sole causation or PEX signoff. Kirchhoff residual and energy conservation passed. Original limits/acceptance remain unchanged.

Native coordinates are supplied with scale1000/1/0.5; coordinate values are in centimicrons after applying lscale. GDS uses0.001um DBU. Actual terminal coordinates match for A series/shunt/base and supply124; ground126 retains native -2nm y offset, not silently normalized. For A, original physical anchors T227_rppd_2=[1024100,2059690],T228_rppd_1=[1084100,2055530],T123_B=[1084525,2305300]DBU, native cluster139/component66. Native rnodes T273_mim_btm.n1=[204120,439962] and n2=[215520,439962] in EXT coordinates. Full eleven-pair report retains all endpoint coordinate records and unit-injection energy contributions.

Next PHY action: on GitHub acquire the exact original GDS and wire L2N from original RC archive41251732540/release430243359 using scripts/cdr-wire-path-map-inputs.json atf09bea650a2180b14efa651f3d648f9fdc3ba77e. The native members include binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds and mim/precise/wire/native05/wires.l2n (plus matching wires.gds). Map actual owned conductor shapes, identify legal direct or wider signal/supply access and generate a reversible physical candidate with foreign-metal/via clearance checks. Frozen scripts/cdr_current_via2_m3_access_candidate.py at9bf12d1e496f7d9192582175ab2fa714e3e8d41b demonstrates authentic LayoutToNetlist layer/owned-net/GDS-union checks; its old eight-drain targets and authority cannot be reused as new geometry. Then full DRC/LVS, fresh RC and loaded-wave validation. Width2/Nx8 electrical device-geometry trials are not regenerated accepted layouts; do not pretend this wire-only diagnosis closes that gap. No arbitrary R scaling or gate weakening.

Mainchip full64 run41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64 is still active; use existing handle, no duplicate dispatch. Its terminal results require actual-pin/class restoration/connectivity qualification, DRC/antenna, matching154480-instance netlist, fresh RC and unchanged final STA.

All work remains cloud-only. Local workspace/task temp empty; no local CAD or native payload acquisition. Eight-hour monitor read-only inventory now693; prior HTTP502 live monitor failure remains recorded. Full serial PHY, physical routing closure and final setup/hold remain open.

## Previous checkpoint v255: three native physical path and supply diagnoses completed

Cloud run41329721970/source11960a3bf126617857f2afda3686410664ff5764 passed71 controls (62 original and9 sign-settling controls) and all three isolated case analyses: width2, width8, buffer_drive. Each authenticated its original native archive on GitHub (129/129/124 members) and independently reproduced all six original data, phase, device and V/I metrics before reporting physical node voltages. All three original data gates remain false. Width2 remains device-safe; width8 and buffer_drive remain rejected. This is diagnosis, not a new simulation or accepted circuit/layout.

Complete60-file proof c084b7f31a004473bb62c7c478aba86b6ac8d6e1 is imported under docs/evidence/physical-path-diagnostics-terminal-41329721970; receipt SHA256 be10edf4e74e940f8a526fb2ddf84580f4805d537103cd3239177c33ff7e7553. Initial run41329263955 failed source parsing before native acquisition because of missing whitespace in fn.__code__ is value.__code__. Its source/run/jobs/log/receipt are preserved. Successor fixed only that syntax and passed all71 controls.

Actual width2 sampled measurement-window common-mode means along A: sampler2.100638V, series input2.034841V, series output1.723213V, shunt top1.613528V, buffer base1.673503V, buffer collector1.836408V, first downstream receiver base1.870649V. Same-net physical terminal identity is verified. Actual supply terminal xpd.w_t124_c has mean avdd drop0.351546V; tail126/129 ground rises0.113409/0.116035V. Shunt228/235/239 ground rises0.112550/0.106404/0.112662V. These are sampled waveform voltage measurements, not inferred DC currents or power signoff.

Width8 shunt228/235/239 ground rises increase to0.220667/0.199536/0.210432V. Nx8 buffer drive retains A series-output/shunt-top means1.722627/1.613000V and supply124 drop0.352617V. At0.6UI all255 A source samples are valid in width2, while buffer/receiver wrong-sign counts are111/129; Nx8 buffer drive worsens buffer wrong signs to125. Full path reports preserve A/C/D_X/D_Y, all receiver identities,138 supply terminals per case, unchanged sample windows and gates. Sign-settling is an additional diagnostic, never a substitute for100mV acceptance.

Next PHY work: locate the actual original500-device layout builder, GDS and fresh-RC producer41251732540 via scripts/cdr-via2-m3-loaded-producer-inputs.json at2a62d651d415fba8db3c5b758d1b66c05cde3a38 (not present at root105fe). Map measured high-current signal and supply terminal drops to authentic interconnect geometry; repair legal conductors/PDN and regenerate fresh physical extraction on cloud before evaluating. Large same-net and supply drops motivate this direction but do not prove a single root cause. Do not blindly repeat tail sizing, arbitrarily scale extracted R, widen divider devices, weaken limits or relabel diagnostic success as PHY acceptance.

Existing full64 native route41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64/release430685443 remains the only active route. Observe it without duplicate dispatch; after terminal preservation qualify actual new pins/connectivity/original route classes, DRC/antenna, matching154480-instance diode-inclusive netlist, fresh RC and unchanged three-corner setup/hold.

All CAD, simulation, native acquisition and numerical/geometric analysis remain on GitHub; local coordination uses source/API-derived text in RAM only. Workspace and task temp verified empty. Monitor remains every8hours, read-only, automatic_native_dispatch:false, now inventories691 runs; prior live monitor HTTP502 remains unresolved evidence, not healthy qualification. Full serial PHY, physical routing closure and final timing remain open.

## Previous checkpoint v254: buffer drive experiment rejected; full raw diagnosis completed

Actual native run41325168813/source43fd3f71a289fef004aeb41cd2d0972d81f76f41 finished with electrical rejection, not timeout. Engine return0,1088.429415022s, no diagnostics. All six original data checks failed; device limits failed. Phase40.0143933667mV passes30mV and loaded V/I passes. Native archive and failures are durably published in release430697288/tag cloud-results-41325168813-1-cdr-sampler-load. Complete71-file derived/native-publication proof990d448dd8f502691046b7b6dbb4ae2621e87375 is imported under docs/evidence/buffer-drive-native-terminal-41325168813 (receipt a3295ba5cfabd0a1791f7d77789e4ad9ec7f97426b7217502b89eae6dab41ff5). No native archive was acquired locally.

Cloud full-wave run41327211667/source9c5843a973b5a0175d137af0780ae1b5aca46968 on codex/cdr-buffer-wave-analysis PASSED62 reader controls, authenticated all124 native archive members and independently reproduced every original six-data/phase/device/V-I measurement. It is a successful diagnosis of a failed circuit. Complete25-file proof fc2d712203a350ba8a68d7c650290c771a597a29 is imported under docs/evidence/buffer-drive-wave-terminal-41327211667 (receipt76751db63c22a55ec771dae301222f5de480be5e76b245b40cdb12874752e70f).

Nine actual HBT minimum-active-VCE failures against unchanged0.4V:
129=0.39647300049766077V;
137=0.29473418798359907V;
139=0.2964981295741759V;
142=0.27748090769744127V;
143=0.27614763950230437V;
155=0.34184134412719663V;
157=0.3445799462464897V;
160=0.33242284308074294V;
161=0.32964571373351964V.
These are C-buffer tail129 and all eight XOR selectors. The prior width2 parent passed device limits. Increasing tail Nx4 to8 and halving collector load length therefore cannot be adopted as a fix.

Compared with width2 parent41306148937, A/B below100mV sample counts stay97/25; C wrong signs30 to31 and D stays33. X wrong signs418 to383, Y6 to12. All six data gates remain false. At0.6UI with all255 A source samples valid, A-divider wrong signs remain0 while A-buffer wrong signs worsen111 to125. New A/C mean tail currents are3.582214/3.566502mA, compared with2.529654/2.513732mA for width2. A/C tail minimum-active-VCE becomes0.483172/0.396473V. Do not infer current doubles merely because Nx doubles; measured common-mode/headroom/loading must govern the next design.

Next PHY work: use the actual physical driver/consumer snapshots and sampler worst-bit windows to address the upstream A/B margin/settling failures, C/D bit errors, and divider/buffer/XOR common-mode and headroom. Preserve the width2 device-safe baseline and failed Nx8 trial. Do not just repeat stronger drive or relax thresholds. Any new geometry remains exploratory until regenerated legal layout, fresh extracted RC, corners and full closed-loop/link proof. Existing current evidence is NOT a full serial PHY or chip timing result.

The reader now accepts a passing device flag only if its recomputed decision agrees, rather than hardcoding failure. Data_passed is independently enforced as ALL six data checks AND the original phase gate. It additionally reproduces loaded V/I against the original frozen producer statements;62 controls include exact original VI comparison on four fixtures and invalid combined-data flags. All original electrical limits and accepted=false/full-PHY scope are retained.

Mainchip full64 native run41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64 remains active; observe existing job/release430685443, never duplicate it. After terminal publication authenticate outputs on cloud, restore original route classes on actual new pins, requalify native connectivity/GDS, measure DRC/antenna, export matching diode-inclusive netlist and extract fresh RC for unchanged three-corner setup/hold. Old candidate/142-net pin proof and old netlist/SPEF are not new-route evidence.

All CAD/native acquisition/analysis stays on GitHub. Local workspace/task temp remain empty, source/API-derived text coordination uses RAM only. Eight-hour monitor remains read-only and inventories689 runs. Full serial PHY, physical routing closure and final timing remain open.

## Previous checkpoint v253: A/C buffer drive candidate qualified and native screening dispatched

Width2 diagnosis showed source-valid A divider samples arriving before the buffered output, with A/C tail minimum active VCE of0.573442/0.486867V against0.4V. Width2 native41306148937 passed device/VI and37.080mV phase but failed all six data gates. The new source43fd3f71a289fef004aeb41cd2d0972d81f76f41 on codex/cdr-buffer-drive changes exactly two tail HBTs126/129 from Nx4 to8 and four collector loads232/233/243/244 from length1.8um to0.9um, retaining width8um. All12 width2 dividers,200MOS units, physical terminals, remaining geometry and original measurement/current/data/phase predicates are retained. Reversing all six edits restores exact parent bytes and descriptors. Both the500-device binder and650-device native model receive identical edits and actual binding exposes Nx8 for both tails. This is a native electrical experiment, not layout acceptance.

Independent controls41325031300 PASSED:67 new refusal controls,75 inherited width controls and all earlier suites. Complete45-file proof8725ab4120e5999dba12b776a5d3fc2115fe296c is imported under docs/evidence/buffer-drive-controls-terminal-41325031300. Receipt SHA2562f3d959bd7331ade5dea063c56557dfe437699f09e4880a7cc5d0a156972cb3a.

Actual native run41325168813 was dispatched exactly once on that same source with independent controls41325031300. Empty exact-source release430697288 / cloud-results-41325168813-1-cdr-sampler-load was reserved and read back. Its own source controls passed; native job124903702846 is active. Observe the existing job; do not repeat dispatch/reservation mutations. Original ngspice/model/runtime and1200-second engine supervision are retained. The shared host publishes native archive parts, complete-output-index and parts.json into the release even for electrical failures; fallback artifacts preserve failed publication. Retained distributed RC is screening only. Any useful result requires regenerated layout/fresh PEX and full corners/closed-loop/link proof before PHY acceptance.

Actual full64 mainchip route41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64 remains live at its Execute and preserve actual full64 route step. No internal route iteration is inferred from that API observation. Preserve its existing exact-source release430685443. After terminal publication, authenticate results in the cloud, restore original classes using actual new route pins, requalify actual new connectivity/GDS correspondence and run original-class DRC/antenna. Old d526... candidate/142-net pin proof must not be relabeled. Then export matching diode-inclusive netlist, extract fresh RC and enforce unchanged multi-corner setup/hold. Last measured old candidate still has399DRC and19antenna nets/23rows.

All CAD/native acquisition/analysis remain on GitHub; local source/API-derived text coordination is RAM-only. Local workspace/project temp empty with no local CAD processes. Native payloads must not be downloaded locally even into RAM. The8-hour monitor inventories both new runs and never automatically duplicates native dispatch. Full serial PHY, mainchip physical closure and final timing remain unachieved.

## Previous checkpoint v252: actual full64 native route dispatched and running

Source ff1c0e6163e0ba1537a075d50e940fafc9332c64 on codex/mainchip-full64-native integrates the actual original64-pass router with authenticated saved-diode acquisition, original prep/guide/PG/fixed-overlay/828-net clear, owned native engine/runtime/container and permanent checkpoint publication. Independent controls41323333392 passed all11 full64 lifecycle plus12 preservation/dispatch controls,0 failures/errors/skips, and authenticated2361 original source files. Complete20-file proof063318bb2cb55c5b394a4c091dc8d8fa6ebaf20e is imported under docs/evidence/full64-native-controls-terminal-41323333392.

**Actual native run41323446729 has been dispatched exactly once.** Permanent empty exact-source release430685443/tag cloud-results-41323446729-1-mainchip-bulk-postdrt-antenna was reserved and verified. The native run repeated all source controls successfully. Latest live observation: job124898487629/native-routing in progress at Execute and preserve actual full64 route. This step includes cloud acquisition and CAD; do not infer the current internal route iteration from the Actions step alone. Poll this existing run, not a replacement.

The native phase order is bootstrap,guide-overlay,guide-reload-audit,power-contact-audit,make-overlay,fixed-import,fixed-audit,clear,route. The source executes the exact original64-pass Tcl; it is a fresh same-seed trial, not a resumed internal iteration. Native report is bulk-postdrt-full64-inner-result.json; successful route status is COMPLETE_FULL64_NATIVE_ROUTE_CHECKPOINT. Route output pins are in bulk-postdrt-antenna/full-route-stage.json and work/bulk-postdrt-antenna/routed-fixed.odb/.def plus route-partial.odb/.def. Output preservation always runs. Host output is full64-native-evidence; fallback artifact contains the run-owned out directory. Do not download native archives locally.

The checkpoint intentionally retains temporary fixed classes. It is NOT a restored candidate, physical/timing/full-PHY acceptance. The next stage must restore classes using the actual new routed-fixed pins and the scoped restoration algorithm, then measure fresh native graphs and requalify relevant GDS pin correspondence. Old core.CANDIDATE d526... and exact142 failed-net/1300-pin/77-master-pin qualification are bound to the old8-pass candidate and MUST NOT be relabeled as new-route proof. Core.audit accepts an explicit expected tuple, but production values must come from authenticated new readout, not from making tests pass. No broad acceptance is granted by route completion.

Host preservation is now implemented and tested in mainchip_full64_output_preservation.py: exact four Tcl programs require capsule pins and64KiB cap; the two clock-gate DEF files are native-only and require matching capsule pins; host-progress is a regular JSON object capped16MiB and exact-copy verified. The original three host failures were reproduced before confirming the correction. All unexpected-file/symlink/unpublished-large/output-overwrite/hash-drift refusals remain. This correction is integrated into this full64 host.

All source and evidence are in GitHub, local workspace/task temp empty and no local CAD processes. The monitor tracks this run every8 hours and never automatically duplicates native dispatch. New source and reservation/dispatch recipes are already executed; never replay creation mutations. Last accepted physical evidence remains399 DRC/19 antenna nets/23 rows, qualified connectivity828/PG2702/protected1691 from the old candidate. Full serial PHY and final matching-netlist RC/STA remain open.
## Previous checkpoint v251: classification and source-only full64 qualification

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
