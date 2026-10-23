# v50 geometry repair candidate for measured v49 losses

Actual v49 extracted simulation failed all three original loaded cases. Full-wave loss diagnosis40032831292 measured nominal AVDD-to-load losses0.304658V/0.317578V and local return elevations0.158325–0.253541V. Physical public-to-terminal power paths were50.85–64.51ohm. Exact old waveforms and losses are retained in the referenced receipts.

v50 keeps every native v49 device, placement, intrinsic dimension, finite contact and circuit connection. It changes the physical long routing:6um escape-column pitch, TopMetal1 vertical trunks2um for input/bias/substrate and4um for current-carrying nodes, TopMetal2 horizontal buses8um for supply/return,4um for output/tail and2um for the other nets. Bus pitch is12um and begins at110um. Native via stacks connect actual terminal escapes to these layers; eight exported ports move to TopMetal2. There is no synthetic wire-R scaling or ideal power alias.

The checker applies the same560 native DRC categories, deep/flat18-device transistor LVS and nine actual fault controls. Open/short faults follow the actual port layer/width. This physical candidate must pass the actual decks and a fresh wire extraction and loaded native simulation. The previousRC values and pre-layout pass cannot accept this candidate. Wider top metal can change capacitance; improvement is unproven until rerun.

Parent integration, full serial Gen3x4 and final chip timing remain open.

## Actual first DRC and landing correction

Run40033603461 rejected120TM1.a markers. The pinned deck requires minimum1.64um TopMetal1 width. Cloud inspection40034691292 read the original report and retained every coordinate. Example actual edge pairs at the substrate trunk centeredx285um include a50nm lateral protrusion betweenx283.95 and284um and local separation1.26um at the upper via landing. The2um trunk does not completely absorb the native via landing shape.

The correction makes every vertical TopMetal1 trunk4um wide, keeping6um center spacing. Existing4um current-carrying trunks, horizontal widths, all intrinsic devices and original rule decks are unchanged. This removes the narrow-trunk landing transition by geometry, rather than waiving the120errors. Full native DRC/LVS/fault verification is rerun and its result remains pending. Any extra wire capacitance must still be extracted and simulated.
