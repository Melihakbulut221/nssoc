# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Tiny real IHP long-wire repair proves the exact native API before chip load.
foreach key {NSSOC_ELECTRICAL_ROOT NSSOC_ELECTRICAL_OUT NSSOC_TARGETED_PDK_ROOT} {
    if {![info exists ::env($key)]} {error "$key is required"}
}
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_hold_reproducibility.tcl]
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_electrical_margin_helpers.tcl]
set out $::env(NSSOC_ELECTRICAL_OUT)
if {[file exists $out]} {error "Electrical fixture output already exists"}
file mkdir $out
set std [file join $::env(NSSOC_TARGETED_PDK_ROOT) ihp-sg13g2 libs.ref sg13g2_stdcell]
read_lef [file join $std lef sg13g2_tech.lef]
read_lef [file join $std lef sg13g2_stdcell.lef]
define_corners fast typical slow
foreach {corner liberty} {fast sg13g2_stdcell_fast_1p32V_m40C.lib typical sg13g2_stdcell_typ_1p20V_25C.lib slow sg13g2_stdcell_slow_1p08V_125C.lib} {
    read_liberty -corner $corner [file join $std lib $liberty]
}
set f [open [file join $out before.v] {WRONLY CREAT EXCL}]
puts $f {module tiny(input clk,input rst_n,input d,input independent,output q,output q2);
 wire target,guarded;
 sg13g2_buf_1 driver(.A(d),.X(target));
 sg13g2_dfrbpq_1 \bank[0].sink (.CLK(clk),.RESET_B(rst_n),.D(target),.Q(q));
 sg13g2_buf_1 untouched(.A(independent),.X(guarded));
 sg13g2_dfrbpq_1 sink2(.CLK(clk),.RESET_B(rst_n),.D(guarded),.Q(q2));
endmodule}
close $f
read_verilog [file join $out before.v]
link_design tiny
initialize_floorplan -die_area {0 0 12000 100} -core_area {5 5 11995 95} -site CoreSite
make_tracks
set native_sink {bank\[0\].sink}
foreach name [list driver $native_sink untouched sink2] x {20160 11000160 50400 70560} {
    set inst [[ord::get_db_block] findInst $name]
    $inst setLocation $x 15120; $inst setOrient R0; $inst setPlacementStatus PLACED
}
set i 0
foreach name {clk rst_n d independent q q2} {
    place_pin -pin_name $name -layer Metal2 -location [list 0 [expr {10+10*$i}]]; incr i
}
detailed_placement
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
create_clock -period 20 [get_ports clk]
set_input_delay -max 0.5 -clock clk [get_ports {d independent}]
set_input_delay -min 0.1 -clock clk [get_ports {d independent}]
set_output_delay -max 0.5 -clock clk [get_ports {q q2}]
set_output_delay -min 0 -clock clk [get_ports {q q2}]
set_wire_rc -signal -layer Metal2
set_wire_rc -clock -layer Metal2
estimate_parasitics -placement
set before [sta::max_capacitance_violation_count]
if {$before < 1} {error "Tiny actual long-wire fixture has no real capacitance violation"}
write_sdc -no_timestamp [file join $out before.sdc]
write_verilog [file join $out mapped-before.v]
nssoc_electrical_status [file join $out before-status.tsv]
nssoc_electrical_report $out before {{driver target}}
set count [llength [[ord::get_db_block] getInsts]]
rename rsz::repair_net_cmd rsz::saved_repair_net_cmd
set missing [catch {nssoc_electrical_margin_repair driver target}]
rename rsz::saved_repair_net_cmd rsz::repair_net_cmd
set wrong [catch {nssoc_electrical_margin_repair driver guarded}]
set absent [catch {nssoc_electrical_margin_repair missing target}]
set_dont_touch [get_nets target]
set protected [catch {nssoc_electrical_margin_repair driver target}]
unset_dont_touch [get_nets target]
if {!$missing || !$wrong || !$absent || !$protected || [llength [[ord::get_db_block] getInsts]] != $count} {
    error "Electrical boundary negative controls failed or mutated fixture"
}
set actual_sink [[ord::get_db_block] findInst $native_sink]
if {$actual_sink eq "NULL" || [$actual_sink getName] ne $native_sink} {error "Native escaped instance spelling differs"}
nssoc_electrical_margin_graph driver target [list [list driver sg13g2_buf_1 X] [list $native_sink sg13g2_dfrbpq_1 D]]
set wrong_graph [catch {nssoc_electrical_margin_graph driver target [list [list driver sg13g2_buf_1 X] [list $native_sink sg13g2_dfrbpq_1 CLK]]}]
set unescaped_name [catch {nssoc_electrical_margin_graph driver target {{driver sg13g2_buf_1 X} {{bank[0].sink} sg13g2_dfrbpq_1 D}}}]
set omitted_terminal [catch {nssoc_electrical_margin_graph driver target {{driver sg13g2_buf_1 X}}}]
if {!$wrong_graph || !$unescaped_name || !$omitted_terminal || [llength [[ord::get_db_block] getInsts]] != $count} {
    error "Native terminal graph negative controls were not rejected before mutation"
}
set untouched [list [[[[ord::get_db_block] findInst untouched] getMaster] getName] \
    [[[[ord::get_db_block] findInst untouched] findITerm X] getNet]]
set call [nssoc_electrical_margin_repair driver target]
global_connect
detailed_placement
check_placement -verbose
estimate_parasitics -placement
sta::delays_invalid
sta::find_timing -full_update
set after [sta::max_capacitance_violation_count]
if {$after >= $before || [llength [[ord::get_db_block] getInsts]] <= $count} {error "Actual targeted native repair did not improve real fixture capacitance"}
if {[list [[[[ord::get_db_block] findInst untouched] getMaster] getName] \
    [[[[ord::get_db_block] findInst untouched] findITerm X] getNet]] ne $untouched} {error "Unrelated fixture driver changed"}
nssoc_electrical_report $out after {{driver target}}
nssoc_electrical_status [file join $out after-status.tsv]
write_sdc -no_timestamp [file join $out after.sdc]
write_verilog [file join $out after.v]
if {[nssoc_hold_sha [file join $out before.sdc]] ne [nssoc_hold_sha [file join $out after.sdc]]} {error "Native electrical fixture changed SDC"}
nssoc_hold_write_json [file join $out result.json] [nssoc_hold_jobject [dict create \
    status [nssoc_hold_jstr PASS_NATIVE_ELECTRICAL_CONTROL] missing_api_rejected true \
    wrong_net_rejected true missing_driver_rejected true dont_touch_rejected true wrong_graph_rejected true \
    unescaped_name_rejected true omitted_terminal_rejected true native_escaped_name_verified true \
    real_capacitance_before $before real_capacitance_after $after unrelated_driver_preserved true \
    call [nssoc_hold_jobject $call] constraints_preserved true \
    candidate_adopted false timing_accepted false manufacturing_approval false]]
puts PASS_NATIVE_ELECTRICAL_CONTROL_NO_CHIP_ACCEPTANCE
