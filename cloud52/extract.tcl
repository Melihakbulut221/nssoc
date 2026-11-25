read_db {/work/routed.odb}
set_thread_count 2
define_process_corner -ext_model_index 0 nominal
extract_parasitics -ext_model_file {/repo/hw/soc/tools/pdk/ihp-sg13g2/libs.tech/librelane/IHP_rcx_patterns.rules} -lef_res
write_spef {/work/nominal.spef}
