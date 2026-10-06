# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
set root [file normalize [file join [file dirname [info script]] ../../..]]
source [file join $root hw/soc/pnr/timing_hold_reproducibility.tcl]
set ::nssoc_alu_geometry_definitions_only 1
source [file join $root hw/soc/pnr/alu_physical_geometry.tcl]
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl
read_current_odb
source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl
set_global_connections
set_propagated_clock [all_clocks]
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
# Fresh process: explicitly rebuild routes from this fresh placement/CTS database.
source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
estimate_parasitics -global_routing
sta::delays_invalid
sta::find_timing -full_update
check_placement -verbose
nssoc_alu_geometry $::env(STEP_DIR)
set snapshot [nssoc_hold_snapshot fresh_grt $::env(STEP_DIR)]
set stream [open [file join $::env(STEP_DIR) setup-endpoints.tsv] {WRONLY CREAT EXCL}]
puts $stream "endpoint\tglobal_vertex_slack_seconds"
set vertices {}
foreach pin [sta::endpoints] {
    set name [nssoc_hold_field [get_property $pin full_name]]
    if {[dict exists $vertices $name] || [llength [$pin vertices]] != 1} {error "Ambiguous setup endpoint"}
    dict set vertices $name [lindex [$pin vertices] 0]
}
set negative 0
foreach name [lsort [dict keys $vertices]] {
    set slack [nssoc_hold_slack [[dict get $vertices $name] slack max]]
    if {$slack ne "UNCONSTRAINED" && $slack < 0} {incr negative}
    puts $stream "$name\t$slack"
}
close $stream
nssoc_hold_assert_coverage [sta::endpoint_path_count] [dict keys $vertices] $negative [sta::endpoint_violation_count max]
set metrics [dict create \
    setup_wns_seconds [nssoc_hold_number [sta::worst_slack_cmd max]] \
    hold_wns_seconds [nssoc_hold_number [sta::worst_slack_cmd min]] \
    setup_tns_seconds [nssoc_hold_number [sta::total_negative_slack_cmd max]] \
    hold_tns_seconds [nssoc_hold_number [sta::total_negative_slack_cmd min]] \
    setup_violating_endpoints $negative hold_violating_endpoints [sta::endpoint_violation_count min] \
    slew_violations [sta::max_slew_violation_count] capacitance_violations [sta::max_capacitance_violation_count] \
    instance_count [llength [[ord::get_db_block] getInsts]]]
report_checks -path_delay max -group_path_count 20 -fields {fanout cap slew} -digits 9 > [file join $::env(STEP_DIR) setup.rpt]
report_checks -path_delay min -group_path_count 20 -fields {fanout cap slew} -digits 9 > [file join $::env(STEP_DIR) hold.rpt]
report_check_types -max_slew -max_cap -violators -digits 9 > [file join $::env(STEP_DIR) electrical.rpt]
check_power_grid -net VPWR -error_file [file join $::env(STEP_DIR) VPWR-connectivity.rpt]
check_power_grid -net VGND -error_file [file join $::env(STEP_DIR) VGND-connectivity.rpt]
nssoc_hold_write_json [file join $::env(STEP_DIR) audit.json] [nssoc_hold_jobject [dict create \
    status [nssoc_hold_jstr FRESH_GLOBAL_ROUTE_ESTIMATE_ONLY] \
    timing_accepted false candidate_adopted false manufacturing_approval false \
    hold_stage [dict get $snapshot json] timing_metrics [nssoc_hold_jobject $metrics] \
    setup_endpoint_count [dict size $vertices] setup_negative_endpoint_count $negative]]
write_views
puts "NSSOC_ALU_FRESH_ROUTE_AUDIT_COMPLETE_NO_ADOPTION"
