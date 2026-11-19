# Combined actual-RC timing: 19 setup violations remain, hold zero

Run 44448236669/head 720ad3910edaa210b56b946d6cd0e9ced9454a77 passed execution, attempt 1. Artifact 14494314980 SHA256 4f2b81dfa242d40fee5eb0b38ed89274c7d65ae10d3163d2a99fc7f1d254f038 and all 134 outputs verified. This is not full signoff.

| Corner | Setup count | Worst setup ns | Hold count | Worst hold ns | Slew/fanout/cap |
|---|---:|---:|---:|---:|---|
| slow | 19 | -0.194866350793 | 0 | +0.449112759694 | 502/210/52 |
| typical | 0 | +7.27195746425 | 0 | +0.185584886045 | 4/210/54 |
| fast | 0 | +10.3034810267 | 0 | +0.0371606089751 | 0/210/60 |

Slow TNS -2.22351210404 ns, improved from -23.1071239794. Setup count improved 59 to 19 and worst setup from -0.74034647175 to -0.194866350793 ns. Hold remains zero in all three measured corners. DRC and antenna of source route are zero. Source ODB 81766779033ee0642d322a417e4e8f389807b7cb2d1d5ceb6cf1842915fb68ee; fresh netlist 6e8d7284dbf45081e157ccfda60450843738a75fde19e60bd16007b11ebbdc11; DEF be5c9dea994a104d4c0c620074b9c6e941cf3b005316fcd5700c85de39b7cd0f; unchanged SDC f121116a72150c56126ac3d8dc4fda946e6d0040984e9264ef3d877171029de1.

All 19 remaining violations start nssoc_sta_i_77897/Q and traverse nssoc_sta_i_2496 (nor2_1) and fanout2484 (buf_1). Worst endpoint is nssoc_sta_i_78564/D. On that path 2496 drives eight loads, cap 0.095023 pF, slew 1.219093 ns, cell delay 1.047064 ns. fanout2484 has cap 0.077661 pF and delay 0.422932 ns. Later high-delay branches include 14982/a21oi_1 (2.776915 ns, cap .222228 pF, slew 2.858998 ns) on 8 of 19 paths. First inventory the common drivers and legal library variants, then choose a bounded exact-function resize; keep all clock geometry fixed and remeasure after routing.

Annotation diagnosis: 1403 fully unannotated drivers = 1288 disconnected + 115 connected/no-sink; zero loaded unannotated, partial or missing native loads; 102969 SPEF nets. This is not complete functional/timing coverage. Electrical constraints, qualified RC min/max, external timing, full SRAM/I/O transistor LVS and manufacturing approval remain open. No period, derating, model or waiver relaxation was applied.
