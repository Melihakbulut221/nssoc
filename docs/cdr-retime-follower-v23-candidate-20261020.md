# Native CDR retime follower candidate
The exact v22 diagnosis shows weak C/D master inputs and late A/B slave transfer.
Shortening retime routing alone did not meet the original loaded data/phase gates.
This candidate replaces one differential passive retime attenuator with two native
npn13G2 Nx4 emitter followers and two native rppd w=4um/l=4.5um pull-down resistors.
Collectors connect to the existing AVDD rail; bases take the original A/B signals;
emitters drive the C/D input pair. This is a circuit hypothesis, not a pass claim.
No ideal amplifier, synthesized clock, new bias source, reduced load or changed
acceptance threshold is introduced. Native finite substrate contacts remain.
The initial cloud campaign builds a real seven-port leaf and checks all560 DRC
categories, deep and flat eight-device LVS, wrong resistor, wrong HBT multiplier,
missing HBT, collector/emitter swap, actual output open, actual input short and
offgrid geometry. Existing rejected v22 source and evidence remain immutable.
A physical pass alone does not establish useful common mode, speed, headroom or
closed-loop CDR. Both parent retime instances must subsequently be replaced,
AVDD physically routed, complete parent DRC/LVS and fresh RC repeated, and the
original loaded early/late waveforms and fault/device checks passed. Full serial
PHY, x4/mainchip integration and final timing remain open.
All generation, simulation and physical validation run on hosted cloud runners.
