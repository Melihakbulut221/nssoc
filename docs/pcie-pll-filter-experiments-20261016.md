# PLL filter acquisition experiments — 2026-10-16

All execution is cloud-only. No local CAD, tests or artifact downloads.

The completed actual845-device1us acquisition38813902351 fails the original800–900ns frequency gate:126.215885ppm versus100ppm. The900–1000ns window is84.003666ppm. Phase-span/no-slip/control checks passed both windows. Changing observation windows is not a repair.

Source diagnosis38847244994 (summarySHA256 `89899b2b091046c12b3fd24105e074028a4c68e4eed8fd9cc2320aef9b050422`) proves the10um-by10um cap_cmim `X_xpump_xd0001` connects VCTRL to AVSS. The845devices and8648wire records have17physical ports plus a distinct wire-capacitance reference. The predecessor38846227092 mistakenly counted that reference as a physical port; its failure is retained. The corrected hosted test rejects missing, renamed, duplicate and conflated reference pins.

Experiment hypothesis: modest changes to loop capacitance may alter the measured settling/ripple tradeoff. The9um and11um square candidates bracket the baseline100um² area with81um² and121um². Area ratio is NOT assumed to equal exact modeled capacitance. Both run the full original1us, .3125ps step, same34probes, zero-sourceOP/102OFF, same patched native engine and original PDK. All mandatory100ppm/50ps/no-slip/control gates remain unchanged. Negative controls reject extra edits, changed capacitor nodes/parameters, altered wire records, unchanged candidates and undeclared sizes. This is a measured design experiment, not a predicted solution.

Only the one intrinsic capacitor width and length change. Existing wire RC is a frozen baseline estimate and is NOT candidate extraction. Neither candidate is adopted by a green workflow or passing acquisition. A successful candidate requires regenerated physical capacitor/layout, fresh affected RC and revalidated parent composition followed by full native acquisition, timestep refinement, clock load, PVT and device safety. FullserialGen3x4 PHY/mainchip closure remains open.

The general relationship between loop parameters and settling is described in [TI PLL transient-response training](https://www.ti.com/ja-jp/video/6161794724001) and [TI loop bandwidth design](https://www.ti.com/de-de/video/6218308679001). These references do not validate this circuit or predict which candidate will pass.
