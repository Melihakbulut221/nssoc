# Six-buffer fresh RC result — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44550131521 succeeded at 1aa4f5288de36c472ea5ce9548bffa0c703ee623.
Artifact 14542543395 SHA256 `7eb3ec71a5435393eb626b14d2a3c190a21a935e169730413fd5662d11ca44f1`; all 140 outputs independently checked in memory.

Bound ODB `bd28f784aa3cad49b72197de70c394727ab0e72608610febd4c4e16dfc4a28bc`; Verilog `1e49dbd06ce9478c5c4cdd44ac891f1f9698dfea76bd63a3f564f8bb79023be6`; DEF `1629c639c61d4c013bd97141fc1c91066f071a934c4569d92f0bd391d82b728e`; nominal SPEF `0f7ca1545d4c9979cf74ff9133f7749f55356efa7570fcaf2776bfda93485405`.
SDC unchanged: `f121116a72150c56126ac3d8dc4fda946e6d0040984e9264ef3d877171029de1` (20 ns, 5 percent derating).

| Nominal RC / PVT | Setup violations | Hold violations | Worst setup ns | Worst hold ns | Slew | Fanout | Capacitance |
|---|---:|---:|---:|---:|---:|---:|---:|
| Slow 1.08V 125C | 0 | 0 | 0.02084910081369358 | 0.4491127596936628 | 456 | 210 | 52 |
| Typical 1.20V 25C | 0 | 0 | 7.431625303271305 | 0.1855849970673458 | 0 | 210 | 54 |
| Fast 1.32V -40C | 0 | 0 | 10.303333589054711 | 0.037160608975109796 | 0 | 210 | 60 |

Compared with 44528360188, slow slew count improves 472 to 456 and all-corner fanout 211 to 210. Capacitance counts are unchanged. Pin-level comparison must check for new violations rather than relying on net totals.
106672 instances exported without renaming; 1410 added diodes present without missing, duplicate or mismatched signal connections. All ten moved diodes are additionally checked by the wrapper.

1403 unannotated drivers are classified: 1288 disconnected and 115 connected without sinks. No loaded unannotated driver was found, but this classification is not timing coverage approval. RC is nominal only; min/max qualification, SRAM characterization, full transistor LVS/foundry DRC, pad/core timing, package/PCB timing and manufacturing approval remain open. Neither this green run nor zero setup/hold counts establish production readiness.
