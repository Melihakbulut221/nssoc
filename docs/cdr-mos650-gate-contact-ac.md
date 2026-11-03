# Current gate-contact model diagnostic

This run consumes the exact current650 physical wire producer41712243960, tied to DRC/LVS-passing GDS c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c. It reauthenticates the complete producer archive in the hosted runner and rebuilds all200 native gate IDs, full physical dimensions and contact-end geometry. There are50 one-ended and150 two-ended electrodes. The 8.885um geometry has only two-ended electrodes, so actual cases are14 QS/RF combinations, not16.

The original frozen models remain immutable. A separate copy exposes the six hardcoded lv NMOS instance NGCON values as one wrapper argument, default2; all resistance and NQS parameters remain unchanged. Eight fresh canonical NGCON2 cases must reproduce the explicit-NGCON2 variants over17 frequency points within relative1e-9/absolute1e-7. All native instance NGCON values are read back; full device/model readbacks, stdout, stderr, decks, measurements and failures are preserved. Existing0.8V gate/0.6V drain biases, physical AS/AD/PS/PD, pre_layout0 and1MHz to10GHz remain fixed.

A changed input impedance is not an extracted physical gate resistor. No external poly network has yet been composed with the compact models. Gate contact geometry alone does not qualify the model, resolve distributed electrode coupling, or validate a full PHY. Complete loaded electrical, serial and all-corner timing requirements remain open.

## Preserve first native mismatch and isolate comparison topology

Run41715622293 executes both native sweeps without warnings and reads back every requested NGCON correctly, but fails the original NGCON2 equivalence guard. Seven real-impedance samples differ outside relative1e-9/absolute1e-7; the largest observed difference is4.311324346417678e-6 ohm. The eight-instance canonical deck and fourteen-instance explicit deck have different matrix sizes, so the failed comparison does not isolate wrapper semantics from numerical ordering.

The successor preserves the same equivalence thresholds, biases, frequencies, physical dimensions and models. It executes each of eight canonical and fourteen physical contact/RF cases in its own one-transistor native deck. This controls matrix size for the paired comparisons and preserves all22 independent stdout/stderr/readbacks. It does not waive the failure or claim any loaded-circuit qualification.
