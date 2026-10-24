# Full loaded validation of the cleaned v27 native model

The four-case cloud workflow waits for exact independent MIM audit/composition39548204907.
It accepts only the actual cleaned476-device model with17694R12714C and7intrinsic MIMs.

All original256bits,34.25ns,.3125ps,150fF sampler collector and50fF XOR loads are retained.
Nominal early/late, clock-stopped and VI-bias-off cases use the original100mV data sampling,
37.5ps clock-to-valid,30mV phase,50uA current and native HBT/MOS safety gates.
Every waveform and rejection remains evidence. No masked interval or relaxed threshold.

The change shortens only eight physical BP/BN pull-up resistors from2.4um to.9um.
It targets observed v26 master selector headroom failures; improved electrical behavior
must be measured, not inferred from physical DRC/LVS success.

This remains an externally clocked8GHz loaded block test. Full recovered-clock operation,
PVT/ESD/qualified PEX, complete Gen3x4 integration and final mainchip STA remain unproven.
