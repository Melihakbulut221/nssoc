* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
* SPDX-License-Identifier: CERN-OHL-W-2.0
* Native supply-fed resistor references. One geometry at all PVT corners.
* Actual HBT diode references and next-stage loading remain in their stages.
.subckt nssoc_tx_final_bias_feed_v1 avdd reference sub
XFEED avdd reference sub rppd w=2u l=12u b=0 sw_et=1
.ends nssoc_tx_final_bias_feed_v1
.subckt nssoc_tx_output_bias_feed_v1 avdd reference sub
XFEED avdd reference sub rppd w=2u l=4.5u b=0 sw_et=1
.ends nssoc_tx_output_bias_feed_v1
