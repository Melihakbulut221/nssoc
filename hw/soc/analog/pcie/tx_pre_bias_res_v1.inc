* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
* SPDX-License-Identifier: CERN-OHL-W-2.0
* Real prestage reference feed, replacing an ideal constant current source.
* The receiving mux's diode-connected HBT determines the loaded ref voltage.
* One fixed geometry across PVT; native resistance, contact, substrate and
* self-heating model effects remain. Actual resulting current must be measured.
.subckt nssoc_tx_pre_bias_res_v1 avdd ref sub
XFEED avdd ref sub rppd w=2u l=22u b=0 sw_et=1
.ends nssoc_tx_pre_bias_res_v1
