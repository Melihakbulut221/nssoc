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

## Matched pump currents (run42015897890)

Both variants keep the conditioner fix and change only the UP mirror XD0375. Settings are exploratory, as above (1.5 us, 1 ps maximum step).

| Variant | XD0375 | Late VCO | Late feedback | VCO / feedback | Double transitions (late window) | vctrl band |
|---|---:|---:|---:|---:|---:|---:|
| series4_cp8 | 8 um | 8.39 GHz | about 100 MHz | 83.39 | 29 / 839 | 0.73-0.93 V |
| series4_cpmatch | 10.4 um | 8.40 GHz | 100.3 MHz | 83.72 | 89 / 839 | 0.73-0.93 V |

With the pump matched, the loop does move: vctrl now rises to 0.80-0.93 V, and the feedback averages the 100 MHz reference (phase span 2.41 ns, down from 5.0 ns). The VCO nevertheless stays at 8.4 GHz, because the divider again loses counts and the ratio is 83.7 instead of 80. The loop has pulled the feedback onto the reference by locking to the wrong ratio.

## VCO swing collapses where 8 GHz is reached

From the 1.48-1.50 us samples of series4_cpmatch, per VCO period:

- The VCO is a three-stage CML ring with resistor loads (XD0480-0482, XD0490-0492) and MIM loading on every ring node (XD0572/0575/0576/0578/0584/0593). vctrl drives the gates of four PMOS sources (XD0320/0333/0334/0335). Their current feeds the diode XD0408 that biases the three ring tails XD0402/0404/0406. The ring is therefore tuned by tail current alone.
- The VCO differential peak-to-peak correlates with vctrl at -0.80. It is 0.37-0.42 V at vctrl 0.73-0.79 V (period 114-118 ps, 8.5-8.8 GHz). It falls to 0.12-0.14 V at vctrl 0.88-0.93 V (period 121-131 ps, 7.6-8.3 GHz).
- Every double transition in the window falls in a cycle with collapsed swing. In those cycles the mean clock peak is +0.070/-0.063 V, against +0.156/-0.147 V in normal cycles.
- vctrl swings by about 0.2 V within one 10 ns reference period, because the control node has only the 8 x 8 um MIM XD0574 to avss, in parallel with the resistive bias divider XD0567 (1 x 120 um rppd from vco_avdd) and XD0568 (1 x 47 um rppd to avss), and no series-RC integrating branch. Each UP pulse therefore pushes the ring briefly into the low-swing region.

The 8 GHz target therefore lies in the region where reducing tail current both lowers the frequency and removes the swing that the divider needs. Pump matching cannot fix this. The ring has to reach 8 GHz with full tail current, which is a VCO centre-frequency change. Run42044215569 tests this on the same deck by scaling only the six ring-node MIMs. `cpmatch_mim105` and `cp8_mim105` scale each side by 1.055 (+11% area), and `cpmatch_mim109` by 1.09 (+19%). Every extracted wire is kept, so these remain what-ifs rather than layouts.

## Ring-node MIM scaling (run42044215569)

| Variant | Change on top of the conditioner fix | VCO (late) | Feedback (late) | VCO / feedback | Double transitions | vctrl band |
|---|---|---:|---:|---:|---:|---:|
| cp8_mim105 | XD0375 8 um, six ring MIMs x1.055 per side (+11% area) | 8.50 GHz | 106.5 MHz | 79.80 | 16 / 849 | 0.65-0.76 V |
| cpmatch_mim109 | XD0375 10.4 um, ring MIMs x1.09 per side (+19% area) | 8.68 GHz | 106.5 MHz | 81.50 | 19 / 762 | 0.60-0.71 V |
| cpmatch_mim105 | XD0375 10.4 um, ring MIMs x1.055 | job failed after 78 min; its log is no longer retrievable (BlobNotFound) | | | | |

The patch was applied as intended (`variant-patch.json`). The six ring-node MIMs therefore carry only a small share of the ring-node capacitance: +11% MIM area lowers the VCO by about 1-2% at the same vctrl. With the divider correct again (ratio 79.8), the feedback sits at about 106 MHz, above the 100 MHz reference. vctrl nonetheless stays in a narrow band around 0.7 V instead of rising to slow the VCO.

That points to the loop filter. The control node has the resistive bias XD0567 (to vco_avdd) and XD0568 (to avss) and the 8 x 8 um MIM XD0574, with no integrating branch. The divider holds vctrl near its own level, and the charge pump can only move vctrl by its current times the parallel bias resistance. The loop therefore has finite DC gain and cannot pull a free-running VCO of about 8.5 GHz to 8 GHz.

Run42075871975 tests that directly with an exploratory, non-layout what-if on top of `series4_cp8`:

- The bias resistors are made ten times longer.
- An ideal series RC is added from vctrl to avss: 2.1 kOhm + 30 pF (`cp8_int2k1`) or 1 kOhm + 60 pF (`cp8_int1k`).

If the loop then acquires 8 GHz, the PLL needs a type-II loop filter in layout. Without one, no VCO or pump trim will make it acquire.

## Integrating loop filter (run42075871975, exploratory)

Both variants start from `series4_cp8`. The bias resistors XD0567/XD0568 are ten times longer, and an ideal series RC runs from vctrl to avss.

| Variant | VCO/feedback (late) | Double transitions | vctrl over 0.1-1.5 us | VCO over 0.1-1.5 us |
|---|---:|---:|---|---|
| cp8_int2k1 (2.1 kOhm + 30 pF) | 80.03 | 1 / 884 | 0.12 -> 0.61 V, rising steadily | 8.98 -> 9.32 -> 8.86 GHz, falling |
| cp8_int1k (1 kOhm + 60 pF) | 80.00 | 1 / 917 | 0.07 -> 0.44 V, rising steadily | 8.82 -> 9.33 -> 9.19 GHz, falling |

With an integrating branch, the loop pulls in the right direction and keeps doing so. vctrl climbs at about 0.35-0.4 V/us, and the VCO falls toward the target while the divider counts exactly by 80. The loop was not acquiring before because the resistive-bias filter had finite DC gain.

These runs start with the integrating capacitor at 0 V, so vctrl begins far from the operating point. Within the exploratory 1.5 us window the VCO reaches 8.86 GHz, not 8 GHz.

Run42106436994 (`cp8_int2k1_ic080`, `cp8_int2k1_ic088`) starts the same filter with the integrating node and vctrl at 0.80 / 0.88 V. Those runs test lock at 8 GHz, and whether the VCO swing collapse seen near vctrl 0.9 V (series4_cpmatch) then breaks the divider.

### Started near the operating point (run42106436994)

| Variant | Initial vctrl and integrator | Settled vctrl | Feedback (late) | VCO (late) | VCO / feedback | Double transitions |
|---|---:|---:|---:|---:|---:|---:|
| cp8_int2k1_ic080 | 0.80 V | 0.84-0.88 V | 100.6 MHz | 8.33 GHz | 82.86 | 61 / 832 |
| cp8_int2k1_ic088 | 0.88 V | 0.84-0.88 V | 98.3 MHz | 8.30 GHz | 84.38 | 38 / 829 |

The integrating loop settles quickly. vctrl stays within 0.84-0.88 V from 0.1 us onward, and the feedback averages the 100 MHz reference with a phase span of 3.0 ns in the 0.80 V case.

The VCO then sits at 8.30 GHz, not 8.0 GHz. At that vctrl the current-tuned ring's swing has collapsed (see "VCO swing collapses where 8 GHz is reached"). The first divider double-counts in 5-7% of periods, the ratio is 82.9-84.4, and the loop locks the feedback to the reference at the wrong VCO frequency.

The two PLL defects are therefore independent, and both are now demonstrated:

1. **Loop filter.** The resistive-bias control node has finite DC gain. An integrating (type-II) filter is needed, shown by `cp8_int2k1`/`cp8_int1k` pulling steadily in the right direction.
2. **VCO tuning.** The ring is tuned only by tail current, so it cannot reach 8 GHz with the swing the first divider needs. The VCO needs a tuning mechanism that keeps its swing near 8 GHz, such as load or varactor tuning or a lower free-running centre with a fixed tail current. Alternatively, the first divider must count correctly at the reduced swing.

Neither can be reached by resizing devices in the extracted deck. Both are schematic and layout changes, followed by fresh DRC, LVS and extraction and the full 1 us acquisition bench.

## Ring loads with the integrating filter: lock at 8 GHz (run42160789512, exploratory)

These runs build on `cp8_int2k1` (conditioner fix, XD0375 8 um, bias tenfold weaker, ideal 2.1 kOhm + 30 pF integrator). The six ring load resistors XD0480-0482 and XD0490-0492 (8 um wide rppd) are lengthened. The integrator and vctrl start at 0.70 V.

| Variant | Ring load length | VCO (1.4-1.5 us) | Feedback | VCO / feedback | Phase span (late) | Double transitions | vctrl (late) |
|---|---:|---:|---:|---:|---:|---:|---:|
| int2k1_rl112 | 4.93 um (x1.12) | **7.97 GHz** | **99.68 MHz** | **79.97** | **0.29 ns** | 1 / 797 | 0.61-0.65 V |
| int2k1_rl125 | 5.5 um (x1.25) | 7.28 GHz | 91.07 MHz | 79.91 | 8.98 ns | 1 / 727 | 0.61-0.74 V |

With x1.12 loads the loop locks. The VCO settles from 7.7 GHz through an 8.12 GHz overshoot to 7.97-8.05 GHz, and the feedback converges to the 100 MHz reference with a residual phase span of 0.29 ns. The divider counts exactly by 80 because 8 GHz is now reached at vctrl about 0.62 V, where the ring keeps its full swing. With x1.25 loads the ring is too slow (7.3 GHz) for the available range.

This is the first PLL configuration in this work that acquires 8 GHz. It is still exploratory:

- the 1 ps maximum step, not the acceptance 0.3125 ps;
- an ideal R and C in the filter;
- an initial condition on the filter.

Run42180076257 removes the initial condition (cold start). One variant weakens the bias divider threefold, so it still precharges the integrator. The other uses the tenfold-weaker divider.

Candidate design change for layout:

- XD0497/XD0498 at 16 um;
- XD0375 at 8 um;
- ring loads at 4.93 um length;
- a type-II loop filter with series R and C to replace the bias-only control node, in silicon as an rppd plus MIM.

That is followed by fresh DRC, LVS and extraction and the 1 us acquisition bench.
