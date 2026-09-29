# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Native OpenDB + OpenDP control, not a whole-chip STA or routing test.
# Run from repo root with pinned LibreLane AppImage openroad -no_init -exit FILE.
source hw/soc/pnr/critical_xnor_placement.tcl
proc require {condition message} {
    if {![uplevel 1 [list expr $condition]]} { error $message }
}
proc rejected {script pattern} {
    if {![catch {uplevel 1 $script} message]} { error "Invalid case accepted: $script" }
    require {[string match $pattern $message]} "Unexpected rejection: $message"
}
set db [ord::get_db]
# LEF import establishes the native database distance unit; a raw dbTech_create
# has zero DBU in this build, which would make native displacement reports NaN.
set lef_channel [file tempfile lef_path [file join [pwd] hw soc out critical-placement-control.lef]]
puts $lef_channel {VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
UNITS
  DATABASE MICRONS 1000 ;
END UNITS
MANUFACTURINGGRID 0.001 ;
LAYER M1
  TYPE ROUTING ;
  DIRECTION HORIZONTAL ;
  PITCH 0.2 ;
  WIDTH 0.1 ;
  SPACING 0.1 ;
END M1
END LIBRARY}
close $lef_channel
try { read_lef $lef_path } finally { file delete $lef_path }
set tech [$db getTech]
set metal [$tech findLayer M1]
set lib [odb::dbLib_create $db synthetic $tech]
set site [odb::dbSite_create $lib unit]
$site setClass CORE
$site setWidth 1000
$site setHeight 2000
$site setSymmetryY
set chip [odb::dbChip_create $db $tech]
set block [odb::dbBlock_create $chip synthetic]
$block setDefUnits 1000
require {[$block getDbUnitsPerMicron] == 1000} "Native DBU is not 1000"
$block setDieArea [odb::new_Rect 0 0 1000000 100000]
for {set i 0} {$i < 10} {incr i} {
    odb::dbRow_create $block row$i $site 0 [expr {$i*2000}] R0 HORIZONTAL 1000 1000
}
$block setCoreArea [odb::new_Rect 0 0 1000000 20000]
set master [odb::dbMaster_create $lib sg13g2_xnor2_1]
$master setWidth 2000
$master setHeight 2000
$master setType CORE
$master setSite $site
$master setSymmetryY
foreach pin {A B Y} direction {INPUT INPUT OUTPUT} {
    set term [odb::dbMTerm_create $master $pin $direction SIGNAL]
    set mpin [odb::dbMPin_create $term]
    odb::dbBox_create $mpin $metal 100 100 200 200
}
$master setFrozen
set driver [odb::dbInst_create $block $master _072583_]
set target [odb::dbInst_create $block $master _072584_]
foreach inst [list $driver $target] x {10000 410000} {
    $inst setLocation $x 0
    $inst setPlacementStatus PLACED
}
set net [odb::dbNet_create $block _018489_]
[$driver findITerm Y] connect $net
[$target findITerm B] connect $net
# Synthetic geometry deliberately carries a real macro name so the production
# allow-list and exactly-32 guard run unchanged; this is not that SRAM layout.
set macro_master [odb::dbMaster_create $lib SP6TSRAM512x64]
$macro_master setWidth 20000
$macro_master setHeight 2000
$macro_master setType BLOCK
$macro_master setFrozen
for {set i 0} {$i < 32} {incr i} {
    set macro [odb::dbInst_create $block $macro_master ram$i]
    $macro setLocation [expr {$i*25000}] 60000
    $macro setPlacementStatus FIRM
}
# Block the exact midpoint with a macro: selector must find another row/site.
set obstacle [$block findInst ram0]
$obstacle setPlacementStatus PLACED
$obstacle setLocation 209000 0
$obstacle setPlacementStatus FIRM
set original [$target getLocation]
set original_macros [nssoc_critical_placement::macro_snapshot $block]
set original_pins [nssoc_critical_placement::pins $target]
$target setPlacementStatus FIRM
rejected {nssoc_apply_critical_placement} {*must be placed, movable*}
require {[$target getLocation] eq $original} "Rejected input was modified"
$target setPlacementStatus PLACED
set extra [odb::dbInst_create $block $master extra]
$extra setLocation 500000 0
$extra setPlacementStatus PLACED
[$extra findITerm A] connect $net
rejected {nssoc_apply_critical_placement} {*exactly one driver and one sink*}
[$extra findITerm A] disconnect
$extra setLocation 210000 2000
nssoc_apply_critical_placement
set moved [$target getLocation]
require {$moved ne $original} "Target did not move"
require {[$target getOrient] eq "R0"} "Orientation changed"
require {[lindex $moved 0] % 1000 == 0 && [lindex $moved 1] % 2000 == 0} "Candidate is off grid"
set b [$target getBBox]
set o [$obstacle getBBox]
require {!([$b xMin] < [$o xMax] && [$b xMax] > [$o xMin] && [$b yMin] < [$o yMax] && [$b yMax] > [$o yMin])} "Candidate overlaps macro"
detailed_placement
check_placement -verbose
require {[$target getLocation] ne $moved || [$extra getLocation] ne {210000 2000}} "Native legalization did not resolve deliberate cell overlap"
nssoc_verify_critical_placement
require {[nssoc_critical_placement::macro_snapshot $block] eq $original_macros} "SRAM changed"
require {[nssoc_critical_placement::pins $target] eq $original_pins} "Connectivity changed"
require {[dict get $nssoc_critical_placement::state after_distance_dbu] < 400000} "Distance did not improve"
# Verification is fail closed if legalization undoes improvement or changes a
# protected macro. These controls mutate only this tiny synthetic database.
dict set nssoc_critical_placement::state status MOVED_AWAITING_LEGALIZATION
$target setLocation {*}$original
rejected {nssoc_verify_critical_placement} {*did not preserve a shorter*}
$target setLocation {*}$moved
$obstacle setPlacementStatus PLACED
$obstacle setLocation 210000 0
$obstacle setPlacementStatus FIRM
rejected {nssoc_verify_critical_placement} {*changed orientation, connectivity or SRAM placement*}
$obstacle setPlacementStatus PLACED
$obstacle setLocation 209000 0
$obstacle setPlacementStatus FIRM
set new_net [odb::dbNet_create $block changed_noncritical_input]
[$target findITerm A] connect $new_net
rejected {nssoc_verify_critical_placement} {*changed orientation, connectivity or SRAM placement*}
[$target findITerm A] disconnect
set nssoc_critical_placement::state {}
odb::dbInst_destroy [$block findInst ram31]
rejected {nssoc_apply_critical_placement} {*exactly 32 SRAM*}
puts "PASS_NATIVE_OPENDP_SYNTHETIC_PLACEMENT_AND_REJECTION_CONTROLS_NO_CHIP_STA"
