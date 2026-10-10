# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Active interface profile: base electrical/PVT constraints plus explicit IO.
source $::env(SCRIPTS_DIR)/base.sdc
source [file join [file dirname [info script]] soc_top_qspi_io.sdc]

create_clock -name eth_rx_clk_i -period 8.0 [get_ports eth_rx_clk_i]
create_clock -name eth_tx_clk_i -period 8.0 [get_ports eth_tx_clk_i]
unset_input_delay [get_ports {eth_rx_clk_i eth_tx_clk_i eth_rxd_i* eth_rx_dv_i eth_rx_er_i}]
unset_output_delay [get_ports {eth_txd_o* eth_tx_en_o eth_tx_er_o eth_gtx_clk_o}]
create_generated_clock -name eth_gtx -source [get_ports eth_tx_clk_i] -divide_by 1 [get_ports eth_gtx_clk_o]

# Board/PHY budgets, not characterized pad/package measurements. Fixed 1 Gb/s
# full-duplex GMII. Replace against the selected external PHY and board skew.
set_input_delay -clock eth_rx_clk_i -max 3.0 [get_ports {eth_rxd_i* eth_rx_dv_i eth_rx_er_i}]
set_input_delay -clock eth_rx_clk_i -min 0.5 [get_ports {eth_rxd_i* eth_rx_dv_i eth_rx_er_i}]
set_output_delay -clock eth_gtx -max 2.5 [get_ports {eth_txd_o* eth_tx_en_o eth_tx_er_o}]
set_output_delay -clock eth_gtx -min -0.5 [get_ports {eth_txd_o* eth_tx_en_o eth_tx_er_o}]
set_clock_uncertainty $::env(CLOCK_UNCERTAINTY_CONSTRAINT) [get_clocks {eth_rx_clk_i eth_tx_clk_i eth_gtx}]
set_clock_transition $::env(CLOCK_TRANSITION_CONSTRAINT) [get_clocks {eth_rx_clk_i eth_tx_clk_i}]

# Async FIFOs use Gray pointers; control crosses through synchronizers. Bound
# all crossing datapaths by the shortest source period (8 ns) to prevent
# unbounded Gray-bus skew. Do NOT use clock_groups: it overrides max_delay.
# No phase-based hold requirement exists between these independent clocks.
foreach src {clk_i eth_rx_clk_i eth_tx_clk_i} {
    foreach dst {clk_i eth_rx_clk_i eth_tx_clk_i} {
        if {$src ne $dst} {
            set_max_delay -ignore_clock_latency 8.0 -from [get_clocks $src] -to [get_clocks $dst]
            set_false_path -hold -from [get_clocks $src] -to [get_clocks $dst]
        }
    }
}
if {[info exists ::env(OPENLANE_SDC_IDEAL_CLOCKS)] && $::env(OPENLANE_SDC_IDEAL_CLOCKS)} {
    unset_propagated_clock [all_clocks]
} else {
    set_propagated_clock [all_clocks]
}
