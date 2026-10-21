# Independent validation of cleaned v27 native parasitics

Native extraction39547338459 and full MIM capture39547470228 passed.
The actual clean-parent GDS ada3f68c2ac15a5a564c5985f9082ac5276fdacec533a386f22442de40a33682
produced17694 resistors,12714 capacitors,111 physical conductors,938 points and7 intrinsic MIM devices.

This workflow independently audits the actual raw resistances/capacitances and native MIM ownership,
retaining13 wire and9 intrinsic corruption controls. Composition preserves all raw wire tokens,
all476 native devices, exactly one compact model per native MIM, and19 composition controls.

Only provenance/model names and the actually measured element census differ from the v26 method.
No electrical thresholds or waveform scope changed. After successful composition, rerun the full
original256-bit34.25ns loaded nominal early/late and clock-stopped/VI-bias-off tests.

Passing these stages does not establish closed-loop recovery, full Gen3x4, PVT/ESD,
qualified PEX or final mainchip setup/hold.
