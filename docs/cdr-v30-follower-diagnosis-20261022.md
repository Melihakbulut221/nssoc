# v30 actual retimer loading diagnosis

Both v30 latch diagnoses reproduce all original HBT and output checks from the unmodified full native waveforms. At0.3UI, sampler A master output is at least258.7mV (early) while slave output is39.3mV; sampler C master input is only7.20mV and sampler D19.58mV. All255 C/D master input diagnostic samples at that phase are below100mV. Internal100mV is only a diagnostic marker, not an input acceptance gate.

Reducing the four input resistor lengths worsened downstream sampling, even though transistor stress passed. Before changing device geometry again, the new read-only cloud job measures the actual ac/bd follower base/emitter voltage, current and common mode. It preserves exact v30 waveforms/geometry, all original latch checks and fault controls. No current source, data driver, clock or ideal waveform regeneration is substituted.

Compare these observations against the v29 follower measurements to decide how to repair loading and propagation. The source adaptation is restricted to output namespace and the existing follower observation block. Full PHY acceptance remains false.
