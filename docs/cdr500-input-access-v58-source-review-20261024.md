# CDR500 input-access candidate v58 — source review only

The passed existing-network diagnosis is run [40085495203](https://github.com/Melihakbulut221/nssoc/actions/runs/40085495203), source `ae95568cccf257f9740b65019b49914933fa18ea`. Its complete summary and archive are immutable, hash-pinned release assets; the receipt is `docs/evidence/cdr500-input-path-diagnosis-pass-20261024.json`.

| Native gain / driver / termination | Driver to gain, ohm | Driver to termination, ohm | Gain to termination, ohm |
|---|---:|---:|---:|
|59 /69 /187|39.442081|44.520515|44.402965|
|60 /70 /188|49.056888|47.268300|51.146988|
|111 /121 /225|39.622081|44.520515|44.582965|
|112 /124 /226|49.236888|47.268300|51.326988|

These are the exact existing **metal-network unit-current** results with all24550 raw/composed resistor records checked, KCL residuals below4e-12A and energy identity preserved. Other terminal currents float for this diagnostic. They are not intrinsic HBT/rppd resistance, operating current or a claim that transient voltage drop equals one pairwise R times one circuit current. Original nominal electrical failures remain.

Actual ownership shows the largest upstream/termination access records traversing old `pd_child_rc_retime` paths: original M3 escapes, long M4 columns and M5 buses. The sampler input also has a real0.4um M3 base escape. Reduced-resistor endpoint coordinates were matched to same-conductor materials; a reduced edge is never assigned one unique material or assumed to be a straight segment.

`generate_cdr500_input_access_v58.py` proposes only added drawing geometry in the parent. It derives all positions from actual original via centroids and native device/terminal ownership:

1. Preserve both original retime M4 columns on each of the four input conductors. Add3.2um TM1 parallel straps with actual native M4-to-TM1 via stacks at both ends.
2. Add3.2um TM2 bus shunts from the existing parent top-metal boundary to the two witnessed retime column heads, with actual M5-to-TM2 stacks. Existing parent wires stay.
3. Preserve original sampler base geometry and its four-column cuts. Add a sixteen-column native M1-to-M3 stack at the same actual base access center and widen the same-owned M3 escape to1.2um with added metal.

There are28 added native via instances and16 route rectangles. All existing child drawings, primitive geometry, source parameters, parent placements, labels and macro boundary must remain exact before and after GDS serialization. Added via PCells may contain only allowed drawing metals/vias, no labels or device layers. Any native cut partially overlapping an original cut is rejected. Original bottom-landings must be present and owned. Foreign native conductors, adjacent-layer vias and different candidate nets are checked before insertion; conservative planning clearance is an early rejection and never substitutes for process DRC.

Nine corruption controls cover endpoint identity, owned path layer, native and wire owner, a foreign terminal point, absent original landing, forbidden device layer, actual foreign conductor and removal of actual original material. Every protected source/PDK input is rehashed at completion. The future controller must additionally restore the exact qualified PDK/runtime and enforce the manifest before generation.

**No native job has run this candidate. No measured resistance reduction, DRC/LVS pass, circuit acceptance or full-PHY claim is made.** Root or peer source review comes first. Fresh full560-rule DRC and unsimplified deep/flat500-device LVS with original faults, strict native planes, finite contacts, seven intrinsic MIMs, both-order precise RC and all original corruption controls must follow. The unchanged ten loaded cases,34.25ns,256bits and original electrical gates may run only after those prerequisites pass. There are no device, bias, waveform, ideal-short, RC-value or acceptance-threshold edits.
