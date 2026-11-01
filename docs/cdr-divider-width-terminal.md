# Divider width native result: phase passes,whole candidate rejected

Native41306148937/source2a62d651d415fba8db3c5b758d1b66c05cde3a38 completed in863.844793s with engine0,no diagnostics and unchanged sources. Device/VI gates pass. Phase37.0801368476mV passes30mV,improving on the twelve-divider parent's29.3294064481mV. Only12physical rppd widths changed1um->2um; HBT Nx and200MOS units remain original.

All six original data gates still fail. A/B clock-to-valid42.34375/37.96875ps exceed37.5ps. C/D have30/33 wrong-sign samples; X/Y have418/6. A phase pass is not complete CDR or serialPHY acceptance. The whole candidate remainsREJECTED_WHOLE_MIM_PD650_LOADED.

Full111-file evidence is preserved in docs/evidence/divider-width-native-terminal-41306148937. Native raw/model/runtime remain on release430565351. ModelSHA2567468f677a97cba341dbdc350ec2a1ab5c70cfd48f1233f81e449e23935b69fc6. Study actual sampler and downstream waveforms next without relaxing any original gate. Retained distributed wireRC is exploratory; no regenerated layout/freshPEX or closed-loop qualification is implied.
