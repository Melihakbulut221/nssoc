# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Run from repo root: pinned LibreLane AppImage openroad -no_init -exit FILE
# Tests the installed Tcl command parser and translated C++ argument contract.
# C++ optimization/parasitics calls are replaced: NO DB, STA or speed benchmark.
source hw/soc/pnr/timing_repair_experiment.tcl
set calls {}
foreach command {rsz::set_max_utilization est::check_parasitics rsz::repair_setup rsz::repair_hold design_is_routed} {
    rename $command ${command}_original
}
proc rsz::set_max_utilization {args} {}
proc est::check_parasitics {} {}
proc design_is_routed {} {return 0}
proc rsz::repair_setup {args} { lappend ::calls [linsert $args 0 setup]; return 0 }
proc rsz::repair_hold {args} { lappend ::calls [linsert $args 0 hold]; return 0 }

nssoc_timing_experiment setup_baseline
nssoc_timing_experiment setup_batch4
nssoc_timing_experiment hold_guarded
if {[llength $calls] != 3} { error "Expected three native parser calls" }
set a [lindex $calls 0]
set b [lindex $calls 1]
set h [lindex $calls 2]
# Native dcf36133 setup args: margin, TNS fraction, passes, iterations, repairs.
if {[lrange $a 0 5] ne {setup 0.1 1.0 10000 100 1}} { error "Baseline drift: $a" }
if {[lrange $b 0 5] ne {setup 0.1 1.0 10000 100 4}} { error "Batch drift: $b" }
if {[lreplace $b 5 5 1] ne $a} { error "A/B differs beyond repairs-per-pass" }
# Hold args: setup margin, hold margin, allow_setup, buffer fraction, passes,
# iterations, match footprint, verbose. A false allow_setup is mandatory.
if {$h ne {hold 0.1 0.15 0 0.4 10000 100 0 1}} { error "Hold guard drift: $h" }
if {![catch {nssoc_timing_experiment unrecognized} message]} { error "Unknown profile accepted" }
if {[llength $calls] != 3} { error "Unknown profile invoked optimization" }
puts "BASELINE_NATIVE_ARGS $a"
puts "BATCH4_NATIVE_ARGS $b"
puts "HOLD_NATIVE_ARGS $h"
puts "PASS_NATIVE_PARSER_ONLY_NO_DATABASE_STA_OR_SPEED_BENCHMARK"
