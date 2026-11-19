# Electrical repair dependencies — 2026-11-19

Native inventory run 44453782430 (6a3f7a4e8979032e9a8ea1d86393f6dbdb1d6d8a) maps 1302 reported rows across three corners to 353 unique nets in combined ODB 81766779033ee0642d322a417e4e8f389807b7cb2d1d5ceb6cf1842915fb68ee. Artifact 14497116804 SHA256 4c5112a9c9b6c0c740993861872e923c42b224f7b70e115103f1bdda1f386681; three outputs verified.

The initial `antenna` boolean used the wrong master name (`sg13g2_diode`). Actual native master records show `sg13g2_antennanp`; the exact recorded connectivity remains usable. Recompute classification from master names, retain every load and violation, and fix the native helper for future runs. This is a diagnostic correction, not a physical change or violation waiver.

Corrected mapping: 100 slew-violating nets, 210 fanout-violating nets, 60 capacitance-violating nets including nine SRAM outputs. Every one of the 210 fanout nets has at most eight functional sinks; added antenna diodes cause its total fanout to exceed eight. These include two clocks. There are 837 antenna terminals on the inventoried nets. Example: nssoc_sta_n_62713 has eight functional sinks plus 16 diodes; net5013 and net4366 each have eight functional sinks plus 12 diodes.

Retain antenna protection and current constraints. Evaluate branching or reduced qualified diode placement with full post-route antenna checks, exact functional connectivity and RC timing; do not remove diode loading from constraints merely to pass. Clock modifications need a separate skew/hold admission, since fast hold margin is only about 37 ps. The active setup-only routing candidate intentionally preserves clocks.

Worst slew is driven by nssoc_sta_i_55577 (nor4_1), followed by nssoc_sta_i_54413 (nor4_1); native nor4_2 exists, but actual input slew and output RC must be checked before sizing. Nine SRAM outputs need local load isolation or shorter routes, not a relaxed macro capacitance limit. New buffered routes can require new antenna repairs, so closure must iterate electrical and antenna checks together.
