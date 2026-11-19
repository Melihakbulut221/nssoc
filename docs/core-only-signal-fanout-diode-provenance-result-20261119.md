# Signal fanout diode provenance results — 2026-11-19

## Verified evidence

- Synthetic mutation run: https://github.com/Melihakbulut221/nssoc/actions/runs/44583396300 ; source 0282908c6eb305bc3891a9000c842d9ea68bbc69. All 7,205 negative controls passed. Tests cover missing/unexpected moves, wrong old/new nets, missing/duplicated/stale source or output instances, cumulative-inventory membership changes, false evidence flags and double rebinding. These tests do not constitute physical signoff.
- Real baseline/preparation evidence run: https://github.com/Melihakbulut221/nssoc/actions/runs/44583860864 ; source bc333d7410f157608a0a8b0685db4c381e2a980e. Completed successfully.
- Evidence artifact: 14559164087, SHA256 3139fb1fa0c3893e458a40750e08b3ab2fab8fd868ab9ad8f644adf0ed539538. Downloaded in memory and both output hashes verified.
- rebound-inventory.json: a047d8a95d583891ae1310dc16f3ad143917d10e17edb8a667f249370d694335.
- moved-diodes.json: 1f0cbf5694d00150aa19a1a8c87bbc459687fd867faf332d8665db8493a6ef68.

All 720 moved diodes have their original master and signal connection verified against the actual prior routed netlist. Of these, 698 belong to the 1,410-entry cumulative added-diode inventory; the remaining 22 original diodes are explicitly enumerated in rebind_signal_fanout_antenna_inventory.py and also require source-netlist proof. The cumulative inventory retains exactly 1,410 entries, with exactly 698 changed. Input evidence remains unchanged. The old netlist is rejected as a purported new export.

The source ODB is 12a48d839091ba5c4fea76a193fea75fcc5f2f38621b1df809cb3df5bd51e458. The prepared 413-buffer candidate ODB is 2338707a927b80c95dbb087a332ea42f32e9c514c737bc25ae344d4e4da7a40c. Both are bound by immutable artifact digests in the evidence script.

## Required next gates

Route run 44573258297 remains the physical candidate. Do not infer route success from diode provenance success. Require its native route/antenna metrics, independent geometry, unchanged original cells, fixed-route restoration, 2,113 clock-route preservation and NDR preservation before fresh extraction. Check all 720 moved connections against the newly exported routed netlist, as well as the rebound 1,410-entry inventory. Then perform new nominal RC extraction and all-corner STA at the unchanged 50 MHz / 20 ns and 5% derating.

Qualified RC extremes, full production DRC/LVS, SRAM characterization, external I/O/package/PCB timing and manufacturer approval remain separate unclosed gates. This evidence is not production acceptance. PCIe and Ethernet remain excluded from the approved production scope.
