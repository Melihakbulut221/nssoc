# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Only the 23 positive data buffers on two exact native slow setup paths.
# The current candidate is not accepted until fresh timing and equation proof.
set nssoc_target_buffers {
    {$abc$1826071$auto$blifparse.cc:397:parse_blif$1829320} sg13g2_buf_1
    {$abc$1826071$auto$blifparse.cc:397:parse_blif$1829321} sg13g2_buf_1
    {$abc$1826071$auto$blifparse.cc:397:parse_blif$1829322} sg13g2_buf_1
    {$abc$1826071$auto$blifparse.cc:397:parse_blif$1832236} sg13g2_buf_1
    {$abc$1826071$auto$blifparse.cc:397:parse_blif$1832237} sg13g2_buf_1
    {$abc$1826071$auto$blifparse.cc:397:parse_blif$1832346} sg13g2_buf_1
    {$abc$1826071$auto$blifparse.cc:397:parse_blif$1832385} sg13g2_buf_1
    {$abc$1826071$auto$blifparse.cc:397:parse_blif$1832716} sg13g2_buf_1
    {$abc$1826071$auto$blifparse.cc:397:parse_blif$1833580} sg13g2_buf_4
    {$abc$1826071$auto$blifparse.cc:397:parse_blif$1877866} sg13g2_buf_2
    {$abc$1826071$auto$blifparse.cc:397:parse_blif$1879510} sg13g2_buf_1
    {fanout1269} sg13g2_buf_4
    {fanout4550} sg13g2_buf_1
    {fanout5189} sg13g2_buf_1
    {fanout5662} sg13g2_buf_1
    {fanout6417} sg13g2_buf_2
    {fanout7153} sg13g2_buf_1
    {fanout744} sg13g2_buf_1
    {fanout7707} sg13g2_buf_1
    {fanout8217} sg13g2_buf_2
    {fanout852} sg13g2_buf_4
    {fanout858} sg13g2_buf_4
    {fanout8588} sg13g2_buf_2
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
}
if {[llength $nssoc_cells] != 23} {error "Changed target count"}
remove_buffers $nssoc_cells
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
