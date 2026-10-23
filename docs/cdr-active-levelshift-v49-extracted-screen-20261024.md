# v49 physical loaded waveform screen

The real physical leaf passed native DRC/LVS, exact terminal binding, fresh wire extraction and native model composition in runs40024005062,40026009718,40028080567,40028786566,40029826867. This does not prove its loaded electrical performance or whole-CDR operation.

The new cloud-only workflow restores the SHA-pinned composed18primitive53R93C model. Native interface order and exact device/parameter/terminal records are checked before simulation. Nine finite body contacts and the distinct internal body net are retained. The extractor reference is explicitly grounded at the external testbench, without shorting the internal body to ground. All wire nodes, intrinsic terminal nodes and native HBT/MOS currents are saved.

Each nominal, hot-low, cold-high, swapped-output and bias-off case runs the original full34.25ns/256bit waveform with0.3125ps maximum step,10ohm source and150fF per output. Original2.5V supply scaling,1.48V input common mode,60mV differential input,500uA reference, solver options, native OFF flags, zero-source operating-point, full binary reader,100mV/37.5ps signal gates,1.8–2.15V output common-mode gate, and HBT/MOS safety limits are unchanged. An Actions control compares the complete acceptance-analysis region with the pre-layout baseline, allowing only physical tail instance lookup and explicit extracted-leaf status names.

Eight corrupted physical-binding cases must be rejected in addition to the14previous composition controls. All native waveforms and failures are published to Releases.

The ideal500uA reference is a standalone leaf stimulus only. Actual C/D parent integration must use the intended physical bias network and avoid duplicating the sampler and new leaf's8um reference MOS. Actual updated parent geometry, DRC/LVS, whole-parent extraction, original CDR gates, full-loop/PVT and RF/substrate qualification remain required. The native HBT model uses hbt_typ; these three supply/temperature/model combinations do not claim exhaustive HBT process coverage.

Status at creation: unmeasured extracted electrical performance. No parent/full serial Gen3x4 PHY/mainchip/timing acceptance.
