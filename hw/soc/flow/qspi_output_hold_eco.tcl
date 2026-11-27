# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Apply after the post-global-route repair of the SCK delay candidate.
if {[llength [get_cells -quiet qspi_sck_hold_*]] != 14} {
    error "Expected the 14-cell QSPI SCK input candidate"
}
if {[llength [get_cells -quiet nssoc_io_hold*]] || [llength [get_nets -quiet nssoc_io_delay*]]} {
    error "QSPI output delays already inserted"
}
set block [ord::get_db_block]
foreach {name length} {
    qspi_io_o[2] 4    qspi_cs_no[1] 4    qspi_cs_no[0] 4
    qspi_io_oe_o[2] 4 qspi_io_oe_o[0] 4  qspi_io_oe_o[3] 3
    qspi_io_oe_o[1] 3 qspi_io_o[0] 3     qspi_io_o[3] 3
    qspi_io_o[1] 3
} {
    set term [$block findBTerm $name]
    if {$term eq "NULL" || [$term getIoType] ne "OUTPUT"} {error "Missing output $name"}
    set drivers {}
    foreach pin [[$term getNet] getITerms] {
        if {[[$pin getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $pin}
    }
    if {[llength $drivers] != 1} {error "Unknown driver of $name"}
    lassign [[[lindex $drivers 0] getInst] getLocation] x y
    for {set i 0} {$i < $length} {incr i} {
        set loc [list [expr {[ord::dbu_to_microns $x] + 6.0*$i}] [ord::dbu_to_microns $y]]
        insert_buffer -buffer_cell sg13g2_dlygate4sd3_1 -load_pins [list $name] -location $loc -buffer_name nssoc_io_hold -net_name nssoc_io_delay
    }
}
