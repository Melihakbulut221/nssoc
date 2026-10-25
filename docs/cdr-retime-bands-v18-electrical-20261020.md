# CDR v18 full loaded electrical result: rejected

All four jobs in [run 39381284126](https://github.com/Melihakbulut221/nssoc/actions/runs/39381284126) completed. Exact source e599a5ea4840b5ff51637559594c250ea780f14c; model SHA256 46452abe7eca2751d59767db8fc32a1dfcb9cf0c2cd627fad3a9434c7e668cde. All native simulations returned zero, used the complete 34.25 ns capture, 256-bit stimulus and unchanged acceptance rules. Physical DRC/LVS, source geometry, MIM and extraction passes do not qualify the electrical candidate.

| Case | A wrong/low-100mV | B wrong/low-100mV | C wrong/low-100mV | D wrong/low-100mV | Phase average |
|---|---:|---:|---:|---:|---:|
| nominal early | 81/129 | 129/129 | 184/202 | 337/345 | 17.184 mV |
| nominal late | 97/129 | 0/128 | 188/200 | 312/326 | 32.550 mV |

Each sampler has 765 fixed sampling points. Both nominal jobs pass device limits but fail data acceptance; early additionally fails the unchanged 30 mV phase threshold. A/B worst clock-to-valid remains approximately 46–53 ps and C/D approximately 119 ps. The band reorder did not solve the internal sampler settling problem.

Compared with v16, early C wrong samples improve 189 to 184 and D 339 to 337, but A regresses 77 to 81. Late D regresses 310 to 312. This is not an accepted replacement for the nominal electrical design. Clock-stopped and bias-off negative controls completed successfully by rejecting their injected failures; their success is not nominal PHY operation.

All immutable release assets, digests, native raw hashes and small report excerpts are pinned in [the electrical receipt](evidence/cdr-retime-bands-v18-electrical-rejection-20261020.json). Full terminal captures remain in the cloud. Next analog work must address the leaf sampler's internal settling and C/D signal amplitude, then regenerate and revalidate geometry and parasitics; relaxing phase/sample/load/device gates is not a repair.
