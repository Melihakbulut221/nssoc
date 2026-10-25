# Fresh CDR v2 model and extraction sequence

Native parent run 39079610383 passed full configured DRC and both LVS modes. Native plane run 39080139959 passed 158 interface points, 51 nets and 19 faults. Wire-input run 39080362471 found 394 devices, 1134 intrinsic terminals, 111 conductor components and 776 distinct metal probe points on this new layout. Physical geometry and all source checksums were preserved.

Two independent cloud stages now use the exact new geometry: native device binding and a wire-only extraction/audit baseline. The latter is deliberately diagnostic and cannot serve as the accepted electrical RC model: it excludes intrinsic MIM masks. The next mandatory stage restores actual MIM/Vmim masks, verifies all eleven MIM identities and moved bottom-plate probes, uses the explicit-model technology semantics, and repeats raw R/C conservation with all 22 corruption controls before composition. No v1 native IDs or wire values are used for the v2 model. The v1 whole-wire failures remain unchanged.

This sequence is not closed-loop or full serial PHY acceptance. The accepted model must still run the unchanged early/late loaded transient cases, all device limits and fault cases, then real PLL/CDR integration and complete serial-interface validation.
