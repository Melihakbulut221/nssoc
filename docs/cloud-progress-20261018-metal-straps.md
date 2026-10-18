# Cloud continuation checkpoint, 2026-10-18

All project operations are cloud-only. Local `/home/hasanmelih/Documents/ChatGPT/nnsoc` is empty. Do not restore CAD archives, source checkouts or waveforms locally. Read summaries in memory through GitHub API; native inspection and computations must run hosted Actions. Preserve successful and failed evidence. No full PHY or final timing closure is claimed.

## Completed in this continuation

* Run39150862130 recovered four failed load-resistor screen artifacts from39149512255, with original ZIP and every output hash verified. No resimulation; all four electrical screens remain rejected. Publication group names now use1p2/1p6 instead of dots.
* Run39149970188 measured actual supply-wire, intrinsic-load and collector-wire voltage drops from the rejected local-v5 waveform. Evidence shows large wire losses; the unchanged intrinsic2.12um load is retained in the physical candidate.
* Sampler run39151208754 stopped at local-tap escape clearance; its failure remains recorded. Actual primitive spacing increased24um to30um.
* Sampler run39151562771 PASSED native560category DRC, unsimplified deep/flat54device LVS, LEF,14fault controls and independent primitive drawing conservation with3fault controls. New native TopMetal1 vertical and TopMetal2 horizontal straps cover every net. Source3319f117f885d24b117fcbbd588657ab18df14dc.
* Parent run39152067894 PASSED full484device physical gates at1715c1e19afb2b253107efa167db756ceb1a3d0b. Top `nssoc_cdr_pd484_strapped_v6`. Four new sampler masters retain their own76supply risers/8buses, checked against actual parent geometry; other twelve leaves retain50overlay risers/19buses. Same circuit/native primitives, original parent DRC/LVS/fault gates.
* TX nominal job117705290956 in39137607059 finished full34ns/256bit native simulation, returncode0/no diagnostics, but failed original electrical gates:181of768wrong-sign samples,220below100mV,minimum margin-0.289359V,24HBT failures,0MOS failures. Runtime11331.48s. Full native capture is preserved in cloud Release; do not call this a pass.

## Continue from these exact points

1. Build fresh strapped-v6 parent drawing/terminal binding, wire inputs, actual RC, native model binding, MIM capture/audit/composition, then the unchanged full256bit loaded early/late/fault tests. Start from the passing parent receipt `docs/evidence/cdr-strapped-v6-parent-physical-pass-20261018.json`; do not reuse old local-v5 wiring. Baseline pipeline helpers are `cloud_cdr_retimed_local_v5_*` and `cloud_cdr_local_v5_mim_*`, with exact source deltas. New sampler has unchanged primitives but new top name, geometry and terminal positions. Native Layout owners must survive region comparisons. Never globally replace short RC census numbers inside SHA256 literals.
2. Inspect the TX failure's full interface/device evidence and actual native waves in a hosted review workflow. Nominal receipt: `docs/evidence/tx-v5-return-repair-full32-nominal-rejection-20261018.json`. Negative `swap_leaf_select` job117705290938 was still running at last check; preserve it.
3. Mainchip resume39149110568 was still running. Source32d3361453bb4f954d6ef447d6d34bf15ef7f139 resumes originaldrt-run-2checkpoint with one antenna repair cycle, then fresh RC/three-corner STA. Keep original clock/gate requirements and zero DRC/antenna requirements. Do not restart a healthy job because observation ends. Original source/routing and rejection receipts remain authoritative.

The existing eight-hour cloud monitor remains in place. Keep all new artifacts in cloud Releases and all method/evidence changes on `codex/complete-open-work`.
