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
if {[llength [$block getInsts]] != 152762} {error "Wrong source instance census"}
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
    source $::env(NSSOC_ROUTER_INIT_TCL)
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
    # Whole-instance dont-touch also prohibits inserting a data-input buffer.
    # Retain original user flags and clock-net protection, but forbid every
    # drive strength of clock-pin cell families from native resizing.
    # Hard macro geometry and every sequential clock pin remain independently
    # checked after repair and legalization.
    foreach inst [$block getInsts] {
        set preserve_family [[$inst getMaster] isBlock]
        foreach pin [$inst getITerms] {
            if {[[$pin getMTerm] getSigType] eq "CLOCK"} {set preserve_family 1}
        }
        if {$preserve_family} {
            set master [[$inst getMaster] getName]
            regsub {_[0-9]+$} $master {_*} family
            set family_cells [get_lib_cells "*/$family"]
            if {[llength $family_cells] == 0} {error "Missing protected clock-pin/macro family: $master"}
            set_dont_use $family_cells
        }
        set n [$inst getName]
        $inst setDoNotTouch $original_touch($n)
    }
    # Exact routed SPEF baseline above remains immutable evidence.
    # read_guides is not a complete pin-connected global-route tree:
    # run 39663969344 failed RSZ-0074 (3 reachable loads versus 8 expected).
    # Use placement/Steiner estimates ONLY to construct a candidate.
    # Fresh routing/extraction/all-corner measurements remain mandatory.
    estimate_parasitics -placement
    foreach c $::env(NSSOC_CORNERS) {
        foreach kind {max min} {
            report_checks -corner $c -path_delay $kind -group_path_count 1 \
                -digits 9 -format full_clock_expanded \
                > "$::env(NSSOC_RESIZER_OUT)/optimizer-placement-$c-$kind.rpt"
        }
    }
    puts "NSSOC_PLACEMENT_ESTIMATES_FOR_CANDIDATE_ONLY_NOT_FINAL_TIMING"
    # Repair electrical loads on the explicitly labelled candidate estimate.
    # All clock/SRAM guards and original clocks/constraints remain in force.
    # Keep a real checkpoint even if subsequent timing/proof rejects the candidate.
    if {[catch {repair_design -slew_margin 10 -cap_margin 10 -max_utilization 80 -verbose} failure options]} {
        write_db "$::env(NSSOC_RESIZER_OUT)/electrical-unchecked.odb"
        write_verilog "$::env(NSSOC_RESIZER_OUT)/electrical-unchecked.v"
        return -options $options $failure
    }
    write_db "$::env(NSSOC_RESIZER_OUT)/electrical-checkpoint.odb"
    write_verilog "$::env(NSSOC_RESIZER_OUT)/electrical-checkpoint.v"
    # Setup may add positive buffers/load splits; no clone/remove/swap/retime.
    # Native Liberty equation proof and original-instance retention are mandatory.
    if {[catch {
        repair_timing -setup -setup_margin 0 -repair_tns 100 \
            -max_iterations 80 -max_repairs_per_pass 1 -max_utilization 80 \
            -skip_pin_swap -skip_gate_cloning -skip_size_down \
            -skip_buffer_removal -skip_last_gasp -skip_vt_swap -skip_crit_vt_swap \
            -verbose
    } failure options]} {
        write_db "$::env(NSSOC_RESIZER_OUT)/setup-unchecked.odb"
        write_verilog "$::env(NSSOC_RESIZER_OUT)/setup-unchecked.v"
        return -options $options $failure
    }
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
    # Preserve the real native result even if a later acceptance gate rejects it.
    write_db "$::env(NSSOC_RESIZER_OUT)/hold-unchecked.odb"
    write_verilog "$::env(NSSOC_RESIZER_OUT)/hold-unchecked.v"
    # Positive delay cells have X=A in the pinned Liberty, like ordinary buffers.
    # Enable/tri-state buffers and arbitrary added logic remain forbidden.
    # New delay buffers need real supply nets in addition to signal equations.
    foreach inst [$block getInsts] {
        set n [$inst getName]
        if {[info exists original_master($n)]} {continue}
        if {![regexp {^sg13g2_(buf_(1|2|4|8|16)|dlygate4sd[123]_1)$} [[$inst getMaster] getName]]} {
            error "Unexpected new master in hold repair: $n / [[$inst getMaster] getName]"
        }
        foreach {pin_name net_name} {VDD VPWR VSS VGND} {
            set pin [$inst findITerm $pin_name]
            set net [$block findNet $net_name]
            if {$pin eq "NULL" || $net eq "NULL"} {error "Missing new buffer supply: $n pin=$pin_name net=$net_name"}
            set prior [$pin getNet]
            if {$prior eq "NULL"} {$pin connect $net}
            if {[$pin getNet] ne $net} {error "New buffer supply connected to wrong net"}
        }
    }
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
