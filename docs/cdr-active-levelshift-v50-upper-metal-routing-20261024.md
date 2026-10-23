# v50 geometry repair candidate for measured v49 losses

Actual v49 extracted simulation failed all three original loaded cases. Full-wave loss diagnosis40032831292 measured nominal AVDD-to-load losses0.304658V/0.317578V and local return elevations0.158325–0.253541V. Physical public-to-terminal power paths were50.85–64.51ohm. Exact old waveforms and losses are retained in the referenced receipts.

v50 keeps every native v49 device, placement, intrinsic dimension, finite contact and circuit connection. It changes the physical long routing:6um escape-column pitch, TopMetal1 vertical trunks2um for input/bias/substrate and4um for current-carrying nodes, TopMetal2 horizontal buses8um for supply/return,4um for output/tail and2um for the other nets. Bus pitch is12um and begins at110um. Native via stacks connect actual terminal escapes to these layers; eight exported ports move to TopMetal2. There is no synthetic wire-R scaling or ideal power alias.

The checker applies the same560 native DRC categories, deep/flat18-device transistor LVS and nine actual fault controls. Open/short faults follow the actual port layer/width. This physical candidate must pass the actual decks and a fresh wire extraction and loaded native simulation. The previousRC values and pre-layout pass cannot accept this candidate. Wider top metal can change capacitance; improvement is unproven until rerun.

Parent integration, full serial Gen3x4 and final chip timing remain open.
