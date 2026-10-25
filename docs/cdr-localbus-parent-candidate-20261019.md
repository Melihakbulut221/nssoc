# Local-bus CDR parent candidate — 2026-10-19

Sampler run [39247903547](https://github.com/Melihakbulut221/nssoc/actions/runs/39247903547)
passed the unchanged560-category native DRC screen, unsimplified deep/flat54-device
LVS, LEF and16negative controls. This fixes the first candidate's10M5.b markers.
All54 native drawings, placements, primitive parameters and public pins are
unchanged; only internal bus/column geometry changed. Full report and hashes:
docs/evidence/cdr-localbus-sampler-physical-pass-20261019.json.

The new localbus_v12 parent restores that exact leaf and the seven unchanged
other native child types. All41 source cards,16 macros,484 physical devices and
original parent DRC/LVS/fault gates remain. Source-delta controls bind the
adaptation to folded_v11. Independent native leaf drawing conservation is
rerun against the exact folded leaf.

This is not electrical or PHY acceptance. Even after native parent success,
fresh geometry planes, terminal binding, wireRC, MIM capture/audit/composition
and unchanged full loaded nominal early/late and fault waveforms are required.
Old foldedRC must not be reused. Recovered-clock operation, complete serial
Gen3x4 and final mainchip setup/hold remain OPEN. All execution is in GitHub;
the local workspace remains empty.
