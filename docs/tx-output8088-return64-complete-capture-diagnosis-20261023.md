# Actual8088 return64 TX: complete rejected capture diagnosis

This reads the immutable full capture of run39957261794. It does not rerun the
simulator or alter source bits, clock phases, loads, solver, data windows, or
electrical gates. The normal34ns capture has85 failed HBTs, zero failed MOS,
14 wrong-sign output samples and32 samples below100mV.

The original CMOS interface fails its1.8V minimum common-mode requirement even
though all sampled differential margins exceed150mV. Its measured range is
1.7524871524056675 to1.8013822257963321V. The final interface also has54 wrong-sign
and369 below150mV samples. Level4/8 show126/63 below150mV samples. Level16 passes
its original interface screen. None of this is repaired or accepted.

The cloud-only reader verifies every archive part and complete tar hash, hashes
all original output members, extracts the exact raw/contract/OP/bench, and
reproduces the original complete review exactly. It then partitions every
original interface sample among62 differential inputs, preserving all failing
samples and direct HBT base identities. For each failing HBT it records the
actual native violation times, terminal voltages, and per-emitter current.
Thirteen source-corruption controls and five aggregate-corruption controls
must reject changes. Full capture is77706rows by14182columns at original34ns.

Direct terminal identity is diagnostic; it is not an assumption that nodes
connected through extracted resistors have identical voltage. The next circuit
repair must use these measured endpoints and the original physical device map.
The source release remains intact; the read-only diagnostic publishes a compact
receipt, retaining hashes rather than a second multi-gigabyte raw copy.

This does not close TX electrical gates, CDR/PLL, serial PHY, routed mainchip,
postroute timing, foundry extraction, DRC/LVS, ESD, or production approval.
