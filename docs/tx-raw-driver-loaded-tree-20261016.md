# Raw physical TX input drivers loaded by the routed serializer tree

Cloud experiment: `tx-driver-loaded-cloud.yml`, paired intrinsic/wire cases. All eight input instances use the actual100-device model (84raw MOS fingers,4resistors,12finite contacts). The wire case retains251R294C per driver. Both use the same actual162-device `compact_return_strap` routed core, including its real intermacro wire network. No device resizing or oracle adjustment occurs.

The original34ns256-bit8GT/s output oracle,0.3/0.5/0.7UI phases,100mV output and150mV interface margins,62HBT and now672raw MOS checks, zero-source operating point and strict solver readback remain active. All MOS terminal probes are rebuilt from actual named D/G/S/B model terminals. Three adapter faults must reject missing instances, swapped input/output pins and omitted native terminal probes. Runtime uses the previously source-verified VBIC companion patch; it is not foundry qualification.

Waveforms stream losslessly on hosted runners. No local archive, checkout, simulation or tests. There is no internal wall-time kill; the hosted job has the platform360-minute limit. Native failure and partial output are retained. A completed study can still fail engineering gates, and workflow success alone is never acceptance.

Current status: awaiting native electrical results. Clocks, supplies and connections between driver macros and tree remain ideal external boundaries. This is neither32:1/x4 coverage nor CDR/PLL/ESD/fullchip/production approval. Qualified substrate spreading and poly/diffusion resistance remain open.
