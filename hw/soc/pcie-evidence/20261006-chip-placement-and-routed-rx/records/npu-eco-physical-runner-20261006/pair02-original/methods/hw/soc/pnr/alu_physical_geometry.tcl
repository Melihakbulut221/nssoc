# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# This script is also sourced by the final audit; helpers never change geometry.
proc nssoc_alu_geometry {directory} {
    set stream [open [file join $directory signal-pins.tsv] {WRONLY CREAT EXCL}]
    puts $stream "name\tdirection\tsignal_type\tlayer\tx0_dbu\ty0_dbu\tx1_dbu\ty1_dbu\tstatus"
    set terms {}
    foreach term [[ord::get_db_block] getBTerms] {
        if {[$term getSigType] ni {POWER GROUND}} {dict set terms [$term getName] $term}
    }
    foreach name [lsort [dict keys $terms]] {
        if {[regexp {[\t\r\n]} $name]} {error "Invalid terminal identity"}
        set term [dict get $terms $name]
        set rows {}
        foreach pin [$term getBPins] {
            foreach box [$pin getBoxes] {
                lappend rows [join [list $name [$term getIoType] [$term getSigType] \
                    [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax] \
                    [$pin getPlacementStatus]] \t]
            }
        }
        if {[llength $rows] == 0} {error "Unplaced shared terminal $name"}
        foreach row [lsort $rows] {puts $stream $row}
    }
    close $stream
    set stream [open [file join $directory macros.tsv] {WRONLY CREAT EXCL}]
    puts $stream "instance\tmaster\tx_dbu\ty_dbu\torientation\tstatus"
    set macros {}
    foreach inst [[ord::get_db_block] getInsts] {
        if {[[$inst getMaster] isBlock]} {dict set macros [$inst getName] $inst}
    }
    foreach name [lsort [dict keys $macros]] {
        set inst [dict get $macros $name]
        lassign [$inst getLocation] x y
        puts $stream [join [list $name [[$inst getMaster] getName] $x $y [$inst getOrient] [$inst getPlacementStatus]] \t]
    }
    close $stream
    set stream [open [file join $directory bounds.tsv] {WRONLY CREAT EXCL}]
    puts $stream "kind\tx0_dbu\ty0_dbu\tx1_dbu\ty1_dbu"
    foreach {kind method} {die getDieArea core getCoreArea} {
        set rectangle [[ord::get_db_block] $method]
        puts $stream [join [list $kind [$rectangle xMin] [$rectangle yMin] [$rectangle xMax] [$rectangle yMax]] \t]
    }
    close $stream
    set stream [open [file join $directory dbu.txt] {WRONLY CREAT EXCL}]
    puts $stream [[[ord::get_db] getTech] getDbUnitsPerMicron]
    close $stream
}

if {![info exists ::nssoc_alu_geometry_definitions_only]} {
    source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
    read_current_odb
    nssoc_alu_geometry $::env(STEP_DIR)
    write_views
    puts "NSSOC_ALU_COMMON_TEMPLATE_GEOMETRY_CAPTURED"
}
