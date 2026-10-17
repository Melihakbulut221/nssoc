* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
* SPDX-License-Identifier: CERN-OHL-W-2.0
* Native resistor feeding the loaded HBT clock common-mode reference.
* Same resistor family as the offset leg; fixed geometry across all corners.
.subckt nssoc_tx_clock_bias_feed_v1 avdd cm sub
XFEED avdd cm sub rppd w=2u l=14.5u b=0 sw_et=1
.ends nssoc_tx_clock_bias_feed_v1
