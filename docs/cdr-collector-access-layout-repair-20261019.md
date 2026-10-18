# CDR sampler collector access repair candidate

Native coordinate review 39170551593 binds R1047 (9.49825 ohm) between T174_rppd_2.n67 and T052_C to the original extracted node records. The collector terminal is at raw (308378,101580), its preceding branch at (303819,101588); raw scale is retained in the evidence, not guessed as micrometers. Current sampler metadata confirms each collector uses a 0.4um Metal3 escape and four-column native Metal1-to-Metal3 via stack.

Candidate v12 changes only all16 HBT collector escapes to1.2um width and16 via columns. Native HBT drawings, dimensions, centers, collector lane positions and single-row via Y coordinates remain. Bases/emitter access, MOS/resistor access, supply/output straps and primitive placement remain unchanged. The first native collector pin spans14.8um, with separate base/emitter escape heights; actual DRC/LVS must still prove the candidate fits. No numerical parasitic is rescaled.

The cloud physical job uses the original560-rule DRC, unsimplified54-device deep and flat LVS, LEF check and fourteen actual negative controls. Source-delta verification and independent primitive drawing/placement comparison remain; additional routing metadata checks bind exactly16 collector changes. Candidate is unverified until this job completes. Even a physical pass requires new whole-parent layout, native RC and the original256-bit/full-device waveform gates. No timing, CDR or serial PHY acceptance follows from this edit alone.

The 6.21653ohm supply feeder R10067 remains a separate physical bottleneck. Keep its exact native records for the next parent repair. Do not mix an unverified supply change into this isolated collector experiment.
