# Actual pin-metal GDS correspondence

Original native restoration41308526628 passed the unchanged1691clock/fixed-net gate but failed the wire-only connectivity predicate on142 of828owners. Diagnosis41312549409 passed23controls and found every failed graph connected when only the observed physical ODB pin rectangles were included. It did not certify those rectangles against GDS.

This read-only cloud job authenticates the complete existing469346574-byte native release430583367, including every archived member, and selects the current627640193-byte restored snapshot. It binds every observed pin to its actual instance/master/net and transform. It obtains the five original SHA256-pinned Ciel PDK archives using revision c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c from the unchanged prepare_mainchip_postroute_pdk.py source. No current upstream main branch is substituted.

The actual pinned sg13g2.map supplies drawing layers. Exact integer geometry conversion refuses rounding. The checker compares the native master pin union against all matching LEF pin definitions and its area against GDS drawing polygons, including hierarchy and holes. Pin-marker layers are never used as conducting metal. It then verifies the complete transformed native master pin union against the exact appended rectangles from the actual graph diagnosis. Unavailable SRAM/custom models and every mismatch remain explicit unresolved results.

The45controls include the inherited23graph controls plus22specific geometry/parser checks, including all8OpenDB orientation/origin transforms, polygon holes, missing metal, one-DBU mismatches, disjoint/decomposed geometry, unsupported pin geometry and ambiguous layer maps. Actual control results, not this planned count, determine qualification.

No route, pin, source library or original acceptance predicate is edited. A successful correspondence result proves only the observed metal used by the diagnostic graph. It does not execute full-chip LVS/DRC, export a final chip GDS, generate RC, close timing or certify a PHY. Any eventual connectivity-model correction must separately preserve all original failures and validate the remaining physical gates.

Implementation references:
- Pinned OpenDB dbTransform.cpp and dbInst.cpp at dcf36133a369abc8f3c5e5738cd4d82e4903c0e0: https://github.com/The-OpenROAD-Project/OpenROAD/tree/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/odb/src/db
- KLayout Region boolean geometry: https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout Trans integer orientations: https://www.klayout.de/doc-qt5/code/class_Trans.html
- Pinned Python distribution: https://pypi.org/project/klayout/0.30.2/

All acquisition and geometric computation run on GitHub. Native inputs remain in their exact original cloud releases; new derived reports and code are preserved as Actions artifacts and imported into Git proof records.
