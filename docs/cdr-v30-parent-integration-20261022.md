# v30 sampler replacement in the actual 476-device parent

The leaf run39703416443/source17dffb1c636237b5dbf154ca393338fd4a9096d7 passed the native560-category DRC with zero markers, unsimplified54-device deep and flat LVS, LEF checks and all20 injected physical/reference faults. Its native GDS SHA256 is f1618ddc27ef0de9939796cee2f1830f93b6f265c036de4e596bf1d838428d30. This is physical leaf evidence, not electrical acceptance.

The next native cloud job restores the actual passed v29 parent from run39692037466 and the new v30 leaf from run39703416443. It replaces all four serialized pd_child_sampler instances, changing exactly16 reference resistor lengths across the four samplers. It preserves all original parent polygons, including the previously proven eight M4 notch fills, all transforms, all other native child drawings, all pin locations and the LEF. It does not reapply the v29 notch-repair procedure to a changed geometry.

Independent serialized-region checks reject removed parent geometry, added parent metal and removed instances. The unchanged child-geometry verifier checks all16 placements and eight leaf types with its three corruption tests. The unchanged native parent DRC/LVS gates must pass before any fresh extraction is accepted. If new child edges expose a parent DRC violation, retain that actual failure and diagnose the geometry before repair.

Fresh wire/MIM extraction, intrinsic device binding, composition and the complete original early/late/fault waveforms remain required. Old v29 RC cannot qualify v30. The whole serial PHY, recovered clock, mainchip setup/hold closure and production approval remain open.
