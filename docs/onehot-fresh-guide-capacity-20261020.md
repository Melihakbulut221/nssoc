# Native fanout route: measured guide congestion

Run39415055626 failed before detailed routing with GRT-0116. The final global report had8 overflow (Metal3:1, Metal5:7),141,683 routed nets and17,961,357um global wirelength. Native GRT-0704 recommended reducing layer adjustment from20% to0%.

The next trial changes only the artificial global-guide resource reduction from0.2 to0.0. [OpenROAD documentation](https://openroad.readthedocs.io/en/latest/main/src/grt/README.html#set-global-routing-layer-adjustment) describes this setting as the reduction in tracks assumed by global routing; it is not a spacing or manufacturing-rule override. No negative adjustment or capacity above the native estimate is used. This may still fail detailed routing.

All152,762 actual cells, pin connectivity, placement, fixed clock wires, power geometry, layer range,200 congestion iterations, native detailed DRC, antenna/disconnection checks and original20/4/8/8ns timing gates remain unchanged. Congestion is never accepted via allow_congestion. A passing global route is not routed timing closure or production signoff. The failed raw artifacts and report are retained.
