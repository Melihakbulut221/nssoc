# A/C divider with original C/D output loads

This controlled experiment starts from the rejected A/C-divider candidate sourcee2e753c37fcff8b8fef85695208b8157a7399b57, actual native run41280806504. Its clean731.256152s simulation passed device predicates but only samplerB passed data validity. A/C-divider changes raised phase13.177843mV andVI42.150650uA relative to q15, still below30mV/50uA; A/C/D andX/Y timing remain rejected. Full64-file terminal proofe5bd8c9efb5ce8726416f0366b42eeb28aca19e1 and actual16-control comparison41282030219/full15prooff1dc2fcb4893382082993f15595647a0c50628e5 preserve all original measurements.

The q15 same-time diagnosis41282425236/sourceae6db2f7ee9a11bad03154f5401ca9837a3db6fb authenticates complete C/D follower, input-buffer, master, slave, hold and clock topology. At the worst original sample at3.1ns, C slave input differential magnitude is140.084623mV but output33.754185mV; D input157.171451mV but output22.772750mV. Same-time differential collector currents are4.212637mA and4.548597mA. These are transient snapshots, not a DC Ohm-law estimate or proof of a particular fix.

## Exact new hypothesis

Restore the four C/D output-load resistors XD175/176/212/214 from the prior candidate1.5um/W32 to their original2.6um/W32 by removing them from the intrinsic rewrite. Keep A/B output loads XD191/194/202/205 at1.5um/W32. Keep original master loads unchanged, prior four buffer pullups1um/W8, four shunts3.4um/W4 and eight A/C divider lengths1.8um/10.8um,W1.

Exactly20 intrinsic length tokens differ from the authenticated original500-device model. This separates retimed C/D loading from A/B loading. It may improve output amplitude but may worsen settling or voltage headroom; the existing original whole-model gates decide. The earlier global q20 output-load sweep is not a proof of this mixed-load candidate.

Source controls authenticate every selected original parameter/ordered native terminal, preserve exact untouched C/D synthetic cards and all other original bytes/metadata, and retain21 corruption plus5 archive refusals. Actual preparation retains13 original binding refusals. Original prepare/measure bodies,1151vectors,10ohm sources,150fF sampler/50fF XOR loads,stimulus and all electrical limits are unchanged. D-selector divider networks, every MIM and HBT size stay unchanged.

All work executes on GitHub. Only a successful exact-source control proof and independently reserved empty exact-source release admit the actual simulation. Baseline distributed RC is retained for this intrinsic experiment; no new layout/fresh PEX/closed-loop/fullPHY/finaltiming acceptance is claimed. Preserve all failures. Do not reuse the prior24-target map as proof of a new regenerated layout.

## Qualified dispatch

Source8c7b5cdd86447fe374ae06064f2fef735a7c9b91, branchcodex/cdr-ac-cd-output-restore. Controls41282742236 passed21 mutation and5 archive refusals; full13-file proof5033155164f61cc4331052de3e335961da5e2ac3.

Exactly one native dispatch41282867236. Independent exact-source empty release430414047/tagcloud-results-41282867236-1-cdr-sampler-load reserved2026-11-01T06:57:51.667570UTC; full6-file reservation proofcfeadc6fff84946f78728fbf5e92d899a8d86ede. The native workflow repeated source controls successfully and was observed executing the actual simulation. This checkpoint claims no terminal result. Do not redispatch or edit the active source.

A new20-target comparator and physical ownership map must be qualified; the previous24-target versions do not qualify this target set. A passing intrinsic result would still require independently authored reference, regenerated geometry, DRC/LVS, fresh RC and all500-device rebinding, corners and full closed-loop integration.
