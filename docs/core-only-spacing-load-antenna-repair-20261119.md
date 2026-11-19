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

## Preparation count correction
Run 44494021182 (head 88d707b53ae40e8a3f4e6545cdae0edeb5ffba9e) stopped at the wrapper's incorrect exactly-one-diode assertion. Artifact 14512979378, SHA256 70984c32ad4f0da63f8b5bba3e37cc5cca90b48e73a048bc994edcc1d8cd3842, all seven outputs verified.
Native repair inserted exactly two cells, ANTENNA_2567 and ANTENNA_2568, both sg13g2_antennanp on nssoc_slewiso_1_net, with VDD to VPWR and VSS to VGND. The additive native audit passed: 106654 originals unchanged; total 106656; existing power geometry and connections preserved. Candidate ODB 44e5b8fe6d989394000395ca7449744007dc812710149bc856efaa6172aad9d4.

The next preparation pins these two identities and their exact signal terms, retains the 10 percent repair margin, and requires four physical supply contacts plus route preservation. This corrects an observed count assumption; it does not waive antenna, power, geometry or timing gates. The failed preparation did not reach supply-contact or route-preservation checks and is not admitted.
