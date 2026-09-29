# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Run in a fresh process against an immutable copied checkpoint. The controller
# must pin this file, the selected helper, libraries, SDC and checkpoint inputs.

proc nssoc_experiment_measure {phase profile} {
    if {$phase ni {before after}} {error "Invalid measurement phase: $phase"}
    set prefix [file join $::env(STEP_DIR) "experiment-$phase"]
    report_checks -path_delay max -group_path_count 10 \
        -fields {fanout cap slew} -digits 6 > "$prefix-setup.rpt"
    report_checks -path_delay min -group_path_count 10 \
        -fields {fanout cap slew} -digits 6 > "$prefix-hold.rpt"
    report_check_types -max_slew -max_cap -violators -digits 6 \
        > "$prefix-electrical.rpt"

    set label [string toupper $phase]
    foreach {kind flag} {SETUP -max HOLD -min} {
        puts "EXPERIMENT_${label}_${kind}_WNS_BEGIN"
        report_worst_slack $flag -digits 6
        puts "EXPERIMENT_${label}_${kind}_WNS_END"
        puts "EXPERIMENT_${label}_${kind}_TNS_BEGIN"
        report_tns $flag -digits 6
        puts "EXPERIMENT_${label}_${kind}_TNS_END"
    }
    puts "EXPERIMENT_${label}_AREA_BEGIN"
    report_design_area
    puts "EXPERIMENT_${label}_AREA_END"

    # The public STA getters return the configured user time unit. Convert
    # explicitly rather than assuming every selected Liberty library uses ns.
    set ns_per_unit [expr {[sta::unit_scale time] * 1.0e9}]
    set numbers [dict create \
        setup_wns_ns [expr {[sta::worst_slack -max] * $ns_per_unit}] \
        hold_wns_ns [expr {[sta::worst_slack -min] * $ns_per_unit}] \
        setup_tns_ns [expr {[sta::total_negative_slack -max] * $ns_per_unit}] \
        hold_tns_ns [expr {[sta::total_negative_slack -min] * $ns_per_unit}] \
        setup_violating_endpoints [sta::endpoint_violation_count max] \
        hold_violating_endpoints [sta::endpoint_violation_count min] \
        slew_violations [sta::max_slew_violation_count] \
        capacitance_violations [sta::max_capacitance_violation_count] \
        instance_count [llength [[ord::get_db_block] getInsts]] \
        area_um2 [expr {[rsz::design_area] * 1.0e12}] \
        utilization_fraction [rsz::utilization]]
    set stream [open "$prefix.json" w]
    puts $stream "\{"
    puts $stream "  \"profile\": \"$profile\","
    puts $stream "  \"phase\": \"$phase\","
    puts $stream "  \"parasitics\": \"global_route_estimates\","
    puts $stream "  \"signoff\": false,"
    set pairs [list]
    dict for {key value} $numbers {
        if {![string is double -strict $value] || !($value < 1.0e30 && $value > -1.0e30)} {
            close $stream
            error "Non-finite or unavailable timing measurement $key=$value"
        }
        lappend pairs "  \"$key\": $value"
    }
    puts $stream [join $pairs ",\n"]
    puts $stream "\}"
    close $stream
}

proc nssoc_experiment_same_files {first second} {
    set a [open $first rb]
    set b [open $second rb]
    set same 1
    while {1} {
        set left [read $a 1048576]
        set right [read $b 1048576]
        if {$left ne $right} {set same 0; break}
        if {[eof $a] && [eof $b]} {break}
    }
    close $a
    close $b
    return $same
}

if {![info exists ::env(NSSOC_TIMING_EXPERIMENT_PROFILE)]} {
    error "NSSOC_TIMING_EXPERIMENT_PROFILE is required"
}
set profile $::env(NSSOC_TIMING_EXPERIMENT_PROFILE)
if {$profile ni {setup_baseline setup_batch4 hold_guarded critical_xnor}} {
    error "Unknown NSSOC timing experiment: $profile"
}
set recipe [file join [file dirname [info script]] timing_repair_experiment.tcl]
if {$profile eq "critical_xnor"} {
    if {![info exists ::env(NSSOC_CRITICAL_PLACEMENT_SCRIPT)]} {
        error "NSSOC_CRITICAL_PLACEMENT_SCRIPT is required"
    }
    set recipe $::env(NSSOC_CRITICAL_PLACEMENT_SCRIPT)
}
if {![file isfile $recipe]} {error "Missing immutable experiment helper: $recipe"}

source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl
read_current_odb
set_thread_count 2
set_propagated_clock [all_clocks]
set_dont_touch_objects
report_units
write_sdc -no_timestamp $::env(STEP_DIR)/experiment-before.sdc

set macro_snapshots [dict create]
foreach inst [[ord::get_db_block] getInsts] {
    if {[[$inst getMaster] getName] in {SP6TSRAM512x64 DP8TSRAMDP256x16}} {
        dict set macro_snapshots [$inst getName] \
            [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]
        $inst setPlacementStatus FIRM
    }
}
if {[dict size $macro_snapshots] != 32} {error "Expected exactly 32 actual SRAM macros"}
remove_fillers
write_verilog $::env(STEP_DIR)/before.nl.v

# All profiles receive the same initial GRT and legalization sequence. Keep the
# baseline/batch4 preparation identical to the existing checkpointed controller,
# without repeating whole-chip electrical repair or changing timing constraints.
foreach net [[ord::get_db_block] getNets] {
    set wire [$net getWire]
    if {$wire ne "NULL"} {odb::dbWire_destroy $wire}
}
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
estimate_parasitics -global_routing
global_route -start_incremental
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
global_route -end_incremental
estimate_parasitics -global_routing
nssoc_experiment_measure before $profile

puts "EXPERIMENT_REPAIR_BEGIN $profile"
set repair_started_ms [clock milliseconds]
source $recipe
global_route -start_incremental
if {$profile eq "critical_xnor"} {
    write_verilog $::env(STEP_DIR)/critical-placement-before.nl.v
    nssoc_apply_critical_placement
} else {
    nssoc_timing_experiment $profile
}
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
if {$profile eq "critical_xnor"} {
    nssoc_verify_critical_placement
    write_verilog $::env(STEP_DIR)/critical-placement-after.nl.v
    if {![nssoc_experiment_same_files \
            $::env(STEP_DIR)/critical-placement-before.nl.v \
            $::env(STEP_DIR)/critical-placement-after.nl.v]} {
        error "Placement-only candidate changed the native logical netlist"
    }
    puts "CRITICAL_PLACEMENT_NATIVE_NETLIST_BYTE_IDENTICAL"
}
global_route -end_incremental
estimate_parasitics -global_routing
puts "EXPERIMENT_REPAIR_ELAPSED_SECONDS [expr {([clock milliseconds] - $repair_started_ms) / 1000.0}]"
puts "EXPERIMENT_REPAIR_END $profile"
nssoc_experiment_measure after $profile

set seen_macros 0
foreach inst [[ord::get_db_block] getInsts] {
    if {[dict exists $macro_snapshots [$inst getName]]} {
        incr seen_macros
        set original [dict get $macro_snapshots [$inst getName]]
        set actual [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]
        if {$actual ne $original} {error "Hard macro changed: [$inst getName]"}
    } elseif {[[$inst getMaster] getName] in {SP6TSRAM512x64 DP8TSRAMDP256x16}} {
        error "Unexpected SRAM instance: [$inst getName]"
    }
}
if {$seen_macros != 32} {error "An original SRAM instance was removed"}
puts "ALL_32_HARD_MACRO_MASTERS_LOCATIONS_ORIENTATIONS_PRESERVED"
write_sdc -no_timestamp $::env(STEP_DIR)/experiment-after.sdc
if {![nssoc_experiment_same_files \
        $::env(STEP_DIR)/experiment-before.sdc \
        $::env(STEP_DIR)/experiment-after.sdc]} {
    error "The timing experiment changed the native timing constraints"
}
puts "EXPERIMENT_NATIVE_TIMING_CONSTRAINTS_BYTE_IDENTICAL"
write_views
puts "EXPERIMENT_COMPLETE_REQUIRES_ROUTING_RCX_STA_EQUIVALENCE $profile"
