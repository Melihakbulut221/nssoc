# CDR v30 fresh native RC and next electrical gates

Fresh extraction [39707446970](https://github.com/Melihakbulut221/nssoc/actions/runs/39707446970) completed on the repaired v30 physical parent. All four stages passed: actual native planes, whole conductor graph, compact-model terminal binding and fresh wire-only RC. The native graph retains 476 devices, 1382 intrinsic terminals, 111 independent wire components and 938 physical extraction points.

MIM-aware capture [39708084548](https://github.com/Melihakbulut221/nssoc/actions/runs/39708084548) independently measured **17918 R / 12850 C**, with all seven native MIM devices and five capture corruption controls. These are new geometry-dependent counts, not the v29 counts of 17906 R / 12834 C.

The new validation workflow preserves the raw R/C conservation audit, 13 original wire corruption controls, nine MIM-specific controls and 19 composition controls. It must verify each MIM device and emit exactly one intrinsic model per physical capacitor. The complete immutable summaries and manifest pins are committed with their exact source run identities.

This is not qualified foundry PEX, closed-loop CDR, serial PHY acceptance or mainchip timing closure. After audit/composition pass, run the unchanged full-duration loaded wave tests and device operating-envelope checks, including early/late nominal cases and original negative controls.
