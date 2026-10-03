# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Exactly one source-bound ablation; immutable old helper, only reserved names differ.
if {![info exists ::env(NSSOC_HOLD_ABLATION_VARIANT)] || $::env(NSSOC_HOLD_ABLATION_VARIANT) ni {eth npu}} {error "Unapproved hold ablation variant"}
set nssoc_ablation_variant $::env(NSSOC_HOLD_ABLATION_VARIANT)
set nssoc_ablation_single_path [file join $::env(NSSOC_TARGETED_METHOD_ROOT) hw/soc/pnr/timing_explicit_hold_helpers.tcl]
if {[nssoc_hold_sha $nssoc_ablation_single_path] ne "6d12da88eaf4e6f93c945ae125c4395690225abc5fa6d1f8d5d05267707149fc"} {error "Frozen single-delay helper differs"}
set nssoc_ablation_f [open $nssoc_ablation_single_path rb]
set nssoc_ablation_source [read $nssoc_ablation_f];close $nssoc_ablation_f
source $nssoc_ablation_single_path
namespace eval ::nssoc_ablation [string map [list \
    nssoc_explicit_sd3 nssoc_ablation_${nssoc_ablation_variant}_sd3 \
    nssoc_explicit_holdnet nssoc_ablation_${nssoc_ablation_variant}_net] $nssoc_ablation_source]
unset nssoc_ablation_source nssoc_ablation_f nssoc_ablation_single_path
proc nssoc_ablation_call {operation args} {
    if {$operation ni {preflight vacancy insert verify graph placement route}} {error "Unapproved ablation operation"}
    if {$::env(NSSOC_HOLD_ABLATION_VARIANT) ne $::nssoc_ablation_variant} {error "Hold ablation variant changed"}
    return [::nssoc_ablation::nssoc_explicit_$operation {*}$args]
}
proc nssoc_ablation_row {insertions} {
    if {[llength $insertions] == 0} {return {}}
    if {[llength $insertions] != 1} {error "Exactly one ablation insertion is required"}
    set row [lindex $insertions 0]
    set variant $::nssoc_ablation_variant
    if {![regexp "^nssoc_ablation_${variant}_sd3\[0-9\]+$" [dict get $row buffer]] ||
        ![regexp "^nssoc_ablation_${variant}_net\[0-9\]+$" [dict get $row new_net]] ||
        [dict get $row master] ne "sg13g2_dlygate4sd3_1"} {error "Ablation row prefix/master differs"}
    return $row
}
proc nssoc_ablation_verify {insertions} {
    if {[llength $insertions] != 1} {error "Exactly one ablation insertion is required"}
    nssoc_ablation_call verify [nssoc_ablation_row $insertions]
}
proc nssoc_ablation_graph {path {insertions {}}} {
    nssoc_ablation_call graph $path [nssoc_ablation_row $insertions]
}
proc nssoc_ablation_placement {path {insertions {}}} {
    set row [nssoc_ablation_row $insertions];set skip {}
    if {$row ne {}} {set skip [dict get $row buffer]}
    nssoc_ablation_call placement $path $skip
}
proc nssoc_ablation_route {root name {insertions {}}} {
    set row [nssoc_ablation_row $insertions];set skip {}
    if {$row ne {}} {set skip [dict get $row buffer]}
    nssoc_ablation_call route $root $name $skip
}
proc nssoc_ablation_insert {root driver sink net places} {
    set directory [file join $root insert0]
    if {[file exists $directory]} {error "Ablation insertion output already exists"}
    file mkdir $directory
    return [nssoc_ablation_call insert $directory $driver $sink $net $places]
}
