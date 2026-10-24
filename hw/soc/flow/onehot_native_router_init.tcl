# SPDX-License-Identifier: Apache-2.0
# Hydrate the pinned native global router before the resizer registers callbacks.
# Existing source guides are reused; no new whole-chip routing is requested.
proc nssoc_read_text {path} {
    set f [open $path r]
    set text [read $f]
    close $f
    return $text
}
proc nssoc_physical_def {text} {
    # GCell grid is router bookkeeping, not cells, nets, pins or physical wires.
    regsub -all -line {^GCELLGRID[^\n]*\n} $text {} text
    return $text
}
proc nssoc_router_snapshot {prefix} {
    write_def "$prefix.def"
    foreach c $::env(NSSOC_CORNERS) {
        foreach kind {max min} {
            report_checks -corner $c -path_delay $kind -group_path_count 1 \
                -digits 9 -format full_clock_expanded > "$prefix-$c-$kind.rpt"
        }
    }
}
set prefix "$::env(NSSOC_RESIZER_OUT)/router-init"
nssoc_router_snapshot "$prefix-before"
write_guides "$prefix-source.guide"
set_routing_layers -signal Metal2-TopMetal2 -clock Metal4-TopMetal2
set_global_routing_layer_adjustment * 0.2
set_macro_extension 0
read_guides "$prefix-source.guide"
# start/end with no edits initializes native FastRoute/net tables and removes
# its temporary callback before the resizer installs its own callback.
global_route -start_incremental -congestion_iterations 200
global_route -end_incremental -congestion_iterations 200
nssoc_router_snapshot "$prefix-after"
set before [nssoc_physical_def [nssoc_read_text "$prefix-before.def"]]
set after [nssoc_physical_def [nssoc_read_text "$prefix-after.def"]]
if {$before ne $after} {error "Native router initialization changed physical DEF"}
# Verify the equality guard would reject an actual changed serialization.
set corrupt [string replace $after 0 0 X]
if {$before eq $corrupt} {error "Changed DEF control was accepted"}
foreach c $::env(NSSOC_CORNERS) {
    foreach kind {max min} {
        set a [nssoc_read_text "$prefix-before-$c-$kind.rpt"]
        set b [nssoc_read_text "$prefix-after-$c-$kind.rpt"]
        if {$a ne $b} {error "Native routing initialization changed source timing: $c/$kind"}
    }
}
puts "NSSOC_ROUTER_INITIALIZATION_EXACT_PHYSICAL_DEF_AND_SIX_REPORTS_PRESERVED"
