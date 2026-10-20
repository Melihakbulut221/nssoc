# SPDX-License-Identifier: Apache-2.0
"""Regenerate native guides after the proved fanout placement/connectivity changes."""
from pathlib import Path
from onehot_clock_restore_route_flow import FixedClockDetailedRouting
from interface_flow import Interfaces
from replay_onehot_routed_extraction_flow import AuditedRCX,AuditedRoutedSTA
from librelane.flows import Flow
from librelane.steps import OpenROAD,Odb

FRESH_GUIDES=r'''
# The input has only stale data wires removed. Source geometry, netlist,
# power and clock wires were independently checked before this native step.
set_routing_layers -signal Metal2-TopMetal2 -clock Metal4-TopMetal2
set_global_routing_layer_adjustment * 0.0
# General adjustment does not overwrite persisted per-layer adjustments.
set nssoc_adjustment_report [open "$::env(STEP_DIR)/native-layer-adjustments.tsv" w]
puts $nssoc_adjustment_report "layer\tbefore\tafter"
foreach nssoc_layer_name {Metal2 Metal3 Metal4 Metal5 TopMetal1 TopMetal2} {
    set nssoc_layer [[ord::get_db_tech] findLayer $nssoc_layer_name]
    set nssoc_before [$nssoc_layer getLayerAdjustment]
    set_global_routing_layer_adjustment $nssoc_layer_name 0.0
    set nssoc_after [$nssoc_layer getLayerAdjustment]
    puts $nssoc_adjustment_report "$nssoc_layer_name\t$nssoc_before\t$nssoc_after"
    puts "NSSOC_LAYER_ADJUSTMENT $nssoc_layer_name $nssoc_before -> $nssoc_after"
    if {abs($nssoc_after) > 1e-9} { error "Persisted layer adjustment was not cleared" }
}
close $nssoc_adjustment_report
set_macro_extension 0
global_route -congestion_iterations 200 -verbose
write_guides "$::env(STEP_DIR)/fresh-fanout.guide"
write_db "$::env(STEP_DIR)/fresh-fanout-global.odb"
puts "NSSOC_FRESH_FANOUT_GUIDES_FROM_CURRENT_NATIVE_PINS"
'''.strip('\n')
class FreshFanoutDetailedRouting(FixedClockDetailedRouting):
    def get_script_path(self):
        original=Path(super().get_script_path())
        text=original.read_text()
        anchor='set i 0\n'
        assert text.count(anchor)==1
        candidate=text.replace(anchor,FRESH_GUIDES+'\n'+anchor)
        assert candidate.replace(FRESH_GUIDES+'\n'+anchor,anchor)==text
        output=Path(self.step_dir)/'fresh_fanout_native.tcl'
        output.write_text(candidate);return str(output)
@Flow.factory.register()
class OnehotFreshFanoutRoute(Interfaces):
    Steps=[FreshFanoutDetailedRouting,OpenROAD.CheckAntennas,Odb.ReportDisconnectedPins,AuditedRCX,AuditedRoutedSTA]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
