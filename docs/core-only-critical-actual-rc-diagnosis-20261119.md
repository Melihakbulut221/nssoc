# Actual RC timing after six critical resizes: load isolation required

Diagnostic run 44422630920, head fb2d53065c9bbc1642bb75882e4690afa53b2a33, artifact 14482064879, SHA256 badb317c0b7ea2a2137ca3167d59474160bc6612b6942364aebdd1b5f0d0817c. All 132 output hashes verified. This is routed candidate 44402072903 before antenna repairs, not a production-admissible layout.

At unchanged 20 ns / 5 percent derate and actual nominal extracted RC:
- Slow: 64 setup violations, WNS -0.8535252746 ns, TNS -29.65015517 ns; hold 0, worst hold +0.44911276 ns. Electrical: 484 slew, 126 fanout, 50 capacitance violations.
- Typical: setup 0, hold 0, worst hold +0.185584886 ns; electrical 4 slew, 126 fanout, 54 capacitance violations.
- Fast: setup 0, hold 0, worst hold +0.037160609 ns; electrical 0 slew, 126 fanout, 60 capacitance violations.
- 1403 unannotated drivers classified as 1288 disconnected and 115 no-sink; zero loaded unannotated drivers. This classification is not blanket functional/timing coverage approval.

The previously estimated zero-setup result did not survive actual RC. Six resizes reduced violation count from 69 to 64 but did not materially improve worst slack. Do not promote estimated closure.

The 64 violated max.rpt paths were enumerated (not merely the first displayed path). 48 launch from nssoc_sta_i_77912; 16 from nssoc_sta_i_77897. All 48 in the first group traverse nssoc_sta_i_2657 (nand3_1) and nssoc_sta_i_11771 (nor3_2).

| Driver | Violated paths | Max cell delay ns | Output slew ns | Cap pF | Fanout |
|---|---:|---:|---:|---:|---:|
| nssoc_sta_i_2657 / nand3_1 | 48 | 1.157462 | 1.143185 | 0.082759 | 3 |
| nssoc_sta_i_11771 / nor3_2 | 48 | 1.884719 | 1.880131 | 0.187138 | 8 |
| nssoc_sta_i_14982 / a21oi_1 | 8 | 2.774710 | 2.855876 | 0.221972 | 5 |
| nssoc_sta_i_14419 / nor3_1 | 8 | 1.693900 | 2.104858 | 0.108616 | 2 |
| nssoc_sta_i_14661 / and2_1 | 8 | 1.666715 | 1.678363 | 0.267234 | 8 |
| nssoc_sta_i_14660 / a22oi_1 | 8 | 1.550113 | 1.864029 | 0.143960 | 4 |

Pinned slow standard-cell Liberty at PDK c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c was inspected directly: nand3 variants are nand3_1 and nand3b_1 (different function), while nor3 has _1 and _2 only. Do not invent nand3_2 or nor3_4. The 48-path common prefix therefore needs load isolation/fanout buffering or logic restructuring with equivalence proof; the remaining endpoint-specific heavy drivers may allow function-preserving resizes. Inspect exact sinks, wire/diode capacitance and physical placement before forming the ECO.

Next: bind the eventual timing ECO to the latest antenna-repaired source, preserve diode inventory and connectivity, target the common loaded prefix rather than another full-route seed change, and measure actual RC again. The minimum fast hold margin is only 37 ps on this diagnostic candidate; hold must be rechecked after every timing repair. Final repaired-route STA remains mandatory.
