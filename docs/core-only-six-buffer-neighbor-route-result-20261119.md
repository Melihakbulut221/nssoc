# Six-buffer neighbor route geometry result — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44538905014, head 07d0ef3dd129d244b41d4cde36aeff19b9c919ff, failed only its final zero-antenna assertion. Artifact 14539530451 SHA256 24af52387042dd16ef340e6df0c1bbca15d1710e87ee7ff65a60fec4b2eddaca: all 47 outputs verified.

Routed ODB SHA256 7f0a7df920df5716d0f31ca93b6f141c0d1909a403f6ded16c38cf5eb93c8764. Router DRC 0 at iteration 3. All 17 prior cross-net contacts removed; native geometry has zero contacts/disconnections/unwired nets/missing terminals and negative controls pass. Identity 106670 instances, 103096 nets. All 103080 unselected nonpower records and 2113 clocks preserved; 102964 encoded fixed routes restored.

One remaining antenna net/pin: nssoc_regiso_0_net, wire2380/A. Metal5 cumulative ratio 206.96 and TopMetal1 239.36 exceed limit 200. No full clean-route or timing acceptance claimed.

Next native diode-only repair uses ratio margin 10 percent. It must add 1..4 diodes only on this net, preserve all original cells and all other routes, and prove local power contact. Four existing loads leave at most four additional diode loads under the eight-load limit; an excessive insertion fails admission and is not silently accepted. Expected unaffected nonpower records: 103093. Fresh route/antenna/RC and all-corner STA remain required.
