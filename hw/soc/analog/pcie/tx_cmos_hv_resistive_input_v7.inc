* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
* SPDX-License-Identifier: CERN-OHL-W-2.0
* v6 gate resistor length increased from4.5um to12um.
* Measured v6 cold buf16 peak1.338V still exceeds1.32V.
* Source slew/phase unchanged; actual native gate waveform must be screened.
* Prospective damping of buf16 feedthrough at cold/high supply; must measure.
* Not yet laid out or PVT accepted.
.subckt nssoc_tx_cmos_hv_resistive_input_v7 din dout avdd dvdd avss sub
XGATE din gate sub rppd w=2u l=12u b=0 sw_et=1
XBUF drv gate dvdd avss sg13g2_buf_16
XHV_0 sink drv avss sub sg13_hv_nmos w=10u l=.45u ng=10
XHV_1 sink drv avss sub sg13_hv_nmos w=10u l=.45u ng=10
XHV_2 sink drv avss sub sg13_hv_nmos w=10u l=.45u ng=10
XHV_3 sink drv avss sub sg13_hv_nmos w=10u l=.45u ng=10
XIN sink dout sub rppd w=2u l=6.92u b=0 sw_et=1
XUP avdd dout sub rppd w=4u l=3.08u b=0 sw_et=1
XDOWN dout avss sub rppd w=2u l=7.10u b=0 sw_et=1
.ends nssoc_tx_cmos_hv_resistive_input_v7
