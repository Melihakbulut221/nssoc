# SPDX-License-Identifier: Apache-2.0
# Real native database plus an open-file/Tcl-memory continuation witness.
# This does not start or certify detailed routing.
set case $::env(NSSOC_CHECKPOINT_CASE)
if {[file exists [file join $case boots.log]]} {error "Cold entrypoint restart detected"}
read_db $::env(NSSOC_CHECKPOINT_ODB)
set block [ord::get_db_block]
if {[llength [$block getInsts]] != 152762} {error "Actual saved design differs"}
set token "[pid]_[clock clicks]"
set boot [open [file join $case boots.log] w]
puts $boot $token
close $boot
set journal [open [file join $case journal.log] w]
for {set counter 0} {$counter < 120} {incr counter} {
    puts $journal "$token $counter [llength [$block getInsts]]"
    flush $journal
    after 250
}
close $journal
write_db [file join $case final.odb]
set done [open [file join $case done] w]
puts $done $token
close $done
exit
