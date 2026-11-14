# Replay CRC select candidate, 2026-11-14

The goal is to reduce the replay buffer's input-to-register setup path while preserving exact packet behavior. In the existing source, `in_sop_i` selects the CRC input state before the bytewise XOR network. The upper 24-bit residue comparison follows that network. This puts the SOP signal ahead of both operations.

The optional `SOC_PCIE_REPLAY_CRC_SELECT` implementation computes the starting CRC from `32'hffffffff` and the continuing CRC from `input_crc` independently. It selects their 32-bit results at the end. The upper-residue predicate is likewise computed independently and then selected. No register, cycle, handshake, polynomial, reset condition, residue constant or update enable changes. The macro defaults off and is still an experiment.

For any state S, byte B and selection P, `CRC(P ? INIT : S, B)` equals `P ? CRC(INIT, B) : CRC(S, B)`. Applying the same selection to the comparison against the unchanged upper residue preserves `crc_upper_match`. Formal verification nevertheless covers the complete actual replay module, including its mapped memories, to catch integration mistakes.

Run 43634922779 proved the original and candidate equivalent for depth/maximum-byte combinations 2/22 and 4/38, each in default and physical-option builds. The latter enable EOP caching, write predecode, read ahead, in-bank access and reset copies. Four deliberately corrupted candidates flip bit zero of `next_crc`; every one failed semantic equivalence as expected. Pinned OSS CAD Suite is 2026-08-04. The formal flow uses async2sync and induction; it does not establish analog asynchronous-reset timing or manufacturing qualification.

The precise source and eight proof outcomes are in `docs/evidence/replay-crc-select-formal-20261114.json`. Source is on `codex/replay-crc-select`, commit 90b31c2acdbd1170b4b4aa0e74f26e9bcaff789e. Candidate RTL SHA256 is a5891101ff12672cf6da0fa5da09c638e44fc7a5d4fc94b445535e7b00834d45.

Physical comparison uses an equal-area baseline that already includes the EOP cache. Only CRC selection differs. All original clock, I/O, uncertainty, derate and library constraints remain. Reports include all constrained input/output/register paths. Setup and hold optimization margins are stricter than zero-slack acceptance; no acceptance limit is relaxed. Additional logic may increase area, fanout or routing pressure, and synthesis could undo the intended restructuring. These effects must be measured before adoption.

This candidate is not integrated into the main chip. It has no independent routed, extracted, full-chip boot, LVS, analog PHY or production approval. Its insertion changes source line numbers; future mapping checks must derive the real sequential-cell origin from lowered RTL instead of accepting an old line-number binding. The currently running EOP-only chip remains untouched.
