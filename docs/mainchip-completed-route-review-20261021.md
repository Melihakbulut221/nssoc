# Completed mainchip route review

This manual cloud workflow consumes two immutable, independently verified inputs: a successfully completed saved native DRT process, and the passed exact mainchip dependency package. It refuses an active route, global-only preflight or mismatched source/controller. Every existing instance, port, net, placement and fixed clock route is checked by the existing native geometry gate and its original corruption controls.

The raw/full resolved config, original20/4/8/8ns clocks,5%derating, uncertainty and nominal extraction rule remain unchanged. PDK/project files and runtime-owned base.sdc retain their hashes. The initial state discards inherited metrics and stale physical/timing views. A new DEF is exported directly from the proved completed ODB using the exact native runtime because OpenROAD.RCX consumes DEF; no old DEF is imported.

The only flow steps are antenna checking, disconnected-pin reporting, audited fresh nominal RC extraction and audited standalone OpenSTA. It never invokes routing, diode insertion, buffering or timing repair. Native antenna text must agree with counts. Every corner requires propagated clocks, finite metrics, nonnegative setup/hold worst slack and zero setup,hold,max-cap,max-slew,max-fanout violations. All reports and failures are published.

A green control job proves methods and rejection decisions only. Native analysis is dispatch-only and requires both real completed-source descriptors. A complete analysis with violations remains COMPLETE_NATIVE_POSTROUTE_WITH_UNCLOSED_GATES. Even a nominal pass does not assert qualified RC-min/max, full-chip transistor LVS, production DRC, analog/ESD or full serial PHY acceptance.

Input package: run39635867954, source d37ef5a4358933a7b9b106ef7f9c6724a4e71f3b; see the exact pass receipt. The active mainchip ninth run39631640578 must finish before this workflow can run.
