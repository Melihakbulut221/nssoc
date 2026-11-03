# Cloud continuation — checkpoint v347

Updated: 2026-11-03T19:21:28.889341+00:00

## Actual full-chip route and local gate-metal repair

Actual-chip engine qualification41695305770/source5518d9fa75b505848e2c6a5c7d1b4a0ca9c011af SUCCEEDED (release433078096). Full143820nets,154480instances,1691protected-clock records, native ODB/DEF serialization and complete original DRT/antenna observations were preserved. Existing92DRTmarkers and21antenna nets/27violations remain failures of the reference layout, not signoff. Qualification made0routing calls.

Full64 independent source controls41699472604 SUCCEEDED. Actual original full64 routing41699812301/source9430a57873e78d3c283b531da8e8e74da416f297 on codex/mainchip-guide-tiled-full64 has reserved release433106055. Follow its live snapshot below. This is the actual complete routing trial; no memory reduction or setup/hold success is established yet. Preserve full64 strategy and all11 phases; compare only completed physical and timing outcomes.

PHY side-only gate-metal attempt41700152258/source12497f2c8dea39d4aa6adca64c9ee7d52a879e89 FAILED: all370 first-group side offsets crossed foreignM1; publication then failed404 because no release was reserved. Complete derived failure and failed-step logs are imported. Its original native input remains in qualified wire release433047733. The fallback artifact13261034587 has90day retention; do not falsely call it permanently published.

Successor47572b12d3c8becade5488550be754e0d0a56f3a introduced direct gate-axis vias, zero-to10um offsets, explicit260nm M1 contact pads and geometrically proven original own-netM2 attachment. It retains all foreign-net clearances and checks all50groups, recording full rejected group obstacles. Run41701260499 FAILED before any native geometry: GITHUB_TOKEN tag creation returnedHTTP403. Do not treat it as a circuit result or repeat it unchanged.

Current generation41701650129/sourced6824692de9324b0a130e4e95270f119f11185bf on codex/cdr-mos650-gate-metallization verifies the authorized dispatcher's pre-created exact-source release433116338 before native work. Geometry is identical to the unexecuted gate-axis repair; no permissions were widened. Follow the same live run. Generation is not physical acceptance.

If generation passes, adapt candidate acquisition only in scripts/cloud_cdr_wire_shortcuts_physical.py from frozen physical source852e610cd4873d7cfcd3b09d85f03c62b5151969. Use native-gate-metallization.tar.gz rootmos650-gate-metallization/native/layout/{nssoc_cdr_pd500_resistor_v59.gds,schematic.cir,result.json}; independently rebuilt650 reference must equal35500bytes/SHA25621d730545b983930eacf733ba77a7593df52e253987991724de9594fe136bbfb. Keep exact checker SHA30c4586b86167ad775af14b5568152820a802037150bdfd282e7ba0843a1555f, all560DRC/deep-flat650LVS/13faults and original scoped runtime controls. Do not accept partial routing groups or waive violations.

After physical acceptance, regenerate all native terminal/contact identities and RC for modifiedGDS. Old wire binder requires one contact per poly group and must change for actual multiple contacts. Original650 metalRC41693055344 and native gateAC41696724132 remain useful diagnosis, not RC acceptance for modifiedGDS. QS gateRterms0 and missing normal-poly sheetR remain explicit; RF/NQS model hasdifferentterms andfixedngcon2. Full electrical composition includingMIM, physical gate/access paths and NQS overlap precedes original loaded circuit/fullserial qualification.

The three product requirements remain unclosed. Passed source-controls, generation, unitAC and engine compatibility must never be counted as fullPHY, mainchip routing or final setup/hold completion.

Observed 2026-11-03T19:21:28.889341+00:00:
- 41695305770: completed/success
- 41699472604: completed/success
- 41699812301: in_progress/None
- 41700152258: completed/failure
- 41701260499: completed/failure
- 41701650129: completed/failure


## Preserved prior history
This current entry replaces the accumulated repeated status text. It does not
discard previous source, failures, measurements or controls. The complete
v346 continuation and all prior checkpoint documents remain at the immutable
commit below; use specific referenced reports instead of reading the entire
historical status log on every resumption:
https://github.com/Melihakbulut221/nssoc/blob/a112a514867c670008169c4d97772e20ab6bd6f6/CLOUD_RESUME.md

## Execution and acceptance
All native CAD, GDS, ODB, SPICE and runtime payloads remain cloud-only.
The local workspace is empty. Source and derived text coordination uses RAM.
The8-hour monitor remains read-only, automatic_native_dispatch=false; a
configured inventory is not proof that its latest live observation succeeded.
Poll exact existing handles before any new dispatch. Never restart on a
polling timeout. Full serial Gen3x4, actual full-chip routing and final
setup/hold must all be proven; none is closed by a generator, source control,
engine build, roundtrip or partial macro test.
