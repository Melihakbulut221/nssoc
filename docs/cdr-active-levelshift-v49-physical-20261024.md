# Native active level-shifter: physical candidate

Cloud native run40022525081 completed all five cases successfully with the same component gates as the rejected v48. Only XDP/XDN resistor length changed7.2um to9.6um. The complete source-pinned receipt preserves native full34.25ns/110385row/13column captures and all fault evidence.

| Corner | Output common mode V | Minimum signed signal mV | Maximum input-to-valid ps | Peak HBT VCE V |
|---|---:|---:|---:|---:|
| nominal |1.919483–1.920950|199.561|22.031|1.439937|
| hot/low |1.803955–1.805376|164.741|25.469|1.306410|
| cold/high |2.035715–2.037194|224.469|19.844|1.541499|

The hot/low common-mode margin is only3.955mV. Passing a limited standalone screen is not sufficient to qualify robustness, PVT or the full CDR. HBT uses hbt_typ throughout. All original parent requirements remain open.

The new generator instantiates the exact2HBT/3LVNMOS/4rppd circuit using native SG13_dev PCells and9finite substrate contacts. Each MOS receives a real local contact alongside its active strip. SUB and AVSS remain separate conductor ports; the LVS reference models finite ptap1 devices to BULK. The8ports include IREF and the tail is internal. GDS, LEF, physical schematic, placements and source hashes are published from GitHub, never staged locally.

The checker uses the unchanged pinned PDK revision5e6d592 and native runtime. It requires all560DRC categories and both deep/flat18-device LVS comparisons with no_simplify/top_lvl_pins enabled. Six reference faults exercise resistor value, HBT multiplier, missing amplifier, HBT collector/emitter swap, MOS width and MOS gate/source swap. Three actual GDS faults exercise off-grid, output open and input short. A generated layout alone cannot pass. The cloud controller first retrieves all five original component summaries by exact hashes and verifies their full captures, device/signal/common-mode results and fault rejection.

Pending after this leaf: actual native DRC/LVS results, fresh extracted RC, parent signal/bias integration, unchanged complete CDR gates and closed-loop/PVT validation. No completed leaf check implies serial Gen3 x4 or mainchip setup/hold closure.
