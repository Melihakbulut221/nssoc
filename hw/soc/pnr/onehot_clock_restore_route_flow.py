# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Keep FIXED clock wire geometry while native antenna repair inspects routed wires."""
import hashlib
from pathlib import Path
from interface_flow import Interfaces
from replay_onehot_detailed_route_flow import GuardedDetailedRouting
from replay_onehot_routed_extraction_flow import AuditedRCX,AuditedRoutedSTA
from librelane.flows import Flow
from librelane.steps import OpenROAD,Odb

ORIGINAL_SCRIPT_SHA='b4d67fe2ed81269a0907480cdcaf09442ccf8f86325ae04a8a0f9032355c8880'
ANTENNA_CALL='        set diodes_inserted [log_cmd repair_antennas {*}$arg_list]'
FIXED_ANTENNA_CALL=r'''
        # Native ANT WireBuilder recognizes net-level ROUTED metadata when
        # deciding whether an existing detailed wire must be synthesized.
        # Change only that metadata during ANT; keep its FIXED encoded wire.
        set nssoc_fixed_net [[ord::get_db_block] findNet clknet_3_5_0_pcie_clk_i]
        if {[$nssoc_fixed_net getWireType] ne "FIXED"} {
            error "Fixed clock metadata missing before native antenna repair"
        }
        set nssoc_fixed_wire [$nssoc_fixed_net getWire]
        if {$nssoc_fixed_wire eq "NULL"} {error "Fixed clock wire missing"}
        $nssoc_fixed_net setWireType ROUTED
        set nssoc_ant_code [catch {
            set diodes_inserted [log_cmd repair_antennas {*}$arg_list]
        } nssoc_ant_result nssoc_ant_options]
        $nssoc_fixed_net setWireType FIXED
        if {[$nssoc_fixed_net getWire] ne $nssoc_fixed_wire} {
            error "Native antenna repair replaced the physical fixed clock wire"
        }
        if {$nssoc_ant_code} {
            return -options $nssoc_ant_options $nssoc_ant_result
        }
        puts "NSSOC_FIXED_CLOCK_ANTENNA_METADATA_RESTORED"
'''.strip('\n')

class FixedClockDetailedRouting(GuardedDetailedRouting):
    def get_script_path(self):
        original=Path(super().get_script_path())
        raw=original.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==ORIGINAL_SCRIPT_SHA,'Pinned guarded native DRT script changed'
        text=raw.decode()
        assert text.count(ANTENNA_CALL)==1
        candidate=text.replace(ANTENNA_CALL,FIXED_ANTENNA_CALL)
        assert candidate.replace(FIXED_ANTENNA_CALL,ANTENNA_CALL)==text
        output=Path(self.step_dir)/'fixed_clock_native.tcl'
        output.write_text(candidate)
        return str(output)

@Flow.factory.register()
class OnehotClockRestoreRoute(Interfaces):
    Steps=[FixedClockDetailedRouting,OpenROAD.CheckAntennas,Odb.ReportDisconnectedPins,AuditedRCX,AuditedRoutedSTA]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
