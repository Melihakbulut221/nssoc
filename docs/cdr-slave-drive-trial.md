# Slave sampler drive/load experiment

This is an exploratory circuit change, not an accepted PHY or a matching physical layout.
The authenticated full-wave diagnosis41497066977 reproduces every original per-bit final-output delay. Actual clock-selector zero crossings lag the ideal clock by1.5625..4.6875ps; original A/B/C/D output maxima remain45.78125/41.71875/51.09375/54.53125ps against37.5ps. At representative worst A/B/C transitions, master output and slave input already have the expected polarity while the slave output remains old or below100mV. D also has an upstream late-data contribution. These observations motivate a slave output-drive experiment; they do not prove a sole cause.

The original collector Via2 full500 freshRC41439516945 remains the parent. This experiment does not compound either failed C/D bias trial41458294059 or41494299114.
Exactly24 devices change:
- Eight slave collector pull-up rppd resistors SA/SB/SC/SD_S_RP/RN: L2.6um to1.9um, W32um unchanged.
- Sixteen slave tail NMOS devices SA/SB/SC/SD_S_T0..3: W36um to48um, L0.3um unchanged. Consistent provisional diffusion parameters AD/AS12.24p to16.32p and PD/PS72.68um to96.68um use the parent's0.34um diffusion extension (AD=W*0.34um, PD=2W+0.68um). These formulae are a proposed device geometry, not an extracted geometry.

A first-order sheet-only output resistance reduction of26.923% and nominal width/current increase of33.333% predict an I*R product of0.97436 times parent. This is a hypothesis only; nonlinear bias, contacts, feedback, device capacitance and real metal resistance may invalidate it. Current density, voltages, full waveform, phase/current and all final-output gates remain active. No HBT, reference bias, master stage, C/D input divider, stimulus, clock, measurement threshold or150fF output test load is changed.

All24 targets are joined to actual complete500-device LVS mapping41450661063 with exact native terminal/parameter checks. Every changed primitive token and the complete model/contract must reverse exactly to the authenticated original; the other476 primitives and every interconnect R/C card remain identical. Source controls test all24 primitive roundtrips and14 refused malformed cards; original29 definitions,5 executable blocks,9 numerical source files,13 admission refusals and actual13 binding refusals plus2 equivalent-unit cases remain mandatory.

Changed intrinsic MOS diffusion/model capacitance is simulated, but fixed parent interconnect RC is explicitly provisional. A numerical improvement or pass cannot be promoted to physical acceptance: schematic and GDS generation, DRC/LVS, canonical terminal identity, new parasitic extraction and repeated loaded simulation are still required. Full closed-loop serial PHY, PVT, ESD/EM, mainchip integration and final STA are not proven by this experiment. All execution and native evidence remain cloud-only.
