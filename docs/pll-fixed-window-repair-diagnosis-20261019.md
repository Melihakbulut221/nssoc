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
