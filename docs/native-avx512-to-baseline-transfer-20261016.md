# Physical845 saved process: AVX512 source to non-AVX512 destination

Masked source38904997140 passed the original4ns12818row/34probe trajectory SHA633f0aaa88c7c08655e6d1b7f99d08284916746331f7c50c03091161ca2bbd1e, host/container equality, same-host actual process restore and all3negative controls. Its CPU is AMD EPYC9V74 and advertises AVX512. Every runtime shared-library byte is identical to the original unmasked source; only declared libc dispatch masks and capture metadata differ.

The separate-job workflow requires a destination without AVX512 before restoring any source. If GitHub assigns an AVX512 runner it records a diagnostic target mismatch, not a simulator or circuit failure; retry only after that terminal result, never duplicate a healthy restore. For an eligible destination, load the exact immutable image, model files, checkpoint images, actual binary prefix, command and GLIBC_TUNABLES. No debugger, cold restart or waveform reconstruction is used. Require the complete final raw bytes and every native sample to equal the source uninterrupted reference, with all3corruption controls.

A pass is a bounded cross-CPU runtime result only. Full original1us physical PLL acquisition still needs its own actual capture and all original lock/frequency/jitter/phase-slip/control/device gates. No PHY or mainchip timing acceptance is implied.
