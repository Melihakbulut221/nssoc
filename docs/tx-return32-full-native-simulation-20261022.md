# Return32 actual full native transient
Run39770384053 prepared both original nominal and swapped-selector cases. Both use the actual new8088-device model a9faee6c09dbaa599e8fac3051c0f778c5939479c6bc3c4769cff6763662168f with140222R99906C. Each case passed the unchanged10032-value operating-point transport and five corruption controls, plus ten physical-parent bench adaptation faults.

The native simulator controller is mechanically derived from the previous full-wave controller, changing only namespace, exact prepared source pins/date and model digest. All256 input bits,34ns trajectory,14182 columns,604HBT/5376MOS observations, full timestep, loads, sample phases, device bounds and original waveform readers stay unchanged. The source checker freezes the original reader and simulation dependencies.

Both nominal and swapped-selector native processes launch on hosted runners. Initial native work is7200seconds rather than600seconds, within the unchanged controller's supported300..7200 range; the job allows240minutes to preserve and publish. If unfinished, the same process and its complete raw prefix must be checkpointed and resumed using its exact immutable descriptor. It is not a shortened waveform, reduced observation set or a cold restart. No native completion or electrical acceptance is claimed by this commit.

Historical electrical rejection and all new failures are preserved. External clock modulation/intermacro clock routes, supply/bias feeds, qualified device-access/body/RF PEX and full serial PHY/mainchip integration remain distinct unfinished requirements.
