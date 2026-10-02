# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Small native sizing/API control. This fixture contains no chip input.
foreach key {NSSOC_ELECTRICAL_ROOT NSSOC_CRITICAL_OUT NSSOC_TARGETED_PDK_ROOT} {
    if {![info exists ::env($key)]} {error "$key is required"}
}
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_hold_reproducibility.tcl]
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_critical_followup_helpers.tcl]
set out $::env(NSSOC_CRITICAL_OUT)
if {[file exists $out]} {error "Critical sizing fixture output already exists"}
file mkdir $out
set std [file join $::env(NSSOC_TARGETED_PDK_ROOT) ihp-sg13g2 libs.ref sg13g2_stdcell]
read_lef [file join $std lef/sg13g2_tech.lef]
read_lef [file join $std lef/sg13g2_stdcell.lef]
define_corners fast typical slow
foreach {corner liberty} {fast sg13g2_stdcell_fast_1p32V_m40C.lib typical sg13g2_stdcell_typ_1p20V_25C.lib slow sg13g2_stdcell_slow_1p08V_125C.lib} {
    read_liberty -corner $corner [file join $std lib $liberty]
}
set f [open [file join $out before.v] {WRONLY CREAT EXCL}]
puts $f {module tiny(input clk,input rst_n,input d,input other,output q,output q2,output spare);
 wire target;
 sg13g2_buf_4 driver(.A(d),.X(target));
 sg13g2_buf_1 blocker(.A(other),.X(spare));
 sg13g2_dfrbpq_1 sink(.CLK(clk),.RESET_B(rst_n),.D(target),.Q(q));
 sg13g2_dfrbpq_1 sink2(.CLK(clk),.RESET_B(rst_n),.D(target),.Q(q2));
endmodule}
close $f
read_verilog [file join $out before.v]
link_design tiny
initialize_floorplan -die_area {0 0 200 100} -core_area {5 5 195 95} -site CoreSite
make_tracks
set block [ord::get_db_block]
foreach name {driver blocker sink sink2} x {20160 30240 50400 70560} {
    set inst [$block findInst $name]
    $inst setLocation $x 15120
    $inst setOrient R0
    $inst setPlacementStatus PLACED
}
set i 0
foreach name {clk rst_n d other q q2 spare} {
    place_pin -pin_name $name -layer Metal2 -location [list 0 [expr {10+10*$i}]]
    incr i
}
detailed_placement
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
create_clock -period 20 [get_ports clk]
set_input_delay -max 0.5 -clock clk [get_ports {d other}]
set_input_delay -min 0.1 -clock clk [get_ports {d other}]
set_output_delay -max 0.5 -clock clk [get_ports {q q2 spare}]
set_output_delay -min 0 -clock clk [get_ports {q q2 spare}]
set_wire_rc -signal -layer Metal2
set_wire_rc -clock -layer Metal2
set driver [$block findInst driver]
set blocker [$block findInst blocker]
set xy [$driver getLocation]
# A legal eight-site gap intentionally becomes an overlap after the 13-site swap.
$blocker setLocation [expr {[lindex $xy 0]+[[$driver getMaster] getWidth]}] [lindex $xy 1]
$blocker setOrient [$driver getOrient]
check_placement -verbose
estimate_parasitics -placement
sta::find_timing -full_update
write_sdc -no_timestamp [file join $out before.sdc]
write_db [file join $out before.odb]
write_verilog [file join $out mapped-before.v]
set original_connections [nssoc_critical_connections $driver]
set original_count [llength [$block getInsts]]
proc critical_all_connections {} {
    set rows {}
    foreach inst [[ord::get_db_block] getInsts] {
        lappend rows [list [$inst getName] [nssoc_critical_connections $inst]]
    }
    return [lsort $rows]
}
set all_connections [critical_all_connections]
set expected_place [concat [$driver getLocation] [list [$driver getOrient] [$driver getPlacementStatus]]]
set expected_terms {{driver sg13g2_buf_4 X} {sink sg13g2_dfrbpq_1 D} {sink2 sg13g2_dfrbpq_1 D}}
set target [$block findNet target]
set input [$block findNet d]
set failures {}
proc critical_expect_rejection {name command} {
    if {![catch {uplevel 1 $command} message]} {error "Negative control unexpectedly accepted: $name"}
    dict set ::failures $name [nssoc_hold_jstr $message]
}
set call [list nssoc_critical_size_preflight driver d target $expected_terms $expected_place]
{*}$call
critical_expect_rejection wrong_input [list nssoc_critical_size_preflight driver other target $expected_terms $expected_place]
critical_expect_rejection wrong_graph [list nssoc_critical_size_preflight driver d target [lrange $expected_terms 0 1] $expected_place]
critical_expect_rejection wrong_place [list nssoc_critical_size_preflight driver d target $expected_terms {0 0 R0 PLACED}]
$target setSigType CLOCK
critical_expect_rejection clock_net $call
$target setSigType SIGNAL
set_dont_touch [get_nets target]
critical_expect_rejection protected_net $call
unset_dont_touch [get_nets target]
set_dont_touch [get_cells driver]
critical_expect_rejection protected_driver $call
unset_dont_touch [get_cells driver]
set_dont_touch [get_cells sink]
critical_expect_rejection protected_load $call
unset_dont_touch [get_cells sink]
set_dont_touch [get_nets d]
critical_expect_rejection protected_input $call
unset_dont_touch [get_nets d]
$driver setPlacementStatus FIRM
critical_expect_rejection fixed_driver $call
$driver setPlacementStatus UNPLACED
critical_expect_rejection unplaced_driver $call
$driver setPlacementStatus [lindex $expected_place 3]
foreach pin {VDD VSS} {
    set term [$driver findITerm $pin]
    set original_net [$term getNet]
    if {$original_net eq "NULL"} {error "Native fixture PG baseline is disconnected"}
    $term disconnect
    critical_expect_rejection missing_$pin $call
    $term connect $original_net
}
set before_shape [nssoc_critical_shape [$driver getMaster]]
set after_shape [nssoc_critical_shape [[ord::get_db] findMaster sg13g2_buf_8]]
foreach key {width height site site_width site_height pinmap} {
    set corrupted $after_shape
    dict set corrupted $key altered_guard_value
    critical_expect_rejection incompatible_${key}_guard [list nssoc_critical_shapes_compatible $before_shape $corrupted]
}
if {[critical_all_connections] ne $all_connections || [llength [$block getInsts]] != $original_count ||
    [concat [$driver getLocation] [list [$driver getOrient] [$driver getPlacementStatus]]] ne $expected_place} {
    error "Negative controls failed to preserve native fixture state"
}
{*}$call
set sized [nssoc_critical_size driver d target $expected_terms $expected_place]
set overlap [catch {check_placement -verbose} overlap_message]
if {!$overlap} {error "Native placement checker failed to detect deliberate post-swap overlap"}
write_def [file join $out overlapping-after-swap.def]
detailed_placement
check_placement -verbose
if {[critical_all_connections] ne $all_connections || [llength [$block getInsts]] != $original_count} {
    error "Legalization changed native driver connectivity or instance count"
}
estimate_parasitics -placement
sta::delays_invalid
sta::find_timing -full_update
foreach corner {fast typical slow} {
    report_checks -corner $corner -through [get_pins driver/X] -path_delay min_max \
        -fields {slew cap input fanout} -digits 9 \
        > [file join $out after-$corner.rpt]
    set report [open [file join $out after-$corner.rpt] r]
    set text [read $report]
    close $report
    if {[string first "driver/X (sg13g2_buf_8)" $text] < 0 || [string first "Corner: $corner" $text] < 0} {
        error "Native sized driver has no observed timing path in $corner"
    }
}
# Actual debug/report APIs used by the separate hold-observation child.
foreach {category level} {repair_hold 3 resizer 1 journal 1} {
    set_debug_level RSZ $category $level
    set_debug_level RSZ $category 0
}
report_buffers > [file join $out native-report-buffers.rpt]
rsz::report_buffers_cmd 0
write_sdc -no_timestamp [file join $out after.sdc]
write_db [file join $out after.odb]
write_verilog [file join $out after.v]
set before_sha [nssoc_hold_sha [file join $out before.sdc]]
set after_sha [nssoc_hold_sha [file join $out after.sdc]]
if {$before_sha ne $after_sha} {error "Native sizing fixture changed source SDC"}
set flags {}
foreach name [dict keys $failures] {dict set flags ${name}_rejected true}
nssoc_hold_write_json [file join $out result.json] [nssoc_hold_jobject [dict merge $flags [dict create \
    status [nssoc_hold_jstr PASS_NATIVE_CRITICAL_SIZE_CONTROL] \
    negative_control_messages [nssoc_hold_jobject $failures] \
    synthetic_shape_guard_scope [nssoc_hold_jstr {Mutated copies of native measured master properties; not alternate-layout validation.}] \
    call [nssoc_hold_jobject $sized] native_overlap_detected true native_overlap_repaired true \
    native_overlap_error [nssoc_hold_jstr $overlap_message] \
    all_three_corners_loaded_and_timed true constraints_preserved true pg_bindings_preserved true \
    all_instance_connections_preserved true \
    pre_sdc_sha256 [nssoc_hold_jstr $before_sha] post_sdc_sha256 [nssoc_hold_jstr $after_sha] \
    debug_hold_resizer_journal_api_called true native_report_buffers_called true \
    native_report_buffers_cmd_zero_called true \
    candidate_adopted false timing_accepted false manufacturing_approval false]]]
puts PASS_NATIVE_CRITICAL_SIZE_CONTROL_NO_CHIP_ACCEPTANCE
