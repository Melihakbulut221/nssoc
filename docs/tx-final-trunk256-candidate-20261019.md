# TX final return trunk candidate, 2026-10-19

The6um local strap reduced the final-tail mean static return resistance by only0.089730153ohm. Read-only native coordinate review39222023394 identified the unchanged shared0.706551ohm branchR105585 betweenP_avss.n5354 andP_avss.n5353. Both endpoints lie inside the final-column128um TopMetal1 return trunk, separated by more than4mm inY. EXT coordinates use the file scale0.5centimicron per unit, as specified in[Magic EXT format](https://opencircuitdesign.com/~tim/programs/magic/manpages/ext_manpage.html). The candidate geometry verifier independently repeats this source-bound unit conversion and containment check in the cloud.

The new candidate widens only this final-column TM1 trunk from128to256um at its current center. The6um local emitter strap, all via arrays, all other rails, all31 device macros, signal routing and circuit stay unchanged. The larger bottom extent shifts the normalized layout origin; the whole-GDS delta comparison compensates only that known origin translation and rejects any additional drawing change.

Exact whole-GDS delta, three corruption controls, original1674-device deep/flat LVS,560-category DRC and original transistor/connectivity/grid fault controls must all pass. Fresh native RC and full loaded waveform testing remain mandatory. The target branch reduction and electrical benefit are not assumed or marked passed. No parasitic scaling or waveform threshold change is allowed. Original strap6 full-wave run39221063981 remains running independently.

## Native physical pass

Run39222629402 at3e0b1192107823f3e80bdbfb332da8ea761bf038 passed the exact whole-GDS delta (693022.72um2 added TM1), three geometry corruption controls, deep/flat1674-device LVS, zero-marker560-category DRC and the five original device/connectivity/grid fault controls. The verifier bound the measuredR105585 endpoints to the prior final trunk, checked unchanged6um local strap and all via layers, and allowed no other drawing change after normalizing origin translation. Fresh native RC extraction is now required; no resistance reduction or electrical pass is inferred from this physical result.

## Fresh native RC pass

Run39223805006 ateebfce6fdadef5921116bae53483407772b73ddf passed the original native graph, terminal ownership, capacitance conservation and13 raw-corruption controls. It extracted116611 resistors and77514 capacitors across377 metal components with1674 devices and3262 probes. Counts match the predecessor, but values are newly extracted from the wider trunk. Full-model composition, measured return resistance and unchanged loaded waveform gates remain pending; no electrical improvement is inferred from the extraction pass.

## Full model composition

Run39224815994 at aa24170d0ed625a57690805858ba09769edcf1aa passed full1674-device composition with the fresh116611R/77514C graph, six original composition fault controls and physical binding of124 input legs to372 data bases. No ideal intermacro aliases or duplicate child parasitics were introduced. Compact topology equivalence against the verified strap6 model is the next gate before updating the source-bound waveform builder. The electrical result is still unproven.

## Topology and loaded tests

Run39225546587 proved all1674 compact devices equivalent to the strap6 baseline using physical primitive positions, with exact parameters, fixed public nets and a bijective internal-node map. Missing-device, changed-parameter, wrong-terminal and swapped-physical-identity controls were rejected. Candidate-specific builder hashes and a clock-adapter import now select only this proven model; all source bits, sampling phases, solver and device gates remain unchanged. Full nominal256-bit loaded simulation, swapped-leaf fault simulation and independent native return-resistance comparison are launched separately in the cloud. Neither model equivalence nor DC diagnosis establishes waveform or full PHY acceptance.
