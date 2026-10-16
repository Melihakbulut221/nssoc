# Actual physical nine-cell sizing experiment

The source is routed234run38896397749, ODB4a044ffdb4d92ec3e9150cb4a9696ed7dbfacc05361e64bc6b278259e6c3eeb4. Its independent continuity/contact screen passed113790nets; antenna639nets/791pins remain. Annotation has0loadedunannotateddrivers. Endpoint census38914920637 retains9359/470/1setup and0/0/7hold failures atslow/typical/fast.

Screen38917800540 tested9available doubled masters, preserving5unavailable requests as open. All135264source endpoint values reproduced. With frozen sourceRC, fastsetup1→0 (WNS+127.767ps), slowsetup9359→9357, typical470→470; holds unchanged0/0/7; no new violations. Logic passed and real inversion failed. The frozenRC result is only motivation.

The physical controller restores the exact parent, applies exactlythose9masterchanges, and makes onlythose9instances movable. Native detailed placement checks legal placement within200um; every other instance/master/location/orientation is preserved. Every net membership, PG geometry, NDR and top pin stays unchanged. A deliberate unselected-cell movement must fail the auditor. Wholechip restricted logic and inversion controls run again after legalization.

All signal pins touching the resized cells receive fresh native global guides; all other guide blocks are byte-identical to the parent. Full detailed routing follows. Only a zero native-router-DRV result proceeds to fresh nominalRC extraction and all22544endpoint/135264row measurement with unchanged originalSDC and cellcorner libraries, including exact graph coverage. Antenna results remain visible. The job preserves every failure and does not adopt the child as signed off.

After completion, independent signal geometry/annotation checks must bind the new output, and any setup/hold regressions must be evaluated. QualifiedRC, SRAM/PVT, fullchip transistorLVS, antenna repair and full serialPHY remain outside this candidate's acceptance. This is real placement/routing, not the prior unlegalized frozen-wireODB.


## Selected-guide correction after run38921431431

The actual nine replacements passed native legalization, unchanged-cell/net/PG/NDR
checks, and wholechip restricted Liberty logic proof (real inversion rejected).
The run then failed because selected GRT produced zero guide nets. Existing
`dbWire` routes were still attached to all23 selected nets. Pinned OpenROAD
`dcf36133a369abc8f3c5e5738cd4d82e4903c0e0` records those nets as already wired.
The empty guide was rejected; it was never adopted or silently replaced by the
parent guide.

The repair creates `guide-input.odb` from the intact legal `candidate.odb`.
Only the23 actual signal nets attached to resized cells lose their detailed wires
on this temporary copy. Every unselected dbWire opcode and data entry, all special
wires, all cells, net connectivity, PG, NDR and ports must remain identical.
A real unselected-wire detach is rejected and restored; the saved database is
re-read and verified. `guide-input-proof.json` retains source and removed-wire
hashes. Selected GRT must still generate exactly all23 selected net guide blocks.
The detailed router continues to use the intact `candidate.odb` with merged new
guides, then fresh extraction and all-endpoint checks. This correction itself is
not evidence of successful routing or timing closure.


Cloud diagnosis38925101397 of the actual rejected38924027432 archive found
23selected nets present,0missing, but113767extra guide nets (113790total).
These extra blocks were not byte-identical to the saved parent guide, so none
were accepted. Pinned native GlobalRouter::saveGuides replaces dbGuides only
for entries in its23-net routes_ map; other existing dbGuides survive and are
included by guide serialization. This is distinct from dbWire routes.

The guide-only copy now explicitly clears all old dbGuide metadata before GRT.
The initial113790guided-net census and removed rectangle count are retained;
serialized guide-input.odb must have zero dbGuides. All detailed-wire, cells,
connectivity and PG/NDR checks remain; the original candidate.odb and saved
parent guide are unchanged. Exactly23fresh generated guide blocks remain
mandatory, and all other merged blocks still come byte-for-byte from parent.
