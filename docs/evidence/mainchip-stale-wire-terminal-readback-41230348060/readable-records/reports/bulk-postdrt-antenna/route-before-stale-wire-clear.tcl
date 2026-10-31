source {/work/routing-inputs/global/run/1-nssoc-repairfreshglobal/_env.tcl}
if {![info exists ::env(DESIGN_NAME)] || $::env(DESIGN_NAME) ne "soc_top"} {error "Original setting DESIGN_NAME differs"}
if {![info exists ::env(DRT_THREADS)] || $::env(DRT_THREADS) ne "2"} {error "Original setting DRT_THREADS differs"}
if {![info exists ::env(DRT_OPT_ITERS)] || $::env(DRT_OPT_ITERS) ne "64"} {error "Original setting DRT_OPT_ITERS differs"}
if {![info exists ::env(DRT_SAVE_SNAPSHOTS)] || $::env(DRT_SAVE_SNAPSHOTS) ne "0"} {error "Original setting DRT_SAVE_SNAPSHOTS differs"}
if {![info exists ::env(DRT_SAVE_DRC_REPORT_ITERS)] || $::env(DRT_SAVE_DRC_REPORT_ITERS) ne "5"} {error "Original setting DRT_SAVE_DRC_REPORT_ITERS differs"}
set ::env(STEP_DIR) {/work/out/work/bulk-postdrt-antenna}
read_db {/work/out/work/bulk-postdrt-antenna/fixed.odb}
set_routing_layers -signal Metal2-TopMetal2 -clock Metal4-TopMetal2
set_thread_count $::env(DRT_THREADS)

set drc_report_iter_step_arg ""
if { $::env(DRT_SAVE_SNAPSHOTS) } {
    set_debug_level DRT snapshot 1
    set drc_report_iter_step_arg "-drc_report_iter_step 1"
    detailed_route_debug -snapshot_dir "$::env(STEP_DIR)"
}
if { [info exists ::env(DRT_SAVE_DRC_REPORT_ITERS)] } {
    set drc_report_iter_step_arg "-drc_report_iter_step $::env(DRT_SAVE_DRC_REPORT_ITERS)"
}


set drt_args [list]
lappend drt_args -droute_end_iter $::env(DRT_OPT_ITERS)
lappend drt_args -or_seed 42
lappend drt_args -verbose 1
lappend drt_args {*}$drc_report_iter_step_arg

puts NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_BEGIN
set route_code [catch {detailed_route {*}$drt_args -output_drc {/work/out/work/bulk-postdrt-antenna/fixed-routing.drc}} route_result route_options]
set save_errors {}
if {[catch {write_def {/work/out/work/bulk-postdrt-antenna/route-partial.def}} save_error]} {lappend save_errors $save_error}
if {[catch {write_db {/work/out/work/bulk-postdrt-antenna/route-partial.odb}} save_error]} {lappend save_errors $save_error}
if {$route_code} {puts stderr "NSSOC_BULK_ROUTE_SAVE_ERRORS $save_errors"; return -options $route_options $route_result}
if {[llength $save_errors]} {error "route output preservation: $save_errors"}

write_def {/work/out/work/bulk-postdrt-antenna/routed-fixed.def}
write_db {/work/out/work/bulk-postdrt-antenna/routed-fixed.odb}
puts NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_RETURNED
exit
