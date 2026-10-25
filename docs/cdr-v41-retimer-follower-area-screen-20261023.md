# CDR v41 retimer follower area screen

V40 cached-wave diagnosis39926831412 reproduces all original failures. For early C, changing from slave_select4 to all_select34 moves measured master track-off nearest-edge median from15.0616ps to15.6146ps and slave track-on from15.4191ps to15.8255ps. These nearest-edge statistics are descriptive, not a proof of causal delay or ordinal lock. C's early0.3UI slave output still has46 wrong signs. Larger selectors do not establish a repair and additionally lose VCE headroom.

New candidates return to exact v39follower_l18, retaining masterNx2/slaveNx3 selectors, all data/hold HBTs,1.8um emitter pull-downs,6um C/D input dividers, tail MOS and external clocks/loads. Only four actual ac/bd emitter-follower HBT emitter counts change4->6 or4->8. Their B/E/C connections, parentNx/native IDs and positive/negative source pins are bound to the actual completed v39 diagnosis. Five parameter and six native-graph corruptions must reject.

The hypothesis is that changing the follower current density may alter VBE/common-mode and drive without shortening pull-down resistors further. It may instead increase load on A/B and worsen delay. No current, gain, headroom or pass is assumed. Every original output, phase, current and device gate remains active for both complete early/late34.25ns captures.

Relative to original476-device model,80 unique parameter changes must reverse exactly. All17918R/12850C wire cards stay frozen for this exploratory screen; four additional area changes are not a fresh physical implementation. Any useful result still requires actual candidate PCells/placement, native DRC/LVS, fresh complete RC, full loaded/PVT/recovery-loop validation and eventualx4 integration. No failed v39/v40 capture is discarded.
