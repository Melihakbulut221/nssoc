# SPDX-License-Identifier: Apache-2.0
# Only the known CTS8 bus root: two positive buffers, eight old sinks each.
set eco_block [ord::get_db_block]
set eco_root [$eco_block findInst clkbuf_0_clk_bus]
if {$eco_root eq "NULL" || $eco_root eq ""} {error "Missing bus root"}
set eco_master [$eco_root getMaster]
if {[$eco_master getName] ne "sg13g2_buf_16"} {error "Unexpected clock root master"}
set eco_x [$eco_root findITerm X]
set eco_net [$eco_x getNet]
if {$eco_net eq "NULL"} {error "Missing clock output net"}
if {[llength [$eco_net getBTerms]] != 0} {error "Unexpected clock BTerms"}
set eco_loads {}
set eco_drivers {}
foreach pin [$eco_net getITerms] {
    if {[$pin getIoType] eq "INPUT"} {
        set inst [$pin getInst]
        lassign [$inst getLocation] x y
        lappend eco_loads [list $x $y [$inst getName] $pin]
    } elseif {[$pin getIoType] eq "OUTPUT"} {
        lappend eco_drivers $pin
    } else {error "Unexpected clock pin direction"}
}
if {[llength $eco_loads] != 16 || $eco_drivers ne [list $eco_x]} {
    error "Bus-root endpoint census changed"
}
# Validate all names and supply pins before any mutation.
foreach i {0 1} {
    if {[$eco_block findInst core_bus_split_$i] ne "NULL" ||
        [$eco_block findNet core_bus_split_net_$i] ne "NULL"} {
        error "Clock ECO name collision"
    }
}
set eco_supplies [dict create]
foreach name {VDD VSS} {
    set pin [$eco_root findITerm $name]
    if {$pin eq "NULL" || [$pin getNet] eq "NULL"} {error "Missing root supply $name"}
    dict set eco_supplies $name [$pin getNet]
}
foreach name {A X VDD VSS} {
    if {[$eco_master findMTerm $name] eq "NULL"} {error "Missing buffer pin $name"}
}
# Record every original terminal, not just the moved endpoints.
set eco_expected [dict create]
set eco_masters [dict create]
set eco_bterms [dict create]
foreach inst [$eco_block getInsts] {
    dict set eco_masters $inst [$inst getMaster]
    foreach pin [$inst getITerms] {dict set eco_expected $pin [$pin getNet]}
}
foreach pin [$eco_block getBTerms] {dict set eco_bterms $pin [$pin getNet]}
set eco_expected_instances [expr {[llength [$eco_block getInsts]] + 2}]
set eco_expected_nets [expr {[llength [$eco_block getNets]] + 2}]
# Deterministic spatial grouping. Equal populations prevent new fanout excess.
set eco_loads [lsort -integer -index 0 $eco_loads]
set eco_created {}
foreach i {0 1} {
    set group [lrange $eco_loads [expr {$i*8}] [expr {$i*8+7}]]
    set net [odb::dbNet_create $eco_block core_bus_split_net_$i]
    $net setSigType CLOCK
    set inst [odb::dbInst_create $eco_block $eco_master core_bus_split_$i]
    set sx 0
    set sy 0
    foreach row $group {
        lassign $row x y name pin
        incr sx $x
        incr sy $y
    }
    $inst setLocation [expr {$sx/8}] [expr {$sy/8}]
    $inst setPlacementStatus PLACED
    [$inst findITerm A] connect $eco_net
    [$inst findITerm X] connect $net
    dict for {name supply} $eco_supplies {[$inst findITerm $name] connect $supply}
    foreach row $group {
        set pin [lindex $row 3]
        puts "CORE_CLOCK_ECO_MOVE [[ $pin getInst] getName]/[[$pin getMTerm] getName] core_bus_split_net_$i"
        $pin disconnect
        $pin connect $net
        dict set eco_expected $pin $net
    }
    lappend eco_created [list $inst $net]
}
proc verify_core_clock_split {} {
    global eco_block eco_expected eco_masters eco_bterms eco_created eco_net eco_x
    global eco_expected_instances eco_expected_nets eco_supplies
    if {[llength [$eco_block getInsts]] != $eco_expected_instances ||
        [llength [$eco_block getNets]] != $eco_expected_nets} {error "Unexpected cell/net census after ECO"}
    dict for {inst master} $eco_masters {
        if {[$inst getMaster] ne $master} {error "Original cell master changed"}
    }
    dict for {pin net} $eco_expected {
        if {[$pin getNet] ne $net} {error "Original terminal connectivity changed unexpectedly"}
    }
    dict for {pin net} $eco_bterms {
        if {[$pin getNet] ne $net} {error "Top port connectivity changed"}
    }
    if {[llength [$eco_net getITerms]] != 3 || [$eco_x getNet] ne $eco_net} {
        error "Clock root must drive exactly two buffer inputs"
    }
    foreach pair $eco_created {
        lassign $pair inst net
        if {[llength [$net getITerms]] != 9 || [llength [$net getBTerms]] != 0} {
            error "Split clock net must have one driver and eight loads"
        }
        if {[[$inst findITerm A] getNet] ne $eco_net || [[$inst findITerm X] getNet] ne $net} {
            error "Incorrect split buffer polarity/connectivity"
        }
        dict for {name supply} $eco_supplies {
            if {[[$inst findITerm $name] getNet] ne $supply} {error "Split supply mismatch"}
        }
    }
    puts "CORE_CLOCK_ECO_VERIFIED all_original_terminals_checked added_cells=2 added_nets=2 root_loads=2 branch_loads=8,8"
}
verify_core_clock_split
