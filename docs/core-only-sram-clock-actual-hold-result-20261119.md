# Preserved SRAM clock ECO: actual nominal-RC timing result

Run [44441326165](https://github.com/Melihakbulut221/nssoc/actions/runs/44441326165), attempt 1, head 8904b7bcd091004ec4b789b49d277ac49cd0d30c completed successfully. Artifact 14490929227 SHA256 7424647eac99dd2eb46f1c67a756c79d6ec0ba3a667289d85f509d656feb89e6 and all 133 manifest outputs were independently verified. The result is diagnostic, not manufacturing acceptance.

## Measured result

| Corner | Setup violations | Setup worst slack ns | Hold violations | Hold worst slack ns | Slew / fanout / cap violations |
|---|---:|---:|---:|---:|---|
| slow 1.08 V 125 C | 59 | -0.74034647175 | 0 | +0.449112759694 | 502 / 209 / 52 |
| typical 1.20 V 25 C | 0 | +6.93770216468 | 0 | +0.185584775023 | 4 / 209 / 54 |
| fast 1.32 V -40 C | 0 | +10.3034055315 | 0 | +0.0371606089751 | 0 / 209 / 60 |

Relative to antenna-clean baseline run 44430367099, typical hold goes from 4 violations at -0.12389645216 ns to zero, and fast hold goes from 52 violations at -0.429732483983 ns to zero. Slow setup remains exactly 59 violations, worst slack -0.74034647175 ns, TNS -23.1071239794 ns. No clock-period or derating relaxation: 20 ns and 5 percent remain in force. This supports retaining the isolated clock-driver resize as a candidate; it does not close setup or electrical constraints.

## Source bindings

- ODB: a2d85760fec57ea28ea10a192c27528326b9fb48aa5c4a682367c08fdacca9ba
- Fresh netlist: 4a3fc2c196249590e6703fd52bc04b31ab22c4bc7c2cbddeaec38f3f12b93a02
- Fresh DEF: 76e17bc3cd2fc5c9c505cfb3b3c08939642745cb73dba22fc742825ff637f6b3
- SDC: f121116a72150c56126ac3d8dc4fda946e6d0040984e9264ef3d877171029de1
- Fresh nominal SPEF: 1742636e89198faef00faae8d51888b0a47151c77a68c98b15c7fb806fb8ca32

Annotation diagnosis has zero loaded unannotated drivers, zero partially unannotated drivers and zero missing native loads; 1403 unannotated drivers comprise 1288 disconnected and 115 connected-with-no-sink. There are 102967 SPEF nets. This is classification, not complete coverage acceptance.

## Remaining work and live successors

This measured ODB still has one antenna violation at SRAM b1/A_CLK. A single admitted diode (preparation 44442143764) is being routed in [44442857432](https://github.com/Melihakbulut221/nssoc/actions/runs/44442857432), which must pass independent geometry, DRC, antenna and unchanged-route checks. Its output needs another fresh RC/STA run; do not transfer these hold results to the changed geometry.

Data-path setup repair with one explicitly permitted contacting neighbor is running in [44441944245](https://github.com/Melihakbulut221/nssoc/actions/runs/44441944245). It remains a separate candidate and must not be combined blindly. The preceding data candidate failed an independent physical short check despite DRT zero.

Qualified RC min/max, full timing coverage, external package/PCB timing, SRAM and I/O transistor LVS, complete manufacturing checks and manufacturer approval remain open. PCIe/Ethernet are excluded by the approved reduced scope.
