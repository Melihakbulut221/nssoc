# Actual TX v5 failure locations

Run39085786545 bound every restored physical file to the original full-wire simulation's protected hashes and mapped all eight failed HBTs into exactly one native macro each.

Six failed HBTs xd0109/0110/0111/0112/0114/0115 are in the final macro `f`. The first four are on the native `sp`/`sn` clock conductors. The final two use the `mr` bias and distributed `avss` emitter return. Their shortest raw-resistor paths from the public AVSS port are approximately16.19/16.22 ohm; largest individual segments are4.53,2.83 and2.00 ohm. These are shortest path sums, not effective resistance measurements. The original waveform gives their emitter mean near0.172V and minimum VCE below0.295V.

The remaining two failed HBTs xd0515/xd0521 are in macro `p8_7`, on native clock conductor `sp8_7n`. Their original VCE minima are approximately0.398V. This identifies a second local limitation and prevents attributing every failure only to the final return.

The v5 parent currently has32um AVSS trunks/bus,32um child stubs and a4um final local return strap. A physical repair must use this exact v5 source; the older high3/tight return64 layout is a different circuit/placement and cannot supply its RC or acceptance proof. Actual stage failures, all native HBT failures and original bit/phase gates remain open.
