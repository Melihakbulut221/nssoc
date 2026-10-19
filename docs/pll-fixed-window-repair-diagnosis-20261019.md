# Diagnose original PLL acquisition failure before another circuit change

The original800–900ns100ppm gate still fails. Completed C9 andC8 captures
reported132.847 and134.051ppm, respectively. C8 at half timestep reports
135.380ppm. All three pass the separate900–1000ns gate; that does not close
the earlier failure. No measurement interval or criterion is shifted.

The9um→8um capacitor change did not improve this observation, and it also
changed some actual wire capacitances. It does not justify another blind
capacitor reduction. The half-step capture preserves34native vectors for the
complete1us/6,401,211rows; it cannot prove all845devices safe.

The cloud-only diagnostic restores that exact capture and model, reproduces
the complete original acquisition and feedback-cycle analyses and retains the
original failure. It then reports each actual feedback cycle's differential
clock periods, observed VCTRL ripple/increments partitioned by UP/DOWN states,
fixed-threshold PFD internal/output crossings, actual top-level passive/source
cards and native control-node capacitance inventory. It enumerates missing
terminal-voltage probes for full-device validation.

UP/DOWN duty and VCTRL increments are observations, not pump current or charge.
Mutual capacitances are not grounded; a resistor-connectivity inventory is not
an effective loop RC model. No fitted target, changed transient, new acceptance
window or signoff claim is introduced. Use actual results to select the next
physical pump/filter/PFD repair and then rerun unchanged full native gates.


## Exact source-byte repair after cloud preflight rejection

Run [39278718492](https://github.com/Melihakbulut221/nssoc/actions/runs/39278718492) stopped before analysis at the baseline SHA256 guard. Its failure and published FAIL_MISSING_REPORT remain retained. The recorded baseline hash was for the immutable source plus one extra final LF. The actual baseline is unchanged from commit a88f83134de3c47b396c86c39f5c7edd3caf40e4.

The manifest now pins the actual baseline bytes. Removing the extra final LF from the candidate makes it exactly the declared transformation of that baseline. No Python statements, native model, acquisition windows, numerical thresholds or original rejection were changed. The cloud retry must pass the same exact source guard, reproduce the original capture and then perform the diagnostic review. This correction is not PLL acceptance.


## Top-level deck parser correction

Source inspection identified a second diagnostic-only error before the retry ran: `review_cloud_pll_loop.records` requires one `.subckt`/`.ends` model and accepts only X/R/C cards. It cannot parse the native test deck, which has a SPICE title, sources and a control section. The new helper uses a distinct test-deck lexical reader that joins continuation cards and excludes control commands. The strict native model parser remains unchanged. A cloud preflight checks source/instance cards, continuation handling and four malformed-deck rejections before restoring the large capture. These checks do not change any analog analysis or acceptance criterion.
