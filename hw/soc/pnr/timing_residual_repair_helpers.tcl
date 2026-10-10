# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# New bounded continuation. The completed margin producer remains immutable.
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_electrical_margin_helpers.tcl]
proc nssoc_residual_hold_preflight {endpoint expected_master} {
    if {[llength [info commands rsz::repair_hold_pin]] != 1} {error "Native repair_hold_pin unavailable"}
    if {![regexp {^([A-Za-z0-9_]+)/(D)$} $endpoint -> name port]} {error "Expected exact flop data endpoint"}
    set inst [[ord::get_db_block] findInst $name]
    if {$inst eq "NULL" || [[$inst getMaster] getName] ne $expected_master ||
        $expected_master ne "sg13g2_dfrbpq_1" || [$inst isDoNotTouch] || [$inst isFixed] || ![$inst isPlaced]} {
        error "Hold endpoint instance is missing, protected, unplaced or wrong master"
    }
    set term [$inst findITerm $port]
    if {$term eq "NULL" || [[$term getMTerm] getIoType] ne "INPUT"} {error "Hold endpoint terminal differs"}
    set net [$term getNet]
    if {$net eq "NULL" || [$net getSigType] ne "SIGNAL" || [$net isDoNotTouch]} {error "Hold data net is missing, protected or clock"}
    foreach load [$net getITerms] {
        if {[[$load getInst] isDoNotTouch]} {error "Hold data net touches protected instance"}
    }
    set pin [sta::get_port_pin_error residual_hold_endpoint $endpoint]
    if {[get_property $pin full_name] ne $endpoint || [llength [$pin vertices]] != 1} {error "Ambiguous hold STA endpoint"}
    return $pin
}
proc nssoc_residual_slack {pin} {
    set slack [nssoc_hold_slack [[lindex [$pin vertices] 0] slack min]]
    if {$slack eq "UNCONSTRAINED"} {error "Unconstrained residual endpoint"}
    return $slack
}
proc nssoc_residual_geometry {expected actual} {
    if {$actual ne $expected} {error "Residual repair changed an SRAM master/location/orientation"}
}
proc nssoc_residual_hold_repair {endpoint master} {
    set pin [nssoc_residual_hold_preflight $endpoint $master]
    set before [llength [[ord::get_db_block] getInsts]]
    set slack [nssoc_residual_slack $pin]
    set calls 0; set status NO_LONGER_NEGATIVE
    if {$slack < 0} {
        set calls 1; set status ONE_NATIVE_PASS_COMPLETE
        # The exact native SWIG method takes SI seconds and a FRACTION of
        # instance count. One pass can affect violating sibling loads too.
        # Observed growth is separately bounded because the native loop can
        # overshoot its internal counter inside one path.
        set code [catch {
            rsz::repair_hold_pin $pin 1e-10 2e-11 0 [expr {32.0/$before}] 1
        } message options]
        set after [llength [[ord::get_db_block] getInsts]]
        if {$after < $before || $after-$before > 32} {error "Residual hold call exceeded 32-cell bound"}
        if {$code} {return -options $options $message}
    }
    return [dict create endpoint [nssoc_hold_jstr $endpoint] master [nssoc_hold_jstr $master] \
        status [nssoc_hold_jstr $status] initial_slack_seconds $slack native_calls $calls \
        initial_instance_count $before actual_instance_count [llength [[ord::get_db_block] getInsts]] \
        setup_margin_seconds 1e-10 hold_margin_seconds 2e-11 allow_setup_violations false \
        max_passes 1 max_added_cells 32]
}
proc nssoc_residual_hold_reports {root stage targets} {
    foreach target $targets {
        lassign $target endpoint master
        set pin [sta::get_port_pin_error residual_report $endpoint]
        set label [string map {/ _} $endpoint]
        foreach corner [lsort [dict keys [nssoc_hold_corners]]] {
            foreach delay {min max} {
                report_checks -to $pin -corner $corner -path_delay $delay -format full_clock_expanded \
                    -fields {slew cap input nets fanout} -digits 9 \
                    > [file join $root "$stage-$label-$corner-$delay.rpt"]
            }
        }
    }
}
