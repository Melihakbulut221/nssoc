# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_electrical_repair_helpers.tcl]
proc nssoc_electrical_margin_graph {driver netname expected} {
    set net [nssoc_electrical_preflight $driver $netname]
    set actual {}
    foreach term [$net getITerms] {
        set inst [$term getInst]
        lappend actual [list [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName]]
    }
    if {[lsort $actual] ne [lsort $expected]} {
        error "Exact electrical target terminal graph differs: $driver $netname; actual=[lsort $actual]; expected=[lsort $expected]"
    }
    return [lsort $actual]
}
proc nssoc_electrical_margin_repair {driver netname} {
    set net [nssoc_electrical_preflight $driver $netname]
    set initial [llength [[ord::get_db_block] getInsts]]
    set original_master [[[[ord::get_db_block] findInst $driver] getMaster] getName]
    # 0 disables wire-length-only repair. Positive 20 percent margins tighten
    # repair targets, not Liberty/SDC limits; this is experimental headroom.
    rsz::repair_net_cmd [get_net $netname] 0 20 20
    set final [llength [[ord::get_db_block] getInsts]]
    if {$final < $initial || $final-$initial > 256} {error "Bounded electrical trial grew by more than 256 cells"}
    return [dict create driver [nssoc_hold_jstr "$driver/X"] net [nssoc_hold_jstr $netname] \
        original_master [nssoc_hold_jstr $original_master] initial_instance_count $initial \
        actual_instance_count $final native_calls 1 max_length_m 0 slew_margin_percent 20 cap_margin_percent 20]
}
