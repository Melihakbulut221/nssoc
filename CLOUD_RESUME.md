# Cloud continuation — checkpoint v351

Updated: 2026-11-03T20:54:34.467932+00:00

## Native contact-count and actual gate resistance measured

Run41716341181/source44efb7eae677d57988386398073f7c83f6145c7d on codex/cdr-mos650-gate-contact-ac SUCCEEDED, release433203305. Complete current wire producer41712243960 was authenticated in the cloud. All200 current native MOS IDs, actual W/L/AS/AD/PS/PD,50 one-ended and150 two-ended electrodes were rebuilt and matched to the fixture. The8.885um geometry has only two-ended electrodes, so there are14 actual dimension/contact/QS-RF cases plus8 canonical reference cases.

All22 separate one-transistor native executions completed with no diagnostics. Every requested NGCON and actual RG/XGW/NF/W/L was read back from the frozen native simulator. The eight explicit NGCON2 cases reproduce the untouched original models with the ORIGINAL relative1e-9/absolute1e-7 complex-impedance tolerance and identical native resistance/geometry readbacks. Original model files remain unchanged; only a separate wrapper copy exposes the six formerly fixed NGCON arguments. All stdout/stderr, readbacks, decks and complete native archives are preserved.

Measured RF RG atW8um is73.09375ohm one-ended vs52.59375ohm two-ended; atW8.89um75.51709786276714 vs52.79209786276715; atW9um75.82407407407408 vs52.824074074074076. QS RG remains4.824074074074075 to5.427083333333333ohm despite RGO/RSHG0, because native RINT is1.3025e-11. RF RGO40/RSHG3, RVPOLY0, DLSIL0, SWGEO1 and nativeXGW100nm are recorded. Complete input impedance is not the gate resistor; atW8um/two-ended/RF/1GHz its real part is74.08834477288276ohm while actualRG is52.59375ohm.

First run41715622293/sourcee5b3fd44493da81faa269798b5b43667b6d74330/release433199094 FAILED the strict equivalence gate despite zero native diagnostics and correct NGCON readbacks. Its canonical8-device and explicit14-device decks differed in matrix size; seven real-impedance samples exceeded tolerance, max4.311324346417678e-6ohm. Successor controls this numerical confound with one device per native deck; the exact original comparison tolerance is unchanged. The first complete failure and measurements remain preserved. Source-only intermediate27409f8771edc1dd82ba63fa55ca726dd010c882 was not dispatched; native RG instrumentation is in44efb7.

This resolves a model diagnostic, not physical gate/poly/contact network composition. No full PEX, complete electrical, fullserialPHY or finaltiming acceptance is claimed. Current accepted metalRC remains41713023974:28619R/18469C,1428 distinct anchors and13raw corruption controls. Actual mainchip full64 routing41699812301 is polled independently; no duplicate route was started.


## Observed native contact-model outcomes
[
  {
    "conclusion": "failure",
    "result": {
      "bytes": 1043,
      "record": {
        "electrical_accepted": false,
        "error": "explicit NGCON2 reproduces unchanged original model real_impedance_ohm",
        "error_type": "ValueError",
        "final_timing_complete": false,
        "full_pex_qualified": false,
        "full_phy_accepted": false,
        "gate_poly_RC_extracted": false,
        "mim_intrinsic_composition_qualified": false,
        "substrate_r_modeled": false,
        "traceback": "Traceback (most recent call last):\n  File \"/home/runner/work/nssoc/nssoc/scripts/cdr_mos650_gate_ac.py\", line 384, in main\n    count=characterize(models)\n          ^^^^^^^^^^^^^^^^^^^^\n  File \"/home/runner/work/nssoc/nssoc/scripts/cdr_mos650_gate_ac.py\", line 350, in characterize\n    need(math.isclose(a[key],b[key],rel_tol=1e-9,abs_tol=1e-7),\"explicit NGCON2 reproduces unchanged original model \"+key)\n  File \"/home/runner/work/nssoc/nssoc/scripts/cdr_mos650_gate_ac.py\", line 12, in need\n    if not ok:raise ValueError(msg)\n              ^^^^^^^^^^^^^^^^^^^^^\nValueError: explicit NGCON2 reproduces unchanged original model real_impedance_ohm\n"
      },
      "sha256": "e9393838234a0c7fb4aaed7e84d2ebe0b1d1475891f37ffd65794c4bfa974af5"
    },
    "run": 41715622293
  },
  {
    "conclusion": "success",
    "result": {
      "bytes": 560,
      "record": {
        "actual_mos_units": 200,
        "context": {
          "attempt": 1,
          "run": 41716341181,
          "source": "44efb7eae677d57988386398073f7c83f6145c7d"
        },
        "electrical_accepted": false,
        "final_timing_complete": false,
        "full_pex_qualified": false,
        "full_phy_accepted": false,
        "gate_poly_RC_extracted": false,
        "gate_resistance_qualified": false,
        "mim_intrinsic_composition_qualified": false,
        "status": "MEASURED_CURRENT_GATE_CONTACT_COUNT_EFFECT_REQUIRES_PHYSICAL_NETWORK_COMPOSITION",
        "substrate_r_modeled": false,
        "unique_physical_dimensions": 4
      },
      "sha256": "0f1408cfe21173f5167d98bbafb39f01bcf2903e172463da9a30c1397cdd433a"
    },
    "run": 41716341181
  }
]


Observed 2026-11-03T20:54:34.467932+00:00:
- 41699812301: in_progress/None
- 41715622293: completed/failure
- 41716341181: completed/success


## History and execution
Previous actual route and failure handoff:
https://github.com/Melihakbulut221/nssoc/blob/353d1aeb84ee6a272b4551af510815147ee80634/CLOUD_RESUME.md
All earlier sources, complete reports and failed runs remain preserved.
All native CAD/geometry/runtime/electrical payloads stay cloud-only. The local
workspace is empty; source and derived-text API coordination uses RAM.
The8-hour monitor remains read-only with automatic_native_dispatch=false.
Poll existing exact handles; do not restart on observation timeouts.
Full serialPHY, completed mainchip routing and final setup/hold must all
pass real complete verification before the overall goal is complete.
