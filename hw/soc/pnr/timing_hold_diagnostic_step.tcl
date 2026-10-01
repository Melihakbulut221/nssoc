# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# One fresh LibreLane OpenROAD process; never a repair/adoption step.
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
proc nssoc_hold_stage {name} {
    global stages snapshots
    set snapshot [nssoc_hold_snapshot $name $::env(STEP_DIR)]
    lappend stages [dict get $snapshot json]
    dict set snapshots $name $snapshot
}

# A reloaded ODB does not preserve the producer's estimated-RC cache. This
# stage labels missing models and never represents them as routed signoff.
nssoc_hold_stage reload_no_parasitics
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
nssoc_hold_stage grt_rebuilt_before_dpl

# Reproduce exactly the published setup A/B initial preparation boundary.
global_route -start_incremental
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
global_route -end_incremental
estimate_parasitics -global_routing
nssoc_hold_stage matched_before

# Same native physical state: only read queries, then explicitly invalidate
# timing caches. Full endpoint and all driver/load RC dumps prove the boundary.
nssoc_hold_stage same_state_repeat
nssoc_hold_assert_same_physical [dict get $snapshots matched_before] [dict get $snapshots same_state_repeat]
sta::arrivals_invalid
sta::find_timing
nssoc_hold_stage arrivals_recomputed
nssoc_hold_assert_same_physical [dict get $snapshots matched_before] [dict get $snapshots arrivals_recomputed]
sta::delays_invalid
sta::find_timing -full_update
nssoc_hold_stage full_timing_recomputed
nssoc_hold_assert_same_physical [dict get $snapshots matched_before] [dict get $snapshots full_timing_recomputed]

# Re-estimation and legalization/routing are separate, explicitly mutating
# diagnostic boundaries. No repair_timing, buffering or constraint relaxation.
estimate_parasitics -global_routing
nssoc_hold_stage parasitics_reestimated
global_route -start_incremental
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
global_route -end_incremental
estimate_parasitics -global_routing
nssoc_hold_stage incremental_no_repair

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
set constraints {}
foreach name [dict keys $snapshots] {
    lappend constraints [dict get $snapshots $name fingerprints constraints]
}
if {[llength [lsort -unique $constraints]] != 1} {error "Diagnostic changed native timing constraints"}
set matched_netlist [dict get $snapshots matched_before fingerprints netlist]
foreach name {same_state_repeat arrivals_recomputed full_timing_recomputed parasitics_reestimated incremental_no_repair} {
    if {[dict get $snapshots $name fingerprints netlist] ne $matched_netlist} {
        error "No-repair diagnostic changed logical connectivity"
    }
}
set sdc_files {}
foreach name [dict keys $snapshots] {lappend sdc_files [nssoc_hold_jstr "$name/constraints.sdc"]}
set receipt [nssoc_hold_jobject [dict create schema 1 status [nssoc_hold_jstr COMPLETE_DIAGNOSTIC_ONLY] \
    timing_accepted false candidate_adopted false manufacturing_approval false \
    all_endpoint_coverage true source_sram_macros_preserved 32 \
    sram_macro_count 32 sram_placement_preserved true \
    time_unit_seconds [nssoc_hold_number [sta::unit_scale time]] value_units [nssoc_hold_jstr seconds] \
    sdc_files "\[[join $sdc_files ,]\]" stages "\[[join $stages ,]\]" \
    scope [nssoc_hold_jstr {No-op timing-cache and explicit route/parasitic boundary diagnosis only; no acceptance-tolerance change, repair, candidate adoption or signoff.}]]]
nssoc_hold_write_json [file join $::env(STEP_DIR) hold-diagnostic.json] $receipt
puts "NSSOC_HOLD_DIAGNOSTIC_COMPLETE_NO_ADOPTION"
