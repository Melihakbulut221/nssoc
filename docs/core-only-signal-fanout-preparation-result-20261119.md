# Signal fanout preparation result — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44572321564 passed at source `d2890354ff2ba58a2c1f64a23c0d19bd039d5d2c`. Artifact 14555371112 SHA-256 `70cd6cd78803faf97e50979f0c04a738616121c1a9a9b7338408f18de949bbaf`; all 17 output hashes verified.

Candidate ODB `2338707a927b80c95dbb087a332ea42f32e9c514c737bc25ae344d4e4da7a40c`, source `12a48d839091ba5c4fea76a193fea75fcc5f2f38621b1df809cb3df5bd51e458`. Added 413 buffers, total 107,106 instances. All original geometry and connections after identity-buffer collapse preserved; deliberate wrong-connection control rejected. All 826 new power terminals passed rail contact checks. The 720 original diodes are retained and their signal connections recover after buffer collapse.

205 source nets plus 413 new outputs require routing. All 102,910 unaffected nonpower DEF records, 2,113 clock routes and NDR assignments were preserved. Changed nets have at most eight loads in this prepared topology. That does not yet establish routed electrical or timing closure.

Next run routes these exact 618 nets, encodes unaffected paths as FIXED for detailed routing, restores their ROUTED status, and checks exact preservation and independent wire/via connectivity/contact geometry. Any antenna or contact failure remains a rejection; fresh RC is allowed only after these checks pass.
