* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
* SPDX-License-Identifier: CERN-OHL-W-2.0
* Real prestage reference feed, replacing an ideal constant current source.
* The receiving mux's diode-connected HBT determines the loaded ref voltage.
* One fixed geometry across PVT; native resistance, contact, substrate and
* self-heating model effects remain. Actual resulting current must be measured.
.subckt nssoc_tx_pre_bias_res_v1 avdd ref sub
XFEED avdd ref sub rppd w=2u l=22u b=0 sw_et=1
.ends nssoc_tx_pre_bias_res_v1

* Fixed-temperature-coefficient candidate; original feed above is unchanged.
* Sheet estimates: 100*7 + (16.5/2)*260 = 2845 ohm versus2860 baseline.
* Rsil TC1=3100ppm/K, Rppd TC1=170ppm/K; actual native corner models decide.
* https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/02_process_control_params.html
* This is a schematic feed: physical routing, contact current and PEX unproven.
.subckt nssoc_tx_pre_bias_res_tc_v1 avdd ref sub
XTC avdd mid sub rsil w=1u l=100u b=0 sw_et=1
XFEED mid ref sub rppd w=2u l=16.5u b=0 sw_et=1
.ends nssoc_tx_pre_bias_res_tc_v1
