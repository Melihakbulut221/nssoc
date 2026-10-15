# HBT polarity and operating-limit provenance

The existing tree review uses `abs(VBE) <= 1 V`, `abs(VCE) <= 1.6 V`, post-startup `VCE >= 0.4 V` and current per emitter <=3mA. These remain unchanged engineering screens. They are not sufficient evidence of foundry-qualified safe operating area.

The public IHP npn13g2 process-monitor table lists BVCEO minimum/target1.4/1.6V, BVCBO3.8/4.8V, BVEBO1.0/1.6V and maximum collector current3.5mA for a0.07x0.9um emitter. The 1.6V BVCEO target is not a guaranteed maximum operating voltage. [IHP bipolar parameters](https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/03_bjt_params.html#npn13g2-specs).

A.r measures emitter-to-base breakdown with collector current zero and IEB1uA. It does not specify an absolute, polarity-independent forward-VBE maximum. A.p and A.q also use distinct measurement conditions. [IHP measurement conditions](https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/04_meas_cond.html).

Original native compact cold-HBT observation38771786806 has a **positive** VBE1.023395260872V at3.27075ns, not a measured reverse emitter-base voltage of that magnitude. Its legacy engineering failure stays recorded. Neither this observation nor its current below the tabulated maximum proves lifetime, thermal, reverse-junction, RF or transient safe operation. Do not increase device area solely on the premise that this positive voltage crossed BVEBO.

`cloud_hbt_polarity.py` adds signed native extrema and clearly labelled comparisons with process-monitor values, without replacing any original acceptance field. It records every captured HBT, actual indices/times/terminal voltages and per-emitter current. Controls distinguish positive/negative1.023V, preserve both legacy failures, and reject malformed captures. Separate qualification and measured waveform/function margins remain mandatory.

The rejected data8/select10 candidate still fails original bits and interfaces in the hot wire case, independently of this provenance issue. Its rejection is unchanged.
