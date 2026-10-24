# PD500 terminal-free metal diagnosis

The physical candidate from run 40073349301 passes the native 560-category DRC and unsimplified deep/flat 500-device LVS. Its fresh whole-parent wire-input run 40073945226 rejects a native metal net with no intrinsic terminals. Physical matching alone does not satisfy the strict electrical-conductor contract.

This isolated diagnostic restores the exact rejected GDS, LVS database and strict probe by published hashes. It reruns that unchanged probe and requires the same rejection, then independently enumerates every native net without intrinsic terminals. Exact metal/via polygons, label-free connectivity, root versus child ownership, original-root overlap and intersections with preserved v14 source-bypass strips are recorded. No geometry is changed and no original gate is weakened.

The initial commit contains the diagnostic and source rejection receipt. A successful diagnostic is evidence of ownership and connectivity only; it is not RC, electrical, PHY, timing or production acceptance. Repair selection requires inspecting its native results.

## Native result and bounded repair

[Diagnostic run40074893232](https://github.com/Melihakbulut221/nssoc/actions/runs/40074893232) completed successfully. The unchanged strict probe reproduced its exact rejection. All248 native nets and123 label-free wire components were enumerated. Of134 nets without intrinsic terminals,124 have no metal or public pins; the remaining10 are real floating metal components. Native clusters41–45 and142–146 have no intrinsic/public terminals and their complete metal/via geometry is exclusively root-owned, with no child contribution. Each contains one M2, one M3, two M4 polygons,16 Via1,16 Via2 and8 Via3 cuts. Of these40 cuts,16 Via1 lack lower M1 and2 Via3 lack upper M4.

The ten components contain20 of the32 preserved v14 M4 pieces. Their total metal area is285675500DBU² (285.6755µm²). Two include the earlier M3 detours; this is why the proposed repair removes whole measured components, not arbitrary old overlays. The other12 M4 pieces are outside this proven floating set and remain untouched.

Summary SHA256: `ed751395fdbe3049a69c6fe799a465528e49d7b7a825915cd902d5ec7855d11b`; parts manifest SHA256: `d74d553c32525eeb79e5cbdc759971d6e0be13aada11dd19f50566ca655bfa2f`. Exact polygons, graph edges, one-sided cuts and ownership are preserved in the receipt.

The bounded cleanup recomputes the entire diagnostic, requires exact agreement, checks native terminal/public-pin absence and root-exclusive/no-child ownership, and permits only the pinned layer area/via census. Seven corruption controls protect these conditions. All other drawings, hierarchy, texts, schematic and LEF remain unchanged across GDS serialization.

## Verified cleanup and next checkpoint

[Cleanup run40076590920](https://github.com/Melihakbulut221/nssoc/actions/runs/40076590920), source `2627eb651ebff31b96abac985d19e1bc9b76d6a8`, completed successfully:

- Full560-category DRC: zero violations.
- Unsimplified deep and flat LVS: all500 devices match; no extraction diagnostics.
- All12 physical fault controls and all7 cleanup corruption controls rejected.
- Fresh160 native planes across51 logical nets;19 plane corruption controls rejected.
- All16 placements and nine native child drawings preserved; five child-geometry controls rejected.
- The four original strict wire methods are byte-identical to their previously rejected versions. They now pass, with113 complete metal/via components,238 native nets,500 uniquely located devices and1446 native terminals. No terminal-free metal component remains.
- All978 logical/physical anchors are bound, with953 metal-terminal and493 intrinsic-body dispositions; no substrate resistance is claimed.

The cleaned GDS SHA256 is `e6ab61471595cd3635c8e2ef3922a09d6b128db0a5338fd6106f3a8e4aefc2f3`. The strict probe SHA256 remains `d0ff17e291afae70873724369a89304dfd845ace8a5b9ed438e478c05b9a3790`.

The immutable publication group is `cdr500-floating-wire-cleanup`, run40076590920. Summary asset671670485 has SHA256 `817bdcb956662d9f3384ddcd72e237a4b9afb77e2cae3703eb4c063b0def90a2`; parts manifest671670572 has SHA256 `ee011be772093b73ceaa45c735aaa2591eb9d321b4f35260c795c1df290839c6`. The complete receipt is `docs/evidence/cdr500-floating-wire-cleanup-pass-20261024.json`.

The next stage must restore this exact cleaned output: `parent/layout/`, `parent/physical/lvs_flat/`, `native-planes.json` and `wire/`. The old rejected source remains under `source/` solely as evidence. Fresh whole-parent RC and original full loaded early/late/fault waveforms remain required. This result does not establish electrical safety, recovered-clock behavior, complete PCIe PHY, main-chip integration, final timing, qualified PEX or production acceptance. No fresh RC or electrical run was launched by this bounded cleanup.
