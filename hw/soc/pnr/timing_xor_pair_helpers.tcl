# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Second fixed non-inverting buffer on the measured C10 RF11 two-sink cone.
# The original first-target helper remains immutable and is sourced separately.
proc nssoc_xnor_preflight {} {
    set block [ord::get_db_block]
    if {![llength [info commands insert_buffer]]} {error "Native insert_buffer API unavailable"}
    foreach inst [$block getInsts] {
        if {[string match nssoc_xnor_buf2* [$inst getName]]} {error "XNOR buffer already exists"}
    }
    foreach net [$block getNets] {
        if {[string match nssoc_xnor_bufnet* [$net getName]]} {error "XNOR buffer net already exists"}
    }
    set net [$block findNet _016495_]
    if {$net eq "NULL" || [llength [$net getITerms]] != 3 || [llength [$net getBTerms]] != 0} {
        error "XNOR target must have exactly one driver and two sinks"
    }
    foreach name {_070589_ _070602_ _072894_} master {sg13g2_xnor2_1 sg13g2_a22oi_1 sg13g2_a221oi_1} pin {Y A2 A1} direction {OUTPUT INPUT INPUT} {
        set inst [$block findInst $name]
        if {$inst eq "NULL" || [[$inst getMaster] getName] ne $master || ![$inst isPlaced] || [$inst isFixed] || [$inst isDoNotTouch]} {
            error "XNOR target instance identity/status differs: $name"
        }
        set term [$inst findITerm $pin]
        if {$term eq "NULL" || [$term getNet] ne $net || [[$term getMTerm] getIoType] ne $direction} {
            error "XNOR target pin identity differs: $name/$pin"
        }
    }
    if {[[ord::get_db] findMaster sg13g2_buf_2] eq "NULL"} {error "Pinned buf2 master missing"}
    return $net
}

proc nssoc_xnor_insert {} {
    set net [nssoc_xnor_preflight]
    set block [ord::get_db_block]
    set before {}; set oldnets {}
    foreach inst [$block getInsts] {dict set before [$inst getName] 1}
    foreach n [$block getNets] {dict set oldnets [$n getName] 1}
    set driver [$block findInst _070589_]
    lassign [$driver getLocation] x y
    set dbu [$block getDbUnitsPerMicron]
    if {$dbu <= 0} {error "Invalid XNOR placement DBU"}
    set location [list [expr {double($x+[[$driver getMaster] getWidth])/$dbu+0.96}] [expr {double($y)/$dbu}]]
    insert_buffer -buffer_cell sg13g2_buf_2 -net _016495_ -location $location \
        -buffer_name nssoc_xnor_buf2 -net_name nssoc_xnor_bufnet
    set added {}; set addednets {}
    foreach inst [$block getInsts] {
        if {![dict exists $before [$inst getName]]} {lappend added [$inst getName]}
    }
    foreach n [$block getNets] {
        if {![dict exists $oldnets [$n getName]]} {lappend addednets [$n getName]}
    }
    if {[llength $added] != 1 || [llength $addednets] != 1 ||
            [llength [$block getInsts]] != [dict size $before]+1 ||
            [llength [$block getNets]] != [dict size $oldnets]+1} {error "XNOR insertion did not add exactly one cell and net"}
    set row [dict create buffer [lindex $added 0] new_net [lindex $addednets 0] \
        original_net _016495_ driver _070589_/Y sinks {_070602_/A2 _072894_/A1} master sg13g2_buf_2 \
        initial_instances [dict size $before] location_um $location]
    nssoc_xnor_verify $row
    return $row
}

proc nssoc_xnor_verify {row} {
    set block [ord::get_db_block]
    set buffer [$block findInst [dict get $row buffer]]
    if {$buffer eq "NULL" || [[$buffer getMaster] getName] ne "sg13g2_buf_2" ||
            [llength [$block getInsts]] != [dict get $row initial_instances]+1} {error "XNOR buffer identity/growth changed"}
    set input [[$buffer findITerm A] getNet]
    set output [[$buffer findITerm X] getNet]
    if {$input eq "NULL" || $output eq "NULL" || $input eq $output ||
            [lsort [list [$input getName] [$output getName]]] ne [lsort [list _016495_ [dict get $row new_net]]]} {
        error "XNOR buffer nets differ"
    }
    if {[llength [$input getITerms]] != 2 || [llength [$output getITerms]] != 3 ||
            [llength [$input getBTerms]] || [llength [$output getBTerms]] ||
            [[[$block findInst _070589_] findITerm Y] getNet] ne $input} {error "XNOR driver branch differs"}
    foreach name {_070602_ _072894_} pin {A2 A1} {
        if {[[[$block findInst $name] findITerm $pin] getNet] ne $output} {error "XNOR sink branch differs"}
    }
    lassign [[$block findInst _070589_] getLocation] dx dy
    lassign [$buffer getLocation] bx by
    if {abs($bx-$dx)+abs($by-$dy) > 50*[$block getDbUnitsPerMicron]} {error "Inserted buffer legalized farther than 50um from XNOR"}
}

proc nssoc_xnor_insertion_json {row} {
    set result {}
    foreach name {buffer new_net original_net driver master} {dict set result $name [nssoc_hold_jstr [dict get $row $name]]}
    dict set result sinks {["_070602_/A2","_072894_/A1"]}
    dict set result initial_instances [dict get $row initial_instances]
    dict set result location_um "\[[join [dict get $row location_um] ,]\]"
    return [nssoc_hold_jobject $result]
}

proc nssoc_xnor_verify_power {row} {
    set block [ord::get_db_block]
    set buffer [$block findInst [dict get $row buffer]]
    set driver [$block findInst _070589_]
    foreach pin {VDD VSS} type {POWER GROUND} {
        set term [$buffer findITerm $pin]
        set reference [[$driver findITerm $pin] getNet]
        if {$term eq "NULL" || $reference eq "NULL" || [$term getNet] ne $reference ||
                [$reference getSigType] ne $type} {error "XNOR buffer supply pin is floating or differs: $pin"}
    }
}

proc nssoc_pair_graph {path {insertions {}}} {
    set block [ord::get_db_block]
    set skip {}; set renames {}
    foreach insertion $insertions {
        dict set skip [dict get $insertion buffer] 1
        dict set renames [dict get $insertion new_net] [dict get $insertion original_net]
    }
    set out [open $path {WRONLY CREAT EXCL}]
    puts $out "kind\tname\tmaster\tpin\tnet"
    set instances {}
    foreach inst [$block getInsts] {dict set instances [$inst getName] $inst}
    foreach name [lsort [dict keys $instances]] {
        if {[dict exists $skip $name]} {continue}
        set inst [dict get $instances $name]
        puts $out [join [list instance [nssoc_hold_field $name] [[$inst getMaster] getName] {} {}] \t]
        set terms {}
        foreach term [$inst getITerms] {dict set terms [[$term getMTerm] getName] $term}
        foreach pin [lsort [dict keys $terms]] {
            set term [dict get $terms $pin]; set net [$term getNet]; set netname {}
            if {$net ne "NULL"} {set netname [$net getName]}
            if {[dict exists $renames $netname]} {set netname [dict get $renames $netname]}
            set mt [$term getMTerm]
            puts $out [join [list pin [nssoc_hold_field $name] "[$mt getIoType]:[$mt getSigType]" [nssoc_hold_field $pin] [nssoc_hold_field $netname]] \t]
        }
    }
    set nets {}
    foreach net [$block getNets] {dict set nets [$net getName] $net}
    foreach name [lsort [dict keys $nets]] {
        if {[dict exists $renames $name]} {continue}
        puts $out [join [list net [nssoc_hold_field $name] [[dict get $nets $name] getSigType] {} {}] \t]
    }
    set ports {}
    foreach port [$block getBTerms] {dict set ports [$port getName] $port}
    foreach name [lsort [dict keys $ports]] {
        set port [dict get $ports $name]; set net [$port getNet]; set netname {}
        if {$net ne "NULL"} {set netname [$net getName]}
        if {[dict exists $renames $netname]} {set netname [dict get $renames $netname]}
        puts $out [join [list port [nssoc_hold_field $name] "[$port getIoType]:[$port getSigType]" {} [nssoc_hold_field $netname]] \t]
    }
    close $out
}

