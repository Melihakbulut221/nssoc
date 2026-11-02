# Current critical resistance physical mapping

This read-only cloud job maps the actual 32 unit-current queries from run 41395210468 to the current horizontal-ground GDS and native distributed RC. It does not infer a physical layer from a SPICE node name or the Magic rnode type placeholder.

Every RC archive member is authenticated. All 978 native port coordinates must reproduce the actual GDS anchors on the original 5 nm extraction grid; all 24,530 resistor endpoints, values and multiplicities must match the native exported network. Each of the three most influential edges per query is traced through the original composition map, then bound to its native wire component. Owned and foreign geometry at both native endpoints is reported for all 13 conductor layers, whose complete unions must equal GDS.

Original geometry guards and 85 controls are unchanged. Input and output geometry are compared for equality. No geometry is generated; there is no new transient, physical acceptance, qualified PEX, full PHY acceptance or final timing claim. The prior loaded electrical rejection remains authoritative.

The 32.5245 ohm source-terminal branches dominate the measured ground-pair resistance. This mapping is needed before selecting a physical repair. Unit-current power is a sensitivity measure, not actual operating dissipation.

Mapping attempts41396652103 and41396958129 refused the original pre-MIM anchor set. The diagnostic proved that971coordinates match and exactly seven MIM bottom access references differ. The already authenticated current extraction anchors at mim/precise/wire/anchors08.json contain these exact seven relocations (devices273-279), moving the reference to actual Metal5 outside the intrinsic MIM mask. This was an input-selection error in the new mapping, not a change in the RC or a relaxed tolerance.

The corrected reader uses the extraction-stage anchors. It requires all978anchor identities, exactly the seven documented changes and equality of every other anchor field. Both original and extraction coordinates must belong to the same actual native owned metal. All978port coordinates still must pass the unchanged2nm/5nm-grid gate.
