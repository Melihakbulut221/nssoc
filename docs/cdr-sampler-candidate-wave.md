# Rejected sampler candidate: simultaneous headroom diagnosis

Native run41272254964 was rejected. Its complete original waveform is read on GitHub runners without rerunning a simulator or modifying geometry. Exact source8a07e8f773d931f9cb7f4ac72e5520b68bb133be, release430356103 and all archive members are authenticated. Only the existing wave and candidate composition are materialized on the runner. No native payload is downloaded to the user's computer.

The unchanged frozen streamed reader reconstructs every original1151 vector. All124HBT metrics, all6stage metrics and1530per-bit delays, phase average andVIcurrent/voltage must reproduce the complete authenticated native report. Report provenance is the candidate's actual run, never relabeled as the baseline.

The extension locates every failing original HBT predicate: active minVCE>=0.4V; all-time absVCE<=1.6V; all-time absVBE<=1.0V; absIc per emitter<=3mA. Startup maxima remain included. Every violating interval is retained. At each worst row, it records all124HBT terminal voltages/currents simultaneously, the original logical aliases and clock/input/bias outputs. This distinguishes transient overstress from steady loaded settling without discarding failing points.

Seven existing frozen reader/archive/measurement controls retain their bodies; only their module import targets the new diagnostic. Nine additional event controls cover startup retention, active mask, signed voltages, per-emitter normalization, interval preservation, exact threshold inclusivity, invalid arrays and rejected case identity. All run in cloud before acquiring native data.

The resulting data guides the next circuit repair. Successful diagnosis is not a successful PHY simulation or physical acceptance. Existing collector-load changes improved B but left A/C/D/X/Y and five HBT gates failing. Coupled common-mode and settling must be addressed before further physical implementation.

The IHP [bipolar process specification](https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/03_bjt_params.html) lists npn13G2 collector-emitter breakdown as1.4V minimum/1.6V typical under its stated test conditions. The inherited1.6V screening gate is preserved for reproducibility; passing it alone does not establish a foundry-approved reliability envelope or production approval.
