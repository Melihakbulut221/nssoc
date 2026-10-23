# C/D master transfer gain: four native collector loads

The rejected v43 selector area change did not close C/D data or phase.
Return to the source-bound v41 follower_n8 parent, preserving rejected
results and every original gate.

Original full-record diagnosis identifies weak C/D master transfer:
at original edge C master minimum signed output48.0mV, D -3.54mV;
at+0.1UI C54.6mV and D42.6mV. At observed master current handoff,
129 C and123 D master outputs are below the internal100mV diagnostic
marker. Internal100mV is not a new acceptance requirement. Their slave
outputs miss the actual original+0.3UI deadline in65/97 bits.

Parent C/D master data/hold HBT minimum active VCE ranges approximately
0.567–0.815V, verified from original native summary668664370,
SHA9a9c6ff5356e2c5e2da91e04df2f3c76190aff8fd5a1ab400d4ac65ff41b863e.
This motivates testing finite collector-load gain changes, not assuming
new safety. Larger loads also change output commonmode and settling.

Two candidates change only the four actual C/D master rppd collector
lengths2.6um to3.4um or3.9um, retaining32um width and native self-heating.
Actual native output/supply clusters and all four master HBT collectors
identify each resistor. Missing, duplicate, wrong-terminal/model/id/size
and corrupted-output bindings must be rejected.

All A/B, slave, HBT areas, followers, current/bias network, external8GHz
clock10ohm source,150fF/50fF loads, original256bits, full34.25ns record,
solver and device/data/phase/VI gates remain. Four early/late native cases
run only in GitHub. There is no predicted pass or changed clock window.

This is a frozen-wire intrinsic experiment, with84 unique original card
changes including the parent80 and these four new loads. Only a useful
electrical candidate can proceed to actual revised GDS, fresh extraction,
DRC/LVS, fullRC/PVT/loop and serial-mainchip integration qualification.
