# Antenna-clean spacing ECO timing result — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44482078997 succeeded at `85c2c5b0c18f83bb8ea7a722c29956b35f9996cf`, attempt 1. Artifact 14508759821 SHA256 `72228851b81ed0d082ef3342a9fefa037f4cb07507f4fef5d43f8de5d77730bd`; all 136 output hashes verified.

Fresh nominal RC/STA uses ODB `a185d1494ffb265a9d07a08a4175704602ade02cf974ee8f9efbb923d22d098e`. Fresh Verilog SHA256 `5132825e120f21ec7abd1dd216a5b0d07bfbd3835e7e81066b8dc2dd488f9a07`, DEF `978800477445f5f785595411d8f89861b841ea229ce5fa8ea921e42876649dd6`. SDC remains `f121116a72150c56126ac3d8dc4fda946e6d0040984e9264ef3d877171029de1` (20 ns, existing derating unchanged). All 1398 cumulative added diodes exported with no missing, duplicate or mismatched signal connection.

| Library corner with nominal RC | Setup violations | Worst setup ns | Hold violations | Worst hold ns | Slew | Fanout | Capacitance |
|---|---:|---:|---:|---:|---:|---:|---:|
| slow 1.08 V 125 C | 0 | 0.0207727174674391 | 0 | 0.4491127596936628 | 495 | 210 | 52 |
| typical 1.20 V 25 C | 0 | 7.4315826707059545 | 0 | 0.1855848860450402 | 0 | 210 | 54 |
| fast 1.32 V -40 C | 0 | 10.303306943701365 | 0 | 0.037160608975109796 | 0 | 210 | 60 |

Setup/hold TNS and WNS remain zero. These values are from fresh corner metrics, not historical pre-route metrics bundled for provenance.

Slow slew count improved from 507 in the previous three-resize neighbor-route candidate (run 44468611583) to 495. The preserved pre-slew baseline (44459123476) had 502. This is a net count improvement, not yet a proven pin-by-pin classification. Typical/fast slew are zero. Electrical closure is incomplete: slew, fanout and capacitance failures remain; nominal slow setup margin is only about 20.8 ps.

Physical predecessor 44478446308 had native DRC 0, antenna 0 and independent signal geometry clean. That is not foundry GDS DRC or transistor LVS. All accepted/final_timing_complete/qualified_rc_minmax/annotation_qualified/manufacturing_approval flags remain false. Full-chip integration, qualified RC/Liberty and external I/O/package/board signoff remain required.

Next action: export source-verified baseline, resize and spacing corner reports for pin-level comparison and select the next electrical repair from measured connectivity and loads. Do not relax library limits or hide diode loads to make counts pass.
