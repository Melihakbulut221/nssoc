# Actual gate-poly resistance mesh before complete loaded integration

This worker reads the exact current DRC/LVS-passing650 GDS, full current gate polygons and all200 real contact anchors from authenticated wire41712243960. It regenerates each of50 poly groups from actual GDS geometry, verifies all200 intrinsic electrodes, all200 contact cuts, M1 enclosure, contact centers and ownership, and rejects intersection with SalBlock or pSD. It does not modify the GDS.

A rectilinear finite-volume mesh places boundaries at every actual poly, contact and intrinsic-electrode edge, then refines at maximum600/300/150nm pitches. Every cell must cover exact polygon material; the union and summed area must match without gaps/overlaps. Positive sheet conductances use center distance and common face width. Every complete160nm contact is represented by area-weighted vertical conductance patches whose sum equals its declared conductance. All intrinsic-electrode patch areas sum exactly to the original area, with rational weights totaling1. Full networks and coupling maps are retained in native archives.

Nominal values7ohm/square and15ohm/contact come from the [IHP process control tables](https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/02_process_control_params.html), sections2.7/2.14. The published ranges are6.2..7.8ohm/square and8..20ohm/contact. These are engineering inputs, not narrow-gate calibration or full temperature/corner qualification. The [IHP layer table](https://ihp-open-pdk-docs.readthedocs.io/en/latest/layout_rules/02_layer_table.html) identifies SalBlock28 and pSD14 used for the material exclusion checks.

For each mesh pitch, an independent native SPICE rectangular-sheet test must reproduce the analytic70ohm resistance of a10um by1um sheet, including half-cell boundary distances. The actual gate network is then run in the original frozen native simulator. Diagnostic-only zero-volt sources terminate the real M1 contact ports; uniform total1nA is injected over each actual intrinsic electrode. All200 weighted electrode potentials must be finite/positive, and contact currents must sum to200nA. Refinement changes are reported without claiming general convergence.

Equal-potential intrinsic partition41717942914 passed160 native tests and13696 DC/full-terminal AC comparisons with original W/L/AS/AD/PS/PD retained. This mesh generation does not yet connect those nonlinear models or the actual metal network. It also does not include gate extrinsic capacitance, full MIM/substrate composition or complete loaded/serial qualification. All such acceptance flags remain false. No model gate is silently shorted to a contact.

## Preserve geometry-library numeric type failure

First native run41719493627 verifies every actual gate material/contact relationship and passes the600nm-grid native analytic70ohm sheet reference. Mesh generation then fails because KLayout exposes an integral DBU-squared area as a Python float, while Fraction(numerator,denominator) requires Rational inputs.

The successor checks that each area is finite, exactly integral and below2**53 before conversion to int. It never rounds a fractional area. Geometry, mesh boundaries, material values, source GDS, native circuit checks and current-conservation thresholds are unchanged. The full original failure remains preserved.

## Native refinement evidence and75nm continuation

Run41720040423/source6c1eb9d790cf5caeff98d10784e868e5e1113648 passes all exact material/area/contact checks and all three analytic/native mesh solves. The150nm mesh has53848cells,94084poly resistors and800 contact conductance patches representing the same200 actual contacts. Complete per-gate area weights remain exact.

The maximum simultaneous-uniform-injection gate-average change is0.343038% for600->300nm and2.178391% for300->150nm. These results do not establish general convergence. The successor retains all three prior pitches and adds75nm with identical material values and acceptance checks; no existing tolerance is relaxed. Full nonlinear intrinsic and actual metal-network integration remain open.
