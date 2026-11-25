set ::env(SCRIPTS_DIR) /nix/store/ffl2vg3m80k0p74pyffnmai83fnv38mf-python3-3.13.9-env/lib/python3.13/site-packages/librelane/scripts
set ::env(_TCL_ENV_IN) /work/env.tcl
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
set_cmd_units -time ns -capacitance pF -distance um
set ::env(_SDC_IN) {/repo/hw/soc/sta/soc_interfaces_external_irq.sdc}
set ::env(_LIB_CORNER_0) {nom_typ_1p20V_25C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_typ_1p2V_3p3V_25C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x64_c2_bm_bist_typ_1p20V_25C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_1024x32_c2_bm_bist_typ_1p20V_25C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_512x16_c2_bm_bist_typ_1p20V_25C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_2P_256x16_c2_bm_bist_typ_1p20V_25C.lib}
set ::env(_LIB_CORNER_1) {nom_slow_1p08V_125C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p08V_125C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_slow_1p08V_3p0V_125C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x64_c2_bm_bist_slow_1p08V_125C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_1024x32_c2_bm_bist_slow_1p08V_125C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_512x16_c2_bm_bist_slow_1p08V_125C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_2P_256x16_c2_bm_bist_slow_1p08V_125C.lib}
set ::env(_LIB_CORNER_2) {nom_fast_1p32V_m40C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_fast_1p32V_m40C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_fast_1p32V_3p6V_m40C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x64_c2_bm_bist_fast_1p32V_m55C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_1024x32_c2_bm_bist_fast_1p32V_m55C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_512x16_c2_bm_bist_fast_1p32V_m55C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_2P_256x16_c2_bm_bist_fast_1p32V_m55C.lib}
set ::env(_PNR_EXCLUDED_CELLS) {sg13g2_dfrbp_2 sg13g2_lgcp_1 sg13g2_sighold sg13g2_sdfbbp_1 sg13g2_slgcp_1}
set ::env(CURRENT_ODB) /work/routed.odb
read_current_odb
foreach corner {nom_fast_1p32V_m40C nom_typ_1p20V_25C nom_slow_1p08V_125C} {read_spef -corner $corner {/work/nominal.spef}}
report_parasitic_annotation -report_unannotated
foreach corner {nom_fast_1p32V_m40C nom_typ_1p20V_25C nom_slow_1p08V_125C} {
    foreach delay {min max} {
        puts "QSPIGRT $corner $delay port"
        report_checks -to [get_ports qspi_sck_o] -path_delay $delay -corner $corner -digits 6 -format slack_only
        puts "QSPIGRT $corner $delay design"
        report_checks -sort_by_slack -path_delay $delay -corner $corner -digits 6 -format slack_only -group_path_count 1
    }
}

foreach corner {nom_fast_1p32V_m40C nom_typ_1p20V_25C nom_slow_1p08V_125C} {
    foreach delay {min max} {
        puts "NSSOC_ENDPOINTS $corner $delay"
        report_checks -sort_by_slack -path_delay $delay -corner $corner -digits 6 -format end -group_path_count 40 -endpoint_path_count 1
    }
}

report_checks -path_delay max -corner nom_slow_1p08V_125C -group_path_count 10 -unique_paths_to_endpoint -format full_clock_expanded -digits 6
