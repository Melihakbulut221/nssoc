# Eight-diode preparation verified — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44518671953 succeeded at attempt 1 on d14bbe71c8b0f6c51415c86b5f4f43384272f08d.
Artifact 14527411628 SHA256 308f48a0aef5a5f9dc5d779b4e12df86264f90ee82a244850de27cc08d6a3c7c; all 13 output hashes independently verified in memory.

Exactly ANTENNA_2569 through ANTENNA_2576 were added to nssoc_sta_n_60783. The candidate contains 106664 instances; all original 106656 instances retain exact geometry/status/connections. All sixteen added power terminals have positive same-net supply contact, no wrong-supply contacts; synthetic negative controls and actual native rail-removal detection pass. This proves local LEF/special-wire contact, not global IR/EM or transistor LVS.

103087 unaffected non-power net records and all 2113 clocks are unchanged. ODB SHA256 8d1a34b991abf59c1e26a7e2ef119b3ee74f7bf82ddd96167b4e95814524e5ed.

The next experiment routes only 60783 while encoding all other routes FIXED and later restoring ROUTED status. Exact record/identity, antenna, DRC and independent native geometry gates remain mandatory. Preparation success alone does not establish antenna closure, fresh-RC timing or manufacturing approval. No timing constraints are changed.
