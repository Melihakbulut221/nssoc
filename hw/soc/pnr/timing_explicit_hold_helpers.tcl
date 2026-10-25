# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Explicit identity delay insertion; loading this file does not alter a design.
proc nssoc_explicit_placement {path {skip {}}} {
    set rows {}
    foreach inst [[ord::get_db_block] getInsts] {
        if {[$inst getName] eq $skip} {continue}
        dict set rows [$inst getName] [list [[$inst getMaster] getName] {*}[$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] [$inst isDoNotTouch]]
    }
    set f [open $path {WRONLY CREAT EXCL}]
    puts $f "instance\tmaster\tx_dbu\ty_dbu\torientation\tstatus\tdont_touch"
    foreach name [lsort [dict keys $rows]] {puts $f [join [list $name {*}[dict get $rows $name]] \t]}
    close $f
}
proc nssoc_explicit_preflight {driver sink netname expected_place} {
    set block [ord::get_db_block]
    foreach inst [$block getInsts] {if {[string match nssoc_explicit_sd3* [$inst getName]]} {error "Explicit insertion instance prefix already exists"}}
    foreach n [$block getNets] {if {[string match nssoc_explicit_holdnet* [$n getName]]} {error "Explicit insertion net prefix already exists"}}
    set net [$block findNet $netname]
    if {$net eq "NULL" || [$net getSigType] ne "SIGNAL" || [$net isSpecial] || [$net isDoNotTouch] || [$net isConnectedByAbutment] ||
        [llength [$net getITerms]] != 2 || [llength [$net getBTerms]] != 0} {error "Explicit target must be an unprotected sole Q to D signal"}
    foreach name [list $driver $sink] pin {Q D} direction {OUTPUT INPUT} {
        set inst [$block findInst $name]
        if {$inst eq "NULL" || [[$inst getMaster] getName] ne "sg13g2_dfrbpq_1" || ![$inst isPlaced] || [$inst isFixed] || [$inst isDoNotTouch]} {error "Explicit endpoint identity/status differs"}
        set term [$inst findITerm $pin]
        if {$term eq "NULL" || [$term getNet] ne $net || [[$term getMTerm] getIoType] ne $direction} {error "Explicit endpoint connection differs"}
        if {[concat [$inst getLocation] [list [$inst getOrient] [$inst getPlacementStatus]]] ne [dict get $expected_place $name]} {error "Explicit endpoint source placement differs"}
        foreach supply {VDD VSS} type {POWER GROUND} {
            set pg [$inst findITerm $supply]
            if {$pg eq "NULL" || [$pg getNet] eq "NULL" || [[$pg getNet] getSigType] ne $type} {error "Explicit endpoint supply is unbound"}
        }
    }
    set master [[ord::get_db] findMaster sg13g2_dlygate4sd3_1]
    if {$master eq "NULL" || [$master getWidth] != 4320 || [$master getHeight] != 3780 || [$master getSite] eq "NULL"} {error "Source-bound sd3 shape/site differs"}
    foreach pin {A X VDD VSS} direction {INPUT OUTPUT INOUT INOUT} type {SIGNAL SIGNAL POWER GROUND} {
        set term [$master findMTerm $pin]
        if {$term eq "NULL" || [$term getIoType] ne $direction || [$term getSigType] ne $type} {error "Source-bound sd3 pinmap differs"}
    }
    if {[llength [$master getMTerms]] != 4} {error "Unexpected sd3 terminals"}
    return $net
}
proc nssoc_explicit_overlap {a b} {
    lassign $a x0 y0 x1 y1; lassign $b u0 v0 u1 v1
    return [expr {$x0 < $u1 && $x1 > $u0 && $y0 < $v1 && $y1 > $v0}]
}
proc nssoc_explicit_vacancy {driver {radius_um 10}} {
    if {$radius_um != 10} {error "Explicit vacancy radius must remain 10 microns"}
    set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]
    if {$dbu <= 0} {error "Invalid placement distance unit"}
    set inst [$block findInst $driver];set master [[ord::get_db] findMaster sg13g2_dlygate4sd3_1]
    lassign [$inst getLocation] dx dy
    set radius [expr {10*$dbu}];set width [$master getWidth];set height [$master getHeight]
    set search [list [expr {$dx-$radius}] [expr {$dy-$radius}] [expr {$dx+$radius+$width}] [expr {$dy+$radius+$height}]]
    set obstacles {}
    foreach i [$block getInsts] {
        if {![$i isPlaced]} {error "Unplaced original instance prevents a legal vacancy proof"}
        set box [$i getBBox];set bb [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
        if {[nssoc_explicit_overlap $search $bb]} {lappend obstacles $bb}
    }
    foreach blockage [$block getBlockages] {
        set box [$blockage getBBox];set bb [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
        if {[nssoc_explicit_overlap $search $bb]} {lappend obstacles $bb}
    }
    set core [$block getCoreArea];set candidates {}
    foreach row [$block getRows] {
        if {[$row getDirection] ne "HORIZONTAL" || [$row getSite] ne [$master getSite] ||
            [[$row getSite] getHeight] != $height || [$row getOrient] ni {R0 MX}} {continue}
        set box [$row getBBox];set y [$box yMin];set pitch [$row getSpacing]
        if {abs($y-$dy)>$radius || $pitch <= 0 || $y < [$core yMin] || $y+$height > [$core yMax]} {continue}
        lassign [$row getOrigin] origin_x origin_y
        set lo [expr {max([$box xMin],[$core xMin],$dx-$radius)}]
        set hi [expr {min([$box xMax]-$width,[$core xMax]-$width,$dx+$radius)}]
        for {set x [expr {$origin_x+int(ceil(double($lo-$origin_x)/$pitch))*$pitch}]} {$x <= $hi} {incr x $pitch} {
            set distance [expr {abs($x-$dx)+abs($y-$dy)}]
            if {$distance>$radius} {continue}
            set bb [list $x $y [expr {$x+$width}] [expr {$y+$height}]];set blocked 0
            foreach obstacle $obstacles {if {[nssoc_explicit_overlap $bb $obstacle]} {set blocked 1;break}}
            if {!$blocked} {lappend candidates [list $distance $x $y [$row getName] [$row getOrient]]}
        }
    }
    if {![llength $candidates]} {error "No existing legal sd3 vacancy within 10 microns; original cells will not move"}
    # Numerical distance/x/y, then row-name/orientation: deterministic tie break.
    set candidates [lsort -command nssoc_explicit_candidate_order $candidates]
    return [lindex $candidates 0]
}
proc nssoc_explicit_candidate_order {a b} {
    foreach index {0 1 2} {if {[lindex $a $index] != [lindex $b $index]} {return [expr {[lindex $a $index]<[lindex $b $index] ? -1 : 1}]}}
    return [string compare [lrange $a 3 end] [lrange $b 3 end]]
}

proc nssoc_explicit_graph {path {insertion {}}} {
    set block [ord::get_db_block]
    set skip {}; set rename_net {}
    if {$insertion ne {}} {
        set skip [dict get $insertion buffer]
        set rename_net [dict get $insertion new_net]
    }
    set out [open $path {WRONLY CREAT EXCL}]
    puts $out "kind\tname\tmaster\tpin\tnet"
    set instances {}
    foreach inst [$block getInsts] {dict set instances [$inst getName] $inst}
    foreach name [lsort [dict keys $instances]] {
        if {$name eq $skip} {continue}
        set inst [dict get $instances $name]
        puts $out [join [list instance [nssoc_hold_field $name] [[$inst getMaster] getName] {} {}] \t]
        set terms {}
        foreach term [$inst getITerms] {dict set terms [[$term getMTerm] getName] $term}
        foreach pin [lsort [dict keys $terms]] {
            set term [dict get $terms $pin]; set net [$term getNet]; set netname {}
            if {$net ne "NULL"} {set netname [$net getName]}
            if {$rename_net ne {} && $netname eq $rename_net} {set netname [dict get $insertion original_net]}
            set mt [$term getMTerm]
            puts $out [join [list pin [nssoc_hold_field $name] "[$mt getIoType]:[$mt getSigType]" [nssoc_hold_field $pin] [nssoc_hold_field $netname]] \t]
        }
    }
    set nets {}
    foreach net [$block getNets] {dict set nets [$net getName] $net}
    foreach name [lsort [dict keys $nets]] {
        if {$rename_net ne {} && $name eq $rename_net} {continue}
        puts $out [join [list net [nssoc_hold_field $name] [[dict get $nets $name] getSigType] {} {}] \t]
    }
    set ports {}
    foreach port [$block getBTerms] {dict set ports [$port getName] $port}
    foreach name [lsort [dict keys $ports]] {
        set port [dict get $ports $name]; set net [$port getNet]; set netname {}
        if {$net ne "NULL"} {set netname [$net getName]}
        if {$rename_net ne {} && $netname eq $rename_net} {set netname [dict get $insertion original_net]}
        puts $out [join [list port [nssoc_hold_field $name] "[$port getIoType]:[$port getSigType]" {} [nssoc_hold_field $netname]] \t]
    }
    close $out
}

proc nssoc_explicit_verify {row} {
    set block [ord::get_db_block];set buffer [$block findInst [dict get $row buffer]]
    if {$buffer eq "NULL" || [[$buffer getMaster] getName] ne "sg13g2_dlygate4sd3_1" ||
        [llength [$block getInsts]] != [dict get $row initial_instances]+1 || [llength [$block getNets]] != [dict get $row initial_nets]+1} {error "Explicit cell/net census differs"}
    set input [[$buffer findITerm A] getNet];set output [[$buffer findITerm X] getNet]
    if {$input eq "NULL" || $output eq "NULL" || $input eq $output ||
        [lsort [list [$input getName] [$output getName]]] ne [lsort [list [dict get $row original_net] [dict get $row new_net]]]} {error "Explicit buffer nets differ"}
    foreach net [list $input $output] name [list [dict get $row driver] [dict get $row sink]] pin {Q D} {
        if {[llength [$net getITerms]] != 2 || [llength [$net getBTerms]] != 0 || [$net getSigType] ne "SIGNAL" ||
            [[[$block findInst $name] findITerm $pin] getNet] ne $net} {error "Explicit sole-branch topology changed"}
    }
    set driver [$block findInst [dict get $row driver]]
    foreach pin {VDD VSS} type {POWER GROUND} {
        set reference [[$driver findITerm $pin] getNet];set term [$buffer findITerm $pin]
        if {$reference eq "NULL" || [$term getNet] ne $reference || [$reference getSigType] ne $type} {error "Explicit delay supply is floating/different"}
    }
    if {[$buffer getLocation] ne [dict get $row location_dbu] || [$buffer getOrient] ne [dict get $row orientation] || [$buffer getPlacementStatus] ne "PLACED"} {error "Explicit chosen vacancy changed"}
    check_placement -verbose
}
proc nssoc_explicit_insert {root driver sink netname expected_place} {
    nssoc_explicit_preflight $driver $sink $netname $expected_place
    set block [ord::get_db_block]
    set chosen [nssoc_explicit_vacancy $driver]
    lassign $chosen distance x y rowname orient
    set row [dict create buffer nssoc_explicit_sd3 new_net nssoc_explicit_holdnet original_net $netname \
        driver $driver sink $sink master sg13g2_dlygate4sd3_1 initial_instances [llength [$block getInsts]] \
        initial_nets [llength [$block getNets]] location_dbu [list $x $y] orientation $orient \
        row_name $rowname distance_dbu $distance dbu_per_micron [$block getDbUnitsPerMicron] radius_um 10]
    nssoc_explicit_graph [file join $root graph-before.tsv]
    nssoc_explicit_placement [file join $root objects-before.tsv]
    set oldinst {};set oldnets {}
    foreach i [$block getInsts] {dict set oldinst [$i getName] 1}
    foreach n [$block getNets] {dict set oldnets [$n getName] 1}
    set dbu [$block getDbUnitsPerMicron]
    insert_buffer -buffer_cell sg13g2_dlygate4sd3_1 -net $netname \
        -location [list [expr {double($x)/$dbu}] [expr {double($y)/$dbu}]] \
        -buffer_name nssoc_explicit_sd3 -net_name nssoc_explicit_holdnet
    set added {};set addednets {}
    foreach i [$block getInsts] {if {![dict exists $oldinst [$i getName]]} {lappend added [$i getName]}}
    foreach n [$block getNets] {if {![dict exists $oldnets [$n getName]]} {lappend addednets [$n getName]}}
    if {[llength $added] != 1 || [llength $addednets] != 1 ||
        ![regexp {^nssoc_explicit_sd3[0-9]+$} [lindex $added 0]] || ![regexp {^nssoc_explicit_holdnet[0-9]+$} [lindex $addednets 0]]} {error "Native insertion did not add exactly the approved instance/net prefixes"}
    dict set row buffer [lindex $added 0];dict set row new_net [lindex $addednets 0]
    set buffer [$block findInst [dict get $row buffer]]
    $buffer setOrient $orient
    $buffer setLocation $x $y
    $buffer setPlacementStatus PLACED
    foreach supply {VDD VSS} {[$buffer findITerm $supply] connect [[[$block findInst $driver] findITerm $supply] getNet]}
    nssoc_explicit_verify $row
    nssoc_explicit_graph [file join $root graph-after-contracted.tsv] $row
    nssoc_explicit_placement [file join $root objects-after-contracted.tsv] [dict get $row buffer]
    foreach prefix {graph objects} {
        if {[nssoc_hold_sha [file join $root $prefix-before.tsv]] ne [nssoc_hold_sha [file join $root $prefix-after-contracted.tsv]]} {error "Explicit insertion changed an original object/connection"}
    }
    return $row
}
proc nssoc_explicit_json {row} {
    set result {}
    dict for {key value} $row {
        if {$key eq "location_dbu"} {dict set result $key "\[[join $value ,]\]"} elseif {$key in {initial_instances initial_nets distance_dbu dbu_per_micron radius_um}} {
            dict set result $key $value
        } else {dict set result $key [nssoc_hold_jstr $value]}
    }
    return [nssoc_hold_jobject $result]
}
# Match original GRT preparation/order, with no detailed placement or repair.
proc nssoc_explicit_route {root name {skip {}}} {
    foreach net [[ord::get_db_block] getNets] {set wire [$net getWire];if {$wire ne "NULL"} {odb::dbWire_destroy $wire}}
    source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
    source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
    estimate_parasitics -global_routing
    global_route -start_incremental
    global_route -end_incremental
    estimate_parasitics -global_routing
    sta::delays_invalid
    sta::find_timing -full_update
    check_placement -verbose
    nssoc_explicit_placement [file join $root "$name-original-objects.tsv"] $skip
}
proc nssoc_explicit_observe {root name driver sink} {
    nssoc_hold_write_json [file join $root "$name-observation.json"] [nssoc_hold_jobject [nssoc_combined_metrics]]
    foreach corner [lsort [dict keys [nssoc_hold_corners]]] {
        foreach delay {min max} {
            foreach edge {rise fall} {
                report_checks -from [get_pins $driver/CLK] -${edge}_to [get_pins $sink/D] -corner $corner \
                    -path_delay $delay -format full_clock_expanded -fields {slew cap input fanout} -digits 9 \
                    > [file join $root "$name-$corner-$delay-$edge.rpt"]
            }
        }
    }
}
