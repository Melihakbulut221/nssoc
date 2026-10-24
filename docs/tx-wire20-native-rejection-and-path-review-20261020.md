# TX wire20 full32 rejection and native-path diagnosis

Run39409002976 nominal captured the original34ns/256bit full physical1674-device
core with116611R77538C, eleven physical clock-reference/feed macros,
604HBT and512MOS. It returned0 and retained77562 native rows. Acceptance failed:
79/768 output samples have the wrong sign and97 are below100mV; six HBTs
still fail the original0.4V active VCE gate. No MOS failed.

Final-interface samples include540 wrong signs and1612 below150mV; level4
has117 wrong signs and2142 below150mV; level8 has0 wrong signs but27 below150mV.
Level16 and CMOS inputs pass their interface gates. These aggregate figures
do not establish which physical node first causes an error.

The read-only cloud path review restores the exact raw capture, original
contract, original bias operating point, native interfaces and actual wire20
composed model. It reproduces the entire original review literally before
mapping every failed HBT to terminal voltages and original-bit interface
samples at the unchanged0.3/0.5/0.7UI phases. Only source/candidate identities
differ from the prior wire24 reviewer. No new SPICE run, phase adjustment,
oracle substitution, threshold change or data regeneration is used.

Keep the rejected waveform and device violations. Determine data-arrival and
selector/tail headroom causes before the next physical repair. This diagnosis
does not accept TX or the full PHY. Ideal external modulation/supply and
intermacro clock connection assumptions remain open.
