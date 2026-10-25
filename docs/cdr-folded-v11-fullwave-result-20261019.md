# Folded CDR full loaded result — 2026-10-19

Run [39237412866](https://github.com/Melihakbulut221/nssoc/actions/runs/39237412866)
used source649e7406fb4ec7e9d2c227115e3587bb5fa7a916 and the freshly extracted
folded layout:484 native devices,15482 wire resistors,11590 capacitors including
11 native MIMs exactly once. Original256bits, fixed phases, loads and all device
gates were retained. Nominal early/late both REJECTED; clock-stop and VI-bias-off
negative controls passed as fault detection, not as functional PHY acceptance.

| Measurement | Previous early | Folded early | Previous late | Folded late |
|---|---:|---:|---:|---:|
| Wrong sampler observations |796|885|759|745|
| Low sampler margin observations |942|1148|935|970|

The early phase output is +0.047133V, the wrong polarity for early data.
Its VI current also has the wrong sign. HBT xpd.xd0129 falls below the
unchanged0.4V active VCE gate:0.398285618V. The late phase/VI gates and all
late device checks pass, but all four sampler and both comparison gates fail.
Thus the clock-span reduction has not closed data timing and cannot be adopted
as an accepted PHY. Longer internal nets in the folded layout remain a possible
cause to investigate; this result alone does not establish that cause.

Full immutable receipts, exact summary/parts hashes and before/after measures
are in docs/evidence/cdr-folded-v11-*.json. Next work must investigate native
internal data/tail/clock delays from the saved waves and actual extracted paths,
without moving sample phases or relaxing device limits. Closed-loop recovery,
PVT and qualified RF/body PEX remain open.
