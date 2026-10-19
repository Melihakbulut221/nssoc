# Collector-v8 RC and actual TX stage localization

All computation runs on GitHub-hosted runners. Local project directory remains empty.

CDR runs 39200042565 and 39200042548 passed the original native wire extraction and model-binding gates. The new actual layout exports 15,467 resistors and 11,524 capacitors; all 111 conductors and 946 anchor points are retained. Thirteen real raw-RC corruption controls and twelve model corruption controls remain enforced. These results do not qualify RF/substrate PEX or establish a working CDR. The next run restores the same geometry and binds the eleven actual MIM devices before independent raw audit, composition and original loaded 256-bit waveforms.

TX full capture 39158584151 remains rejected. Diagnostic run 39199027825 exactly reproduced its original gates from the unchanged native waveform. CMOS input and level-16 pass; level-8 has no wrong signs but fails 1,044 samples below 150mV (minimum 77.49mV). Level-4 has 450 wrong-sign samples; final interface has 1,152. These interface totals include physical terminal-pair observations, not unique transmitted bits. The final output still has 140/768 wrong samples and 164 below 100mV.

Twenty-four HBTs fail original voltage gates. For example XD0110 at its actual minimum VCE sample has C=0.918759V, B=1.443575V, E=0.561123V; VCE=0.357637V. The current review maps these measured failing devices to the actual updated 31-macro placement, instead of assigning ownership from historical coordinates. This diagnostic is not a circuit repair or acceptance.

Mainchip setup/hold, antenna closure, complete serial Gen3 x4 PHY, final routed integration and qualified signoff remain OPEN. Preserve all original failures and clocks/thresholds.

## Full-mask capture and measured failing-device ownership

MIM-aware capture 39200491952 passed actual eleven-capacitor identity/terminal checks and five injected faults. Its actual full-mask network is 15,490 R / 11,535 C, distinct from the earlier wire-only 15,467 R / 11,524 C. The next independent raw audit pins these measured counts and retains all thirteen wire and nine intrinsic-device corruption controls. No count was inferred from the old geometry.

Native ownership run 39200492051 places six failing HBTs in final macro f and eighteen in p8_1/p8_3/p8_5/p8_6/p8_7. The final four select devices XD0109–112 use actual sp/sn bases; XD0114–115 are tail devices with base mr and emitter on avss. The other eighteen failing devices are select branches with sp8_* bases. This rules out treating the failed devices as the data-input transistors. Final select and tail constraints must be solved together; merely reducing select common mode could improve select headroom while hurting the tail. Preserve original thresholds and rerun the full loaded tree after a real circuit/geometry change.

## Full raw audit and source-bound composition

Run 39200773873 passed all thirteen raw wire and nine intrinsic MIM corruption controls. Composition 39200983805 passed all nineteen original corruption controls, preserving every one of the 15,490 R and 11,535 C cards, 484 native devices and exactly eleven MIM models. These are model-construction checks, not electrical acceptance.

The new streamed matrix uses nominal early/late and clock-stopped/VI-bias-off cases, unchanged 256-bit source sequence, original 34.25ns window, 0.3125ps maximum step, 150fF sampler collector loads and 50fF comparator loads. All 1,107 voltage/current vectors remain requested through the previously validated bounded-save binary transport. Every original sampler/phase/VI-current/HBT/MOS/capacitor threshold is unchanged. No operating waveform from the previous geometry is reused as acceptance for this geometry. Full PVT, convergence, recovered-clock loop, RF/substrate/ESD and final x4 integration remain required.
