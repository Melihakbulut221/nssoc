# TX actual data loading and rejected trunk widening — 2026-10-19

## Full-wave result

[Native trunk256 run39226121734](https://github.com/Melihakbulut221/nssoc/actions/runs/39226121734) is terminal. Nominal returned0 after14618.29s, retained the original full256bits/34ns/three sample phases and complete capture, and reported no simulator diagnostics. Original electrical gates REJECT it:140wrong/164below100mV output samples,24HBT failures. All512MOS bounds pass. This is not an infrastructure failure. Its injected swapped-leaf control was detected independently.

The layout change had lowered the measured passive return resistance, but it did not reduce the output error counts. Final-stage interface wrong-sign samples1152→1150 while low samples2207→2215; level4 andlevel8 violation counts are unchanged. Therefore further identical return-trunk widening is not the selected next repair. No successful waveform or fullPHY acceptance is claimed.

## Actual connected data networks

[Read-only native network run39257226392](https://github.com/Melihakbulut221/nssoc/actions/runs/39257226392) passed its independent passive-network controls, restored the immutable model and contract, and bound all124data legs/372actual HBT bases. The60intermacro legs each have one actual native output-series rppd boundary leading to six upstream collectors. The64external data legs retain their original physical input pins. No device or R/C value was modified.

The table reports each pair's measured wire capacitance interval and metal-only source-terminal-to-base effective resistance interval. These are actual connected passive networks with KCL residual checks. They exclude nonlinear resistor resistance and intrinsic/body/RF device capacitances. Coupling capacitance is retained explicitly in the full report; summing incident capacitance is not an effective switched load or a delay estimate.

| Data pair | Incident wire C per leg(fF) | Metal pair R(ohm) | Original minimum signed margin(V) |
|---|---:|---:|---:|
| p8_0 | 522.272–535.509 | 33.865627–34.392666 | 0.083550 |
| p8_1 | 230.355–243.540 | 20.239647–20.766616 | 0.228512 |
| p8_2 | 362.787–375.331 | 26.029627–26.556666 | 0.153984 |
| p8_3 | 400.470–413.654 | 28.339627–28.866666 | 0.139885 |
| p8_4 | 422.373–432.234 | 29.025527–29.552466 | 0.127545 |
| p8_5 | 362.476–372.430 | 26.073527–26.600466 | 0.155255 |
| p8_6 | 247.450–257.145 | 20.925507–21.452476 | 0.218756 |
| p8_7 | 535.782–545.737 | 34.305527–34.832466 | 0.077494 |
| p4_3 | 289.979–299.997 | 23.215700–23.742669 | -0.146765 |

The weakest p8_0/p8_7 legs have substantially more wire loading than p8_1/p8_6, while the same upstream collector branches retain about84.07/91.22fF. This correlation and the separately measured small clock-wire edge brackets narrow the next repair to data routing/drive, but are not causal proof or electrical closure.

## Next physical repair boundary

Inspect a data-path-aware placement/route candidate against the existing fast-stage placement. Current physical rows moved only a,b,p4 nodes toward the final stage; the p8 nodes retain their original subtree rows. Reduce the long p8_0/p8_7 connections while checking every newly lengthened p16 connection and retaining all native body/rail/port geometry checks. A global or multi-column replan may be needed: merely moving p8 nodes can transfer the load problem to p16 and overfill existing routing channels. Do not blindly shrink the600um child row pitch; the generator checks actual child height.

If placement cannot meet the original full-wave margin at all interfaces, qualify a transistor/resistor drive redesign with actual measured loads and headroom. Preserve the full-chip HBT emitter budget and unchanged0.4V minimumVCE; increasing drive or lowering clock commonmode without checking the other stacked devices is not a completed repair. Any changed macro/placement requires new native DRC, deep/flat LVS, extracted RC and all original nominal/fault/PVT waveform gates. Do not reuse an old extracted model for changed GDS.

Full serialPHY, recovered PLL/CDR, four lanes, mainchip integration and final setup/hold remain OPEN. Mainchip39-buffer route39243328773 is a separate live run; retain it. All executions/artifacts are cloud-only and the local workspace remains empty.
