# Slew ECO neighbor-contact correction — 2026-11-19

Run 44462498877, head f0ae390358c93878e00e9297a5b8986e2d49d59b, attempt 1 failed correctly. Artifact 14501991516 SHA256 f85161b2a2f9adb151690f1573590652670e80f205e1efe74a879670b2055cb7; all 45 outputs verified. Rejected ODB 13384a5a3bd32205e8c82e7ef67e004099f664f293cca963645da9a545ed7a60 must not be admitted as physically clean.

Native detailed routing reached zero DRC at iteration 23 and antenna nets/pins were zero. Exact identity, all 103071 unselected non-power records and 2113 clocks passed. Independent decoded geometry found no disconnected nets or missing terminal geometry, but ten Metal2 contacts across four net pairs:

- nssoc_sta_n_55098 versus nssoc_sta_n_58640: 3 contacts.
- net5477 versus nssoc_sta_n_55117: 2 contacts.
- net4410 versus nssoc_sta_n_55140: 2 contacts.
- nssoc_sta_n_56385 versus nssoc_sta_n_56322: 3 contacts.

Each pair contains one of the 14 selected incident nets and an otherwise fixed neighbor. New routing admits exactly these four neighbors in addition to the 14 original nets, starting from the verified preparation ODB 4fc368e1d6ca1d5661f048b8cad148d38554176849b003245bf2f74454edf14b (run 44461789690), not from the shorted result. All 18 nets must be SIGNAL; no clock changes are authorized. Preservation count becomes 103067 unaffected non-power records, still 2113 clocks. Native encoded FIXED wires protect every other route. Independent geometry, antenna and DRC checks remain mandatory; no waiver is added. Fresh nominal RC and three-corner timing follow only after physical admission. The earlier clean nominal setup/hold baseline remains unchanged and production approval remains open.
