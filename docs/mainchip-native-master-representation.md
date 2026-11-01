# Native master representation correction

Actual run41305082558 completed scoped restore-plan and OpenROAD import. Expected and actual restored DEF match exactly atSHA256a5183887cf3733b0c8cf9070af98156596d624a11808e955403daf350b80a36c. The unchanged physical route-delta validator then rejected master equality; final audits did not finish.

Readout41307592168 authenticated all51 native archive members and compared complete saved descriptors. All58masters and154480instances match,as do every nonroute field hash. There are no added/removed masters,geometry or MPin-order differences. Source snapshot construction returns innermost pin boxes as tuples; persisted JSON reads them as lists. This Python representation mismatch explains the false equality failure.

Source05d336a1b1b681c9d96b71d464c5ea430835e438 converts only these innermost tuples to lists. Serialized bytes must remain identical; no coordinates,layers,orders,duplicates,master values or database contents change. The original physical validators remain byte-identical and receive matching representations.49 independent controls41308125643 reproduce the bug and retain corruption detection; all2361 original source pins verify. Corrected native readback is still required.

Full failure proof:docs/evidence/scoped-restoration-native-terminal-41305082558. Actual master readout:docs/evidence/master-diagnosis-terminal-41307592168. Neither proves complete connectivity,zeroDRC,final timing or fullPHY.
