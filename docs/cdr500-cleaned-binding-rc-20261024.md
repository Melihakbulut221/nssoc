# Fresh intrinsic binding and wire RC from the cleaned PD500

Both stages consume only the immutable passed cleanup run40076590920 and verify its exact source/GDS, full physical/fault checks, native graph and actual-anchor census before native work. The six source corruption controls reject stale identity, stale GDS, wrong component census, a missing cleanup control, a removed MIM and a rounded gain MOS width.

The intrinsic stage binds500 devices/1446 terminals, retaining seven MIMs. It preserves native terminal orders, exact extracted-SPICE geometry and the existing one-binary-ULP JSON readback check. The measured MOS widths include four53.335µm devices; rounded or old gain widths are rejected explicitly. All217 small and four large ptaps are compared against the executed pinned PDK contact equation; invalid contact geometry and altered compact contact parameters are rejected. All original12 binding controls remain, including three MIM controls, with two added gain-width controls.

The wire-only RC stage restores the original cleaned output directory so original absolute anchor input hashes remain valid. It uses113 measured wire components and978 actual anchors (953 metal terminal/493 intrinsic body dispositions), preserves every native resistor edge/value, per-point capacitance and mutual attachment, and runs all13 original raw corruption controls. Seven intrinsic MIMs remain separate from wire-only extraction. No aliases are added to hide opens; no substrate spreading resistance or qualified RF model is claimed.

Workflow `cdr500-cleaned-binding-rc-cloud.yml` runs independent binding and RC jobs and publishes immutable `cdr500-cleaned-binding` / `cdr500-cleaned-rc` groups. No transient simulation is dispatched. Actual results must be inspected before composition and the unchanged full loaded early/late/fault electrical gates.
## Cloud checkpoint

The native source is `383748effef8f5132e4739f9f74b7557c431d6ef`. [Run 40077616252](https://github.com/Melihakbulut221/nssoc/actions/runs/40077616252) contains independent `native (binding)` and `native (rc)` jobs. The source-bound snapshot is in [the active checkpoint](evidence/cdr500-cleaned-binding-rc-checkpoint-20261024.json). At the recorded timestamp both jobs were queued and had executed no steps; there is no binding or RC acceptance yet.

The previous run 40077487147 was cancelled while queued, before native execution, solely to correct a stale textual scope and its protected method hash. Its exact source and cancellation disposition remain in the checkpoint. No transient job has been dispatched. Resume by checking the existing run and recording its immutable terminal releases; do not duplicate the native jobs.

## Terminal native results

Run 40077616252 completed successfully at the recorded native source. The queued checkpoint above is historical. The [binding receipt](evidence/cdr500-cleaned-binding-pass-20261024.json) verifies all 500 devices and 1,446 terminals, all 7 intrinsic MIMs, 14 corruption controls, and all 221 contacts against the executed pinned PDK equation. The 217 small contacts are 81.6666666667 ohm; the four large contacts are 11.6666666667 ohm.

The [fresh RC receipt](evidence/cdr500-cleaned-rc-pass-20261024.json) reports 24,535 native resistors and 15,671 capacitors across 113 wire components and 978 actual anchors. All 13 raw corruption controls were rejected. Native resistor topology and values, every point capacitance, mutual attachment, complete collapsed matrix, and component ownership checks passed. Substrate spreading and RF distribution remain unqualified.

Next, perform the original two-order capacitance precision validation and fresh intrinsic/wire composition before the unchanged 10-case, 34.25 ns, 256-bit loaded waveform gates. No loaded waveform acceptance is inferred from these native passes.
