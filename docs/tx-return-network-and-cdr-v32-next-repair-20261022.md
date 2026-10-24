# Native evidence for the next physical repair

CDR diagnosis [39753512279](https://github.com/Melihakbulut221/nssoc/actions/runs/39753512279) reproduced all 120 HBT checks and all four original sampler checks in both complete v32 captures. This confirms passing nominal device gates and failing electrical timing; diagnostic success is not PHY acceptance.

At the original capture edge, A has adequate internal slave-input margin, but its output remains too slow. B depends on early/late case: early B still has 129 wrong-sign slave inputs at that edge; late B does not. C/D have weak master inputs; D still has 64 wrong-sign master/slave inputs at the edge in both cases. Slave track-current crossings occur about 12.6–14.3 ps after the expected edge. The real followers remain conducting but their minimum collector current falls to about 0.145–0.199 mA. These are observations, not proof of a single root cause or new acceptance thresholds.

The v32 stronger slave bleeds did not solve settling and worsened C/D. The next sampler candidate must address clock selection and loaded regeneration while preserving original external clock, data phase, output load and deadline; it must also preserve the headroom improvement.

## Transmitter return network

The original full-wave headroom diagnosis measured about 0.25–0.28 V at the output HBT emitter. The current generator routes the output AVSS handoff with a 6 um path; the separate 128 um trunks and 32 um feed improvement serves the core driver network. This motivates measuring the actual output return path, but does not yet prove which resistance dominates.

The cloud return-network diagnostic restores the exact immutable 8088-device composition and 140222R/99906C model. It derives output tail/reference/data roles from native conductor identity, then measures passive unit-current resistance from the actual output tail and all 62 mux-tail emitter terminals to the unchanged AVSS port. Original native resistors and parallel paths are retained. Analytic series, parallel, bridge and dangling-branch controls plus malformed/disconnected-network rejection exercise the solver; KCL and energy identities are checked on every solve.

This is a DC wire-network diagnostic. Capacitors are open only in that analysis; the original model and transient remain unchanged. It cannot establish transient closure, predict the whole operating drop from collector current alone, or qualify device-access/substrate/RF extraction. Dominant edges must guide a physical geometry change followed by fresh DRC/LVS/RC and original complete loaded tests.
