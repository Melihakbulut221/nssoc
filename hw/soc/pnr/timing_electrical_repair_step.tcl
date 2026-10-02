# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Reproduce the isolated parent candidate before exactly three native net repairs.
source $::env(NSSOC_HOLD_DIAGNOSTIC_HELPER)
set methods $::env(NSSOC_TARGETED_METHOD_ROOT)
source [file join $methods hw/soc/pnr/timing_targeted_hold_probe_helpers.tcl]
source [file join $methods hw/soc/pnr/timing_combined_repair_helpers.tcl]
source [file join $methods hw/soc/pnr/timing_electrical_repair_helpers.tcl]
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl
nssoc_targeted_native_gate
set root $::env(STEP_DIR)
set ::env(NSSOC_ELECTRICAL_ROOT) $methods
set ::env(NSSOC_ELECTRICAL_OUT) [file join $root electrical-control]
exec [info nameofexecutable] -exit [file join $methods sw/tests/timing_electrical_repair_native.tcl] \
    > [file join $root electrical-control.log] 2>@1
puts NSSOC_ELECTRICAL_NATIVE_GATE_PASS_BEFORE_CANDIDATE_LOAD
# io.tcl has already restored the original C10 environment. Override only these
# explicitly pinned, unadopted candidate views, keeping the original constraints.
set ::env(CURRENT_ODB) $::env(NSSOC_ELECTRICAL_CANDIDATE_ODB)
set ::env(_SDC_IN) $::env(NSSOC_ELECTRICAL_CANDIDATE_SDC)
if {[nssoc_hold_sha $::env(CURRENT_ODB)] ne $::env(NSSOC_ELECTRICAL_ODB_SHA) ||
    [nssoc_hold_sha $::env(_SDC_IN)] ne $::env(NSSOC_ELECTRICAL_SDC_SHA)} {error "Candidate overlay identity changed"}
read_current_odb
set_thread_count 2
set_propagated_clock [all_clocks]
set_dont_touch_objects
set macros [nssoc_combined_macros]
nssoc_combined_prepare $root candidate_source
set before [nssoc_combined_record $root candidate_before true]
source $::env(NSSOC_ELECTRICAL_BASELINE_TCL)
dict for {key expected} $nssoc_electrical_expected_metrics {
    if {[dict get $before $key] != $expected} {error "Candidate fresh metric differs before repair: $key"}
}
dict for {name expected} $nssoc_electrical_expected_files {
    if {[nssoc_hold_sha [file join $root candidate_before $name]] ne $expected} {
        error "Candidate fresh physical fingerprint differs before repair: $name"
    }
}
puts NSSOC_ELECTRICAL_BASELINE_EXACT_BEFORE_REPAIR
set targets {{fanout1387 net1387} {fanout1391 net1391} {fanout1228 net1228}}
# Validate all three before allowing the first mutation.
foreach target $targets {nssoc_electrical_preflight {*}$target}
nssoc_electrical_status [file join $root before-status.tsv]
nssoc_electrical_report $root candidate_before $targets
set calls {}
global_route -start_incremental
foreach target $targets {
    lassign $target driver netname
    puts "NSSOC_ELECTRICAL_NET_BEGIN $driver $netname"
    lappend calls [nssoc_hold_jobject [nssoc_electrical_repair $driver $netname]]
    puts "NSSOC_ELECTRICAL_NET_END $driver $netname"
    nssoc_combined_budget 103697 41478 [llength [[ord::get_db_block] getInsts]]
}
source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl
set_global_connections
nssoc_combined_refresh
set after [nssoc_combined_record $root after_electrical true]
nssoc_electrical_status [file join $root after-status.tsv]
nssoc_electrical_report $root after_electrical $targets
if {[nssoc_combined_macros] ne $macros} {error "Electrical repair changed an SRAM master/location/orientation"}
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
    set command [list [info nameofexecutable] -exit [file join $methods hw/soc/pnr/timing_combined_reload.tcl]]
    set code [catch {exec {*}$command > [file join $root "$name.log"] 2>@1} message]
    set ::env(STEP_DIR) $root
    set ::env(CURRENT_ODB) $original_odb
    set ::env(_SDC_IN) $original_sdc
    if {$code} {error "Independent electrical reload failed ($name): $message"}
    lappend reloads [nssoc_combined_read [file join $root "$name-process.json"]]
}
foreach suffix {odb def sdc v} {
    if {[nssoc_combined_pin [file join $candidate soc_top.$suffix]] ne [dict get $candidate_pins soc_top.$suffix]} {
        error "Electrical candidate changed during reload"
    }
}
set stages {}; set metrics {}
foreach name {candidate_before after_electrical reload_first reload_repeat} {
    lappend stages [nssoc_combined_read [file join $root "$name-stage.json"]]
    dict set metrics $name [nssoc_combined_read [file join $root "$name-metrics.json"]]
}
nssoc_hold_write_json [file join $root electrical-repair.json] [nssoc_hold_jobject [dict create \
    schema 1 status [nssoc_hold_jstr COMPLETE_DIAGNOSTIC_ONLY] \
    candidate_adopted false timing_accepted false manufacturing_approval false thresholds_changed false \
    setup_repair_invocations 0 hold_repair_invocations 0 calls "\[[join $calls ,]\]" \
    sram_macro_count 32 sram_placement_preserved true candidate_files [nssoc_hold_jobject $candidate_pins] \
    stages "\[[join $stages ,]\]" timing_metrics [nssoc_hold_jobject $metrics] \
    independent_reload_processes "\[[join $reloads ,]\]" \
    source_checkpoint_preserved true estimated_global_route_only true]]
puts NSSOC_ELECTRICAL_COMPLETE_NO_ADOPTION
