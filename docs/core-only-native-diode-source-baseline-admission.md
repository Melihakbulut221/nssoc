# Native diode source-build baseline admitted — 2026-11-18

[Run 44390258723](https://github.com/Melihakbulut221/nssoc/actions/runs/44390258723), head 569086f1abcf060a418786557805018e307a8db9, attempt 1 completed successfully. Artifact 14468646377 SHA-256 c00c7f6c155c48b20d33f055419394704b124ad85ed676b94f8aa257eb2b98a7 and all declared output hashes were independently checked.

Success means reproduction of the known failure, not successful simulation. The published ngspice47 binary and unchanged source build both stop at printed time 2.13261685e-08 seconds, with 21366 finite samples and KLU selected. Both logs report timestep-too-small and aborted transient. Both processes return 0 despite the abort. The requested transient endpoint is 50 ns and was not reached.

The published binary SHA-256 is eaca52dad06845779fed4f50420a6a0cf4a32776e6a572432275f350002b87b8. The source-built binary SHA-256 is 5c069ed52a0141318745b479c9bdbd708b4df4dc18d6681821ee0e4e61f79864. Source archive digests are pinned in scripts/cloud_native_diode_source_baseline.py and derivative-candidate.json. Source retrieval uses the signed Debian source index; installed dependency versions and build logs are preserved. The container image tag itself is mutable and this experiment does not qualify a production simulator distribution.

Fourteen equal printed timestamps occur in each partial failure trace as the solver step collapses below text-output resolution. The baseline classifier records these and requires nondecreasing finite timestamps, the actual abort message, a partial endpoint between 20 and 24 ns, and agreement of the two abort times within the original 1 ps maximum time step. It never interprets a truncated trace as completed. Both cases now execute independently even if one case's diagnostic parsing fails.

Previous failed runs were harness/environment problems: 44387697093 built the source but could not launch the published executable without libsndfile; 44389032608 reproduced the published failure but strict printed-timestamp uniqueness stopped the harness before it ran the source-built executable. Those runs were not accepted as full baseline comparisons.

## Next experiment

[44391317766](https://github.com/Melihakbulut221/nssoc/actions/runs/44391317766), head d70786a5925f585719fa3f7fedcf6fbd36ef97cc, was dispatched with the above exact baseline artifact. It independently rebuilds/reproduces the unchanged baseline before applying only the staged voltage-derivative patch. Current input parameters, solver tolerances and the 50 ns fixture remain unchanged. Patch and source hashes are required to match. It is experimental and does not replace the accepted runtime. Full native diode cases, branch/current/charge/temperature checks and original pad cases are still required before any pad-timing conclusion.

The independent second antenna repair/reroute remains 44388764024/head9eda08b7e6a8dc2dc79807245ba3a637630e8db8, active at this checkpoint. First reroute ended with DRC0 and 17 antenna nets/19 pins; this is not antenna closure. The old extraction-v4 workflow requires the failed first reroute and must not be dispatched. Bind its successor to the eventual successful repair artifact and exact added-cell count.
