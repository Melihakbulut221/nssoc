# V22 fullwave late-phase rejection

Native run39458941860 nominal_late completed without diagnostics, preserving all113475 raw rows,1108 columns and the original34.25ns interval. The full waveform digest is802e2b400b8a27b6e1c968c23ca7e0586efee301cb30c6a4801fa0097c643d32. All116 native HBT flags were verified; zero-source operating point was zero. The device gates passed, but the data and phase gates did not.

| Sampler | Wrong-sign samples | Below100mV samples | Worst signed margin | Maximum clock-to-valid |
|---|---:|---:|---:|---:|
| A |0|129|30.399mV|44.531ps|
| B |0|64|82.844mV|39.219ps|
| C |117|128|-116.849mV|66.719ps|
| D |181|254|-194.375mV|118.906ps|

V21 late D had252 wrong and277 low-margin samples; v22 improves this to181/254 but does not close sampling. The phase average22.264mV remains below the original30mV requirement. VI mean signed current61.639uA passes its independent gate. The external-clock screen is still not closed-loop CDR acceptance.

Clock-stopped and VI-bias-off actual fault cases were detected successfully. The early-phase job was still live when this receipt was written; do not restart it or claim its result. Next circuit work must address the remaining A/B regeneration delay and C/D capture timing while preserving original loads, bit sequence, device checks and early/late phase gates. No threshold or observation window has been relaxed.
