# Timing-priority TX extraction — 2026-10-19

The cloud extraction run [39305590019](https://github.com/Melihakbulut221/nssoc/actions/runs/39305590019) passed the original native graph, terminal ownership, complete capacitance conservation and 13 corruption controls. It extracted 1,674 native devices, 116,611 metal resistors and 77,538 metal capacitors from the actual timing-priority parent GDS. The 31 child cells remain unchanged; the capacitor count is measured from this layout, not copied from the preceding minimax layout (77,516).

The follow-up cloud composition preserves every native device and every extracted R/C row, independently reconstructs all 377 metal conductors and probes all 124 input legs / 372 data-base terminals against native LVS geometry. It retains the six malformed-composition tests and two wrong physical endpoint tests. The source delta changes only exact physical identity, measured census, receipt pins and paths, with additional timing-priority geometry assertions.

The shorter final-stage data paths are only a geometry result. Twenty-four earlier-stage legs grew; all original loaded-wave signal, interface and device gates must be rerun on this exact model. No full PHY, PVT, qualified PEX, four-lane or mainchip timing closure is claimed. The prior minimax waveform rejection and the CDR source-contact voltage regressions remain preserved.

All CAD execution and archives are on GitHub. The local project directory is empty.
