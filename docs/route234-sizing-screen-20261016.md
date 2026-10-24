# Fourteen-driver sizing experiment on the actual234 routed source

The234child has7fast hold failures,0typical and0slow, but9359/470/1setup failures at slow/typical/fast. It is not accepted. The15overloaded output drivers previously measured on146are only hypotheses until remeasured on this child.

The new cloud experiment restores the exact234ODB/SPEF and independent22544endpoint/135264row census, verifies the parent/child recipe, reproduces every published endpoint value, then queries min/max through all15outputs in all3corners. The initial14-driver recipe excludes place27767/X, whose146hold margin was148ps. All14selected outputs must still have positive reachable hold margin on234before substitution. Positive margin is not proof that acceleration is safe.

Each selected real PDK master is doubled1→2or2→4only when its physical master exists and terminal names/directions/types agree. All114025cell anchors, allunselectedmasters, allpin/net membership and114097nets remain unchanged. Actual wholechip netlists are checked using the existing restricted Liberty-backed logic proof; inversion of place29858must fail. All22544endpoints are then compared with exact graph coverage and unchanged original SDC, cell corners and234SPEF. Unconstrained endpoints and every new negative slack stay visible.

This is explicitly a frozen-RC ranking experiment. The output is named unlegalized-frozen-wire.odb. Wider cells and moved pins invalidate its route geometry, so it cannot replace the routed234candidate. A promising result requires legal placement, actual route repair, fresh parasitic extraction, allendpoint remeasurement and independent geometry/annotation/antenna/LVS checks before adoption. No clock relaxation, false-path insertion, changed endpoint scope or electrical waiver is used.

## Actual library result and revised experiment

Run38916747397 reproduced all135264original234endpoint rows and measured all15reachable driver margins, but rejected the first proposed substitution: sg13g2_nand4_2 is absent from the actual ODB library. This failed hypothesis is retained. The revised experiment writes the actual library master inventory, explicitly records every unavailable doubled cell, leaves those instances unchanged, and measures only available members of the same14requests. The number implemented is reported; it is not described as14completed substitutions. It never substitutes a guessed cell or synthesizes timing for a nonexistent master. Unimplemented heavy-load drivers remain open for a separately proven buffering/decomposition solution.
