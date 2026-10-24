set ::nssoc_alu_geometry_definitions_only 1
source {/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/pnr/alu_physical_geometry.tcl}
read_lef {/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/npu-eco-physical-runner-20261006/bundle01/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef}
read_lef {/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/npu-eco-physical-runner-20261006/bundle01/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_stdcell.lef}
read_lef {/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/npu-eco-physical-runner-20261006/bundle01/pdk/ihp-sg13g2/libs.ref/sg13g2_io/lef/sg13g2_io.lef}
read_lef {/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/npu-eco-physical-runner-20261006/bundle01/inputs/hw/soc/out/sram-closure-20260926/repaired-macro-abstracts-v3/SP6TSRAM512x64-valid/SP6TSRAM512x64.lef}
read_lef {/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/npu-eco-physical-runner-20261006/bundle01/inputs/hw/soc/out/sram-closure-20260926/repaired-macro-abstracts-v3/DP8TSRAMDP256x16-valid/DP8TSRAMDP256x16.lef}
read_def {/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/npu-eco-physical-runner-20261006/bundle01/inputs/hw/soc/out/pipeline-timing-checkpointed-20260929/attempt3/chunk-010/01-openroad-resizertimingpostgrt/soc_top.def}
nssoc_alu_geometry {/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/npu-eco-physical-runner-20261006/template-control06/source}
exit
