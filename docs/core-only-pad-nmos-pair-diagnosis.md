# NMOS isolation results and pair/diode follow-up

Run44375953410/head4d1c7caf4d3382fd0c23eb1dbd5f1e025f54485a:
- Forward-only native NMOS: all six captures complete. Artifact14461458273 SHA256a6af8030acceeaf4e2a7274c549c0e4bb2a59d70f4cd025fd4dd5f3eb6d20a3d.
- Reverse-only native NMOS: all six complete. Artifact14461766163 SHA2561b79fa91d112977f864a036c4a04aa932c4d4e643517c44e428209d182f3ffaa.
- Native NMOS clamp:0-turnoff still fails21.3262ns;five other captures complete. Artifact14461513271 SHA25648614d76ae9825031660ff8bc5236da99a4fa2787d01f67794b692c519b0d46b.

All archive digests and declared output hashes verified. Each individual transistor carries about1.065637mA enabled and9.174pA off under this fixture; combined clamp carries twice that. No evidence here proves a device orientation defective.

New changed diagnostic fixtures preserve the same PVT,source models,dimensions,ideal gate ramp,KLU/Gear2,1ps and tolerances: n_pair contains exactly the two oppositely oriented native NMOS devices without antenna diode; n_antenna contains the original dantenna subcircuit only. The diode connects ground to driven gate, not to pad, so pad drive-current assertions are inapplicable in that fixture. No omitted diode or transistor is proposed as a product change. Both still require full50ns captures and fatal numerical-error handling.

This pair/diode test determines whether the combined transistor system reproduces the failure without the antenna element. Synthetic continuation/readback tests cover all five fixture choices. No partial or reduced fixture grants full-pad/production acceptance. Core route44337630426 remains independently active.
