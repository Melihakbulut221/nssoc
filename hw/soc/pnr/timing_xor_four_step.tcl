# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
set root [file normalize [file join [file dirname [info script]] ../../..]]
source [file join $root hw/soc/pnr/timing_hold_reproducibility.tcl]
source [file join $root hw/soc/pnr/timing_targeted_hold_probe_helpers.tcl]
source [file join $root hw/soc/pnr/timing_xor_buffer_helpers.tcl]
source [file join $root hw/soc/pnr/timing_xor_pair_helpers.tcl]
source [file join $root hw/soc/pnr/timing_xor_four_helpers.tcl]
set native [file normalize [info nameofexecutable]]
set identity [nssoc_targeted_native_identity $::env(NSSOC_TARGETED_LAUNCHER_PATH) $native [file readlink /proc/[pid]/exe]]
set ::env(NSSOC_XOR_ROOT) $root
set ::env(NSSOC_XOR_OUT) [file join $::env(STEP_DIR) xor-four-control]
set fixture [file join $root sw/tests/timing_xor_four_native.tcl]
exec $native -no_init -exit $fixture > [file join $::env(STEP_DIR) xor-four-control.log] 2>@1
if {$identity ne [nssoc_targeted_native_identity $::env(NSSOC_TARGETED_LAUNCHER_PATH) $native [file readlink /proc/[pid]/exe]]} {
    error "Native XOR runtime identity changed"
}
nssoc_hold_write_json [file join $::env(STEP_DIR) xor-four-gate.json] [nssoc_hold_jobject [dict create \
    status [nssoc_hold_jstr PASS_NATIVE_XOR_FOUR_GATE] returncode 0 native_identity $identity \
    fixture_sha256 [nssoc_hold_jstr [nssoc_hold_sha $fixture]] \
    helper_sha256 [nssoc_hold_jstr [nssoc_hold_sha [file join $root hw/soc/pnr/timing_xor_four_helpers.tcl]]]]]
puts "NSSOC_XOR_FOUR_NATIVE_GATE_PASS_BEFORE_C10_LOAD"
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl
read_current_odb
source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl
set_global_connections
set_thread_count 2
set_propagated_clock [all_clocks]
set_dont_touch_objects
report_units
set macros {}
foreach inst [[ord::get_db_block] getInsts] {
    if {[[$inst getMaster] getName] in {SP6TSRAM512x64 DP8TSRAMDP256x16}} {
        dict set macros [$inst getName] [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]
        $inst setPlacementStatus FIRM
    }
}
if {[dict size $macros] != 32} {error "XOR ECO requires exactly 32 SRAM macros"}
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
set stages {}; set snapshots {}; set metrics {}
proc nssoc_xor_stage {name} {
    global stages snapshots metrics
    set snapshot [nssoc_hold_snapshot $name $::env(STEP_DIR)]
    lappend stages [dict get $snapshot json]
    dict set snapshots $name $snapshot
    set data [dict create setup_wns_seconds [nssoc_hold_number [sta::worst_slack_cmd max]] \
        hold_wns_seconds [nssoc_hold_number [sta::worst_slack_cmd min]] \
        setup_tns_seconds [nssoc_hold_number [sta::total_negative_slack_cmd max]] \
        hold_tns_seconds [nssoc_hold_number [sta::total_negative_slack_cmd min]] \
        setup_violating_endpoints [sta::endpoint_violation_count max] \
        hold_violating_endpoints [sta::endpoint_violation_count min] \
        slew_violations [sta::max_slew_violation_count] capacitance_violations [sta::max_capacitance_violation_count] \
        instance_count [llength [[ord::get_db_block] getInsts]]]
    dict set metrics $name [nssoc_hold_jobject $data]
    report_checks -path_delay max -group_path_count 10 -fields {fanout cap slew} -digits 9 > [file join $::env(STEP_DIR) "$name-setup.rpt"]
    report_check_types -max_slew -max_cap -violators -digits 9 > [file join $::env(STEP_DIR) "$name-electrical.rpt"]
}
nssoc_xor_stage matched_before
nssoc_targeted_assert_baseline [sta::endpoint_path_count] [sta::endpoint_violation_count min] [dict keys [nssoc_hold_corners]]
nssoc_xor_graph [file join $::env(STEP_DIR) graph-before.tsv]
global_route -start_incremental
puts "NSSOC_XOR_INSERT_BEGIN"
set insertion [nssoc_xor_insert]
set_global_connections
nssoc_xor_verify_power $insertion
puts "NSSOC_XOR_INSERT_END"
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
nssoc_xor_verify $insertion
nssoc_xor_graph [file join $::env(STEP_DIR) graph-first.tsv]
nssoc_xor_graph [file join $::env(STEP_DIR) graph-first-contracted.tsv] $insertion
if {[nssoc_hold_sha [file join $::env(STEP_DIR) graph-before.tsv]] ne [nssoc_hold_sha [file join $::env(STEP_DIR) graph-first-contracted.tsv]]} {
    error "Single-buffer contraction changed original chip logic"
}
nssoc_xor_stage after_first
nssoc_pair_graph [file join $::env(STEP_DIR) graph-first-pair.tsv]
if {[nssoc_hold_sha [file join $::env(STEP_DIR) graph-first.tsv]] ne [nssoc_hold_sha [file join $::env(STEP_DIR) graph-first-pair.tsv]]} {error "Pair graph exporter differs"}
global_route -start_incremental
puts "NSSOC_XNOR_INSERT_BEGIN"
set second [nssoc_xnor_insert]
set_global_connections
nssoc_xnor_verify_power $second
nssoc_xor_verify_power $insertion
puts "NSSOC_XNOR_INSERT_END"
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
nssoc_xnor_verify $second
set adjusted_first $insertion
dict incr adjusted_first initial_instances
nssoc_xor_verify $adjusted_first
nssoc_pair_graph [file join $::env(STEP_DIR) graph-second.tsv]
nssoc_pair_graph [file join $::env(STEP_DIR) graph-second-contracted.tsv] [list $insertion $second]
if {[nssoc_hold_sha [file join $::env(STEP_DIR) graph-before.tsv]] ne [nssoc_hold_sha [file join $::env(STEP_DIR) graph-second-contracted.tsv]]} {error "Two-buffer contraction changed original chip logic"}
nssoc_xor_stage after_second
set insertions [list $insertion $second]
set inserted_json [list [nssoc_xor_insertion_json $insertion] [nssoc_xnor_insertion_json $second]]
foreach index {3 4} name {after_third after_fourth} graph {graph-third.tsv graph-after.tsv} {
    global_route -start_incremental
    puts "NSSOC_FIXED_${index}_INSERT_BEGIN"
    set added [nssoc_four_insert $index]
    lappend insertions $added
    lappend inserted_json [nssoc_four_json $added]
    set_global_connections
    nssoc_four_verify_all $insertions
    puts "NSSOC_FIXED_${index}_INSERT_END"
    source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
    check_placement -verbose
    global_route -end_incremental
    estimate_parasitics -global_routing
    nssoc_four_verify_all $insertions
    nssoc_pair_graph [file join $::env(STEP_DIR) $graph]
    nssoc_xor_stage $name
}
nssoc_pair_graph [file join $::env(STEP_DIR) graph-contracted.tsv] $insertions
if {[nssoc_hold_sha [file join $::env(STEP_DIR) graph-before.tsv]] ne [nssoc_hold_sha [file join $::env(STEP_DIR) graph-contracted.tsv]]} {error "Four-buffer contraction changed original chip logic"}
sta::delays_invalid
sta::find_timing -full_update
nssoc_xor_stage after_full_update
nssoc_hold_assert_same_physical [dict get $snapshots after_fourth] [dict get $snapshots after_full_update]
set seen 0
foreach inst [[ord::get_db_block] getInsts] {
    if {[dict exists $macros [$inst getName]]} {
        incr seen
        if {[list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]] ne [dict get $macros [$inst getName]]} {error "SRAM macro changed"}
    } elseif {[[$inst getMaster] getName] in {SP6TSRAM512x64 DP8TSRAMDP256x16}} {error "Unexpected SRAM macro"}
}
if {$seen != 32} {error "SRAM macro missing"}
set candidate [file join $::env(STEP_DIR) rejected-candidate]
file mkdir $candidate
write_db [file join $candidate soc_top.odb]
write_def [file join $candidate soc_top.def]
write_verilog [file join $candidate soc_top.v]
write_sdc -no_timestamp [file join $candidate soc_top.sdc]
set views {}
foreach name {soc_top.odb soc_top.def soc_top.v soc_top.sdc} {
    set path [file join $candidate $name]
    dict set views $name [nssoc_hold_jobject [dict create bytes [file size $path] sha256 [nssoc_hold_jstr [nssoc_hold_sha $path]]]]
}
set row [dict create schema 1 status [nssoc_hold_jstr COMPLETE_DIAGNOSTIC_ONLY] \
    timing_accepted false candidate_adopted false manufacturing_approval false thresholds_changed false \
    sram_macro_count 32 sram_placement_preserved true original_graph_preserved true supply_connections_preserved true \
    insertions "\[[join $inserted_json ,]\]" stages "\[[join $stages ,]\]" \
    timing_metrics [nssoc_hold_jobject $metrics] candidate_files [nssoc_hold_jobject $views] \
    candidate_status [nssoc_hold_jstr REJECTED_PENDING_INDEPENDENT_TIMING_AND_PHYSICAL_VALIDATION]]
nssoc_hold_write_json [file join $::env(STEP_DIR) xor-four.json] [nssoc_hold_jobject $row]
puts "NSSOC_XOR_FOUR_COMPLETE_NO_ADOPTION"
