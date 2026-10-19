# Two-row sampler placement candidate — 2026-10-19

The four width8/16 early/late diagnostic cases all failed the original data
gates. All116HBT/46MOS safety gates passed, but early sampler A worst clock-to-valid
regressed to the measurement cap. Neither diagnostic is adopted into layout.
Full comparison and source summary hashes are preserved in
[evidence](evidence/cdr-width-sensitivity-comparison-20261019.json).

The current native input-drive sampler is 1600.695 x191.63 um; its reported
CLKP/CLKN primitive-center horizontal spans are1275.805/1014.405 um.
This new **unvalidated** candidate retains the exact original circuit and all54
native primitive drawings, including4um input divider resistors. It folds the37
active primitives into two rows at y20/120um with30um same-row clearance and
globally distinct escape columns at least5um apart. Public buses move above both
rows. The actual generator requires each clock span to shrink at least20 percent
and width below1200um. Those span checks are placement objectives, not timing.

The cloud job generates real GDS/LEF, independently compares all54 primitive
drawings and unchanged circuit, and runs the original560-category DRC,
unsimplified deep/flat54device LVS, LEF and16 corruption tests. It does not reuse
the former physical pass. Real routing may fail and failures must be preserved.

Even successful leaf physical checks require new parent assembly/DRC/LVS,
complete native RC/MIM extraction and original full256-bit loaded early/late,
fault and corner waves. No physical, timing, recovered-clock or PHY completion
is claimed here. Existing TX fullwave and mainchip routing jobs remain running.
