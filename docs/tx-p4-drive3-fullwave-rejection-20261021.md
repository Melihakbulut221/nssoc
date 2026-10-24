# Preserve the rejected full32 TX result

Run39453950816 nominal completed the original34ns capture with77580 complete rows and3004 columns. The native simulator had no recorded diagnostics and its zero-source operating point passed. This is a completed rejected electrical test, not a simulator timeout.

The original768 samples contain13 wrong-sign and20 below100mV samples. The worst signed margin is-279.780mV. The final,level4 andlevel8 interface checks fail; CMOS andlevel16 interface checks pass. Eighteen HBTs violate the unchanged0.4V minimum VCE check; no MOS voltage check failed. The worst HBT minimum VCE is359.028mV.

This case uses the prior core plus aggregate input drivers and eleven separately bounded clock macros. It is not the newly composed8074-device full input-driver/core model. Keep its original waveform, source-bit oracle, sampling phases, loads and device gates. Localize the failing output intervals and18native HBT roles before selecting the next physical change; preserve the live separate-native-driver comparison rather than restarting it. Clock macro/mainchip physical integration and the actual8074-parent electrical screen remain required.

All evidence is pinned by the release summary/part hashes in the associated receipt. No rejection has been waived or converted into PHY acceptance.
