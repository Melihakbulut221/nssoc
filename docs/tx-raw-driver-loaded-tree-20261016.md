# Raw physical TX input drivers loaded by the routed serializer tree

Cloud experiment: `tx-driver-loaded-cloud.yml`, paired intrinsic/wire cases. All eight input instances use the actual100-device model (84raw MOS fingers,4resistors,12finite contacts). The wire case retains251R294C per driver. Both use the same actual162-device `compact_return_strap` routed core, including its real intermacro wire network. No device resizing or oracle adjustment occurs.

The original34ns256-bit8GT/s output oracle,0.3/0.5/0.7UI phases,100mV output and150mV interface margins,62HBT and now672raw MOS checks, zero-source operating point and strict solver readback remain active. All MOS terminal probes are rebuilt from actual named D/G/S/B model terminals. Three adapter faults must reject missing instances, swapped input/output pins and omitted native terminal probes. Runtime uses the previously source-verified VBIC companion patch; it is not foundry qualification.

Waveforms stream losslessly on hosted runners. No local archive, checkout, simulation or tests. There is no internal wall-time kill; the hosted job has the platform360-minute limit. Native failure and partial output are retained. A completed study can still fail engineering gates, and workflow success alone is never acceptance.

Current status: awaiting native electrical results. Clocks, supplies and connections between driver macros and tree remain ideal external boundaries. This is neither32:1/x4 coverage nor CDR/PLL/ESD/fullchip/production approval. Qualified substrate spreading and poly/diffusion resistance remain open.

## Actual nominal result38878882117

Intrinsic driver control passes the unchanged complete34ns gates:768original output samples,minimum241.974mV,no wrong signs,no failed MOS/HBT,zero-sourceOP and no native diagnostics. SummarySHA `b68db7ae2195f1b73348ff8c0f64693737c3dc1f76c741ea8a95c5c775abc693`.

Actual driver wire case **fails**:32wrong-sign output samples(all0.3UI),50below100mV,minimum-198.497mV. CMOS interface minimum96.297mV and common-mode1.75578–1.76596V fail original150mV/1.8–2.05V limits. Final interface minimum13.231mV;12HBT fail VCE headroom,672MOS pass. No native diagnostics and complete79019-row34ns capture do not override these failures. SummarySHA `ecf7270b283658784c05dac1bb6c15e5946d390cc64d11b1bd5087027290980d`. Wire candidate is rejected.

Next: two explicit artificial sensitivity captures, removing only294wireC or scaling only251wireR by0.001 per driver. Preserve all100intrinsic devices,finitecontacts,nodes,sources,downstreamroutedcore,observations and originalgates. These are diagnoses to identify whether real supply/signal routing geometry needs resistance/capacitance repair. Neither artificial variant can be accepted as physical layout. Actual new geometry must repeat nativeDRC/LVS/RC/composition before electrical acceptance.
