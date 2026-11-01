# Coupled sampler load and headroom candidate

This is one exploratory twelve-resistor circuit candidate, not physical signoff. It follows original loaded run41260582673, rejected four-shunt run41268684044, complete comparison41269888640 and full-wave clock/data diagnosis41271280278.

Hypothesis: reducing the eight sampler output collector pullup resistances can improve loaded output settling and raise the A/B output common mode feeding the C/D input buffers. The latter may offset the excessive VCE introduced at those input buffers by the four-shunt-only candidate. Reduced differential swing is a real risk; the original100mV/37.5ps sampler gates remain unchanged and may reject it.

Exact intrinsic changes from authenticated baseline:
- XD0175,XD0176,XD0191,XD0194,XD0202,XD0205,XD0212,XD0214: rppd L2.6um to1.5um, W32um unchanged. These are the eight physical pullups of the four sampler Q output nets.
- XD0184,XD0185,XD0222,XD0223: rppd L5um to7.4um, W4um unchanged. These are the same four input-amplifier shunts from the rejected experiment.
- All terminals, other device parameters, all remaining circuit cards and baseline wire RC remain byte/value identical. Exact original-model authentication precedes the reversible12-token rewrite.

Original prepare and measure executable bodies remain identical in an independent candidate namespace. No changes to original1151 vectors,10ohm clock/data input source resistances,150fF sampler loads,50fF XOR loads,125ps UI, clock/data sequences, stage/phase/VI predicates or device stress limits. Full original13 native binding controls are required before simulation. Source controls reject13 circuit corruptions and5 archive corruptions and verify original frozen catalog/module/function identity. Synthetic cards used for these tests are never native simulation evidence.

The candidate reuses baseline distributed RC only for an exploratory electrical screen. Length changes alter real geometry and parasitics; no candidate PCell layout, new DRC/LVS or fresh RC is claimed. Even an electrical pass requires those steps plus corners/closed-loop integration before acceptance. The IHP rppd PCell explicitly uses process minL/minW, geometry and contacts; a future layout must be generated/checked, not inferred from length tokens alone:
https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/main/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/rppd_code.py

All execution is on GitHub. Qualify exact source controls first; independently reserve an empty exact-source release before the sole actual simulation can enter native admission. Preserve complete baseline/native/candidate/results on success or failure. Source branch: codex/cdr-sampler-load-headroom. Output release tag: cloud-results-RUN-1-cdr-sampler-load. Final PHY, physical acceptance and timing remain false.
