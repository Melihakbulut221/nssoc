# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Combined repair support. Loading this file never starts native work.
proc nssoc_combined_metrics {} {
    return [dict create recorded_ms [clock milliseconds] \
        setup_wns_seconds [nssoc_hold_number [sta::worst_slack_cmd max]] \
        hold_wns_seconds [nssoc_hold_number [sta::worst_slack_cmd min]] \
        setup_tns_seconds [nssoc_hold_number [sta::total_negative_slack_cmd max]] \
        hold_tns_seconds [nssoc_hold_number [sta::total_negative_slack_cmd min]] \
        setup_violating_endpoints [sta::endpoint_violation_count max] \
        hold_violating_endpoints [sta::endpoint_violation_count min] \
        slew_violations [sta::max_slew_violation_count] \
        capacitance_violations [sta::max_capacitance_violation_count] \
        instance_count [llength [[ord::get_db_block] getInsts]]]
}
proc nssoc_combined_geometry {path} {
    set names {}
    foreach inst [[ord::get_db_block] getInsts] {dict set names [$inst getName] $inst}
    set stream [open $path {WRONLY CREAT EXCL}]
    puts $stream "instance\tmaster\tx_dbu\ty_dbu\torientation"
    foreach name [lsort [dict keys $names]] {
        set inst [dict get $names $name]
        lassign [$inst getLocation] x y
        puts $stream [join [list $name [[$inst getMaster] getName] $x $y [$inst getOrient]] \t]
    }
    close $stream
}
proc nssoc_combined_macros {} {
    set macros {}
    foreach inst [[ord::get_db_block] getInsts] {
        if {[[$inst getMaster] getName] in {SP6TSRAM512x64 DP8TSRAMDP256x16}} {
            dict set macros [$inst getName] [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]
            $inst setPlacementStatus FIRM
        }
    }
    if {[dict size $macros] != 32} {error "Expected exactly 32 SRAM macros"}
    return $macros
}
proc nssoc_combined_refresh {} {
    source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
    global_route -end_incremental
    estimate_parasitics -global_routing
    sta::delays_invalid
    sta::find_timing -full_update
}
proc nssoc_combined_prepare {root prefix} {
    remove_fillers
    foreach net [[ord::get_db_block] getNets] {
        set wire [$net getWire]
        if {$wire ne "NULL"} {odb::dbWire_destroy $wire}
    }
    nssoc_combined_geometry [file join $root "$prefix-loaded-geometry.tsv"]
    source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
    source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
    estimate_parasitics -global_routing
    nssoc_combined_geometry [file join $root "$prefix-grt-geometry.tsv"]
    nssoc_hold_write_json [file join $root "$prefix-grt-metrics.json"] \
        [nssoc_hold_jobject [nssoc_combined_metrics]]
    global_route -start_incremental
    nssoc_combined_refresh
    nssoc_combined_geometry [file join $root "$prefix-dpl-geometry.tsv"]
}
proc nssoc_combined_record {root name {full false}} {
    set metrics [nssoc_combined_metrics]
    report_checks -path_delay max -group_path_count 10 -fields {fanout cap slew} -digits 9 \
        > [file join $root "$name-setup.rpt"]
    report_check_types -max_slew -max_cap -violators -digits 9 \
        > [file join $root "$name-electrical.rpt"]
    nssoc_hold_write_json [file join $root "$name-metrics.json"] [nssoc_hold_jobject $metrics]
    if {$full} {
        set snapshot [nssoc_hold_snapshot $name $root]
        nssoc_hold_write_json [file join $root "$name-stage.json"] [dict get $snapshot json]
    }
    return $metrics
}
proc nssoc_combined_budget {initial budget actual} {
    if {$actual < $initial || $actual - $initial > $budget} {
        error "Combined original-instance growth budget violated"
    }
    return [expr {$budget-($actual-$initial)}]
}
proc nssoc_combined_hold_progress {before after} {
    # A budgeted next pass requires at least one measured hold improvement.
    return [expr {[dict get $after hold_wns_seconds] > [dict get $before hold_wns_seconds] ||
        [dict get $after hold_tns_seconds] > [dict get $before hold_tns_seconds] ||
        [dict get $after hold_violating_endpoints] < [dict get $before hold_violating_endpoints]}]
}
proc nssoc_combined_pin {path} {
    return [nssoc_hold_jobject [dict create bytes [file size $path] sha256 [nssoc_hold_jstr [nssoc_hold_sha $path]]]]
}
proc nssoc_combined_read {path} {
    set stream [open $path r]
    try {return [string trim [read $stream]]} finally {close $stream}
}
proc nssoc_combined_headroom {} {
    set memory [nssoc_combined_read /proc/meminfo]
    set process [nssoc_combined_read /proc/[pid]/status]
    if {![regexp -line {^MemAvailable:\s+(\d+) kB$} $memory -> available] ||
        ![regexp -line {^VmRSS:\s+(\d+) kB$} $process -> resident]} {
        error "Cannot establish reload memory headroom"
    }
    set required [expr {max(2097152, int(ceil(1.25*$resident)))}]
    if {$available < $required} {error "Insufficient reload memory headroom: $available kB, required $required kB"}
    return [dict create available_kib $available parent_rss_kib $resident required_kib $required]
}
