# Resized core antenna repair round one

Run 44420129432, head 3e56fb282941bad19a74019ff73a65d41f058141, artifact 14482852777, SHA256 6ceddd39ed4711d1735da8e5be09b1ac79b56de71d6c3d7631561aa100a13e80. All 18 manifest output hashes verified.

Native routing completed with process return code zero. Router DRC remains zero. Antenna violations fell from 234 nets / 265 pins to 15 nets / 15 pins; the strict zero-antenna assertion correctly rejects this candidate. 534 diodes were added, giving 106617 instances. Original geometry/connectivity audit passed. All 1068 added diode power terminals have verified same-supply metal contact, with no reported failure. This is not full PDN or transistor signoff.

Routed ODB: 0bccd439a9efe8b7463ae5d32f1ae42616c49872548bf6aabaaa35e3eb721eb5.

Round two binds to this exact report, artifact, hash and ODB, preserving all existing instances and adding only native antenna diodes. It retains the same 10 percent repair margin, strict connectivity/geometry and physical power-contact checks, and zero router DRC / antenna acceptance gates. No PDK limits or timing constraints change. Fresh RC/timing is still required for the eventual antenna-clean candidate; concurrent diagnostic run 44422630920 concerns the previous, pre-repair route only.
