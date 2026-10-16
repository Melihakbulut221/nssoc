# Full TX driver wire extraction prerequisites

This cloud job exports every actual Metal1 through TopMetal2 and interlayer via polygon from the already proved full-driver GDS. The native metal/via connectivity graph must bind each complete conductor component to exactly one unsimplified native LVS net, and every native metal net must be covered. It preserves terminal/port ownership, missing-metal nets, polygon counts, layer hashes and empty layers. Components are never joined merely because native net names agree.

The graph method is adapted from the source-hashed pump procedure, with every substitution recorded in `docs/evidence/tx-driver-wire-method-20261016.json`. The full driver uses84rawMOS fingers,4resistors and12finite contacts, not the pump's topology. The original GDS, native database and all physical evidence are restored and rehashed in GitHub Actions.

This is geometric wire binding, not an RC value or final PEX result. Native terminal reference planes and fresh RC extraction/audit follow. Gate/poly/diffusion resistance, correct junction handling, substrate and RF qualification must remain explicit model boundaries; there is no electrical or mainchip acceptance at this stage.

## Measured full-driver conductor graph

Run38872584488 passed:10physical metal/via components,12electrical native nets,100raw devices and372native terminals. All6external ports are covered. The one additional native net has no electrical device terminal. There are84MOS,4resistors and12finite contacts. Every source polygon and the unsimplified net ownership were preserved.

`cloud_tx_driver_anchors.py` next binds272metal terminals and explicitly retains100body/well terminals. It selects actual contacts from the native terminal's diffusion/poly geometry, checks original resistor PCell pin rectangles when required, and probes both native LVS and the independent metal graph. Coincident contact points share a single wire reference plane; they are not duplicated as unrelated ports. Every candidate contact and the selected reference is retained. Four corrupted reference sets must fail.

This reference-plane selection leaves poly/diffusion resistance and body spreading explicit and unqualified. It does not silently claim these resistances were extracted. Fresh metal/via RC and its raw audit follow this step, before any complete-driver loaded simulation.

Run38874325892 completed: all372native terminals bound,272metal terminals represented by158shared actual contact planes,100explicit body/well terminals, plus6public ports. Total164unique planes cover all10physical components. All4actual reference corruptions were rejected. Fresh native RC and its raw audit remain the next required step.

## Fresh native wire RC

`cloud_tx_driver_rc.py` restores the proven164planes and10actual metal/via components, then runs the pinned native Magic runtime on `full_driver_wires`. The adapted audit retains the original raw resistor multiset, per-point ground capacitance, every mutual-capacitance attachment, the full conductor-collapsed capacitance matrix and source-node retirement checks. Original tolerances are unchanged. All13actual raw-export/reference corruptions remain mandatory; aliases from the original ideal netlist are never inserted into the exported resistor graph.

The exact source-method hashes and all adaptations from the earlier pump method are in `docs/evidence/tx-driver-rc-methods-20261016.json`. Source-bound paths are rebased and rehashed; the164actual reference points and372terminal identities are unchanged. This stage still excludes poly/diffusion resistance, substrate spreading and qualified RF extraction. No full-driver electrical acceptance follows until the raw100-device model is composed with these actual wires and simulated.
