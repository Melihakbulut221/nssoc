# New pad schematic diagnostic binding — 2026-11-19

Upstream I/O snapshot `cc9afba57e0ec1b5ba77e6bbb638ba9dbe5866b8` changes the 4mA pad subcircuit port order from `vss vdd iovss iovdd p2c c2p c2p_en pad` to `pad c2p p2c c2p_en vdd vss iovdd iovss`. Internal gate nodes become net2 (NMOS) and net1 (PMOS), as confirmed by the new GateDecode signature `ngate pgate core en iovdd vdd vss`. The circuit adds substrate tap resistors at the pad and protection cells. This is not just a file extension or naming change.

The diagnostic preserves old successful six-case evidence separately and creates a new six-case test with correctly mapped ports and observed gate nodes. New schematic source SHA256 `1d53ab7df431b717ef5aff43e1117c0224681d5cc84886da37a319280ee958d6`. The official corrected diode library remains hash-bound. Existing MOS/resistor runtime bundle is retained explicitly for this compatibility probe; this is not a fully qualified PDK revision migration or production signoff. If the new circuit requires model capabilities absent from the bundle, fail and inspect rather than silently alter parameters.

Before final adoption, compare GDS geometry/connectivity and requalify coherent model, Liberty, padframe and extraction views. In particular, the newer 3.5 ns Liberty default is not authority to edit the old 1.2 ns model in place.
