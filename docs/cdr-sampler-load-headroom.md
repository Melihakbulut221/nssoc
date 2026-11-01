# Original-master output-load experiment q15

The preceding24-resistor native run41274791029 (sourceeca0c5abf194169c8b42f58a48f22feb716e7dec) completed normally, but was electrically rejected. Its exact-source complete comparison41276473135 passed13corruption controls and authenticated all original predicates. All124HBT,50MOS,7MIM and original tail-current checks passed in that nominal case. Every data stage still failed, phase mean was5.619mV and VI current19.073uA; VI voltage5.209mV passed its5mV floor. This is not physical or fullPHY acceptance.

## Controlled question

The24-resistor case changed both the input-buffer divider and the8master-latch loads relative to the previous12-resistor case. The latter had B passing, whereas the24-resistor case had B's minimum margin62.216mV and maximum delay118.906ps. Those coupled changes do not establish which change caused the regression.

This experiment restores all8master-load lengths to their original2.6um while holding the new buffer values fixed. The two predeclared sibling experiments differ only in the8slave/output load lengths: q15 uses1.5um, q20 uses2.0um. Comparing q15 with the24-resistor case isolates master restoration; comparing q20 with q15 isolates output load. Restoring output swing may improve reaching the fixed100mV threshold, while increased resistance can also worsen settling and change headroom. No pass or improvement is assumed.

## Exact delta from authenticated original baseline

* 8 slave/output collector loads XD0175/176/191/194/202/205/212/214: L2.6 -> 1.5um, W32 unchanged.
* 4 input-buffer pullups XD0182/183/220/221: L1.8 ->1.0um, W8 unchanged.
* 4 input-buffer shunts XD0184/185/222/223: L5 ->3.4um, W4 unchanged.

Exactly16length tokens change. The8master loads XD0177/178/195/196/207/208/215/216 retain original L2.6/W32. All other500-device fields, model bytes and baseline wireRC are unchanged. Original prepare/measure executable bodies, clock/data waveforms,1151vectors,10ohm source resistance,150fF sampler/50fF XOR load and every electrical threshold remain unchanged. Source controls require17circuit corruption refusals and5archive refusals; the original13actual binding controls still run before native measurement.

Run source controls first. Before simulator start, independently reserve and read back an empty exact-source release. All computation and native outputs remain onGitHub. Retain every success and failure.

This is an intrinsic screen with baselineRC, not a generated layout. The24-device map is insufficient for physical editing because masters now remain untouched. The collector PCells are shared with those masters; a passing16-device candidate requires selected-instance private cells, a new complete physical mapping, native DRC/LVS, freshRC, corners and closed-loop/fullPHY verification. Do not globally change the shared collector cell definition.
