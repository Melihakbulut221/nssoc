# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# The child alone may attempt hold repair. Its output never enters sizing.
source [file join $::env(NSSOC_TARGETED_METHOD_ROOT) hw/soc/pnr/timing_combined_reload.tcl]
set ::env(NSSOC_ELECTRICAL_ROOT) $::env(NSSOC_TARGETED_METHOD_ROOT)
source [file join $::env(NSSOC_TARGETED_METHOD_ROOT) hw/soc/pnr/timing_critical_followup_helpers.tcl]
source $::env(NSSOC_ELECTRICAL_BASELINE_TCL)
set before [nssoc_combined_metrics]
dict for {key value} $nssoc_electrical_expected_metrics {
    if {[dict get $before $key] != $value} {error "Independent hold baseline metric differs: $key"}
}
dict for {filename value} $nssoc_electrical_expected_files {
    if {[nssoc_hold_sha [file join $root reload_first $filename]] ne $value} {error "Independent hold baseline fingerprint differs: $filename"}
}
set eligibility [nssoc_critical_hold_eligibility _135215_/D _135214_/Q]
if {[dict get $eligibility hold_slack_seconds] != $nssoc_critical_hold_slack} {error "Exact residual endpoint slack differs"}
nssoc_electrical_status [file join $root before-status.tsv]
nssoc_critical_hold_reports $root before
set_debug_level RSZ repair_hold 3
set_debug_level RSZ resizer 1
set_debug_level RSZ journal 1
puts NSSOC_CRITICAL_HOLD_BUFFER_SELECTION_BEGIN
rsz::report_buffers_cmd 0
puts NSSOC_CRITICAL_HOLD_BUFFER_SELECTION_END
puts NSSOC_CRITICAL_HOLD_CALL_BEGIN
global_route -start_incremental
set call [nssoc_residual_hold_repair _135215_/D sg13g2_dfrbpq_1]
puts NSSOC_CRITICAL_HOLD_CALL_END
set_debug_level RSZ repair_hold 0
set_debug_level RSZ resizer 0
set_debug_level RSZ journal 0
source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl
set_global_connections
nssoc_combined_refresh
check_placement -verbose
set after [nssoc_combined_record $root after_hold_debug true]
nssoc_critical_hold_reports $root after
nssoc_electrical_status [file join $root after-status.tsv]
nssoc_residual_geometry $macros [nssoc_combined_macros]
set views [nssoc_critical_export [file join $root candidate]]
nssoc_hold_write_json [file join $root hold-debug.json] [nssoc_hold_jobject [dict create \
    schema 1 status [nssoc_hold_jstr COMPLETE_ISOLATED_HOLD_DEBUG] \
    eligibility [nssoc_hold_jobject $eligibility] call [nssoc_hold_jobject $call] \
    after_metrics [nssoc_hold_jobject $after] candidate_files [nssoc_hold_jobject $views] \
    input_odb_sha256 [nssoc_hold_jstr $::env(NSSOC_COMBINED_ODB_SHA)] \
    input_sdc_sha256 [nssoc_hold_jstr $::env(NSSOC_COMBINED_SDC_SHA)] \
    candidate_adopted false timing_accepted false manufacturing_approval false \
    journal_limit [nssoc_hold_jstr {Native debug exposes journal begin/restore/end and per-transition load slacks, but not the transient slew/WNS values inside rollback's OR predicate. Do not infer an unobserved subpredicate.}]]]
puts NSSOC_CRITICAL_HOLD_DEBUG_COMPLETE
