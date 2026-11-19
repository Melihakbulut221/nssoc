# Load-isolation neighbor route: geometry clean, antenna repair — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44490108562 failed the antenna gate (attempt 1), head `990b804ba362a4b4c35bf47819614cfc46c1ca88`.
Artifact `14513204198`, SHA256 `962ce5782016caa0e77a3079e283e9b4b849b750775ba98a10d03d27c7400bde`: all 47 outputs verified.
ODB `0cb063d1069d079d08912d11c1cf23429e1d53417e5185b822df4b4d27da6fc7`.

## Measured result
- DRT violations: zero, iteration 10.
- Independent inter-net contacts: zero (previous three contacts removed).
- Disconnected geometry, unwired multi-terminal nets, terminals without geometry: none; negative controls passed.
- Instances: 106654; all original instance identities and terminal connections preserved.
- Unchanged non-power net records: 103081; all 2113 clock nets preserved.
- Encoded FIXED and restored ROUTED checks: 102965 nets.
- Antenna: one net, one pin remains. `nssoc_slewiso_1_net`, `nssoc_sta_i_57620/A1`, TopMetal1 cumulative ratio 203.30 versus limit 200. The other sink 52834/A2 is below the limit at 195.48. TopMetal2 is below its limit.

## Next step
Prepare an additive sg13g2_antennanp repair from this exact ODB. Require unchanged existing instances, connections, power geometry and all unmodified routes; new diode signal only on nssoc_slewiso_1_net; verify both supply contacts using native geometry. Then route the repaired net, repeat independent geometry/antenna/DRC checks, and extract fresh RC before measuring timing. No DRC or antenna waiver and no constraint relaxation.

This candidate is not accepted for production and has not received fresh timing analysis. Full chip and production signoff remain open.
