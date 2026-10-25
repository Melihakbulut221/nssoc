# Fresh CDR local-bus extraction result — 2026-10-19

[Run39249871918](https://github.com/Melihakbulut221/nssoc/actions/runs/39249871918)
passed all four native stages against the physically verified localbus_v12
parent. Complete source-bound reports are preserved in docs/evidence.

- All16 macro placements and8 child drawings conserved;158 native planes,
  51 logical nets,1394 terminals;19 plane and3 geometry controls.
- Whole actual metal graph and946 physical/reference points bound without
  merging conductor components by labels.
- Native484-device compact-model binding passed its original12 fault controls.
- Fresh wire-only extraction:15459R,11479C,111 connected conductor components,
  zero disconnected probes; original point/value/ownership and collapsed-C
  conservation passed, along with13 raw corruption controls.

The earlier folded parent had15459R/11579C in its wire-only capture. A lower
number of capacitor records alone does not establish lower critical loading,
correct sampling or better timing. Those require the full actual model and
unchanged electrical gates.

MIM-aware capture39250952988 at source
dfa37e1f272e2726f1f90715fc1b07668fbb9cec is active. It consumes these exact
four successful releases; preserve it and do not start a duplicate.
After it completes, verify the actual new R/C census and11 native MIM
identities, run original22 raw audits/19 composition controls, then the
unchanged loaded early/late and clock-stopped/VI-off waveforms.

Wire-only extraction retains473 unmodeled body/well terminal dispositions;
it does not qualify substrate impedance, RF distribution, closed-loop CDR,
full serial Gen3x4, mainchip integration or final setup/hold.
