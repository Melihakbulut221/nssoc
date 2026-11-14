# SPDX-License-Identifier: Apache-2.0
read_db out/native/buf4-legalized-unrouted.odb
if {[ord::openroad_version] ne "dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"} {error "Runtime changed"}
check_placement -verbose
set f [open out/derived/saved-placement.json w]
puts $f {{"status":"SAVED_PLACEMENT_RECHECK_PASSED","placement_only":true,"timing_validated":false}}
close $f
puts NSSOC_SAVED_PLACEMENT_RECHECK_PASSED
