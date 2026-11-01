# A/C divider with original C/D output loads

This controlled experiment starts from the rejected A/C-divider candidate sourcee2e753c37fcff8b8fef85695208b8157a7399b57, actual native run41280806504. Its clean731.256152s simulation passed device predicates but only samplerB passed data validity. A/C-divider changes raised phase13.177843mV andVI42.150650uA relative to q15, still below30mV/50uA; A/C/D andX/Y timing remain rejected. Full64-file terminal proofe5bd8c9efb5ce8726416f0366b42eeb28aca19e1 and actual16-control comparison41282030219/full15prooff1dc2fcb4893382082993f15595647a0c50628e5 preserve all original measurements.

The q15 same-time diagnosis41282425236/sourceae6db2f7ee9a11bad03154f5401ca9837a3db6fb authenticates complete C/D follower, input-buffer, master, slave, hold and clock topology. At the worst original sample at3.1ns, C slave input differential magnitude is140.084623mV but output33.754185mV; D input157.171451mV but output22.772750mV. Same-time differential collector currents are4.212637mA and4.548597mA. These are transient snapshots, not a DC Ohm-law estimate or proof of a particular fix.

## Exact new hypothesis

Restore the four C/D output-load resistors XD175/176/212/214 from the prior candidate1.5um/W32 to their original2.6um/W32 by removing them from the intrinsic rewrite. Keep A/B output loads XD191/194/202/205 at1.5um/W32. Keep original master loads unchanged, prior four buffer pullups1um/W8, four shunts3.4um/W4 and eight A/C divider lengths1.8um/10.8um,W1.

Exactly20 intrinsic length tokens differ from the authenticated original500-device model. This separates retimed C/D loading from A/B loading. It may improve output amplitude but may worsen settling or voltage headroom; the existing original whole-model gates decide. The earlier global q20 output-load sweep is not a proof of this mixed-load candidate.

Source controls authenticate every selected original parameter/ordered native terminal, preserve exact untouched C/D synthetic cards and all other original bytes/metadata, and retain21 corruption plus5 archive refusals. Actual preparation retains13 original binding refusals. Original prepare/measure bodies,1151vectors,10ohm sources,150fF sampler/50fF XOR loads,stimulus and all electrical limits are unchanged. D-selector divider networks, every MIM and HBT size stay unchanged.

All work executes on GitHub. Only a successful exact-source control proof and independently reserved empty exact-source release admit the actual simulation. Baseline distributed RC is retained for this intrinsic experiment; no new layout/fresh PEX/closed-loop/fullPHY/finaltiming acceptance is claimed. Preserve all failures. Do not reuse the prior24-target map as proof of a new regenerated layout.

## Completed native result

Controls41282742236/source8c7b5cdd86447fe374ae06064f2fef735a7c9b91 passed21 mutation and5 archive refusals. Independent empty exact-source release430414047/tagcloud-results-41282867236-1-cdr-sampler-load admitted exactly one native41282867236.

The engine completed in706.750878665s with exit0, no diagnostics and unchanged sources. Device predicates passed, including all124HBT,50MOS,7MIM and tail groups. The complete circuit was rejected under unchanged electrical gates.

| Stage | Maximum delay ps | Minimum signed margin mV | Below100mV samples | Wrong-sign samples | Pass |
| --- | ---: | ---: | ---: | ---: | --- |
| A |41.40625|65.242374|97|0|no|
| B |37.34375|105.191923|0|0|yes|
| C |118.90625|-12.305347|160|27|no|
| D |104.53125|-18.856008|128|48|no|
| X |118.90625|-120.401645|749|385|no|
| Y |118.90625|-20.254185|687|56|no|

Phase21.159943mV still fails30mV. VI62.965906uA passes50uA; output18.591273mV passes5mV and bias passes. Despite improved phase/VI relative to the prior24-target A/C experiment, C/D now have wrong-sign samples and all A/C/D/X/Y validity gates remain false. Do not promote this intrinsic candidate to layout or continue a blind common output-load sweep.

Complete64-file proof740a55daac8798d2f3af976919609d5f7a2353c8, docs/evidence/cdr-sampler-load-terminal-41282867236, retains every failure. Native archive1054102581 bytes/SHA256577686ccfb6b9a09502185da3d5ec89add0f9a5a24374486e251ff8eb42d379d is in four release parts on GitHub; no native payload was acquired locally.

Actual original-gate comparison41284059156/source93458f9d15f762a194bb02d9314a8d211a9c1d80 passed18 corruption controls and authenticated the full measured result; full15-file proofafd1a4f68e882c3124867e6eca2f34600b951875. This successful comparison confirms circuit rejection.

The new20-target physical map41283407710/source1e5bd82f6587c5ac2f764a286802aa858922aaa8 passed16 controls and all500device/4928instance matching. Only A/B191/194/202/205 require private cells; their195/196/207/208 master-load siblings stay untouched. Map preparation is not geometry acceptance.

Existing-wave diagnosis41284095439/source93fcfe9d9287e1ff9090e96e69000588f6c7eb66 completed successfully; full35-file proofe62b19e3d08245b9993160e0bdc2db1468a1cef4. It verified all109 archive members and reproduced all124HBT, six-stage1530-delay and phase/VI results from the same native waveform, without rerunning simulation. Same-time C/D and clock-emitter diagnosis41284522943 also completed; full14-file proofdfa424f2d2bf58bf35adcef6bec6c8f9fb1d6604. See cdr-mixed20-wave-diagnosis.md and cdr-mixed20-cd-latch-diagnosis.md for failures, limitations and the next scoped drive hypothesis.
