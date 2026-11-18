# Provisional integrated chip database

Cloud assembly combines the verified mapped pad/status shell, provisional native core LEF and native pad-ring placement. All producer archives and selected views are pinned by digest/run/head; native tech/stdcell/I/O LEFs are pinned to IHP c4b8.

The native OpenDB builder instantiates every mapped shell cell and the core boundary, preserves every source JSON terminal connection, adds real tie cells for literal0/1 nets, and explicitly binds core VPWR/VGND to VDD/VSS. Standard-cell VDD/VSS and I/O vdd/vss/iovdd/iovss remain in the correct four distinct supply domains. The 296 ring instances and core are fixed; shell cells remain UNPLACED. Core translation (336.96,362.88)um is provisional. Native pad rectangles define external BPin geometry.

Checks cover exact logical terminal connections, missing/wrong core supply and missing-clock negative controls, no core/pad footprint overlap, and database write/readback invariance. Connectivity in this ODB does NOT imply metal power or signal routes exist. Ties still need physical placement/fanout repair. The core boundary derives from pre-DRT geometry and must be replaced/rechecked against final DRT. No integrated timing, CDC, DRC/LVS, ESD, GDS or manufacturing acceptance is asserted.
