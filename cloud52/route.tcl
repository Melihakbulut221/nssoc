set ::env(SCRIPTS_DIR) /nix/store/ffl2vg3m80k0p74pyffnmai83fnv38mf-python3-3.13.9-env/lib/python3.13/site-packages/librelane/scripts
set ::env(_TCL_ENV_IN) /work/env.tcl
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
set_cmd_units -time ns -capacitance pF -distance um
set ::env(_SDC_IN) {/repo/hw/soc/sta/soc_interfaces_external_irq.sdc}
set ::env(_LIB_CORNER_0) {nom_typ_1p20V_25C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_typ_1p2V_3p3V_25C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x64_c2_bm_bist_typ_1p20V_25C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_1024x32_c2_bm_bist_typ_1p20V_25C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_512x16_c2_bm_bist_typ_1p20V_25C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_2P_256x16_c2_bm_bist_typ_1p20V_25C.lib}
set ::env(_LIB_CORNER_1) {nom_slow_1p08V_125C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p08V_125C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_slow_1p08V_3p0V_125C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x64_c2_bm_bist_slow_1p08V_125C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_1024x32_c2_bm_bist_slow_1p08V_125C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_512x16_c2_bm_bist_slow_1p08V_125C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_2P_256x16_c2_bm_bist_slow_1p08V_125C.lib}
set ::env(_LIB_CORNER_2) {nom_fast_1p32V_m40C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_fast_1p32V_m40C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_fast_1p32V_3p6V_m40C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x64_c2_bm_bist_fast_1p32V_m55C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_1024x32_c2_bm_bist_fast_1p32V_m55C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_512x16_c2_bm_bist_fast_1p32V_m55C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_2P_256x16_c2_bm_bist_fast_1p32V_m55C.lib}
set ::env(_PNR_EXCLUDED_CELLS) {sg13g2_dfrbp_2 sg13g2_lgcp_1 sg13g2_sighold sg13g2_sdfbbp_1 sg13g2_slgcp_1}
set ::env(CURRENT_ODB) /work/input.odb
read_current_odb
set ::env(GRT_ADJUSTMENT) 0.2
set ::env(GRT_MACRO_EXTENSION) 0
set ::env(GRT_LAYER_ADJUSTMENTS) "0 0 0 0 0 0 0"
set ::env(GRT_ALLOW_CONGESTION) 0
set ::env(GRT_ANTENNA_REPAIR_ITERS) 3
set ::env(GRT_OVERFLOW_ITERS) 50
set ::env(GRT_ANTENNA_REPAIR_MARGIN) 10
set ::env(GRT_ANTENNA_REPAIR_JUMPER_ONLY) 0
set ::env(GRT_ANTENNA_REPAIR_DIODE_ONLY) 0
set ::env(DPL_CELL_PADDING) 0
set ::env(STEP_DIR) /work
set block [ord::get_db_block]
proc pin_map {inst} {
    set result {}
    foreach pin [$inst getITerms] {
        set net [$pin getNet]
        dict set result [[$pin getMTerm] getName] [expr {$net eq "NULL" ? "" : [$net getName]}]
    }
    return [lsort -stride 2 -index 0 $result]
}
foreach name {fanout662 fanout4070 fanout3716 fanout5688 fanout2869 fanout3256} {
    set inst [$block findInst $name]
    if {$inst eq "NULL" || [[$inst getMaster] getName] ne "sg13g2_buf_1"} {error "Unexpected buffer $name"}
    set before [pin_map $inst]
    if {$::env(TRIAL) eq "sized"} {
        set replacement [[ord::get_db] findMaster sg13g2_buf_4]
        if {![$inst swapMaster $replacement]} {error "Could not resize $name"}
    }
    if {[pin_map $inst] ne $before} {error "Connectivity changed on $name"}
}
detailed_placement
check_placement
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
estimate_parasitics -global_routing
puts MATCHED_GLOBAL_PATH
report_checks -from [get_pins _129487_/CLK] -to [get_pins _125472_/D] -path_delay max -corner nom_slow_1p08V_125C -digits 6 -format full_clock_expanded -fields {slew cap fanout input_pin net}
source /repo/hw/soc/flow/prune_orphan_guides.tcl
puts "ORPHANS [prune_orphan_guides [ord::get_db_block]]"
set_thread_count 12
detailed_route -droute_end_iter 64 -or_seed 42 -verbose 1 -drc_report_iter_step 1 -output_drc /work/soc_top.drc
puts "ROUTING_DRVS [detailed_route_num_drvs]"
write_db /work/routed.odb
check_antennas
