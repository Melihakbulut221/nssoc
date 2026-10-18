# Onehot mainchip global routing and detailed-route handoff

Run [39082708488](https://github.com/Melihakbulut221/nssoc/actions/runs/39082708488), source `1eed365029e07ccc65680e5e30a2adb3e46c116d`, completed native global routing in 510.67 seconds. It routed 141375 nets, reported zero final overflow, preserved native NDR demand without disabling any nets, and retained 20 SRAM macros. Wire length is 16751664 um and the reported via count is 1061581. These are global-route measurements, not detailed-route geometry or final timing.

The source was targeted repair 39080594759, independently bound to the onehot RTL, native boot/protocol proofs and retained-cell logic proof. The original clocks (20/4/8/8 ns), 5 percent derate and 20 percent capacity reserve remain. Clock routes use Metal4 through TopMetal2.

The `replay-onehot-detailed-route-cloud` workflow restores the exact proven source chain and global-route ODB/guide hashes. It runs native detailed routing with the existing orphan-only guide cleanup, native antenna repair, an antenna report and disconnected-pin report. A completed clean stage requires zero native routing DRC errors, zero antenna nets and zero critical disconnected pins; partial or failing stages remain recorded. Full physical connectivity, geometry DRC/LVS, extracted timing and serial PHY integration still require their independent checks. No timing or circuit acceptance criterion is relaxed.

The 3.0.5 native DRT and checker interfaces were inspected in the published LibreLane source before constructing the continuation. Two routing threads and a DRC report every five iterations are resource/report settings only. The native 64 optimization-iteration limit and positive antenna-repair limit are retained.
