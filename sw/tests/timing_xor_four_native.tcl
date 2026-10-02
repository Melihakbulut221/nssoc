# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Real pinned SG13G2 insert_buffer and three-corner STA; only a tiny fixture.
foreach key {NSSOC_XOR_ROOT NSSOC_XOR_OUT NSSOC_TARGETED_PDK_ROOT} {
    if {![info exists ::env($key)]} {error "$key is required"}
}
source [file join $::env(NSSOC_XOR_ROOT) hw/soc/pnr/timing_hold_reproducibility.tcl]
source [file join $::env(NSSOC_XOR_ROOT) hw/soc/pnr/timing_xor_buffer_helpers.tcl]
source [file join $::env(NSSOC_XOR_ROOT) hw/soc/pnr/timing_xor_pair_helpers.tcl]
source [file join $::env(NSSOC_XOR_ROOT) hw/soc/pnr/timing_xor_four_helpers.tcl]
set out $::env(NSSOC_XOR_OUT)
if {[file exists $out]} {error "XOR control output already exists"}
file mkdir $out
set std [file join $::env(NSSOC_TARGETED_PDK_ROOT) ihp-sg13g2 libs.ref sg13g2_stdcell]
read_lef [file join $std lef sg13g2_tech.lef]
read_lef [file join $std lef sg13g2_stdcell.lef]
define_corners fast typical slow
foreach {corner liberty} {fast sg13g2_stdcell_fast_1p32V_m40C.lib typical sg13g2_stdcell_typ_1p20V_25C.lib slow sg13g2_stdcell_slow_1p08V_125C.lib} {
    read_liberty -corner $corner [file join $std lib $liberty]
}
set f [open [file join $out tiny.v] {WRONLY CREAT EXCL}]
puts $f {module tiny(input clk, input rst_n, input a, input b, input c, output q, output q2, output q3, output q4);
 wire _017423_, w;
 sg13g2_xor2_1 _071517_(.A(a),.B(b),.X(_017423_));
 sg13g2_xnor2_1 _071519_(.A(_017423_),.B(c),.Y(w));
 sg13g2_dfrbpq_1 f0(.CLK(clk),.RESET_B(rst_n),.D(w),.Q(q));
wire _016495_, w2, w3;
 sg13g2_xnor2_1 _070589_(.A(a),.B(b),.Y(_016495_));
 sg13g2_a22oi_1 _070602_(.A1(a),.A2(_016495_),.B1(b),.B2(c),.Y(w2));
 sg13g2_a221oi_1 _072894_(.A1(_016495_),.A2(w2),.B1(b),.B2(c),.C1(a),.Y(w3));
 sg13g2_dfrbpq_1 f1(.CLK(clk),.RESET_B(rst_n),.D(w3),.Q(q2));
wire _018473_, w4, _020735_, w5;
 sg13g2_xnor2_1 _072567_(.A(a),.B(b),.Y(_018473_));
 sg13g2_xnor2_1 _072570_(.A(_018473_),.B(c),.Y(w4));
 sg13g2_dfrbpq_1 f2(.CLK(clk),.RESET_B(rst_n),.D(w4),.Q(q3));
 sg13g2_nand4_1 _074829_(.A(a),.B(b),.C(c),.D(rst_n),.Y(_020735_));
 sg13g2_xor2_1 _074831_(.A(c),.B(_020735_),.X(w5));
 sg13g2_dfrbpq_1 f3(.CLK(clk),.RESET_B(rst_n),.D(w5),.Q(q4));
endmodule}
close $f
read_verilog [file join $out tiny.v]
link_design tiny
initialize_floorplan -die_area {0 0 450 100} -core_area {5 5 445 95} -site CoreSite
make_tracks
foreach name {_071517_ _071519_ f0 _070589_ _070602_ _072894_ f1 _072567_ _072570_ f2 _074829_ _074831_ f3} x {20160 365280 400320 24960 327360 365760 405120 20160 365280 400320 24960 365760 405120} {
    set inst [[ord::get_db_block] findInst $name]
    set y 15120
    if {$name in {_070589_ _070602_ _072894_ f1}} {set y 60480}
    if {$name in {_072567_ _072570_ f2}} {set y 34020}
    if {$name in {_074829_ _074831_ f3}} {set y 79380}
    $inst setLocation $x $y
    $inst setOrient R0
    $inst setPlacementStatus PLACED
}
set i 0
foreach name {clk rst_n a b c q q2 q3 q4} {
    place_pin -pin_name $name -layer Metal2 -location [list 0 [expr {10+10*$i}]]
    incr i
}
detailed_placement
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
create_clock -period 20 [get_ports clk]
set_input_delay -max 0.5 -clock clk [get_ports {a b c}]
set_input_delay -min 0.1 -clock clk [get_ports {a b c}]
set_output_delay -max 0.5 -clock clk [get_ports {q q2 q3 q4}]
set_output_delay -min 0 -clock clk [get_ports {q q2 q3 q4}]
set_wire_rc -signal -layer Metal2
set_wire_rc -clock -layer Metal2
estimate_parasitics -placement
write_sdc -no_timestamp [file join $out before.sdc]
nssoc_xor_graph [file join $out before.tsv]
set count [llength [[ord::get_db_block] getInsts]]
rename insert_buffer xor_saved_insert_buffer
set missing [catch {nssoc_xor_insert} message]
rename xor_saved_insert_buffer insert_buffer
if {!$missing || ![string match *API* $message]} {error "Missing insertion API was not rejected"}
set extra [[[ord::get_db_block] findInst _071519_] findITerm B]
set original [$extra getNet]
$extra connect [[ord::get_db_block] findNet _017423_]
set fanout [catch {nssoc_xor_insert} message]
$extra connect $original
if {!$fanout || ![string match *exactly* $message] || [llength [[ord::get_db_block] getInsts]] != $count} {
    error "Extra fanout was not rejected before mutation"
}
set first_sink [[[ord::get_db_block] findInst _071519_] findITerm A]
set first_net [$first_sink getNet]
$first_sink disconnect
set first_missing [catch {nssoc_xor_insert} message]
$first_sink connect $first_net
if {!$first_missing || ![string match *exactly* $message]} {error "First missing sink not rejected"}
$first_sink disconnect
$extra connect $first_net
set first_wrong [catch {nssoc_xor_insert} message]
$extra connect $original
$first_sink connect $first_net
if {!$first_wrong || ![string match *identity* $message] || [llength [[ord::get_db_block] getInsts]] != $count} {error "First wrong sink not rejected before mutation"}
estimate_parasitics -placement
set insertion [nssoc_xor_insert]
global_connect
detailed_placement
check_placement -verbose
nssoc_xor_verify $insertion
nssoc_xor_verify_power $insertion
nssoc_xor_graph [file join $out first.tsv]
nssoc_xor_graph [file join $out first-contracted.tsv] $insertion
if {[nssoc_hold_sha [file join $out before.tsv]] ne [nssoc_hold_sha [file join $out first-contracted.tsv]]} {
    error "Native buffer contraction changed original fixture logic"
}
set duplicate [catch {nssoc_xor_insert} message]
if {!$duplicate || ![string match *already* $message] || [llength [[ord::get_db_block] getInsts]] != $count+1} {
    error "Duplicate insertion was not rejected before mutation"
}
# Mutate only tiny fixture wiring to prove exact two-load preflight refusals.
set block [ord::get_db_block]
set sink [[$block findInst _072894_] findITerm A1]
set target [$sink getNet]
$sink disconnect
set missing_sink [catch {nssoc_xnor_insert} message]
$sink connect $target
if {!$missing_sink || ![string match *exactly* $message]} {error "Missing sink was not rejected"}
set extra [[$block findInst _072894_] findITerm B1]
set other [$extra getNet]
$extra connect $target
set extra_sink [catch {nssoc_xnor_insert} message]
$extra connect $other
if {!$extra_sink || ![string match *exactly* $message]} {error "Extra second-target sink was not rejected"}
$sink disconnect
$extra connect $target
set wrong_sink [catch {nssoc_xnor_insert} message]
$extra connect $other
$sink connect $target
if {!$wrong_sink || ![string match *identity* $message]} {error "Wrong sink was not rejected"}
if {[llength [$block getInsts]] != $count+1} {error "Rejected second target mutated cells"}
estimate_parasitics -placement
set second [nssoc_xnor_insert]
global_connect
detailed_placement
check_placement -verbose
nssoc_xnor_verify $second
nssoc_xnor_verify_power $second
nssoc_xor_verify_power $insertion
set pg [[ $block findInst [dict get $second buffer]] findITerm VDD]
set supply [$pg getNet]
$pg disconnect
set bad_power [catch {nssoc_xnor_verify_power $second} message]
$pg connect $supply
if {!$bad_power || ![string match *floating* $message]} {error "Floating power was not rejected"}
set wrong_supply [[[$block findInst [dict get $second buffer]] findITerm VSS] getNet]
$pg connect $wrong_supply
set wrong_power [catch {nssoc_xnor_verify_power $second} message]
$pg connect $supply
if {!$wrong_power || ![string match *differs* $message]} {error "Wrong power was not rejected"}
nssoc_pair_graph [file join $out second.tsv]
nssoc_pair_graph [file join $out second-contracted.tsv] [list $insertion $second]
if {[nssoc_hold_sha [file join $out before.tsv]] ne [nssoc_hold_sha [file join $out second-contracted.tsv]]} {error "Pair contraction changed fixture logic"}
set second_duplicate [catch {nssoc_xnor_insert} message]
if {!$second_duplicate || ![string match *already* $message] || [llength [$block getInsts]] != $count+2} {error "Second duplicate not rejected"}
set insertions [list $insertion $second]
set inserted_json [list [nssoc_xor_insertion_json $insertion] [nssoc_xnor_insertion_json $second]]
set extra_controls {}
foreach index {3 4} graph {third.tsv after.tsv} spare_pin {B A} {
    set target_info [nssoc_four_target $index]
    set sink_inst [$block findInst [dict get $target_info sink]]
    set sink [$sink_inst findITerm [dict get $target_info sink_pin]]
    set net [$sink getNet]; set spare [$sink_inst findITerm $spare_pin]; set other [$spare getNet]
    set before_count [llength [$block getInsts]]
    $sink disconnect
    set missing [catch {nssoc_four_insert $index} message]
    $sink connect $net
    if {!$missing || ![string match *exactly* $message]} {error "Fixed missing sink not rejected"}
    $spare connect $net
    set extra [catch {nssoc_four_insert $index} message]
    $spare connect $other
    if {!$extra || ![string match *exactly* $message]} {error "Fixed extra sink not rejected"}
    $sink disconnect
    $spare connect $net
    set wrong [catch {nssoc_four_insert $index} message]
    $spare connect $other
    $sink connect $net
    if {!$wrong || ![string match *identity* $message] || [llength [$block getInsts]] != $before_count} {error "Fixed wrong sink not rejected before mutation"}
    estimate_parasitics -placement
    set added [nssoc_four_insert $index]
    lappend insertions $added
    lappend inserted_json [nssoc_four_json $added]
    global_connect
    detailed_placement
    check_placement -verbose
    nssoc_four_verify_all $insertions
    set pg [[$block findInst [dict get $added buffer]] findITerm VDD]
    set supply [$pg getNet]
    $pg disconnect
    set bad_power [catch {nssoc_four_verify_power $added} message]
    $pg connect $supply
    if {!$bad_power || ![string match *floating* $message]} {error "Fixed floating power not rejected"}
    set ground [[[$block findInst [dict get $added buffer]] findITerm VSS] getNet]
    $pg connect $ground
    set wrong_power [catch {nssoc_four_verify_power $added} message]
    $pg connect $supply
    if {!$wrong_power || ![string match *differs* $message]} {error "Fixed wrong power not rejected"}
    set duplicate [catch {nssoc_four_insert $index} message]
    if {!$duplicate || ![string match *already* $message] || [llength [$block getInsts]] != $before_count+1} {error "Fixed duplicate not rejected"}
    nssoc_pair_graph [file join $out $graph]
    lappend extra_controls [nssoc_hold_jobject [dict create index $index missing_sink_rejected true wrong_sink_rejected true extra_sink_rejected true floating_power_rejected true wrong_power_rejected true duplicate_rejected true]]
}
nssoc_pair_graph [file join $out contracted.tsv] $insertions
if {[nssoc_hold_sha [file join $out before.tsv]] ne [nssoc_hold_sha [file join $out contracted.tsv]]} {error "Four-buffer fixture contraction changed logic"}
estimate_parasitics -placement
sta::delays_invalid
sta::find_timing -full_update
set corners {}
foreach corner [sta::corners] {
    set name [$corner name]
    report_checks -corner $name -path_delay min_max -group_path_count 2 -digits 9 > [file join $out "$name.rpt"]
    lappend corners [nssoc_hold_jstr $name]
}
write_sdc -no_timestamp [file join $out after.sdc]
if {[nssoc_hold_sha [file join $out before.sdc]] ne [nssoc_hold_sha [file join $out after.sdc]]} {error "XOR fixture changed constraints"}
write_verilog [file join $out after.v]
set row [dict create status [nssoc_hold_jstr PASS_NATIVE_XOR_FOUR_CONTROL] \
    missing_sink_rejected true wrong_sink_rejected true extra_second_sink_rejected true floating_power_rejected true wrong_power_rejected true second_duplicate_rejected true \
    first_missing_sink_rejected true first_wrong_sink_rejected true missing_api_rejected true extra_fanout_rejected true duplicate_rejected true \
    original_graph_preserved true constraints_preserved true supply_connections_preserved true \
    corners "\[[join $corners ,]\]" insertions "\[[join $inserted_json ,]\]" extra_target_controls "\[[join $extra_controls ,]\]" \
    timing_accepted false candidate_adopted false manufacturing_approval false]
nssoc_hold_write_json [file join $out result.json] [nssoc_hold_jobject $row]
puts "PASS_NATIVE_XOR_FOUR_CONTROL_NO_CHIP_ACCEPTANCE"
