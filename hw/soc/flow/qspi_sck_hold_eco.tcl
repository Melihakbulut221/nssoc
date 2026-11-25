# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Apply to an unrouted post-CTS database after reading its original SDC/Liberty.
# Add delay only on the SCK output branch. The caller must legalize, route and
# recheck both min and max paths for the resulting geometry.
proc insert_qspi_sck_hold_delay {count} {
    if {![string is integer -strict $count] || $count < 1} {
        error "Expected a positive count of SG13G2 delay cells"
    }
    set block [ord::get_db_block]
    set port [$block findBTerm qspi_sck_o]
    if {$port eq "NULL" || [$port getIoType] ne "OUTPUT"} {
        error "Missing qspi_sck_o output"
    }
    set net [$port getNet]
    if {[llength [$net getITerms]] != 1 || [llength [$net getBTerms]] != 1} {
        error "Expected an isolated output net on qspi_sck_o"
    }
    set driver [lindex [$net getITerms] 0]
    if {[[$driver getMTerm] getIoType] ne "OUTPUT"} {
        error "Missing SCK output driver"
    }
    for {set i 0} {$i < $count} {incr i} {
        if {[$block findInst qspi_sck_hold_$i] ne "NULL" ||
            [$block findNet qspi_sck_dly_$i] ne "NULL"} {
            error "Existing QSPI ECO cell or net at index $i"
        }
    }
    lassign [[$driver getInst] getLocation] x y
    set x [ord::dbu_to_microns $x]
    set y [ord::dbu_to_microns $y]
    for {set i 0} {$i < $count} {incr i} {
        insert_buffer -buffer_cell sg13g2_dlygate4sd3_1 -load_pins qspi_sck_o \
            -location [list [expr {$x + 6.0 * $i}] $y] \
            -buffer_name qspi_sck_hold_$i -net_name qspi_sck_dly_$i
    }
}
