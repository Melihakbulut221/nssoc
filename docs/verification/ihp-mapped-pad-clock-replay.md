# Digital pad replay with the mapped Ibex candidate

The directed test elaborated the generated nssoc_chip with the actual flattened candidate soc_top (SHA-256 47d85b8fb3517cebd962622e1c97c415d21a91a2835d6d5abd227b2d4f286605), the status serializer, native IHP I/O and standard cells, and both native SRAM models. The wrapper has SHA-256 a7f935e1536f632ad72de358b453db0fba449cbd83864ead496776636f9c5d58. The PDK is c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c. With MODEL_ROOT pointing at its libs.ref directory and SUITE at the OSS CAD Suite bin directory, replay with Bash:

```bash
"$SUITE/iverilog" -g2012 -s tb -o mapped.vvp \
  hw/soc/tb/tb_chip_mapped_gmii_pad.v "$WRAPPER" hw/soc/rtl/chip/soc_status_serial.v "$MAPPED_SOC" \
  "$MODEL_ROOT"/sg13g2_stdcell/verilog/sg13g2_stdcell.v "$MODEL_ROOT"/sg13g2_io/verilog/sg13g2_io.v \
  "$MODEL_ROOT"/sg13g2_sram/verilog/{RM_IHPSG13_2P_256x16_c2_bm_bist,RM_IHPSG13_1P_2048x64_c2_bm_bist,RM_IHPSG13_1P_core_behavioral_bm_bist,RM_IHPSG13_2P_core_behavioral_bm_bist_ideal}.v &&
"$SUITE/vvp" mapped.vvp
```

Observed: `PASS mapped GMII TX clock pad loop and reset input`, finish at 40 ns. Four directed observations compare the input at the mapped core, its forwarded GMII clock output, the pad output, and the reset input at the core. Scope is digital connectivity. Icarus warned about unsupported edge-sensitive ifnone timing paths. Reset sequencing, Ethernet traffic, pad timing, analog behavior and package performance remain open.

## Physical runs checked on 2026-11-26

Both matched float-derate runs stopped in OpenROAD.STAMidPNR at the first fast-corner min.rpt after global placement. The candidate step reported 3 GiB peak RSS, the control 6 GiB. The 16 GiB cgroup recorded additional OOM kills during this window. No extracted slack or detailed route came from either attempt. Their separate pre-step-22 checkpoints allow sequential resumption with the same SDC and report settings.

The earlier first-detail soc_top native LVS wrapper returned 124 at its 1200-second bound. The required report was absent, and make check-native-lvs rejected it. The underlying KLayout extraction process was still alive after the wrapper returned. A second gate invocation is queued against that same process's final database. The new candidate has no routed stream at this checkpoint.
