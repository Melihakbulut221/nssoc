# Pullup geometry hypothesis after native headroom diagnosis

The actual localpins driver fails12HBT minimum0.4V VCE gates. Full-capture
replay38929031066 reproduced every original engineering field. At xd0125's
native worst sample24.409808ns, C=0.957976V and E=0.620758V: VCE=0.337218V.
Simultaneous d0p/d0n are1.811197/1.792500V, a low common-mode transition.
The intrinsic control has a higher collector voltage at its own worst sample;
those distinct timestamps do not by themselves establish causality.

The source-bound native100-device mapping identifies XD87 unambiguously as
XUP: avdd-to-dout rppd, width4um,length3.08um,ps0,b0,m1. Two prospective
lengths2.7um and2.4um test whether stronger pullup support can prevent the
low-output/common-mode transition from reducing selector collector headroom.
This is a hypothesis, not a demonstrated correction. Current and all device
limits remain evaluated; raising a node must not silently trade a minimum
VCE failure for excessive VCE/VBE or MOS stress.

The cloud study preserves every original260wireR/295wireC, all other99raw
devices and finite contacts, and the12um input-gate damping resistor. Named
native terminal bindings, original resistor parameters and exactly one length
change are checked. Deliberate gate-damping and pullup-terminal corruptions
must fail. All8drivers,672MOS,62HBT,full34ns/256sourcebits,zeroOP,original
0.3/0.5/0.7UI phases and100/150mV/0.4V criteria remain unchanged.

This uses frozen old interconnect with a changed compact resistor parameter:
it is a schematic sensitivity, explicitly not a physical candidate. A useful
result requires a new physical resistor/driver layout, native DRC/LVS, fresh
terminal binding/RC/composition and full loaded/PVT tests before adoption.
Neither variant closes32:1/four-lane SERDES, PLL/CDR or mainchip timing.

## Physical realizability experiment

The shared localpins generator now accepts explicit l2p7/l2p4 pullup variants.
The default original geometry remains available. Each variant starts with the
SHA-pinned original schematic and proves that the parsed device census differs
in exactly one XUP length field; all other rows and source text are unchanged.
Actual native rppd PCells use the new length, and access geometry is recomputed
from their actual conductor pin boxes. The effective schematic, raw and aggregate
physical references, geometry and complete source-change audit are preserved.

The tx-input-driver-pullup-cloud workflow generates both physical candidates in
GitHub runners. Each must pass the original native DRC and four deep/flat,
raw/combined LVS comparisons with 100 raw devices, plus every original physical
fault. An additional actual wrong-length schematic (original3.08um against the
new GDS) must fail LVS. Neither frozen-wire sensitivity nor these physical gates
qualifies the new interconnect: fresh native extraction, terminal mapping,
wire RC, composed loaded capture and PVT remain mandatory before adoption.

## Physical results and next native extraction

Cloud run38932966041 (sourceabe4789b219810eb893bc5f2dd85dbea5713ddee)
completed both variants successfully. Each passed four native LVS comparisons,
full DRC and all eight negative cases, including the wrong3.08um pullup length.
The actual100-device physical references contain exactly one changed source row.
GDS hashes and both source summary/parts hashes are frozen in
scripts/cloud_tx_driver_pullup_junctions.py, whose cloud workflow restores only
the needed authenticated native GDS/LVS/reference files. It exports fresh raw
and combined junction records, retains all original five MOS binding controls,
independently binds all four physical resistors, and rejects a changed resistor
length or body. This is still not wire RC or loaded electrical acceptance.

## Actual pullup layouts and fresh RC complete; loaded studies active

Cloud-only checkpoint: 2026-10-16T17:01:43.813343+00:00. The local project directory remains empty.
This goal turn made physical/model progress; it is not blocked. Do not restart
healthy runs. Full serial Gen3x4 PHY, mainchip routing and final timing are open.

- **Actual fresh-RC loaded run38936139904**, source9e6679b30a0f31556d0ea32097cefd1c480dc47e, is active for both l2p7/l2p4. It uses the actual new GDS-derived100-device models and new260R295C wire extraction, unchanged full34ns/256bits/0.3,0.5,0.7UI/672MOS/62HBT gates, same physical downstream162-device tree. Inspect both results and retain failures; do not confuse them with frozen-wire sensitivity38931374696. External clocks/supplies/intermacro boundaries, four-lane32:1 PHY and qualification remain open.
- **Native physical38932966041 passed both variants**: four raw/aggregate/deep/flat LVS comparisons, DRC, all original faults and an added actual wrong-pullup-length LVS mismatch. Only XUP length3.08um becomes2.7/2.4um; gate damping12um and other devices preserved. Generator scripts/cloud_tx_input_driver_localpins.py has explicit --pullup-length; default original unchanged.
- **Junction38933670094, wire/contact38934298533, intrinsic38934646634, freshRC38935036370 and composition38935779019 all passed both variants.** Each has100devices,372terminals(272metal/100body),164referenceplanes,10wirecomponents,260R295C; five original MOS binding faults+two resistor faults, four contact faults, eight intrinsic faults,13nativeRC faults and10composition faults were rejected. Three combined/raw MOS junction disagreements remain recorded; actual raw fingers supply the models. Native extraction scope is not qualified substrate/poly-diffusion/RF/PEX.
- First composition38935616068 failed before composition with KeyError source_unchanged because the RC producer does not publish that flag. Fixd5e2c134de853818424bb2e999b13db495938cb2 validates every restored output hash for both schemas, retains the intrinsic flag check and all physical/model controls. Corrected38935779019 passed. Preserve the initial failure; no circuit or engineering limit changed.
- **Frozen-wire sensitivity38931374696 is complete, both electrically FAIL** despite successful workflow execution. l2p7: output171.306mV,CMOS163.418mV,final133.826mV/288below150mV;12HBTfail,0MOSfail. l2p4: output177.705mV,CMOS158.474mV,final135.955mV/261below150mV;2HBTfail(xd0001/xd0003 VCE0.393142/0.393154V vs0.4Vlimit),0MOSfail. Both full34ns,zeroOP,0wrongoutput/0below100mV,0solverdiagnostics. This narrows the next correction to the remaining two HBT headroom failures and final interface margin; the actual binding identifies the final2:1 selectors; never lower limits or adopt frozen wires.
- **Nine-size full-signal route38930352215** and **native full1usPLL38910378266** are still active at this observation. Follow the prior exact native continuation and independent route review instructions below.

All source/receipt hashes and measured failures are in
`docs/evidence/tx-driver-pullup-results-20261016.json`. New controllers are
cloud_tx_driver_pullup_{junctions,wires,intrinsic,rc,compose,loaded}.py.
No new archive or CAD output exists locally. After loaded results, use actual
waveform/device failures to choose the next source/geometry repair; fullPVT,
32:1/four-lane integration, clocks/CDR and mainchip acceptance remain required.

