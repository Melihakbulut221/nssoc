# SPDX-License-Identifier: Apache-2.0
read_db out/native/source.odb
if {[ord::openroad_version] ne "dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"} {error "Runtime changed"}
set block [ord::get_db_block]
if {[llength [$block getInsts]] != 159934} {error "Source instance count changed"}
check_placement -verbose
set target [$block findInst place31551]
if {$target eq "NULL" || [[$target getMaster] getName] ne "sg13g2_buf_1"} {error "Unexpected source driver"}
set net [[$target findITerm X] getNet]
if {$net eq "NULL" || [$net getName] ne "net31551" || [$net getSigType] ne "SIGNAL" || [$target isFixed] || [$target isDoNotTouch] || [$net isDoNotTouch]} {error "Protected or different source net"}
set outputs 0
foreach iterm [$net getITerms] {if {[[$iterm getMTerm] getIoType] eq "OUTPUT"} {incr outputs}}
if {$outputs != 1 || [llength [$net getBTerms]] != 0} {error "Unexpected driver topology"}
set master [[ord::get_db] findMaster sg13g2_buf_4]
if {$master eq "NULL"} {error "Requested master absent from pinned library"}
set oldpins {};set newpins {}
foreach t [[$target getMaster] getMTerms] {lappend oldpins [list [$t getName] [$t getIoType] [$t getSigType]]}
foreach t [$master getMTerms] {lappend newpins [list [$t getName] [$t getIoType] [$t getSigType]]}
if {[lsort $oldpins] ne [lsort $newpins]} {error "Master pin schema differs"}
set statuses {};set fixed {}
foreach inst [$block getInsts] {
 set name [$inst getName];dict set statuses $name [$inst getPlacementStatus]
 if {$name ne "place31551"} {
  dict set fixed $name [list [$inst getLocation] [$inst getOrient] [[$inst getMaster] getName]]
  $inst setPlacementStatus LOCKED
 }
}
set anchor [$target getLocation]
if {![$target swapMaster $master]} {error "Master swap failed"}
$target setLocation {*}$anchor
$target setPlacementStatus PLACED
puts "NSSOC_FIXED_COUNT [dict size $fixed]"
detailed_placement -max_displacement {1000 1000}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {[dict exists $fixed $name] && [dict get $fixed $name] ne [list [$inst getLocation] [$inst getOrient] [[$inst getMaster] getName]]} {error "Unselected geometry changed: $name"}
 $inst setPlacementStatus [dict get $statuses $name]
}
check_placement -verbose
puts NSSOC_PLACEMENT_CHECK_OK
write_db out/native/buf4-legalized-unrouted.odb
puts NSSOC_PLACEMENT_ONLY_NOT_ROUTED
