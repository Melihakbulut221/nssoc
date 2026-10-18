# Onehot targeted repair result and fresh routing candidate

Native run 39080594759 removed exactly nine selected internal buffers, retained clock connections, repaired the branches, and passed retained-equation/state proof over 97622 cells with native negative controls. All source, protocol and native boot proofs were revalidated. The baseline exactly reproduces the preceding repaired timing.

| Corner | Setup count before → after | Setup WS ns before → after | Hold count before → after | Hold WS ns after |
|---|---:|---:|---:|---:|
| Slow | 8147 → 8037 | -6.19976 → -5.54096 | 11 → 10 | -0.575487 |
| Typical | 5036 → 4864 | -2.80900 → -2.50691 | 22 → 16 | -0.468540 |
| Fast | 1098 → 663 | -1.07956 → -0.901378 | 171 → 24 | -0.391465 |

Fast register-to-register hold failures decreased from 130 to three, with worst slack -0.049087 ns. These are fresh placement-estimate measurements and do not close final timing. The worst external hold remains unchanged.

The next cloud job restores this exact targeted ODB/netlist plus its source chain. It runs global routing with clock layers Metal4–TopMetal2, original signal layers and 20% capacity reserve, and 200 congestion iterations. Original clocks, SDC, 5% derate and 20 SRAMs remain bound. Both zero native final overflow and preservation of native nondefault routing rules are mandatory. This is a new netlist/placement candidate; old regional congestion coordinates are not reused. Detailed routing, extracted timing, DRC/LVS and full PHY integration are subsequent gates.
