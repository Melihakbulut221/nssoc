# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Post-route hold repair of the routed timing measurement
# (docs/combined-timing.md section 12; step NSSOC.PostRouteHold of
# hw/soc/pnr/routed_measure_flow.py).
#
# On the detail-routed database: the routed wires are extracted with the
# flow's nominal OpenRCX rules (the rules AuditedRCX uses) and annotated in
# every corner, and the resizer inserts hold buffers with setup protected
# (-setup_margin 0: a buffer may use positive setup slack only). Existing
# instances keep their master, place and orientation: every library cell
# but the hold buffer cells is dont_use, any original instance whose
# master changed anyway is swapped back, and the originals are FIRM while
# the new buffers are legalized. Exactly the nets connected to a new
# buffer (or to an original instance that moved, if the held legalization
# fails) lose their wires, and the detailed routing step that follows
# routes them; no existing pin moves, so every other wire stays valid.
# The resizer re-estimates the nets it changes from global routes kept in
# memory (a fresh global_route, needed for its incremental mode); every
# other net keeps its extracted parasitics. Clocks, SDC,
# corners and derates are the flow's own; nothing here is acceptance: the
# routed database is extracted and timed again afterwards (AuditedRCX,
# AuditedRoutedSTA).
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl

read_current_odb
set_propagated_clock [all_clocks]
foreach {name period} {clk_i 20 pcie_clk_i 4 eth_rx_clk_i 8 eth_tx_clk_i 8} {
    set clock [get_clocks $name]
    if {[llength $clock] != 1 || abs([get_property $clock period]-$period)>1e-9} {
        error "Original routed clock budget changed: $name"
    }
}
foreach clock [all_clocks] {
    if {![get_property $clock is_propagated]} {error "Post-route hold repair has an ideal clock"}
}
puts "NSSOC_HOLD_ORIGINAL_CLOCKS_PROPAGATED"
if {[catch {design_is_routed} routed]} {set routed unknown}
puts "NSSOC_HOLD_DESIGN_ROUTED $routed"

set_dont_touch_objects
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl

# Global routes in memory, for the resizer's incremental re-estimation of
# the nets it changes and for the incremental route after legalization.
source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl

# Extract the routed wires and annotate every corner with them.
set rcx_flags [list]
if { !$::env(RCX_MERGE_VIA_WIRE_RES) } {
    lappend rcx_flags -no_merge_via_res
}
puts "NSSOC_HOLD_RCX_RULES $::env(NSSOC_RCX_RULESET)"
define_process_corner -ext_model_index 0 CURRENT_CORNER
log_cmd extract_parasitics {*}$rcx_flags -ext_model_file $::env(NSSOC_RCX_RULESET) -lef_res
set spef $::env(STEP_DIR)/pre-hold.spef
write_spef $spef
foreach corner [lln::get_corner_names] {
    read_spef -corner $corner $spef
}
catch {est::set_parasitics_src "detailed_routing"}

proc nssoc_hold_report {tag} {
    # report_checks -corner is the form the probe's corner STA uses.
    foreach corner [lln::get_corner_names] {
        foreach kind {min max} {
            puts "NSSOC_HOLD_REPORT $tag $corner $kind"
            if {[catch {report_checks -corner $corner -path_delay $kind -group_path_count 1 -format end -digits 3} err]} {
                puts "NSSOC_HOLD_REPORT_FAILED $tag $corner $kind: $err"
            }
        }
    }
    foreach kind {min max} {
        if {![catch {sta::endpoint_violation_count $kind} n]} {
            puts "NSSOC_HOLD_VIOLATING_ENDPOINTS $tag $kind $n"
        }
    }
}

# Hold-violating endpoint count only. The per-path breakdown by setup slack
# used get_property on path ends, which crashes this OpenROAD build (signal 11
# in sta::Properties::getProperty(PathEnd*)), so it is not computed here.
proc nssoc_hold_census {tag} {
    if {[catch {find_timing_paths -path_delay min -group_path_count 100000 -endpoint_path_count 1 -slack_max 0} ends]} {
        puts "NSSOC_HOLD_CENSUS_FAILED $tag: $ends"
        return
    }
    puts "NSSOC_HOLD_CENSUS $tag hold_violating=[llength $ends]"
}

set block [ord::get_db_block]
set db [ord::get_db]
array set before_master {}
array set before_place {}
foreach inst [$block getInsts] {
    set n [$inst getName]
    set before_master($n) [[$inst getMaster] getName]
    set before_place($n) [list [$inst getLocation] [$inst getOrient]]
}
set before_count [llength [$block getInsts]]
nssoc_hold_report extracted-before
nssoc_hold_census extracted-before

# Only hold buffer cells may be chosen, so no existing instance can be
# resized to another master (the first measurement resized 371).
set hold_cells {sg13g2_dlygate4sd1_1 sg13g2_dlygate4sd2_1 sg13g2_dlygate4sd3_1 sg13g2_buf_1 sg13g2_buf_2}
set_dont_use [get_lib_cells */*]
foreach cell $hold_cells {
    set lib_cells [get_lib_cells -quiet */$cell]
    if {[llength $lib_cells] == 0} {error "Missing hold buffer cell $cell"}
    unset_dont_use $lib_cells
}
puts "NSSOC_HOLD_CELLS $hold_cells"

set hold_args [list]
lappend hold_args -verbose
lappend hold_args -hold
lappend hold_args -setup_margin 0
lappend hold_args -hold_margin $::env(NSSOC_POST_ROUTE_HOLD_MARGIN)
lappend hold_args -max_buffer_percent $::env(NSSOC_POST_ROUTE_HOLD_MAX_BUFFER_PCT)
lappend hold_args -skip_pin_swap -skip_gate_cloning -skip_size_down -skip_buffer_removal
log_cmd repair_timing {*}$hold_args

# Any original instance whose master changed regardless is swapped back.
set new_insts [list]
set reverted 0
foreach inst [$block getInsts] {
    set n [$inst getName]
    if {![info exists before_master($n)]} {
        lappend new_insts $inst
    } elseif {$before_master($n) ne [[$inst getMaster] getName]} {
        set master [$db findMaster $before_master($n)]
        if {$master eq "NULL" || ![$inst swapMaster $master]} {
            error "Cannot restore the master of $n ($before_master($n))"
        }
        incr reverted
    }
}
set new_masters [dict create]
foreach inst $new_insts {dict incr new_masters [[$inst getMaster] getName]}
puts "NSSOC_HOLD_INSTANCES before=$before_count after=[llength [$block getInsts]] new=[llength $new_insts] masters_restored=$reverted new_masters=$new_masters"
nssoc_hold_census after-repair

# Legalize the new buffers with every original placed instance FIRM. If
# that cannot be legalized, the flow's ordinary legalization runs instead,
# and the nets of every original instance that moved are rerouted too.
global_route -start_incremental
source $::env(SCRIPTS_DIR)/openroad/common/dpl_cell_pad.tcl
set held [list]
foreach inst [$block getInsts] {
    if {[$inst getPlacementStatus] eq "PLACED" && [info exists before_master([$inst getName])]} {
        $inst setPlacementStatus FIRM
        lappend held $inst
    }
}
set dpl_args [list -max_displacement [subst { $::env(PL_MAX_DISPLACEMENT_X) $::env(PL_MAX_DISPLACEMENT_Y) }]]
if {[catch {log_cmd detailed_placement {*}$dpl_args} err]} {
    puts "NSSOC_HOLD_LEGALIZE_HELD_FAILED $err"
    foreach inst $held {$inst setPlacementStatus PLACED}
    set held [list]
    log_cmd detailed_placement {*}$dpl_args
    puts "NSSOC_HOLD_LEGALIZE all_movable"
} else {
    puts "NSSOC_HOLD_LEGALIZE originals_held=[llength $held]"
}
foreach inst $held {$inst setPlacementStatus PLACED}
check_placement -verbose
set arg_list [list]
append_if_flag arg_list GRT_ALLOW_CONGESTION -allow_congestion
log_cmd global_route -end_incremental {*}$arg_list
unset_dont_touch_objects

# Remove the wires of exactly the nets the repair changed: every signal net
# on a new buffer, and every signal net on an original instance that moved.
set touched [list]
foreach inst $new_insts {lappend touched $inst}
set moved 0
foreach inst [$block getInsts] {
    set n [$inst getName]
    if {[info exists before_place($n)]
        && $before_place($n) ne [list [$inst getLocation] [$inst getOrient]]} {
        lappend touched $inst
        incr moved
    }
}
array set rip {}
foreach inst $touched {
    foreach iterm [$inst getITerms] {
        set net [$iterm getNet]
        if {$net eq "NULL"} {continue}
        if {[$net getSigType] in {POWER GROUND}} {continue}
        set rip([$net getName]) $net
    }
}
set wires 0
foreach name [array names rip] {
    set wire [$rip($name) getWire]
    if {$wire ne "NULL"} {
        odb::dbWire_destroy $wire
        incr wires
    }
}
puts "NSSOC_HOLD_REROUTE nets=[array size rip] wires_removed=$wires originals_moved=$moved"
# The next step (NSSOC.RemoveNonOrthogonalWires) removes any wire these
# nets carry in the written database, and any wire with a non-orthogonal
# segment on any net, before detailed routing.
set f [open [file join [file dirname $::env(STEP_DIR)] post-route-hold-nets.txt] w]
foreach name [lsort [array names rip]] {puts $f $name}
close $f

nssoc_hold_report estimated-after
set still 0
foreach name [array names rip] {
    if {[$rip($name) getWire] ne "NULL"} {incr still}
}
puts "NSSOC_HOLD_DONE changed_nets_with_wires=$still"

write_views
