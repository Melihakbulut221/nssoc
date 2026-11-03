# Cloud continuation — checkpoint v349

Updated: 2026-11-03T20:17:25.926481+00:00

## Actual gate-metal repair driven by full DRC failure

Physical run41707025516/sourceadbb69b069592dc87400988cc6ea995032c9a086 FAILED. Both deep and flat650-device LVS passed. All560 DRC categories executed, with392 markers: M1.a8, M1.b8, M1.e8, M2.b368. Full failure, every derived log/report and immutable native release433147774 are preserved. No failure was waived.

Generation41709100324/source101974bb123d67efb713785ca1c7088939d0c2b2 SUCCEEDED (release433160175). Original M1 landing geometry is retained outside the proven gate corridor instead of deleting entire old via pads, which had produced narrow edge fragments. New M2 landing notches are closed only within each proven physical wire net near the actual additions, with foreign-net spacing guards. Actual before/after material around all M1.a/M1.e markers was exported.

Those material windows exposed eight original4um-tall wide S/D junction plates facing the160nm gate strap at180nm. M1.e requires220nm spacing when metal width exceeds300nm and parallel run exceeds1um. Generation41709759119/source087721d42112ed108543d2da053ee6d0e2f20a9c SUCCEEDED (release433163953) after cutting220nm slots inside those exact same-net plates. The complete160nm contact rail and BOTH160nm bridge necks remain. Entire slot ownership is probed against actual native S/D and physical wire net; all original Cont and current Via1 remain covered. This alters actual material, not the rule. New slot resistance must be included in freshRC.

Actual new GDS:1624572bytes/SHA256c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c. All original device/nonconductor geometry,650-device independent reference, hierarchy and annotations remain preserved. Independent full physical41710162510/sourceb3d9d1d284b1e8464d5359e7e21991aef21a787c/release433166461 consumes this exact candidate. The checker SHA30c4586b86167ad775af14b5568152820a802037150bdfd282e7ba0843a1555f is unchanged:560 categories, deep/flat LVS and13 intentional controls, plus independent current Via1 coverage. Consult its actual snapshot and complete report below, never infer physical acceptance from generation.

Mainchip full64 route41699812301/source9430a57873e78d3c283b531da8e8e74da416f297 remains the same authoritative trial. Full route and final setup/hold are not yet proven. Full serialPHY is also unclosed: regenerate bindings and freshRC on the accepted current material, model all gate/poly/contact resistance and compact-model overlap, then run the original complete loaded electrical and serial link qualification. No source or sub-block test substitutes for these product requirements.

All computation and native payloads remain in GitHub; local workspace remains empty. Read-only8-hour monitor is preserved.


## Confirmed new physical acceptance, limited to this exact650-device macro
Run41710162510 completed its native physical verification successfully. Full report status PASS_NATIVE_PDK_CDR_PD650_DRC_LVS_AND_FAULT_CONTROLS; all560 DRC categories, zero markers; deep and flat650 LVS both PASS; all13 original intentional faults rejected. Actual DRC report SHA25665323bd352a208ac709ce75e782faf3b6dd9291cce44ddb14ee15e01d5e919b0. Derived artifact13267549262 contains the complete report. This closes the392-marker local gate-metal DRC issue with real geometry and unchanged checker. It does NOT close full serialPHY, freshRC, mainchip routing or final timing.


## Observed complete physical results
[
  {
    "conclusion": "failure",
    "drc": {
      "categories": {
        "'M1.a'": 8,
        "'M1.b'": 8,
        "'M1.e'": 8,
        "'M2.b'": 368
      },
      "category_count": 560,
      "log_sha256": "21df57caa6cc5c81a0c81da1a5437f960d1e45059ebbf0a050d9ecda4eca809d",
      "markers": 392,
      "process_returncode": 0,
      "report_sha256": "d64633d3f64220a215d350042d3867f3cff8da70c841d8c8ec21fabc3619ecb0",
      "status": "FAIL"
    },
    "phases": {
      "drc": "FAIL",
      "gain_gate_disconnected": "REJECTED_EXPECTED_FAULT",
      "gain_tail_width": "REJECTED_EXPECTED_FAULT",
      "lvs": "PASS",
      "lvs_flat": "PASS",
      "missing_gain_hbt": "REJECTED_EXPECTED_FAULT",
      "missing_hbt": "REJECTED_EXPECTED_FAULT",
      "offgrid": "NOT_RUN_FAILED_PREREQUISITE",
      "old_data_header_length": "REJECTED_EXPECTED_FAULT",
      "old_retime_width": "REJECTED_EXPECTED_FAULT",
      "old_sampler_input_width": "REJECTED_EXPECTED_FAULT",
      "q_open": "REJECTED_EXPECTED_FAULT",
      "rail_short": "REJECTED_EXPECTED_FAULT",
      "v59_old_length": "REJECTED_EXPECTED_FAULT",
      "wrong_finger_count": "REJECTED_EXPECTED_FAULT",
      "wrong_follower_polarity": "REJECTED_EXPECTED_FAULT"
    },
    "run": 41707025516,
    "status": "FAIL"
  },
  {
    "conclusion": "success",
    "drc": {
      "categories": {},
      "category_count": 560,
      "log_sha256": "3d2ee5d840eeb362bd626e7e3407724d61d9e33c630ea68b5d738c764daa1214",
      "markers": 0,
      "process_returncode": 0,
      "report_sha256": "65323bd352a208ac709ce75e782faf3b6dd9291cce44ddb14ee15e01d5e919b0",
      "status": "PASS"
    },
    "phases": {
      "drc": "PASS",
      "gain_gate_disconnected": "REJECTED_EXPECTED_FAULT",
      "gain_tail_width": "REJECTED_EXPECTED_FAULT",
      "lvs": "PASS",
      "lvs_flat": "PASS",
      "missing_gain_hbt": "REJECTED_EXPECTED_FAULT",
      "missing_hbt": "REJECTED_EXPECTED_FAULT",
      "offgrid": "REJECTED_EXPECTED_FAULT",
      "old_data_header_length": "REJECTED_EXPECTED_FAULT",
      "old_retime_width": "REJECTED_EXPECTED_FAULT",
      "old_sampler_input_width": "REJECTED_EXPECTED_FAULT",
      "q_open": "REJECTED_EXPECTED_FAULT",
      "rail_short": "REJECTED_EXPECTED_FAULT",
      "v59_old_length": "REJECTED_EXPECTED_FAULT",
      "wrong_finger_count": "REJECTED_EXPECTED_FAULT",
      "wrong_follower_polarity": "REJECTED_EXPECTED_FAULT"
    },
    "run": 41710162510,
    "status": "PASS_NATIVE_PDK_CDR_PD650_DRC_LVS_AND_FAULT_CONTROLS"
  }
]


Observed 2026-11-03T20:17:25.926481+00:00:
- 41699812301: in_progress/None
- 41707025516: completed/failure
- 41709100324: completed/success
- 41709759119: completed/success
- 41710162510: completed/success


## History and execution
Previous actual route and failure handoff:
https://github.com/Melihakbulut221/nssoc/blob/08d1adbe5ce0e56d9847e6ab10da93e7b84305da/CLOUD_RESUME.md
All earlier sources, complete reports and failed runs remain preserved.
All native CAD/geometry/runtime/electrical payloads stay cloud-only. The local
workspace is empty; source and derived-text API coordination uses RAM.
The8-hour monitor remains read-only with automatic_native_dispatch=false.
Poll existing exact handles; do not restart on observation timeouts.
Full serialPHY, completed mainchip routing and final setup/hold must all
pass real complete verification before the overall goal is complete.
