# CDR sampler v32 physical candidate

The v31 full-waveform diagnosis reproduced every original electrical failure. It located xd0105/xd0106 at the C-master track selectors (minimum active VCE approximately 0.379–0.382 V, below 0.4 V). A/B slave inputs were already valid at the external sampling edge, but their loaded outputs settled too late. C/D additionally had weak or late master data observations. The actual v31 followers remained conducting in the analyzed nominal-late capture.

This candidate changes exactly four native rppd dimensions per sampler relative to the physically verified v30 leaf still used by v31:

| Device | Width | Old length | Candidate length | Hypothesis |
|---|---:|---:|---:|---|
| BP, BN | 4 µm | 1.1 µm | 0.9 µm | Raise input common mode to improve master clock-selector VCE; input gain and loading may worsen |
| S_BS | 1 µm | 12.8 µm | 6.4 µm | Increase inactive slave data-emitter discharge |
| S_BH | 1 µm | 9.6 µm | 4.8 µm | Increase inactive slave hold-emitter discharge |

These are unproven design hypotheses. No timing, voltage, current, load, source-bit or clock gate is relaxed. All transistor dimensions, the four collector loads, IP/IN, master bleeds, physical primitive positions, external ports and the other 50 native primitive drawings must remain unchanged.

The leaf workflow regenerates actual PCells and performs the original 560-category DRC, unsimplified deep/flat 54-device LVS, native LEF checks and all 20 previous fault controls. Two new reference faults independently restore the old slave data/hold bleed lengths, making 22 physical/LVS/LEF fault controls. Geometry comparison retains its original faults and adds both old slave-bleed lengths.

Even a passing leaf is not an electrical improvement or a full PHY. It must replace the four samplers in the actual v31 parent, retain the v31 follower change, pass parent DRC/LVS, receive fresh RC extraction and run the unchanged full loaded early/late and fault cases. Previous rejected results and their original waveforms remain immutable. All work runs on GitHub-hosted runners.
