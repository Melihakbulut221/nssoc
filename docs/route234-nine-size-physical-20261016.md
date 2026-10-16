# Actual physical nine-cell sizing experiment

The source is routed234run38896397749, ODB4a044ffdb4d92ec3e9150cb4a9696ed7dbfacc05361e64bc6b278259e6c3eeb4. Its independent continuity/contact screen passed113790nets; antenna639nets/791pins remain. Annotation has0loadedunannotateddrivers. Endpoint census38914920637 retains9359/470/1setup and0/0/7hold failures atslow/typical/fast.

Screen38917800540 tested9available doubled masters, preserving5unavailable requests as open. All135264source endpoint values reproduced. With frozen sourceRC, fastsetup1→0 (WNS+127.767ps), slowsetup9359→9357, typical470→470; holds unchanged0/0/7; no new violations. Logic passed and real inversion failed. The frozenRC result is only motivation.

The physical controller restores the exact parent, applies exactlythose9masterchanges, and makes onlythose9instances movable. Native detailed placement checks legal placement within200um; every other instance/master/location/orientation is preserved. Every net membership, PG geometry, NDR and top pin stays unchanged. A deliberate unselected-cell movement must fail the auditor. Wholechip restricted logic and inversion controls run again after legalization.

All signal pins touching the resized cells receive fresh native global guides; all other guide blocks are byte-identical to the parent. Full detailed routing follows. Only a zero native-router-DRV result proceeds to fresh nominalRC extraction and all22544endpoint/135264row measurement with unchanged originalSDC and cellcorner libraries, including exact graph coverage. Antenna results remain visible. The job preserves every failure and does not adopt the child as signed off.

After completion, independent signal geometry/annotation checks must bind the new output, and any setup/hold regressions must be evaluated. QualifiedRC, SRAM/PVT, fullchip transistorLVS, antenna repair and full serialPHY remain outside this candidate's acceptance. This is real placement/routing, not the prior unlegalized frozen-wireODB.
