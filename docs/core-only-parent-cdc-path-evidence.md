# Routed parent mailbox CDC path evidence

This measurement is for the retained core-only product (PCIe and Ethernet excluded).
It is **not** asynchronous CDC signoff or full-chip timing closure.

## Authenticated inputs and scope

Run [44345861138](https://github.com/Melihakbulut221/nssoc/actions/runs/44345861138),
source 366aa664bca6801ebdafff018621931e29d0a5f7,
artifact 14444839373, SHA-256 59e75bf5c424de2272177cc4fdf2aee05ffab20957a3bf3374411eaf88b31811.
All 528 output hashes and protected repository source hashes were independently checked.
The measurement uses the existing routed parent ODB and its nominal SPEF.
The core remains a black box in this parent analysis.

There are 162 active payload positions (156 distinct snapshot source flops),
plus four two-flop synchronizer chains measured for both max and min delay.
Each of three library corners produced 170 actual endpoint reports.
No clock exceptions were added and the provisional 20 ns parent clock periods remain unchanged.

## Measurements

The following delay is destination data arrival minus source clock-pin arrival,
including source clock-to-Q and the combinational data path. It is not a qualified
asynchronous handshake margin. Detailed endpoint identities and all 510 measured
paths are preserved in the companion evidence JSON.

| Library corner | Maximum payload clock-to-D (ns) | Minimum provisional payload slack (ns) | Minimum synchronizer max/min slack (ns) |
| --- | ---: | ---: | ---: |
| slow | 0.966762543 | 17.887842178 | 0.290302843 |
| typ | 0.610756755 | 18.491912842 | 0.181521356 |
| fast | 0.398860634 | 18.865404129 | 0.118415229 |

## Remaining acceptance work

Positive slack under the provisional common phase does not prove an asynchronous
crossing safe. Derive and enforce the held-data-before-acknowledgement capture
budget from the mailbox protocol for all allowed clock relationships. Include
acknowledgement propagation, minimum capture latency, setup/hold, uncertainty,
reset release, and the rule that the host holds its request through the frame.
Qualify metastability resolution with suitable cell characterization and target
reliability; a two-flop structural pattern alone is insufficient.

Nominal RC and parent-only reports do not establish RC-min/max coverage, actual
core/parent hierarchical timing, qualified external I/O budgets, or production
approval. Existing parent electrical violations remain separate open work.
No timing exception, frequency change, or acceptance waiver is introduced here.
