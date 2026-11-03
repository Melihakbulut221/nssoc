# Cloud continuation — checkpoint v355

Updated: 2026-11-03T22:17:23.623233+00:00

## Current650 MIM-aware native RC passed in both input orders

Run41728568165/source1b40bf2db3844d6281c467022b248a2871ced6df on codex/cdr-mos650-mim-rc SUCCEEDED,release433272698. Actual current650 geometry,2046 terminals,1428 physical anchors and200 gate contacts are preserved. The seven actual MIM masks/vias were restored to the wire-only extraction view without modifying any original metal/via material. Seven bottom measurement points were rebound to verified real Metal5 access outside the intrinsic masks.

Native double-total Magic1a44bd5c... with explicit-MIM technology1439949a... produced28634 resistors,18476 wire capacitors and7 separate intrinsic MIM cards. Actual original and reversed coupling-record order produced identical complete R/C/device exports. Both runs passed full raw resistor topology/value, per-point groundC, mutual attachment/value and collapsed matrix conservation; each rejected all13 original raw wire corruptions and9 MIM source/replacement/export corruptions. Full intrinsic-to-metal nonlinear composition remains unexecuted.

First run41727960676/source884b9c7df8247b1c31f4822e7f706a98d6ed4bb8 FAILED at MIM identity comparison after native geometry and extraction completed. Two actual4800nm square devices had JSON dimension spellings4.800000000000001 and perimeter19.200000000000003; passing those directly into exact Decimal comparison was an adapter bug. Successor derives w/l/A/P from exact native integer rectangle vertices, matches both plates/bounding boxes/areas, and accepts only these two enumerated serialization artifacts. No geometry, RC values or acceptance thresholds changed. The complete failed evidence and logs are preserved.

Gate reduction41725473326 remains qualified only for nominal linear port behavior/power/noise. Next compose all actual650 nonlinear devices with these gate macros and the new MIM-aware metal network, preserving the seven native MIM attachment points. Read docs/cdr-mos650-full650-composition-next.md. Reuse old canonical non-MOS model parameters only after current native identity/geometry checks, not old wire networks. Preserve original whole-loaded stimulus and every threshold; actual serial recovered-clock operation remains required afterward.

Mainchip full64 route41699812301 remains independently monitored. Neither full serialPHY, final routed mainchip, final setup/hold nor production acceptance is closed. All native payloads remain in cloud.

## Complete observed outcomes
[
  {
    "conclusion": "failure",
    "result": {
      "bytes": 1148,
      "record": {
        "electrical_accepted": false,
        "error": "AssertionError('Wrong/duplicate native MIM geometry or terminal ownership')",
        "final_timing_complete": false,
        "full_pex_qualified": false,
        "full_phy_accepted": false,
        "gate_poly_RC_extracted": false,
        "mim_intrinsic_composition_qualified": false,
        "substrate_r_modeled": false,
        "traceback": "Traceback (most recent call last):\n  File \"/home/runner/work/nssoc/nssoc/scripts/cdr_mos650_metal_rc.py\", line 284, in main\n    mim_extract(cfg,physical)\n  File \"/home/runner/work/nssoc/nssoc/scripts/cdr_mos650_metal_rc.py\", line 247, in mim_extract\n    captured=support.check_capture((wire/\"rc03/wires.spice\").read_text(),anchors,binding)\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/home/runner/work/nssoc/nssoc/scripts/cdr_mos650_mim_support.py\", line 89, in check_capture\n    assert key in expected and key not in found,'Wrong/duplicate native MIM geometry or terminal ownership';found[key]=x[0]\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Wrong/duplicate native MIM geometry or terminal ownership\n"
      },
      "sha256": "8ddf5dc9d7e0718f791ba8fd1b63a930f7885fa78c81649adbf1a932509cc0ce"
    },
    "run": 41727960676,
    "source": "884b9c7df8247b1c31f4822e7f706a98d6ed4bb8"
  },
  {
    "conclusion": "success",
    "mim-native-integer-dimensions.json": {
      "all_parameters_derived_from_exact_native_plate_polygons": true,
      "devices": [
        {
          "bbox_dbu": [
            1143600,
            2055810,
            1147200,
            2059410
          ],
          "exact_parameters": {
            "A": "12.96",
            "P": "14.4",
            "l": "3.6",
            "m": "1.0",
            "w": "3.6"
          },
          "known_serialization_artifacts": [],
          "native_id": 423,
          "raw_parameters": {
            "A": 12.96,
            "P": 14.4,
            "l": 3.6,
            "m": 1.0,
            "w": 3.6
          }
        },
        {
          "bbox_dbu": [
            1323600,
            2055810,
            1327200,
            2059410
          ],
          "exact_parameters": {
            "A": "12.96",
            "P": "14.4",
            "l": "3.6",
            "m": "1.0",
            "w": "3.6"
          },
          "known_serialization_artifacts": [],
          "native_id": 424,
          "raw_parameters": {
            "A": 12.96,
            "P": 14.4,
            "l": 3.6,
            "m": 1.0,
            "w": 3.6
          }
        },
        {
          "bbox_dbu": [
            1143600,
            2581070,
            1148400,
            2585870
          ],
          "exact_parameters": {
            "A": "23.04",
            "P": "19.2",
            "l": "4.8",
            "m": "1.0",
            "w": "4.8"
          },
          "known_serialization_artifacts": [
            {
              "exact_from_integer_polygons": "4.8",
              "parameter": "w",
              "raw": "4.800000000000001"
            },
            {
              "exact_from_integer_polygons": "4.8",
              "parameter": "l",
              "raw": "4.800000000000001"
            },
            {
              "exact_from_integer_polygons": "19.2",
              "parameter": "P",
              "raw": "19.200000000000003"
            }
          ],
          "native_id": 425,
          "raw_parameters": {
            "A": 23.04,
            "P": 19.200000000000003,
            "l": 4.800000000000001,
            "m": 1.0,
            "w": 4.800000000000001
          }
        },
        {
          "bbox_dbu": [
            1323600,
            2581070,
            1328400,
            2585870
          ],
          "exact_parameters": {
            "A": "23.04",
            "P": "19.2",
            "l": "4.8",
            "m": "1.0",
            "w": "4.8"
          },
          "known_serialization_artifacts": [
            {
              "exact_from_integer_polygons": "4.8",
              "parameter": "w",
              "raw": "4.800000000000001"
            },
            {
              "exact_from_integer_polygons": "4.8",
              "parameter": "l",
              "raw": "4.800000000000001"
            },
            {
              "exact_from_integer_polygons": "19.2",
              "parameter": "P",
              "raw": "19.200000000000003"
            }
          ],
          "native_id": 426,
          "raw_parameters": {
            "A": 23.04,
            "P": 19.200000000000003,
            "l": 4.800000000000001,
            "m": 1.0,
            "w": 4.800000000000001
          }
        },
        {
          "bbox_dbu": [
            1143600,
            2831700,
            1147200,
            2835300
          ],
          "exact_parameters": {
            "A": "12.96",
            "P": "14.4",
            "l": "3.6",
            "m": "1.0",
            "w": "3.6"
          },
          "known_serialization_artifacts": [],
          "native_id": 427,
          "raw_parameters": {
            "A": 12.96,
            "P": 14.4,
            "l": 3.6,
            "m": 1.0,
            "w": 3.6
          }
        },
        {
          "bbox_dbu": [
            1323600,
            2831700,
            1327200,
            2835300
          ],
          "exact_parameters": {
            "A": "12.96",
            "P": "14.4",
            "l": "3.6",
            "m": "1.0",
            "w": "3.6"
          },
          "known_serialization_artifacts": [],
          "native_id": 428,
          "raw_parameters": {
            "A": 12.96,
            "P": 14.4,
            "l": 3.6,
            "m": 1.0,
            "w": 3.6
          }
        },
        {
          "bbox_dbu": [
            1743600,
            4515480,
            1783600,
            4555480
          ],
          "exact_parameters": {
            "A": "1600",
            "P": "160",
            "l": "40",
            "m": "1.0",
            "w": "40"
          },
          "known_serialization_artifacts": [],
          "native_id": 429,
          "raw_parameters": {
            "A": 1600.0,
            "P": 160.0,
            "l": 40.0,
            "m": 1.0,
            "w": 40.0
          }
        }
      ],
      "electrical_accepted": false,
      "final_timing_complete": false,
      "full_pex_qualified": false,
      "full_phy_accepted": false,
      "gate_poly_RC_extracted": false,
      "mim_intrinsic_composition_qualified": false,
      "substrate_r_modeled": false
    },
    "result": {
      "bytes": 1655,
      "record": {
        "actual_capacitors": 18476,
        "actual_resistors": 28634,
        "both_native_orders_verified": true,
        "context": {
          "attempt": 1,
          "run": 41728568165,
          "source": "1b40bf2db3844d6281c467022b248a2871ced6df"
        },
        "current_native_devices": 650,
        "current_native_terminals": 2046,
        "electrical_accepted": false,
        "final_timing_complete": false,
        "full_loaded_composition_executed": false,
        "full_pex_qualified": false,
        "full_phy_accepted": false,
        "gate_poly_RC_extracted": false,
        "intrinsic_mim_cards_separated_from_wire_C_matrix": true,
        "mim_fault_controls_per_order": 9,
        "mim_intrinsic_composition_qualified": false,
        "native_mim_devices": 7,
        "native_orders": [
          "precise",
          "precise_reversed"
        ],
        "native_rc_and_device_records_equal_in_both_orders": true,
        "order_equivalence": {
          "coupling_records": 1010,
          "non_coupling_records_unchanged": true,
          "original_order_restored": true,
          "symmetric_endpoint_value_multiset_exact": true
        },
        "physical_anchors": 1428,
        "physical_gate_contacts": 200,
        "physical_source_run": 41712243960,
        "reversal": {
          "coupling_records": 1010,
          "non_coupling_records_unchanged": true,
          "original_order_restored": true,
          "original_sha256": "536bfd09cb3268b8eaff4aa63ac1eb20b4f483ccae1b435b64203da4a484b87d",
          "reordered_sha256": "ffbb9fed4c4cd64a34f817e075367a7288b5f8c955a7268956415fefabd3f9eb",
          "reversed_enumeration": true,
          "symmetric_endpoint_value_multiset_exact": true
        },
        "status": "PASS_CURRENT650_MIM_AWARE_TWO_ORDER_RC_AND22_FAULTS_EACH_REQUIRES_FULL_COMPOSITION",
        "substrate_r_modeled": false,
        "wire_fault_controls_per_order": 13
      },
      "sha256": "1d07445dc6540c3e22b931791a0f2b2ca202de539bac9a2abe1ae9cdda92efbf"
    },
    "run": 41728568165,
    "source": "1b40bf2db3844d6281c467022b248a2871ced6df"
  }
]


Observed 2026-11-03T22:17:23.623233+00:00:
- 41699812301: in_progress/None
- 41727960676: completed/failure
- 41728568165: completed/success


## History and execution
Previous actual route and failure handoff:
https://github.com/Melihakbulut221/nssoc/blob/c1322401cfe6613ecd3c5c43aec7e7befe82a9dd/CLOUD_RESUME.md
All earlier sources, complete reports and failed runs remain preserved.
All native CAD/geometry/runtime/electrical payloads stay cloud-only. The local
workspace is empty; source and derived-text API coordination uses RAM.
The8-hour monitor remains read-only with automatic_native_dispatch=false.
Poll existing exact handles; do not restart on observation timeouts.
Full serialPHY, completed mainchip routing and final setup/hold must all
pass real complete verification before the overall goal is complete.
