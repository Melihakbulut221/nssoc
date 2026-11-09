#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
#
# Pre-placement timing screen of the PCIe packet domain.
#
#   run.sh <typ.lib> <slow.lib> <out_dir> <openroad command...>
#
# Synthesises pcie_timing_top.v (the packet-async soc_top instantiation of
# the PCIe subsystem) with the soc_top recipe used by the main-chip
# implementation probe: the same 21 PCIe sources, typical-corner mapping,
# Kogge-Stone carry mapping, abc.constr and `abc -D 20`. Flip-flops are then
# renamed after the register they drive (or, without a public output net,
# after their RTL source line), so every path report names RTL registers.
# The netlist-naming steps drop the recipe's `-purge` so register names
# survive; that changes names only, not logic.
#
# OpenROAD then places the netlist alone (40% utilisation, random pins),
# runs repair_design (buffering of high-fanout nets such as the packet
# reset and link status) and reports both corners ("placed"), then runs an
# sizing-only repair_timing ("sized"), then an unbounded repair_timing,
# and reports again ("repaired"). Clocks are ideal
# and parasitics are placement estimates with the PDK's LAYERS_RC: an
# estimate for comparing RTL variants, not a sign-off number.
set -euo pipefail
TYP=$1; SLOW=$2; OUT=$3; shift 3
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
RTL=$ROOT/hw/soc/rtl/pcie
mkdir -p "$OUT"
SRCS=""
for block in crc16_byte acknak_tx packet_tx crc32_byte lcrc_rx sequence_rx \
  lcrc_tx packet_endpoint tlp_stream tlp_regs link_packets dllp_rx replay_tx \
  reliable_packets credit_tx flow_packets rx_credit fc_tx buffered_flow_packets \
  apb_arbiter apb_cdc; do
  SRCS="$SRCS $RTL/soc_pcie_$block.v"
done
printf 'set_driving_cell sg13g2_buf_4\nset_load 0.005\n' > "$OUT/abc.constr"
cat > "$OUT/syn.ys" <<YS
read_liberty -lib $TYP
read_verilog -sv -defer $SRCS
read_verilog -defer $HERE/pcie_timing_top.v
hierarchy -check -top pcie_timing_top
synth -flatten -top pcie_timing_top -run begin:fine
techmap -map +/techmap.v -map +/choices/kogge-stone.v
synth -top pcie_timing_top -run fine
opt
dfflibmap -liberty $TYP
opt
abc -liberty $TYP -constr $OUT/abc.constr -D 20
setundef -zero
opt_clean
hilomap -singleton -hicell sg13g2_tiehi L_HI -locell sg13g2_tielo L_LO
splitnets
clean
rename -wire -suffix _reg t:sg13g2_df* t:sg13g2_sdf* t:sg13g2_dl*
rename -src t:sg13g2_df* t:sg13g2_sdf* t:sg13g2_dl*
write_verilog -norename -noattr -noexpr -nohex -nodec $OUT/pcie.sta.v
tee -o $OUT/area.rpt stat -liberty $TYP
YS
yosys -q -l "$OUT/syn.log" -s "$OUT/syn.ys" > /dev/null
grep -E "Chip area|cells$|Number of cells" "$OUT/area.rpt" | tail -3 || true
cat > "$OUT/pcie.sdc" <<'SDC'
create_clock -name pcie_clk_i -period 4.0 [get_ports pcie_clk_i]
create_clock -name clk_i -period 20.0 [get_ports clk_i]
set_clock_groups -asynchronous -group [get_clocks pcie_clk_i] -group [get_clocks clk_i]
set_clock_uncertainty 0.25 [all_clocks]
set_clock_transition 0.15 [all_clocks]
set pcie_in [get_ports {pcie_link_up_i pcie_training_i pcie_retrain_done_i pcie_function_id_i* pcie_rx_data_i* pcie_rx_sop_i pcie_rx_eop_i pcie_rx_error_i pcie_rx_valid_i pcie_rx_dllp_i pcie_tx_ready_i}]
set pcie_out [get_ports {pcie_rx_ready_o pcie_tx_data_o* pcie_tx_sop_o pcie_tx_eop_o pcie_tx_valid_o pcie_tx_dllp_o pcie_tx_replay_o pcie_initialized_o pcie_error_o pcie_retrain_request_o}]
set_input_delay -clock pcie_clk_i -max 0.8 $pcie_in
set_input_delay -clock pcie_clk_i -min 0.2 $pcie_in
set_output_delay -clock pcie_clk_i -max 0.8 $pcie_out
set_output_delay -clock pcie_clk_i -min 0.2 $pcie_out
set_input_delay -clock clk_i 4.0 [get_ports {ep_pready ep_pslverr ep_prdata*}]
set_output_delay -clock clk_i 4.0 [get_ports {ep_psel ep_penable ep_pwrite ep_paddr* ep_pwdata* ep_pstrb*}]
set_false_path -from [get_ports rst_sys_n]
set_driving_cell -lib_cell sg13g2_buf_4 -pin X [all_inputs]
set_load 0.006 [all_outputs]
set_max_fanout 10 [current_design]
set_timing_derate -early 0.95
set_timing_derate -late 1.05
SDC
LEF_READ=""
for lef in ${LEFS:-}; do LEF_READ="$LEF_READ
read_lef $lef"; done
cat > "$OUT/sta.tcl" <<TCL
$LEF_READ
define_corners typ slow
read_liberty -corner typ $TYP
read_liberty -corner slow $SLOW
read_verilog $OUT/pcie.sta.v
link_design pcie_timing_top
read_sdc $OUT/pcie.sdc
# OpenSTA renamed the path-count flags; accept either spelling.
if {[catch {report_checks -group_path_count 1 -endpoint_path_count 1 -format end > /dev/null}]} {
  set G -group_count; set E -endpoint_count
} else { set G -group_path_count; set E -endpoint_path_count }
proc reports {stage} {
  global G E
  set regs_ck [all_registers -clock pcie_clk_i -clock_pins]
  set regs_d [all_registers -clock pcie_clk_i -data_pins]
  # The same paths without the three link status flops and the packet reset
  # release as startpoints, so the logic behind their fanout trees shows.
  set core_ck {}
  foreach pin \$regs_ck {
    if {![regexp {^(pcie_link_up_q|pcie_training_q|pcie_retrain_done_q|packet_reset_release|packet_rst_n|u_pcie\.up_|u_pcie\.flow\.up_|u_pcie\.flow\.packets\.up_)} [get_full_name \$pin]]} {
      lappend core_ck \$pin
    }
  }
  foreach c {typ slow} {
    report_checks -corner \$c -path_delay max -from \$core_ck -to \$regs_d \$G 5000 \$E 1 -format end > $OUT/\${stage}_core_end_\$c.rpt
    report_checks -corner \$c -path_delay max -from \$core_ck -to \$regs_d \$G 1500 \$E 1 -fields {net} -digits 3 > $OUT/\${stage}_core_full_\$c.rpt
    puts "NSSOC_PCIE_REPORT \$stage \$c"
    report_checks -corner \$c -path_delay max -from \$regs_ck -to \$regs_d \$G 5000 \$E 1 -format end > $OUT/\${stage}_r2r_end_\$c.rpt
    report_checks -corner \$c -path_delay max -from \$regs_ck -to \$regs_d \$G 40 \$E 1 -fields {net} -digits 3 > $OUT/\${stage}_r2r_full_\$c.rpt
    report_checks -corner \$c -path_delay max -from [get_clocks pcie_clk_i] -to [get_clocks pcie_clk_i] \$G 5000 \$E 1 -format end > $OUT/\${stage}_all_end_\$c.rpt
    report_checks -corner \$c -path_delay max -from [get_clocks pcie_clk_i] -to [get_clocks pcie_clk_i] \$G 10 \$E 1 -fields {net} -digits 3 > $OUT/\${stage}_all_full_\$c.rpt
    report_checks -corner \$c -path_delay min -from [get_clocks pcie_clk_i] -to [get_clocks pcie_clk_i] \$G 3 -format end > $OUT/\${stage}_hold_end_\$c.rpt
  }
}
reports synth
initialize_floorplan -utilization 40 -aspect_ratio 1 -core_space 10 -site CoreSite
make_tracks
place_pins -hor_layers Metal3 -ver_layers Metal2
foreach {l r c} {Metal2 2.53519E-03 1.69121E-04 Metal3 1.54329E-03 1.82832E-04 Metal4 6.31424E-04 1.66454E-04 Metal5 6.84051E-04 8.57431E-05} {
  set_layer_rc -layer \$l -resistance \$r -capacitance \$c
}
set_wire_rc -signal -layer Metal3
set_wire_rc -clock -layer Metal4
global_placement -density 0.6
estimate_parasitics -placement
repair_design
detailed_placement
estimate_parasitics -placement
reports placed
# Sizing and pin swapping only: buffering in this unrouted context builds
# long buf_1 chains that say more about the estimator than the logic.
if {[catch {repair_timing -setup -setup_margin 0 -skip_buffering} err]} {
  puts "NSSOC_PCIE_SIZED_SKIPPED \$err"
} else {
  estimate_parasitics -placement
  reports sized
}
puts "NSSOC_PCIE_REPAIR_BEGIN"
repair_timing -setup -setup_margin 0
detailed_placement
estimate_parasitics -placement
reports repaired
puts "NSSOC_PCIE_REPAIR_DONE"
TCL
timeout ${STA_TIMEOUT:-5400} "$@" "$OUT/sta.tcl" > "$OUT/sta.log" 2>&1 || { echo "STA_EXIT=$?"; tail -40 "$OUT/sta.log"; }
grep -E "NSSOC_PCIE|RSZ-00|GPL-0002|DPL-" "$OUT/sta.log" | head -40 || true
grep -iE "error|warning" "$OUT/sta.log" | sort | uniq -c | head -20 || true
python3 -B "$HERE/paths.py" "$OUT" | tee "$OUT/summary.txt"
