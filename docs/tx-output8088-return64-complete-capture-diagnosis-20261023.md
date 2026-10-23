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


The first read-only run39972075681 rejected archive inventory equality before
electrical review. The exact original workflow appends criu-build.log after
writing result.json. The corrected reader permits exactly this one extra member,
requires every original output hash unchanged and all selected files present,
and still verifies every archive byte. Five additional corruption checks reject
changed/missing raw, extra member, missing build log and changed embedded summary.
The failed diagnostic remains published; no native simulator is restarted.


Run39973764125 passed the read-only diagnostic. It reproduced the full original
review exactly and rejected13 source,5 archive and5 actual aggregate corruptions.
The electrical design remains rejected. Every one of85 HBT failures is minimum
VCE below0.4V; no maximum VCE/VBE/current or MOS violation occurred. Worst
xd5676 reaches0.34511908405080094V at18.02690522679898ns:
C0.9102081725906641V,B1.4446111903834702V,E0.5650890885398632V.
Actual per-emitter current there is0.9407995397877761mA.

Six differential interface pairs fail the150mV differential margin: a,b,p4_0,
p4_3,p8_0,p8_7. Pair b has45 wrong-sign samples and a has9. The three source
phases and every physical parallel base pair are retained. CMOS pairs additionally
fail common-mode. Direct voltage-node equality does not identify the failed
HBT bases as interface bases; the new physical-graph diagnostic therefore maps
every failed terminal through the original140222 resistor graph and archived
composition device records. It does not equate voltages across finite resistance
or prove a causal repair. See the new failure-topology cloud workflow.
