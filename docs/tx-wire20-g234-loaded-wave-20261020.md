# Actual wire20 composition verified; original full-wave test

The corrected [composition39407840528](https://github.com/Melihakbulut221/nssoc/actions/runs/39407840528) passed all1674-device/116611R/77538C composition checks, six malformed-model controls, and124 actual input legs/372 data-base bindings with both wrong-endpoint controls. The original failed handoff39407119769 is retained.

Compact model SHA256: `f9bf6f7473546b80a91541e0fab9b74cb0ff567a89ece495ebfef097c39c28ca`.
Distributed model SHA256: `d701fa02f415c1ba3e8f6a1243c362bc085a4b02df736712cf324b0a188899fe`.

The new cloud-only test changes only the physical core source to this freshly extracted2.0µm geometry. It keeps the actual eleven clock macros (l5p7 at groups0/2/3/4 and l6p25 elsewhere), full34ns/256bits, three sampling phases, loads, native simulator/solver settings, all604HBT/512MOS limits,124 interfaces, and actual leaf-selection fault. Native physical-position-based compact-model correspondence with all three malformed-model cases and identity-swap fault precedes each simulation. New model hashes are exact, not an arbitrary accepted range.

The previous wire24 group234 nominal result (83wrong output samples/768,104low,6failingHBT) remains rejected. The wire20 candidate is not electrically accepted until its unchanged gates pass. No reduced-duration, ideal intermacro core connection, shifted sampling, phase fit or changed device limit is introduced.

This isolated nominal test retains external ideal clock modulation, supplies and some frontends. Even an electrical pass does not establish recovered serial Gen3x4, PVT/channel/jitter/ESD qualification, substrate/RF PEX or mainchip integration. Mainchip fanout route39407840101 runs separately.
