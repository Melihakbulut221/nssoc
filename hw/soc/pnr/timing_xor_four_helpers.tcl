# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Only the two connections measured after the frozen two-buffer trial.
proc nssoc_four_target {index} {
    switch -- $index {
        3 {return [dict create driver _072567_ driver_pin Y driver_master sg13g2_xnor2_1 sink _072570_ sink_pin A sink_master sg13g2_xnor2_1 original_net _018473_ prefix nssoc_rf30_buf]}
        4 {return [dict create driver _074829_ driver_pin Y driver_master sg13g2_nand4_1 sink _074831_ sink_pin B sink_master sg13g2_xor2_1 original_net _020735_ prefix nssoc_addr_buf]}
        default {error "Only fixed third and fourth targets are allowed"}
    }
}
proc nssoc_four_preflight {index} {
    set row [nssoc_four_target $index]
    set block [ord::get_db_block]
    if {![llength [info commands insert_buffer]]} {error "Native insert_buffer API unavailable"}
    set prefix [dict get $row prefix]
    foreach inst [$block getInsts] {if {[string match ${prefix}* [$inst getName]]} {error "Fixed buffer already exists"}}
    foreach n [$block getNets] {if {[string match ${prefix}net* [$n getName]]} {error "Fixed buffer net already exists"}}
    set net [$block findNet [dict get $row original_net]]
    if {$net eq "NULL" || [llength [$net getITerms]] != 2 || [llength [$net getBTerms]] != 0} {error "Fixed target requires exactly one driver and one sink"}
    foreach role {driver sink} direction {OUTPUT INPUT} {
        set inst [$block findInst [dict get $row $role]]
        if {$inst eq "NULL" || [[$inst getMaster] getName] ne [dict get $row ${role}_master] || ![$inst isPlaced] || [$inst isFixed] || [$inst isDoNotTouch]} {error "Fixed target instance identity/status differs"}
        set term [$inst findITerm [dict get $row ${role}_pin]]
        if {$term eq "NULL" || [$term getNet] ne $net || [[$term getMTerm] getIoType] ne $direction} {error "Fixed target pin identity differs"}
    }
    if {[[ord::get_db] findMaster sg13g2_buf_2] eq "NULL"} {error "Pinned buf2 master missing"}
    return $row
}
proc nssoc_four_insert {index} {
    set target [nssoc_four_preflight $index]
    set block [ord::get_db_block]
    set before {}; set oldnets {}
    foreach inst [$block getInsts] {dict set before [$inst getName] 1}
    foreach net [$block getNets] {dict set oldnets [$net getName] 1}
    set driver [$block findInst [dict get $target driver]]
    lassign [$driver getLocation] x y
    set dbu [$block getDbUnitsPerMicron]
    if {$dbu <= 0} {error "Invalid fixed target DBU"}
    set location [list [expr {double($x+[[$driver getMaster] getWidth])/$dbu+0.96}] [expr {double($y)/$dbu}]]
    set prefix [dict get $target prefix]
    insert_buffer -buffer_cell sg13g2_buf_2 -net [dict get $target original_net] -location $location -buffer_name $prefix -net_name ${prefix}net
    set added {}; set addednets {}
    foreach inst [$block getInsts] {if {![dict exists $before [$inst getName]]} {lappend added [$inst getName]}}
    foreach net [$block getNets] {if {![dict exists $oldnets [$net getName]]} {lappend addednets [$net getName]}}
    if {[llength $added] != 1 || [llength $addednets] != 1 || [llength [$block getInsts]] != [dict size $before]+1 || [llength [$block getNets]] != [dict size $oldnets]+1} {error "Fixed insertion must add exactly one cell and net"}
    set row [dict create index $index buffer [lindex $added 0] new_net [lindex $addednets 0] original_net [dict get $target original_net] \
        driver [dict get $target driver]/[dict get $target driver_pin] sink [dict get $target sink]/[dict get $target sink_pin] \
        master sg13g2_buf_2 initial_instances [dict size $before] location_um $location]
    nssoc_four_verify $row
    return $row
}
proc nssoc_four_verify {row} {
    set target [nssoc_four_target [dict get $row index]]
    set block [ord::get_db_block]
    set buffer [$block findInst [dict get $row buffer]]
    if {$buffer eq "NULL" || [[$buffer getMaster] getName] ne "sg13g2_buf_2" || [llength [$block getInsts]] != [dict get $row initial_instances]+1} {error "Fixed buffer identity/growth changed"}
    set input [[$buffer findITerm A] getNet]; set output [[$buffer findITerm X] getNet]
    if {$input eq "NULL" || $output eq "NULL" || [$input getName] ne [dict get $row new_net] || [$output getName] ne [dict get $target original_net]} {error "Fixed buffer direction/nets differ"}
    foreach net [list $input $output] role {driver sink} {
        if {[llength [$net getITerms]] != 2 || [llength [$net getBTerms]] != 0 || [[[$block findInst [dict get $target $role]] findITerm [dict get $target ${role}_pin]] getNet] ne $net} {error "Fixed branch connectivity differs"}
    }
    lassign [[$block findInst [dict get $target driver]] getLocation] dx dy
    lassign [$buffer getLocation] bx by
    if {abs($bx-$dx)+abs($by-$dy) > 50*[$block getDbUnitsPerMicron]} {error "Fixed buffer legalized farther than 50um from driver"}
}
proc nssoc_four_verify_power {row} {
    set target [nssoc_four_target [dict get $row index]]
    set block [ord::get_db_block]
    set buffer [$block findInst [dict get $row buffer]]; set driver [$block findInst [dict get $target driver]]
    foreach pin {VDD VSS} type {POWER GROUND} {
        set term [$buffer findITerm $pin]; set reference [[$driver findITerm $pin] getNet]
        if {$term eq "NULL" || $reference eq "NULL" || [$term getNet] ne $reference || [$reference getSigType] ne $type} {error "Fixed buffer power is floating or differs"}
    }
}
proc nssoc_four_verify_all {insertions} {
    set total [llength [[ord::get_db_block] getInsts]]
    if {$total != [dict get [lindex $insertions 0] initial_instances]+[llength $insertions]} {error "Four-buffer cumulative cell budget changed"}
    set number 0
    foreach row $insertions {
        incr number
        dict set row initial_instances [expr {$total-1}]
        switch -- $number {
            1 {nssoc_xor_verify $row; nssoc_xor_verify_power $row}
            2 {nssoc_xnor_verify $row; nssoc_xnor_verify_power $row}
            default {nssoc_four_verify $row; nssoc_four_verify_power $row}
        }
    }
}
proc nssoc_four_json {row} {
    set result {}
    foreach name {buffer new_net original_net driver sink master} {dict set result $name [nssoc_hold_jstr [dict get $row $name]]}
    foreach name {index initial_instances} {dict set result $name [dict get $row $name]}
    dict set result location_um "\[[join [dict get $row location_um] ,]\]"
    return [nssoc_hold_jobject $result]
}
