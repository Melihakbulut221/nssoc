# Lossless storage continuation qualification

The actual PLL process is preserved at 892.691247612412 ns. The complete original 5106-column trace exceeds the current runner's measured disk budget with checkpoint reserves. No source waveform, sample, column, solver setting, analysis duration or electrical gate is to be removed.

This new storage primitive keeps the immutable prior raw bytes in their verified source archive. A new sparse working file retains the complete raw header and a tail spanning the existing native file offset, while representing the old middle interval as a hole. Its logical reader reconstructs that interval from the complete hash-verified prior raw stream and verifies the original payload byte for byte. The archive remains authoritative; the sparse file alone is explicitly not a waveform.

The qualification workflow runs only owned binary fixtures on ext4 and compressed Btrfs. It checks exact full-byte reconstruction, permitted header backpatching, partial append tails, original payload hashes, physical allocation and 16 corruptions. Writing into the archived-only hole is a hard failure. Concurrent mutation, changed header boundary, corrupted source, changed retained payload, shifted map, truncated data and source duplication must also fail.

This is a storage component, not permission to activate the saved PLL. Before adopting it:
1. Bind the immutable source descriptor, complete ordered archive digest and exact raw member/payload hashes; verify all archive parts before any native activation.
2. Prove real CRIU/ngspice continuation across hosts preserves the actual file offset, runtime, existing solver state and byte stream; reject unexpected accesses or writes into the archived-only interval.
3. Qualify the original full-column waveform and acquisition readers on the reconstructed stream without altered equations, sample count, duration, voltage/current gates or tolerances.
4. Preserve every immutable source extent and current header/tail in the new capsule, and prove restore plus corruption rejection on the published representation.
5. Only then continue the exact845-device process with original12GiB native and4GiB backing reserves and complete1us analysis.

Existing production continuation controllers are unchanged. Source and test results do not imply full capture, device safety, qualified PEX, closed-loop PLL/CDR, serial Gen3 x4 PHY or final chip timing acceptance.
