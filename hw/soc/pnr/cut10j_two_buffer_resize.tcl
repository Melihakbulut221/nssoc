# SPDX-License-Identifier: Apache-2.0
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(NSSOC_DERATE_GUARD)
read_current_odb
set_propagated_clock [all_clocks]
foreach {name period} {clk_i 20 pcie_clk_i 4 eth_rx_clk_i 8 eth_tx_clk_i 8} {
    set c [get_clocks $name]
    if {[llength $c] != 1 || abs([get_property $c period]-$period)>1e-9} {error "Clock budget changed"}
}
set block [ord::get_db_block]
proc connections {block} {
    set rows {}
    foreach net [$block getNets] {
        set pins {}
        foreach p [$net getITerms] {lappend pins [list I [[$p getInst] getName] [[$p getMTerm] getName]]}
        foreach p [$net getBTerms] {lappend pins [list B [$p getName]]}
        lappend rows [list [$net getName] [$net getSigType] [lsort $pins]]
    }
    return [lsort $rows]
}
set before [connections $block]
set targets {place28029 sg13g2_buf_2 fanout67050 sg13g2_buf_1}
set master [ord::get_db_tech]
set target_master [[ord::get_db] findMaster sg13g2_buf_16]
if {$target_master eq "NULL"} {error "Target buffer missing"}
set report [open "$::env(STEP_DIR)/targeted-resize.tsv" w]
puts $report "instance\tbefore\tafter"
foreach {name expected} $targets {
    set inst [$block findInst $name]
    if {$inst eq "NULL" || [[$inst getMaster] getName] ne $expected} {error "Source driver identity differs: $name"}
    if {![ $inst swapMaster $target_master ]} {error "Buffer master replacement failed: $name"}
    if {[[$inst getMaster] getName] ne "sg13g2_buf_16"} {error "Replacement not applied"}
    puts $report "$name\t$expected\tsg13g2_buf_16"
}
close $report
if {[connections $block] ne $before} {error "Pin/net connectivity changed during resize"}
# Resizing/legalization invalidates detailed wires. Discard SIGNAL/CLOCK wires
# and all old guides, retain power special wires; regenerate GRT and DRT.
set removed 0
foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND}} {continue}
    set wire [$net getWire]
    if {$wire ne "NULL"} {odb::dbWire_destroy $wire; incr removed}
    foreach guide [$net getGuides] {odb::dbGuide_destroy $guide}
}
puts "NSSOC_INVALIDATED_SIGNAL_WIRES $removed"
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
if {[connections $block] ne $before} {error "Connectivity changed during legalization"}
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
estimate_parasitics -placement
write_views
puts "NSSOC_TWO_BUFFER_RESIZE_CONNECTIVITY_PRESERVED"
