# Selector4 parent: fresh MIM-aware native capture

The 484-device parent passed native DRC and strict deep/flat LVS in run
39394475994. This workflow continues only after all four extraction jobs in
39396626134 succeed at exact source 8789725da417537488b307aa0f76c08624822ac2.
That extraction selects the verified parent root explicitly; unused native
PCell library roots are not traversed as another circuit.

The capture controller changes only the v18 source namespaces. It requires
fresh v19 GDS, wire graph, terminal anchors and compact-device binding. It
rebinds eleven actual bottom-plate contacts outside their intrinsic masks,
preserves all actual conductor geometry, retains 946 points and 111 physical
components, and checks native MIM dimensions and plate ownership. The five
original missing-device, wrong-width, swapped-plates, wrong-model and wire-short
controls remain. Upstream 19 plane, 12 binding and 13 wire-RC controls remain.

All four prerequisite reports and archive manifests are hash-bound and their
source lineage is cross-checked. Waiting for that specific live prerequisite
does not restart it. A rejected prerequisite prevents capture. Outputs and
failures are published in cloud release artifacts.

This is capture preparation, not an electrical pass or qualified PEX.
Strict raw-RC auditing, exactly-once intrinsic MIM composition and the unchanged
34.25 ns / 256-bit early, late, stopped-clock and bias-off full-parent simulations
must follow. The new selector dimensions require those fresh simulations;
prior v18 waveforms do not validate v19. Current density, device voltage,
data differential amplitude and original timing gates are not relaxed.
