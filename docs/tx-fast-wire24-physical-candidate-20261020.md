# Actual TX fast-route width candidate

Native data-network review39338196252 completed the124-leg,372-base passive
network census against the exact rejected timing-priority waveform.
For ap/bp, actual wire capacitances are216.87/236.75fF; maximum metal pair
resistances are20.91/21.37ohm. p4_0p/p4_3p remain300.32/347.41fF and
24.07/26.22ohm; p8_0p/p8_7p are347.80/355.01fF and26.07/26.38ohm.
These are native passive-wire measurements, not intrinsic rppd resistance
or a transient delay prediction. Source intrinsic devices remain nonlinear models.

The next physical experiment starts from the actual passing1674-device GDS
6b8a3d68e6f94cc7a0812ab89c360a8098633d6e41fa238654c8e16c5ea73057.
It narrows only the28 intermacro signal routes after the leaf-stage outputs:
TopMetal1 vertical trunks and TopMetal2 horizontal stubs change4to2.4um.
Original4um square landings, every native via, child drawing, macro position,
schematic, LEF, supply rail and remaining32data routes are retained exactly.

The pinned IHP rules specify1.64um minimum TopMetal1 and2.00um TopMetal2 widths:
[TopMetal1 rule](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/5e6d592e4002946a4616f798c357f0f3c06cf3b6/ihp-sg13g2/libs.tech/klayout/tech/drc/rule_decks/beol/5_22_topmetal1.drc),
[TopMetal2 rule](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/5e6d592e4002946a4616f798c357f0f3c06cf3b6/ihp-sg13g2/libs.tech/klayout/tech/drc/rule_decks/beol/5_25_topmetal2.drc).
The2.4um candidate is above both minima; only the full native deck can prove DRC.

The motivation is reducing wire loading without adding emitters or changing
input common-mode dividers. Increased wire resistance may outweigh capacitance
reduction. No improvement is claimed until freshRC and unchanged loaded gates.
The24HBT violations and existing sampling failures remain open.

The generator independently checks every cell instance and drawing against
the permitted parent-metal subtraction, verifies serialized GDS, and rejects
three actual geometry corruptions. It then runs the exact baseline native
physical verifier without a byte change:560DRC categories, hierarchical/flat
1674-device LVS and original wrong-finger/missing-HBT/open/short/offgrid controls.
All source receipts and failures remain in GitHub; no CAD output is stored locally.
