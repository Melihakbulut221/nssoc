# TX critical intermacro routes: 2.0um physical candidate

The fresh group234 waveform39372036289 still fails83/768 output signs and104
samples below100mV after eighteen selector-device violations were removed.
Its exact-capture review39399643386 reproduces every original electrical gate.
The weakest level8 leg is p8_7 (minimum signed margin0.143745V against0.15V);
level4 p4_0/p4_3 already have wrong-sign samples, and final a/b inputs remain
wrong. The separately simulated final differential bridge39376417214 improves
headroom but worsens output errors (87/768). Neither is accepted.

This new physical candidate narrows the same28 parent data trunks and stubs
from the shared4um baseline to2.0um. The previous wire24 candidate used2.4um.
Thus the two candidates differ only in the specified parent route width:
all1674 devices,31 macro placements, native child geometry, vias,4um
landing squares, clocks, power/return wiring, external pins and schematic
remain identical. No existing extracted R/C is scaled or substituted.

IHP's published [main DRC rules](https://ihp-open-pdk-docs.readthedocs.io/en/latest/verification/drc/02_main_rules.html)
list TopMetal1 minimum1.64um and TopMetal2 minimum2.0um. Both routed layers
use2.0um here. The actual pinned native560-category DRC and deep/flat LVS
remain mandatory; the published table is design guidance, not signoff.

The hypothesis is that reducing parent conductor loading can improve the
remaining data-arrival margins. Higher metal resistance can offset that
benefit; no delay or transient improvement is assumed. The serialized-GDS
geometry comparison and three actual geometry faults are retained, followed
by unchanged native circuit/short/open controls.

Only a physical candidate is created now. It requires fresh full-parent RC,
native device binding, exact composition, original34ns/256bit nominal/fault
screens and PVT checks. The six final HBT headroom failures remain separate
unclosed requirements. Source stimuli, sample phases, emitter budgets and
device voltage limits are not changed to pass this experiment. All execution
and artifacts remain in GitHub; no local CAD files are created.
