# Routed128buffer candidate: clock/data regression investigation

The completed native route39331918238 has0routing DRC errors,0critical disconnected pins and16antenna nets. Setup counts are9660/7027/3107 and hold counts3/17/95 at slow/typical/fast cell corners with fresh nominal RC. All original20/4/8/8ns clocks and5percent derate remain. The candidate is not accepted.

Read-only review39362291106 found a shared PCIe capture-clock branch in representative newly failing fast hold paths: clkbuf_3_5_0_pcie_clk_i/X to clkbuf_6_46_0_pcie_clk_i/A contributes0.684392ns net delay and1.292744ns receiving slew. The same branch appears in the advertiser refresh paths. This is evidence to investigate, not proof that changing the clock branch will safely repair timing.

The new hosted comparison reads all available old/new min path reports and separates data arrival and required-time changes at identical endpoints. It ranks capture branches by measured delay change and affected negative endpoints, and retains reported setup slack on those same endpoints in all3corners. No report sample is represented as an exhaustive endpoint census.

Before inserting hold delay into many data paths, inspect actual clock route geometry and extracted parasitics for common changed branches. Any proposed clock repair must preserve constraints and be remeasured for setup and hold after native route/RC; improving hold by making capture earlier can hurt setup.

OpenROAD's documented incremental global routing can update dirty nets after edits, but availability and exact behavior must be checked against the pinned runtime before implementation: [global routing documentation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/grt/README.md). The running design is not changed by consulting this documentation.

Full PCIe serial PHY, loaded PLL/CDR/TX qualification, comprehensive LVS/DRC/antenna and final timing remain separate open requirements.
