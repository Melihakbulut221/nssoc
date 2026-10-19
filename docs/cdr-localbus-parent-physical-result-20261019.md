# CDR local-bus parent physical result and fresh extraction — 2026-10-19

[Parent run39249146302](https://github.com/Melihakbulut221/nssoc/actions/runs/39249146302)
completed the unchanged560-category DRC screen and unsimplified deep/flat
484-device LVS with all9 original reference/geometry negative controls.
Census:116HBT,46LVNMOS,102rppd,11MIM,209taps. This is the complete
CDR phase-detector/V-I physical hierarchy, not the recovered-clock loop,
whole PCIe PHY or main SoC layout.

All41 source cards and16 macros remain. Only sampler internal routing
changed from folded_v11; native primitive drawings, placements, parameters
and public pins remain identical. Full immutable report:
docs/evidence/cdr-localbus-v12-parent-physical-pass-20261019.json.

A new cloud-only extraction workflow binds the actual158 planes,
51 logical nets,1394 native terminals and946 metal/reference anchors.
It re-extracts111 conductor components and applies the original19 plane,
12 model-binding and13 raw-RC corruption controls. Method differences are
restricted to source namespaces and pinned new geometry. No resistance or
capacitance scaling, omitted conductors or substituted circuit is allowed.

Pending: fresh extraction results, actual MIM plate capture/audit and
composition, then unchanged complete loaded early/late and fault waveforms.
Wire-only checks do not qualify substrate/RF extraction, closed-loop CDR,
full serial Gen3x4, mainchip integration or final setup/hold.
