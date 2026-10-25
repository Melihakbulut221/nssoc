# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Independent sizing and hold-observation helpers; sourcing does not mutate a design.
source [file join $::env(NSSOC_ELECTRICAL_ROOT) hw/soc/pnr/timing_residual_repair_helpers.tcl]
proc nssoc_critical_pinmap {master} {
    set rows {}
    foreach term [$master getMTerms] {lappend rows [list [$term getName] [$term getIoType] [$term getSigType]]}
    return [lsort $rows]
}
proc nssoc_critical_shape {master} {
    set site [$master getSite]
    if {$site eq "NULL"} {error "Replacement has no placement site"}
    return [dict create width [$master getWidth] height [$master getHeight] \
        site [$site getName] site_width [$site getWidth] site_height [$site getHeight] \
        pinmap [nssoc_critical_pinmap $master]]
}
proc nssoc_critical_shapes_compatible {before after} {
    foreach key {height site site_width site_height pinmap} {
        if {[dict get $before $key] ne [dict get $after $key]} {error "Incompatible replacement $key"}
    }
    set pitch [dict get $before site_width]
    if {$pitch <= 0 || [dict get $before width] != 8*$pitch || [dict get $after width] != 13*$pitch ||
        [dict get $before height] != [dict get $before site_height]} {error "Buffer width/height differs from pinned eight/thirteen-site shapes"}
}
proc nssoc_critical_connections {inst} {
    set result {}
    foreach term [$inst getITerms] {
        set net [$term getNet]; set name NULL
        if {$net ne "NULL"} {set name [$net getName]}
        lappend result [list [[$term getMTerm] getName] $name]
    }
    return [lsort $result]
}
proc nssoc_critical_size_preflight {driver inputnet outputnet expected_terms expected_place {require_power true}} {
    set block [ord::get_db_block];set inst [$block findInst $driver]
    set net [nssoc_electrical_preflight $driver $outputnet]
    if {[[$inst getMaster] getName] ne "sg13g2_buf_4" || [$net isSpecial] || [$net isConnectedByAbutment]} {
        error "Sizing source master or output-net eligibility differs"
    }
    set actual_terms {}
    foreach term [$net getITerms] {
        set load [$term getInst]
        if {[$load isDoNotTouch]} {error "Sizing output touches a protected instance"}
        lappend actual_terms [list [$load getName] [[$load getMaster] getName] [[$term getMTerm] getName]]
    }
    if {[lsort $actual_terms] ne [lsort $expected_terms]} {error "Sizing output graph differs"}
    set input [$inst findITerm A]
    if {$input eq "NULL" || [[$input getMTerm] getIoType] ne "INPUT" || [$input getNet] eq "NULL"} {error "Sizing input missing"}
    set input_net [$input getNet]
    if {[$input_net getName] ne $inputnet || [$input_net getSigType] ne "SIGNAL" ||
        [$input_net isDoNotTouch] || [$input_net isSpecial] || [$input_net isConnectedByAbutment]} {error "Sizing input net differs or is protected"}
    set place [concat [$inst getLocation] [list [$inst getOrient] [$inst getPlacementStatus]]]
    if {$place ne $expected_place} {error "Sizing source placement differs"}
    set replacement [[ord::get_db] findMaster sg13g2_buf_8]
    if {$replacement eq "NULL"} {error "Replacement master missing"}
    nssoc_critical_shapes_compatible [nssoc_critical_shape [$inst getMaster]] [nssoc_critical_shape $replacement]
    foreach term [$inst getITerms] {
        set kind [[$term getMTerm] getSigType]
        if {$kind in {POWER GROUND} && $require_power && [$term getNet] eq "NULL"} {error "Sizing power/ground terminal disconnected"}
    }
    return $inst
}
# OpenDB keeps the transform origin on a master swap. A wider MY/R180
# cell therefore shifts its lower-left box corner until we restore that anchor.
proc nssoc_critical_geometry {inst} {
    lassign [$inst getLocation] x y
    lassign [$inst getOrigin] ox oy
    set master [$inst getMaster];set bbox [$inst getBBox]
    return [dict create x $x y $y origin_x $ox origin_y $oy \
        width [$master getWidth] height [$master getHeight] site_width [[$master getSite] getWidth] \
        bbox_x_min [$bbox xMin] bbox_y_min [$bbox yMin] bbox_x_max [$bbox xMax] bbox_y_max [$bbox yMax] \
        orientation [$inst getOrient] status [$inst getPlacementStatus]]
}
proc nssoc_critical_geometry_json {geometry} {
    foreach key {orientation status} {dict set geometry $key [nssoc_hold_jstr [dict get $geometry $key]]}
    return [nssoc_hold_jobject $geometry]
}
proc nssoc_critical_geometry_consistent {geometry} {
    set orientation [dict get $geometry orientation]
    if {$orientation ni {R0 MY MX R180}} {error "Unsupported sizing row orientation"}
    set x [dict get $geometry x];set y [dict get $geometry y]
    set width [dict get $geometry width];set height [dict get $geometry height]
    set ox [expr {$x+($orientation in {MY R180} ? $width : 0)}]
    set oy [expr {$y+($orientation in {MX R180} ? $height : 0)}]
    foreach {key value} [list origin_x $ox origin_y $oy bbox_x_min $x bbox_y_min $y \
        bbox_x_max [expr {$x+$width}] bbox_y_max [expr {$y+$height}]] {
        if {[dict get $geometry $key] != $value} {error "Native sizing geometry relation differs: $key"}
    }
}
proc nssoc_critical_swap_geometry {before after} {
    nssoc_critical_geometry_consistent $before
    nssoc_critical_geometry_consistent $after
    foreach key {origin_x origin_y height site_width orientation status} {
        if {[dict get $before $key] ne [dict get $after $key]} {error "Native swap changed preserved geometry: $key"}
    }
    set pitch [dict get $before site_width]
    if {[dict get $before width] != 8*$pitch || [dict get $after width] != 13*$pitch} {error "Native swap width differs"}
    set dx [expr {[dict get $before orientation] in {MY R180} ? -5*$pitch : 0}]
    if {[dict get $after x] != [dict get $before x]+$dx || [dict get $after y] != [dict get $before y]} {
        error "Native swap moved beyond the exact orientation/width transform"
    }
    return $dx
}
proc nssoc_critical_size {driver inputnet outputnet expected_terms expected_place {require_power true}} {
    set inst [nssoc_critical_size_preflight $driver $inputnet $outputnet $expected_terms $expected_place $require_power]
    set pins [nssoc_critical_connections $inst];set before [nssoc_critical_shape [$inst getMaster]]
    set count [llength [[ord::get_db_block] getInsts]]
    set geometry_before [nssoc_critical_geometry $inst]
    nssoc_critical_geometry_consistent $geometry_before
    set observed_terms {}
    foreach term [[[$inst findITerm X] getNet] getITerms] {
        set load [$term getInst]
        lappend observed_terms [list [$load getName] [[$load getMaster] getName] [[$term getMTerm] getName]]
    }
    set term_json {}
    foreach row [lsort $observed_terms] {
        set fields {}; foreach item $row {lappend fields [nssoc_hold_jstr $item]}
        lappend term_json "\[[join $fields ,]\]"
    }
    set place_json {}
    foreach item [concat [$inst getLocation] [list [$inst getOrient] [$inst getPlacementStatus]]] {
        lappend place_json [nssoc_hold_jstr $item]
    }
    set pins_json {}
    foreach pair $pins {dict set pins_json [lindex $pair 0] [nssoc_hold_jstr [lindex $pair 1]]}
    # OpenSTA's native command updates the DB/STA cell binding. No direct pin or
    # logic rewrite; legal placement and fresh RC are still mandatory afterwards.
    replace_cell [get_cells $driver] sg13g2_buf_8
    set geometry_swapped [nssoc_critical_geometry $inst]
    if {[[$inst getMaster] getName] ne "sg13g2_buf_8" || [nssoc_critical_connections $inst] ne $pins ||
        [llength [[ord::get_db_block] getInsts]] != $count} {
        error "Native sizing changed connectivity, count or replacement master"
    }
    set native_dx [nssoc_critical_swap_geometry $geometry_before $geometry_swapped]
    # Anchor the larger footprint at the exact source lower-left; never accept
    # an arbitrary movement. DPL/check_placement, fresh routing and reloads
    # remain mandatory after this explicit physical edit.
    $inst setLocation [dict get $geometry_before x] [dict get $geometry_before y]
    set geometry_anchored [nssoc_critical_geometry $inst]
    nssoc_critical_geometry_consistent $geometry_anchored
    foreach key {width height site_width orientation status} {
        if {[dict get $geometry_anchored $key] ne [dict get $geometry_swapped $key]} {error "Anchor restore changed non-location geometry: $key"}
    }
    if {[[$inst getMaster] getName] ne "sg13g2_buf_8" || [nssoc_critical_connections $inst] ne $pins || [llength [[ord::get_db_block] getInsts]] != $count ||
        [concat [$inst getLocation] [list [$inst getOrient] [$inst getPlacementStatus]]] ne $expected_place} {
        error "Sizing anchor restore changed connectivity, count or source placement"
    }
    return [dict create instance [nssoc_hold_jstr $driver] original_master [nssoc_hold_jstr sg13g2_buf_4] \
        replacement_master [nssoc_hold_jstr sg13g2_buf_8] native_calls 1 instance_count $count \
        original_width [dict get $before width] replacement_width [[$inst getMaster] getWidth] \
        site_width [dict get $before site_width] connectivity_preserved true immediate_placement_preserved true \
        observed_input_net [nssoc_hold_jstr $inputnet] observed_output_net [nssoc_hold_jstr $outputnet] \
        observed_output_terminals "\[[join $term_json ,]\]" observed_placement "\[[join $place_json ,]\]" \
        observed_all_pin_nets [nssoc_hold_jobject $pins_json] \
        geometry_before [nssoc_critical_geometry_json $geometry_before] \
        geometry_after_native_swap [nssoc_critical_geometry_json $geometry_swapped] \
        geometry_after_anchor_restore [nssoc_critical_geometry_json $geometry_anchored] \
        native_swap_delta_x_dbu $native_dx anchor_restore_calls 1 source_lower_left_restored true]
}
proc nssoc_critical_export {directory} {
    file mkdir $directory
    write_db [file join $directory soc_top.odb]
    write_def [file join $directory soc_top.def]
    write_sdc -no_timestamp [file join $directory soc_top.sdc]
    write_verilog [file join $directory soc_top.v]
    set result {}
    foreach suffix {odb def sdc v} {dict set result soc_top.$suffix [nssoc_combined_pin [file join $directory soc_top.$suffix]]}
    return $result
}
proc nssoc_critical_hold_eligibility {endpoint driver} {
    set pin [nssoc_residual_hold_preflight $endpoint sg13g2_dfrbpq_1]
    set inst [[ord::get_db_block] findInst [lindex [split $endpoint /] 0]]
    set net [[$inst findITerm D] getNet];set outputs {}
    foreach term [$net getITerms] {
        if {[[$term getMTerm] getIoType] eq "OUTPUT"} {lappend outputs $term}
    }
    if {[llength $outputs] != 1} {error "Hold net has ambiguous driver"}
    set term [lindex $outputs 0];set source [$term getInst]
    if {"[$source getName]/[[$term getMTerm] getName]" ne $driver ||
        [[$source getMaster] getName] ne "sg13g2_dfrbpq_1"} {error "Hold source driver differs"}
    set eligible [expr {![$net isSpecial] && ![$net isConnectedByAbutment] && ![$net isDoNotTouch]}]
    return [dict create endpoint [nssoc_hold_jstr $endpoint] driver [nssoc_hold_jstr $driver] \
        native_data_net [nssoc_hold_jstr [$net getName]] is_special [$net isSpecial] \
        connected_by_abutment [$net isConnectedByAbutment] dont_touch [$net isDoNotTouch] \
        source_bound_nontristate_driver true source_predicate_ok_to_buffer $eligible \
        hold_slack_seconds [nssoc_residual_slack $pin] \
        setup_wns_seconds [nssoc_hold_number [sta::worst_slack_cmd max]] \
        interpretation [nssoc_hold_jstr {Pinned Resizer::okToBufferNet predicate evaluated on native objects; not a callable native predicate or a proof that the later hold-slack/buffer/journal gates pass.}]]
}
proc nssoc_critical_hold_reports {root stage} {
    set endpoint [sta::get_port_pin_error critical_hold_report _135215_/D]
    set inst [[ord::get_db_block] findInst _135215_]
    set netname [[[$inst findITerm D] getNet] getName]
    foreach corner [lsort [dict keys [nssoc_hold_corners]]] {
        foreach delay {min max} {
            foreach transition {rise fall} {
                report_checks -${transition}_to $endpoint -corner $corner -path_delay $delay \
                    -format full_clock_expanded -fields {slew cap input nets fanout} -digits 9 \
                    > [file join $root "$stage-$corner-$delay-$transition.rpt"]
            }
        }
        report_check_types -corner $corner -net $netname -max_slew -max_capacitance -digits 9 -verbose \
            > [file join $root "$stage-$corner-driver-electrical.rpt"]
    }
}
