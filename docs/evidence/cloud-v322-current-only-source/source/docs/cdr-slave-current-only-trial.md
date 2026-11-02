# Slave current-only isolation trial

This is a new provisional electrical experiment, not accepted PHY or physical layout.

The full-wave stage diagnosis41508059395 of rejected trial41501239838 shows two distinct failures. At representative C bit8, output is28.415mV at0.3UI, reaches120.445mV at0.4UI and173.372mV at0.5UI, then falls to99.105mV at0.9UI. The118.90625ps metric is the original bounded last-invalid-sample measurement; it must not be described as a successful delayed transition. Eight C bits hit this bound. A/B/D maximum metrics remain42.96875/38.90625/49.21875ps against37.5ps. Clock crossing lag is1.5625..4.6875ps. These are observed diagnostic samples, not interpolated threshold crossings.

Hypothesis: the prior simultaneous collector-load reduction weakened C hold margin while increasing slave tail width affected speed. Isolate the current change using the original physical parent41439516945, retaining all original collector resistors L2.6um,W32um. Do not derive from either failed bias or combined drive/load model.

Exactly16 slave tail NMOS devices SA/SB/SC/SD_S_T0..3 change W36um to48um with L0.3um unchanged. Proposed AD/AS16.32p and PD/PS96.68um remain consistent with the prior0.34um diffusion-extension convention. All other484 primitive parameter dictionaries, every interconnect RC card, every resistor, all HBTs, master stages, input divider, test stimulus, external8GHz clock and150fF output loads stay unchanged. Exact complete-model reversal and mapped terminal identities are checked before simulation. Original29 definitions,5 blocks,9 numerical files,13 admission refusals, original13 native binding refusals,2 unit-equivalent cases and8 actual geometry fault refusals remain mandatory.

This is an isolation experiment. Increased current may improve swing/slew or worsen transistor headroom, intrinsic capacitance and power; no improvement is presumed. Every original voltage/current,100mV output,37.5ps delay and full-wave gate remains active. No change to measurement logic, stimulus, load or acceptance thresholds.

The existing16-MOS adapter validates a read-only reversed model with the original geometry binder and returns actual48um parameters for actual simulation. It does not replace simulated dimensions. The target list now contains only16 MOS devices, so it grants no resistor exception. Source controls retain14 generic malformed-card refusals and5 geometry adapter refusals. Frozen historical docs describe earlier trials; this document defines the current experiment.

Fixed parent wire RC is provisional. A positive electrical result still requires matching schematic/GDS, DRC/LVS, fresh parasitic extraction and rerunning the complete loaded simulation. This does not establish closed-loop Gen3 x4, PVT/ESD/EM, chip integration or final STA. All native execution and evidence remain on GitHub.
