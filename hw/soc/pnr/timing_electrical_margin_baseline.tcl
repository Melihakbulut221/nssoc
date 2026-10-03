# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# A second native process must reproduce the pinned candidate before any repair.
source [file join $::env(NSSOC_TARGETED_METHOD_ROOT) hw/soc/pnr/timing_combined_reload.tcl]
source $::env(NSSOC_ELECTRICAL_BASELINE_TCL)
set observed [nssoc_combined_metrics]
dict for {key expected} $nssoc_electrical_expected_metrics {
    if {[dict get $observed $key] != $expected} {error "Independent baseline metric differs: $key"}
}
dict for {filename expected} $nssoc_electrical_expected_files {
    if {[nssoc_hold_sha [file join $root $name $filename]] ne $expected} {
        error "Independent baseline physical fingerprint differs: $filename"
    }
}
puts NSSOC_ELECTRICAL_INDEPENDENT_BASELINE_EXACT_BEFORE_REPAIR
