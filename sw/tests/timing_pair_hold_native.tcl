# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Tiny native two-branch control. No full-chip inputs or placement repair.
foreach key {NSSOC_ELECTRICAL_ROOT NSSOC_TARGETED_METHOD_ROOT NSSOC_PAIR_OUT NSSOC_TARGETED_PDK_ROOT} {
    if {![info exists ::env($key)]} {error "$key is required"}
}
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_hold_reproducibility.tcl]
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_pair_hold_helpers.tcl]
set out $::env(NSSOC_PAIR_OUT)
if {[file exists $out]} {error "Pair native output already exists"}
file mkdir $out
set std [file join $::env(NSSOC_TARGETED_PDK_ROOT) ihp-sg13g2 libs.ref sg13g2_stdcell]
read_lef [file join $std lef/sg13g2_tech.lef]
read_lef [file join $std lef/sg13g2_stdcell.lef]
define_corners fast typical slow
foreach {corner liberty} {fast sg13g2_stdcell_fast_1p32V_m40C.lib typical sg13g2_stdcell_typ_1p20V_25C.lib slow sg13g2_stdcell_slow_1p08V_125C.lib} {
    read_liberty -corner $corner [file join $std lib $liberty]
}
set f [open [file join $out before.v] {WRONLY CREAT EXCL}]
puts $f {module tiny(input clk,input rst_n,input d0,input d1,input other,output q0,output q1,output spare);
 wire target0,target1;
 sg13g2_dfrbpq_1 driver0(.CLK(clk),.RESET_B(rst_n),.D(d0),.Q(target0));
 sg13g2_dfrbpq_1 sink0(.CLK(clk),.RESET_B(rst_n),.D(target0),.Q(q0));
 sg13g2_dfrbpq_1 driver1(.CLK(clk),.RESET_B(rst_n),.D(d1),.Q(target1));
 sg13g2_dfrbpq_1 sink1(.CLK(clk),.RESET_B(rst_n),.D(target1),.Q(q1));
 sg13g2_dlygate4sd3_1 nssoc_explicit_sd31(.A(other),.X(spare));
endmodule}
close $f
read_verilog [file join $out before.v]
link_design tiny
initialize_floorplan -die_area {0 0 200 100} -core_area {5.28 7.56 194.88 94.50} -site CoreSite
make_tracks
set block [ord::get_db_block]
foreach name {driver0 sink0 driver1 sink1 nssoc_explicit_sd31} x {50400 80640 50400 80640 50400} y {30240 30240 37800 37800 26460} orient {R0 R0 R0 R0 MX} {
    set inst [$block findInst $name]
    $inst setOrient $orient
    $inst setLocation $x $y
    $inst setPlacementStatus PLACED
}
set index 0
foreach name {clk rst_n d0 d1 other q0 q1 spare} {
    place_pin -pin_name $name -layer Metal2 -location [list 10 [expr {10+10*$index}]]
    incr index
}
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
check_placement -verbose
create_clock -period 20 [get_ports clk]
set_input_delay -max 0.5 -clock clk [get_ports {d0 d1 other}]
set_input_delay -min 0.1 -clock clk [get_ports {d0 d1 other}]
set_output_delay -max 0.5 -clock clk [get_ports {q0 q1 spare}]
set_output_delay -min 0 -clock clk [get_ports {q0 q1 spare}]
set_wire_rc -signal -layer Metal2
set_wire_rc -clock -layer Metal2
set_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2
set_global_routing_layer_adjustment Metal2-TopMetal2 0.3
proc pair_route {} {
    global_route -verbose
    estimate_parasitics -global_routing
    global_route -start_incremental
    global_route -end_incremental
    estimate_parasitics -global_routing
    sta::delays_invalid
    sta::find_timing -full_update
    check_placement -verbose
}
proc pair_read {path} {
    set f [open $path r];set text [read $f];close $f;return $text
}
proc pair_metrics {label {rows {}}} {
    set result {}
    foreach i {0 1} {
        set corners {}
        foreach corner {fast typical slow} {
            set values {}
            foreach delay {min max} {
                set paths [find_timing_paths -from [get_pins driver$i/CLK] -to [get_pins sink$i/D] \
                    -corner $corner -path_delay $delay -group_path_count 1 -endpoint_path_count 1]
                if {[llength $paths] != 1} {error "Missing tiny branch$i $corner/$delay register path"}
                set slack [get_property [lindex $paths 0] slack]
                dict set ::pair_slacks $i $corner $delay $slack
                dict set values ${delay}_slack_ns [nssoc_hold_number $slack]
            }
            report_checks -from [get_pins driver$i/CLK] -to [get_pins sink$i/D] -corner $corner \
                -path_delay min_max -fields {slew cap input fanout} -digits 9 \
                > [file join $::out $label-branch$i-$corner.rpt]
            set text [pair_read [file join $::out $label-branch$i-$corner.rpt]]
            if {[string first "Corner: $corner" $text] < 0} {error "Missing native corner report"}
            if {$rows ne {}} {
                set buffer [dict get [lindex $rows $i] buffer]
                if {[string first "$buffer/X (sg13g2_dlygate4sd3_1)" $text] < 0} {error "Native sd3 is absent from branch$i/$corner"}
            }
            dict set corners $corner [nssoc_hold_jobject $values]
        }
        dict set result target$i [nssoc_hold_jobject $corners]
    }
    return $result
}
set failures {}
proc pair_expect_rejection {name command} {
    if {![catch {uplevel 1 $command} message]} {error "Negative control unexpectedly accepted: $name"}
    dict set ::failures $name [nssoc_hold_jstr $message]
}
pair_route
set before_metrics [pair_metrics before]
set before_slacks $pair_slacks
write_sdc -no_timestamp [file join $out before.sdc]
write_db [file join $out before.odb]
write_def [file join $out before.def]
set expected_place {}
foreach name {driver0 sink0 driver1 sink1} {
    set inst [$block findInst $name]
    dict set expected_place $name [concat [$inst getLocation] [list [$inst getOrient] [$inst getPlacementStatus]]]
}

nssoc_pair_graph [file join $out pristine-graph.tsv]
nssoc_pair_placement [file join $out pristine-objects.tsv]
file copy [file join $out pristine-graph.tsv] [file join $out graph-before.tsv]
file copy [file join $out pristine-objects.tsv] [file join $out objects-before.tsv]
set original_instances [llength [$block getInsts]]
set original_nets [llength [$block getNets]]
if {$original_instances != 5} {error "The tiny original must contain four DFFs and exactly one old sd3"}
set old_sd3 [$block findInst nssoc_explicit_sd31]
set old_sd3_place [concat [$old_sd3 getLocation] [list [$old_sd3 getOrient] [$old_sd3 getPlacementStatus]]]
set old_sd3_pg {};foreach supply {VDD VSS} {dict set old_sd3_pg $supply [[$old_sd3 findITerm $supply] getNet]}
foreach i {0 1} {
    set call [list nssoc_pair_call $i preflight driver$i sink$i target$i $expected_place]
    {*}$call
    pair_expect_rejection missing_driver_$i [list nssoc_pair_call $i preflight absent sink$i target$i $expected_place]
    pair_expect_rejection wrong_target_$i [list nssoc_pair_call $i preflight driver$i sink$i other $expected_place]
    pair_expect_rejection changed_radius_$i [list nssoc_pair_call $i vacancy driver$i 11]
    set target [$block findNet target$i]
    set_dont_touch [get_nets target$i]
    pair_expect_rejection protected_branch_$i $call
    unset_dont_touch [get_nets target$i]
    set target_sink [[$block findInst sink$i] findITerm D]
    $target_sink disconnect
    pair_expect_rejection missing_endpoint_$i $call
    $target_sink connect $target
    foreach name [list driver$i sink$i] {
        set inst [$block findInst $name]
        set_dont_touch [get_cells $name]
        pair_expect_rejection protected_${name} $call
        unset_dont_touch [get_cells $name]
        $inst setPlacementStatus FIRM
        pair_expect_rejection fixed_${name} $call
        $inst setPlacementStatus PLACED
        foreach supply {VDD VSS} {
            set term [$inst findITerm $supply];set net [$term getNet]
            $term disconnect
            pair_expect_rejection ${name}_missing_${supply} $call
            $term connect $net
        }
    }
}
pair_expect_rejection wrong_namespace [list nssoc_pair_call 2 preflight driver0 sink0 target0 $expected_place]
pair_expect_rejection unapproved_operation [list nssoc_pair_call 0 arbitrary_operation]
pair_expect_rejection cross_branch_endpoint [list nssoc_pair_call 0 preflight driver0 sink1 target0 $expected_place]
$old_sd3 setPlacementStatus UNPLACED
pair_expect_rejection unplaced_old_sd3 [list nssoc_pair_call 0 vacancy driver0]
$old_sd3 setPlacementStatus PLACED
set shared [[$block findInst sink1] findITerm D]
set shared_original [$shared getNet]
$shared connect [$block findNet target0]
pair_expect_rejection physically_shared_branch [list nssoc_pair_call 0 preflight driver0 sink0 target0 $expected_place]
$shared connect $shared_original
nssoc_pair_graph [file join $out negatives-restored-graph.tsv]
nssoc_pair_placement [file join $out negatives-restored-objects.tsv]
foreach kind {graph objects} {
    if {[nssoc_hold_sha [file join $out pristine-$kind.tsv]] ne [nssoc_hold_sha [file join $out negatives-restored-$kind.tsv]]} {
        error "Preflight negatives changed original $kind"
    }
}
set vacancy0 [nssoc_pair_call 0 vacancy driver0]
set vacancy1_before [nssoc_pair_call 1 vacancy driver1]
foreach v [list $vacancy0 $vacancy1_before] {
    if {[lrange $v 0 2] ne {3780 50400 34020} || [lindex $v 4] ne "MX"} {error "Unexpected original nearest vacancy: $v"}
}
if {[nssoc_pair_call 0 vacancy driver0] ne $vacancy0 || [nssoc_pair_call 1 vacancy driver1] ne $vacancy1_before} {
    error "Original vacancy choice is not deterministic"
}
# Direct native fault controls invalidate cached topology even after restoration.
# Clear only those stale fixture caches, then rebuild the actual routed parasitics.
estimate_parasitics -placement
pair_route
set first [nssoc_pair_insert $out 0 driver0 sink0 target0 $expected_place]
if {![regexp {^nssoc_pair0_sd3[0-9]+$} [dict get $first buffer]] || ![regexp {^nssoc_pair0_net[0-9]+$} [dict get $first new_net]]} {error "Native first prefix suffix is absent"}
set vacancy1_after [nssoc_pair_call 1 vacancy driver1]
if {[lrange $vacancy1_after 0 2] ne {3780 50400 41580} || [lindex $vacancy1_after 4] ne "MX"} {
    error "First insertion did not force the predicted second vacancy: $vacancy1_after"
}
# The first cell occupies the former exact lower-left choice for driver1.
if {[dict get $first location_dbu] ne [lrange $vacancy1_before 1 2] || $vacancy1_before eq $vacancy1_after} {
    error "First insertion is not an independently observed second-branch obstacle"
}
if {[nssoc_pair_call 1 vacancy driver1] ne $vacancy1_after} {error "Second vacancy is not deterministic"}
set second [nssoc_pair_insert $out 1 driver1 sink1 target1 $expected_place]
if {![regexp {^nssoc_pair1_sd3[0-9]+$} [dict get $second buffer]] || ![regexp {^nssoc_pair1_net[0-9]+$} [dict get $second new_net]]} {error "Native second prefix suffix is absent"}
set rows [list $first $second]
set verify_index 0
proc pair_complete_verify {rows} {
    nssoc_pair_verify $rows
    incr ::verify_index
    nssoc_pair_graph [file join $::out verify-$::verify_index-graph.tsv] $rows
    nssoc_pair_placement [file join $::out verify-$::verify_index-objects.tsv] $rows
    foreach kind {graph objects} {
        if {[nssoc_hold_sha [file join $::out pristine-$kind.tsv]] ne [nssoc_hold_sha [file join $::out verify-$::verify_index-$kind.tsv]]} {
            error "Full pair contraction changed original $kind"
        }
    }
}
pair_complete_verify $rows
set verify_call [list pair_complete_verify $rows]
pair_expect_rejection omitted_branch [list nssoc_pair_verify [list $first]]
pair_expect_rejection omitted_both [list nssoc_pair_verify {}]
pair_expect_rejection duplicate_branch [list nssoc_pair_verify [list $first $first]]
pair_expect_rejection reversed_branch_order [list nssoc_pair_verify [list $second $first]]
foreach key {driver sink original_net new_net buffer} {
    set wrong_second [dict replace $second $key [dict get $first $key]]
    pair_expect_rejection duplicate_$key [list nssoc_pair_verify [list $first $wrong_second]]
}
foreach key {initial_instances initial_nets} {
    set wrong [dict replace $second $key [dict get $first $key]]
    pair_expect_rejection wrong_second_$key [list nssoc_pair_verify [list $first $wrong]]
}
set wrong [dict replace $first master sg13g2_buf_1]
pair_expect_rejection wrong_recorded_master [list nssoc_pair_verify [list $wrong $second]]
# Original cell identity, old sd3 and connections must survive pair contraction.
foreach name {driver0 sink0 driver1 sink1 nssoc_explicit_sd31} {
    set inst [$block findInst $name];set loc [$inst getLocation]
    $inst setLocation [expr {[lindex $loc 0]+480}] [lindex $loc 1]
    pair_expect_rejection moved_original_$name $verify_call
    $inst setLocation {*}$loc
    set_dont_touch [get_cells $name]
    pair_expect_rejection protected_original_$name $verify_call
    unset_dont_touch [get_cells $name]
}
$old_sd3 setOrient R180;$old_sd3 setLocation 50400 26460
pair_expect_rejection old_sd3_orientation $verify_call
$old_sd3 setOrient MX;$old_sd3 setLocation 50400 26460
$old_sd3 setPlacementStatus FIRM
pair_expect_rejection old_sd3_status $verify_call
$old_sd3 setPlacementStatus PLACED
set a [$old_sd3 findITerm A];set old [$a getNet]
$a connect [$block findNet d0]
pair_expect_rejection old_sd3_graph $verify_call
$a connect $old
foreach supply {VDD VSS} {
    set t [$old_sd3 findITerm $supply];set old [$t getNet]
    $t disconnect
    pair_expect_rejection old_sd3_missing_$supply $verify_call
    $t connect $old
}
set extra [odb::dbNet_create $block forbidden_extra_net]
pair_expect_rejection extra_net $verify_call
odb::dbNet_destroy $extra
set extra [odb::dbInst_create $block [[ord::get_db] findMaster sg13g2_buf_1] forbidden_extra_cell]
pair_expect_rejection extra_cell $verify_call
odb::dbInst_destroy $extra
foreach row $rows index {0 1} {
    set inst [$block findInst [dict get $row buffer]]
    foreach supply {VDD VSS} {
        set t [$inst findITerm $supply];set old [$t getNet]
        $t disconnect
        pair_expect_rejection new${index}_missing_$supply $verify_call
        $t connect $old
        set opposite [expr {$supply eq "VDD" ? "VSS" : "VDD"}]
        $t connect [$block findNet $opposite]
        pair_expect_rejection new${index}_wrong_$supply $verify_call
        $t connect $old
    }
    set a [$inst findITerm A];set x [$inst findITerm X];set an [$a getNet];set xn [$x getNet]
    $a connect $xn;$x connect $an
    pair_expect_rejection new${index}_reversed_branch $verify_call
    $a connect $an;$x connect $xn
    $inst setLocation 50400 26460
    set wrong_row [dict replace $row location_dbu {50400 26460}]
    set wrong_rows [lreplace $rows $index $index $wrong_row]
    # Consistent claimed location makes the real native placement checker reject overlap.
    pair_expect_rejection native_overlap_$index [list nssoc_pair_verify $wrong_rows]
    $inst setLocation {*}[dict get $row location_dbu]
    $inst setPlacementStatus FIRM
    pair_expect_rejection fixed_new_$index $verify_call
    $inst setPlacementStatus PLACED
}
pair_complete_verify $rows
if {[llength [$block getInsts]] != $original_instances+2 || [llength [$block getNets]] != $original_nets+2} {error "Actual pair delta differs from exactly two cells/nets"}
if {[concat [$old_sd3 getLocation] [list [$old_sd3 getOrient] [$old_sd3 getPlacementStatus]]] ne $old_sd3_place} {error "Old sd3 placement changed"}
foreach supply {VDD VSS} {if {[[$old_sd3 findITerm $supply] getNet] ne [dict get $old_sd3_pg $supply]} {error "Old sd3 PG changed"}}
estimate_parasitics -placement
pair_route
pair_complete_verify $rows
set after_metrics [pair_metrics after $rows]
foreach i {0 1} {
    foreach corner {fast typical slow} {
        if {[dict get $pair_slacks $i $corner min] <= [dict get $before_slacks $i $corner min] ||
            [dict get $pair_slacks $i $corner max] <= 0} {error "Pair sd3 native timing response missing for branch$i/$corner"}
    }
}
nssoc_pair_graph [file join $out graph-after-contracted.tsv] $rows
nssoc_pair_placement [file join $out objects-after-contracted.tsv] $rows
write_sdc -no_timestamp [file join $out after.sdc]
write_db [file join $out after.odb]
write_def [file join $out after.def]
write_verilog [file join $out after.v]
set pre_sdc [nssoc_hold_sha [file join $out before.sdc]]
set post_sdc [nssoc_hold_sha [file join $out after.sdc]]
if {$pre_sdc ne $post_sdc} {error "Pair fixture changed source constraints"}
set insertion_json "\[[nssoc_explicit_json $first],[nssoc_explicit_json $second]\]"
nssoc_hold_write_json [file join $out result.json] [nssoc_hold_jobject [dict create \
    status [nssoc_hold_jstr PASS_NATIVE_PAIR_HOLD_CONTROL] \
    negative_control_messages [nssoc_hold_jobject $failures] insertions $insertion_json \
    initial_instances $original_instances final_instances [llength [$block getInsts]] \
    initial_nets $original_nets final_nets [llength [$block getNets]] \
    first_vacancy [nssoc_hold_jstr $vacancy0] second_original_vacancy [nssoc_hold_jstr $vacancy1_before] second_actual_vacancy [nssoc_hold_jstr $vacancy1_after] \
    before_metrics [nssoc_hold_jobject $before_metrics] after_metrics [nssoc_hold_jobject $after_metrics] \
    independently_predicted_nearest_vacancies true first_new_cell_blocks_second_original_vacancy true \
    all_original_objects_preserved true all_original_placements_preserved true original_sd3_preserved true preserved_original_delay true full_graph_contraction_preserved true \
    exactly_two_new_cells_and_nets true all_pg_bindings_preserved true pg_bindings_preserved true first_insertion_is_second_obstacle true \
    actual_global_route_before_and_after true all_three_corners_loaded_and_timed true \
    no_detailed_placement_called true constraints_preserved true \
    pre_sdc_sha256 [nssoc_hold_jstr $pre_sdc] post_sdc_sha256 [nssoc_hold_jstr $post_sdc] \
    estimated_global_route_tiny_control_only true tiny_native_control_only true candidate_adopted false timing_accepted false manufacturing_approval false]]
puts PASS_NATIVE_PAIR_HOLD_CONTROL_NO_CHIP_ACCEPTANCE
