# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Actual native SG13G2 three-flop placement/STA/per-pin repair regression.
# Run from repo root with NSSOC_PDK_ROOT and a new NSSOC_TEST_OUT directory.
# This is a small placement-parasitic fixture, never a chip timing result.
foreach key {NSSOC_PDK_ROOT NSSOC_TEST_OUT} {
    if {![info exists ::env($key)]} {error "$key is required"}
}
set out $::env(NSSOC_TEST_OUT)
if {[file exists $out]} {error "Native fixture output must not already exist"}
file mkdir $out
set std [file join $::env(NSSOC_PDK_ROOT) ihp-sg13g2 libs.ref sg13g2_stdcell]
source hw/soc/pnr/timing_repair_experiment.tcl
read_lef [file join $std lef sg13g2_tech.lef]
read_lef [file join $std lef sg13g2_stdcell.lef]
define_corners fast typical slow
foreach {corner liberty} {
    fast sg13g2_stdcell_fast_1p32V_m40C.lib
    typical sg13g2_stdcell_typ_1p20V_25C.lib
    slow sg13g2_stdcell_slow_1p08V_125C.lib
} {
    read_liberty -corner $corner [file join $std lib $liberty]
}
set stream [open [file join $out tiny.v] w]
puts $stream {module tiny(input clk, input rst_n, input d,
    output q_bad1, output q_bad2, output q_good);
  sg13g2_dfrbp_1 f0(.Q(q_bad1),.Q_N(),.D(d),.RESET_B(rst_n),.CLK(clk));
  sg13g2_dfrbp_1 f1(.Q(q_bad2),.Q_N(),.D(d),.RESET_B(rst_n),.CLK(clk));
  sg13g2_dfrbp_1 f2(.Q(q_good),.Q_N(),.D(d),.RESET_B(rst_n),.CLK(clk));
endmodule}
close $stream
read_verilog [file join $out tiny.v]
link_design tiny
initialize_floorplan -die_area {0 0 100 100} -core_area {5 5 95 95} -site CoreSite
make_tracks
set index 0
foreach name {f0 f1 f2} {
    set inst [[ord::get_db_block] findInst $name]
    $inst setLocation [expr {10560 + $index * 20160}] 15120
    $inst setOrient R0
    $inst setPlacementStatus PLACED
    incr index
}
set index 0
foreach name {clk rst_n d q_bad1 q_bad2 q_good} {
    place_pin -pin_name $name -layer Metal2 -location [list 0 [expr {10 + 10 * $index}]]
    incr index
}
detailed_placement
create_clock -period 20 [get_ports clk]
set_input_delay -max 0.5 -clock clk [get_ports d]
set_input_delay -min 0.2 -clock clk [get_ports d]
set_output_delay -max 3 -clock clk [get_ports {q_bad1 q_bad2 q_good}]
set_output_delay -min -0.8 -clock clk [get_ports q_bad1]
set_output_delay -min -0.6 -clock clk [get_ports q_bad2]
set_output_delay -min 0 -clock clk [get_ports q_good]
set_wire_rc -signal -layer Metal2
set_wire_rc -clock -layer Metal2
estimate_parasitics -placement
set ::env(STEP_DIR) $out

proc endpoint_min_slack {name} {
    set result 1.0e30
    foreach path [find_timing_paths -to [get_ports $name] -path_delay min \
            -group_path_count 1 -endpoint_path_count 1] {
        set result [expr {min($result, [get_property $path slack])}]
    }
    if {$result == 1.0e30} {error "Missing fixture endpoint $name"}
    return $result
}
proc read_record {path} {
    set stream [open $path r]
    set value [read $stream]
    close $stream
    return $value
}
set before_count [llength [[ord::get_db_block] getInsts]]
set before_setup [sta::worst_slack -max]
set before1 [endpoint_min_slack q_bad1]
set before2 [endpoint_min_slack q_bad2]
if {$before1 >= $before2 || $before2 >= 0 || [endpoint_min_slack q_good] <= 0} {
    error "Fixture must have two ranked negative outputs and one positive output"
}
write_sdc -no_timestamp [file join $out before.sdc]

# Boundary failures must not add cells or create a selection receipt.
foreach bad {0 33 invalid 1.5} {
    if {![catch {nssoc_hold_guarded_targeted $bad} message]} {
        error "Invalid endpoint limit accepted: $bad"
    }
}
rename rsz::repair_hold_pin rsz::repair_hold_pin_saved
set failed [catch {nssoc_hold_guarded_targeted 1} message]
rename rsz::repair_hold_pin_saved rsz::repair_hold_pin
if {!$failed || ![string match *unavailable* $message]} {
    error "Missing native API was not rejected"
}
if {[llength [[ord::get_db_block] getInsts]] != $before_count ||
        [file exists [file join $out hold-targeted-selection.tcldict]]} {
    error "A failed precondition mutated the fixture or target evidence"
}

# Two selected negative endpoints share one fixed floor(0.4 * 3) = 1 budget.
# The first real native insertion must exhaust it before the second call.
set result [nssoc_hold_guarded_targeted 2]
set selection [read_record [file join $out hold-targeted-selection.tcldict]]
if {[dict get $selection corners] ne {fast slow typical} ||
        [dict get $selection selected_count] != 2 ||
        [lindex [lindex [dict get $selection targets] 0] 1] ne "q_bad1" ||
        [lindex [lindex [dict get $selection targets] 0] 2] ne "fast" ||
        [dict get $selection negative_endpoints_all_corners_before] != 2} {
    error "Incorrect cross-corner target selection: $selection"
}
if {[dict get $selection setup_margin_ns] != 0.1 ||
        [dict get $selection hold_margin_ns] != 0.15 ||
        [dict get $selection allow_setup_violations] != 0 ||
        [dict get $selection max_passes_per_endpoint] != 1} {
    error "Guard or pass bound changed"
}
if {[dict get $selection initial_instance_count] != 3 ||
        [dict get $selection global_buffer_budget] != 1 ||
        [dict get $result actual_instance_growth] != 1 ||
        [dict get $result remaining_buffer_budget] != 0 ||
        [dict get [lindex [dict get $result calls] 1] endpoint] ne "q_bad2" ||
        [dict get [lindex [dict get $result calls] 1] status] ne "GLOBAL_BUFFER_BUDGET_EXHAUSTED"} {
    error "Per-endpoint calls did not share the fixed global buffer budget"
}
puts "PASS_NATIVE_BATCH_GLOBAL_BUDGET_EXHAUSTION_PREVENTS_SECOND_CALL"
set after_count [llength [[ord::get_db_block] getInsts]]
set after1 [endpoint_min_slack q_bad1]
set after2 [endpoint_min_slack q_bad2]
set after_setup [sta::worst_slack -max]
if {$after_count <= $before_count || $after1 <= $before1} {
    error "The real native per-pin repair did not add delay at the selected output"
}
if {abs($after2 - $before2) > 1.0e-6 || [sta::worst_slack -max] < 0.1} {
    error "The unselected output or setup safety margin regressed"
}
write_sdc -no_timestamp [file join $out after.sdc]
if {[read_record [file join $out before.sdc]] ne [read_record [file join $out after.sdc]]} {
    error "Native repair changed the timing constraints"
}
if {![catch {nssoc_hold_guarded_targeted 1} message]} {
    error "Existing immutable selection receipt was overwritten"
}
if {[llength [[ord::get_db_block] getInsts]] != $after_count} {
    error "Rejected repeat mutated the design"
}

# A second real native call must refuse delay insertion when the selected
# endpoint lacks setup headroom. This exercises the actual C++ setup guard.
set blocked [file join $out blocked-setup]
file mkdir $blocked
set ::env(STEP_DIR) $blocked
set_output_delay -max 19.7 -clock clk [get_ports q_bad2]
set blocked_setup_before [sta::worst_slack -max]
set blocked_hold_before [endpoint_min_slack q_bad2]
write_sdc -no_timestamp [file join $blocked before.sdc]
nssoc_hold_guarded_targeted 1
set blocked_selection [read_record [file join $blocked hold-targeted-selection.tcldict]]
if {[lindex [lindex [dict get $blocked_selection targets] 0] 1] ne "q_bad2" ||
        [llength [[ord::get_db_block] getInsts]] != $after_count ||
        abs([endpoint_min_slack q_bad2] - $blocked_hold_before) > 1.0e-6 ||
        abs([sta::worst_slack -max] - $blocked_setup_before) > 1.0e-6} {
    error "Native setup guard failed to reject a timing-unsafe insertion"
}
write_sdc -no_timestamp [file join $blocked after.sdc]
if {[read_record [file join $blocked before.sdc]] ne [read_record [file join $blocked after.sdc]]} {
    error "Setup-guarded native call changed constraints"
}
puts "PASS_NATIVE_SETUP_GUARD_REJECTS_UNSAFE_DELAY_INSERTION setup_before=$blocked_setup_before setup_after=[sta::worst_slack -max]"

# No negative endpoints: the opt-in profile performs no margin-only sweep.
# Positive paths below +0.15 ns remain a separately recorded completion task.
set positive [file join $out no-negative-targets]
file mkdir $positive
set ::env(STEP_DIR) $positive
set_output_delay -min 0 -clock clk [get_ports {q_bad1 q_bad2}]
nssoc_timing_experiment hold_guarded_targeted
set positive_selection [read_record [file join $positive hold-targeted-selection.tcldict]]
if {[dict get $positive_selection selected_count] != 0 ||
        [dict get $positive_selection remaining_margin_repair_required] ne "true" ||
        [llength [[ord::get_db_block] getInsts]] != $after_count} {
    error "Zero-negative fixture performed a margin-only repair or claimed closure"
}
write_db [file join $out tiny-after.odb]
write_verilog [file join $out tiny-after.v]

# A path already containing a delay cell can add more than the native budget
# during a single per-pin pass. Exercise the real C++ overrun and reject its
# isolated candidate, including when C++ itself raises RSZ-0060 before return.
set overrun [file join $out native-budget-overrun]
file mkdir $overrun
set ::env(STEP_DIR) $overrun
set_output_delay -max 3 -clock clk [get_ports q_bad2]
set_output_delay -min -2 -clock clk [get_ports q_bad1]
set overrun_initial [llength [[ord::get_db_block] getInsts]]
set failed [catch {nssoc_hold_guarded_targeted 1} message]
if {!$failed || ![string match {*global buffer budget violated*} $message]} {
    error "The real native buffer overrun was not rejected: $message"
}
set failure [read_record [file join $overrun hold-targeted-budget-failure.tcldict]]
if {[dict get $failure candidate_accepted] ne "false" ||
        [dict get $failure phase] ne "after_call" ||
        [dict get $failure initial_instance_count] != $overrun_initial ||
        [dict get $failure global_buffer_budget] != int(floor(0.4 * $overrun_initial)) ||
        [dict get $failure actual_instance_growth] <= [dict get $failure global_buffer_budget] ||
        [file exists [file join $overrun hold-targeted-result.tcldict]]} {
    error "Invalid fail-closed budget overrun evidence: $failure"
}
write_db [file join $overrun rejected-candidate.odb]
puts "PASS_REAL_NATIVE_BUDGET_OVERRUN_REJECTED growth=[dict get $failure actual_instance_growth] budget=[dict get $failure global_buffer_budget]"
puts "NATIVE_TARGETED_FIXTURE q_bad1_before=$before1 q_bad1_after=$after1 q_bad2_before=$before2 q_bad2_after=$after2 cells_before=$before_count cells_after=$after_count setup_before=$before_setup setup_after=$after_setup"
puts "PASS_REAL_NATIVE_TARGETED_HOLD_SMALL_FIXTURE_NOT_CHIP_SIGNOFF"
