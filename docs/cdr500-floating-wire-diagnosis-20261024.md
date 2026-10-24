# PD500 terminal-free metal diagnosis

The physical candidate from run 40073349301 passes the native 560-category DRC and unsimplified deep/flat 500-device LVS. Its fresh whole-parent wire-input run 40073945226 rejects a native metal net with no intrinsic terminals. Physical matching alone does not satisfy the strict electrical-conductor contract.

This isolated diagnostic restores the exact rejected GDS, LVS database and strict probe by published hashes. It reruns that unchanged probe and requires the same rejection, then independently enumerates every native net without intrinsic terminals. Exact metal/via polygons, label-free connectivity, root versus child ownership, original-root overlap and intersections with preserved v14 source-bypass strips are recorded. No geometry is changed and no original gate is weakened.

The initial commit contains the diagnostic and source rejection receipt. A successful diagnostic is evidence of ownership and connectivity only; it is not RC, electrical, PHY, timing or production acceptance. Repair selection requires inspecting its native results.

## Native result and bounded repair

[Diagnostic run40074893232](https://github.com/Melihakbulut221/nssoc/actions/runs/40074893232) completed successfully. The unchanged strict probe reproduced its exact rejection. All248 native nets and123 label-free wire components were enumerated. Of134 nets without intrinsic terminals,124 have no metal or public pins; the remaining10 are real floating metal components. Native clusters41–45 and142–146 have no intrinsic/public terminals and their complete metal/via geometry is exclusively root-owned, with no child contribution. Each contains one M2, one M3, two M4 polygons,16 Via1,16 Via2 and8 Via3 cuts. Of these40 cuts,16 Via1 lack lower M1 and2 Via3 lack upper M4.

The ten components contain20 of the32 preserved v14 M4 pieces. Their total metal area is285675500DBU² (285.6755µm²). Two include the earlier M3 detours; this is why the proposed repair removes whole measured components, not arbitrary old overlays. The other12 M4 pieces are outside this proven floating set and remain untouched.

Summary SHA256: `ed751395fdbe3049a69c6fe799a465528e49d7b7a825915cd902d5ec7855d11b`; parts manifest SHA256: `d74d553c32525eeb79e5cbdc759971d6e0be13aada11dd19f50566ca655bfa2f`. Exact polygons, graph edges, one-sided cuts and ownership are preserved in the receipt.

The new cleanup is still a candidate. It recomputes the entire diagnostic, requires exact agreement, checks native terminal/public-pin absence and root-exclusive/no-child ownership, and permits only the pinned layer area/via census. Seven corruption controls protect these conditions. All other drawings, hierarchy, texts, schematic and LEF remain unchanged across GDS serialization. Full560-category DRC, unsimplified500-device deep/flat LVS,12 physical fault controls, fresh native planes and the unchanged strict wire methods must pass before any fresh RC stage.
