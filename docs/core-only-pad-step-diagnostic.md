# Controlled time-step diagnosis

Prior KLU/Gear2 5ps run44372922971 failed only0-turnoff near22.7529ns. This matrix retains that solver, itl4=100, all six cases, full50ns capture, pinned circuit/models/PVT, nativeDC operating point and default error tolerances. Change only requested and maximum transient step to2.5ps or1ps. Record the actual maximum printed waveform step and reject capture exceeding the requested bound beyond0.1percent plus1e-18s printing allowance. Positive increasing times, finite values, no diagnostics and native solver readbacks remain mandatory. This printing allowance does not modify simulator tolerances.

Successful captures require cross-step waveform/current-decay comparison before even a schematic qualification. Incomplete0-turnoff remains a failure regardless of partial current decay. If failure remains tied to the same internal state, proceed to reduced model/device diagnosis; no further blind solver sweeps.

Test fixtures sample at1ps to verify the capture-size guard under both requested limits. Synthetic tests remain fault-injection tests, not native evidence. Core route44337630426 remains independently running and must not be restarted solely due to observation time.
