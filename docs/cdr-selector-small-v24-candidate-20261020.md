# CDR v24: smaller physical clock selectors

The v23 diagnosis (39487495346) independently reproduces all 120 HBT measurements, both violating HBTs, and all four original 256-bit sampler checks for both nominal captures. The two below-0.4V VCE devices are the C sampler's actual master track selectors. Late actual selector-base clock crossings are about 3–5ps after the external crossings; median native slave track-current onset relative to expected edges is about 14–16ps. These are measurements, not a timing closure claim.

Candidate v24 changes only eight selector HBTs in each sampler from Nx4 to Nx2. Data/regeneration HBTs remain Nx4; MOS tails, reference bias, load resistors, input resistors, device counts and all original waveform acceptance limits remain unchanged. Prior v23 late peak selector current per emitter is 1.1894mA maximum; holding total current fixed would give about 2.379mA at Nx2, below the unchanged 3mA limit. That scaling is a design estimate; new nonlinear transient measurements are mandatory.

The physical cloud job creates actual Nx2 PCells at the original 37 primitive positions, compares all 46 unchanged primitive drawings and the ten original ports, and runs the complete 560-category DRC, unsimplified 54-device deep/flat LVS, LEF and original 18 fault controls. Smaller selectors are intended to reduce capacitive delay and improve selector VCE through changed VBE; neither effect is assumed accepted.

Still required after a physical pass: replacement in the actual v23 parent, retaining/reapplying its real collector/retime straps, fresh whole-parent extraction and all original loaded 256-bit electrical gates. No old parasitics may qualify the new geometry. Full PHY/mainchip integration remains open.
