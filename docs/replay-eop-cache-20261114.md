# Replay end-of-packet cache — 14 November 2026

## Problem and implementation

Fresh main-chip post-CTS timing on the write-predecode candidate found a slow-corner path from `retry.read_pos[1]` to `retry.replay_read_onehot[33]`, with -3.164052 ns slack at the original 4 ns PCIe clock. [Exact mapped-cell readback](https://github.com/Melihakbulut221/nssoc/actions/runs/43629195905) establishes both endpoint identities. The comparison with `send_last` sits ahead of the high-fanout cursor control. This is a control path, not a write into the packet byte store.

The experimental `SOC_PCIE_REPLAY_EOP_CACHE` switch registers `read_pos == send_last` alongside the updates of those two operands. It adds no stream pipeline stage or transfer latency:

- Reset sets both original operands to zero, so the cached comparison resets to one.
- Link loss holds the operands and the cached result.
- A send start sets the cursor to zero and the last position to `length - 1`; the cached result becomes `length == 1`.
- An accepted non-last byte increments the cursor with exactly the original BW-bit wraparound. The cached result compares that next cursor with `send_last`.
- Otherwise the result holds. A send start and an accepted current byte cannot coincide because the former requires `!sending` and the latter requires `sending`.

The original combinational implementation remains the default. The candidate RTL SHA-256 is `e478d785013174a7a7ce63b6fcbd8aa609736e65e292748eb8c0311e453f69e8`. It is on the experiment branches, not yet adopted into `timing/combined`.

## Functional evidence

[Full RTL equivalence](https://github.com/Melihakbulut221/nssoc/actions/runs/43629312391) passed for 2×22-byte and 4×38-byte stores. Both sides enable the existing write predecode, ahead read, in-bank read and reset-copy options; only the EOP cache differs. The proof maps the actual memory and flattens the real module without memory blackboxes. It uses `async2sync` and induction, so it does not qualify analog reset behavior or every possible parameterization.

[Randomized comparisons](https://github.com/Melihakbulut221/nssoc/actions/runs/43629411055) passed twelve 300,000-cycle runs: six with only the cache enabled, six with all the physical options. Existing output, storage and coverage checks remain. A compiled mutation that increments the comparison cursor by two instead of one produces a real mismatch in all twelve corresponding runs. Simulator errors propagate as failures. The original source is restored after each mutation.

See [functional receipt](evidence/replay-eop-cache-functional-20261114.json) and [simulation and physical receipts](evidence/replay-eop-cache-qualification-20261114.json).

## Physical comparison and tradeoffs

[Paired placement](https://github.com/Melihakbulut221/nssoc/actions/runs/43629920068) uses identical 600×600 µm cores, IHP library files, estimated layer RC, a 4 ns ideal clock and 5% derating. The baseline already includes write predecode. Source provenance verifies that the cached comparison survives synthesis as one actual flip-flop; an internal signal name is not treated as proof of hardware retention. No `keep` attribute was added to force the measured result.

| Measurement | Baseline | EOP cache |
|---|---:|---:|
| Mapped cell count | 5,895 | 5,870 |
| Slow setup after electrical repair | -2.881974 ns | -2.486284 ns |
| Typical setup after electrical repair | -0.367894 ns | -0.142452 ns |
| Fast hold after electrical repair | -0.048063 ns | -0.064218 ns |

The setup improvement is accompanied by a hold regression. [Actual netlist aliases](https://github.com/Melihakbulut221/nssoc/actions/runs/43630223798) show that the new worst slow path starts at `replay_read_onehot[33]` and ends at `read_replay_bank[0].ahead[5]`. Its large select-network loads and small buffer stages dominate the delay. Removing the comparison does not solve that distribution problem.

[Native setup/hold repair](https://github.com/Melihakbulut221/nssoc/actions/runs/43630824750) subsequently completed both candidates with 100 setup iterations and 1,000 hold iterations. The original 20% hold-buffer insertion budget stopped an earlier trial; the completed comparison allows 40% on both candidates without changing clock, slack or input/output constraints. It does not enable `-allow_setup_violations`.

| Measurement after hold repair and legalization | Baseline | EOP cache |
|---|---:|---:|
| Slow setup | -1.305586 ns | -1.123962 ns |
| Fast hold | -0.009951 ns | -0.017249 ns |
| Inserted hold buffers | 1,291 | 1,299 |

Both still fail timing. The native setup log reaches its 100-iteration search limit while making changes. [A 600-iteration block comparison](https://github.com/Melihakbulut221/nssoc/actions/runs/43631139914) is running; this does not change the full-chip optimization budget. The [complete measurement receipt](evidence/eop-cache-setup100-hold40-20261114.json) preserves all 48 reports' values and hashes.

## Required full-chip gates

[Fresh chip mapping](https://github.com/Melihakbulut221/nssoc/actions/runs/43630345267) is running with the same system/Ethernet SRAM configuration and physical RTL options plus the cache. Simulation and synthesis both validate and forward the new switch. Its checker requires the exact new RTL, the cached sequential cell, all 26 write-predecode bits and all 20 SRAM macros.

These isolated results do not qualify CTS, routed parasitics, full-chip input/output timing, DRC, LVS or antenna behavior. A new netlist requires its own gate boot, placement/CTS, routing, extraction and verification. The older chip's boot and LVS results cannot be transferred. Full serial Gen3 x4 PHY and production approval remain separate incomplete requirements. Native layout, netlist and simulator files remain in the cloud; receipts bind their exact sources and hashes.
