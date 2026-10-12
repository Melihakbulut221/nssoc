* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
* SPDX-License-Identifier: CERN-OHL-W-2.0
* Unqualified CMOS-to-HBT data interface experiment, not an accepted PHY.
* Actual foundry buf16 plus substrate-connected, self-heating native resistors.
* Nominal 260ohm/square estimates target ~1.93V common mode / 0.30V differential.
* Contact resistance, base current and CMOS backfeed must be measured natively.
* dvdd is 1.2V; avdd is 2.5V. Rail sinking/startup sequencing are not qualified.
.subckt nssoc_tx_cmos_resistive_input_v1 din dout avdd dvdd avss sub
XBUF drv din dvdd avss sg13g2_buf_16
XIN drv dout sub rppd w=2u l=3.08u b=0 sw_et=1
XUP avdd dout sub rppd w=4u l=2.16u b=0 sw_et=1
XDOWN dout avss sub rppd w=1u l=10.12u b=0 sw_et=1
.ends nssoc_tx_cmos_resistive_input_v1
