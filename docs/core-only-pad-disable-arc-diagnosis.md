# Slow-corner bidirectional pad diagnosis (2026-11-18)

The 3048-instance parent route 44360083454 is independently admitted: artifact 14455650701, SHA256 81864e55ef6fd8c641dae1fdb55f5ca4b7324eef210b740523553142d40cc156, 27 output and 7 repository source hashes verified, native DRC 0, exact identity and visible geometry passed. Routed ODB: 719cdc0a6d0effed3d911b9080de93dda1422f9d4910a34f627ae62fd68c3b59.

Fresh timing 44362003609 / 3019df728554a279346dfd35fb8d6985935718ee: artifact 14455801272, SHA256 5e03e4fc2cfbc8632248a5154cb47812e4a3cf7429b2022dc18fb4ba2d570206. All 30 outputs and 3 protected repository sources verified; 3022 exact SPEF nets. SPEF SHA256 74908529bc58bcb5a2899799367b522e96244d30a468d21354ffc1c56c5deaf7. Parent-only slew counts slow/typ/fast: 22/0/0, versus 51/39/27 before core-output buffering. No new buffer-chain violation. Nominal RC and provisional IO/CDC remain limitations.

Actual original-core comparison 44362575697 / be82145129c1dfb302fb62d0c60dd778bdfacacb: artifact 14455806852, SHA256 c31dae704fbf8964ce127d74942d273b6326e25ff15ede420984f254cf2ed879; all outputs and protected sources verified. Typical scoped max/min slack +6.709907532/+0.184363917 ns. Original core unannotated driver set unchanged; no unknown boundary drivers. This uses the old pre-ECO 104885-instance core, not current core signoff. Missing external IO budgets, 103 unconstrained endpoints and physical-only filler/corner timing blackboxes remain explicit warnings.

## Root cause of the remaining 22 parent slow-corner violations

Native read-only report_dcalc run 44362946636 / a7014b881603daf1b851cd21bff6141033e39b38: artifact 14456576962, SHA256 1a51492ff2cf08586a37fa150d8acb979a49f7920b017f1fc1f825580f2e1c25. All 52 outputs and protected repository sources verified, including 44 per-pad arc reports. Every violation is at the pad terminal of the 16 GPIO, 4 QSPI and 2 I2C bidirectional cells.

Example GPIO0: normal c2p rise/fall slew 0.663277030/0.601117134 ns; enable slew 0.663084567/0.602489471 ns. Disable arcs instead report 0Z slew 1.773274302 ns and 1Z slew 1.919492006 ns. The latter exactly matches the max-slew violation against 1.200000048 ns. This is not a remaining long internal-wire transition.

The pinned IHP slow IO Liberty (SHA256 a23776c264fc0d177b4a5612eb3e1595c0eddc98d5b28b5ef7925e40b743b6ae) contains numerically identical cell_rise/rise_transition and cell_fall/fall_transition tables for the three_state_disable arc. This observation does not establish that the published model is wrong and does not authorize deleting those arcs.

| Bidirectional pad | Minimum disable rise table value ns | Minimum disable fall table value ns |
|---|---:|---:|
| 4 mA | 1.73402 | 1.88995 |
| 16 mA | 2.00669 | 2.58314 |
| 30 mA | 2.26155 | 3.40017 |

These are tabulated values, not new native candidate measurements or universal extrapolation bounds. A stronger pad is not supported as the remedy for this particular violation: the published disable tables get slower. All three have the same 80 x 180 um LEF body including pins/obstructions after normalizing only the FOREIGN cell name. Pinned sg13g2_io.lef SHA256 8b3dc3960960c08e07a1cde3dd9cd0484f5b12df07c4628726fff551bb775c0c. This does not establish GDS equivalence or power/ESD equivalence.

Next: qualify the high-impedance transition model and external bus/pullup/turnaround behavior using transistor models and real interface loads. Keep the 22 violations visible until a model correction or an interface-specific acceptance criterion is justified by evidence. Do not hide the issue with blanket false paths, set_disable_timing, a relaxed global slew limit, or unqualified pad substitution.

Pinned OpenSTA report_dcalc definition: https://github.com/The-OpenROAD-Project/OpenSTA/blob/857316ff001b2a8dbbdc5996944d08a6d38c87ab/dcalc/DelayCalc.tcl

Core detailed route 44337630426 and selected ECO boot 44342916945 remain live at last check; preserve these handles. No manufacturing approval has been achieved.
