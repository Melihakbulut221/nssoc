# Qualified local lane mux experiment

Exact RTL SHA256 2a345ba4082873f73fd8f308880a1f8d29651e24c12bbeaf9ac20b8f4082636e. Qualification run43659882138/head7b3d47cd6bd0666f035f6c231f5edefb705ca1c6: two full-module equivalence proofs and eight300000-cycle traffic cases, with two formal and eight traffic mutations rejected. All result/log hashes independently verified.

SOC_PCIE_RX_LOCAL_LANE_NEXT distributes only the next-state mux inside hierarchy-preserved copies. Master lane and original synchronous reset-free copy registers remain unchanged. Prior independent local cursor failed equivalence and is rejected. No timing exceptions or extra cycles. Native mapping/boot/CTS/route/STA acceptance is pending; old netlist hold-zero is not transferable.
