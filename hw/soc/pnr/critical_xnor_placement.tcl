# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Opt-in physical experiment for the checkpoint-9 critical XNOR connection.
# Sourcing does not mutate the design. Invoke apply AFTER removing fillers and
# before detailed placement; invoke verify immediately AFTER detailed placement
# and before timing optimization changes cells. Use an isolated checkpoint.
# This is a placement candidate, not a routed-timing improvement or signoff.
namespace eval nssoc_critical_placement {
    variable state {}
}

proc nssoc_critical_placement::distance {a b} {
    lassign $a ax ay
    lassign $b bx by
    return [expr {abs($ax-$bx)+abs($ay-$by)}]
}

proc nssoc_critical_placement::pins {inst} {
    set result {}
    foreach term [$inst getITerms] {
        set net [$term getNet]
        set net_name {}
        if {$net ne "NULL"} { set net_name [$net getName] }
        lappend result [list [[$term getMTerm] getName] $net_name]
    }
    return [lsort -index 0 $result]
}

proc nssoc_critical_placement::macro_snapshot {block} {
    set result {}
    foreach inst [$block getInsts] {
        set master [[$inst getMaster] getName]
        if {$master ni {SP6TSRAM512x64 DP8TSRAMDP256x16}} { continue }
        lappend result [list [$inst getName] $master [$inst getLocation] \
            [$inst getOrient] [$inst getPlacementStatus] [pins $inst]]
    }
    if {[llength $result] != 32} { error "Critical placement requires exactly 32 SRAM instances" }
    return [lsort -index 0 $result]
}

proc nssoc_critical_placement::validate {block} {
    set result {}
    foreach name {_072583_ _072584_} {
        set inst [$block findInst $name]
        if {$inst eq "NULL" || [[$inst getMaster] getName] ne "sg13g2_xnor2_1"} {
            error "Critical XNOR identity/master drift: $name"
        }
        if {![$inst isPlaced] || [$inst isFixed] || [$inst isDoNotTouch]} {
            error "Critical XNOR must be placed, movable and not dont-touch: $name"
        }
        lappend result $inst
    }
    lassign $result driver target
    set net [$block findNet _018489_]
    if {$net eq "NULL" || [llength [$net getITerms]] != 2 || [llength [$net getBTerms]] != 0} {
        error "Critical net must have exactly one driver and one sink, without external terminals"
    }
    foreach inst [list $driver $target] pin {Y B} io {OUTPUT INPUT} {
        set term [$inst findITerm $pin]
        if {$term eq "NULL" || [$term getNet] ne $net || [[$term getMTerm] getIoType] ne $io} {
            error "Critical connection identity drift: [$inst getName]/$pin"
        }
    }
    return $result
}

proc nssoc_critical_placement::receipt {status} {
    variable state
    dict set state status $status
    if {[info exists ::env(STEP_DIR)]} {
        set output [open [file join $::env(STEP_DIR) critical-placement.tcldict] w]
        puts $output $state
        close $output
    }
}

proc nssoc_apply_critical_placement {} {
    variable nssoc_critical_placement::state
    if {$state ne {}} { error "Critical placement already initialized in this process" }
    set block [ord::get_db_block]
    if {[$block getDbUnitsPerMicron] <= 0} { error "Invalid database distance unit" }
    lassign [nssoc_critical_placement::validate $block] driver target
    set orient [$target getOrient]
    if {$orient ni {R0 MX}} { error "Unsupported target orientation: $orient" }
    set master [$target getMaster]
    set site [$master getSite]
    if {$site eq "NULL"} { error "Target master has no placement site" }
    set width [$master getWidth]
    set height [$master getHeight]
    set before [$target getLocation]
    set driver_before [$driver getLocation]
    lassign $before bx by
    lassign $driver_before dx dy
    # Halfway is deliberately bounded: do not collapse the entire cone into the
    # driver location. Other fanins/fanouts can still worsen; STA must decide.
    set ax [expr {($bx+$dx)/2}]
    set ay [expr {($by+$dy)/2}]
    set old_distance [nssoc_critical_placement::distance $before $driver_before]
    set macros [nssoc_critical_placement::macro_snapshot $block]
    set obstacles {}
    foreach inst [$block getInsts] {
        if {[$inst isBlock] || [$inst isFixed]} {
            set box [$inst getBBox]
            lappend obstacles [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
        }
    }
    set core [$block getCoreArea]
    set chosen {}
    set score {}
    foreach row [$block getRows] {
        if {[$row getDirection] ne "HORIZONTAL" || [$row getOrient] ne $orient ||
            [$row getSite] ne $site || [[$row getSite] getHeight] != $height} { continue }
        set box [$row getBBox]
        set y [$box yMin]
        if {$y < [$core yMin] || $y+$height > [$core yMax]} { continue }
        set lo [expr {max([$box xMin], [$core xMin])}]
        set hi [expr {min([$box xMax], [$core xMax])-$width}]
        set pitch [$row getSpacing]
        lassign [$row getOrigin] origin_x origin_y
        if {$pitch <= 0 || $lo > $hi} { continue }
        # Include obstacle edges so a blocked midpoint can move to a nearby site.
        set anchors [list $ax $lo $hi]
        foreach obstacle $obstacles {
            lassign $obstacle ox0 oy0 ox1 oy1
            if {$y < $oy1 && $y+$height > $oy0} {
                lappend anchors [expr {$ox0-$width}] $ox1
            }
        }
        foreach anchor $anchors {
            set x [expr {$origin_x+round(double($anchor-$origin_x)/$pitch)*$pitch}]
            set x [expr {max($origin_x+int(ceil(double($lo-$origin_x)/$pitch))*$pitch,
                min($x,$origin_x+int(floor(double($hi-$origin_x)/$pitch))*$pitch))}]
            if {$x < $lo || $x > $hi} { continue }
            set blocked 0
            foreach obstacle $obstacles {
                lassign $obstacle ox0 oy0 ox1 oy1
                if {$x < $ox1 && $x+$width > $ox0 && $y < $oy1 && $y+$height > $oy0} {
                    set blocked 1
                    break
                }
            }
            if {$blocked} { continue }
            set location [list $x $y]
            if {[nssoc_critical_placement::distance $location $driver_before] >= $old_distance} { continue }
            set candidate_score [nssoc_critical_placement::distance $location [list $ax $ay]]
            if {$chosen eq {} || $candidate_score < $score} {
                set chosen $location
                set score $candidate_score
                set chosen_row [$row getName]
            }
        }
    }
    if {$chosen eq {}} { error "No core row/site candidate shortens the critical connection" }
    set state [dict create status PREPARED driver _072583_ target _072584_ net _018489_ \
        method midpoint_then_nearest_compatible_unblocked_row_site \
        dbu_per_micron [$block getDbUnitsPerMicron] before_location_dbu $before \
        driver_before_location_dbu $driver_before candidate_location_dbu $chosen \
        candidate_row $chosen_row orientation $orient before_distance_dbu $old_distance \
        driver_pins [nssoc_critical_placement::pins $driver] \
        target_pins [nssoc_critical_placement::pins $target] macros $macros \
        timing_accepted false manufacturing_approval false]
    $target setLocation {*}$chosen
    nssoc_critical_placement::receipt MOVED_AWAITING_LEGALIZATION
    puts "NSSOC_CRITICAL_PLACEMENT_CANDIDATE $before -> $chosen; distance before $old_distance DBU"
}

proc nssoc_verify_critical_placement {} {
    variable nssoc_critical_placement::state
    if {$state eq {} || [dict get $state status] ne "MOVED_AWAITING_LEGALIZATION"} {
        error "No unverified critical-placement candidate"
    }
    set block [ord::get_db_block]
    lassign [nssoc_critical_placement::validate $block] driver target
    if {[$target getOrient] ne [dict get $state orientation] ||
        [nssoc_critical_placement::pins $driver] ne [dict get $state driver_pins] ||
        [nssoc_critical_placement::pins $target] ne [dict get $state target_pins] ||
        [nssoc_critical_placement::macro_snapshot $block] ne [dict get $state macros]} {
        error "Critical placement changed orientation, connectivity or SRAM placement"
    }
    set after [nssoc_critical_placement::distance [$target getLocation] [$driver getLocation]]
    if {$after >= [dict get $state before_distance_dbu]} {
        error "Legalization did not preserve a shorter critical connection; reject candidate"
    }
    dict set state after_location_dbu [$target getLocation]
    dict set state driver_after_location_dbu [$driver getLocation]
    dict set state after_distance_dbu $after
    nssoc_critical_placement::receipt SHORTER_AFTER_LEGALIZATION_STA_STILL_REQUIRED
    puts "NSSOC_CRITICAL_PLACEMENT_SHORTER [dict get $state before_distance_dbu] -> $after DBU; timing remains unverified"
}
