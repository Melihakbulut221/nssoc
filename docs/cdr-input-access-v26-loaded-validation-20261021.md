# Full loaded electrical test of actual cleaned v26 parent

The cloud workflow waits for exact MIM audit/composition39533943848 at
ac80df8ba248afe9223a458552a467cb2081c2b9. It consumes only the cleaned and
physically verified v26 model with476devices,17674R,12694C andseven intrinsic MIMs.

Nominal early/late and original clock-stopped/VI-bias-off fault cases retain all
256bits,34.25ns, original timestep,150fF sampler collector and50fF XOR loads.
The original100mV data sampling,37.5ps clock-to-valid,phase/current/HBT/MOS gates
are unchanged. Failures remain failures; no timing masks or threshold changes.

This is still an externally clocked8GHz block test. It cannot prove recovered
clock/closed loop, PVT, RF/body/ESD qualification, full Gen3x4 or final mainchip STA.
