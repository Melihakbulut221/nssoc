# V22 measured master/slave failure locations

Cloud diagnosis39464720493 independently reproduced every116-HBT device measurement and all four original sampler failures from both complete raw waveforms. It retained all physical parallel selector bases and all native graph fault controls.

In the late case, samplerA at0.3UI has216.752mV minimum signed slave input but only30.399mV at its output; its maximum clock-to-valid is44.531ps versus the unchanged37.5ps limit. B has200.067mV slave input and82.844mV output at0.3UI. These observations identify remaining slave-transfer/regeneration delay despite positive input polarity.

C has only12.345mV master input and9.141mV slave input at the expected capture edge. At0.3UI, its master input remains15.834mV and the output has117 wrong-sign samples. D's master input is already wrong for128 edge samples, with minimum signed -15.519mV; its final result still has181 wrong-sign samples. The early case has analogous weak C/D input: C11.236mV and D-22.362mV at the edge; D still has253 wrong-sign samples.

The next design must address both A/B internal transfer time and the C/D loaded retime path. More wire shortening alone is not established as sufficient. Do not relax the original output100mV/0.3UI gates, alter expected bit timing, remove loads, or equate these intermediate voltage markers with a new acceptance test. Physical transistor/level-shift changes require actual native geometry, DRC/LVS, fresh RC and both original phase cases. The previously rejected v17 resistor rebalance remains rejected.
