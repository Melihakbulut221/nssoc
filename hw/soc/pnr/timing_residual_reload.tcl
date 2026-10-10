# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Same read-only fresh reload, followed by explicit min/max paths for all targets.
source [file join $::env(NSSOC_TARGETED_METHOD_ROOT) hw/soc/pnr/timing_combined_reload.tcl]
set ::env(NSSOC_ELECTRICAL_ROOT) $::env(NSSOC_TARGETED_METHOD_ROOT)
source [file join $::env(NSSOC_TARGETED_METHOD_ROOT) hw/soc/pnr/timing_residual_repair_helpers.tcl]
source $::env(NSSOC_ELECTRICAL_BASELINE_TCL)
set targets {}
foreach endpoint [dict keys $nssoc_residual_expected_hold] {lappend targets [list $endpoint sg13g2_dfrbpq_1]}
nssoc_residual_hold_reports $root $name $targets
puts "NSSOC_RESIDUAL_RELOAD_PATHS_COMPLETE $name"
