# Full TX driver wire extraction prerequisites

This cloud job exports every actual Metal1 through TopMetal2 and interlayer via polygon from the already proved full-driver GDS. The native metal/via connectivity graph must bind each complete conductor component to exactly one unsimplified native LVS net, and every native metal net must be covered. It preserves terminal/port ownership, missing-metal nets, polygon counts, layer hashes and empty layers. Components are never joined merely because native net names agree.

The graph method is adapted from the source-hashed pump procedure, with every substitution recorded in `docs/evidence/tx-driver-wire-method-20261016.json`. The full driver uses84rawMOS fingers,4resistors and12finite contacts, not the pump's topology. The original GDS, native database and all physical evidence are restored and rehashed in GitHub Actions.

This is geometric wire binding, not an RC value or final PEX result. Native terminal reference planes and fresh RC extraction/audit follow. Gate/poly/diffusion resistance, correct junction handling, substrate and RF qualification must remain explicit model boundaries; there is no electrical or mainchip acceptance at this stage.
