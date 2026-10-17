# Physical C8 full acquisition at half timestep

The completed externally clamped three-step comparison39040693114 reproduced all original measurements. Half/quarter frequencies differ4.96ppm in the fixed40-50ns window and feedback timing differs about0.23ps, while an extra second-divider falling edge near timezero remains in the quarter-step capture. This is not convergence or closed-loop acquisition acceptance.

The new campaign starts a separate continuous1us closed-loop trajectory on the exact845device/8660wire C8 physical parent SHA3d2dfdd6d27a05fc5d911461c84471b1e05f62e976b7ae31de9d01595a503b60. It changes only transient output/maxstep from0.3125ps to0.15625ps. The original deck SHA1817d6ee2cdbd95023151f7dfc33dfc6f0f7ab5578e3b177568323fddeb51f2f must be recovered byte-for-byte when this one change is reversed.

Original1usstop,34voltageprobes,KLU/reltol1e-4/abstol1e-12,zero-sourceOP,102nativeOFFreadbacks, allphysicalmodels and both final100ns100ppm/50ps/no-slip/control gates remain unchanged. Coarse-step,shortstop,wrongOFF and relaxedtolerance mutations must be rejected before native execution. The old failed coarse result is retained.

Cloud host time limits preserve the actual native process using the already-proven cross-host checkpoint machinery. Every resumed prefix must match, native-entrypoint must appear exactly once, and no concatenated or fitted waveform substitutes for the trajectory. The complete capture must additionally prove maximumstep0.15625ps and more than6million native samples. Initial and continuation jobs publish durable checkpoint descriptors if further continuation is required.

Even a passing acquisition result covers selected probes at this condition. Full-device safety,PVT,jitter/noise,CDR,serialx4 and mainchip acceptance remain separate and open.
