# Actual TX8088 physical integration

Run39578033552 passed full560-category DRC with zero markers, unsimplified deep/flat LVS for8088 devices, exact165 external ports and all seven physical/reference corruption controls. Original failed runs remain available. No geometry, spacing, native comparison or port identity was waived.

Fresh metal/via graph extraction uses the actual parent GDS3b1a16d8e96f0326b430c7c9214e61e723dcb0eee07e70266f30bc8a9ba673e7. Its method is an exact documented adaptation of the8074 graph extractor, preserving no-label-union, one physical component per native metal net, all geometry and complete terminal coverage. The declared census is593 HBT,5376 MOS,1613 body contacts,504rppd and2rsil,28620 terminals. Four child net joins plus shared substrate imply703 metal components and768 electrical nets; these are assertions to validate, not measured results yet.

Full fresh parent RC, terminal references, composition and loaded electrical simulation remain mandatory. This includes actualmp/mn, AVSS and SUB routes. Clock modulation and supply/bias boundaries remain open. Neither full serial Gen3x4 PHY nor mainchip timing is accepted.

PLL storage scan39571416471 failed after hashing the actual raw member: the frozen header reader rejected a vector name/type. A separate small cloud job inspects the saved prefix and reproduces this rejection before any expensive repeat. It cannot establish original archive completeness or acquisition performance.
