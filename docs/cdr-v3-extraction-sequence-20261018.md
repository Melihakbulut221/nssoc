# CDR v3 extraction sequence

The new 23 supply shunts and 569 via stacks passed native physical verification39084708980. Native plane binding39085138687 and whole-device/wire references39085392184 now pass for that exact geometry:394 devices,1134 terminals,111 independent wire components and776 actual conductor points. Native IDs must come from these v3 receipts.

The v3 model-binding and wire-only diagnostic extraction jobs use the unchanged native methods against the new source. Binding retains exact native SPICE dimensions, all devices and eight corruption controls. Wire-only extraction retains the native raw graph/value/conservation checks and13 corruptions. Its capacitance lacks the MIM masks and is therefore a diagnostic baseline, never the loaded waveform model.

Next restore both actual terminal results, capture complete MIM-aware geometry, bind each of11 intrinsic capacitors exactly once, audit every raw resistor/capacitor and collapsed matrix, and compose the new model with its measured counts. Only then run the unchanged loaded early/late gates, followed by PVT/convergence and full recovered-clock integration. Physical passes do not establish electrical closure.

Native binding39085569056 and diagnostic wire-only RC39085569087 completed successfully. The diagnostic geometry yields9956 resistors and7750 capacitors; all13 raw corruption controls reject. These counts belong only to this new v3 diagnostic extraction. The next job includes the actual11 MIM masks, rebinds their bottom points to metal outside the masks, and checks native device identity/terminal ownership before strict raw RC auditing.

## MIM-aware capture and strict audit continuation

GitHub run 39085974150 completed the actual v3 MIM-aware native extraction: 9,979 resistors, 7,761 wire capacitors, 11 actual MIM devices, 111 physical components and 776 physical points. The full receipt and original artifacts are pinned; all five capture corruption controls were rejected. This is not qualified PEX or electrical closure.

The v3 raw audit restores that exact capture and the v3 device binding. It preserves the 13 wire conservation controls and nine MIM identity controls. Only receipt paths, helper version and the observed native R/C census differ from v2. After it passes, compose the exact-once native MIM model and repeat the original loaded early/late stimuli and stopped-clock/VI-off controls. Do not reuse v2 RC or accept compact-model results as full-wire results. All execution and artifacts remain on GitHub.
