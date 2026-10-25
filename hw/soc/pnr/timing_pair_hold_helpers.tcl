# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Reuse the immutable single-insertion implementation; only reserved names change.
set nssoc_pair_single_path [file join $::env(NSSOC_TARGETED_METHOD_ROOT) hw/soc/pnr/timing_explicit_hold_helpers.tcl]
if {[nssoc_hold_sha $nssoc_pair_single_path] ne "6d12da88eaf4e6f93c945ae125c4395690225abc5fa6d1f8d5d05267707149fc"} {error "Frozen single-delay helper differs"}
set nssoc_pair_f [open $nssoc_pair_single_path rb]
set nssoc_pair_source [read $nssoc_pair_f];close $nssoc_pair_f
source $nssoc_pair_single_path
foreach nssoc_pair_index {0 1} {
    namespace eval ::nssoc_pair_$nssoc_pair_index [string map [list \
        nssoc_explicit_sd3 nssoc_pair${nssoc_pair_index}_sd3 \
        nssoc_explicit_holdnet nssoc_pair${nssoc_pair_index}_net] $nssoc_pair_source]
}
unset nssoc_pair_source nssoc_pair_f nssoc_pair_index nssoc_pair_single_path
proc nssoc_pair_call {index operation args} {
    if {$index ni {0 1} || $operation ni {preflight vacancy insert verify}} {error "Unapproved pair operation"}
    return [::nssoc_pair_${index}::nssoc_explicit_$operation {*}$args]
}
proc nssoc_pair_insert {root index driver sink net places} {
    if {$index ni {0 1}} {error "Invalid pair index"}
    set directory [file join $root insert$index]
    if {[file exists $directory]} {error "Pair insertion output already exists"}
    file mkdir $directory
    return [nssoc_pair_call $index insert $directory $driver $sink $net $places]
}
proc nssoc_pair_contract {insertions} {
    if {[llength $insertions] ni {0 2}} {error "Pair contraction needs zero or exactly two identities"}
    set skip {};set rename {}
    if {![llength $insertions]} {return [list $skip $rename]}
    foreach row $insertions index {0 1} {
        foreach key {buffer new_net original_net driver sink master initial_instances initial_nets} {
            if {![dict exists $row $key]} {error "Incomplete pair identity"}
        }
        if {![regexp "^nssoc_pair${index}_sd3\[0-9\]+$" [dict get $row buffer]] ||
            ![regexp "^nssoc_pair${index}_net\[0-9\]+$" [dict get $row new_net]] ||
            [dict get $row master] ne "sg13g2_dlygate4sd3_1"} {error "Pair prefix/master differs"}
        dict set skip [dict get $row buffer] 1
        dict set rename [dict get $row new_net] [dict get $row original_net]
    }
    if {[llength $insertions]} {
        lassign $insertions first second
        foreach key {driver sink original_net buffer new_net} {if {[dict get $first $key] eq [dict get $second $key]} {error "Pair branches are not disjoint"}}
        if {[llength [lsort -unique [list [dict get $first driver] [dict get $first sink] [dict get $second driver] [dict get $second sink]]]] != 4} {error "Pair endpoint identities overlap"}
        foreach key {initial_instances initial_nets} {
            if {[dict get $second $key] != [dict get $first $key]+1} {error "Pair sequential census differs"}
        }
    }
    return [list $skip $rename]
}
proc nssoc_pair_verify {insertions} {
    if {[llength $insertions] != 2} {error "Exactly two inserted identities required"}
    nssoc_pair_contract $insertions
    set base [lindex $insertions 0];set block [ord::get_db_block]
    if {[llength [$block getInsts]] != [dict get $base initial_instances]+2 || [llength [$block getNets]] != [dict get $base initial_nets]+2} {error "Pair total cell/net census differs"}
    foreach row $insertions index {0 1} {
        # The frozen per-cell verifier expects its one-cell view of the total.
        # The actual recorded before-insertion census remains untouched above.
        set final_view [dict replace $row initial_instances [expr {[dict get $base initial_instances]+1}] initial_nets [expr {[dict get $base initial_nets]+1}]]
        nssoc_pair_call $index verify $final_view
    }
}
proc nssoc_pair_placement {path {insertions {}}} {
    lassign [nssoc_pair_contract $insertions] skip rename
    set rows {}
    foreach inst [[ord::get_db_block] getInsts] {
        if {[dict exists $skip [$inst getName]]} {continue}
        dict set rows [$inst getName] [list [[$inst getMaster] getName] {*}[$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] [$inst isDoNotTouch]]
    }
    set f [open $path {WRONLY CREAT EXCL}]
    puts $f "instance\tmaster\tx_dbu\ty_dbu\torientation\tstatus\tdont_touch"
    foreach name [lsort [dict keys $rows]] {puts $f [join [list $name {*}[dict get $rows $name]] \t]}
    close $f
}
proc nssoc_pair_graph {path {insertions {}}} {
    lassign [nssoc_pair_contract $insertions] skip rename
    set block [ord::get_db_block];set out [open $path {WRONLY CREAT EXCL}]
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
            set term [dict get $terms $pin];set net [$term getNet];set netname {}
            if {$net ne "NULL"} {set netname [$net getName]}
            if {[dict exists $rename $netname]} {set netname [dict get $rename $netname]}
            set mt [$term getMTerm]
            puts $out [join [list pin [nssoc_hold_field $name] "[$mt getIoType]:[$mt getSigType]" [nssoc_hold_field $pin] [nssoc_hold_field $netname]] \t]
        }
    }
    set nets {}
    foreach net [$block getNets] {dict set nets [$net getName] $net}
    foreach name [lsort [dict keys $nets]] {
        if {[dict exists $rename $name]} {continue}
        puts $out [join [list net [nssoc_hold_field $name] [[dict get $nets $name] getSigType] {} {}] \t]
    }
    set ports {}
    foreach port [$block getBTerms] {dict set ports [$port getName] $port}
    foreach name [lsort [dict keys $ports]] {
        set port [dict get $ports $name];set net [$port getNet];set netname {}
        if {$net ne "NULL"} {set netname [$net getName]}
        if {[dict exists $rename $netname]} {set netname [dict get $rename $netname]}
        puts $out [join [list port [nssoc_hold_field $name] "[$port getIoType]:[$port getSigType]" {} [nssoc_hold_field $netname]] \t]
    }
    close $out
}
proc nssoc_pair_route {root name {insertions {}}} {
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
    nssoc_pair_placement [file join $root "$name-original-objects.tsv"] $insertions
}
