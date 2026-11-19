# Three-buffer route rejection and targeted neighbor repair — 2026-11-19

## Rejected evidence
Run https://github.com/Melihakbulut221/nssoc/actions/runs/44485580230 completed with failure, attempt 1, head `4848d0affb0ef20f2bbe3a2c865f749d1cc3ec64`.
Artifact `14511783320`, SHA256 `2f8d185a83040cdcb943220c0ef7dfd99ecabaf28161e95dfacdab56605fc77b`; all 45 output hashes verified.
Routed ODB `36de40df4a47f8bc1e15c78a515efe75c07d96ec567059b9b02608c5353ff26e`.

Native DRT reported zero violations after iteration 23, but independent native geometry found three Metal2 contacts between `net5592` and `nssoc_sta_n_63283`. No disconnected nets, unwired multi-terminal nets, or missing terminal geometry were reported. Antenna analysis reported one net / one pin violation. This candidate is rejected and has no timing acceptance.

All 106654 instance identities and terminal connections, 103082 unselected signal/clock net records and 2113 clock nets passed preservation. 102966 encoded fixed routes were checked before routing and restored afterward.

## Next experiment
Restart from the verified three-buffer preparation run 44484842788, not the rejected routed database. Add only `net5592` to the previous six allowed nets. Preserve the remaining 103081 non-power nets, every clock, all cell identities and NDR rules. Keep the independent geometry, DRC and antenna checks mandatory. Verify the rejected predecessor artifact in cloud before routing.

Antenna violations must be remeasured after the corrected route; no waiver is introduced. Fresh RC and three-corner timing may follow only if the physical checks pass. The 50 MHz / 20 ns constraints and derating are unchanged.

This experiment does not establish full chip LVS, foundry DRC, qualified min/max RC, external I/O timing, or manufacturing approval. Package, PCB and connected devices are not selected, per user confirmation; external I/O timing therefore remains open.
