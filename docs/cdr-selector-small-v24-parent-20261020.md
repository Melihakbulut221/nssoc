# Actual v24 sampler replacement in the CDR parent

Leaf run 39489042777 passes complete native physical validation: 560-category DRC, unsimplified 54-device deep/flat LVS, LEF, eighteen faults, and exact primitive/position/interface checks. Eight clock-selector drawings change from Nx4 to Nx2; the other 46 native drawings and all ten port rectangles are identical.

The next cloud-only job replaces exactly four sampler children in the physically passed, cleaned v23 parent. It changes exactly 32 corresponding reference Nx parameters. It preserves every parent polygon, existing shortened collector/retime trunk, all 16 transforms, and the other seven kinds of native child. No historical obsolete-metal cleanup is replayed. The existing unchanged PD476 full DRC/LVS and nine faults and all-child geometry validator must pass.

The top-level cell identifier remains nssoc_cdr_pd476_follower_v23 so the unchanged parent validator and physical interface apply. Exact evidence/source hashes identify the new revision; the retained cell name is not a claim that old RC can be reused. Fresh native wire extraction and loaded electrical tests are still required before accepting the new circuit.
