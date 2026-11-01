# q15 A/C divider impedance experiment

This is an exploratory intrinsic experiment derived from rejected q15 run41277054717. Original eight master lengths stay2.6um/W32. The q15 sixteen resistor changes remain: eight output loads1.5um/W32, four buffer pullups1um/W8, four shunts3.4um/W4.

Read-only original-wave diagnostics41280306194 and41280275014 passed7 frozen-reader,13 event and8 transfer controls plus an authenticated actual-topology preflight. q15 A->AD had127 source transitions but only22 matched buffer crossings within the bounded125ps window; C->CD had128/14. The respective sampler-to-base median observed matched delays were61.9468ps and68.6585ps. These are diagnostic correlations, not proof that changing resistance fixes the circuit. Full35-file proofs031a9d3d6554b1574f4ba609279d3543cff03b8e and3266bcfca451cc2e8c06ac372409f1dbb240fb04 retain all events and original metrics.

## Controlled delta

Only eight additional A/C divider lengths change:
* Series R227,R229,R238,R240:3.6um ->1.8um, width1um.
* Ground shunts R228,R230,R239,R241:21.6um ->10.8um, width1um.

This preserves the geometric series/shunt length ratio and tests reduced input impedance. It does not assume unchanged loaded DC voltage: base current, contacts, output loading and device capacitance remain in the actual nonlinear simulation. D->S0/S1 dividers, all MIM capacitors, all HBT emitter counts, and all remaining device parameters are unchanged. In total exactly24 intrinsic length tokens differ from the authenticated original500-device model; this is a distinct target set from the older24-resistor master/buffer candidate.

The mutation requires exact500-device census, every targeted original model parameter, ordered terminals/net/cluster and complete native card tokens. Reversing the24 changes must recover every original model byte and composition value. Source controls include21 corruption refusals and5 archive refusals; actual preparation retains13 original binding controls.

All original prepare/measure function bodies,150fF sampler and50fF XOR loads,10ohm sources,1151 vectors, stimulus,125ps UI,100mV/37.5ps sampler,100mV/75ps XOR, device current/voltage and phase/VI gates remain fixed. Current at3mA per emitter remains a failure. Original distributed wire RC is retained for exploratory comparison; this is not fresh PEX or regenerated layout.

Run source controls first, preserve their complete proof, then independently reserve an empty exact-source release for one actual native run. Record all failures and full native/derived evidence on GitHub. No native archive, model, SPICE, wave or geometry is acquired locally. A passing circuit would still need a new full physical map for these eight divider instances, independently authored schematic changes, physical DRC/LVS, fresh RC, corners and closed-loop validation. FullPHY and finalchip timing remain open.
