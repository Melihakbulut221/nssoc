# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Real four-cell data-endpoint hold repair and fail-closed boundary controls.
foreach key {NSSOC_ELECTRICAL_ROOT NSSOC_RESIDUAL_OUT NSSOC_TARGETED_PDK_ROOT} {
    if {![info exists ::env($key)]} {error "$key is required"}
}
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_hold_reproducibility.tcl]
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_residual_repair_helpers.tcl]
set out $::env(NSSOC_RESIDUAL_OUT)
if {[file exists $out]} {error "Residual fixture must be fresh"}
file mkdir $out
set std [file join $::env(NSSOC_TARGETED_PDK_ROOT) ihp-sg13g2 libs.ref sg13g2_stdcell]
read_lef [file join $std lef sg13g2_tech.lef]
read_lef [file join $std lef sg13g2_stdcell.lef]
define_corners fast typical slow
foreach {corner liberty} {fast sg13g2_stdcell_fast_1p32V_m40C.lib typical sg13g2_stdcell_typ_1p20V_25C.lib slow sg13g2_stdcell_slow_1p08V_125C.lib} {
    read_liberty -corner $corner [file join $std lib $liberty]
}
set f [open [file join $out tiny.v] {WRONLY CREAT EXCL}]
puts $f {module tiny(input clk,input rst_n,input d,input blocked,output q,output q2);
wire target, guarded;
sg13g2_buf_1 driver(.A(d),.X(target));
sg13g2_dfrbpq_1 sink(.CLK(clk),.RESET_B(rst_n),.D(target),.Q(q));
sg13g2_buf_1 other(.A(blocked),.X(guarded));
sg13g2_dfrbpq_1 sink2(.CLK(clk),.RESET_B(rst_n),.D(guarded),.Q(q2));
endmodule}
close $f
read_verilog [file join $out tiny.v]
link_design tiny
initialize_floorplan -die_area {0 0 200 100} -core_area {5 5 195 95} -site CoreSite
make_tracks
foreach name {driver sink other sink2} x {20160 40320 80640 100800} {
    set inst [[ord::get_db_block] findInst $name]
    $inst setLocation $x 15120; $inst setOrient R0; $inst setPlacementStatus PLACED
}
set i 0
foreach name {clk rst_n d blocked q q2} {
    place_pin -pin_name $name -layer Metal2 -location [list 0 [expr {10+10*$i}]]; incr i
}
detailed_placement
create_clock -period 20 [get_ports clk]
set_input_delay -max 0.5 -clock clk [get_ports d]
set_input_delay -max 20 -clock clk [get_ports blocked]
set_input_delay -min -0.8 -clock clk [get_ports {d blocked}]
set_output_delay -max 0.5 -clock clk [get_ports {q q2}]
set_output_delay -min 0 -clock clk [get_ports {q q2}]
set_wire_rc -signal -layer Metal2
set_wire_rc -clock -layer Metal2
estimate_parasitics -placement
set before [nssoc_residual_slack [nssoc_residual_hold_preflight sink/D sg13g2_dfrbpq_1]]
set blocked_before [nssoc_residual_slack [nssoc_residual_hold_preflight sink2/D sg13g2_dfrbpq_1]]
if {$before >= 0 || $blocked_before >= 0} {error "Real fixture lacks negative hold endpoints"}
write_sdc -no_timestamp [file join $out before.sdc]
write_verilog [file join $out before.v]
set count [llength [[ord::get_db_block] getInsts]]
set tests {}
foreach endpoint {absent/D sink/CLK sink/RESET_B sink/Q} {
    if {![catch {nssoc_residual_hold_repair $endpoint sg13g2_dfrbpq_1}]} {error "Bad endpoint accepted: $endpoint"}
}
rename rsz::repair_hold_pin rsz::saved_hold_pin
set missing [catch {nssoc_residual_hold_repair sink/D sg13g2_dfrbpq_1}]
rename rsz::saved_hold_pin rsz::repair_hold_pin
set wrong_master [catch {nssoc_residual_hold_repair sink/D sg13g2_dfrbp_1}]
set_dont_touch [get_nets target]
set protected [catch {nssoc_residual_hold_repair sink/D sg13g2_dfrbpq_1}]
unset_dont_touch [get_nets target]
set_dont_touch [get_cells driver]
set protected_driver [catch {nssoc_residual_hold_repair sink/D sg13g2_dfrbpq_1}]
unset_dont_touch [get_cells driver]
set target [[ord::get_db_block] findNet target]
$target setSigType CLOCK
set clock [catch {nssoc_residual_hold_repair sink/D sg13g2_dfrbpq_1}]
$target setSigType SIGNAL
set sink [[ord::get_db_block] findInst sink]
set original_status [$sink getPlacementStatus]
$sink setPlacementStatus FIRM
set fixed [catch {nssoc_residual_hold_repair sink/D sg13g2_dfrbpq_1}]
$sink setPlacementStatus UNPLACED
set unplaced [catch {nssoc_residual_hold_repair sink/D sg13g2_dfrbpq_1}]
$sink setPlacementStatus $original_status
set location [$sink getLocation]
set geometry [list [[$sink getMaster] getName] $location [$sink getOrient]]
nssoc_residual_geometry $geometry $geometry
$sink setLocation 50000 15120
set moved [list [[$sink getMaster] getName] [$sink getLocation] [$sink getOrient]]
set geometry_rejected [catch {nssoc_residual_geometry $geometry $moved}]
$sink setLocation {*}$location
if {!$missing || !$wrong_master || !$protected || !$protected_driver || !$fixed || !$unplaced || !$clock || !$geometry_rejected ||
    [llength [[ord::get_db_block] getInsts]] != $count} {error "Residual native negatives failed"}
# Exercise the actual native setup guard on a real data endpoint. No fake API.
set blocked_call [nssoc_residual_hold_repair sink2/D sg13g2_dfrbpq_1]
if {[llength [[ord::get_db_block] getInsts]] != $count ||
    [nssoc_residual_slack [sta::get_port_pin_error check sink2/D]] != $blocked_before} {
    error "Native setup safety refused neither insertion nor delay change"
}
set call [nssoc_residual_hold_repair sink/D sg13g2_dfrbpq_1]
detailed_placement
check_placement -verbose
estimate_parasitics -placement
sta::delays_invalid
sta::find_timing -full_update
set after [nssoc_residual_slack [sta::get_port_pin_error check sink/D]]
if {$after <= $before || [llength [[ord::get_db_block] getInsts]] <= $count} {
    error "Actual per-data-pin repair failed to improve fixture hold"
}
nssoc_residual_hold_reports $out after {{sink/D sg13g2_dfrbpq_1} {sink2/D sg13g2_dfrbpq_1}}
write_sdc -no_timestamp [file join $out after.sdc]
write_verilog [file join $out after.v]
if {[nssoc_hold_sha [file join $out before.sdc]] ne [nssoc_hold_sha [file join $out after.sdc]]} {error "Residual fixture changed constraints"}
nssoc_hold_write_json [file join $out result.json] [nssoc_hold_jobject [dict create \
    status [nssoc_hold_jstr PASS_NATIVE_RESIDUAL_CONTROL] wrong_endpoint_rejected true missing_api_rejected true \
    wrong_master_rejected true protected_rejected true protected_driver_rejected true \
    fixed_rejected true unplaced_rejected true clock_rejected true geometry_rejected true \
    native_setup_guard_preserved true constraints_preserved true \
    before_hold_seconds $before after_hold_seconds $after call [nssoc_hold_jobject $call] \
    setup_blocked_call [nssoc_hold_jobject $blocked_call] \
    candidate_adopted false timing_accepted false manufacturing_approval false]]
puts PASS_NATIVE_RESIDUAL_CONTROL_NO_CHIP_ACCEPTANCE
