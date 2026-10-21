# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2019-2025, The OpenROAD Authors
# Exact repair_timing body from dcf36133a369abc8f3c5e5738cd4d82e4903c0e0; only proc name differs.
proc nssoc_repair_timing_reference { args } {
  sta::parse_key_args "repair_timing" args \
    keys {-setup_margin -hold_margin -slack_margin \
            -libraries -max_utilization -max_buffer_percent -sequence \
            -recover_power -repair_tns -max_passes -max_iterations -max_repairs_per_pass} \
    flags {-setup -hold -allow_setup_violations -skip_pin_swap -skip_gate_cloning \
             -skip_size_down -skip_buffering -skip_buffer_removal -skip_last_gasp \
             -skip_vt_swap -skip_crit_vt_swap -match_cell_footprint -verbose}

  set setup [info exists flags(-setup)]
  set hold [info exists flags(-hold)]

  if { !$setup && !$hold } {
    set setup 1
    set hold 1
  }

  if { [info exists keys(-slack_margin)] } {
    utl::warn RSZ 76 "-slack_margin is deprecated. Use -setup_margin/-hold_margin"
    if { !$setup && $hold } {
      set setup_margin 0.0
      set hold_margin [rsz::parse_time_margin_arg "-slack_margin" keys]
    } else {
      set setup_margin [rsz::parse_time_margin_arg "-slack_margin" keys]
      set hold_margin 0.0
    }
  } else {
    set setup_margin [rsz::parse_time_margin_arg "-setup_margin" keys]
    set hold_margin [rsz::parse_time_margin_arg "-hold_margin" keys]
  }

  if { [info exists keys(-sequence)] } {
    set sequence $keys(-sequence)
  } else {
    set sequence ""
  }

  set allow_setup_violations [info exists flags(-allow_setup_violations)]
  set skip_pin_swap [info exists flags(-skip_pin_swap)]
  set skip_gate_cloning [info exists flags(-skip_gate_cloning)]
  set skip_size_down [info exists flags(-skip_size_down)]
  set skip_buffering [info exists flags(-skip_buffering)]
  set skip_buffer_removal [info exists flags(-skip_buffer_removal)]
  set skip_last_gasp [info exists flags(-skip_last_gasp)]
  set skip_vt_swap [info exists flags(-skip_vt_swap)]
  set skip_crit_vt_swap [info exists flags(-skip_crit_vt_swap)]
  rsz::set_max_utilization [rsz::parse_max_util keys]

  set max_buffer_percent 20
  if { [info exists keys(-max_buffer_percent)] } {
    set max_buffer_percent $keys(-max_buffer_percent)
    sta::check_percent "-max_buffer_percent" $max_buffer_percent
  }
  set max_buffer_percent [expr $max_buffer_percent / 100.0]

  set repair_tns_end_percent 1.0
  if { [info exists keys(-repair_tns)] } {
    set repair_tns_end_percent $keys(-repair_tns)
    sta::check_percent "-repair_tns" $repair_tns_end_percent
    set repair_tns_end_percent [expr $repair_tns_end_percent / 100.0]
  }

  set recover_power_percent -1
  if { [info exists keys(-recover_power)] } {
    set recover_power_percent $keys(-recover_power)
    sta::check_percent "-recover_power" $recover_power_percent
    set recover_power_percent [expr $recover_power_percent / 100.0]
  }

  set verbose 0
  if { [info exists flags(-verbose)] } {
    set verbose 1
  }

  set max_passes 10000
  if { [info exists keys(-max_passes)] } {
    set max_passes $keys(-max_passes)
  }

  set max_iterations -1
  if { [info exists keys(-max_iterations)] } {
    set max_iterations $keys(-max_iterations)
  }

  set match_cell_footprint [info exists flags(-match_cell_footprint)]
  if { [design_is_routed] } {
    est::set_parasitics_src "detailed_routing"
  }

  set max_repairs_per_pass 1
  if { [info exists keys(-max_repairs_per_pass)] } {
    set max_repairs_per_pass $keys(-max_repairs_per_pass)
  }

  sta::check_argc_eq0 "repair_timing" $args
  est::check_parasitics

  set recovered_power 0
  set repaired_setup 0
  set repaired_hold 0
  if { $recover_power_percent >= 0 } {
    set recovered_power [rsz::recover_power $recover_power_percent $match_cell_footprint $verbose]
  } else {
    if { $setup } {
      set repaired_setup [rsz::repair_setup $setup_margin $repair_tns_end_percent $max_passes \
        $max_iterations $max_repairs_per_pass $match_cell_footprint $verbose \
        $sequence \
        $skip_pin_swap $skip_gate_cloning $skip_size_down $skip_buffering \
        $skip_buffer_removal $skip_last_gasp $skip_vt_swap $skip_crit_vt_swap]
    }
    if { $hold } {
      set repaired_hold [rsz::repair_hold $setup_margin $hold_margin \
        $allow_setup_violations $max_buffer_percent $max_passes \
        $max_iterations $match_cell_footprint $verbose]
    }
  }

  return [expr $recovered_power || $repaired_setup || $repaired_hold]
}
