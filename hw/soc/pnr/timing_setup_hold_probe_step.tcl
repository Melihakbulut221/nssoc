# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# A bounded diagnostic experiment. Never emits an accepted physical candidate.
foreach key {STEP_DIR SCRIPTS_DIR NSSOC_HOLD_DIAGNOSTIC_HELPER} {
    if {![info exists ::env($key)]} {error "$key is required"}
}
source $::env(NSSOC_HOLD_DIAGNOSTIC_HELPER)
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl
read_current_odb
set_thread_count 2
set_propagated_clock [all_clocks]
set_dont_touch_objects
report_units

set stages {}
set snapshots {}
set measurements {}
proc nssoc_setup_probe_stage {name} {
    global stages snapshots measurements
    # The shared snapshot records native TNS before endpoint enumeration.
    set snapshot [nssoc_hold_snapshot $name $::env(STEP_DIR)]
    lappend stages [dict get $snapshot json]
    dict set snapshots $name $snapshot
    set metrics [dict create recorded_ms [clock milliseconds] \
        setup_wns_seconds [nssoc_hold_number [sta::worst_slack_cmd max]] \
        hold_wns_seconds [nssoc_hold_number [sta::worst_slack_cmd min]] \
        setup_tns_seconds [nssoc_hold_number [sta::total_negative_slack_cmd max]] \
        hold_tns_seconds [nssoc_hold_number [sta::total_negative_slack_cmd min]] \
        setup_violating_endpoints [sta::endpoint_violation_count max] \
        hold_violating_endpoints [sta::endpoint_violation_count min] \
        slew_violations [sta::max_slew_violation_count] \
        capacitance_violations [sta::max_capacitance_violation_count] \
        instance_count [llength [[ord::get_db_block] getInsts]]]
    dict set measurements $name [nssoc_hold_jobject $metrics]
    report_checks -path_delay max -group_path_count 10 -fields {fanout cap slew} -digits 9 \
        > [file join $::env(STEP_DIR) "$name-setup.rpt"]
    report_check_types -max_slew -max_cap -violators -digits 9 \
        > [file join $::env(STEP_DIR) "$name-electrical.rpt"]
}

set macros {}
foreach inst [[ord::get_db_block] getInsts] {
    if {[[$inst getMaster] getName] in {SP6TSRAM512x64 DP8TSRAMDP256x16}} {
        dict set macros [$inst getName] [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]
        $inst setPlacementStatus FIRM
    }
}
if {[dict size $macros] != 32} {error "Expected exactly 32 source SRAM macros"}
remove_fillers
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
nssoc_setup_probe_stage matched_before

# Pinned RepairSetup.cc: max_passes is per endpoint; max_iterations is the
# global optimization-iteration budget. Disable post-loop sweeps explicitly.
# Up to four successful driver moves are attempted within the one iteration;
# each move can affect multiple cells. This is not a four-cell change limit.
# All work-budget differences from the old batch4 campaign are recorded below.
set repair_command [list repair_timing -setup -setup_margin 0.1 \
    -max_iterations 1 -max_passes 1 -max_repairs_per_pass 4 -repair_tns 100 \
    -max_buffer_percent 40 -skip_buffer_removal -skip_size_down \
    -skip_last_gasp -skip_crit_vt_swap -verbose]
set initial_instances [llength [[ord::get_db_block] getInsts]]
set growth_budget [expr {int(floor(0.4 * $initial_instances))}]
global_route -start_incremental
set started_ms [clock milliseconds]
puts "NSSOC_SETUP_HOLD_PROBE_REPAIR_BEGIN"
puts "NSSOC_SETUP_HOLD_PROBE_REPAIR_COMMAND $repair_command"
{*}$repair_command
set finished_ms [clock milliseconds]
puts "NSSOC_SETUP_HOLD_PROBE_REPAIR_END"
set actual_instances [llength [[ord::get_db_block] getInsts]]
set growth [expr {$actual_instances-$initial_instances}]
set argv_json {}
foreach word $repair_command {lappend argv_json [nssoc_hold_jstr $word]}
set invocation [dict create command "\[[join $argv_json ,]\]" call_count 1 \
    max_iterations 1 max_passes 1 max_repairs_per_pass 4 allow_setup_violations false \
    skip_last_gasp true skip_crit_vt_swap true \
    started_ms $started_ms finished_ms $finished_ms elapsed_ms [expr {$finished_ms-$started_ms}] \
    initial_instance_count $initial_instances actual_instance_count $actual_instances \
    global_instance_growth_budget $growth_budget actual_instance_growth $growth \
    native_setup_buffer_percentage_enforced false \
    granularity [nssoc_hold_jstr {One global endpoint optimization iteration, at most one endpoint pass, up to four successful driver moves; a move may mutate multiple cells. No post-loop last-gasp or critical-VT sweep.}] \
    work_budget_changes [nssoc_hold_jstr {Compared with frozen setup_batch4: max_iterations 100 to 1, max_passes default10000 to 1, skip_last_gasp and skip_crit_vt_swap enabled. Setup margin0.1ns and all physical acceptance thresholds unchanged.}] \
    growth_guard_scope [nssoc_hold_jstr {Pinned repair_timing forwards max_buffer_percent only to hold repair. This diagnostic adds a post-call net-instance-growth guard of floor(40% of initial instances); it is not a count of all inserted or transient cells. No accepted candidate is emitted.}]]
nssoc_hold_write_json [file join $::env(STEP_DIR) repair-invocation.json] [nssoc_hold_jobject $invocation]
if {$growth < 0 || $growth > $growth_budget} {error "Setup probe net-instance-growth budget violated"}

# These read-only getters expose the native post-repair cached state before
# legalization/end-incremental/reestimation. Routes are explicitly provisional;
# this stage is never an accepted routed output or a matched-final comparison.
nssoc_setup_probe_stage after_repair_native
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
global_route -end_incremental
estimate_parasitics -global_routing
nssoc_setup_probe_stage after_setup
sta::delays_invalid
sta::find_timing -full_update
nssoc_setup_probe_stage after_full_update
nssoc_hold_assert_same_physical [dict get $snapshots after_setup] [dict get $snapshots after_full_update]

set seen 0
foreach inst [[ord::get_db_block] getInsts] {
    if {[dict exists $macros [$inst getName]]} {
        incr seen
        if {[list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]] ne [dict get $macros [$inst getName]]} {
            error "Source SRAM master/location/orientation changed"
        }
    } elseif {[[$inst getMaster] getName] in {SP6TSRAM512x64 DP8TSRAMDP256x16}} {
        error "Unexpected SRAM instance added"
    }
}
if {$seen != 32} {error "Source SRAM instance removed"}
set final_instances [llength [[ord::get_db_block] getInsts]]
set final_growth [expr {$final_instances-$initial_instances}]
if {$final_growth < 0 || $final_growth > $growth_budget} {error "Final setup probe net-instance-growth budget violated"}
set buffer_budget [dict create initial_instance_count $initial_instances global_buffer_budget $growth_budget \
    after_repair_instance_count $actual_instances final_instance_count $final_instances \
    maximum_observed_growth [expr {max($growth,$final_growth)}] within_budget true]
set constraints {}
set sdc_files {}
foreach name [dict keys $snapshots] {
    lappend constraints [dict get $snapshots $name fingerprints constraints]
    lappend sdc_files [nssoc_hold_jstr "$name/constraints.sdc"]
}
if {[llength [lsort -unique $constraints]] != 1} {error "Setup diagnostic changed timing constraints"}
set receipt [nssoc_hold_jobject [dict create schema 1 status [nssoc_hold_jstr COMPLETE_DIAGNOSTIC_ONLY] \
    timing_accepted false candidate_adopted false manufacturing_approval false thresholds_changed false \
    all_endpoint_coverage true source_sram_macros_preserved 32 sram_macro_count 32 sram_placement_preserved true \
    time_unit_seconds [nssoc_hold_assert_units [sta::unit_scale time]] \
    native_time_unit_seconds [nssoc_hold_number [sta::unit_scale time]] \
    time_unit_representation [nssoc_hold_jstr {IEEE-754 binary32 promoted to Tcl double}] value_units [nssoc_hold_jstr seconds] \
    repair_invocation [nssoc_hold_jobject $invocation] timing_metrics [nssoc_hold_jobject $measurements] \
    buffer_budget [nssoc_hold_jobject $buffer_budget] provisional_stages {["after_repair_native"]} \
    stage_scope [nssoc_hold_jobject [dict create \
        matched_before [nssoc_hold_jstr {Same C10 GRT/DPL preparation as the frozen setup A/B experiment.}] \
        after_repair_native [nssoc_hold_jstr {Provisional native cache, route and placement after repair before DPL/end-incremental/RC reestimation.}] \
        after_setup [nssoc_hold_jstr {After normal DPL/end-incremental/RC reestimation.}] \
        after_full_update [nssoc_hold_jstr {Same physical state as after_setup; timing caches fully recomputed.}]]] \
    sdc_files "\[[join $sdc_files ,]\]" stages "\[[join $stages ,]\]" \
    scope [nssoc_hold_jstr {Bounded setup-repair arithmetic and complete hold-endpoint diagnosis only; native regression guards unchanged, no accepted candidate, no final timing/signoff.}]]]
nssoc_hold_write_json [file join $::env(STEP_DIR) setup-probe.json] $receipt
puts "NSSOC_SETUP_HOLD_PROBE_COMPLETE_NO_ADOPTION"
