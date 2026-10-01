# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Cloud-first, tiny native API/coverage/precision/physical mutation controls.
foreach key {NSSOC_PDK_ROOT NSSOC_TEST_OUT NSSOC_HOLD_DIAGNOSTIC_HELPER} {
    if {![info exists ::env($key)]} {error "$key is required"}
}
set out $::env(NSSOC_TEST_OUT)
if {[file exists $out]} {error "Fixture output must be fresh"}
file mkdir $out
source $::env(NSSOC_HOLD_DIAGNOSTIC_HELPER)
set std [file join $::env(NSSOC_PDK_ROOT) ihp-sg13g2 libs.ref sg13g2_stdcell]
read_lef [file join $std lef sg13g2_tech.lef]
read_lef [file join $std lef sg13g2_stdcell.lef]
define_corners fast typical slow
foreach {corner liberty} {
    fast sg13g2_stdcell_fast_1p32V_m40C.lib
    typical sg13g2_stdcell_typ_1p20V_25C.lib
    slow sg13g2_stdcell_slow_1p08V_125C.lib
} {read_liberty -corner $corner [file join $std lib $liberty]}
set stream [open [file join $out tiny.v] {WRONLY CREAT EXCL}]
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
set_routing_layers -signal Metal2-Metal5 -clock Metal2-Metal5
global_route -allow_congestion
estimate_parasitics -global_routing
set snapshots {}
set first [nssoc_hold_snapshot original $out]
lappend snapshots [dict get $first json]
set repeat [nssoc_hold_snapshot repeat $out]
lappend snapshots [dict get $repeat json]
nssoc_hold_assert_same_physical $first $repeat
sta::arrivals_invalid
sta::find_timing
set arrivals [nssoc_hold_snapshot arrivals $out]
lappend snapshots [dict get $arrivals json]
nssoc_hold_assert_same_physical $first $arrivals
sta::delays_invalid
sta::find_timing -full_update
set updated [nssoc_hold_snapshot full_update $out]
lappend snapshots [dict get $updated json]
nssoc_hold_assert_same_physical $first $updated

# Require both negative and positive native endpoint values independently.
set stream [open [file join $out original endpoints.tsv] r]
set table [split [read $stream] \n]
close $stream
set slack_by_pin {}
foreach row [lrange $table 1 end] {
    if {$row eq ""} {continue}
    lassign [split $row \t] pin slack
    dict set slack_by_pin $pin $slack
}
foreach pin {q_bad1 q_bad2 q_good} {
    if {![dict exists $slack_by_pin $pin]} {error "Fixture endpoint absent: $pin"}
    set slack [dict get $slack_by_pin $pin]
    if {$slack eq "UNCONSTRAINED"} {error "Fixture endpoint unexpectedly unconstrained"}
    if {$pin eq "q_good" && $slack <= 0} {error "Positive fixture endpoint is not positive"}
    if {$pin ne "q_good" && $slack >= 0} {error "Violating fixture endpoint is not negative"}
}
set expected [sta::endpoint_path_count]
set all_names {}
foreach pin [sta::endpoints] {lappend all_names [get_property $pin full_name]}
set negative [sta::endpoint_violation_count min]
if {![catch {nssoc_hold_assert_coverage $expected [lrange $all_names 1 end] $negative $negative}]} {
    error "Dropped native endpoint incorrectly accepted"
}
if {![catch {nssoc_hold_assert_path_coverage [dict create q_bad1 -1e-9] [dict create]}]} {
    error "Finite negative endpoint omitted in every corner incorrectly accepted"
}
if {![catch {nssoc_hold_assert_units 1.0}]} {error "Corrupt time units incorrectly accepted"}
nssoc_hold_assert_units [sta::unit_scale time]

# Actually move and reroute a cell; the no-op guard must reject it.
global_route -start_incremental
set inst [[ord::get_db_block] findInst f0]
lassign [$inst getLocation] x y
$inst setLocation [expr {$x+31680}] [expr {$y+15120}]
detailed_placement
global_route -end_incremental
estimate_parasitics -global_routing
set mutated [nssoc_hold_snapshot rerouted_mutation $out]
lappend snapshots [dict get $mutated json]
if {[dict get $first fingerprints routing] eq [dict get $mutated fingerprints routing]} {
    error "Route mutation did not change native route segments"
}
if {![catch {nssoc_hold_assert_same_physical $first $mutated}]} {
    error "Real routed geometry mutation incorrectly accepted as no-op"
}
set cases {}
foreach name {complete_coverage bad_coverage corrupt_units route_mutation} {
    dict set cases $name [nssoc_hold_jobject [dict create passed true]]
}
set record [nssoc_hold_jobject [dict create status [nssoc_hold_jstr PASS_NATIVE_HOLD_FIXTURE_NATIVE_ONLY] \
    cases [nssoc_hold_jobject $cases] stages "\[[join $snapshots ,]\]" \
    timing_accepted false candidate_adopted false manufacturing_approval false]]
nssoc_hold_write_json [file join $out fixture.json] $record
puts "PASS_NATIVE_HOLD_REPRODUCIBILITY_FIXTURE"
