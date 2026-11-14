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
set targets {
    place28029 sg13g2_buf_2 sg13g2_buf_16
    fanout67050 sg13g2_buf_1 sg13g2_buf_16
    {$abc$730691$auto$blifparse.cc:397:parse_blif$762276} sg13g2_nor2_1 sg13g2_nor2_2
    place24666 sg13g2_buf_1 sg13g2_buf_16
}
set crc_master ""
foreach candidate {sg13g2_a21oi_4 sg13g2_a21oi_2} {
    if {[[ord::get_db] findMaster $candidate] ne "NULL"} {set crc_master $candidate; break}
}
if {$crc_master eq ""} {error "No stronger A21OI master exists in frozen PDK"}
lappend targets {$abc$730691$auto$blifparse.cc:397:parse_blif$771273} sg13g2_a21oi_1 $crc_master
if {[llength $targets] != 15} {error "Expected precisely five driver replacements"}
proc master_pins {master} {
    set rows {}
    foreach p [$master getMTerms] {lappend rows [list [$p getName] [$p getIoType] [$p getSigType]]}
    return [lsort $rows]
}
set report [open "$::env(STEP_DIR)/targeted-resize.tsv" w]
puts $report "instance\tbefore\tafter"
foreach {name expected replacement} $targets {
    set inst [$block findInst $name]
    if {$inst eq "NULL" || [[$inst getMaster] getName] ne $expected} {error "Source driver identity differs: $name"}
    set target_master [[ord::get_db] findMaster $replacement]
    if {$target_master eq "NULL"} {error "Target master missing: $replacement"}
    if {[master_pins [$inst getMaster]] ne [master_pins $target_master]} {error "Master pin signature differs: $name"}
    if {![$inst swapMaster $target_master]} {error "Master replacement failed: $name"}
    if {[[$inst getMaster] getName] ne $replacement} {error "Replacement not applied: $name"}
    puts $report "$name\t$expected\t$replacement"
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
puts "NSSOC_FIVE_DRIVER_RESIZE_CONNECTIVITY_PRESERVED"
