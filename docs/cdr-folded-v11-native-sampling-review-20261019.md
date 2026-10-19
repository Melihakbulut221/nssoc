# Folded CDR rejection diagnosis from original native captures

The shorter sampler clock geometry did not close full loaded sampling.
Run39237412866 has885/745 wrong sampler observations for nominal early/late.
Early phase/VI has the wrong sign and native HBT0129 fails active VCE.
All original electrical rejection gates remain in force.

This cloud-only review restores each exact saved whole wave and its actual
484-device/15482R/11590C MIM-aware native model. It reproduces every original
sampler wrong-sign/margin count, reads the original0.3/0.6/0.9UI samples, and
traces the real master/slave bases, collector wires, intrinsic load drops,
local clock crossings and device terminals. It performs no new transient,
latency fitting, phase change, ideal internal stimulation or RC scaling.

The reused diagnosis previously expected no failed HBT because its source
case had none. For the new rejected early capture it now requires precisely
the saved HBT0129 failure, reproduced from the raw terminal voltages/currents;
late still requires none. This changes diagnostic applicability, not the
0.4V VCE,1.6V VCE/1V VBE/3mA per-emitter functional acceptance thresholds.
Every original native device check is recomputed against its saved result.

Shortest resistor path sums are upper bounds on path resistance, not effective
RC delay. Incident wire capacitance excludes intrinsic device loading.
Only actual native waves support voltage/timing observations. Compare the
new reports with the earlier input-drive-v10 reports before choosing the next
physical sampler placement/data-tail-clock repair. Complete PHY and recovered
closed-loop clock remain unproven.

## Native review result

Run39243551295 reproduced the original rejected gates. Early sampler A has
zero wrong/low observations at0.6/0.9UI but still105wrong/129low at the required
0.3UI; sampler B still has34wrong/109low at0.6UI. No late phase is substituted
for the original gate. The failedHBT0129 was reproduced at19.62259375ns:
VCE0.398285618V, base1.735160571V, emitter1.291549943V, collector1.689835561V.
Its base is on native logicaladp; its collector/emitter are internal nets.

External clock incident wire capacitance is about1.21354pF(cp)/1.12309pF(cn),
but internal emitter/tail networks must also be checked. The next read-only
stage comparison traces actual sampler master/slave input emitter terminals
to selector collectors and common MOS tail drains through the native111
conductor groups, then compares wire quantities and saved terminal voltages
against the original v10 captures. It changes no geometry or acceptance gate.
