# Near-driver buffered route: actual three-corner results

Run [39243328773](https://github.com/Melihakbulut221/nssoc/actions/runs/39243328773) completed native detailed routing, fresh nominal OpenRCX and three cell corners in18421.54seconds. Routing DRC and critical disconnections are zero;32antenna-violating nets remain. No comprehensive chip DRC/LVS or qualified min/max RC acceptance is implied.

|Cell corner|Setup violations|Hold violations|Setup WNS ns|Hold WNS ns|Slew violations|Capacitance violations|
|---|---:|---:|---:|---:|---:|---:|
|nom_slow_1p08V_125C|9684|5|-20.66547|-0.431694|4122|802|
|nom_typ_1p20V_25C|7627|7|-7.882026|-0.372727|822|811|
|nom_fast_1p32V_m40C|3733|19|-3.799566|-0.325945|207|828|

All three corners retain1993fanout violations. The original20/4/8/8ns clocks,5percent derating,20SRAM and native functional/topology proofs remain unchanged. The new39buffers reduce setup counts versus the preceding route, but the slow-corner worst setup slack worsens from−20.18643ns to−20.66547ns. This is not monotonic closure and is not accepted as final timing. Typical/fast WNS and some electrical metrics improve; the full result, including regressions, remains retained.

The new read-only path-review workflow restores the exact native max/min/checks/clock reports, retains worst paths and compares every reported numeric metric to the source route. It uses the already exercised parser and malformed-report controls with an exact source delta guard. No reroute or constraint change is performed. The next repair must be selected from actual slow-corner path drivers, loading, cell delays and clock-domain constraints, then revalidated at all three corners.
