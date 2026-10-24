* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
* SPDX-License-Identifier: CERN-OHL-W-2.0
* Prospective lighter HV gate/drain load; native model measurement required.
* No qualified operating point or layout acceptance is implied.
.subckt nssoc_tx_cmos_hv_resistive_input_v3 din dout avdd dvdd avss sub
XBUF drv din dvdd avss sg13g2_buf_16
XHV_0 sink drv avss sub sg13_hv_nmos w=10u l=.45u ng=10
XHV_1 sink drv avss sub sg13_hv_nmos w=10u l=.45u ng=10
XHV_2 sink drv avss sub sg13_hv_nmos w=10u l=.45u ng=10
XHV_3 sink drv avss sub sg13_hv_nmos w=10u l=.45u ng=10
XIN sink dout sub rppd w=2u l=9.08u b=0 sw_et=1
XUP avdd dout sub rppd w=4u l=3.08u b=0 sw_et=1
XDOWN dout avss sub rppd w=2u l=7.10u b=0 sw_et=1
.ends nssoc_tx_cmos_hv_resistive_input_v3
