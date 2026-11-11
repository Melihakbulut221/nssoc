# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Post-route hold repair of the routed timing measurement
# (docs/combined-timing.md section 12; step NSSOC.PostRouteHold of
# hw/soc/pnr/routed_measure_flow.py).
#
# On the detail-routed database: the routed wires are extracted with the
# flow's nominal OpenRCX rules (the rules AuditedRCX uses) and annotated in
# every corner, the resizer repairs hold with setup protected
# (-setup_margin 0, no setup violations allowed), the new buffers are
# legalized with every original instance kept in place, and the global
# routes of the changed nets are updated incrementally, so the detailed
# routing step that follows reconnects only what changed. The resizer
# re-estimates the nets it changes from the global routes it keeps in
# memory; every other net keeps its extracted parasitics. Clocks, SDC,
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
    foreach corner [lln::get_corner_names] {
        foreach kind {min max} {
            puts "NSSOC_HOLD_REPORT $tag $corner $kind"
            if {[catch {report_worst_slack -$kind -corner $corner -digits 3} err]} {
                puts "NSSOC_HOLD_REPORT_FAILED $err"
            }
        }
    }
    foreach kind {min max} {
        if {![catch {sta::endpoint_violation_count $kind} n]} {
            puts "NSSOC_HOLD_VIOLATING_ENDPOINTS $tag $kind $n"
        }
    }
}

set block [ord::get_db_block]
array set before_master {}
foreach inst [$block getInsts] {
    set before_master([$inst getName]) [[$inst getMaster] getName]
}
set before_count [llength [$block getInsts]]
nssoc_hold_report extracted-before

set hold_args [list]
lappend hold_args -verbose
lappend hold_args -hold
lappend hold_args -setup_margin 0
lappend hold_args -hold_margin $::env(NSSOC_POST_ROUTE_HOLD_MARGIN)
lappend hold_args -max_buffer_percent $::env(NSSOC_POST_ROUTE_HOLD_MAX_BUFFER_PCT)
log_cmd repair_timing {*}$hold_args

set after_count [llength [$block getInsts]]
set changed 0
foreach inst [$block getInsts] {
    set n [$inst getName]
    if {![info exists before_master($n)] || $before_master($n) ne [[$inst getMaster] getName]} {
        incr changed
    }
}
puts "NSSOC_HOLD_INSTANCES before=$before_count after=$after_count new_or_resized=$changed"

# Legalize. Only new and resized instances may move: every other placed
# instance is held FIRM, so its routed wires stay valid. If that cannot be
# legalized, the flow's ordinary legalization runs instead (any moved
# instance is rerouted by the incremental global and detailed routing).
global_route -start_incremental
source $::env(SCRIPTS_DIR)/openroad/common/dpl_cell_pad.tcl
set held [list]
foreach inst [$block getInsts] {
    set n [$inst getName]
    if {[$inst getPlacementStatus] eq "PLACED" && [info exists before_master($n)]
        && $before_master($n) eq [[$inst getMaster] getName]} {
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

nssoc_hold_report estimated-after
foreach corner [lln::get_corner_names] {
    puts "NSSOC_HOLD_WORST_HOLD_PATHS $corner"
    catch {report_checks -corner $corner -path_delay min -group_path_count 5 -format end -digits 3}
}
puts "NSSOC_HOLD_DONE"

write_views
