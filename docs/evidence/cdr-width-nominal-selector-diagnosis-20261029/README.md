# Current-width nominal electrical diagnosis

The two actual nominal cases from run40906725656/sourcee1914245 are electrical rejections despite simulator rc0 and empty simulator diagnostics. Four master tracking selectors fail the unchanged0.4V activeVCE gate: D61/62 and C115/116. Their minima are0.34713/0.34826/0.38149/0.38278V (early) and0.34298/0.34412/0.38261/0.38374V (late).

All124 HBT scalar predicates were recomputed; only these minimumVCE gates fail. All50 MOS, all stage-tail current and7 MIM gates pass. Sampler timing still fails37.5ps in all four stages; comparator timing exceeds75ps and phase/VI fail. No gate or stimulus was changed.

The current composition and locations are joined to all500 actual devices and1446 terminals. Current C selector collector is cluster134/net$698, not historical136/$708. The exact four selector roles, current connected-device records, physical resistor/MOS dimensions and source hashes are in diagnosis.json.

The prior column widening improved selector minima only3.74-5.31mV;16-57mV deficits remain. Gain60 already reaches1.57552V against the1.6V maximum, so blindly lifting LP/LN or changing shared bias is not supported. A narrowly measured residual interconnect repair is the first conditional scope. A real matched local master-clock interface is a separate unvalidated circuit hypothesis if wire loss is insufficient. No dimensions, voltages, sweep or native execution are authorized.

Required next evidence is simultaneous current-capture terminal/current/contact rows at selector minima and gain maxima, with exact RC-path ownership. These reports provide scalar extrema; historical same-row data cannot substitute for the current capture. Both complete authenticated raw derived JSON reports are retained beside this analysis. No waveform/archive/native payload was acquired and no authored tests or CAD ran locally.
