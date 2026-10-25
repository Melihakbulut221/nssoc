# V3 measured headroom and explicit external-boundary experiments

Native diagnosis39087834710 reproduced the complete original failed early/late waves:113475rows898columns34.25ns, all sampler counts and all122HBT minimum VCE values. Fourteen failed identities match exactly. The full receipts pin both original capture hashes and every derived output.

In the early capture, select-input common mode is about1.342V and XOR select-input common mode about1.169V. Select-tail emitter means are0.191/0.197V with collector means about0.406V; XOR tail collector means about0.342V and emitters0.144-0.153V. Sampler clock common mode stays about1.290V; sampler tail collectors about0.505V and emitters0.076-0.102V. The supply overlay reduces some return rises but does not provide adequate active VCE.

Three declared boundary experiments run both original early/late cases: clock145 changes only external clock common mode from1.29 to1.45V; select500 changes only ibs0/ibs1 reference currents from1mA to0.5mA; clock145_select500 combines them. They use the identical actual394device9979R7761C layout model. Data bits, phases, clock differential amplitude, edge times, loads,34.25ns duration,.3125ps timestep and all voltage/current/margin/timing gates remain unchanged. Clock sources still start at zero. Twelve positive clock checks and four deliberate clock corruptions validate the transformation. A source-delta audit proves the controller differs only at declared boundary/control/output edits.

These are operating-point diagnostics, not original-interface acceptance, new qualified layout or physical bias-generator integration. No native device or extracted wire is resized/scaled. Any apparent improvement requires a physically realizable clock/bias interface, fresh native verification of that interface and complete PVT/convergence/full-loop validation; failing original v3 evidence remains authoritative. No profile is adopted automatically.

## Preflight rejection retained

Run39088317707 failed before any native waveform: the boundary parser did not handle the original multiline SPICE PWL continuation markers. The correction removes only start-of-line continuation plus markers, preserves numeric signs/exponents and writes multiline sources. A new shared preflight executes all clock controls before launching the native matrix. No electrical threshold or stimulus time changed; the rejected run and representative reports/log digest are retained.
