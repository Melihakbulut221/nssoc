# CDR v29: a physical collector-load and input-bias candidate

This is an unproven component experiment, not an accepted CDR, PCIe PHY or chip integration.

## Evidence and design choice

The complete v28 native captures still fail the original early0.3UI/37.5ps sample gate. Later0.6/0.9UI samples pass. The two unsafe nominal HBTs are C sampler clock selectors, with minimum VCE around0.38955/0.39142V against the original0.4V limit. The actual retime follower outputs remain conducting; measured common modes are approximately1.364/1.387V. Prior shrink-only data/hold changes and stronger input loading did not close all original gates. See the unchanged v24-v28 rejection and diagnostic receipts.

The new candidate changes six actual rppd PCells per sampler from the independently passed v28 geometry:

| Primitive | Width | Old length | New length |
| --- | --- | --- | --- |
| M_RP, M_RN, S_RP, S_RN collector loads |32um|2.12um|2.6um|
| BP, BN bias pull-ups |4um|2.4um|2.2um|

IP/IN remain4um by2.4um. Every HBT/MOS, mirror ratio, bleeder, connection, public pin and original primitive position is retained. There are still16HBT,9MOS,12resistors and17physical taps.

A first-order equal-width divider estimate changes the input weight from0.5 to2.2/(2.4+2.2), raising the common mode by roughly25mV for a1.36V source and2.5V supply. The corresponding differential reduction is about4.35 percent. The collector resistor length increases22.64 percent geometrically. These are design estimates only: native end corrections, base loading, transistor current, extracted capacitance and output RC can change the outcome. The hypothesis is that modestly higher input common mode and larger collector swing improve selector headroom and early threshold crossing. Increased RC delay, saturation, power or reduced input differential may instead reject the candidate. No improved waveform is claimed.

## Required proof

The new cloud workflow preserves the actual v28 leaf positions and public interface, compares all54 native primitive drawings, and requires exactly the six declared resistor changes plus48 unchanged drawings. It retains the original560 native DRC categories, unsimplified deep/flat54-device LVS, LEF and all twenty physical/reference faults. A separate native-geometry rejection checks accidental restoration of the old collector length.

A physical pass only permits replacement in the full476-device parent and fresh whole-parent RC/MIM capture/composition. Original full256-bit34.25ns loaded early/late cases, stopped-clock and disabled-VI faults,100mV margin,37.5ps clock-to-valid,30mV phase,50uA current, every transistor bound and every diagnostic gate must then rerun unchanged. This stage does not alter any external clock, source load, sampling instant, expected bit, voltage limit or acceptance threshold. Do not reuse v28 RC as new geometry proof.

All work and failures remain in hosted Actions/Releases. Mainchip detailed route39682593979, PLL39674830790 and TX39681742199/39681748051 remain independent live work.
