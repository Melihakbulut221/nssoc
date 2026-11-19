# Two-driver resize fresh RC/STA result — 2026-11-19

Run: https://github.com/Melihakbulut221/nssoc/actions/runs/44528360188
Head: 0d69398e384b2e88b14cab7e025f9fc29eceeed0
Artifact: 14533133820; SHA256 40ef5c20cacb5ec9e175e20cc7022fdeda0092768253242ebef14f634334f5a4. All 138 output hashes verified.

Fresh routed ODB: 171fa1a8f80a9eff594c169519b2fc216ff12ffd7c2e4ef150964ee0af26a1bb
Fresh Verilog: 069bc8d4d21b515f790c884ee39a11e1016b4f028211656dc3a879a8a2a5d8bf
Fresh DEF: 73b5eb062c357c7f1bdb01ce22ab9a1a7e6af5f76f34d8848cd411242069119a
Unchanged SDC: f121116a72150c56126ac3d8dc4fda946e6d0040984e9264ef3d877171029de1

106664 instances; all 1408 cumulative added diodes exported without missing/duplicate/connection mismatches. 2816 diode local power terminals supported by cumulative evidence. No full PDN signoff implied.

| Nominal RC / cell corner | Setup violations | Hold violations | Setup worst slack ns | Hold worst slack ns | Slew | Fanout | Capacitance |
|---|---:|---:|---:|---:|---:|---:|---:|
| slow 1.08 V / 125 C | 0 | 0 | 0.020710545 | 0.449112760 | 472 | 211 | 52 |
| typical 1.20 V / 25 C | 0 | 0 | 7.431540926 | 0.185584775 | 0 | 211 | 54 |
| fast 1.32 V / -40 C | 0 | 0 | 10.303290956 | 0.037160609 | 0 | 211 | 60 |

Compared with run 44502914675: slow slew 480 -> 472; fanout 210 -> 211 in every corner; capacitance unchanged. This improvement is not electrical closure. Next step is authenticated pin-level comparison, including the added fanout violation, before another ECO. Clock remains 20 ns / 50 MHz with 5% derating.

Nominal RC only. Qualified RC min/max, annotation acceptance, full SRAM characterization and full-chip timing remain open. The existing hierarchical comparison script uses the historical 104885-instance core and must be updated with current core views; it does not validate this ECO. Package/PCB/devices remain unspecified. Foundry DRC/LVS and manufacturing approval remain unproven.
