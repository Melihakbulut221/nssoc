# Cloud continuation — checkpoint v214

Updated: 2026-11-01T04:06:09.463198+00:00

Latest user instruction is cloud-only and local cleanup. Workspace empty, no local CAD/native processes. Source authoring/static inspection and API-derived text transport use RAM only; all tests/simulation/numerical/geometry/CAD execute on GitHub. Never acquire native archives, SPICE/models, raw waves, ODB/GDS or native-frame gzip locally, including RAM. Unrelated files/attachments preserved.

## Active actual mainchip run

[41270471645](https://github.com/Melihakbulut221/nssoc/actions/runs/41270471645), exactsource2b8931b9c8988fc5dbf497a7b561db579e39f64c, branch codex/mainchip-net459-diode-prune. Independently reserved empty exact-source release430345631/tagcloud-results-41270471645-1-mainchip-bulk-postdrt-antenna. Freeze source until terminal. Do not duplicate dispatch.

Source controls41270165333 succeeded:15scope,10host and all inherited unchanged suites. Full83-file proof imported. The fix compares both complete persisted JSON snapshots; strict geometry/identity/protected-net core is unchanged. Original run41266854050 failed before detailed_route due Python tuples versus JSON lists. Cloud readback41269689818 proves unchanged strict delta passes all828 nets on complete saved snapshots and reproduces representation mismatch.

Prior failure native archive872464089B remains release430325810. Complete failedjob logs with all735 authenticated encoded derived records are retained in docs/evidence/mainchip-targeted-failure-41266854050. No native payload acquired locally. Old release reservation is consumed and must not be reused.

## CDR rejected experiment

Four-shunt actual41268684044 engine returned0 after688.745s, all1151vectors measured, but original electrical gates failed. Full61-file terminal and15-file comparison41269888640 proofs are retained. Four old minVCE failures disappear, four new maxVCE failures T59/T60/T111/T112 appear. All six data stages fail; phase0.01465777V below0.03V. VI44.3405uA below50uA. **VI output0.0125679V passes its0.005V minimum**; priorv211 prose incorrectly implied an upper limit. No gate changed.

See docs/cdr-four-shunt-rejection-and-next-circuit-scope.md for authenticated upstream driver topology. No further circuit candidate dispatched. BaselineRC only; no regenerated candidate layout or freshPEX. FullserialPHY/closedloopCDRPLL/allcorners still open.

## New clock path diagnosis

Source45286428f2d9a5dfcf6781ef04f1bb61cd20def8 on codex/cdr-clock-path-diagnostic. Sourcecontrols41271164898 passed all seven original and six new tests; full16-file proof imported.
[Read-only waveform diagnosis41271280278](https://github.com/Melihakbulut221/nssoc/actions/runs/41271280278) completed SUCCESS on the SAME immutable source. Full31-file12559046B proof is imported. It authenticates complete original113-member archive and1151-vector raw; reruns no simulator and changes no geometry. Native payloads remain on GitHub.

The analysis first reproduces all original124HBT metrics/all6stage1530bit delays/phaseVI. Then measures all physical cp/cn clock pairs over eight shared emitter tails,32clockdevices,both edge directions and255bits, preserving missing/multiple local crossings. All four samplers retain255original bit/deadline/settling records with native topology output/preceding stage links. This is diagnostic correlation, not isolated cell propagation or signoff. Source and corruption controls are in scripts/cdr_clock_path_diagnostic.py and scripts/check_cdr_clock_path_diagnostic.py; frozen original reader/diagnosis preserved. See docs/cdr-clock-path-diagnostic.md.

## Next actions

1. Clock diagnosis41271280278 is complete. See docs/cdr-clock-path-results-and-design-next-step.md. Internal clock delay is relative to loaded external ports (about1.95–4.06ps), while first external edge itself is about11ps after nominal. Complete all-bit records are retained; use cloud-only derived aggregation for full statistics before selecting next clock/data/headroom circuit change. Do not rerun the native archive just for statistics.
2. Poll same actualmainchip41270471645, preserve complete terminal evidence. Verify actual clear delta then router/physical gates; step names alone do not prove router execution.
2. Verify all828 connectivity,1351 diodeattachments,1691 protectedclock/fixedrecords, zero DRC/antenna, then finalsetup/hold separately. Do not conflate route success with closure.
3. Develop next CDR circuit based on both common-mode/headroom and six-stage margin/delay failures; retain original stimulus/1151vectors/all original gates. Require regenerated layout/freshRC and closed-loop evidence before acceptance.
4. Keep8h read-only monitor automatic_native_dispatch:false; inventory573runs.
5. FullserialPHY, routedmainchip, finalsetup/hold and production approval remain OPEN.
