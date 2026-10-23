# CDR v39 complete native outcomes — 2026-10-23

All four cases in run39869412251 completed the original113475-row,1104-column,34.25ns native simulation. Each retained1,002,247,291 raw bytes, original256bits,8GHz clock,150fF/50fF loads and original100mV/37.5ps/device/phase gates. Native return code was0, diagnostic lists empty, protected sources unchanged and device checks passed. All four data, phase and VI results failed.

The experiment changes only four actual retimer pull-down resistor lengths relative to v37cdbias15. L1.8/L1.5um increased the modeled follower bias relative to the original2.25um. This is still a frozen-RC intrinsic screen, not candidate layout or post-layout acceptance.

| Follower length | Case | A minimum / maximum delay | C wrong signs / maximum delay | D wrong signs / maximum delay |
|---|---|---|---|---|
|1.8um|early|92.004mV /38.281ps|39 /54.531ps|64 /50.781ps|
|1.8um|late|89.127mV /38.594ps|24 /51.719ps|62 /50.781ps|
|1.5um|early|91.905mV /38.281ps|33 /54.219ps|43 /49.844ps|
|1.5um|late|89.031mV /38.594ps|15 /51.094ps|40 /49.844ps|

B passed both amplitude and delay in every case. A did not. Shortening the resistor improves some C/D errors relative to v37, but wrong signs and late settling persist. A remains essentially unchanged. The device-boundary pass is not data recovery, CDR-loop, PVT or complete PHY acceptance.

The next design decision must account for follower loading, input common mode, master/slave headroom and clock steering together; neither another blind resistor reduction nor promoting a single improved metric is justified. Complete native raw archives remain in the immutable cloud releases, with exact summary/parts/raw hashes in the accompanying JSON. The54um single-finger MOS placement obstruction also remains; isolated PCell availability has not produced a new qualified macro.

The repaired mainchip postroute consumer was inspected separately: it requires a completed153130-instance routing candidate, exact updated netlist3a200ea7..., original20/4/8/8ns clocks and5percent derating, discards inherited SPEF/metrics, and executes fresh antenna/disconnect/nominalRC/three-cornerSTA. Routing run39868561968 is still active, so no postroute acceptance or final timing claim follows.
