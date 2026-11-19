# 21-buffer neighbor route result — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44562378599 completed successfully at source `d800be2ea61e39adef89e58c075591d77f71773e`.
Artifact `14549769828`, SHA-256 `f11b5b5f3affd565311424f68028f32613ecc68c35d313bf6f914e5b3d1a3f39`; all 47 output file hashes were independently checked.
Final ODB: `12a48d839091ba5c4fea76a193fea75fcc5f2f38621b1df809cb3df5bd51e458`.

The 35-net selection includes the eight source nets, 21 buffer outputs and six measured contacting neighbors. It starts from the original prepared candidate, not the rejected routed metal.

- Router DRC: zero at iteration 3.
- Antenna: zero violating nets and pins.
- Independent native wire/via/LEF geometry: zero contacting net pairs, disconnected nets, unwired multi-terminal nets, and terminals without geometry. The route-removal negative control detected the induced disconnection.
- Identity: 106,693 instances and 103,117 nets; exact geometry/masters/terminals/special wires/ports preserved through routing.
- 103,080 unaffected nonpower DEF records and 2,113 clock nets preserved; 102,964 encoded fixed paths restored to ROUTED.
- Ten DRT-0349 warnings remain recorded; zero flow errors.

This resolves the prior candidate's 22 visible contact pairs. It is not transistor LVS or foundry DRC and does not establish final timing. Fresh DEF/netlist export, nominal RC and three-corner STA are the next gate. The 44 moved diode terminals must match the explicit mapping and all 1,410 cumulative added diode exports must match. Clock period/derating remain unchanged. Qualified RC corners, macro characterization, full-chip integration and production approval remain separate open requirements.
