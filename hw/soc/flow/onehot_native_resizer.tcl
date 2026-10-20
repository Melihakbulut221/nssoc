# SPDX-License-Identifier: Apache-2.0
# Read-only source-bound timing baseline, followed by bounded candidate repair.
# This script is sourced after exact libraries, ODB, SDC and SPEF are loaded.
foreach {name period} {clk_i 20 pcie_clk_i 4 eth_rx_clk_i 8 eth_tx_clk_i 8} {
    set clock [get_clocks $name]
    if {[llength $clock] != 1 || abs([get_property $clock period]-$period)>1e-9} {
        error "Original physical clock budget changed: $name"
    }
}
set_propagated_clock [all_clocks]
foreach clock [all_clocks] {
    if {![get_property $clock is_propagated]} {error "Unexpected ideal clock"}
}
set block [ord::get_db_block]
if {[llength [$block getInsts]] != 151022} {error "Wrong source instance census"}
set macros 0
foreach inst [$block getInsts] {
    if {[[$inst getMaster] isBlock]} {incr macros}
}
if {$macros != 20} {error "Original twenty SRAM instances missing"}
puts "NSSOC_EXACT_ROUTED_SOURCE_CLOCKS_AND_SRAM_RETAINED"
if {$::env(NSSOC_RESIZER_STAGE) eq "baseline"} {
    foreach c $::env(NSSOC_CORNERS) {
        foreach kind {max min} {
            report_checks -corner $c -path_delay $kind -group_path_count 1 \
                -digits 9 -format full_clock_expanded \
                > "$::env(NSSOC_RESIZER_OUT)/before-$c-$kind.rpt"
        }
        report_check_types -corner $c -max_slew -max_capacitance -max_fanout \
            -violators -digits 9 > "$::env(NSSOC_RESIZER_OUT)/before-$c-checks.rpt"
    }
} elseif {$::env(NSSOC_RESIZER_STAGE) eq "repair"} {
    # Record every original placement and master before the optimizer runs.
    array set original_status {}
    array set original_master {}
    array set original_touch {}
    array set clock_touch {}
    foreach inst [$block getInsts] {
        set n [$inst getName]
        set original_status($n) [$inst getPlacementStatus]
        set original_touch($n) [$inst isDoNotTouch]
        set original_master($n) [[$inst getMaster] getName]
        set protect [[$inst getMaster] isBlock]
        foreach pin [$inst getITerms] {
            set net [$pin getNet]
            if {[[$pin getMTerm] getSigType] eq "CLOCK"
                || ($net ne "NULL" && [$net getSigType] eq "CLOCK")} {
                set protect 1
                if {$net ne "NULL" && ![info exists clock_touch($net)]} {
                    set clock_touch($net) [$net isDoNotTouch]
                    $net setDoNotTouch true
                }
            }
        }
        if {$protect} {
            # Native Resizer::setDontTouch uses this same ODB flag.
            # Object identity avoids STA glob/escape interpretation of Yosys names.
            $inst setDoNotTouch true
            if {![$inst isDoNotTouch]} {error "Native instance protection failed"}
        }
    }
    # Keep connectivity in the setup pass; do not clone/remove/swap/retime.
    # Multiple native repairs per pass reduce repeated full timing traversals.
    repair_timing -setup -setup_margin 0 -repair_tns 100 \
        -max_iterations 40 -max_repairs_per_pass 8 \
        -skip_pin_swap -skip_gate_cloning -skip_size_down -skip_buffering \
        -skip_buffer_removal -skip_last_gasp -skip_vt_swap -skip_crit_vt_swap \
        -verbose
    write_db "$::env(NSSOC_RESIZER_OUT)/setup-checkpoint.odb"
    write_verilog "$::env(NSSOC_RESIZER_OUT)/setup-checkpoint.v"
    # Restore cell flags before hold: protected clock nets stay immutable,
    # while a positive buffer may connect to a flip-flop/SRAM DATA input.
    foreach inst [$block getInsts] {
        set n [$inst getName]
        if {[info exists original_touch($n)]} {
            $inst setDoNotTouch $original_touch($n)
        }
    }
    # Setup violations are not authorized by this hold repair.
    repair_timing -hold -setup_margin 0 -hold_margin 0.1 \
        -max_iterations 200 -max_buffer_percent 20 -verbose
    write_db "$::env(NSSOC_RESIZER_OUT)/hold-checkpoint.odb"
    write_verilog "$::env(NSSOC_RESIZER_OUT)/hold-checkpoint.v"
    foreach net [array names clock_touch] {
        $net setDoNotTouch $clock_touch($net)
    }
    # Only changed/new instances are mobile during legalization.
    foreach inst [$block getInsts] {
        set n [$inst getName]
        if {[info exists original_master($n)]
            && $original_master($n) eq [[$inst getMaster] getName]} {
            $inst setPlacementStatus FIRM
        } else {
            $inst setPlacementStatus PLACED
        }
    }
    detailed_placement -max_displacement {80 80}
    check_placement -verbose
    foreach inst [$block getInsts] {
        set n [$inst getName]
        if {[info exists original_status($n)]} {
            $inst setPlacementStatus $original_status($n)
        }
    }
    write_db "$::env(NSSOC_RESIZER_OUT)/candidate.odb"
    write_verilog "$::env(NSSOC_RESIZER_OUT)/candidate.v"
    puts "NSSOC_REPAIR_CANDIDATE_REQUIRES_NEW_ROUTE_RC_ALL_CORNERS"
} else {
    error "Unknown native repair stage"
}
