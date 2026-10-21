# Independent validation of input-loading v28 native parasitics

Native extraction39559188023 and full MIM capture39561460306 passed.
The actual input-loading parent GDS 9dd0a49425183d04e1389ff19b97c3f82784d4715c8e0fcb5e628adcbfde7a6b
produced17674 resistors,12694 capacitors,111 physical conductors,938 points and7 intrinsic MIM devices.

This workflow independently audits the actual raw resistances/capacitances and native MIM ownership,
retaining13 wire and9 intrinsic corruption controls. Composition preserves all raw wire tokens,
all476 native devices, exactly one compact model per native MIM, and19 composition controls.

Only provenance/model names and the actually measured element census differ from the v26 method.
No electrical thresholds or waveform scope changed. After successful composition, rerun the full
original256-bit34.25ns loaded nominal early/late and clock-stopped/VI-bias-off tests.

Passing these stages does not establish closed-loop recovery, full Gen3x4, PVT/ESD,
qualified PEX or final mainchip setup/hold.
