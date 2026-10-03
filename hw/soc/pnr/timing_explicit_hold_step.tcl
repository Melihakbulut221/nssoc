# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
source $::env(NSSOC_HOLD_DIAGNOSTIC_HELPER)
set methods $::env(NSSOC_TARGETED_METHOD_ROOT)
set ::env(NSSOC_ELECTRICAL_ROOT) $methods
source [file join $methods hw/soc/pnr/timing_targeted_hold_probe_helpers.tcl]
source [file join $methods hw/soc/pnr/timing_combined_repair_helpers.tcl]
source [file join $methods hw/soc/pnr/timing_critical_followup_helpers.tcl]
source [file join $methods hw/soc/pnr/timing_explicit_hold_helpers.tcl]
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl
nssoc_targeted_native_gate
set root $::env(STEP_DIR)
set ::env(NSSOC_ELECTRICAL_ROOT) $methods
set ::env(NSSOC_EXPLICIT_OUT) [file join $root explicit-control]
exec [info nameofexecutable] -exit [file join $methods sw/tests/timing_explicit_hold_native.tcl] > [file join $root explicit-control.log] 2>@1
puts NSSOC_EXPLICIT_NATIVE_CONTROL_PASS
set ::env(CURRENT_ODB) $::env(NSSOC_ELECTRICAL_CANDIDATE_ODB)
set ::env(_SDC_IN) $::env(NSSOC_ELECTRICAL_CANDIDATE_SDC)
if {[nssoc_hold_sha $::env(CURRENT_ODB)] ne $::env(NSSOC_ELECTRICAL_ODB_SHA) ||
    [nssoc_hold_sha $::env(_SDC_IN)] ne $::env(NSSOC_ELECTRICAL_SDC_SHA)} {error "Exact sized candidate overlay differs"}
set original_odb $::env(CURRENT_ODB);set original_sdc $::env(_SDC_IN)
read_current_odb
set_thread_count 2
set_propagated_clock [all_clocks]
set_dont_touch_objects
set macros [nssoc_combined_macros]
nssoc_explicit_placement [file join $root source-original-objects.tsv]
nssoc_explicit_route $root candidate_source
if {[nssoc_hold_sha [file join $root source-original-objects.tsv]] ne [nssoc_hold_sha [file join $root candidate_source-original-objects.tsv]]} {error "Baseline fresh routing moved an original object"}
set before [nssoc_combined_record $root candidate_before true]
source $::env(NSSOC_ELECTRICAL_BASELINE_TCL)
dict for {key value} $nssoc_electrical_expected_metrics {if {[dict get $before $key] != $value} {error "Exact sized source metric differs: $key"}}
dict for {filename value} $nssoc_electrical_expected_files {if {[nssoc_hold_sha [file join $root candidate_before $filename]] ne $value} {error "Exact sized source fingerprint differs: $filename"}}
nssoc_explicit_preflight _135214_ _135215_ $nssoc_explicit_net $nssoc_explicit_places
nssoc_electrical_status [file join $root before-status.tsv]
nssoc_explicit_observe $root before _135214_ _135215_
puts NSSOC_EXPLICIT_SOURCE_BASELINE_EXACT
set insertion [nssoc_explicit_insert $root _135214_ _135215_ $nssoc_explicit_net $nssoc_explicit_places]
# This reports the direct mutation's timing state before fresh routing. It is
# diagnostic only; acceptance always uses the independently routed/reloaded views.
sta::delays_invalid
sta::find_timing -full_update
nssoc_explicit_observe $root inserted_before_fresh_route _135214_ _135215_
nssoc_explicit_route $root after_insertion [dict get $insertion buffer]
nssoc_explicit_verify $insertion
set after [nssoc_combined_record $root after_insertion true]
nssoc_explicit_observe $root after_insertion _135214_ _135215_
nssoc_electrical_status [file join $root after-status.tsv]
if {[nssoc_combined_macros] ne $macros} {error "Explicit insertion changed SRAM placement"}
if {[nssoc_hold_sha [file join $root source-original-objects.tsv]] ne [nssoc_hold_sha [file join $root after_insertion-original-objects.tsv]]} {error "Original cell movement after explicit insertion"}
set candidate [file join $root candidate]
set views [nssoc_critical_export $candidate]
set ::env(NSSOC_COMBINED_ROOT) $root
set ::env(NSSOC_COMBINED_PARENT_PID) [pid]
set ::env(NSSOC_COMBINED_ODB_SHA) [nssoc_hold_sha [file join $candidate soc_top.odb]]
set ::env(NSSOC_COMBINED_SDC_SHA) [nssoc_hold_sha [file join $candidate soc_top.sdc]]
# Native Tcl data is generated only from the insertion's observed immutable row.
set insertion_file [file join $root insertion.tcldict]
set f [open $insertion_file {WRONLY CREAT EXCL}];puts $f $insertion;close $f
set ::env(NSSOC_EXPLICIT_INSERTION_FILE) $insertion_file
set ::env(NSSOC_EXPLICIT_INSERTION_SHA) [nssoc_hold_sha $insertion_file]
set ::env(NSSOC_EXPLICIT_ORIGINAL_OBJECT_SHA) [nssoc_hold_sha [file join $root source-original-objects.tsv]]
set ::env(NSSOC_EXPLICIT_ORIGINAL_GRAPH_SHA) [nssoc_hold_sha [file join $root graph-before.tsv]]
set reloads {}
foreach name {reload_first reload_repeat} {
    nssoc_hold_write_json [file join $root "$name-headroom.json"] [nssoc_hold_jobject [nssoc_combined_headroom]]
    set ::env(STEP_DIR) [file join $root $name-process];file mkdir $::env(STEP_DIR)
    set ::env(CURRENT_ODB) [file join $candidate soc_top.odb]
    set ::env(_SDC_IN) [file join $candidate soc_top.sdc]
    set ::env(NSSOC_COMBINED_RELOAD_STAGE) $name
    set code [catch {exec [info nameofexecutable] -exit [file join $methods hw/soc/pnr/timing_explicit_hold_reload.tcl] > [file join $root "$name.log"] 2>@1} message]
    set ::env(STEP_DIR) $root
    set ::env(CURRENT_ODB) $original_odb;set ::env(_SDC_IN) $original_sdc
    if {$code} {error "Independent explicit candidate reload failed: $name $message"}
    lappend reloads [nssoc_combined_read [file join $root "$name-process.json"]]
}
foreach suffix {odb def sdc v} {if {[nssoc_combined_pin [file join $candidate soc_top.$suffix]] ne [dict get $views soc_top.$suffix]} {error "Explicit candidate export changed"}}
set stages {};set metrics {}
foreach name {candidate_before after_insertion reload_first reload_repeat} {
    lappend stages [nssoc_combined_read [file join $root "$name-stage.json"]]
    dict set metrics $name [nssoc_combined_read [file join $root "$name-metrics.json"]]
}
nssoc_hold_write_json [file join $root explicit-hold.json] [nssoc_hold_jobject [dict create \
    schema 1 status [nssoc_hold_jstr COMPLETE_DIAGNOSTIC_ONLY] candidate_adopted false timing_accepted false \
    manufacturing_approval false thresholds_changed false detailed_placement_calls 0 repair_timing_calls 0 \
    insertion [nssoc_explicit_json $insertion] original_objects_preserved true full_graph_contraction_preserved true \
    source_odb_sha256 [nssoc_hold_jstr $::env(NSSOC_ELECTRICAL_ODB_SHA)] \
    source_sdc_sha256 [nssoc_hold_jstr $::env(NSSOC_ELECTRICAL_SDC_SHA)] \
    sram_macro_count 32 sram_placement_preserved true source_checkpoint_preserved true estimated_global_route_only true \
    candidate_files [nssoc_hold_jobject $views] stages "\[[join $stages ,]\]" timing_metrics [nssoc_hold_jobject $metrics] \
    independent_reload_processes "\[[join $reloads ,]\]" ]]
puts NSSOC_EXPLICIT_HOLD_COMPLETE_NO_ADOPTION
