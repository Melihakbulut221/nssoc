# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Repair/export isolated state. Rejected timing is retained; never auto-adopted.
source $::env(NSSOC_HOLD_DIAGNOSTIC_HELPER)
set methods $::env(NSSOC_TARGETED_METHOD_ROOT)
source [file join $methods hw/soc/pnr/timing_targeted_hold_probe_helpers.tcl]
source [file join $methods hw/soc/pnr/timing_combined_repair_helpers.tcl]
# Load the pinned environment and I/O procedure definitions before consulting
# CURRENT_ODB/_SDC_IN. These sources do not load the chip database.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl
nssoc_targeted_native_gate
# Prove the same inherited LibreLane environment and child entry can load an
# ODB/SDC before spending the measured ~74 minutes on full-chip setup repair.
set root $::env(STEP_DIR)
set original_odb $::env(CURRENT_ODB)
set original_sdc $::env(_SDC_IN)
set ::env(NSSOC_COMBINED_ROOT) $root
set ::env(NSSOC_COMBINED_PARENT_PID) [pid]
set ::env(NSSOC_COMBINED_RELOAD_STAGE) startup_control
set ::env(CURRENT_ODB) [file join $::env(NSSOC_TARGETED_CONTROL_OUT) tiny-after.odb]
set ::env(_SDC_IN) [file join $::env(NSSOC_TARGETED_CONTROL_OUT) after.sdc]
set ::env(NSSOC_COMBINED_ODB_SHA) [nssoc_hold_sha $::env(CURRENT_ODB)]
set ::env(NSSOC_COMBINED_SDC_SHA) [nssoc_hold_sha $::env(_SDC_IN)]
exec [info nameofexecutable] -exit [file join $methods hw/soc/pnr/timing_combined_reload.tcl] \
    > [file join $root startup-control.log] 2>@1
set ::env(CURRENT_ODB) $original_odb
set ::env(_SDC_IN) $original_sdc
puts NSSOC_COMBINED_STARTUP_CONTROL_PASS_BEFORE_C10_LOAD
read_current_odb
set_thread_count 2
set_propagated_clock [all_clocks]
set_dont_touch_objects
set root $::env(STEP_DIR)
set macros [nssoc_combined_macros]
nssoc_combined_prepare $root source
set before [nssoc_combined_record $root matched_before true]
set baseline [nssoc_targeted_assert_baseline [sta::endpoint_path_count] \
    [sta::endpoint_violation_count min] [dict keys [nssoc_hold_corners]]]
set initial [dict get $before instance_count]
set budget [expr {int(floor(0.4*$initial))}]
source [file join $methods hw/soc/pnr/timing_repair_experiment.tcl]
# Preserve the original per-batch guard, and additionally enforce ONE original
# chip budget before/after every endpoint across all subsequent hold batches.
rename nssoc_hold_check_batch_budget nssoc_combined_original_batch_budget
proc nssoc_hold_check_batch_budget {args} {
    global initial budget
    nssoc_combined_budget $initial $budget [llength [[ord::get_db_block] getInsts]]
    set result [nssoc_combined_original_batch_budget {*}$args]
    nssoc_combined_budget $initial $budget [llength [[ord::get_db_block] getInsts]]
    return $result
}
set setup_started [clock milliseconds]
puts NSSOC_COMBINED_SETUP_BATCH4_BEGIN
global_route -start_incremental
nssoc_timing_experiment setup_batch4
nssoc_combined_refresh
set setup_finished [clock milliseconds]
puts NSSOC_COMBINED_SETUP_BATCH4_END
set current [nssoc_combined_record $root after_setup]
nssoc_combined_budget $initial $budget [dict get $current instance_count]
set batches {}
set stop_reason FOUR_BATCH_LIMIT
for {set index 1} {$index <= 4} {incr index} {
    if {[dict get $current hold_violating_endpoints] == 0} {set stop_reason NO_NEGATIVE_HOLD; break}
    if {[nssoc_combined_budget $initial $budget [dict get $current instance_count]] == 0} {
        set stop_reason ORIGINAL_GROWTH_BUDGET_EXHAUSTED; break
    }
    set name hold_batch_$index
    set directory [file join $root $name]
    file mkdir $directory
    set batch_before $current
    set ::env(STEP_DIR) $directory
    global_route -start_incremental
    set started [clock milliseconds]
    puts "NSSOC_COMBINED_HOLD_BEGIN $index"
    try {nssoc_timing_experiment hold_guarded_targeted} finally {set ::env(STEP_DIR) $root}
    set finished [clock milliseconds]
    puts "NSSOC_COMBINED_HOLD_END $index"
    nssoc_combined_refresh
    set current [nssoc_combined_record $root $name]
    nssoc_combined_budget $initial $budget [dict get $current instance_count]
    set selection [nssoc_targeted_read [file join $directory hold-targeted-selection.tcldict]]
    set result [nssoc_targeted_read [file join $directory hold-targeted-result.tcldict]]
    set record [nssoc_hold_jobject [dict create index $index started_ms $started finished_ms $finished \
        before [nssoc_hold_jobject $batch_before] after [nssoc_hold_jobject $current] \
        selection [nssoc_targeted_selection_json $selection] result [nssoc_targeted_result_json $result] \
        selection_sha256 [nssoc_hold_jstr [nssoc_hold_sha [file join $directory hold-targeted-selection.tcldict]]] \
        result_sha256 [nssoc_hold_jstr [nssoc_hold_sha [file join $directory hold-targeted-result.tcldict]]]]]
    nssoc_hold_write_json [file join $directory invocation.json] $record
    lappend batches $record
    if {![nssoc_combined_hold_progress $batch_before $current]} {set stop_reason NO_HOLD_PROGRESS; break}
}
source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl
set_global_connections
sta::delays_invalid
sta::find_timing -full_update
set after [nssoc_combined_record $root after_hold true]
if {[nssoc_combined_macros] ne $macros} {error "Repair changed SRAM master/location/orientation"}
nssoc_combined_budget $initial $budget [dict get $after instance_count]
set candidate [file join $root candidate]
file mkdir $candidate
write_db [file join $candidate soc_top.odb]
write_def [file join $candidate soc_top.def]
write_sdc -no_timestamp [file join $candidate soc_top.sdc]
write_verilog [file join $candidate soc_top.v]
set candidate_pins {}
foreach suffix {odb def sdc v} {dict set candidate_pins soc_top.$suffix [nssoc_combined_pin [file join $candidate soc_top.$suffix]]}
set ::env(NSSOC_COMBINED_ROOT) $root
set ::env(NSSOC_COMBINED_PARENT_PID) [pid]
set ::env(NSSOC_COMBINED_ODB_SHA) [nssoc_hold_sha [file join $candidate soc_top.odb]]
set ::env(NSSOC_COMBINED_SDC_SHA) [nssoc_hold_sha [file join $candidate soc_top.sdc]]
set original_odb $::env(CURRENT_ODB)
set original_sdc $::env(_SDC_IN)
set reloads {}
foreach name {reload_first reload_repeat} {
    nssoc_hold_write_json [file join $root "$name-headroom.json"] [nssoc_hold_jobject [nssoc_combined_headroom]]
    set directory [file join $root $name-process]
    file mkdir $directory
    set ::env(STEP_DIR) $directory
    set ::env(CURRENT_ODB) [file join $candidate soc_top.odb]
    set ::env(_SDC_IN) [file join $candidate soc_top.sdc]
    set ::env(NSSOC_COMBINED_RELOAD_STAGE) $name
    # exec waits for healthy native work. No elapsed watchdog or cancellation.
    set command [list [info nameofexecutable] -exit [file join $methods hw/soc/pnr/timing_combined_reload.tcl]]
    set code [catch {exec {*}$command > [file join $root "$name.log"] 2>@1} message]
    set ::env(STEP_DIR) $root
    set ::env(CURRENT_ODB) $original_odb
    set ::env(_SDC_IN) $original_sdc
    if {$code} {error "Independent reload failed ($name): $message"}
    lappend reloads [nssoc_combined_read [file join $root "$name-process.json"]]
}
foreach suffix {odb def sdc v} {
    if {[nssoc_combined_pin [file join $candidate soc_top.$suffix]] ne [dict get $candidate_pins soc_top.$suffix]} {
        error "Candidate changed during reload"
    }
}
set stages {}
set metrics {}
foreach name {matched_before after_hold reload_first reload_repeat} {
    lappend stages [nssoc_combined_read [file join $root "$name-stage.json"]]
    dict set metrics $name [nssoc_combined_read [file join $root "$name-metrics.json"]]
}
nssoc_hold_write_json [file join $root combined-repair.json] [nssoc_hold_jobject [dict create \
    schema 1 status [nssoc_hold_jstr COMPLETE_DIAGNOSTIC_ONLY] \
    candidate_adopted false timing_accepted false manufacturing_approval false thresholds_changed false \
    matched_before_census [nssoc_hold_jobject $baseline] initial_instance_count $initial global_buffer_budget $budget \
    setup_profile [nssoc_hold_jstr setup_batch4] setup_call_count 1 setup_started_ms $setup_started setup_finished_ms $setup_finished \
    hold_batch_limit 4 hold_stop_reason [nssoc_hold_jstr $stop_reason] hold_batches "\[[join $batches ,]\]" \
    sram_macro_count 32 sram_placement_preserved true candidate_files [nssoc_hold_jobject $candidate_pins] \
    stages "\[[join $stages ,]\]" timing_metrics [nssoc_hold_jobject $metrics] \
    independent_reload_processes "\[[join $reloads ,]\]" \
    source_checkpoint_preserved true estimated_global_route_only true]]
puts NSSOC_COMBINED_REPAIR_COMPLETE_NO_ADOPTION
