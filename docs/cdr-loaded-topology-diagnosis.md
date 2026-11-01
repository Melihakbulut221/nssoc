# Loaded CDR headroom topology diagnosis

Cloud run [41267705616](https://github.com/Melihakbulut221/nssoc/actions/runs/41267705616) at source fd3c0ccf005a15c5e168b35b02a93e79a8ee138b completed successfully. All 500 physical devices, 51 logical native nets, 124 HBT waveform identities and original four failure events joined exactly. Nine corruption controls rejected altered device IDs, terminal probes, parameters, aliases, missing waveform devices and relaxed original thresholds.

The complete 16-file proof at docs/evidence/cdr-loaded-topology-terminal-41267705616 contains original authenticated inputs, source, results, controls, job log and GitHub metadata. The proof commit is 3e45b11b44cfbc08f51334b1bb2d372384c3820b. Artifact transport and API-derived JSON were handled only in RAM; all computation ran on GitHub.

## Findings

T061/T062 share C net $158, E net $149 and B net cn; these are the D sampler's lower clock-steering pair. Their collector net joins the emitters of T054/T056 and bleed resistor T179. Their tail net joins MOS devices T003–T006. The worst measured VCE is 0.3407016057195903 V against the unchanged 0.4 V minimum.

T115/T116 share C net $698, E net $680 and B net cn; these are the corresponding C sampler pair. Their collector net joins T106/T108 emitters and bleed resistor T217. Their tail net joins T032–T035. Worst VCE is 0.3762439066818176 V.

The upper D-pair bases are on $99/$98, with pull-ups T182/T183 (rppd W8um L1.8um) and ground shunts T184/T185 (W4um L5um). The C-pair bases are on $652/$651 with equivalent pull-ups T220/T221 and shunts T222/T223. The existing v59 generator changed these four shunts from L7.4um to L5um; it retained source references and old native primitive geometry.

## Next circuit experiment

A concrete candidate is restoring only T184/T185/T222/T223 from L5um to L7.4um, keeping W4um and all terminal connections. This is a hypothesis to raise the upper-pair base common-mode and hence lower-pair collector headroom. It is not a demonstrated repair: gain, sampler settling, tail compliance, all 124 HBT limits and phase/VI may improve or regress. Compare it against the exact current loaded baseline using the original external clock/data/corner/stimulus and acceptance predicates. Do not change clock common-mode or relax a threshold to obtain a pass.

Before native simulation, qualify exact source and reserve an independent empty exact-source cloud release. An exploratory model-parameter change cannot claim physical acceptance. Before accepting layout, replace real native PCells, update schematic references, verify unchanged unrelated geometry/connectivity, and rerun full physical extraction and fresh MIM/wire RC. Preserve all failed trials. Then rerun original loaded metrics and all required corners. Do not treat the old v58 result as evidence for the new via2/M3 geometry.

Native-net membership is connectivity, not equality of distributed RC terminal voltages. No ideal aliases, removed parasitics or relabeled test oracles were used.

## Scope still open

Full serial Gen3 x4 PHY and closed-loop CDR/PLL, mainchip routing and final setup/hold remain open. Mainchip run41266854050 continues independently at immutable source8b7404c7340ef5ebc4a70e36dfa30a96d07013d9. Do not duplicate it or mutate that branch until terminal.
