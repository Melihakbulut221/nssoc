# Six-buffer eleven-net route rejected — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44533830219, head c5a7af65d4771c54314edc1d8d761cc6a7ad3b50, attempt 1, failed visible-geometry audit.
Artifact 14535888831 SHA256 a9a11bbbc74e1c58095f5eeeef7b73299e42d2b483760ed67564b8111f9a5dd5; all 45 output hashes verified. Routed ODB 284137acb3478477515652b8627036a1674eb91694fac3ce10257c46000c1bc7.

Router DRC 0 at iteration 23. Antenna 1 net / 1 pin: nssoc_regiso_0_net, wire2380/A; Metal5 cumulative 206.96 and TopMetal1 239.36 against limit 200. Existing diode protection is insufficient at these intermediate layers. No disconnected geometry, missing terminals or unwired multi-terminal nets.

Visible inter-net contacts: 17. Metal2 62797/64543:2; Metal2 regiso_5/62886:3; Metal2 18115/60783:7; Metal3 18115/60783:5 (numeric names prefixed nssoc_sta_n_, regiso prefixed nssoc_ and suffixed _net). Identity 106670 instances / 103096 nets preserved; 103083 unselected nonpower records and all 2113 clock routes preserved; 102967 fixed encoded routes restored.

Next candidate starts from the same verified six-buffer preparation 941525579d58b9da088a84b47f3bf4ed35ce33e6b24bc9ee6c6aabeca91d9b2e and expands only by the three measured neighbors 62797, 62886 and 18115. Fourteen selected nets total; 103080 nonpower routes remain protected. Require new geometry and antenna results; no RC signoff from the rejected route.

The independent complete electrical-row parser run 44537220826 succeeded. Artifact 14536577764 SHA256 73aa36fa0ac908c2ad3568bae34ccaf3abec118cb753ab26b8aa42ca670bf1c2 verified; all three corners and electrical count classes match native metrics for both previous candidates. Eighty blank-slack fanout rows are now retained. This does not change physical timing results.
