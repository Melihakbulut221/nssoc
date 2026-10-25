# Fast assertion candidate after the retained four-case diagnosis

The immutable four-case run40093613768 remains numerically rejected. Exact cloud readback40095334893 verified every355saved vector plus time for all34ns and reproduced that rejection. All106 HBT safety screens, the held asynchronous presets and first-fall release screens passed in the retained waveforms, but three cases failed the unchanged fixed output sample oracle.

The measured cause is concrete: reset begins at12.03125ns; the first fixed UI center is12.0625ns. The release FF output clears at12.05928–12.05932ns, then a master/slave output needing a new preset does not cross until12.08190–12.08269ns. This is50.65–51.44ps assertion latency against the original31.25ps opportunity. P/initial-high happens already to have the desired signs; its passing sample is not evidence that reset is fast enough.

The candidate adds a direct real ARM path to the existing XRUN input network. Two native rppd W2/L3.6 resistors feed ARM_P/ARM_N into the same differential HBT base nodes that already receive the real release pair. One native rppd W1/L32 shunts the positive base, creating a fixed negative decision offset. Thus both ARM and release must be positive to run; asserting reset need not wait for the serial release FF before it reaches the run selectors. The existing release FF still controls deassertion and the first actual parent falling edge.

This is an actual244-device source candidate:106HBT,130rppd,8MIM. The original241 compact devices, current/clock stacks, first-fall FF and two P/P orN/P parent orientations recover byte-for-byte after undoing the two XRUN call changes and removing the new level definition. Only three resistors are added to the instantiated source. No ideal internal driver, injected initial condition, fitted phase, changed frequency or threshold relaxation is introduced.

The nominal passive calculation is solely a design check. It assumes equal sheet resistance, no contacts, no HBT base current and no temperature dependence. It predicts the desired sign for16 declared ARM/release combinations; it does not establish actual loaded transfer, gain, delay, voltage safety or a stable measured envelope. The geometry is chosen for a negative decision margin in the mixed input states, not by moving the old sample times.

Required next proof is the same four finite-time34ns cases with the original clock/ARM schedule, all106 HBT safety bounds, every original fixed UI center and full capture. Newly added thermal states must also be saved. A rejection must retain its full evidence. Actual base loading may invalidate this simple passive logic and is a reason to reject or redesign, not to waive the oracle.

The independent NaN-temperature/dynamic-gmin startup issue remains open. The all-zero recorded OP does not erase the earlier diagnostics. Any separate initialization-method repair must retain exact device parameters, prove its actual simulator behavior and zero-source OP, never choose a differential startup state, and pass the same unchanged transient gates.

No new circuit transient, new layout, load/tree qualification, real reset distribution, PLL connection or full-PHY acceptance is claimed by this source addition.
