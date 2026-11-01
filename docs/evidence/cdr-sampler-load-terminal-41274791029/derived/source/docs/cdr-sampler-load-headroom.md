# Master/slave latch and input-buffer impedance experiment

This supersedes the rejected12-resistor coupled-load candidate for experimental design only. It does not accept or modify its layout.

## Evidence and mechanism

Full original-gate native comparison41273897568 found only B passing; A/C/D/X/Y failed. Native wave diagnosis41274403461 (sourceb3b4c87e894662f61eb53210c1dbe982885b3f00) repeats all124HBT metrics, all6stage/1530bit delays and phase/VI outputs with the original frozen reader. Seven inherited controls and9event controls pass, including the strict Ic/emitter<3mA boundary. Its preceding diagnostic41274356086 is retained but superseded because its event detector treated current equality as passing; no simulator or original measurement was changed.

Voltage maxima at XD0059/60/111/112 occur during active operation around3.72–3.96ns, not only initialization. Collectors reach about2.016–2.047V while emitters are0.371–0.391V, giving maxVCE1.638–1.656V against1.6V. XD0061's minimum at30.312ns is0.398992V (collector0.909276V/emitter0.510284V) against0.4V.

The exact topology shows XD0059/60 andXD0111/112 are input differential pairs with pullups plus shunts at their collectors. Those collectors directly drive the following master latch. Reducing only final Q load resistors improved B but left the master loads unchanged; increasing only the shunt length raised the off-side collector and created active overvoltage. These measurements motivate reducing buffer impedance while limiting its high level and reducing master settling time together.

## Exact exploratory intrinsic delta

All lengths are um. Width, model, instance identity, terminals and unrelated parameters remain unchanged.

*16master/slave collector loads: XD0175/176/177/178/191/194/195/196/202/205/207/208/212/214/215/216, L2.6->1.5 atW32.
*4buffer pullups: XD0182/183/220/221, L1.8->1.0 atW8.
*4buffer shunts: XD0184/185/222/223, L5->3.4 atW4.

This is a24-length-token modification from the authenticated original baseline, not a chained edit of a failed native model. Shorter paired buffer pullup/shunt devices are an initial engineering hypothesis for lower loaded impedance and narrower voltage excursion; actual resistance includes contacts and the model, so length ratios are not accepted as a measured voltage prediction. Lower latch/load swing, increased bias loading and supply/wire drops may still cause failure. Only the full native screen can decide.

The original500-device census, complete model bytes outside these24tokens, wire RC,10ohm source resistance,150fF sampler/50fF XOR loads, clock/data waveforms,1151saved vectors, active and all-time predicates and frozen prepare/measure code remain unchanged. Source controls include17malformed-circuit refusals and5archive refusals. The original13actual binding controls still run on the native deck.

## Admission and physical follow-up

First run exact-source source controls. Before simulator start, independently reserve and read back an empty exact-source output release. The host verifies that reservation and its own completed source-controls job. Preserve success or failure fully. No native artifacts are downloaded locally.

No layout regeneration or new RC is claimed here. The old12-instance map is insufficient for this24-device candidate; a passing screen requires a new complete map, private cells for all shared targeted PCells, actual geometry, native DRC/LVS, freshRC, corners and closed-loop/wholePHY verification.

Original inherited voltage screening is preserved. As documented in the IHP [bipolar process specification](https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/03_bjt_params.html), a typical breakdown figure is not a foundry-approved operating envelope. A passing1.6V screen does not by itself prove reliability or production approval.
