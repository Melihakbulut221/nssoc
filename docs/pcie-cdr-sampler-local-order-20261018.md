# Native CDR sampler placement candidate

The complete repaired power484 screen39141648105 still fails data/phase and
53/52 HBT gates. Actual path review39142648950 reproduces those failures.
The prior waveform showed up to about150mV collector-to-base drop on the
same sampler output feedback conductor. Full-parent clock/output wire
capacitance remains significant. XOR source access improvement alone did
not repair sampler behavior.

This candidate changes only the physical order of37 active/passive primitives
inside the existing54-device sampler. Native PCell widths and original18um
clearance determine exact positions. Deterministic pair swaps and segment
reversals reduce weighted native-center spans, prioritizing master/slave
output/feedback nets, clocks and data. This is a geometry planning objective,
not a timing model or an acceptance criterion. All dimensions, source circuit,
route widths, native via arrays and17 finite substrate taps remain unchanged.

The original560-rule DRC, unsimplified deep/flat54-device LVS, fourteen actual
fault controls and native LEF readback apply. Exact source-delta checks retain
the prior generator/checker/controller and all original checks. No transistor
or waveform gate is relaxed. A leaf physical pass must be followed by full
parent integration, independent primitive/route identity checks, fresh native
MIM-aware RC and all original loaded early/late/fault screens. Full PHY,
closed-loop recovery and mainchip timing remain unproven.


First run39143329188 stopped during generation: a distributed body tap had no
independent M4 column within the old plus/minus3um search window after the
primitive reordering. Native DRC/LVS was not reached. The correction expands
only the eight distributed taps' nearest-safe search to plus/minus20um. All
nine local MOS taps keep their original search and primitive-clearance checks;
all taps retain the original2um M4-column separation, area/perimeter and
finite reference devices. The failed source and logs remain archived.
