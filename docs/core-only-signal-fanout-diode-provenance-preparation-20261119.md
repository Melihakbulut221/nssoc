# Signal fanout diode provenance preparation — 2026-11-19

The 413-buffer candidate moves 720 diode signal terminals. In-memory inspection of the immutable prior evidence artifact 14552601238 (SHA256 c087cc956123c59fe350ce6538d6b4250abbbc43c9ba3384928f4ddd0c372cbf) found 698 in the cumulative 1410 added-diode inventory and 22 outside it. All 698 original connections match the candidate specification. Inventory SHA256: c13b289360d5248714ff38c4a2a9cc36accecf634847c3e99d6683de25d1e376.

The new helper pins all 720 moves and the exact 22 exceptions. It requires proof of original master and connectivity for every moved diode in the baseline netlist, verifies the cumulative inventory against that netlist, preserves its size and unrelated entries, and separately verifies all 720 moved exports. No missing diode can be silently exempted. Synthetic mutation tests are dispatched separately; their results do not prove physical connectivity or signoff.

Routing run 44573258297 is independent and must pass its geometry and antenna gates before this helper is used in fresh extraction. Actual baseline/export evidence integration remains pending. Package, PCB and attached devices are not selected; external I/O timing is not production-approved. Production scope excludes PCIe and Ethernet; the 50 MHz constraint and 5% derating remain unchanged.
