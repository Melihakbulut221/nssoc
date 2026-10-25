# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Reject a lexical value that the native SDC would truncate before loading it.
if {![info exists ::env(TIME_DERATING_CONSTRAINT)]} {
 error "Missing TIME_DERATING_CONSTRAINT"
}
set derate $::env(TIME_DERATING_CONSTRAINT)
if {![string is double -strict $derate] ||
    [catch {expr {double($derate) >= 0 && double($derate) < 100}} valid] || !$valid} {
 error "Invalid TIME_DERATING_CONSTRAINT"
}
set intended_derate [expr {double($derate) / 100.0}]
if {[expr {$derate / 100}] != $intended_derate} {
 error "TIME_DERATING_CONSTRAINT loses precision in the native SDC integer division"
}
puts "DERATE_GUARD percent=$derate early=[expr {1-$intended_derate}] late=[expr {1+$intended_derate}]"
