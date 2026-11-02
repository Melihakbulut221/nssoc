# Balanced C/D input-bias electrical trial

The first provisional pull-up-only trial41458294059 failed the unchanged loaded gates. It raised critical C/D clock-selector Vce by44-53mV but only C devices passed0.4V; D remained0.39314/0.39609V. C maximum clock-to-valid degraded from51.09ps to118.91ps; phase14.185mV and VI42.660uA still failed. Original complete1,045,823,299byte raw waves are preserved. That trial is not a physical or electrical accepted candidate.

The next provisional circuit experiment starts from the authenticated original collector Via2 parent freshRC41439516945, not the failed trial's modified model. Native full500 mapping41450661063 fixes these exact targets:
- SD_UP/UN (182/183) and SC_UP/UN (220/221): L1.8um ->1.75um, W8um unchanged.
- SD_DP/DN (184/185) and SC_DP/DN (222/223): L5um ->6um, W4um unchanged.

Rationale is an explicitly approximate first-order sheet-resistance calculation, not a PDK resistance measurement: parent normalized shunt resistance is1/(8/1.8+4/5)=0.190677966 sheet-resistance units; trial is1/(8/1.75+4/6)=0.190909091, +0.1212%. The unloaded supply-divider ratio rises from0.847457627 to0.872727273. This attempts to raise input common-mode while retaining differential load resistance/gain, unlike the earlier pull-up-only change that reduced the normalized load resistance by14.49%. Contact resistance, bias dependence, capacitance and full nonlinear operation can invalidate this estimate; the real frozen ngspice simulation decides. External supplies, bias sources,clock,stimulus and acceptance limits are not altered.

Only these eight primitive length parameters change. The helper authenticates complete original mapping, original full parent RC/runtime, exact native IDs/terminals/parameters, entire model reversal and complete contract reversal; the other492 devices and every parent wire R/C card remain unchanged. Source controls retain all original29 definitions/5blocks/9sourcefiles/13admission refusals plus six card refusals and both real resistor parameter shapes. Actual preparation still requires all13binding refusals and2unit-equivalence controls.

All output provenance marks PROVISIONAL_DEVICE_PARAMETER_TRIAL_WITH_FIXED_PARENT_INTERCONNECT_RC. No modified resistor layout, new extraction, full PHY or final timing acceptance is claimed. Even a numerical pass requires actual schematic/GDS regeneration, full DRC/LVS, canonical mapping, freshRC and unchanged loaded tests. Full waves and failures are preserved in a separately reserved cloud release. Work is cloud-only.
