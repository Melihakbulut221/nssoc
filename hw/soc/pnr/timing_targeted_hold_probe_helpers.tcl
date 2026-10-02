# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# JSON adapters and a separate tiny native gate; no design load on source.
proc nssoc_targeted_assert_baseline {endpoints negative corners} {
    if {$endpoints != 23527 || $negative != 113 || [lsort $corners] ne {fast slow typical}} {
        error "Matched-before census differs from known C10: endpoints=$endpoints negative=$negative corners=$corners"
    }
    return [dict create endpoint_count $endpoints negative_vertex_endpoints $negative corners {["fast","slow","typical"]}]
}
proc nssoc_targeted_read {path} {
    set stream [open $path r]
    set value [read $stream]
    close $stream
    dict size $value
    return $value
}
proc nssoc_targeted_numbers {row names} {
    set result {}
    foreach name $names {dict set result $name [nssoc_hold_number [dict get $row $name]]}
    return $result
}
proc nssoc_targeted_selection_json {row} {
    set data [nssoc_targeted_numbers $row {setup_margin_ns hold_margin_ns allow_setup_violations max_buffer_fraction initial_instance_count global_buffer_budget max_passes_per_endpoint endpoint_limit negative_endpoints_all_corners_before selected_count}]
    foreach name {profile remaining_margin_repair_required signoff} {
        dict set data $name [expr {$name eq "profile" ? [nssoc_hold_jstr [dict get $row $name]] : [dict get $row $name]}]
    }
    set corners {}
    foreach name [dict get $row corners] {lappend corners [nssoc_hold_jstr $name]}
    dict set data corners "\[[join $corners ,]\]"
    set targets {}
    foreach target [dict get $row targets] {
        lassign $target slack endpoint corner
        lappend targets [nssoc_hold_jobject [dict create initial_slack_ns [nssoc_hold_number $slack] \
            endpoint [nssoc_hold_jstr $endpoint] worst_corner [nssoc_hold_jstr $corner]]]
    }
    dict set data targets "\[[join $targets ,]\]"
    return [nssoc_hold_jobject $data]
}
proc nssoc_targeted_result_json {row} {
    set data [nssoc_targeted_numbers $row {initial_instance_count global_buffer_budget actual_instance_count actual_instance_growth remaining_buffer_budget negative_endpoints_all_corners_after}]
    dict set data remaining_margin_repair_required [dict get $row remaining_margin_repair_required]
    dict set data signoff [dict get $row signoff]
    set calls {}
    foreach call [dict get $row calls] {
        set entry {}
        dict for {key value} $call {
            if {$key in {endpoint status}} {set value [nssoc_hold_jstr $value]} else {set value [nssoc_hold_number $value]}
            dict set entry $key $value
        }
        lappend calls [nssoc_hold_jobject $entry]
    }
    dict set data calls "\[[join $calls ,]\]"
    return [nssoc_hold_jobject $data]
}
proc nssoc_targeted_files_json {root {prefix {}}} {
    set files {}
    foreach path [lsort [glob -nocomplain -directory [file join $root $prefix] *]] {
        set name [file join $prefix [file tail $path]]
        if {[file type $path] eq "link"} {error "Symlink in targeted native evidence"}
        if {[file isdirectory $path]} {
            set files [dict merge $files [nssoc_targeted_files_json $root $name]]
        } else {
            dict set files $name [nssoc_hold_jobject [dict create bytes [file size $path] sha256 [nssoc_hold_jstr [nssoc_hold_sha $path]]]]
        }
    }
    return $files
}
proc nssoc_targeted_native_gate {} {
    foreach key {NSSOC_TARGETED_METHOD_ROOT NSSOC_TARGETED_CONTROL_OUT NSSOC_TARGETED_PDK_ROOT} {
        if {![info exists ::env($key)]} {error "$key is required"}
    }
    set root $::env(NSSOC_TARGETED_METHOD_ROOT)
    set out $::env(NSSOC_TARGETED_CONTROL_OUT)
    set fixture [file join $root sw/tests/timing_hold_targeted_native.tcl]
    set recipe [file join $root hw/soc/pnr/timing_repair_experiment.tcl]
    set fixture_hash [nssoc_hold_sha $fixture]
    set recipe_hash [nssoc_hold_sha $recipe]
    set executable [file normalize [info nameofexecutable]]
    set executable_hash [nssoc_hold_sha $executable]
    if {[file exists $out] || [file exists "$out.log"]} {error "Targeted native gate output already exists"}
    file mkdir [file dirname $out]
    set ::env(NSSOC_PDK_ROOT) $::env(NSSOC_TARGETED_PDK_ROOT)
    set ::env(NSSOC_TEST_OUT) $out
    set previous [pwd]
    cd $root
    set code [catch {exec $executable -exit $fixture > "$out.log" 2>@1} message options]
    cd $previous
    set exitcode 0
    if {$code} {
        set exitcode -1
        if {[dict exists $options -errorcode] && [lindex [dict get $options -errorcode] 0] eq "CHILDSTATUS"} {
            set exitcode [lindex [dict get $options -errorcode] 2]
        }
    }
    set receipt [dict create status [nssoc_hold_jstr [expr {$code ? "FAIL_TARGETED_NATIVE_GATE" : "PASS_TARGETED_NATIVE_GATE"}]] \
        returncode $exitcode executable_sha256 [nssoc_hold_jstr $executable_hash] \
        fixture_sha256 [nssoc_hold_jstr $fixture_hash] recipe_sha256 [nssoc_hold_jstr $recipe_hash] \
        timing_accepted false candidate_adopted false manufacturing_approval false]
    if {$code} {
        nssoc_hold_write_json "$out-failure.json" [nssoc_hold_jobject $receipt]
        error "Targeted native fixture failed before C10 load: $message"
    }
    if {[nssoc_hold_sha $fixture] ne $fixture_hash || [nssoc_hold_sha $recipe] ne $recipe_hash || [nssoc_hold_sha $executable] ne $executable_hash} {
        error "Targeted native gate inputs changed"
    }
    file copy "$out.log" [file join $out native.log]
    dict set receipt selection [nssoc_targeted_selection_json [nssoc_targeted_read [file join $out hold-targeted-selection.tcldict]]]
    dict set receipt result [nssoc_targeted_result_json [nssoc_targeted_read [file join $out hold-targeted-result.tcldict]]]
    set failure [nssoc_targeted_read [file join $out native-budget-overrun hold-targeted-budget-failure.tcldict]]
    dict set receipt overrun [nssoc_hold_jobject [nssoc_targeted_numbers $failure {initial_instance_count global_buffer_budget actual_instance_count actual_instance_growth}]]
    dict set receipt files [nssoc_hold_jobject [nssoc_targeted_files_json $out]]
    nssoc_hold_write_json [file join $out gate.json] [nssoc_hold_jobject $receipt]
    puts "NSSOC_TARGETED_NATIVE_GATE_PASS_BEFORE_C10_LOAD"
}
