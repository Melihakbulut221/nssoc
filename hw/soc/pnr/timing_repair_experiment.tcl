# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Opt-in experiments; sourcing this file does not change a loaded design.
# See docs/106-timing-repair-research.md. These are NOT validated chip results.
# The caller must load the same isolated post-CTS checkpoint, propagated clocks,
# all corners, global-route parasitics and macro/dont-touch constraints in each
# experiment, then legalize, update routing/parasitics and measure every result.
# Never source this into the already running, hash-pinned repair controller.
proc nssoc_timing_experiment {profile} {
    switch -- $profile {
        setup_baseline { set repairs 1 }
        setup_batch4 { set repairs 4 }
        hold_guarded {
            # Deliberately omit -allow_setup_violations. Existing setup failures
            # still require before/after comparison; this is not an STA waiver.
            repair_timing -hold -setup_margin 0.1 -hold_margin 0.15 \
                -max_iterations 100 -max_buffer_percent 40 -verbose
            return
        }
        hold_guarded_targeted {
            # Opt-in only: current pinned campaigns never select this profile.
            # Remaining non-negative paths below +0.15 ns still need
            # separate repair; this bounded batch is not a closure waiver.
            nssoc_hold_guarded_targeted 16
            return
        }
        default { error "Unknown NSSOC timing experiment: $profile" }
    }
    # Change only repairs-per-pass between A and B. The native engine treats it
    # as an upper bound and may perform fewer moves or revert unsuccessful ones.
    repair_timing -setup -setup_margin 0.1 -max_iterations 100 \
        -max_repairs_per_pass $repairs -repair_tns 100 \
        -max_buffer_percent 40 -skip_buffer_removal -skip_size_down -verbose
}

# Pinned dcf36133 native/debug API: repair_hold_pin selects one endpoint, keeps
# the same setup guard, and checks max_passes between that endpoint's passes.
# Unlike repair_timing -hold, it cannot sweep thousands of other endpoints
# before rechecking the iteration limit. The caller must first initialize
# detailed placement, propagated clocks and parasitics, and still perform its
# usual legalization, full before/after timing/electrical checks and acceptance.
# A pass may visit every driver on one path: this is not a wall-clock limit.
proc nssoc_hold_check_batch_budget {initial budget endpoint phase native_error} {
    set actual [llength [[ord::get_db_block] getInsts]]
    set growth [expr {$actual - $initial}]
    if {$growth < 0 || $growth > $budget} {
        set receipt [dict create status GLOBAL_BUFFER_BUDGET_VIOLATION \
            endpoint $endpoint phase $phase initial_instance_count $initial \
            global_buffer_budget $budget actual_instance_count $actual \
            actual_instance_growth $growth native_error $native_error \
            candidate_accepted false signoff false]
        set stream [open [file join $::env(STEP_DIR) hold-targeted-budget-failure.tcldict] \
            {WRONLY CREAT EXCL}]
        puts $stream $receipt
        close $stream
        error "Targeted hold global buffer budget violated: growth=$growth budget=$budget; candidate rejected"
    }
    return [list $actual $growth [expr {$budget - $growth}]]
}

proc nssoc_hold_guarded_targeted {{limit 16}} {
    if {![string is integer -strict $limit] || $limit < 1 || $limit > 32} {
        error "Targeted hold limit must be an integer from 1 through 32"
    }
    if {![info exists ::env(STEP_DIR)] || ![file isdirectory $::env(STEP_DIR)]} {
        error "An existing isolated STEP_DIR is required for target evidence"
    }
    foreach receipt {hold-targeted-selection.tcldict hold-targeted-result.tcldict \
            hold-targeted-budget-failure.tcldict} {
        if {[file exists [file join $::env(STEP_DIR) $receipt]]} {
            error "An immutable targeted hold receipt already exists: $receipt"
        }
    }
    if {[llength [info commands rsz::repair_hold_pin]] != 1} {
        error "The pinned native repair_hold_pin API is unavailable"
    }
    if {abs([sta::unit_scale time] - 1.0e-9) > 1.0e-15} {
        error "The targeted profile requires the existing nanosecond timing unit"
    }
    est::check_parasitics
    set corners [list]
    foreach corner [sta::corners] {lappend corners [$corner name]}
    if {[llength $corners] == 0} {error "No loaded timing corners"}
    set corners [lsort $corners]

    # Select the worst distinct negative endpoints across every loaded corner.
    # Each group contributes up to limit paths; selecting the worst limit of
    # their union preserves global priority without requesting a full census.
    set candidates [dict create]
    foreach corner $corners {
        foreach path [find_timing_paths -corner $corner -path_delay min \
                -slack_max 0.0 -group_path_count $limit -endpoint_path_count 1 \
                -sort_by_slack] {
            set slack [get_property $path slack]
            if {$slack >= 0.0} {continue}
            set name [get_property [get_property $path endpoint] full_name]
            if {![dict exists $candidates $name] ||
                    $slack < [lindex [dict get $candidates $name] 0]} {
                dict set candidates $name [list $slack $name $corner]
            }
        }
    }
    set ranked [lsort -index 1 [dict values $candidates]]
    set ranked [lsort -real -index 0 $ranked]
    set targets [lrange $ranked 0 [expr {$limit - 1}]]
    set count_before [sta::endpoint_violation_count min]
    set initial_instances [llength [[ord::get_db_block] getInsts]]
    set global_buffer_budget [expr {int(floor(0.4 * $initial_instances))}]
    set selection [dict create profile hold_guarded_targeted \
        corners $corners setup_margin_ns 0.1 hold_margin_ns 0.15 \
        allow_setup_violations 0 max_buffer_fraction 0.4 \
        initial_instance_count $initial_instances global_buffer_budget $global_buffer_budget \
        max_passes_per_endpoint 1 endpoint_limit $limit \
        negative_endpoints_all_corners_before $count_before \
        selected_count [llength $targets] \
        target_fields {initial_slack_ns endpoint worst_corner} targets $targets \
        remaining_margin_repair_required true signoff false]
    # Never overwrite an earlier target snapshot within a step directory.
    set selection_path [file join $::env(STEP_DIR) hold-targeted-selection.tcldict]
    set stream [open $selection_path {WRONLY CREAT EXCL}]
    puts $stream $selection
    close $stream

    set calls [list]
    foreach target $targets {
        lassign $target initial_slack name corner
        lassign [nssoc_hold_check_batch_budget $initial_instances $global_buffer_budget \
            $name before_call {}] actual growth remaining
        if {$remaining == 0} {
            lappend calls [dict create endpoint $name status GLOBAL_BUFFER_BUDGET_EXHAUSTED \
                actual_instance_count $actual actual_instance_growth $growth]
            continue
        }
        # Pin names are captured before mutations; re-resolve pins and timing
        # because a prior target may have already repaired a shared path.
        set pin [sta::get_port_pin_error targeted_hold_endpoint $name]
        set still_negative false
        foreach path [find_timing_paths -to $pin -path_delay min \
                -slack_max 0.0 -group_path_count 1 -endpoint_path_count 1] {
            if {[get_property $path slack] < 0.0} {set still_negative true; break}
        }
        if {!$still_negative} {
            lappend calls [dict create endpoint $name status NO_LONGER_NEGATIVE]
            continue
        }
        puts "TARGETED_HOLD_BEGIN [list $name]"
        # The C++ insertion counter resets per endpoint and on rollback. Its
        # per-call 40% test can also overshoot inside one path. Enforce one fixed
        # batch budget using actual OpenDB instance growth, even on native error.
        set code [catch {
            rsz::repair_hold_pin $pin [sta::time_ui_sta 0.1] \
                [sta::time_ui_sta 0.15] 0 0.4 1
        } message options]
        lassign [nssoc_hold_check_batch_budget $initial_instances $global_buffer_budget \
            $name after_call $message] actual growth remaining
        if {$code != 0} {return -options $options $message}
        puts "TARGETED_HOLD_END [list $name]"
        lappend calls [dict create endpoint $name status ONE_NATIVE_PASS_COMPLETE \
            actual_instance_count $actual actual_instance_growth $growth \
            remaining_buffer_budget $remaining]
    }
    lassign [nssoc_hold_check_batch_budget $initial_instances $global_buffer_budget \
        {} complete {}] actual growth remaining
    set result [dict create calls $calls \
        initial_instance_count $initial_instances global_buffer_budget $global_buffer_budget \
        actual_instance_count $actual actual_instance_growth $growth \
        remaining_buffer_budget $remaining \
        negative_endpoints_all_corners_after [sta::endpoint_violation_count min] \
        remaining_margin_repair_required true signoff false]
    set stream [open [file join $::env(STEP_DIR) hold-targeted-result.tcldict] \
        {WRONLY CREAT EXCL}]
    puts $stream $result
    close $stream
    puts "TARGETED_HOLD_BATCH_COMPLETE_REQUIRES_FULL_REMEASUREMENT"
    return $result
}
