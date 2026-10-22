# CDR v36/v37 loading comparison

The complete v37 waveforms reject both wider matched input/bias resistor trials. In the early case, 6um width gives C/D64/64 wrong-sign apertures versus3/30 in the matching v36 load12 parent;8um gives128/166. These are original output apertures, not new internal criteria. All four v37 native simulations complete without numerical diagnostics and retain passing device gates. Wider input conductance is not an accepted fix.

Compare actual frozen full captures for v36 load12 and v37 width6, both early and late. Restore each original1,002,247,291-byte waveform and exact modified composition. Reproduce every original120HBT envelope and all four complete sampler checks before observing native follower currents, actual resistor endpoint/base voltages, master/slave current steering, fixed aperture observations and headroom. Explicitly validate64/72 declared primitive parameter changes and reverse them to the identical original476-device contract. No new SPICE run, waveform truncation, clock shift, internal100mV acceptance criterion or fitted divider replaces original results.

The existing v35 late load16 follower observation reports strictly positive collector current and VBE above0.79V throughout active capture, with zero cutoff observations. It does not support a simple follower-off explanation; it also does not prove why the changed v37 input loading regresses. The new controlled comparison targets that uncertainty.

Actual pinned PDK generation39862564844 confirms the single-finger54um MOS bbox is[0,-0.18,0.98,54.18]um: height54.36um and top54.18um, violating the old generator's local top<50um planning bound. This bound is a placement guard, not a foundry rule. Candidate layout needs actual replanning and full DRC/LVS/fresh RC; do not simply mark these frozen-RC candidates integrated or waive the guard. All17 requested PCell parameter readbacks pass; this proves isolated cells only.

All work runs in GitHub Actions. Original rejected runs and source-bound diagnostics remain immutable. Full serial PHY, actual candidate layout, routed mainchip and final setup/hold are not complete.
