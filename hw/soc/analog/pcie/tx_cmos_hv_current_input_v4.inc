* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
* SPDX-License-Identifier: CERN-OHL-W-2.0
* Prospective current-sinking interface; native nominal/PVT checks required.
* HV drains connect directly to the loaded data node, without series XIN RC.
* LV output sees gates only. Both rail-setting resistors remain native rppd.
.subckt nssoc_tx_cmos_hv_current_input_v4 din dout avdd dvdd avss sub
XBUF drv din dvdd avss sg13g2_buf_16
XHV_0 dout drv avss sub sg13_hv_nmos w=4u l=.45u ng=4
XHV_1 dout drv avss sub sg13_hv_nmos w=4u l=.45u ng=4
XHV_2 dout drv avss sub sg13_hv_nmos w=4u l=.45u ng=4
XHV_3 dout drv avss sub sg13_hv_nmos w=4u l=.45u ng=4
XUP avdd dout sub rppd w=4u l=3.08u b=0 sw_et=1
XDOWN dout avss sub rppd w=2u l=6.16u b=0 sw_et=1
.ends nssoc_tx_cmos_hv_current_input_v4
