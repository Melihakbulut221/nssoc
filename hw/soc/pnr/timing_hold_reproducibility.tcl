# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Read-only diagnostic helpers for OpenROAD dcf36133 / OpenSTA 857316ff.
# Search.i:endpoints/endpoint_path_count, Graph.i:Vertex.slack and PathEnd.slack
# return the complete native endpoint census and SI-second Slack values.
# Search.cc:totalNegativeSlack is MIN(per-corner SUM(negative endpoint slack)).
# It is NOT the sum of every endpoint's minimum across all corners.

proc nssoc_hold_jstr {value} {
    return "\"[string map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t] $value]\""
}
proc nssoc_hold_jobject {values} {
    set rows {}
    dict for {key value} $values {lappend rows "[nssoc_hold_jstr $key]:$value"}
    return "\{[join $rows ,]\}"
}
proc nssoc_hold_write_json {path value} {
    set stream [open $path {WRONLY CREAT EXCL}]
    puts $stream $value
    close $stream
}
proc nssoc_hold_number {value} {
    if {![string is double -strict $value] || !($value < 1e100 && $value > -1e100)} {
        error "Invalid finite native number: $value"
    }
    return [format %.17g $value]
}
proc nssoc_hold_slack {value} {
    set value [nssoc_hold_number $value]
    if {abs($value) >= 1e20} {return UNCONSTRAINED}
    return $value
}
proc nssoc_hold_field {value} {
    if {[regexp {[\t\r\n]} $value]} {error "Unsafe TSV identity"}
    return $value
}
proc nssoc_hold_sha {path} {
    set result [exec sha256sum -- $path]
    if {![regexp {^([0-9a-f]{64})[[:space:]]} $result -> digest]} {
        error "SHA256 unavailable for $path"
    }
    return $digest
}
proc nssoc_hold_assert_coverage {expected names negative engine_negative} {
    if {[llength $names] != $expected || [llength [lsort -unique $names]] != $expected} {
        error "Incomplete or duplicate native endpoint census"
    }
    if {$negative != $engine_negative} {error "Exported negative endpoint census differs from native engine"}
}
proc nssoc_hold_assert_units {scale} {
    nssoc_hold_number $scale
    # This experiment is bound to the SG13G2 libraries in the published bundle.
    # Raw getters below are seconds regardless of this UI scale.
    if {$scale != 1e-9} {error "Published SG13G2 time-unit contract differs"}
}
proc nssoc_hold_assert_path_coverage {vertices path_minima} {
    dict for {name slack} $vertices {
        if {$slack eq "UNCONSTRAINED"} {
            if {[dict exists $path_minima $name]} {error "Finite PathEnd missing from vertex census"}
        } elseif {![dict exists $path_minima $name]} {
            error "Finite native endpoint omitted from all corner paths: $name"
        } elseif {$slack != [dict get $path_minima $name]} {
            # With endpoint fanout native Vertex.slack and PathEnd.slack can
            # differ. Do not accept that unsupported subset as complete proof.
            error "Unsupported native vertex-versus-PathEnd slack semantics: $name"
        }
    }
    foreach name [dict keys $path_minima] {
        if {![dict exists $vertices $name]} {error "PathEnd outside native endpoint census"}
    }
}
proc nssoc_hold_sums {values} {
    set plain 0.0
    set compensated 0.0
    set correction 0.0
    set single 0.0
    foreach value $values {
        set plain [expr {$plain + $value}]
        set y [expr {$value - $correction}]
        set next [expr {$compensated + $y}]
        set correction [expr {($next - $compensated) - $y}]
        set compensated $next
        binary scan [binary format f [expr {$single + $value}]] f single
    }
    set reverse 0.0
    foreach value [lreverse $values] {
        binary scan [binary format f [expr {$reverse + $value}]] f reverse
    }
    return [dict create fixed_order_tns_seconds $plain compensated_tns_seconds $compensated \
        float32_forward_tns_seconds $single float32_reverse_tns_seconds $reverse]
}

proc nssoc_hold_corners {} {
    set corners {}
    foreach corner [sta::corners] {
        set name [nssoc_hold_field [$corner name]]
        if {[dict exists $corners $name]} {error "Duplicate native corner"}
        dict set corners $name $corner
    }
    if {![dict size $corners]} {error "No timing corners loaded"}
    return $corners
}

proc nssoc_hold_parasitics {path corners} {
    # All driver/load tuples, not just selected critical paths. gzip -n writes
    # deterministic, lossless compressed bytes without a large plain TSV copy.
    set pins {}
    foreach pin [get_pins -hierarchical *] {
        dict set pins [nssoc_hold_field [get_property $pin full_name]] $pin
    }
    foreach port [get_ports *] {
        set pin [sta::get_port_pin_error hold_diagnostic_port $port]
        dict set pins [nssoc_hold_field [get_property $pin full_name]] $pin
    }
    set drivers {}
    dict for {name pin} $pins {
        if {[$pin is_driver] && ![$pin is_pwr_gnd]} {dict set drivers $name $pin}
    }
    set stream [open "|gzip -n -c > [list $path]" w]
    puts $stream "corner\tdriver\ttransition\tmin_max\tkind\tload\tc2_farads\trpi_ohms\tc1_farads\telmore_seconds"
    set original_corner [sta::cmd_corner]
    set tuple_count 0
    set model_count 0
    set missing_models 0
    try {
        foreach corner_name [lsort [dict keys $corners]] {
            sta::set_cmd_corner [dict get $corners $corner_name]
            foreach name [lsort [dict keys $drivers]] {
                set driver [dict get $drivers $name]
                set loads {}
                set iterator [$driver connected_pin_iterator]
                while {[$iterator has_next]} {
                    set pin [$iterator next]
                    if {[$pin is_load] && ![$pin is_pwr_gnd]} {
                        dict set loads [nssoc_hold_field [get_property $pin full_name]] $pin
                    }
                }
                $iterator finish
                foreach rf {rise fall} {
                    foreach mm {min max} {
                        set pi [sta::find_pi_elmore $driver $rf $mm]
                        set prefix [list $corner_name $name $rf $mm]
                        if {[llength $pi] == 0} {
                            incr missing_models
                            puts $stream [join [concat $prefix {NO_PI_MODEL - - - - -}] \t]
                            incr tuple_count
                        } elseif {[llength $pi] == 3} {
                            incr model_count
                            set numbers {}
                            foreach value $pi {lappend numbers [nssoc_hold_number $value]}
                            puts $stream [join [concat $prefix {PI_MODEL -} $numbers {-}] \t]
                            incr tuple_count
                            foreach load_name [lsort [dict keys $loads]] {
                                set delay [sta::find_elmore $driver [dict get $loads $load_name] $rf $mm]
                                puts $stream [join [concat $prefix [list ELMORE $load_name - - - [nssoc_hold_number $delay]]] \t]
                                incr tuple_count
                            }
                        } else {error "Unexpected native Pi model arity"}
                    }
                }
            }
        }
    } finally {
        sta::set_cmd_corner $original_corner
        close $stream
    }
    return [dict create driver_count [dict size $drivers] tuple_count $tuple_count \
        pi_model_count $model_count missing_pi_model_count $missing_models]
}

proc nssoc_hold_physical {directory corners} {
    write_sdc -no_timestamp [file join $directory constraints.sdc]
    write_verilog [file join $directory connectivity.v]
    set names {}
    foreach inst [[ord::get_db_block] getInsts] {dict set names [$inst getName] $inst}
    set stream [open [file join $directory placement.tsv] {WRONLY CREAT EXCL}]
    puts $stream "instance\tmaster\tx_dbu\ty_dbu\torientation\tstatus"
    foreach name [lsort [dict keys $names]] {
        set inst [dict get $names $name]
        lassign [$inst getLocation] x y
        puts $stream [join [list [nssoc_hold_field $name] [[$inst getMaster] getName] $x $y [$inst getOrient] [$inst getPlacementStatus]] \t]
    }
    close $stream
    if {[grt::have_routes]} {
        write_global_route_segments [file join $directory routes.txt]
    } else {
        # At initial reload no GlobalRouter routes exist. Full DEF retains the
        # ODB wire topology instead; the stage explicitly labels this difference.
        write_def [file join $directory routes.txt]
    }
    set rc [nssoc_hold_parasitics [file join $directory parasitics.tsv.gz] $corners]
    set fingerprints {}
    foreach {key name} {constraints constraints.sdc netlist connectivity.v placement placement.tsv routing routes.txt parasitics parasitics.tsv.gz} {
        dict set fingerprints $key [nssoc_hold_sha [file join $directory $name]]
    }
    return [dict create fingerprints $fingerprints parasitic_inventory $rc]
}

proc nssoc_hold_snapshot {name output} {
    if {![regexp {^[a-z][a-z0-9_]*$} $name]} {error "Invalid diagnostic stage"}
    set directory [file join $output $name]
    if {[file exists $directory]} {error "Diagnostic stage must be fresh"}
    file mkdir $directory
    nssoc_hold_assert_units [sta::unit_scale time]
    set corners [nssoc_hold_corners]
    # Sample native aggregation before path enumeration may update caches.
    set native_global_before [sta::total_negative_slack_cmd min]
    set engine_negative [sta::endpoint_violation_count min]
    set pins [sta::endpoints]
    set expected [sta::endpoint_path_count]
    set census {}
    foreach pin $pins {
        set pin_name [nssoc_hold_field [get_property $pin full_name]]
        if {[dict exists $census $pin_name]} {error "Native endpoint name alias"}
        set vertices [$pin vertices]
        # Pin census deduplicates vertices. Reject unsupported bidirectional
        # ambiguity instead of silently omitting a native graph endpoint.
        if {[llength $vertices] != 1 || [[lindex $vertices 0] is_bidirect_driver]} {
            error "Ambiguous bidirectional native endpoint: $pin_name"
        }
        dict set census $pin_name [lindex $vertices 0]
    }
    set ordered [lsort [dict keys $census]]
    set stream [open [file join $directory endpoints.tsv] {WRONLY CREAT EXCL}]
    puts $stream "endpoint\tglobal_vertex_slack_seconds"
    set negative 0
    set vertex_slacks {}
    foreach endpoint $ordered {
        set slack [nssoc_hold_slack [[dict get $census $endpoint] slack min]]
        dict set vertex_slacks $endpoint $slack
        if {$slack ne "UNCONSTRAINED" && $slack < 0} {incr negative}
        puts $stream "$endpoint\t$slack"
    }
    close $stream
    nssoc_hold_assert_coverage $expected $ordered $negative $engine_negative
    set stream [open [file join $directory hold-endpoints.tsv] {WRONLY CREAT EXCL}]
    puts $stream "corner\tendpoint\tmin_rise_seconds\tmin_fall_seconds\tmin_seconds"
    set corner_rows {}
    set path_minima {}
    foreach corner_name [lsort [dict keys $corners]] {
        set corner [dict get $corners $corner_name]
        set native_before [sta::total_negative_slack_corner_cmd $corner min]
        set sampled {}
        set limit [expr {$expected + 1}]
        foreach rf {rise fall} {
            # Source PathGroup.cc caps ONE path per native vertex per group.
            # There are exactly E unambiguous vertices, so E+1 cannot truncate
            # any group. No slack filter: positive constrained endpoints remain.
            foreach path [find_timing_paths -corner $corner_name -path_delay min_$rf \
                    -group_path_count $limit -endpoint_path_count 1] {
                set endpoint [get_property [$path pin] full_name]
                if {![dict exists $census $endpoint] || [$path vertex] ne [dict get $census $endpoint]} {
                    error "Path endpoint outside complete native census"
                }
                if {[$path is_unconstrained]} {error "Unconstrained PathEnd in constrained query"}
                set value [nssoc_hold_slack [$path slack]]
                if {$value eq "UNCONSTRAINED"} {error "Non-finite constrained path slack"}
                if {![dict exists $sampled $endpoint $rf] || $value < [dict get $sampled $endpoint $rf]} {
                    dict set sampled $endpoint $rf $value
                }
            }
        }
        set values {}
        set represented 0
        set path_negative 0
        foreach endpoint $ordered {
            set rise UNCONSTRAINED
            set fall UNCONSTRAINED
            if {[dict exists $sampled $endpoint rise]} {set rise [dict get $sampled $endpoint rise]}
            if {[dict exists $sampled $endpoint fall]} {set fall [dict get $sampled $endpoint fall]}
            set slack UNCONSTRAINED
            foreach value [list $rise $fall] {
                if {$value ne "UNCONSTRAINED" && ($slack eq "UNCONSTRAINED" || $value < $slack)} {set slack $value}
            }
            if {$slack ne "UNCONSTRAINED"} {
                incr represented
                if {$slack < 0} {incr path_negative; lappend values $slack}
                if {![dict exists $path_minima $endpoint] || $slack < [dict get $path_minima $endpoint]} {
                    dict set path_minima $endpoint $slack
                }
            }
            puts $stream [join [list $corner_name $endpoint $rise $fall $slack] \t]
        }
        set row [dict create name [nssoc_hold_jstr $corner_name] \
            constrained_endpoints $represented unrepresented_endpoints [expr {$expected-$represented}] \
            negative_path_endpoints $path_negative \
            native_tns_seconds_before [nssoc_hold_number $native_before] \
            native_tns_seconds_after [nssoc_hold_number [sta::total_negative_slack_corner_cmd $corner min]] \
            native_wns_seconds [nssoc_hold_number [sta::worst_slack_corner $corner min]]]
        dict for {key value} [nssoc_hold_sums $values] {dict set row $key [nssoc_hold_number $value]}
        lappend corner_rows [nssoc_hold_jobject $row]
    }
    close $stream
    nssoc_hold_assert_path_coverage $vertex_slacks $path_minima
    set native_global_after [sta::total_negative_slack_cmd min]
    set physical [nssoc_hold_physical $directory $corners]
    set fingerprint_json {}
    dict for {key value} [dict get $physical fingerprints] {dict set fingerprint_json $key [nssoc_hold_jstr $value]}
    set row [dict create name [nssoc_hold_jstr $name] endpoint_count $expected engine_endpoint_count $expected \
        exported_endpoint_count [llength $ordered] negative_vertex_endpoints $negative \
        engine_negative_vertex_endpoints $engine_negative all_endpoint_coverage true \
        vertex_path_semantics_match true \
        time_unit_seconds [nssoc_hold_number [sta::unit_scale time]] value_units [nssoc_hold_jstr seconds] \
        numeric_format [nssoc_hold_jstr %.17g] \
        raw_getters [nssoc_hold_jstr {SWIG Slack delayAsFloat -> Tcl double, SI seconds}] \
        parasitic_observation_scope [nssoc_hold_jstr {All Pi/Elmore getter tuples observed; find_elmore returns zero for both absent and zero load delay, so this is not a complete parasitic topology/annotation-existence proof.}] \
        native_global_tns_seconds_before [nssoc_hold_number $native_global_before] \
        native_global_tns_seconds_after [nssoc_hold_number $native_global_after] \
        corners "\[[join $corner_rows ,]\]" \
        parasitic_inventory [nssoc_hold_jobject [dict get $physical parasitic_inventory]]]
    nssoc_hold_write_json [file join $directory native.json] [nssoc_hold_jobject $row]
    set files {}
    foreach path [lsort [glob -directory $directory *]] {
        dict set files [file tail $path] [nssoc_hold_jobject [dict create bytes [file size $path] sha256 [nssoc_hold_jstr [nssoc_hold_sha $path]]]]
    }
    dict set row files [nssoc_hold_jobject $files]
    dict set row fingerprints [nssoc_hold_jobject $fingerprint_json]
    set result [nssoc_hold_jobject $row]
    puts "HOLD_DIAGNOSTIC_STAGE $name ENDPOINTS $expected NEGATIVE $negative"
    return [dict create name $name json $result fingerprints [dict get $physical fingerprints]]
}

proc nssoc_hold_assert_same_physical {left right} {
    if {[dict get $left fingerprints] ne [dict get $right fingerprints]} {
        error "No-op physical/parasitic fingerprint changed"
    }
}
