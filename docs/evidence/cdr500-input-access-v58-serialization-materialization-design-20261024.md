# Exact serialized-material comparison repair — 2026-10-24

Native raw readback40095863916 at source8285822268be0197fcb1b5bb67eb139d243daed5 reproduced the original rejection. Summary asset672268553 SHA256 bdc258e7bebd9bb6d14cc967318473dd052e730bbc6ad76ba546903438ce12a3 contains the exact witness.

Only layers(63,0) and(134,25) produced raw XOR is_empty=false. In both, expected polygon count=0, actual polygon count=0, XOR polygon count=0, every area=0, no polygon records exist, both directed differences are empty, and materialized merged XOR is empty. All33 original layers were inspected,135 original child drawings/labels/instances match, and all25 public labels match. This is an empty lazy polygon-Region representation issue; no actual missing/extra conductor was observed. It does not establish DRC/LVS or electrical qualification.

The repair materializes the serialized polygon Region with .merged() before the existing exact XOR in both post-read comparison loops. This matches the existing pre-write material comparisons and initial snapshots. It does not skip either empty layer, exclude any layer, introduce an area threshold or permit nonzero material difference. Expected material remains original plus the exact recorded additions. Public text and original-child instance comparisons remain independent exact checks.

Three additional native controls operate on the actual serialized layout: remove a10nm square proven fully inside the original M3 lane; add a5nm square proven outside the macro material; corrupt one actual serialized public label. Every fault must reject. Original9 geometry controls,3 exact high-cut controls,8 native selection controls,all500 original devices,24 added upper via instances,20metal rectangles,original cut geometry,children,boundary and all source hashes remain mandatory.

The read-only raw witness is retained for transparency and is separately identified from the materialized acceptance implementation. The branch workflow returns to full physical mode only after independent source review. Full560-category DRC, deep+flat500-device LVS and12 faults, fresh planes/strict113-component978-anchor wire gates follow. Fresh MIM-aware two-order RC and original10 loaded cases remain required; no electrical or resistance benefit is inferred.

Control scope: the three mutations operate on KLayout Regions derived from the reread GDS and actual label records in the cloud native process RAM. They do not write and reread separately corrupted GDS files.
