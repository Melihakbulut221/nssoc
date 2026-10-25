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

Initial generation39231848138 was rejected before GDS output: CLKP span fell to
428.330um but CLKN only to915.105um, missing the declared20percent reduction.
The original span gate remains. The revised real placement groups all eight
unchanged clock-selector HBTs at the front of row2; other devices retain their
relative order within their group. All54 native drawings,30um row clearances,
5um global escape-column clearance and all physical faults remain required.

Second generation39232466808 passed the clock-span/outline planning checks but
rejected a local MOS body-contact route before producing GDS. The revised planner
reserves each real local MOS contact center (x+4um) together with all escape
columns before the other row is placed. The5um separation and native tap geometry
are unchanged; this is an actual placement reservation, not a waived check.

Native leaf run39232996365 passed:560mainDRC categories/zero markers,
unsimplified deep/flat54device LVS, all16 original corruption controls and
independent all54 primitive drawing conservation. GDS outline1003.0x291.63um;
CLKP/CLKN horizontal spans477.985/263.480um. Some internal spans increased
(M_SE454.12->761.45um); no electrical improvement is inferred from clock span.
The folded-v11 parent workflow now restores this exact leaf four times with
the seven other child types unchanged, keeping the original41 source cards,
16 macro instances,484 native devices and all parent physical fault tests.
Fresh full parent RC and original loaded waves remain mandatory.

Full parent39234425893 passed native560-category DRC, unsimplified deep/flat484
device LVS and original parent fault controls. The new physical source is now
bound to fresh planes, wire-inputs, native device binding and raw RC extraction.
The pipeline retains158 planes/51 logical nets/1394 native terminals, independent
16macro/eight-child geometry checks, source-pin recovery on identical primitives
and all prior binding/RC corruption tests. Actual R/C census will be measured,
not copied from the prior layout. No timing or full-PHY acceptance follows yet.

Fresh extraction39235222638 passed native planes, wire-inputs, device binding
and raw wire RC audits with all original fault controls. All four complete
source-bound receipts are committed. The full-mask MIM capture now uses this
actual new parent RC and device binding, preserving all11 intrinsic MIM devices
and their native terminal ownership. Wire-only RC is not a qualified full-PHY
parasitic model; full-mask audit/composition and loaded waves remain required.

Fresh full-mask capture39236131141 passed:15482R/11590C and exactly11 native
MIM identities,111 components and946 points. These are measured counts from
the new geometry; they replace only the old census fields in downstream
auditing. All raw value/point/ownership/conservation and22 corruption gates,
plus19 composition controls, remain unchanged. Strict audit and composition
run next; capture alone does not qualify body/RF PEX or full-PHY timing.

Full-mask audit/composition39236937640 passed original22 raw and19 composition
controls. The complete fresh model contains484 native devices,15482R/11590C and
11 intrinsic MIM models, with each cap projected exactly once. The full loaded
streamed matrix now tests nominal early/late plus clock-stopped and VI-bias-off
faults, retaining all original256 bits/34.25ns/.3125ps,1107 vectors,150fF/50fF
loads, source impedances and fixed sampling/device/phase/current gates.
Only model identities and the measured C census changed in the test runner.
No pass is assumed before the actual complete waveforms are reviewed.
