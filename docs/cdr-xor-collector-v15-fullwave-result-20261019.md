# XOR collector v15: device headroom repaired, sampling still rejected
Run39320016317 atcb5959ee34233dd5c1c99b767bc53e587d4c8186 completed both nominal cases and the actual clock-stopped/VI-bias-off controls.
Native simulations exited0without diagnostics and retained their protected sources. Each nominal capture is113475rows/1108columns through34.25ns with the unchanged0.3125ps maximum step.

Both nominal device screens now pass. Minimum HBT VCE is0.436888772V early and0.436756920V late, above the unchanged0.4V bound; the prior source-contact-v14 case had6/2VCE failures and minima0.386162076/0.386461451V. All original MOS and current screens remain in force.

Sampling still fails. Early A/B/C/D wrong signs are69/129/186/339; late89/0/188/319. Late B still has128samples below100mV despite no wrong signs.
A/B worst clock-to-valid is50.78125/51.71875ps early and51.71875/44.53125ps late, above37.5ps. C/D reach118.90625ps.

Early phase magnitude regresses from0.0204668V to0.0156253V against0.03V; signed VI current is36.5923uA against50uA. Late phase0.0318463V and VI80.3641uA pass their separate gates, but complete sampling does not.
The two injected-fault cases passed only because their faults were detected; they are not nominal link passes.

The physical collector-access repair recovered device headroom; it did not close the complete CDR. Preserve both nominal rejections and prior failures. Next replay the original sampler checks and map actual shared-emitter HBT data/clock base pairs and worst samples to physical sampler instances. This is diagnosis of existing full waves, not a new stimulus, shifted window or acceptance relaxation.
