# CDR interface redesign constraints from preserved measurements

These are diagnostics of the rejected `lowz4_bd10` candidate, not a passing PHY,
new simulation, new extraction, or layout qualification. Source measurements are
in [cdr-stage-voltage-20261113.json](evidence/cdr-stage-voltage-20261113.json).
Cloud run [43477642117](https://github.com/Melihakbulut221/nssoc/actions/runs/43477642117)
authenticated the preserved capture archives before reading them. No native
waveforms were transferred to the local workspace.

## Measured interface levels

Values below are medians of 258 bits sampled at 16 phases per UI. These sampled
ranges do not bound continuous-time overshoot, PVT variation, or device safety.

| Path | Sampler common mode | Existing XOR-input common mode | Required nominal shift to reproduce existing level |
| --- | ---: | ---: | ---: |
| A data | 2.088290 V | 1.832054 V | 0.256236 V |
| C data | 2.061536 V | 1.823578 V | 0.237958 V |
| D select 0 | 2.057453 V | 1.233883 V | 0.823570 V |
| D select 1 | 2.057453 V | 1.232723 V | 0.824730 V |

The data and select paths need different level shifts. A uniform buffer bypass or
identical follower on every path is therefore not justified by these measurements.
In particular, the select path needs about 0.824 V shift, whereas data paths need
about 0.24–0.26 V. These differences are target operating points, not assumed
transistor Vbe values. A proposed follower must demonstrate its actual loaded Vbe,
current, swing, and headroom with the pinned device models.

The existing select pair XD0281/XD0282 shares one emitter tail, as does
XD0299/XD0300. Replacing their common-emitter topology with two emitter followers
requires independent sink branches and a revised connectivity/census contract;
simply moving the collector/emitter pins while keeping the common tail is invalid.
The original select-tail MOS groups are XD0158–XD0161 and XD0180–XD0183. Data
buffers XD0273/XD0275 and XD0278/XD0280 have HBT tails XD0276 and XD0279.
These statements are from authenticated topology artifact 14060738835,
run 43472881982, model SHA256
`a855b1b460530fd6332c6f3631218810ac11aee64015149690f3869a86f1aef9`.

## Constraints for the next circuit candidate

- Preserve the full external sampler/XOR loads and frozen per-bit evaluation
  windows. No acceptance by shifting the oracle, dropping transition bits, or
  substituting a phase-average-only metric.
- The recorded sampler-to-XOR-output budget is 31–56 ps; the existing divider
  and buffer alone exceed it. Raising sampler current and resizing the old
  buffers were already tested and did not close this gate.
- Demonstrate sampler validity at the existing 0.3 UI/37.5 ps check. A faster
  level shifter alone cannot close the remaining sampler settling failures.
- Keep independent physical-device census and terminal checks. A topology change
  must bind every new or moved device to the checker; it cannot inherit a
  `devices_passed` result from the unchanged original circuit.
- Treat any rewired or resized extracted netlist as a schematic what-if. Even a
  successful electrical experiment still requires new layout, DRC, unblanked
  LVS, fresh parasitics, and re-running the same loaded gates.

No new circuit candidate is accepted by this report. The all-device pass of
`lowz4_bd10` does not override its sampler and XOR data failures.
