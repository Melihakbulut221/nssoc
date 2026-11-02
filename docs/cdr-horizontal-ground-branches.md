# Actual horizontal ground branch reinforcement

Actual13-layer native topology41384121103 established a wide vertical TopMetal1 ground bus and32horizontal TopMetal2 branches, each3200nmhigh, connected through existing lower-layer ground conductors. The failed vertical Metal5 hypothesis41383764902 is preserved; this candidate uses the actual existing TopMetal2 branches instead.

All32original owned branch polygons widen vertically from3200to10000nm. Their longitudinal endpoints, all existing material, devices, vias, schematic and public port pad remain unchanged. Every new polygon must clear foreign TopMetal2 by5005nm, foreign TopVia2 and unclassified drawing conservatively, and remain inside the original layout. Any refused branch rejects the complete proposal; no partial candidate is promoted.

Original68source controls remain intact plus9horizontal-specific controls. Native generation repeats complete current ground topology, validates exact layer unions and same-net ownership, then checks the sole serialized TopMetal2 delta and complete original-material reversal. The proposal is motivated by measured local ground rise, but its electrical effect is unproven and parasitic capacitance will also change.

After generation, require the unchanged full560DRC, deep/flatLVS13, current canonical binding, fresh RC and actual loaded-wave gates. No physical, electrical, full-PHY or final-timing acceptance is asserted at generation.
Process rule reference: https://ihp-open-pdk-docs.readthedocs.io/en/latest/verification/drc/02_main_rules.html

## Preserved source-control failure and precise API correction

Run41385188402 failed the positive horizontal-widening control before native acquisition; no GDS was generated and native-generation was skipped. KLayout Region.sized with two integer arguments binds the isotropic(distance,mode) overload. The intended anisotropic call requires three arguments(dx,dy,mode). Use sized(0,3400,2) for actual y-only widening and explicitly assert the independent expected control rectangle coordinates. The malformed-width refusal also uses the explicit anisotropic overload. Geometry guard limits, target widths and original source controls are unchanged.

API reference: https://www.klayout.de/doc-qt5/code/class_Region.html

## Native10um proposal refused; redesigned5um branches

Actual generation41385545130 passed77source controls, then all32branches failed foreign TopMetal2 spacing. No GDS was emitted. The10um symmetric expansion is preserved as a rejected proposal.

The redesigned branch width is exactly5000nm, grown only900nm per side with the explicit three-argument native sizing API. IHP TM2.b requires2um spacing; TM2.bR requires5um if either parallel line is wider than5um over a long run. This design therefore enforces2005nm spacing to every foreign polygon and5005nm to every foreign polygon whose vertical extent exceeds5000nm. That latter condition is conservative for nonparallel shapes and short runs. Unclassified drawing and foreign-via guards remain conservative and all original full560physical checks are still required.

Two additional source controls distinguish legal at-most5um parallel lines from a wide neighboring line that still requires5um. All original68controls and the horizontal guard controls remain. This changes the physical candidate to fit actual routing space; it does not accept the failed10um geometry or relax final DRC/LVS/electrical acceptance.
