# MOS model domain audit — cloud-only

Pinned native-model audit 41285573717 found 42 of 50 MOS definitions outside the stated 0.15–10 um width range; all current ng=1. The unexecuted W36->54 um single-finger trial is superseded and MUST NOT be dispatched. Width is passed through as w=w in captured wrapper branches; changing ng alone is not a demonstrated model-domain repair. First join all50 original MOS to actual physical gate geometry and verify the full core nf/ng mapping, then qualify a physically consistent split-device/finger implementation preserving total original W/L and bias. No simulation/geometry change or acceptance occurred in these audits.

## Evidence

The model declarations are from the exact three model files used by rejected native run41282867236/source8c7b5cdd86447fe374ae06064f2fef735a7c9b91. GitHub revalidated all109 archived members. No model files, native archive, raw waves or layout databases were acquired locally. Derived audit outputs retain file hashes, bounded declarations and all50 MOS parameters.

- Run41285179612/source4df22e76092a84ac3723780cbce20f1abb477394: initial audit; width-range continuation was not captured.
- Run41285372486/source401e440ecea29b5f58d49a67a316de99b217da4b: captures declared L0.13–10um/W0.15–10um; wrapper selector coverage incomplete.
- Run41285573717/sourcee8ca7fd04bef1410db26a069c1e5b198fd15a8e5: corrected selector with four controls, continued range context, complete50-device census and explicit domain rejection.

The actual pinned cornerMOSlv.lib SHA25603d505847c880d233b341be115a1e5460edf4d8e9b3e8a7df791a52fa4455d67 and sg13g2_moslv_parm.lib SHA256cbf10b8453a18bb70b8ad0d6e40faa0937338e699b5460947a94900db6c92a6e declare that range. sg13g2_moslv_mod.lib SHA256124c48af28aee8f4788170b50dbb4d798e7d830c6bb37516f749e16f676fa9db shows w=w and ng-dependent junction formulas. Its captured lines do not yet establish every nf/core mapping: inspect those branches before deriving a correction.

All50 ng=1:32 devicesW36um,4W53.335um,2W32um,4W64um and8W8um. Therefore42 definitions exceed the declared maximum. Existing stress passes do not establish model calibration outside this domain.

Canonical physical locations at e7b9d3a152295b7f870ea2783c90f5c6116547a1, docs/evidence/cdr-via2-m3-canonical-view-terminal-41243752186/readback/native/view/candidate/wire/device-locations01.json show one gate polygon for inspected ids1,7,11,36,47, including the wide devices. This is a five-device inspection, not a complete physical50-device join. Complete that join on GitHub before claiming all physical fingers are identified.

[IHP LVS FET documentation](https://ihp-open-pdk-docs.readthedocs.io/en/main/verification/lvs/04_01_fets.html) describes total extracted width and W/ng finger width; [device documentation](https://ihp-open-pdk-docs.readthedocs.io/en/latest/contents/device_libraries/mosfets.html) documents width/finger parameters. These conventions do not override the pinned simulator wrapper or authorize a metadata-only correction.

## Required continuation

Preserve original total width, length and bias while qualifying geometry/model mapping. Do not assume increasing ng makes an unchanged w=w core in-range. An explicitly split parallel-device realization may be needed; it requires independent schematic, native layout, junction geometry, matching extraction, DRC/LVS and fresh RC. Preserve all original 500-device identities or explicitly prove any expansion/mapping and every untouched device. Do not mix domain correction with slave-drive resizing.

Original electrical limits remain unchanged. No full serial PHY, fresh-PEX circuit, mainchip serial integration or final timing acceptance is claimed. All numerical analysis, tests, simulation and CAD execute on GitHub; local coordination uses API/source/derived text in RAM only.
