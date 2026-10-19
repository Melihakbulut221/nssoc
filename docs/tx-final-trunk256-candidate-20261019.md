# TX final return trunk candidate, 2026-10-19

The6um local strap reduced the final-tail mean static return resistance by only0.089730153ohm. Read-only native coordinate review39222023394 identified the unchanged shared0.706551ohm branchR105585 betweenP_avss.n5354 andP_avss.n5353. Both endpoints lie inside the final-column128um TopMetal1 return trunk, separated by more than4mm inY. EXT coordinates use the file scale0.5centimicron per unit, as specified in[Magic EXT format](https://opencircuitdesign.com/~tim/programs/magic/manpages/ext_manpage.html). The candidate geometry verifier independently repeats this source-bound unit conversion and containment check in the cloud.

The new candidate widens only this final-column TM1 trunk from128to256um at its current center. The6um local emitter strap, all via arrays, all other rails, all31 device macros, signal routing and circuit stay unchanged. The larger bottom extent shifts the normalized layout origin; the whole-GDS delta comparison compensates only that known origin translation and rejects any additional drawing change.

Exact whole-GDS delta, three corruption controls, original1674-device deep/flat LVS,560-category DRC and original transistor/connectivity/grid fault controls must all pass. Fresh native RC and full loaded waveform testing remain mandatory. The target branch reduction and electrical benefit are not assumed or marked passed. No parasitic scaling or waveform threshold change is allowed. Original strap6 full-wave run39221063981 remains running independently.

## Native physical pass

Run39222629402 at3e0b1192107823f3e80bdbfb332da8ea761bf038 passed the exact whole-GDS delta (693022.72um2 added TM1), three geometry corruption controls, deep/flat1674-device LVS, zero-marker560-category DRC and the five original device/connectivity/grid fault controls. The verifier bound the measuredR105585 endpoints to the prior final trunk, checked unchanged6um local strap and all via layers, and allowed no other drawing change after normalizing origin translation. Fresh native RC extraction is now required; no resistance reduction or electrical pass is inferred from this physical result.
