# Routed128buffer candidate: clock/data regression investigation

The completed native route39331918238 has0routing DRC errors,0critical disconnected pins and16antenna nets. Setup counts are9660/7027/3107 and hold counts3/17/95 at slow/typical/fast cell corners with fresh nominal RC. All original20/4/8/8ns clocks and5percent derate remain. The candidate is not accepted.

Read-only review39362291106 found a shared PCIe capture-clock branch in representative newly failing fast hold paths: clkbuf_3_5_0_pcie_clk_i/X to clkbuf_6_46_0_pcie_clk_i/A contributes0.684392ns net delay and1.292744ns receiving slew. The same branch appears in the advertiser refresh paths. This is evidence to investigate, not proof that changing the clock branch will safely repair timing.

The new hosted comparison reads all available old/new min path reports and separates data arrival and required-time changes at identical endpoints. It ranks capture branches by measured delay change and affected negative endpoints, and retains reported setup slack on those same endpoints in all3corners. No report sample is represented as an exhaustive endpoint census.

Before inserting hold delay into many data paths, inspect actual clock route geometry and extracted parasitics for common changed branches. Any proposed clock repair must preserve constraints and be remeasured for setup and hold after native route/RC; improving hold by making capture earlier can hurt setup.

OpenROAD's documented incremental global routing can update dirty nets after edits, but availability and exact behavior must be checked against the pinned runtime before implementation: [global routing documentation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/grt/README.md). The running design is not changed by consulting this documentation.

Full PCIe serial PHY, loaded PLL/CDR/TX qualification, comprehensive LVS/DRC/antenna and final timing remain separate open requirements.

## Native clock versus data attribution

Cloud run [39364077862](https://github.com/Melihakbulut221/nssoc/actions/runs/39364077862)
completed the same-endpoint native report comparison after rejecting and correcting
unrecognized actual SRAM clock ports and CTS delay-buffer stages. Native slack
equations and source hashes remain checked. Full frozen report and provenance:
docs/evidence/onehot-clock-regression-pass-20261020.json.

At the fast corner, 75 of 95 negative reported minimum paths share the output of
clkbuf_3_5_0_pcie_clk_i. Compared with the actual previous 33-buffer route, its
connections to clock branches 6_44, 6_45, 6_46 and 6_47 gained respectively
0.513008, 0.515861, 0.525570 and 0.527561 ns of measured net delay.
These paths include asynchronous removal checks; they are not all register
data hold paths. The report sample contains 31 previously nonnegative endpoints
that became negative; unmatched or unsampled endpoints cannot be counted as
newly failing.

This is evidence of clock-route regression, not proof that advancing capture
clocks alone is safe: several of the same endpoints already fail setup in the
current design. Next compare actual ODB geometry and exported nominal wire RC,
then validate a physical repair with fresh routing, extraction and all corners.
No clock period, external delay, derating, exception or acceptance threshold
has been changed. The 128-buffer layout remains rejected for final timing.
