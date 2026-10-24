# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# A bounded diagnostic experiment. Never emits an accepted physical candidate.
foreach key {STEP_DIR SCRIPTS_DIR NSSOC_HOLD_DIAGNOSTIC_HELPER NSSOC_TARGETED_METHOD_ROOT} {
    if {![info exists ::env($key)]} {error "$key is required"}
}
source $::env(NSSOC_HOLD_DIAGNOSTIC_HELPER)
source [file join $::env(NSSOC_TARGETED_METHOD_ROOT) hw/soc/pnr/timing_targeted_hold_probe_helpers.tcl]
# Separate exact native executable, tiny fixture first; failure forbids C10 load.
nssoc_targeted_native_gate
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
proc nssoc_targeted_probe_stage {name} {
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
nssoc_targeted_probe_stage matched_before
set baseline [nssoc_targeted_assert_baseline [sta::endpoint_path_count] \
    [sta::endpoint_violation_count min] [dict keys [nssoc_hold_corners]]]

# Reuse the separately pinned existing profile exactly: 16 negative endpoints,
# one native pass each, setup0.1ns/hold0.15ns and fixed global growth budget.
source [file join $::env(NSSOC_TARGETED_METHOD_ROOT) hw/soc/pnr/timing_repair_experiment.tcl]
set initial_instances [llength [[ord::get_db_block] getInsts]]
set growth_budget [expr {int(floor(0.4 * $initial_instances))}]
global_route -start_incremental
set started_ms [clock milliseconds]
puts "NSSOC_TARGETED_HOLD_PROBE_REPAIR_BEGIN"
nssoc_timing_experiment hold_guarded_targeted
set finished_ms [clock milliseconds]
puts "NSSOC_TARGETED_HOLD_PROBE_REPAIR_END"
set actual_instances [llength [[ord::get_db_block] getInsts]]
set growth [expr {$actual_instances-$initial_instances}]
set selection [nssoc_targeted_read [file join $::env(STEP_DIR) hold-targeted-selection.tcldict]]
set result [nssoc_targeted_read [file join $::env(STEP_DIR) hold-targeted-result.tcldict]]
set invocation [dict create profile [nssoc_hold_jstr hold_guarded_targeted] call_count 1 \
    endpoint_limit 16 max_passes_per_endpoint 1 setup_margin_ns 0.1 hold_margin_ns 0.15 \
    allow_setup_violations false started_ms $started_ms finished_ms $finished_ms \
    elapsed_ms [expr {$finished_ms-$started_ms}] \
    initial_instance_count $initial_instances actual_instance_count $actual_instances \
    global_instance_growth_budget $growth_budget actual_instance_growth $growth \
    selection [nssoc_targeted_selection_json $selection] result [nssoc_targeted_result_json $result] \
    selection_sha256 [nssoc_hold_jstr [nssoc_hold_sha [file join $::env(STEP_DIR) hold-targeted-selection.tcldict]]] \
    result_sha256 [nssoc_hold_jstr [nssoc_hold_sha [file join $::env(STEP_DIR) hold-targeted-result.tcldict]]] \
    remaining_margin_repair_required true]
nssoc_hold_write_json [file join $::env(STEP_DIR) repair-invocation.json] [nssoc_hold_jobject $invocation]
if {$growth < 0 || $growth > $growth_budget} {error "Targeted probe net-instance-growth budget violated"}

# These read-only getters expose the native post-repair cached state before
# legalization/end-incremental/reestimation. Routes are explicitly provisional;
# this stage is never an accepted routed output or a matched-final comparison.
nssoc_targeted_probe_stage after_repair_native
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
global_route -end_incremental
estimate_parasitics -global_routing
nssoc_targeted_probe_stage after_hold
sta::delays_invalid
sta::find_timing -full_update
nssoc_targeted_probe_stage after_full_update
nssoc_hold_assert_same_physical [dict get $snapshots after_hold] [dict get $snapshots after_full_update]

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
if {$final_growth < 0 || $final_growth > $growth_budget} {error "Final targeted probe net-instance-growth budget violated"}
set buffer_budget [dict create initial_instance_count $initial_instances global_buffer_budget $growth_budget \
    after_repair_instance_count $actual_instances final_instance_count $final_instances \
    maximum_observed_growth [expr {max($growth,$final_growth)}] within_budget true]
set constraints {}
set sdc_files {}
foreach name [dict keys $snapshots] {
    lappend constraints [dict get $snapshots $name fingerprints constraints]
    lappend sdc_files [nssoc_hold_jstr "$name/constraints.sdc"]
}
if {[llength [lsort -unique $constraints]] != 1} {error "Targeted hold diagnostic changed timing constraints"}
set receipt [nssoc_hold_jobject [dict create schema 1 status [nssoc_hold_jstr COMPLETE_DIAGNOSTIC_ONLY] \
    timing_accepted false candidate_adopted false manufacturing_approval false thresholds_changed false \
    all_endpoint_coverage true source_sram_macros_preserved 32 sram_macro_count 32 sram_placement_preserved true \
    time_unit_seconds [nssoc_hold_assert_units [sta::unit_scale time]] \
    native_time_unit_seconds [nssoc_hold_number [sta::unit_scale time]] \
    time_unit_representation [nssoc_hold_jstr {IEEE-754 binary32 promoted to Tcl double}] value_units [nssoc_hold_jstr seconds] \
    matched_before_census [nssoc_hold_jobject $baseline] \
    repair_invocation [nssoc_hold_jobject $invocation] timing_metrics [nssoc_hold_jobject $measurements] \
    buffer_budget [nssoc_hold_jobject $buffer_budget] provisional_stages {["after_repair_native"]} \
    stage_scope [nssoc_hold_jobject [dict create \
        matched_before [nssoc_hold_jstr {Same C10 GRT/DPL preparation as the frozen setup A/B experiment.}] \
        after_repair_native [nssoc_hold_jstr {Provisional native cache, route and placement after repair before DPL/end-incremental/RC reestimation.}] \
        after_hold [nssoc_hold_jstr {After normal DPL/end-incremental/RC reestimation.}] \
        after_full_update [nssoc_hold_jstr {Same physical state as after_hold; timing caches fully recomputed.}]]] \
    sdc_files "\[[join $sdc_files ,]\]" stages "\[[join $stages ,]\]" \
    scope [nssoc_hold_jstr {Existing 16-target hold profile and complete endpoint diagnosis only; margins and guards unchanged. No accepted candidate, resumable ODB or final timing/signoff.}]]]
nssoc_hold_write_json [file join $::env(STEP_DIR) targeted-hold-probe.json] $receipt
puts "NSSOC_TARGETED_HOLD_PROBE_COMPLETE_NO_ADOPTION"
