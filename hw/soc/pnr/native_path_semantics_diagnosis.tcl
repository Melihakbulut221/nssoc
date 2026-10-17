# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Diagnostic mode ONLY: preserve each original guard failure, never accept census.
rename nssoc_hold_assert_path_coverage nssoc_original_assert_path_coverage
set nssoc_semantic_mismatches {}
set nssoc_semantic_failures {}
proc nssoc_hold_assert_path_coverage {vertices minima} {
    set code [catch {nssoc_original_assert_path_coverage $vertices $minima} message]
    if {$code ni {0 1}} {error "Unexpected original guard completion code"}
    if {$code==1} {
        lappend ::nssoc_semantic_failures [nssoc_hold_jobject [dict create delay [nssoc_hold_jstr $::delay] error [nssoc_hold_jstr $message]]]
    }
    dict for {name value} $vertices {
        set path UNCONSTRAINED
        if {[dict exists $minima $name]} {set path [dict get $minima $name]}
        if {$value ne $path} {
            set now [nssoc_hold_slack [[dict get $::census $name] slack $::delay]]
            lappend ::nssoc_semantic_mismatches [dict create endpoint $name delay $::delay vertex_before $value path_minimum $path vertex_after_census $now]
        }
    }
}
proc nssoc_semantics_finish {output} {
    set rows {};set native_pins {}
    foreach pin [sta::endpoints] {dict set native_pins [get_property $pin full_name] $pin}
    foreach record $::nssoc_semantic_mismatches {
        set name [dict get $record endpoint];set delay [dict get $record delay]
        set pin [dict get $native_pins $name];set queries {}
        foreach corner [lsort [dict keys $::corners]] {
            foreach rf {rise fall} {
                foreach limit {1 20} {
                    set slacks {}
                    foreach path [find_timing_paths -to [list $pin] -corner $corner -path_delay ${delay}_${rf} -group_path_count [expr {$::expected+1}] -endpoint_path_count $limit] {
                        if {[get_property [$path pin] full_name] ne $name || [$path is_unconstrained]} {error "Unexpected targeted endpoint"}
                        lappend slacks [nssoc_hold_number [$path slack]]
                    }
                    lappend queries [nssoc_hold_jobject [dict create corner [nssoc_hold_jstr $corner] transition [nssoc_hold_jstr $rf] endpoint_path_limit $limit path_slacks_seconds "\[[join $slacks ,]\]"]]
                }
            }
        }
        set row {}
        dict for {k v} $record {dict set row $k [nssoc_hold_jstr $v]}
        dict set row vertex_after_targeted [nssoc_hold_jstr [nssoc_hold_slack [[dict get $::census $name] slack $delay]]]
        dict set row targeted_queries "\[[join $queries ,]\]"
        lappend rows [nssoc_hold_jobject $row]
    }
    set result [dict create status [nssoc_hold_jstr COMPLETE_NATIVE_SEMANTICS_DIAGNOSIS_NOT_CENSUS_ACCEPTANCE] accepted false mismatch_count [llength $rows] mismatches "\[[join $rows ,]\]" original_guard_failures "\[[join $::nssoc_semantic_failures ,]\]" value_units [nssoc_hold_jstr seconds]]
    nssoc_hold_write_json $output [nssoc_hold_jobject $result]
    puts NSSOC_NATIVE_SEMANTICS_DIAGNOSIS_COMPLETE
}
