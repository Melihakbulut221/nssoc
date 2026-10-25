# Fresh v16 CDR RC: capture passed, raw audit and composition pending

All four extraction stages in run39335172776 passed against the physical
v16 GDS c920186862bde235868d3fa009fedcff868246750f0fa38874e3c6b42ba7255e.
MIM-aware capture39336054657 also passed: 17674 resistors,12709 capacitors,
11 native MIM devices,111 physical conductors and946 reference points.
The five original capture corruption controls remain enabled.

These are the actual fresh extracted counts, not acceptance thresholds or
old v15 R/C reused on new geometry. Electrical behavior is still unproven.
The new raw audit verifies every exported R and collapsed C against native
extraction and runs the unchanged13 wire plus9 intrinsic-MIM fault controls.
Composition subsequently retains each intrinsic MIM exactly once and runs
the original19 composition corruption controls. The source delta changes
only version identifiers, receipt dates and measured geometry census.

All five source receipts are pinned to completed GitHub runs, source commits
and release asset digests. The audit/composition workflow fails closed on any
source mismatch. Its success would enable loaded original fullwave checks;
it would not constitute qualified PEX, closed-loop CDR or full serial PHY.
