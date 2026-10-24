# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Exact OpenROAD dcf36133 rsz::repair_net_cmd, guarded before any chip mutation.
proc nssoc_electrical_preflight {driver netname} {
    if {![llength [info commands rsz::repair_net_cmd]]} {error "Native repair_net_cmd API unavailable"}
    set block [ord::get_db_block]
    set net [$block findNet $netname]
    set inst [$block findInst $driver]
    if {$net eq "NULL" || $inst eq "NULL" || [$net getSigType] ne "SIGNAL" ||
            [$net isDoNotTouch] || [$inst isDoNotTouch] || ![$inst isPlaced] || [$inst isFixed]} {
        error "Electrical target missing, protected, clock, or unplaced: $driver $netname"
    }
    if {![regexp {^sg13g2_buf_(1|2|4|8|16)$} [[$inst getMaster] getName]]} {
        error "Electrical target is not the expected positive buffer family"
    }
    set term [$inst findITerm X]
    if {$term eq "NULL" || [$term getNet] ne $net || [[$term getMTerm] getIoType] ne "OUTPUT"} {
        error "Electrical driver/net identity differs"
    }
    set outputs 0; set inputs 0
    foreach term [$net getITerms] {
        set direction [[$term getMTerm] getIoType]
        if {$direction eq "OUTPUT"} {incr outputs} elseif {$direction eq "INPUT"} {incr inputs} else {error "Bidirectional electrical target"}
    }
    if {$outputs != 1 || $inputs < 1 || [llength [$net getBTerms]] != 0} {error "Electrical target must be one internal driver with sinks"}
    return $net
}
proc nssoc_electrical_status {path} {
    set out [open $path {WRONLY CREAT EXCL}]
    puts $out "kind\tname\tdont_touch\tsignal_type\tconnections"
    set instances {}; set nets {}
    foreach inst [[ord::get_db_block] getInsts] {dict set instances [$inst getName] $inst}
    foreach name [lsort [dict keys $instances]] {
        set inst [dict get $instances $name]; set master {}; set pins {}
        if {[$inst isDoNotTouch]} {
            set master [[$inst getMaster] getName]
            foreach term [$inst getITerms] {
                set net [$term getNet]; set netname {}
                if {$net ne "NULL"} {set netname [$net getName]}
                lappend pins "[[$term getMTerm] getName]=$netname"
            }
        }
        puts $out [join [list instance [nssoc_hold_field $name] [$inst isDoNotTouch] $master [nssoc_hold_field [join [lsort $pins] |]]] \t]
    }
    foreach net [[ord::get_db_block] getNets] {dict set nets [$net getName] $net}
    foreach name [lsort [dict keys $nets]] {
        set net [dict get $nets $name]; set pins {}
        if {[$net getSigType] eq "CLOCK" || [$net isDoNotTouch]} {
            foreach term [$net getITerms] {lappend pins "[[$term getInst] getName]/[[$term getMTerm] getName]"}
            foreach port [$net getBTerms] {lappend pins "PORT:[$port getName]"}
        }
        puts $out [join [list net [nssoc_hold_field $name] [$net isDoNotTouch] [$net getSigType] [nssoc_hold_field [join [lsort $pins] |]]] \t]
    }
    close $out
}
proc nssoc_electrical_report {root name targets} {
    foreach corner [lsort [dict keys [nssoc_hold_corners]]] {
        foreach target $targets {
            lassign $target driver netname
            report_check_types -corner $corner -net $netname -max_slew -max_capacitance -digits 9 -verbose \
                > [file join $root "$name-$driver-$corner.rpt"]
        }
    }
}
proc nssoc_electrical_repair {driver netname} {
    set net [nssoc_electrical_preflight $driver $netname]
    set initial [llength [[ord::get_db_block] getInsts]]
    set original_master [[[[ord::get_db_block] findInst $driver] getMaster] getName]
    # 0 length disables wire-length-only repair. Both margins are exactly zero;
    # real Liberty/SDC capacitance/slew/fanout limits remain unchanged.
    rsz::repair_net_cmd [get_net $netname] 0 0 0
    set final [llength [[ord::get_db_block] getInsts]]
    if {$final < $initial || $final-$initial > 256} {error "Bounded electrical trial grew by more than 256 cells"}
    return [dict create driver [nssoc_hold_jstr "$driver/X"] net [nssoc_hold_jstr $netname] \
        original_master [nssoc_hold_jstr $original_master] initial_instance_count $initial \
        actual_instance_count $final native_calls 1 max_length_m 0 slew_margin_percent 0 cap_margin_percent 0]
}
