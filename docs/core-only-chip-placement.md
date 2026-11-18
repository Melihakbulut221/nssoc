# Provisional shell placement

Run44280535239/source d7494b71ca03709edd3c4a99589c843170bcc0cf SUCCESS. Native14415469830 SHA77c6f9d188a013dd4b30560971bbf8b5f7c3599652238e2dc2ac20378b32da32;summary14417405367 SHA1975922a2e68aa5a2820e6b93c954099c60d6f656e7f55d050eeb5643de4f82f. All8outputs/native-summary equality/protected source hashes verified. Native check_placement completes; independent audit:1253shellcells PLACED,297fixed blocks unchanged,8774connections/80top pin shapes preserved,1407rows,zero rectangle overlaps,ODB readback exact. placement-check.json absent because native DPL writes only when marker category exists; not a missing required proof. See docs/evidence/core-only-chip-placement-20261118.json.

Next: real shell clocks/CDC and pad timing models, CTS/PDN/routing, rebind final core. Main DRT44263061910 still live at last poll, untouched. No final timing or manufacturing acceptance; PCIe/Ethernet excluded,20ns/5% unchanged.


The initial invocation failed on unsupported disable flags. The pinned OpenROAD Tcl help lists these flags but its parser does not accept them. The corrected invocation uses global_placement -density 0.3, with timing/routability optimization not enabled. No constraints were relaxed and no cells or connections were removed.
