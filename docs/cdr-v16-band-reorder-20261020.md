# CDR v16 physical-band reorder candidate

The completed v16 latch diagnosis reproduces the original sampling failures. A/B outputs settle late, and C/D additionally receive weak incoming data. Their long physical source/filter/consumer paths motivate this candidate.

The candidate starts from the **actual DRC/LVS-clean v16 GDS** with SHA256 c920186862bde235868d3fa009fedcff868246750f0fa38874e3c6b42ba7255e, not an earlier layout. It retains all484 native devices, child PCell hierarchy and all v13/v14/v15/v16 local metal and via additions. It partitions only the first six macro bands, enumerates all720 orders and chooses a strictly shorter retime span under explicit clock-span and unchanged data-input-span planning bounds.

Every non-trunk parent conductor must fit wholly within one movable band or the unchanged public supply entry region. A crossing conductor aborts generation. Only the original global TopMetal1 trunk rectangles are replaced by rectangles derived from the new actual branch positions. Source and candidate per-net spans and every considered order are retained.

The serialized GDS must exactly match the conserved parent-band geometry, unchanged translated child drawings and rebuilt trunks. The reference circuit is byte-identical. Public signal pin positions and LEF are regenerated to match the actual moved connections. The independent16-placement/eight-leaf geometry checker, its three faults, the original560-rule DRC, deep/flat484-device LVS and original physical/reference faults remain mandatory.

This is a physical repair candidate, **not** electrical acceptance. Geometric span bounds are not timing constraints or new waveform gates. Fresh whole-parent MIM-aware distributed extraction and the original full loaded early/late tests are required even if DRC/LVS passes. There is no change to circuit values, waveform oracle, sample phases, loads or acceptance limits. The rejected v17 resistor-divider experiment is not used.

All generation and verification execute in GitHub Actions. No local CAD output or source checkout is created.

## Measured physical result and next extraction

[Run39379285294](https://github.com/Melihakbulut221/nssoc/actions/runs/39379285294), source6fae6cae4e8242e3436fe8873b5e42bed7e112be, passed the original560-rule DRC, deep/flat484-device LVS with no extraction diagnostics, all nine native physical/reference faults, and exact child/serialized geometry conservation. The actual new GDS SHA256 is27321a65507bccd81228e05933676158794b3c099186535fd4f9b892afacb37e. The [full receipt](evidence/cdr-retime-bands-v18-physical-pass-20261020.json) binds the original report and all geometry controls.

The selected prefix is sd,bd,sb,sa,sc,ac. Total targeted retime-net span fell from5387.34um to3455.56um (35.86%). Input dp/dn spans remain323.63um. The tradeoffs are retained: cp grows964.89→1189.52um, cn976.89→1189.52um, and D-output dqp/dqn grow by865.89um. These are geometrical measurements, not measured electrical delay or accepted timing.

The new v18 extraction pipeline restores this exact physical result and reruns all158 native interface bindings, all484-device/1394-terminal model bindings, actual terminal-plane recovery and full wire graph/R/C auditing. It retains the original nineteen interface faults, twelve model faults and thirteen raw-R/C corruption controls. Original v16 extraction sources remain unchanged; an exact source-delta checker permits only the new physical provenance, model/view names and artifact paths. No old RC is reused for this placement. Whole-parent MIM composition and the original full loaded early/late electrical checks must follow.

## Fresh extraction completed; MIM-aware audit and assembly continue

[Fresh extraction39379894690](https://github.com/Melihakbulut221/nssoc/actions/runs/39379894690) passed all four stages:158 interfaces,484 devices/1394 terminals,111 physical conductors, native compact-model binding and strict wire-only RC checks. The wire-only extraction contains17651R/12701C.

[Whole-MIM capture39380388968](https://github.com/Melihakbulut221/nssoc/actions/runs/39380388968) then completed with all eleven actual MIM devices and946 physical points:17674R/12712C. These counts differ from the old placement and are bound to the new native capture receipt. They are not substitutes for raw geometry/ownership/value auditing.

The next pipeline independently audits raw R/C with the original thirteen corruption controls, validates MIM identities/plates/dimensions with the original nine intrinsic corruptions, and composes the actual484-device model while retaining all nineteen assembly faults. MIM devices must appear exactly once. Original v16 methods remain intact; only source identities, paths, model name and the newly measured capacitance/token census change. Loaded electrical waveforms are still pending.

## Original full loaded waveform comparison

The new fullwave workflow is bound to validation run39380893611 at source762861b4b1b13b5baf6c9634a87a731ab6e613fa. It requires successful independent raw audit and composition, verifies their capture/assembly chain, and checks all13 wire,9 intrinsic and19 composition controls before invoking the simulator.

All four original cases are retained: nominal_early, nominal_late, clock_stopped and vi_bias_off. The256-bit sequence,34.25ns capture, external8GHz clock, fixed sample phases, actual collector loads, safety/current checks, startup handling, tool/model hashes and waveform acceptance logic are unchanged. The exact source delta changes only artifact paths, the candidate model name and the independently measured C census12709→12712. The complete new17674R/12712C/484-device model is used; there is no wire pruning or reuse of old placement parasitics. Full-PHY and recovered-clock acceptance remain separate.
