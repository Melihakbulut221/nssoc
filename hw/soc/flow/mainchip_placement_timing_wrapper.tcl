# SPDX-License-Identifier: Apache-2.0
# Explicit candidate model, never a final extracted-timing acceptance path.
source [file join [file dirname [info script]] mainchip_repair_timing_native_reference.tcl]
set nssoc_native_body [info body repair_timing]
if {[info args repair_timing] ne "args"
    || $nssoc_native_body ne [info body nssoc_repair_timing_reference]} {
    error "Native repair_timing wrapper differs from pinned OpenROAD revision"
}
# The exact native wrapper forcibly selects detailed_routing on any routed ODB.
# Retain every argument, constraint check and native optimizer call, replacing
# only that automatic model selection in this separate candidate procedure.
set nssoc_override {  if { [design_is_routed] } {
    est::set_parasitics_src "detailed_routing"
  }}
set nssoc_where [string first $nssoc_override $nssoc_native_body]
if {$nssoc_where < 0
    || [string first $nssoc_override $nssoc_native_body [expr {$nssoc_where+1}]] >= 0} {
    error "Expected exactly one native automatic parasitic-mode override"
}
set nssoc_replacement {  est::set_parasitics_src "placement"}
set nssoc_candidate_body [string replace $nssoc_native_body $nssoc_where \
    [expr {$nssoc_where+[string length $nssoc_override]-1}] $nssoc_replacement]
proc nssoc_repair_timing_candidate {args} $nssoc_candidate_body
if {[info body repair_timing] ne $nssoc_native_body} {
    error "Original native repair_timing was altered"
}
if {[info body nssoc_repair_timing_candidate] ne $nssoc_candidate_body} {
    error "Candidate wrapper serialization changed"
}
# Fail closed if the pinned-body identity predicate would accept a changed gate.
set nssoc_bad_body [string map {{set allow_setup_violations} {set waived_setup_violations}} $nssoc_native_body]
if {$nssoc_bad_body eq $nssoc_native_body
    || $nssoc_bad_body eq [info body nssoc_repair_timing_reference]} {
    error "Native-wrapper changed-gate rejection control failed"
}
foreach {name body} [list native $nssoc_native_body candidate $nssoc_candidate_body] {
    set f [open "$::env(NSSOC_RESIZER_OUT)/repair-timing-$name-body.tcl" w]
    puts -nonewline $f $body
    close $f
}
puts "NSSOC_EXACT_NATIVE_WRAPPER_ONE_MODEL_OVERRIDE_ORIGINAL_GATES_RETAINED"
