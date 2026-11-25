set ::env(STEP_ID) OpenROAD.STAMidPNR
set ::env(TECH_LEF) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef
set ::env(MACRO_LEFS) "/repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lef/RM_IHPSG13_1P_2048x64_c2_bm_bist.lef /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lef/RM_IHPSG13_1P_1024x32_c2_bm_bist.lef /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lef/RM_IHPSG13_1P_512x16_c2_bm_bist.lef /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lef/RM_IHPSG13_2P_256x16_c2_bm_bist.lef"
set ::env(STD_CELL_LIBRARY) sg13g2_stdcell
set ::env(VDD_PIN) VPWR
set ::env(GND_PIN) VGND
set ::env(TECH_LEFS) "\"nom_*\" /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef \"min_*\" /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef \"max_*\" /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef"
set ::env(PRIMARY_GDSII_STREAMOUT_TOOL) magic
set ::env(DEFAULT_CORNER) nom_typ_1p20V_25C
set ::env(STA_CORNERS) "nom_fast_1p32V_m40C nom_slow_1p08V_125C nom_typ_1p20V_25C"
set ::env(RT_MIN_LAYER) Metal2
set ::env(RT_MAX_LAYER) TopMetal2
set ::env(SCL_GROUND_PINS) VSS
set ::env(SCL_POWER_PINS) VDD
set ::env(TRISTATE_CELLS) "\"sg13g2_ebufn_*\" \"sg13g2_einvn_*\""
set ::env(FILL_CELLS) "sg13g2_fill_1 sg13g2_fill_2"
set ::env(DECAP_CELLS) "\"sg13g2_decap_*\""
set ::env(LIB) "nom_typ_1p20V_25C \"/repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_typ_1p2V_3p3V_25C.lib\" nom_fast_1p32V_m40C \"/repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_fast_1p32V_m40C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_fast_1p32V_3p6V_m40C.lib\" nom_slow_1p08V_125C \"/repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p08V_125C.lib /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_slow_1p08V_3p0V_125C.lib\""
set ::env(CELL_LEFS) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_stdcell.lef
set ::env(CELL_GDS) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/gds/sg13g2_stdcell.gds
set ::env(CELL_VERILOG_MODELS) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v
set ::env(CELL_SPICE_MODELS) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice
set ::env(CELL_CDLS) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/cdl/sg13g2_stdcell.cdl
set ::env(SYNTH_EXCLUDED_CELL_FILE) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.tech/librelane/sg13g2_stdcell/synth_exclude.cells
set ::env(PNR_EXCLUDED_CELL_FILE) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.tech/librelane/sg13g2_stdcell/pnr_exclude.cells
set ::env(OUTPUT_CAP_LOAD) 6.0
set ::env(MAX_FANOUT_CONSTRAINT) 10
set ::env(CLOCK_UNCERTAINTY_CONSTRAINT) 0.25
set ::env(CLOCK_TRANSITION_CONSTRAINT) 0.15
set ::env(TIME_DERATING_CONSTRAINT) 5.0
set ::env(IO_DELAY_CONSTRAINT) 20
set ::env(SYNTH_DRIVING_CELL) sg13g2_buf_4/X
set ::env(SYNTH_TIEHI_CELL) sg13g2_tiehi/L_HI
set ::env(SYNTH_TIELO_CELL) sg13g2_tielo/L_LO
set ::env(SYNTH_BUFFER_CELL) sg13g2_buf_1/A/X
set ::env(PLACE_SITE) CoreSite
set ::env(CELL_PAD_EXCLUDE) "\"sg13g2_fill_*\" \"sg13g2_decap_*\""
set ::env(DIODE_CELL) sg13g2_antennanp/A
set ::env(DESIGN_NAME) soc_top
set ::env(CLOCK_PERIOD) 20
set ::env(CLOCK_PORT) "clk_i eth_rx_clk_i eth_tx_clk_i"
set ::env(CLOCK_NET) "clk_i eth_rx_clk_i eth_tx_clk_i"
set ::env(DIE_AREA) "0 0 3326.4 2475.9"
set ::env(MACROS) "RM_IHPSG13_1P_2048x64_c2_bm_bist \"gds /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/gds/RM_IHPSG13_1P_2048x64_c2_bm_bist.gds lef /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lef/RM_IHPSG13_1P_2048x64_c2_bm_bist.lef instances \\\"u_ram.g_ram_2048x64_ecc.u_b0 \\\\\\\"location \\\\\\\\\\\\\\\"120.0 60.48\\\\\\\\\\\\\\\" orientation FS\\\\\\\" u_ram.g_ram_2048x64_ecc.u_b1 \\\\\\\"location \\\\\\\\\\\\\\\"944.64 60.48\\\\\\\\\\\\\\\" orientation FS\\\\\\\" u_ram.g_ram_2048x64_ecc.u_b2 \\\\\\\"location \\\\\\\\\\\\\\\"120.0 1787.94\\\\\\\\\\\\\\\" orientation N\\\\\\\" u_ram.g_ram_2048x64_ecc.u_b3 \\\\\\\"location \\\\\\\\\\\\\\\"944.64 1787.94\\\\\\\\\\\\\\\" orientation N\\\\\\\"\\\" vh /repo/hw/soc/pnr/RM_IHPSG13_1P_2048x64_c2_bm_bist_bb.v nl \\\"\\\" pnl \\\"\\\" spef \\\"\\\" lib \\\"nom_typ_1p20V_25C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x64_c2_bm_bist_typ_1p20V_25C.lib nom_slow_1p08V_125C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x64_c2_bm_bist_slow_1p08V_125C.lib nom_fast_1p32V_m40C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x64_c2_bm_bist_fast_1p32V_m55C.lib\\\" spice \\\"\\\" sdf \\\"\\\" json_h None\" RM_IHPSG13_1P_1024x32_c2_bm_bist \"gds /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/gds/RM_IHPSG13_1P_1024x32_c2_bm_bist.gds lef /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lef/RM_IHPSG13_1P_1024x32_c2_bm_bist.lef instances \\\"\\\" vh /repo/hw/soc/pnr/RM_IHPSG13_1P_1024x32_c2_bm_bist_bb.v nl \\\"\\\" pnl \\\"\\\" spef \\\"\\\" lib \\\"nom_typ_1p20V_25C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_1024x32_c2_bm_bist_typ_1p20V_25C.lib nom_slow_1p08V_125C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_1024x32_c2_bm_bist_slow_1p08V_125C.lib nom_fast_1p32V_m40C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_1024x32_c2_bm_bist_fast_1p32V_m55C.lib\\\" spice \\\"\\\" sdf \\\"\\\" json_h None\" RM_IHPSG13_1P_512x16_c2_bm_bist \"gds /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/gds/RM_IHPSG13_1P_512x16_c2_bm_bist.gds lef /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lef/RM_IHPSG13_1P_512x16_c2_bm_bist.lef instances \\\"\\\" vh /repo/hw/soc/pnr/RM_IHPSG13_1P_512x16_c2_bm_bist_bb.v nl \\\"\\\" pnl \\\"\\\" spef \\\"\\\" lib \\\"nom_typ_1p20V_25C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_512x16_c2_bm_bist_typ_1p20V_25C.lib nom_slow_1p08V_125C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_512x16_c2_bm_bist_slow_1p08V_125C.lib nom_fast_1p32V_m40C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_512x16_c2_bm_bist_fast_1p32V_m55C.lib\\\" spice \\\"\\\" sdf \\\"\\\" json_h None\" RM_IHPSG13_2P_256x16_c2_bm_bist \"gds /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/gds/RM_IHPSG13_2P_256x16_c2_bm_bist.gds lef /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lef/RM_IHPSG13_2P_256x16_c2_bm_bist.lef instances \\\"\\\\\\\"u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[0].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2340 60.48\\\\\\\\\\\\\\\" orientation FS\\\\\\\" \\\\\\\"u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[1].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2340 351.54\\\\\\\\\\\\\\\" orientation N\\\\\\\" \\\\\\\"u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[2].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2340 642.6\\\\\\\\\\\\\\\" orientation FS\\\\\\\" \\\\\\\"u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[3].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2340 933.66\\\\\\\\\\\\\\\" orientation N\\\\\\\" \\\\\\\"u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[4].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2340 1224.72\\\\\\\\\\\\\\\" orientation FS\\\\\\\" \\\\\\\"u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[5].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2340 1515.78\\\\\\\\\\\\\\\" orientation N\\\\\\\" \\\\\\\"u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[6].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2340 1806.84\\\\\\\\\\\\\\\" orientation FS\\\\\\\" \\\\\\\"u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[7].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2340 2097.9\\\\\\\\\\\\\\\" orientation N\\\\\\\" \\\\\\\"u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[0].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2808 60.48\\\\\\\\\\\\\\\" orientation FS\\\\\\\" \\\\\\\"u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[1].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2808 351.54\\\\\\\\\\\\\\\" orientation N\\\\\\\" \\\\\\\"u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[2].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2808 642.6\\\\\\\\\\\\\\\" orientation FS\\\\\\\" \\\\\\\"u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[3].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2808 933.66\\\\\\\\\\\\\\\" orientation N\\\\\\\" \\\\\\\"u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[4].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2808 1224.72\\\\\\\\\\\\\\\" orientation FS\\\\\\\" \\\\\\\"u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[5].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2808 1515.78\\\\\\\\\\\\\\\" orientation N\\\\\\\" \\\\\\\"u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[6].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2808 1806.84\\\\\\\\\\\\\\\" orientation FS\\\\\\\" \\\\\\\"u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank\\\\\\\\\\\\\\\[7].u_mem\\\\\\\" \\\\\\\"location \\\\\\\\\\\\\\\"2808 2097.9\\\\\\\\\\\\\\\" orientation N\\\\\\\"\\\" vh /repo/hw/soc/pnr/RM_IHPSG13_2P_256x16_c2_bm_bist_bb.v nl \\\"\\\" pnl \\\"\\\" spef \\\"\\\" lib \\\"nom_typ_1p20V_25C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_2P_256x16_c2_bm_bist_typ_1p20V_25C.lib nom_slow_1p08V_125C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_2P_256x16_c2_bm_bist_slow_1p08V_125C.lib nom_fast_1p32V_m40C /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_2P_256x16_c2_bm_bist_fast_1p32V_m55C.lib\\\" spice \\\"\\\" sdf \\\"\\\" json_h None\""
set ::env(EXTRA_SPICE_MODELS) "/repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/cdl/RM_IHPSG13_1P_2048x64_c2_bm_bist.cdl /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/cdl/RM_IHPSG13_1P_1024x32_c2_bm_bist.cdl /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_sram/cdl/RM_IHPSG13_2P_256x16_c2_bm_bist.cdl"
set ::env(FALLBACK_SDC) /nix/store/ffl2vg3m80k0p74pyffnmai83fnv38mf-python3-3.13.9-env/lib/python3.13/site-packages/librelane/scripts/base.sdc
set ::env(PAD_GDS) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/gds/sg13g2_io.gds
set ::env(PAD_LEFS) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/lef/sg13g2_io.lef
set ::env(PAD_VERILOG_MODELS) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/verilog/sg13g2_io.v
set ::env(PAD_SPICE_MODELS) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/spice/sg13g2_io.spi
set ::env(PAD_CDLS) /repo/hw/soc/tools/pdk/ihp-sg13g2/libs.ref/sg13g2_io/cdl/sg13g2_io.cdl
set ::env(PAD_CORNER) sg13g2_Corner
set ::env(PAD_FILLERS) "sg13g2_Filler10000 sg13g2_Filler4000 sg13g2_Filler2000 sg13g2_Filler1000 sg13g2_Filler400 sg13g2_Filler200"
set ::env(PAD_SITE_NAME) sg13g2_ioSite
set ::env(PAD_CORNER_SITE_NAME) sg13g2_cornerSite
set ::env(PAD_BONDPAD_NAME) bondpad_70x70
set ::env(PAD_BONDPAD_WIDTH) 70
set ::env(PAD_BONDPAD_HEIGHT) 70
set ::env(PAD_BONDPAD_OFFSETS) "\"sg13g2_IOPad*\" \"5.0 -70.0\""
set ::env(PAD_EDGE_SPACING) 140
set ::env(PNR_CORNERS) "nom_typ_1p20V_25C nom_slow_1p08V_125C nom_fast_1p32V_m40C"
set ::env(SET_RC_VERBOSE) 0
set ::env(LAYERS_RC) "\"*\" \"Metal1 \\\"res 0.00854576 cap 1E-10\\\" Metal2 \\\"res 0.00253519 cap 0.000169121\\\" Metal3 \\\"res 0.00154329 cap 0.000182832\\\" Metal4 \\\"res 0.000631424 cap 0.000166454\\\" Metal5 \\\"res 0.000684051 cap 0.0000857431\\\"\""
set ::env(VIAS_R) "\"*\" \"Cont \\\"res 0.0022\\\" Via1 \\\"res 0.0020\\\" Via2 \\\"res 0.0020\\\" Via3 \\\"res 0.0020\\\" Via4 \\\"res 0.0020\\\" TopVia1 \\\"res 0.0004\\\" TopVia2 \\\"res 0.00022\\\"\""
set ::env(PDN_CONNECT_MACROS_TO_GRID) 1
set ::env(PDN_MACRO_CONNECTIONS) "\"u_ram\\\\.g_ram_2048x64_ecc\\\\.u_b\\\[0-3] VPWR VGND VDD! VSS!\" \"u_ram\\\\.g_ram_2048x64_ecc\\\\.u_b\\\[0-3] VPWR VGND VDDARRAY! VSS!\" \"u_eth\\\\.u_mac\\\\.(rx|tx)_fifo\\\\.fifo_inst\\\\.u_sram\\\\.g_bank\\\\\\\\\\\\\\\[\\\[0-7]\\\\\\\\\\\\]\\\\.u_mem VPWR VGND VDD! VSS!\" \"u_eth\\\\.u_mac\\\\.(rx|tx)_fifo\\\\.fifo_inst\\\\.u_sram\\\\.g_bank\\\\\\\\\\\\\\\[\\\[0-7]\\\\\\\\\\\\]\\\\.u_mem VPWR VGND VDDARRAY! VSS!\""
set ::env(PDN_ENABLE_GLOBAL_CONNECTIONS) 1
set ::env(PNR_SDC_FILE) /repo/hw/soc/sta/soc_interfaces_external_irq.sdc
set ::env(DEDUPLICATE_CORNERS) 0
set ::env(CURRENT_ODB) /repo/hw/soc/pnr/runs/cloud-mbist-closure/29-openroad-resizertimingpostcts/soc_top.odb
