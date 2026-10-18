# Native sampler load-drive candidate v2

This is an unaccepted component experiment toward the full8GT/s serial PHY. No mainchip macro is replaced by this source. All work executes on GitHub-hosted runners.

## Measured reason

Whole physical PD420 run39119999874 failed original sampling gates and early-phase direction. Read-only run39121253725 reproduced the actual wave failures; the receipt cdr-hybrid-v2-native-path-review-20261018.json pins both native reports and original captures. The retimed input pairs are strongly attenuated. Incident extracted wire capacitance reaches0.748pF on aqn and0.702pF on aqp; these sums include coupling and are NOT equivalent grounded output loads. Nominal HBT/MOS safety passing did not establish valid data or CDR operation.

## Explicit component change

Keep12HBT instances,3nativeLVNMOS and12rppd topology. Scale each HBT emitter multiplicity4x (data/hold2→8, clock4→16; totalNx32→128), tail width32→128um at0.3um length, and collector resistor width8→32um with length2.12um unchanged. Reference stays8um/0.3um and500uA: nominal mirror ratio4→16. Intent is more output current at approximately retained static swing and current per emitter; this is a design hypothesis, not measured success. Increased input/clock capacitance, resistor parasitics, power, startup and supply droop can defeat it. No ideal gain or latch is added. Input level-shift resistors remain unchanged so this experiment does not claim to solve the separate retimed-interface attenuation.

## Unchanged acceptance and harder load

Use1pF grounded at each output as an explicit stress experiment, instead of the old standalone150fF. It is not substituted for the distributed parent network. Preserve256PRBS source bits,34.25ns trajectory,0.3125ps maximum step,10ohm data/clock sources, original clock phase,100mV minimum data margin and37.5ps clock-to-valid limit. Preserve every startup, native OFF flag, transistor terminal/current and source-immutability gate. Run nominal/hot_low/cold_high and actual swapped-output/stopped-clock negative controls. A detected fault does not establish transistor safety under that fault. Exact source/controller delta guards retain the old guard chain and acceptance expressions.

All results and failures are published. Before any integration, require measured outcomes, actual new geometry and DRC/LVS, fresh distributed extraction/model binding, full parent trajectory and complete CDR/PLL loop/corner verification. Final mainchip timing and fullPHY acceptance remain false.

## Actual first run rejected

Run39122483815 passed exact source/controller guards but all five cases failed native startup; no valid bit-error, delay or device-limit characterization was produced. Nominal simulator returned0 while its log reported temperature limiting NaN and transient timestep failure at50.063ps; the existing diagnostic gate correctly rejected it. Read-only cloud diagnosis restores original logs/decks and OP without weakening any gate or substituting a new waveform. See the pinned startup-rejection receipt.
