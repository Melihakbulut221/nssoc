# Load-isolation global-route result and hold diagnosis

This is diagnostic evidence, not signoff. PCIe and Ethernet remain excluded from the approved reduced scope. Clock period remains 20 ns with 5% timing derating. Package, PCB and attached devices are not selected; external I/O signoff remains open.

## Authenticated evidence

Run: https://github.com/Melihakbulut221/nssoc/actions/runs/44426862303
Head: `5315afedc0c70d7851c068873285241899dcd0a9`
Artifact: `14484968617`, SHA256 `f27db3ae32c439d4d4b0cfdc8728e226c52430ff27f4aed6f89f28570235d33f`.
All 106 manifest output hashes were verified before reading the reports. The green workflow means measurement completed, not timing closure.

| Estimated corner | Setup violations | Hold violations | Worst hold slack ns |
|---|---:|---:|---:|
| slow | 0 | 0 | 0.369061 |
| typical | 0 | 38 | -0.234191 |
| fast | 0 | 205 | -0.604620 |

Slow estimated setup slack is only +0.0661107 ns. Slow slew/fanout/cap violation counts are 55/207/4. Actual routed parasitics have not been extracted for this candidate.

## Concrete hold path

In `routing/4-nssoc-coreonlyroutedfast/min.rpt`, the worst path starts at `nssoc_sta_i_72253` and ends at SRAM bank `u_ram.g_ram_2048x64_ecc.u_b1/A_ADDR[0]`. It passes through `nssoc_sta_i_8999`, `nssoc_sta_i_9002`, `hold15685`, and `wire2034`; neither new load-isolation buffer is in this data path.

Data arrival is 2.950000 ns. Capture clock arrival is 2.261927 ns, clock uncertainty 0.250000 ns, and library hold time 1.042693 ns, giving required time 3.554620 ns and slack -0.604620 ns. Capture SRAM clock slew is 0.991138 ns. The adjacent bank b0 address path also fails at -0.597286 ns.

The preparation code clears every signal wire and guide before global routing, including clock nets. Accordingly this is a whole-route perturbation, not an experiment changing only the two data branches. Existing cells and logical clock connections are preserved, but that does not preserve routed clock RC. A causal claim that the two added buffers alone caused all 205 violations is not justified.

## Next engineering decision

Do not promote this candidate as a timing fix or add blanket hold delays based on these estimates. Compare clock-route topology and clock pin slew against the authenticated source route, and evaluate a targeted routing ECO that preserves unaffected routes, or measure detailed-route RC before selecting hold edits. Any routing preservation must be explicitly audited; do not assume fixed placement preserves wires. Recheck every timing corner, antenna, router DRC, functional connectivity and supply contact after a new candidate.

The separate third antenna repair run 44427090834 (head 8a27e631912305e5a184c0268279374283705dc9) was still in progress when this note was prepared. It is not the two-buffer candidate. Await its exact result rather than restarting it.
