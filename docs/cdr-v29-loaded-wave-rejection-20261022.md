# Actual v29 loaded waveform rejection

Run [39695370523](https://github.com/Melihakbulut221/nssoc/actions/runs/39695370523), source c875a4f6effbd936d054a58f22f90bdaaf27d3e3, completed all four original 34.25 ns cases using 476 native devices, 17906 extracted resistors and 12834 capacitors. Both nominal cases failed. Clock-stopped and VI-bias-off cases detected the injected faults; those green jobs do not accept the nominal circuit.

| Original measurement | Early | Late | Required |
| --- | ---: | ---: | ---: |
| Worst sampler clock-to-valid | 59.21875 ps | 54.53125 ps | <=37.5 ps |
| Sampler C wrong-sign samples | 9 | 0 | 0 |
| Sampler D wrong-sign samples | 96 | 74 | 0 |
| Signed phase response magnitude | 14.2764 mV | 18.5014 mV | >=30 mV |
| Signed VI mean current magnitude | 43.5888 uA | 53.0758 uA | >=50 uA |
| HBT device-limit violations | 0 | 1 | 0 |

Late-case xpd.xd0105 minimum active VCE is 0.399709092746213 V, below the unchanged 0.4 V limit. All nominal MOS terminal checks pass. All four samplers still fail their original margin/timing checks, and both loaded XOR comparisons fail. Thus improved nominal HBT headroom does not close data timing or phase response.

The next cloud diagnostic restores each complete immutable native wave and the exact v29 physical geometry. It reconstructs the actual master/slave transistor graph, reproduces all 120 HBT measurements and all four original sampler checks, and measures internal data/clock current-steering windows without changing source bits, clock alignment, loads, acceptance limits or simulation duration. Only the exact v29 source bindings, measured RC census and observed violation sets change relative to the prior diagnostic; the 3 mA violation boundary is made consistent with the original strict less-than gate.

No closed-loop clock recovery, complete serial PHY, routed-mainchip timing closure, or production approval is claimed. Source, complete raw waves and failures remain in GitHub Releases. Local workspace remains empty.
