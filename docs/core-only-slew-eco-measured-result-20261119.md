# Three-driver slew ECO measured result — 2026-11-19

RC/STA run 44468611583, head 4736499767af0cb0853f6e5dd792593f362615a1, attempt 1 succeeded. Artifact 14503269406 SHA256 b41baf9c021dd370de9538a652764e02ef1a1c36d84994c836aa7a3280d487a0; all 135 manifest outputs verified. Three fresh violator-list reports contain no timing violations.

| Corner | Setup violations | Setup worst slack ns | Hold violations | Hold worst slack ns | Slew | Fanout |
|---|---:|---:|---:|---:|---:|---:|
| slow 1.08V 125C | 0 | 0.02127897918098623 | 0 | 0.4491127596936628 | 507 | 210 |
| typical 1.20V 25C | 0 | 7.431960146545003 | 0 | 0.1855848860450402 | 0 | 210 |
| fast 1.32V -40C | 0 | 10.303470368535212 | 0 | 0.037160608975109796 | 0 | 210 |

Nominal-RC setup/hold closure is preserved, with unchanged 20 ns and 5% derating. Typical slew violations improve from four to zero, but slow-corner slew violations increase from 502 to 507. This is a mixed candidate, not electrical closure. Do not promote it to a production baseline on green job status. Earlier baseline run 44459123476 remains preserved. Next action is exact pin-by-pin comparison of old/new checks reports to identify removed, persistent and introduced slew violations before choosing load isolation, route or upstream-driver changes. Capacitance changes still need detailed report comparison; no reduction is claimed. Qualified RC min/max, full-chip integration/signoff, SRAM/I/O LVS and manufacturer approval remain open.
