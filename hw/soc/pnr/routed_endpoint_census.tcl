# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Read only; caller has loaded immutable real routed SPEF, libraries and SDC.
nssoc_hold_assert_units [sta::unit_scale time]
set corners [nssoc_hold_corners]
set census {};set mapping {}
set expected [sta::endpoint_path_count]
foreach pin [sta::endpoints] {
    set name [nssoc_hold_field [get_property $pin full_name]]
    if {[dict exists $census $name]} {error "Duplicate native endpoint"}
    set vertices [$pin vertices]
    if {[llength $vertices]!=1 || [[lindex $vertices 0] is_bidirect_driver]} {error "Ambiguous endpoint vertex $name"}
    # Exact pinned dbSta.i identity conversion; never strip or guess escaping.
    set iterm [sta::sta_to_db_pin $pin]
    if {$iterm ne "NULL"} {
        set mapped [dict create kind [nssoc_hold_jstr instance] instance [nssoc_hold_jstr [[$iterm getInst] getName]] pin [nssoc_hold_jstr [[$iterm getMTerm] getName]]]
    } else {
        set bterm [sta::sta_to_db_port [sta::sta_pin_to_port $pin]]
        if {$bterm eq "NULL"} {error "Endpoint has no native physical terminal: $name"}
        set mapped [dict create kind [nssoc_hold_jstr boundary] port [nssoc_hold_jstr [$bterm getName]]]
    }
    dict set mapping $name [nssoc_hold_jobject $mapped]
    dict set census $name [lindex $vertices 0]
}
set ordered [lsort [dict keys $census]]
set stream [open [file join $nssoc_endpoint_out endpoint-slacks.tsv] {WRONLY CREAT EXCL}]
puts $stream "corner\tdelay\tendpoint\trise_seconds\tfall_seconds\tworst_seconds"
set counts {};set wns {}
foreach delay {min max} {
    set global {};set negative 0
    foreach name $ordered {
        set value [nssoc_hold_slack [[dict get $census $name] slack $delay]]
        dict set global $name $value
        if {$value ne "UNCONSTRAINED" && $value<0} {incr negative}
    }
    nssoc_hold_assert_coverage $expected $ordered $negative [sta::endpoint_violation_count $delay]
    dict set counts $delay $negative
    set minima {}
    foreach corner_name [lsort [dict keys $corners]] {
        set sampled {};set corner [dict get $corners $corner_name]
        dict set wns ${corner_name}_${delay} [nssoc_hold_number [sta::worst_slack_corner $corner $delay]]
        foreach rf {rise fall} {
            foreach path [find_timing_paths -corner $corner_name -path_delay ${delay}_${rf} -group_path_count [expr {$expected+1}] -endpoint_path_count 1] {
                set name [get_property [$path pin] full_name]
                if {![dict exists $census $name] || [$path vertex] ne [dict get $census $name]} {error "Path outside census"}
                if {[$path is_unconstrained]} {error "Unexpected unconstrained PathEnd"}
                set slack [nssoc_hold_slack [$path slack]]
                if {$slack eq "UNCONSTRAINED"} {error "Invalid constrained slack"}
                if {![dict exists $sampled $name $rf] || $slack<[dict get $sampled $name $rf]} {dict set sampled $name $rf $slack}
            }
        }
        foreach name $ordered {
            set rise UNCONSTRAINED;set fall UNCONSTRAINED;set worst UNCONSTRAINED
            if {[dict exists $sampled $name rise]} {set rise [dict get $sampled $name rise]}
            if {[dict exists $sampled $name fall]} {set fall [dict get $sampled $name fall]}
            foreach value [list $rise $fall] {
                if {$value ne "UNCONSTRAINED" && ($worst eq "UNCONSTRAINED" || $value<$worst)} {set worst $value}
            }
            if {$worst ne "UNCONSTRAINED" && (![dict exists $minima $name] || $worst<[dict get $minima $name])} {dict set minima $name $worst}
            puts $stream [join [list $corner_name $delay $name $rise $fall $worst] \t]
        }
        flush $stream
        puts "ROUTED_CENSUS $corner_name $delay $expected"
    }
    nssoc_hold_assert_path_coverage $global $minima
}
close $stream
set names {};foreach name $ordered {lappend names [nssoc_hold_jstr $name]}
set corner_names {};foreach name [lsort [dict keys $corners]] {lappend corner_names [nssoc_hold_jstr $name]}
set result [dict create native_pin_mapping [nssoc_hold_jobject $mapping] engine_endpoint_count $expected native_time_unit_seconds [nssoc_hold_number [sta::unit_scale time]] value_units [nssoc_hold_jstr seconds] negative_endpoint_count [nssoc_hold_jobject $counts] native_wns_seconds [nssoc_hold_jobject $wns] corners "\[[join $corner_names ,]\]" endpoints "\[[join $names ,]\]"]
nssoc_hold_write_json [file join $nssoc_endpoint_out native-census.json] [nssoc_hold_jobject $result]
puts NSSOC_ACTUAL_ROUTED_CENSUS_COMPLETE
