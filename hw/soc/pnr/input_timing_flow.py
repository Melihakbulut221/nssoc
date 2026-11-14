from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA,CORNERS,ElectricalPostCTS
EXTRA = r"""
set index 0
foreach {direction names} {from {pcie_rx_dllp_i pcie_rx_error_i pcie_rx_eop_i pcie_rx_sop_i pcie_rx_data_i[0] pcie_rx_data_i[1] pcie_rx_data_i[2] pcie_rx_data_i[3] pcie_rx_data_i[4] pcie_rx_data_i[5] pcie_rx_data_i[6] pcie_rx_data_i[7] pcie_rx_valid_i pcie_function_id_i[0] pcie_function_id_i[1] pcie_function_id_i[2] pcie_function_id_i[3] pcie_function_id_i[4] pcie_function_id_i[5] pcie_function_id_i[6] pcie_function_id_i[7] pcie_function_id_i[8] pcie_function_id_i[9] pcie_function_id_i[10] pcie_function_id_i[11] pcie_function_id_i[12] pcie_function_id_i[13] pcie_function_id_i[14] pcie_function_id_i[15] pcie_training_i} to {eth_txd_o[0] eth_txd_o[1] eth_txd_o[2] eth_txd_o[3] eth_txd_o[4] eth_txd_o[5] eth_txd_o[6] eth_txd_o[7] eth_tx_en_o eth_tx_er_o}} {
 foreach name $names {
  set port [get_ports [list $name]]
  if {[llength $port]!=1} {error "Missing IO $name"}
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
foreach name {{$abc$734844$auto$blifparse.cc:397:parse_blif$770181/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$770185/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$770194/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$770206/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$772210/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$772648/A1} {$abc$734844$auto$blifparse.cc:397:parse_blif$772649/A1} {$abc$734844$auto$blifparse.cc:397:parse_blif$772650/A1} {$abc$734844$auto$blifparse.cc:397:parse_blif$772652/A1} {$abc$734844$auto$blifparse.cc:397:parse_blif$772653/A1} {$abc$734844$auto$blifparse.cc:397:parse_blif$772756/A1} {$abc$734844$auto$blifparse.cc:397:parse_blif$772762/A1} {$abc$734844$auto$blifparse.cc:397:parse_blif$773765/A1} {$abc$734844$auto$blifparse.cc:397:parse_blif$774033/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$774496/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$778729/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778732/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778748/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778749/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778752/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778753/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778755/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778757/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778759/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778760/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778762/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778763/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778768/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778769/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$778776/A1} {$abc$734844$auto$blifparse.cc:397:parse_blif$778849/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$778866/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$778880/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$778902/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$779053/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$779069/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$779137/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779140/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779143/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779144/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779146/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779154/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779155/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779156/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779157/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779160/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779162/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779163/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779165/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779166/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779167/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779170/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779171/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779172/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779173/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779174/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779175/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779177/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779178/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779179/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779181/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779182/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779183/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779184/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779185/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779186/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779187/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779188/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779189/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$779943/A1} {$abc$734844$auto$blifparse.cc:397:parse_blif$781072/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$781082/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$781084/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$781086/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$785333/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785334/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785336/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785337/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785338/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785339/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785340/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785342/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785343/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785344/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785345/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785346/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785347/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785350/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785354/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785356/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785358/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785364/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785365/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785366/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785367/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785370/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785371/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785372/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785373/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$785380/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$800578/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$800580/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$804752/A0} {$abc$734844$auto$blifparse.cc:397:parse_blif$805337/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$805033/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$805688/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$805043/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$736143/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$761569/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$761616/A} {$abc$734844$auto$blifparse.cc:397:parse_blif$749749/A}} {
 set target [get_pins [list $name]]
 if {[llength $target]!=1} {error "Missing feedback pin $name"}
 foreach type {max min} {
  puts "%OL_CREATE_REPORT io-$index-$type.rpt"
  puts "NSSOC_TARGET_BRANCH_PIN $name"
  report_checks -through $target -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
  puts "%OL_END_REPORT"
 }
 incr index
}

"""
class InputSTA(SingleCornerSTA):
 def get_script_path(self):
  p=Path(super().get_script_path());s=p.read_text()
  if not s.rstrip().endswith('write_libs'):raise RuntimeError('Unexpected native STA termination')
  q=Path(self.step_dir)/'input_timing_native.tcl';q.write_text(s+'\n'+EXTRA);return str(q)

ECO = r"""
set block [ord::get_db_block]
set master [[ord::get_db] findMaster sg13g2_dlygate4sd3_1]
if {$master eq "NULL"} {error "Missing native delay cell"}
set before {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
set original_placement {}
foreach inst [$block getInsts] {
 dict set original_placement [$inst getName] [list [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus]]
 if {[$inst getPlacementStatus] eq "PLACED"} {$inst setPlacementStatus FIRM}
}
set old_count [llength [$block getInsts]]
set old_nets [llength [$block getNets]]
set changed {}
set branch_index 0
foreach pair { {{$abc$734844$auto$blifparse.cc:397:parse_blif$770181/A} {$auto$ff.cc:337:slice$159932/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$770185/A} {$auto$ff.cc:337:slice$159933/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$770194/A} {$auto$ff.cc:337:slice$159935/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$770206/A} {$auto$ff.cc:337:slice$159938/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$772210/A} {$auto$ff.cc:337:slice$160454/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$772648/A1} {$auto$ff.cc:337:slice$160640/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$772649/A1} {$auto$ff.cc:337:slice$160641/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$772650/A1} {$auto$ff.cc:337:slice$160642/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$772652/A1} {$auto$ff.cc:337:slice$160644/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$772653/A1} {$auto$ff.cc:337:slice$160645/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$772756/A1} {$auto$ff.cc:337:slice$160701/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$772762/A1} {$auto$ff.cc:337:slice$160703/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$773765/A1} {$auto$ff.cc:337:slice$161241/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$774033/A} {$auto$ff.cc:337:slice$161432/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$774496/A} {$auto$ff.cc:337:slice$161755/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778729/A0} {$auto$ff.cc:337:slice$162815/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778732/A0} {$auto$ff.cc:337:slice$162818/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778748/A0} {$auto$ff.cc:337:slice$162832/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778749/A0} {$auto$ff.cc:337:slice$162833/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778752/A0} {$auto$ff.cc:337:slice$162835/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778753/A0} {$auto$ff.cc:337:slice$162836/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778755/A0} {$auto$ff.cc:337:slice$162838/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778757/A0} {$auto$ff.cc:337:slice$162840/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778759/A0} {$auto$ff.cc:337:slice$162842/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778760/A0} {$auto$ff.cc:337:slice$162843/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778762/A0} {$auto$ff.cc:337:slice$162844/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778763/A0} {$auto$ff.cc:337:slice$162845/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778768/A0} {$auto$ff.cc:337:slice$162850/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778769/A0} {$auto$ff.cc:337:slice$162851/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778776/A1} {$auto$ff.cc:337:slice$162856/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778849/A} {$auto$ff.cc:337:slice$162887/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778866/A} {$auto$ff.cc:337:slice$162892/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778880/A} {$auto$ff.cc:337:slice$162896/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$778902/A} {$auto$ff.cc:337:slice$162903/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779053/A} {$auto$ff.cc:337:slice$163058/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779069/A} {$auto$ff.cc:337:slice$163071/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779137/A0} {$auto$ff.cc:337:slice$163237/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779140/A0} {$auto$ff.cc:337:slice$163240/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779143/A0} {$auto$ff.cc:337:slice$163243/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779144/A0} {$auto$ff.cc:337:slice$163244/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779146/A0} {$auto$ff.cc:337:slice$163246/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779154/A0} {$auto$ff.cc:337:slice$163253/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779155/A0} {$auto$ff.cc:337:slice$163254/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779156/A0} {$auto$ff.cc:337:slice$163255/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779157/A0} {$auto$ff.cc:337:slice$163256/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779160/A0} {$auto$ff.cc:337:slice$163258/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779162/A0} {$auto$ff.cc:337:slice$163260/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779163/A0} {$auto$ff.cc:337:slice$163261/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779165/A0} {$auto$ff.cc:337:slice$163263/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779166/A0} {$auto$ff.cc:337:slice$163264/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779167/A0} {$auto$ff.cc:337:slice$163265/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779170/A0} {$auto$ff.cc:337:slice$163267/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779171/A0} {$auto$ff.cc:337:slice$163268/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779172/A0} {$auto$ff.cc:337:slice$163269/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779173/A0} {$auto$ff.cc:337:slice$163270/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779174/A0} {$auto$ff.cc:337:slice$163271/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779175/A0} {$auto$ff.cc:337:slice$163272/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779177/A0} {$auto$ff.cc:337:slice$163274/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779178/A0} {$auto$ff.cc:337:slice$163275/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779179/A0} {$auto$ff.cc:337:slice$163276/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779181/A0} {$auto$ff.cc:337:slice$163277/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779182/A0} {$auto$ff.cc:337:slice$163278/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779183/A0} {$auto$ff.cc:337:slice$163279/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779184/A0} {$auto$ff.cc:337:slice$163280/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779185/A0} {$auto$ff.cc:337:slice$163281/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779186/A0} {$auto$ff.cc:337:slice$163282/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779187/A0} {$auto$ff.cc:337:slice$163300/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779188/A0} {$auto$ff.cc:337:slice$163301/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779189/A0} {$auto$ff.cc:337:slice$163302/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$779943/A1} {$auto$ff.cc:337:slice$163777/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$781072/A} {$auto$ff.cc:337:slice$164426/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$781082/A} {$auto$ff.cc:337:slice$164431/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$781084/A} {$auto$ff.cc:337:slice$164432/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$781086/A} {$auto$ff.cc:337:slice$164433/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785333/A0} {$auto$ff.cc:337:slice$166474/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785334/A0} {$auto$ff.cc:337:slice$166475/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785336/A0} {$auto$ff.cc:337:slice$166477/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785337/A0} {$auto$ff.cc:337:slice$166478/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785338/A0} {$auto$ff.cc:337:slice$166479/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785339/A0} {$auto$ff.cc:337:slice$166480/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785340/A0} {$auto$ff.cc:337:slice$166481/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785342/A0} {$auto$ff.cc:337:slice$166482/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785343/A0} {$auto$ff.cc:337:slice$166483/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785344/A0} {$auto$ff.cc:337:slice$166484/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785345/A0} {$auto$ff.cc:337:slice$166485/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785346/A0} {$auto$ff.cc:337:slice$166486/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785347/A0} {$auto$ff.cc:337:slice$166487/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785350/A0} {$auto$ff.cc:337:slice$166490/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785354/A0} {$auto$ff.cc:337:slice$166493/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785356/A0} {$auto$ff.cc:337:slice$166495/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785358/A0} {$auto$ff.cc:337:slice$166497/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785364/A0} {$auto$ff.cc:337:slice$166502/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785365/A0} {$auto$ff.cc:337:slice$166503/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785366/A0} {$auto$ff.cc:337:slice$166504/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785367/A0} {$auto$ff.cc:337:slice$166505/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785370/A0} {$auto$ff.cc:337:slice$166508/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785371/A0} {$auto$ff.cc:337:slice$166509/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785372/A0} {$auto$ff.cc:337:slice$166510/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785373/A0} {$auto$ff.cc:337:slice$166511/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$785380/A0} {$auto$ff.cc:337:slice$166517/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$800578/A0} {$auto$ff.cc:337:slice$173075/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$800580/A0} {$auto$ff.cc:337:slice$173077/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$804752/A0} {$auto$ff.cc:337:slice$175046/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$805337/A} {$auto$ff.cc:337:slice$175514/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$805033/A} {$auto$ff.cc:337:slice$175806/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$805688/A} {$auto$ff.cc:337:slice$175809/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$805043/A} {$auto$ff.cc:337:slice$175810/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$736143/A} {$auto$ff.cc:337:slice$180554/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$761569/A} {$auto$ff.cc:337:slice$181399/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$761616/A} {$auto$ff.cc:337:slice$181686/Q}}
 {{$abc$734844$auto$blifparse.cc:397:parse_blif$749749/A} {$auto$ff.cc:337:slice$349960/Q}}} {
 lassign $pair sinkname sourcename
 set slash [string last / $sinkname]
 set instname [string range $sinkname 0 [expr {$slash-1}]]
 set pinname [string range $sinkname [expr {$slash+1}] end]
 set target_inst [$block findInst $instname]
 if {$target_inst eq "NULL"} {error "Missing feedback instance $instname"}
 set sink [$target_inst findITerm $pinname]
 if {$sink eq "NULL" || [[$sink getMTerm] getIoType] ne "INPUT"} {error "Missing feedback input $sinkname"}
 set net [$sink getNet]
 if {$net eq "NULL"} {error "Unconnected SRAM enable"}
 set drivers {}
 foreach pin [$net getITerms] {if {[[$pin getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $pin}}
 if {[llength $drivers]!=1 || [llength [$net getBTerms]]!=0} {error "Unexpected SRAM enable source"}
 set driver [lindex $drivers 0]
 set actual_source "[[$driver getInst] getName]/[[$driver getMTerm] getName]"
 if {$actual_source ne $sourcename} {error "Feedback source mismatch $actual_source expected $sourcename"}
 set location [[$driver getInst] getLocation]
 set orientation [[$driver getInst] getOrient]
 set stem nssoc_feedback_hold_${branch_index}
 foreach name [list ${stem}_0 ${stem}_1] {
  if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_out] ne "NULL"} {error "ECO name collision"}
 }
 $sink disconnect
 set last $net
 foreach suffix {0 1} {
  set inst [odb::dbInst_create $block $master ${stem}_${suffix}]
  set next [odb::dbNet_create $block ${stem}_${suffix}_out]
  [$inst findITerm A] connect $last
  [$inst findITerm X] connect $next
  $inst setOrient $orientation
  $inst setLocation {*}$location
  $inst setPlacementStatus PLACED
  set last $next
 }
 $sink connect $last
 dict set changed $sink $last
 incr branch_index
}
if {[dict size $changed]!=111 || [llength [$block getInsts]]!=$old_count+222 || [llength [$block getNets]]!=$old_nets+222} {error "Wrong ECO census"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $before $name]} {continue}
 lassign [dict get $before $name] cell pins
 if {[[$inst getMaster] getName] ne $cell} {error "Original master changed"}
 foreach pin [$inst getITerms] {
  set expected [dict get $pins [[$pin getMTerm] getName]]
  if {[dict exists $changed $pin]} {set expected [dict get $changed $pin]}
  if {[$pin getNet] ne $expected} {error "Original incidence changed"}
 }
}
puts "NSSOC_222_NATIVE_DELAY_CELLS_111_FEEDBACK_BRANCHES_ONLY"
"""
class TrainingHoldECO(ElectricalPostCTS):
 id='NSSOC.TrainingHoldECO'
 name='Two native delay cells on111 qualified short feedback branches'
 def get_script_path(self):
  p=Path(super().get_script_path());s=p.read_text()
  a=s.index('# Buffer I/O');b=s.index('report_floating_nets -verbose',a)
  s=s[:a]+ECO+'\n'+s[b:]
  if 'log_cmd repair_design' in s or 'unset_propagated_clock [all_clocks]' in s:raise RuntimeError('Unexpected broad repair or ideal clock')
  if s.count('write_views')!=1:raise RuntimeError('Unexpected native write boundary')
  s=s.replace('write_views','\nforeach inst [$block getInsts] {\n set name [$inst getName]\n if {![dict exists $original_placement $name]} {continue}\n lassign [dict get $original_placement $name] location orientation status\n if {[$inst getLocation] ne $location || [$inst getOrient] ne $orientation} {error "Original placement moved: $name"}\n $inst setPlacementStatus $status\n}\nputs "NSSOC_ORIGINAL_PLACEMENT_UNCHANGED_AND_STATUSES_RESTORED"\n'+'\nwrite_views')
  q=Path(self.step_dir)/'training_hold_eco.tcl';q.write_text(s);return str(q)

@Flow.factory.register()
class InputTiming(Interfaces):
 Steps=[TrainingHoldECO]+[type('Input'+n,(InputSTA,),dict(id='NSSOC.Input'+n,corner=c))for n,c in CORNERS]
if __name__=='__main__':
 from librelane.__main__ import cli
 cli()
