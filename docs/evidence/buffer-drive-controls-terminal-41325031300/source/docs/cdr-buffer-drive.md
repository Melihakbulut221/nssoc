# A/C buffer drive trial

Parent: width2 source `2a62d651d415fba8db3c5b758d1b66c05cde3a38`, native run41306148937, wave diagnosis41309130293 (proof f5623ecd4f4b400c63548f01966be8fae753fcbd).

That parent passed device/VI and phase screening (37.080 mV against30 mV), but failed all six data gates. At0.6UI the A divider had255 source-valid samples and no wrong signs; its buffered output had111 wrong signs. A/C tail minimum active VCE was0.573442/0.486867V against0.4V. These observations motivate a drive-strength trial; they do not establish the cause or prove the proposed repair.

## Exact change

- HBT XD0126 and XD0129: nx4 to8, retaining emitter dimensions and all ordered physical terminals.
- Collector loads XD0232, XD0233, XD0243, XD0244: length1.8um to0.9um, retaining width8um and all terminals.
- Preserve width2 twelve-divider parent, all124 HBT instances,200MOS units/50origins, all remaining dimensions, interface, source/measurement bodies and electrical limits.

The intended experiment increases A/C tail drive and reduces collector load impedance together. Actual current, swing, settling, headroom and power must come from native measurements. This is distinct from prior40-HBT downsizing run41299745896, which failed phase and data.

Every changed physical record is pinned to the original composition, each native model card is validated, and reversing the six edits must restore all model bytes and descriptors exactly. The500-device binder and650-device expanded model receive identical edits. Original compiled binding must expose nx8 for both tails; per-emitter current limits remain unchanged. Missing/duplicated/miswired/retargeted/repeated edits are rejected.

## Cloud execution

Run source-controls independently on the exact source first. The simulate dispatch requires that successful controls run and a separately reserved empty exact-source release. Original engine/runtime,1200-second engine budget,1302-column raw capture, all device/VI/data/phase decisions and failed results are retained. Native acquisition, simulation, analysis and publication occur only on GitHub.

Existing distributed interconnect RC is retained for comparison only. No new geometry or RC extraction is claimed. A promising electrical result still requires regenerated legal layout, fresh extracted parasitics and full corner/closed-loop/link qualification. This experiment cannot establish full serial PHY, chip routing, final setup/hold or production acceptance.

Current status: source implementation prepared; controls and native outcome must be recorded from actual jobs.
