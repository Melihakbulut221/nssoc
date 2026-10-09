# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Apply only to a copied, placed packet-interface design. The caller must rerun
# all-corner timing, routing and physical verification before accepting the ECO.
# Clock definitions, I/O budgets and exceptions are never changed here.
proc nssoc_eth_output_hold_eco {} {
    set ports [list {eth_txd_o[0]} {eth_txd_o[1]} {eth_txd_o[2]} {eth_txd_o[3]} \
        {eth_txd_o[4]} {eth_txd_o[5]} {eth_txd_o[6]} {eth_txd_o[7]} \
        eth_tx_en_o eth_tx_er_o]
    foreach name $ports {
        if {[llength [get_ports -quiet $name]] != 1} {
            error "Expected Ethernet output port: $name"
        }
    }
    foreach name {eth_tx_clk_i eth_gtx} {
        if {[llength [get_clocks -quiet $name]] != 1} {
            error "Expected Ethernet clock: $name"
        }
    }
    if {[llength [get_cells -quiet eth_hold_eco_*]] != 0} {
        error "Ethernet output delay ECO already exists"
    }
    if {[[ord::get_db] findMaster sg13g2_dlygate4sd3_1] eq "NULL"} {
        error "Native Ethernet delay cell is missing"
    }
    set frozen {}
    foreach inst [[ord::get_db_block] getInsts] {
        if {[$inst getPlacementStatus] eq "PLACED"} {
            lappend frozen [list $inst [$inst getPlacementStatus] [$inst getLocation] [$inst getOrient]]
            $inst setPlacementStatus FIRM
        }
    }
    try {
        set i 0
        foreach port $ports {
            for {set j 0} {$j < 2} {incr j} {
                insert_buffer -buffer_cell sg13g2_dlygate4sd3_1 \
                    -load_pins [get_ports $port] \
                    -buffer_name eth_hold_eco_${i}_${j} \
                    -net_name eth_hold_eco_net_${i}_${j}
            }
            incr i
        }
        detailed_placement
        foreach item $frozen {
            lassign $item inst status xy orient
            if {[$inst getLocation] ne $xy || [$inst getOrient] ne $orient} {
                error "Existing instance moved during Ethernet ECO"
            }
        }
    } finally {
        foreach item $frozen {
            lassign $item inst status xy orient
            $inst setPlacementStatus $status
        }
    }
    check_placement -verbose
    puts "NSSOC_ETH_OUTPUT_DELAY_ECO_20 existing_placements_preserved=[llength $frozen]"
}
