# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Explicit alternative completeness proof for pinned OpenSTA 857316ff.
# Preserve the frozen Vertex guard; compare every raw graph path minimum to
# the PathEnd minimum with exact equality. No slack tolerance is introduced.
rename nssoc_hold_assert_path_coverage nssoc_original_assert_path_coverage
set nssoc_graph_checks {}
set nssoc_graph_failures {}
set nssoc_graph_mismatches {}
proc nssoc_hold_assert_path_coverage {vertices minima} {
    set code [catch {nssoc_original_assert_path_coverage $vertices $minima} message]
    if {$code ni {0 1}} {error "Unexpected original guard completion code"}
    if {$code==1} {
        lappend ::nssoc_graph_failures [nssoc_hold_jobject [dict create delay [nssoc_hold_jstr $::delay] error [nssoc_hold_jstr $message]]]
    }
    set graph_minima {};set raw_count 0;set constrained 0;set negative 0
    set filename [file join $::nssoc_endpoint_out graph-paths-$::delay.tsv.gz]
    set stream [open "|gzip -n -c > [list $filename]" w]
    puts $stream "endpoint\ttransition\ttag\tslack_seconds\tarrival_seconds\trequired_seconds"
    try {
        foreach name [lsort [dict keys $vertices]] {
            set vertex [dict get $::census $name]
            set minimum UNCONSTRAINED;set observed {};set endpoint_paths 0
            foreach rf {rise fall} {
                set iterator [$vertex path_iterator $rf $::delay]
                try {
                    while {[$iterator has_next]} {
                        set path [$iterator next]
                        if {[get_property [$path pin] full_name] ne $name || [$path edge] ne $rf} {error "Graph path identity mismatch: $name"}
                        set slack [nssoc_hold_slack [$path slack]]
                        lappend observed $slack
                        incr raw_count;incr endpoint_paths
                        puts $stream [join [list $name $rf [nssoc_hold_field [$path tag]] $slack [nssoc_hold_number [$path arrival]] [nssoc_hold_number [$path required]]] \t]
                        if {$slack ne "UNCONSTRAINED" && ($minimum eq "UNCONSTRAINED" || $slack<$minimum)} {set minimum $slack}
                    }
                } finally {$iterator finish}
            }
            dict set graph_minima $name $minimum
            if {$minimum ne "UNCONSTRAINED"} {
                incr constrained
                if {$minimum<0} {incr negative}
            }
            set value [dict get $vertices $name]
            if {$value ne $minimum} {
                # This is NOT accepted using a numeric tolerance. Require the
                # native chosen Path object, its raw slack, and exact graph
                # membership; the caller additionally executes pinned Fuzzy.cc.
                if {$value eq "UNCONSTRAINED" || $minimum eq "UNCONSTRAINED" || $minimum>$value || ($minimum<0)!=($value<0) || $value ni $observed} {error "Unexplained native vertex/graph difference: $name"}
                set selected [sta::vertex_worst_slack_path $vertex $::delay]
                if {$selected eq "NULL" || [get_property [$selected pin] full_name] ne $name || [nssoc_hold_slack [$selected slack]] ne $value} {error "Native chosen path does not reproduce vertex: $name"}
                lappend ::nssoc_graph_mismatches [nssoc_hold_jobject [dict create endpoint [nssoc_hold_jstr $name] delay [nssoc_hold_jstr $::delay] vertex_seconds $value graph_minimum_seconds $minimum native_chosen_path_seconds [nssoc_hold_number [$selected slack]] native_chosen_path_tag [nssoc_hold_jstr [$selected tag]] native_chosen_path_transition [nssoc_hold_jstr [$selected edge]] raw_graph_paths $endpoint_paths]]
            }
        }
    } finally {close $stream}
    # Same unmodified strict equality guard, now applied to comparable raw
    # minima instead of the fuzzy-selected native aggregate.
    nssoc_original_assert_path_coverage $graph_minima $minima
    nssoc_hold_assert_coverage $::expected [dict keys $graph_minima] $negative [sta::endpoint_violation_count $::delay]
    lappend ::nssoc_graph_checks [nssoc_hold_jobject [dict create delay [nssoc_hold_jstr $::delay] endpoints [dict size $graph_minima] constrained $constrained raw_graph_paths $raw_count negative $negative graph_minimum_exactly_equals_pathend_minimum true]]
}
proc nssoc_graph_finish {output} {
    if {[llength $::nssoc_graph_checks]!=2} {error "Incomplete min/max graph proof"}
    set result [dict create status [nssoc_hold_jstr COMPLETE_EXACT_GRAPH_PATH_COVERAGE_REQUIRES_NATIVE_SELECTION_CHECK] accepted false checks "\[[join $::nssoc_graph_checks ,]\]" mismatches "\[[join $::nssoc_graph_mismatches ,]\]" original_guard_failures "\[[join $::nssoc_graph_failures ,]\]" value_units [nssoc_hold_jstr seconds]]
    nssoc_hold_write_json $output [nssoc_hold_jobject $result]
    puts NSSOC_EXACT_GRAPH_PATH_COVERAGE_COMPLETE
}
