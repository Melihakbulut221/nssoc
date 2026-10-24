# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Only the 9 positive data buffers on measured onehot native setup paths.
# The current candidate is not accepted until fresh timing and equation proof.
set nssoc_target_buffers {
    {$abc$1804206$auto$blifparse.cc:397:parse_blif$1817130} sg13g2_buf_2
    {$abc$1804206$auto$blifparse.cc:397:parse_blif$1826858} sg13g2_buf_1
    {$abc$1804206$auto$blifparse.cc:397:parse_blif$1846017} sg13g2_buf_1
    {$abc$1804206$auto$blifparse.cc:397:parse_blif$1846394} sg13g2_buf_1
    {fanout383} sg13g2_buf_2
    {fanout409} sg13g2_buf_1
    {fanout601} sg13g2_buf_1
    {fanout655} sg13g2_buf_1
    {fanout7897} sg13g2_buf_1
}

set nssoc_block [ord::get_db_block]
proc nssoc_clock_connections {block} {
    set rows {}
    foreach net [$block getNets] {
        if {[$net getSigType] ne "CLOCK"} {continue}
        set pins {}
        foreach pin [$net getITerms] {lappend pins [list [[$pin getInst] getName] [[$pin getMTerm] getName]]}
        foreach pin [$net getBTerms] {lappend pins [list PORT [$pin getName]]}
        lappend rows [list [$net getName] [lsort $pins]]
    }
    return [lsort $rows]
}
set nssoc_clock_before [nssoc_clock_connections $nssoc_block]
if {[llength $nssoc_clock_before] == 0} {error "No native clock nets"}
set nssoc_before [dict create]
foreach inst [$nssoc_block getInsts] {
    dict set nssoc_before [$inst getName] [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]
}
set nssoc_cells {}
set nssoc_names {}
foreach {name master} $nssoc_target_buffers {
    set inst [$nssoc_block findInst $name]
    if {$inst eq "NULL" || $inst eq ""} {error "Missing exact target: $name"}
    if {[[$inst getMaster] getName] ne $master} {error "Changed target master: $name"}
    if {[$inst getPlacementStatus] in {FIXED FIRM COVER}} {error "Fixed target: $name"}
    set signals {}
    foreach pin [$inst getITerms] {
        if {[$pin getSigType] in {POWER GROUND}} {continue}
        lappend signals [[$pin getMTerm] getName]
        set net [$pin getNet]
        if {$net eq "NULL" || $net eq ""} {error "Unconnected target: $name"}
        if {[$net getSigType] ne "SIGNAL" || [llength [$net getBTerms]] != 0} {error "Clock/special/port target: $name"}
    }
    if {[lsort $signals] ne {A X}} {error "Not a positive A/X buffer: $name"}
    set cell [get_cells -quiet $name]
    if {[llength $cell] != 1} {error "Ambiguous STA target: $name"}
    lappend nssoc_cells {*}$cell
    lappend nssoc_names $name
}
if {[llength $nssoc_cells] != 9} {error "Changed target count"}
# This pinned native API resolves its argument list through get_cells.
# Pass expanded instance NAMES, never a nested list of SWIG object handles.
set nssoc_remove_body [info body remove_buffers]
if {![regexp {rsz::remove_buffers_cmd\s+\[get_cells\s+\$args\]} $nssoc_remove_body]} {error "Unsupported native remove_buffers argument policy"}
set nssoc_resolved [get_cells $nssoc_names]
if {[llength $nssoc_resolved] != 9 || [lsort $nssoc_resolved] ne [lsort $nssoc_cells]} {error "Native target name resolution changed"}
# Explicit empty selection is dangerous: reject it before invoking the command.
set nssoc_bad [get_cells -quiet {__nssoc_absent_target_negative_control__}]
if {[llength $nssoc_bad] != 0} {error "Missing-target resolution control failed"}
puts "NSSOC_TARGET_ARGUMENTS_VERIFIED names=9 resolved=9 missing_control=0"
remove_buffers {*}$nssoc_names
set nssoc_after [dict create]
foreach inst [$nssoc_block getInsts] {
    set name [$inst getName]
    dict set nssoc_after $name [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]
    if {![dict exists $nssoc_before $name] || [dict get $nssoc_after $name] ne [dict get $nssoc_before $name]} {error "Unbuffer changed retained instance: $name"}
}
set nssoc_removed {}
dict for {name value} $nssoc_before {
    if {![dict exists $nssoc_after $name]} {lappend nssoc_removed $name}
}
set nssoc_expected {}
foreach {name master} $nssoc_target_buffers {lappend nssoc_expected $name}
if {[lsort $nssoc_removed] ne [lsort $nssoc_expected]} {error "Native removal differs from exact targets"}
if {[nssoc_clock_connections $nssoc_block] ne $nssoc_clock_before} {error "Clock connectivity changed during data contraction"}
puts "NSSOC_TARGETED_UNBUFFER_PASS removed=[llength $nssoc_removed] retained=[dict size $nssoc_after] clock_nets=[llength $nssoc_clock_before]"
estimate_parasitics -placement
