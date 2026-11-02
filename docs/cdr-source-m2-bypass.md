# Eight actual source-ground M2 bypass candidates

Input is the actual4ccf1212 sourceM1 GDS qualified physically by41401709497 and electrically REJECTED by41405079602. Source-M1 widening only saved0.6357ohm per ground path (41407813062). Via1-only41412504017 proposed zero admissible cuts and failed all eight drain coverages; its source and failure remain preserved.

This new experiment adds a physical route, not a Via1-only retry. For each actual eight source anchors, retain the existing1500x4000nm sourceM1 landing and construct a1400nm wide M2 column to the owned M3 ground access17.6um below. Add a290nm high landing joining the original minimum M2 access. Connect sourceM1 to newM2 using24Via1 cuts (3x8); connect newM2 to existingM3 using3Via2 cuts. All216new cuts are190nm squares on5nm grid with480nm pitch and50nm enclosure by both adjacent owned metals. All existing/other new cuts retain240nm spacing. New M2 stays240nm from foreignM2 and50nm from foreignVia1/Via2. Require full source patch ownership, original ground component identity and original extent. No newdevices or originalgeometry removal.

All13original native conductor unions must match GDS; current32query diagnosis selects exactly eight ground source anchors. Serialize only declared newM2/Via1/Via2 delta, prove every other layer unchanged and reverse all insertions to original material. Preserve partial proposals on refusals. Original95controls remain unchanged, plus8source-M2 attachment/foreign-geometry controls.

IHP main rules specify Via1/Via2 width190nm and spacing220nm; proposed240nm spacing is conservative. Native full560DRC is still mandatory and proposal guards do not certify DRC.
https://ihp-open-pdk-docs.readthedocs.io/en/latest/verification/drc/02_main_rules.html

Important electrical risk: ground resistance reductions can alter sourcebias and increase HBT current. The preceding small ground repair slightly worsened minimum HBT Vce. Generation claims no electrical improvement; keep all original loaded phase/current/Vce/sampler gates. Full physicalDRC/deep-flatLVS13, canonical partition proof, freshRC, loaded transient, actual current sharing/PVT/EM and bias-headroom review are required. Full closed-loop Gen3x4 PHY and mainchip signoff remain open.

All native operations/data run only in GitHub; no local CAD or waveform files.
