# Fresh CDR loaded screen and retained TX path diagnosis

The v16 CDR fullwave workflow waits for exact validation39337079644 at
b13f95047c5b3cd4a9ef90c8531580c7f8a5596b. It verifies both successful jobs,
release digests and capture-to-audit-to-composition provenance before simulation.
All original13wire+9MIM and19composition controls must pass.

It runs nominal early/late input phases and the original stopped-clock/VI-off
fault cases on the complete484-device,17674R,12709C model. The original256bits,
1107 vectors, external8GHz clock, fixed sample phases,150fF sampler loads,
50fF comparator loads, HBT/MOS/capacitor/current gates and dependency hashes
remain unchanged. Fault detection alone is never nominal electrical acceptance.
This is not recovered-clock CDR or full PCIe PHY qualification.

TX path diagnosis39336705951 reproduced every original gate on the unchanged
39308903140 fullwave. Final input groups b/a account for432/405 wrong-sign
interface samples. p4_3/p4_0 account for144/108; p4_1/p4_2 retain positive
polarity but inadequate margins. p8_7 and p8_0 have minima124.82mV and134.99mV
against the original150mV interface threshold. These counts include multiple
physical-terminal pairs and must not be presented as independent bit errors.

The lowest measured HBT VCE is at xtree.xd0109:0.3561841964V at5.158282802ns.
Actual collector/base/emitter voltages are0.9303198885/1.4573091421/0.5741356921V.
The read-only diagnosis also preserves actual resistor-connected clock-base
edge brackets. These observations localize failures; they do not establish
a causal repair. The failed TX result remains rejected.
