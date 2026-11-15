# SPDX-License-Identifier: Apache-2.0
"""Measure setup and hold for every current PCIe input and Ethernet output."""
from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA, CORNERS
EXTRA = r"""
set index 0
foreach {direction names} {from {pcie_training_i pcie_function_id_i[0] pcie_function_id_i[1] pcie_function_id_i[2] pcie_function_id_i[3] pcie_function_id_i[4] pcie_function_id_i[5] pcie_function_id_i[6] pcie_function_id_i[7] pcie_function_id_i[8] pcie_function_id_i[9] pcie_function_id_i[10] pcie_function_id_i[11] pcie_function_id_i[12] pcie_function_id_i[13] pcie_function_id_i[14] pcie_function_id_i[15] pcie_rx_data_i[0] pcie_rx_data_i[1] pcie_rx_data_i[2] pcie_rx_data_i[3] pcie_rx_data_i[4] pcie_rx_data_i[5] pcie_rx_data_i[6] pcie_rx_data_i[7] pcie_rx_dllp_i pcie_rx_error_i pcie_rx_eop_i pcie_rx_sop_i pcie_rx_valid_i} to {eth_txd_o[0] eth_txd_o[1] eth_txd_o[2] eth_txd_o[3] eth_txd_o[4] eth_txd_o[5] eth_txd_o[6] eth_txd_o[7] eth_tx_en_o eth_tx_er_o}} {
 foreach name $names {
  set port [get_ports [list $name]]
  if {[llength $port]!=1} {error "Missing boundary port $name"}
  foreach type {max min} {
   puts "%OL_CREATE_REPORT io-$index-$type.rpt"
   puts "NSSOC_TARGET_PORT $name"
   if {$direction eq "from"} {
    report_checks -from $port -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
   } else {
    report_checks -to $port -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
   }
   puts "%OL_END_REPORT"
  }
  incr index
 }
}
if {$index!=40} {error "Boundary census changed"}
puts "NSSOC_IO_PATHS_MEASURED"
"""
class TargetIOSTA(SingleCornerSTA):
    def get_script_path(self):
        p=Path(super().get_script_path())
        s=p.read_text()
        if not s.rstrip().endswith("write_libs"):raise RuntimeError("Unexpected native STA termination")
        q=Path(self.step_dir)/"target_io.tcl";q.write_text(s+"\n"+EXTRA);return str(q)
@Flow.factory.register()
class TargetIOTrial(Interfaces):
    Steps=[type("TargetIO"+n,(TargetIOSTA,),dict(id="NSSOC.CorrpreTargetIOAfter"+n,corner=c)) for n,c in CORNERS]
if __name__=="__main__":
    from librelane.__main__ import cli
    cli()
