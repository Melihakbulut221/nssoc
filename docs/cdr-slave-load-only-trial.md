# Isolated slave collector-load experiment

This experiment completes the missing load-only corner of the same original collector Via2 fresh-RC41439516945 comparison. It is a provisional parameter experiment, not a physically accepted PHY.

## Evidence and hypothesis

Original36um MOS/L2.6um collector parent loaded41441047354 produced phase14.325205mV,VI43.051234uA and A/B/C/D max clock-to-valid45.78125/41.71875/51.09375/54.53125ps. C/D wrong-sign counts were2/34.
Combined48um MOS/L1.9um trial41501239838 removed wrong signs but C late hold-margin failures capped the clock-to-valid metric at118.90625ps; phase12.974092mV andVI39.691842uA still failed. The complete per-bit stage diagnosis41508059395 is preserved in root checkpointv322.
Current-only48um/L2.6um trial41514109475 actually completed its34.25ns transient in894.319366s, but C/D wrong signs worsened to8/46, phase15.796080mV stayed below30mV,VI46.852669uA stayed below50uA and all four sampler delays exceeded37.5ps. HBT71(SB_S_LN) added a0.390572V active Vce failure. Its width-only change must not be promoted to layout.

The isolated load change may reduce output charging delay and improve collector headroom without increased tail current or its diffusion capacitance. It can also reduce differential amplitude. Neither a resistor ratio nor improved transition polarity proves success. The full unchanged measurement gates decide.

## Exact change and retained checks

From original physical parent41439516945, change only8 rppd slave collector lengths2.6um to1.9um,W32um unchanged: native205/202(SA),194/191(SB),214/212(SC),176/175(SD). All MOS widths36um and associated original diffusion geometry remain unchanged. All other492devices, wire R/C, MIM, master loads, bias, clocks, stimuli and full loaded500-device topology remain the authenticated parent.

Targets come from the complete500-device mapping41450661063 and are checked again against the restored actual mapping, full terminal identities and actual card parameters. Exact whole-model and whole-contract reversal prove only these8 resistor length tokens change. The original geometry binder is called directly; the48um MOS adapter is unused and excluded from the active source closure. All original29 numerical definitions,5 executable blocks,9 source files,13 admission refusals,14 malformed primitive-card refusals and actual13 binding refusals plus2 equivalent-unit tests remain.

Full transient stimulus,34.25ns duration,150fF sampler loads,100mV margin,37.5ps delay,30mV phase,50uA VI and device voltage/current limits are unchanged. Runtime, parent release authentication, complete native publication and exact-source independent release reservation are unchanged. Controls execute first on GitHub; only successful exact-source controls admit a new explicitly dispatched native run.

No matching resistor geometry or fresh extraction exists for this trial. Even a full electrical pass needs new schematic/GDS, DRC, deep and flat LVS, fresh RC/MIM, repeated loaded waves, closed-loop CDR/PLL and full Gen3x4/mainchip/timing evidence. Preserve failures. All native work and evidence remain in the cloud.
