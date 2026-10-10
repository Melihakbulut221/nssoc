# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Clear stale route metadata on an unloaded internal output after an ECO.
# Do not remove the cell/net/pin, physical geometry, or any connected-net guide.
proc prune_orphan_guides {block} {
    set removed 0
    foreach net [$block getNets] {
        if {[$net getSigType] ne "SIGNAL"} {continue}
        if {[llength [$net getBTerms]] != 0} {continue}
        set pins [$net getITerms]
        if {[llength $pins] != 1} {continue}
        if {[[lindex $pins 0] getIoType] ne "OUTPUT"} {continue}
        set count [llength [$net getGuides]]
        if {$count == 0} {continue}
        puts "ORPHAN_GUIDES net=[$net getName] removed=$count"
        $net clearGuides
        if {[llength [$net getGuides]] != 0} {
            error "Failed to clear stale guides on [$net getName]"
        }
        incr removed $count
    }
    return $removed
}
