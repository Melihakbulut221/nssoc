* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
* SPDX-License-Identifier: CERN-OHL-W-2.0
* Candidate native common-mode feedback for an actual loaded serializer stage.
* Both outputs feed the existing diode-connected reference through equal
* physical rppd resistors. Rising output common mode increases tail current,
* producing negative feedback through the stage collector loads.
* Fixed geometry at every PVT point; no controlled source or voltage clamp.
* Two26um/2um feeds have13um/2um effective parallel geometry. The lower
* output-to-reference headroom versus supply feed motivates this first point.
* Schematic feed candidate only: no feed layout/RC or PVT acceptance implied.
.subckt nssoc_tx_pre_bias_feedback_v1 op on ref sub
XFP op ref sub rppd w=2u l=26u b=0 sw_et=1
XFN on ref sub rppd w=2u l=26u b=0 sw_et=1
.ends nssoc_tx_pre_bias_feedback_v1
