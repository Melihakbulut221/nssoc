# Actual scoped-router timeout and required checkpointing correction

Original run41270471645/source2b8931b9c8988fc5dbf497a7b561db579e39f64c is terminal failure. The supervised native router ran14400.811145697seconds, returned-15, and recorded supervision_failure=elapsed_limit. This is an observed four-hour cutoff, not a memory-failure diagnosis. Full logs,677 encoded JSON records and complete native publication metadata are preserved in de4e92bc723d6885c3c800aa5c9676f7495f9a4a, `docs/evidence/mainchip-828-terminal-41270471645`. Native release430345631 remains intact.

Cloud readout41290408993/sourcec74b2fb8311315a09f16f899c2cd540fcb0731cb authenticated the complete archived native members and extracted the actual full router stdout and exact Tcl without rerunning CAD. Full19-file proof e19b8a246accee5125c14291b6effd46b94249ad, `docs/evidence/mainchip-828-readout-41290408993`.

The last completed optimization iteration was26, with129 native router DRC violations. Iteration27 reached40% when the supervisor cut the process. This is an intermediate router count, not final chip DRC or STA acceptance.

The exact route Tcl requested64 iterations and had DRT_SAVE_SNAPSHOTS=0. Its route-partial and routed-fixed DEF/ODB writes execute only after detailed_route returns. A SIGTERM at the supervision limit bypassed those Tcl writes. The archived native index contains the known stale-wire-cleared seed and restoration views, but no route-partial/routed-fixed ODB carrying optimized progress. The restored candidate.odb matches the guide-overlay/insertion-connected seed identity; it must not be described as the26-iteration routed checkpoint.

The failure restoration independently preserved all1691 original clock/fixed DEF records and attached geometry. That scope does not prove final signal routing, antenna, connectivity, RC or timing.

Required next implementation: an explicit bounded routing stage that returns and publishes its native database before the supervision limit, followed by authenticated continuation from that database. Keep all828 routing owners,1351 diode placements and1691 protected records; do not silently change final physical/electrical gates. Separately validate routing iteration policy/source controls and actual checkpoint write/readback before another long native dispatch. Do not simply repeat the64-iteration run with the same lost-progress behavior.

Final mainchip DRC, antenna/connectivity, extracted RC and three-corner setup/hold remain open. This is still a packet-interface SoC; serial PHY ownership/integration is separate.

OpenROAD documents the existing `-droute_end_iter` limit and the `DRT snapshot`/`-snapshot_dir` mechanism in its [official detailed routing documentation](https://openroad.readthedocs.io/en/latest/main/src/drt/README.html). This does not prove checkpoint behavior for the pinned engine. Qualify actual native write/readback and continuation before relying on either mechanism.
