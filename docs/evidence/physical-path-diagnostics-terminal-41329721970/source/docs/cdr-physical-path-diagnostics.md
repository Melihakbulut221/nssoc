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
