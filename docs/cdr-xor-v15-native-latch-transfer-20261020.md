# Native master/slave transfer diagnosis
The original v15 full-wave failure persists. Previous replay39324658022 proved that A/B fail only the early sample but C/D retain wrong data at0.9UI. Actual clock-base median nearest-edge differences are only4.4–9.4ps; that observation alone does not identify a repair.

This follow-up reads the same immutable full native captures. It reconstructs each actual16HBTsampler from native shared-emitter groups and collector/base connectivity:
- two master/slave output pairs;
- actual cross-coupled hold pairs;
- slave input native nets matching master outputs;
- two parallel selectors per data/hold clock branch.

Every physical selector is retained. Actual graph corruptions remove a selector, change a slave input net and break a collector reference. All must reject. Actual sampled currents from the four selectors per bank determine observed track-minus-hold steering. No behavioral latch or regenerated waveform is inserted.

For each original expected capture edge, report master input/output and slave input/output at fixed offsets from-0.5UI through0.9UI, along with actual selector currents. The100mV marker at internal nodes is diagnostic only; original output phase/100mV/37.5ps gates are unchanged and reproduced. Simultaneously positive steering currents are observations, not proof of a data race.

Use complete native connectivity and these physical terminal waveforms to choose a data-transfer or latch repair. This does not accept the CDR, alter the nominal source wave, qualify PVT/RC or close the serial PHY. All execution and evidence remain on GitHub.
