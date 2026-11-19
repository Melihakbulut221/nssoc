# Three-buffer load-isolation candidate: fresh timing result — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44502914675 succeeded, attempt 1, head f598bfab9e5aca3548c5c51df96ff477b1b0b609.
Artifact 14519695416 SHA256 1dcb18436e79ca0c6aa5d5e07f57fb6a09858cf76acb548c6702b50cdc48fae1; all 137 outputs verified.

Fresh views are bound to routed ODB 8bd5334ca987ad52d5987b776587773d801188c9f83119d102cfd63a348d00c8; Verilog c4a75453b1abd1fd37608e610a4c2e5aeecf8e94953d7d04cee43ef56fdaee50; DEF 3bbd6c87791bbc7875278fef1e44f88c88cd062075b451a982289d18f14e7699; unchanged SDC f121116a72150c56126ac3d8dc4fda946e6d0040984e9264ef3d877171029de1. All 1400 cumulative added antenna diodes are exported with no missing, duplicate or mismatched signal connections.

## Actual fresh metrics
These come from extraction/2-nssoc-coreonlyextractedsta/<corner>/fresh_metrics.json, not historical pre_route_corners.

| Corner | Setup violations | Hold violations | Setup worst slack ns | Hold worst slack ns | Slew | Fanout | Capacitance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| slow 1.08V 125C | 0 | 0 | 0.020785151965666573 | 0.4491127596936628 | 480 | 210 | 52 |
| typical 1.20V 25C | 0 | 0 | 7.431590664311957 | 0.1855847750227346 | 0 | 210 | 54 |
| fast 1.32V -40C | 0 | 0 | 10.303312272772034 | 0.037160608975109796 | 0 | 210 | 60 |

WNS and TNS remain zero in all corners. Relative to spacing-only run 44482078997, slow slew violations fall from 495 to 480; typical/fast slew remain zero; fanout and capacitance counts are unchanged. The weakest setup margin is about 20.8 ps and fast hold about 37.2 ps. Counts alone do not prove which pins improved or regressed; the next cloud comparison exports the exact source-verified per-pin reports for that analysis.

The route passed native DRT, antenna and independent signal geometry checks in run 44498843994. This nominal-RC measurement does not prove qualified RC min/max, full annotation coverage, updated full-chip integration, transistor LVS, foundry DRC or manufacturing approval. accepted, final_timing_complete, qualified_rc_minmax, annotation_qualified and manufacturing_approval are all false. Clock period and derating are unchanged. External package/PCB/device timing remains unspecified.
