# Shunt-v4 XOR primitive: fresh-layout loaded verification, 2026-10-17

Run39049659259/source332c9260 passes the original native full-wire primitive tests for nominal, hot/low and cold/high. The actual output-swap fault produces768wrong samples and is rejected by the unchanged source-bit oracle. This closes the v2/v3 primitive margin/headroom failures for this specific circuit and finite set of bench conditions. It is not an accepted CDR, complete PVT/RF extraction, or serial PCIe PHY.

| Condition | Minimum signed margin (mV) | Wrong samples | Minimum active HBT VCE (V) |
|---|---:|---:|---:|
|nominal|142.357336|0|0.475438|
|hot_low|150.959468|0|0.424815|
|cold_high|130.574477|0|0.492737|
|swap_output|-202.803253|768|0.475438|

Each normal case has768correct samples, zero below100mV, all19HBTs within0.4–1.6V limits and the original current bound. Every native OFF flag reads back, the zero-source operating point is zero and there are no native numerical diagnostics. The actual source waveform remains256symbols,34ns total and three fixed phases; no fitted timing/changed bit oracle.

The chain uses fresh shunt8um/width8um geometry (collectorloads1.8um/18um, other devices unchanged): core39047111778, crossedparent39048145296, nativeplanes39048840245, RC39049134526, composition39049460903. Native560category DRC/deepflat54device LVS/faults, all4020R/2641C terminal attachments,13RCcorruptions and sixcompositionfaults pass in their stated scopes. Model SHA256 b201876a3b0988f746822213f51c120e09f9837c0f26ddb1a7a591bd57dfdc23.

Boundaries remain external10ohm sources with2.0V data and1.3Vselect common modes,500uAidealbias and50fF peroutput. Finite substrate contacts are included but substrate spreading/RF qualification is not. Next native integration must reconcile sampler-output common mode/loading with both XOR input domains, preserve sample identities across rising/falling edges and measure detector polarity/deadzone. Neither an externalclock sampler nor a working XOR implements clock recovery. Actual V/I feedback, acquisition/frequency-offset/missing-transition behavior, noise/jitter/BER, per-lane physical routing and x4 mainchip integration remain open.

This integration requirement is consistent with transistor-level Alexander-detector characterization in [Lee, Kundert and Razavi, JSSC2004, sectionsII–III](https://kenkundert.com/docs/jssc04-09.pdf). The paper motivates characterization and does not validate this process or implementation. Older sampler experiments with externalclock/nodeset/startup diagnostics must not be promoted to clean recovered-clock evidence.

Full source-bound reports, original raw waveform archive hashes and native controls are preserved in docs/evidence/cdr-v4-fullwire-pass-20261017.json and its GitHub release links. v2/v3failed traces remain unchanged.
