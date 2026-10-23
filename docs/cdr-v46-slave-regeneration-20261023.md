# CDR slave regeneration hypothesis after full native stage separation

Both l39 full-capture observations completed in run39993707351 without changing
the original120 HBT/four sampler results. In the early case all255 master
outputs meet100mV at the original37.5ps deadline, while64 outputs of each C/D
slave do not. Slave selector collector-current crossing lags its base crossing
by approximately0.6-0.8ps; that observation alone does not explain the full
approximately8ps worst-case output delay excess.

The measured slave data minimum VCE is approximately0.526V; the least slave
hold VCE is0.470805V, only71mV above the original gate. Increasing collector
resistance or current therefore consumes little available voltage margin.
The master-area reduction v45 worsened timing and stays rejected.

Two finite candidates target the actually late stage: four C/D slave hold
HBTs Nx4->3, or those four plus four slave data HBTs Nx4->3. The parent l39
master circuitry and every selector/follower/load/bias remain unchanged.
The parent maximum current per proposed emitter is checked independently in
both measured phases against the original3mA gate before simulation.
This tests regeneration capacitance in a different measured stage; it does
not assume a speed improvement from reduced area.

The same original256-bit/34.25ns,1104-column capture, actual8GHz10ohm clocks,
150fF sampler/50fF XOR loads, device/data/phase gates and source controls run.
No gate, window, waveform or extracted R/C card is relaxed or edited.
No candidate is promoted without the original full gates. Any promising
intrinsic result still requires actual new geometry, DRC/LVS and fresh RC.
