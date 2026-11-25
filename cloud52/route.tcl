read_db /work/input.odb
source /repo/hw/soc/flow/prune_orphan_guides.tcl
puts "ORPHANS [prune_orphan_guides [ord::get_db_block]]"
set_thread_count 12
detailed_route -droute_end_iter 64 -or_seed 42 -verbose 1 -drc_report_iter_step 1 -output_drc /work/soc_top.drc
puts "ROUTING_DRVS [detailed_route_num_drvs]"
write_db /work/routed.odb
check_antennas
