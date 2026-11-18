# SPDX-License-Identifier: Apache-2.0
"""Core-only extracted timing guards; no timing or clock budget relaxation."""
CLOCK_GUARD = r"""
if {![info exists ::env(TIME_DERATING_CONSTRAINT)] ||
    ![string is double -strict $::env(TIME_DERATING_CONSTRAINT)] ||
    $::env(TIME_DERATING_CONSTRAINT) != 5.0} {
    error "Core-only extracted timing requires five percent derate"
}
if {[llength [all_clocks]] != 1} {error "Core-only requires exactly one clock"}
set clock [get_clocks clk_i]
if {[llength $clock] != 1 || abs([get_property $clock period]-20.0)>1e-9} {
    error "Core-only requires clk_i at 20 ns"
}
if {![get_property $clock is_propagated]} {error "Extracted STA has ideal clock"}
puts "CORE_ONLY_EXTRACTED_CLOCK_VERIFIED"
"""

def guarded_sta(text, derate):
    anchor = 'source $::env(SCRIPTS_DIR)/openroad/common/io.tcl\n'
    old = '    if { [get_property $clock is_propagated] } {\n        set is_virtual "yes"\n    }'
    for expected in (anchor, 'read_spefs\n', '    read_timing_info\n', old):
        if text.count(expected) != 1:
            raise ValueError('Unsupported native STA script anchor: ' + repr(expected))
    # Reporting typo only. Never change propagation state to make a guard pass.
    text = text.replace(old, old.replace('set is_virtual', 'set is_propagated'))
    text = text.replace(anchor, anchor + derate + '\nif {[namespace exists ::ord]} {error "Extracted STA requires standalone OpenSTA and actual SPEF"}\n')
    return text.replace('read_spefs\n', 'read_spefs\n' + CLOCK_GUARD)
