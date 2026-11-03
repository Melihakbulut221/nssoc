# Cloud continuation — checkpoint v359

Updated: 2026-11-03T23:02:29.148075+00:00

## Current CDR/PLL boundary and restored native divider map

Three existing cloud jobs remain independently monitored. No new simulation or physical repair is claimed by this source audit. The exact first-divider15-HBT/four-load terminal map referenced by the old root diagnosis was missing in the root continuation branch. Its exact original bytes are restored from a4bf51c1219fe521f34bb477035cdfc2a5012335, SHA256d405e7125ae9b838dc258d65ccfc91c03d0f3e9e03ccaed59a741dfb75058df5.

Read docs/pcie-cdr-pll-connection-audit-20261104.md and its source-bound JSON before designing the actual PLL/CDR parent. The current five topology sources match the existing first-latch diagnosis. The physical first-stage four collector loads areW8/L2.8um, despiteL2.12um in the generic sampler schematic. The RHI120-C8 capture and earlier PLL845 capture are distinct; neither acquisition is accepted. Recorded first-divider voltage evidence does not supply individual HBT branch currents.

The full current650 N1/N2 waveforms and original full64 mainchip route remain active requirements; continue their exact handles. Full serialGen3x4, final serial-integrated chip and setuphold remain unproven.

Exact RHI120 final window: 104.152221297MHz feedback, 5.002708790ns phase span; acquisition rejected. The older110.440674MHz figure belongs to the earlier PLL845 capture, not this first-latch diagnosis source.

Observed 2026-11-03T23:02:29.148075+00:00:
- 41699812301: in_progress/None
- 41733225660: in_progress/None
- 41734419971: in_progress/None


## History and execution
Previous actual route and failure handoff:
https://github.com/Melihakbulut221/nssoc/blob/3c82b96d25c5971ff5ade987018fa64ff1aa4fcf/CLOUD_RESUME.md
All earlier sources, complete reports and failed runs remain preserved.
All native CAD/geometry/runtime/electrical payloads stay cloud-only. The local
workspace is empty; source and derived-text API coordination uses RAM.
The8-hour monitor remains read-only with automatic_native_dispatch=false.
Poll existing exact handles; do not restart on observation timeouts.
Full serialPHY, completed mainchip routing and final setup/hold must all
pass real complete verification before the overall goal is complete.
