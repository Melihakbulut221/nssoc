# PLL first divider: per-HBT currents on the unchanged RHI120-C8 deck

Run41845446581 (`analysis/pll-divider-currents`) reran the preserved RHI120-C8 preparation deck (release421575365, archive SHA a7b33b07...) for the full original 1 us with the pinned runtime. Only the save list was rewritten: the public vectors, every terminal voltage of the 15 first-divide-by-two HBTs and 4 collector loads, and for the first time each HBT's Ic, Ib and Ie. Stimuli, loads, solver options, native OFF flags and duration are unchanged. Diagnosis only, no acceptance.

## Reproduction

- Feedback phase span in 0.9-1.0 us: 5.00278 ns (original capture 5.00271 ns).
- Feedback frequency in the same window: 104.23 MHz (original 104.15 MHz; the counting method differs, the phase span matches to 0.07 ps).
- 3201410 points to 1 us, the same as the original capture.

The deck therefore reproduces the original acquisition failure, so its currents describe the original circuit.

## What the currents show (late window)

- VCO clock: 8.590 GHz (58.75 ps half period), +-0.24 V differential. With the 100 MHz reference and an intended divide-by-80, the measured VCO/feedback ratio is 82.4, which is not an integer.
- In 0.98-1.0 us the first divider's slave output toggles 178 times in 170.5 clock periods: 162 periods have one transition and **8 periods (4.7%) have two**. Every double transition loses one count, which explains the non-integer ratio, and the loop cannot acquire on such a feedback signal.
- The divider's clock pairs (xd0387/0388 slave, xd0392/0393 master) see only +-84 to +-89 mV at their bases and +-57 to +-62 mV of effective Vbe split. The off-side current fraction has a median of 0.23 and a 95th percentile of 0.47 of the pair current, so the clock pairs never steer the 1.30-1.33 mA tails fully. The data pairs do switch fully (0.003-1.28 mA).
- Both tails keep Vce >= 0.433 V.

The handoff's observations (about +-88 mV conditioned clock, 38-49 mV effective VBE split in some events, 159 double transitions at 10 mV) are therefore confirmed with device currents. The conditioner attenuates the +-0.24 V VCO swing to about +-0.09 V. At that drive the latch's regeneration time is a large fraction of the 58 ps half period, and some cycles flip twice.

## Next measurement-driven change

Raise the clock drive at the divider clock pairs to well above +-100 mV of effective Vbe split (conditioner gain or load, or direct level-shifted VCO drive), or reduce the clock pairs' emitter-path resistance. Then rerun this deck to check for zero double transitions and an exact divide-by-80, before any closed-loop acceptance. The 8.59 GHz VCO frequency also has to be brought to 8 GHz by the loop once the divider counts correctly.

## Conditioner what-if (run41946612555)

The first-divider "conditioner" is a resistor network: a series rppd from the VCO output to each clock-pair base (XD0497/XD0498, 4 um x 3.6 um) and a pull-up from `div_avdd` (XD0488/XD0489, 1 um x 4 um). Each variant reruns the same deck to 0.6 us and is measured on the same 0.5-0.6 us window; only the listed resistor widths change, and every extracted wire is kept.

| Variant | Change | VCO / feedback | Feedback | Double transitions | Clock-pair base swing | Off-side clock-pair Ic min |
|---|---|---:|---:|---:|---:|---:|
| original | none | **90.46** | 96.18 MHz | 16 / 869 periods | -91..+86 mV | 0.122 / 0.149 mA |
| cond_series4 | XD0497/0498 4 -> 16 um | **79.86** | 108.14 MHz | 1 / 863 | -162..+157 mV | 0.013 / 0.018 mA |
| cond_lowz4 | series 4 -> 16 um, pull-ups 1 -> 4 um | **80.01** | 109.15 MHz | 1 / 872 | -138..+135 mV | 0.028 / 0.037 mA |

In the original, the divider loses so many counts that the feedback (96 MHz) reads below the 100 MHz reference while the VCO is already at 8.70 GHz, above its 8.0 GHz target. The loop therefore sees a frequency error of the wrong sign and keeps the VCO high, which explains the acquisition failure. With the series resistance cut to a quarter, the clock pairs steer fully, the divider counts by 80, and the feedback reads above the reference, so the loop now gets the correct error sign. Neither variant is locked at 0.6 us: the VCO is still at 8.64-8.73 GHz. The original 0.9-1.0 us acquisition gates (100 ppm, 50 ps) remain unevaluated for these variants. A 1 us variant run exceeds one hosted job (0.892 us in 5h40m), so it needs the existing continuation method or a larger runner.

Recommended layout candidate: XD0497/XD0498 at 16 um width (cond_series4), with fresh DRC/LVS/RC and the full 1 us acquisition bench.

## Exploratory lock trend (run41973451788)

This run is not an acceptance measurement. The maximum step was relaxed from 0.3125 ps to 1 ps (about 116 points per 8.6 GHz period) so that 1.5 us fits in one hosted job. Both conditioner variants keep the corrected divider for the whole run (ratio 79.72 / 79.82; one double transition in about 870 periods in 1.4-1.5 us). The loop still does not acquire:

- cond_series4: in 50 ns windows from 0.1 to 1.5 us the VCO wanders between 8.52 and 8.85 GHz, the feedback stays at 106-111 MHz (always above the 100 MHz reference), and vctrl moves between 0.60 and 0.75 V. Lower vctrl corresponds to higher frequency (8.85 GHz at 0.60 V, 8.52 GHz at 0.75 V).
- cond_lowz4: VCO 8.57-8.88 GHz, vctrl 0.60-0.74 V, no trend toward 8 GHz.
- The vctrl oscillation repeats roughly every 100-150 ns, close to the 1/(feedback - reference) beat of about 118 ns. In 1.48-1.50 us UP is high 43% of the time and raises vctrl at about 40 V/us; DOWN is seen only while UP is also high.

With the divider fixed, the next blocker is frequency acquisition in the PFD, charge pump and filter. Over each beat, vctrl's net movement is about zero, and it never leaves the 0.60-0.75 V band, although reaching 8 GHz needs vctrl near or above 1 V by the observed tuning slope. The next measurements are UP/DOWN pulse widths and overlap over full beat cycles, charge-pump output current against vctrl, and the reachable vctrl range.

## Why the loop does not acquire (run41990447679)

Same exploratory settings, cond_series4, with UP/DOWN occupancy per 50 ns window:

- UP and DOWN are both high for 21-31% of every window. In the 1.48-1.50 us detail, each overlap pulse lasts about 2.58 ns of the 10 ns reference period, far longer than a PFD reset pulse should.
- vctrl rises at +40.5 V/us while only UP is high and falls at -25.5 V/us while both are high. With equal integration capacitance, that means the DOWN sink is about 1.63 times the UP source.
- Across the run UP-only (about 16%) exceeds DOWN-only (about 8%), so the PFD does ask for a higher vctrl (lower frequency). The net DOWN current during the long overlap cancels that request, so vctrl stays near 0.6-0.75 V.

Charge-pump bias: the reference diode XD0185 (2/2 um NMOS) mirrors through XD0186 into the PMOS diode XD0374 (8/2 um). The UP source XD0375 is 6.4/2 um (0.8x), while the DOWN sink XD0188 is 2/2 um (1.0x). The design is therefore DOWN-heavy by 25% before any Vds effect; 1.63x is measured. The 2.58 ns overlap points to a slow PFD reset path.

Run42015897890 what-ifs `series4_cp8` (XD0375 8 um, nominal 1:1) and `series4_cpmatch` (XD0375 10.4 um, measured ratio) test whether matched pump currents let the loop pull the VCO toward 8 GHz. The reset delay is the next item if they do not.
