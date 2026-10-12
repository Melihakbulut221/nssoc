* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
* SPDX-License-Identifier: CERN-OHL-W-2.0
* Unqualified inverting CMOS/HV-MOS data interface; no layout acceptance.
* LV buf16 drives HV gates only; no DC resistor path into the 1.2V output.
* Four native 3.3V-device branches share the pull-down current.
* Prospective nominal unloaded levels ~2.08V / ~1.8V; measure with real mux load.
.subckt nssoc_tx_cmos_hv_resistive_input_v2 din dout avdd dvdd avss sub
XBUF drv din dvdd avss sg13g2_buf_16
XHV_0 sink drv avss sub sg13_hv_nmos w=20u l=.45u ng=20
XHV_1 sink drv avss sub sg13_hv_nmos w=20u l=.45u ng=20
XHV_2 sink drv avss sub sg13_hv_nmos w=20u l=.45u ng=20
XHV_3 sink drv avss sub sg13_hv_nmos w=20u l=.45u ng=20
XIN sink dout sub rppd w=2u l=6.92u b=0 sw_et=1
XUP avdd dout sub rppd w=4u l=3.08u b=0 sw_et=1
XDOWN dout avss sub rppd w=2u l=7.70u b=0 sw_et=1
.ends nssoc_tx_cmos_hv_resistive_input_v2
