# NMOS isolation fixtures

The prior ideal-gate full output fixture reproduces the low-drive turnoff failure even with receiver and decoder removed. These three further reduced diagnostic circuits retain125C/slow models/supplies,1.5V pad clamp,1ps,KLU,Gear2,itl4=100 and unchanged native tolerance/model bytes:

- n_clamp: original sg13g2_Clamp_N2N2D, including its two HV NMOS devices, antenna diode and guard-ring declarations.
- n_forward: only original forward-oriented sg13_hv_nmos, drain=pad,source/body=iovss,l0.6um,w4.4um.
- n_reverse: only original reverse-oriented sg13_hv_nmos,drain/body=iovss,source=pad,same dimensions. Do not swap these terminals to manufacture a pass.

All use ideal gate sources from prior fixture. Data0 drives gate3V then0V on disable; data1 keeps NMOS gate0V, so those cases are off-state controls and must not be required to drive current. PMOS and pad-level DC protection diodes are explicitly omitted. These changes isolate behavior, never qualify a replacement pad. Preserve full-pad failure and all production gates.

Every independent capture still requires50ns,finite/increasing samples,step bound,native solver readback and no numerical diagnostics. Synthetic continuation/readback tests run before native simulations. Compare failing instances and body/drain orientation before attributing causality to compact models or compiler/runtime. Main route44337630426 remains independently active.
