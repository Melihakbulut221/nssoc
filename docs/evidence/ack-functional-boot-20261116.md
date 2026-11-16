# New ACK mapped functional boot and MBIST observer qualification

The source-bound supplementary functional boot passed in [run 43814779296](https://github.com/Melihakbulut221/nssoc/actions/runs/43814779296), commit 506367db9accba350150ccd391294bef0cb025c3. This is not native PDK model equivalence, SDF, routed timing, full serial PHY acceptance or production signoff.

## Authenticated result

Artifact 14205080681 (`ack-delta-functional-boot-43814779296`), SHA256 a210e2f9fcee80c5d8a16278e728d4d7c18620e230710d9e3aee6d51b4401ea8, was downloaded into RAM and its complete digest verified. Both included boot logs matched their report hashes. Run log SHA256 4effd9e8db143b13be04681e07259ca2661bcca6e2930d5f8b9517dd5b3b34ce.

Mapped JSON e6b2b44049da71b74e9dd2adb30a551f7bb0883072f21d83e9bac93b70bc2ecd and netlist 5b4f45a0919975a9a5da7d9dd11f4c59349dc17b361fa32282bf170a2db00165 came from authenticated recovery run43812773466. The inventory contains four system1P SRAM macros and sixteen Ethernet2P macros. No older-map boot result is reused.

Observed results:

- LOGICROM_GL: 2,267,527 cycles; 28 checks; zero failures; exit code0; magic600dc0de.
- Watchdog1/0/0, flash violations0, UART pass1, framing errors0.
- PCIe packet-async idle: PASS, 5,668,736 samples.
- System/Ethernet MBIST: PASS, busy1,310,691 cycles, completion cycle1,310,724, Ethernet done3.
- Original four-million-cycle bound, firmware/reset/watchdog/MBIST checks retained.
- Compile25.275s; simulation3302.513s. Source and read-only observer unchanged.

## Monitor correction promoted

Only the testbench observer is changed: its two integer output ports are explicitly declared signed32-bit registers, and its unknown-status check uses equivalent per-bit four-state comparisons. This addresses CVC integer-output truncation and its reduction-expression handling without altering the DUT, initialization, SRAM or acceptance conditions.

Original monitor SHA256 c117d03640b2cc18be2390e050f8c7f85fdf14c694738355c6fbcc42f9650a0d is preserved as `hw/soc/tb/mapped_mbist_boot_monitor_original.v`. Corrected monitor SHA256 6d6b7c1aa116ba428cc7d7401cecec23c3ee66645254dd7550a81460ffbff7df.

`scripts/diagnose_mbist_monitor_engines.py` verifies the exact transformation and compares Icarus and four CVC modes. All five corrected traces match the210-row original-Icarus reference. Eight failure controls detect failed SRAM, unknown status, dropped completion and absent busy phase. All16,384 four-state combinations of seven status bits match the unknown predicate in all five modes.

Reproduce using workflow_dispatch on the immutable tested branch `codex/ack-delta-functional-boot` at the above commit. Its workflow builds pinned CVC1c5e043ec33ef6f1fdbf38565501c944893a83cf, installs Icarus and runs the monitor qualifier plus cell/SRAM gates before boot. The experiment workflow is not merged into the integration branch.

## Limits

CVC uses derived zero-delay standard cells with NBA outputs (SHA25645b335d8e543ab7b70afa0d269e6b59b08fd85227420dfe20f4255862c4c7a34). Native-library deep-clock composition differs; `native_model_equivalent=false`. These directed qualifications do not prove arbitrary simultaneous-edge equivalence. Native gate boot, SDF and physical signoff remain open. PCIe traffic here is an idle packet-interface check, not Gen3x4 serial interoperability.
