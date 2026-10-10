# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# One explicit non-inverting buffer on the pinned C10 RF24 syndrome connection.
proc nssoc_xor_preflight {} {
    set block [ord::get_db_block]
    if {![llength [info commands insert_buffer]]} {error "Native insert_buffer API unavailable"}
    foreach inst [$block getInsts] {
        if {[string match nssoc_xor_buf2* [$inst getName]]} {error "XOR buffer already exists"}
    }
    foreach net [$block getNets] {
        if {[string match nssoc_xor_bufnet* [$net getName]]} {error "XOR buffer net already exists"}
    }
    set net [$block findNet _017423_]
    if {$net eq "NULL" || [llength [$net getITerms]] != 2 || [llength [$net getBTerms]] != 0} {
        error "XOR target must have exactly one driver and one sink"
    }
    foreach name {_071517_ _071519_} master {sg13g2_xor2_1 sg13g2_xnor2_1} pin {X A} direction {OUTPUT INPUT} {
        set inst [$block findInst $name]
        if {$inst eq "NULL" || [[$inst getMaster] getName] ne $master || ![$inst isPlaced] || [$inst isFixed] || [$inst isDoNotTouch]} {
            error "XOR target instance identity/status differs: $name"
        }
        set term [$inst findITerm $pin]
        if {$term eq "NULL" || [$term getNet] ne $net || [[$term getMTerm] getIoType] ne $direction} {
            error "XOR target pin identity differs: $name/$pin"
        }
    }
    if {[[ord::get_db] findMaster sg13g2_buf_2] eq "NULL"} {error "Pinned buf2 master missing"}
    return $net
}

# Canonical full graph, including all original cells, pin directions, power
# connectivity and top ports. Contracting ONLY the new non-inverting buffer
# must reproduce the original byte stream. Placement is measured separately.
proc nssoc_xor_graph {path {insertion {}}} {
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
            if {$rename_net ne {} && $netname eq $rename_net} {set netname _017423_}
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
        if {$rename_net ne {} && $netname eq $rename_net} {set netname _017423_}
        puts $out [join [list port [nssoc_hold_field $name] "[$port getIoType]:[$port getSigType]" {} [nssoc_hold_field $netname]] \t]
    }
    close $out
}

proc nssoc_xor_insert {} {
    set net [nssoc_xor_preflight]
    set block [ord::get_db_block]
    set before {}; set oldnets {}
    foreach inst [$block getInsts] {dict set before [$inst getName] 1}
    foreach n [$block getNets] {dict set oldnets [$n getName] 1}
    set driver [$block findInst _071517_]
    lassign [$driver getLocation] x y
    set dbu [$block getDbUnitsPerMicron]
    if {$dbu <= 0} {error "Invalid XOR placement DBU"}
    set location [list [expr {double($x+[[$driver getMaster] getWidth])/$dbu+0.96}] [expr {double($y)/$dbu}]]
    insert_buffer -buffer_cell sg13g2_buf_2 -net _017423_ -location $location \
        -buffer_name nssoc_xor_buf2 -net_name nssoc_xor_bufnet
    set added {}; set addednets {}
    foreach inst [$block getInsts] {
        if {![dict exists $before [$inst getName]]} {lappend added [$inst getName]}
    }
    foreach n [$block getNets] {
        if {![dict exists $oldnets [$n getName]]} {lappend addednets [$n getName]}
    }
    if {[llength $added] != 1 || [llength $addednets] != 1 ||
            [llength [$block getInsts]] != [dict size $before]+1 ||
            [llength [$block getNets]] != [dict size $oldnets]+1} {error "XOR insertion did not add exactly one cell and net"}
    set row [dict create buffer [lindex $added 0] new_net [lindex $addednets 0] \
        original_net _017423_ driver _071517_/X sink _071519_/A master sg13g2_buf_2 \
        initial_instances [dict size $before] location_um $location]
    nssoc_xor_verify $row
    return $row
}

proc nssoc_xor_verify {row} {
    set block [ord::get_db_block]
    set buffer [$block findInst [dict get $row buffer]]
    if {$buffer eq "NULL" || [[$buffer getMaster] getName] ne "sg13g2_buf_2" ||
            [llength [$block getInsts]] != [dict get $row initial_instances]+1} {error "XOR buffer identity/growth changed"}
    set input [[$buffer findITerm A] getNet]
    set output [[$buffer findITerm X] getNet]
    if {$input eq "NULL" || $output eq "NULL" || $input eq $output ||
            [lsort [list [$input getName] [$output getName]]] ne [lsort [list _017423_ [dict get $row new_net]]]} {
        error "XOR buffer nets differ"
    }
    foreach net [list $input $output] instname {_071517_ _071519_} pin {X A} {
        if {[llength [$net getITerms]] != 2 || [llength [$net getBTerms]] != 0 ||
                [[[$block findInst $instname] findITerm $pin] getNet] ne $net} {error "XOR branch connectivity differs"}
    }
    lassign [[$block findInst _071517_] getLocation] dx dy
    lassign [$buffer getLocation] bx by
    if {abs($bx-$dx)+abs($by-$dy) > 50*[$block getDbUnitsPerMicron]} {error "Inserted buffer legalized farther than 50um from XOR"}
}

proc nssoc_xor_insertion_json {row} {
    set result {}
    foreach name {buffer new_net original_net driver sink master} {dict set result $name [nssoc_hold_jstr [dict get $row $name]]}
    dict set result initial_instances [dict get $row initial_instances]
    dict set result location_um "\[[join [dict get $row location_um] ,]\]"
    return [nssoc_hold_jobject $result]
}

proc nssoc_xor_verify_power {row} {
    set block [ord::get_db_block]
    set buffer [$block findInst [dict get $row buffer]]
    set driver [$block findInst _071517_]
    foreach pin {VDD VSS} type {POWER GROUND} {
        set term [$buffer findITerm $pin]
        set reference [[$driver findITerm $pin] getNet]
        if {$term eq "NULL" || $reference eq "NULL" || [$term getNet] ne $reference ||
                [$reference getSigType] ne $type} {error "XOR buffer supply pin is floating or differs: $pin"}
    }
}
