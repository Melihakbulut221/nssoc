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
