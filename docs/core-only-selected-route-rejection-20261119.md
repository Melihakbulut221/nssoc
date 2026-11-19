# Selected data routing rejected by route-preservation gate

Run 44430646506/head 114ada1259666213fd98c6655b41eb6883e0e9d7. Artifact 14486519767 SHA256 decf588129a86f60d12679e83a4982a070a099104e2fa62a3363c400bd1ea8f1 and all 22 outputs verified.

Selected global routing processed four data nets and preserved all 103081 other non-supply DEF records including 2113 clocks. Detailed routing reached zero router DRC and retained the source's 15 antenna net/pin violations, but changed 33 unselected DEF net records, including 19 clock records. The exact preservation gate rejected the candidate. Output ODB SHA256 3d5ace33b7e3fb91e515a393bdc788f29f7da60456900783531ea8873ce0103f.

DEF record changes alone do not quantify metal changes or timing effects. A native wire/via shape multiset comparison is now required to distinguish record reordering from actual shape changes. It is diagnostic only; no preservation waiver or timing acceptance is granted. Existing clock-resize routing is a separate candidate and remains subject to its own gate.
