# Actual TX return-path analysis

Complete physical mapping39977012991 preserves all703 native conductor clusters,
8088 devices,140222R and99906C and rejects4 actual device-binding corruptions.
82 of85 low-VCE devices have bases connected to original clock ports. The other
three are output-tail xd5644 (base tr) and final-tail xd5667/5674 (base mr).
Their emitter nodes connect through finite extracted metal to AVSS.

At their respective minimum-VCE instants the emitter voltages are:
xd5644 0.11115259694292916V, xd5667 0.08669510390288371V,
xd5674 0.08666668371428174V. These are different measurement instants; they are
not a common snapshot or a proven standalone explanation of all85 failures.
Reducing clock common-mode alone can consume tail-device headroom.

The new cloud reader computes grounded sparse DC conductance of the unmodified
AVSS resistor graph, with unit current injected at each of these three actual
emitter reference planes. It checks KCL residual, reciprocity, positivity and
the shortest-path resistance upper bound. Series/parallel analytic controls and
a disconnected-target rejection protect the calculation. Every shortest path
and its largest resistance segments are retained for physical routing review.
No R/C value, terminal, device or original gate changes.

This resistance matrix is a routing diagnostic. It does not substitute for the
actual multi-source loaded IR drop, transistor simulation, capacitive transient,
device-access/substrate extraction, GDS/DRC/LVS, full serial PHY or mainchip timing.


Run39978950673 passed:11693 nodes,15648 resistors in the original AVSS component,
maximum KCL residual3.637978807091713e-12A. Effective self-resistances for
xd5644/xd5667/xd5674 are10.326486441861093/6.286958767402294/6.275982084626535ohm.
The latter two share2.35779442271229ohm transfer resistance. The output-tail
branch has zero transfer to them under the ideal publicAVSS ground constraint.

The output shortest path includes r139947=9.87597ohm adjacent to avss. Shortest
path size alone is not a contribution estimate in a parallel network. The next
read-only sensitivity run computes each original segment's unit-injection
current and I-squared-R contribution, requires their sum to reproduce effective
resistance, and retains original extractor-node identities for physical mapping.
No resistor is removed/scaled or assumed to be a physical fix.
