## Current continuation: actual native gate AC measured; missing poly resistance identified

Native gate characterization41696724132/sourcea78102915a5a1ead89ff23331c26a149eebcaf0d/release433087144 SUCCEEDED: all4 actual unit geometries covering200MOS, bothQS/RF modes,17points per case1MHz-10GHz, nativecode0 and no diagnostics. Actual showmod confirms QS rgo/rshg0, RF swnqs5/rgo40/rshg3. Complete native gate input impedance is NOT equivalent to physical series gate resistance. At1GHz QSReZ4.83798-5.44274ohm, RFReZ71.76934-74.08834ohm at declared0.8Vgate/.6Vdrain; differences includeNQS.

The current Magic tech has pc contact entries but NO ordinary poly/allpoly sheet resistance. Recognized Rsil nres resistance is not an existing calibrated gate extraction rule. Current50single-contact physical gate groups contain long shared stems, while native RF wrapper fixesngcon2. Therefore neither ordinary QS plus metal-only RC nor blindly enablingRF mode represents the complete physical gate network. See docs/cdr-mos650-gate-ac.md and complete receipt/native readback/measurements.

NEXT PHY: establish physical poly/contact sheet model with applicability evidence; model actual distributed stem and gate paths, preserve currentflat native IDs and deduplicated geometric anchors, resolve compact overlap (including an RF/NQS zero-rgo/rshg readback experiment if used), check discretization and intrinsic/MIM/poly-coupling coverage, then original complete loaded electrical gates. No numerical threshold is relaxed and no fullPHY acceptance is implied.

MAINCHIP: follow SAME qualification41695305770/source5518d9fa75b505848e2c6a5c7d1b4a0ca9c011af/release433078096. New bounded-region engine is built; actual full-chip qualification status below determines the next action. If it succeeds, bind actual native capture/ELF/runtime into full64 execution, preserve22refusal controls and original11phases, then route once. Do not restart on observation timeout. Full routing and finalsetup/hold remain open.

All native payloads remain GitHub-only, localworkspaceempty, read-only8hour monitor unchanged.

Observed 2026-11-03T18:49:51.081996+00:00:
- 41695305770: in_progress/None
- 41696724132: completed/success


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
