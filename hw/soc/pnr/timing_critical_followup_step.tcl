# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Hold diagnosis and sizing always load independent copies of the original candidate.
source $::env(NSSOC_HOLD_DIAGNOSTIC_HELPER)
set methods $::env(NSSOC_TARGETED_METHOD_ROOT)
set ::env(NSSOC_ELECTRICAL_ROOT) $methods
source [file join $methods hw/soc/pnr/timing_targeted_hold_probe_helpers.tcl]
source [file join $methods hw/soc/pnr/timing_combined_repair_helpers.tcl]
source [file join $methods hw/soc/pnr/timing_critical_followup_helpers.tcl]
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl
nssoc_targeted_native_gate
set root $::env(STEP_DIR)
set ::env(NSSOC_ELECTRICAL_ROOT) $methods
set ::env(NSSOC_CRITICAL_OUT) [file join $root sizing-control]
exec [info nameofexecutable] -exit [file join $methods sw/tests/timing_critical_followup_native.tcl] \
    > [file join $root sizing-control.log] 2>@1
set ::env(NSSOC_RESIDUAL_OUT) [file join $root residual-control]
exec [info nameofexecutable] -exit [file join $methods sw/tests/timing_residual_repair_native.tcl] \
    > [file join $root residual-control.log] 2>@1
puts NSSOC_CRITICAL_NATIVE_CONTROLS_PASS
set ::env(CURRENT_ODB) $::env(NSSOC_ELECTRICAL_CANDIDATE_ODB)
set ::env(_SDC_IN) $::env(NSSOC_ELECTRICAL_CANDIDATE_SDC)
if {[nssoc_hold_sha $::env(CURRENT_ODB)] ne $::env(NSSOC_ELECTRICAL_ODB_SHA) ||
    [nssoc_hold_sha $::env(_SDC_IN)] ne $::env(NSSOC_ELECTRICAL_SDC_SHA)} {error "Original candidate overlay changed"}
set original_odb $::env(CURRENT_ODB);set original_sdc $::env(_SDC_IN)
# The parent has loaded no chip yet; the diagnostic child exits before sizing.
set hold_root [file join $root hold-debug];file mkdir $hold_root
nssoc_hold_write_json [file join $hold_root headroom.json] [nssoc_hold_jobject [nssoc_combined_headroom]]
set ::env(NSSOC_COMBINED_ROOT) $hold_root
set ::env(NSSOC_COMBINED_PARENT_PID) [pid]
set ::env(NSSOC_COMBINED_ODB_SHA) $::env(NSSOC_ELECTRICAL_ODB_SHA)
set ::env(NSSOC_COMBINED_SDC_SHA) $::env(NSSOC_ELECTRICAL_SDC_SHA)
set ::env(NSSOC_COMBINED_RELOAD_STAGE) reload_first
set ::env(STEP_DIR) [file join $hold_root process];file mkdir $::env(STEP_DIR)
set code [catch {exec [info nameofexecutable] -exit [file join $methods hw/soc/pnr/timing_critical_hold_child.tcl] \
    > [file join $hold_root native.log] 2>@1} message]
set ::env(STEP_DIR) $root
if {$code} {error "Isolated hold diagnostic failed: $message"}
puts NSSOC_CRITICAL_HOLD_CHILD_EXITED_BEFORE_SIZING
# Reassert the untouched source views, never the hold child's exported ODB.
set ::env(CURRENT_ODB) $original_odb;set ::env(_SDC_IN) $original_sdc
if {[nssoc_hold_sha $original_odb] ne $::env(NSSOC_ELECTRICAL_ODB_SHA) ||
    [nssoc_hold_sha $original_sdc] ne $::env(NSSOC_ELECTRICAL_SDC_SHA)} {error "Hold child changed original candidate"}
read_current_odb
set_thread_count 2
set_propagated_clock [all_clocks]
set_dont_touch_objects
set macros [nssoc_combined_macros]
nssoc_combined_prepare $root candidate_source
set before [nssoc_combined_record $root candidate_before true]
source $::env(NSSOC_ELECTRICAL_BASELINE_TCL)
dict for {key value} $nssoc_electrical_expected_metrics {
    if {[dict get $before $key] != $value} {error "Sizing baseline metric differs: $key"}
}
dict for {filename value} $nssoc_electrical_expected_files {
    if {[nssoc_hold_sha [file join $root candidate_before $filename]] ne $value} {error "Sizing baseline fingerprint differs: $filename"}
}
set target [nssoc_critical_size_preflight fanout639 $nssoc_critical_input net639 $nssoc_critical_terms $nssoc_critical_place]
nssoc_electrical_status [file join $root before-status.tsv]
nssoc_electrical_report $root candidate_before {{fanout639 net639}}
puts NSSOC_CRITICAL_INDEPENDENT_SIZING_BASELINE_EXACT
global_route -start_incremental
set call [nssoc_critical_size fanout639 $nssoc_critical_input net639 $nssoc_critical_terms $nssoc_critical_place]
source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl
set_global_connections
nssoc_combined_refresh
check_placement -verbose
set after [nssoc_combined_record $root after_sizing true]
nssoc_residual_geometry $macros [nssoc_combined_macros]
nssoc_electrical_status [file join $root after-status.tsv]
nssoc_electrical_report $root after_sizing {{fanout639 net639}}
set candidate [file join $root candidate]
set views [nssoc_critical_export $candidate]
set ::env(NSSOC_COMBINED_ROOT) $root
set ::env(NSSOC_COMBINED_PARENT_PID) [pid]
set ::env(NSSOC_COMBINED_ODB_SHA) [nssoc_hold_sha [file join $candidate soc_top.odb]]
set ::env(NSSOC_COMBINED_SDC_SHA) [nssoc_hold_sha [file join $candidate soc_top.sdc]]
set reloads {}
foreach name {reload_first reload_repeat} {
    nssoc_hold_write_json [file join $root "$name-headroom.json"] [nssoc_hold_jobject [nssoc_combined_headroom]]
    set ::env(STEP_DIR) [file join $root $name-process];file mkdir $::env(STEP_DIR)
    set ::env(CURRENT_ODB) [file join $candidate soc_top.odb]
    set ::env(_SDC_IN) [file join $candidate soc_top.sdc]
    set ::env(NSSOC_COMBINED_RELOAD_STAGE) $name
    set code [catch {exec [info nameofexecutable] -exit [file join $methods hw/soc/pnr/timing_combined_reload.tcl] \
        > [file join $root "$name.log"] 2>@1} message]
    set ::env(STEP_DIR) $root
    set ::env(CURRENT_ODB) $original_odb;set ::env(_SDC_IN) $original_sdc
    if {$code} {error "Independent sized-candidate reload failed: $name $message"}
    lappend reloads [nssoc_combined_read [file join $root "$name-process.json"]]
}
foreach suffix {odb def sdc v} {
    if {[nssoc_combined_pin [file join $candidate soc_top.$suffix]] ne [dict get $views soc_top.$suffix]} {error "Sizing views changed during reload"}
}
set stages {};set metrics {}
foreach name {candidate_before after_sizing reload_first reload_repeat} {
    lappend stages [nssoc_combined_read [file join $root "$name-stage.json"]]
    dict set metrics $name [nssoc_combined_read [file join $root "$name-metrics.json"]]
}
nssoc_hold_write_json [file join $root critical-followup.json] [nssoc_hold_jobject [dict create \
    schema 1 status [nssoc_hold_jstr COMPLETE_DIAGNOSTIC_ONLY] \
    candidate_adopted false timing_accepted false manufacturing_approval false thresholds_changed false \
    sizing_call [nssoc_hold_jobject $call] hold_mutation_used_for_sizing false \
    sizing_input_odb_sha256 [nssoc_hold_jstr $::env(NSSOC_ELECTRICAL_ODB_SHA)] \
    sizing_input_sdc_sha256 [nssoc_hold_jstr $::env(NSSOC_ELECTRICAL_SDC_SHA)] \
    hold_debug [nssoc_combined_read [file join $hold_root hold-debug.json]] \
    sram_macro_count 32 sram_placement_preserved true source_checkpoint_preserved true estimated_global_route_only true \
    candidate_files [nssoc_hold_jobject $views] stages "\[[join $stages ,]\]" timing_metrics [nssoc_hold_jobject $metrics] \
    independent_reload_processes "\[[join $reloads ,]\]" ]]
puts NSSOC_CRITICAL_FOLLOWUP_COMPLETE_NO_ADOPTION
