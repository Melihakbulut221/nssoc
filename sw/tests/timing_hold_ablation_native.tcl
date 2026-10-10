# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Tiny native single-branch ablation control. No full-chip inputs or placement repair.
foreach key {NSSOC_ELECTRICAL_ROOT NSSOC_TARGETED_METHOD_ROOT NSSOC_ABLATION_OUT NSSOC_TARGETED_PDK_ROOT} {
    if {![info exists ::env($key)]} {error "$key is required"}
}
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_hold_reproducibility.tcl]
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_hold_ablation_helpers.tcl]
set variant $::env(NSSOC_HOLD_ABLATION_VARIANT)
set selected [expr {$variant eq "eth" ? 0 : 1}]
set untouched [expr {1-$selected}]
set out $::env(NSSOC_ABLATION_OUT)
if {[file exists $out]} {error "Ablation native output already exists"}
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
proc abl_route {} {
    global_route -verbose
    estimate_parasitics -global_routing
    global_route -start_incremental
    global_route -end_incremental
    estimate_parasitics -global_routing
    sta::delays_invalid
    sta::find_timing -full_update
    check_placement -verbose
}
proc abl_read {path} {
    set f [open $path r];set text [read $f];close $f;return $text
}
proc abl_metrics {label {row {}}} {
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
                dict set ::abl_slacks $i $corner $delay $slack
                dict set values ${delay}_slack_ns [nssoc_hold_number $slack]
            }
            report_checks -from [get_pins driver$i/CLK] -to [get_pins sink$i/D] -corner $corner \
                -path_delay min_max -fields {slew cap input fanout} -digits 9 \
                > [file join $::out $label-branch$i-$corner.rpt]
            set text [abl_read [file join $::out $label-branch$i-$corner.rpt]]
            if {[string first "Corner: $corner" $text] < 0} {error "Missing native corner report"}
            if {$row ne {}} {
                set present [expr {[string first "[dict get $row buffer]/X (sg13g2_dlygate4sd3_1)" $text] >= 0}]
                if {$present != ($i == $::selected)} {error "Native sd3 belongs to wrong observed branch"}
            }
            dict set corners $corner [nssoc_hold_jobject $values]
        }
        dict set result target$i [nssoc_hold_jobject $corners]
    }
    return $result
}
set failures {}
proc abl_expect_rejection {name command} {
    if {![catch {uplevel 1 $command} message]} {error "Negative control unexpectedly accepted: $name"}
    dict set ::failures $name [nssoc_hold_jstr $message]
}
abl_route
set before_metrics [abl_metrics before]
set before_slacks $abl_slacks
write_sdc -no_timestamp [file join $out before.sdc]
write_db [file join $out before.odb]
write_def [file join $out before.def]
set expected_place {}
foreach name {driver0 sink0 driver1 sink1} {
    set inst [$block findInst $name]
    dict set expected_place $name [concat [$inst getLocation] [list [$inst getOrient] [$inst getPlacementStatus]]]
}
nssoc_ablation_call graph [file join $out pristine-graph.tsv]
nssoc_ablation_call placement [file join $out pristine-objects.tsv]
nssoc_ablation_graph [file join $out adapter-before-graph.tsv]
nssoc_ablation_placement [file join $out adapter-before-objects.tsv]
foreach kind {graph objects} {
    if {[nssoc_hold_sha [file join $out pristine-$kind.tsv]] ne [nssoc_hold_sha [file join $out adapter-before-$kind.tsv]]} {error "Empty adapter changed original $kind"}
}
file copy [file join $out pristine-graph.tsv] [file join $out graph-before.tsv]
file copy [file join $out pristine-objects.tsv] [file join $out objects-before.tsv]
set original_instances [llength [$block getInsts]]
set original_nets [llength [$block getNets]]
if {$original_instances != 5 || $original_nets != 12} {error "Original tiny five-cell/twelve-net census differs"}
set old_sd3 [$block findInst nssoc_explicit_sd31]
set old_sd3_place [concat [$old_sd3 getLocation] [list [$old_sd3 getOrient] [$old_sd3 getPlacementStatus]]]
set old_sd3_pg {};foreach supply {VDD VSS} {dict set old_sd3_pg $supply [[$old_sd3 findITerm $supply] getNet]}
set driver driver$selected;set sink sink$selected;set target target$selected
set call [list nssoc_ablation_call preflight $driver $sink $target $expected_place]
{*}$call
abl_expect_rejection missing_driver [list nssoc_ablation_call preflight absent $sink $target $expected_place]
abl_expect_rejection wrong_target [list nssoc_ablation_call preflight $driver $sink other $expected_place]
abl_expect_rejection changed_radius [list nssoc_ablation_call vacancy $driver 11]
set expected_bad [dict replace $expected_place $driver {0 0 R0 PLACED}]
abl_expect_rejection wrong_source_placement [list nssoc_ablation_call preflight $driver $sink $target $expected_bad]
set target_net [$block findNet $target]
set_dont_touch [get_nets $target]
abl_expect_rejection protected_branch $call
unset_dont_touch [get_nets $target]
$target_net setSigType CLOCK
abl_expect_rejection clock_branch $call
$target_net setSigType SIGNAL
set target_sink [[$block findInst $sink] findITerm D]
$target_sink disconnect
abl_expect_rejection missing_endpoint $call
$target_sink connect $target_net
foreach name [list $driver $sink] role {driver sink} {
    set inst [$block findInst $name]
    set_dont_touch [get_cells $name]
    abl_expect_rejection protected_$role $call
    unset_dont_touch [get_cells $name]
    $inst setPlacementStatus FIRM
    abl_expect_rejection fixed_$role $call
    $inst setPlacementStatus PLACED
    foreach supply {VDD VSS} {
        set term [$inst findITerm $supply];set net [$term getNet]
        $term disconnect
        abl_expect_rejection ${role}_missing_$supply $call
        $term connect $net
    }
}
set ::env(NSSOC_HOLD_ABLATION_VARIANT) other
abl_expect_rejection wrong_variant $call
set ::env(NSSOC_HOLD_ABLATION_VARIANT) $variant
abl_expect_rejection unapproved_operation [list nssoc_ablation_call arbitrary_operation]
abl_expect_rejection cross_branch_endpoint [list nssoc_ablation_call preflight $driver sink$untouched $target $expected_place]
$old_sd3 setPlacementStatus UNPLACED
abl_expect_rejection unplaced_old_sd3 [list nssoc_ablation_call vacancy $driver]
$old_sd3 setPlacementStatus PLACED
set shared [[$block findInst sink$untouched] findITerm D]
set shared_original [$shared getNet]
$shared connect $target_net
abl_expect_rejection physically_shared_branch $call
$shared connect $shared_original
set reserved [odb::dbInst_create $block [[ord::get_db] findMaster sg13g2_buf_1] nssoc_ablation_${variant}_sd3999]
abl_expect_rejection reserved_cell_prefix $call
odb::dbInst_destroy $reserved
set reserved [odb::dbNet_create $block nssoc_ablation_${variant}_net999]
abl_expect_rejection reserved_net_prefix $call
odb::dbNet_destroy $reserved
nssoc_ablation_call graph [file join $out negatives-restored-graph.tsv]
nssoc_ablation_call placement [file join $out negatives-restored-objects.tsv]
foreach kind {graph objects} {
    if {[nssoc_hold_sha [file join $out pristine-$kind.tsv]] ne [nssoc_hold_sha [file join $out negatives-restored-$kind.tsv]]} {error "Preflight negatives changed original $kind"}
}
set vacancy [nssoc_ablation_call vacancy $driver]
if {[lrange $vacancy 0 2] ne {3780 50400 34020} || [lindex $vacancy 4] ne "MX"} {error "Unexpected original nearest vacancy: $vacancy"}
if {[nssoc_ablation_call vacancy $driver] ne $vacancy} {error "Nearest vacancy choice is not deterministic"}
# Fixture-only direct topology faults invalidate cached parasitics after restoration.
# Clear those stale caches, then rebuild actual GRT/RC before the native insertion.
estimate_parasitics -placement
abl_route
set insertion [nssoc_ablation_insert $out $driver $sink $target $expected_place]
nssoc_ablation_verify [list $insertion]
abl_expect_rejection adapter_omitted_row [list nssoc_ablation_verify {}]
abl_expect_rejection adapter_duplicate_row [list nssoc_ablation_verify [list $insertion $insertion]]
foreach key {buffer new_net master} value {wrong_sd31 wrong_net1 sg13g2_buf_1} {
    abl_expect_rejection adapter_wrong_$key [list nssoc_ablation_verify [list [dict replace $insertion $key $value]]]
}
nssoc_ablation_graph [file join $out adapter-after-graph.tsv] [list $insertion]
nssoc_ablation_placement [file join $out adapter-after-objects.tsv] [list $insertion]
foreach kind {graph objects} {
    if {[nssoc_hold_sha [file join $out pristine-$kind.tsv]] ne [nssoc_hold_sha [file join $out adapter-after-$kind.tsv]]} {error "Single-row adapter changed original $kind"}
}
set verify_index 0
proc abl_complete_verify {row} {
    # These receipt-field checks mirror the trial's source-bound contract;
    # electrical topology and physical legality are checked by the real API.
    if {![regexp "^nssoc_ablation_${::variant}_sd3\[0-9\]+$" [dict get $row buffer]] ||
        ![regexp "^nssoc_ablation_${::variant}_net\[0-9\]+$" [dict get $row new_net]] ||
        [dict get $row master] ne "sg13g2_dlygate4sd3_1" || [dict get $row driver] ne $::driver ||
        [dict get $row sink] ne $::sink || [dict get $row original_net] ne $::target ||
        [dict get $row initial_instances] != 5 || [dict get $row initial_nets] != 12 ||
        [dict get $row radius_um] != 10} {error "Source-bound one-branch insertion record differs"}
    nssoc_ablation_call verify $row
    incr ::verify_index
    nssoc_ablation_call graph [file join $::out verify-$::verify_index-graph.tsv] $row
    nssoc_ablation_call placement [file join $::out verify-$::verify_index-objects.tsv] [dict get $row buffer]
    foreach kind {graph objects} {
        if {[nssoc_hold_sha [file join $::out pristine-$kind.tsv]] ne [nssoc_hold_sha [file join $::out verify-$::verify_index-$kind.tsv]]} {error "Single ablation contraction changed original $kind"}
    }
}
abl_complete_verify $insertion
set verify_call [list abl_complete_verify $insertion]
foreach key {buffer new_net master driver sink original_net initial_instances initial_nets radius_um} value {wrong_sd31 wrong_net1 sg13g2_buf_1 absent absent other 4 11 11} {
    abl_expect_rejection record_$key [list abl_complete_verify [dict replace $insertion $key $value]]
}
foreach name {driver0 sink0 driver1 sink1 nssoc_explicit_sd31} {
    set inst [$block findInst $name];set loc [$inst getLocation]
    $inst setLocation [expr {[lindex $loc 0]+480}] [lindex $loc 1]
    abl_expect_rejection moved_original_$name $verify_call
    $inst setLocation {*}$loc
    set_dont_touch [get_cells $name]
    abl_expect_rejection protected_original_$name $verify_call
    unset_dont_touch [get_cells $name]
}
$old_sd3 setOrient R180;$old_sd3 setLocation 50400 26460
abl_expect_rejection old_sd3_orientation $verify_call
$old_sd3 setOrient MX;$old_sd3 setLocation 50400 26460
$old_sd3 setPlacementStatus FIRM
abl_expect_rejection old_sd3_status $verify_call
$old_sd3 setPlacementStatus PLACED
set a [$old_sd3 findITerm A];set old [$a getNet]
$a connect [$block findNet d0]
abl_expect_rejection old_sd3_graph $verify_call
$a connect $old
foreach supply {VDD VSS} {
    set t [$old_sd3 findITerm $supply];set old [$t getNet]
    $t disconnect
    abl_expect_rejection old_sd3_missing_$supply $verify_call
    $t connect $old
}
# The unselected branch is a preserved original object, not a second experiment.
set other_sink [[$block findInst sink$untouched] findITerm D];set saved_other [$other_sink getNet]
$other_sink connect [$block findNet d0]
abl_expect_rejection untouched_branch_graph $verify_call
$other_sink connect $saved_other
set extra [odb::dbNet_create $block forbidden_extra_net]
abl_expect_rejection extra_net $verify_call
odb::dbNet_destroy $extra
set extra [odb::dbInst_create $block [[ord::get_db] findMaster sg13g2_buf_1] forbidden_extra_cell]
abl_expect_rejection extra_cell $verify_call
odb::dbInst_destroy $extra
set buffer_name [dict get $insertion buffer]
set inst [$block findInst $buffer_name]
foreach supply {VDD VSS} {
    set t [$inst findITerm $supply];set old [$t getNet]
    $t disconnect
    abl_expect_rejection new_missing_$supply $verify_call
    $t connect $old
    set opposite [expr {$supply eq "VDD" ? "VSS" : "VDD"}]
    $t connect [$block findNet $opposite]
    abl_expect_rejection new_wrong_$supply $verify_call
    $t connect $old
}
set a [$inst findITerm A];set x [$inst findITerm X];set an [$a getNet];set xn [$x getNet]
$a connect $xn;$x connect $an
abl_expect_rejection reversed_new_branch $verify_call
$a connect $an;$x connect $xn
$inst setLocation 50400 26460
# Match the claimed wrong location so the actual native checker diagnoses overlap.
abl_expect_rejection native_overlap [list nssoc_ablation_call verify [dict replace $insertion location_dbu {50400 26460}]]
$inst setLocation {*}[dict get $insertion location_dbu]
$inst setPlacementStatus FIRM
abl_expect_rejection fixed_new $verify_call
$inst setPlacementStatus PLACED
# Remove and faithfully restore only the tiny newly added objects; counts must fail.
set saved_terms {};foreach term [$inst getITerms] {dict set saved_terms [[$term getMTerm] getName] [[$term getNet] getName]}
odb::dbInst_destroy $inst
abl_expect_rejection missing_actual_cell [list nssoc_ablation_call verify $insertion]
set inst [odb::dbInst_create $block [[ord::get_db] findMaster sg13g2_dlygate4sd3_1] $buffer_name]
$inst setOrient [dict get $insertion orientation];$inst setLocation {*}[dict get $insertion location_dbu];$inst setPlacementStatus PLACED
dict for {pin net} $saved_terms {[$inst findITerm $pin] connect [$block findNet $net]}
set newnet [$block findNet [dict get $insertion new_net]];set saved_terms {}
foreach term [$newnet getITerms] {lappend saved_terms [list [[$term getInst] getName] [[$term getMTerm] getName]]}
odb::dbNet_destroy $newnet
abl_expect_rejection missing_actual_net [list nssoc_ablation_call verify $insertion]
set newnet [odb::dbNet_create $block [dict get $insertion new_net]];$newnet setSigType SIGNAL
foreach pair $saved_terms {lassign $pair name pin;[[$block findInst $name] findITerm $pin] connect $newnet}
abl_complete_verify $insertion
if {[llength [$block getInsts]] != 6 || [llength [$block getNets]] != 13} {error "Ablation did not add exactly one cell/net"}
if {[concat [$old_sd3 getLocation] [list [$old_sd3 getOrient] [$old_sd3 getPlacementStatus]]] ne $old_sd3_place} {error "Original sd3 placement changed"}
foreach supply {VDD VSS} {if {[[$old_sd3 findITerm $supply] getNet] ne [dict get $old_sd3_pg $supply]} {error "Original sd3 PG changed"}}
estimate_parasitics -placement
abl_route
abl_complete_verify $insertion
set after_metrics [abl_metrics after $insertion]
foreach corner {fast typical slow} {
    if {[dict get $abl_slacks $selected $corner min] <= [dict get $before_slacks $selected $corner min] ||
        [dict get $abl_slacks $selected $corner max] <= 0} {error "Selected branch lacks real native timing response"}
}
nssoc_ablation_call graph [file join $out graph-after-contracted.tsv] $insertion
nssoc_ablation_call placement [file join $out objects-after-contracted.tsv] [dict get $insertion buffer]
write_sdc -no_timestamp [file join $out after.sdc]
write_db [file join $out after.odb]
write_def [file join $out after.def]
write_verilog [file join $out after.v]
set pre_sdc [nssoc_hold_sha [file join $out before.sdc]];set post_sdc [nssoc_hold_sha [file join $out after.sdc]]
if {$pre_sdc ne $post_sdc} {error "Ablation fixture changed source constraints"}
nssoc_hold_write_json [file join $out result.json] [nssoc_hold_jobject [dict create \
    status [nssoc_hold_jstr PASS_NATIVE_HOLD_ABLATION_CONTROL] variant [nssoc_hold_jstr $variant] \
    selected_branch $selected untouched_branch $untouched insertion [nssoc_explicit_json $insertion] \
    negative_control_messages [nssoc_hold_jobject $failures] \
    initial_instances $original_instances final_instances [llength [$block getInsts]] \
    initial_nets $original_nets final_nets [llength [$block getNets]] \
    selected_vacancy [nssoc_hold_jstr $vacancy] before_metrics [nssoc_hold_jobject $before_metrics] after_metrics [nssoc_hold_jobject $after_metrics] \
    independently_predicted_nearest_vacancy true untouched_branch_preserved true single_row_adapters_verified true \
    all_original_objects_preserved true all_original_placements_preserved true preserved_original_delay true full_graph_contraction_preserved true \
    exactly_one_new_cell_and_net true pg_bindings_preserved true actual_global_route_before_and_after true all_three_corners_loaded_and_timed true \
    no_detailed_placement_called true constraints_preserved true \
    pre_sdc_sha256 [nssoc_hold_jstr $pre_sdc] post_sdc_sha256 [nssoc_hold_jstr $post_sdc] \
    estimated_global_route_tiny_control_only true tiny_native_control_only true candidate_adopted false timing_accepted false manufacturing_approval false]]
puts PASS_NATIVE_HOLD_ABLATION_CONTROL_NO_CHIP_ACCEPTANCE
