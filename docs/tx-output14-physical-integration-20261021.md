# TX output stage preparation for actual lane integration

The actual8074 bench uses xtx: inp=mp, inn=mn, outp=op, outn=on, avdd=tvdd, avss=sub=0, iref=tr.
The frozen output model has four HBTs (Nx1,8,8,8), two native rsil loads W10um L70.215um,
and three zero-volt measurement probes. It presently idealizes substrate contact.

The existing native generator78bf226b2d81f821501e5661876068dd60725c005734d770be87fbd857c9be2c
is reused unchanged. Fresh cloud DRC and unsimplified deep/flat transistor LVS must retain
four HBTs, two rsil and all eight distinct native ptap1 contacts, eight ports and independent
SUB/BULK. Six native reference/geometry faults and six actual-bench binding faults must reject.

Source binding removes only the three declared measurement probes and maps ideal source
SUB to internal physical BULK connected via eight real contacts to public SUB.
This is a documented model change requiring fresh extracted electrical validation.
No pass here constitutes parent integration, wire RC qualification or full PHY acceptance.
Next: native point/RC extraction of output14, actual parent placement and finite mp/mn,
power/reference/substrate/output intermacro routes, fresh whole-lane DRC/LVS and full
original waveform gates. Clock modulation and other bias boundaries are still required.

All execution and artifacts remain in GitHub. Legacy evidence and live native TX simulations
remain unchanged; the physical lane candidate must receive a new model and provenance.
