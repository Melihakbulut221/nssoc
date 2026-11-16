# Clock output drive experiment (not accepted)

Native rejected-wave diagnosis [43836172779](https://github.com/Melihakbulut221/nssoc/actions/runs/43836172779), source8155e6034639a8fdd7f9b1544db88c00d3ed03ae, artifact14209849601 SHA256a0bc797d7a752da286ba88a521eabbfa629a5bc56dbe3495469c96804793d737, was authenticated in full. Original source capture is rejected MIM-area4 case43806909384. All247 rising and247 falling clock transitions crossed both zero and100mV at all11 observations; no missing crossings. Crossing latency is a diagnostic, not acceptance.

Median100mV incremental delay: input to crossed collectors5.9375ps, collectors to output27.5ps rising/28.125ps falling, output to physical sampler bases1.875–3.75ps. The output follower dominates this clock-path measurement. This does not establish it is the only cause of failed data sampling. Original sampler deadline remains37.5ps.

The trial doubles output emitter-follower and current-sink banks: each polarity has six Nx5 followers (was three) and eight Nx4 mirrored sinks (was four). It adds14 native HBT instances and62 emitters:44/161 total instead of30/99. Input/cascode stage, all seven sizing resistors including3200ohm reference, supply, original source impedances and waveforms remain unchanged. Intended benefit is increased transconductance/sink current at the loaded output. Increased input loading/power and voltage/current stress are measured risks, not assumed to pass.

The650-device physical network retains the prior shortened-divider/MIM-area4 exploratory parameters and OLD metal/gate RC. New clock devices and seven ideal sizing resistors are not laid out. Geometry does not match candidate; full PEX, RF substrate, closed loop, PVT, SOA/compliance, serial Gen3x4 and chip signoff remain open. Even a nominal pass is only a circuit candidate for subsequent physical implementation.

Run original256bits,150fF sampler/50fF comparator loads,37.5ps sampler deadline,100mV sampling margin, original device/current screens and native diagnostic checks. No shifted sampling, relaxed thresholds or removed devices. Every added HBT is saved and checked. Reject any original failed gate.
