# Physical path and supply diagnosis

This cloud-only read-only experiment compares already completed width2 (41306148937), width8 (41310192873) and A/C buffer drive (41325168813) native waves. All three circuits remain rejected. It launches no simulator and changes no device, net, route, model, RC or acceptance threshold.

The original62-control waveform reader at9c5843a973b5a0175d137af0780ae1b5aca46968 is preserved byte-for-byte. Its functions execute with separately bound producer metadata and output directories. Every existing archive member is authenticated and every original data/device/phase/V-I measurement is reproduced before additional diagnostics. Every run, source, release and asset pin is explicit. The original reader module remains unchanged.

Actual physical nodes, rather than inferred equal-voltage logical nets, are measured along:
sampler collectors; series-resistor input and output; shunt-resistor top; buffer bases and collectors; and a physical downstream receiver base. Native cluster/net equality is checked for every interconnect comparison. Every downstream receiver identity is reported. The four paths are A,C,D-to-X and D-to-Y.

For each original expected bit, the report preserves signed samples at0.3/0.6/0.9UI and records the first sampled positive value after the last nonpositive sample within the original0.95UI diagnostic window. A path still wrong at the last sample is censored and receives no finite settling claim. These sign diagnostics are not replacement100mV acceptance gates. All original decisions remain independently reproduced.

For every captured native device terminal on avdd or avss, report the actual voltage and source-referenced drop over active and measurement windows. Physical wire-end differences and stage common modes are retained. This can distinguish where delay and voltage loss occur; correlation alone is not a causal proof. No DC current is inferred from nominal resistor dimensions.

Controls execute all62 inherited parser/measurement/device/V-I checks, plus9 sign-settling checks covering already-correct paths, repeated crossings, zeros, censoring, nonfinite data, nonmonotonic times, mismatched lengths and insufficient windows. Expected total71; only actual job results establish success.

Three isolated GitHub jobs analyze the three immutable datasets. Full raw data stays in its original permanent release; owned cloud caches are removed only after successful reproduction and diagnostic preservation. Derived evidence is retained as artifacts. No local native acquisition is required.

A next circuit or layout repair must follow the measured results, preserve the failed trials and be independently simulated and physically extracted. This analysis does not establish full serial PHY, closed-loop CDR, routed-chip acceptance or final timing.

Completed run: https://github.com/Melihakbulut221/nssoc/actions/runs/41329721970 . All71 controls and all3 original-case reproductions passed. This does not accept any circuit/layout. Durable evidence: docs/evidence/physical-path-diagnostics-terminal-41329721970.

## Latest result: three native physical path and supply diagnoses completed

Cloud run41329721970/source11960a3bf126617857f2afda3686410664ff5764 passed71 controls (62 original and9 sign-settling controls) and all three isolated case analyses: width2, width8, buffer_drive. Each authenticated its original native archive on GitHub (129/129/124 members) and independently reproduced all six original data, phase, device and V/I metrics before reporting physical node voltages. All three original data gates remain false. Width2 remains device-safe; width8 and buffer_drive remain rejected. This is diagnosis, not a new simulation or accepted circuit/layout.

Complete60-file proof c084b7f31a004473bb62c7c478aba86b6ac8d6e1 is imported under docs/evidence/physical-path-diagnostics-terminal-41329721970; receipt SHA256 be10edf4e74e940f8a526fb2ddf84580f4805d537103cd3239177c33ff7e7553. Initial run41329263955 failed source parsing before native acquisition because of missing whitespace in fn.__code__ is value.__code__. Its source/run/jobs/log/receipt are preserved. Successor fixed only that syntax and passed all71 controls.

Actual width2 sampled measurement-window common-mode means along A: sampler2.100638V, series input2.034841V, series output1.723213V, shunt top1.613528V, buffer base1.673503V, buffer collector1.836408V, first downstream receiver base1.870649V. Same-net physical terminal identity is verified. Actual supply terminal xpd.w_t124_c has mean avdd drop0.351546V; tail126/129 ground rises0.113409/0.116035V. Shunt228/235/239 ground rises0.112550/0.106404/0.112662V. These are sampled waveform voltage measurements, not inferred DC currents or power signoff.

Width8 shunt228/235/239 ground rises increase to0.220667/0.199536/0.210432V. Nx8 buffer drive retains A series-output/shunt-top means1.722627/1.613000V and supply124 drop0.352617V. At0.6UI all255 A source samples are valid in width2, while buffer/receiver wrong-sign counts are111/129; Nx8 buffer drive worsens buffer wrong signs to125. Full path reports preserve A/C/D_X/D_Y, all receiver identities,138 supply terminals per case, unchanged sample windows and gates. Sign-settling is an additional diagnostic, never a substitute for100mV acceptance.

Next PHY work: locate the actual original500-device layout builder, GDS and fresh-RC producer41251732540 via scripts/cdr-via2-m3-loaded-producer-inputs.json at2a62d651d415fba8db3c5b758d1b66c05cde3a38 (not present at root105fe). Map measured high-current signal and supply terminal drops to authentic interconnect geometry; repair legal conductors/PDN and regenerate fresh physical extraction on cloud before evaluating. Large same-net and supply drops motivate this direction but do not prove a single root cause. Do not blindly repeat tail sizing, arbitrarily scale extracted R, widen divider devices, weaken limits or relabel diagnostic success as PHY acceptance.

Existing full64 native route41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64/release430685443 remains the only active route. Observe it without duplicate dispatch; after terminal preservation qualify actual new pins/connectivity/original route classes, DRC/antenna, matching154480-instance diode-inclusive netlist, fresh RC and unchanged three-corner setup/hold.

All CAD, simulation, native acquisition and numerical/geometric analysis remain on GitHub; local coordination uses source/API-derived text in RAM only. Workspace and task temp verified empty. Monitor remains every8hours, read-only, automatic_native_dispatch:false, now inventories691 runs; prior live monitor HTTP502 remains unresolved evidence, not healthy qualification. Full serial PHY, physical routing closure and final timing remain open.
