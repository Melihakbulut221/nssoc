# CDR slave parallel2 with lower divider impedance

Preceding native screen run 43482979273, source ea738250b5aa2719444d5d67b2c1c710564b6163,
finished with process rc=0 and passed device/phase gates, but failed data gates.
Sampler B passed; A/C/D failed. X had 424 wrong-sign samples / 765. No acceptance.

Derived comparison run 43497607363, source b1dae4a565ea0e85f667ae791635834601443f27,
artifact 14073410383 (SHA256 d4a0fee9e6b72ac473cb05cec26a1806d900ecc5345df2255074ef3300cd0787),
compared original lowz4_bd10 to bd10_slave_parallel2. The best positive waveform
correlation lag was unchanged at the 16 samples/UI diagnostic resolution:
samplerA->bufferA input 0.3125 UI, bufferA input->output 0.3125 UI;
samplerC->bufferC input 0.375 UI, bufferC input->output 0.3125 UI;
samplerD->select0 input 0.4375 UI, select0 input->output 0.1875 UI.
Correlation is not causal propagation delay, and is not an acceptance gate.
Some amplitude margins worsened despite improved B sampling.

The next hypothesis is excess divider/interface impedance. Compared with
bd10_slave_parallel2, change ONLY the same twelve divider resistor widths
from 4um to 8um, retaining lengths, six MIM dimensions, BD pull-up width,
64 slave-tail MOS and eight collector-resistor multiplicities m=2. The
lower impedance also increases sampler loading; this tradeoff may fail.
No bench bias, clock, source bits, output loads or acceptance limits change.
The simulator process must exit zero as well as every frozen waveform gate pass.

This uses previous extracted wires as a what-if. Effective device multiplicity
is unchanged from parallel2 (+72 over the original). It is NOT new layout,
extracted geometry, electrical signoff or a complete serial PHY. Only a passing
candidate warrants physical regeneration and full PVT/parasitic validation.
