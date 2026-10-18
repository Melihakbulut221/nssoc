# Compact PD394 native loaded evaluation

The corrected compact sampler passed native geometry, DRC and LVS before full PD394 physical integration. Fresh compact native plane/device identities were extracted; no old v3 native IDs were reused.

Raw RC audit 39093269827 passed the unchanged 13 wire corruption controls and nine MIM identity controls. Composition 39093544313 passed 15 malformed-model controls, with 394 devices, 9655 resistors, 7555 capacitors, and eleven intrinsic MIM models represented exactly once. Every raw wire R/C token is retained. Immutable reports and archives are pinned in the adjacent evidence receipts.

The new loaded workflow evaluates nominal early/late timing plus actual stopped-clock and VI-bias-off controls. Its source delta manifest and hosted byte-equivalence guard restrict changes to fresh artifact/model identities and independently audited element counts. The original 256-bit, 34.25 ns stimulus, 0.3125 ps step, external clock common mode, sampler/XOR loading and all bit/device/current limits are unchanged. These are new simulations of the compact geometry, not replayed v3 results.

At launch no loaded result exists. Native physical/RC/composition passes alone do not establish clock recovery, full serial PHY or final chip timing. Keep all rejected predecessors and complete wave evidence.
