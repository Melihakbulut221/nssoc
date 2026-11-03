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
