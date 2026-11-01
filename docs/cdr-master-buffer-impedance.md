# Master/slave latch and input-buffer impedance experiment

This supersedes the rejected12-resistor coupled-load candidate for experimental design only. It does not accept or modify its layout.

## Evidence and mechanism

Full original-gate native comparison41273897568 found only B passing; A/C/D/X/Y failed. Native wave diagnosis41274403461 (sourceb3b4c87e894662f61eb53210c1dbe982885b3f00) repeats all124HBT metrics, all6stage/1530bit delays and phase/VI outputs with the original frozen reader. Seven inherited controls and9event controls pass, including the strict Ic/emitter<3mA boundary. Its preceding diagnostic41274356086 is retained but superseded because its event detector treated current equality as passing; no simulator or original measurement was changed.

Voltage maxima at XD0059/60/111/112 occur during active operation around3.72–3.96ns, not only initialization. Collectors reach about2.016–2.047V while emitters are0.371–0.391V, giving maxVCE1.638–1.656V against1.6V. XD0061's minimum at30.312ns is0.398992V (collector0.909276V/emitter0.510284V) against0.4V.

The exact topology shows XD0059/60 andXD0111/112 are input differential pairs with pullups plus shunts at their collectors. Those collectors directly drive the following master latch. Reducing only final Q load resistors improved B but left the master loads unchanged; increasing only the shunt length raised the off-side collector and created active overvoltage. These measurements motivate reducing buffer impedance while limiting its high level and reducing master settling time together.

## Exact exploratory intrinsic delta

All lengths are um. Width, model, instance identity, terminals and unrelated parameters remain unchanged.

* 16master/slave collector loads: XD0175/176/177/178/191/194/195/196/202/205/207/208/212/214/215/216, L2.6->1.5 atW32.
* 4buffer pullups: XD0182/183/220/221, L1.8->1.0 atW8.
* 4buffer shunts: XD0184/185/222/223, L5->3.4 atW4.

This is a24-length-token modification from the authenticated original baseline, not a chained edit of a failed native model. Shorter paired buffer pullup/shunt devices are an initial engineering hypothesis for lower loaded impedance and narrower voltage excursion; actual resistance includes contacts and the model, so length ratios are not accepted as a measured voltage prediction. Lower latch/load swing, increased bias loading and supply/wire drops may still cause failure. Only the full native screen can decide.

The original500-device census, complete model bytes outside these24tokens, wire RC,10ohm source resistance,150fF sampler/50fF XOR loads, clock/data waveforms,1151saved vectors, active and all-time predicates and frozen prepare/measure code remain unchanged. Source controls include17malformed-circuit refusals and5archive refusals. The original13actual binding controls still run on the native deck.

## Admission and physical follow-up

First run exact-source source controls. Before simulator start, independently reserve and read back an empty exact-source output release. The host verifies that reservation and its own completed source-controls job. Preserve success or failure fully. No native artifacts are downloaded locally.

No layout regeneration or new RC is claimed here. The old12-instance map is insufficient for this24-device candidate; a passing screen requires a new complete map, private cells for all shared targeted PCells, actual geometry, native DRC/LVS, freshRC, corners and closed-loop/wholePHY verification.

Original inherited voltage screening is preserved. As documented in the IHP [bipolar process specification](https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/03_bjt_params.html), a typical breakdown figure is not a foundry-approved operating envelope. A passing1.6V screen does not by itself prove reliability or production approval.


## Terminal result

Native run41274791029 (sourceeca0c5abf194169c8b42f58a48f22feb716e7dec, release430370301) completed with engine returncode0 and no native diagnostics after1139.887429s. The original full device predicates passed, but all six data stages, phase and VI current failed. This is an electrical rejection, not a simulator-start or archive error.

| Stage | Maximum delay ps | Minimum signed mV | Below100mV samples | Wrong-sign samples |
| --- | ---: | ---: | ---: | ---: |
| A | 45.46875 | 39.13727 | 109 | 0 |
| B | 118.90625 | 62.21606 | 83 | 0 |
| C | 118.90625 | 17.87941 | 269 | 0 |
| D | 118.90625 | -3.06290 | 155 | 3 |
| X | 118.90625 | -103.49336 | 763 | 371 |
| Y | 118.90625 | -6.53915 | 756 | 125 |

Phase5.619233mV is below30mV. VI current19.073419uA is below50uA; VI voltage5.209325mV passes5mV. Original nominal HBT margins now pass, including minimum VCE atXD61 .410003V andXD115 .410431V, but this proves neither corners nor reliability.

Full64-file terminal proof8d5acc3dd28028897d09b6adc46bfcdfae8392be and actual comparison41276473135/source78cd193415dcb2445ad3d50e318815f5d8e6beb8/full15-file proof8431599645f7adf3efe96815df67550ceb689dae preserve complete source, controls, measurements and logs. The comparison repeats13corruption refusals and verifies the entire24-token binding and all original gates. Original reports remain available; no acceptance is transferred from a synthetic fixture.

Physical map41274889443 passed9controls and all500devices/4928instances/24targets without modifying geometry. Its24targets cover all native users of four selected resistor cell definitions within the complete500-device census. This fact does not authorize reusing shared master/slave cells for the follow-up16-target candidates: restored master users must remain unchanged.

## Controlled follow-up

See [original-master follow-up](cdr-original-master-followup.md). Restore eight master lengths and retain the new input-buffer values, then compare two output-load lengths. This separates two effects previously changed together. Neither variant is accepted before its real native results pass the unchanged predicates. No new layout, DRC/LVS or freshRC is claimed.
