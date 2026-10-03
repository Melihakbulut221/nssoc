# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Tiny native vacancy/insertion control. No chip inputs or placement repair.
foreach key {NSSOC_ELECTRICAL_ROOT NSSOC_EXPLICIT_OUT NSSOC_TARGETED_PDK_ROOT} {
    if {![info exists ::env($key)]} {error "$key is required"}
}
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_hold_reproducibility.tcl]
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_explicit_hold_helpers.tcl]
set out $::env(NSSOC_EXPLICIT_OUT)
if {[file exists $out]} {error "Explicit native output already exists"}
file mkdir $out
set std [file join $::env(NSSOC_TARGETED_PDK_ROOT) ihp-sg13g2 libs.ref sg13g2_stdcell]
read_lef [file join $std lef/sg13g2_tech.lef]
read_lef [file join $std lef/sg13g2_stdcell.lef]
define_corners fast typical slow
foreach {corner liberty} {fast sg13g2_stdcell_fast_1p32V_m40C.lib typical sg13g2_stdcell_typ_1p20V_25C.lib slow sg13g2_stdcell_slow_1p08V_125C.lib} {
    read_liberty -corner $corner [file join $std lib $liberty]
}
set f [open [file join $out before.v] {WRONLY CREAT EXCL}]
puts $f {module tiny(input clk,input rst_n,input d,input other,output q,output spare);
 wire target;
 sg13g2_dfrbpq_1 driver(.CLK(clk),.RESET_B(rst_n),.D(d),.Q(target));
 sg13g2_dfrbpq_1 sink(.CLK(clk),.RESET_B(rst_n),.D(target),.Q(q));
 sg13g2_buf_8 blocker(.A(other),.X(spare));
endmodule}
close $f
read_verilog [file join $out before.v]
link_design tiny
initialize_floorplan -die_area {0 0 200 100} -core_area {5 5 195 95} -site CoreSite
make_tracks
set block [ord::get_db_block]
foreach name {driver sink blocker} x {50400 80640 50400} y {30240 30240 26460} orient {R0 R0 MX} {
    set inst [$block findInst $name]
    $inst setOrient $orient
    $inst setLocation $x $y
    $inst setPlacementStatus PLACED
}
set index 0
foreach name {clk rst_n d other q spare} {
    place_pin -pin_name $name -layer Metal2 -location [list 0 [expr {10+10*$index}]]
    incr index
}
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
check_placement -verbose
create_clock -period 20 [get_ports clk]
set_input_delay -max 0.5 -clock clk [get_ports {d other}]
set_input_delay -min 0.1 -clock clk [get_ports {d other}]
set_output_delay -max 0.5 -clock clk [get_ports {q spare}]
set_output_delay -min 0 -clock clk [get_ports {q spare}]
set_wire_rc -signal -layer Metal2
set_wire_rc -clock -layer Metal2
estimate_parasitics -placement
sta::find_timing -full_update
write_sdc -no_timestamp [file join $out before.sdc]
write_db [file join $out before.odb]
nssoc_explicit_graph [file join $out pristine-graph.tsv]
nssoc_explicit_placement [file join $out pristine-objects.tsv]
set expected_place {}
foreach name {driver sink} {
    set inst [$block findInst $name]
    dict set expected_place $name [concat [$inst getLocation] [list [$inst getOrient] [$inst getPlacementStatus]]]
}
set call [list nssoc_explicit_preflight driver sink target $expected_place]
{*}$call
set failures {}
proc explicit_expect_rejection {name command} {
    if {![catch {uplevel 1 $command} message]} {error "Negative control unexpectedly accepted: $name"}
    dict set ::failures $name [nssoc_hold_jstr $message]
}
proc explicit_read {path} {
    set f [open $path r];set text [read $f];close $f;return $text
}
proc explicit_metrics {} {
    set metrics {}
    foreach corner {fast typical slow} {
        set values {}
        foreach delay {min max} {
            set paths [find_timing_paths -from [get_pins driver/CLK] -to [get_pins sink/D] \
                -corner $corner -path_delay $delay -group_path_count 1 -endpoint_path_count 1]
            if {[llength $paths] != 1} {error "Missing tiny $corner/$delay register path"}
            set slack [get_property [lindex $paths 0] slack]
            dict set ::explicit_slacks $corner $delay $slack
            dict set values ${delay}_slack_ns [nssoc_hold_number $slack]
        }
        dict set metrics $corner [nssoc_hold_jobject $values]
    }
    return $metrics
}
set before_metrics [explicit_metrics]
set before_slacks $explicit_slacks
explicit_expect_rejection missing_driver [list nssoc_explicit_preflight absent sink target $expected_place]
explicit_expect_rejection wrong_driver_master [list nssoc_explicit_preflight blocker sink target $expected_place]
explicit_expect_rejection wrong_sink [list nssoc_explicit_preflight driver driver target $expected_place]
explicit_expect_rejection wrong_net [list nssoc_explicit_preflight driver sink d $expected_place]
explicit_expect_rejection missing_net [list nssoc_explicit_preflight driver sink absent $expected_place]
set wrong_place $expected_place;dict set wrong_place driver {0 0 R0 PLACED}
explicit_expect_rejection source_placement [list nssoc_explicit_preflight driver sink target $wrong_place]
set target [$block findNet target]
set term [[$block findInst sink] findITerm D]
$term disconnect
explicit_expect_rejection missing_endpoint $call
$term connect $target
set extra [[$block findInst blocker] findITerm A];set old_net [$extra getNet]
$extra connect $target
explicit_expect_rejection extra_endpoint $call
$extra connect $old_net
$target setSigType CLOCK
explicit_expect_rejection clock_net $call
$target setSigType SIGNAL
set_dont_touch [get_nets target]
explicit_expect_rejection protected_net $call
unset_dont_touch [get_nets target]
foreach name {driver sink} {
    set inst [$block findInst $name]
    set_dont_touch [get_cells $name]
    explicit_expect_rejection protected_$name $call
    unset_dont_touch [get_cells $name]
    $inst setPlacementStatus FIRM
    explicit_expect_rejection fixed_$name $call
    $inst setPlacementStatus UNPLACED
    explicit_expect_rejection unplaced_$name $call
    $inst setPlacementStatus PLACED
    foreach supply {VDD VSS} {
        set term [$inst findITerm $supply];set old_net [$term getNet]
        $term disconnect
        explicit_expect_rejection ${name}_missing_$supply $call
        $term connect $old_net
    }
}
explicit_expect_rejection changed_radius [list nssoc_explicit_vacancy driver 11]
set blocker [$block findInst blocker]
$blocker setPlacementStatus UNPLACED
explicit_expect_rejection unplaced_other_object [list nssoc_explicit_vacancy driver]
$blocker setPlacementStatus PLACED
set blockage [odb::dbBlockage_create $block 0 0 200000 100000]
explicit_expect_rejection no_legal_vacancy [list nssoc_explicit_vacancy driver]
odb::dbBlockage_destroy $blockage
set reserved [odb::dbNet_create $block nssoc_explicit_holdnet]
explicit_expect_rejection preexisting_reserved_net $call
odb::dbNet_destroy $reserved
nssoc_explicit_graph [file join $out negative-restored-graph.tsv]
nssoc_explicit_placement [file join $out negative-restored-objects.tsv]
foreach kind {graph objects} {
    if {[nssoc_hold_sha [file join $out pristine-$kind.tsv]] ne [nssoc_hold_sha [file join $out negative-restored-$kind.tsv]]} {
        error "Preflight negative controls changed original objects"
    }
}
set chosen [nssoc_explicit_vacancy driver]
# The below-row blocker excludes the equally distant lower vacancy. The row
# directly above is the unique distance-3780 candidate at the driver's x.
if {[lrange $chosen 0 2] ne {3780 50400 34020} || [lindex $chosen 4] ne "MX"} {
    error "Unexpected independently predicted nearest vacancy: $chosen"
}
if {[nssoc_explicit_vacancy driver] ne $chosen} {error "Vacancy choice is not deterministic"}
# Direct database fault injection above invalidates cached parasitics even when
# the exact graph is restored. Rebuild before exercising the native resizer API.
estimate_parasitics -placement
sta::delays_invalid
sta::find_timing -full_update
if {[catch {nssoc_explicit_insert $out driver sink target $expected_place} insertion]} {
    set instance_names {};foreach inst [$block getInsts] {lappend instance_names [$inst getName]}
    set net_names {};foreach net [$block getNets] {lappend net_names [$net getName]}
    puts "FAILED_INSERTION_NATIVE_INSTANCES $instance_names"
    puts "FAILED_INSERTION_NATIVE_NETS $net_names"
    help insert_buffer
    error $insertion
}
set inserted_name [dict get $insertion buffer]
set inserted [$block findInst $inserted_name]
set verify_index 0
proc explicit_complete_verify {row} {
    nssoc_explicit_verify $row
    incr ::verify_index
    nssoc_explicit_graph [file join $::out verify-$::verify_index-graph.tsv] $row
    nssoc_explicit_placement [file join $::out verify-$::verify_index-objects.tsv] [dict get $row buffer]
    foreach kind {graph objects} {
        if {[nssoc_hold_sha [file join $::out pristine-$kind.tsv]] ne [nssoc_hold_sha [file join $::out verify-$::verify_index-$kind.tsv]]} {
            error "Complete contraction or original placement changed: $kind"
        }
    }
}
explicit_complete_verify $insertion
set inserted_call [list explicit_complete_verify $insertion]
$blocker setLocation 50880 26460
explicit_expect_rejection moved_original_cell $inserted_call
$blocker setLocation 50400 26460
$blocker setOrient R180
$blocker setLocation 50400 26460
explicit_expect_rejection changed_original_orientation $inserted_call
$blocker setOrient MX
$blocker setLocation 50400 26460
$blocker setPlacementStatus FIRM
explicit_expect_rejection changed_original_status $inserted_call
$blocker setPlacementStatus PLACED
set_dont_touch [get_cells blocker]
explicit_expect_rejection changed_original_protection $inserted_call
unset_dont_touch [get_cells blocker]
set term [$blocker findITerm A];set old_net [$term getNet]
$term connect [$block findNet d]
explicit_expect_rejection changed_original_graph $inserted_call
$term connect $old_net
set extra_net [odb::dbNet_create $block forbidden_extra_net]
explicit_expect_rejection extra_new_net $inserted_call
odb::dbNet_destroy $extra_net
set extra_cell [odb::dbInst_create $block [[ord::get_db] findMaster sg13g2_buf_1] forbidden_extra_cell]
explicit_expect_rejection extra_new_cell $inserted_call
odb::dbInst_destroy $extra_cell
$inserted setLocation 50400 30240
set overlap_row $insertion;dict set overlap_row location_dbu {50400 30240}
# Keep the supplied vacancy row consistent with the actual illegal position so
# this rejection must come from native check_placement, not the equality guard.
explicit_expect_rejection native_overlap [list nssoc_explicit_verify $overlap_row]
$inserted setLocation 50400 34020
$inserted setLocation 50880 34020
explicit_expect_rejection moved_delay_cell $inserted_call
$inserted setLocation 50400 34020
$inserted setOrient R0
explicit_expect_rejection changed_delay_orientation $inserted_call
$inserted setOrient MX
$inserted setLocation 50400 34020
$inserted setPlacementStatus FIRM
explicit_expect_rejection fixed_delay_cell $inserted_call
$inserted setPlacementStatus PLACED
foreach supply {VDD VSS} {
    set term [$inserted findITerm $supply];set old_net [$term getNet]
    $term disconnect
    explicit_expect_rejection delay_missing_$supply $inserted_call
    $term connect $old_net
}
set a [$inserted findITerm A];set x [$inserted findITerm X]
set a_net [$a getNet];set x_net [$x getNet]
$a connect $x_net;$x connect $a_net
explicit_expect_rejection reversed_delay_topology $inserted_call
$a connect $a_net;$x connect $x_net
replace_cell [get_cells $inserted_name] sg13g2_buf_1
explicit_expect_rejection wrong_delay_master $inserted_call
replace_cell [get_cells $inserted_name] sg13g2_dlygate4sd3_1
$inserted setOrient MX;$inserted setLocation 50400 34020;$inserted setPlacementStatus PLACED
explicit_complete_verify $insertion
estimate_parasitics -placement
sta::delays_invalid
sta::find_timing -full_update
set after_metrics [explicit_metrics]
foreach corner {fast typical slow} {
    if {[dict get $explicit_slacks $corner min] <= [dict get $before_slacks $corner min] ||
        [dict get $explicit_slacks $corner max] <= 0} {error "Tiny sd3 timing response was not observed in $corner"}
    report_checks -corner $corner -through [get_pins $inserted_name/X] -path_delay min_max \
        -fields {slew cap input fanout} -digits 9 > [file join $out after-$corner.rpt]
    set text [explicit_read [file join $out after-$corner.rpt]]
    if {[string first "$inserted_name/X (sg13g2_dlygate4sd3_1)" $text] < 0 || [string first "Corner: $corner" $text] < 0} {
        error "Actual sd3 delay is absent from $corner timing path"
    }
}
write_sdc -no_timestamp [file join $out after.sdc]
write_db [file join $out after.odb]
write_def [file join $out after.def]
write_verilog [file join $out after.v]
set before_sha [nssoc_hold_sha [file join $out before.sdc]]
set after_sha [nssoc_hold_sha [file join $out after.sdc]]
if {$before_sha ne $after_sha} {error "Explicit fixture changed source SDC"}
nssoc_hold_write_json [file join $out result.json] [nssoc_hold_jobject [dict create \
    status [nssoc_hold_jstr PASS_NATIVE_EXPLICIT_HOLD_CONTROL] \
    negative_control_messages [nssoc_hold_jobject $failures] \
    insertion [nssoc_explicit_json $insertion] \
    before_metrics [nssoc_hold_jobject $before_metrics] after_metrics [nssoc_hold_jobject $after_metrics] \
    independently_predicted_nearest_vacancy true deterministic_vacancy true \
    full_graph_contraction_preserved true all_original_placements_preserved true \
    no_detailed_placement_called true pg_bindings_preserved true all_three_corners_loaded_and_timed true \
    constraints_preserved true pre_sdc_sha256 [nssoc_hold_jstr $before_sha] post_sdc_sha256 [nssoc_hold_jstr $after_sha] \
    placement_parasitic_tiny_control_only true candidate_adopted false timing_accepted false manufacturing_approval false]]
puts PASS_NATIVE_EXPLICIT_HOLD_CONTROL_NO_CHIP_ACCEPTANCE
