# Audited local-bus CDR model and full native waveform campaign

[Validation39251956786](https://github.com/Melihakbulut221/nssoc/actions/runs/39251956786)
passed the original13 raw-wire plus9 intrinsic-MIM controls and19 composition
controls. All fresh native point/value/ownership/capacitance checks are retained.
The resulting model nssoc_cdr_pd484_localbus_mim_wire_v12 contains484 native
devices,15482R,11490C and exactly11 intrinsic MIM instances.

The new cloud waveform matrix uses this model with the original complete
256-bit34.25ns transient, fixed phases and150fF sampler/50fF XOR loads.
Nominal-early, nominal-late, clock-stopped and VI-bias-off cases are retained.
Original bit truth, HBT/MOS voltage/current limits, native startup readbacks,
solver/timestep/diagnostic gates and real collector-current readback remain.
Only the actual new model namespace, input receipts and measured C count
change. No waveform phase fitting, RC scaling or shortened trajectory is used.

Await actual results. Physical/extraction/model validation does not prove
sampling, phase detection, full closed-loop CDR, Gen3x4 or mainchip timing.
All execution and raw artifacts remain in GitHub.
