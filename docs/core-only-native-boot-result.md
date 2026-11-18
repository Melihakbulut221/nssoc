# Native mapped core boot result

[Run44239816779](https://github.com/Melihakbulut221/nssoc/actions/runs/44239816779) completed the real mapped core boot with IHP's native standard-cell and SRAM models. Original mapped netlist SHA2561c0ea43bd478c7cf628ecd8af8fc53b9e31e557d963324bc72cd5b8608ca679a, mapping run44238569057. Source31cb1846a8cf0eb683344e24c27a25438c22a75c uses previously qualified system-only MBIST observer changes. No RAM/ROM preload is used.

The native log records28firmware checks, zero fail mask/exit code,2263211cycles, watchdog1/0/0, zero flash protocol violations and UART framing errors. System MBIST is busy for1310690observed cycles and completes at1310723, before CPU firmware succeeds. Native simulation took7599.16seconds. This is a completed mapped-functional-boot gate.

Independent verification covers the artifact digest,9archived output hashes, all mapping-derived source hashes against the original mapping manifest, three bench/flash/monitor source hashes, and actual pass/failure/MBIST/serial records. Two .vvp binaries were excluded from upload and have not been independently inspected. Full source/input bindings and unchanged-source result are recorded in docs/evidence/core-only-native-boot-20261118.json; the native log is preserved alongside it.

Scope: functional Icarus14/-DFUNCTIONAL simulation, no SDF. Vendor unsupported-ifnone timing warnings preclude treating this as timing simulation. It tests the original synthesized core, not the subsequently repaired physical netlists. MBIST completion is not complete memory fault coverage, transistor SRAM characterization, padframe/DFT completion, or production approval. Post-ECO equivalence and final full-chip qualification remain required. PCIe/Ethernet are excluded by the approved release scope.
