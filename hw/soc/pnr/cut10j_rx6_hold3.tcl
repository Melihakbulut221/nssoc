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

# Isolate only bank6 A_ADDR6 after its existing final buffer. Functional identity
# of delay A->X is checked in all restored standard-cell Liberty models first.
set macro_name {u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank[6].u_mem}
set macro [$block findInst $macro_name]
if {$macro eq "NULL"} {error "Missing target SRAM"}
set endpoint [$macro findITerm {A_ADDR[6]}]
if {$endpoint eq "NULL"} {error "Missing target SRAM address pin"}
set old_net [$endpoint getNet]
if {$old_net eq "NULL" || [$old_net getName] ne "net66201"} {error "Unexpected target net"}
set driver [$block findInst wire66201]
if {$driver eq "NULL" || [[$driver getMaster] getName] ne "sg13g2_buf_4"} {error "Unexpected endpoint driver"}
if {[[$driver findITerm X] getNet] ne $old_net || [llength [$old_net getITerms]] != 2 || [llength [$old_net getBTerms]] != 0} {error "Endpoint branch identity/fanout differs"}
set delay_master [[ord::get_db] findMaster sg13g2_dlygate4sd3_1]
if {$delay_master eq "NULL"} {error "Missing delay cell"}
set anchor [$block findInst hold51227]
if {$anchor eq "NULL" || [[$anchor getMaster] getName] ne "sg13g2_dlygate4sd3_1"} {error "Missing existing delay-cell power reference"}
set signal_signature {}
set supplies {}
foreach mt [$delay_master getMTerms] {
    if {[$mt getSigType] in {POWER GROUND}} {
        set pin [$anchor findITerm [$mt getName]]
        set net [$pin getNet]
        if {$net eq "NULL" || [$net getSigType] ne [$mt getSigType]} {error "Delay-cell reference power disconnected"}
        dict set supplies [$mt getName] $net
    } else {lappend signal_signature [list [$mt getName] [$mt getIoType]]}
}
if {[lsort $signal_signature] ne [lsort {{A INPUT} {X OUTPUT}}] || [dict size $supplies] != 2} {error "Unexpected delay-cell pin contract"}
set added_insts {}; set added_nets {}; set previous $old_net
set start_location [$driver getLocation]
for {set i 0} {$i < 3} {incr i} {
    set name "nssoc_rx6_addr6_hold_$i"
    set netname "nssoc_rx6_addr6_hold_net_$i"
    if {[$block findInst $name] ne "NULL" || [$block findNet $netname] ne "NULL"} {error "ECO names already exist"}
    set inst [odb::dbInst_create $block $delay_master $name]
    set net [odb::dbNet_create $block $netname]
    $net setSigType SIGNAL
    $inst setLocation [lindex $start_location 0] [lindex $start_location 1]
    $inst setPlacementStatus PLACED
    [$inst findITerm A] connect $previous
    [$inst findITerm X] connect $net
    dict for {pin supply} $supplies {[$inst findITerm $pin] connect $supply}
    lappend added_insts $inst; lappend added_nets $net; set previous $net
}
$endpoint disconnect
$endpoint connect $previous
# Check the entire chain before contracting only its proven identity buffers.
set previous $old_net
foreach inst $added_insts net $added_nets {
    if {[[$inst findITerm A] getNet] ne $previous || [[$inst findITerm X] getNet] ne $net} {error "Broken ECO chain"}
    if {[llength [$net getITerms]] != 2 || [llength [$net getBTerms]] != 0} {error "Unexpected ECO branch"}
    dict for {pin supply} $supplies {if {[[$inst findITerm $pin] getNet] ne $supply} {error "ECO supply mismatch"}}
    set previous $net
}
if {[$endpoint getNet] ne $previous} {error "Endpoint not connected to final delay"}
set contracted {}
foreach net [$block getNets] {
    if {[lsearch -exact $added_nets $net] >= 0} {continue}
    set pins {}
    foreach pin [$net getITerms] {
        if {[lsearch -exact $added_insts [$pin getInst]] >= 0} {continue}
        lappend pins [list I [[$pin getInst] getName] [[$pin getMTerm] getName]]
    }
    foreach pin [$net getBTerms] {lappend pins [list B [$pin getName]]}
    if {$net eq $old_net} {lappend pins [list I $macro_name {A_ADDR[6]}]}
    lappend contracted [list [$net getName] [$net getSigType] [lsort $pins]]
}
if {[lsort $contracted] ne $before} {error "Unexpected original connectivity change after contracting delay chain"}
set after_eco [connections $block]
set report [open "$::env(STEP_DIR)/rx6-hold-eco.tsv" w]
puts $report "endpoint\toriginal_net\tcell\tcount\tconnection_check"
puts $report "$macro_name/A_ADDR\[6\]\tnet66201\tsg13g2_dlygate4sd3_1\t3\texact_identity_contraction_passed"
close $report
puts "NSSOC_RX6_ENDPOINT_ONLY_THREE_DELAY_IDENTITY_CHECK_PASSED"

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
if {[connections $block] ne $after_eco} {error "Connectivity changed during legalization"}
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
estimate_parasitics -placement
write_views
puts "NSSOC_FIVE_DRIVER_RESIZE_CONNECTIVITY_PRESERVED"
