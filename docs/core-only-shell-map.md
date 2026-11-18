# Core-only pad-shell technology mapping

This cloud experiment maps the real 192-bit serial status mailbox to pinned IHP standard cells, retaining 76 signal/4 supply pad instances and exactly one explicit `soc_top` boundary. The boundary is generated from the authenticated current mapping port contract. It does not contain a behavioral core replacement during synthesis. Native IHP pad Verilog supplies blackbox pin definitions; native standard-cell Liberty drives DFF/logic mapping. All inputs and output netlists are hashed.

The mapped shell is then simulated with native IHP pad and standard-cell models and the previously qualified explicit **core stub**, exercising GPIO/QSPI direction/readback, I2C open-drain behavior and the serial MBIST frame. A pad-enable inversion must still fail. This proves only the shell's tested functional behavior after technology mapping; it is not exhaustive equivalence, actual core boot, routed shell, bundled-data CDC closure, padframe integration, DRC/LVS, ESD or manufacturing approval.

Next physical integration needs the authenticated routed core views, a matching physical boundary/placement strategy, power connections and shell/clock/CDC routing. The current detailed-route producer remains untouched. No fabricated pass or timing exception is used to join the domains.
