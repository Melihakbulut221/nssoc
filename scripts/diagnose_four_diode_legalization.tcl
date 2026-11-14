read_db out/native/diode-diagnostic.odb
if {[ord::openroad_version] ne "dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"} {error "Runtime changed"}
set block [ord::get_db_block]
set targets {ANTENNA_482 ANTENNA_1342 ANTENNA_457 ANTENNA_458}
set fixed_locations [dict create]
set old_statuses [dict create]
set f [open out/native/before-status.tsv r]
while {[gets $f line] >= 0} {lassign [split $line "\t"] n s; dict set old_statuses $n $s}
close $f
foreach n $targets {if {[$block findInst $n] eq "NULL"} {error "Missing target $n"}}
set count 0
foreach inst [$block getInsts] {
 set n [$inst getName]
 incr count
 if {$n in $targets} {$inst setPlacementStatus PLACED} else {
  dict set fixed_locations $n [list [$inst getLocation] [$inst getOrient]]
  $inst setPlacementStatus LOCKED
 }
}
puts "NSSOC_FIXED_COUNT [dict size $fixed_locations]"
puts "NSSOC_TOTAL_COUNT $count"
set rc [catch {detailed_placement -max_displacement {1000 1000}} message options]
puts "NSSOC_LEGALIZE_RC $rc"
puts "NSSOC_LEGALIZE_MESSAGE $message"
write_db out/native/legalization-attempt.odb
if {$rc} {return -options $options $message}
set after_count 0
foreach inst [$block getInsts] {
 incr after_count
 set n [$inst getName]
 if {[dict exists $fixed_locations $n] && [dict get $fixed_locations $n] ne [list [$inst getLocation] [$inst getOrient]]} {error "Non-target moved: $n"}
 if {[dict exists $old_statuses $n]} {$inst setPlacementStatus [dict get $old_statuses $n]} else {$inst setPlacementStatus PLACED}
}
if {$after_count != $count} {error "Instance count changed"}
check_placement -verbose
puts "NSSOC_PLACEMENT_CHECK_OK"
write_db out/native/four-diode-legalized.odb
puts "NSSOC_PLACEMENT_ONLY_DONE_NOT_ROUTED"
