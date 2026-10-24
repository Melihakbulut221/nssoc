# XOR collector v15: actual loaded waveform test
The new physical geometry passed560-category native DRC, deep/flat484-device LVS and original physical fault tests.
All four fresh extraction stages passed. Actual MIM-aware capture39318436586 measured17834R/12805C and11MIM devices.
Validation39319103832 passed all13wire+9MIM raw-audit fault controls and19composition controls.
The final deck includes each of484native devices exactly once, preserving every raw wire R/C token and exact native reference planes.

Next: nominal early/late cases and actual clock-stopped/VI-bias-off controls.
The unchanged test uses256bits,34.25ns,0.3125ps maximum step and all1107saved vectors.
Sampler150fF and XOR50fF loads remain. Original100mV/37.5ps sampler, phase/current and116HBT/46MOS voltage-current gates are unchanged.
This is an externally clocked8GHz diagnostic, not a recovered-clock CDR or full PCIePHY acceptance.
The source-contact-v14 failed waveforms remain retained as failures; new geometry must pass its own tests.
TX39308903140 and mainchip39293720171 remain independent live runs. All CAD and artifacts are cloud-only.
