# Three fixed physical clock-bias substitutions

The actual wire24 capture was rejected: 83/768 wrong-sign samples, 104 below 100 mV and 24 HBT headroom failures. Run 39370785088 reproduced every original engineering gate exactly and inspected the original native resistor-connected selector bases. The waveform itself was not regenerated.

The native conductor mapping assigns 18 failing selectors to bias groups2/3/4: sp8_1 (4 devices), sp8_3 (4), sp8_5 (4), sp8_6 (2), sp8_7 (4). Their minimum VCE values range from 0.382584 to 0.399526 V against the unchanged 0.4 V bound. The four final selectors and two final tails are separate failures; this candidate does not claim to fix them.

The experiment replaces only the three l6p25 clock-reference instances at groups2/3/4 with the existing physically verified l5p7 six-device RC macro. Group0 retains its existing l5p7 macro; the other seven groups retain l6p25. Both source macro GDS/extraction/model hashes and all native components are restored and checked. This is an explicit composition change, not an arbitrary change to stale parasitic values.

Measured selector-base common mode at the original middle groups was about 1.394–1.412 V. The lower-bias macro in group0 was about 1.343–1.390 V under its different actual load. This motivates a hypothesis that lower selector-base bias can recover middle-stage headroom; it does not predict the new loaded voltages or prove improved bits. All three groups remain fixed across corners.

Before simulation, the candidate rechecks the exact failed-waveform summary and native clock-terminal graph, and verifies that precisely these groups own the 18 affected failures. The native adapter binds every actual macro, retains all terminal/current probes and rejects five concrete corruptions per group, including substitution of the wrong native macro. All 55 controls must pass.

The unchanged full wire32 test retains original 34 ns duration, 256 source bits, three sample phases, 604 HBTs, 512 MOS devices, all interface bounds, native OFF/readback and original solver controls. Normal and actual leaf-selector fault captures are independent cloud jobs. A passing fault case is not a nominal pass.

No new assembled PHY GDS or mainchip integration is claimed by this composition experiment. Full intermacro physical routing, qualified PEX, PVT, final-stage repair and full serial PHY closure remain required. If this candidate succeeds, carry the exact changed macro instances into physical integration; do not reuse the previous full assembly as evidence for the new composition.
