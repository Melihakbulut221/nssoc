# Whole PLL845 raw RC audit — 2026-10-20

Capture review39352788481 passed on sourcec9d331e8ae3cf316c225e66bfa331161e1f05160 without repeating the native CAD extraction. It preserves3380 R,5104 C,235 conductor components,1604 physical points,1877 logical references and all26 uniquely identifiable MIM devices. Eight exported-capture corruption cases and52 one-nanometre dimension metadata cases were rejected.

The next cloud job audits the same immutable raw .ext, .res.ext, native log, baseline SPICE and distributed SPICE. The original strict auditor is adapted only for the independently proven845/2737/235/1604 census, exact original logical-label convention and retained819 body plus58 shared-diffusion identities. Numerical tolerances, raw R edge/value equality, per-point ground C, exact mutual-C attachment, full collapsed C matrix and every native retirement/distribution witness remain required.

All26 actual intrinsic MIMs must agree across the source extraction, resistor replacement and both SPICE views. The existing13 raw-wire and9 intrinsic-MIM corruptions must fail at their expected guards. Removing a non-bridge R deliberately preserves connectivity so that the value/topology comparison, rather than a different earlier gate, is tested. Cross-conductor faults use two actual independently owned anchors.

The physical source remains exactly845 devices; its census is not inferred from the RC export. The metal-only RC graph includes only26 MIMs as explicit intrinsic devices; the other819 device instances still require complete intrinsic-model composition. No full PHY, loaded loop, substrate/poly/diffusion/salicide resistance or qualified PEX acceptance is asserted.

## Native raw audit passed

[Run39353209044](https://github.com/Melihakbulut221/nssoc/actions/runs/39353209044) at source2add3d6d68a43e058e9de9d55fee7307e69de4d2 completed successfully. It retained3380 R and5104 C on all235 physical conductor components, with1604 physical points/1877 logical references and zero disconnected probes. Every raw R edge/value, per-point ground C, mutual-C attachment/value, full collapsed matrix and per-conductor ground-C total matched.

All26 MIMs matched in native source, replacement, baseline and distributed views. All13 raw-wire and9 intrinsic-MIM corruption cases were rejected at their intended gates. Source artifacts and methods stayed unchanged. The original failed capture remains archived; this successful audit refers to the same preserved native data and the independently passed exact-GDS dimension review.

[Immutable audit evidence](https://github.com/Melihakbulut221/nssoc/releases/tag/cloud-results-39353209044-1-pll845-whole-raw-audit) contains the complete433KB summary, raw extraction files and corruption diffs. The repository receipt pins those assets.

Next work is exact all845-device intrinsic model binding and composition with this audited wire graph, followed by actual loaded closed-loop simulation. The819 retained body/well terminal identities,58 shared-diffusion terminal identities and30 salicide access references still do not model distributed body/poly/diffusion/salicide resistance. This is a native wire-RC conservation pass, not qualified full PEX, full serial PHY, final mainchip timing or production acceptance.
