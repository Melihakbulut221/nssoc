# Antenna-clean core: actual nominal RC timing remains open

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44430367099
Head 21a7f032242658c83f05f4b144fc989fc72087a0.
Artifact 14487156680 SHA256 f1f945a711c4b1071d03030cacf2be01d9b16da224b29ffad9684bb816787d9f; all 130 outputs verified.
ODB SHA256 234841fdb17170a7973e3315d2e493e9220c13808a881fa43e262e63a3b02d76.
SPEF SHA256 5730e53fa0f1be90c29597e6f90f2a2d8ceee19ac64c6106ab826e5d6232eb42.

20 ns and 5% derating remain unchanged. This is actual routed nominal RC, not qualified RC min/max or production signoff.

| Corner | Setup violations | Worst setup slack ns | Hold violations | Worst hold slack ns |
|---|---:|---:|---:|---:|
| nom_slow_1p08V_125C | 59 | -0.7403464717499858 | 0 | 0.4491127596936628 |
| nom_typ_1p20V_25C | 0 | 6.9377021646796075 | 4 | -0.12389645216009994 |
| nom_fast_1p32V_m40C | 0 | 10.303459710393875 | 52 | -0.42973248398308955 |

Antenna repair improved slow setup count from 64 to 59 and WNS from -0.853525 to -0.740346 ns, but introduced hold failures relative to the pre-repair diagnostic route. Therefore antenna closure cannot be substituted for timing closure. All 59 reported setup paths start at nssoc_sta_i_77912 (48) or nssoc_sta_i_77897 (11).

Annotation classification found 1403 unannotated drivers (1288 disconnected, 115 without sinks), zero loaded unannotated drivers, zero partial missing loads and 102967 SPEF nets. This diagnosis is not full timing coverage acceptance. Slow slew/fanout/cap violations are 506/209/52.

## Hold evidence

nom_typ_1p20V_25C: reported violated paths 4; endpoint groups {"u_ram.g_ram_2048x64_ecc.u_b2": 1, "u_ram.g_ram_2048x64_ecc.u_b0": 2, "u_ram.g_ram_2048x64_ecc.u_b3": 1}

Worst path details:
```
nssoc_sta_i_72331 (rising edge-triggered flip-flop clocked by clk_i)
                                              3.063546   data arrival time
                      1.022979    0.399289    1.979917 ^ u_ram.g_ram_2048x64_ecc.u_b2/A_CLK (RM_IHPSG13_1P_2048x64_c2_bm_bist)
                                  0.250000    2.229917   clock uncertainty
                                  0.957525    3.187442   library hold time
                                              3.187442   data required time
                                              3.187442   data required time
                                             -3.063546   data arrival time
                                             -0.123896   slack (VIOLATED)
```

nom_fast_1p32V_m40C: reported violated paths 52; endpoint groups {"u_ram.g_ram_2048x64_ecc.u_b2": 15, "u_ram.g_ram_2048x64_ecc.u_b0": 22, "u_ram.g_ram_2048x64_ecc.u_b3": 4, "u_ram.g_ram_2048x64_ecc.u_b1": 11}

Worst path details:
```
nssoc_sta_i_72331 (rising edge-triggered flip-flop clocked by clk_i)
                                              2.134913   data arrival time
                      0.941342    0.371218    1.526514 ^ u_ram.g_ram_2048x64_ecc.u_b2/A_CLK (RM_IHPSG13_1P_2048x64_c2_bm_bist)
                                  0.250000    1.776514   clock uncertainty
                                  0.788132    2.564646   library hold time
                                              2.564646   data required time
                                              2.564646   data required time
                                             -2.134913   data arrival time
                                             -0.429732   slack (VIOLATED)
```

## Next action

Keep the selected-net routing run 44430646506 separate: it contains two added data buffers and the earlier antenna-round-one source. Authenticate its route-preservation and timing results before choosing a new combined candidate. Use these actual hold paths to select data-delay or clock-distribution repairs; do not relax hold checks, clock uncertainty or library values. Full foundry DRC/LVS, SRAM qualification, external I/O and manufacturer approval remain open.
