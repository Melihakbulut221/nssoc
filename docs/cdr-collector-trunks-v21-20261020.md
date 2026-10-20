# CDR collector routing v21 — physical candidate, not electrical acceptance

The unchanged v20 late waveform failed the original sampling gates despite safe
116-HBT/46-MOS operating limits. Native latch diagnosis reproduced that rejection:
A/B slave inputs are adequate at +0.3 UI but their outputs are late; C/D master
inputs are small. The new passive measurement (run 39432130535) found actual
collector conductor incident wire capacitance of 0.784/0.857 pF on C's source
legs and 0.465/0.514 pF on D's source legs. Filter-output conductor capacitance is
0.231–0.266 pF. These are separate conductor capacitance sums and effective
resistances, not an RC delay estimate or a qualified extraction signoff.

The exact physical route metadata shows that aqn/aqp leave their macro at
x=987.6 um and detour to x=32/43.2 um; bqn/bqp detour to x=390.4/401.6 um.
The candidate moves only these four internal TopMetal1 trunks to
x=959/965/971/977 um in the existing channel. Ten existing TopMetal2 horizontal
arms become shorter; their ten original native TM1/TM2 junction cells move with
the trunks. No extra ideal connection is created. Device parameters, all 16
child placements, child drawings, the schematic, public ports and LEF are fixed.

The generator requires each old rectangle and junction to match actual
serialized geometry, proves the exact fourteen-rectangle delta, rereads the
new GDS and rejects missing metal, missing instances and extra one-grid metal.
The original independent eight-child geometry check and full 484-device native
PDK DRC/deep-and-flat LVS/fault controls run in GitHub Actions. Every failed
generation or physical result is published. No rule is waived.

If the native physical gates pass, extract the **new** parent geometry, repeat
the MIM audit/composition and run the original full early/late 256-bit waveforms
plus stopped-clock and disabled-V/I controls. Retain the original loads,
phase offsets, per-emitter safety limits and acceptance gates. Do not reuse
v20 wire values for v21 or infer waveform success from shorter wires.

PLL 39423618115, TX 39409002976 and mainchip route 39427183963 were independently
confirmed live while this candidate was prepared. Full serial PHY, routed
mainchip closure and final setup/hold remain unaccepted. All CAD/evidence stays
in cloud storage; no local checkout is needed.
