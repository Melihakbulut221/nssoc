# Actual retimed-D selector topology and loaded transfer diagnosis

The initial q20 run41279373178/source2aea08e3421f8bcf6d8a6e8adaf783cc6ea7082f and q15 run41279400555/sourcec421cc577281d78441fd51c6db160020e990a62c failed after reproducing the original electrical metrics. Their transfer analysis assumed B directly drove the selector dividers. The real topology guard rejected that assumption; this is an analysis failure, not a passing circuit result.

Complete31-file failure proofs are retained:
* q20:9aceb9e54839bc2c213aa1156c89da75a752b0d1, docs/evidence/cdr-sampler-candidate-wave-41279373178.
* q15:1992e4d33a5871e498282e7a1557c0cced73ee12, docs/evidence/cdr-sampler-candidate-wave-41279400555.

The authenticated candidate composition establishes:
* DQP native cluster18 through R234 L6um/W1 to receiver base cluster150; R235 L8.6um/W1 shunts to avss cluster23; MIM2754.8x4.8um parallels R234.
* DQN cluster17 through R236 L6um/W1 to base151; shuntR237 L8.6um/W1 and parallel MIM2764.8x4.8um.
* Q131/Q149 bases share150, Q132/Q150 share151. The positive S0/S1 outputs are Q132/Q150 collectors, negatives Q131/Q149.
* These selectors therefore receive retimed D, not B directly. Existing q15 B passing its original screen does not establish valid selector drive because D fails.

Corrected diagnosis retains A->AD and C->CD and uses D->S0/D->S1. It records A->C and B->D observed crossings plus expected-sequence lags to expose retimer behavior. Before native archive acquisition, a separate source-controls job verifies the actual full500-device composition and all four paths against authenticated original measurements. The archive job requires that successful preflight and later checks extracted composition equality. Seven frozen-reader, thirteen operating-point and eight transfer controls protect the interpretation.

Diagnostic50mV sampler/buffer and10mV base hysteresis identify observable transitions. Matching is bounded by the next input transition and125ps; missing, ambiguous and nearby outside-window events remain recorded. These thresholds never replace the original100mV/37.5ps sampler and100mV/75ps XOR gates. Expected pipeline lag is recorded separately; a crossing match alone does not establish protocol or timing correctness.

No circuit or layout mutation has been made by this read-only diagnosis. All native archives/waves/models remain on GitHub; local source/API-derived text coordination is temporary RAM only. Full serial PHY and final chip timing remain open.

## Completed corrected diagnoses

Both corrected runs succeeded: q20 run41280275014/sourcea487ebb6213d2e40bbdbac997f6624bf8cfa6afb and q15 run41280306194/sourceb1ef7227f2b828072722cd7bae0501f59494e18f. Each passed7 frozen-reader,13 operating-point and8 transfer controls and the actual-topology preflight. All124HBT metrics, six stages,1530 original bit delays and phase/VI values reproduce the original report. Their complete35-file proofs are3266bcfca451cc2e8c06ac372409f1dbb240fb04 and031a9d3d6554b1574f4ba609279d3543cff03b8e.

| Path | q15 source transitions | q15 matched sampler->buffer | q15 missing in window | q20 source transitions | q20 matched | q20 missing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A->AD |127|22|105|127|18|109|
| C->CD |128|14|114|128|14|114|
| D->S0 |128|14|114|128|12|116|
| D->S1 |128|14|114|128|12|116|

No ambiguous matches occurred. q15 median matched sampler-to-base delays are61.9468ps(A),68.6585ps(C),61.7180ps(D->S0) and61.9117ps(D->S1). A base-to-buffer median is58.2426ps and C51.8529ps. These medians use different matched subsets and must not be added to infer a complete path delay. Missing-in-window means no same-direction confirmed crossing under the diagnostic matching rule, not a measured packet bit error.

B->D has128/128 matching crossings and no missing events in both candidates; q15 median65.88095ps, q20 median66.13516ps. B and D expected arrays have index lag0 because B uses the falling edge and D the rising edge. A->C expected arrays have index lag1; its approximately122ps matched delays sit near the125ps window boundary. q15 has62 matched/65 outside-or-missing, q20 has54/73. These retimer observations do not override the original100mV validity failures and window-boundary exclusions are not by themselves lost pipeline data.

## Next circuit experiment

The next controlled hypothesis reduces the eight A/C divider lengths while preserving their geometric series/shunt ratio: R227/229/238/2403.6->1.8um andR228/230/239/24121.6->10.8um, allW1um, retaining the earlier q15 sixteen length changes. D selectors, capacitors, HBT sizes and the original native workload/gates remain unchanged. This produces a distinct24-target candidate; it is not the earlier24-resistor master/buffer experiment.

Lower impedance may reduce base settling delay, but can increase sampler loading and shift loaded bias because of base current and contact effects. Only actual unchanged-gate simulation can accept or reject the hypothesis. It is not an accepted physical change; a new physical map and fresh DRC/LVS/RC are required after any passing intrinsic result.
