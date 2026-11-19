# Six-buffer preparation verified — 2026-11-19

Successful run https://github.com/Melihakbulut221/nssoc/actions/runs/44532861957, head 481824f68e5ada49d73c47c15b93aa2f77b48615, attempt 1. Previous run 44532203751 failed before executing design tools because Ubuntu libfuse2 download failed; no candidate artifact was produced by that run.

Artifact 14533803559 SHA256 19ba066d94d191b0ae85c306da9a3cce7f1a76cc692c0741e9c5757de37b40f4, all 17 output hashes verified. Candidate ODB SHA256 941525579d58b9da088a84b47f3bf4ed35ce33e6b24bc9ee6c6aabeca91d9b2e.

Six new buf_8 cells; 106670 instances. All original instance geometry preserved. Exact original terminal connections recovered after collapsing six identity buffers; deliberately wrong-connection control rejected. All original diodes retained; ten explicit signal reconnections verified (491,500,2569..2576). 103083 unaffected nonpower DEF net records and all 2113 clock routes preserved. NDR assignments preserved. All 12 added power terminals contact the correct native rails, with no failures; synthetic controls and actual rail-removal negative control passed.

Next step: route only five original nets and six new buffer output nets. Encode all unselected routed wires FIXED, verify native encoded type, restore ROUTED and verify unchanged routes. Require identity, native visible-geometry and antenna results before fresh RC. This preparation is not timing, antenna, full GDS/LVS or production signoff.
