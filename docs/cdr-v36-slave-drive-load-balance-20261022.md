# CDR v36 slave drive and load balance

The complete v35 diagnosis reproduced all original failures. Master outputs reach the diagnostic100mV marker by the original37.5ps deadline, while many slave outputs are still below the actual100mV output gate. Reducing collector resistance alone improved primary sampling but also reduced the swing feeding secondary samplers. Increasing HBT area alone in v34 did not close the output timing.

This screen tests a coupled physical-design hypothesis: increase only slave tail width and matched HBT emitter area by1.5x, and reduce only slave collector load resistance. This may preserve current density and signal swing while reducing the time required to charge the unchanged150fF loads. Actual current, swing, safety and timing are measured; neither scaling assumption is acceptance evidence.

Two explicit candidates retain every original master primitive, all clocks, external bias currents, stimulus, phase, waveform columns, samples and acceptance gates:

| Candidate | Slave tail MOS | Slave selector/data-hold Nx | Slave collector resistor |
|---|---|---|---|
| slave_drive15_load12 | four54um/0.3um devices per slave | 3/6 | width32um, length1.2um |
| slave_drive15_load10 | four54um/0.3um devices per slave | 3/6 | width32um, length1.0um |

Both retain the earlier eight disclosed bleed12 dimensions. Native topology identifies exactly32 slave HBTs,16 slave MOS and16 slave resistors; every other primitive card and every17918R/12850C wire card remains unchanged. Reversing the declared parameter edits must reproduce the exact original composition.

The MOS intrinsic diffusion fields use a disclosed single-finger rectangular hypothesis:54um by0.34um, area18.36um2 and perimeter108.68um per diffusion. The original extracted36um cards must first verify area12.24um2/perimeter72.68um. These candidate dimensions are NOT new GDS or extracted parasitics. Nine corrupt-geometry controls reject inconsistent baseline inputs.

The source adaptation separately identifies the necessary width inventory checks. It leaves the original120HBT/46MOS voltage and current gates, capacitor limits, loaded sampler checks, phase and VI limits untouched. All original corruption controls remain.

Any useful result still requires actual candidate PCells, routing, DRC, unsimplified LVS, fresh intrinsic and wire extraction, and the full original loaded/PVT/closed-loop sequence. No physical or PHY acceptance is claimed by this exploratory frozen-RC screen.
