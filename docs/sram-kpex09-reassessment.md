# SRAM coupled-RC extractor reassessment, 13 November 2026

The old full-DP Magic-based RC export fails pairwise capacitance conservation (docs/101). It remains rejected. KLayout-PEX v0.9.0, upstream commit `1b923ea54d8d9b1028de1043afd654c9e1838049`, offers an analytical coupled RC path with distributed capacitance. This is a candidate method, not evidence that the SRAM is qualified.

The cloud workflow extracts CC and RC from the real DP8T leaf within the hash-locked repaired DP256x16 GDS. It preserves the original macro file and records package versions, installation archive hashes, native outputs and exit codes. The existing chip route and analog jobs are not changed. A zero extractor exit code is only execution success.

Before any accepted memory timing model: inspect terminal attachment; compare collapsed MOS topology against the independent schematic; validate coupling conservation and physical placement against the same engine's CC result; reject disconnected-terminal and lost-coupling mutations; independently check effective R/C and numerical convergence; then expand to the whole macro and characterize complete arcs. The historical repaired macro is not automatically the macro in the current routed chip.

Upstream references: [0.9.0 release](https://github.com/iic-jku/klayout-pex/releases/tag/v0.9.0), [Magic grounding limitation](https://github.com/iic-jku/klayout-pex/issues/284), [SG13G2 resistance-corner qualification gap](https://github.com/iic-jku/klayout-pex/issues/549). The release retains limitations for multi-emitter HBT terminal geometry and does not establish calibrated complete process corners. This SRAM MOS leaf screen does not qualify the PCIe HBT PHY.

## Completed leaf checkpoint

Runs 43487978461 and 43488742366 complete nominal extraction and independent collapsed-network checks: eight MOS identities/parameters and port/device connectivity preserved; 68 resistors, 288 distributed capacitors, all 61 reference capacitor pairs conserved within the fixed 1e-23 F absolute plus 1e-5 relative tolerance. Removed capacitance, disconnected resistance and changed MOS model controls are rejected. The NWell resistance warning remains. This is not independent schematic LVS or full-macro qualification. Exact references are in [the receipt](evidence/sram-kpex09-leaf-20261113.json). Full DP256x16 CC and RC extraction is dispatched separately.
