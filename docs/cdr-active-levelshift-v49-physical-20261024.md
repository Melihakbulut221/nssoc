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

## Actual physical result

Run40024005062 completed on source0de20af72216c5cdd5a7ace6d766d1060c697540. All560DRC categories ran with0markers. Both deep and flat unsimplified transistor comparisons matched exactly18layout/reference devices with8external ports and no extraction diagnostics. All9intentional faults were rejected by actual native runs. The q_open case retains a matched device census but the deck explicitly rejects the disconnected top-level pin; the audit correctly reports FAIL. Device-census matching alone is never sufficient.

Actual GDS SHA256: f05e4b9c2125e0e65d18b10e6e9fc708067b0ea5b2055e9a747b8a062939c5dc.
Actual LEF SHA256:6388a428159c853abe2c1eabe0cec50b883d3ffa6cbd9beb6bcb857ff559ef03.
Physical schematic SHA256:83855e9e0e8ebc9bc6a4df10105927c58bde3bd5afe32e647d52f98bae277720.
Bounding box526um by188.63um. Complete GDS, LEF, schematic, native LVS databases, DRC databases and all fault files remain in the source-pinned release archive. Receipt: docs/evidence/cdr-active-levelshift-v49-physical-pass-20261024.json.

Next, extract fresh conductor/via RC from this exact GDS, retain intrinsic MOS/HBT/R and finite substrate contacts exactly once, then connect it to the real rejected C/D sampler parent and its existing bias network. Existing standalone ideal current bias and150fF load are not evidence for parent integration. The tiny hot/low common-mode margin requires loaded/fullwave evidence. Mainchip and complete serial PHY are still unaccepted.
