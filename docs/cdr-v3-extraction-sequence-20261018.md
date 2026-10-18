# CDR v3 extraction sequence

The new 23 supply shunts and 569 via stacks passed native physical verification39084708980. Native plane binding39085138687 and whole-device/wire references39085392184 now pass for that exact geometry:394 devices,1134 terminals,111 independent wire components and776 actual conductor points. Native IDs must come from these v3 receipts.

The v3 model-binding and wire-only diagnostic extraction jobs use the unchanged native methods against the new source. Binding retains exact native SPICE dimensions, all devices and eight corruption controls. Wire-only extraction retains the native raw graph/value/conservation checks and13 corruptions. Its capacitance lacks the MIM masks and is therefore a diagnostic baseline, never the loaded waveform model.

Next restore both actual terminal results, capture complete MIM-aware geometry, bind each of11 intrinsic capacitors exactly once, audit every raw resistor/capacitor and collapsed matrix, and compose the new model with its measured counts. Only then run the unchanged loaded early/late gates, followed by PVT/convergence and full recovered-clock integration. Physical passes do not establish electrical closure.

Native binding39085569056 and diagnostic wire-only RC39085569087 completed successfully. The diagnostic geometry yields9956 resistors and7750 capacitors; all13 raw corruption controls reject. These counts belong only to this new v3 diagnostic extraction. The next job includes the actual11 MIM masks, rebinds their bottom points to metal outside the masks, and checks native device identity/terminal ownership before strict raw RC auditing.
