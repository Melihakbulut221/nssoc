# CDR v59: measured headroom and resistor hypotheses

This is a source-only design matrix. It selects real resistor dimensions for two isolated physical experiments; it does not claim that their OP, timing, layout or full PHY passes. The original eight electrical failures from run40108285374 remain failures. Saved-capture ledger40171679250 reproduced the original full measurements before producing these observations.

The first candidates are:
- C/D gain-bias shunts: native184/185/222/223, W4µm/L7.4µm → W4µm/L5.0µm.
- A/B slave collector loads: native191/194/202/205, W32µm/L2.6µm → W32µm/L2.0µm.

Run each isolated arm through source review, fresh physical/RC qualification, clean OP and the original loaded gates. Combine these two sets only after isolated evidence justifies it. All transistors, source currents, external clocks, P/N wiring, thresholds and expected bits stay unchanged. No previously extracted RC may serve as proof of the changed geometry.

## Evidence and actual paths

The hash-pinned JSON beside this document records every native ID, C/B/E node, resistor terminal, same-row observation and formula input. It binds the actual500-device model (124HBT/50MOS/98rppd/7MIM/221 finite taps),24574R/15694C, three complete113475×1152-column captures and the original rejected source.

D gain59 shares collector cluster21 with pullup183/shunt185; gain60 uses cluster22/pullup182/shunt184. C gain111 uses cluster121/pullup221/shunt223; gain112 uses cluster122/pullup220/shunt222. These are four symmetric collector-bias paths. The separate follower loads187/188/225/226 and the actual input conductors remain unchanged.

B hold71/72 cross-couple collector clusters59/58 and share emitter cluster71; their slave loads are194/191, bleed198. A hold87/88 use clusters88/87, emitter100, loads205/202 and bleed210. The master-stage loads and all C/D slave loads remain unchanged.

All eight native clock-tail current differences reverse515 times in each case. This does not prove clock phase or timing, but a missing collector-voltage zero crossing cannot justify swapping clocks.

## Same-row gain headroom

The nominal C/D gain maximum VCE is1.6708–1.6813V; the unchanged upper bound is1.6V. At the worst actual row (nominal_early, device60, row12736,3.91140625ns), C=2.0414751116V, E=.3602203744V, B=1.1705803567V and Ic=.7434262mA total/Nx4. The required reduction of C−E is81.2547mV. This low instantaneous Ic is not evidence of an overcurrent; it also cannot replace the other collector-node currents.

For a deliberately simplified two-resistor load, let Ru connect sourceS to collectorC, Rd connect C to groundG, beta=Ru/Rd, a=Ru/Ru_new and b=Rd/Rd_new. Calibrating the unknown aggregate load to the original same-row C gives:

    C_new - C = [(a-1)(S-C) + (b-1) beta (G-C) - Ru delta_I] / (a+b beta)
    VCE_new = VCE + (C_new-C) - delta_E

This is conditional on the collapsed connection approximation. It is not measured KCL. The native resistor terminals and HBT terminals are distinct distributed vertices; S=prescribed source rail and G=0 are explicit placeholders, not claims about their actual local voltages. delta_I includes every changed missing branch/displacement current. delta_E is not assumed small by evidence.

The exact frozen PDK has two end contacts with total70/W_um ohms at27°C, independent of length. Thus pure L scaling is too optimistic. The transparent reference used here is Rs*L/W plus those contacts, with the separately specified body/contact temperature factors. It deliberately omits native mismatch/geometry corrections, bias dependence and self-heating. The source audit pins those omitted terms; the unchanged native model must evaluate them later.

| Candidate | Conditional nominal worst sampled gain VCE | Design tradeoff |
|---|---:|---|
| Pullup1.8→2.2µm |1.6049V|Insufficient even in this reference model; not selected.|
| Pullup1.8→2.4µm |1.5680V|Lowers bias but raises incremental collector resistance and can slow the already late sampler.|
| Shunt7.4→5.0µm |1.5764V|Lowers bias and reduces incremental load resistance; reduces gain and increases shunt demand.|

The shunt is the first isolated arm because it avoids the pullup arm's larger incremental resistance. The reference Ru||Rd changes approximately59.2561→56.2126Ω for shunt5.0; the pullup2.4 arm instead gives73.8913Ω. No delay improvement follows from these numbers.

At the worst nominal row, the shunt projection has only23.6mV of conditional voltage margin. An aggregate load reduction of about.420mA or an emitter decrease of23.6mV could erase it; changes can occur together. The pullup alternative has32.0mV conditional margin and a source-rail-error coefficient−.24698, so a100mV lower actual local rail could change its projection by+24.7mV. These are sensitivity warnings about the approximation, not observed candidate behavior. All maximum/minimum sample-row projections are retained in JSON; extrema may move in a real transient.

## Same-row hot hold headroom

At hot device71's worst row68864 (20.81578125ns), C=1.8332860321V, B=2.2005924336V, E=1.4747481012V. Thus VBE=.7258443325V, B−C=.3673064016V, VCE=.3585379309V. The original minimum is.4V.

The useful exact identity is VCE=VBE−(B−C). Changing both cross-coupled loads moves both C and the opposite collector driving B/E. A fixed-emitter estimate would overstate the improvement. If VBE and branch-current difference are frozen, then VCE_new=VBE−r_eff*(B−C); the worst row requires r_eff≤.8871186 (at least11.288% differential-resistance reduction).

For the observed hot125°C/res_wcs corner, drawn-body+contact arithmetic gives old R≈25.6977Ω and:
- L2.2: r≈.8580306, conditional VCE≈.4106842V.
- L2.0: r≈.7870460, conditional VCE≈.4367573V.

If only fraction f of effective differential resistance is the changed intrinsic resistor and the remainder is unchanged series wiring, r_eff=1−f(1−r). At the worst row, L2.2 needs f≥.7951, whereas L2.0 needs f≥.5301. These fractions are not measured. Unequal distributed paths, nonlinear regeneration, changed Ic and changed VBE can invalidate the projection. L2.0 is selected as the first isolated physical experiment; L2.2 remains a smaller perturbation alternative.

The four hot rows project.4368–.4596V for L2.0 only under those assumptions. None is a predicted minimum over the new waveform. Reduced output swing could hurt the unchanged100mV margin or affect the next stage despite faster local RC. The original37.5ps/256-bit/VI/device gates decide.

## Scope and next executable work

This commit contains no generator, workflow activation, circuit execution or accepted geometry. It records the exact dimensions and priorities for the next source implementation. Only four native rppd length parameters change in each first arm. Width, endpoints, device count, compact models, transistor multiplicity, actual bias source currents and clock polarity do not change.

The next generator must preserve original native ownership/placements/ports and all material outside the four declared resistor replacements, with exact child/root drawing and serialization guards. A changed resistor footprint can require actual native endpoint routing; source arithmetic cannot waive that. Required gates remain560-category DRC, full500 deep/flat LVS, strict wires/978 anchors/113 measured components (new counts must be measured), seven intrinsic MIMs, both native RC orders and original negative controls. New geometry gets fresh RC.

Then restore the exact runtime; require clean zero-source OP, actual124HBT OFF readback, no UIC and no numerical diagnostics. Evaluate the original ten cases,34.25ns/.3125ps,256 source bits,150fF/50fF loading,100mV and37.5ps, all HBT/MOS/MIM and VI/phase limits, stopped-clock and disabled-VI controls. A partial screen is labeled as such. Combined and deferred arms are not launched until isolated evidence is recorded.

Earlier39149512255 shortened all16 loads on a different484-device baseline and failed; those results remain preserved. Earlier v29 deliberately increased loads to2.6 to improve selector headroom. This new isolated four-load experiment can also lose selector headroom or downstream margin. These historical tradeoffs are part of the matrix, not erased by the new arithmetic.

No local artifact, native archive or simulator was used to prepare this design. Exact sources and bounded published JSON were inspected in RAM. The arithmetic is source-level hypothesis sizing; native control tests have not executed for a candidate.
