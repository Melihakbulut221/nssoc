# Native sampler stage and clock timing diagnosis

This read-only analysis reuses the complete actual collector Via2 loaded-wave failure41441047354. It creates no simulation, circuit or layout. The existing cloud acquisition authenticates all release assets and every native archive member, and the frozen full binary-wave reader must reproduce the original raw capture exactly. Original parser controls and original operating-point/timing diagnosis remain intact.

A separately pinned subset of48 HBT records from actual full500 native mapping41450661063 identifies master/slave DP,DN,CS0/1,CH0/1 for samplersA/B/C/D. Each record is joined to the actual restored composition and loaded measurement by native ID, instance, all parameters and all four native terminals. Native node voltages are never replaced with ideal net aliases.

For each of the16 sample/hold selector pairs, both rising and falling local differential clock zero-crossings are compared with the corresponding ideal CP/CN pair. Results retain raw sample brackets, candidate associations, missing and ambiguous matches. A +/-0.25UI association window is a diagnostic convention, not an acceptance threshold or recovered-clock claim.

Master input/output and slave input/output voltage transitions are recorded. At the original sampler bit edges, the analysis records actual existing samples at0,.1,.2,.3,.4,.5,.6,.75,.9UI. It uses the first raw sample at or after each requested diagnostic time with explicit index/time; it does not interpolate/resample. Every original per-bit final sampler clock-to-valid delay must independently reproduce within1e-18seconds. Upstream observations never replace original output tests.

This is intended to distinguish clock-distribution delay, master settling, slave input-wire delay and slave output settling before a circuit change. Correlation alone does not prove causation or qualify timing. All fullPHY, physical and finaltiming acceptance flags remain false. Source and native payloads remain in GitHub; only derived JSON/text is returned.
